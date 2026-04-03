"""
Demo: Feature 7 — Agent Decision Toolkit
==========================================
Shows all three depth levels on real shopping intents.

Run: python demo_agent_toolkit.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.agent_toolkit import decide

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

CONFIDENCE_BAR = lambda c: "█" * int(c * 10) + "░" * (10 - int(c * 10))
REC_ICON = {"buy_now": "🟢", "good_deal": "✅", "wait": "⏳", "overpriced": "🔴"}
TIER_ICON = {"exceptional": "🏆", "good": "✅", "fair": "🟡", "overpriced": "🔴"}

def print_decision(result, show_full=True):
    conf = result.purchase_confidence
    print(f"\n{'═'*68}")
    print(f"  AGENT DECISION  [{result.depth.upper()}]")
    print(f"{'═'*68}")

    # Top pick
    price_str = f"${result.top_pick_price:.2f} @ {result.top_pick_retailer}" if result.top_pick_price else "N/A"
    print(f"\n  🎯  TOP PICK")
    print(f"  {result.top_pick_title}")
    print(f"  Price     : {price_str}")
    print(f"  Reasoning : {result.top_pick_reasoning}")
    print(f"  Confidence: [{CONFIDENCE_BAR(conf)}] {conf:.0%}")

    # Alternatives
    if result.alternative_titles:
        print(f"\n  📋  ALTERNATIVES")
        for i, (aid, atitle) in enumerate(zip(result.alternative_ids, result.alternative_titles), 1):
            vs = result.value_scores.get(aid)
            score_str = f"{vs.overall_score:.0f}/100 {TIER_ICON.get(vs.value_tier,'')}" if vs else ""
            print(f"  {i}. {atitle[:55]}  {score_str}")

    # Value scores for top 4
    print(f"\n  📊  VALUE SCORES")
    sorted_scores = sorted(result.value_scores.values(), key=lambda v: v.rank)
    for vs in sorted_scores[:4]:
        marker = "◀ top pick" if vs.product_id == result.top_pick_id else ""
        icon   = TIER_ICON.get(vs.value_tier, "")
        print(f"  #{vs.rank} {icon} {vs.overall_score:>4.0f}/100  {vs.product_title[:45]}  {marker}")

    # Reviews
    if result.reviews:
        print(f"\n  ⭐  REVIEWS")
        for pid, r in list(result.reviews.items())[:3]:
            marker = " ◀ top pick" if pid == result.top_pick_id else ""
            bar = "█" * (r.aggregate_score // 10) + "░" * (10 - r.aggregate_score // 10)
            print(f"  [{bar}] {r.aggregate_score}/100  {r.product_title[:40]}{marker}")
            if pid == result.top_pick_id and r.pros:
                print(f"    + {' | '.join(r.pros[:2])}")
            if pid == result.top_pick_id and r.cons:
                print(f"    - {r.cons[0]}")

    # Deal intelligence
    if result.deals:
        print(f"\n  💰  DEAL STATUS")
        for pid, d in result.deals.items():
            marker = " ◀ top pick" if pid == result.top_pick_id else ""
            icon = REC_ICON.get(d.recommendation, "?")
            disc = f"  ({d.discount_pct:.0f}% off)" if d.discount_pct else ""
            sale = f"  — {d.next_likely_sale} in {d.days_to_sale}d" if d.next_likely_sale else ""
            print(f"  {icon} {d.recommendation.upper():<12} ${d.current_price:.2f}{disc}{sale}{marker}")

    # Comparison (full only)
    if result.comparison:
        c = result.comparison
        print(f"\n  🆚  COMPARISON  ({c.category})")
        winner_title = c.product_titles.get(c.overall_winner, "?")[:35]
        print(f"  Overall winner: {winner_title}")
        for ax in c.axes[:4]:
            winner_short = c.product_titles.get(ax.winner, "?")[:22]
            print(f"  {ax.axis:<24} → {winner_short}")
        if c.best_for:
            print(f"  Best for:")
            for persona, pid in list(c.best_for.items())[:3]:
                label = persona.replace("_", " ").title()
                print(f"    {label:<26} → {c.product_titles.get(pid,'?')[:30]}")

    # Agent guidance
    print(f"\n  🤖  AGENT GUIDANCE")
    print(f"  Follow-up questions:")
    for q in result.follow_up_questions[:3]:
        print(f"    • {q}")
    print(f"  Objection handling:")
    for obj, resp in list(result.objection_handling.items())[:3]:
        print(f"    [{obj}] {resp[:70]}")

    if result.persona_applied:
        print(f"\n  👤  Persona '{result.persona_id}' applied — results personalised.")

    print(f"\n  Buy URL: {result.top_pick_url}")
    print(f"{'═'*68}")


# ── Test 1: QUICK depth ───────────────────────────────────────────────────────
print("\n" + "━"*68)
print("  TEST 1 — QUICK depth  (search + value rank only)")
print("━"*68)
r1 = decide(client, "yoga mat for beginners", depth="quick")
print_decision(r1)

# ── Test 2: STANDARD depth ────────────────────────────────────────────────────
print("\n" + "━"*68)
print("  TEST 2 — STANDARD depth  (+ reviews + deal intel)")
print("━"*68)
r2 = decide(client, "bluetooth speaker under $100 for outdoor use", depth="standard")
print_decision(r2)

# ── Test 3: FULL depth + persona ──────────────────────────────────────────────
print("\n" + "━"*68)
print("  TEST 3 — FULL depth + persona  (all 7 features)")
print("━"*68)
r3 = decide(
    client,
    intent     = "wireless noise-cancelling headphones for travel",
    depth      = "full",
    persona_id = "demo_user",
)
print_decision(r3)
