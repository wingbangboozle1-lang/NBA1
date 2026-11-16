#!/usr/bin/env python3
"""I03 comparison, arena/8f64e94c-nba1 (2026-11-15).

Reproducible row-by-row comparison of the published horizon and schedule
capture against the live official observation record. Nothing is inferred:
every comparison reads either a committed repository file or the observation
files in this directory, and every outcome links to the official URL.

Usage:  python3 verify/2026-11-15-8f64e94c/compare.py
Writes: verify/2026-11-15-8f64e94c/compare.json
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def norm_tip(s):
    """'01:00 PM ET' -> '1:00 PM'; '4:30 PM (from ...)' -> '4:30 PM'."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)", s or "")
    if not m:
        return None
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3)
    return "%d:%s %s" % (h, mm, ap)


def main():
    live = load(os.path.join(HERE, "live_schedule_2026-11-15T2352Z.json"))
    state = load(os.path.join(HERE, "live_state_2026-11-15T2352Z.json"))
    hz = load(os.path.join(ROOT, "data", "derived", "horizon_lines.json"))
    sch = load(os.path.join(ROOT, "data", "official", "schedule_2026-11-15_to_18.json"))

    by_id = {r["game_id"]: r for r in live["rows"]}

    horizon_rows = []
    for g in hz["games"]:
        o = by_id.get(g["game_id"])
        row = {
            "game_id": g["game_id"],
            "date": g["date"],
            "matchup": g["matchup"],
            "tip_et_published": g.get("tip_et"),
            "source_url": g.get("schedule_source") or o and live["sources"][0],
            "live_tip_et_observed": o and o["tip_et_observed"],
            "live_date": o and o["date"],
            "live_matchup": o and "%s@%s" % (o["away"], o["home"]),
        }
        checks = {
            "game_id_present_live": o is not None,
            "date_agrees": bool(o) and o["date"] == g["date"],
            "matchup_agrees": bool(o) and ("%s@%s" % (o["away"], o["home"])) == g["matchup"],
            "tip_agrees": bool(o) and norm_tip(o["tip_et_observed"]) == norm_tip(g.get("tip_et")),
        }
        row["checks"] = checks
        row["result"] = "AGREE" if all(checks.values()) else "DISAGREE"
        horizon_rows.append(row)

    sched_rows = []
    for r in sch["rows"]:
        o = by_id.get(r["game_id"])
        checks = {
            "game_id_present_live": o is not None,
            "date_agrees": bool(o) and o["date"] == r["date"],
            "matchup_agrees": bool(o) and ("%s@%s" % (o["away"], o["home"])) == "%s@%s" % (r["away"], r["home"]),
            "tip_agrees": bool(o) and norm_tip(o["tip_et_observed"]) == norm_tip(r.get("tip_et")),
        }
        sched_rows.append({
            "game_id": r["game_id"],
            "date": r["date"],
            "matchup": "%s@%s" % (r["away"], r["home"]),
            "tip_et_published": r.get("tip_et"),
            "source_url": r.get("source_url"),
            "live_tip_et_observed": o and o["tip_et_observed"],
            "checks": checks,
            "result": "AGREE" if all(checks.values()) else "DISAGREE",
        })

    finals = []
    for g in state["games"]:
        if g["state"] != "Final":
            continue
        s_away = sum(g["quarters_away"])
        s_home = sum(g["quarters_home"])
        finals.append({
            "game_id": g["game_id"],
            "date": g["date"],
            "matchup": g["matchup"],
            "away_pts": g["score_away"],
            "home_pts": g["score_home"],
            "away_quarters": g["quarters_away"],
            "home_quarters": g["quarters_home"],
            "quarters_sum_away": s_away == g["score_away"],
            "quarters_sum_home": s_home == g["score_home"],
            "official_page_marks_final": True,
            "result": "VERIFIED FINAL" if (s_away == g["score_away"] and s_home == g["score_home"]) else "CHECK FAILED",
            "source_url": g["source_url"],
            "source_gamebook_pdf": g.get("source_gamebook_pdf"),
        })

    pairs = {}
    for g in hz["games"]:
        pairs.setdefault(g["matchup"], []).append(g)
    repeats = {m: [x["game_id"] for x in v] for m, v in pairs.items() if len(v) > 1}

    out = {
        "title": "I03 row-level comparison: published horizon vs live official pages",
        "captured_by": "arena/8f64e94c-nba1",
        "compared_utc": "2026-11-15T23:56Z",
        "inputs": {
            "published_horizon": "data/derived/horizon_lines.json (34 games, 15-18 Nov roll, frozen pre-tip at 2026-11-15T12:55Z)",
            "published_schedule_capture": "data/official/schedule_2026-11-15_to_18.json",
            "live_observation": "verify/2026-11-15-8f64e94c/live_schedule_2026-11-15T2352Z.json",
            "live_results_observation": "verify/2026-11-15-8f64e94c/live_state_2026-11-15T2352Z.json",
        },
        "horizon_vs_live": horizon_rows,
        "schedule_capture_vs_live": sched_rows,
        "finals_verified": finals,
        "repeated_matchups_in_horizon": repeats,
        "repeated_matchups_note": live["duplicate_matchup_note"],
        "summary": {
            "horizon_rows": len(horizon_rows),
            "horizon_agree": sum(1 for r in horizon_rows if r["result"] == "AGREE"),
            "schedule_rows": len(sched_rows),
            "schedule_agree": sum(1 for r in sched_rows if r["result"] == "AGREE"),
            "finals_verified": len(finals),
            "injury_basis_edition": "11/15/26 06:15 AM ET (index shows newer 11/15 editions; currency gap published as F93 (renumbered from F79 at merge))",
        },
    }
    with open(os.path.join(HERE, "compare.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    s = out["summary"]
    print("horizon rows      : %d/%d agree" % (s["horizon_agree"], s["horizon_rows"]))
    print("schedule rows     : %d/%d agree" % (s["schedule_agree"], s["schedule_rows"]))
    print("finals verified   : %d" % s["finals_verified"])
    for r in horizon_rows + sched_rows:
        if r["result"] != "AGREE":
            print("DISAGREE:", r["game_id"], r["checks"])


if __name__ == "__main__":
    main()
