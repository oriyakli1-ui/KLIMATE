from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st


USER_AGENT_HEADER: Dict[str, str] = {
    "User-Agent": "Klimate Chess Analytics - Student Project"
}


class ChessComAPIError(Exception):
    """Custom exception for Chess.com API related errors."""


def _safe_get(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Perform a GET request to the given URL with the required User-Agent header.

    Parameters
    ----------
    url : str
        URL to call.
    timeout : int, optional
        Timeout in seconds for the HTTP request, by default 10.

    Returns
    -------
    Dict[str, Any]
        Parsed JSON response.

    Raises
    ------
    ChessComAPIError
        If the request fails or the response is not JSON.
    """
    try:
        response = requests.get(url, headers=USER_AGENT_HEADER, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ChessComAPIError(f"Request to {url} failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise ChessComAPIError(f"Invalid JSON response from {url}") from exc


def _parse_game(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a single game JSON object into a flat dictionary.

    Parameters
    ----------
    game : Dict[str, Any]
        Raw game dictionary from the Chess.com API.

    Returns
    -------
    Optional[Dict[str, Any]]
        Parsed game dictionary with selected fields, or None if required
        information is missing.
    """
    white = game.get("white", {})
    black = game.get("black", {})

    # Some entries may be malformed; guard against missing keys.
    if not white or not black:
        return None

    end_time_ts = game.get("end_time") or game.get("end_time_unix")
    if end_time_ts is None:
        # Fallback to current UTC if not provided, though this should be rare.
        game_date_utc = dt.datetime.utcnow()
    else:
        game_date_utc = dt.datetime.fromtimestamp(int(end_time_ts), dt.timezone.utc)

    # Result is from White's perspective in Chess.com archives.
    white_result = white.get("result", "")
    black_result = black.get("result", "")

    # Prefer ECO/Opening if provided; otherwise empty string.
    eco = game.get("eco", "")
    opening = game.get("opening", "")

    time_class = game.get("time_class", "")
    pgn = game.get("pgn", "")

    return {
        "date_utc": game_date_utc,
        "white_player": white.get("username", ""),
        "black_player": black.get("username", ""),
        "white_rating": white.get("rating"),
        "black_rating": black.get("rating"),
        "white_result": white_result,
        "black_result": black_result,
        "time_class": time_class,
        "eco": eco,
        "opening": opening,
        "pgn": pgn,
    }


@st.cache_data(show_spinner=False, ttl=300)
def fetch_player_games(username: str, max_games: int = 200) -> pd.DataFrame:
    """
    Fetch a player's most recent games from the Chess.com public API.

    This function retrieves the monthly archives for the given user, then walks
    backward from the most recent month until it has collected up to
    ``max_games`` games (or all available games if fewer exist).

    Parameters
    ----------
    username : str
        Chess.com username (case-insensitive).
    max_games : int, optional
        Maximum number of games to retrieve, by default 200.

    Returns
    -------
    pd.DataFrame
        DataFrame containing one row per game with the following columns:

        - ``date_utc`` (datetime64[ns, UTC], timezone-aware)
        - ``white_player``
        - ``black_player``
        - ``white_rating``
        - ``black_rating``
        - ``white_result``
        - ``black_result``
        - ``time_class``
        - ``eco``
        - ``opening``
        - ``pgn``

    Raises
    ------
    ChessComAPIError
        If there is an issue communicating with the Chess.com API or parsing
        the responses.
    """
    if max_games <= 0:
        raise ValueError("max_games must be a positive integer")

    username = username.strip().lower()
    if not username:
        raise ValueError("username must be a non-empty string")

    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    data = _safe_get(archives_url)

    archive_urls: List[str] = data.get("archives", [])
    if not archive_urls:
        # No archives / no games for this user.
        return pd.DataFrame(
            columns=[
                "date_utc",
                "white_player",
                "black_player",
                "white_rating",
                "black_rating",
                "white_result",
                "black_result",
                "time_class",
                "eco",
                "opening",
                "pgn",
            ]
        )

    collected_games: List[Dict[str, Any]] = []

    # Iterate from the most recent few months backwards to avoid fetching
    # the entire historical archive (performance safeguard).
    recent_archives = archive_urls[-3:] if len(archive_urls) > 3 else archive_urls
    for month_url in reversed(recent_archives):
        if len(collected_games) >= max_games:
            break

        month_data = _safe_get(month_url)
        month_games = month_data.get("games", [])

        # Games in the archive are generally in chronological order;
        # we want the most recent games first overall, so iterate reversed.
        for game in reversed(month_games):
            if len(collected_games) >= max_games:
                break

            parsed = _parse_game(game)
            if parsed is not None:
                collected_games.append(parsed)

    if not collected_games:
        return pd.DataFrame(
            columns=[
                "date_utc",
                "white_player",
                "black_player",
                "white_rating",
                "black_rating",
                "white_result",
                "black_result",
                "time_class",
                "eco",
                "opening",
                "pgn",
            ]
        )

    df = pd.DataFrame(collected_games)

    # Normalize date column to pandas datetime; keep timezone-aware (UTC).
    df["date_utc"] = pd.to_datetime(df["date_utc"], utc=True)

    # Sort by date descending (most recent first).
    df = df.sort_values("date_utc", ascending=False).reset_index(drop=True)

    return df


if __name__ == "__main__":
    # Simple manual test for the data pipeline.
    sample_username = "oriyakli1"
    try:
        games_df = fetch_player_games(sample_username, max_games=50)
        print(f"Fetched games DataFrame shape for '{sample_username}': {games_df.shape}")
    except ChessComAPIError as exc:
        print(f"Failed to fetch games for '{sample_username}': {exc}")
