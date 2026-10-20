"""Lichess as a second data source. Produces the same game table as ``data_engine.fetch_games`` (Chess.com vocabulary).

Rating semantics: Lichess reports the rating BEFORE the game plus ``ratingDiff``; we store the rating AFTER the game
(before + diff), which is what Chess.com publishes, so ``insights.enrich_games`` treats both sources identically.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import requests

from metrics import count_plies

API = "https://lichess.org"
HEADERS = {"User-Agent": "Klimate Chess Analytics/1.0 (+https://github.com/oriyakli1-ui/KLIMATE)"}
MIN_PLIES = 6
SKIP_STATUS = {"created", "started", "aborted", "noStart", "unknownFinish", "cheat"}
SPEED_TO_CLASS = {"ultraBullet": "bullet", "bullet": "bullet", "blitz": "blitz", "rapid": "rapid", "classical": "rapid"}


class LichessAPIError(Exception):
    """Lichess could not be reached or answered with an error."""


def _results(status: str, winner: Optional[str]) -> tuple:
    """(white_result, black_result) in Chess.com's vocabulary."""
    if winner is None:
        word = "stalemate" if status == "stalemate" else "agreed"
        return word, word
    loser = {"mate": "checkmated", "resign": "resigned", "outoftime": "timeout", "timeout": "abandoned"}.get(status, "resigned")
    return ("win", loser) if winner == "white" else (loser, "win")


def parse_game(g: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One Lichess game object (ndjson line) -> one row, or None when it is not a real standard game."""
    if g.get("variant", "standard") != "standard" or g.get("status") in SKIP_STATUS:
        return None
    speed = g.get("speed", "")
    if speed == "correspondence":
        return None
    players = g.get("players", {})
    out: Dict[str, Any] = {}
    for side in ("white", "black"):
        p = players.get(side) or {}
        user = p.get("user") or {}
        if not user.get("name") or p.get("rating") is None:      # anonymous or AI opponent
            return None
        out[f"{side}_player"] = user["name"]
        out[f"{side}_rating"] = int(p["rating"]) + int(p.get("ratingDiff") or 0)   # rating after the game
    out["white_result"], out["black_result"] = _results(g.get("status", ""), g.get("winner"))
    clock = g.get("clock") or {}
    base, inc = clock.get("initial"), clock.get("increment") or 0
    tc = "" if base is None else (f"{base}+{inc}" if inc else str(base))
    opening = (g.get("opening") or {}).get("name", "") or ""
    pgn = g.get("pgn", "") or ""
    end = pd.Timestamp(int(g.get("lastMoveAt") or g["createdAt"]), unit="ms", tz="UTC")
    start = pd.Timestamp(int(g["createdAt"]), unit="ms", tz="UTC")
    family = opening.split(":")[0].strip() or "Unknown"
    out.update({
        "date_utc": end, "start_utc": start, "time_class": SPEED_TO_CLASS.get(speed, ""),
        "eco": (g.get("opening") or {}).get("eco", ""), "opening": family, "opening_variation": opening or "Unknown",
        "pgn": pgn, "time_control": tc, "rated": bool(g.get("rated", False)), "rules": "chess",
        "url": f"{API}/{g['id']}" if g.get("id") else "", "plies": count_plies(pgn),
    })
    return out


def fetch_games(username: str, max_games: int = 200, months: int = 3,
                progress: Optional[Callable[[int, int], None]] = None, columns: Optional[List[str]] = None) -> pd.DataFrame:
    """The player's most recent standard games from the last ``months`` months (0 = no time limit)."""
    username = username.strip()
    if not username:
        raise ValueError("username must be a non-empty string")
    params: Dict[str, Any] = {"max": int(max_games), "pgnInJson": "true", "clocks": "true", "opening": "true",
                              "perfType": "ultraBullet,bullet,blitz,rapid,classical"}
    if months > 0:
        params["since"] = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30 * months)).timestamp() * 1000)
    rows: List[Dict[str, Any]] = []
    try:
        with requests.get(f"{API}/api/games/user/{username}", params=params, stream=True, timeout=30,
                          headers={**HEADERS, "Accept": "application/x-ndjson"}) as r:
            if r.status_code == 404:
                raise LichessAPIError(f"Lichess user '{username}' was not found.")
            if r.status_code == 429:
                raise LichessAPIError("Lichess asked us to slow down. Please try again in a minute.")
            r.raise_for_status()
            for n, line in enumerate(r.iter_lines(decode_unicode=True), start=1):
                if not line:
                    continue
                parsed = parse_game(json.loads(line))
                if parsed is not None:
                    rows.append(parsed)
                if progress and n % 20 == 0:
                    progress(min(n, max_games), max_games)
    except requests.RequestException as exc:
        raise LichessAPIError(f"Request to Lichess failed: {exc}") from exc
    if progress:
        progress(max_games, max_games)
    cols = columns or list(rows[0].keys() if rows else [])
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    df = df[df["plies"] >= MIN_PLIES].sort_values("date_utc", ascending=False).reset_index(drop=True)
    df.attrs["excluded"] = {"variants": 0, "daily": 0, "short": len(rows) - len(df)}
    return df


def fetch_ratings(username: str) -> Dict[str, object]:
    """Current and all-time-best ratings, in the shape ``analytics.get_real_time_ratings`` returns ('N/A' when unknown)."""
    classes = ("rapid", "blitz", "bullet")
    na = "N/A"
    out: Dict[str, object] = {**{c: na for c in classes}, "best": {c: na for c in classes}, "peak": na, "peak_class": ""}
    name = username.strip()
    try:
        r = requests.get(f"{API}/api/user/{name}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        perfs = r.json().get("perfs", {})
        h = requests.get(f"{API}/api/user/{name}/rating-history", headers=HEADERS, timeout=10)
        h.raise_for_status()
        history = {x.get("name", "").lower(): x.get("points", []) for x in h.json()}
    except (requests.RequestException, ValueError):
        return out
    for c in classes:
        p = perfs.get(c) or {}
        if p.get("games", 0) and p.get("rating"):
            out[c] = int(p["rating"])
        pts = [pt[3] for pt in history.get(c, []) if len(pt) >= 4]
        if pts:
            out["best"][c] = int(max(pts))
    known = {c: v for c, v in out["best"].items() if isinstance(v, int)}
    if known:
        out["peak_class"] = max(known, key=known.get)
        out["peak"] = known[out["peak_class"]]
    return out
