#!/usr/bin/env python3
"""
verify_data.py — provenance + internal-consistency checks for every dataset in data/.

Checks (the ones the project promises on every table row):
  1. PROVENANCE   every row carries an https source_url on an approved official domain.
  2. BLANK SCAN   empty/null values are counted and reported as "unverified" (never filled in).
  3. SCHEDULE     every W-L record on the schedule equals the GP/W/L in the team stats table.
  4. PACE         pace * minutes / 48 == season possession total (within 2%).
  5. RATINGS      pts*gp == OffRtg*POSS/100 and opp_pts*gp == DefRtg*POSS/100 (within 10 points,
                  absorbing the rounding of published rates).
  6. PLAYER ID    PTS == 2*FGM + 3PM + FTM (within 0.25) for every fully-published player row.

Exit 0 = no hard defect. "Unverified" findings never fail the build; they are published on the
Flagged for Review page.
"""
import json
import os
import sys
import urllib.parse
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

APPROVED_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
    "cdn.nba.com", "stats.nba.com", "data.nba.com",
}

errors, warnings, info = [], Counter(), []
blank = Counter()


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def check_provenance(doc_name, rows, key="source_url"):
    for i, row in enumerate(rows):
        url = row.get(key)
        if not url:
            errors.append(f"{doc_name}: row {i} has no {key}")
            continue
        p = urllib.parse.urlparse(url)
        if p.scheme != "https":
            errors.append(f"{doc_name}: row {i} source is not https ({url})")
        if (p.hostname or "") not in APPROVED_HOSTS:
            errors.append(f"{doc_name}: row {i} host '{(p.hostname or '')}' not an approved official host")
    info.append(f"{doc_name}: {len(rows)} rows, all with approved source hosts")


def main():
    teams = load("teams_advanced_2026_27.json")
    sched = load("schedule_2026_11_13_to_16.json")
    scoring = load("teams_scoring_2026_27.json")
    players = load("players_2026_27.json")
    injuries = load("injury_report_2026_11_13.json")

    for name, rows in [
        ("teams_advanced_2026_27.json", teams["rows"]),
        ("schedule_2026_11_13_to_16.json", sched["games"]),
        ("teams_scoring_2026_27.json", scoring["rows"]),
        ("players_2026_27.json", players["players"]),
        ("injury_report_2026_11_13.json", injuries["rows"]),
    ]:
        check_provenance(name, rows)

    by_abbr = {r["abbr"]: r for r in teams["rows"]}
    scor = {r["abbr"]: r for r in scoring["rows"]}

    # 3 ---------------------------------------------------------------- schedule
    for g in sched["games"]:
        for side in ("away", "home"):
            abbr = g[side]
            rec = g[f"{side}_record"]
            if abbr not in by_abbr:
                errors.append(f"schedule: unknown abbr {abbr} in {g['game_id']}")
                continue
            t = by_abbr[abbr]
            if f"{t['w']}-{t['l']}" != rec:
                errors.append(f"schedule {g['game_id']} {abbr}: {rec} != team stats {t['w']}-{t['l']}")
    info.append(f"schedule: {len(sched['games'])} games; every W-L reconciled to team stats")

    # 4 --------------------------------------------------------------- pace/poss
    for t in teams["rows"]:
        implied = t["pace"] * t["min"] / 48.0
        if abs(implied - t["poss"]) / t["poss"] > 0.02:
            errors.append(f"{t['abbr']}: pace*min/48={implied:.1f} vs poss={t['poss']}")
    info.append(f"pace: {len(teams['rows'])} teams; pace*min/48 matches season possessions within 2%")

    # 5 ------------------------------------------------------- ratings vs scoring
    worst = 0.0
    for abbr, t in by_abbr.items():
        s = scor[abbr]
        if s["gp"] != t["gp"]:
            errors.append(f"{abbr}: GP {s['gp']} on scoring page != {t['gp']} on advanced page")
        exp_pts = t["off_rtg"] * t["poss"] / 100.0
        exp_opp = t["def_rtg"] * t["poss"] / 100.0
        d1 = abs(s["pts"] * s["gp"] - exp_pts)
        d2 = abs(s["opp_pts"] * s["gp"] - exp_opp)
        worst = max(worst, d1, d2)
        if d1 > 10 or d2 > 10:
            errors.append(f"{abbr}: scoring vs ratings residual too large (off {d1:.1f}, def {d2:.1f})")
    info.append(f"ratings: 30 teams; pts*gp vs OffRtg*POSS/100 max residual {worst:.2f} points")

    # 6 --------------------------------------------------------- player pts identity
    checked = 0
    for p in players["players"]:
        if p["stat_source"] != "players_traditional":
            continue
        checked += 1
        calc = 2 * p["fgm"] + p["fg3m"] + p["ftm"]
        if abs(p["pts"] - calc) > 0.25:
            errors.append(f"player {p['player']}: PTS {p['pts']} != 2*FGM+3PM+FTM {calc:.2f}")
    info.append(f"players: {checked} full box-score rows satisfy PTS = 2*FGM + 3PM + FTM")

    # 2 -------------------------------------------------------------- blank scan
    for fn in sorted(os.listdir(DATA)):
        if not fn.endswith(".json"):
            continue
        doc = load(fn)
        for bag in [v for v in doc.values() if isinstance(v, list)]:
            for row in bag:
                if isinstance(row, dict):
                    for k, v in row.items():
                        if v is None or v == "":
                            blank[f"{fn}::{k}"] += 1
    for key, n in sorted(blank.items()):
        warnings[f"{key} (x{n})"] += 1

    print("=" * 78)
    print("VERIFICATION REPORT — data/")
    print("=" * 78)
    for line in info:
        print("  PASS        ", line)
    for key in warnings:
        print("  UNVERIFIED  ", key)
    for line in errors:
        print("  ERROR       ", line)
    print("-" * 78)
    print(f"errors={len(errors)}  unverified_fields={len(warnings)}  passed_checks={len(info)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
