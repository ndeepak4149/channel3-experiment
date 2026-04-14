"""
Channel4 FastAPI Backend
========================
Wraps all 7 features as REST endpoints.
Deploy to Railway — set CHANNEL3_API_KEY and ANTHROPIC_API_KEY env vars.
"""
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from channel3_sdk import Channel3
from features.agent_toolkit import decide
from features.basket_optimizer import optimize_basket
from features.review_intelligence import get_review_intelligence
from features.deal_intelligence import get_deal_intelligence
from features.comparison import compare as run_compare
from features.value_ranking import rank_products
from features.persona import get_persona, declare, observe_pick

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Channel4 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_client() -> Channel3:
    key = os.getenv("CHANNEL3_API_KEY")
    if not key:
        raise HTTPException(500, "CHANNEL3_API_KEY not configured")
    return Channel3(api_key=key)


# ── Request/Response models ───────────────────────────────────────────────────

class DecideRequest(BaseModel):
    intent: str
    depth: str = "standard"        # quick | standard | full
    persona_id: Optional[str] = None
    previous_intent: Optional[str] = None  # last query in the chat session

class BasketRequest(BaseModel):
    queries: List[str]             # list of search queries, one per item

class CompareRequest(BaseModel):
    queries: List[str]             # 2-4 product search queries

class PersonaDeclareRequest(BaseModel):
    declaration_type: str          # brand_prefer | brand_avoid | size | tier | priority
    value: str
    extra: str = ""

class SearchRequest(BaseModel):
    query: str
    limit: int = 8


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Channel4 API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Feature 7: Agent Decision Toolkit ────────────────────────────────────────

@app.post("/api/decide")
def api_decide(req: DecideRequest):
    """
    Main endpoint — runs the full agent pipeline.
    Combines search → review → value rank → deal intel → comparison → guidance.
    """
    client = get_client()
    try:
        # Resolve full intent: if follow-up message, combine with previous context
        resolved_intent = req.intent
        if req.previous_intent and req.previous_intent.strip():
            resolved_intent = f"{req.previous_intent}, {req.intent}"

        result = decide(
            client     = client,
            intent     = resolved_intent,
            depth      = req.depth,
            persona_id = req.persona_id,
        )
        # Serialize — convert nested Pydantic models to dicts
        return {
            "intent":              result.intent,
            "depth":               result.depth,
            "top_pick": {
                "id":        result.top_pick_id,
                "title":     result.top_pick_title,
                "price":     result.top_pick_price,
                "retailer":  result.top_pick_retailer,
                "url":       result.top_pick_url,
                "reasoning": result.top_pick_reasoning,
            },
            "alternatives": [
                {
                    "id":       aid,
                    "title":    atitle,
                    "price":    result.product_offers.get(aid, {}).get("price"),
                    "retailer": result.product_offers.get(aid, {}).get("retailer"),
                    "url":      result.product_offers.get(aid, {}).get("url"),
                }
                for aid, atitle in zip(result.alternative_ids, result.alternative_titles)
            ],
            "product_offers": result.product_offers,
            "value_scores": {
                pid: {
                    "rank":          vs.rank,
                    "overall_score": vs.overall_score,
                    "value_tier":    vs.value_tier,
                    "one_liner":     vs.one_liner,
                    "breakdown":     vs.score_breakdown,
                }
                for pid, vs in result.value_scores.items()
            },
            "reviews": {
                pid: {
                    "aggregate_score":   r.aggregate_score,
                    "consensus_summary": r.consensus_summary,
                    "pros":              r.pros,
                    "cons":              r.cons,
                    "red_flags":         r.red_flags,
                    "confidence":        r.confidence,
                    "source_mode":       r.source_mode,
                }
                for pid, r in result.reviews.items()
            },
            "deals": {
                pid: {
                    "current_price":    d.current_price,
                    "recommendation":   d.recommendation,
                    "reasoning":        d.reasoning,
                    "discount_pct":     d.discount_pct,
                    "next_likely_sale": d.next_likely_sale,
                    "days_to_sale":     d.days_to_sale,
                    "confidence":       d.confidence,
                }
                for pid, d in result.deals.items()
            },
            "comparison": {
                "category":       result.comparison.category,
                "overall_winner": result.comparison.overall_winner,
                "runner_up":      result.comparison.runner_up,
                "summary":        result.comparison.summary,
                "best_for":       result.comparison.best_for,
                "axes": [
                    {
                        "axis":        ax.axis,
                        "ratings":     ax.ratings,
                        "winner":      ax.winner,
                        "explanation": ax.explanation,
                    }
                    for ax in result.comparison.axes
                ],
                "product_titles": result.comparison.product_titles,
            } if result.comparison else None,
            "follow_up_questions": result.follow_up_questions,
            "objection_handling":  result.objection_handling,
            "purchase_confidence": result.purchase_confidence,
            "persona_applied":     result.persona_applied,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 1: Review Intelligence ───────────────────────────────────────────

@app.get("/api/review/{product_id}")
def api_review(product_id: str, title: str = "", brand: str = ""):
    try:
        r = get_review_intelligence(product_id, title, brand)
        return {
            "product_id":        r.product_id,
            "aggregate_score":   r.aggregate_score,
            "consensus_summary": r.consensus_summary,
            "pros":              r.pros,
            "cons":              r.cons,
            "red_flags":         r.red_flags,
            "confidence":        r.confidence,
            "source_mode":       r.source_mode,
            "total_sources":     r.total_sources,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 2: Value Ranking ──────────────────────────────────────────────────

@app.post("/api/search")
def api_search(req: SearchRequest):
    client = get_client()
    try:
        results = client.search.perform(query=req.query, limit=req.limit)
        products = [p for p in (results.products or []) if p.offers]
        ranked = rank_products(products, query=req.query)
        return {
            "query":    req.query,
            "category_profile": ranked.category_profile,
            "products": [
                {
                    "id":       p.id,
                    "title":    p.title,
                    "brands":   [b.name for b in (p.brands or [])],
                    "images":   [img.url for img in (p.images or []) if img.url][:3],
                    "categories": (p.categories or [])[:2],
                    "offers": [
                        {
                            "domain":        o.domain,
                            "price":         o.price.price,
                            "compare_at":    o.price.compare_at_price,
                            "currency":      o.price.currency,
                            "url":           o.url,
                            "availability":  o.availability,
                        }
                        for o in (p.offers or [])
                    ],
                    "key_features": (p.key_features or [])[:5],
                    "value_score": next(
                        ({"rank": vs.rank, "score": vs.overall_score, "tier": vs.value_tier, "one_liner": vs.one_liner}
                         for vs in ranked.ranked if vs.product_id == p.id),
                        None
                    ),
                }
                for p in products
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 3: Smart Comparison ───────────────────────────────────────────────

@app.post("/api/compare")
def api_compare(req: CompareRequest):
    client = get_client()
    if len(req.queries) < 2:
        raise HTTPException(400, "Need at least 2 queries")
    try:
        # Search for one product per query
        product_ids = []
        for q in req.queries[:4]:
            results = client.search.perform(query=q, limit=3)
            products = [p for p in (results.products or []) if p.offers]
            if products:
                product_ids.append(products[0].id)

        if len(product_ids) < 2:
            raise HTTPException(400, "Could not find enough products")

        result = run_compare(client, product_ids)
        return {
            "category":       result.category,
            "overall_winner": result.overall_winner,
            "runner_up":      result.runner_up,
            "summary":        result.summary,
            "best_for":       result.best_for,
            "product_titles": result.product_titles,
            "axes": [
                {
                    "axis":        ax.axis,
                    "ratings":     ax.ratings,
                    "winner":      ax.winner,
                    "explanation": ax.explanation,
                }
                for ax in result.axes
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 4: Deal Intelligence ──────────────────────────────────────────────

@app.get("/api/deal/{product_id}")
def api_deal(product_id: str):
    client = get_client()
    try:
        product = client.products.retrieve(product_id)
        deal = get_deal_intelligence(client, product)
        return {
            "product_id":       deal.product_id,
            "product_title":    deal.product_title,
            "current_price":    deal.current_price,
            "recommendation":   deal.recommendation,
            "reasoning":        deal.reasoning,
            "discount_pct":     deal.discount_pct,
            "original_price":   deal.original_price,
            "price_percentile": deal.price_percentile,
            "all_time_low":     deal.all_time_low,
            "average_price_30d":deal.average_price_30d,
            "next_likely_sale": deal.next_likely_sale,
            "days_to_sale":     deal.days_to_sale,
            "confidence":       deal.confidence,
            "data_source":      deal.data_source,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 5: Basket Optimizer ───────────────────────────────────────────────

@app.post("/api/basket/optimize")
def api_basket(req: BasketRequest):
    client = get_client()
    if not req.queries:
        raise HTTPException(400, "No items in basket")
    try:
        products = []
        for q in req.queries[:12]:
            results = client.search.perform(query=q, limit=3)
            found = [p for p in (results.products or []) if p.offers]
            if found:
                products.append(found[0])

        if not products:
            raise HTTPException(400, "No products found for basket items")

        result = optimize_basket(products)
        return {
            "items": [
                {
                    "product_id":           it.product_id,
                    "product_title":        it.product_title,
                    "recommended_retailer": it.recommended_retailer,
                    "price":                it.price,
                    "discount_pct":         it.discount_pct,
                    "product_url":          it.product_url,
                    "availability":         it.availability,
                }
                for it in result.items
            ],
            "retailer_breakdown": {
                domain: {
                    "items":       s.items,
                    "subtotal":    s.subtotal,
                    "shipping":    s.shipping,
                    "order_total": s.order_total,
                    "note":        s.note,
                }
                for domain, s in result.retailer_breakdown.items()
            },
            "subtotal":                 result.subtotal,
            "total_shipping":           result.total_shipping,
            "total_cost":               result.total_cost,
            "cheapest_single_retailer": result.cheapest_single_retailer,
            "cheapest_single_total":    result.cheapest_single_total,
            "savings_vs_single":        result.savings_vs_single,
            "notes":                    result.notes,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Feature 6: Persona ────────────────────────────────────────────────────────

@app.get("/api/persona/{persona_id}")
def api_get_persona(persona_id: str):
    p = get_persona(persona_id)
    return {
        "persona_id":          p.persona_id,
        "price_tier":          p.price_tier,
        "deal_sensitivity":    p.deal_sensitivity,
        "value_priorities":    p.value_priorities,
        "preferred_brands":    p.preferred_brands,
        "avoided_brands":      p.avoided_brands,
        "category_affinities": p.category_affinities,
        "declared_sizes":      p.declared_sizes,
        "avg_spend_per_item":  p.avg_spend_per_item,
        "interaction_count":   p.interaction_count,
    }

@app.post("/api/persona/{persona_id}/declare")
def api_declare(persona_id: str, req: PersonaDeclareRequest):
    p = get_persona(persona_id)
    p, msg = declare(p, req.declaration_type, req.value, req.extra)
    return {"message": msg, "persona": {
        "price_tier":       p.price_tier,
        "preferred_brands": p.preferred_brands,
        "avoided_brands":   p.avoided_brands,
        "declared_sizes":   p.declared_sizes,
        "value_priorities": p.value_priorities,
    }}
