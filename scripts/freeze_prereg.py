#!/usr/bin/env python3
"""freeze_prereg.py — freeze pre-registration files for every strategy family and
record the pre-tip publication of the 2026-11-15..18 rolling slate in the ledger.

MUST run before the first tip of the slate it publishes (2026-11-15T18:00Z,
IND@PHI 1:00 PM ET). The ledger entry it writes commits to the exact bytes of the
published picks/lines and to every prereg file, so a later settlement can prove
what was frozen.

Writes:
  data/prereg/Prereg_index.json
  data/prereg/S01..S08 + T-SINGLE/T-PARLAY/T-SGP prereg files (one per strategy)
  data/archive/horizon_picks_2026-11-15.json (byte-identical copy of the live file)
  data/archive/horizon_lines_2026-11-15.json
  data/ledger/ledger.json  (appends entry 4: pre_tip_publication for the new slate)

Run:  python3 scripts/freeze_prereg.py
"""
import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB_AT = "2026-11-15T12:55Z"
FIRST_TIP = "2026-11-15T18:00Z"  # IND@PHI 1:00 PM ET
SESSION = "arena/83d380ad-nba1"
UNIVERSE = ("all 34 games on the official 2026-11-15..2026-11-18 slate "
            "(data/raw/official_schedule_capture_2026-11-15.json); window rule = "
            "today (2026-11-15 UTC) + 3 days per the project brief")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def digest(rel):
    return sha(open(os.path.join(ROOT, rel), "rb").read())


def load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def dump(rel, doc):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", rel)


GATES = {
    "G1_sample_floor": "n >= 100 graded bets",
    "G2_significance": "one-sided binomial p < 0.05, Bonferroni-corrected",
    "G3_luck_bootstrap": "5th percentile of 10000-draw bootstrap ROI > 0",
    "G4_stability": "profitable in both disjoint halves",
    "G5_fragility": "profitable after removing the best 5% of bets",
    "G6_provenance": "all driving inputs from approved official hosts",
    "conjunction": "ALL gates must pass. There is no partial credit.",
    "status_2026_11_15": "NO strategy has passed (Build A 0/8, Build B 0/10). All tickets are MODEL OUTPUT — UNVALIDATED, unfunded, zero stake.",
}

PRICE_STATUS = ("No licensed two-sided price exists (no odds feed; F-W07). Spread/total "
                "tickets settle on the repo's paper -110 convention (stake 1.10 to win 1.00). "
                "Moneyline strategies record W/L only; unit ROI stays blank until a price exists. "
                "SGP tickets settle at the model's published joint_prob_rho as fair price.")

STRATS = [
    ("S01", "High-confidence moneyline", "moneyline",
     "Bet the model's pick straight up when its win probability is at least 0.65.",
     {"win_prob_min": 0.65},
     "W/L from the official final (OT included). Units: BLOCKED (no market price) — record outcome only; "
     "settlement source = the official game page final score, recorded in data/settlement/ for each slate.",
     "data/derived/strategies.json (Build A), docs/data/leaderboard.json (Build B)"),
    ("S02", "Extreme-confidence moneyline", "moneyline",
     "Bet the model's pick straight up when its win probability is at least 0.75.",
     {"win_prob_min": 0.75},
     "W/L from the official final (OT included). Units: BLOCKED (no market price).",
     "data/derived/strategies.json, docs/data/leaderboard.json"),
    ("S03", "Total deviation fade", "total",
     "When the model's projected total sits more than 6 points away from the market total, fade the model "
     "and take the market side.",
     {"deviation_points_min": 6.0},
     "Settle the fade side against the final combined score vs the market total. BLOCKED: the strategy "
     "requires a point-in-time market total, which does not exist in this repo (F-W07); no ticket is "
     "produced until it does. When unblocked: settlement uses the official final (quarters sum asserted).",
     "data/derived/strategies.json"),
    ("S04", "Two-leg moneyline parlay, cross-game", "parlay",
     "Combine the two highest-confidence moneyline picks on a slate into a cross-game parlay.",
     {"legs": 2, "selection": "top-2 by model win probability, different games"},
     "Both legs must win (official finals). Price: the published Frechet–Hoeffding band "
     "(fair_odds_lb/ub) is printed beside the naive product at publication; settlement pays the "
     "band lower bound at -110 legs (paper). Push convention: a push leg voids the stake proportionally.",
     "data/derived/horizon_picks.json parlays[] (2026-11-15..18 vintage)"),
    ("S05", "Player prop over, half-line", "player_prop",
     "Take the over on a player points prop line set half a point below his season average, when the "
     "model's over probability exceeds the break-even rate.",
     {"line_offset_points": -0.5, "selection": "season_avg - 0.5", "prob_over_min": 0.5},
     "Settle from the official box-score points row for that player in that game (Over wins if pts > "
     "line; ties at .5 impossible with the half-line). Player inactive = VOID leg. "
     "Price: -110 paper convention.",
     "data/derived/horizon_picks.json sgp_candidates[] leg construction"),
    ("S06", "Same-game parlay: player points + team total", "sgp",
     "Pair a player-points over with the same game's total over in one ticket.",
     {"legs": 2, "kinds": ["player_points_over", "game_total_over"]},
     "Both legs must win (official box score + official final). Any losing leg loses the stake 1.10; "
     "void legs removed. Price at the model's published joint_prob_rho (G-PROP blocked).",
     "data/derived/horizon_picks.json sgp_candidates[]"),
    ("S07", "Injury-fade total under", "total",
     "Take the under when a NEW absence removes at least 12 expected points from one side "
     "(canonical NEW_ABSENCE rule, scripts/injury_impact.py).",
     {"expected_points_removed_min": 12.0, "absence_class": "NEW_ABSENCE"},
     "Settle vs the final combined score (official final). Settlement source = the official game "
     "page; absence evidence = the official injury-report PDF edition stored with its timestamp.",
     "data/derived/horizon_lines.json availability_rows + scripts/injury_impact.py"),
    ("S08", "NULL CONTROL — coin flip", "control",
     "Bet a coin flip on every game in the backtest sample (control arm).",
     {"selection": "deterministic pseudo-random side per game (seeded)"},
     "W/L from the official final; graded like S01. Exists to measure how often a strategy beats "
     "noise; never a published bet.",
     "data/derived/strategies.json"),
]

TICKETS = [
    ("T-SINGLE", "Horizon single (G-CFG margin gate)",
     "For each window game, the two-estimator-originated margin line is published; a side is picked "
     "when |projected margin| >= 3.0, otherwise PASS (NO BET).",
     {"pick_gate_margin": 3.0, "source": "data/originated_lines.json assumptions (inherited)"},
     "Grade from the published pick_line text \\\"TEAM -x.x\\\": cover if the team wins by more than x.x, "
     "PUSH at exactly x.x, else LOSS. Paper -110 (WIN +1.00 / LOSS -1.10 / PUSH 0.00). Gate failures "
     "settle NO BET 0.00. Finals from data/official/results_YYYY-MM-DD.json (quarters sum asserted)."),
    ("T-PARLAY", "Horizon cross-game parlay",
     "All ordered pairs of G-CFG-passing singles from different games on the same date; joint "
     "probability published as the Frechet–Hoeffding band with the naive product printed beside it.",
     {"legs": 2, "different_games": True, "band": "Frechet–Hoeffding"},
     "Every leg must WIN; any losing leg loses stake 1.10; WIN pays the published fair-odds band "
     "lower bound (paper)."),
    ("T-SGP", "Horizon same-game player-prop pair",
     "Two over-props in one game (teammates or opponents), lines at the player's season average, "
     "sigma = sqrt(avg)*1.15, rho from the measured sgp_rho register; max 2 tickets per date.",
     {"legs": 2, "sigma_rule": "sqrt(season_avg) * 1.15 (documented assumption)",
      "rho_source": "docs/data/correlations.json sgp_rho register (Build B, MODEL-DERIVED)",
      "per_date_cap": 2},
     "Legs settle from official box-score points (Over if pts > line). Inactive player = VOID leg "
     "(removed; remaining legs settle at the frozen ticket price). Any losing leg loses stake 1.10; "
     "all-live-legs-win pays 1.10 * (1/joint_prob_rho - 1) at the price frozen at publication."),
]

DIGESTS = {
    "data/derived/horizon_picks.json": digest("data/derived/horizon_picks.json"),
    "data/derived/horizon_lines.json": digest("data/derived/horizon_lines.json"),
    "data/teams_advanced_2026_27.json": digest("data/teams_advanced_2026_27.json"),
    "data/teams_scoring_2026_27.json": digest("data/teams_scoring_2026_27.json"),
    "data/raw/official_schedule_capture_2026-11-15.json": digest("data/raw/official_schedule_capture_2026-11-15.json"),
    "data/official/injury_2026-11-15_0615AM.json": digest("data/official/injury_2026-11-15_0615AM.json"),
    "data/official/results_2026-11-14.json": digest("data/official/results_2026-11-14.json"),
    "data/settlement/settlement_2026-11-14.json": digest("data/settlement/settlement_2026-11-14.json"),
}

def prereg(sid, name, family, signal, thresholds, settlement, definition_ref):
    return {
        "prereg_id": sid,
        "strategy_name": name,
        "family": family,
        "signal": signal,
        "thresholds": thresholds,
        "universe": UNIVERSE,
        "exact_settlement_rule": settlement,
        "price_status": PRICE_STATUS,
        "validation_gates": GATES,
        "definition_ref": definition_ref,
        "frozen_at_utc": PUB_AT,
        "frozen_by": SESSION,
        "first_tip_of_universe": FIRST_TIP,
        "frozen_before_first_tip": True,
        "input_digests_sha256": DIGESTS,
    }

files = []
for sid, name, family, signal, thresholds, settlement, ref in STRATS:
    rel = f"data/prereg/{sid}.json"
    dump(rel, prereg(sid, name, family, signal, thresholds, settlement, ref))
    files.append(rel)
for tid, name, signal, thresholds, settlement in TICKETS:
    rel = f"data/prereg/{tid}.json"
    dump(rel, prereg(tid, name, "horizon_ticket", signal, thresholds, settlement,
                     "data/derived/horizon_picks.json (2026-11-15..18 vintage)"))
    files.append(rel)

index = {
    "title": "Pre-registration index — strategies frozen before the first tip of the 2026-11-15..18 slate",
    "rule": ("Per the project brief: every strategy's signal, thresholds, universe and exact "
             "settlement rule are frozen before the first bet of the slate. Files are hash-chained "
             "into data/ledger/ledger.json at publication."),
    "frozen_at_utc": PUB_AT,
    "first_tip": FIRST_TIP,
    "files": {rel: digest(rel) for rel in files},
    "universe": UNIVERSE,
    "slate_tickets_published": "data/derived/horizon_picks.json (archived byte-identical at "
                               "data/archive/horizon_picks_2026-11-15.json)",
    "prior_vintage_settled": ("data/settlement/settlement_2026-11-14.json covers the 2026-11-14 slate "
                              "of the 2026-11-14..17 vintage; that vintage's 11/15-11/17 picks remain "
                              "settleable from data/archive/horizon_picks_2026-11-14.json (ledger entry 1)."),
}
dump("data/prereg/Prereg_index.json", index)

# ---- archive the new vintage + append ledger entry 4 ----------------------
ARCH = {"data/archive/horizon_picks_2026-11-15.json": "data/derived/horizon_picks.json",
        "data/archive/horizon_lines_2026-11-15.json": "data/derived/horizon_lines.json"}
for dst, src in ARCH.items():
    os.makedirs(os.path.dirname(os.path.join(ROOT, dst)), exist_ok=True)
    open(os.path.join(ROOT, dst), "wb").write(open(os.path.join(ROOT, src), "rb").read())
print("archived 2026-11-15 vintage")

ledger_rel = "data/ledger/ledger.json"
ledger = load(ledger_rel)
assert ledger["entries"], "ledger missing"


def canon(d):
    return json.dumps(d, sort_keys=True).encode()


prev = None
for e in ledger["entries"]:
    if prev is not None:
        assert e["prev"] == prev, f"chain broken before entry {e['entry']}"
    prev = sha(canon(e))
assert prev == ledger["head"], "ledger head mismatch at append time"

e4 = {
    "entry": 4,
    "type": "pre_tip_publication",
    "at_utc": PUB_AT,
    "first_tip_utc": FIRST_TIP,
    "window": "2026-11-15 .. 2026-11-18 (today + 3 days)",
    "files": {dst: sha(open(os.path.join(ROOT, dst), "rb").read()) for dst in ARCH},
    "prereg_files": {rel: digest(rel) for rel in files + ["data/prereg/Prereg_index.json"]},
    "model_input_digests": DIGESTS,
    "note": ("Rolling-slate publication for the 2026-11-15..18 window, generated after the "
             "2026-11-14 games were settled (entry 3) and before the first tip of the window. "
             "Preregistration files for every strategy family are frozen by digest here. The "
             "2026-11-14..17 vintage (entry 1) remains settleable from its archives."),
    "prev": prev,
}
h4 = sha(canon(e4))
ledger["entries"].append(e4)
ledger["head"] = h4
dump(ledger_rel, ledger)
print("ledger entry 4 appended; head", h4[:16])
