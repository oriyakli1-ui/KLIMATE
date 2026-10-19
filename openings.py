"""Opening names from Chess.com ECO URLs.

Chess.com publishes ``eco`` as a URL such as
``https://www.chess.com/openings/Caro-Kann-Defense-Advance-Variation-3...c5``.
This module turns it into a readable full name plus an "opening family"
("Caro-Kann Defense") so that variations are grouped into samples big enough
to say something about.
"""
from __future__ import annotations

import re
from typing import Tuple

# Multi-word families whose first "head word" (Defense, Opening, ...) would cut them wrong.
_FAMILIES = [
    "Ruy Lopez", "Italian Game", "Scotch Game", "Vienna Game", "Four Knights Game", "Three Knights Game",
    "Petrovs Defense", "Philidor Defense", "Nimzo-Indian Defense", "Queens Indian Defense",
    "Kings Indian Defense", "Kings Indian Attack", "Grunfeld Defense", "Benoni Defense", "Slav Defense",
    "Semi-Slav Defense", "Catalan Opening", "English Opening", "Reti Opening", "Bird Opening",
    "London System", "Trompowsky Attack", "Torre Attack", "Colle System", "Scandinavian Defense",
    "Pirc Defense", "Modern Defense", "Alekhine Defense", "Dutch Defense", "French Defense",
    "Caro-Kann Defense", "Sicilian Defense", "Queens Gambit Accepted", "Queens Gambit Declined",
    "Queens Gambit", "Kings Gambit Accepted", "Kings Gambit Declined", "Kings Gambit", "Englund Gambit",
    "Evans Gambit", "Danish Gambit", "Budapest Defense", "Benko Gambit", "Queens Pawn Opening",
    "Kings Pawn Opening", "Zukertort Opening", "Hungarian Opening", "Polish Opening", "Owen Defense",
    "Bishops Opening", "Center Game", "Elephant Gambit", "Latvian Gambit", "Scandinavian Gambit",
    "Vants Kruijs Opening", "Nimzowitsch Defense", "Old Indian Defense", "Bogo-Indian Defense",
]
_HEAD_WORDS = {"Defense", "Opening", "Gambit", "Game", "Attack", "System"}
_SUFFIX_WORDS = {"Accepted", "Declined", "Refused"}
# Pool entries and the old display names carry no apostrophes ("Queens Gambit"), keep that.
_ALIASES = {"Petrovs Defense": "Petrov Defense"}
_FIRST_MOVE = re.compile(r"-\d+\.")
_UNKNOWN = {"undefined", "unknown", "null", "none"}


def _pretty(words: list[str]) -> str:
    return " ".join(words)


def parse_eco_url(url: object) -> Tuple[str, str]:
    """Return ``(full_name, family)``; both are '' when the value is not a usable URL/slug."""
    s = str(url or "").strip()
    if not s:
        return "", ""
    slug = s.rsplit("/", 1)[-1]
    if slug.lower() in _UNKNOWN:  # Chess.com literally sends ".../openings/Undefined" for unrecognised openings
        return "", ""
    m = _FIRST_MOVE.search(slug)
    if m:
        slug = slug[: m.start()]
    words = [w for w in slug.split("-") if w]
    if not words:
        return "", ""
    full = _pretty(words)

    # Hyphenated families ("Caro-Kann") must be compared on the slug, not on split words.
    low_slug = "-".join(words).lower()
    for fam in sorted(_FAMILIES, key=len, reverse=True):
        prefix = fam.lower().replace(" ", "-")
        if low_slug.startswith(prefix):
            rest = [w for w in "-".join(words)[len(prefix):].split("-") if w]
            name = _ALIASES.get(fam, fam)
            return _pretty([name] + rest), name
    for i, w in enumerate(words):
        if w in _HEAD_WORDS:
            end = i + 2 if i + 1 < len(words) and words[i + 1] in _SUFFIX_WORDS else i + 1
            return full, _pretty(words[:end])
    return full, _pretty(words[:3])
