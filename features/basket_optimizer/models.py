from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel


class BasketItem(BaseModel):
    product_id: str
    product_title: str
    recommended_retailer: str
    price: float
    original_price: Optional[float]    # compare_at_price if on sale
    discount_pct: Optional[float]
    product_url: str
    availability: str


class RetailerSummary(BaseModel):
    domain: str
    items: List[str]                   # product titles
    subtotal: float
    shipping: float
    order_total: float
    free_shipping_threshold: Optional[float]
    note: Optional[str]                # e.g. "Added $4.10 item to unlock free shipping"


class BasketOptimization(BaseModel):
    items: List[BasketItem]
    retailer_breakdown: Dict[str, RetailerSummary]  # domain → summary
    subtotal: float
    total_shipping: float
    total_cost: float

    # Comparison baselines
    cheapest_single_retailer: str
    cheapest_single_total: float
    savings_vs_single: float

    notes: List[str]
