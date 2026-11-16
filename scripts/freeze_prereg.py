#!/usr/bin/env python3
"""freeze_prereg.py — freeze pre-registration files for every strategy family and
record the pre-tip publication of the current rolling slate in the ledger.

ROLLING: the window, the first tip and the input digests are all resolved at run
time from data/derived/horizon_lines.json, which is itself produced by
scripts/originate_horizon.py from the newest official schedule capture. Nothing
about the slate is typed here any more, so a new capture cannot silently
pre-register the wrong window.

MUST run before the first tip of the slate it publishes. The ledger entry it
writes commits to the exact bytes of the published picks/lines and to every
prereg file, so a later settlement can prove what was frozen.

Writes:
  data/prereg/Prereg_index.json
  data/prereg/S01..S08 + T-SINGLE/T-PARLAY/T-SGP prereg files (one per strategy)
  data/archive/horizon_picks_<window-start>.json (byte-identical copy of the live file)
  data/archive/horizon_lines_<window-start>.json
  data/ledger/ledger.json  (appends the next entry: pre_tip_publication)

Run:  python3 scripts/freeze_prereg.py
"""
import hashlib
import json
import os
import subprocess

import datetime as _dt
import glob as _glob
import re as _re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION = "arena/161f1638-nba1"


def _load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def _newest(pattern):
    c = [q for q in _glob.glob(os.path.join(ROOT, pattern))
         if _re.search(r"\d{4}-\d{2}-\d{2}", q)]
    return sorted(c)[-1] if c else None


# ---- the window, from the originated lines file (never typed) ----------
_LINES = _load("data/derived/horizon_lines.json")
_LMETA = _LINES["_meta"]
_DATES = sorted({g["date"] for g in _LINES["games"]})
_N_GAMES = len(_LINES["games"])
WINDOW_START, WINDOW_END = _DATES[0], _DATES[-1]
WINDOW = "%s .. %s" % (WINDOW_START, WINDOW_END)
PER_DAY = ", ".join("%s=%d" % (d, sum(1 for g in _LINES["games"] if g["date"] == d))
                    for d in _DATES)

# ---- first tip, in UTC, from the official tip times --------------------
# Eastern time is UTC-5 in November (EST is in force until the second Sunday in
# March), so 7:00 PM ET on a date is 00:00Z on the next date. That matters: the
# pre-registration has to be frozen before the first tip in UTC, not before the
# first tip on the calendar day the slate is labelled with.
_ET_OFFSET_HOURS = 5


def _tip_utc(date_str, tip_et):
    m = _re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*ET", str(tip_et).strip())
    if not m:
        return None
    hh, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and hh != 12:
        hh += 12
    if ap == "AM" and hh == 12:
        hh = 0
    y, mo, d = map(int, date_str.split("-"))
    return _dt.datetime(y, mo, d, hh, mm, tzinfo=_dt.timezone.utc) + \
        _dt.timedelta(hours=_ET_OFFSET_HOURS)


_TIPS = [(g["date"], g["matchup"], g.get("tip_et"), _tip_utc(g["date"], g.get("tip_et")))
         for g in _LINES["games"]]
_TIPS_OK = [t for t in _TIPS if t[3] is not None]
assert _TIPS_OK, "no parseable tip time in horizon_lines.json - refusing to pre-register"
_FIRST = min(_TIPS_OK, key=lambda t: t[3])
FIRST_TIP = _FIRST[3].strftime("%Y-%m-%dT%H:%MZ")
_TIP_LABEL = str(_FIRST[2]).strip()
FIRST_TIP_GAME = "%s %s (%s)" % (_FIRST[0], _FIRST[1], _TIP_LABEL)
PUB_AT = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
assert PUB_AT < FIRST_TIP, (
    "publishing at %s but the first tip is %s - the freeze would be after the fact"
    % (PUB_AT, FIRST_TIP))

_SCHED_REL = os.path.relpath(
    os.path.join(ROOT, _LMETA["inputs"]["schedule_capture"].lstrip("/")), ROOT) \
    if _LMETA["inputs"].get("schedule_capture", "").startswith(("data/", "/data")) \
    else "data/raw/" + os.path.basename(_LMETA["inputs"]["schedule_capture"])
_INJ_REL = "data/official/" + os.path.basename(_LMETA["inputs"]["injury_file"])

UNIVERSE = ("all %d games on the official %s slate (%s: %s); source file %s; "
            "window rule = the newest official schedule capture, today (UTC) + up "
            "to 3 days per the project brief"
            % (_N_GAMES, WINDOW, _SCHED_REL, PER_DAY, _SCHED_REL))


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
     "data/derived/horizon_picks.json parlays[] (%s vintage)" % WINDOW),
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

# Every input the lines were built from, hashed at the moment of publication so a
# later settlement can prove which bytes were frozen. Resolved from the lines file
# plus the newest stored official capture of each kind - nothing typed.
DIGEST_RELS = [
    "data/derived/horizon_picks.json",
    "data/derived/horizon_lines.json",
] + list(_LMETA["inputs"]["ratings_files"]) + [
    _SCHED_REL,
    _INJ_REL,
]
for _pat in ("data/official/results_*.json", "data/settlement/settlement_*.json"):
    _f = _newest(_pat)
    if _f:
        DIGEST_RELS.append(os.path.relpath(_f, ROOT))
DIGEST_RELS = list(dict.fromkeys(DIGEST_RELS))          # de-dup, keep order
DIGESTS = {}
for _rel in DIGEST_RELS:
    try:
        DIGESTS[_rel] = digest(_rel)
    except OSError:
        print("WARNING: input %s is missing - not hashed" % _rel)
assert len(DIGESTS) >= 6, "too few inputs hashed - refusing to pre-register"
print("publishing window %s (%d games), first tip %s (%s), frozen at %s"
      % (WINDOW, _N_GAMES, FIRST_TIP, FIRST_TIP_GAME, PUB_AT))

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
        "slate_window": WINDOW,
        "games_in_universe": _N_GAMES,
        "first_tip_of_universe_utc": FIRST_TIP,
        "first_game_tipping": FIRST_TIP_GAME,
        "frozen_before_first_tip": True,
        "hours_before_first_tip": round(
            (_dt.datetime.strptime(FIRST_TIP, "%Y-%m-%dT%H:%MZ")
             - _dt.datetime.strptime(PUB_AT, "%Y-%m-%dT%H:%MZ")).total_seconds() / 3600.0, 2),
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
                     "data/derived/horizon_picks.json (%s vintage)" % WINDOW))
    files.append(rel)

index = {
    "title": ("Pre-registration index — strategies frozen before the first tip of the %s slate"
              % WINDOW),
    "rule": ("Per the project brief: every strategy's signal, thresholds, universe and exact "
             "settlement rule are frozen before the first bet of the slate. Files are hash-chained "
             "into data/ledger/ledger.json at publication."),
    "frozen_at_utc": PUB_AT,
    "slate_window": WINDOW,
    "games_in_universe": _N_GAMES,
    "games_per_day": PER_DAY,
    "first_tip_utc": FIRST_TIP,
    "first_game_tipping": FIRST_TIP_GAME,
    "files": {rel: digest(rel) for rel in files},
    "universe": UNIVERSE,
    "slate_tickets_published": "data/derived/horizon_picks.json (archived byte-identical at "
                               "data/archive/horizon_picks_%s.json)" % WINDOW_START,
    "prior_vintage_settled": ("data/settlement/settlement_2026-11-14.json covers the 2026-11-14 slate "
                              "of the 2026-11-14..17 vintage; that vintage's 11/15-11/17 picks remain "
                              "settleable from data/archive/horizon_picks_2026-11-14.json (ledger entry 1)."),
}
dump("data/prereg/Prereg_index.json", index)

# ---- snapshot this vintage's pre-registration set -----------------------
# The live data/prereg/ files are re-frozen for every slate, so a ledger entry
# that points only at them stops verifying the moment the next slate is
# published. Every vintage is therefore also written here, byte-identical, at
# publication time, and verify_ledger.py accepts an archived copy when the live
# path has been superseded.
PREREG_FILES = files + ["data/prereg/Prereg_index.json"]
PREREG_ARCHIVE = "data/archive/prereg_%s" % WINDOW_START
for _rel in PREREG_FILES:
    _dst = os.path.join(ROOT, PREREG_ARCHIVE, os.path.basename(_rel))
    os.makedirs(os.path.dirname(_dst), exist_ok=True)
    open(_dst, "wb").write(open(os.path.join(ROOT, _rel), "rb").read())
print("snapshot %d prereg files -> %s" % (len(PREREG_FILES), PREREG_ARCHIVE))

# ---- archive the new vintage + append ledger entry ----------------------
ARCH = {"data/archive/horizon_picks_%s.json" % WINDOW_START: "data/derived/horizon_picks.json",
        "data/archive/horizon_lines_%s.json" % WINDOW_START: "data/derived/horizon_lines.json"}
for dst, src in ARCH.items():
    os.makedirs(os.path.dirname(os.path.join(ROOT, dst)), exist_ok=True)
    open(os.path.join(ROOT, dst), "wb").write(open(os.path.join(ROOT, src), "rb").read())
print("archived %s vintage" % WINDOW_START)

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

_last = ledger["entries"][-1]
if (_last.get("type") == "pre_tip_publication"
        and (_last.get("window") or "").startswith(WINDOW_START)
        and _last.get("files")
        and all(sha(open(os.path.join(ROOT, dst), "rb").read()) == h
                for dst, h in _last["files"].items())
        and _last.get("prereg_files") == {rel: digest(rel) for rel in PREREG_FILES}
        and _last.get("model_input_digests") == DIGESTS):
    print("unchanged: entry %s already freezes this exact window (%s) with identical "
          "digests - not appending a duplicate" % (_last["entry"], WINDOW))
    raise SystemExit(0)

_n = max(e["entry"] for e in ledger["entries"]) + 1
e_new = {
    "entry": _n,
    "type": "pre_tip_publication",
    "at_utc": PUB_AT,
    "first_tip_utc": FIRST_TIP,
    "first_game_tipping": FIRST_TIP_GAME,
    "window": "%s (today + up to 3 days)" % WINDOW,
    "games_in_universe": _N_GAMES,
    "games_per_day": PER_DAY,
    "files": {dst: sha(open(os.path.join(ROOT, dst), "rb").read()) for dst in ARCH},
    "prereg_files": {rel: digest(rel) for rel in PREREG_FILES},
    "prereg_archive_dir": PREREG_ARCHIVE,
    "model_input_digests": DIGESTS,
    "note": ("Rolling-slate publication for the %s window, generated before the first tip of "
             "the window (%s) and after the previous slate's settlement. Preregistration files "
             "for every strategy family are frozen by digest here. Every earlier vintage stays "
             "settleable from its own archive under data/archive/." % (WINDOW, FIRST_TIP)),
    "prev": prev,
}
h_new = sha(canon(e_new))
ledger["entries"].append(e_new)
ledger["head"] = h_new
dump(ledger_rel, ledger)
print("ledger entry %d appended; head %s" % (_n, h_new[:16]))
