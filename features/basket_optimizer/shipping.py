"""
Shipping cost model for known retailers.
Structure: domain → {threshold: free_shipping_minimum, flat_rate: cost_if_below_threshold}
"""
from __future__ import annotations
from typing import Optional, Tuple

# Known retailer shipping policies
SHIPPING_DB: dict[str, dict] = {
    # Free shipping always
    "amazon.com":           {"threshold": 0,    "flat_rate": 0},
    "target.com":           {"threshold": 35,   "flat_rate": 5.99},
    "walmart.com":          {"threshold": 35,   "flat_rate": 5.99},
    "bestbuy.com":          {"threshold": 35,   "flat_rate": 5.99},
    "nordstrom.com":        {"threshold": 0,    "flat_rate": 0},
    "kohls.com":            {"threshold": 25,   "flat_rate": 8.95},
    "macys.com":            {"threshold": 25,   "flat_rate": 10.95},
    "zappos.com":           {"threshold": 0,    "flat_rate": 0},
    "nike.com":             {"threshold": 0,    "flat_rate": 0},
    "adidas.com":           {"threshold": 0,    "flat_rate": 0},
    "apple.com":            {"threshold": 0,    "flat_rate": 0},
    "newegg.com":           {"threshold": 35,   "flat_rate": 4.99},
    "costco.com":           {"threshold": 0,    "flat_rate": 0},
    "revolve.com":          {"threshold": 100,  "flat_rate": 9.95},
    "ssense.com":           {"threshold": 100,  "flat_rate": 15},
    "farfetch.com":         {"threshold": 200,  "flat_rate": 10},
    "sephora.com":          {"threshold": 35,   "flat_rate": 5.95},
    "ulta.com":             {"threshold": 35,   "flat_rate": 7.95},
    "adorama.com":          {"threshold": 49,   "flat_rate": 5.99},
    "bhphotovideo.com":     {"threshold": 0,    "flat_rate": 0},
    "staples.com":          {"threshold": 45,   "flat_rate": 4.99},
    "officedepot.com":      {"threshold": 45,   "flat_rate": 4.99},
    "wayfair.com":          {"threshold": 35,   "flat_rate": 4.99},
    "homedepot.com":        {"threshold": 45,   "flat_rate": 5.99},
    "lowes.com":            {"threshold": 45,   "flat_rate": 5.99},
    "sweetwater.com":       {"threshold": 49,   "flat_rate": 6.99},
    "guitarcenter.com":     {"threshold": 25,   "flat_rate": 6.99},
    "rei.com":              {"threshold": 50,   "flat_rate": 5.99},
    "dickssportinggoods.com": {"threshold": 49, "flat_rate": 6.99},
    "jomashop.com":         {"threshold": 100,  "flat_rate": 9.95},
}

DEFAULT_SHIPPING = {"threshold": 50, "flat_rate": 7.99}


def get_shipping_cost(domain: str, order_subtotal: float) -> Tuple[float, Optional[float], bool]:
    """
    Returns (shipping_cost, free_threshold, is_free).
    """
    policy = SHIPPING_DB.get(domain.lower(), DEFAULT_SHIPPING)
    threshold = policy["threshold"]
    flat_rate = policy["flat_rate"]

    if threshold == 0 or order_subtotal >= threshold:
        return 0.0, threshold if threshold > 0 else None, True
    else:
        return flat_rate, threshold, False


def gap_to_free_shipping(domain: str, current_subtotal: float) -> Optional[float]:
    """
    Returns how much more needs to be spent to unlock free shipping.
    Returns None if already free or no threshold known.
    """
    policy = SHIPPING_DB.get(domain.lower(), DEFAULT_SHIPPING)
    threshold = policy["threshold"]
    if threshold == 0 or current_subtotal >= threshold:
        return None
    return round(threshold - current_subtotal, 2)
