"""
╔══════════════════════════════════════════════════════════════╗
║              CHANNEL4 — AI SHOPPING ASSISTANT               ║
║   All 7 intelligence features in one conversational CLI     ║
╚══════════════════════════════════════════════════════════════╝

Commands:
  <shopping intent>         Full agent decision (standard depth)
  /quick  <intent>          Quick search + value rank only
  /full   <intent>          Full depth — all 7 features
  /basket                   Switch to basket optimizer mode
  /persona                  Show your current persona profile
  /compare <q1> vs <q2>     Compare two product searches
  /deal    <query>          Check deal timing for a product
  /depth   quick|standard|full   Set default depth
  /persona-id <id>          Switch persona (default: default_user)
  /help                     Show this help
  /quit                     Exit

Run: python channel4.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.agent_toolkit import decide
from features.basket_optimizer import optimize_basket
from features.persona import get_persona, declare
from features.deal_intelligence import get_deal_intelligence
from features.comparison import compare as run_compare

client      = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))
persona_id  = "default_user"
depth       = "standard"
basket      = []

REC_ICON  = {"buy_now": "🟢 BUY NOW", "good_deal": "✅ GOOD DEAL", "wait": "⏳ WAIT", "overpriced": "🔴 OVERPRICED"}
TIER_ICON = {"exceptional": "🏆", "good": "✅", "fair": "🟡", "overpriced": "🔴"}


# ── Renderers ─────────────────────────────────────────────────────────────────

def render_quick(result):
    conf_bar = "█" * int(result.purchase_confidence * 10) + "░" * (10 - int(result.purchase_confidence * 10))
    price    = f"${result.top_pick_price:.2f} @ {result.top_pick_retailer}" if result.top_pick_price else "N/A"
    print(f"\n  🎯 {result.top_pick_title}")
    print(f"     {price}  |  confidence [{conf_bar}] {result.purchase_confidence:.0%}")
    print(f"     {result.top_pick_reasoning}")
    if result.alternative_titles:
        print(f"\n  Also consider:")
        for t in result.alternative_titles[:2]:
            vs = next((v for v in result.value_scores.values() if v.product_title == t), None)
            score = f"{vs.overall_score:.0f}/100" if vs else ""
            print(f"    • {t[:55]}  {score}")
    print(f"\n  Questions to ask: {result.follow_up_questions[0] if result.follow_up_questions else '—'}")
    print(f"  Buy: {result.top_pick_url}")


def render_standard(result):
    render_quick(result)
    if result.deals:
        top_deal = result.deals.get(result.top_pick_id)
        if top_deal:
            icon = REC_ICON.get(top_deal.recommendation, "?")
            disc = f"  ({top_deal.discount_pct:.0f}% off)" if top_deal.discount_pct else ""
            sale = f"  — next sale: {top_deal.next_likely_sale}" if top_deal.next_likely_sale else ""
            print(f"\n  Deal: {icon}{disc}{sale}")
    if result.reviews:
        top_rev = result.reviews.get(result.top_pick_id)
        if top_rev and top_rev.pros:
            print(f"  Reviews ({top_rev.aggregate_score}/100): {' | '.join(top_rev.pros[:2])}")
            if top_rev.red_flags:
                print(f"  ⚠ Flag: {top_rev.red_flags[0]}")


def render_full(result):
    render_standard(result)
    if result.comparison:
        c = result.comparison
        winner = c.product_titles.get(c.overall_winner, "?")[:40]
        print(f"\n  Comparison winner: {winner}")
        for persona_key, pid in list(c.best_for.items())[:3]:
            label = persona_key.replace("_", " ").title()
            print(f"    {label:<26} → {c.product_titles.get(pid,'?')[:30]}")
    print(f"\n  Objections:")
    for k, v in list(result.objection_handling.items())[:2]:
        print(f"    [{k}] {v[:75]}")
    if result.persona_applied:
        print(f"\n  👤 Persona '{result.persona_id}' applied.")


def render_result(result):
    print()
    if result.depth == "quick":
        render_quick(result)
    elif result.depth == "standard":
        render_standard(result)
    else:
        render_full(result)
    print()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_basket():
    """Mini basket mode inline."""
    global basket
    print("\n  🛒 BASKET MODE  (type a product search, 'optimize' to run, 'done' to exit)\n")
    while True:
        try:
            raw = input("  basket > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw.lower() == "done":
            break
        if raw.lower() == "optimize":
            if not basket:
                print("  Basket is empty.")
                continue
            print(f"\n  Optimizing {len(basket)} items...")
            result = optimize_basket(basket)
            print(f"  Total: ${result.total_cost:.2f}  (shipping: ${result.total_shipping:.2f})")
            print(f"  Savings vs single retailer: ${result.savings_vs_single:.2f}")
            for domain, s in result.retailer_breakdown.items():
                ship = "free" if s.shipping == 0 else f"${s.shipping:.2f} shipping"
                print(f"  🏪 {domain}  ${s.subtotal:.2f} + {ship}  = ${s.order_total:.2f}")
            for item in result.items:
                print(f"    • {item.product_title[:50]}  ${item.price:.2f}")
                print(f"      {item.product_url}")
            if result.notes:
                for note in result.notes:
                    print(f"  💡 {note}")
            print()
        else:
            results = client.search.perform(query=raw, limit=4)
            products = [p for p in (results.products or []) if p.offers][:3]
            if not products:
                print("  No results.")
                continue
            for i, p in enumerate(products, 1):
                best = min(p.offers, key=lambda o: o.price.price)
                print(f"  [{i}] {p.title[:55]}  ${best.price.price:.2f} @ {best.domain}")
            try:
                choice = input("  Add [1-3 or Enter to skip]: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if choice.isdigit() and 1 <= int(choice) <= len(products):
                basket.append(products[int(choice)-1])
                print(f"  ✅ Added. Basket: {len(basket)} item{'s' if len(basket)!=1 else ''}")


def cmd_persona():
    p = get_persona(persona_id)
    print(f"\n  👤 PERSONA: {p.persona_id}")
    print(f"  Tier        : {p.price_tier.upper()}")
    print(f"  Priorities  : {' > '.join(p.value_priorities)}")
    print(f"  Deal sense  : {p.deal_sensitivity:.0%}")
    if p.preferred_brands:
        print(f"  Fav brands  : {', '.join(p.preferred_brands[:6])}")
    if p.avoided_brands:
        print(f"  Avoid       : {', '.join(p.avoided_brands)}")
    if p.declared_sizes:
        print(f"  Sizes       : {' '.join(f'{k}={v}' for k,v in p.declared_sizes.items())}")
    cats = sorted(p.category_affinities.items(), key=lambda x:-x[1])[:3]
    if cats:
        print(f"  Categories  : {' | '.join(f'{k} {v:.0%}' for k,v in cats)}")
    print(f"  Interactions: {p.interaction_count}")
    print()
    # Inline declaration
    print("  Declare preferences (or Enter to skip):")
    print("  Examples:  prefer Nike  |  avoid Generic  |  size shoes_us 10  |  tier premium")
    while True:
        try:
            raw = input("  persona > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        parts = raw.split()
        if parts[0] == "prefer" and len(parts) >= 2:
            p, msg = declare(p, "brand_prefer", " ".join(parts[1:]))
            print(f"  {msg}")
        elif parts[0] == "avoid" and len(parts) >= 2:
            p, msg = declare(p, "brand_avoid", " ".join(parts[1:]))
            print(f"  {msg}")
        elif parts[0] == "size" and len(parts) >= 3:
            p, msg = declare(p, "size", parts[1], parts[2])
            print(f"  {msg}")
        elif parts[0] == "tier" and len(parts) >= 2:
            p, msg = declare(p, "tier", parts[1])
            print(f"  {msg}")
        else:
            print("  Unrecognised. Try: prefer Nike | avoid X | size shoes_us 10 | tier premium")


def cmd_deal(query):
    results = client.search.perform(query=query, limit=3)
    products = [p for p in (results.products or []) if p.offers]
    if not products:
        print("  No products found.")
        return
    p = products[0]
    deal = get_deal_intelligence(client, p)
    icon = REC_ICON.get(deal.recommendation, "?")
    print(f"\n  {p.title[:60]}")
    print(f"  {icon}  ${deal.current_price:.2f}")
    print(f"  {deal.reasoning}")
    if deal.next_likely_sale:
        print(f"  Next sale: {deal.next_likely_sale} ({deal.days_to_sale} days)")
    print()


def cmd_compare(raw):
    if " vs " not in raw.lower():
        print("  Format: /compare <query1> vs <query2>")
        return
    parts = raw.lower().split(" vs ", 1)
    q1, q2 = parts[0].strip(), parts[1].strip()
    r1 = client.search.perform(query=q1, limit=3)
    r2 = client.search.perform(query=q2, limit=3)
    p1 = next((p for p in (r1.products or []) if p.offers), None)
    p2 = next((p for p in (r2.products or []) if p.offers), None)
    if not p1 or not p2:
        print("  Could not find both products.")
        return
    print(f"\n  Comparing: {p1.title[:40]} vs {p2.title[:40]}")
    result = run_compare(client, [p1.id, p2.id])
    winner = result.product_titles.get(result.overall_winner, "?")
    print(f"  Winner  : {winner}")
    print(f"  Summary : {result.summary}")
    for ax in result.axes[:4]:
        w = result.product_titles.get(ax.winner, "?")[:30]
        print(f"  {ax.axis:<24} → {w}")
    print()


# ── Main REPL ─────────────────────────────────────────────────────────────────

def print_header():
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              CHANNEL4 — AI SHOPPING ASSISTANT              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Persona: {persona_id}  |  Depth: {depth}  |  Type /help for commands\n")


def run():
    global persona_id, depth
    print_header()

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not raw:
            continue

        low = raw.lower()

        if low in ("quit", "exit", "/quit", "/exit"):
            print("  Goodbye!")
            break
        elif low in ("/help", "help"):
            print(__doc__)
        elif low == "/basket":
            cmd_basket()
        elif low == "/persona":
            cmd_persona()
        elif low.startswith("/persona-id "):
            persona_id = raw.split(None, 1)[1].strip()
            print(f"  Persona switched to '{persona_id}'")
        elif low.startswith("/depth "):
            d = raw.split(None, 1)[1].strip().lower()
            if d in ("quick", "standard", "full"):
                depth = d
                print(f"  Default depth set to '{depth}'")
            else:
                print("  Use: /depth quick | standard | full")
        elif low.startswith("/deal "):
            cmd_deal(raw[6:].strip())
        elif low.startswith("/compare "):
            cmd_compare(raw[9:].strip())
        elif low.startswith("/quick "):
            intent = raw[7:].strip()
            print(f"  Searching for '{intent}' (quick)...")
            try:
                result = decide(client, intent, depth="quick", persona_id=persona_id)
                render_result(result)
            except Exception as e:
                print(f"  Error: {e}")
        elif low.startswith("/full "):
            intent = raw[6:].strip()
            print(f"  Searching for '{intent}' (full — may take ~20s)...")
            try:
                result = decide(client, intent, depth="full", persona_id=persona_id)
                render_result(result)
            except Exception as e:
                print(f"  Error: {e}")
        else:
            # Default: treat as shopping intent
            print(f"  Searching [{depth}]...")
            try:
                result = decide(client, raw, depth=depth, persona_id=persona_id)
                render_result(result)
            except Exception as e:
                print(f"  Error: {e}")


if __name__ == "__main__":
    run()
