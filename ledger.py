"""Elo Ledger: what your habits actually cost or earn, in real Chess.com rating points.

Chess.com publishes each player's rating after every game, so the rating change caused by a
game is that rating minus the previous one in the same rating pool (computed in
``insights.enrich_games`` as ``rating_change``). That gives a measured (not modelled) rating
delta per game, which is then compared between situations
(after a loss, first game of a session, time scrambles, late at night, long sessions).

Pure pandas, no Streamlit. Every row reports sample sizes and a significance verdict;
"reliable" requires a stricter bar (z >= 2.5) because several situations are tested at once.
Differences describe association, not proof of cause.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

NIGHT_HOURS = (0, 6)         # local start hour in [0, 6)
RELIABLE_Z = 2.5

CONDITIONS: List[Tuple[str, str]] = [
    ("after_loss", "Games right after a loss (same session)"),
    ("first_game", "First game of a session"),
    ("late_session", "5th game or later in a session"),
    ("scramble", "Games that end in a time scramble"),
    ("night", "Games started between 00:00 and 05:59"),
]


def _masks(g: pd.DataFrame, timezone: str) -> Dict[str, pd.Series]:
    hour = g["start_utc"].fillna(g["date_utc"]).dt.tz_convert(timezone).dt.hour
    return {
        "after_loss": g["losses_before"] >= 1,
        "first_game": g["session_game_no"] == 1,
        "late_session": g["session_game_no"] >= 5,
        "scramble": g["scramble"].map(lambda x: x is True or x == 1.0 if x == x else False),
        "night": (hour >= NIGHT_HOURS[0]) & (hour < NIGHT_HOURS[1]),
    }


def _welch(a: np.ndarray, b: np.ndarray) -> Tuple[float, float]:
    """(z, standard error) of the difference of two means."""
    if len(a) < 2 or len(b) < 2:
        return 0.0, float("nan")
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return (float((a.mean() - b.mean()) / se) if se > 0 else 0.0), se


def ledger(g: pd.DataFrame, timezone: str = "UTC", min_games: int = 20) -> Dict[str, object]:
    """Ledger table plus headline numbers. ``g`` is the enriched frame."""
    d = g[g["rating_change"].notna()]
    summary = {
        "rated_games": int(g["rated"].sum()) if "rated" in g else 0,
        "usable_games": len(d),
        "net_points": float(d["rating_change"].sum()) if len(d) else 0.0,
        "mean_per_game": float(d["rating_change"].mean()) if len(d) else float("nan"),
    }
    rows = []
    masks = _masks(d, timezone) if len(d) else {}
    for key, label in CONDITIONS:
        if key not in masks:
            continue
        inside, outside = d[masks[key]]["rating_change"].to_numpy(), d[~masks[key]]["rating_change"].to_numpy()
        enough = len(inside) >= min_games and len(outside) >= min_games
        z, se = _welch(inside, outside) if enough else (0.0, float("nan"))
        diff = float(inside.mean() - outside.mean()) if enough else float("nan")
        rows.append({
            "key": key, "situation": label, "games": len(inside), "mean_in": float(inside.mean()) if len(inside) else float("nan"),
            "mean_out": float(outside.mean()) if len(outside) else float("nan"), "difference": diff,
            "points_vs_normal": diff * len(inside) if enough else float("nan"), "z": z,
            "diff_lo": diff - 1.96 * se if enough else float("nan"), "diff_hi": diff + 1.96 * se if enough else float("nan"),
            "reliable": bool(enough and abs(z) >= RELIABLE_Z), "enough": enough,
        })
    return {"summary": summary, "table": pd.DataFrame(rows)}
