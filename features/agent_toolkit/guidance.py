"""
Claude call to generate agent guidance:
  - follow_up_questions
  - objection_handling
  - top_pick_reasoning
"""
from features.llm_utils import get_anthropic_client, clean_and_parse_json, CLAUDE_HAIKU_MODEL


SYSTEM = """You are a shopping assistant AI. Given a user's shopping intent and the top recommended product with its scores, generate concise agent guidance.

Respond ONLY with valid JSON:
{
  "top_pick_reasoning": "<1-2 sentences: why this is the best pick for this intent>",
  "follow_up_questions": ["<question 1>", "<question 2>", "<question 3>"],
  "objection_handling": {
    "too_expensive": "<response if user says it costs too much>",
    "unsure_of_brand": "<response if user doesn't know the brand>",
    "need_more_options": "<response if user wants alternatives>",
    "bad_reviews": "<response if user is worried about reviews>"
  },
  "purchase_confidence": <float 0.0-1.0>
}

Rules:
- top_pick_reasoning: specific to this product + intent, mention price/reviews/deal if relevant
- follow_up_questions: help clarify unresolved aspects of the intent (budget, use case, size, etc.)
- objection_handling: give concrete, product-specific responses — mention the runner-up as alternative
- purchase_confidence: 0.9+ if top pick has great reviews + good deal, 0.5-0.7 if mixed signals, <0.5 if uncertain"""


def generate_guidance(
    intent: str,
    top_pick_title: str,
    top_pick_price: float,
    top_pick_score: float,
    review_score: int,
    deal_rec: str,
    runner_up_title: str,
    runner_up_price: float,
) -> dict:
    user_msg = f"""Intent: {intent}

Top Pick: {top_pick_title}
Price: ${top_pick_price:.2f}
Value Score: {top_pick_score:.0f}/100
Review Score: {review_score}/100
Deal Status: {deal_rec}

Runner-up: {runner_up_title} (${runner_up_price:.2f})

Generate agent guidance JSON."""

    client = get_anthropic_client()
    msg = client.messages.create(
        model=CLAUDE_HAIKU_MODEL,
        max_tokens=800,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return clean_and_parse_json(msg.content[0].text)
