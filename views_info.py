"""Methodology page: how every number is produced and what it can and cannot tell you."""
from __future__ import annotations

import streamlit as st

SECTIONS = [
    ("Where the data comes from", """
Klimate reads your **public** games from the Chess.com public API. Nothing is stored on a server: the analysis runs while you use
the app and disappears when you close it. Only standard chess games are analysed; variants, daily (correspondence) games and games
shorter than 6 half-moves are left out and not counted.
"""),
    ("How a result is scored", """
A win is 1 point, a draw 0.5, a loss 0. **Score** = points divided by games. It is reported with a 95% interval, because 50 games
say much less than 500. Games won or lost by abandonment are included, exactly as Chess.com records them.
"""),
    ("Ratings (and a trap in the data)", """
Chess.com publishes every rating **after** the game, for both players. Klimate therefore derives the rating change of a game as this
rating minus your previous rating in the same time control, and your pre-game rating from that. The opponent's pre-game rating is
estimated as their published rating plus your change. Anything that cannot be reconstructed reliably (the first game of a time
control, an unseen game in between) is left out rather than guessed.
"""),
    ("Sessions, tilt and time of day", """
A **session** is a run of games where less than 30 minutes pass between one game's end and the next game's start (taken from the
PGN start and end times). Time of day uses the hour a game **started**, in your own timezone.
"""),
    ("What 'reliable' means", """
Differences between situations (after a loss, at night, in a given opening...) are only called reliable when they are larger than
chance would explain. Because many situations are tested at once, the bar is stricter than the usual 95%. "No reliable pattern" is a
valid and common result, not a failure of the tool.
"""),
    ("Engine analysis", """
Stockfish evaluates positions at a fixed depth. A move is an *inaccuracy* when it gives away 10 or more percentage points of win
chance, a *mistake* at 20+, a *blunder* at 30+ (a convention inspired by Lichess). Accuracy is the average per-move accuracy using
Lichess's per-move formula. Borderline moves can change with deeper analysis or another Stockfish version.
"""),
    ("Elo Ledger and Play Now", """
The ledger compares your **measured** rating change per game between situations. It shows association, not proof of cause, and the
situations overlap, so their totals must not be added. Play Now applies the same comparison to the situation you are in right now and
says "not enough evidence" when your history cannot answer.
"""),
    ("Converting advantages and the Opponent Scout", """
An *advantage game* is one in which Stockfish gave you 80% or more win chance at some point; a *lost position* is one that fell to 20% or
less. Converting means winning (a draw does not count) and saving means drawing or winning, each with a 95% interval. The Opponent Scout
reads only public games, lists an opening as a soft spot only with 5+ games whose interval lies clearly below the player's overall score,
and makes no claim about habits (clock, tilt, colour) below 20 games.
"""),
    ("How we check ourselves", """
`tools/audit_against_chesscom.py` recomputes the headline numbers (results, streaks, sessions, hours, ratings, performance rating,
ledger totals, board maps, clock values) from the raw API data with independent code and compares them with the app. It is run after every
change to a metric, and an automated test suite renders every page.
"""),
    ("Known limits", """
Chess.com does not publish clock data for every game, opening names come from Chess.com's own classification (about 1% are
'Undefined'), and Stockfish on the live site may be an older build than the one on a laptop. The 'plays like' grandmaster match on the
Wrapped card is for fun only.
"""),
]


def render_methodology() -> None:
    st.markdown("### ℹ️ Methodology")
    st.caption("How Klimate gets its numbers, and how far to trust them.")
    for i, (title, body) in enumerate(SECTIONS):
        with st.expander(title, expanded=(i == 0)):
            st.markdown(body.strip())
