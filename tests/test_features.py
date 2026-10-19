import numpy as np
import pandas as pd
import pytest

import insights as I
import ledger
import opening_eval as OE
import readiness
from tests.conftest import make_games


def _rated_games(results, changes_for, gap=None, start="2026-01-01 10:00"):
    """Games whose published (post-game) rating follows a rule: change = changes_for(i, results)."""
    df = make_games(results, gap_minutes=gap, start=start)
    rating, ratings = 1200, []
    for i in range(len(results)):
        rating += changes_for(i, results)
        ratings.append(rating)
    df["white_rating"] = ratings
    df["black_rating"] = [1200] * len(results)
    return df


def test_rating_semantics_pre_game_ratings_and_changes():
    df = _rated_games(["win", "loss", "win"], lambda i, r: {"win": 8, "loss": -8}[r[i]])
    g = I.enrich_games(df, "me")
    assert list(g["rating_after"]) == [1208, 1200, 1208]
    assert g["rating_change"].isna().iloc[0] and list(g["rating_change"].iloc[1:]) == [-8.0, 8.0]
    assert list(g["user_rating"].iloc[1:]) == [1208.0, 1200.0]          # rating BEFORE the game = previous post-game rating
    assert g["opp_rating"].iloc[1] == 1200 + (-8)                        # opponent before ~ opp_after + our change


def test_inconsistent_rating_jumps_are_not_trusted():
    # a "win" whose rating fell means an unseen game sits in between: that change must be dropped
    df = _rated_games(["win", "win", "win"], lambda i, r: [8, -30, 8][i])
    g = I.enrich_games(df, "me")
    assert g["rating_change"].isna().tolist() == [True, True, False]


def test_ledger_flags_a_costly_habit(games_factory):
    rng = np.random.default_rng(5)
    n = 400
    results = list(rng.choice(["win", "loss"], size=n))
    gaps = [3 if rng.random() < 0.6 else 120 for _ in range(n - 1)]
    base = make_games(results, gap_minutes=gaps)
    g0 = I.enrich_games(base, "me")
    # games right after a loss lose 14 points, everything else +-8
    lb = g0["losses_before"].tolist()
    changes = []
    for i, r in enumerate(results):
        # g0 is sorted by time, same order as results
        changes.append(-14 if (lb[i] >= 1 and r == "loss") else (8 if r == "win" else -8))
    # make after-loss games clearly worse: wins there are worth only +2
    changes = [2 if (lb[i] >= 1 and results[i] == "win") else c for i, c in enumerate(changes)]
    df = base.copy()
    rating, ratings = 1200, []
    for c in changes:
        rating += c
        ratings.append(rating)
    df["white_rating"] = ratings
    g = I.enrich_games(df, "me")
    res = ledger.ledger(g, "UTC")
    row = res["table"].set_index("key").loc["after_loss"]
    assert row["enough"] and row["difference"] < -4 and row["reliable"]
    assert res["summary"]["usable_games"] >= n - 5
    assert abs(res["summary"]["net_points"] - (ratings[-1] - ratings[0])) < 1e-6


def test_ledger_needs_enough_games(games_factory):
    g = I.enrich_games(games_factory(["win"] * 10), "me")
    res = ledger.ledger(g)
    assert res["table"].empty or not res["table"]["enough"].any()


def _history(after_two_losses_lose: bool):
    rng = np.random.default_rng(11)
    results = []
    # sessions of 4 games: W/L mix; if the player already lost 2 in a row the 3rd is always a loss
    gaps = []
    for _ in range(80):
        s = []
        for k in range(4):
            if after_two_losses_lose and len(s) >= 2 and s[-1] == s[-2] == "loss":
                s.append("loss")
            else:
                s.append("win" if rng.random() < 0.5 else "loss")
        results += s
        gaps += [2, 2, 2, 200]
    return make_games(results, gap_minutes=gaps[:-1])


def test_readiness_red_after_a_losing_streak_when_history_says_so():
    g = I.enrich_games(_history(True), "me")
    last_end = g["date_utc"].max()
    # craft the present: last two games of the final session were losses, 5 minutes ago
    now = last_end + pd.Timedelta(minutes=5)
    state = readiness.current_state(g, now)
    if state["losses_in_row"] < 2:   # force the situation on the last session
        g = g.copy()
        last_sid = g["session_id"].iloc[-1]
        idx = g[g["session_id"] == last_sid].index[-2:]
        g.loc[idx, "outcome"] = "loss"
        state = readiness.current_state(g, now)
    assert state["in_session"] and state["losses_in_row"] >= 2
    res = readiness.assess(g, state)
    assert res["light"] == "red"
    assert any(c.get("worse") for c in res["checks"])


def test_readiness_is_green_or_grey_without_a_tilt_effect_and_fresh_start():
    g = I.enrich_games(_history(False), "me")
    now = g["date_utc"].max() + pd.Timedelta(hours=5)
    state = readiness.current_state(g, now)
    assert not state["in_session"] and state["next_game_no"] == 1
    assert readiness.assess(g, state)["light"] in ("green", "grey")


def test_opening_fen_and_report():
    assert OE.fen_after("1. e4 e5 2. Nf3", 20) is None
    pgn = " ".join(f"{i}. Nf3 Nf6 {i}... Ng1 Ng8" if False else "" for i in range(1)) or "1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 5. Nf3 Nf6 6. Ng1 Ng8 7. Nf3 Nf6 8. Ng1 Ng8 9. Nf3 Nf6 10. Ng1 Ng8"
    fen = OE.fen_after(pgn, 20)
    assert fen and fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")

    rng = np.random.default_rng(2)
    rows = []
    for _ in range(40):
        rows.append({"opening": "Bad Opening", "color": "Black", "score": float(rng.choice([0, 1])), "eval": float(rng.normal(-1.5, 0.6))})
    for _ in range(120):
        rows.append({"opening": "Normal Opening", "color": "White", "score": float(rng.choice([0, 1])), "eval": float(rng.normal(0.1, 0.6))})
    for _ in range(200):
        rows.append({"opening": "Other Opening", "color": "White", "score": float(rng.choice([0, 1])), "eval": float(rng.normal(0.0, 0.6))})
    rep = OE.report(pd.DataFrame(rows)).set_index(["opening", "color"])
    assert rep.loc[("Bad Opening", "Black"), "verdict"].startswith("Opening problem")
    assert not rep.loc[("Normal Opening", "White"), "verdict"].startswith("Opening problem")
    lo, mid, hi = rep.loc[("Bad Opening", "Black"), ["eval_lo", "eval", "eval_hi"]]
    assert lo < mid < hi < -1.0                       # evaluation intervals are not clamped to [0, 1]


def test_opening_collect_uses_the_players_side_and_skips_short_games():
    pgn = "1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 5. Nf3 Nf6 6. Ng1 Ng8 7. Nf3 Nf6 8. Ng1 Ng8 9. Nf3 Nf6 10. Ng1 Ng8"
    df = pd.DataFrame({"date_utc": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"], utc=True),
                       "white_player": ["me", "opp", "me"], "black_player": ["opp", "me", "opp"],
                       "white_result": ["win", "checkmated", "win"], "black_result": ["checkmated", "win", "checkmated"],
                       "opening": ["Italian Game", "Italian Game", "Italian Game"],
                       "pgn": [pgn, pgn, "1. e4 e5"]})
    out = OE.collect(df, "me", lambda fen: 1.0)           # +1 for White
    assert len(out) == 2                                  # the 2-ply game has no move-10 position
    assert sorted(out["color"]) == ["Black", "White"]
    assert out[out.color == "White"]["eval"].iloc[0] == 1.0 and out[out.color == "Black"]["eval"].iloc[0] == -1.0



def test_opening_report_is_quiet_when_all_openings_are_alike():
    rng = np.random.default_rng(9)
    rows = []
    for name in ("A", "B", "C"):
        for _ in range(60):
            rows.append({"opening": name, "color": "White", "score": float(rng.choice([0, 1])), "eval": float(rng.normal(0.0, 0.6))})
    rep = OE.report(pd.DataFrame(rows))
    assert rep["verdict"].str.startswith("Within").all()
