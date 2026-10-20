# Roadmap

Everything below uses free tools only until demand is shown. Streamlit remains the prototype layer; logic lives in Streamlit-free modules so a
future API (FastAPI) plus web/Android front end can reuse it.

## Done
- Honest statistics everywhere (intervals, strict thresholds, "no reliable pattern"), audited against raw Chess.com data.
- Habits in rating points (Elo Ledger), Play Now readiness, Weekly Report with rule tracking, Action Center.
- Stockfish Coach Report incl. converting advantages and fighting back, Opening Check, Training Plan.
- Opponent Scout, public-player demo, dark theme, grouped navigation.

## Next (needs real users first)
- Measure which pages visitors use (GA4) and cut what is not used.
- Shareable report pages and email/weekly digest.
- Accounts and saved history (requires a backend; paid hosting only after demand).
- Android app (PWA or Expo) on top of an API.
- Optional: Lichess accounts, Chess.com-API request budget for many concurrent users.
