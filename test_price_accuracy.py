"""
Price Accuracy Verification
============================
Two-pass test:
  Pass 1 — build basket (records Channel3 prices at T1)
  Pass 2 — re-fetch each product from Channel3 API (prices at T2, ~seconds later)

This measures:
  a) Price stability  — how much Channel3 prices drift between calls
  b) Cross-offer spread — cheapest vs most expensive retailer per product

For manual retailer verification, the exact retailer URLs are printed at the end.

Run: python test_price_accuracy.py
"""
import os, time
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.basket_optimizer import optimize_basket

QUERIES = [
    "sony wh-1000xm5 headphones",
    "nike running shoes men",
    "yoga mat thick",
    "mechanical keyboard logitech",
    "air purifier hepa",
    "protein powder whey",
    "sunscreen spf 50 face",
    "standing desk electric",
    "water bottle insulated",
    "laptop sleeve 15 inch",
    "resistance bands set",
    "bluetooth speaker portable",
]

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

# ── Pass 1: Build basket ──────────────────────────────────────────────────────
print("Pass 1 — building basket (recording T1 prices)...")
basket_products = []

for query in QUERIES:
    results = client.search.perform(query=query, limit=5)
    products = [p for p in (results.products or []) if p.offers]
    picked = next((p for p in products if len(p.offers or []) > 1), None) or (products[0] if products else None)
    if picked:
        basket_products.append(picked)

result = optimize_basket(basket_products)
print(f"  {len(result.items)} items across {len(result.retailer_breakdown)} retailers\n")

t1_prices = {item.product_id: item.price for item in result.items}

# ── Pass 2: Re-fetch fresh from Channel3 ─────────────────────────────────────
print("Pass 2 — re-fetching each product from Channel3 API (T2)...")
t2_data = {}
for item in result.items:
    try:
        fresh = client.products.retrieve(item.product_id)
        offers = fresh.offers or []
        in_stock = [o for o in offers if o.availability == "InStock"]
        pool = in_stock or offers
        if pool:
            best = min(pool, key=lambda o: o.price.price)
            all_prices = sorted(set(o.price.price for o in pool))
            t2_data[item.product_id] = {
                "best_price":  best.price.price,
                "best_domain": best.domain,
                "all_prices":  all_prices,
                "num_offers":  len(pool),
                "compare_at":  best.price.compare_at_price,
            }
    except Exception as e:
        t2_data[item.product_id] = None
    time.sleep(0.1)

print(f"  Re-fetched {len([v for v in t2_data.values() if v])} products\n")

# ── Accuracy report ───────────────────────────────────────────────────────────
print("=" * 76)
print("  PRICE ACCURACY REPORT")
print("=" * 76)
print(f"  {'PRODUCT':<40} {'T1 (basket)':>11} {'T2 (fresh)':>11} {'DRIFT':>8}  STATUS")
print(f"  {'─'*40} {'─'*11} {'─'*11} {'─'*8}  {'─'*10}")

diffs = []
matches = 0
total = 0

for item in result.items:
    t1 = t1_prices.get(item.product_id)
    t2_info = t2_data.get(item.product_id)

    if t1 is None:
        continue
    total += 1

    if t2_info:
        t2 = t2_info["best_price"]
        diff = t2 - t1
        diff_pct = abs(diff) / t1 * 100 if t1 else 0
        diffs.append(abs(diff))

        if diff == 0:
            status = "✅ EXACT"
            matches += 1
        elif diff_pct < 1:
            status = "✅ <1%"
            matches += 1
        elif diff_pct < 5:
            status = "🟡 ~MATCH"
            matches += 1
        else:
            status = "❌ CHANGED"

        drift_str = f"+${diff:.2f}" if diff > 0 else (f"-${abs(diff):.2f}" if diff < 0 else "$0.00")
        t2_str = f"${t2:.2f}"
    else:
        drift_str = "—"
        t2_str = "N/A"
        status = "⚠ NO DATA"

    print(f"  {item.product_title[:40]:<40} ${t1:>9.2f}  {t2_str:>11}  {drift_str:>8}  {status}")

# ── Price spread analysis ─────────────────────────────────────────────────────
print(f"\n{'─'*76}")
print("  OFFER SPREAD ANALYSIS (price range across retailers per product)")
print(f"{'─'*76}")
print(f"  {'PRODUCT':<40} {'CHEAPEST':>9} {'PRICIEST':>9} {'SPREAD':>8}  OFFERS")
print(f"  {'─'*40} {'─'*9} {'─'*9} {'─'*8}  {'─'*6}")

spreads = []
for item in result.items:
    t2_info = t2_data.get(item.product_id)
    if not t2_info or len(t2_info["all_prices"]) < 2:
        cheapest = t2_info["best_price"] if t2_info else item.price
        priciest = cheapest
        spread = 0.0
        offers_n = t2_info["num_offers"] if t2_info else 1
    else:
        cheapest = t2_info["all_prices"][0]
        priciest = t2_info["all_prices"][-1]
        spread   = priciest - cheapest
        offers_n = t2_info["num_offers"]
        spreads.append(spread)

    spread_pct = spread / cheapest * 100 if cheapest else 0
    spread_str = f"${spread:.2f} ({spread_pct:.0f}%)" if spread > 0 else "—"
    print(f"  {item.product_title[:40]:<40} ${cheapest:>7.2f}  ${priciest:>7.2f}  {spread_str:>10}  {offers_n}")

# ── Grand summary ─────────────────────────────────────────────────────────────
verified = len([v for v in t2_data.values() if v])
accuracy_pct = matches / total * 100 if total else 0
avg_drift = sum(diffs) / len(diffs) if diffs else 0
max_drift = max(diffs) if diffs else 0
avg_spread = sum(spreads) / len(spreads) if spreads else 0

print(f"\n{'─'*76}")
print("  SUMMARY")
print(f"{'─'*76}")
print(f"  Products tested        : {total}")
print(f"  Channel3 → Channel3    : {accuracy_pct:.0f}% match rate  ({matches}/{total} within 5%)")
print(f"  Avg price drift T1→T2  : ${avg_drift:.4f}  (seconds apart — measures data freshness)")
print(f"  Max price drift T1→T2  : ${max_drift:.2f}")
print(f"  Avg cross-retailer spread: ${avg_spread:.2f}  (spread between cheapest & priciest retailer)")
print()
print("  INTERPRETATION")
print("  ─────────────────────────────────────────────────────────────────")
if avg_drift < 0.01:
    print("  ✅ Prices are highly stable — Channel3 data is consistent.")
else:
    print(f"  🟡 Small drift detected (${avg_drift:.2f} avg) — prices may update between search and checkout.")
if avg_spread > 20:
    print(f"  💰 High retailer spread (${avg_spread:.2f} avg) — basket optimizer is saving real money.")
else:
    print(f"  ℹ️  Modest retailer spread (${avg_spread:.2f} avg) — prices are fairly uniform across retailers.")

# ── Manual verification section ──────────────────────────────────────────────
print(f"\n{'─'*76}")
print("  MANUAL PRICE VERIFICATION")
print("  (Channel3 buy URLs require Cloudflare human check — open in browser)")
print(f"{'─'*76}")
for item in result.items:
    t2_info = t2_data.get(item.product_id)
    disc = ""
    if t2_info and t2_info.get("compare_at") and t2_info["compare_at"] > item.price:
        pct = (t2_info["compare_at"] - item.price) / t2_info["compare_at"] * 100
        disc = f"  [{pct:.0f}% off listed ${t2_info['compare_at']:.2f}]"
    print(f"\n  {item.product_title[:60]}")
    print(f"  Channel3 price : ${item.price:.2f} @ {item.recommended_retailer}{disc}")
    print(f"  Verify at      : {item.product_url}")

print(f"\n{'='*76}")
