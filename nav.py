"""Navigation structure: pages grouped by what the player wants to do (pure data, tested)."""
from __future__ import annotations

from typing import Dict, List, Tuple

# group key -> (label, [(page key, bootstrap icon), ...]); labels for pages live in strings.py ("nav_<key>")
GROUPS: List[Tuple[str, str, List[Tuple[str, str]]]] = [
    ("home", "🏠 Home", [("overview", "house"), ("weekly", "calendar-week"), ("playnow", "lightning-charge")]),
    ("habits", "🧠 Habits", [("behavior", "activity"), ("ledger", "cash-coin"), ("time", "stopwatch"), ("clock", "clock-history")]),
    ("chess", "♟️ Chess", [("openingcheck", "book"), ("blindspots", "bullseye"), ("spatial", "grid-3x3-gap"), ("coach", "cpu"), ("engine", "motherboard")]),
    ("growth", "📈 Growth", [("progress", "graph-up"), ("plan", "calendar-check"), ("compare", "people"), ("methodology", "info-circle")]),
]


def group_labels() -> Dict[str, str]:
    """Display label -> group key."""
    return {label: key for key, label, _ in GROUPS}


def pages_of(group_key: str) -> List[Tuple[str, str]]:
    return next(pages for key, _, pages in GROUPS if key == group_key)


def all_pages() -> List[str]:
    return [p for _, _, pages in GROUPS for p, _ in pages]


def group_of(page: str) -> str:
    return next(key for key, _, pages in GROUPS if any(p == page for p, _ in pages))
