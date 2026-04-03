"""
Pass raw review snippets through Claude to extract structured intelligence.
"""
from __future__ import annotations
from typing import List

from features.llm_utils import get_anthropic_client, clean_and_parse_json, CLAUDE_HAIKU_MODEL


SYSTEM_SNIPPET = """You are a product review analyst. Given review snippets from various sources, extract structured intelligence. Be objective and base everything strictly on the provided snippets.

Respond ONLY with valid JSON:
{
  "aggregate_score": <int 0-100>,
  "consensus_summary": "<3-5 sentences of what reviewers broadly agree on>",
  "pros": ["<pro>", ...],
  "cons": ["<con>", ...],
  "red_flags": ["<serious recurring complaint>", ...],
  "source_sentiments": [<float -1.0 to 1.0 per snippet, same order>],
  "confidence": <float 0-1>
}
Rules: aggregate_score 0=hated 50=mixed 100=loved. pros/cons each ≤15 words, deduplicated. red_flags only genuine recurring issues, [] if none. confidence low (0.1-0.3) if snippets vague/few, high (0.7-1.0) if many specific."""

SYSTEM_KNOWLEDGE = """You are a product review analyst with broad knowledge of consumer products. When no web snippets are available, use your training knowledge to provide accurate review intelligence for the product.

Respond ONLY with valid JSON:
{
  "aggregate_score": <int 0-100>,
  "consensus_summary": "<3-5 sentences summarising the general consensus about this product>",
  "pros": ["<pro>", ...],
  "cons": ["<con>", ...],
  "red_flags": ["<serious recurring complaint>", ...],
  "source_sentiments": [],
  "confidence": <float 0-1>
}
Rules: aggregate_score 0=hated 50=mixed 100=loved. pros/cons each ≤15 words, deduplicated. red_flags only genuine issues, [] if none. confidence: 0.3-0.5 for niche/obscure products, 0.5-0.8 for well-known products. Be honest — if you don't know the product well, say so in summary and set confidence low."""


def _call_claude(system: str, user_message: str) -> dict:
    client = get_anthropic_client()
    message = client.messages.create(
        model=CLAUDE_HAIKU_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return clean_and_parse_json(message.content[0].text)


def extract_review_intelligence(
    product_title: str,
    brand: str,
    snippets: List[dict],
) -> dict:
    """
    Call Claude with snippets if available, otherwise fall back to knowledge mode.
    """
    if snippets:
        snippet_text = "\n\n".join(
            f"[{i+1}] Source: {s['platform']} | URL: {s['url']}\n{s['snippet']}"
            for i, s in enumerate(snippets)
        )
        user_message = (
            f"Product: {product_title}\nBrand: {brand or 'Unknown'}\n"
            f"Snippets: {len(snippets)}\n\n--- SNIPPETS ---\n{snippet_text}\n--- END ---\n\n"
            "Extract review intelligence as JSON."
        )
        return _call_claude(SYSTEM_SNIPPET, user_message)
    else:
        user_message = (
            f"Product: {product_title}\nBrand: {brand or 'Unknown'}\n\n"
            "No web snippets were fetched. Use your training knowledge to provide "
            "review intelligence for this product as JSON."
        )
        return _call_claude(SYSTEM_KNOWLEDGE, user_message)
