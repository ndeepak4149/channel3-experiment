"""
Feature 2: Value Ranking Engine
================================
Ranks a list of Channel3 products by multi-signal value score.
Each product is scored across 6 signals (price efficiency, reviews,
brand trust, deal quality, availability, source diversity) with
weights tuned per product category.

Usage:
    from features.value_ranking import rank_products

    ranked = rank_products(products, query="wireless headphones")
    for vs in ranked.ranked:
        print(vs.rank, vs.product_title, vs.overall_score, vs.one_liner)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional

from channel3_sdk.types import ProductDetail

from .models import RankedSearchResponse, ValueScore
from .weights import get_profile
from .signals import (
    brand_trust_score,
    price_efficiency_score,
    availability_score,
    source_diversity_score,
    deal_quality_score,
    review_sentiment_score,
    generate_one_liner,
)

# Map overall score → tier label
def _tier(score: float) -> str:
    if score >= 78:
        return "exceptional"
    elif score >= 62:
        return "good"
    elif score >= 48:
        return "fair"
    else:
        return "overpriced"


def score_product(
    product: ProductDetail,
    review_aggregate: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Compute all signal scores for a single product. Returns raw breakdown dict."""
    if weights is None:
        _, weights = get_profile(product.categories or [])

    return {
        "price_efficiency": price_efficiency_score(product),
        "review_sentiment": review_sentiment_score(review_aggregate),
        "brand_trust":      brand_trust_score(product),
        "deal_quality":     deal_quality_score(product),
        "availability":     availability_score(product),
        "source_diversity": source_diversity_score(product),
    }


def rank_products(
    products: List[ProductDetail],
    query: str = "",
    review_scores: Optional[Dict[str, int]] = None,
    persona=None,                                     # Optional[PurchasePersona]
) -> RankedSearchResponse:
    """
    Score and rank a list of products.

    Args:
        products:       List of Channel3 ProductDetail objects (from search results).
        query:          Original search query (for the response label).
        review_scores:  Optional dict of product_id → review aggregate score (0-100).
                        If provided, the review_sentiment signal uses real data.
                        If omitted, review_sentiment defaults to neutral 50.
    """
    if not products:
        return RankedSearchResponse(
            query=query,
            category_profile="none",
            ranking_explanation="No products to rank.",
            ranked=[],
        )

    review_scores = review_scores or {}

    # Determine category profile from the first product with categories
    categories = []
    for p in products:
        if p.categories:
            categories = p.categories
            break
    profile_name, weights = get_profile(categories)

    # Apply persona-aware weight adjustments if a persona is provided
    if persona is not None:
        from features.persona.bias import personalized_weights, persona_score_adjustment
        weights = personalized_weights(weights, persona)

    value_scores: List[ValueScore] = []
    for product in products:
        breakdown = score_product(
            product,
            review_aggregate=review_scores.get(product.id),
            weights=weights,
        )
        # Weighted sum
        overall = sum(breakdown[sig] * weights[sig] for sig in breakdown)

        # Persona brand adjustment
        if persona is not None:
            from features.persona.bias import persona_score_adjustment
            brand_names = [b.name for b in (product.brands or [])]
            adjustment = persona_score_adjustment(brand_names, persona)
            overall = max(0, min(100, overall + adjustment))
        tier = _tier(overall)
        one_liner = generate_one_liner(product, breakdown, overall, tier)

        value_scores.append(ValueScore(
            product_id=product.id,
            product_title=product.title,
            overall_score=round(overall, 1),
            score_breakdown=breakdown,
            signal_weights=weights,
            value_tier=tier,
            one_liner=one_liner,
            rank=0,  # filled in below after sorting
        ))

    # Sort best → worst and assign ranks
    value_scores.sort(key=lambda v: v.overall_score, reverse=True)
    for i, vs in enumerate(value_scores):
        vs.rank = i + 1

    explanation = (
        f"Ranked {len(products)} products using the '{profile_name}' weight profile. "
        f"Top signals: {', '.join(sorted(weights, key=weights.get, reverse=True)[:3])}."
    )

    return RankedSearchResponse(
        query=query,
        category_profile=profile_name,
        ranking_explanation=explanation,
        ranked=value_scores,
    )
