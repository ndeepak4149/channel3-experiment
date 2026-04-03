from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel


class ValueScore(BaseModel):
    product_id: str
    product_title: str
    overall_score: float                  # 0-100
    score_breakdown: Dict[str, float]     # signal → score (0-100 each)
    signal_weights: Dict[str, float]      # signal → weight used
    value_tier: str                       # "exceptional" | "good" | "fair" | "overpriced"
    one_liner: str                        # e.g. "Great sound at 40% below typical price"
    rank: int                             # 1 = best value in this result set


class RankedSearchResponse(BaseModel):
    query: str
    category_profile: str                 # which weight profile was used
    ranking_explanation: str
    ranked: List[ValueScore]              # sorted best → worst
