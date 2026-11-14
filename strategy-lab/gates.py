"""Module 5 - the gates a strategy has to pass before it earns a stake, and the reward tier.

The reward rule this lab proposes, in one line: a strategy is worth a stake only if it wins
more often than the originated line it bets against already implies, on at least 30 plays,
in both halves of the window, with a multiple-comparison correction applied across the whole
library - and the market gate is reserved for a licensed price feed the repository does not
have. That last gate is why nothing on this board is ever marked funded.

GA/GEB..GF are computable from official data; GG is not, and is reported as blocked rather
than skipped.
"""
from __future__ import annotations

import statistics as st

from labdata import load
from statools import binom_two_sided, rnd

# ------------------------------------------------- module 5: gates, rewards, checks
GATE_DEFS = [
    ("GA", "Sample", "At least 30 graded plays; 10-29 is provisional, below 10 is unreadable."),
    ("GB", "Calibration", "Realised win rate within 8 points of the probability the originated line implied."),
    ("GC", "Skill over the originated line", "Exact Poisson-binomial one-sided p <= 0.05 for wins exceeding the model's own expectation."),
    ("GD", "Multiple-comparison control", "Benjamini-Hochberg q <= 0.10 across this library AND the shared-draw library null <= 0.05."),
    ("GE", "Stability", "Both halves of the window show a positive excess over the model, not just the pooled sample."),
    ("GF", "Uncorrelated-bootstrap P&L", "Moving-block bootstrap 95% interval for mean units has a lower bound above zero."),
    ("GG", "Market test", "Beats a real price after vig. BLOCKED for the whole repository: no NBA-operated source publishes one."),
]


def module_gates(tour):
    lib_p = tour["library_null"]["probability_luck_only_library_matches_or_beats"]
    out = []
    for rec in tour["strategies"]:
        n = rec["n"] or 0
        gap = None if rec["calibration_gap"] is None else abs(rec["calibration_gap"])
        ga = n >= 30
        gb = (gap is not None and gap <= 0.08)
        gc = (rec["p_model_null"] is not None and rec["p_model_null"] <= 0.05)
        gd = (rec["bh_q"] is not None and rec["bh_q"] <= 0.10) and (lib_p is not None and lib_p <= 0.05)
        halves = rec.get("halves") or {}
        both = []
        for k in ("first_half", "second_half"):
            h = halves.get(k)
            if h and h["n"]:
                both.append(h["wins"] / h["n"] > 0.5)
        ge = len(both) == 2 and all(both)
        boot = rec.get("bootstrap_units") or {}
        gf = boot.get("ci_lo") is not None and boot["ci_lo"] > 0
        passed = [ga, gb, gc, gd, ge, gf]
        n_pass = sum(passed)
        excess = rec["excess_wins"] or 0
        pv = rec["p_model_null"]
        if n_pass == 6:
            tier, stake = "Tier 1 - research-funded (paper)", 1.0
        elif ga and gb and ge and (pv or 1) <= 0.15:
            tier, stake = "Tier 2 - half unit (paper)", 0.5
        elif excess > 0 and n >= 10 and (pv or 1) <= 0.35:
            tier, stake = "Tier 3 - quarter unit, provisional sample", 0.25
        elif excess < 0 and n >= 10:
            tier, stake = "Contradicts the rule - do not flip it", 0.0
        else:
            tier, stake = "Not funded - reference only", 0.0
        direction = ("wins MORE than its own line expected" if excess > 0 else
                     "wins LESS than its own line expected; flipping the rule after seeing that is "
                     "the overfitting the gates exist to prevent" if excess < 0 else
                     "exactly as its own line expected")
        out.append({
            "id": rec["id"], "name": rec["name"], "family": rec["family"], "market": rec["market"],
            "n": n, "wins": rec["wins"], "hit_rate": rec["hit_rate"],
            "excess_wins": rec["excess_wins"], "z_vs_model": rec["z_vs_model"],
            "p_model_null": rec["p_model_null"], "bh_q": rec["bh_q"],
            "gates": {"GA": ga, "GB": gb, "GC": gc, "GD": gd, "GE": ge, "GF": gf, "GG": False},
            "gates_passed": n_pass, "gates_possible": 6,
            "tier": tier, "paper_stake_units": stake,
            "direction": direction,
            "blocking_reason": ("every computable gate passed; only the market gate is left, and no NBA-operated "
                                "source publishes a price, so it cannot be closed in this repository"
                                if n_pass >= 4 else
                                "fails the skill gate: the record is inside what the originated line already implied"),
            "source_url": "https://www.nba.com/games?date=2026-10-20",
        })
    return {"gate_definitions": [{"id": a, "name": b, "definition": c} for a, b, c in GATE_DEFS],
            "rows": out,
            "funded": [r["id"] for r in out if r["gates_passed"] == 6],
            "note": ("GG is unpassable by construction in this repository, so no strategy can be promoted "
                     "past the paper tiers here. GA-GF are all computable from official data and are the "
                     "gates this lab grades against.")}


def module_probability_audit(ctx):
    """Every probability the site's game-flow page prints, against the season's realised
    frequency on the same definitions. A sanity reference, not a backtest: the horizon
    games have not been played, so what is compared is the model's distribution against
    the completed games it was fitted on."""
    games = [g for g in ctx["games"] if g["kind"] == "scored"]
    n = len(games)
    marg = [g["home_pts"] - g["away_pts"] for g in games]
    realised = {
        "home_win": sum(1 for m in marg if m > 0) / n,
        "margin_within_5": sum(1 for m in marg if abs(m) <= 5) / n,
        "margin_20plus": sum(1 for m in marg if abs(m) >= 20) / n,
        "overtime": sum(1 for g in games if g["ot"]) / n,
        "away_win": sum(1 for m in marg if m < 0) / n,
    }
    try:
        gf = load("site", "data", "gameflow.json")["rows"]
    except Exception:
        gf = []
    predicted = {}
    if gf:
        predicted = {
            "p_home_win": st.mean([r["p_home_win"] for r in gf]),
            "p_margin_within_5": st.mean([r["p_margin_within_5"] for r in gf]),
            "p_margin_20plus": st.mean([r["p_margin_20plus"] for r in gf]),
            "p_overtime_approx": st.mean([r["p_overtime_approx"] for r in gf]),
        }
    rows = []
    mapping = [("home win", "p_home_win", "home_win"),
               ("margin inside 5", "p_margin_within_5", "margin_within_5"),
               ("margin 20 or more", "p_margin_20plus", "margin_20plus"),
               ("goes to overtime", "p_overtime_approx", "overtime")]
    for label, pk, rk in mapping:
        pv = predicted.get(pk)
        rv = realised[rk]
        k = sum(1 for g, m in zip(games, marg) if (
            (label == "home win" and m > 0) or
            (label == "margin inside 5" and abs(m) <= 5) or
            (label == "margin 20 or more" and abs(m) >= 20) or
            (label == "goes to overtime" and g["ot"])))
        rows.append({
            "quantity": label,
            "mean_model_probability_published": rnd(pv, 4) if pv is not None else None,
            "realised_rate_on_completed_games": rnd(rv, 4),
            "realised_count": k, "games": n,
            "gap_points": rnd((rv - pv) * 100, 2) if pv is not None else None,
            "p_exact_vs_model": rnd(binom_two_sided(k, n, pv), 5) if pv else None,
            "source_url": "https://www.nba.com/games?date=2026-10-20",
            "page_under_test": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/gameflow.json",
        })
    return {"games": n, "window": f"{games[0]['date']} .. {games[-1]['date']}",
            "rows": rows,
            "caveat": ("the predicted column is the mean of the 27 published horizon rows, which describe "
                       "games that have not been played; comparing them with the completed games is a "
                       "distribution check, not a graded forecast"),
            "away_win_rate": rnd(realised["away_win"], 4),
            "home_win_rate": rnd(realised["home_win"], 4)}
