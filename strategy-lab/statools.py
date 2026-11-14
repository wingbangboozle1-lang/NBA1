"""Exact statistics for the strategy lab — no normal approximations, no scipy.

Everything here is computed from counts, so a reviewer can re-derive any number in the
lab from the play log with pencil and paper if they want to.
"""
from __future__ import annotations

import bisect
import math
import random
import statistics as st

SEED = 20261114          # fixed: every number in this directory is reproducible
N_BOOT = 2000            # moving-block bootstrap resamples
BOOT_BLOCK = 3           # bootstrap block length, in plays (ordered by date)
N_MC = 6000              # shared-draw library simulations
BREAKEVEN = 110.0 / 210.0  # 0.523809... the stated -110 convention, not an observed price


def rnd(x, d=2):
    if x is None:
        return None
    return round(float(x), d)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _logcomb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def binom_two_sided(w, n, p=0.5):
    """Exact two-sided binomial p-value (minlike): the probability of outcomes at
    least as unlikely as the observed one."""
    if not n:
        return None

    def pk(k):
        return math.exp(_logcomb(n, k) + k * math.log(p) + (n - k) * math.log(1 - p))

    p_obs = pk(w)
    tot = 0.0
    for k in range(n + 1):
        if pk(k) <= p_obs * (1 + 1e-9):
            tot += pk(k)
    return min(1.0, tot)


def binom_one_sided_ge(w, n, p):
    """P(X >= w), X ~ Bin(n, p): how often a coin with that edge wins at least this much."""
    if not n:
        return None
    tot = 0.0
    for k in range(w, n + 1):
        tot += math.exp(_logcomb(n, k) + k * math.log(p) + (n - k) * math.log(1 - p))
    return min(1.0, tot)


def poisson_binom_ge(probs, k):
    """Exact P(S >= k) for S = sum of independent Bernoulli(p_i), by dynamic program.

    This is the test the repository has been missing. With no market price there is no
    external number to beat, so the only well-defined null is 'the originated line is
    right': a signal has to win more often than the model's own probability said it would.
    """
    probs = [min(max(p, 1e-9), 1 - 1e-9) for p in probs]
    n = len(probs)
    if n == 0:
        return None
    dist = [0.0] * (n + 1)
    dist[0] = 1.0
    for i, p in enumerate(probs):
        nd = [0.0] * (n + 1)
        for s in range(i + 1):
            if dist[s] == 0.0:
                continue
            nd[s] += dist[s] * (1 - p)
            nd[s + 1] += dist[s] * p
        dist = nd
    return min(1.0, sum(dist[k:]))


def wilson(w, n, z=1.959963984540054):
    if not n:
        return (None, None)
    ph = w / n
    den = 1 + z * z / n
    ctr = (ph + z * z / (2 * n)) / den
    half = (z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))) / den
    return (ctr - half, ctr + half)


def t_two_sided_p(t, df):
    """Two-sided p for a t statistic, integrating the t density by Simpson's rule."""
    if not df or t is None or df <= 0:
        return None

    def dens(x):
        return math.exp(-0.5 * (df + 1) * math.log1p(x * x / df))

    c = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)
    hi = abs(t)
    top = hi + 60.0
    n = 4000
    h = (top - hi) / n
    acc = dens(hi) + dens(top)
    for i in range(1, n):
        acc += dens(hi + i * h) * (4 if i % 2 else 2)
    return min(1.0, 2.0 * c * acc * h / 3.0)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, None, None
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return None, None, None
    r = sxy / math.sqrt(sxx * syy)
    tstat = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    return r, tstat, t_two_sided_p(tstat, n - 2)


def _solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda rr: abs(M[rr][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for cc in range(c, n + 1):
                    M[r][cc] -= f * M[c][cc]
    return [M[i][n] / M[i][i] for i in range(n)]


def _invert(A):
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda rr: abs(M[rr][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        M[c] = [x / pv for x in M[c]]
        for r in range(n):
            if r != c:
                f = M[r][c]
                M[r] = [M[r][cc] - f * M[c][cc] for cc in range(2 * n)]
    return [row[n:] for row in M]


def ols(rows, y):
    """Least squares with an implicit intercept in column 0."""
    n, k = len(rows), len(rows[0]) + 1
    X = [[1.0] + list(r) for r in rows]
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    beta = _solve(XtX, Xty)
    if beta is None:
        return None
    resid = [y[i] - sum(X[i][a] * beta[a] for a in range(k)) for i in range(n)]
    dof = max(1, n - k)
    s2 = sum(r * r for r in resid) / dof
    inv = _invert(XtX)
    se = [math.sqrt(max(1e-15, s2 * inv[a][a])) for a in range(k)] if inv else [0.0] * k
    tstat = [(beta[a] / se[a]) if se[a] else None for a in range(k)]
    return {"beta": beta, "se": se, "t": tstat, "n": n, "dof": dof, "resid": resid}


def benjamini_hochberg(pairs):
    """Step-up q-values. pairs: [(id, p)]."""
    obs = sorted([(i, p) for i, p in pairs if p is not None], key=lambda x: x[1])
    m = len(obs)
    out, prev = {}, 1.0
    for rank in range(m, 0, -1):
        _id, p = obs[rank - 1]
        q = min(prev, p * m / rank)
        out[_id] = q
        prev = q
    for i, p in pairs:
        if p is None:
            out[i] = None
    return out


def block_bootstrap(values, B=N_BOOT, block_len=BOOT_BLOCK):
    """Moving-block bootstrap on a sequence ordered by date. Blocks are resampled, not
    single plays, so the within-slate dependence between a strategy's plays survives the
    resample; an IID bootstrap understates the spread of a same-night series."""
    n = len(values)
    if n < block_len:
        return None
    rng = random.Random(SEED + 7)
    starts = list(range(0, n - block_len + 1))
    means = []
    for _ in range(B):
        sample = []
        while len(sample) < n:
            s = rng.choice(starts)
            sample.extend(values[s:s + block_len])
        means.append(st.mean(sample[:n]))
    means.sort()
    return {"mean": rnd(st.mean(values), 3),
            "ci_lo": rnd(means[int(0.025 * (len(means) - 1))], 3),
            "ci_hi": rnd(means[int(0.975 * (len(means) - 1))], 3),
            "p_mean_le_0": rnd(sum(1 for m in means if m <= 0) / len(means), 4),
            "B": len(means), "block_len": block_len}


def auc(p_home, y_home):
    """Mann-Whitney AUC with tie correction."""
    n = len(p_home)
    if n < 4 or sum(y_home) in (0, n):
        return None
    pos = [p for p, y in zip(p_home, y_home) if y == 1]
    neg = [p for p, y in zip(p_home, y_home) if y == 0]
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else (0.5 if a == b else 0.0)
    return wins / (len(pos) * len(neg))


_CDF_CACHE = {}


def binom_sample(n, p, rng):
    """Inverse-CDF draw from Bin(n, p) with a cached CDF."""
    key = (n, round(p, 10))
    cdf = _CDF_CACHE.get(key)
    if cdf is None:
        cdf, acc = [], 0.0
        for k in range(n + 1):
            acc += math.exp(_logcomb(n, k) + k * math.log(p) + (n - k) * math.log(1 - p))
            cdf.append(acc)
        cdf[-1] = 1.0
        _CDF_CACHE[key] = cdf
    return bisect.bisect_left(cdf, rng.random())
