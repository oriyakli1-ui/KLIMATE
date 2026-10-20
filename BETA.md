# Klimate private beta kit

Goal: 20 real players use Klimate for a week and tell us what is confusing, wrong or worth paying for. Nothing is sold during the beta.

## Who to invite (aim for 20)
10 club or online friends rated 800-1800, 5 players who stream or coach, 5 from a community you already belong to. Mix Chess.com and Lichess.

## Invitation message (edit before sending)
> Hi [name]! I built a free tool that shows what your chess habits cost you in rating points (tilt, late-night games, time scrambles) from your public games. Could you try it for a week and tell me what is confusing or wrong? No login, nothing stored: klimate.streamlit.app. Takes 3 minutes. Thank you!

## What to ask (create a free Google Form with these three questions)
1. In one sentence, what does Klimate do? (tests whether the message is clear)
2. Which page was most useful, and what did you expect to find but did not?
3. Anything wrong or confusing? Paste the username you used so we can check the numbers.
Optional: Would you pay for more depth, and how much per month? (the Klimate Pro page measures this anonymously)

Set the form's address in the `KLIMATE_WAITLIST_URL` environment variable (Streamlit secrets) to show a "Join the waiting list" link on the Pro page.

## What to watch in Google Analytics
`analysis_loaded` (activation), `phased=true` share, `coach_auto_ready`, `page_selected` by page, `scout_run`, `summary_card_downloaded`, `feedback` up vs down, `pro_viewed` and `pro_answer` by price.

## Go / no-go before a public launch
- [ ] Audit passes for 10+ different public players on both platforms (done for 12 Chess.com players and one Lichess account).
- [ ] No page crashes in the beta; top 3 complaints fixed.
- [ ] 70%+ of beta users reach the Home screen in under 15 seconds (ask in the form).
- [ ] Feedback "useful" at least 60%.
- [ ] At least some users open 3+ pages and return within 7 days.
- [ ] Privacy text reviewed; Chess.com API terms re-checked.
- [ ] Rollback plan: `git revert` the last merge on `main` and push; Streamlit Cloud redeploys within a few minutes.

## After the beta
If the Pro "I would pay" answers are meaningful at some price, build accounts and payments (needs a backend and costs money). If not, keep Klimate free and improve the free product.
