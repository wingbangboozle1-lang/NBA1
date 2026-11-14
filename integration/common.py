"""Shared helpers for the integration desk.

Design rule for this whole directory: nothing is written to a page unless it can
be traced to a row in a JSON file under `data/`, and nothing goes into a JSON file
under `data/live/` unless it was transcribed from an official NBA property. Where a
number is a modelling choice it is declared in `ASSUMPTIONS` and printed as such on
the site; where a number is missing it stays None and renders as a blank cell.
"""

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "data", "live")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "integration", "out")

OFFICIAL_HOSTS = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com"}

TEAM_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


# --------------------------------------------------------------------- io
def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
    return os.path.join(OUT, name)


def assert_official(url, context=""):
    """Fail loudly if a value claims a source that is not an NBA property."""
    if not url:
        raise AssertionError(f"missing source_url {context}")
    host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    if host not in OFFICIAL_HOSTS:
        raise AssertionError(f"non-official source {host!r} {context}")
    return url


# ------------------------------------------------------------------- stats
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs, sample=True):
    xs = [x for x in xs if x is not None]
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    ss = sum((x - m) ** 2 for x in xs)
    return math.sqrt(ss / (n - 1 if sample else n))


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    dy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def fisher_ci(r, n, z=1.96):
    """95% CI for a Pearson r via Fisher z. Returns (lo, hi) or None."""
    if r is None or n < 4:
        return None
    r = max(-0.999999, min(0.999999, r))
    zz = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo_z, hi_z = zz - z * se, zz + z * se
    inv = lambda t: (math.exp(2 * t) - 1) / (math.exp(2 * t) + 1)
    return round(inv(lo_z), 4), round(inv(hi_z), 4)


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion — the hit-rate interval."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - hw), 4), round(min(1.0, c + hw), 4)


def binom_two_sided(k, n, p0=0.5):
    """Exact two-sided binomial tail (double the smaller tail, capped at 1).

    Small n by construction here (a slate is dozens of bets), so the exact
    enumeration is cheap and avoids a normal-approximation lie.
    """
    if n == 0:
        return None

    def pmf(i):
        return math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i)

    obs = pmf(k)
    total = sum(pmf(i) for i in range(n + 1))
    tail = sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs * (1 + 1e-9))
    return min(1.0, tail / total)


def block_bootstrap(values, stat=mean, blocks=2000, block=5, seed=7):
    """Stationary block bootstrap. Blocks matter: a slate is not i.i.d. — games on
    the same night share injuries, rest and venue, so resampling single games
    understates the true spread of a season's results."""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n < 3:
        return None
    rng = _Lcg(seed)
    out = []
    for _ in range(blocks):
        sample = []
        while len(sample) < n:
            start = int(rng.next() * n)
            for j in range(block):
                sample.append(vals[(start + j) % n])
        out.append(stat(sample[:n]))
    out.sort()
    return round(out[int(0.025 * len(out))], 4), round(out[int(0.975 * len(out))], 4)


class _Lcg:
    """Tiny deterministic generator so the bootstrap interval is reproducible.

    Python's own `random` is deliberately not used: a published confidence interval
    that changes between runs cannot be checked by anyone.
    """

    def __init__(self, seed=7):
        self.s = (seed * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)

    def next(self):
        self.s = (self.s * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        return (self.s >> 11) / float(1 << 53)


def frechet_bounds(pa, pb, lo=True):
    """Fréchet–Hoeffding bounds on P(A and B) given the marginals.

    Used wherever a parlay or SGP joint probability is published: the bounds are the
    only statement about dependence that is true without a measured correlation.
    """
    if pa is None or pb is None:
        return None
    return round(max(0.0, pa + pb - 1.0) if lo else min(pa, pb), 4)


def joint_bounds(pa, pb):
    return {"lo": frechet_bounds(pa, pb, True), "hi": frechet_bounds(pa, pb, False)}


def fmt(v, nd=1, blank="—"):
    if v is None or v == "":
        return blank
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def pct(v, nd=1):
    return "—" if v is None else f"{v * 100:.{nd}f}%"
