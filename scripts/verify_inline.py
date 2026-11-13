#!/usr/bin/env python3
"""
verify_inline.py — a second pair of eyes on derived outputs.

verify_data.py checks the RAW captured data against its official sources.
This script checks the DERIVED outputs against the raw data, and hunts for the specific
failure modes this project is most exposed to:

  1. A derived number that no raw input can produce (invented value).
  2. A probability outside [0,1], or a refusal to reach 0/1 when the gap demands it.
  3. A row carrying no source link.
  4. The null control scoring better than a real strategy.
  5. A strategy marked VALIDATED without clearing every gate.
  6. An injury adjustment applied to a player whose absence is already in the team stats.
  7. A total that is wildly implausible for a 48-minute NBA game.

Exit code is 1 if any hard failure is found, so it can gate the build.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
D = os.path.join(DATA, "derived")

APPROVED = ("www.nba.com", "official.nba.com", "ak-static.cms.nba.com", "nba.com")

results = []


def add(group, name, ok, detail):
    results.append({"group": group, "name": name, "ok": ok, "detail": detail})


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def has_source(obj):
    """True if the object or a nested value carries an approved-host URL."""
    blob = json.dumps(obj)
    return any(h in blob for h in APPROVED)


def main():
    lines = load(os.path.join(D, "lines.json"))
    bt = load(os.path.join(D, "backtest.json"))
    corr = load(os.path.join(D, "correlations.json"))
    inj = load(os.path.join(D, "injury_impact.json"))
    strat = load(os.path.join(D, "strategies.json"))
    evidence = load(os.path.join(DATA, "player_absence_evidence.json"))

    # 1. every derived game line must trace to a raw schedule row
    sched = {(g["game_id"]): g for g in load(os.path.join(DATA, "schedule_2026_11_13_to_16.json"))["games"]}
    orphans = [g["game_id"] for g in lines["games"] if g["game_id"] not in sched]
    add("provenance", "every line has a schedule row", not orphans,
        f"{len(lines['games'])} lines, {len(orphans)} orphaned: {orphans}")

    # 2. projections must be reconstructible from the printed inputs
    bad = []
    for g in lines["games"]:
        poss = g["pace_home"] + g["pace_away"] - 99.85
        if abs(poss - g["game_possessions"]) > 0.05:
            bad.append((g["game_id"], "poss", round(poss, 2), g["game_possessions"]))
        if abs((g["proj_home_pts"] + g["proj_away_pts"]) - g["line_total"]) > 0.06:
            bad.append((g["game_id"], "total", g["proj_home_pts"] + g["proj_away_pts"], g["line_total"]))
        if abs((g["proj_home_pts"] - g["proj_away_pts"]) - g["line_spread_home"]) > 0.06:
            bad.append((g["game_id"], "spread", g["proj_home_pts"] - g["proj_away_pts"], g["line_spread_home"]))
    add("arithmetic", "line_total and line_spread reconstruct from projected points", not bad,
        f"{len(bad)} mismatches" + (f": {bad[:4]}" if bad else ""))

    # 3. probabilities must be in (0,1) and must not saturate
    probs = []
    for g in lines["games"]:
        ml = g.get("line_home_ml")
        if ml is not None:
            probs.append(1.0 / (1.0 + ml / 100.0) if ml > 0 else abs(ml) / (abs(ml) + 100.0))
    out_of_range = [p for p in probs if not (0.0 < p < 1.0)]
    saturated = [p for p in probs if p < 0.02 or p > 0.98]
    add("probability", "no win probability is outside (0,1)", not out_of_range,
        f"{len(out_of_range)} out of range")
    add("probability", "no win probability saturates beyond 2%", not saturated,
        f"{len(saturated)} saturating of {len(probs)}")

    # 4. every table row must carry a source link
    rows_without = []
    for coll in ("games", "props"):
        for r in lines.get(coll, []):
            if not has_source(r):
                rows_without.append(f"{coll}:{r.get('game_id') or r.get('player')}")
    add("sourcing", "every line/prop row carries an official source link", not rows_without,
        f"{len(rows_without)} unsourced" + (f": {rows_without[:5]}" if rows_without else ""))

    # 5. backtest must be self-consistent and explicitly labelled
    s = bt["summary"]
    add("backtest", "backtest carries the contaminated label",
        "CONTAMINATED" in s.get("labelled", ""), s.get("labelled", "")[:60])
    add("backtest", "backtest row count matches summary", len(bt["rows"]) == s["n_games"],
        f"{len(bt['rows'])} rows vs {s['n_games']} declared")
    recomputed = sum(1 for r in bt["rows"] if r["model_pick"] == r["actual_winner"]) / len(bt["rows"])
    add("backtest", "straight-up accuracy recomputes",
        abs(recomputed - s["straight_up_accuracy"]) < 0.0002,
        f"{recomputed:.4f} vs {s['straight_up_accuracy']}")

    # 6. correlations: value must be null exactly when it is claimed unavailable
    null_valued = [c for c in corr["tier_c_not_computable"] if c["value"] is not None]
    add("correlations", "tier-C entries are genuinely null (never guessed)", not null_valued,
        f"{len(null_valued)} tier-C rows carry a value")
    computed = [c for c in corr["tier_a_empirical"] if c["r"] is None]
    add("correlations", "every tier-A row has a computed r", not computed,
        f"{len(computed)} missing")
    ident = [c for c in corr["tier_a_empirical"] if c["r"] is not None and abs(c["r"]) > 0.995]
    add("correlations", "no tier-A correlation is actually an identity", not ident,
        f"{len(ident)} near-identities presented as findings")

    # 7. injuries: a baked-in absence must never produce an adjustment
    bad_adj = [p["player"] for p in inj["players"]
               if p["absence_class"] in ("ALREADY_BAKED_IN", "SEASON_LONG", "NOT_ABSENT")
               and p["expected_points_removed"] != 0]
    add("injuries", "no baked-in absence is deducted twice", not bad_adj,
        f"{len(bad_adj)} double-counted: {bad_adj}")

    classes = {}
    for r in evidence["rows"]:
        classes[r["class"]] = classes.get(r["class"], 0) + 1
    add("injuries", "evidence file uses only declared classes",
        set(classes) <= {"NEW_ABSENCE", "ALREADY_BAKED_IN", "SEASON_LONG", "NOT_ABSENT", "UNKNOWN"},
        str(classes))

    # 8. strategies: no false VALIDATED, and the null control must fail
    false_valid = [e["id"] for e in strat["leaderboard"]
                   if e["status"] == "VALIDATED" and (e["failed_gates"] or e["n_graded"] < 100)]
    add("strategies", "no strategy is VALIDATED while failing a gate or under n=100",
        not false_valid, f"{len(false_valid)} false validations: {false_valid}")

    null = next(e for e in strat["leaderboard"] if e["id"] == "S08")
    add("strategies", "the null control is not VALIDATED", null["status"] != "VALIDATED",
        f"control status {null['status']} with {null['gates_passed']}/{null['gates_total']} gates")

    # the bootstrap gate must not pass when there are too few losses to resample
    degenerate_pass = [e["id"] for e in strat["leaderboard"]
                       if e["gates"]["G3_luck_bootstrap"].get("degenerate")
                       and e["gates"]["G3_luck_bootstrap"]["passed"]]
    add("strategies", "luck gate never passes on a degenerate sample", not degenerate_pass,
        f"{len(degenerate_pass)} degenerate passes: {degenerate_pass}")

    thin = [(e["id"], e["gates"]["G3_luck_bootstrap"].get("losses"))
            for e in strat["leaderboard"] if e["n_graded"] and
            (e["gates"]["G3_luck_bootstrap"].get("losses") or 0) < 5]
    reported = all(e["gates"]["G3_luck_bootstrap"].get("degenerate") for e in strat["leaderboard"]
                   if e["n_graded"] and (e["gates"]["G3_luck_bootstrap"].get("losses") or 0) < 5)
    add("strategies", "every thin-loss sample is labelled degenerate", reported,
        f"thin-loss strategies: {thin}")

    declared = strat["_meta"]["validated_count"]
    actual = sum(1 for e in strat["leaderboard"] if e["status"] == "VALIDATED")
    add("strategies", "declared validated_count matches the ledger", declared == actual,
        f"declared {declared}, actual {actual}")

    # 9. totals must be plausible for a 48-minute game
    totals = [g["line_total"] for g in lines["games"]]
    implausible = [t for t in totals if t < 180 or t > 280]
    add("plausibility", "every projected total is within 180-280 points", not implausible,
        f"{len(implausible)} implausible: {implausible}")

    # 10. the site build must exist if it is claimed
    idx = os.path.join(ROOT, "docs", "index.html")
    add("site", "landing page exists", os.path.exists(idx),
        "docs/index.html" if os.path.exists(idx) else "missing")

    # ------------------------------------------------------------------ report
    print()
    groups = []
    for r in results:
        if r["group"] not in groups:
            groups.append(r["group"])
    fails = 0
    for g in groups:
        rs = [r for r in results if r["group"] == g]
        bad = [r for r in rs if not r["ok"]]
        fails += len(bad)
        print(f"[{g}] {len(rs) - len(bad)}/{len(rs)} passed")
        for r in rs:
            mark = "PASS      " if r["ok"] else "FAIL      "
            print(f"   {mark}{r['name']} — {r['detail']}")
    print(f"\nderived checks: {sum(1 for r in results if r['ok'])}/{len(results)} passed, failures={fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
