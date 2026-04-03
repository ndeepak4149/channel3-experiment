"""
to verify Channel3 SDK is set up correctly and data fetching works.
Run: python verify_setup.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CHANNEL3_API_KEY")
if not api_key:
    print("ERROR: CHANNEL3_API_KEY not set. Copy .env.example to .env and add your key.")
    print("Get your key at: https://trychannel3.com/dashboard/api-keys")
    sys.exit(1)

from channel3_sdk import Channel3

client = Channel3(api_key=api_key)

print("=== Channel3 Setup Verification ===\n")

# ── 1. Search ────────────────────────────────────────────────────────────────
print("1. Testing search endpoint...")
products = []
try:
    results = client.search.perform(query="wireless headphones under $100", limit=5)
    products = results.products or []
    print(f"   OK — got {len(products)} products")
    for p in products[:3]:
        offers = p.offers or []
        price_str = f"${offers[0].price.price:.2f}" if offers else "no price"
        retailer  = offers[0].domain if offers else "N/A"
        print(f"   • {p.title[:60]:<60} {price_str} @ {retailer}")
except Exception as e:
    print(f"   FAIL: {e}")

print()

# ── 2. Product detail ────────────────────────────────────────────────────────
if products:
    first_id = products[0].id
    print(f"2. Testing product detail (id={first_id})...")
    try:
        detail = client.products.retrieve(first_id)
        print(f"   OK — {detail.title}")
        print(f"   Categories : {detail.categories}")
        print(f"   Brands     : {[b.name for b in (detail.brands or [])]}")
        print(f"   Offers     : {len(detail.offers or [])} offer(s)")
        if detail.offers:
            o = detail.offers[0]
            print(f"   Best offer : ${o.price.price:.2f} @ {o.domain} | in-stock: {o.availability == 'InStock'}")
            if o.price.compare_at_price:
                saving = o.price.compare_at_price - o.price.price
                print(f"   On sale    : was ${o.price.compare_at_price:.2f}, saving ${saving:.2f}")
    except Exception as e:
        print(f"   FAIL: {e}")
else:
    print("2. Skipping product detail (no results from search)")

print()

# ── 3. Price history ─────────────────────────────────────────────────────────
if products:
    first_id = products[0].id
    print(f"3. Testing price history (id={first_id})...")
    try:
        history = client.price_tracking.get_history(first_id, days=30)
        entries  = history.history or []
        stats    = history.statistics
        print(f"   OK — {len(entries)} data point(s) over 30 days")
        if stats:
            print(f"   Current: ${stats.current_price:.2f} ({stats.current_status})")
            print(f"   Range  : ${stats.min_price:.2f} – ${stats.max_price:.2f}  |  avg ${stats.mean:.2f}")
        if entries:
            latest = max(entries, key=lambda e: e.timestamp)
            print(f"   Latest entry: ${latest.price:.2f} on {latest.timestamp.date()}")
    except Exception as e:
        print(f"   FAIL (product may not be tracked yet): {e}")

print()

# ── 4. Brands ────────────────────────────────────────────────────────────────
print("4. Testing brands list...")
try:
    brand_names = []
    for brand in client.brands.list():
        brand_names.append(brand.name)
        if len(brand_names) >= 5:
            break
    print(f"   OK — sample brands: {', '.join(brand_names)}")
except Exception as e:
    print(f"   FAIL: {e}")

print()
print("=== Verification complete ===")
print("If all checks passed, you're ready to build!")
