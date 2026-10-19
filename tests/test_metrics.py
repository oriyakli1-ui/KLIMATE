import math

import numpy as np
import pandas as pd
import pytest

import insights as I
import metrics as M
import spatial


@pytest.mark.parametrize("mine,opp,expected", [
    ("win", "checkmated", 1.0), ("win", "timeout", 1.0), ("win", "abandoned", 1.0),
    ("checkmated", "win", 0.0), ("timeout", "win", 0.0), ("resigned", "win", 0.0), ("abandoned", "win", 0.0),
    ("agreed", "agreed", 0.5), ("repetition", "repetition", 0.5), ("stalemate", "stalemate", 0.5),
    ("insufficient", "insufficient", 0.5), ("50move", "50move", 0.5), ("timevsinsufficient", "insufficient", 0.5),
    ("kingofthehill", "checkmated", 1.0), ("checkmated", "kingofthehill", 0.0),   # unusual winner strings
    ("weird", "weird", None),
])
def test_score_result(mine, opp, expected):
    assert M.score_result(mine, opp) == expected


def test_performance_rating_matches_the_elo_definition():
    opp = [1500] * 10
    assert abs(M.performance_rating(opp, 5.0) - 1500) < 0.5          # 50% against 1500s -> 1500
    assert abs(M.performance_rating(opp, 7.5) - (1500 + 400 * math.log10(0.75 / 0.25))) < 1.0   # 75% -> +191
    assert M.performance_rating(opp, 10.0) == 2300                    # perfect score is capped at +800
    assert M.performance_rating(opp, 0.0) == 700
    assert math.isnan(M.performance_rating([], 0.0))
    # expected score at the returned rating equals the actual score
    r = M.performance_rating([1400, 1600, 1500, 1700], 2.5)
    assert abs(sum(M.expected_score(r, o) for o in [1400, 1600, 1500, 1700]) - 2.5) < 1e-6


def test_intervals():
    lo, hi = M.wilson_interval(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60
    assert M.wilson_interval(0, 0)[0] != M.wilson_interval(0, 0)[0]
    m, lo, hi = M.mean_ci([1, 0] * 50)
    assert m == 0.5 and lo < 0.5 < hi and hi - lo < 0.25
    assert not M.significantly_different(10, 0.5, 10, 0.6)
    assert M.significantly_different(200, 0.3, 200, 0.5)
    assert not M.significantly_different(200, 0.5, 200, 0.55, z=2.5)


def test_count_plies():
    pgn = '[Event "x"]\n\n1. e4 {[%clk 0:10:00]} 1... c5 {[%clk 0:10:00]} 2. Nf3 {[%clk 0:09:58]} 1-0'
    assert M.count_plies(pgn) == 3
    assert M.count_plies("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6") == 6
    assert M.count_plies("") == 0 and M.count_plies(None) == 0


def test_sessions_use_idle_time_between_end_and_next_start(games_factory):
    # 40-minute games back to back: end-to-end gaps are 45 min, but the idle time is only 5 minutes.
    g = I.enrich_games(games_factory(["win"] * 4, gap_minutes=[5, 5, 5], duration=40), "me")
    assert g["session_id"].nunique() == 1
    g2 = I.enrich_games(games_factory(["win"] * 3, gap_minutes=[31, 29], duration=10), "me")
    assert list(g2["session_id"]) == [1, 2, 2]


def test_overall_summary_and_tilt(games_factory):
    g = I.enrich_games(games_factory(["win", "loss", "draw", "loss"] * 30, gap_minutes=([2, 2, 2, 120] * 30)[:-1]), "me")
    s = I.overall_summary(g)
    assert s["n"] == 120 and s["wins"] == 30 and s["draws"] == 30 and s["losses"] == 60
    assert abs(s["score"] - 0.375) < 1e-9 and s["score_lo"] < s["score"] < s["score_hi"]
    assert abs(s["win_rate"] - 0.25) < 1e-9
    t = I.tilt_summary(g)
    # games after a loss: the draw (after loss #1... pattern win,loss,draw,loss): draw and next-session-first are not after loss
    assert t["n_after"] == 30 and t["n_other"] == 90 and t["enough"]
    assert t["loss_after"] == 0.0 and not t["significant"]      # after a loss comes a draw: tilt does not exist here


def test_performance_summary_never_mixes_time_classes(games_factory):
    df = games_factory(["win", "loss"] * 20)
    df.loc[df.index[:10], "time_class"] = "blitz"
    p = I.performance_summary(I.enrich_games(df, "me"))
    assert p["time_class"] == "rapid" and p["n"] == 30 and p["mixed_classes"]
    assert 1190 < p["rating"] < 1210 or p["rating"] != p["rating"]


def test_hourly_profile_and_best_hour(games_factory):
    # 60 games that start at 20:xx and are won, 60 games at 09:xx that are lost.
    a = games_factory(["win"] * 60, start="2026-01-01 20:00", gap_minutes=[60 * 24 - 5] * 59)
    b = games_factory(["loss"] * 60, start="2026-01-01 09:00", gap_minutes=[60 * 24 - 5] * 59)
    g = I.enrich_games(pd.concat([a, b], ignore_index=True), "me")
    prof = I.hourly_profile(g, "UTC")
    assert prof.loc[prof.hour == 20, "games"].iloc[0] == 60 and prof.loc[prof.hour == 9, "score"].iloc[0] == 0.0
    best = I.best_hour(prof)
    assert best and best["hour"] == 20 and best["score"] == 1.0
    # same data in another timezone shifts the hour (Asia/Jerusalem = UTC+2 in January)
    assert I.hourly_profile(g, "Asia/Jerusalem").loc[lambda d: d.games == 60, "hour"].tolist() == [11, 22]


def test_best_hour_is_none_for_noise(games_factory):
    rng = np.random.default_rng(7)
    parts = [games_factory(list(rng.choice(["win", "loss"], 12)), start=f"2026-01-01 {h:02d}:00", gap_minutes=[60 * 24 - 5] * 11) for h in range(24)]
    g = I.enrich_games(pd.concat(parts, ignore_index=True), "me")
    assert I.best_hour(I.hourly_profile(g, "UTC")) is None


def test_spatial_maps_use_the_players_side_of_the_board():
    pgn = "1. e4 e5 2. Nf3 Nc6"
    act_w, _, used_w = spatial.heatmaps([(pgn, True)], "Pawn")
    act_b, _, used_b = spatial.heatmaps([(pgn, False)], "Pawn")
    assert used_w == used_b == 1
    assert act_w[3, 4] == 1          # white e4 -> rank 4 from white's side
    assert act_b[3, 4] == 1          # black e5 -> rank 5 absolute, rank 4 from black's side
    act_n, _, _ = spatial.heatmaps([(pgn, True)], "Knight")
    assert act_n[2, 5] == 1          # Nf3


def test_spatial_captures_count_the_players_pieces_including_en_passant():
    # white pawn e5 captured en passant by black d5xe6 e.p. (black pawn on d5 moves to e6)
    pgn = "1. e4 a6 2. e5 d5 3. exd6 Nf6"       # white captures black's pawn en passant on d6 -> black's d5 pawn is captured
    _, cap_black, _ = spatial.heatmaps([(pgn, False)], "Pawn")
    assert cap_black.sum() == 1 and cap_black[7 - 4, 3] == 1   # d5 square seen from black's side: rank index 7-4=3
    _, cap_white, _ = spatial.heatmaps([(pgn, True)], "Pawn")
    assert cap_white.sum() == 0



def test_linear_trend():
    slope, se = M.linear_trend([1000 + 2 * i for i in range(30)])
    assert abs(slope - 2.0) < 1e-9 and se < 1e-6
    rng = np.random.default_rng(3)
    noisy = list(1000 + rng.normal(0, 30, 80))
    slope, se = M.linear_trend(noisy)
    assert abs(slope / se) < 2.5          # pure noise is not a reliable trend
    assert math.isnan(M.linear_trend([1, 2])[0])
