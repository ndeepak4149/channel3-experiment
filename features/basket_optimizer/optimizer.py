"""
Core optimization algorithm.

Strategy:
  1. Build offer matrix: product → list of (domain, price, url, availability)
  2. Start with the cheapest offer per product (greedy baseline)
  3. Try consolidating products to fewer retailers to unlock free shipping
  4. Return the assignment with the lowest total (price + shipping)
"""
from __future__ import annotations
from itertools import product as cartesian_product
from typing import Dict, List, Tuple

from channel3_sdk.types import ProductDetail

from .models import BasketItem, BasketOptimization, RetailerSummary
from .shipping import get_shipping_cost, gap_to_free_shipping

MAX_BRUTE_FORCE = 5   # for baskets ≤ 5 items, try all offer combos


def _build_offer_matrix(products: List[ProductDetail]) -> List[List[dict]]:
    """
    Returns a list (one per product) of available offers, sorted cheapest first.
    """
    matrix = []
    for p in products:
        offers = [
            {
                "product_id":    p.id,
                "product_title": p.title,
                "domain":        o.domain,
                "price":         o.price.price,
                "compare_at":    o.price.compare_at_price,
                "url":           o.url,
                "availability":  o.availability,
            }
            for o in (p.offers or [])
            if o.availability == "InStock"
        ]
        if not offers:
            # fall back to any offer
            offers = [
                {
                    "product_id":    p.id,
                    "product_title": p.title,
                    "domain":        o.domain,
                    "price":         o.price.price,
                    "compare_at":    o.price.compare_at_price,
                    "url":           o.url,
                    "availability":  o.availability,
                }
                for o in (p.offers or [])
            ]
        offers.sort(key=lambda x: x["price"])
        matrix.append(offers)
    return matrix


def _total_cost(assignment: List[dict]) -> Tuple[float, float, Dict[str, List[dict]]]:
    """
    Given one offer per product, compute total cost including shipping.
    Returns (total_with_shipping, total_shipping, retailer_groups).
    """
    # Group by retailer
    groups: Dict[str, List[dict]] = {}
    for offer in assignment:
        groups.setdefault(offer["domain"], []).append(offer)

    total_shipping = 0.0
    for domain, items in groups.items():
        subtotal = sum(i["price"] for i in items)
        shipping, _, _ = get_shipping_cost(domain, subtotal)
        total_shipping += shipping

    subtotal_total = sum(o["price"] for o in assignment)
    return subtotal_total + total_shipping, total_shipping, groups


def _optimize(offer_matrix: List[List[dict]]) -> List[dict]:
    """
    Find the assignment (one offer per product) with lowest total cost.
    Uses brute-force for ≤ MAX_BRUTE_FORCE products, greedy otherwise.
    """
    if not offer_matrix:
        return []

    n = len(offer_matrix)

    if n <= MAX_BRUTE_FORCE:
        # Brute-force: try all combinations (cap each product at top 4 offers)
        capped = [offers[:4] for offers in offer_matrix]
        best_total = float("inf")
        best_assignment = [offers[0] for offers in capped]

        for combo in cartesian_product(*capped):
            total, _, _ = _total_cost(list(combo))
            if total < best_total:
                best_total = total
                best_assignment = list(combo)

        return best_assignment
    else:
        # Greedy: pick cheapest offer per product, then try to consolidate
        assignment = [offers[0] for offers in offer_matrix]
        best_total, _, _ = _total_cost(assignment)

        # Try swapping each product to other retailers to reduce shipping
        improved = True
        while improved:
            improved = False
            for i, offers in enumerate(offer_matrix):
                for offer in offers[:4]:
                    trial = assignment[:i] + [offer] + assignment[i+1:]
                    trial_total, _, _ = _total_cost(trial)
                    if trial_total < best_total - 0.01:
                        assignment = trial
                        best_total = trial_total
                        improved = True
                        break

        return assignment


def optimize_basket(products: List[ProductDetail]) -> BasketOptimization:
    """
    Main entry point. Returns a full BasketOptimization result.
    """
    if not products:
        raise ValueError("Basket is empty.")

    offer_matrix = _build_offer_matrix(products)

    # Remove products with no offers
    valid = [(p, offers) for p, offers in zip(products, offer_matrix) if offers]
    if not valid:
        raise ValueError("No products have available offers.")

    products_valid = [p for p, _ in valid]
    offer_matrix_valid = [offers for _, offers in valid]

    best_assignment = _optimize(offer_matrix_valid)

    subtotal = sum(o["price"] for o in best_assignment)
    best_total, best_shipping, groups = _total_cost(best_assignment)

    # ── Build BasketItem list ─────────────────────────────────────────────────
    items: List[BasketItem] = []
    for offer in best_assignment:
        cat = offer.get("compare_at")
        disc = round((cat - offer["price"]) / cat * 100, 1) if cat and cat > offer["price"] else None
        items.append(BasketItem(
            product_id          = offer["product_id"],
            product_title       = offer["product_title"],
            recommended_retailer= offer["domain"],
            price               = offer["price"],
            original_price      = cat,
            discount_pct        = disc,
            product_url         = offer["url"],
            availability        = offer["availability"],
        ))

    # ── Build RetailerSummary list ────────────────────────────────────────────
    retailer_breakdown: Dict[str, RetailerSummary] = {}
    notes: List[str] = []

    for domain, domain_offers in groups.items():
        sub = sum(o["price"] for o in domain_offers)
        shipping, threshold, is_free = get_shipping_cost(domain, sub)

        note = None
        gap = gap_to_free_shipping(domain, sub)
        if gap and gap > 0:
            note = f"Spend ${gap:.2f} more at {domain} to unlock free shipping"
            notes.append(note)

        retailer_breakdown[domain] = RetailerSummary(
            domain=domain,
            items=[o["product_title"][:50] for o in domain_offers],
            subtotal=round(sub, 2),
            shipping=round(shipping, 2),
            order_total=round(sub + shipping, 2),
            free_shipping_threshold=threshold if threshold else None,
            note=note,
        )

    # ── Cheapest single-retailer baseline ─────────────────────────────────────
    # Find which retailer could fulfil all products and at what cost
    all_domains = set(o["domain"] for offers in offer_matrix_valid for o in offers)
    cheapest_single_domain = None
    cheapest_single_total = float("inf")

    for domain in all_domains:
        # Check if this retailer has all products
        per_product_prices = []
        for offers in offer_matrix_valid:
            domain_offers = [o for o in offers if o["domain"] == domain]
            if not domain_offers:
                break
            per_product_prices.append(min(o["price"] for o in domain_offers))
        else:
            sub = sum(per_product_prices)
            shipping, _, _ = get_shipping_cost(domain, sub)
            total = sub + shipping
            if total < cheapest_single_total:
                cheapest_single_total = total
                cheapest_single_domain = domain

    # If no single retailer has everything, use most expensive greedy as baseline
    if cheapest_single_domain is None:
        cheapest_single_domain = "any single retailer"
        # Estimate: sum of most expensive offers per product + average shipping
        cheapest_single_total = sum(
            max(o["price"] for o in offers) for offers in offer_matrix_valid
        ) + 7.99 * len(groups)

    savings = round(cheapest_single_total - best_total, 2)

    return BasketOptimization(
        items=items,
        retailer_breakdown=retailer_breakdown,
        subtotal=round(subtotal, 2),
        total_shipping=round(best_shipping, 2),
        total_cost=round(best_total, 2),
        cheapest_single_retailer=cheapest_single_domain or "N/A",
        cheapest_single_total=round(cheapest_single_total, 2),
        savings_vs_single=max(savings, 0),
        notes=notes,
    )
