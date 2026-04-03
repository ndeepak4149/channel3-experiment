"""
Gather review snippets for a product from multiple sources.
Uses DuckDuckGo's HTML search endpoint via httpx — no API key required.
"""
from __future__ import annotations
import re
import time
from typing import List
import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

DDG_URL = "https://html.duckduckgo.com/html/"

QUERY_TEMPLATES = [
    ("reddit",    "{name} {brand} review reddit",                          4),
    ("reddit",    "{name} worth it site:reddit.com",                       3),
    ("retailer",  "{name} {brand} customer reviews",                       3),
    ("editorial", "{name} {brand} review site:wirecutter.com OR site:rtings.com OR site:techradar.com", 2),
]


def _ddg_search(query: str, max_results: int = 5) -> List[dict]:
    """Hit DuckDuckGo HTML endpoint and extract result snippets."""
    try:
        resp = httpx.post(
            DDG_URL,
            data={"q": query, "b": "", "kl": "us-en"},
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception:
        return []

    html = resp.text
    results = []

    # Extract result blocks: each has a link and a snippet
    # DuckDuckGo HTML has <a class="result__a" href="..."> and <a class="result__snippet">
    links   = re.findall(r'class="result__a"[^>]*href="([^"]+)"', html)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for url, snippet in zip(links, snippets):
        if len(results) >= max_results:
            break
        # Skip DuckDuckGo ad/tracking redirect URLs
        if "duckduckgo.com" in url or "y.js" in url:
            continue
        # Clean HTML tags and entities from snippet
        clean = re.sub(r"<[^>]+>", "", snippet).strip()
        clean = re.sub(r"&#x27;", "'", clean)
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"&[a-z]+;", " ", clean)
        clean = re.sub(r"\s+", " ", clean)
        if url and clean:
            results.append({"url": url, "snippet": clean[:600]})

    return results


def fetch_review_snippets(
    product_title: str,
    brand: str = "",
    max_sources: int = 12,
) -> List[dict]:
    """
    Search for review content and return a list of dicts:
      { platform, url, snippet }
    """
    results: List[dict] = []
    seen_urls: set = set()

    for platform, template, n in QUERY_TEMPLATES:
        if len(results) >= max_sources:
            break

        query = template.format(name=product_title, brand=brand).strip()
        hits = _ddg_search(query, max_results=n)
        time.sleep(0.5)  # polite delay between queries

        for hit in hits:
            url = hit.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append({
                "platform": platform,
                "url": url,
                "snippet": hit["snippet"],
            })
            if len(results) >= max_sources:
                break

    return results
