"""
Test Feature 3 — Smart Product Comparison across multiple categories.
Run: python test_comparison.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.comparison import compare

QUERIES = [
    "yoga mat",
    "running shoes",
    "air purifier",
    "mechanical keyboard",
    "sunscreen spf 50",
]

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))


def short(title: str, n: int = 28) -> str:
    return title[:n] + "…" if len(title) > n else title


def run_comparison(query: str, idx: int):
    print(f"\n{'═'*68}")
    print(f"  [{idx}/{len(QUERIES)}] '{query}'")
    print(f"{'═'*68}")

    results = client.search.perform(query=query, limit=8)
    products = [p for p in (results.products or []) if p.brands and p.offers][:3]

    if len(products) < 2:
        print("  Not enough products — skipping.")
        return

    print("  Comparing:")
    for p in products:
        best = min(p.offers, key=lambda o: o.price.price)
        print(f"    • {short(p.title, 50):<52} ${best.price.price:.0f}")

    print("  Running comparison...", end="", flush=True)
    try:
        result = compare(client, [p.id for p in products])
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return

    winner = short(result.product_titles.get(result.overall_winner, "?"), 35)
    runner = short(result.product_titles.get(result.runner_up, ""), 35) if result.runner_up else "—"

    print(f"\r  Category : {result.category}")
    print(f"  Winner   : {winner}")
    print(f"  Runner-up: {runner}")
    print(f"  Summary  : {result.summary[:160]}…")

    # Axis table (compact)
    col = 10
    ids = result.product_ids
    titles_short = {pid: short(result.product_titles.get(pid, pid), col) for pid in ids}
    header = f"  {'AXIS':<22}" + "  ".join(f"{titles_short[pid]:<{col}}" for pid in ids)
    print(f"\n{header}")
    print(f"  {'─'*22}" + "  ".join("─"*col for _ in ids))
    for ax in result.axes:
        row = f"  {ax.axis:<22}"
        for pid in ids:
            r = ax.ratings.get(pid, 0)
            stars = "★" * int(round(r/2)) + "☆" * (5 - int(round(r/2)))
            win_marker = " ◀" if pid == ax.winner else "  "
            row += f"{stars}{win_marker}"
        print(row)

    print(f"\n  BEST FOR:")
    for persona, pid in result.best_for.items():
        label = persona.replace("_", " ").title()
        print(f"    {label:<26} → {short(result.product_titles.get(pid, pid), 35)}")


for i, q in enumerate(QUERIES, 1):
    run_comparison(q, i)

print(f"\n{'═'*68}")
print("  All comparisons done.")
print(f"{'═'*68}")
