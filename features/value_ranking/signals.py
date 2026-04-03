"""
Individual signal scorers — each returns a float 0-100.
All functions take a Channel3 ProductDetail object + optional context.
"""
from __future__ import annotations
from typing import Optional
from channel3_sdk.types import ProductDetail

# ── Brand trust index ─────────────────────────────────────────────────────────
# Tier 1 (85-95): globally trusted, strong QC, good support
# Tier 2 (65-80): well-known, generally reliable
# Tier 3 (45-60): lesser-known but legitimate
# Unknown brands default to 45

BRAND_TRUST: dict[str, int] = {
    # Electronics
    "apple": 92, "sony": 90, "samsung": 87, "bose": 88, "lg": 85,
    "microsoft": 88, "dell": 83, "logitech": 85, "jbl": 80, "sennheiser": 88,
    "audio-technica": 85, "jabra": 82, "anker": 78, "razer": 76, "corsair": 78,
    "asus": 80, "lenovo": 82, "hp": 78, "acer": 72,
    # Fashion / Footwear
    "nike": 88, "adidas": 86, "new balance": 84, "reebok": 78, "puma": 76,
    "under armour": 80, "converse": 78, "vans": 76, "levi's": 82,
    "north face": 84, "columbia": 80, "patagonia": 88,
    # Health / Beauty
    "neutrogena": 82, "cerave": 85, "la roche-posay": 86, "olay": 78,
    "therabody": 82, "111skin": 72,
    # Fitness
    "manduka": 84, "lifefitness": 80, "bowflex": 75, "bala": 72,
    "alo": 75, "lululemon": 85,
    # Home / Office
    "ikea": 80, "herman miller": 90, "steelcase": 88, "bush furniture": 68,
    "autonomous": 72, "flexispot": 70,
    # General / Retail
    "amazon basics": 70, "costco": 75, "target": 68, "walmart": 62,
}


def brand_trust_score(product: ProductDetail) -> float:
    brands = product.brands or []
    if not brands:
        return 45.0
    scores = []
    for b in brands:
        key = b.name.lower().strip()
        scores.append(BRAND_TRUST.get(key, 45))
    return float(max(scores))  # use the most trusted brand listed


def price_efficiency_score(product: ProductDetail) -> float:
    """
    Score based on discount depth vs compare_at_price.
    If no compare_at_price available, returns neutral 50.
    """
    offers = product.offers or []
    if not offers:
        return 50.0

    discounts = []
    for o in offers:
        p = o.price
        if p.compare_at_price and p.compare_at_price > p.price:
            pct = (p.compare_at_price - p.price) / p.compare_at_price * 100
            discounts.append(pct)

    if not discounts:
        return 50.0

    avg_discount = sum(discounts) / len(discounts)
    # 0% off → 50, 10% off → 60, 20% off → 70, 30% off → 80, 50%+ off → 100
    score = 50.0 + min(avg_discount, 50.0)
    return min(score, 100.0)


def availability_score(product: ProductDetail) -> float:
    """Score based on how many offers are InStock."""
    offers = product.offers or []
    if not offers:
        return 20.0
    in_stock = sum(1 for o in offers if o.availability == "InStock")
    ratio = in_stock / len(offers)
    # full stock across all retailers = 100, none = 20
    return 20.0 + ratio * 80.0


def source_diversity_score(product: ProductDetail) -> float:
    """More retailers = less risk of stockout / price gouging."""
    offers = product.offers or []
    n = len(offers)
    if n == 0:
        return 10.0
    elif n == 1:
        return 40.0
    elif n == 2:
        return 60.0
    elif n == 3:
        return 75.0
    elif n == 4:
        return 85.0
    else:
        return 95.0


def deal_quality_score(product: ProductDetail) -> float:
    """
    How good is the current deal?
    Uses compare_at_price depth + number of offers on sale.
    """
    offers = product.offers or []
    if not offers:
        return 50.0

    on_sale = [o for o in offers if o.price.compare_at_price and o.price.compare_at_price > o.price.price]
    if not on_sale:
        return 50.0

    best_pct = max(
        (o.price.compare_at_price - o.price.price) / o.price.compare_at_price * 100
        for o in on_sale
    )
    # <10% → 55, 10-20% → 65, 20-30% → 75, 30-40% → 85, 40%+ → 95
    if best_pct < 10:
        return 55.0
    elif best_pct < 20:
        return 65.0
    elif best_pct < 30:
        return 75.0
    elif best_pct < 40:
        return 85.0
    else:
        return 95.0


def review_sentiment_score(aggregate_score: Optional[int]) -> float:
    """Pass-through from Feature 1. Returns 50 if not available."""
    if aggregate_score is None:
        return 50.0
    return float(aggregate_score)


# ── One-liner generator ───────────────────────────────────────────────────────

def generate_one_liner(
    product: ProductDetail,
    breakdown: dict[str, float],
    overall: float,
    value_tier: str,
) -> str:
    offers = product.offers or []
    best_price = min((o.price.price for o in offers), default=None)
    brand = product.brands[0].name if product.brands else ""

    # Find the top-scoring and bottom-scoring signals
    top_signal = max(breakdown, key=breakdown.get)
    bottom_signal = min(breakdown, key=breakdown.get)

    SIGNAL_PHRASES = {
        "price_efficiency": "strong discount",
        "review_sentiment": "excellent reviews",
        "brand_trust":      "trusted brand",
        "deal_quality":     "great deal right now",
        "availability":     "widely available",
        "source_diversity": "sold by multiple retailers",
    }
    WEAK_PHRASES = {
        "price_efficiency": "no visible discount",
        "review_sentiment": "mixed reviews",
        "brand_trust":      "lesser-known brand",
        "deal_quality":     "not on sale",
        "availability":     "limited availability",
        "source_diversity": "single retailer only",
    }

    top_phrase  = SIGNAL_PHRASES.get(top_signal, "")
    weak_phrase = WEAK_PHRASES.get(bottom_signal, "")

    price_str = f"${best_price:.0f}" if best_price else ""
    name = (brand + " " if brand else "") + (product.title.split()[0] if product.title else "Product")

    if value_tier == "exceptional":
        return f"{top_phrase.capitalize()} — one of the best value picks at {price_str}."
    elif value_tier == "good":
        return f"Solid choice: {top_phrase}, though {weak_phrase}."
    elif value_tier == "fair":
        return f"Average value — {top_phrase} but {weak_phrase}."
    else:
        return f"Hard to justify at {price_str}: {weak_phrase}."
