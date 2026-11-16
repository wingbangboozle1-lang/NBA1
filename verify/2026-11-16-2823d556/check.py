#!/usr/bin/env python3
"""Re-run the evidence check in verify/2026-11-16-2823d556/ against the committed files.

    python3 verify/2026-11-16-2823d556/check.py

Exit 0 = every assertion below still holds against the current tree.
Exit 1 = a committed file has changed underneath the published finding, and the
finding must be re-derived before it is repeated anywhere.

This deliberately does NOT re-fetch the official pages: they move by the minute.
It proves the *comparison* still reproduces, i.e. that the committed side of the
comparison has not changed since the finding was published.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
failures: list[str] = []


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def local(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


drift = local("drift.json")
reads = local("live_reads.json")

print("verify/2026-11-16-2823d556 — reproducing the committed side\n")

# 1. The committed team-advanced table still counts the same number of games.
adv = load("data/official/teams_advanced_2026-11-15_2345Z.json")
gp_total = sum(r["gp"] for r in adv["rows"])
check(gp_total / 2 == drift["committed_inputs"]["team_advanced_games_counted"],
      f'team-advanced sum(gp)/2 == {drift["committed_inputs"]["team_advanced_games_counted"]} '
      f'(got {gp_total/2})')
check(adv["retrieved_utc"] == drift["committed_inputs"]["team_advanced_retrieved_utc"],
      f'team-advanced retrieved_utc unchanged ({adv["retrieved_utc"]})')

# 2. Every committed record quoted in the drift table still matches the file.
adv_by = {r["abbr"]: r for r in adv["rows"]}
bad = []
for t in drift["team_record_comparison"]:
    a = adv_by.get(t["abbr"])
    got = f'{a["w"]}-{a["l"]}' if a else None
    if got != t["committed_team_advanced_record"]:
        bad.append((t["abbr"], t["committed_team_advanced_record"], got))
check(not bad, f"all {len(drift['team_record_comparison'])} committed team records still match"
               + ("" if not bad else f" — mismatches: {bad}"))

# 3. The committed schedule capture still holds the same 11/16 rows.
cap = load("data/raw/official_schedule_capture_2026-11-16.json")
cols = cap["cols"]
cap_rows = [dict(zip(cols, r)) for r in cap["rows"] if r[0] == "2026-11-16"]
cap_by = {r["game_id"]: r for r in cap_rows}
missing = [d["game_id"] for d in drift["slate_11_16_row_comparison"]
           if d["game_id"] not in cap_by]
check(not missing, f"all {len(cap_rows)} 11/16 rows still present in the committed capture"
                   + ("" if not missing else f" — missing: {missing}"))
rec_bad = [d["game_id"] for d in drift["slate_11_16_row_comparison"]
           if d["game_id"] in cap_by
           and (cap_by[d["game_id"]]["away_record"] != d["away_record_committed"]
                or cap_by[d["game_id"]]["home_record"] != d["home_record_committed"])]
check(not rec_bad, "committed schedule records still match the drift table"
                   + ("" if not rec_bad else f" — mismatches: {rec_bad}"))

# 4. The published picks still carry the provenance string this finding quotes.
picks = load("data/archive/horizon_picks_2026-11-16.json")
quoted = "2026-11-15T23:38Z..23:52Z"
as_of = picks["_meta"].get("as_of", "")
check(quoted in as_of, f'horizon_picks_2026-11-16.json _meta.as_of still cites "{quoted}"')

# 5. The two picks named in the finding still exist with the quoted numbers.
want = {"0022600245": ("BOS -14.5", 0.8129), "0022600252": ("DEN -5.0", 0.6203)}
by_id = {r["game_id"]: r for r in picks["singles"]}
for gid, (line, prob) in want.items():
    r = by_id.get(gid)
    ok = bool(r) and r["pick"]["pick_line"] == line and abs(r["model_home_win_prob"] - prob) < 1e-9
    check(ok, f"pick {gid} still published as {line} at prob {prob}"
              + ("" if ok else f" — got {r['pick']['pick_line'] if r else None} / "
                               f"{r['model_home_win_prob'] if r else None}"))

# 6. The 11/15 completion state recorded here is internally consistent.
s15 = reads["slate_2026_11_15"]
check(s15["n_final"] + s15["n_in_progress"] == s15["n_games"] == 9,
      f'11/15: {s15["n_final"]} final + {s15["n_in_progress"]} in progress == 9 games')
check(s15["settleable"] is False, "11/15 recorded as NOT settleable at the retrieval time")
check(all((r["away_pts"] is None and r["home_pts"] is None) for r in s15["rows"] if not r["is_final"]),
      "no in-progress game carries a score in the final-score fields")
check(all(r["away_pts"] is not None and r["home_pts"] is not None
          for r in s15["rows"] if r["is_final"]),
      "every FINAL row carries both final scores")

print()
if failures:
    print(f"REPRODUCE FAILED — {len(failures)} assertion(s) no longer hold:")
    for f in failures:
        print("  -", f)
    print("\nThe committed files moved. Re-derive the finding from the official pages before")
    print("repeating it anywhere.")
    sys.exit(1)
print("REPRODUCE OK — every assertion still holds against the current tree.")
print("NOTE: this checks the committed side only. The live official readings are a point-in-time")
print("      record from " + reads["retrieved_utc"] + " and are not re-fetched here.")
sys.exit(0)
