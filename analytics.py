from __future__ import annotations

import io
import time
from typing import Dict, List, Tuple

import chess
import chess.pgn
import numpy as np
import pandas as pd
import requests
import streamlit as st
import google.generativeai as genai

from data_engine import ChessComAPIError, fetch_player_games


def _filter_player_games(df: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Return only games where the given username participated.
    """
    username = username.strip().lower()
    if df.empty or not username:
        return df.iloc[0:0]

    mask = (df["white_player"].str.lower() == username) | (
        df["black_player"].str.lower() == username
    )
    return df.loc[mask].copy()


def _compute_results(series_white: pd.Series, series_black: pd.Series, is_white: pd.Series) -> pd.Series:
    """
    Internal helper to map Chess.com results to numeric score from the
    perspective of the player (`1`=win, `0.5`=draw, `0`=loss).
    """
    white_res = series_white.fillna("")
    black_res = series_black.fillna("")

    # Winner is whoever has result == "win"; everything else we treat as draw
    # for simplicity if no "win" flag is present.
    white_wins = white_res == "win"
    black_wins = black_res == "win"

    # Initialize with draws (0.5)
    score = pd.Series(0.5, index=series_white.index, dtype="float64")

    # White wins
    score = np.where(white_wins & is_white, 1.0, score)
    score = np.where(white_wins & ~is_white, 0.0, score)

    # Black wins
    score = np.where(black_wins & ~is_white, 1.0, score)
    score = np.where(black_wins & is_white, 0.0, score)

    return pd.Series(score, index=series_white.index, dtype="float64")


def calculate_true_win_rate(df: pd.DataFrame, username: str) -> float:
    """
    Calculate the true win rate for a given player.

    True win rate is defined as:
        (Wins + 0.5 * Draws) / Total_Games

    where wins/draws are computed from the perspective of `username`.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games as returned by `fetch_player_games`.
    username : str
        Chess.com username whose performance to evaluate.

    Returns
    -------
    float
        True win rate in the range [0.0, 1.0]. Returns 0.0 if there are no
        games for the given player.
    """
    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return 0.0

    is_white = player_games["white_player"].str.lower() == username.strip().lower()

    scores = _compute_results(
        series_white=player_games["white_result"],
        series_black=player_games["black_result"],
        is_white=is_white,
    )

    total_games = len(scores)
    if total_games == 0:
        return 0.0

    true_win_rate = float(scores.sum() / total_games)
    return true_win_rate


def calculate_performance_rating(df: pd.DataFrame, username: str) -> float:
    """
    Calculate a FIDE-style performance rating approximation for a player.

    Formula:
        Performance = Average_Opponent_Rating
                      + 400 * (Wins - Losses) / Total_Games

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games as returned by `fetch_player_games`.
    username : str
        Chess.com username whose performance rating to compute.

    Returns
    -------
    float
        Estimated performance rating. Returns NaN if ratings are unavailable
        or there are no games for the player.
    """
    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return float("nan")

    username_lc = username.strip().lower()
    is_white = player_games["white_player"].str.lower() == username_lc

    # Opponent ratings (keep as Pandas Series for Pandas ops)
    opp_rating = player_games["black_rating"].where(is_white, player_games["white_rating"])
    opp_rating = pd.to_numeric(opp_rating, errors="coerce")

    if opp_rating.dropna().empty:
        return float("nan")

    avg_opp_rating = float(opp_rating.mean())

    scores = _compute_results(
        series_white=player_games["white_result"],
        series_black=player_games["black_result"],
        is_white=is_white,
    )

    total_games = len(scores)
    if total_games == 0:
        return float("nan")

    # Wins, draws, losses from scores
    wins = float((scores == 1.0).sum())
    losses = float((scores == 0.0).sum())

    performance = avg_opp_rating + 400.0 * (wins - losses) / float(total_games)
    return performance


def calculate_tilt_index(df: pd.DataFrame, username: str) -> Dict[str, float]:
    """
    Measure how a player's performance changes in games played immediately
    after a loss (a simple 'tilt' index).

    Steps:
    - Compute the baseline true win rate across all games.
    - Sort games chronologically.
    - Identify games played immediately after a loss.
    - Compute the true win rate on only those post-loss games.
    - Compare the two to compute tilt_drop_percentage.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games as returned by `fetch_player_games`.
    username : str
        Chess.com username whose tilt index to compute.

    Returns
    -------
    Dict[str, float]
        Dictionary with keys:
        - 'baseline_win_rate'
        - 'post_loss_win_rate'
        - 'tilt_drop_percentage' (negative if performance improves)
    """
    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return {
            "baseline_win_rate": 0.0,
            "post_loss_win_rate": 0.0,
            "tilt_drop_percentage": 0.0,
        }

    # Ensure chronological order
    if "date_utc" in player_games.columns:
        player_games = player_games.sort_values("date_utc", ascending=True).reset_index(drop=True)

    username_lc = username.strip().lower()
    is_white = player_games["white_player"].str.lower() == username_lc

    scores = _compute_results(
        series_white=player_games["white_result"],
        series_black=player_games["black_result"],
        is_white=is_white,
    )

    total_games = len(scores)
    if total_games == 0:
        return {
            "baseline_win_rate": 0.0,
            "post_loss_win_rate": 0.0,
            "tilt_drop_percentage": 0.0,
        }

    baseline_win_rate = float(scores.sum() / total_games)

    # Identify games that are immediately after a loss
    loss_indices = scores[scores == 0.0].index
    post_loss_indices = []
    for idx in loss_indices:
        next_idx = idx + 1
        if next_idx < len(scores):
            post_loss_indices.append(next_idx)

    if not post_loss_indices:
        # No games immediately after losses; no evidence of tilt.
        return {
            "baseline_win_rate": baseline_win_rate,
            "post_loss_win_rate": baseline_win_rate,
            "tilt_drop_percentage": 0.0,
        }

    post_loss_scores = scores.iloc[post_loss_indices]
    post_loss_total = len(post_loss_scores)
    if post_loss_total == 0:
        post_loss_win_rate = baseline_win_rate
    else:
        post_loss_win_rate = float(post_loss_scores.sum() / post_loss_total)

    if baseline_win_rate == 0.0:
        tilt_drop_percentage = 0.0
    else:
        tilt_drop_percentage = (baseline_win_rate - post_loss_win_rate) / baseline_win_rate * 100.0

    return {
        "baseline_win_rate": baseline_win_rate,
        "post_loss_win_rate": post_loss_win_rate,
        "tilt_drop_percentage": tilt_drop_percentage,
    }


def analyze_openings(df: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Analyze performance per opening (or ECO) for a given player.

    The function groups games by an opening label, preferring the 'opening'
    column when available and falling back to 'eco' if 'opening' is empty.
    For each opening group, it computes:

    - Total games
    - True win rate
    - Performance rating

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games as returned by `fetch_player_games`.
    username : str
        Chess.com username whose openings to analyze.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - 'opening'
        - 'total_games'
        - 'true_win_rate'
        - 'performance_rating'
        Sorted by 'total_games' descending.
    """
    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return pd.DataFrame(
            columns=["opening", "total_games", "true_win_rate", "performance_rating"]
        )

    # Build an opening label that prefers 'opening' then 'eco'
    opening_series = player_games.get("opening", pd.Series(index=player_games.index, dtype="object")).fillna("")
    eco_series = player_games.get("eco", pd.Series(index=player_games.index, dtype="object")).fillna("")

    opening_label = opening_series.where(opening_series.str.len() > 0, eco_series)
    opening_label = opening_label.replace("", "Unknown")
    player_games = player_games.assign(opening_group=opening_label)

    records = []
    for opening_name, group in player_games.groupby("opening_group"):
        total_games = len(group)
        if total_games == 0:
            continue

        twr = calculate_true_win_rate(group, username)
        perf = calculate_performance_rating(group, username)

        records.append(
            {
                "opening": opening_name,
                "total_games": total_games,
                "true_win_rate": twr,
                "performance_rating": perf,
            }
        )

    if not records:
        return pd.DataFrame(
            columns=["opening", "total_games", "true_win_rate", "performance_rating"]
        )

    result_df = pd.DataFrame(records)
    result_df = result_df.sort_values("total_games", ascending=False).reset_index(drop=True)
    return result_df


def get_real_time_ratings(username: str) -> Dict[str, object]:
    """
    Fetch live ratings from the Chess.com public stats API for the given user.

    Returns a dict with keys 'rapid', 'blitz', 'bullet'. Values are ints when
    available or 'N/A' on any error or missing field.
    """
    username_clean = (username or "").strip().lower()
    if not username_clean:
        return {"rapid": "N/A", "blitz": "N/A", "bullet": "N/A"}

    url = f"https://api.chess.com/pub/player/{username_clean}/stats"
    headers = {"User-Agent": "KlimateApp/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
    except Exception:
        return {"rapid": "N/A", "blitz": "N/A", "bullet": "N/A"}

    def _extract(tc_key: str) -> object:
        try:
            rating = (
                data.get(tc_key, {})
                .get("last", {})
                .get("rating", "N/A")
            )
            return int(rating) if isinstance(rating, (int, float)) else "N/A"
        except Exception:
            return "N/A"

    return {
        "rapid": _extract("chess_rapid"),
        "blitz": _extract("chess_blitz"),
        "bullet": _extract("chess_bullet"),
    }


def get_gemini_coach_explanation(fen: str, actual_move: str, best_move: str, user_loss: float) -> str:
    """
    Use Gemini to generate a short coaching explanation for a specific blunder or key moment.
    """
    if not fen:
        return "AI Coach is currently resting. Position (FEN) is unavailable."

    prompt = (
        "You are an elite Chess Psychology Coach. "
        f"The current board position (FEN) is: {fen}. "
        f"The player played '{actual_move}', but the best engine move was '{best_move}'. "
        f"This mistake cost the player {user_loss:.2f} points in evaluation. "
        "Your goal is to explain the 'Why' behind the mistake from a human perspective. "
        "Analyze if this looks like: "
        "- Panic/Defensive oversight. "
        "- Greed (grabbing a pawn while ignoring a threat). "
        "- Tunnel vision (focusing on one area while missing the big picture). "
        "- Impatience in a winning position. "
        "Explain in 2-3 punchy, encouraging sentences. Focus on the human psychology of the error and give one actionable tip to avoid this pattern next time."
    )

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        # Prefer response.text when available
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "AI Coach is currently resting. The response did not contain usable text."
    except Exception as e:
        return "AI Coach is currently resting. Error: " + str(e)


def get_gemini_opening_deep_dive(opening_name: str) -> str:
    """
    Use Gemini to generate a structured grandmaster-level deep dive for an opening.
    """
    name = str(opening_name or "").strip()
    if not name or name.lower().startswith("choose"):
        return ""

    prompt = (
        'You are an elite Chess Grandmaster and coach. The user wants to study the opening: '
        f'"{name}". '
        "Provide a comprehensive but beautifully structured analysis. Include: "
        "1. Core Ideas & Philosophy of the opening. "
        "2. Main Variations. "
        "3. How to play WITH it (Attacking plans). "
        "4. How to play AGAINST it (Defensive plans). "
        "Format beautifully with markdown and emojis."
    )

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "AI Coach is currently resting. The response did not contain usable text."
    except Exception as e:
        return "AI Coach is currently resting. Error: " + str(e)


@st.cache_data(show_spinner=False, ttl=300)
def get_gemini_opening_masterclass(opening_name: str) -> str:
    """
    Use Gemini to generate a punchy, actionable masterclass for an opening,
    returning the FEN string on the first line.
    """
    name = str(opening_name or "").strip()
    if not name or name.lower().startswith("choose"):
        return ""

    prompt = (
        f'Analyze the chess opening "{name}". '
        "CRITICAL: The very first line of your response MUST be ONLY the standard FEN string of the position after the defining moves of this opening. "
        "Starting from the second line, provide a beautifully formatted, highly educational masterclass. "
        "Include: 1. The Core Idea. 2. How to defend against it (if the opponent plays it) with specific plans. 3. How to exploit it/gain an advantage. "
        "Use markdown, headers, and bullet points to make it visually accessible and easy to learn from."
    )

    try:
        import google.generativeai as genai
        import streamlit as st
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "AI Coach is currently resting. The response did not contain usable text."
    except Exception as e:
        return "AI Coach is currently resting. Error: " + str(e)


def get_current_profile_stats(df: pd.DataFrame) -> Tuple[Dict[str, object], str]:
    """
    Compute current ratings per time control and the user's current streak.

    The DataFrame is expected to be filtered to a single user and to include:
    - 'time_class'   (e.g., 'rapid', 'blitz', 'bullet')
    - 'user_rating'  (numeric)
    - 'user_result'  (string result from user's perspective)
    """
    if df is None or df.empty:
        return {"rapid": "N/A", "blitz": "N/A", "bullet": "N/A"}, "➖ 0"

    df_reversed = df.iloc[::-1].reset_index(drop=True)

    # Ratings are now obtained from the Chess.com API separately;
    # keep placeholders here for backward compatibility.
    ratings: Dict[str, object] = {"rapid": "N/A", "blitz": "N/A", "bullet": "N/A"}

    if "user_result" not in df_reversed.columns:
        return ratings, "➖ 0"

    loss_results = {"checkmated", "timeout", "resigned", "abandoned", "lose", "loss"}

    def _classify(res: object) -> str:
        r = str(res or "").strip().lower()
        if r == "win":
            return "WIN"
        if r in loss_results:
            return "LOSS"
        return "DRAW"

    outcomes = [_classify(r) for r in df_reversed["user_result"]]
    if not outcomes:
        return ratings, "➖ 0"

    first = outcomes[0]
    if first == "DRAW":
        return ratings, "➖ 0"

    streak_type = first
    streak_len = 0
    for o in outcomes:
        if o != streak_type:
            break
        streak_len += 1

    if streak_type == "WIN":
        streak_str = f"🔥 {streak_len} Wins"
    else:
        streak_str = f"🧊 {streak_len} Losses"

    return ratings, streak_str


@st.cache_data(show_spinner=False)
def analyze_time_of_day(
    df: pd.DataFrame, username: str, timezone: str = "Asia/Jerusalem"
) -> pd.DataFrame:
    """
    Analyze performance by hour of the day (Cognitive Clock) in a given timezone.

    Converts game timestamps from UTC to the given timezone, extracts the hour,
    and for each hour computes total_games and true_win_rate (Wins + 0.5*Draws)/Total
    from the perspective of the given player.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games as returned by `fetch_player_games`.
    username : str
        Chess.com username whose performance by time of day to analyze.
    timezone : str, optional
        IANA timezone name for local time conversion, by default "Asia/Jerusalem".

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: 'hour', 'wins', 'losses', 'draws', 'total_games', 'true_win_rate'.
        Sorted by hour ascending. Empty DataFrame with these columns if no data.
    """
    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return pd.DataFrame(columns=["hour", "wins", "losses", "draws", "total_games", "true_win_rate"])

    df_work = player_games.copy()
    df_work["date_utc"] = pd.to_datetime(df_work["date_utc"], utc=True)
    if df_work["date_utc"].dt.tz is None:
        df_work["date_utc"] = df_work["date_utc"].dt.tz_localize("UTC", ambiguous="infer")
    df_work["local_time"] = df_work["date_utc"].dt.tz_convert(timezone)
    df_work["hour"] = df_work["local_time"].dt.hour

    username_lc = username.strip().lower()
    is_white = df_work["white_player"].str.lower() == username_lc
    scores = _compute_results(
        series_white=df_work["white_result"],
        series_black=df_work["black_result"],
        is_white=is_white,
    )
    df_work["score"] = scores
    df_work["win"] = (scores == 1.0).astype(int)
    df_work["loss"] = (scores == 0.0).astype(int)
    df_work["draw"] = (scores == 0.5).astype(int)

    grouped = (
        df_work.groupby("hour", as_index=False)
        .agg(
            wins=("win", "sum"),
            losses=("loss", "sum"),
            draws=("draw", "sum"),
            total_games=("score", "count"),
            true_win_rate=("score", "mean"),
        )
    )

    # Ensure all hours 0-23 present
    all_hours = pd.DataFrame({"hour": range(24)})
    grouped = all_hours.merge(grouped, on="hour", how="left")
    for col in ["wins", "losses", "draws", "total_games"]:
        grouped[col] = grouped[col].fillna(0).astype(int)
    grouped["true_win_rate"] = grouped["true_win_rate"].fillna(0.0)
    grouped = grouped.sort_values("hour").reset_index(drop=True)

    return grouped


def get_wrapped_data(df: pd.DataFrame, username: str, live_ratings: Dict[str, object]) -> Dict[str, object]:
    """
    Build a Spotify-Wrapped style positive metrics summary for the given user.

    Returns a dict with:
    - top_rating
    - total_victories
    - deadliest_opening
    - golden_hour
    """
    # Top rating
    rating_values: List[int] = []
    try:
        for key in ["rapid", "blitz", "bullet"]:
            val = (live_ratings or {}).get(key, "N/A")
            if isinstance(val, (int, float)):
                rating_values.append(int(val))
    except Exception:
        rating_values = []
    top_rating: object = max(rating_values) if rating_values else "Not enough data"

    # Victories
    total_victories: object = "Not enough data"
    try:
        player_games = _filter_player_games(df, username)
        if not player_games.empty:
            username_lc = username.strip().lower()
            is_white = player_games["white_player"].astype(str).str.lower() == username_lc
            user_result = player_games["white_result"].where(is_white, player_games["black_result"])
            total_victories = int((user_result.fillna("").astype(str).str.lower() == "win").sum())
    except Exception:
        total_victories = "Not enough data"

    # Deadliest opening: highest true_win_rate where total_games >= 3
    deadliest_opening: object = "Not enough data"
    try:
        openings_df = analyze_openings(df, username)
        if not openings_df.empty:
            eligible = openings_df[openings_df["total_games"] >= 3].copy()
            if not eligible.empty:
                best_row = eligible.sort_values(
                    ["true_win_rate", "total_games"], ascending=[False, False]
                ).iloc[0]
                opening_name = str(best_row.get("opening", "Unknown"))
                wr_pct = float(best_row.get("true_win_rate", 0.0)) * 100.0
                deadliest_opening = {"opening": opening_name, "win_rate_pct": wr_pct}
    except Exception:
        deadliest_opening = "Not enough data"

    # Golden hour: highest true_win_rate with minimum 3 games
    golden_hour: object = "Not enough data"
    try:
        tod_df = analyze_time_of_day(df, username, timezone="Asia/Jerusalem")
        if not tod_df.empty:
            eligible = tod_df[tod_df["total_games"] >= 3].copy()
            if not eligible.empty:
                best_row = eligible.sort_values(
                    ["true_win_rate", "total_games"], ascending=[False, False]
                ).iloc[0]
                hour = int(best_row.get("hour", 0))
                golden_hour = f"{hour:02d}:00"
    except Exception:
        golden_hour = "Not enough data"

    return {
        "top_rating": top_rating,
        "total_victories": total_victories,
        "deadliest_opening": deadliest_opening,
        "golden_hour": golden_hour,
    }


def _square_to_row_col(square: int) -> Tuple[int, int]:
    """Convert chess square index (0-63) to 2D (row, col). row 0 = rank 1, col 0 = file a."""
    rank = chess.square_rank(square)  # 0 = rank 1, 7 = rank 8
    file_idx = chess.square_file(square)  # 0 = a, 7 = h
    return int(rank), int(file_idx)


# Map UI piece filter strings to chess piece type constants (None = All).
PIECE_FILTER_MAP = {
    "All": None,
    "All Pieces": None,
    "Pawn": chess.PAWN,
    "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP,
    "Rook": chess.ROOK,
    "Queen": chess.QUEEN,
    "King": chess.KING,
}


def generate_spatial_heatmaps(
    df: pd.DataFrame, username: str, piece_filter: str = "All"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build 8x8 activity and vulnerability heatmaps from game PGNs, optionally
    filtered by piece type.

    - activity_map: for each of the player's moves (optionally of the selected
      piece type), increment the destination square.
    - vulnerability_map: for each opponent capture of the player's piece
      (optionally of the selected type), increment the square where the piece
      was captured. Handles en passant (captured pawn on its square).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of games with columns including 'pgn', 'white_player', 'black_player'.
    username : str
        Chess.com username to analyze.
    piece_filter : str, optional
        One of 'All', 'All Pieces', 'Pawn', 'Knight', 'Bishop', 'Rook', 'Queen', 'King'.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (activity_map, vulnerability_map), each 8x8 with row 0 = rank 1, col 0 = file a.
    """
    activity_map = np.zeros((8, 8), dtype=np.float64)
    vulnerability_map = np.zeros((8, 8), dtype=np.float64)
    username_lc = username.strip().lower()
    filter_type = PIECE_FILTER_MAP.get(
        (piece_filter or "All").strip(), PIECE_FILTER_MAP["All"]
    )

    player_games = _filter_player_games(df, username)
    if player_games.empty:
        return activity_map, vulnerability_map

    pgn_col = player_games.get("pgn")
    if pgn_col is None:
        return activity_map, vulnerability_map

    white_players = player_games["white_player"].astype(str).str.lower()
    black_players = player_games["black_player"].astype(str).str.lower()

    for idx, pgn_raw in enumerate(pgn_col):
        if pgn_raw is None or not isinstance(pgn_raw, str) or not pgn_raw.strip():
            continue
        try:
            game = chess.pgn.read_game(io.StringIO(pgn_raw.strip()))
        except Exception:
            continue
        if game is None:
            continue

        try:
            board = game.board()
            is_white = white_players.iloc[idx] == username_lc
            player_color = chess.WHITE if is_white else chess.BLACK

            for move in game.mainline_moves():
                to_sq = move.to_square
                from_sq = move.from_square

                if board.turn == player_color:
                    # Activity: only count if piece type matches filter
                    piece = board.piece_at(from_sq)
                    if piece is None:
                        board.push(move)
                        continue
                    if filter_type is not None and piece.piece_type != filter_type:
                        board.push(move)
                        continue
                    row, col = _square_to_row_col(to_sq)
                    activity_map[row, col] += 1
                else:
                    # Vulnerability: opponent's capture of player's piece
                    if board.is_capture(move):
                        if board.is_en_passant(move):
                            captured_square = (
                                to_sq - 8 if board.turn == chess.WHITE else to_sq + 8
                            )
                            captured = board.piece_at(captured_square)
                            captured_type = chess.PAWN if captured else None
                        else:
                            captured_square = to_sq
                            captured = board.piece_at(to_sq)
                            captured_type = captured.piece_type if captured else None

                        if (
                            captured is not None
                            and captured.color == player_color
                            and (filter_type is None or captured_type == filter_type)
                        ):
                            row, col = _square_to_row_col(captured_square)
                            vulnerability_map[row, col] += 1
                board.push(move)
        except Exception:
            continue

    return activity_map, vulnerability_map


@st.cache_data(show_spinner=False)
def analyze_game_with_chess_api(pgn_string: str, max_plies: int = 40) -> pd.DataFrame:
    """
    Analyze a game with an external engine API (chess-api.com).

    For each ply, advances the game one move, posts the resulting FEN to the API,
    and records evaluation + best move.

    POST:
        https://chess-api.com/v1
        json={"fen": fen, "depth": 8}

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
                json={"fen": fen, "depth": 8},
                timeout=15,
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
            eval_now = prev_eval
            best_move = prev_best

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


@st.cache_data(show_spinner=False)
def get_all_blunders(
    eval_df: pd.DataFrame, pgn_string: str, username: str, threshold: float = 0.8
) -> List[Dict[str, object]]:
    """
    Find key moments (mistakes/blunders) for the given user.

    Implements a robust, sign-aware loss metric from the user's perspective and
    returns up to the top 5 worst moments (by user_loss).
    """
    if eval_df is None or eval_df.empty:
        return []
    if not isinstance(pgn_string, str) or not pgn_string.strip():
        return []
    if not isinstance(username, str) or not username.strip():
        return []
    if "evaluation" not in eval_df.columns or "ply" not in eval_df.columns:
        return []

    # Parse PGN headers to determine user color.
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_string))
    except Exception:
        return []
    if game is None:
        return []

    is_white = (game.headers.get("White", "") or "").strip().lower() == username.strip().lower()

    df = eval_df.copy().reset_index(drop=True)
    df["evaluation"] = pd.to_numeric(df["evaluation"], errors="coerce")

    # 1) swing (signed) per spec
    df["swing"] = df["evaluation"].diff().fillna(0.0)

    # 2) determine user's turns
    # Our ply is 1-based, but the spec references even plies (0,2,4...) for White.
    # Use 0-based parity via (ply-1).
    ply0 = pd.to_numeric(df["ply"], errors="coerce").fillna(0).astype(int) - 1
    df["is_user_turn"] = (ply0 % 2) == (0 if is_white else 1)

    # 3) user_loss from user's perspective
    if is_white:
        # evaluation drop is bad for White => negative swing
        df["user_loss"] = -df["swing"]
    else:
        # evaluation spike is good for White => bad for Black
        df["user_loss"] = df["swing"]

    # 4) find critical moments
    hits_df = df[(df["is_user_turn"]) & (df["user_loss"] >= 0.8)].copy()
    if hits_df.empty:
        hits_df = df[(df["is_user_turn"]) & (df["user_loss"] >= 0.5)].copy()
    if hits_df.empty:
        return []

    # 5) sort safely (top 5 worst moments)
    hits_df = hits_df.sort_values(by="user_loss", ascending=False).head(5)

    # 6) build results, replaying PGN to get FEN before ply and extracting UCIs
    results: List[Dict[str, object]] = []
    for _, row in hits_df.iterrows():
        try:
            ply = int(row["ply"])
        except Exception:
            continue

        eval_swing = float(row.get("user_loss", 0.0) or 0.0)
        actual_san = str(row.get("move_san") or "").strip()
        # Off-by-one fix: best_move on the blunder ply is for the opponent (after the mistake).
        # We want the engine recommendation from the position BEFORE the mistake (ply-1).
        best_move_uci = ""
        try:
            prev_ply = ply - 1
            if prev_ply > 0 and "best_move" in df.columns:
                prev_ply_row = df[df["ply"] == prev_ply]
                if not prev_ply_row.empty:
                    best_move_uci = str(prev_ply_row["best_move"].iloc[0] or "").strip()
        except Exception:
            best_move_uci = ""

        critical_fen = ""
        actual_move_uci = ""
        try:
            board = game.board()
            for i, mv in enumerate(game.mainline_moves(), start=1):
                if i == ply:
                    actual_move_uci = mv.uci()
                    break
                board.push(mv)
            critical_fen = board.fen()
        except Exception:
            critical_fen = ""
            actual_move_uci = ""

        results.append(
            {
                "ply": ply,
                "eval_swing": float(eval_swing),
                "critical_fen": critical_fen,
                "actual_move_uci": actual_move_uci,
                "best_move_uci": best_move_uci,
                "actual_san": actual_san,
            }
        )

    return results


if __name__ == "__main__":
    sample_username = "oriyakli1"
    try:
        games_df = fetch_player_games(sample_username, max_games=50)
    except ChessComAPIError as exc:
        print(f"Failed to fetch games for '{sample_username}': {exc}")
    else:
        print(f"Fetched {len(games_df)} games for '{sample_username}'.")

        twr = calculate_true_win_rate(games_df, sample_username)
        perf = calculate_performance_rating(games_df, sample_username)
        tilt = calculate_tilt_index(games_df, sample_username)
        openings_df = analyze_openings(games_df, sample_username)

        print(f"\nTrue win rate for '{sample_username}': {twr:.3f}")
        print(f"Performance rating for '{sample_username}': {perf:.1f}")
        print("\nTilt index:")
        for key, value in tilt.items():
            print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")

        print("\nOpening performance (top 10 by volume):")
        print(openings_df.head(10).to_string(index=False))

