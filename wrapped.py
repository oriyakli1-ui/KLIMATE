"""Numbers for the shareable 'Chess DNA' card. Every figure is a description of the player's data,
with the sample size shown, or an explicit 'not enough data' (nothing is rounded up to look good)."""
from __future__ import annotations

from typing import Dict

import pandas as pd

import insights
import style

MIN_OPENING_GAMES = 10
MIN_HOUR_GAMES = 10


def build_wrapped(g: pd.DataFrame, raw_games: pd.DataFrame, username: str, ratings: dict, timezone: str = "UTC") -> Dict[str, str]:
    summ = insights.overall_summary(g)

    peak = ratings.get("peak", "N/A")
    peak_class = ratings.get("peak_class", "")
    peak_txt = str(peak)
    peak_label = f"All-time peak · {peak_class}" if peak_class and peak != "N/A" else "All-time peak"

    wins = f"{summ['win_rate']:.0%} of {summ['n']} games" if summ.get("n") else "N/A"

    ops = insights.opening_summary(g, MIN_OPENING_GAMES)
    if ops.empty:
        opening = f"Not enough data ({MIN_OPENING_GAMES}+ games with one opening)"
    else:
        best = ops.sort_values("score", ascending=False).iloc[0]
        opening = f"{best['opening']} ({best['score']:.0%} over {int(best['games'])} games)"

    profile = insights.hourly_profile(g, timezone)
    bh = insights.best_hour(profile, MIN_HOUR_GAMES)
    prime = f"{bh['hour']:02d}:00 ({bh['score']:.0%} over {bh['games']} games)" if bh else "No clear prime time yet"

    gm = style.match_archetype(style.style_profile(raw_games, username))[0]
    return {
        "peak_rating": peak_txt, "peak_label": peak_label, "wins": wins, "best_opening": opening,
        "prime_time": prime, "gm_match": gm,
    }
