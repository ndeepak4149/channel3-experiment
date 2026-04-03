"""
Test Feature 1 across 6-7 different products.
Run: python test_multi_products.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.review_intelligence import get_review_intelligence

QUERIES = [
    "wireless headphones",
    "running shoes nike",
    "standing desk",
    "protein powder",
    "air purifier",
    "mechanical keyboard",
    "sunscreen spf 50",
]

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))


def pick_product(query: str):
    results = client.search.perform(query=query, limit=5)
    products = results.products or []
    # prefer product with a known brand and at least one offer
    for p in products:
        if p.brands and p.offers:
            return p
    return products[0] if products else None


def run(query: str, idx: int):
    print(f"\n{'─'*60}")
    print(f"  [{idx}/7] Query: '{query}'")
    print(f"{'─'*60}")

    product = pick_product(query)
    if not product:
        print("  No product found, skipping.")
        return

    brand = product.brands[0].name if product.brands else ""
    offers = product.offers or []
    best = min(offers, key=lambda o: o.price.price) if offers else None
    price_str = f"${best.price.price:.2f} @ {best.domain}" if best else "N/A"

    print(f"  Product : {product.title[:65]}")
    print(f"  Brand   : {brand or 'N/A'}  |  Price: {price_str}")
    print(f"  Fetching reviews...", end="", flush=True)

    review = get_review_intelligence(
        product_id=product.id,
        product_title=product.title,
        brand=brand,
    )

    bar = "█" * (review.aggregate_score // 5) + "░" * (20 - review.aggregate_score // 5)
    mode_tag = "web+llm" if review.source_mode == "web+llm" else "llm-knowledge"
    print(f"\r  Score   : [{bar}] {review.aggregate_score}/100  ({review.total_sources} sources, {review.confidence:.0%} conf) [{mode_tag}]")
    print(f"  Summary : {review.consensus_summary[:180]}...")

    if review.pros:
        print(f"  Pros    : {' | '.join(review.pros[:3])}")
    if review.cons:
        print(f"  Cons    : {' | '.join(review.cons[:2])}")
    if review.red_flags:
        print(f"  ⚠ Flags : {' | '.join(review.red_flags)}")


print("=" * 60)
print("  REVIEW INTELLIGENCE — MULTI-PRODUCT TEST")
print("=" * 60)

for i, q in enumerate(QUERIES, 1):
    run(q, i)

print(f"\n{'='*60}")
print("  Done. Results are cached — re-runs will be instant.")
print(f"{'='*60}")
