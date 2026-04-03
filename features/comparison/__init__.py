"""
Feature 3: Smart Product Comparison
=====================================
Takes 2-4 Channel3 product IDs, fetches full product data + review
intelligence, and uses Claude to produce a structured comparison matrix
with per-axis winners, an overall winner, and persona-based recommendations.

Usage:
    from features.comparison import compare

    result = compare(client, ["pid1", "pid2", "pid3"])
    print(result.overall_winner)
    print(result.best_for)
"""
from __future__ import annotations
from typing import List, Optional

from channel3_sdk import Channel3

from .models import ComparisonAxis, ProductComparison
from .extractor import compare_products
from features.review_intelligence import get_review_intelligence


def compare(
    client: Channel3,
    product_ids: List[str],
) -> ProductComparison:
    """
    Fetch product details + reviews for each ID, then run Claude comparison.
    """
    if len(product_ids) < 2:
        raise ValueError("Need at least 2 product IDs to compare.")
    if len(product_ids) > 4:
        product_ids = product_ids[:4]

    products_data = []
    titles: dict[str, str] = {}

    for pid in product_ids:
        # Fetch full product detail from Channel3
        product = client.products.retrieve(pid)
        titles[pid] = product.title

        # Best offer price
        offers = product.offers or []
        best_offer = min(offers, key=lambda o: o.price.price) if offers else None
        price = best_offer.price.price if best_offer else None
        compare_at = best_offer.price.compare_at_price if best_offer else None

        # Brand
        brand = product.brands[0].name if product.brands else ""

        # Review intelligence (Feature 1 — cached after first call)
        review = get_review_intelligence(pid, product.title, brand)

        products_data.append({
            "product_id":      pid,
            "title":           product.title,
            "brand":           brand,
            "price":           price,
            "compare_at_price": compare_at,
            "key_features":    product.key_features or [],
            "categories":      product.categories or [],
            "review_score":    review.aggregate_score,
            "review_summary":  review.consensus_summary,
            "review_pros":     review.pros,
            "review_cons":     review.cons,
        })

    # Run Claude comparison
    result = compare_products(products_data)

    # Build ComparisonAxis objects
    axes = []
    for ax in result.get("axes", []):
        axes.append(ComparisonAxis(
            axis=ax["axis"],
            ratings=ax["ratings"],
            winner=ax["winner"],
            explanation=ax["explanation"],
        ))

    return ProductComparison(
        product_ids=product_ids,
        product_titles=titles,
        category=result.get("category", ""),
        axes=axes,
        overall_winner=result.get("overall_winner", product_ids[0]),
        runner_up=result.get("runner_up"),
        summary=result.get("summary", ""),
        best_for=result.get("best_for", {}),
    )
