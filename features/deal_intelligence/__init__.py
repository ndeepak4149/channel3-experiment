"""
Feature 4: Deal Intelligence & Buy Timing
==========================================
Combines Channel3 price-tracking history, compare_at_price signals,
and a sale-event calendar to produce a buy/wait recommendation.

Data priority:
  1. Price history (Channel3 API)  → highest confidence
  2. compare_at_price              → medium confidence
  3. Sale calendar only            → low confidence

Usage:
    from features.deal_intelligence import get_deal_intelligence

    deal = get_deal_intelligence(client, product)
    print(deal.recommendation)   # "buy_now" | "good_deal" | "wait" | "overpriced"
    print(deal.reasoning)
"""
from __future__ import annotations

from channel3_sdk import Channel3
from channel3_sdk.types import ProductDetail

from features.value_ranking.weights import get_profile
from .models import DealIntelligence
from .calendar import next_sale_event
from .analyzer import (
    analyze_price_history,
    analyze_compare_at_price,
    calendar_recommendation,
    get_best_offer,
)


def get_deal_intelligence(
    client: Channel3,
    product: ProductDetail,
) -> DealIntelligence:
    """
    Analyse deal quality for a single product.
    Tries Channel3 price history first, falls back to compare_at_price,
    then falls back to calendar-only.
    """
    best_offer = get_best_offer(product)
    current_price = best_offer.price.price if best_offer else 0.0
    compare_at    = best_offer.price.compare_at_price if best_offer else None
    currency      = best_offer.price.currency if best_offer else "USD"

    # Category profile for sale calendar
    profile_name, _ = get_profile(product.categories or [])
    sale_name, days_to_sale = next_sale_event(profile_name)

    # ── Tier 1: Price history ─────────────────────────────────────────────────
    try:
        history = client.price_tracking.get_history(product.id, days=30)
        stats   = history.statistics

        if stats and stats.min_price and stats.max_price and stats.mean:
            percentile, savings, rec, reasoning = analyze_price_history(
                current_price  = current_price,
                min_price      = stats.min_price,
                max_price      = stats.max_price,
                mean_price     = stats.mean,
                current_status = stats.current_status,
            )

            # Downgrade to "wait" if sale is imminent (≤14 days) and not already a great deal
            if days_to_sale and days_to_sale <= 14 and rec not in ("buy_now",):
                rec = "wait"
                reasoning += f" Also, {sale_name} is only {days_to_sale} days away."

            return DealIntelligence(
                product_id       = product.id,
                product_title    = product.title,
                current_price    = current_price,
                currency         = currency,
                price_percentile = percentile,
                all_time_low     = stats.min_price,
                all_time_high    = stats.max_price,
                average_price_30d = stats.mean,
                savings_vs_average = savings,
                original_price   = compare_at,
                discount_pct     = round((compare_at - current_price) / compare_at * 100, 1)
                                   if compare_at and compare_at > current_price else None,
                next_likely_sale = sale_name,
                days_to_sale     = days_to_sale,
                recommendation   = rec,
                confidence       = "high",
                reasoning        = reasoning,
                data_source      = "price_history",
            )
    except Exception:
        pass  # price tracking not available for this product

    # ── Tier 2: compare_at_price ──────────────────────────────────────────────
    if compare_at and compare_at > current_price:
        discount_pct, rec, reasoning = analyze_compare_at_price(current_price, compare_at)

        if days_to_sale and days_to_sale <= 14 and rec not in ("buy_now",):
            rec = "wait"
            reasoning += f" {sale_name} is {days_to_sale} days away."

        return DealIntelligence(
            product_id        = product.id,
            product_title     = product.title,
            current_price     = current_price,
            currency          = currency,
            price_percentile  = None,
            all_time_low      = None,
            all_time_high     = None,
            average_price_30d = None,
            savings_vs_average = round(compare_at - current_price, 2),
            original_price    = compare_at,
            discount_pct      = round(discount_pct, 1),
            next_likely_sale  = sale_name,
            days_to_sale      = days_to_sale,
            recommendation    = rec,
            confidence        = "medium",
            reasoning         = reasoning,
            data_source       = "compare_at_price",
        )

    # ── Tier 3: calendar only ─────────────────────────────────────────────────
    rec, reasoning = calendar_recommendation(days_to_sale)

    return DealIntelligence(
        product_id        = product.id,
        product_title     = product.title,
        current_price     = current_price,
        currency          = currency,
        price_percentile  = None,
        all_time_low      = None,
        all_time_high     = None,
        average_price_30d = None,
        savings_vs_average = None,
        original_price    = None,
        discount_pct      = None,
        next_likely_sale  = sale_name,
        days_to_sale      = days_to_sale,
        recommendation    = rec,
        confidence        = "low",
        reasoning         = reasoning,
        data_source       = "calendar_only",
    )
