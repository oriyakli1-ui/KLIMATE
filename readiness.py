"""Play-Now check: should you start another game right now, judged by YOUR OWN history?

The current situation (idle time since the last game, game number in the session, losses in a
row, local hour) is compared with how you actually performed in the same situation before,
using the measured rating change per game and the score. A situation is only called good or bad
when the difference is statistically reliable; otherwise the check says there is not enough evidence.
Pure pandas, no Streamlit.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

import insights
from metrics import significantly_different

MIN_GAMES = 25


def current_state(g: pd.DataFrame, now: pd.Timestamp, timezone: str = "UTC") -> Dict[str, object]:
    """Where the player is right now, from the games already played."""
    if g.empty:
        return {"in_session": False, "minutes_since_last": None, "next_game_no": 1, "losses_in_row": 0, "hour": now.tz_convert(timezone).hour}
    last = g.sort_values("date_utc").iloc[-1]
    idle = (now - last["date_utc"]).total_seconds() / 60.0
    in_session = idle <= insights.SESSION_GAP_MINUTES
    if in_session:
        sess = g[g["session_id"] == last["session_id"]].sort_values("date_utc")
        losses = 0
        for outcome in reversed(sess["outcome"].tolist()):
            if outcome != "loss":
                break
            losses += 1
        next_no = int(last["session_game_no"]) + 1
    else:
        losses, next_no = 0, 1
    return {"in_session": in_session, "minutes_since_last": max(0.0, idle), "next_game_no": next_no,
            "losses_in_row": losses, "hour": now.tz_convert(timezone).hour,
            "last_result": str(last["outcome"]), "session_games": next_no - 1 if in_session else 0}


def _compare(g: pd.DataFrame, mask: pd.Series, label: str) -> Dict[str, object]:
    """Score and rating change inside vs outside a situation."""
    inside, outside = g[mask], g[~mask]
    res: Dict[str, object] = {"label": label, "n": len(inside), "enough": len(inside) >= MIN_GAMES and len(outside) >= MIN_GAMES}
    if not res["enough"]:
        return res
    s_in, s_out = float(inside["score"].mean()), float(outside["score"].mean())
    res.update(score_in=s_in, score_out=s_out, worse=bool(s_in < s_out and significantly_different(len(inside), s_in, len(outside), s_out, 2.0)),
               better=bool(s_in > s_out and significantly_different(len(inside), s_in, len(outside), s_out, 2.0)))
    d_in, d_out = inside["rating_change"].dropna(), outside["rating_change"].dropna()
    if len(d_in) >= MIN_GAMES and len(d_out) >= MIN_GAMES:
        res["points_in"], res["points_out"] = float(d_in.mean()), float(d_out.mean())
    return res


def assess(g: pd.DataFrame, state: Dict[str, object], timezone: str = "UTC") -> Dict[str, object]:
    """Traffic light plus the evidence lines behind it."""
    checks: List[Dict[str, object]] = []
    if state["losses_in_row"] >= 1:
        # the exact streak first; if history has too few such games, widen to shorter streaks
        for k in range(int(state["losses_in_row"]), 0, -1):
            check = _compare(g, g["losses_before"] >= k, f"games that followed {k}+ loss{'es' if k > 1 else ''} in a row")
            if check["enough"] or k == 1:
                checks.append(check)
                break
    if state["next_game_no"] >= 5:
        checks.append(_compare(g, g["session_game_no"] >= 5, "5th game or later in a session"))
    if state["next_game_no"] == 1:
        checks.append(_compare(g, g["session_game_no"] == 1, "first game of a session"))
    hour = g["start_utc"].fillna(g["date_utc"]).dt.tz_convert(timezone).dt.hour
    if 0 <= state["hour"] < 6:
        checks.append(_compare(g, (hour >= 0) & (hour < 6), "games started between 00:00 and 05:59"))

    judged = [c for c in checks if c["enough"]]
    if any(c.get("worse") for c in judged):
        light = "red"
    elif not checks:
        light = "green" if len(g) >= 2 * MIN_GAMES else "grey"
    elif not judged:
        light = "grey"
    else:
        light = "green"
    return {"light": light, "checks": checks}
