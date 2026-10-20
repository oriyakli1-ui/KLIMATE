# Klimate marketing kit

Internal notes. Nothing here is published; share only when ready.

## Positioning
**One line:** Klimate shows what your chess habits cost you in rating points, from your public Chess.com games.
**For:** rated online players (roughly 800-1800) who feel they play worse at certain times or after losses but cannot prove it.
**Against the alternatives:** engines tell you what move was wrong; Klimate tells you which habit costs rating, with intervals, and says "no reliable pattern" when the data is too thin. Free, no account, nothing stored.
**Proof points (all verifiable):** every headline number is audited against the raw Chess.com API; habits are priced from measured per-game rating changes; the Opponent Scout and Play Now work from public data only.

## Honest limits to state up front
- Psychology and tilt tools already exist (Statmate, ChessTracker); the edge is rigor and measured cost.
- Chess.com only for now. Differences between habits show association, not proof of cause.
- Engine labels are approximate and can differ slightly between Stockfish builds.

## Audiences and hooks
| Audience | Hook | Page to link |
|---|---|---|
| Players who tilt | "What do 3 losses in a row actually cost you?" | Elo Ledger / Play Now |
| Improvers | "Which of your winning positions do you throw away?" | Coach Report |
| Tournament and club players | "Scout any opponent in 30 seconds" | Opponent Scout |
| Streamers and coaches | Weekly card and Wrapped image to share | Weekly Report, Wrapped |

## Post drafts (edit before use)
**Reddit r/chess (story first, tool second):**
> I got tired of guessing why I lose rating, so I measured it. Using my public Chess.com games, I priced my habits in rating points: [fill in your own finding, e.g. losing after a loss]. I built a free tool that does this for anyone (no login, nothing stored). It also says "no reliable pattern" when the data is too thin. Feedback welcome: klimate.streamlit.app

**Short post (X/Facebook):**
> What do your habits cost you in rating points? Type your Chess.com name and see. Free, private, checked against the raw data. klimate.streamlit.app

Rules: follow each community's self-promotion rules, lead with a real finding, answer every comment, never claim improvement guarantees.

## FAQ
- **Is it free?** Yes. Paid features may come later; the core stays free.
- **Do you store my games?** No. Public Chess.com data is read on demand.
- **Why does it sometimes say "no reliable pattern"?** Because small samples fake patterns; we only show what beats chance.
- **Can I look at someone else?** Yes, public games only (Opponent Scout, Compare).

## Two-week launch plan
1. Week 1: private beta with 10-20 players from clubs or friends; watch `feedback`, `history_loaded`, `coach_auto_ready`, `scout_run` and `demo_clicked` in GA4; fix the top three complaints.
2. Week 2: one post per channel, spaced out; one real finding per post; reply within a day.
3. Review: which page do returning users open, and where do new users drop (landing, load, first page)? Cut or improve accordingly.

## Metrics that matter
Activation (loaded a dashboard / visited landing), page depth (opened 3+ pages), return within 7 days, share of `feedback` = up, Opponent Scout use.

## Before promoting
Confirm Chess.com API terms still allow this use, keep the User-Agent pointing to the GitHub page, and avoid Chess.com trademarks and feature names in marketing copy.
