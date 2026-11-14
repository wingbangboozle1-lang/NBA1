#!/usr/bin/env python3
"""X02–X04 — verify the 2026-11-13 official finals captured in capture.json.

Checks, per game (nothing is inferred; a failed check is reported, never fixed):
  C1  schedule-card final score == game-page final score (where the game page returned a linescore)
  C2  linescore quarter sums == the final score (arithmetic)
  C3  schedule status is 'Final' or 'Final/OT'
  C4  game_id ends with the number in the game_url, and away/home abbreviations match the URL slug
  C5  the row is absent from the committed snapshot data/raw/games_completed.json (promotion candidate)

Writes:
  data/verified/finals_2026-11-13.json   (one row per game; sources on every row)
  audit/finals_2026-11-13/report.json    (every check, every result)
Exit code 0 = all checks pass; 1 = at least one check failed (the failure is printed, not hidden).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
cap = json.load(open(os.path.join(HERE, "capture.json")))
snap = json.load(open(os.path.join(ROOT, "data", "raw", "games_completed.json")))

snap_ids = {r[7] for r in snap["rows"]}
checks = []
out_rows = []
failed = 0


def check(game, name, ok, detail):
    global failed
    checks.append({"game_id": game, "check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        failed += 1


for g in cap["games"]:
    gid = g["game_id"]
    sc = g["schedule_card"]
    gp = g["game_page"]
    slug = g["game_url"].rsplit("/", 1)[-1]  # e.g. nyk-vs-ind-0022600034

    # C3 status label
    check(gid, "C3 status label", sc["status"] in ("Final", "Final/OT"), sc["status"])

    # C4 id + slug agree with the team abbreviations
    slug_teams = slug.split("-0022")[0]  # e.g. nyk-vs-ind
    a_slug, h_slug = [t.lower() for t in slug_teams.split("-vs-")]
    check(gid, "C4 url slug matches away/home and id",
          a_slug == g["away"].lower() and h_slug == g["home"].lower() and slug.endswith(gid),
          f"{slug} vs {g['away']}@{g['home']}")

    # C2 linescore arithmetic, and C1 schedule vs game page
    if gp["linescore_away"] is not None:
        sa, sh = sum(gp["linescore_away"]), sum(gp["linescore_home"])
        check(gid, "C2 linescore sums to final",
              sa == gp["final_away"] and sh == gp["final_home"],
              f"away {gp['linescore_away']}={sa} (page final {gp['final_away']}); "
              f"home {gp['linescore_home']}={sh} (page final {gp['final_home']})")
        check(gid, "C1 schedule card == game page",
              sc["away_pts"] == gp["final_away"] and sc["home_pts"] == gp["final_home"],
              f"schedule {sc['away_pts']}-{sc['home_pts']} vs game page {gp['final_away']}-{gp['final_home']}")
        ot = 0 if len(gp["linescore_away"]) == 4 else len(gp["linescore_away"]) - 4
        check_method = "two official pages agree (schedule card + game-page linescore)"
        verified = True
    else:
        ot = None if sc["status"] == "Final/OT" else 0
        check_method = "one official page (schedule card); game-page linescore not returned by the fetch tool"
        verified = "single-source"

    # C5 not yet in the committed snapshot
    check(gid, "C5 absent from committed snapshot", gid not in snap_ids,
          "absent — promotion candidate" if gid not in snap_ids else "already committed")

    out_rows.append({
        "date": g["date"],
        "game_id": gid,
        "away": g["away"],
        "away_pts": sc["away_pts"],
        "home": g["home"],
        "home_pts": sc["home_pts"],
        "status_label": sc["status"],
        "ot": ot,
        "venue": g["venue"],
        "verification": check_method,
        "verified": verified,
        "sources": [cap["schedule_url"], g["game_url"]],
        "snapshot_format_note": "columns match data/raw/games_completed.json except 'neutral' (not printed on the official card, so not written)",
    })

data = {
    "file": "data/verified/finals_2026-11-13.json",
    "purpose": "Row-level verified finals for 2026-11-13 (closes the 'not final' gap in the committed snapshot). Promotion into data/raw/games_completed.json and settlement is the integration session's job.",
    "captured_by": "arena/cfb25ff0-nba1",
    "rows": out_rows,
    "all_checks_passed": failed == 0,
    "checks_run": len(checks),
    "checks_failed": failed,
}
os.makedirs(os.path.join(ROOT, "data", "verified"), exist_ok=True)
with open(os.path.join(ROOT, "data", "verified", "finals_2026-11-13.json"), "w") as fh:
    json.dump(data, fh, indent=1)
    fh.write("\n")

report = {"checks": checks, "summary": {"games": len(out_rows), "checks_run": len(checks), "failed": failed}}
with open(os.path.join(HERE, "report.json"), "w") as fh:
    json.dump(report, fh, indent=1)
    fh.write("\n")

for c in checks:
    print(("PASS " if c["ok"] else "FAIL ") + c["game_id"] + " " + c["check"] + " :: " + c["detail"])
print(f"\n{len(out_rows)} games, {len(checks)} checks, {failed} failed")
sys.exit(0 if failed == 0 else 1)
