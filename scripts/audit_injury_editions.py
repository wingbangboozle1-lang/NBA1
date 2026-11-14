#!/usr/bin/env python3
"""Reproducible audit of the NBA injury-report editions used by this repository.

Inputs (all in data/):
  audit/pdf_0515_transcription.txt  every player row transcribed from the official 05:15 PM ET PDF
                                    (https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf)
                                    as "player|status", read by hand from the PDF text on 2026-11-14.
  injuries_0515.json                the 05:15 PM rows as stored
  injury_report_2026_11_13.json     the 03:00 PM rows as stored (archived edition)
  injury_impact.json                the impact layer output (for the points column)

Outputs:
  audit/injury_0515_verification.json  transcription vs stored rows, both directions
  audit/injury_edition_diff.json       statuses that changed between the 03:00 PM and 05:15 PM editions

Exit code 1 if any transcribed row is missing from the stored data or the stored data has a row the
transcription does not contain (rows with an unprinted team are compared as unattributed rows).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
AUDIT = os.path.join(DATA, "audit")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    pdf = []
    with open(os.path.join(AUDIT, "pdf_0515_transcription.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                player, status = line.split("|")
                pdf.append((player, status))
    stored = load("injuries_0515.json")
    attributed = [(r["player"], r["status"]) for r in stored["rows"] if r.get("player")]
    unattributed = [(r["player"], r["status"]) for r in stored["unattributed_rows"]]
    stored_all = attributed + unattributed
    pdf_set, stored_set = set(pdf), set(stored_all)

    missing_in_data = sorted(pdf_set - stored_set)
    extra_in_data = sorted(stored_set - pdf_set)
    dup_pdf = len(pdf) - len(pdf_set)

    verification = {
        "source_url": stored["source_url"],
        "transcribed_player_rows": len(pdf),
        "stored_player_rows_attributed": len(attributed),
        "stored_player_rows_team_not_printed": len(unattributed),
        "stored_not_yet_submitted_rows": sum(1 for r in stored["rows"] if not r.get("player")),
        "transcribed_rows_missing_from_data": [{"player": p, "status": s} for p, s in missing_in_data],
        "stored_rows_missing_from_transcription": [{"player": p, "status": s} for p, s in extra_in_data],
        "duplicate_transcribed_rows": dup_pdf,
        "result": "PASS" if not missing_in_data and not extra_in_data else "FAIL",
        "note": "Matched on player name and status. A missing team cell is not a mismatch; it is listed as "
                "team_not_printed and never inferred.",
    }

    old = load("injury_report_2026_11_13.json")["rows"]
    new_by_player = {}
    for r in stored["rows"] + stored["unattributed_rows"]:
        if r.get("player"):
            new_by_player[r["player"]] = r
    impact = {p["player"]: p for p in load(os.path.join("derived", "injury_impact.json"))["players"]}
    changes = []
    for r in old:
        p = r.get("player")
        if not p or p not in new_by_player:
            continue
        n = new_by_player[p]
        if r["status"] != n["status"]:
            changes.append({
                "player": p,
                "team": impact.get(p, {}).get("team") or r.get("team"),
                "status_0300pm": r["status"],
                "status_0515pm": n["status"],
                "points_removed": impact.get(p, {}).get("expected_points_removed", 0.0),
                "source_0300pm": r.get("source_url"),
                "source_0515pm": stored["source_url"],
            })
    diff = {
        "title": "Injury statuses that changed between the 03:00 PM and 05:15 PM ET editions, 11/13/2026",
        "source_0300pm": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf",
        "source_0515pm": stored["source_url"],
        "status_changes": changes,
        "count": len(changes),
        "note": "Only players present in both editions with a team are compared. Points removed is the "
                "impact-layer value for the 05:15 PM status (0.0 means no measured production adjustment).",
    }
    os.makedirs(AUDIT, exist_ok=True)
    with open(os.path.join(AUDIT, "injury_0515_verification.json"), "w", encoding="utf-8") as f:
        json.dump(verification, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(AUDIT, "injury_edition_diff.json"), "w", encoding="utf-8") as f:
        json.dump(diff, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"transcribed {len(pdf)} player rows; stored {len(attributed)} attributed + {len(unattributed)} team-not-printed")
    print(f"missing in data: {len(missing_in_data)}  extra in data: {len(extra_in_data)}  -> {verification['result']}")
    print(f"status changes 03:00 PM -> 05:15 PM: {len(changes)}")
    return 0 if verification["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
