"""
Infer persona signals from product interactions.
Called whenever a user adds a product to their basket or clicks a result.
"""
from __future__ import annotations
from channel3_sdk.types import ProductDetail
from features.value_ranking.weights import get_profile
from .models import PurchasePersona


def _price_tier(avg: float) -> str:
    if avg < 40:
        return "budget"
    elif avg < 150:
        return "mid"
    else:
        return "premium"


def _dominant_priorities(persona: PurchasePersona) -> list[str]:
    """Re-derive value_priorities from observed behaviour."""
    tier   = persona.price_tier
    deal_s = persona.deal_sensitivity

    base = ["quality", "price", "brand", "sustainability"]

    # If they consistently pick on-sale items → price moves up
    if deal_s > 0.6:
        base = ["price", "quality", "brand", "sustainability"]
    # If they consistently pick premium → quality moves up
    elif tier == "premium":
        base = ["quality", "brand", "price", "sustainability"]
    elif tier == "budget":
        base = ["price", "quality", "sustainability", "brand"]

    return base


def observe_product_pick(
    persona: PurchasePersona,
    product: ProductDetail,
    was_on_sale: bool = False,
) -> PurchasePersona:
    """
    Update persona from a single product pick (basket add or click).
    Returns mutated persona — caller must call storage.save() to persist.
    """
    # ── Brand ─────────────────────────────────────────────────────────────────
    for brand in (product.brands or []):
        name = brand.name.strip()
        counts = dict(persona.brand_counts)
        counts[name] = counts.get(name, 0) + 1
        persona.brand_counts = counts

    # Re-derive top brands (appear in ≥2 picks or top 3 by count)
    bc = persona.brand_counts
    if bc:
        sorted_brands = sorted(bc, key=bc.get, reverse=True)
        persona.preferred_brands = [b for b in sorted_brands if bc[b] >= 1][:8]

    # ── Category ──────────────────────────────────────────────────────────────
    profile_name, _ = get_profile(product.categories or [])
    cc = dict(persona.category_counts)
    cc[profile_name] = cc.get(profile_name, 0) + 1
    persona.category_counts = cc

    total_cat = sum(cc.values()) or 1
    persona.category_affinities = {k: round(v / total_cat, 3) for k, v in cc.items()}

    # ── Price tier ────────────────────────────────────────────────────────────
    offers = product.offers or []
    in_stock = [o for o in offers if o.availability == "InStock"]
    pool = in_stock or offers
    if pool:
        price = min(o.price.price for o in pool)
        prices = list(persona.price_history) + [price]
        persona.price_history = prices[-50:]   # keep last 50
        persona.avg_spend_per_item = round(sum(prices) / len(prices), 2)
        persona.price_tier = _price_tier(persona.avg_spend_per_item)

    # ── Deal sensitivity ──────────────────────────────────────────────────────
    persona.total_picks += 1
    if was_on_sale:
        persona.on_sale_picks += 1
    if persona.total_picks > 0:
        persona.deal_sensitivity = round(persona.on_sale_picks / persona.total_picks, 2)

    # ── Value priorities ──────────────────────────────────────────────────────
    persona.value_priorities = _dominant_priorities(persona)

    persona.interaction_count += 1
    return persona


def apply_declaration(
    persona: PurchasePersona,
    declaration_type: str,
    value: str,
    extra: str = "",
) -> tuple[PurchasePersona, str]:
    """
    Apply an explicit user declaration to the persona.

    Types:
      brand_prefer <brand>       — add to preferred brands
      brand_avoid  <brand>       — add to avoided brands
      size <key> <value>         — e.g. size shoes_us 10
      priority <order>           — e.g. priority price,quality,brand,sustainability
      tier <budget|mid|premium>  — override price tier
    Returns (updated_persona, confirmation_message)
    """
    dtype = declaration_type.lower().strip()

    if dtype == "brand_prefer":
        brand = value.strip().title()
        if brand not in persona.preferred_brands:
            persona.preferred_brands = [brand] + [b for b in persona.preferred_brands if b != brand]
        if brand in persona.avoided_brands:
            persona.avoided_brands = [b for b in persona.avoided_brands if b != brand]
        return persona, f"Added '{brand}' to preferred brands."

    elif dtype == "brand_avoid":
        brand = value.strip().title()
        if brand not in persona.avoided_brands:
            persona.avoided_brands = [brand] + [b for b in persona.avoided_brands if b != brand]
        if brand in persona.preferred_brands:
            persona.preferred_brands = [b for b in persona.preferred_brands if b != brand]
        return persona, f"Added '{brand}' to avoided brands."

    elif dtype == "size":
        # value = key, extra = size value
        key = value.lower().strip().replace(" ", "_")
        persona.declared_sizes[key] = extra.strip()
        return persona, f"Saved size: {key} = {extra.strip()}"

    elif dtype == "tier":
        tier = value.lower().strip()
        if tier in ("budget", "mid", "premium"):
            persona.price_tier = tier
            persona.value_priorities = _dominant_priorities(persona)
            return persona, f"Price tier set to '{tier}'."
        return persona, f"Unknown tier '{tier}'. Use: budget, mid, premium."

    elif dtype == "priority":
        priorities = [p.strip() for p in value.split(",")]
        valid = {"quality", "price", "brand", "sustainability"}
        priorities = [p for p in priorities if p in valid]
        if priorities:
            persona.value_priorities = priorities
            return persona, f"Value priorities updated: {' > '.join(priorities)}"
        return persona, "No valid priorities found. Use: quality, price, brand, sustainability"

    return persona, f"Unknown declaration type '{dtype}'."
