from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from features.review_intelligence.models import ReviewIntelligence
from features.deal_intelligence.models import DealIntelligence
from features.value_ranking.models import ValueScore
from features.comparison.models import ProductComparison


class AgentDecision(BaseModel):
    # Intent & depth
    intent: str
    depth: str                            # "quick" | "standard" | "full"

    # Top recommendation
    top_pick_id: str
    top_pick_title: str
    top_pick_price: Optional[float]
    top_pick_retailer: Optional[str]
    top_pick_url: Optional[str]
    top_pick_reasoning: str

    # Alternatives (product ids + titles)
    alternative_ids: List[str]
    alternative_titles: List[str]

    # Intelligence layers (populated based on depth)
    value_scores: Dict[str, ValueScore]              # always present
    reviews: Dict[str, ReviewIntelligence]           # standard + full
    deals: Dict[str, DealIntelligence]               # standard + full
    comparison: Optional[ProductComparison]          # full only

    # Agent guidance
    follow_up_questions: List[str]
    objection_handling: Dict[str, str]               # objection → response
    purchase_confidence: float                       # 0-1

    # Persona context (if used)
    persona_id: Optional[str] = None
    persona_applied: bool = False
