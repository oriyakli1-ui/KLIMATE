import pandas as pd

import insights as I
import weekly
from tests.conftest import make_games


def _g(results, gaps, start="2026-03-01 10:00"):
    return I.enrich_games(make_games(results, gap_minutes=gaps, start=start), "me")


def test_anchor_is_now_when_active_and_last_game_otherwise():
    g = _g(["win"] * 3, [5, 5], start="2026-03-01 10:00")
    last = g["date_utc"].max()
    assert weekly.anchor_time(g, last + pd.Timedelta(days=2)) == last + pd.Timedelta(days=2)
    assert weekly.anchor_time(g, last + pd.Timedelta(days=30)) == last


def test_weekly_report_compares_two_periods():
    # week 1: 4 games on 1 March; week 2: 6 games on 9 March
    a = make_games(["win", "loss", "loss", "loss"], gap_minutes=[5, 5, 5], start="2026-03-01 10:00")
    b = make_games(["win"] * 6, gap_minutes=[5] * 5, start="2026-03-09 10:00")
    g = I.enrich_games(pd.concat([a, b], ignore_index=True), "me")
    rep = weekly.weekly_report(g, pd.Timestamp("2026-03-10 00:00", tz="UTC"))
    assert rep["this"]["games"] == 6 and rep["previous"]["games"] == 4
    assert rep["this"]["score"] == 1.0 and rep["previous"]["score"] == 0.25
    assert rep["this"]["sessions"] == 1 and rep["this"]["longest_session"] == 6
    assert rep["this"]["minutes"] == 6 * 5
    assert list(rep["daily"]["games"]) == [6]


def test_rule_adherence_counts_stops_and_continuations():
    # session 1: L L L then stops (reaches rule n=3, stops); session 2: L L L then plays on (continues); session 3: W W (never reaches)
    results = ["loss", "loss", "loss", "loss", "loss", "loss", "win", "win", "win"]
    # break into sessions with long gaps: games 1-3, 4-7, 8-9
    gaps = [2, 2, 200, 2, 2, 2, 200, 2]
    g = _g(results, gaps)
    r = weekly.rule_adherence(g, 3)
    assert r["reached"] == 2 and r["continued"] == 1 and r["stopped"] == 1 and abs(r["adherence"] - 0.5) < 1e-9
    assert len(r["continued_games"]) == 1
    assert weekly.rule_adherence(g, 6)["reached"] == 0
    assert weekly.rule_adherence(g.iloc[0:0], 3)["reached"] == 0
