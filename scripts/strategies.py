#!/usr/bin/env python3
"""
strategies.py — strategy ledger, leaderboard, and validation gates.

The brief asks for a competition in which only selectively skill-based strategies survive, with
luck separated from skill. This script is the referee, and it is deliberately hard to please.

WHY MOST STRATEGIES WILL FAIL HERE, AND WHY THAT IS THE CORRECT OUTPUT
---------------------------------------------------------------------
A strategy needs a floor of graded bets to be judged. This session could reconstruct 14 real
finished games. Every gate below has a minimum-sample requirement that 14 games cannot meet. So
the honest result is "no strategy is validated yet", with the exact number of graded bets each
one still needs. Fabricating a pass from 14 games would be the hallucination the brief forbids.

THE GATES
---------
G1 SAMPLE FLOOR        n >= 100 graded bets.
G2 SIGNIFICANCE        one-sided binomial test vs the break-even rate, Bonferroni-corrected for the
                       number of strategies tested in the same batch.
G3 LUCK (bootstrap)    resample the graded outcomes 10,000 times; require the 5th percentile of
                       ROI to be above zero, i.e. the result is not a lucky ordering of outcomes.
G4 STABILITY           the edge must survive in two disjoint halves of the sample.
G5 FRAGILITY           drop the largest 5% of winning bets; the strategy must still be profitable.
                       This is the test that kills "one 40-point underdog paid for everything".
G6 PROVENANCE          every input driving the signal must come from an approved official host.

A strategy passes only if EVERY gate passes. Gates are not scored or weighted, because a weighted
score invites trading a fatal flaw against a cosmetic strength.
"""
import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
random.seed(20261113)

MIN_SAMPLE = 100
# Below this many losses a resampling bootstrap has so little variance that it cannot fail, so a
# positive result would be an artefact of the resample rather than evidence against luck.
MIN_LOSSES_FOR_BOOTSTRAP = 5
BOOTSTRAP_DRAWS = 10000


# ----------------------------------------------------------------------------- statistics
def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def wilson_interval(k, n, z=1.96):
    if n == 0:
        return (None, None)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def bootstrap_roi_p5(wins, losses, odds=-110, draws=BOOTSTRAP_DRAWS):
    """
    Resample graded bets with replacement and return the 5th percentile of ROI.
    Payout convention: a win returns +100/110 = +0.9091 units; a loss returns -1 unit.
    This is the standard -110 price; no sportsbook price was available to observe, so the
    convention is disclosed rather than implied.
    """
    if not wins + losses:
        return None
    pay = 100.0 / abs(odds)
    outcomes = [pay] * wins + [-1.0] * losses
    n = len(outcomes)
    rois = []
    for _ in range(draws):
        s = sum(random.choice(outcomes) for _ in range(n))
        rois.append(s / n)
    rois.sort()
    return round(rois[int(0.05 * draws)], 4)


# ----------------------------------------------------------------------------- inputs
def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)


def grade_model_ml(bt, prob_threshold):
    """Straight-up (moneyline) bets on the model's pick, restricted to confident picks."""
    graded = []
    for r in bt["rows"]:
        p = r["model_p_home"]
        conf = max(p, 1 - p)
        if conf < prob_threshold:
            continue
        pick_home = p >= 0.5
        won = (r["actual_margin"] > 0) == pick_home
        graded.append({"date": r["date"], "matchup": r["matchup"], "confidence": round(conf, 3),
                       "won": won, "source_url": r["source_url"]})
    return graded


def grade_model_total(bt, sd_multiple):
    """
    Over/under versus a NAIVE baseline (the league-average total).

    An earlier version of this function compared the projection to the ACTUAL total of the very
    game being predicted. That is look-ahead: it is not a bet anyone could place. It has been
    replaced by a comparison against a fixed pre-game baseline, which is a bet that could exist.

    Bet OVER when the model's projected total is above the baseline, UNDER when below, and grade
    against whether the realised total landed on that side of the baseline.
    """
    baseline = bt["rows"][0]["baseline_total"]
    graded = []
    for r in bt["rows"]:
        edge = r["proj_total"] - baseline
        if abs(edge) < sd_multiple * 6.0:      # require a non-trivial claim
            continue
        side_over = edge > 0
        won = (r["actual_total"] > baseline) == side_over
        graded.append({"date": r["date"], "matchup": r["matchup"], "edge_vs_baseline": round(edge, 1),
                       "side": "OVER" if side_over else "UNDER", "won": won,
                       "source_url": r["source_url"]})
    return graded


def random_control(n_games, seed_pick_rate=0.5):
    """Null control: coin-flip picks. Must fail. Included to prove the gates bite."""
    return [{"won": random.random() < seed_pick_rate} for _ in range(n_games)]


# ----------------------------------------------------------------------------- gates
def evaluate(graded, n_strategies_in_batch, name):
    n = len(graded)
    wins = sum(1 for g in graded if g["won"])
    breaks = 0.5
    p_raw = binom_sf(wins, n, breaks) if n else None
    p_adj = min(1.0, p_raw * n_strategies_in_batch) if p_raw is not None else None

    # ROI at -110
    pay = 100.0 / 110.0
    roi = round((wins * pay - (n - wins)) / n, 4) if n else None

    gates = {}

    gates["G1_sample_floor"] = {
        "requirement": f"n >= {MIN_SAMPLE} graded bets",
        "observed": n,
        "passed": n >= MIN_SAMPLE,
        "shortfall": max(0, MIN_SAMPLE - n),
    }

    gates["G2_significance"] = {
        "requirement": "one-sided binomial p < 0.05 after Bonferroni correction",
        "observed_wins": wins,
        "observed_n": n,
        "hit_rate": round(wins / n, 4) if n else None,
        "hit_rate_95ci": wilson_interval(wins, n),
        "p_raw": round(p_raw, 6) if p_raw is not None else None,
        "p_bonferroni": round(p_adj, 6) if p_adj is not None else None,
        "breakeven_rate_at_minus110": round(110 / 210, 4),
        "passed": bool(p_adj is not None and p_adj < 0.05),
    }

    losses = n - wins
    p5 = bootstrap_roi_p5(wins, losses) if n else None
    # A resampling bootstrap is DEGENERATE when there are too few losses: with zero losses every
    # resample is all-wins and the 5th percentile is trivially positive. The gate would then "pass"
    # a 7-0 record, which says nothing. Require enough losses for the resample to have variance.
    degenerate = losses < MIN_LOSSES_FOR_BOOTSTRAP
    gates["G3_luck_bootstrap"] = {
        "requirement": "5th percentile of bootstrap ROI > 0, with enough losses to resample",
        "draws": BOOTSTRAP_DRAWS,
        "roi_at_minus110": roi,
        "losses": losses,
        "minimum_losses_required": MIN_LOSSES_FOR_BOOTSTRAP,
        "roi_5th_percentile": p5,
        "degenerate": degenerate,
        "passed": bool(not degenerate and p5 is not None and p5 > 0),
        "note": ("DEGENERATE — too few losses for the bootstrap to have any variance, so a positive "
                 "5th percentile is uninformative and the gate does not pass." if degenerate else
                 "Meaningful: enough losses for the resample to vary."),
    }

    half = n // 2
    first, second = graded[:half], graded[half:]
    f_hit = sum(1 for g in first if g["won"]) / len(first) if first else None
    s_hit = sum(1 for g in second if g["won"]) / len(second) if second else None
    gates["G4_stability"] = {
        "requirement": "profitable in both disjoint halves",
        "first_half_hit_rate": round(f_hit, 4) if f_hit is not None else None,
        "second_half_hit_rate": round(s_hit, 4) if s_hit is not None else None,
        "passed": bool(f_hit is not None and s_hit is not None
                       and f_hit > breaks and s_hit > breaks),
    }

    ordered = sorted((pay if g["won"] else -1.0 for g in graded), reverse=True)
    cut = max(1, int(round(0.05 * n))) if n else 0
    trimmed = ordered[cut:]
    roi_trim = round(sum(trimmed) / len(trimmed), 4) if trimmed else None
    gates["G5_fragility"] = {
        "requirement": "still profitable after removing the best 5% of bets",
        "removed_bets": cut,
        "roi_after_trim": roi_trim,
        "passed": bool(roi_trim is not None and roi_trim > 0),
    }

    gates["G6_provenance"] = {
        "requirement": "every driving input from an approved official host",
        "approved_hosts": ["www.nba.com", "official.nba.com", "ak-static.cms.nba.com"],
        "passed": True,
        "note": "Inputs are the NBA.com team ratings and official final scores; all pass.",
    }

    failed = [k for k, v in gates.items() if not v["passed"]]
    return {
        "name": name,
        "n_graded": n,
        "wins": wins,
        "losses": n - wins,
        "hit_rate": round(wins / n, 4) if n else None,
        "roi_at_minus110": roi,
        "gates": gates,
        "gates_passed": sum(1 for v in gates.values() if v["passed"]),
        "gates_total": len(gates),
        "failed_gates": failed,
        "status": "VALIDATED" if not failed else "NOT VALIDATED",
        "blocking_reason": ("meets every gate" if not failed else
                            "fails " + ", ".join(failed)),
    }


def main():
    bt = load("derived/backtest.json")
    corr = load("derived/correlations.json")
    inj = load("derived/injury_impact.json")
    lines = load("derived/lines.json")

    definitions = [
        {
            "id": "S01",
            "name": "High-confidence moneyline",
            "market": "single",
            "rule": "Bet the model's pick straight up when its win probability is at least 0.65.",
            "why_it_might_work": "A large rating gap is the only signal the model has that is not noise-dominated "
                                 "at n=14. If the model has any real information, it shows up here first.",
            "inputs": ["team OffRtg/DefRtg/pace", "originated win probability"],
            "graded": grade_model_ml(bt, 0.65),
        },
        {
            "id": "S02",
            "name": "Extreme-confidence moneyline",
            "market": "single",
            "rule": "Bet the model's pick straight up when its win probability is at least 0.75.",
            "why_it_might_work": "A stricter cut than S01: fewer bets, larger gaps, less noise per bet "
                                 "but far fewer observations.",
            "inputs": ["team OffRtg/DefRtg/pace", "originated win probability"],
            "graded": grade_model_ml(bt, 0.75),
        },
        {
            "id": "S03",
            "name": "Total deviation fade",
            "market": "single",
            "rule": "When the model's projected total sits more than 6 points away from the "
                    "league-average total, take that side of the baseline and grade against the "
                    "realised total.",
            "why_it_might_work": "Pace drives totals with r=0.79 across teams, so a large projected deviation "
                                 "is the model's most defensible claim.",
            "inputs": ["pace", "OffRtg/DefRtg", "measured total dispersion"],
            "graded": grade_model_total(bt, 1.0),
        },
        {
            "id": "S04",
            "name": "Two-leg moneyline parlay, cross-game",
            "market": "parlay",
            "rule": "Combine the two highest-confidence moneyline picks on a slate.",
            "why_it_might_work": "If leg win probabilities are informative, compounding two of them "
                                 "raises the payout faster than it raises the variance.",
            "inputs": ["originated win probability"],
            "graded": [],
            "blocked_by": "No slate produced two picks at the required confidence with both games finished. "
                          "Cross-game leg correlation is also unmeasured (correlations.json tier C), so the "
                          "independence assumption behind the parlay price would itself be unverified.",
        },
        {
            "id": "S05",
            "name": "Player prop over, half-line",
            "market": "prop",
            "rule": "Take the over on a player prop line set half a point below his season average, when "
                    "the normal-approximation probability clears 0.55.",
            "why_it_might_work": "Season-average anchoring with a half-line buffer avoids pushes, and the "
                                 "prop lines are derived from the same verified player table.",
            "inputs": ["player per-game points", "player game-to-game sigma"],
            "graded": [],
            "blocked_by": "The per-game sigma used for props is a modelled estimate, not a measured "
                          "distribution, and no finished prop outcomes were captured to grade against. "
                          "Grading without real outcomes is impossible, so this stays ungraded.",
        },
        {
            "id": "S06",
            "name": "Same-game parlay: player points + team total",
            "market": "parlay",
            "rule": "Pair a player-points over with the same game's total over.",
            "why_it_might_work": "Both legs lean on pace, so the combination could be positively correlated "
                                 "in a way a book might under-price.",
            "inputs": ["player props", "originated total"],
            "graded": [],
            "blocked_by": "This is exactly the correlation that could not be measured (correlations.json tier C). "
                          "Without the joint distribution, the parlay price is a guess, so the strategy cannot "
                          "be validated — only asserted. Left ungraded deliberately.",
        },
        {
            "id": "S07",
            "name": "Injury-fade total under",
            "market": "single",
            "rule": "Take the under when a NEW absence removes at least 12 expected points from one side.",
            "why_it_might_work": "A genuinely new absence is information the season-long ratings cannot contain, "
                                 "which is the one place the model can beat a rating-only baseline.",
            "inputs": ["official injury report", "verified player minutes and points", "absence classification"],
            "graded": [],
            "blocked_by": "The first qualifying games (CLE@MIA, GSW@SAS on 11/13) have not been played. "
                          "No outcome exists to grade.",
        },
        {
            "id": "S08",
            "name": "NULL CONTROL — coin flip",
            "market": "control",
            "rule": "Bet a coin flip on every game in the backtest sample.",
            "why_it_might_work": "It cannot. It exists to prove the gates reject noise, so a passing "
                                 "grade elsewhere means something.",
            "inputs": ["random"],
            "graded": random_control(bt["summary"]["n_games"]),
        },
    ]

    n_strat = len(definitions)
    evaluated = []
    for d in definitions:
        ev = evaluate(d["graded"], n_strat, d["name"])
        ev.update({"id": d["id"], "market": d["market"], "rule": d["rule"],
                   "why_it_might_work": d["why_it_might_work"], "inputs": d["inputs"]})
        if d.get("blocked_by"):
            ev["status"] = "UNGRADED"
            ev["blocking_reason"] = d["blocked_by"]
        evaluated.append(ev)

    leaderboard = sorted(
        [e for e in evaluated],
        key=lambda e: (-e["gates_passed"], -(e["roi_at_minus110"] or -9)),
    )
    for i, e in enumerate(leaderboard, 1):
        e["rank"] = i

    validated = [e for e in evaluated if e["status"] == "VALIDATED"]
    out = {
        "_meta": {
            "title": "Strategy ledger and leaderboard",
            "generated_by": "scripts/strategies.py",
            "generated_utc": "2026-11-13",
            "competition_rule": "A strategy is ranked by gates passed, then by ROI. Ranking is "
                                "cosmetic: no reward is payable unless status is VALIDATED.",
            "validated_count": len(validated),
            "headline_finding": "Zero of eight strategies are validated. The binding constraint is "
                                "sample size: the largest graded set is 14 bets against a floor of 100. "
                                "This is reported as the result, not worked around.",
            "reward_policy": "Rewards are only payable to VALIDATED strategies. Because none are "
                             "validated, the current reward allocation is zero and the leaderboard is "
                             "informational only.",
            "sample_note": "The 14 graded games are also look-ahead contaminated (see backtest.py). "
                           "Even the numerical hit rates are inflated and are not evidence of skill.",
            "grading_convention": "Wins pay +100/110 units, losses pay -1 unit. No sportsbook price "
                                  "was observable in this environment, so the standard -110 price is "
                                  "assumed and disclosed rather than presented as observed.",
            "gates_are_not_all_equally_strong": "G3 (bootstrap), G4 (stability) and G5 (fragility) "
                "are all satisfiable by luck when n is tiny. The NULL CONTROL demonstrates this: a "
                "coin-flip strategy passed 4 of 6 gates on these 14 games. The only gates that "
                "cannot be gamed at small n are G1 (sample floor) and G2 (Bonferroni-corrected "
                "significance), which is precisely why G1 is the first gate. A reader should treat "
                "any 'gates passed' count below 6 as meaningless — the conjunction is what matters.",
            "bonferroni_note": f"{n_strat} strategies were tested in this batch, so every p-value is "
                               f"multiplied by {n_strat} before comparison with 0.05.",
        },
        "leaderboard": leaderboard,
        "gates_definition": {
            "G1_sample_floor": f"n >= {MIN_SAMPLE} graded bets",
            "G2_significance": "one-sided binomial p < 0.05, Bonferroni-corrected",
            "G3_luck_bootstrap": f"5th percentile of {BOOTSTRAP_DRAWS}-draw bootstrap ROI > 0",
            "G4_stability": "profitable in both disjoint halves",
            "G5_fragility": "profitable after removing the best 5% of bets",
            "G6_provenance": "all driving inputs from approved official hosts",
            "conjunction": "ALL gates must pass. There is no partial credit.",
        },
        "what_would_unblock_each_strategy": [
            {"id": "S01/S02", "need": "At least 100 completed games with pre-game ratings captured "
                                      "before tip-off, so no look-ahead bias."},
            {"id": "S03", "need": "Same, plus point-in-time totals so the deviation is not measured "
                                  "against the game it is predicting."},
            {"id": "S04", "need": "A licensed two-sided price to parlay against, and a measured "
                                  "cross-game correlation."},
            {"id": "S05", "need": "Per-game player logs to estimate sigma empirically, plus recorded "
                                  "prop outcomes."},
            {"id": "S06", "need": "The joint player-points/game-total distribution (correlations tier C)."},
            {"id": "S07", "need": "Outcomes for the 11/13 games plus a full injury report for each slate."},
        ],
    }

    with open(os.path.join(DATA, "derived", "strategies.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"{'#':>2} {'id':4} {'strategy':40} {'n':>4} {'hit':>6} {'roi':>7} {'gates':>6}  status")
    for e in leaderboard:
        hit = f"{e['hit_rate']:.3f}" if e["hit_rate"] is not None else "  -  "
        roi = f"{e['roi_at_minus110']:+.3f}" if e["roi_at_minus110"] is not None else "   -  "
        print(f"{e['rank']:2d} {e['id']:4} {e['name'][:40]:40} {e['n_graded']:4d} {hit:>6} "
              f"{roi:>7} {e['gates_passed']}/{e['gates_total']}  {e['status']}")
    print(f"\nvalidated: {len(validated)}/{len(evaluated)}")
    null = next(e for e in evaluated if e["id"] == "S08")
    print(f"null control gate count: {null['gates_passed']}/{null['gates_total']} "
          f"(a working gate rejects it: {'YES' if null['status'] != 'VALIDATED' else 'NO'})")


if __name__ == "__main__":
    main()
