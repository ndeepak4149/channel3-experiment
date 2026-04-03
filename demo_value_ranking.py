"""
Demo: Feature 2 — Value Ranking Engine
=======================================
Searches Channel3, optionally enriches with review scores (Feature 1),
then ranks every result by multi-signal value score.

Run: python demo_value_ranking.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.value_ranking import rank_products
from features.review_intelligence import get_review_intelligence

QUERY = "wireless headphones"
ENRICH_WITH_REVIEWS = True   # set False to skip Feature 1 and run instantly

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

# ── Step 1: Search ────────────────────────────────────────────────────────────
print(f"Searching Channel3 for: '{QUERY}'")
results = client.search.perform(query=QUERY, limit=10)
products = results.products or []
print(f"Got {len(products)} products.\n")

# ── Step 2: Optionally get review scores (Feature 1) ─────────────────────────
review_scores: dict[str, int] = {}
if ENRICH_WITH_REVIEWS:
    print("Fetching review intelligence for each product (cached after first run)...")
    for p in products:
        brand = p.brands[0].name if p.brands else ""
        r = get_review_intelligence(p.id, p.title, brand)
        review_scores[p.id] = r.aggregate_score
        print(f"  {r.aggregate_score:>3}/100  {p.title[:55]}")
    print()

# ── Step 3: Rank ──────────────────────────────────────────────────────────────
ranked = rank_products(products, query=QUERY, review_scores=review_scores)

# ── Step 4: Display ───────────────────────────────────────────────────────────
TIER_ICON = {
    "exceptional": "🏆",
    "good":        "✅",
    "fair":        "🟡",
    "overpriced":  "🔴",
}

print("=" * 72)
print(f"  VALUE RANKINGS — '{QUERY}'")
print(f"  {ranked.ranking_explanation}")
print("=" * 72)

# Header
print(f"  {'RNK':<4} {'SCORE':<6} {'TIER':<12} {'PRICE':<10} {'PRODUCT':<35}")
print(f"  {'─'*4} {'─'*6} {'─'*12} {'─'*10} {'─'*35}")

for vs in ranked.ranked:
    # Get the matching product for price
    product = next((p for p in products if p.id == vs.product_id), None)
    offers  = product.offers or [] if product else []
    best    = min(offers, key=lambda o: o.price.price) if offers else None
    price   = f"${best.price.price:.0f}" if best else "N/A"
    icon    = TIER_ICON.get(vs.value_tier, "")

    print(f"  #{vs.rank:<3} {vs.overall_score:<6.1f} {icon} {vs.value_tier:<10} {price:<10} {vs.product_title[:35]}")

print()

# Detail view for top 3
print("─" * 72)
print("  TOP 3 DETAIL")
print("─" * 72)

for vs in ranked.ranked[:3]:
    product = next((p for p in products if p.id == vs.product_id), None)
    offers  = product.offers or [] if product else []
    all_offers = [f"${o.price.price:.0f}@{o.domain}" for o in offers]
    brands  = [b.name for b in (product.brands or [])] if product else []

    print(f"\n  #{vs.rank} — {vs.product_title}")
    print(f"  Brand  : {', '.join(brands) or 'N/A'}")
    print(f"  Offers : {' | '.join(all_offers) or 'N/A'}")
    print(f"  Score  : {vs.overall_score}/100  [{vs.value_tier.upper()}]")
    print(f"  Tip    : {vs.one_liner}")
    print(f"  Breakdown:")
    for signal, score in sorted(vs.score_breakdown.items(), key=lambda x: -x[1]):
        weight_pct = vs.signal_weights[signal] * 100
        bar = "▓" * int(score // 10) + "░" * (10 - int(score // 10))
        print(f"    {signal:<20} [{bar}] {score:>5.1f}  (weight {weight_pct:.0f}%)")

print(f"\n{'='*72}")
