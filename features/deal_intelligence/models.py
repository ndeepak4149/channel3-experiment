from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class DealIntelligence(BaseModel):
    product_id: str
    product_title: str
    current_price: float
    currency: str

    # Price history signals (from Channel3 price tracking)
    price_percentile: Optional[int]    # 0=all-time low, 100=all-time high. None if no history
    all_time_low: Optional[float]
    all_time_high: Optional[float]
    average_price_30d: Optional[float]
    savings_vs_average: Optional[float]  # $ saved vs 30d avg (negative = paying more)

    # compare_at_price signal (from Channel3 offer data)
    original_price: Optional[float]    # compare_at_price if set
    discount_pct: Optional[float]      # % off vs original

    # Sale calendar signal
    next_likely_sale: Optional[str]    # e.g. "Prime Day (Jul 8-9)"
    days_to_sale: Optional[int]

    # Verdict
    recommendation: str                # "buy_now" | "good_deal" | "wait" | "overpriced"
    confidence: str                    # "high" | "medium" | "low"
    reasoning: str                     # Human-readable explanation
    data_source: str                   # "price_history" | "compare_at_price" | "calendar_only"
