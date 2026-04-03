from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PurchasePersona(BaseModel):
    persona_id: str
    display_name: str = "My Profile"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Brand preferences (inferred + declared)
    preferred_brands: List[str] = Field(default_factory=list)
    avoided_brands: List[str] = Field(default_factory=list)

    # Price behaviour
    price_tier: str = "mid"                          # "budget" | "mid" | "premium"
    avg_spend_per_item: Optional[float] = None       # rolling average from basket history
    deal_sensitivity: float = 0.5                    # 0=ignores deals, 1=only buys on sale

    # Category affinities — how often they shop each category (0-1)
    category_affinities: Dict[str, float] = Field(default_factory=dict)

    # Value priorities (ordered, most important first)
    value_priorities: List[str] = Field(
        default_factory=lambda: ["quality", "price", "brand", "sustainability"]
    )

    # Declared sizes
    declared_sizes: Dict[str, str] = Field(default_factory=dict)
    # e.g. {"shoes_us": "10", "shirt": "M", "pants_waist": "32"}

    # Interaction history counters (used for inference, not shown to user)
    interaction_count: int = 0
    brand_counts: Dict[str, int] = Field(default_factory=dict)
    category_counts: Dict[str, int] = Field(default_factory=dict)
    price_history: List[float] = Field(default_factory=list)
    on_sale_picks: int = 0
    total_picks: int = 0
