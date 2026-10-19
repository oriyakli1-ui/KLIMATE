"""Weekly report and habit-rule tracking (pure pandas, tested).

Compares the last 7 days with the 7 days before, from the enriched games frame, and measures how
well the player followed a personal rule such as "stop after N losses in a row".
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

DAY = pd.Timedelta(days=1)


def anchor_time(g: pd.DataFrame, now: pd.Timestamp) -> pd.Timestamp:
    """'Now' if the player was active in the last week, otherwise their most recent game (so the report is never empty)."""
    last = g["date_utc"].max()
    return now if (now - last) < 7 * DAY else last


def period_stats(p: pd.DataFrame) -> Dict[str, object]:
    if p.empty:
        return {"games": 0, "wins": 0, "draws": 0, "losses": 0, "score": float("nan"), "rating_change": 0.0, "minutes": 0.0,
                "sessions": 0, "longest_session": 0, "known_changes": 0}
    start = p["start_utc"].fillna(p["date_utc"])
    minutes = float(((p["date_utc"] - start).dt.total_seconds() / 60.0).clip(lower=0).sum())
    per_session = p.groupby("session_id").size()
    ch = p["rating_change"].dropna()
    return {"games": len(p), "wins": int((p["outcome"] == "win").sum()), "draws": int((p["outcome"] == "draw").sum()),
            "losses": int((p["outcome"] == "loss").sum()), "score": float(p["score"].mean()), "rating_change": float(ch.sum()),
            "minutes": minutes, "sessions": int(per_session.size), "longest_session": int(per_session.max()), "known_changes": len(ch)}


def weekly_report(g: pd.DataFrame, now: pd.Timestamp) -> Dict[str, object]:
    """This week (last 7 days up to the anchor) versus the week before."""
    if g.empty:
        return {"anchor": now, "this": period_stats(g), "previous": period_stats(g), "daily": pd.DataFrame()}
    end = anchor_time(g, now)
    this = g[(g["date_utc"] > end - 7 * DAY) & (g["date_utc"] <= end)]
    prev = g[(g["date_utc"] > end - 14 * DAY) & (g["date_utc"] <= end - 7 * DAY)]
    d = this.assign(day=this["date_utc"].dt.floor("D"))
    daily = (d.groupby("day").agg(games=("score", "size"), score=("score", "mean"), rating_change=("rating_change", "sum")).reset_index()
             if not d.empty else pd.DataFrame(columns=["day", "games", "score", "rating_change"]))
    return {"anchor": end, "this": period_stats(this), "previous": period_stats(prev), "daily": daily, "games_frame": this}


def rule_adherence(p: pd.DataFrame, n: int) -> Dict[str, object]:
    """How often the player stopped after ``n`` losses in a row (within a session) versus kept playing.

    A session 'reached the rule' when a streak of n losses happened; it 'continued' when another game
    was played after that. ``continued_games`` are the games played after the rule point.
    """
    if p.empty or n < 1:
        return {"reached": 0, "continued": 0, "stopped": 0, "adherence": float("nan"), "continued_games": p.iloc[0:0]}
    reached = continued = 0
    for _, s in p.groupby("session_id"):
        if ((s["losses_before"] + (s["outcome"] == "loss").astype(int)) >= n).any():
            reached += 1
            if (s["losses_before"] >= n).any():
                continued += 1
    cont = p[p["losses_before"] >= n]
    stopped = reached - continued
    return {"reached": reached, "continued": continued, "stopped": stopped,
            "adherence": stopped / reached if reached else float("nan"), "continued_games": cont}
