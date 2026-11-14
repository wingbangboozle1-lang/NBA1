"""Shared helpers for the NBA1 line-origination engine (session arena/e32856d8-nba1).

Rule enforced everywhere in this package
----------------------------------------
A number is only produced if it can be traced to a row of an official source file in
data/official/.  Anything else is emitted as None and lands on the site's
"Flagged for Review" page.  Nothing is inferred, interpolated or back-solved.
"""
from __future__ import annotations

import json
import math
import os
import random
from datetime import date as _date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL = os.path.join(ROOT, "data", "official")

TEAMS = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
         "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
         "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}


def load(name: str):
    with open(os.path.join(OFFICIAL, name), encoding="utf-8") as fh:
        return json.load(fh)


def d(s: str) -> _date:
    y, m, dd = (int(x) for x in s.split("-"))
    return _date(y, m, dd)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# --------------------------------------------------------------------------
# statistics helpers (written out explicitly so the method is auditable)
# --------------------------------------------------------------------------
def pearson(xs, ys):
    n = len(xs)
    if n < 4:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    # two-sided t test
    if abs(r) >= 1:
        return {"r": r, "n": n, "p": 0.0, "lo": None, "hi": None}
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = 2 * (1 - _student_t_cdf(abs(t), n - 2))
    # Fisher z 95% interval
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo = math.tanh(z - 1.96 * se)
    hi = math.tanh(z + 1.96 * se)
    return {"r": r, "n": n, "p": p, "lo": lo, "hi": hi}


def _student_t_cdf(t: float, df: int) -> float:
    """Regularised incomplete beta via continued fraction (Numerical Recipes)."""
    x = df / (df + t * t)
    return 1 - 0.5 * _betai(df / 2.0, 0.5, x)


def _betacf(a, b, x):
    tiny, eps = 1e-30, 3e-12
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    dd = 1.0 - qab * x / qap
    if abs(dd) < tiny:
        dd = tiny
    dd = 1.0 / dd
    h = dd
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        dd = 1.0 + aa * dd
        if abs(dd) < tiny:
            dd = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        dd = 1.0 / dd
        h *= dd * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        dd = 1.0 + aa * dd
        if abs(dd) < tiny:
            dd = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        dd = 1.0 / dd
        de = dd * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1 - x))
    bt = math.exp(lbeta)
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def brier(pairs):
    """pairs = [(forecast_probability, outcome 0/1)]"""
    if not pairs:
        return None
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs)
