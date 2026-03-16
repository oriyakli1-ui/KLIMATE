from __future__ import annotations

"""
Offline script to pre-compute deep masterclasses for the 30 most popular
chess openings using the google-genai Client and store them in a pickle file.

Each entry in the generated pool has:
    - name: Opening name (string)
    - fen: Representative FEN position (string)
    - analysis: Masterclass text (string)

Run this script manually (from the project root) when you want to refresh
the masterclass pool:

    py generate_masterclass_pool.py

You must have a valid GEMINI_API_KEY configured in your environment before
running this.
"""

import os
import time
import pickle
from typing import Dict, List

import chess
from google import genai


MASTERCLASS_POOL_PATH = "masterclass_pool.pkl"


top_30_openings: List[str] = [
    "Sicilian Defense",
    "Ruy Lopez (Spanish Opening)",
    "French Defense",
    "Caro-Kann Defense",
    "Queens Gambit (Declined & Accepted)",
    "Kings Pawn Game",
    "Kings Indian Defense",
    "Nimzo-Indian Defense",
    "Italian Game",
    "Slav Defense",
    "Dutch Defense",
    "English Opening",
    "Grunfeld Defense",
    "Reti Opening",
    "Catalan Opening",
    "Modern Defense (Pirc)",
    "Scandinavian Defense (Center Counter)",
    "Scotch Game",
    "Vienna Game",
    "Alekhine Defense",
    "Kings Gambit",
    "Bishops Opening",
    "Evans Gambit",
    "Danish Gambit",
    "Petrov Defense",
    "Philidor Defense",
    "Chigorin Defense",
    "Colle System",
    "London System",
    "Trompowsky Attack",
]


FEN_OVERRIDES: Dict[str, str] = {
    "Sicilian Defense": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
    "Ruy Lopez (Spanish Opening)": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 3",
    "French Defense": "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "Caro-Kann Defense": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
}


def _get_client() -> genai.Client:
    """Configure and return a google-genai Client (models/gemini-1.5-flash)."""
    # The google-genai client can read GEMINI_API_KEY / GOOGLE_API_KEY from
    # the environment automatically, but we validate it explicitly for clarity.
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")
    model_id = "models/gemini-1.5-flash"
    print(f"Key found, using model: {model_id}")
    return genai.Client(api_key=api_key)


def _get_representative_fen(opening_name: str) -> str:
    """
    Return a representative FEN for the given opening name.

    For a few top openings we use curated FENs; for all others we fall back
    to the standard starting position.
    """
    if opening_name in FEN_OVERRIDES:
        return FEN_OVERRIDES[opening_name]
    board = chess.Board()
    return board.fen()


def _generate_masterclass_for_opening(
    client: genai.Client, opening_name: str
) -> Dict[str, str]:
    """
    Call Gemini 1.5 Flash to generate a deep masterclass for a single opening.
    """
    prompt = (
        f"Write an uncompromised, professional, and deep masterclass analysis for the {opening_name} in chess. "
        "Detail the key tactical themes, pawn structures, and long-term positional goals. "
        "Output exactly 5 detailed bullet points. Take your time for accuracy."
    )

    response = client.models.generate_content(
        model="models/gemini-1.5-flash",
        contents=prompt,
    )
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"Empty or invalid response for opening: {opening_name}")

    fen = _get_representative_fen(opening_name)
    return {
        "name": opening_name,
        "fen": fen,
        "analysis": text.strip(),
    }


def main() -> None:
    print("Initializing google-genai Client (gemini-1.5-flash)...")
    client = _get_client()

    pool: List[Dict[str, str]] = []

    print(f"Starting generation for {len(top_30_openings)} openings. This may take several minutes...")
    for idx, opening in enumerate(top_30_openings, start=1):
        print(f"[{idx}/{len(top_30_openings)}] Generating masterclass for: {opening!r}")
        try:
            entry = _generate_masterclass_for_opening(client, opening)
            pool.append(entry)
            print(f"  -> Success. Text length: {len(entry['analysis'])} chars, FEN: {entry['fen']}")
        except Exception as exc:  # noqa: BLE001
            print(f"  !! Failed to generate masterclass for {opening!r}: {exc}")
        # Respect API limits and avoid quota issues.
        time.sleep(10)

    print(f"\nSaving masterclass pool to {MASTERCLASS_POOL_PATH!r} ({len(pool)} entries)...")
    with open(MASTERCLASS_POOL_PATH, "wb") as f:
        pickle.dump(pool, f)

    print("Done.")


if __name__ == "__main__":
    main()
