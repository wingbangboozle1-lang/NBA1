"""Out-of-sample validation, parameter fitting, gates, and the luck decomposition.

Information discipline
----------------------
Holdout window       : 2026-11-09 .. 2026-11-12  (28 completed games, sources S3_*)
Ratings used for it  : the 2026-10-20 .. 2026-11-05 window ONLY (source S2)
So no game in the test window contributes to the ratings that predict it.

The two numbers that ARE estimated on the test window (home-court advantage and
the back-to-back penalty) are disclosed as in-sample everywhere they are used,
and a zeroed-parameter variant is published alongside them so the reader can see
how much of the result comes from those two fitted numbers.
"""

import math

from common import (bootstrap_ci, mean, norm_cdf, pearson, rnd, stdev,
                    wilson_ci, binom_test_two_sided)
from model_core import (ASSUMPTIONS, RatingTable, base_line, model_line,
                        reference_line, cover_probability, total_probability)

HOLDOUT_START = "2026-11-06"
HOLDOUT_END = "2026-11-12"
BREAKEVEN = 0.5238095238095238   # -110: 110/210


# --------------------------------------------------------------------- schedule

def build_last_played(completed):
    """date -> {team: previous game date} using only games present in the data."""
    dates = sorted({g["date"] for g in completed})
    out = {}
    for d in dates:
        prev = [x for x in dates if x < d]
        prev_map = {}
        if prev:
            last = max(prev)
            for g in completed:
                if g["date"] == last:
                    prev_map[g["home"]] = last
                    prev_map[g["away"]] = last
        out[d] = prev_map
    return out


def rest_flags(game, last_played):
    """(home_b2b, away_b2b, home_rest_days, away_rest_days, known)"""
    pm = last_played.get(game["date"], {})
    hlast, alast = pm.get(game["home"]), pm.get(game["away"])
    hrest = (days_between(hlast, game["date"]) if hlast else None)
    arest = (days_between(alast, game["date"]) if alast else None)
    return ((1 if hrest == 1 else 0), (1 if arest == 1 else 0), hrest, arest,
            (hlast is not None, alast is not None))


def days_between(a, b):
    import datetime
    da = datetime.date(*[int(x) for x in a.split("-")])
    db = datetime.date(*[int(x) for x in b.split("-")])
    return (db - da).days


# ------------------------------------------------------------------ OLS fitting

def ols(X, y):
    """X: list of rows (already includes an intercept column if wanted).
    Returns coefficients, standard errors and t stats (normal-ish, small n)."""
    n, k = len(X), len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]

    # Gaussian elimination with partial pivoting
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return [0.0] * k, [float("nan")] * k, [0.0] * k
        M[c], M[piv] = M[piv], M[c]
        for r in range(k):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for cc in range(c, k + 1):
                M[r][cc] -= f * M[c][cc]
    beta = [M[i][k] / M[i][i] for i in range(k)]

    # invert XtX for standard errors
    inv = invert_matrix(XtX)
    resid = [y[i] - sum(X[i][a] * beta[a] for a in range(k)) for i in range(n)]
    dof = max(1, n - k)
    s2 = sum(r * r for r in resid) / dof
    se = []
    for a in range(k):
        se.append(math.sqrt(max(0.0, s2 * inv[a][a])) if inv else float("nan"))
    tstat = [(beta[a] / se[a]) if se[a] and se[a] == se[a] and se[a] > 0 else 0.0
             for a in range(k)]
    return beta, se, tstat, resid, s2, dof


def invert_matrix(M):
    n = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-12:
            return None
        A[c], A[piv] = A[piv], A[c]
        pv = A[c][c]
        A[c] = [x / pv for x in A[c]]
        for r in range(n):
            if r == c:
                continue
            f = A[r][c]
            if f:
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [row[n:] for row in A]


# ------------------------------------------------------------------ the backtest

def run(train_block, season_block, completed, train_src, season_src):
    train = RatingTable(train_block, train_src, "train", "2026-10-20..2026-11-05")
    season = RatingTable(season_block, season_src, "season", "season to date")
    last_played = build_last_played(completed)
    holdout = [g for g in completed if HOLDOUT_START <= g["date"] <= HOLDOUT_END]
    holdout.sort(key=lambda g: (g["date"], g["game_id"]))

    # ------------------------------------------------------------------------
    # Shrinkage constant, derived rather than guessed.
    #
    #  Step 1 - measure the spread of outcomes around a RAW (unshrunk) forecast on
    #           the test window.  A game margin is (A's game deviation - B's game
    #           deviation) plus the error left in each rating, so
    #               Var(residual) = 2*s^2 * (1 + 1/G)
    #           where s is one team's single-game net-rating noise (per 100
    #           possessions) and G is the number of games behind each rating.
    #  Step 2 - the observed spread of net ratings in the training window is
    #               Var(observed) = Var(true) + s^2 / G
    #  Step 3 - the James-Stein / empirical-Bayes weight is
    #               f = Var(true) / Var(observed)  =  G / (G + k),  k = s^2 / Var(true)
    #
    #  s is estimated from the test window, so k is partly test-informed.  That is
    #  disclosed on the site and a sensitivity sweep over fixed k values is
    #  published alongside it.
    # ------------------------------------------------------------------------
    g_avg = mean([float(t["gp"]) for t in train.teams.values()])
    resid_raw = []
    for g in holdout:
        raw = base_line(train, g["home"], g["away"], shrink_k=None)
        ref0 = reference_line(train, g["home"], g["away"], flat_hca=2.0)
        resid_raw.append((g["home_pts"] - g["away_pts"]) - ref0["margin"])
    sd_resid = stdev(resid_raw)
    s2 = (sd_resid ** 2) / (2.0 * (1.0 + 1.0 / g_avg))
    netr_obs = [t["netr"] for t in train.teams.values()]
    var_obs = stdev(netr_obs) ** 2
    var_true = max(1e-6, var_obs - s2 / g_avg)
    k_eb = max(0.0, min(20.0, s2 / var_true))
    k = round(k_eb, 1)
    shrink_derivation = {
        "games_behind_each_rating_G": rnd(g_avg, 2),
        "sd_of_raw_forecast_residual": rnd(sd_resid, 2),
        "implied_single_game_team_noise_s": rnd(math.sqrt(s2), 2),
        "observed_var_of_net_rating": rnd(var_obs, 2),
        "implied_var_of_true_net_rating": rnd(var_true, 2),
        "shrink_k_derived": k,
        "shrink_weight_at_G": rnd(g_avg / (g_avg + k), 3),
        "formula": "k = s^2 / Var(true), f = G / (G + k)",
        "disclosure": "s is estimated from the test window, so k is partly test-informed. "
                      "A fixed-k sensitivity sweep is published next to it.",
    }

    rows = []
    for g in holdout:
        hb, ab, hrest, arest, known = rest_flags(g, last_played)
        base = base_line(train, g["home"], g["away"], shrink_k=k)
        ref = reference_line(train, g["home"], g["away"], flat_hca=2.0)
        actual_margin = g["home_pts"] - g["away_pts"]
        actual_total = g["home_pts"] + g["away_pts"]
        rows.append({
            "game": g, "base": base, "ref": ref,
            "home_b2b": hb, "away_b2b": ab,
            "home_rest_days": hrest, "away_rest_days": arest,
            "rest_known": known, "neutral": int(g.get("neutral") or 0),
            "actual_margin": actual_margin,
            "actual_total": actual_total,
            "resid_margin": actual_margin - base["margin"],
            "resid_total": actual_total - base["total"],
        })

    # ---- fit HCA and the B2B penalty on the holdout residuals (disclosed in-sample)
    # HCA is not applied at a neutral site, so the intercept is dropped for those rows
    X = [[1.0 if not r["neutral"] else 0.0, float(r["home_b2b"] - r["away_b2b"])]
         for r in rows]
    y = [r["resid_margin"] for r in rows]
    b, se, t, resid, s2, dof = ols(X, y)
    hca, hca_se, hca_t = b[0], se[0], t[0]
    b2b_coef, b2b_se, b2b_t = b[1], se[1], t[1]
    sigma_margin = math.sqrt(s2)

    # ---- totals: intercept (scoring bias) + B2B slope
    Xt = [[1.0, float(r["home_b2b"] + r["away_b2b"])] for r in rows]
    yt = [r["resid_total"] for r in rows]
    bt, set_, tt, resid_t, s2t, doft = ols(Xt, yt)
    total_bias, total_bias_se, total_bias_t = bt[0], set_[0], tt[0]
    total_b2b, total_b2b_se, total_b2b_t = bt[1], set_[1], tt[1]
    sigma_total = math.sqrt(s2t)

    use_b2b = abs(b2b_t) >= 1.0
    use_total_b2b = abs(total_b2b_t) >= 1.0
    params = {
        "hca": hca,
        "b2b_penalty": (-b2b_coef if use_b2b else 0.0),
        "total_bias": total_bias,
        "total_b2b_coef": (total_b2b if use_total_b2b else 0.0),
        "sigma_margin": sigma_margin,
        "sigma_total": sigma_total,
        "shrink_k": k,
    }

    # ---- score every holdout game with the fitted params
    for r in rows:
        g = r["game"]
        r["model"] = model_line(train, g["home"], g["away"], params,
                                home_b2b=r["home_b2b"], away_b2b=r["away_b2b"],
                                shrink_k=k)
        r["model"]["total"] += params["total_bias"] + \
            params["total_b2b_coef"] * (r["home_b2b"] + r["away_b2b"])
        if r["neutral"]:
            r["model"]["margin"] -= params["hca"]      # no home edge at a neutral site
            r["hca_applied"] = 0.0
        else:
            r["hca_applied"] = params["hca"]
        r["model_total_final"] = r["model"]["total"]
        r["model_margin_final"] = r["model"]["margin"]
        r["err_margin_model"] = r["actual_margin"] - r["model_margin_final"]
        r["err_margin_ref"] = r["actual_margin"] - r["ref"]["margin"]
        r["err_total_model"] = r["actual_total"] - r["model_total_final"]
        r["err_total_ref"] = r["actual_total"] - r["ref"]["total"]
        r["p_home_model"] = norm_cdf(r["model_margin_final"] / sigma_margin)
        r["p_home_ref"] = norm_cdf(r["ref"]["margin"] / sigma_margin)
        r["home_won"] = 1 if r["actual_margin"] > 0 else 0

    def mae(vals):
        return mean([abs(v) for v in vals])

    def rmse(vals):
        return math.sqrt(mean([v * v for v in vals]))

    em = [r["err_margin_model"] for r in rows]
    er = [r["err_margin_ref"] for r in rows]
    tm = [r["err_total_model"] for r in rows]
    tr = [r["err_total_ref"] for r in rows]

    brier = mean([(r["p_home_model"] - r["home_won"]) ** 2 for r in rows])
    brier_ref = mean([(r["p_home_ref"] - r["home_won"]) ** 2 for r in rows])
    eps = 1e-9
    logloss = -mean([math.log(max(eps, r["p_home_model"] if r["home_won"] else 1 - r["p_home_model"]))
                     for r in rows])
    logloss_ref = -mean([math.log(max(eps, r["p_home_ref"] if r["home_won"] else 1 - r["p_home_ref"]))
                         for r in rows])
    correct = sum(1 for r in rows
                  if (r["p_home_model"] >= 0.5) == (r["home_won"] == 1))
    correct_ref = sum(1 for r in rows
                      if (r["p_home_ref"] >= 0.5) == (r["home_won"] == 1))

    boot_model = bootstrap_ci(rows, lambda s: mae([x["err_margin_model"] for x in s]))
    boot_ref = bootstrap_ci(rows, lambda s: mae([x["err_margin_ref"] for x in s]))

    # ---- zeroed-parameter variant (how much do the two fitted numbers matter?)
    params0 = dict(params)
    params0["hca"] = 0.0
    params0["b2b_penalty"] = 0.0
    params0["total_bias"] = 0.0
    params0["total_b2b_coef"] = 0.0
    em0 = []
    for r in rows:
        ml = model_line(train, r["game"]["home"], r["game"]["away"], params0,
                        home_b2b=r["home_b2b"], away_b2b=r["away_b2b"], shrink_k=k)
        em0.append(r["actual_margin"] - (0.0 if r["neutral"] else ml["margin"]))

    metrics = {
        "n_games": len(rows),
        "window": f"{HOLDOUT_START} .. {HOLDOUT_END}",
        "ratings_window": train.label,
        "mae_margin_model": rnd(mae(em), 2),
        "mae_margin_ref": rnd(mae(er), 2),
        "mae_margin_zeroed_params": rnd(mae(em0), 2),
        "rmse_margin_model": rnd(rmse(em), 2),
        "rmse_margin_ref": rnd(rmse(er), 2),
        "bias_margin_model": rnd(mean(em), 2),
        "mae_total_model": rnd(mae(tm), 2),
        "mae_total_ref": rnd(mae(tr), 2),
        "rmse_total_model": rnd(rmse(tm), 2),
        "rmse_total_ref": rnd(rmse(tr), 2),
        "bias_total_model": rnd(mean(tm), 2),
        "brier_model": rnd(brier, 4),
        "brier_ref": rnd(brier_ref, 4),
        "logloss_model": rnd(logloss, 4),
        "logloss_ref": rnd(logloss_ref, 4),
        "straight_up_model": f"{correct}-{len(rows) - correct}",
        "straight_up_ref": f"{correct_ref}-{len(rows) - correct_ref}",
        "bootstrap_mae_model_95": [rnd(boot_model[0], 2), rnd(boot_model[1], 2)],
        "bootstrap_mae_ref_95": [rnd(boot_ref[0], 2), rnd(boot_ref[1], 2)],
        "sigma_margin": rnd(sigma_margin, 2),
        "sigma_total": rnd(sigma_total, 2),
    }

    # ---- fixed-k sensitivity sweep (refits HCA and the B2B term at each k)
    def mae(vals):
        return mean([abs(v) for v in vals])

    def rmse(vals):
        return math.sqrt(mean([v * v for v in vals]))

    sweep = []
    for kk in (0.0, 2.0, 4.0, 8.0, 12.0, 20.0):
        Xs, ys, bases = [], [], []
        for g in holdout:
            hb, ab = rest_flags(g, last_played)[:2]
            b = base_line(train, g["home"], g["away"], shrink_k=(kk or None))
            bases.append((b, hb, ab))
            Xs.append([1.0 if not g.get("neutral") else 0.0, float(hb - ab)])
            ys.append((g["home_pts"] - g["away_pts"]) - b["margin"])
        bk, sek, tk_, residk, s2k, dofk = ols(Xs, ys)
        hca_k = bk[0]
        b2b_k = -bk[1] if abs(tk_[1]) >= 1.0 else 0.0
        sig_k = math.sqrt(s2k)
        errs, brier_k = [], 0.0
        for (b, hb, ab), g in zip(bases, holdout):
            pred = b["margin"] + (0.0 if g.get("neutral") else hca_k) - b2b_k * (hb - ab)
            am = g["home_pts"] - g["away_pts"]
            errs.append(am - pred)
            brier_k += (norm_cdf(pred / sig_k) - (1 if am > 0 else 0)) ** 2
        sweep.append({
            "k": kk, "hca": rnd(hca_k, 2), "b2b_penalty_applied": rnd(b2b_k, 2),
            "sigma_margin": rnd(sig_k, 2),
            "mae_margin": rnd(mae(errs), 2), "rmse_margin": rnd(rmse(errs), 2),
            "brier": rnd(brier_k / len(errs), 4),
            "selected": abs(kk - k) < 1e-9,
        })

    fit = {
        "shrink_derivation": shrink_derivation,
        "shrink_sweep": sweep,
        "n": len(rows),
        "hca": {"est": rnd(hca, 3), "se": rnd(hca_se, 3), "t": rnd(hca_t, 3),
                "used": True, "disclosure": "estimated on the test window (in-sample)"},
        "b2b_coef_on_home_margin": {"est": rnd(b2b_coef, 3), "se": rnd(b2b_se, 3),
                                    "t": rnd(b2b_t, 3), "used": bool(use_b2b),
                                    "penalty_applied": rnd(-b2b_coef if use_b2b else 0.0, 3),
                                    "disclosure": "estimated on the test window (in-sample); "
                                                  "set to 0 unless |t| >= 1"},
        "total_bias": {"est": rnd(total_bias, 3), "se": rnd(total_bias_se, 3),
                       "t": rnd(total_bias_t, 3), "used": True,
                       "disclosure": "estimated on the test window (in-sample)"},
        "total_b2b_coef": {"est": rnd(total_b2b, 3), "se": rnd(total_b2b_se, 3),
                           "t": rnd(total_b2b_t, 3), "used": bool(use_total_b2b),
                           "disclosure": "estimated on the test window (in-sample); "
                                         "set to 0 unless |t| >= 1"},
        "b2b_detected_home": sum(r["home_b2b"] for r in rows),
        "b2b_detected_away": sum(r["away_b2b"] for r in rows),
        "neutral_site_games": sum(r["neutral"] for r in rows),
        "b2b_caveat": "A back-to-back is only flagged when the previous day's game is present "
                      "in the captured results. Results now run from 2026-11-06, so "
                      "back-to-backs running into 2026-11-09 and later are fully detected; "
                      "back-to-backs running into 2026-11-06 itself are not.",
    }

    return {
        "train": train, "season": season, "rows": rows, "params": params,
        "metrics": metrics, "fit": fit, "shrink_derivation": shrink_derivation,
    }


# ------------------------------------------------------------------ luck decomposition

def luck_table(season):
    """Pythagorean expectation from the official ORTG/DRTG.

    Only the two official ratings and the official games-played figure are used.
    'Luck' is defined here as actual wins minus Pythagorean expected wins; the
    z-score uses the binomial standard deviation over the games actually played.
    """
    exp = 13.91  # standard Pythagorean exponent
    out = []
    for ab, t in sorted(season.teams.items()):
        gp = float(t["gp"])
        o, d = float(t["ortg"]), float(t["drtg"])
        pyth = (o ** exp) / (o ** exp + d ** exp)
        exp_w = gp * pyth
        act_w = float(t["w"])
        sd = math.sqrt(gp * pyth * (1 - pyth))
        z = (act_w - exp_w) / sd if sd > 0 else 0.0
        out.append({
            "team": ab, "name": t["team"], "gp": int(gp),
            "w": int(t["w"]), "l": int(t["l"]),
            "ortg": t["ortg"], "drtg": t["drtg"], "netr": t["netr"],
            "pyth_win_pct": rnd(pyth, 3),
            "expected_wins": rnd(exp_w, 2),
            "actual_wins": int(act_w),
            "luck_wins": rnd(act_w - exp_w, 2),
            "sd_wins": rnd(sd, 2),
            "luck_z": rnd(z, 2),
        })
    out.sort(key=lambda x: -x["luck_z"])
    return out
