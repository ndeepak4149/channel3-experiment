"""
Category-aware weight profiles for the value ranking signals.
Maps Google Product Taxonomy category strings → weight dicts.
Weights must sum to 1.0.
"""
from __future__ import annotations
from typing import Dict

# Signal keys used across all profiles
SIGNALS = [
    "price_efficiency",   # how good is the price vs retail/compare_at
    "review_sentiment",   # aggregate review score from Feature 1
    "brand_trust",        # pre-built brand reputation tier
    "deal_quality",       # discount depth & on-sale status
    "availability",       # in-stock across retailers
    "source_diversity",   # how many retailers carry it
]

# ── Weight profiles (must sum to 1.0) ────────────────────────────────────────

PROFILES: Dict[str, Dict[str, float]] = {
    "electronics": {
        "review_sentiment": 0.30,
        "price_efficiency": 0.22,
        "brand_trust":      0.18,
        "deal_quality":     0.15,
        "availability":     0.10,
        "source_diversity": 0.05,
    },
    "fashion": {
        "price_efficiency": 0.28,
        "deal_quality":     0.22,
        "brand_trust":      0.18,
        "review_sentiment": 0.15,
        "availability":     0.10,
        "source_diversity": 0.07,
    },
    "sports_fitness": {
        "review_sentiment": 0.28,
        "price_efficiency": 0.23,
        "brand_trust":      0.17,
        "deal_quality":     0.15,
        "availability":     0.10,
        "source_diversity": 0.07,
    },
    "health_beauty": {
        "review_sentiment": 0.33,
        "brand_trust":      0.22,
        "price_efficiency": 0.18,
        "deal_quality":     0.12,
        "availability":     0.10,
        "source_diversity": 0.05,
    },
    "furniture_home": {
        "price_efficiency": 0.25,
        "review_sentiment": 0.22,
        "source_diversity": 0.18,
        "availability":     0.15,
        "deal_quality":     0.12,
        "brand_trust":      0.08,
    },
    "default": {
        "review_sentiment": 0.25,
        "price_efficiency": 0.25,
        "brand_trust":      0.15,
        "deal_quality":     0.15,
        "availability":     0.12,
        "source_diversity": 0.08,
    },
}

# ── Category keyword → profile mapping ───────────────────────────────────────

_CATEGORY_MAP = [
    (["electronics", "audio", "headphones", "camera", "computer", "phone",
      "laptop", "tablet", "tv", "monitor", "speaker", "keyboard", "gaming"],  "electronics"),
    (["apparel", "clothing", "fashion", "shoes", "sneakers", "dress",
      "shirt", "pants", "jacket", "bag", "handbag", "accessory"],              "fashion"),
    (["sporting goods", "exercise", "fitness", "yoga", "running", "gym",
      "outdoor", "camping", "cycling", "sports"],                              "sports_fitness"),
    (["health", "beauty", "skincare", "sunscreen", "supplement", "vitamin",
      "protein", "cosmetic", "makeup", "hair", "personal care"],               "health_beauty"),
    (["furniture", "home", "kitchen", "bedding", "office", "desk",
      "chair", "mattress", "storage", "lighting"],                             "furniture_home"),
]


def get_profile(categories: list[str]) -> tuple[str, Dict[str, float]]:
    """
    Given a list of Channel3 category strings, return (profile_name, weights).
    Falls back to 'default' if no match.
    """
    combined = " ".join(categories or []).lower()
    for keywords, profile_name in _CATEGORY_MAP:
        if any(kw in combined for kw in keywords):
            return profile_name, PROFILES[profile_name]
    return "default", PROFILES["default"]
