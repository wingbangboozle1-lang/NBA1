"""Correlation study.

Two clearly separated tables are produced:

1. MEASURED - Pearson correlations computed on the official NBA.com
   Teams-Advanced table (n = 30 teams). Every number in this table is
   reproducible from source S1 and carries that link.

2. MODEL-DERIVED - the correlations that decide how a parlay or same-game
   parlay should be priced. These are not measured: measuring them needs
   play-by-play, which was not available. They are published with the flag
   MODEL-DERIVED and must not be quoted as official values (Flagged F6).
"""

from common import american_from_prob, bivariate_normal_cdf, norm_ppf, pearson, rnd
from strategies import SGP_RHO


MEASURED_PAIRS = [
    ("NetRtg", "Win pct", "Does the efficiency rating actually track the standings?"),
    ("OffRtg", "DefRtg", "Are good offenses and good defenses independent?"),
    ("OffRtg", "Pace", "Does playing faster raise offensive efficiency?"),
    ("DefRtg", "Pace", "Does playing faster hurt defensive efficiency?"),
    ("Pace", "Points per game", "How much of scoring volume is just pace?"),
    ("eFG%", "OffRtg", "How much of offensive efficiency is shot quality?"),
    ("TS%", "OffRtg", "Same, including free throws."),
    ("TOV%", "OffRtg", "Does turning it over actually depress efficiency?"),
    ("OREB%", "OffRtg", "Do offensive rebounds buy efficiency?"),
    ("DREB%", "DefRtg", "Does ending possessions with a rebound help defence?"),
    ("AST%", "OffRtg", "Does ball movement track efficiency?"),
    ("Pace", "NetRtg", "Is there a style edge, or is pace neutral?"),
    ("PIE", "Win pct", "Does the league's own all-in-one metric track winning?"),
]


def _series(season):
    t = season.teams
    s = {}
    for ab, row in t.items():
        gp = float(row["gp"])
        s.setdefault("NetRtg", {})[ab] = row["netr"]
        s.setdefault("OffRtg", {})[ab] = row["ortg"]
        s.setdefault("DefRtg", {})[ab] = row["drtg"]
        s.setdefault("Pace", {})[ab] = row["pace"]
        s.setdefault("eFG%", {})[ab] = row["efg_pct"]
        s.setdefault("TS%", {})[ab] = row["ts_pct"]
        s.setdefault("TOV%", {})[ab] = row["tov_pct"]
        s.setdefault("OREB%", {})[ab] = row["oreb_pct"]
        s.setdefault("DREB%", {})[ab] = row["dreb_pct"]
        s.setdefault("AST%", {})[ab] = row["ast_pct"]
        s.setdefault("PIE", {})[ab] = row["pie"]
        s.setdefault("Win pct", {})[ab] = row["w"] / gp
        s.setdefault("Points per game", {})[ab] = row["ortg"] * row["pace"] / 100.0
    return s


def measured_correlations(season):
    s = _series(season)
    out = []
    for a, b, why in MEASURED_PAIRS:
        xs, ys = [], []
        for ab in sorted(s[a].keys()):
            xs.append(s[a][ab])
            ys.append(s[b][ab])
        r, p, n = pearson(xs, ys)
        out.append({
            "x": a, "y": b, "r": rnd(r, 3), "p_value": rnd(p, 4), "n": n,
            "why": why,
            "r_squared": rnd(r * r, 3),
            "status": "MEASURED from official data",
        })
    return out


def model_derived_correlations():
    rows = [
        ("Side (team A covers)", "Game total", SGP_RHO["side_total"],
         "Under the additive model the two team scores share the same possession count but "
         "the margin is a difference and the total is a sum; with equal team-score variances "
         "their covariance is zero. This is a derived property of the model, not a measurement."),
        ("Player over (team A)", "Team A total", SGP_RHO["player_total_same_team"],
         "A player's production is part of his team's total, so the two must move together. "
         "The magnitude is a model estimate."),
        ("Player over (team A)", "Team A covers", SGP_RHO["player_side_same_team"],
         "Same mechanism, weaker because covering depends on the opponent too."),
        ("Player over (team A)", "Teammate over (team A)", SGP_RHO["two_teammates"],
         "Teammates compete for the same possessions and shots, so the sign should be negative. "
         "Magnitude is a model estimate."),
        ("Player over (team A)", "Opponent player over", SGP_RHO["two_opponents"],
         "Only linked through game pace and game script, so close to zero. Model estimate."),
    ]
    return [{
        "leg_1": a, "leg_2": b, "rho_model": rnd(r, 3),
        "derivation": d, "status": "MODEL-DERIVED - not measured (F6)",
    } for a, b, r, d in rows]


def parlay_pricing_grid():
    """What correlation does to a two-leg price, holding the leg probabilities fixed."""
    grid = []
    for p in (0.55, 0.60, 0.65):
        for rho in (-0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30):
            z = norm_ppf(p)
            p_true = bivariate_normal_cdf(z, z, rho)
            p_indep = p * p
            grid.append({
                "leg_prob": p, "rho": rnd(rho, 2),
                "true_joint_prob": rnd(p_true, 4),
                "independent_product": rnd(p_indep, 4),
                "difference": rnd(p_true - p_indep, 4),
                "fair_price_true": american_from_prob(p_true),
                "price_if_priced_independent": american_from_prob(p_indep),
                "bettor_edge_if_priced_independent_pct":
                    rnd(100.0 * (p_true / p_indep - 1.0), 2),
            })
    return grid
