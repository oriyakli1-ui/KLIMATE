"""Playing-style profile computed from the actual moves, used for the playful grandmaster match."""
from __future__ import annotations

import io
from typing import Dict, Tuple

import chess
import chess.pgn
import pandas as pd

ARCHETYPES = {
    "tal": ("Mikhail Tal", "Attacking wizard: short, sharp games full of captures and checks."),
    "kasparov": ("Garry Kasparov", "Dynamic and fierce: long games with constant initiative."),
    "karpov": ("Anatoly Karpov", "Solid and positional: few forcing moves, patient squeeze."),
    "nakamura": ("Hikaru Nakamura", "Fast and practical: quick games, direct decisions."),
    "carlsen": ("Magnus Carlsen", "Universal: balanced mix of tension and patience."),
}
ACTION_HIGH, ACTION_LOW, LONG_GAME, SHORT_GAME = 0.27, 0.18, 30, 22


def style_profile(games_df: pd.DataFrame, username: str, max_games: int = 150) -> Dict[str, float]:
    """Average moves per game and the share of the player's moves that are captures or checks."""
    u = username.strip().lower()
    moves = actions = games = 0
    for row in games_df.head(max_games).itertuples():
        pgn = getattr(row, "pgn", "")
        if not isinstance(pgn, str) or not pgn.strip():
            continue
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
        except Exception:
            continue
        if game is None:
            continue
        mine = chess.WHITE if (game.headers.get("White", "") or "").lower() == u else chess.BLACK
        board, n = game.board(), 0
        for mv in game.mainline_moves():
            if board.turn == mine:
                n += 1
                if board.is_capture(mv) or board.gives_check(mv):
                    actions += 1
            board.push(mv)
        if n:
            games += 1
            moves += n
    if not games:
        return {"games": 0, "avg_moves": float("nan"), "action_rate": float("nan")}
    return {"games": games, "avg_moves": moves / games, "action_rate": actions / moves}


def match_archetype(profile: Dict[str, float]) -> Tuple[str, str]:
    """Pick the closest archetype. Playful, not scientific: thresholds are rough club-level values."""
    if not profile.get("games"):
        return "Unknown (play more games!)", ""
    a, length = profile["action_rate"], profile["avg_moves"]
    if a >= ACTION_HIGH and length <= SHORT_GAME:
        key = "tal"
    elif a >= ACTION_HIGH:
        key = "kasparov"
    elif a <= ACTION_LOW and length >= LONG_GAME:
        key = "karpov"
    elif length <= SHORT_GAME:
        key = "nakamura"
    else:
        key = "carlsen"
    name, blurb = ARCHETYPES[key]
    return name, blurb
