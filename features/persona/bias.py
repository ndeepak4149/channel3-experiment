"""
Apply persona to Value Ranking — re-weight signals based on user preferences.
"""
from __future__ import annotations
from typing import Dict
from .models import PurchasePersona


def personalized_weights(
    base_weights: Dict[str, float],
    persona: PurchasePersona,
) -> Dict[str, float]:
    """
    Adjust base category weights based on persona's value priorities and price tier.
    Returns a new weight dict (sums to ~1.0).
    """
    weights = dict(base_weights)
    priorities = persona.value_priorities

    # Boost / reduce signals based on declared priorities
    priority_map = {
        "quality":        "review_sentiment",
        "price":          "price_efficiency",
        "brand":          "brand_trust",
        "sustainability": "review_sentiment",   # proxy — no sustainability signal yet
    }

    # Give the top priority a 30% boost, reduce others proportionally
    if priorities:
        top = priorities[0]
        signal = priority_map.get(top)
        if signal and signal in weights:
            boost = weights[signal] * 0.30
            weights[signal] = min(weights[signal] + boost, 0.50)
            # redistribute the boost reduction across remaining signals
            others = [k for k in weights if k != signal]
            reduction = boost / len(others)
            for k in others:
                weights[k] = max(0.02, weights[k] - reduction)

    # Deal-sensitive user → boost deal_quality signal
    if persona.deal_sensitivity > 0.6 and "deal_quality" in weights:
        extra = 0.05
        weights["deal_quality"] = min(weights["deal_quality"] + extra, 0.40)
        weights["price_efficiency"] = max(0.02, weights.get("price_efficiency", 0.10) - extra)

    # Normalize to sum = 1.0
    total = sum(weights.values())
    return {k: round(v / total, 4) for k, v in weights.items()}


def persona_score_adjustment(
    product_brands: list[str],
    persona: PurchasePersona,
) -> float:
    """
    Return a score bonus/penalty (-15 to +15) based on brand preferences.
    """
    if not product_brands:
        return 0.0

    brand_names_lower = [b.lower() for b in product_brands]
    preferred_lower   = [b.lower() for b in persona.preferred_brands]
    avoided_lower     = [b.lower() for b in persona.avoided_brands]

    for b in brand_names_lower:
        if b in avoided_lower:
            return -15.0    # strong penalty for avoided brands
    for b in brand_names_lower:
        if b in preferred_lower:
            rank = preferred_lower.index(b)
            return max(15.0 - rank * 2, 5.0)  # top preferred = +15, each rank lower = -2

    return 0.0
