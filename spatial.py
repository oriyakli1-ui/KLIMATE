"""Where a player moves pieces and where their pieces get captured (pure, tested).

Maps are always from the PLAYER'S side of the board: rank 1 is the player's own back rank,
whichever colour they had. Mixing White and Black games on absolute squares would blur
two opposite perspectives into one meaningless map.
"""
from __future__ import annotations

import io
from typing import Iterable, Tuple

import chess
import chess.pgn
import numpy as np

PIECE_FILTER_MAP = {
    "All": None, "All Pieces": None, "Pawn": chess.PAWN, "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP, "Rook": chess.ROOK, "Queen": chess.QUEEN, "King": chess.KING,
}


def _cell(square: int, player_is_white: bool) -> Tuple[int, int]:
    """(row, col) of a square with row 0 = the player's own back rank, col 0 = file a."""
    rank, file_ = chess.square_rank(square), chess.square_file(square)
    return (rank if player_is_white else 7 - rank), file_


def heatmaps(games: Iterable[Tuple[str, bool]], piece_filter: str = "All") -> Tuple[np.ndarray, np.ndarray, int]:
    """Build the maps from ``(pgn, player_is_white)`` pairs.

    Returns ``(activity, captured, games_used)``:
    - activity: destination squares of the player's moves (optionally one piece type)
    - captured: squares where the opponent captured one of the player's pieces
      (a capture is counted even when the player recaptured: it shows where pieces get traded or lost)
    """
    wanted = PIECE_FILTER_MAP.get((piece_filter or "All").strip(), None)
    activity = np.zeros((8, 8))
    captured = np.zeros((8, 8))
    used = 0
    for pgn, is_white in games:
        if not isinstance(pgn, str) or not pgn.strip():
            continue
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
        except Exception:  # noqa: BLE001 - one broken PGN must not break the page
            continue
        if game is None:
            continue
        color = chess.WHITE if is_white else chess.BLACK
        try:
            board = game.board()
            for move in game.mainline_moves():
                if board.turn == color:
                    piece = board.piece_at(move.from_square)
                    if piece is not None and (wanted is None or piece.piece_type == wanted):
                        r, c = _cell(move.to_square, is_white)
                        activity[r, c] += 1
                elif board.is_capture(move):
                    if board.is_en_passant(move):
                        square = move.to_square + (-8 if board.turn == chess.WHITE else 8)
                        piece = board.piece_at(square)
                    else:
                        square = move.to_square
                        piece = board.piece_at(square)
                    if piece is not None and piece.color == color and (wanted is None or piece.piece_type == wanted):
                        r, c = _cell(square, is_white)
                        captured[r, c] += 1
                board.push(move)
            used += 1
        except Exception:  # noqa: BLE001
            continue
    return activity, captured, used
