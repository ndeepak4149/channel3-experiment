"""
Sale event calendar — upcoming major retail sale events.
Used to inform buy/wait recommendations when price history is unavailable.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, Tuple

# (event_name, month, day_start, day_end)
# Approximate dates — some (Prime Day, Black Friday) vary year to year
SALE_EVENTS = [
    ("Amazon Prime Day",         7,  8,  9),
    ("Back to School Sales",     8,  1, 20),
    ("Labor Day Sales",          9,  1,  3),
    ("Amazon Fall Prime Day",   10, 14, 15),
    ("Black Friday",            11, 28, 30),
    ("Cyber Monday",            12,  2,  2),
    ("Holiday Sales",           12, 20, 26),
    ("New Year Sales",           1,  1,  5),
    ("Valentine's Day Sales",    2, 10, 14),
    ("Presidents Day Sales",     2, 17, 19),
    ("Spring Sales",             3, 15, 25),
    ("Memorial Day Sales",       5, 24, 27),
]

# Category → which events are most relevant
CATEGORY_SALE_MAP: dict[str, list[str]] = {
    "electronics":    ["Amazon Prime Day", "Amazon Fall Prime Day", "Black Friday", "Cyber Monday"],
    "fashion":        ["Black Friday", "Labor Day Sales", "New Year Sales", "Spring Sales"],
    "sports_fitness": ["New Year Sales", "Memorial Day Sales", "Labor Day Sales"],
    "health_beauty":  ["Black Friday", "Cyber Monday", "Valentine's Day Sales"],
    "furniture_home": ["Memorial Day Sales", "Labor Day Sales", "Black Friday"],
    "default":        ["Amazon Prime Day", "Black Friday", "Cyber Monday"],
}


def next_sale_event(
    category_profile: str = "default",
    reference_date: Optional[date] = None,
) -> Tuple[Optional[str], Optional[int]]:
    """
    Return (event_name, days_until) for the next relevant sale event.
    Returns (None, None) if nothing found within 120 days.
    """
    today = reference_date or date.today()
    relevant = CATEGORY_SALE_MAP.get(category_profile, CATEGORY_SALE_MAP["default"])

    best_name: Optional[str] = None
    best_days: Optional[int] = None

    for name, month, day_start, day_end in SALE_EVENTS:
        if name not in relevant:
            continue
        for year in [today.year, today.year + 1]:
            try:
                event_start = date(year, month, day_start)
            except ValueError:
                continue
            delta = (event_start - today).days
            if 0 <= delta <= 120:
                if best_days is None or delta < best_days:
                    best_days = delta
                    event_end = date(year, month, day_end)
                    best_name = f"{name} ({event_start.strftime('%b %-d')}–{event_end.strftime('%-d')})"
                break

    return best_name, best_days
