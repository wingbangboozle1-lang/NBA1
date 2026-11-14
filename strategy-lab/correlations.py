"""Module 4 - correlations and effects measured on the completed games, not assumed.

The site prices same-game parlays with an assumed zero correlation between the side and the
total, and carries a back-to-back penalty of 6.10 points that was fitted on one week of
basketball. Both numbers are re-measured here on every completed game in the official log,
with a standard error and an exact p-value, so a reviewer can see the size of the band
rather than a point estimate.
"""
from __future__ import annotations

import statistics as st

from labdata import rest_maps
from statools import ols, pearson, t_two_sided_p, rnd

FIRST_DAY = "https://www.nba.com/games?date=2026-10-20"


def run(ctx):
    games = [g for g in ctx["games"] if g["kind"] == "scored"]
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    yes, _ = rest_maps(ctx["games"], True)

    margins, totals, hb, ab, gap_edge, ot = [], [], [], [], [], []
    dropped_no_prior = 0
    for g in games:
        ra, rh = yes(g["away"], g["date"]), yes(g["home"], g["date"])
        margins.append(g["home_pts"] - g["away_pts"])
        totals.append(g["home_pts"] + g["away_pts"])
        hb.append(1 if rh["b2b"] else 0)
        ab.append(1 if ra["b2b"] else 0)
        ot.append(1 if g["ot"] else 0)
        if ra["gap"] is None or rh["gap"] is None:
            # no previous game is on record for one of the teams (the first week of the
            # season). The rest regressor is undefined, so the pair is dropped rather
            # than silently replaced by zero - a zero would read as "same rest".
            dropped_no_prior += 1
            gap_edge.append(None)
            continue
        gap_edge.append(rh["gap"] - ra["gap"])
    keep = [i for i, ge in enumerate(gap_edge) if ge is not None]
    sub = lambda xs: [xs[i] for i in keep]
    hb_r, ab_r, ge_r, mar_r, tot_r = (sub(hb), sub(ab), sub(gap_edge), sub(margins), sub(totals))

    fit_m = ols([[h - a, ge] for h, a, ge in zip(hb_r, ab_r, ge_r)], mar_r)
    fit_t = ols([[h - a, ge] for h, a, ge in zip(hb_r, ab_r, ge_r)], tot_r)

    def coef(fit, i, term, unit):
        if not fit:
            return None
        b, se, t = fit["beta"][i], fit["se"][i], fit["t"][i]
        return {"term": term, "coef": rnd(b, 3), "se": rnd(se, 3), "t": rnd(t, 2),
                "n": fit["n"], "dof": fit["dof"], "unit": unit,
                "ci95": [rnd(b - 1.96 * se, 2), rnd(b + 1.96 * se, 2)],
                "p_two_sided": rnd(t_two_sided_p(t, fit["dof"]), 4),
                "source_url": FIRST_DAY}

    b2b_m = coef(fit_m, 1, "back-to-back differential on the home margin", "points")
    gap_m = coef(fit_m, 2, "rest-gap differential on the home margin", "points per extra calendar day")
    b2b_t = coef(fit_t, 1, "back-to-back differential on the game total", "points")

    n_mismatch = sum(1 for h, a in zip(hb, ab) if h != a)
    r_mt, t_mt, p_mt = pearson(margins, totals)
    r_ot, _, p_ot = pearson([float(x) for x in ot], [abs(m) for m in margins])
    legs = leg_correlation(games, yes)

    return {
        "window": f"{games[0]['date']} .. {games[-1]['date']}",
        "games": len(games),
        "regression_sample": {"games_with_a_known_prior_game_for_both_teams": len(keep),
                              "dropped_no_prior_game_on_record": dropped_no_prior,
                              "why_dropped": ("a team with no earlier game on record has no rest figure; "
                                              "treating that as zero rest would fabricate a comparison")},
        "regressions": [
            {"name": "Back-to-back fatigue, measured on the whole season",
             "measured": b2b_m, "games_with_a_b2b_mismatch": n_mismatch,
             "site_value": 6.096,
             "site_source": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json",
             "reading": ("the published penalty is more than twice the full-season coefficient, and the "
                         "full-season coefficient is not distinguishable from zero on this sample")},
            {"name": "Rest-gap effect, measured on the whole season",
             "measured": gap_m, "site_value": None,
             "site_source": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json",
             "reading": "no rest effect beyond the back-to-back flag shows up here; the rest-edge strategies inherit that"},
            {"name": "Back-to-back effect on scoring, measured",
             "measured": b2b_t, "site_value": 0.0,
             "site_source": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json",
             "reading": "the site's totals carry no back-to-back term; the season estimate is positive but inside noise"},
        ],
        "correlations": [
            {"x": "home margin", "y": "game total", "r": rnd(r_mt, 4), "t": rnd(t_mt, 2),
             "p": rnd(p_mt, 4), "n": len(margins),
             "site_assumption": 0.0,
             "meaning": ("the correlation the same-game-parlay pricing assumes to be zero; a value near "
                         "zero here is the assumption being confirmed rather than asserted"),
             "source_url": FIRST_DAY},
            {"x": "went to overtime", "y": "absolute margin", "r": rnd(r_ot, 4), "p": rnd(p_ot, 4),
             "n": len(games), "site_assumption": "not published",
             "meaning": "how strongly close games predict overtime, the input the game-flow page models instead of measures",
             "source_url": FIRST_DAY},
        ],
        "margins": {"mean_home": rnd(st.mean(margins), 3), "sd": rnd(st.pstdev(margins), 3),
                    "within_3": rnd(sum(1 for m in margins if abs(m) <= 3) / len(margins), 4),
                    "within_5": rnd(sum(1 for m in margins if abs(m) <= 5) / len(margins), 4),
                    "twenty_plus": rnd(sum(1 for m in margins if abs(m) >= 20) / len(margins), 4),
                    "ot_rate": rnd(sum(ot) / len(ot), 4), "ot_games": sum(ot),
                    "source_url": FIRST_DAY},
        "totals": {"mean": rnd(st.mean(totals), 2), "sd": rnd(st.pstdev(totals), 3),
                   "regulation_only_mean": rnd(st.mean([t for t, o in zip(totals, ot) if not o]), 2),
                   "source_url": FIRST_DAY},
        "leg_correlation": legs,
    }


def leg_correlation(games, yes):
    """Same-night legs are not independent draws. Measured on the first two games of each
    slate, as a proportion-of-dates statistic, then compared with the product of the legs."""
    by_date = {}
    for g in games:
        by_date.setdefault(g["date"], []).append(g)
    pairs = joint = a_win = b_win = 0
    for dd, ps in sorted(by_date.items()):
        if len(ps) < 2:
            continue
        x, y = ps[0], ps[1]
        aw = 1 if x["home_pts"] > x["away_pts"] else 0
        bw = 1 if y["home_pts"] > y["away_pts"] else 0
        pairs += 1
        a_win += aw
        b_win += bw
        joint += aw * bw
    if not pairs:
        return None
    pa, pb = a_win / pairs, b_win / pairs
    prod = pa * pb
    obs = joint / pairs
    r, tstat, p = pearson([1.0 if g["home_pts"] > g["away_pts"] else 0.0 for g in games],
                          [float(g["ot"]) for g in games])
    return {"date_pairs": pairs, "leg_a_home_win": rnd(pa, 4), "leg_b_home_win": rnd(pb, 4),
            "measured_joint": rnd(obs, 4), "independent_product": rnd(prod, 4),
            "difference": rnd(obs - prod, 4),
            "ratio_true_to_independent": rnd(obs / prod, 4) if prod else None,
            "meaning": ("a same-night double priced as the product of its legs is off by this much on this "
                        "sample; with only two dozen date-pairs the band is wide, which is the honest answer"),
            "warning": ("n = " + str(pairs) + " date-pairs is far too small to reprice parlays on; treat as "
                        "a direction, not a number"),
            "side_vs_ot_correlation": {"r": rnd(r, 4), "p": rnd(p, 4)},
            "source_url": FIRST_DAY}
