"""
Demo: Feature 6 — Purchase Persona Memory
==========================================
Shows how persona builds up from basket interactions and explicit
declarations, then personalizes Value Ranking results.

Run: python demo_persona.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.persona import get_persona, observe_pick, declare
from features.value_ranking import rank_products

PERSONA_ID = "demo_user"

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))


def print_persona(persona, title="PERSONA PROFILE"):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")
    print(f"  ID            : {persona.persona_id}")
    print(f"  Price tier    : {persona.price_tier.upper()}")
    print(f"  Avg spend     : ${persona.avg_spend_per_item:.2f}" if persona.avg_spend_per_item else "  Avg spend     : —")
    print(f"  Deal sensitivity: {persona.deal_sensitivity:.0%}  {'(deal hunter)' if persona.deal_sensitivity > 0.6 else '(not deal-driven)'}")
    print(f"  Priorities    : {' > '.join(persona.value_priorities)}")
    if persona.preferred_brands:
        print(f"  Fav brands    : {', '.join(persona.preferred_brands[:6])}")
    if persona.avoided_brands:
        print(f"  Avoid brands  : {', '.join(persona.avoided_brands)}")
    if persona.category_affinities:
        top_cats = sorted(persona.category_affinities.items(), key=lambda x: -x[1])[:4]
        cats_str  = "  |  ".join(f"{k} {v:.0%}" for k, v in top_cats)
        print(f"  Categories    : {cats_str}")
    if persona.declared_sizes:
        sizes_str = "  ".join(f"{k}={v}" for k, v in persona.declared_sizes.items())
        print(f"  Sizes         : {sizes_str}")
    interactions = persona.interaction_count
    print(f"  Interactions  : {interactions}")
    print(f"{'─'*60}")


# ── 1. Start fresh ────────────────────────────────────────────────────────────
# Delete existing demo persona so we start clean
import os as _os
demo_path = f"personas/{PERSONA_ID}.json"
if _os.path.exists(demo_path):
    _os.remove(demo_path)

persona = get_persona(PERSONA_ID, "Demo User")
print("=" * 60)
print("  FEATURE 6 — PURCHASE PERSONA MEMORY")
print("=" * 60)
print_persona(persona, "INITIAL (blank slate)")

# ── 2. Simulate basket interactions ──────────────────────────────────────────
print("\n  Simulating 8 product interactions...")

sim_queries = [
    ("sony headphones",        False),
    ("nike running shoes",     True),    # on sale pick
    ("apple airpods",          False),
    ("nike yoga mat",          False),
    ("logitech keyboard",      True),    # on sale pick
    ("sony camera",            False),
    ("nike jacket",            True),    # on sale pick
    ("mechanical keyboard",    False),
]

for query, on_sale in sim_queries:
    results = client.search.perform(query=query, limit=3)
    products = [p for p in (results.products or []) if p.offers]
    if products:
        persona = observe_pick(persona, products[0], was_on_sale=on_sale)
        brand = products[0].brands[0].name if products[0].brands else "?"
        offers = products[0].offers or []
        price  = min(o.price.price for o in offers) if offers else 0
        sale_tag = " [ON SALE]" if on_sale else ""
        print(f"  + {products[0].title[:45]:<45}  ${price:.0f}  {brand}{sale_tag}")

print_persona(persona, "AFTER 8 INTERACTIONS (auto-inferred)")

# ── 3. Explicit declarations ──────────────────────────────────────────────────
print("\n  Making explicit declarations...")

persona, msg = declare(persona, "brand_prefer", "Apple")
print(f"  declare brand_prefer Apple   → {msg}")

persona, msg = declare(persona, "brand_avoid", "Generic")
print(f"  declare brand_avoid Generic  → {msg}")

persona, msg = declare(persona, "size", "shoes_us", "11")
print(f"  declare size shoes_us 11     → {msg}")

persona, msg = declare(persona, "size", "shirt", "L")
print(f"  declare size shirt L         → {msg}")

persona, msg = declare(persona, "tier", "premium")
print(f"  declare tier premium         → {msg}")

print_persona(persona, "AFTER EXPLICIT DECLARATIONS")

# ── 4. Personalized vs generic ranking ───────────────────────────────────────
print("\n  Running personalized vs generic ranking for 'wireless headphones'...")
results = client.search.perform(query="wireless headphones", limit=8)
products = [p for p in (results.products or []) if p.offers]

generic_ranking    = rank_products(products, query="wireless headphones")
personalized_ranking = rank_products(products, query="wireless headphones", persona=persona)

print("\n  GENERIC ranking:         vs   PERSONALIZED ranking:")
print(f"  {'─'*35}      {'─'*35}")
for g, p in zip(generic_ranking.ranked[:6], personalized_ranking.ranked[:6]):
    g_brand = next((pr.brands[0].name for pr in products if pr.id == g.product_id and pr.brands), "?")
    p_brand = next((pr.brands[0].name for pr in products if pr.id == p.product_id and pr.brands), "?")
    moved = ""
    # find original rank of personalized item in generic
    orig_rank = next((r.rank for r in generic_ranking.ranked if r.product_id == p.product_id), p.rank)
    if orig_rank > p.rank:
        moved = f" ▲{orig_rank - p.rank}"
    elif orig_rank < p.rank:
        moved = f" ▼{p.rank - orig_rank}"
    print(f"  #{g.rank} {g_brand:<10} {g.product_title[:20]:<20} {g.overall_score:.0f}  |  "
          f"#{p.rank} {p_brand:<10} {p.product_title[:20]:<20} {p.overall_score:.0f}{moved}")

print(f"\n  ↑ Apple/Sony/Nike products are boosted in personalized ranking")
print(f"  because persona has Apple preferred + Sony/Nike from interactions\n")
print("=" * 60)
