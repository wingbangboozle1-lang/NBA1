#!/usr/bin/env python3
"""verify_horizon_fec7d5ae.py — first-hand re-read of the 25-game horizon vs the
stored capture.  Session arena/fec7d5ae-nba1 (COORDINATION §50, V-FEC-04).

Reads https://www.nba.com/games?date=2026-11-16 / 17 / 18 directly at 2026-11-16
~14:35Z and compares every (date, game_id, matchup, tip) against the stored
official schedule capture.  Nothing is inferred: a row that does not match is
reported, not corrected.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION = "arena/fec7d5ae-nba1"
CAPTURED_UTC = "2026-11-16T14:35:00Z"

STORED = "data/official/official_schedule_2026-11-16_to_18_dfef26dc.json"

# First-hand read: (date, matchup, tip_et, game_id)
FIRST_HAND = [
    ("2026-11-16", "ORL@BOS", "7:00 PM ET", "0022600245"),
    ("2026-11-16", "MEM@WAS", "7:00 PM ET", "0022600247"),
    ("2026-11-16", "CHI@CLE", "7:00 PM ET", "0022600246"),
    ("2026-11-16", "HOU@MIA", "7:30 PM ET", "0022600249"),
    ("2026-11-16", "PHI@BKN", "7:30 PM ET", "0022600248"),
    ("2026-11-16", "GSW@NOP", "8:00 PM ET", "0022600251"),
    ("2026-11-16", "POR@MIN", "8:00 PM ET", "0022600250"),
    ("2026-11-16", "PHX@DEN", "9:00 PM ET", "0022600252"),
    ("2026-11-17", "NYK@TOR", "7:30 PM ET", "0022600253"),
    ("2026-11-17", "DET@SAS", "8:00 PM ET", "0022600255"),
    ("2026-11-17", "POR@MIN", "8:00 PM ET", "0022600254"),
    ("2026-11-17", "UTA@LAC", "10:30 PM ET", "0022600257"),
    ("2026-11-17", "CHA@LAL", "11:00 PM ET", "0022600256"),
    ("2026-11-18", "HOU@IND", "7:00 PM ET", "0022600259"),
    ("2026-11-18", "PHI@ORL", "7:00 PM ET", "0022600261"),
    ("2026-11-18", "MIL@MIA", "7:00 PM ET", "0022600260"),
    ("2026-11-18", "MEM@CLE", "7:00 PM ET", "0022600258"),
    ("2026-11-18", "CHI@BKN", "7:30 PM ET", "0022600262"),
    ("2026-11-18", "WAS@TOR", "7:30 PM ET", "0022600263"),
    ("2026-11-18", "GSW@DAL", "8:00 PM ET", "0022600267"),
    ("2026-11-18", "ATL@OKC", "8:00 PM ET", "0022600265"),
    ("2026-11-18", "DET@NOP", "8:00 PM ET", "0022600264"),
    ("2026-11-18", "BOS@DEN", "9:30 PM ET", "0022600266"),
    ("2026-11-18", "PHX@SAC", "10:00 PM ET", "0022600269"),
    ("2026-11-18", "UTA@LAL", "10:00 PM ET", "0022600268"),
]


def norm_tip(t):
    if not t:
        return None
    s = str(t).upper().replace("(ET)", "").replace("ET", "").strip()
    # normalise to "7:00 PM" style
    import re
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", s)
    if m:
        h = int(m.group(1))
        return f"{h}:{m.group(2)} {m.group(3)}"
    return s


def main():
    with open(os.path.join(ROOT, STORED), encoding="utf-8") as fh:
        stored = json.load(fh)
    stored_by_id = {r["game_id"]: r for r in stored["rows"]}
    mismatches = []
    checked = 0
    per_day = {"2026-11-16": 0, "2026-11-17": 0, "2026-11-18": 0}
    for date, matchup, tip, gid in FIRST_HAND:
        per_day[date] = per_day.get(date, 0) + 1
        row = stored_by_id.get(gid)
        if row is None:
            mismatches.append({"game_id": gid, "issue": "not present in stored capture"})
            continue
        checked += 1
        stored_matchup = row["matchup"]
        stored_tip = norm_tip(row.get("tip_et_primary") or row.get("tip_et"))
        if stored_matchup != matchup:
            mismatches.append({"game_id": gid, "issue": "matchup",
                               "first_hand": matchup, "stored": stored_matchup})
        if stored_tip != norm_tip(tip):
            mismatches.append({"game_id": gid, "issue": "tip_et",
                               "first_hand": tip, "stored": stored_tip})
        if row["date"] != date:
            mismatches.append({"game_id": gid, "issue": "date",
                               "first_hand": date, "stored": row["date"]})
    out = {
        "captured_by": SESSION,
        "captured_utc": CAPTURED_UTC,
        "source_urls": [
            "https://www.nba.com/games?date=2026-11-16",
            "https://www.nba.com/games?date=2026-11-17",
            "https://www.nba.com/games?date=2026-11-18",
        ],
        "stored_capture": STORED,
        "first_hand_games": len(FIRST_HAND),
        "first_hand_per_day": per_day,
        "rows_compared": checked,
        "mismatches": mismatches,
        "irregularities_confirmed": [
            {"id": "F102", "item": "POR@MIN appears on 11/16 (id 0022600250) and 11/17 (id 0022600254)",
             "status": "CONFIRMED first-hand on both official games pages"},
            {"id": "F101", "item": "GSW@NOP tip time 8:00 PM ET (this read) vs 09:00 PM ET (earlier capture)",
             "status": "CONFIRMED: 11/16 games page prints 8:00 PM ET for 0022600251"},
        ],
        "result": "PASS" if not mismatches else "MISMATCH",
    }
    outdir = os.path.join(ROOT, "verify/2026-11-16-fec7d5ae")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "horizon_recheck.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"horizon recheck: {checked} rows compared, {len(mismatches)} mismatches -> {out['result']}")
    print(f"  per-day first-hand: {per_day}")
    for m in mismatches:
        print("  -", m)
    return 0 if not mismatches else 2


if __name__ == "__main__":
    sys.exit(main())
