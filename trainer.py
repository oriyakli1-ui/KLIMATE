"""Blunder Trainer: turns the player's own engine-detected mistakes into multiple-choice puzzles (pure, tested)."""
from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional

import chess
import pandas as pd

import analysis

MIN_LOSS = 20.0      # only mistakes that gave away 20+ win-chance points become puzzles
MAX_PUZZLES = 12


def build_puzzles(
    games_df: pd.DataFrame,
    username: str,
    eval_fn: Callable[[str], pd.DataFrame],
    n_games: int = 20,
    per_game: int = 2,
    progress: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, object]]:
    """Puzzles from the player's most recent games. ``eval_fn(pgn)`` returns the per-ply engine evaluations."""
    if games_df is None or games_df.empty:
        return []
    recent = games_df.sort_values("date_utc", ascending=False).head(n_games).reset_index(drop=True)
    puzzles: List[Dict[str, object]] = []
    for i, row in recent.iterrows():
        pgn = row.get("pgn")
        if isinstance(pgn, str) and pgn.strip():
            ev = eval_fn(pgn)
            for m in analysis.key_moments(ev, pgn, username, top=per_game):
                if m["best_uci"] and m["best_uci"] != m["played_uci"] and m["win_loss"] >= MIN_LOSS:
                    puzzles.append({**m, "url": row.get("url", ""), "date": row.get("date_utc")})
        if progress:
            progress(i + 1, len(recent))
    puzzles.sort(key=lambda p: p["win_loss"], reverse=True)
    return puzzles[:MAX_PUZZLES]


def make_options(fen: str, best_uci: str, played_uci: str, seed: int = 0, extra: int = 2) -> List[Dict[str, str]]:
    """Answer choices: the engine's move, the move actually played, and up to ``extra`` other legal moves."""
    board = chess.Board(fen)
    legal = [m.uci() for m in board.legal_moves]
    others = [u for u in legal if u not in (best_uci, played_uci)]
    rng = random.Random(seed)
    picks = rng.sample(others, min(extra, len(others)))
    chosen = [best_uci] + ([played_uci] if played_uci in legal else []) + picks
    rng.shuffle(chosen)
    return [{"uci": u, "san": board.san(chess.Move.from_uci(u))} for u in chosen if u in legal]
