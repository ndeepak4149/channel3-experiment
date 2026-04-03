"""
Use Claude to generate a structured product comparison matrix.
Takes product data + review intelligence and outputs ComparisonAxis objects.
"""
from __future__ import annotations
from typing import List

from features.llm_utils import get_anthropic_client, clean_and_parse_json, CLAUDE_HAIKU_MODEL


SYSTEM_PROMPT = """You are a product comparison expert. Given structured data about 2-4 products (title, brand, price, key features, review intelligence), produce a detailed comparison.

Respond ONLY with valid JSON matching this exact schema:
{
  "category": "<product category, e.g. 'Wireless Headphones'>",
  "axes": [
    {
      "axis": "<comparison dimension, e.g. 'Sound Quality'>",
      "ratings": {"<product_id>": <float 0-10>, ...},
      "winner": "<product_id with highest rating>",
      "explanation": "<1 sentence explaining why the winner leads on this axis>"
    }
  ],
  "overall_winner": "<product_id>",
  "runner_up": "<product_id or null>",
  "summary": "<2-3 sentence overall comparison summary>",
  "best_for": {
    "<persona>": "<product_id>",
    ...
  }
}

Rules:
- Choose 4-6 axes most relevant to the product category (e.g. headphones: Sound Quality, Noise Cancellation, Battery Life, Comfort, Value, Build Quality)
- Ratings must be 0-10 floats, differentiated — avoid giving every product the same score on an axis
- best_for personas: pick 2-4 realistic buyer types (e.g. "budget_conscious", "audiophile", "commuter", "apple_ecosystem_user")
- base ratings on the key_features, review pros/cons, and price — be realistic and opinionated
- summary should be direct: "X wins overall but Y is the better budget pick" """


def compare_products(products_data: List[dict]) -> dict:
    """
    products_data: list of dicts with keys:
      product_id, title, brand, price, compare_at_price,
      key_features, categories, review_score, review_pros,
      review_cons, review_summary
    """
    # Format each product for the prompt
    blocks = []
    for p in products_data:
        discount = ""
        if p.get("compare_at_price") and p["compare_at_price"] > p.get("price", 0):
            pct = (p["compare_at_price"] - p["price"]) / p["compare_at_price"] * 100
            discount = f" (was ${p['compare_at_price']:.0f}, {pct:.0f}% off)"

        block = f"""--- Product ID: {p['product_id']} ---
Title   : {p['title']}
Brand   : {p.get('brand', 'N/A')}
Price   : ${p.get('price', 'N/A')}{discount}
Features: {', '.join(p.get('key_features', [])[:6]) or 'N/A'}
Review  : {p.get('review_score', 'N/A')}/100 — {p.get('review_summary', 'N/A')}
Pros    : {', '.join(p.get('review_pros', [])[:4]) or 'N/A'}
Cons    : {', '.join(p.get('review_cons', [])[:3]) or 'N/A'}"""
        blocks.append(block)

    user_message = (
        f"Compare these {len(products_data)} products and return JSON:\n\n"
        + "\n\n".join(blocks)
    )

    client = get_anthropic_client()
    message = client.messages.create(
        model=CLAUDE_HAIKU_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return clean_and_parse_json(message.content[0].text)
