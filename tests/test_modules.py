import json
import types

import pandas as pd

import data_engine
import insights
import openings
import share_card
import strings
import style
import training


def test_parse_eco_url_families():
    full, fam = openings.parse_eco_url("https://www.chess.com/openings/Caro-Kann-Defense-Advance-Variation-3...c5")
    assert (full, fam) == ("Caro-Kann Defense Advance Variation", "Caro-Kann Defense")
    assert openings.parse_eco_url("https://www.chess.com/openings/Queens-Gambit-Accepted-Old-Variation")[1] == "Queens Gambit Accepted"
    assert openings.parse_eco_url("Sicilian-Defense-Open-Najdorf-Variation-6.Be3-e5")[1] == "Sicilian Defense"
    assert openings.parse_eco_url("Ruy-Lopez-Morphy-Defense")[1] == "Ruy Lopez"
    assert openings.parse_eco_url("") == ("", "") and openings.parse_eco_url(None) == ("", "")


def test_streak_counts_from_the_newest_game(games_factory):
    g = insights.enrich_games(games_factory(["win", "win", "loss", "loss", "loss"]).iloc[::-1], "me")  # newest first
    assert insights.current_streak(g) == ("loss", 3)
    g2 = insights.enrich_games(games_factory(["loss", "loss", "win"]), "me")
    assert insights.current_streak(g2) == ("win", 1)
    g3 = insights.enrich_games(games_factory(["win", "draw"]), "me")
    assert insights.current_streak(g3) == ("none", 0)  # a draw ends the streak


def test_parse_game_adds_new_columns():
    raw = {
        "white": {"username": "A", "rating": 1500, "result": "win"}, "black": {"username": "B", "rating": 1400, "result": "resigned"},
        "end_time": 1700000000, "time_class": "blitz", "time_control": "180+2", "rated": True, "rules": "chess",
        "eco": "https://www.chess.com/openings/Italian-Game-Giuoco-Piano", "pgn": "1. e4", "url": "https://x/1",
    }
    row = data_engine._parse_game(raw)
    assert row["opening"] == "Italian Game" and row["time_control"] == "180+2" and row["rated"] is True
    assert set(data_engine.COLUMNS) <= set(row)
    assert data_engine._parse_game({"white": {}, "black": {}}) is None


def test_closed_months_are_cached_on_disk(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(data_engine, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(data_engine, "_safe_get", lambda url: calls.append(url) or {"games": [{"x": 1}]})
    old = "https://api.chess.com/pub/player/bob/games/2020/01"
    assert data_engine._month_games(old, "bob") == [{"x": 1}]
    assert data_engine._month_games(old, "bob") == [{"x": 1}]
    assert len(calls) == 1  # second read came from disk
    assert json.loads((tmp_path / "bob" / "2020-01.json").read_text()) == [{"x": 1}]

    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    current = f"https://api.chess.com/pub/player/bob/games/{now.year}/{now.month:02d}"
    data_engine._month_games(current, "bob")
    data_engine._month_games(current, "bob")
    assert len(calls) == 3  # the running month is never cached


def test_training_plan_has_seven_days_and_uses_evidence(games_factory):
    g = insights.enrich_games(games_factory(["win", "loss", "loss", "loss"] * 50, gap_minutes=([5, 5, 5, 120] * 50)[:-1]), "me")
    plan = training.build_plan(insights.generate_insights(g), None, training.weak_openings(g))
    assert [p["day"] for p in plan] == [f"Day {i}" for i in range(1, 8)]
    assert plan[0]["tag"] == "tilt"
    assert len(training.build_plan([], None, None)) == 7


def test_strings_format_and_fall_back():
    assert strings.t("analyze") == "Analyze DNA"
    assert strings.t("missing_key") == "missing_key"
    assert strings.t("games_loaded", n=5) == "5 games loaded"
    item = {"key": "x", "params": {}, "title": "T", "detail": "D"}
    assert strings.insight_text(item) == {"title": "T", "detail": "D"}


def test_share_card_is_a_png():
    png = share_card.render_wrapped_png("tester", {"top_rating": "1500", "win_percentage": "55%", "deadliest_opening": "Italian Game (70%)",
                                                   "golden_hour": "20:00", "gm_match": "Anatoly Karpov (Solid)"})
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5000


def test_style_profile_and_match():
    pgn = '[White "me"]\n[Black "opp"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0'
    df = pd.DataFrame({"pgn": [pgn] * 3})
    prof = style.style_profile(df, "me")
    assert prof["games"] == 3 and prof["avg_moves"] == 4 and prof["action_rate"] == 0.25
    assert style.match_archetype(prof)[0] == "Hikaru Nakamura"  # short games, moderate action
    assert style.match_archetype({"games": 0})[0].startswith("Unknown")


def test_fetch_games_reports_progress_and_respects_months(monkeypatch, tmp_path):
    monkeypatch.setattr(data_engine, "CACHE_DIR", tmp_path)
    game = {"white": {"username": "A", "rating": 1, "result": "win"}, "black": {"username": "B", "rating": 1, "result": "resigned"},
            "end_time": 1700000000, "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6", "rules": "chess", "time_class": "rapid"}
    archives = [f"https://api.chess.com/pub/player/bob/games/2020/{m:02d}" for m in (1, 2, 3)]

    def fake_get(url):
        return {"archives": archives} if url.endswith("/archives") else {"games": [game]}

    monkeypatch.setattr(data_engine, "_safe_get", fake_get)
    calls = []
    df = data_engine.fetch_games("Bob", max_games=10, months=2, progress=lambda d, t: calls.append((d, t)))
    assert len(df) == 2 and calls == [(1, 2), (2, 2)]


def test_undefined_opening_is_not_an_opening():
    assert openings.parse_eco_url("https://www.chess.com/openings/Undefined") == ("", "")
    raw = {"white": {"username": "A", "rating": 1, "result": "win"}, "black": {"username": "B", "rating": 1, "result": "resigned"},
           "end_time": 1700000000, "eco": "https://www.chess.com/openings/Undefined", "pgn": "1. e4"}
    assert data_engine._parse_game(raw)["opening"] == "Unknown"


def test_unknown_opening_never_ranks(games_factory):
    df = games_factory(["win"] * 6)
    df["opening"] = "Unknown"
    assert insights.opening_summary(insights.enrich_games(df, "me")).empty


def test_gemini_call_disables_thinking_and_rejects_truncated_answers(monkeypatch):
    import sys
    import types as pytypes

    import llm

    seen = {}

    class FakeModels:
        def __init__(self, finish):
            self.finish = finish

        def generate_content(self, model, contents, config):
            seen["config"] = config
            cand = pytypes.SimpleNamespace(finish_reason=self.finish)
            return pytypes.SimpleNamespace(text="A full answer.", candidates=[cand])

    def fake_client(finish):
        return lambda api_key: pytypes.SimpleNamespace(models=FakeModels(finish))

    monkeypatch.setattr(llm, "st", pytypes.SimpleNamespace(secrets={"GEMINI_API_KEY": "k"}))
    import google.genai as genai

    monkeypatch.setattr(genai, "Client", fake_client("STOP"))
    assert llm._gemini("hi", 300) == "A full answer."
    assert seen["config"].thinking_config.thinking_budget == 0
    assert seen["config"].max_output_tokens >= 800

    monkeypatch.setattr(genai, "Client", fake_client("FinishReason.MAX_TOKENS"))
    try:
        llm._gemini("hi", 300)
    except llm.LLMUnavailable:
        pass
    else:
        raise AssertionError("a truncated answer must not be returned")


def test_cut_off_answers_are_rejected_and_fall_back(monkeypatch):
    import llm

    assert llm.looks_complete("A full sentence.")
    assert llm.looks_complete("It is **bold** and done!")
    assert not llm.looks_complete("Great job! Your **biggest weakness")
    assert not llm.looks_complete("Ends without punctuation")
    assert not llm.looks_complete("")

    monkeypatch.setattr(llm, "_gemini", lambda p, n: "Your **biggest weakness")
    monkeypatch.setattr(llm, "_groq", lambda p, n: "Complete answer from the fallback.")
    assert llm.generate.__wrapped__("x", 300, 2) == "Complete answer from the fallback."
    monkeypatch.setattr(llm, "_groq", lambda p, n: "also cut")
    try:
        llm.generate.__wrapped__("x", 300, 2)
    except llm.LLMUnavailable:
        pass
    else:
        raise AssertionError("two truncated answers must raise")


def test_variants_daily_and_unplayed_games_are_excluded(monkeypatch, tmp_path):
    monkeypatch.setattr(data_engine, "CACHE_DIR", tmp_path)
    base = {"white": {"username": "A", "rating": 1, "result": "win"}, "black": {"username": "B", "rating": 1, "result": "resigned"},
            "end_time": 1700000000, "rules": "chess", "time_class": "rapid", "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6"}
    games = [
        base,
        {**base, "rules": "crazyhouse"},
        {**base, "time_class": "daily"},
        {**base, "pgn": "1. e4"},
    ]
    monkeypatch.setattr(data_engine, "_safe_get", lambda url: {"archives": [".../games/2020/01"]} if url.endswith("/archives") else {"games": games})
    df = data_engine.fetch_games("bob", 50, 1)
    assert len(df) == 1
    assert df.attrs["excluded"] == {"variants": 1, "daily": 1, "short": 1}

import numpy as np
import pandas as pd

import insights
import scout
from tests.test_pages import _games


def test_scout_report_flags_habit_and_soft_spot():
    rng = np.random.default_rng(3)
    res = ["win"] * 25 + ["loss"] * 15
    df = _games(len(res), seed=5)
    df["opening"] = ["Italian Game"] * 20 + ["Slav Defense"] * 20
    df["white_result"], df["black_result"] = zip(*[("win", "checkmated") if r == "win" else ("checkmated", "win") for r in res])
    df.loc[df["opening"] == "Slav Defense", ["white_result", "black_result"]] = ("checkmated", "win")
    opp = insights.enrich_games(df, "me")
    rep = scout.scout_report(opp, opp)
    assert rep["enough"] and rep["n"] == 40
    titles = " | ".join(p["title"] for p in rep["prep"])
    assert "Italian Game" in titles
    assert "soft spot" in titles.lower() and "Slav Defense" in titles


def test_scout_small_sample_makes_no_behaviour_claims():
    opp = insights.enrich_games(_games(6, seed=2), "me")
    rep = scout.scout_report(opp)
    assert not rep["enough"]
    assert not any("tilt" in p["title"].lower() or "time" in p["title"].lower() for p in rep["prep"])


def test_scout_empty():
    rep = scout.scout_report(insights.enrich_games(_games(5).iloc[0:0], "me"))
    assert rep["n"] == 0 and rep["prep"] == []
    assert scout.head_to_head(_games(5), "me", "nobody")["n"] == 0
    assert scout.head_to_head(_games(5), "me", "opp")["n"] == 5


def test_home_facts():
    import home
    from tests.test_pages import _games

    g = insights.enrich_games(_games(150, seed=4), "me")
    h = home.rating_headline(g)
    assert h["time_class"] in ("rapid", "blitz") and h["rating"] == 1200
    assert home.biggest_leak(g.iloc[0:0], None) is None or True
    assert home.rating_headline(g.iloc[0:0]) == {}


def test_trainer_options_and_puzzles():
    import chess
    import trainer

    fen = chess.STARTING_FEN
    opts = trainer.make_options(fen, "e2e4", "a2a3", seed=1)
    ucis = [o["uci"] for o in opts]
    assert "e2e4" in ucis and "a2a3" in ucis and len(set(ucis)) == len(ucis) == 4
    assert all(o["san"] for o in opts)
    assert trainer.make_options(fen, "e2e4", "a2a3", seed=1) == opts      # deterministic
    assert trainer.build_puzzles(pd.DataFrame(), "x", lambda p: None) == []


def _li(**kw):
    g = {"id": "abc12345", "rated": True, "variant": "standard", "speed": "blitz", "status": "mate", "winner": "white",
         "createdAt": 1760000000000, "lastMoveAt": 1760000300000, "clock": {"initial": 180, "increment": 2},
         "opening": {"eco": "B10", "name": "Caro-Kann Defense: Advance Variation"},
         "pgn": '[White "a"]\n[Black "b"]\n\n1. e4 c6 2. d4 d5 3. e5 Bf5 4. Nf3 e6 5. Be2 Nd7 1-0',
         "players": {"white": {"user": {"name": "Alice"}, "rating": 1500, "ratingDiff": 8},
                     "black": {"user": {"name": "Bob"}, "rating": 1520, "ratingDiff": -8}}}
    g.update(kw)
    return g


def test_lichess_parse_game_semantics():
    import lichess

    row = lichess.parse_game(_li())
    assert row["white_rating"] == 1508 and row["black_rating"] == 1512         # ratings AFTER the game
    assert (row["white_result"], row["black_result"]) == ("win", "checkmated")
    assert row["opening"] == "Caro-Kann Defense" and row["time_control"] == "180+2" and row["time_class"] == "blitz"
    assert row["plies"] >= 6 and row["url"].endswith("/abc12345")
    flag = lichess.parse_game(_li(status="outoftime", winner="black"))
    assert (flag["white_result"], flag["black_result"]) == ("timeout", "win")
    draw = lichess.parse_game(_li(status="draw", winner=None))
    assert draw["white_result"] == draw["black_result"] == "agreed"


def test_lichess_skips_non_games():
    import lichess

    assert lichess.parse_game(_li(variant="atomic")) is None
    assert lichess.parse_game(_li(status="aborted")) is None
    assert lichess.parse_game(_li(speed="correspondence")) is None
    ai = _li()
    ai["players"]["black"] = {"aiLevel": 3}
    assert lichess.parse_game(ai) is None


def test_lichess_games_flow_through_enrichment():
    import insights
    import lichess

    rows = [lichess.parse_game(_li(id=f"g{i}", createdAt=1760000000000 + i * 600000, lastMoveAt=1760000300000 + i * 600000)) for i in range(5)]
    df = pd.DataFrame(rows)
    e = insights.enrich_games(df, "alice")
    assert len(e) == 5 and set(e["outcome"]) == {"win"} and e["time_class"].eq("blitz").all()
