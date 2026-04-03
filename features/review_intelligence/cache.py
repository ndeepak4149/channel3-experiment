"""Simple JSON file cache for review results. TTL default: 48 hours."""
from __future__ import annotations
import json
import os
import time
from typing import Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "cache")
DEFAULT_TTL = 48 * 3600  # 48 hours


def _path(key: str) -> str:
    safe = key.replace("/", "_").replace(" ", "_")
    return os.path.join(CACHE_DIR, f"{safe}.json")


def get(key: str, ttl: int = DEFAULT_TTL) -> Optional[dict]:
    path = _path(key)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    if time.time() - data.get("_cached_at", 0) > ttl:
        os.remove(path)
        return None
    return data


def set(key: str, value: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    value["_cached_at"] = time.time()
    with open(_path(key), "w") as f:
        json.dump(value, f, indent=2, default=str)
