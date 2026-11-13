"""Strategy library: signal definitions, bet construction and gate evaluation.

Each strategy is an explicit, reproducible rule. A strategy "plays" only when its
threshold is met, and every play is graded against an official final score.
Strategies whose inputs were not obtainable from an official source are marked
UNGRADED rather than being scored with substituted numbers.
"""

import itertools
import math

from common import (american_from_prob, binom_test_two_sided, bivariate_normal_cdf,
                    norm_cdf, norm_ppf, rnd, wilson_ci)
from model_core import ASSUMPTIONS

BREAKEVEN = 0.5238095238095238   # -110


# ------------------------------------------------------------- strategy registry

STRATEGIES = [
    {
        "id": "S1", "name": "Side edge vs reference", "family": "Single bet",
        "market": "Point spread",
        "rule": "Play the side when the originated margin differs from the reference "
                "spread by at least 3.0 points.",
        "threshold": "3.0 pts", "gradeable": True,
        "why": "The additive efficiency model collapses to a net-rating difference, so a "
               "side edge can only come from shrinkage, home court, rest and availability. "
               "A 3.0-point filter keeps only the plays where those refinements actually bite.",
    },
    {
        "id": "S2", "name": "Total edge vs reference", "family": "Single bet",
        "market": "Game total",
        "rule": "Play over/under when the originated total differs from the reference total "
                "by at least 6.0 points.",
        "threshold": "6.0 pts", "gradeable": True,
        "why": "The reference total is simply the two teams' published scoring averages added "
               "together, so it ignores defence entirely. The gap is the opponent-adjustment signal.",
    },
    {
        "id": "S3", "name": "Moneyline value", "family": "Single bet",
        "market": "Moneyline",
        "rule": "Play the moneyline when the originated win probability differs from the "
                "reference win probability by at least 6 percentage points and the "
                "originated price is shorter than +200.",
        "threshold": "6 pp", "gradeable": True,
        "why": "Moneylines punish favourites less than spreads do, so a large probability "
               "gap is the efficient way to monetise a side edge on a big favourite.",
    },
    {
        "id": "S4", "name": "Pace-driven total", "family": "Single bet",
        "market": "Game total",
        "rule": "Totals only, and only when the game's expected pace is at least 3.0 "
                "possessions per 48 minutes away from the league average AND the total edge "
                "is at least 4.0 points.",
        "threshold": "pace >= 3.0 and 4.0 pts", "gradeable": True,
        "why": "Pace is the most persistent team stat in the official advanced table. "
               "Restricting totals to genuine pace outliers removes the games where the "
               "total edge is just defensive noise.",
    },
    {
        "id": "S5", "name": "Back-to-back fade", "family": "Single bet",
        "market": "Point spread",
        "rule": "Exactly one team is on the second night of a back-to-back and the originated "
                "margin differs from the reference spread by at least 2.0 points.",
        "threshold": "2.0 pts", "gradeable": True,
        "why": "Rest is the one schedule effect that is fully observable from the official "
               "schedule and results. Both teams are held to the same threshold so the filter "
               "is not simply 'fade the tired team'.",
    },
    {
        "id": "S6", "name": "Availability shock", "family": "Single bet",
        "market": "Point spread / total",
        "rule": "At least 15% of one team's minutes are at risk in the official injury report "
                "and the originated number differs from the reference by at least 2.0 points.",
        "threshold": "15% minutes and 2.0 pts", "gradeable": False,
        "why": "Minutes at risk is measurable from the official injury report plus the official "
               "minutes table. UNGRADED: no historical injury-report editions were captured, so "
               "this strategy cannot be scored yet.",
        "ungraded_reason": "Requires archived official injury reports (Flagged F5).",
    },
    {
        "id": "S7", "name": "Player points prop", "family": "Player prop",
        "market": "Player points",
        "rule": "Play over/under a player's season scoring average when the originated "
                "projection differs from that average by at least 2.0 points.",
        "threshold": "2.0 pts", "gradeable": False,
        "why": "Season average is the reference prop line; possession, opponent-defence and "
               "teammate-availability multipliers are the signal. UNGRADED: no player game logs "
               "were captured, so projection accuracy is unmeasured.",
        "ungraded_reason": "Requires player game logs to measure game-to-game variance (Flagged F2/Q3).",
    },
    {
        "id": "S8", "name": "Points + rebounds + assists combo", "family": "Player prop",
        "market": "Player PRA",
        "rule": "Play over/under a player's season PRA average when the originated PRA "
                "projection differs by at least 3.0.",
        "threshold": "3.0 PRA", "gradeable": False,
        "why": "Combining three categories averages out single-category noise. UNGRADED for "
               "the same reason as S7.",
        "ungraded_reason": "Requires player game logs to measure game-to-game variance (Flagged F2/Q3).",
    },
    {
        "id": "S9", "name": "Two-leg cross-game parlay", "family": "Parlay",
        "market": "Parlay",
        "rule": "Take the two highest-edge S1/S2 legs of the day from DIFFERENT games, each "
                "with an edge at least 2.5, and parlay them.",
        "threshold": "2.5 per leg", "gradeable": True,
        "why": "Legs from different games are independent, so the parlay price is the product "
               "of the legs and the only edge is the model edge on each leg.",
    },
    {
        "id": "S10", "name": "Same-game parlay (side + total)", "family": "Parlay / SGP",
        "market": "Same-game parlay",
        "rule": "In the same game, parlay the side leg and the total leg when each has an "
                "edge of at least 2.5 and the modelled side/total correlation is at most 0.30.",
        "threshold": "2.5 per leg, rho <= 0.30", "gradeable": True,
        "why": "Same-game legs share possessions, so they are correlated. Pricing them as "
               "independent is the classic SGP error; the copula price is published next to "
               "the independent price so the difference is visible.",
    },
]

# Model-derived same-game correlations. These are NOT measured from official data
# (that would need play-by-play). Flagged F6.
SGP_RHO = {
    "side_total": 0.00,
    "player_total_same_team": 0.30,
    "player_side_same_team": 0.25,
    "two_teammates": -0.20,
    "two_opponents": 0.05,
}


# ------------------------------------------------------------------ play building

def _side_play(g, thr):
    edge = g["model_margin_final"] - g["ref"]["margin"]
    if abs(edge) < thr:
        return None
    side = "home" if edge > 0 else "away"
    p = norm_cdf((g["model_margin_final"] - g["ref"]["margin"]) / g["sigma_margin"])
    p = p if side == "home" else 1.0 - p
    team = g["home"] if side == "home" else g["away"]
    spread = -g["ref"]["margin"] if side == "home" else g["ref"]["margin"]
    return {
        "strategy": "S1", "market": "Point spread",
        "side": side, "ref_line": rnd(g["ref"]["margin"], 1),
        "model_value": rnd(g["model_margin_final"], 1),
        "edge": rnd(edge, 2), "p_model": rnd(p, 4),
        "team": team, "line_display": f"{team} {spread:+.1f}",
    }


def _total_play(g, thr):
    edge = g["model_total_final"] - g["ref"]["total"]
    if abs(edge) < thr:
        return None
    side = "over" if edge > 0 else "under"
    p = 1.0 - norm_cdf((g["ref"]["total"] - g["model_total_final"]) / g["sigma_total"])
    p = p if side == "over" else 1.0 - p
    return {
        "strategy": "S2", "market": "Game total",
        "side": side, "ref_line": rnd(g["ref"]["total"], 1),
        "model_value": rnd(g["model_total_final"], 1),
        "edge": rnd(edge, 2), "p_model": rnd(p, 4),
        "team": None, "line_display": f"{side.capitalize()} {g['ref']['total']:.1f}",
    }


def _ml_play(g, thr, max_price=200):
    gap = g["p_home_model"] - g["p_home_ref"]
    price = american_from_prob(g["p_home_model"] if gap > 0 else 1 - g["p_home_model"])
    if price is not None and price > max_price:
        return None
    if abs(gap) < thr:
        return None
    side = "home" if gap > 0 else "away"
    p = g["p_home_model"] if side == "home" else 1 - g["p_home_model"]
    team = g["home"] if side == "home" else g["away"]
    return {
        "strategy": "S3", "market": "Moneyline",
        "side": side, "ref_line": rnd(g["ref"]["margin"], 1),
        "model_value": rnd(g["model_margin_final"], 1),
        "edge_pp": rnd(gap * 100, 1), "p_model": rnd(p, 4),
        "fair_price": price,
        "team": team, "line_display": f"{team} ML ({price:+d} fair)",
    }


def build_legs(g):
    """Every candidate leg for one game, tagged with its strategy and edge."""
    legs = []
    sp = _side_play(g, 2.5)
    if sp:
        legs.append(dict(sp))
    tp = _total_play(g, 2.5)
    if tp:
        legs.append(dict(tp))
    return legs


def build_plays(games):
    """Generate every strategy's plays for a set of game contexts."""
    plays = []

    def add(g, p):
        if p is None:
            return
        row = {
            "date": g["date"], "game_id": g["game_id"], "matchup": g["matchup"],
            "away": g["away"], "home": g["home"], "time_et": g.get("time_et"),
            "strategy": p["strategy"], "market": p["market"], "side": p["side"],
            "ref_line": p["ref_line"], "model_value": p["model_value"],
            "edge": p.get("edge"), "edge_pp": p.get("edge_pp"),
            "p_model": p["p_model"], "fair_price": p.get("fair_price"),
            "team": p.get("team"), "line_display": p.get("line_display"),
            "n_legs": 1,
        }
        row["_g"] = g
        row["_legs"] = [p]
        plays.append(row)

    for g in games:
        # S1
        p = _side_play(g, 3.0)
        if p:
            add(g, dict(p, strategy="S1"))
        # S2
        p = _total_play(g, 6.0)
        if p:
            add(g, dict(p, strategy="S2"))
        # S3
        p = _ml_play(g, 0.06)
        if p:
            add(g, dict(p, strategy="S3"))
        # S4 - pace filtered total
        if abs(g["game_pace"] - g["L_pace"]) >= 3.0:
            p = _total_play(g, 4.0)
            if p:
                add(g, dict(p, strategy="S4"))
        # S5 - exactly one team on a back-to-back
        if (g["home_b2b"] + g["away_b2b"]) == 1:
            p = _side_play(g, 2.0)
            if p:
                add(g, dict(p, strategy="S5"))
        # S6 - availability shock (needs the official report)
        rep_home = g.get("inj_home") or {}
        rep_away = g.get("inj_away") or {}
        if (rep_home.get("weighted_lost_share") or 0) >= 0.15 or \
           (rep_away.get("weighted_lost_share") or 0) >= 0.15:
            p = _side_play(g, 2.0)
            if p:
                add(g, dict(p, strategy="S6"))
            p = _total_play(g, 2.0)
            if p:
                add(g, dict(p, strategy="S6"))
        # S7 / S8 - player props
        for pr in g.get("props", []):
            if pr.get("delta_pts") is not None and abs(pr["delta_pts"]) >= 2.0:
                plays.append(_prop_play(g, pr, "S7", "Player points", "pts",
                                        pr["baseline_pts"], pr["proj_pts"],
                                        pr["delta_pts"], 2.0))
            if pr.get("delta_pts_reb_ast") is not None and abs(pr["delta_pts_reb_ast"]) >= 3.0:
                plays.append(_prop_play(g, pr, "S8", "Player PRA", "pra",
                                        pr["baseline_pts_reb_ast"], pr["proj_pts_reb_ast"],
                                        pr["delta_pts_reb_ast"], 3.0))

    # S9 - cross-game parlays, best two legs of the day from different games
    by_date = {}
    for g in games:
        by_date.setdefault(g["date"], []).append(g)
    for date, gs in sorted(by_date.items()):
        cands = []
        for g in gs:
            for leg in build_legs(g):
                cands.append((abs(leg["edge"]), g, leg))
        cands.sort(key=lambda x: -x[0])
        chosen = []
        used_games = set()
        for _, g, leg in cands:
            if g["game_id"] in used_games:
                continue
            chosen.append((g, leg))
            used_games.add(g["game_id"])
            if len(chosen) == 2:
                break
        if len(chosen) == 2:
            plays.append(_parlay_play(chosen, "S9", 0.0))

    # S10 - same-game parlays
    for g in games:
        legs = build_legs(g)
        sides = [l for l in legs if l["market"] == "Point spread"]
        totals = [l for l in legs if l["market"] == "Game total"]
        if sides and totals:
            rho = SGP_RHO["side_total"]
            if abs(rho) <= 0.30:
                plays.append(_parlay_play([(g, sides[0]), (g, totals[0])], "S10", rho))
    return plays


def _prop_play(g, pr, sid, market, key, baseline, proj, delta, thr):
    return {
        "date": g["date"], "game_id": g["game_id"], "matchup": g["matchup"],
        "away": g["away"], "home": g["home"], "time_et": g.get("time_et"),
        "strategy": sid, "market": market,
        "side": ("over" if delta > 0 else "under"),
        "team": pr["player"],
        "line_display": f'{pr["player"]} {"Over" if delta > 0 else "Under"} {baseline}',
        "player": pr["player"], "player_team": pr["team"],
        "ref_line": baseline, "model_value": proj, "edge": rnd(delta, 2),
        "p_model": None, "fair_price": None, "n_legs": 1,
        "note": "No probability is published: game-to-game variance has not been "
                "measured from official player game logs (F2/Q3).",
    }


def _parlay_play(chosen, sid, rho):
    (g1, l1), (g2, l2) = chosen[0], chosen[1]
    p1, p2 = l1["p_model"], l2["p_model"]
    z1, z2 = norm_ppf(min(0.999999, max(1e-6, p1))), norm_ppf(min(0.999999, max(1e-6, p2)))
    p_true = bivariate_normal_cdf(z1, z2, rho)
    p_indep = p1 * p2
    disp = " + ".join(l.get("line_display", f"{l['side']} {l['ref_line']}") for _, l in chosen)
    return {
        "date": g1["date"], "game_id": g1["game_id"] + "+" + g2["game_id"],
        "matchup": g1["matchup"] + " & " + g2["matchup"],
        "away": g1["away"], "home": g1["home"], "time_et": g1.get("time_et"),
        "strategy": sid, "market": "Parlay" if sid == "S9" else "Same-game parlay",
        "side": disp, "line_display": disp, "team": None,
        "legs_detail": [{"market": l["market"], "side": l["side"],
                         "line": l.get("line_display"), "p": rnd(l["p_model"], 4)}
                        for l in (l1, l2)],
        "ref_line": None, "model_value": None,
        "edge": None, "p_model": rnd(p_true, 4),
        "p_if_independent": rnd(p_indep, 4),
        "correlation_adjustment": rnd(p_true - p_indep, 4),
        "rho": rnd(rho, 3),
        "fair_price": american_from_prob(p_true),
        "naive_price": american_from_prob(p_indep),
        "n_legs": 2,
        "_g": g1, "_legs": [l1, l2], "_leg_games": [g1, g2],
    }


# ----------------------------------------------------------------------- grading

def grade_play(play):
    """Grade one play against the official final score. Returns 'win'/'loss'/'push'."""
    g = play.get("_g")
    if g is None or g.get("actual_margin") is None:
        return "ungraded"
    am, at = g["actual_margin"], g["actual_total"]
    if play["strategy"] in ("S9", "S10"):
        results = []
        for leg, lg in zip(play["_legs"], play["_leg_games"]):
            results.append(_grade_single(leg, lg["actual_margin"], lg["actual_total"]))
        if "loss" in results:
            return "loss"
        if "push" in results:
            return "push"
        return "win"
    return _grade_single(play, am, at)


def _grade_single(leg, am, at):
    m = leg["market"]
    if m == "Point spread":
        diff = am - leg["ref_line"]
        if abs(diff) < 1e-9:
            return "push"
        won = diff > 0 if leg["side"] == "home" else diff < 0
        return "win" if won else "loss"
    if m == "Game total":
        diff = at - leg["ref_line"]
        if abs(diff) < 1e-9:
            return "push"
        won = diff > 0 if leg["side"] == "over" else diff < 0
        return "win" if won else "loss"
    if m == "Moneyline":
        if am == 0:
            return "push"
        won = am > 0 if leg["side"] == "home" else am < 0
        return "win" if won else "loss"
    return "ungraded"


def roi_units(play, result):
    """Profit in units at a -110 flat price (parlays priced off the naive product)."""
    if result == "ungraded":
        return 0.0
    if result == "push":
        return 0.0
    if result == "loss":
        return -1.0
    if play["strategy"] in ("S9", "S10"):
        p = play.get("p_if_independent") or (play.get("p_model") or 0.5)
        return (1.0 / p) - 1.0
    return 0.9090909090909091


# ----------------------------------------------------------------------- gates

GATES = [
    ("G1", "Sample size", "At least 30 graded plays (10-29 = provisional)"),
    ("G2", "Calibration", "Observed hit rate within 8 pp of the mean predicted probability"),
    ("G3", "Edge over break-even", "Mean modelled probability >= 52.38% (break-even at -110)"),
    ("G4", "Skill, not luck", "Wilson 95% lower bound on the hit rate above 52.38%"),
    ("G5", "Stability", "Bootstrap 95% CI of the model's margin MAE excludes the reference MAE"),
    ("G6", "Correlation limit", "Every parlay leg pair |rho| <= 0.30"),
    ("G7", "Availability robustness", "Play survives when every Questionable player is flipped to Out"),
]


def summarise(strategy, plays, metrics, params):
    graded = [p for p in plays if p.get("result") not in (None, "ungraded")]
    n = len(graded)
    wins = sum(1 for p in graded if p["result"] == "win")
    losses = sum(1 for p in graded if p["result"] == "loss")
    pushes = sum(1 for p in graded if p["result"] == "push")
    dec = wins + losses
    hit = wins / dec if dec else None
    lo, hi = wilson_ci(wins, dec) if dec else (0.0, 0.0)
    pval = binom_test_two_sided(wins, dec) if dec else 1.0
    units = sum(roi_units(p, p["result"]) for p in graded)
    probs = [p["p_model"] for p in graded if p.get("p_model") is not None]
    mean_p = sum(probs) / len(probs) if probs else None

    gates = []
    # G1
    if n >= 30:
        g1 = ("PASS", f"n = {n} graded plays")
    elif n >= 10:
        g1 = ("PROVISIONAL", f"n = {n} graded plays (needs 30)")
    else:
        g1 = ("FAIL", f"n = {n} graded plays (needs 30)")
    gates.append(("G1", "Sample size", g1[0], g1[1], "n >= 30"))
    # G2
    if mean_p is None or hit is None:
        gates.append(("G2", "Calibration", "N/A", "no probability published for this market",
                      "|observed - mean p| <= 0.08"))
    else:
        gap = abs(hit - mean_p)
        gates.append(("G2", "Calibration", "PASS" if gap <= 0.08 else "FAIL",
                      f"observed {hit:.3f} vs mean predicted {mean_p:.3f} (gap {gap:.3f})",
                      "|observed - mean p| <= 0.08"))
    # G3
    if mean_p is None:
        gates.append(("G3", "Edge over break-even", "N/A", "no probability published",
                      "mean p >= 0.5238"))
    else:
        gates.append(("G3", "Edge over break-even", "PASS" if mean_p >= BREAKEVEN else "FAIL",
                      f"mean modelled probability {mean_p:.3f}", "mean p >= 0.5238"))
    # G4
    if dec == 0:
        gates.append(("G4", "Skill, not luck", "FAIL", "no decided plays", "Wilson LB > 0.5238"))
    else:
        gates.append(("G4", "Skill, not luck", "PASS" if lo > BREAKEVEN else "FAIL",
                      f"Wilson 95% CI [{lo:.3f}, {hi:.3f}], exact binomial p = {pval:.3f}",
                      "Wilson LB > 0.5238"))
    # G5 - model-level, identical for every strategy
    bl, bh = metrics["bootstrap_mae_model_95"]
    ref_mae = metrics["mae_margin_ref"]
    ok = bh < ref_mae
    gates.append(("G5", "Stability", "PASS" if ok else "FAIL",
                  f"model MAE 95% CI [{bl}, {bh}] vs reference MAE {ref_mae}",
                  "bootstrap CI of model MAE entirely below the reference MAE"))
    # G6
    if strategy["family"] in ("Parlay", "Parlay / SGP"):
        rhos = [abs(p.get("rho") or 0.0) for p in graded]
        worst = max(rhos) if rhos else 0.0
        gates.append(("G6", "Correlation limit", "PASS" if worst <= 0.30 else "FAIL",
                      f"max |rho| across legs = {worst:.2f} (model-derived, not measured)",
                      "|rho| <= 0.30"))
    else:
        gates.append(("G6", "Correlation limit", "N/A",
                      "single-leg market - applies to parlays only", "|rho| <= 0.30"))
    # G7
    gates.append(("G7", "Availability robustness", "NOT RUN",
                  "requires the official injury report for the graded window; none was "
                  "captured for 2026-11-09..2026-11-12", "|line move| < 1.0 and same side"))

    return {
        "id": strategy["id"], "name": strategy["name"], "family": strategy["family"],
        "market": strategy["market"], "rule": strategy["rule"],
        "threshold": strategy["threshold"], "why": strategy["why"],
        "gradeable": strategy["gradeable"],
        "ungraded_reason": strategy.get("ungraded_reason"),
        "n_plays": len(plays), "n_graded": n,
        "wins": wins, "losses": losses, "pushes": pushes,
        "hit_rate": rnd(hit, 4) if hit is not None else None,
        "wilson_95": [rnd(lo, 4), rnd(hi, 4)] if dec else None,
        "binomial_p": rnd(pval, 4) if dec else None,
        "units_at_minus110": rnd(units, 3),
        "roi_pct": rnd(100.0 * units / dec, 2) if dec else None,
        "mean_p_model": rnd(mean_p, 4) if mean_p is not None else None,
        "gates": [{"id": a, "name": b, "status": c, "detail": d, "threshold": e}
                  for a, b, c, d, e in gates],
    }
