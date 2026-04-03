"""
Feature 1: Aggregated Review Intelligence
==========================================
Fetches review content from multiple web sources and uses Claude to extract
structured intelligence: score, pros/cons, red flags, and a consensus summary.

Usage:
    from features.review_intelligence import get_review_intelligence

    result = get_review_intelligence(
        product_id="9khaccv",
        product_title="Adidas 4mm Yoga Mat - Blue",
        brand="Adidas",
    )
    print(result.aggregate_score)   # e.g. 78
    print(result.pros)              # ["Excellent grip", "Good value", ...]
"""
from __future__ import annotations
from datetime import datetime, timezone

from . import cache
from .models import ReviewIntelligence, ReviewSource
from .search import fetch_review_snippets
from .extractor import extract_review_intelligence


def get_review_intelligence(
    product_id: str,
    product_title: str,
    brand: str = "",
    force_refresh: bool = False,
) -> ReviewIntelligence:
    """
    Main entry point. Returns cached result if available (TTL: 48h),
    otherwise fetches fresh review data and runs LLM extraction.
    """
    cache_key = f"review_{product_id}"

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached:
            cached.pop("_cached_at", None)
            return ReviewIntelligence(**cached)

    # 1. Gather raw snippets from the web (may return [] if rate-limited)
    snippets = fetch_review_snippets(product_title, brand, max_sources=12)
    source_mode = "web+llm" if snippets else "llm-knowledge"

    # 2. LLM extraction
    extracted = extract_review_intelligence(product_title, brand, snippets)

    # 3. Build ReviewSource objects — pair snippets with their sentiments
    sentiments = extracted.get("source_sentiments", [])
    sources = []
    for i, s in enumerate(snippets):
        sentiment = sentiments[i] if i < len(sentiments) else 0.0
        sources.append(ReviewSource(
            platform=s["platform"],
            url=s["url"],
            snippet=s["snippet"][:200],
            sentiment=float(sentiment),
        ))

    result = ReviewIntelligence(
        product_id=product_id,
        product_title=product_title,
        aggregate_score=extracted["aggregate_score"],
        total_sources=len(snippets),
        consensus_summary=extracted["consensus_summary"],
        pros=extracted["pros"],
        cons=extracted["cons"],
        red_flags=extracted["red_flags"],
        sources=sources,
        confidence=extracted["confidence"],
        last_updated=datetime.now(timezone.utc),
        source_mode=source_mode,
    )

    # 4. Cache the result
    cache.set(cache_key, result.model_dump())

    return result
