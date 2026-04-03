"""
╔══════════════════════════════════════════════════════════╗
║         CHANNEL4 — BASKET OPTIMIZER MODE                ║
║  Add items, then let the engine find the cheapest split  ║
╚══════════════════════════════════════════════════════════╝

Run: python basket_mode.py

Commands:
  <search query>   Search and add a product to your basket
  list             Show current basket
  remove <n>       Remove item #n from basket
  optimize         Run the cross-retailer optimizer
  clear            Empty the basket
  quit / exit      Exit
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from channel3_sdk import Channel3
from features.basket_optimizer import optimize_basket

client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"))

basket: list = []   # list of ProductDetail objects


# ── Display helpers ───────────────────────────────────────────────────────────

def print_header():
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║         CHANNEL4 — BASKET OPTIMIZER MODE                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("  Add items with a search query, then type 'optimize'\n")


def print_basket():
    if not basket:
        print("  🛒  Basket is empty.")
        return
    print(f"\n  🛒  Basket ({len(basket)} item{'s' if len(basket) != 1 else ''}):")
    print(f"  {'#':<3} {'PRODUCT':<45} {'BEST PRICE'}")
    print(f"  {'─'*3} {'─'*45} {'─'*12}")
    for i, p in enumerate(basket, 1):
        offers  = p.offers or []
        in_stock = [o for o in offers if o.availability == "InStock"]
        pool     = in_stock or offers
        best     = min(pool, key=lambda o: o.price.price) if pool else None
        price    = f"${best.price.price:.2f} @ {best.domain}" if best else "N/A"
        print(f"  {i:<3} {p.title[:45]:<45} {price}")
    print()


def print_search_results(products: list) -> list:
    print(f"\n  Found {len(products)} result{'s' if len(products) != 1 else ''}:\n")
    for i, p in enumerate(products, 1):
        offers   = p.offers or []
        in_stock = [o for o in offers if o.availability == "InStock"]
        pool     = in_stock or offers
        best     = min(pool, key=lambda o: o.price.price) if pool else None
        price    = f"${best.price.price:.2f} @ {best.domain}" if best else "N/A"
        retailers = len(set(o.domain for o in offers))
        print(f"  [{i}] {p.title[:55]}")
        print(f"       {price}  |  {retailers} retailer{'s' if retailers != 1 else ''}")
    return products


def print_optimization(result):
    print("\n" + "═" * 64)
    print("  BASKET OPTIMIZATION RESULT")
    print("═" * 64)

    # Per-retailer breakdown
    for domain, summary in result.retailer_breakdown.items():
        ship_str = f"${summary.shipping:.2f} shipping" if summary.shipping > 0 else "free shipping"
        print(f"\n  🏪  {domain}")
        for item_title in summary.items:
            # Find the matching basket item for price
            match = next((it for it in result.items if it.product_title[:50] == item_title[:50]), None)
            price_str = f"${match.price:.2f}" if match else ""
            disc_str  = f"  ({match.discount_pct:.0f}% off)" if match and match.discount_pct else ""
            print(f"       • {item_title[:50]}  {price_str}{disc_str}")
        print(f"       Subtotal: ${summary.subtotal:.2f}  +  {ship_str}  =  ${summary.order_total:.2f}")
        if summary.note:
            print(f"       💡 {summary.note}")

    # Totals
    print(f"\n  {'─'*62}")
    print(f"  Items subtotal : ${result.subtotal:.2f}")
    print(f"  Total shipping : ${result.total_shipping:.2f}")
    print(f"  TOTAL COST     : ${result.total_cost:.2f}")
    print(f"  {'─'*62}")
    print(f"  Cheapest single retailer ({result.cheapest_single_retailer}): ${result.cheapest_single_total:.2f}")
    if result.savings_vs_single > 0:
        print(f"  💰 You save    : ${result.savings_vs_single:.2f} by splitting across retailers")
    else:
        print(f"  ✅ Single retailer is already optimal for this basket")

    # Buy links
    print(f"\n  {'─'*62}")
    print("  BUY LINKS:")
    for item in result.items:
        disc = f"  [{item.discount_pct:.0f}% off]" if item.discount_pct else ""
        print(f"  • {item.product_title[:42]:<44} ${item.price:.2f}{disc}")
        print(f"    {item.product_url}")

    # Notes
    if result.notes:
        print(f"\n  {'─'*62}")
        print("  TIPS:")
        for note in result.notes:
            print(f"  💡 {note}")

    print("═" * 64)


# ── Main REPL ─────────────────────────────────────────────────────────────────

def run():
    print_header()

    while True:
        try:
            raw = input("  basket > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not raw:
            continue

        cmd = raw.lower()

        # ── quit ──────────────────────────────────────────────────────────────
        if cmd in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        # ── list ──────────────────────────────────────────────────────────────
        elif cmd == "list":
            print_basket()

        # ── clear ─────────────────────────────────────────────────────────────
        elif cmd == "clear":
            basket.clear()
            print("  🗑  Basket cleared.")

        # ── remove <n> ────────────────────────────────────────────────────────
        elif cmd.startswith("remove "):
            try:
                idx = int(cmd.split()[1]) - 1
                removed = basket.pop(idx)
                print(f"  Removed: {removed.title[:55]}")
            except (IndexError, ValueError):
                print("  Usage: remove <item number>  e.g. remove 2")

        # ── optimize ──────────────────────────────────────────────────────────
        elif cmd == "optimize":
            if len(basket) < 1:
                print("  Add at least 1 item first.")
                continue
            print(f"\n  ⚙️  Optimizing {len(basket)} item basket across all retailers...")
            try:
                result = optimize_basket(basket)
                print_optimization(result)
            except Exception as e:
                print(f"  Error during optimization: {e}")

        # ── help ──────────────────────────────────────────────────────────────
        elif cmd in ("help", "?"):
            print(__doc__)

        # ── search ────────────────────────────────────────────────────────────
        else:
            print(f"\n  🔍 Searching for '{raw}'...")
            try:
                results = client.search.perform(query=raw, limit=5)
                products = [p for p in (results.products or []) if p.offers]
                if not products:
                    print("  No results found. Try a different query.")
                    continue

                search_results = print_search_results(products)

                try:
                    choice = input("  Add to basket [1-5, or Enter to skip]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not choice:
                    continue

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(search_results):
                        selected = search_results[idx]
                        basket.append(selected)
                        print(f"  ✅ Added: {selected.title[:55]}")
                        print_basket()
                    else:
                        print("  Invalid choice.")
                except ValueError:
                    print("  Invalid choice.")

            except Exception as e:
                print(f"  Search error: {e}")


if __name__ == "__main__":
    run()
