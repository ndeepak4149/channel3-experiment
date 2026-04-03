"""
Demo: Feature 1 — Aggregated Review Intelligence
=================================================
Searches Channel3 for a product, then enriches the top result
with aggregated review intelligence from across the web.

Run: python demo_review.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.review_intelligence import get_review_intelligence

QUERY = "yoga mat"

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

# ── Step 1: Search Channel3 ──────────────────────────────────────────────────
print(f"Searching Channel3 for: '{QUERY}'")
results = client.search.perform(query=QUERY, limit=5)
products = results.products or []

if not products:
    print("No products found.")
    exit(1)

# Pick the first product with a known brand
product = next(
    (p for p in products if p.brands),
    products[0]
)

brand = product.brands[0].name if product.brands else ""
offers = product.offers or []
best_offer = min(offers, key=lambda o: o.price.price) if offers else None

print(f"\nSelected product: {product.title}")
print(f"Brand:  {brand}")
if best_offer:
    print(f"Price:  ${best_offer.price.price:.2f} @ {best_offer.domain}")
print()

# ── Step 2: Get Review Intelligence ─────────────────────────────────────────
print("Fetching review intelligence (web search + Claude extraction)...")
print("This takes ~10-15 seconds on first run, then cached for 48h.\n")

review = get_review_intelligence(
    product_id=product.id,
    product_title=product.title,
    brand=brand,
)

# ── Step 3: Display ──────────────────────────────────────────────────────────
bar = "█" * (review.aggregate_score // 5) + "░" * (20 - review.aggregate_score // 5)
print(f"{'='*60}")
print(f"  REVIEW INTELLIGENCE: {product.title}")
print(f"{'='*60}")
print(f"  Score      : [{bar}] {review.aggregate_score}/100")
print(f"  Sources    : {review.total_sources} snippets | confidence {review.confidence:.0%}")
print(f"  Updated    : {review.last_updated.strftime('%Y-%m-%d %H:%M UTC')}")
print()
print(f"  SUMMARY")
print(f"  {review.consensus_summary}")
print()

if review.pros:
    print("  PROS")
    for pro in review.pros:
        print(f"    + {pro}")
    print()

if review.cons:
    print("  CONS")
    for con in review.cons:
        print(f"    - {con}")
    print()

if review.red_flags:
    print("  RED FLAGS ⚠")
    for flag in review.red_flags:
        print(f"    ! {flag}")
    print()

print(f"  SOURCES ({len(review.sources)})")
for s in review.sources[:5]:
    sentiment_label = "+" if s.sentiment > 0.2 else ("-" if s.sentiment < -0.2 else "~")
    print(f"    [{sentiment_label}] [{s.platform:10}] {s.url[:70]}")
if len(review.sources) > 5:
    print(f"    ... and {len(review.sources) - 5} more")
print(f"{'='*60}")
