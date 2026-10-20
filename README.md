# Klimate

Chess psychology analytics for Chess.com players: find *when*, *how* and *why* you lose points.
Live app: https://klimate.streamlit.app/

## Features
- **Overview, Cognitive Clock, Spatial Analysis, Strategic Blindspots** – results by time of day, board heat maps, weakest openings with an AI masterclass.
- **Elo Ledger** – what each habit (after a loss, first game, late in a session, time scrambles, night games) costs or earns in *measured* Chess.com rating points, with significance.
- **Play Now** – a traffic light for starting another game right now, judged by your own history in the same situation.
- **Opening Check** – Stockfish evaluation after move 10 for every opening and colour: separates opening trouble from later-game trouble.
- **Behavior Lab** – sessions, tilt and your personal stop-loss rule, warm-up effect, opponent strength, colour.
- **Time Management** – clock use from the PGN (scrambles, early time burn, flagging).
- **Coach Report** – Stockfish on your last games: accuracy, blunder/mistake/inaccuracy, weakest phase, error types, AI summary.
- **Converting advantages** (inside the Coach Report) – how often your winning positions (80%+ win chance) become wins and how often lost ones (20%-) are saved, with the move where each advantage collapsed.
- **Opponent Scout** – type any Chess.com username: openings they lean on per colour, gated soft spots, clock and tilt tendencies, your head-to-head record and your own score against their openings.
- **Try a public player** – the landing page can load a famous player so a visitor sees the product without an account.
- **Progress** – rating and score trends with goals saved in the page address.
- **Training Plan** – a weekly plan built from your own findings with free Lichess exercises.
- **Compare** – your habits next to another player's.
- **Wrapped** – shareable card (copy text or download PNG), grandmaster match from your real playing style.

Insights only appear when the difference is larger than chance would explain ("no reliable pattern" is a valid result).

## Run locally
```bash
pip install -r requirements.txt
streamlit run KLIMATEapp.py
```
Optional: install [Stockfish](https://stockfishchess.org/) (or set `STOCKFISH_PATH`) for the Coach Report and fast Engine Deep Dive; on Streamlit Cloud it comes from `packages.txt`. Without it the app falls back to the chess-api.com web service for single-game analysis.

Secrets (`.streamlit/secrets.toml`, or Streamlit Cloud → Secrets) for the AI coach: `GEMINI_API_KEY`, optional `GROQ_API_KEY`.
Set `KLIMATE_GA_DISABLED=1` to stop sending Google Analytics events during development.

## Accuracy
Every headline number is checked against the raw Chess.com data by `tools/audit_against_chesscom.py` (independent code), and statistics carry their uncertainty; see `TECHNICAL_SUMMARY.md`.

## Tests
```bash
pip install -r requirements-dev.txt
pytest tests
```

## Layout
| File | Role |
|---|---|
| `KLIMATEapp.py` | entry point: routing, sidebar, filters |
| `ui_*.py`, `views_*.py` | pages |
| `metrics.py`, `insights.py`, `analysis.py`, `spatial.py`, `wrapped.py`, `training.py`, `style.py`, `openings.py` | pure analysis code (no Streamlit) |
| `analytics.py`, `coach.py`, `llm.py`, `data_engine.py` | engine, LLM and Chess.com access |
| `strings.py`, `ga.py`, `share_card.py` | UI strings, Google Analytics events, PNG card |

Data comes from the public Chess.com API (read-only, requests are serial, closed months are cached on disk).
