"""
Shared utilities for interacting with Large Language Models.
"""
from __future__ import annotations
import json
import os
import anthropic

# Centralized model name constant
CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_client: anthropic.Anthropic | None = None


def get_anthropic_client() -> anthropic.Anthropic:
    """
    Initializes and returns a singleton Anthropic client, ensuring the API key is set.
    """
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment. Please set it.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def clean_and_parse_json(raw_text: str) -> dict:
    """
    Extracts and parses a JSON object from a string, robustly handling surrounding text or markdown.
    """
    # Find the start of the JSON object
    json_start = raw_text.find('{')
    # Find the end of the JSON object
    json_end = raw_text.rfind('}')

    if json_start != -1 and json_end != -1 and json_end > json_start:
        json_str = raw_text[json_start:json_end + 1]
        return json.loads(json_str)
    else:
        raise ValueError("Could not find a valid JSON object in the response.")