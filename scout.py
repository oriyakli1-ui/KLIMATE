"""Opponent Scout: a preparation sheet built from an opponent's public games.

Streamlit-free. Every claim is gated by sample size and an interval, in the same way as the rest of
the app: with too little data the sheet says so instead of guessing.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

import insights
from metrics import significantly_different

MIN_GAMES = 20          # fewer games than this and no behavioural claim is made
MIN_OPENING_GAMES = 4   # an opening needs this many games to be listed with a score
HABIT_SHARE = 0.25      # share of games that makes an opening "their main weapon"


def _openings(g: pd.DataFrame, colour: str, mine: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Openings the opponent plays as ``colour``: games, share, score with 95% interval, and the user's own record."""
    cols = ["opening", "games", "share", "score", "lo", "hi", "my_games", "my_score"]
    sub = g[g["user_color"] == colour]
    ops = insights.opening_summary(sub, min_games=MIN_OPENING_GAMES)
    if ops.empty:
        return pd.DataFrame(columns=cols)
    ops["share"] = ops["games"] / max(len(sub), 1)
    my_games, my_score = [], []
    for name in ops["opening"]:
        theirs = None
        if mine is not None and not mine.empty and "opening" in mine.columns:
            opp_colour = "black" if colour == "white" else "white"   # the user sits on the other side
            theirs = mine[(mine["opening"] == name) & (mine["user_color"] == opp_colour)]
        my_games.append(int(len(theirs)) if theirs is not None else 0)
        my_score.append(float(theirs["score"].mean()) if theirs is not None and len(theirs) else float("nan"))
    ops["my_games"], ops["my_score"] = my_games, my_score
    return ops[cols].head(8).reset_index(drop=True)


def scout_report(opp: pd.DataFrame, mine: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    """``opp`` is the opponent's enriched games, ``mine`` (optional) the user's enriched games."""
    out: Dict[str, object] = {"n": len(opp), "enough": len(opp) >= MIN_GAMES, "prep": []}
    if opp.empty:
        return out
    out["summary"] = insights.overall_summary(opp)
    classes = opp["time_class"].value_counts()
    main = classes.index[0]
    out["classes"] = classes.to_dict()
    out["main_class"] = main
    rated = opp[(opp["time_class"] == main) & opp["rating_after"].notna()].sort_values("date_utc")
    out["rating"] = float(rated["rating_after"].iloc[-1]) if len(rated) else float("nan")
    out["rating_30d_ago"] = float("nan")
    if len(rated) >= 2:
        cutoff = rated["date_utc"].iloc[-1] - pd.Timedelta(days=30)
        older = rated[rated["date_utc"] <= cutoff]
        if len(older):
            out["rating_30d_ago"] = float(older["rating_after"].iloc[-1])
    out["white"] = _openings(opp, "white", mine)
    out["black"] = _openings(opp, "black", mine)
    out["colour"] = insights.color_profile(opp)
    out["tilt"] = insights.tilt_summary(opp)
    out["clock"] = insights.clock_profile(opp)
    out["hours"] = insights.hourly_profile(opp)

    prep: List[Dict[str, str]] = []
    base = out["summary"]["score"]
    for colour in ("white", "black"):
        ops = out[colour]
        if ops.empty:
            continue
        top = ops.iloc[0]
        total = int((opp["user_color"] == colour).sum())
        if top["share"] >= HABIT_SHARE and top["games"] >= 5:
            mine_txt = ""
            if top["my_games"] >= 3:
                mine_txt = f" You score {top['my_score']:.0%} in your own {int(top['my_games'])} games against it."
            prep.append({"tone": "info", "title": f"As {colour.title()} they lean on the {top['opening']}",
                         "detail": f"{int(top['games'])} of their {total} games with {colour} ({top['share']:.0%}). "
                                   f"Prepare a line against it.{mine_txt}"})
        weak = ops[(ops["games"] >= 5) & (ops["hi"] < base)].sort_values("score")
        if len(weak):
            w = weak.iloc[0]
            prep.append({"tone": "good", "title": f"A soft spot as {colour.title()}: {w['opening']}",
                         "detail": f"They score {w['score']:.0%} in {int(w['games'])} games (95% interval {w['lo']:.0%} to {w['hi']:.0%}), "
                                   f"clearly below their overall {base:.0%}. Steer the game there if you can."})
    col = out["colour"]
    if len(col) == 2 and col["games"].min() >= MIN_GAMES:
        w, b = (col.set_index("user_color").loc[c] for c in ("white", "black"))
        if significantly_different(int(w["games"]), float(w["score"]), int(b["games"]), float(b["score"]), 1.96):
            weaker = "White" if w["score"] < b["score"] else "Black"
            prep.append({"tone": "good", "title": f"They are clearly weaker with {weaker}",
                         "detail": f"Score {w['score']:.0%} as White ({int(w['games'])} games) versus {b['score']:.0%} as Black ({int(b['games'])} games)."})
    clk = out["clock"]
    if clk and clk.get("games", 0) >= MIN_GAMES and clk["scramble_rate"] >= 0.25:
        prep.append({"tone": "good", "title": "They often run short of time",
                     "detail": f"{clk['scramble_rate']:.0%} of their games end with almost no clock. Keep the position complex and stay ahead on time."})
    if clk and clk.get("games", 0) >= MIN_GAMES and clk.get("timeout_losses", 0) >= 5:
        prep.append({"tone": "info", "title": "They lose on time",
                     "detail": f"{clk['timeout_losses']} of their games in this sample were lost on the clock."})
    tilt = out["tilt"]
    if tilt["significant"]:
        prep.append({"tone": "good", "title": "They tend to lose again after a loss",
                     "detail": f"They lose {tilt['loss_after']:.0%} of games right after a loss, versus {tilt['loss_other']:.0%} otherwise. "
                               "If you beat them once, a rematch is a good idea."})
    if out["enough"] and not prep:
        prep.append({"tone": "info", "title": "No clear weakness in this sample",
                     "detail": "Nothing stands out from chance. Prepare solid openings and play your own game."})
    out["prep"] = prep
    return out


def head_to_head(raw_games: pd.DataFrame, username: str, opponent: str) -> Dict[str, object]:
    """The user's record against ``opponent`` in the loaded games (user perspective)."""
    if raw_games is None or raw_games.empty:
        return {"n": 0}
    o = opponent.strip().lower()
    pair = raw_games[(raw_games["white_player"].astype(str).str.lower() == o) | (raw_games["black_player"].astype(str).str.lower() == o)]
    pair = insights.enrich_games(pair, username)
    if pair.empty:
        return {"n": 0}
    return insights.overall_summary(pair)


def peak_hours(hours: pd.DataFrame, k: int = 3) -> List[int]:
    """Hours of the day (UTC) in which the opponent starts the most games."""
    if hours.empty or hours["games"].sum() == 0:
        return []
    return [int(h) for h in hours.sort_values("games", ascending=False).head(k)["hour"] if hours.loc[hours["hour"] == h, "games"].iloc[0] > 0]
