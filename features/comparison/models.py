from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel


class ComparisonAxis(BaseModel):
    axis: str                        # e.g. "Sound Quality", "Battery Life"
    ratings: Dict[str, float]        # product_id → score 0-10
    winner: str                      # product_id of the winner on this axis
    explanation: str                 # "Sony edges out Apple with deeper bass"


class ProductComparison(BaseModel):
    product_ids: List[str]
    product_titles: Dict[str, str]   # product_id → title
    category: str
    axes: List[ComparisonAxis]
    overall_winner: str              # product_id
    runner_up: Optional[str]
    summary: str                     # "Sony wins on sound; Apple wins on ecosystem"
    best_for: Dict[str, str]         # persona → product_id
