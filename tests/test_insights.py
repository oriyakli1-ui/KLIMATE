import numpy as np
import pandas as pd

import insights as I


def test_parse_time_control():
    assert I.parse_time_control("600") == (600.0, 0.0)
    assert I.parse_time_control("180+2") == (180.0, 2.0)
    assert I.parse_time_control("1/86400") == (None, None)
    assert I.parse_time_control("") == (None, None)


def test_user_clocks_split_by_colour():
    pgn = "1. e4 {[%clk 0:09:58.7]} 1... c5 {[%clk 0:09:57.2]} 2. Nf3 {[%clk 0:09:50.1]} 2... d6 {[%clk 0:09:40.0]}"
    assert I.user_clocks(pgn, True) == [598.7, 590.1]
    assert I.user_clocks(pgn, False) == [597.2, 580.0]
    assert I.user_clocks("1. e4 e5", True) == []


def test_sessions_and_losses_before(games_factory):
    df = games_factory(["loss", "loss", "win", "loss", "loss"], gap_minutes=[10, 10, 120, 5])
    g = I.enrich_games(df, "me")
    assert list(g["session_id"]) == [1, 1, 1, 2, 2]
    assert list(g["session_game_no"]) == [1, 2, 3, 1, 2]
    # a new session resets the streak; a win breaks it
    assert list(g["losses_before"]) == [0, 1, 2, 0, 1]


def test_enrich_is_sorted_and_scored(games_factory):
    df = games_factory(["win", "draw", "loss"]).iloc[::-1]  # newest first, like data_engine returns
    g = I.enrich_games(df, "me")
    assert g["date_utc"].is_monotonic_increasing
    assert list(g["score"]) == [1.0, 0.5, 0.0]
    assert list(g["outcome"]) == ["win", "draw", "loss"]


def test_stop_loss_is_detected_when_losses_snowball(games_factory):
    results = ["win", "loss", "loss", "loss"] * 50
    gaps = ([5, 5, 5, 120] * 50)[:-1]
    g = I.enrich_games(games_factory(results, gap_minutes=gaps), "me")
    tp = I.tilt_profile(g, min_n=8)
    assert tp["stop_loss_after"] == 1
    keys = [i["key"] for i in I.generate_insights(g)]
    assert "stop_loss" in keys


def test_no_insights_for_fair_coin(games_factory):
    rng = np.random.default_rng(1)
    results = list(rng.choice(["win", "loss"], size=200))
    gaps = list(rng.choice([5, 10, 90], size=199))
    g = I.enrich_games(games_factory(results, gap_minutes=gaps), "me")
    assert I.generate_insights(g) == []


def test_too_few_games_give_no_insights(games_factory):
    g = I.enrich_games(games_factory(["win"] * 10), "me")
    assert I.generate_insights(g) == []


def test_significance_requires_a_real_gap():
    assert not I._significant(10, 0.5, 10, 0.6)
    assert I._significant(200, 0.3, 200, 0.5)


def test_filters(games_factory):
    df = games_factory(["win", "loss"])
    df.loc[1, "time_class"] = "blitz"
    df.loc[1, ["white_player", "black_player"]] = ["opp", "me"]
    g = I.enrich_games(df, "me")
    assert len(I.filter_enriched(g, ["rapid"], "All")) == 1
    assert len(I.filter_enriched(g, ["rapid", "blitz"], "Black")) == 1
    assert I.filter_enriched(g, [], "All").empty
    assert len(I.filter_games(df, "me", ["rapid", "blitz"], "White")) == 1


def test_clock_profile_needs_clock_data(games_factory):
    g = I.enrich_games(games_factory(["win"] * 30), "me")
    assert I.clock_profile(g) == {}


def test_clock_profile_scramble(games_factory):
    pgn = "1. e4 {[%clk 0:09:58.0]} 1... c5 {[%clk 0:09:58.0]} 2. Nf3 {[%clk 0:00:05.0]} 2... d6 {[%clk 0:09:50.0]}"
    g = I.enrich_games(games_factory(["loss"] * 12, clk_pgn=pgn), "me")
    cp = I.clock_profile(g)
    assert cp["games"] == 12 and cp["scramble_rate"] == 1.0
