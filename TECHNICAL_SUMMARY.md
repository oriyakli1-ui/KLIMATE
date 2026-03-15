# Klimate — Technical Summary

A concise technical overview for developers joining the project. Use this to onboard quickly and start coding.

---

## Project Overview

**Klimate** is a chess analytics web app that helps players (e.g. `oriyakli1`) understand their play using Chess.com data. It provides:

- **Aggregate stats**: True win rate, performance rating, tilt index.
- **Time-of-day insights** (Cognitive Clock): When the user performs best/worst.
- **Board-space analytics** (Spatial Analysis): Where they move pieces and where they lose them.
- **Opening weak spots** (Strategic Blindspots): Openings with the highest loss rate and AI masterclass dialogs.
- **Per-game engine analysis** (Engine Deep Dive): Evaluation graphs, blunder detection, and AI coaching with visual boards.

The app is **user-agnostic**: any Chess.com username can be entered on the landing page. There is no auth; session state holds the loaded games and username after “Analyze DNA”.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3 |
| **Frontend / App** | **Streamlit** (single-page app with sidebar navigation) |
| **UI Components** | `streamlit-option-menu` for sidebar menu |
| **Data / Viz** | Pandas, NumPy, **Plotly** (charts) |
| **Chess Logic & Rendering** | **python-chess** (`chess`, `chess.pgn`, `chess.svg`) |
| **Data Source** | **Chess.com public API** (archives, game PGNs, player stats) |
| **Engine Analysis** | **chess-api.com** (POST with FEN; returns evaluation + best move) |
| **AI / Coaching** | **Google Gemini** (`google-generativeai`, model `gemini-2.5-flash`) |
| **HTTP** | `requests` |

There is **no** FastAPI/Flask; the app is Streamlit-only. There is **no** local Stockfish; engine analysis is done via the chess-api.com HTTP API.

---

## Core Features Implemented

### 1. Landing & session

- **Landing**: Centered logo (`logo.png`), tagline, Chess.com username input, “Analyze DNA” button.
- **Flow**: On success, `fetch_player_games(username, max_games=100)` runs, results stored in `st.session_state["games_df"]`, `["username"]`, `["data_loaded"] = True`, then `st.rerun()`. Sidebar is hidden until data is loaded.

### 2. Overview dashboard

- **Live stats row**: Rapid / Blitz / Bullet (from Chess.com stats API) + Current Streak (from `get_current_profile_stats` on the games DataFrame).
- **Metric cards**: True Win Rate, Performance Rating, Tilt Index (with tooltips and success/danger styling).
- **Opening DNA**: Bar chart of top 10 openings by game count, colored by true win rate (Plotly, transparent Bento-style).

### 3. Cognitive Clock

- **Data**: `analytics.analyze_time_of_day(games_df, username)` — games grouped by local hour (default timezone `Asia/Jerusalem`), with `total_games` and `true_win_rate` per hour.
- **UI**: Text insight (best/worst hour when ≥2 games); dual-axis Plotly chart: bars = games per hour, line = win rate (only for hours with enough games to avoid misleading 0% dips).

### 4. Spatial Analysis

- **Data**: `analytics.generate_spatial_heatmaps(games_df, username, piece_filter)` → `(activity_map, vulnerability_map)` 8×8 NumPy arrays. Optional filter: All, Pawn, Knight, Bishop, Rook, Queen, King.
- **UI**: Two tabs — Activity (“Where do you move?”) and Vulnerability (“Where do you lose pieces?”). Plotly `imshow` heatmaps (square aspect), plus text insights for most active / most vulnerable square.

### 5. Strategic Blindspots

- **Data**: Openings with ≥3 games; aggregate Win/Loss/Draw; sort by loss rate; top 5 = “blindspots”.
- **UI**: Horizontal stacked bar (Win / Draw / Loss), then “Deep Dive into your Blindspots” with one button per blindspot opening.
- **Dialog**: `@st.dialog("♟️ Opening Masterclass", width="large")` — `show_opening_masterclass(opening_name)` shows header, Gemini masterclass text (core idea, defend against, exploit), YouTube search link, and a generic starting-position board (SVG).

### 6. Engine Deep Dive

- **Data**: User picks a game from the DataFrame; on “Analyze Game”, `analyze_game_with_chess_api(selected_pgn, max_plies=40)` (chess-api.com, depth 8, cached). Then `get_all_blunders(eval_df, pgn, username, threshold=0.8)` returns up to 5 key moments (user’s turn, by evaluation swing).
- **UI**: Evaluation line chart with blunder markers; selectbox to pick a blunder; two columns: SVG board (position before blunder, red = played move, green = engine move, orientation by user color) and Gemini coach explanation.

### 7. UI/Dashboard and logo

- **Theme**: Dark “Bento” (e.g. `#0F172A` background, `#1E293B` cards, `#06B6D4` accent, `#10B981` / `#EF4444` for success/danger). Custom CSS in `_inject_global_styles()` for cards, metrics, tooltips, inputs, Plotly containers.
- **Layout**: Wide layout; after login, sidebar with `option_menu` (Overview, Cognitive Clock, Spatial Analysis, Strategic Blindspots, Engine Deep Dive). Main area has a “Command Center” emblem (♟️ KLIMATE | COMMAND CENTER) then page content.
- **Logo**: `logo.png` used on landing (centered) and in sidebar; path is project-relative.

---

## File Structure

```
KLIMATE/
├── KLIMATEapp.py      # Streamlit app: landing, routing, all pages, dialogs, CSS
├── analytics.py       # All analytics + Chess.com stats + chess-api.com + Gemini
├── data_engine.py     # Chess.com API: fetch_player_games, _parse_game, _safe_get
├── requirements.txt   # Python dependencies
├── logo.png          # Logo (landing + sidebar)
└── TECHNICAL_SUMMARY.md  # This file
```

- **`data_engine.py`**: Single entry point for game data: `fetch_player_games(username, max_games)`. Uses `User-Agent: Klimate Chess Analytics - Student Project`. Returns DataFrame with `date_utc`, `white_player`, `black_player`, ratings, results, `time_class`, `eco`, `opening`, `pgn`. Only the last 3 monthly archives are requested for speed.
- **`analytics.py`**: Pure analytics (win rate, performance rating, tilt, openings, time-of-day, spatial heatmaps) and external calls: Chess.com stats, chess-api.com engine, Gemini (coach + opening deep dive + opening masterclass). Uses `st.cache_data` on engine and blunder functions; uses `st.secrets["GEMINI_API_KEY"]`.
- **`KLIMATEapp.py`**: Entry point `main()`. Renders landing vs dashboard by `data_loaded`; dashboard branches on `selection` and calls `_render_overview_page`, `_render_cognitive_clock_chart`, spatial block, `_render_strategic_blindspots`, `_render_engine_deep_dive`. Defines `show_opening_masterclass` dialog and helpers (`_format_opening_label`, `_render_metric_card`, etc.).

---

## Current Logic Flow

1. **Landing**  
   User enters Chess.com username → “Analyze DNA” → `data_engine.fetch_player_games(username, 100)` → on success: `session_state["games_df"]`, `["username"]`, `["data_loaded"] = True` → `st.rerun()`.

2. **Dashboard**  
   `games_df` and `username` from session state. Sidebar `option_menu` sets `selection`. Main content shows the Command Center bar and the selected page.

3. **Overview**  
   `get_real_time_ratings(username)` and `get_current_profile_stats(df)` for live row; `calculate_true_win_rate`, `calculate_performance_rating`, `calculate_tilt_index` for metric cards; `analyze_openings` for Opening DNA chart.

4. **Cognitive Clock**  
   `analyze_time_of_day(games_df, username)` → DataFrame by hour → Plotly combo chart + text insight.

5. **Spatial**  
   `generate_spatial_heatmaps(games_df, username, piece_filter)` → two 8×8 arrays → Plotly heatmaps + square insights.

6. **Strategic Blindspots**  
   Group by opening (or ECO), filter ≥3 games, compute Win/Loss/Draw rates, take top 5 by loss rate → stacked bar + buttons → button opens `show_opening_masterclass(opening_name)` (Gemini + YouTube + board).

7. **Engine Deep Dive**  
   User selects game → “Analyze Game” stores PGN in `session_state["analyzed_pgn"]`. Then `analyze_game_with_chess_api(selected_pgn)` → `get_all_blunders(eval_df, pgn, username)` → chart + blunder selectbox → for selected blunder: SVG board (FEN before blunder, arrows from engine/blunder logic), Gemini coach text.

Data flow: **Chess.com API → data_engine (DataFrame) → session_state → analytics (derived metrics + external APIs) → KLIMATEapp (Plotly/Streamlit/Gemini).**

---

## Pending Tasks & Known Bugs

- **No formal backlog** in repo; the following are inferred from current design and typical next steps.
- **Engine Deep Dive**: Depends on chess-api.com availability and rate limits; no fallback engine. Caching reduces repeat calls but first load per game can be slow.
- **Strategic Blindspots**: Opening masterclass dialog shows a generic starting board only; no opening-specific position (would require mapping opening name → moves or extra API).
- **Secrets**: App expects `st.secrets["GEMINI_API_KEY"]`. If missing, Gemini features fail with clear “AI Coach is currently resting” style messages.
- **Data scope**: Only last 3 months of archives are fetched; “Overview” and other stats are thus over that window only.
- **Timezone**: Cognitive Clock uses `Asia/Jerusalem` by default; not configurable in UI.
- **Tests**: No test suite or CI referenced in the repo.

---

## Environment & Secrets

- **Python**: 3.x (project uses type hints and modern syntax).
- **Install**: `pip install -r requirements.txt` (streamlit, pandas, numpy, plotly, streamlit-option-menu, chess, google-generativeai, requests).
- **Run**: `streamlit run KLIMATEapp.py` (from project root).
- **Secrets**:  
  - **Gemini**: Required for AI coach and opening analyses. In Streamlit, set `GEMINI_API_KEY` in:
    - **Local**: `.streamlit/secrets.toml` (e.g. `GEMINI_API_KEY = "your-key"`), or
    - **Streamlit Cloud**: App settings → Secrets.
  - **Chess.com**: No API key; public endpoints only. Custom `User-Agent` is set in `data_engine` and in `analytics.get_real_time_ratings`.
- **Assets**: `logo.png` must exist in the app root (or path adjusted) for landing and sidebar.
- **Optional**: If you add `.streamlit/config.toml`, you can set theme or server options there; not required for current behavior.

---

## Quick Reference

| Need to… | Where |
|----------|--------|
| Change number of games fetched | `KLIMATEapp.py`: `fetch_player_games(username, max_games=100)` |
| Change timezone for Cognitive Clock | `analytics.analyze_time_of_day(..., timezone="...")` (and optionally expose in UI) |
| Change engine depth or plies | `analytics.analyze_game_with_chess_api(..., max_plies=40)` and API `depth` in POST body |
| Change blunder sensitivity | `analytics.get_all_blunders(..., threshold=0.8)` |
| Add a new page | Add option in `option_menu`, add `elif selection == "..."` and a render function |
| Use Gemini elsewhere | Call `genai.configure(api_key=st.secrets["GEMINI_API_KEY"])` and existing helpers or new ones in `analytics.py` |

This document reflects the state of the project as of the last update. For file-level details, refer to docstrings and the code in `KLIMATEapp.py`, `analytics.py`, and `data_engine.py`.
