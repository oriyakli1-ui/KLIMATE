"""Statistical building blocks shared by every tool (pure, tested, no Streamlit).

One definition of each number: how a result is scored, how uncertain a rate is, what a
performance rating is. Pages must use these instead of re-deriving them.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

# Result strings used by Chess.com for the player who did NOT win a decisive game.
LOSS_RESULTS = {"checkmated", "timeout", "resigned", "abandoned", "lose", "loss"}
DRAW_RESULTS = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}


def score_result(mine: object, opponent: object) -> Optional[float]:
    """Score from the player's view: 1 win, 0.5 draw, 0 loss, None when the result is not understood.

    Both sides' results are used so that unusual winner strings never turn a win into a loss.
    """
    m = str(mine or "").strip().lower()
    o = str(opponent or "").strip().lower()
    if m == "win":
        return 1.0
    if m in DRAW_RESULTS and (o in DRAW_RESULTS or not o):
        return 0.5
    if m in LOSS_RESULTS:
        return 0.0
    if o == "win" or o in {"kingofthehill", "threecheck", "bughousepartnerwin"}:
        return 0.0
    if o in LOSS_RESULTS:
        return 1.0  # opponent lost, so the player won even if their own string is unusual
    return None


def mean_ci(values: Sequence[float], z: float = 1.96) -> Tuple[float, float, float]:
    """Mean with a normal-approximation confidence interval (valid for 0/0.5/1 scores, n >= ~10)."""
    a = np.asarray(values, dtype=float)
    n = len(a)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    m = float(a.mean())
    if n < 2:
        return m, float("nan"), float("nan")
    half = z * float(a.std(ddof=1)) / math.sqrt(n)
    return m, max(0.0, m - half), min(1.0, m + half)


def wilson_interval(successes: float, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a proportion (better than the normal one for small n)."""
    if n <= 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def expected_score(rating: float, opponent: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent - rating) / 400.0))


def performance_rating(opponent_ratings: Iterable[float], total_score: float, cap: float = 800.0) -> float:
    """Rating at which the expected total score equals the actual one (Elo logistic model).

    The result is capped at +-``cap`` points from the average opponent, like FIDE's 800-point rule,
    so perfect or zero scores do not produce infinite ratings. NaN for no games.
    """
    opp = np.asarray([o for o in opponent_ratings if o == o], dtype=float)
    n = len(opp)
    if n == 0:
        return float("nan")
    avg = float(opp.mean())
    lo, hi = avg - cap, avg + cap

    def total_expected(r: float) -> float:
        return float(np.sum(1.0 / (1.0 + 10 ** ((opp - r) / 400.0))))

    if total_score <= total_expected(lo):
        return lo
    if total_score >= total_expected(hi):
        return hi
    for _ in range(60):  # bisection: total_expected is increasing in r
        mid = (lo + hi) / 2.0
        if total_expected(mid) < total_score:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def z_difference(n1: int, s1: float, n2: int, s2: float) -> float:
    """z statistic of the difference of two mean scores (worst-case variance 0.25 per game)."""
    if min(n1, n2) < 2:
        return 0.0
    return (s1 - s2) / math.sqrt(0.25 / n1 + 0.25 / n2)


def significantly_different(n1: int, s1: float, n2: int, s2: float, z: float = 1.64) -> bool:
    """True when two mean scores differ by more than chance explains (one-sided ~95% by default).

    Use a larger ``z`` (about 2.5) when the pair was picked as the best of many candidates.
    """
    return abs(z_difference(n1, s1, n2, s2)) >= z


def linear_trend(values: Sequence[float]) -> Tuple[float, float]:
    """Least-squares slope per step and its standard error (nan when fewer than 5 points)."""
    y = np.asarray(values, dtype=float)
    n = len(y)
    if n < 5:
        return float("nan"), float("nan")
    x = np.arange(n, dtype=float)
    xm = x.mean()
    sxx = float(((x - xm) ** 2).sum())
    slope = float(((x - xm) * (y - y.mean())).sum() / sxx)
    resid = y - (y.mean() + slope * (x - xm))
    se = math.sqrt(float((resid ** 2).sum()) / (n - 2) / sxx) if n > 2 else float("nan")
    return slope, se


def count_plies(pgn: object) -> int:
    """Number of half-moves in a PGN movetext (comments and move numbers removed)."""
    if not isinstance(pgn, str) or not pgn.strip():
        return 0
    body = pgn.split("\n\n", 1)[-1] if "[Event" in pgn or "\n\n" in pgn else pgn
    body = _strip_comments(body)
    tokens = [t for t in body.replace("\n", " ").split(" ") if t]
    count = 0
    for t in tokens:
        if t in {"1-0", "0-1", "1/2-1/2", "*"}:
            continue
        if t[0].isdigit() and (t.endswith(".") or "..." in t):
            continue
        if t[0].isdigit() and "." in t:  # "12.Nf3" glued form
            t = t.split(".")[-1]
            if not t:
                continue
        count += 1
    return count


def _strip_comments(text: str) -> str:
    out, depth = [], 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)
