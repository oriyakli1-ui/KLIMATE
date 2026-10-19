"""Opening Damage Report: how good is your position after 10 moves, per opening and colour?

Results mix opening, middlegame and endgame. The engine evaluation right after move 10
(half-move 20) isolates the opening: an opening that regularly leaves you worse by then has an
opening problem, while one that is fine at move 10 but scores badly has a later-game problem.
Pure pandas; the engine call is injected so this module stays testable without Stockfish.
"""
from __future__ import annotations

import io
import math
from typing import Callable, Optional

import chess
import chess.pgn
import pandas as pd

from metrics import score_result

EVAL_PLY = 20          # evaluate after move 10 of each side
MIN_GAMES = 6
CAP = 5.0              # pawns; keeps one crushing evaluation from dominating an average
Z = 2.2                # several openings are compared at once, so a bit stricter than 1.96


def fen_after(pgn: str, plies: int = EVAL_PLY) -> Optional[str]:
    """FEN of the position after ``plies`` half-moves, or None when the game is shorter."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:  # noqa: BLE001
        return None
    if game is None:
        return None
    board = game.board()
    for n, move in enumerate(game.mainline_moves(), start=1):
        board.push(move)
        if n == plies:
            return board.fen()
    return None


def collect(games: pd.DataFrame, username: str, evaluate: Callable[[str], Optional[float]],
            progress: Optional[Callable[[int, int], None]] = None, limit: int = 400) -> pd.DataFrame:
    """One row per game: opening family, colour, result score and the evaluation after move 10 from the player's side.

    ``evaluate(fen)`` returns the engine evaluation in pawns from White's point of view (or None).
    """
    cols = ["opening", "color", "score", "eval"]
    me = username.strip().lower()
    rows = []
    recent = games.sort_values("date_utc", ascending=False).head(limit)
    total = len(recent)
    for i, r in enumerate(recent.itertuples(), start=1):
        white = str(r.white_player).strip().lower() == me
        opening = getattr(r, "opening", "")
        if opening and opening != "Unknown":
            fen = fen_after(r.pgn)
            ev = evaluate(fen) if fen else None
            score = score_result(r.white_result if white else r.black_result, r.black_result if white else r.white_result)
            if ev is not None and score is not None:
                v = max(-CAP, min(CAP, ev if white else -ev))
                rows.append({"opening": opening, "color": "White" if white else "Black", "score": score, "eval": v})
        if progress:
            progress(i, total)
    return pd.DataFrame(rows, columns=cols)


def report(df: pd.DataFrame, min_games: int = MIN_GAMES) -> pd.DataFrame:
    """Per (opening, colour): games, mean evaluation after move 10 with interval, score, and a verdict."""
    cols = ["opening", "color", "games", "eval", "eval_lo", "eval_hi", "score", "verdict"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    base_eval, base_score = float(df["eval"].mean()), float(df["score"].mean())
    n_all = len(df)
    rows = []
    for (op, col), grp in df.groupby(["opening", "color"]):
        n = len(grp)
        if n < min_games:
            continue
        m = float(grp["eval"].mean())
        sd = float(grp["eval"].std(ddof=1)) if n > 1 else float("nan")
        half = 1.96 * sd / math.sqrt(n) if sd == sd else float("nan")
        lo, hi = m - half, m + half
        sd_all = float(df["eval"].std(ddof=1))
        z_eval = (m - base_eval) / math.sqrt(sd ** 2 / n + sd_all ** 2 / n_all) if sd == sd and sd_all > 0 else 0.0
        s = float(grp["score"].mean())
        z_score = (s - base_score) / math.sqrt(0.25 / n + 0.25 / n_all)
        if z_eval <= -Z:
            verdict = "Opening problem: you are worse than usual by move 10"
        elif z_score <= -Z and z_eval > -1.0:
            verdict = "Later-game problem: fine at move 10 but poor results"
        elif z_eval >= Z:
            verdict = "Strong opening: better than usual by move 10"
        else:
            verdict = "Within normal range"
        rows.append({"opening": op, "color": col, "games": n, "eval": m, "eval_lo": lo, "eval_hi": hi, "score": s, "verdict": verdict})
    return pd.DataFrame(rows, columns=cols).sort_values("eval").reset_index(drop=True)
