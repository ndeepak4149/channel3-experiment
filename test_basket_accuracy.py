"""
Basket Optimizer Accuracy Test — 12 products
Builds a realistic mixed basket, runs the optimizer, and produces a
detailed price report you can cross-check against the actual retailer sites.

Run: python test_basket_accuracy.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.basket_optimizer import optimize_basket
from features.basket_optimizer.shipping import get_shipping_cost

# Realistic mixed shopping basket
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

# US state tax rates (approximate) for reference
STATE_TAX = {
    "CA": 0.0725, "NY": 0.08, "TX": 0.0625, "FL": 0.06,
    "WA": 0.065,  "OR": 0.0,  "MT": 0.0,    "NH": 0.0,
}

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

print("=" * 72)
print("  BASKET OPTIMIZER — ACCURACY & PRICE VERIFICATION TEST")
print("=" * 72)
print(f"  Building basket from {len(QUERIES)} product searches...\n")

basket_products = []
search_log = []

for query in QUERIES:
    results = client.search.perform(query=query, limit=5)
    products = [p for p in (results.products or []) if p.offers]

    # Pick first product with multiple offers (more interesting for optimization)
    picked = next((p for p in products if len(p.offers or []) > 1), None)
    if not picked and products:
        picked = products[0]

    if picked:
        offers = picked.offers or []
        in_stock = [o for o in offers if o.availability == "InStock"]
        pool = in_stock or offers
        best = min(pool, key=lambda o: o.price.price)

        search_log.append({
            "query":      query,
            "title":      picked.title,
            "id":         picked.id,
            "offers":     len(offers),
            "best_price": best.price.price,
            "best_domain":best.domain,
            "best_url":   best.url,
            "compare_at": best.price.compare_at_price,
        })
        basket_products.append(picked)
    else:
        search_log.append({"query": query, "title": "NOT FOUND", "id": None})

# ── Show what we found ────────────────────────────────────────────────────────
print(f"  {'#':<3} {'PRODUCT':<45} {'OFFERS':<7} {'BEST PRICE'}")
print(f"  {'─'*3} {'─'*45} {'─'*7} {'─'*20}")
for i, log in enumerate(search_log, 1):
    if log.get("id"):
        disc = f"  (was ${log['compare_at']:.2f})" if log.get("compare_at") else ""
        print(f"  {i:<3} {log['title'][:45]:<45} {log['offers']:<7} ${log['best_price']:.2f} @ {log['best_domain']}{disc}")
    else:
        print(f"  {i:<3} {'NOT FOUND':<45}")

print(f"\n  {len(basket_products)} products added to basket.")

# ── Run optimizer ─────────────────────────────────────────────────────────────
print("\n" + "─" * 72)
print("  Running cross-retailer optimization...")
result = optimize_basket(basket_products)

# ── Detailed price breakdown ──────────────────────────────────────────────────
print("\n" + "=" * 72)
print("  OPTIMIZED BASKET — FULL PRICE BREAKDOWN")
print("=" * 72)

print(f"\n  {'PRODUCT':<44} {'RETAILER':<26} {'PRICE':<9} {'DISC'}")
print(f"  {'─'*44} {'─'*26} {'─'*9} {'─'*8}")

for item in result.items:
    disc = f"{item.discount_pct:.0f}% off" if item.discount_pct else "—"
    print(f"  {item.product_title[:44]:<44} {item.recommended_retailer[:26]:<26} ${item.price:<8.2f} {disc}")

# ── Per-retailer order summary ────────────────────────────────────────────────
print(f"\n{'─'*72}")
print("  PER-RETAILER ORDER TOTALS")
print(f"{'─'*72}")

for domain, summary in result.retailer_breakdown.items():
    ship_str = "FREE" if summary.shipping == 0 else f"${summary.shipping:.2f}"
    print(f"\n  🏪  {domain}")
    for t in summary.items:
        match = next((it for it in result.items if it.product_title[:50] == t[:50]), None)
        print(f"       • {t[:52]}  ${match.price:.2f}" if match else f"       • {t[:52]}")
    print(f"       {'─'*50}")
    print(f"       Subtotal : ${summary.subtotal:.2f}")
    print(f"       Shipping : {ship_str}")
    if summary.free_shipping_threshold:
        print(f"       (Free shipping threshold: ${summary.free_shipping_threshold:.0f})")
    print(f"       ORDER TOTAL: ${summary.order_total:.2f}")
    if summary.note:
        print(f"       💡 {summary.note}")

# ── Grand total with estimated taxes ─────────────────────────────────────────
print(f"\n{'─'*72}")
print("  GRAND TOTAL SUMMARY")
print(f"{'─'*72}")
print(f"  Items subtotal    : ${result.subtotal:.2f}")
print(f"  Shipping (total)  : ${result.total_shipping:.2f}")
print(f"  Pre-tax total     : ${result.total_cost:.2f}")
print()
print("  Estimated taxes by state (add to pre-tax total):")
for state, rate in STATE_TAX.items():
    tax = result.total_cost * rate
    total_with_tax = result.total_cost + tax
    print(f"    {state} ({rate*100:.2f}%)  +${tax:.2f}  =  ${total_with_tax:.2f}")
print()
print(f"  ─── vs single retailer ({result.cheapest_single_retailer}) ───")
print(f"  Cheapest single   : ${result.cheapest_single_total:.2f}")
print(f"  Your savings      : ${result.savings_vs_single:.2f}  "
      f"({'%.1f' % (result.savings_vs_single/result.cheapest_single_total*100 if result.cheapest_single_total else 0)}%)")

# ── Verification links ────────────────────────────────────────────────────────
print(f"\n{'─'*72}")
print("  VERIFY PRICES (click to check on retailer site):")
print(f"{'─'*72}")
for item in result.items:
    print(f"\n  {item.product_title[:55]}")
    print(f"  Listed : ${item.price:.2f} @ {item.recommended_retailer}")
    print(f"  Buy URL: {item.product_url}")

# ── Tips ──────────────────────────────────────────────────────────────────────
if result.notes:
    print(f"\n{'─'*72}")
    print("  MONEY-SAVING TIPS:")
    for note in result.notes:
        print(f"  💡 {note}")

print(f"\n{'='*72}")
print("  NOTE: Prices shown are from Channel3's live data.")
print("  Taxes vary by state and retailer — estimates shown above.")
print("  Verify final prices at retailer checkout before purchasing.")
print(f"{'='*72}")
