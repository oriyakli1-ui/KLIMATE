"""Klimate Pro interest test ("fake door"): shows planned paid features and measures willingness to pay at three prices.

Nothing is sold and nothing is stored here; answers go out only as anonymous analytics events. Pure helpers, tested.
"""
from __future__ import annotations

import os
import random
from typing import Dict, List

PRICES = (5, 9, 15)          # USD per month, assigned at random per visitor
ANSWERS = {"yes": "I would pay this", "maybe": "Maybe, with changes", "no": "Not for me"}

FEATURES: List[Dict[str, str]] = [
    {"feature": "Dashboard, Elo Ledger, Play Now, Weekly Report", "free": "yes", "pro": "yes"},
    {"feature": "Stockfish Coach Report and Blunder Trainer", "free": "20 recent games", "pro": "unlimited, saved"},
    {"feature": "History depth", "free": "6 months", "pro": "24 months"},
    {"feature": "Opponent Scout", "free": "3 per day", "pro": "unlimited"},
    {"feature": "Weekly email digest and PDF report", "free": "no", "pro": "yes"},
]


def pick_price(rng: random.Random | None = None) -> int:
    return (rng or random).choice(PRICES)


def waitlist_url() -> str:
    """Optional link (for example a form) set by the owner in the environment; empty means none configured."""
    return os.environ.get("KLIMATE_WAITLIST_URL", "").strip()
