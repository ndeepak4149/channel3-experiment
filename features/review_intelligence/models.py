from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ReviewSource(BaseModel):
    platform: str           # "reddit", "youtube", "google", "wirecutter", "retailer"
    url: str
    snippet: str            # Key quote or summary from this source
    sentiment: float        # -1.0 to 1.0
    date: Optional[datetime] = None


class ReviewIntelligence(BaseModel):
    product_id: str
    product_title: str
    aggregate_score: int            # 0-100
    total_sources: int
    consensus_summary: str
    pros: List[str]
    cons: List[str]
    red_flags: List[str]
    sources: List[ReviewSource]
    confidence: float               # 0-1, based on source volume/recency
    last_updated: datetime
    source_mode: str = "web+llm"    # "web+llm" or "llm-knowledge"
