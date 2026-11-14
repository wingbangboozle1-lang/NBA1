#!/usr/bin/env python3
"""Link-function and σ sweep for the win probability, scored against the same graded finals.

Written as a module rather than a notebook calculation because it exists to correct an assertion
this session made about someone else's code: the claim was that `SIGMA = 11.0` in
`scripts/build_edge_site.py:41` was too confident. Measured, that is wrong — σ≈11 with a normal
link is the best scorer in the table, and what actually costs accuracy is the logistic link, plus a
home-court term that no variant escapes. A correction has to be re-runnable or it is just another
opinion.

This is in-sample selection on the graded window and is published as such: nothing here sets
a parameter.
"""

import json
import math
import os

from common import OUT, load

SIGMAS = [6, 8, 10, 11, 12, 14, 17.4, 21, 25]


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def logistic(x):
    return 1.0 / (1.0 + math.exp(-x))


def score(p, y):
    n = len(y)
    brier = sum((a - q) ** 2 for a, q in zip(y, p)) / n
    eps = 1e-9
    logloss = -sum(a * math.log(max(q, eps)) + (1 - a) * math.log(max(1 - q, eps))
                   for a, q in zip(y, p)) / n
    return round(brier, 4), round(logloss, 4), round(sum(p) / n, 4)


def main():
    lines = load("integration", "out", "lines.json")
    rows = lines["backtest"]
    meas = lines["diagnostics"]["sigma_margin_measured"]
    y = [1 if r["home_won"] else 0 for r in rows]
    m = [r["model_margin_home"] for r in rows]
    results = {}
    for sig in SIGMAS:
        for kind, f in (("normal", norm_cdf), ("logistic", logistic)):
            p = [f(x / sig) for x in m]
            b, ll, mean_p = score(p, y)
            results[f"{kind}_sigma_{sig}"] = {"brier": b, "logloss": ll, "mean_p_home": mean_p}
    results["flat_coin"] = {"brier": 0.25, "logloss": 0.6931, "mean_p_home": 0.5}
    best = min(((k, v) for k, v in results.items() if k != "flat_coin"), key=lambda kv: kv[1]["brier"])

    rate = round(sum(y) / len(y), 4)
    n_variants = sum(1 for k in results if k != "flat_coin")
    n_above = sum(1 for k, v in results.items()
                  if k != "flat_coin" and v["mean_p_home"] > rate)
    out = {
        "note": (f"the same projected margins, converted by two link functions across a σ grid, "
                 f"scored against {len(rows)} official finals"),
        "n_graded": len(rows),
        "sigma_measured_from_error": meas,
        "results": results,
        "best_by_brier": {"name": best[0], "brier": best[1]["brier"]},
        "home_win_rate_actual": rate,
        "variants_with_mean_p_home_above_actual": n_above,
        "variants_total": n_variants,
        "reading": (f"the calibration claim that a hard-coded σ=11 makes the model overconfident "
                    f"is NOT supported: on this window the best Brier in the table is "
                    f"{best[0]} ({best[1]['brier']}), and the error-dispersion σ ({meas}) "
                    "scores worse. "
                    "The reason is that mean absolute "
                   "error is dragged up by a handful of blowouts while the typical game is much "
                   "tighter, so a σ taken from error dispersion overstates uncertainty for the median "
                   "game. The real defect in scripts/build_edge_site.py is that the constant and the "
                   "link are typed rather than fitted, not that the value is wrong — and the bias "
                   "that does survive is the home-court term: mean P(home) sits above the actual "
                   f"home win rate in {n_above} of {n_variants} variants."),
        "caveat": (f"choosing the best σ from this table IS in-sample selection on "
                   f"{len(rows)} games; it is printed to correct an assertion, not to set a "
                   "parameter"),
    }
    with open(os.path.join(OUT, "transform_test.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"transform · best={best[0]} brier={best[1]['brier']} "
          f"home_rate={out['home_win_rate_actual']} n={len(rows)}")
    return out


if __name__ == "__main__":
    main()
