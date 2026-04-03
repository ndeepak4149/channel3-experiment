"""
Demo: Feature 4 — Deal Intelligence & Buy Timing
=================================================
Searches Channel3 for multiple queries and shows buy/wait
recommendations for each product, ranked by deal quality.

Run: python demo_deal_intelligence.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.deal_intelligence import get_deal_intelligence

QUERIES = [
    "wireless headphones",
    "yoga mat",
    "running shoes",
    "air purifier",
    "mechanical keyboard",
    "sunscreen spf 50",
    "standing desk",
]

REC_ICON = {
    "buy_now":   "🟢 BUY NOW  ",
    "good_deal": "✅ GOOD DEAL",
    "wait":      "⏳ WAIT     ",
    "overpriced":"🔴 OVERPRICED",
}

CONF_ICON = {"high": "●●●", "medium": "●●○", "low": "●○○"}

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

print("=" * 72)
print("  DEAL INTELLIGENCE — BUY TIMING ANALYSIS")
print("=" * 72)

all_deals = []

for query in QUERIES:
    results = client.search.perform(query=query, limit=4)
    products = [p for p in (results.products or []) if p.offers][:2]

    for product in products:
        deal = get_deal_intelligence(client, product)
        all_deals.append((query, product, deal))

# Sort: buy_now first, then good_deal, then wait, then overpriced
ORDER = {"buy_now": 0, "good_deal": 1, "wait": 2, "overpriced": 3}
all_deals.sort(key=lambda x: ORDER.get(x[2].recommendation, 9))

print(f"\n  {'REC':<13} {'CONF':<5} {'PRICE':<9} {'DISCOUNT':<10} {'NEXT SALE':<24} PRODUCT")
print(f"  {'─'*13} {'─'*5} {'─'*9} {'─'*10} {'─'*24} {'─'*32}")

for query, product, deal in all_deals:
    rec_label  = REC_ICON.get(deal.recommendation, deal.recommendation)
    conf_label = CONF_ICON.get(deal.confidence, "?")
    price_str  = f"${deal.current_price:.0f}"
    disc_str   = f"{deal.discount_pct:.0f}% off" if deal.discount_pct else "—"
    sale_str   = deal.next_likely_sale[:22] if deal.next_likely_sale else "—"
    title_str  = product.title[:32]

    print(f"  {rec_label}  {conf_label}  {price_str:<9} {disc_str:<10} {sale_str:<24} {title_str}")

# Detail view for the top 3 buy_now / best deals
top = [d for d in all_deals if d[2].recommendation in ("buy_now", "good_deal")][:3]

if top:
    print(f"\n{'─'*72}")
    print("  TOP DEAL DETAILS")
    print(f"{'─'*72}")
    for query, product, deal in top:
        print(f"\n  {REC_ICON[deal.recommendation]}  {product.title[:60]}")
        print(f"  Price      : ${deal.current_price:.2f} {deal.currency}")
        if deal.discount_pct:
            print(f"  Discount   : {deal.discount_pct:.1f}% off (was ${deal.original_price:.2f})")
        if deal.price_percentile is not None:
            print(f"  Percentile : {deal.price_percentile}/100  "
                  f"(low ${deal.all_time_low:.2f} — high ${deal.all_time_high:.2f})")
        if deal.average_price_30d:
            sign = "+" if (deal.savings_vs_average or 0) < 0 else "-"
            amt  = abs(deal.savings_vs_average or 0)
            print(f"  vs 30d avg : ${deal.average_price_30d:.2f}  ({sign}${amt:.2f})")
        print(f"  Next sale  : {deal.next_likely_sale or '—'}  ({deal.days_to_sale or '?'} days)")
        print(f"  Source     : {deal.data_source}  |  Confidence: {deal.confidence}")
        print(f"  Reasoning  : {deal.reasoning}")

print(f"\n{'='*72}")
