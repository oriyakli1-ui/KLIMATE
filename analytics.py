"""Engine evaluation (local Stockfish, chess-api.com fallback) and live Chess.com ratings."""
from __future__ import annotations

import io
import logging
import os
import shutil
import time
from typing import Dict

import chess
import chess.pgn
import pandas as pd
import requests
import streamlit as st

from llm import coach_explanation as get_gemini_coach_explanation  # noqa: F401  (kept for callers)
from uci import UciEngine

TIME_CLASSES = ("rapid", "blitz", "bullet")
_NA = "N/A"


@st.cache_data(show_spinner=False, ttl=300)
def _fetch_stats(username: str) -> dict:
    """Chess.com stats JSON. Raises on failure so that an error is never cached."""
    last_exc: Exception | None = None
    for attempt in range(2):  # one retry: Chess.com occasionally answers 429/5xx for a moment
        try:
            resp = requests.get(
                f"https://api.chess.com/pub/player/{username}/stats",
                headers={"User-Agent": "Klimate Chess Analytics/1.0 (+https://github.com/oriyakli1-ui/KLIMATE)"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(1.0)
    raise RuntimeError(f"stats request failed: {last_exc}")


def _rating(block: object, which: str) -> object:
    value = ((block or {}).get(which) or {}).get("rating") if isinstance(block, dict) else None
    return int(value) if isinstance(value, (int, float)) else _NA


@st.cache_data(show_spinner=False, ttl=300)
def _lichess_ratings(name: str) -> dict:
    import lichess

    return lichess.fetch_ratings(name)


def get_real_time_ratings(username: str, platform: str | None = None) -> Dict[str, object]:
    """Current and all-time-best ratings from the Chess.com stats API (or Lichess when the session's platform is Lichess).

    Keys: ``rapid``/``blitz``/``bullet`` (current), ``best`` (same keys, all-time best),
    ``peak`` (highest best rating of the three) and ``peak_class``. Values are ints or 'N/A'.
    """
    name = (username or "").strip().lower()
    empty = {**{c: _NA for c in TIME_CLASSES}, "best": {c: _NA for c in TIME_CLASSES}, "peak": _NA, "peak_class": ""}
    if not name:
        return empty
    if (platform or st.session_state.get("platform", "chesscom")) == "lichess":
        return _lichess_ratings(name)
    try:
        data = _fetch_stats(name)
    except Exception:  # noqa: BLE001 - network/JSON problems: show N/A rather than guess
        return empty
    current = {c: _rating(data.get(f"chess_{c}"), "last") for c in TIME_CLASSES}
    best = {c: _rating(data.get(f"chess_{c}"), "best") for c in TIME_CLASSES}
    known = {c: v for c, v in best.items() if isinstance(v, int)}
    peak_class = max(known, key=known.get) if known else ""
    return {**current, "best": best, "peak": known[peak_class] if peak_class else _NA, "peak_class": peak_class}


@st.cache_data(show_spinner=False)
def analyze_game_with_chess_api(pgn_string: str, max_plies: int = 40) -> pd.DataFrame:
    """
    Analyze a game with an external engine API (chess-api.com).

    For each ply, advances the game one move, posts the resulting FEN to the API,
    and records evaluation + best move.

        POST:
        https://chess-api.com/v1
        json={"fen": fen, "depth": 6}

    Parameters
    ----------
    pgn_string : str
        PGN text.
    max_plies : int, optional
        Maximum plies (half-moves) to analyze, by default 40.

    Returns
    -------
    pd.DataFrame
        Columns: ['ply', 'move_san', 'evaluation', 'best_move'].
        Evaluation is in pawns, with mate capped to +/- 10.
    """
    if not isinstance(pgn_string, str) or not pgn_string.strip() or max_plies <= 0:
        return pd.DataFrame(columns=["ply", "move_san", "evaluation", "best_move"])

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_string))
    except Exception:
        return pd.DataFrame(columns=["ply", "move_san", "evaluation", "best_move"])
    if game is None:
        return pd.DataFrame(columns=["ply", "move_san", "evaluation", "best_move"])

    board = game.board()
    rows = []
    prev_eval = 0.0
    prev_best = ""

    for ply_idx, move in enumerate(game.mainline_moves(), start=1):
        if ply_idx > max_plies:
            break

        try:
            move_san = board.san(move)
        except Exception:
            move_san = ""

        try:
            board.push(move)
        except Exception:
            break

        fen = board.fen()
        eval_now = prev_eval
        best_move = prev_best

        try:
            resp = requests.post(
                "https://chess-api.com/v1",
                json={"fen": fen, "depth": 6},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}

            # best move (UCI). Keep this strict-first so downstream SVG arrows work.
            best_move = data.get("bestmove", "") or ""
            if not best_move:
                best_move = (
                    data.get("best_move")
                    or data.get("move")
                    or data.get("san")
                    or ""
                )

            # evaluation: prefer eval in pawns, else centipawns, else mate
            if data.get("mate") is not None:
                mate_val = float(data.get("mate"))
                eval_now = 10.0 if mate_val > 0 else -10.0
            elif data.get("eval") is not None:
                eval_now = float(data.get("eval"))
            elif data.get("evaluation") is not None:
                eval_now = float(data.get("evaluation"))
            elif data.get("centipawns") is not None:
                eval_now = float(data.get("centipawns")) / 100.0
            elif data.get("cp") is not None:
                eval_now = float(data.get("cp")) / 100.0
        except Exception:
            # Unknown, not "same as before": copying the previous eval would draw a
            # believable-looking but invented line. NaN is skipped by blunder detection.
            eval_now = float("nan")
            best_move = ""

        rows.append(
            {
                "ply": ply_idx,
                "move_san": move_san,
                "evaluation": float(eval_now),
                "best_move": str(best_move),
            }
        )
        prev_eval = float(eval_now)
        prev_best = str(best_move)
        time.sleep(0.02)

    return pd.DataFrame(rows, columns=["ply", "move_san", "evaluation", "best_move"])

log = logging.getLogger(__name__)


def _find_stockfish() -> str | None:
    """Path of a local Stockfish binary, or None (set STOCKFISH_PATH to override)."""
    for cand in (
        os.environ.get("STOCKFISH_PATH"),
        shutil.which("stockfish"),
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


@st.cache_data(show_spinner=False)
def analyze_game_with_stockfish(pgn_string: str, max_plies: int = 150, depth: int = 12) -> pd.DataFrame:
    """Evaluate every position of a game with a local Stockfish (white's point of view, in pawns).

    Same columns as ``analyze_game_with_chess_api``. Returns an empty frame when no
    engine is installed or it fails to start, so callers can fall back.
    """
    empty = pd.DataFrame(columns=["ply", "move_san", "evaluation", "best_move"])
    path = _find_stockfish()
    if not path or not isinstance(pgn_string, str) or not pgn_string.strip():
        return empty
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_string))
        engine = UciEngine(path)
    except Exception:
        log.exception("Stockfish failed to start (%s)", path)
        return empty
    if game is None:
        engine.close()
        return empty

    rows = []
    try:
        board = game.board()
        for ply, move in enumerate(game.mainline_moves(), start=1):
            if ply > max_plies:
                break
            san = board.san(move)
            board.push(move)
            cp, best = engine.analyse(board.fen(), depth)
            if cp is None:
                continue
            rows.append(
                {
                    "ply": ply,
                    "move_san": san,
                    "evaluation": float(max(-10.0, min(10.0, cp / 100.0))),
                    "best_move": best,
                }
            )
    except Exception:
        log.exception("Stockfish analysis failed")
    finally:
        engine.close()
    return pd.DataFrame(rows, columns=["ply", "move_san", "evaluation", "best_move"])


def analyze_game(pgn_string: str) -> pd.DataFrame:
    """Best available analysis: local Stockfish (full game) else the chess-api.com HTTP service.

    Adds a ``source`` column so the UI can say what produced the numbers.
    """
    df = analyze_game_with_stockfish(pgn_string)
    if not df.empty:
        df = df.copy()
        df["source"] = "Stockfish"
        return df
    df = analyze_game_with_chess_api(pgn_string, max_plies=40).copy()
    df["source"] = "chess-api.com"
    return df
