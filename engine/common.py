"""Shared math + IO helpers. Standard library only (no numpy) so the
GitHub Actions runner needs no install step.

Every function here is deterministic: same input -> same output.
"""

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "docs", "data")


# --------------------------------------------------------------------------- IO

def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")
    return path


def rows_by_cols(block):
    """Turn {"cols":[...], "rows":[[...]]} into a list of dicts."""
    cols = block["cols"]
    return [dict(zip(cols, r)) for r in block["rows"]]


# ------------------------------------------------------------------- statistics

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    """Sample standard deviation (n-1)."""
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_pdf(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def norm_ppf(p):
    """Inverse normal CDF (Acklam's algorithm, |error| < 1.15e-9)."""
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    tiny, eps, maxit = 1e-30, 3e-16, 300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                          + b * math.log(1.0 - x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def t_sf(t, df):
    """Upper-tail P(T > t) for Student-t with df degrees of freedom."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    p = 0.5 * betainc(df / 2.0, 0.5, x)
    return p if t > 0 else 1.0 - p


def pearson(xs, ys):
    """Pearson r, plus a two-sided p-value from the t distribution."""
    xs, ys = list(xs), list(ys)
    n = len(xs)
    if n < 4:
        return 0.0, 1.0, n
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return 0.0, 1.0, n
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    if n <= 2:
        return r, 1.0, n
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = 2.0 * t_sf(abs(t), n - 2)
    return r, p, n


def binom_pmf(k, n, p):
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binom_test_two_sided(k, n, p=0.5):
    """Exact two-sided binomial test: probability of a result at least as
    extreme as the one observed."""
    if n == 0:
        return 1.0
    obs = binom_pmf(k, n, p)
    if obs == 0:
        return 0.0
    tol = obs * (1 + 1e-9)
    return sum(binom_pmf(i, n, p) for i in range(n + 1)
               if binom_pmf(i, n, p) <= tol)


def wilson_ci(k, n, z=1.959963985):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    ph = k / n
    denom = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / denom
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bivariate_normal_cdf(z1, z2, rho):
    """P(Z1 <= z1, Z2 <= z2) for standard bivariate normal with correlation rho.

    Uses  P = int phi(u) * Phi((z2 - rho*u)/sqrt(1-rho^2)) du  from -inf to z1,
    evaluated with Simpson's rule on [z1-8, z1].
    """
    if abs(rho) < 1e-12:
        return norm_cdf(z1) * norm_cdf(z2)
    s = math.sqrt(max(1e-12, 1.0 - rho * rho))
    lo, hi = z1 - 8.0, z1
    n = 4000
    if n % 2:
        n += 1
    h = (hi - lo) / n

    def f(u):
        return norm_pdf(u) * norm_cdf((z2 - rho * u) / s)

    total = f(lo) + f(hi)
    for i in range(1, n):
        total += f(lo + i * h) * (4 if i % 2 else 2)
    return total * h / 3.0


def bootstrap_ci(xs, fn, iters=2000, seed=20261113):
    """Percentile bootstrap CI for statistic fn(xs). xs = list of records."""
    import random
    rng = random.Random(seed)
    n = len(xs)
    if n < 2:
        return (0.0, 0.0)
    vals = []
    for _ in range(iters):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        vals.append(fn(sample))
    vals.sort()
    lo = vals[int(0.025 * iters)]
    hi = vals[min(iters - 1, int(0.975 * iters))]
    return (lo, hi)


# ------------------------------------------------------------------- formatting

def rnd(x, nd=2):
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return round(x + 0.0, nd)


def american_from_prob(p):
    """Fair American price for probability p (no vig)."""
    if p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def prob_from_american(o):
    if o is None:
        return None
    if o < 0:
        return (-o) / ((-o) + 100.0)
    return 100.0 / (o + 100.0)


ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

TEAM_NAME = {v: k for k, v in ABBR.items()}

TEAM_ID = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}
