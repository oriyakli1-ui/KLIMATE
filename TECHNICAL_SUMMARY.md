# Klimate: Technical Summary

See `README.md` for the feature list and how to run. This file explains how the pieces fit.

## Data flow
Chess.com API -> `data_engine.fetch_player_games` (DataFrame, closed months cached in `.cache/`) -> `st.session_state["games_df"]`
-> `insights.enrich_games` (one row per game from the player's view: score, sessions, clocks) -> `session_state["enriched"]`
-> sidebar filters (`insights.filter_*`) -> pages.

## Modules
- `data_engine.py`: archive fetching, `opening` (family) / `opening_variation` from ECO URLs (`openings.py`), configurable months, progress callback.
- `insights.py`: sessions (30 min gap), tilt/stop-loss, clock profile, rating-gap and colour profiles, `generate_insights` (gated by `_significant`). Returns `key` + `params` and English text from `TEMPLATES`.
- `analysis.py`: Lichess-style win-probability, accuracy, move labels (inaccuracy 10 / mistake 20 / blunder 30 win-chance points), phase and heuristic error types.
- `analytics.py`: classic metrics (win rate, performance, tilt index, openings, time of day, spatial heat maps), Stockfish (`analyze_game_with_stockfish`, found via `STOCKFISH_PATH`, `PATH` or `/usr/games/stockfish`) and the chess-api.com fallback (`analyze_game` picks one and adds a `source` column). Failed HTTP evaluations are NaN, never copied.
- `coach.py`: batch analysis of recent games, `training.py`: weekly plan, `style.py`: playing style -> grandmaster match, `share_card.py`: PNG.
- `llm.py`: Gemini (`google-genai`) then Groq, successful answers cached; failures raise and are not cached.
- `ga.py`: GA4 loader and event queue. Events: analyze_clicked, analysis_loaded, analysis_failed, page_selected, masterclass_opened, wrapped_generated, wrapped_downloaded, wrapped_share_clicked.
- `strings.py`: UI strings (English only; the product targets an international audience).

## Signature tools
- `ledger.py` (Elo Ledger), `readiness.py` (Play Now) and `opening_eval.py` (Opening Check) are pure modules; pages in `views_features.py`.
- Chess.com publishes every rating AFTER the game, for both players. `insights.enrich_games` therefore derives `rating_change` (this rating minus the previous one in the same pool), `user_rating` (pre-game) and an estimated pre-game `opp_rating`; values that cannot be reconstructed reliably stay NaN.

## Accuracy rules (audited)
- `metrics.py` is the single definition of: how a result is scored (`score_result`, uses both players' result strings), confidence intervals, Elo performance rating (solved, never mixes time controls), significance tests, linear trend.
- Only standard-chess, non-daily games of at least 6 half-moves are analysed (`data_engine`, exclusion counts in `df.attrs["excluded"]`).
- Sessions use idle time between one game's end and the next start (PGN StartTime/EndTime). Time of day uses the game's START hour in the visitor's timezone.
- Anything picked as the "best of many" (best hour, best opening) is shown only with its sample size or when it clears a stricter bar.
- `tools/audit_against_chesscom.py <user>` recomputes the headline numbers from raw API data with independent code and compares them with the app's modules. Run it after changing any metric.

## Conventions
- New analysis goes in Streamlit-free modules so it can later move behind an API.
- Anything that varies per rerun must be cached or queued; Streamlit reruns the whole script on every interaction.
- Do not guess data: show "no reliable pattern" or blanks rather than invented numbers.

## Known limits
- Accuracy is an approximation of the Lichess formula (plain mean of per-move accuracy).
- GM match is playful (captures/checks per move and game length), not a statistical model.
- Streamlit Cloud's free tier sleeps and has limited CPU; the Coach Report takes ~2-3 s per game locally.
