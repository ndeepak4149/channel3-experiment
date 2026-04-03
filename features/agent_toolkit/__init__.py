"""
Feature 7: Agent Decision Toolkit
====================================
Single entry-point that orchestrates Features 1-6 into one API call.

Depth levels:
  quick    — search + value ranking only (~2s)
  standard — + deal intelligence + reviews (~10s)
  full     — + smart comparison + persona (~20s)

Usage:
    from features.agent_toolkit import decide

    result = decide(
        client       = channel3_client,
        intent       = "wireless headphones for the gym, under $150",
        depth        = "full",
        persona_id   = "user_deepak",   # optional
    )
    print(result.top_pick_title)
    print(result.top_pick_reasoning)
    print(result.purchase_confidence)
"""
from __future__ import annotations
from typing import Optional

from channel3_sdk import Channel3

from features.value_ranking import rank_products
from features.review_intelligence import get_review_intelligence
from features.deal_intelligence import get_deal_intelligence
from features.comparison import compare
from features.persona import get_persona, observe_pick

from .models import AgentDecision
from .guidance import generate_guidance


def decide(
    client: Channel3,
    intent: str,
    depth: str = "standard",        # "quick" | "standard" | "full"
    persona_id: Optional[str] = None,
    max_products: int = 8,
) -> AgentDecision:
    """
    Full pipeline: search → rank → enrich → compare → guide.
    """
    depth = depth.lower()
    assert depth in ("quick", "standard", "full"), "depth must be quick/standard/full"

    # ── Load persona ──────────────────────────────────────────────────────────
    persona = None
    if persona_id:
        persona = get_persona(persona_id)

    # ── Step 1: Search Channel3 ───────────────────────────────────────────────
    results = client.search.perform(query=intent, limit=max_products)
    products = [p for p in (results.products or []) if p.offers]

    if not products:
        raise ValueError(f"No products found for intent: {intent!r}")

    # ── Step 2: Review intelligence (standard + full) ─────────────────────────
    review_map = {}
    if depth in ("standard", "full"):
        for p in products[:6]:
            brand = p.brands[0].name if p.brands else ""
            r = get_review_intelligence(p.id, p.title, brand)
            review_map[p.id] = r

    review_scores = {pid: r.aggregate_score for pid, r in review_map.items()}

    # ── Step 3: Value ranking (always) ────────────────────────────────────────
    ranked = rank_products(products, query=intent, review_scores=review_scores, persona=persona)

    top_vs      = ranked.ranked[0]
    runner_vs   = ranked.ranked[1] if len(ranked.ranked) > 1 else None
    alt_ids     = [vs.product_id for vs in ranked.ranked[1:4]]
    alt_titles  = [vs.product_title for vs in ranked.ranked[1:4]]

    top_product = next(p for p in products if p.id == top_vs.product_id)
    top_offers  = top_product.offers or []
    top_in_stock = [o for o in top_offers if o.availability == "InStock"]
    top_best    = min((top_in_stock or top_offers), key=lambda o: o.price.price) if top_offers else None

    runner_product = next((p for p in products if p.id == runner_vs.product_id), None) if runner_vs else None
    runner_offers  = runner_product.offers or [] if runner_product else []
    runner_in_stock = [o for o in runner_offers if o.availability == "InStock"]
    runner_best = min((runner_in_stock or runner_offers), key=lambda o: o.price.price) if runner_offers else None

    # ── Step 4: Deal intelligence (standard + full) ───────────────────────────
    deal_map = {}
    if depth in ("standard", "full"):
        top_deal = get_deal_intelligence(client, top_product)
        deal_map[top_vs.product_id] = top_deal
        if runner_product:
            deal_map[runner_vs.product_id] = get_deal_intelligence(client, runner_product)

    # ── Step 5: Smart comparison (full only) ──────────────────────────────────
    comparison_result = None
    if depth == "full" and len(products) >= 2:
        compare_ids = [top_vs.product_id] + alt_ids[:2]
        comparison_result = compare(client, compare_ids)

    # ── Step 6: Generate agent guidance ──────────────────────────────────────
    top_review_score = review_map.get(top_vs.product_id)
    review_score_val = top_review_score.aggregate_score if top_review_score else 50

    top_deal = deal_map.get(top_vs.product_id)
    deal_rec = top_deal.recommendation if top_deal else "unknown"

    guidance = generate_guidance(
        intent          = intent,
        top_pick_title  = top_vs.product_title,
        top_pick_price  = top_best.price.price if top_best else 0,
        top_pick_score  = top_vs.overall_score,
        review_score    = review_score_val,
        deal_rec        = deal_rec,
        runner_up_title = runner_vs.product_title if runner_vs else "N/A",
        runner_up_price = runner_best.price.price if runner_best else 0,
    )

    # ── Build offers map for all ranked products ──────────────────────────────
    product_offers: dict = {}
    for p in products:
        offers = p.offers or []
        in_stock = [o for o in offers if o.availability == "InStock"]
        best = min((in_stock or offers), key=lambda o: o.price.price) if offers else None
        if best:
            product_offers[p.id] = {
                "price":    best.price.price,
                "retailer": best.domain,
                "url":      best.url,
            }

    # ── Step 7: Update persona from top pick (if persona loaded) ──────────────
    if persona and persona_id:
        was_on_sale = bool(top_best and top_best.price.compare_at_price)
        observe_pick(persona, top_product, was_on_sale=was_on_sale)

    # ── Assemble result ───────────────────────────────────────────────────────
    return AgentDecision(
        intent               = intent,
        depth                = depth,
        top_pick_id          = top_vs.product_id,
        top_pick_title       = top_vs.product_title,
        top_pick_price       = top_best.price.price if top_best else None,
        top_pick_retailer    = top_best.domain if top_best else None,
        top_pick_url         = top_best.url if top_best else None,
        top_pick_reasoning   = guidance.get("top_pick_reasoning", ""),
        alternative_ids      = alt_ids,
        alternative_titles   = alt_titles,
        product_offers       = product_offers,
        value_scores         = {vs.product_id: vs for vs in ranked.ranked},
        reviews              = review_map,
        deals                = deal_map,
        comparison           = comparison_result,
        follow_up_questions  = guidance.get("follow_up_questions", []),
        objection_handling   = guidance.get("objection_handling", {}),
        purchase_confidence  = guidance.get("purchase_confidence", 0.5),
        persona_id           = persona_id,
        persona_applied      = persona is not None,
    )
