import json
import types

import pandas as pd

import analytics
import data_engine
import i18n
import insights
import openings
import share_card
import style
import training


def test_parse_eco_url_families():
    full, fam = openings.parse_eco_url("https://www.chess.com/openings/Caro-Kann-Defense-Advance-Variation-3...c5")
    assert (full, fam) == ("Caro-Kann Defense Advance Variation", "Caro-Kann Defense")
    assert openings.parse_eco_url("https://www.chess.com/openings/Queens-Gambit-Accepted-Old-Variation")[1] == "Queens Gambit Accepted"
    assert openings.parse_eco_url("Sicilian-Defense-Open-Najdorf-Variation-6.Be3-e5")[1] == "Sicilian Defense"
    assert openings.parse_eco_url("Ruy-Lopez-Morphy-Defense")[1] == "Ruy Lopez"
    assert openings.parse_eco_url("") == ("", "") and openings.parse_eco_url(None) == ("", "")


def test_streak_counts_from_the_newest_game():
    df = pd.DataFrame({
        "date_utc": pd.to_datetime(["2026-01-03", "2026-01-01", "2026-01-02"], utc=True),
        "user_result": ["checkmated", "win", "win"],  # newest game is the loss
    })
    _, streak = analytics.get_current_profile_stats(df)
    assert "1 Loss" in streak
    df2 = df.assign(user_result=["win", "checkmated", "checkmated"])
    assert "1 Win" in analytics.get_current_profile_stats(df2)[1]


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


def test_i18n_falls_back_and_translates_insights(monkeypatch):
    fake = types.SimpleNamespace(session_state={"lang": "he"})
    monkeypatch.setattr(i18n, "st", fake)
    assert i18n.t("analyze") == "נתח את ה-DNA"
    assert i18n.t("missing_key") == "missing_key"
    item = {"key": "stop_loss", "params": {"n": 1, "es": "", "plus": "", "score": "30%", "baseline": "50%", "games": 40},
            "title": "en", "detail": "en"}
    assert "הפסד אחד" in i18n.insight_text(item)["title"]
    fake.session_state["lang"] = "en"
    assert i18n.insight_text(item)["title"] == "en"


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
            "end_time": 1700000000, "pgn": "1. e4"}
    archives = [f"https://api.chess.com/pub/player/bob/games/2020/{m:02d}" for m in (1, 2, 3)]

    def fake_get(url):
        return {"archives": archives} if url.endswith("/archives") else {"games": [game]}

    monkeypatch.setattr(data_engine, "_safe_get", fake_get)
    calls = []
    df = data_engine.fetch_games("Bob", max_games=10, months=2, progress=lambda d, t: calls.append((d, t)))
    assert len(df) == 2 and calls == [(1, 2), (2, 2)]
