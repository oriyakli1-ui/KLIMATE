"""Independent check of Klimate's numbers against the raw Chess.com data.

Run:  py -3.13 tools/audit_against_chesscom.py oriyakli1 [months]

Every figure is recomputed here with deliberately different code (plain loops over the raw API
JSON, no pandas helpers from the app) and compared with what the app's modules return.
Exit code 1 if anything differs.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import warnings

warnings.filterwarnings("ignore")

import analytics  # noqa: E402
import data_engine  # noqa: E402
import insights  # noqa: E402
import metrics  # noqa: E402
import spatial  # noqa: E402

DRAWS = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}
failures: list[str] = []


def check(name: str, ours, truth, tol: float = 0.0) -> None:
    ok = abs(ours - truth) <= tol if isinstance(ours, (int, float)) and isinstance(truth, (int, float)) else ours == truth
    print(f"{'OK  ' if ok else 'FAIL'} {name}: app={ours!r} independent={truth!r}")
    if not ok:
        failures.append(name)


def main(user: str, months: int = 6) -> int:
    me = user.lower()
    archives = data_engine._safe_get(f"https://api.chess.com/pub/player/{me}/games/archives")["archives"][-months:]
    raw = []
    for url in archives:
        raw += data_engine._month_games(url, me)

    # ---- independent selection of "real" games: standard chess, not daily, >= 6 plies
    def plies(pgn: str) -> int:
        body = re.sub(r"\{[^}]*\}", " ", pgn.split("\n\n", 1)[-1])
        toks = [t for t in body.split() if not re.fullmatch(r"\d+\.+|1-0|0-1|1/2-1/2|\*", t)]
        return len(toks)

    games = [g for g in raw if g.get("rules") == "chess" and g.get("time_class") != "daily" and plies(g["pgn"]) >= 6]
    print(f"raw games {len(raw)} -> real games {len(games)}")

    df = data_engine.fetch_games(user, 100000, months)
    check("games loaded", len(df), len(games))
    g = insights.enrich_games(df, user)
    check("enriched rows", len(g), len(games))

    # ---- results
    w = d = l = 0
    for x in games:
        side = "white" if x["white"]["username"].lower() == me else "black"
        mine, other = x[side]["result"], x["black" if side == "white" else "white"]["result"]
        if mine == "win":
            w += 1
        elif mine in DRAWS:
            d += 1
        else:
            assert other == "win", (mine, other)
            l += 1
    s = insights.overall_summary(g)
    if not games:
        print("no standard games in this window: nothing else to compare")
        return 0
    check("wins", s["wins"], w); check("draws", s["draws"], d); check("losses", s["losses"], l)
    check("score", s["score"], (w + 0.5 * d) / len(games), 1e-9)

    # ---- per time class
    per = collections.defaultdict(lambda: [0, 0.0])
    for x in games:
        side = "white" if x["white"]["username"].lower() == me else "black"
        res = x[side]["result"]
        per[x["time_class"]][0] += 1
        per[x["time_class"]][1] += 1.0 if res == "win" else (0.5 if res in DRAWS else 0.0)
    for tc, (n, pts) in per.items():
        sub = g[g["time_class"] == tc]
        check(f"{tc} games", len(sub), n)
        check(f"{tc} score", float(sub["score"].mean()), pts / n, 1e-9)

    # ---- streak from the newest game
    newest = sorted(games, key=lambda x: x["end_time"], reverse=True)
    def outcome(x):
        side = "white" if x["white"]["username"].lower() == me else "black"
        r = x[side]["result"]
        return "win" if r == "win" else ("draw" if r in DRAWS else "loss")
    kind, n = outcome(newest[0]), 0
    if kind != "draw":
        for x in newest:
            if outcome(x) != kind:
                break
            n += 1
    else:
        kind = "none"
    check("current streak", insights.current_streak(g), (kind, n))

    # ---- hour of day (start time, UTC and Jerusalem)
    for tzname in ("UTC", "Asia/Jerusalem"):
        counts = collections.Counter()
        for x in games:
            hdr = dict(re.findall(r'\[(\w+) "([^"]*)"\]', x["pgn"]))
            start = datetime.strptime(hdr["UTCDate"] + " " + hdr["UTCTime"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
            counts[start.astimezone(ZoneInfo(tzname)).hour] += 1
        prof = insights.hourly_profile(g, tzname)
        check(f"hour histogram {tzname}", {int(h): int(c) for h, c in zip(prof.hour, prof.games) if c}, dict(counts))

    # ---- sessions: idle time between a game's end and the next start > 30 min
    spans = []
    for x in games:
        hdr = dict(re.findall(r'\[(\w+) "([^"]*)"\]', x["pgn"]))
        st = datetime.strptime(hdr["UTCDate"] + " " + hdr["UTCTime"], "%Y.%m.%d %H:%M:%S")
        en = datetime.strptime(hdr["EndDate"] + " " + hdr["EndTime"], "%Y.%m.%d %H:%M:%S")
        spans.append((st, en))
    spans.sort()
    sessions, prev_end = 0, None
    for st, en in spans:
        if prev_end is None or (st - prev_end).total_seconds() / 60 > 30:
            sessions += 1
        prev_end = en if prev_end is None else max(prev_end, en)
    check("sessions", insights.session_profile(g)["sessions"], sessions)

    # ---- opening families from the ECO URL
    fam = collections.Counter()
    for x in games:
        name = x.get("eco", "").rsplit("/", 1)[-1]
        fam["Unknown" if name.lower() in ("", "undefined") else name] += 1
    ours = collections.Counter(g["opening"])
    check("games without an opening name", ours.get("Unknown", 0), fam.get("Unknown", 0))
    check("distinct opening families <= distinct ECO slugs", len(ours) <= len(set(x.get("eco") for x in games)) + 1, True)

    # ---- ratings: Chess.com publishes every rating AFTER the game. Rebuild the rating change of each
    # game (this rating minus the previous one in the same pool), the pre-game ratings and the
    # performance rating with plain loops, and compare with the app's enriched frame / ledger.
    pools = collections.defaultdict(list)
    for x in games:
        if not x.get("rated"):
            continue
        side = "white" if x["white"]["username"].lower() == me else "black"
        opp = "black" if side == "white" else "white"
        res = x[side]["result"]
        pools[x["time_class"]].append((x["end_time"], x[side]["rating"], x[opp]["rating"], 1.0 if res == "win" else (0.5 if res in DRAWS else 0.0)))
    all_valid = []
    for tc, lst in pools.items():
        lst.sort()
        valid = []
        for i in range(1, len(lst)):
            ch = lst[i][1] - lst[i - 1][1]
            sc = lst[i][3]
            ok = abs(ch) <= 45 and ((sc == 1.0 and ch >= 0) or (sc == 0.0 and ch <= 0) or (sc == 0.5 and abs(ch) <= 25))
            if ok:
                valid.append((lst[i][2] + ch, sc, ch))      # (opponent rating before the game, score, change)
        all_valid += [v[2] for v in valid]
        if len(valid) >= 20:
            total = sum(sc for _, sc, _ in valid)
            avg = sum(o for o, _, _ in valid) / len(valid)
            best = min(range(int(avg) - 800, int(avg) + 801),
                       key=lambda r: abs(sum(1 / (1 + 10 ** ((o - r) / 400)) for o, _, _ in valid) - total))
            sub = g[(g["time_class"] == tc) & g["rated"] & g["rating_change"].notna()]
            check(f"games with a measured rating change {tc}", len(sub), len(valid))
            ours_r = metrics.performance_rating(sub["opp_rating"].to_numpy(), float(sub["score"].sum()))
            check(f"performance rating {tc}", round(ours_r), best, 1)
    import ledger  # noqa: E402

    summ = ledger.ledger(g)["summary"]
    check("ledger: usable games", summ["usable_games"], len(all_valid))
    check("ledger: net rating points", round(summ["net_points"], 6), float(sum(all_valid)))

    # ---- live ratings and all-time best
    stats = data_engine._safe_get(f"https://api.chess.com/pub/player/{me}/stats")
    r = analytics.get_real_time_ratings(user)
    have = [tc for tc in ("rapid", "blitz", "bullet") if f"chess_{tc}" in stats]      # not everyone plays every time control
    for tc in ("rapid", "blitz", "bullet"):
        if tc in have:
            check(f"current {tc}", r[tc], stats[f"chess_{tc}"]["last"]["rating"])
            check(f"best {tc}", r["best"][tc], stats[f"chess_{tc}"]["best"]["rating"])
        else:
            check(f"current {tc} (not played)", r[tc], "N/A")
    if have:
        check("peak", r["peak"], max(stats[f"chess_{tc}"]["best"]["rating"] for tc in have))

    # ---- spatial: total activity equals the number of the player's moves
    pairs = [(x["pgn"], x["white"]["username"].lower() == me) for x in games[:60]]
    act, cap, used = spatial.heatmaps(pairs, "All")
    my_moves = 0
    for pgn, is_white in pairs:
        n_pl = plies(pgn)
        my_moves += (n_pl + 1) // 2 if is_white else n_pl // 2
    check("spatial: moves counted == player's moves", int(act.sum()), my_moves)

    # ---- clocks: final clock of the last user move from a regex over %clk
    ok = bad = 0
    for x in games[:80]:
        side_white = x["white"]["username"].lower() == me
        clk = re.findall(r"\[%clk (\d+):(\d+):([\d.]+)\]", x["pgn"])
        secs = [int(h) * 3600 + int(m) * 60 + float(s) for h, m, s in clk]
        mine = secs[0::2] if side_white else secs[1::2]
        if not mine:
            continue
        # rebuild the same game inside the app frame by url
        row = df[df["url"] == x["url"]]
        if row.empty:
            continue
        gi = insights.enrich_games(row, user)
        if abs(float(gi["final_clock"].iloc[0]) - mine[-1]) < 1e-6:
            ok += 1
        else:
            bad += 1
    check("final clock matches the PGN (games checked)", bad, 0)
    print(f"      ({ok} games compared)")

    print("\nALL CHECKS PASSED" if not failures else f"\n{len(failures)} CHECK(S) FAILED: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "oriyakli1", int(sys.argv[2]) if len(sys.argv) > 2 else 6))
