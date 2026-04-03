"""
Price analysis logic — combines price history, compare_at_price,
and sale calendar to produce a buy/wait recommendation.
"""
from __future__ import annotations
from typing import Optional, Tuple

from channel3_sdk.types import ProductDetail


def analyze_price_history(
    current_price: float,
    min_price: float,
    max_price: float,
    mean_price: float,
    current_status: str,   # "low" | "typical" | "high" from Channel3 stats
) -> Tuple[int, float, str, str]:
    """
    Returns (percentile, savings_vs_avg, recommendation, reasoning).
    """
    price_range = max_price - min_price
    if price_range <= 0:
        percentile = 50
    else:
        percentile = int((current_price - min_price) / price_range * 100)
        percentile = max(0, min(100, percentile))

    savings = round(mean_price - current_price, 2)

    if percentile <= 10 or current_status == "low":
        rec = "buy_now"
        reasoning = (
            f"Price is at a {percentile}-year percentile — near its all-time low. "
            f"You're saving ${savings:.2f} vs the 30-day average of ${mean_price:.2f}."
        )
    elif percentile <= 30:
        rec = "buy_now"
        reasoning = (
            f"Price is in the bottom 30% of its historical range (percentile {percentile}). "
            f"Saving ${savings:.2f} vs average."
        )
    elif percentile <= 55:
        rec = "good_deal"
        reasoning = (
            f"Price is close to the 30-day average (${mean_price:.2f}). "
            f"Not a standout deal but not overpriced either."
        )
    elif percentile <= 75:
        rec = "wait"
        reasoning = (
            f"Price is above the 30-day average by ${-savings:.2f}. "
            f"Historical data suggests better prices are available."
        )
    else:
        rec = "overpriced"
        reasoning = (
            f"Price is in the top {100-percentile}% of its range — near its peak. "
            f"You're paying ${-savings:.2f} more than the 30-day average."
        )

    return percentile, savings, rec, reasoning


def analyze_compare_at_price(
    current_price: float,
    compare_at_price: float,
) -> Tuple[float, str, str]:
    """
    Returns (discount_pct, recommendation, reasoning).
    """
    discount_pct = (compare_at_price - current_price) / compare_at_price * 100

    if discount_pct >= 40:
        rec = "buy_now"
        reasoning = f"Listed at {discount_pct:.0f}% off original price (${compare_at_price:.2f}). Strong discount."
    elif discount_pct >= 20:
        rec = "buy_now"
        reasoning = f"On sale at {discount_pct:.0f}% off (was ${compare_at_price:.2f}). Good deal."
    elif discount_pct >= 10:
        rec = "good_deal"
        reasoning = f"Modest {discount_pct:.0f}% discount from ${compare_at_price:.2f}. Decent but not exceptional."
    else:
        rec = "good_deal"
        reasoning = f"Small {discount_pct:.0f}% discount from listed price of ${compare_at_price:.2f}."

    return discount_pct, rec, reasoning


def get_best_offer(product: ProductDetail):
    offers = product.offers or []
    in_stock = [o for o in offers if o.availability == "InStock"]
    pool = in_stock if in_stock else offers
    return min(pool, key=lambda o: o.price.price) if pool else None


def calendar_recommendation(days_to_sale: Optional[int]) -> Tuple[str, str]:
    """Recommendation based purely on upcoming sale proximity."""
    if days_to_sale is None:
        return "good_deal", "No major sale events in the next 120 days."
    elif days_to_sale <= 14:
        return "wait", f"A sale event is only {days_to_sale} days away — worth holding off."
    elif days_to_sale <= 45:
        return "good_deal", f"A sale is {days_to_sale} days out. Buy now if you need it, or wait for a better deal."
    else:
        return "good_deal", f"Next sale event is {days_to_sale} days away. No strong reason to wait."
