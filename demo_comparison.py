"""
Demo: Feature 3 — Smart Product Comparison
===========================================
Searches Channel3, picks the top 3 results, and runs a full
structured comparison with per-axis ratings and winner logic.

Run: python demo_comparison.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.comparison import compare

QUERY = "wireless headphones"

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

# ── Step 1: Search + pick top 3 products ─────────────────────────────────────
print(f"Searching Channel3 for: '{QUERY}'")
results = client.search.perform(query=QUERY, limit=6)
products = [p for p in (results.products or []) if p.brands and p.offers][:3]

if len(products) < 2:
    print("Not enough products found.")
    exit(1)

print("Comparing:")
for p in products:
    offers = p.offers or []
    best = min(offers, key=lambda o: o.price.price) if offers else None
    price = f"${best.price.price:.0f}" if best else "N/A"
    print(f"  • [{p.id}] {p.title[:55]}  {price}")

print("\nFetching review data + running comparison (Claude)...\n")

# ── Step 2: Compare ───────────────────────────────────────────────────────────
result = compare(client, [p.id for p in products])

# ── Step 3: Display ───────────────────────────────────────────────────────────
def short(pid: str) -> str:
    title = result.product_titles.get(pid, pid)
    # Shorten to brand + first meaningful word
    parts = title.split()
    return " ".join(parts[:3]) if len(parts) >= 3 else title

winner_title = short(result.overall_winner)
runner_title = short(result.runner_up) if result.runner_up else "N/A"

print("=" * 70)
print(f"  COMPARISON: {result.category.upper()}")
print("=" * 70)
print(f"  Products : {' vs '.join(short(pid) for pid in result.product_ids)}")
print(f"  Winner   : {winner_title}")
print(f"  Runner-up: {runner_title}")
print(f"\n  {result.summary}\n")

# Axis table
col_w = 16
header = f"  {'AXIS':<22}" + "".join(f"{short(pid):<{col_w}}" for pid in result.product_ids) + "WINNER"
print("─" * 70)
print(header)
print("─" * 70)

for ax in result.axes:
    row = f"  {ax.axis:<22}"
    for pid in result.product_ids:
        rating = ax.ratings.get(pid, 0)
        stars  = "★" * int(round(rating / 2)) + "☆" * (5 - int(round(rating / 2)))
        cell   = f"{stars} {rating:.1f}"
        row   += f"{cell:<{col_w}}"
    row += short(ax.winner)
    print(row)
    print(f"  {'':22}{ax.explanation}")
    print()

# Best-for table
print("─" * 70)
print("  BEST FOR")
print("─" * 70)
for persona, pid in result.best_for.items():
    label = persona.replace("_", " ").title()
    print(f"  {label:<28} → {short(pid)}")

print("=" * 70)
