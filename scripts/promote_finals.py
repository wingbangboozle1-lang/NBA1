#!/usr/bin/env python3
"""Promote verified official finals into a committed snapshot.

    python3 scripts/promote_finals.py --date 2026-11-13

Rule (COORDINATION.md ground rules; never break it):
a row is promoted ONLY after two independent reads of the official page agree
on every promoted value, and every promoted row keeps its official source URL.
If the two runs disagree anywhere, NOTHING is promoted and the disagreement is
printed.

Inputs:
  data/raw/_capture_results_<date>.json             second (latest) fetch
  data/audit/finals_<date>_verification.json        first fetch, recorded rows

Output:
  data/raw/games_completed_<date>.json              same cols as
                                                    data/raw/games_completed.json
                                                    plus per-row provenance

This script performs no inference. It compares two captures byte-for-byte on
the promoted fields and copies them.
"""

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
AUDIT = os.path.join(ROOT, "data", "audit")

FIELDS = ("game_id", "away", "home", "away_pts", "home_pts", "ot")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="slate date, e.g. 2026-11-13")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    d = args.date

    cap_path = os.path.join(RAW, f"_capture_results_{d}.json")
    ev_path = os.path.join(AUDIT, f"finals_{d.replace('-', '_')}_verification.json")
    for p in (cap_path, ev_path):
        if not os.path.exists(p):
            sys.exit(f"missing input: {p}")

    cap = load(cap_path)
    ev = load(ev_path)
    run1 = ev["run_1"]
    run2_rows = cap["parse"]["finals_rows"]

    # run 2 must be a later capture than run 1 (two distinct reads)
    if cap["captured_at_utc"] == run1["captured_at_utc"]:
        sys.exit("run 2 capture is the same capture as run 1 - fetch again first")

    def key(rows):
        return {r["game_id"]: tuple(r[f] for f in FIELDS) for r in rows}

    k1, k2 = key(run1["finals_rows"]), key(run2_rows)
    if k1 != k2:
        print("DISAGREEMENT between the two official reads - nothing promoted.")
        for gid in sorted(set(k1) | set(k2)):
            if k1.get(gid) != k2.get(gid):
                print(f"  {gid}: run1={k1.get(gid)} run2={k2.get(gid)}")
        sys.exit(1)
    if cap["parse"]["unparsed"] or run1["unparsed"]:
        sys.exit("unparsed rows present in one of the runs - nothing promoted")
    if not k1:
        sys.exit("no finals rows captured - nothing to promote")

    src = cap["source_url"]
    rows = []
    for gid in sorted(k1):
        away, home, a_pts, h_pts, ot = k1[gid][1:]
        rows.append([d, away, a_pts, home, h_pts, ot, 0, gid, f"results_{d}"])

    out = {
        "captured_at_utc": cap["captured_at_utc"],
        "promoted_at_utc": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_url": src,
        "note": (
            f"Final scores for {d} transcribed from the official NBA.com Games & Scores "
            f"page ({src}), read twice independently and promoted only because both reads "
            f"agree on every field. Run 1: {run1['workflow_run']} ({run1['captured_at_utc']}, "
            f"page sha256 {run1['page_sha256'][:16]}...). Run 2: {cap['captured_at_utc']} "
            f"(page sha256 {cap['page_sha256'][:16]}...). On NBA.com the first team listed "
            "is the AWAY team and the second is the HOME team. neutral = 1 means a "
            "neutral-site game (none known on this slate). Evidence: "
            f"data/audit/finals_{d.replace('-', '_')}_verification.json."
        ),
        "cols": ["date", "away", "away_pts", "home", "home_pts", "ot",
                 "neutral", "game_id", "source_id"],
        "rows": rows,
    }

    if args.check_only:
        print(f"agreement OK: {len(rows)} finals rows match across both reads")
        return

    dst = os.path.join(RAW, f"games_completed_{d}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"promoted {len(rows)} finals -> {os.path.relpath(dst, ROOT)}")

    # update the evidence file with the promotion record
    ev["run_2"] = {
        "captured_at_utc": cap["captured_at_utc"],
        "page_sha256": cap["page_sha256"],
        "finals_rows": run2_rows,
        "agrees_with_run_1": True,
    }
    ev["promotion"] = {
        "promoted_at_utc": out["promoted_at_utc"],
        "snapshot": f"data/raw/games_completed_{d}.json",
        "rows": len(rows),
    }
    with open(ev_path, "w", encoding="utf-8") as fh:
        json.dump(ev, fh, indent=1)
    print("evidence updated")


if __name__ == "__main__":
    main()
