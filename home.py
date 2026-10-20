"""Facts for the Home hero: where the player stands, the biggest leak and the biggest strength (pure, tested).

Every claim passes the same evidence gates as the rest of the app; with too little data a field is None
and the page says so instead of inventing something.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

import insights


def rating_headline(g: pd.DataFrame) -> Dict[str, object]:
    """Current rating of the most-played rated time class and its change over the last 30 days of data."""
    r = g[g["rated"] & g["rating_after"].notna()].sort_values("date_utc")
    if r.empty:
        return {}
    tc = r["time_class"].value_counts().index[0]
    pool = r[r["time_class"] == tc]
    now = float(pool["rating_after"].iloc[-1])
    cutoff = pool["date_utc"].iloc[-1] - pd.Timedelta(days=30)
    older = pool[pool["date_utc"] <= cutoff]
    change = now - float(older["rating_after"].iloc[-1]) if len(older) else float("nan")
    return {"time_class": tc, "rating": now, "change_30d": change, "games": int(len(pool)),
            "peak": float(pool["rating_after"].max())}


def biggest_leak(g: pd.DataFrame, ledger_table: Optional[pd.DataFrame]) -> Optional[Dict[str, str]]:
    """The costliest habit that is statistically reliable, from the ledger, else a gated behaviour insight."""
    if ledger_table is not None and not ledger_table.empty:
        bad = ledger_table[ledger_table["reliable"] & (ledger_table["difference"] < 0)].sort_values("points_vs_normal")
        if len(bad):
            r = bad.iloc[0]
            return {"title": str(r["situation"]), "detail": f"Costs you {abs(r['difference']):.2f} rating points per game "
                    f"({abs(r['points_vs_normal']):.0f} points over {int(r['games'])} games).", "where": "Elo Ledger"}
    for ins in insights.generate_insights(g):
        if ins["key"] in ("stop_loss", "scramble", "early_burn", "timeouts", "lower_rated", "warmup"):
            return {"title": str(ins["title"]), "detail": str(ins["detail"]), "where": "Behavior Lab"}
    return None


def biggest_strength(g: pd.DataFrame, timezone: str) -> Optional[Dict[str, str]]:
    """A reliable positive: a best hour or an opening whose interval lies above the player's overall score."""
    best = insights.best_hour(insights.hourly_profile(g, timezone))
    if best:
        return {"title": f"You play best around {best['hour']:02d}:00",
                "detail": f"Score {best['score']:.0%} over {best['games']} games versus {best['rest']:.0%} the rest of the day.",
                "where": "Cognitive Clock"}
    overall = insights.overall_summary(g)
    if overall.get("n", 0) >= 30:
        ops = insights.opening_summary(g, min_games=8)
        good = ops[ops["lo"] > overall["score"]]
        if len(good):
            r = good.sort_values("score", ascending=False).iloc[0]
            return {"title": f"Your {r['opening']} is a real weapon",
                    "detail": f"{r['score']:.0%} over {int(r['games'])} games, clearly above your overall {overall['score']:.0%}.",
                    "where": "Overview"}
    return None
