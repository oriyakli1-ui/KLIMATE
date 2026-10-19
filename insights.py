"""Behavioural insights for Klimate: sessions, tilt, time management, rating-gap.

Pure pandas, no Streamlit imports, so the same code can later power an API.
Every function works on the frame returned by ``enrich_games``.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from metrics import mean_ci, performance_rating, score_result, significantly_different, wilson_interval

SESSION_GAP_MINUTES = 30
_CLK_RE = re.compile(r"\[%clk (\d+):(\d{2}):(\d{2}(?:\.\d+)?)\]")


def parse_time_control(tc: object) -> Tuple[Optional[float], Optional[float]]:
    """'600' -> (600, 0); '180+2' -> (180, 2); daily ('1/86400') or unknown -> (None, None)."""
    s = str(tc or "").strip()
    m = re.fullmatch(r"(\d+)(?:\+(\d+))?", s)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2) or 0)


def user_clocks(pgn: object, is_white: bool) -> List[float]:
    """The user's remaining clock (seconds) after each of their moves, from the PGN."""
    if not isinstance(pgn, str) or "%clk" not in pgn:
        return []
    clocks = [int(h) * 3600 + int(m) * 60 + float(s) for h, m, s in _CLK_RE.findall(pgn)]
    return clocks[0::2] if is_white else clocks[1::2]


def enrich_games(df: pd.DataFrame, username: str) -> pd.DataFrame:
    """One row per game of ``username``, oldest first, with user-perspective columns."""
    cols = [
        "date_utc", "start_utc", "rated", "user_color", "user_rating", "rating_after", "rating_change", "opp_rating", "rating_diff", "user_result",
        "opp_result", "score", "outcome", "time_class", "base_seconds", "inc_seconds", "opening",
        "session_id", "session_game_no", "losses_before", "user_moves", "final_clock",
        "avg_move_seconds", "clock_after_15_pct", "scramble", "lost_on_time", "won_on_time",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    u = username.strip().lower()
    white = df["white_player"].astype(str).str.lower() == u
    mine = df[white | (df["black_player"].astype(str).str.lower() == u)].copy()
    if mine.empty:
        return pd.DataFrame(columns=cols)
    is_white = (mine["white_player"].astype(str).str.lower() == u).to_numpy()

    out = pd.DataFrame(index=mine.index)
    out["date_utc"] = pd.to_datetime(mine["date_utc"], utc=True)  # when the game ended
    out["start_utc"] = (
        pd.to_datetime(mine["start_utc"], utc=True) if "start_utc" in mine.columns
        else pd.Series(pd.NaT, index=mine.index, dtype="datetime64[ns, UTC]")
    )
    out["rated"] = mine["rated"].astype(bool) if "rated" in mine.columns else True
    out["user_color"] = np.where(is_white, "white", "black")
    out["user_rating"] = pd.to_numeric(np.where(is_white, mine["white_rating"], mine["black_rating"]), errors="coerce")
    out["opp_rating"] = pd.to_numeric(np.where(is_white, mine["black_rating"], mine["white_rating"]), errors="coerce")
    out["rating_diff"] = out["opp_rating"] - out["user_rating"]
    out["user_result"] = np.where(is_white, mine["white_result"], mine["black_result"])
    out["opp_result"] = np.where(is_white, mine["black_result"], mine["white_result"])
    out["score"] = [score_result(m, o) for m, o in zip(out["user_result"], out["opp_result"])]
    out["score"] = out["score"].astype(float)
    unknown = out["score"].isna()
    if unknown.any():  # results we do not understand are left out rather than guessed
        out = out[~unknown].copy()
    out["outcome"] = np.where(out["score"] == 1.0, "win", np.where(out["score"] == 0.5, "draw", "loss"))
    out["time_class"] = mine["time_class"].fillna("")
    tc = mine["time_control"] if "time_control" in mine.columns else pd.Series("", index=mine.index)
    parsed = tc.map(parse_time_control)
    out["base_seconds"] = parsed.map(lambda x: x[0])
    out["inc_seconds"] = parsed.map(lambda x: x[1])
    out["opening"] = mine["opening"] if "opening" in mine.columns else ""
    out["lost_on_time"] = out["user_result"].astype(str).str.lower() == "timeout"
    out["won_on_time"] = out["opp_result"].astype(str).str.lower() == "timeout"

    # Carry the PGN and colour through the sort so clocks stay aligned with their game.
    out["_pgn"] = mine["pgn"] if "pgn" in mine.columns else ""
    out["_white"] = is_white
    out["_start_eff"] = out["start_utc"].fillna(out["date_utc"])
    out = out.sort_values(["_start_eff", "date_utc"], kind="stable").reset_index(drop=True)
    pgn = out.pop("_pgn")
    white_sorted = out.pop("_white")

    # --- ratings. Chess.com publishes every rating AFTER the game (for both players), so
    # the change a game caused is this rating minus the previous one in the same rating pool,
    # and the pre-game ratings follow from it. Anything that could not be reconstructed
    # reliably (first game of a pool, an unseen game in between) is left NaN, not guessed.
    out["rating_after"] = out["user_rating"]
    out["rating_change"] = np.nan
    for _, idx in out[out["rated"] & out["rating_after"].notna()].groupby("time_class").groups.items():
        pool = out.loc[idx].sort_values("date_utc")
        out.loc[pool.index, "rating_change"] = (pool["rating_after"] - pool["rating_after"].shift(1)).to_numpy()
    ch, sc = out["rating_change"], out["score"]
    consistent = ((sc == 1.0) & (ch >= 0)) | ((sc == 0.0) & (ch <= 0)) | ((sc == 0.5) & (ch.abs() <= 25))
    out["rating_change"] = ch.where(ch.notna() & (ch.abs() <= 45) & consistent)
    out["user_rating"] = out["rating_after"] - out["rating_change"]            # rating before the game
    out["opp_rating"] = out["opp_rating"] + out["rating_change"]               # opponent before the game (~ moved by -change)
    out["rating_diff"] = out["opp_rating"] - out["user_rating"]

    # --- sessions: a new session starts when the idle time between one game's end and the
    # next game's start exceeds SESSION_GAP_MINUTES. (End-to-end gaps would wrongly split a
    # session of long games.) Overlapping games count as the same session.
    gap = (out["_start_eff"] - out["date_utc"].shift()).dt.total_seconds().div(60)
    out["session_id"] = (gap.isna() | (gap > SESSION_GAP_MINUTES)).cumsum().astype(int)
    out["session_game_no"] = out.groupby("session_id").cumcount() + 1
    out = out.drop(columns="_start_eff")

    losses_before, streak, prev_sid = [], 0, None
    for sid, outcome in zip(out["session_id"], out["outcome"]):
        if sid != prev_sid:
            streak, prev_sid = 0, sid
        losses_before.append(streak)
        streak = streak + 1 if outcome == "loss" else 0
    out["losses_before"] = losses_before

    # --- clocks (only for games whose PGN carries %clk comments)
    finals, avgs, c15, moves = [], [], [], []
    for i in range(len(out)):
        clk = user_clocks(pgn.iloc[i], bool(white_sorted.iloc[i]))
        base, inc = out.at[i, "base_seconds"], out.at[i, "inc_seconds"]
        moves.append(len(clk))
        finals.append(clk[-1] if clk else np.nan)
        if clk and base:
            start = [base] + clk[:-1]
            used = [s - c + (inc or 0) for s, c in zip(start, clk)]
            avgs.append(float(np.mean(used)))
            c15.append(clk[14] / base if len(clk) >= 15 else np.nan)
        else:
            avgs.append(np.nan)
            c15.append(np.nan)
    out["user_moves"] = moves
    out["final_clock"] = finals
    out["avg_move_seconds"] = avgs
    out["clock_after_15_pct"] = c15
    thresh = out["base_seconds"].map(lambda b: max(10.0, min(30.0, 0.1 * b)) if b and b == b else np.nan)
    out["scramble"] = (out["final_clock"] < thresh).astype(object)  # object: holds True/False/NaN
    out.loc[out["final_clock"].isna() | thresh.isna(), "scramble"] = np.nan
    return out[cols]


def filter_enriched(g: pd.DataFrame, time_classes: List[str], color: str = "All") -> pd.DataFrame:
    """Filter the enriched frame by time class and colour ("All", "White" or "Black")."""
    if g.empty:
        return g
    out = g[g["time_class"].isin(time_classes)] if time_classes else g.iloc[0:0]
    if color in ("White", "Black"):
        out = out[out["user_color"] == color.lower()]
    return out


def filter_games(df: pd.DataFrame, username: str, time_classes: List[str], color: str = "All") -> pd.DataFrame:
    """Same filter for the raw games frame used by the older pages."""
    if df is None or df.empty:
        return df
    out = df[df["time_class"].isin(time_classes)] if time_classes else df.iloc[0:0]
    if color in ("White", "Black"):
        is_white = out["white_player"].astype(str).str.lower() == username.strip().lower()
        out = out[is_white] if color == "White" else out[~is_white]
    return out


def tilt_profile(g: pd.DataFrame, min_n: int = 8) -> Dict[str, object]:
    """Win rate by number of consecutive losses just before a game (same session only)."""
    if g.empty:
        return {"table": pd.DataFrame(), "baseline": np.nan, "stop_loss_after": None, "enough_data": False}
    base = float(g["score"].mean())
    bucket = g["losses_before"].clip(upper=3).map({0: "0", 1: "1", 2: "2", 3: "3+"})
    table = (
        g.assign(bucket=bucket)
        .groupby("bucket")
        .agg(games=("score", "size"), score=("score", "mean"))
        .reindex(["0", "1", "2", "3+"])
        .dropna()
        .reset_index()
    )
    stop = None
    for _, row in table.iterrows():
        if row["bucket"] != "0" and row["games"] >= min_n and row["score"] <= base - 0.08 \
                and _significant(int(row["games"]), row["score"], len(g), base):
            stop = 3 if row["bucket"] == "3+" else int(row["bucket"])
            break
    return {"table": table, "baseline": base, "stop_loss_after": stop, "enough_data": bool((table["games"] >= min_n).any())}


def session_profile(g: pd.DataFrame) -> Dict[str, object]:
    if g.empty:
        return {"sessions": 0, "avg_games": np.nan, "longest": 0, "by_game_no": pd.DataFrame()}
    per = g.groupby("session_id").size()
    bucket = g["session_game_no"].clip(upper=5).map({1: "1", 2: "2", 3: "3", 4: "4", 5: "5+"})
    by_no = (
        g.assign(bucket=bucket).groupby("bucket").agg(games=("score", "size"), score=("score", "mean"))
        .reindex(["1", "2", "3", "4", "5+"]).dropna().reset_index()
    )
    return {"sessions": int(len(per)), "avg_games": float(per.mean()), "longest": int(per.max()), "by_game_no": by_no}


def clock_profile(g: pd.DataFrame) -> Dict[str, object]:
    """Time-management stats from the PGN clocks. Empty dict when no game carries clocks."""
    c = g[g["final_clock"].notna()]
    if len(c) < 5:
        return {}
    sc = c[c["scramble"] == True]  # noqa: E712
    ns = c[c["scramble"] == False]  # noqa: E712
    losses = c[c["outcome"] == "loss"]
    early = c[c["clock_after_15_pct"].notna()]
    burn = early[early["clock_after_15_pct"] < 0.7]
    calm = early[early["clock_after_15_pct"] >= 0.7]
    return {
        "games": int(len(c)),
        "scramble_rate": float(len(sc) / len(c)),
        "scramble_score": float(sc["score"].mean()) if len(sc) else np.nan,
        "no_scramble_score": float(ns["score"].mean()) if len(ns) else np.nan,
        "scramble_n": int(len(sc)),
        "timeout_loss_share": float((losses["lost_on_time"]).mean()) if len(losses) else np.nan,
        "timeout_losses": int(c["lost_on_time"].sum()),
        "timeout_wins": int(c["won_on_time"].sum()),
        "burn_score": float(burn["score"].mean()) if len(burn) else np.nan,
        "burn_n": int(len(burn)),
        "calm_score": float(calm["score"].mean()) if len(calm) else np.nan,
        "calm_n": int(len(calm)),
        "median_clock_after_15_pct": float(early["clock_after_15_pct"].median()) if len(early) else np.nan,
    }


def rating_gap_profile(g: pd.DataFrame) -> pd.DataFrame:
    d = g.dropna(subset=["rating_diff"])
    if d.empty:
        return pd.DataFrame()
    bins = [-np.inf, -100, -30, 30, 100, np.inf]
    labels = ["Much lower (-100+)", "Lower", "Even (±30)", "Higher", "Much higher (+100)"]
    return (
        d.assign(band=pd.cut(d["rating_diff"], bins=bins, labels=labels))
        .groupby("band", observed=True)
        .agg(games=("score", "size"), score=("score", "mean"))
        .reset_index()
    )


def color_profile(g: pd.DataFrame) -> pd.DataFrame:
    if g.empty:
        return pd.DataFrame()
    return g.groupby("user_color").agg(games=("score", "size"), score=("score", "mean")).reset_index()


def _significant(n1: int, s1: float, n2: int, s2: float, z: float = 1.64) -> bool:
    """See ``metrics.significantly_different``."""
    return significantly_different(n1, s1, n2, s2, z)


def overall_summary(g: pd.DataFrame) -> Dict[str, object]:
    """Wins/draws/losses, score (wins + half draws) and win rate, each with a 95% interval."""
    n = len(g)
    if n == 0:
        return {"n": 0}
    w, d, l = int((g["outcome"] == "win").sum()), int((g["outcome"] == "draw").sum()), int((g["outcome"] == "loss").sum())
    score, s_lo, s_hi = mean_ci(g["score"].to_numpy())
    w_lo, w_hi = wilson_interval(w, n)
    return {"n": n, "wins": w, "draws": d, "losses": l, "score": score, "score_lo": s_lo, "score_hi": s_hi,
            "win_rate": w / n, "win_lo": w_lo, "win_hi": w_hi}


def performance_summary(g: pd.DataFrame, min_games: int = 20) -> Dict[str, object]:
    """Performance rating of the most-played time class, rated games only.

    Ratings of different time controls are not comparable, so classes are never mixed.
    ``rating`` is NaN when there are fewer than ``min_games`` rated games in that class.
    """
    r = g[g["rated"] & g["opp_rating"].notna()]
    if r.empty:
        return {"rating": float("nan"), "time_class": "", "n": 0, "mixed_classes": False}
    tc = r["time_class"].value_counts().index[0]
    sub = r[r["time_class"] == tc]
    rating = float("nan")
    if len(sub) >= min_games:
        rating = performance_rating(sub["opp_rating"].to_numpy(), float(sub["score"].sum()))
    return {"rating": rating, "time_class": tc, "n": len(sub), "mixed_classes": r["time_class"].nunique() > 1,
            "avg_opponent": float(sub["opp_rating"].mean()), "score": float(sub["score"].mean())}


def tilt_summary(g: pd.DataFrame, min_n: int = 20) -> Dict[str, object]:
    """Loss rate right after a loss (same session) versus in games that do not follow a loss."""
    after, other = g[g["losses_before"] >= 1], g[g["losses_before"] == 0]
    out = {"n_after": len(after), "n_other": len(other), "enough": len(after) >= min_n and len(other) >= min_n}
    out["loss_after"] = float((after["outcome"] == "loss").mean()) if len(after) else float("nan")
    out["loss_other"] = float((other["outcome"] == "loss").mean()) if len(other) else float("nan")
    out["delta"] = out["loss_after"] - out["loss_other"] if out["enough"] else float("nan")
    out["significant"] = bool(out["enough"] and out["delta"] > 0 and significantly_different(
        len(after), 1 - out["loss_after"], len(other), 1 - out["loss_other"]))
    return out


def current_streak(g: pd.DataFrame) -> Tuple[str, int]:
    """('win'|'loss'|'none', length) counted from the most recent game; a draw ends the streak."""
    if g.empty:
        return "none", 0
    newest_first = g.sort_values("date_utc", ascending=False)["outcome"].tolist()
    kind = newest_first[0]
    if kind == "draw":
        return "none", 0
    n = 0
    for o in newest_first:
        if o != kind:
            break
        n += 1
    return kind, n


def hourly_profile(g: pd.DataFrame, timezone: str = "UTC") -> pd.DataFrame:
    """Per local hour of the day the game STARTED: games, wins/draws/losses, score with 95% interval."""
    cols = ["hour", "games", "wins", "draws", "losses", "score", "lo", "hi"]
    if g.empty:
        return pd.DataFrame(columns=cols)
    when = g["start_utc"].fillna(g["date_utc"]).dt.tz_convert(timezone)
    d = g.assign(hour=when.dt.hour)
    rows = []
    for h in range(24):
        s = d[d["hour"] == h]
        m, lo, hi = mean_ci(s["score"].to_numpy()) if len(s) else (float("nan"),) * 3
        rows.append({"hour": h, "games": len(s), "wins": int((s["outcome"] == "win").sum()),
                     "draws": int((s["outcome"] == "draw").sum()), "losses": int((s["outcome"] == "loss").sum()),
                     "score": m, "lo": lo, "hi": hi})
    return pd.DataFrame(rows, columns=cols)


def best_hour(profile: pd.DataFrame, min_games: int = 10, z: float = 2.5) -> Optional[Dict[str, object]]:
    """The best hour, only when it beats the rest of the day by more than chance.

    The hour is picked out of up to 24 candidates, so the bar (z=2.5) is stricter than for a
    single planned comparison.
    """
    ok = profile[profile["games"] >= min_games]
    if ok.empty:
        return None
    best = ok.loc[ok["score"].idxmax()]
    rest = profile[profile["hour"] != best["hour"]]
    n_rest = int(rest["games"].sum())
    if n_rest < min_games:
        return None
    s_rest = float((rest["score"].fillna(0) * rest["games"]).sum() / n_rest)
    if not significantly_different(int(best["games"]), float(best["score"]), n_rest, s_rest, z) or best["score"] <= s_rest:
        return None
    return {"hour": int(best["hour"]), "games": int(best["games"]), "score": float(best["score"]), "rest": s_rest}


def opening_summary(g: pd.DataFrame, min_games: int = 1) -> pd.DataFrame:
    """Opening families with games, score and a 95% interval, most played first. 'Unknown' is excluded."""
    cols = ["opening", "games", "score", "lo", "hi"]
    if g.empty or "opening" not in g.columns:
        return pd.DataFrame(columns=cols)
    d = g[g["opening"].astype(str).str.len() > 0]
    d = d[d["opening"] != "Unknown"]
    rows = []
    for name, grp in d.groupby("opening"):
        if len(grp) >= min_games:
            m, lo, hi = mean_ci(grp["score"].to_numpy())
            rows.append({"opening": name, "games": len(grp), "score": m, "lo": lo, "hi": hi})
    return pd.DataFrame(rows, columns=cols).sort_values("games", ascending=False).reset_index(drop=True)


# English templates for the insight cards.
TEMPLATES = {
    "stop_loss": (
        "Your personal stop-loss: quit the session after {n} loss{es} in a row",
        "After {n}{plus} straight loss(es) in a session your score drops to {score} (vs {baseline} overall, {games} games).",
    ),
    "warmup": (
        "You start sessions cold: your first game is your weakest",
        "You score {first} in the first game of a session vs {rest} in the rest ({n} sessions). Try a warm-up game or a few puzzles first.",
    ),
    "scramble": (
        "Time scrambles cost you: {rate} of games end with almost no time",
        "When you are in a scramble you score {score} vs {other} otherwise ({n} games).",
    ),
    "early_burn": (
        "You spend too much clock early in the game",
        "When you have under 70% of your time left after move 15 you score {burn} vs {calm} ({n} games).",
    ),
    "timeouts": (
        "{share} of your losses are on time",
        "{losses} games lost on the clock vs {wins} won that way. Consider an increment time control.",
    ),
    "lower_rated": (
        "You underperform against lower-rated opponents",
        "Against opponents rated 30+ below you, ratings predict {expected} but you score {actual} ({n} games).",
    ),
    "color": (
        "Your {weak} repertoire needs work",
        "You score {w} as White and {b} as Black.",
    ),
}


def _insight(key: str, **params: object) -> Dict[str, object]:
    title, detail = TEMPLATES[key]
    return {"key": key, "params": params, "title": title.format(**params), "detail": detail.format(**params)}


def _pct(x: float) -> str:
    return f"{x:.0%}"


def generate_insights(g: pd.DataFrame, min_n: int = 8) -> List[Dict[str, object]]:
    """Rule-based, evidence-backed findings, most actionable first. No LLM involved.

    Each item has ``key``, ``params`` (strings ready to format) and English ``title``/``detail``.
    """
    found: List[Dict[str, object]] = []
    if len(g) < 20:
        return found

    t = tilt_profile(g, min_n)
    if t["stop_loss_after"]:
        n = int(t["stop_loss_after"])
        row = t["table"][t["table"]["bucket"] == ("3+" if n >= 3 else str(n))].iloc[0]
        found.append(_insight(
            "stop_loss", n=n, es="es" if n > 1 else "", plus="+" if n >= 3 else "",
            score=_pct(row["score"]), baseline=_pct(t["baseline"]), games=int(row["games"]),
        ))

    # One pre-planned comparison (first game of a session vs the rest) instead of picking
    # the best of several buckets, which would produce false positives.
    first, rest = g[g["session_game_no"] == 1], g[g["session_game_no"] >= 2]
    if len(first) >= min_n and len(rest) >= min_n:
        f, r = float(first["score"].mean()), float(rest["score"].mean())
        if r - f >= 0.08 and _significant(len(first), f, len(rest), r):
            found.append(_insight("warmup", first=_pct(f), rest=_pct(r), n=len(first)))

    c = clock_profile(g)
    if c:
        if c["scramble_n"] >= min_n and c["scramble_score"] + 0.10 <= c["no_scramble_score"] \
                and _significant(c["scramble_n"], c["scramble_score"], c["games"] - c["scramble_n"], c["no_scramble_score"]):
            found.append(_insight("scramble", rate=_pct(c["scramble_rate"]), score=_pct(c["scramble_score"]),
                                  other=_pct(c["no_scramble_score"]), n=c["scramble_n"]))
        if c["burn_n"] >= min_n and c["calm_n"] >= min_n and c["burn_score"] + 0.08 <= c["calm_score"] \
                and _significant(c["burn_n"], c["burn_score"], c["calm_n"], c["calm_score"]):
            found.append(_insight("early_burn", burn=_pct(c["burn_score"]), calm=_pct(c["calm_score"]), n=c["burn_n"]))
        if c["timeout_losses"] >= 5 and c["timeout_loss_share"] >= 0.25:
            found.append(_insight("timeouts", share=_pct(c["timeout_loss_share"]), losses=c["timeout_losses"], wins=c["timeout_wins"]))

    low = g[g["rating_diff"] <= -30].dropna(subset=["rating_diff"])
    if len(low) >= min_n:
        expected = float((1.0 / (1.0 + 10 ** (low["opp_rating"] - low["user_rating"]).div(400))).mean())
        actual = float(low["score"].mean())
        if actual <= expected - 0.08 and _significant(len(low), actual, len(low), expected):
            found.append(_insight("lower_rated", expected=_pct(expected), actual=_pct(actual), n=len(low)))

    col = color_profile(g)
    if len(col) == 2 and (col["games"] >= min_n).all():
        idx = col.set_index("user_color")
        w, b = float(idx.loc["white", "score"]), float(idx.loc["black", "score"])
        if abs(w - b) >= 0.12 and _significant(int(idx.loc["white", "games"]), w, int(idx.loc["black", "games"]), b):
            found.append(_insight("color", weak="Black" if b < w else "White", w=_pct(w), b=_pct(b)))
    return found
