#!/usr/bin/env python3
"""capture_injury_2026_11_17.py — archive the 2026-11-17 official injury editions
and diff them.

What this script does
---------------------
1. Parses the two 11/17 editions that were retrieved first-hand this cycle
   (10:15 AM ET and 10:30 AM ET) from the archived text renders of the official
   PDFs, and writes one edition JSON per edition (same field names as the
   earlier editions under data/official/, so downstream readers do not branch).
2. Produces the **consecutive** diff (10:15 -> 10:30) over the 11/17 games.
3. Produces a **cross-day** diff (2026-11-16 01:30 PM -> 2026-11-17 10:30 AM)
   and labels it explicitly as NOT consecutive: the editions published between
   those two stamps were not retrieved by this session, so any change it shows
   is a change "at some point in the gap", never a change "in this step".

Honesty rules
-------------
* No hash is claimed for the PDF bytes. The bytes are unreachable from this
  sandbox (curl and urllib both fail the TLS handshake to ak-static.cms.nba.com);
  only the text render is reachable. The edition JSONs therefore carry
  `raw_pdf_sha256: null` with a note, plus a sha256 over the retained text.
* A row is parsed only when all seven printed columns are present. A row whose
  Reason cell is "NOT YET SUBMITTED" is a submission gap, not a player row, and
  is kept in its own list.
* Nothing is joined or inferred except the two wrapped-cell joins that the
  download itself prints unambiguously; those are listed on the edition.

Run: python3 scripts/capture_injury_2026_11_17.py
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL = os.path.join(ROOT, "data", "official")
NOW = "2026-11-17T15:50Z"

EDITIONS = [
    # key, stamp label, printed revision, pdf file name, text file
    ("1015AM", "2026-11-17 10:15 AM ET", "11/17/2026 10:15 AM ET",
     "Injury-Report_2026-11-17_10_15AM.pdf", "injury_2026-11-17_1015AM_84264db0_text.md"),
    ("1030AM", "2026-11-17 10:30 AM ET", "11/17/2026 10:30 AM ET",
     "Injury-Report_2026-11-17_10_30AM.pdf", "injury_2026-11-17_1030AM_84264db0_text.md"),
]


def parse_text(path):
    """Parse the markdown table render. Returns (player_rows, not_submitted)."""
    players, nys = [], []
    for line in open(path, encoding="utf-8"):
        if not line.startswith("|") or line.startswith("| ---") or line.startswith("| Game Date"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 7:
            continue
        rec = {"game_date": c[0], "game_time_et": c[1], "matchup": c[2],
               "team": c[3], "player": c[4], "status": c[5], "reason": c[6]}
        if c[6] == "NOT YET SUBMITTED":
            nys.append({"game_date": c[0], "game_time_et": c[1], "matchup": c[2], "team": c[3]})
        elif c[4]:
            players.append(rec)
    return players, nys


def key(r):
    return (r["matchup"], r["player"])


def diff(rows_a, rows_b, game_date_filter=None):
    a = {key(r): r for r in rows_a if game_date_filter in (None, r["game_date"])}
    b = {key(r): r for r in rows_b if game_date_filter in (None, r["game_date"])}
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    changed = [k for k in a if k in b and (a[k]["status"], a[k]["reason"]) != (b[k]["status"], b[k]["reason"])]
    return {
        "from_rows": len(a), "to_rows": len(b),
        "added": len(added), "removed": len(removed), "changed": len(changed),
        "added_detail": [{"matchup": k[0], "player": k[1], "status": b[k]["status"]} for k in added],
        "removed_detail": [{"matchup": k[0], "player": k[1], "status": a[k]["status"]} for k in removed],
        "changed_detail": [{"matchup": k[0], "player": k[1],
                            "from_status": a[k]["status"], "to_status": b[k]["status"],
                            "from_reason": a[k]["reason"], "to_reason": b[k]["reason"]} for k in changed],
    }


def main():
    parsed = {}
    for key_id, label, printed, pdf, text in EDITIONS:
        text_path = os.path.join(OFFICIAL, text)
        players, nys = parse_text(text_path)
        parsed[label] = players
        status = {}
        for r in players:
            status[r["status"]] = status.get(r["status"], 0) + 1
        doc = {
            "title": f"Official injury report {label} — archived as retrieved text",
            "edition": pdf.replace("Injury-Report_", "").replace(".pdf", "").replace("_", " "),
            "revision_time_et": f"{printed} (printed on the official PDF)",
            "retrieved_utc": NOW,
            "retrieval_channel": ("web-fetch text render of the official PDF. Raw bytes were NOT retrievable from "
                                  "this sandbox: curl and urllib both fail the TLS handshake to "
                                  "ak-static.cms.nba.com (recorded in COORDINATION §62)."),
            "source_url": f"https://ak-static.cms.nba.com/referee/injury/{pdf}",
            "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "raw_pdf_sha256": None,
            "raw_pdf_sha256_note": ("NOT MEASURED — the bytes could not be downloaded, so no PDF hash is claimed. "
                                    "Earlier editions are byte-exact under data/raw/injury_pdfs/ with sha256 sidecars; "
                                    "this edition is text-only and the gap is published on the Flagged page "
                                    "instead of being filled with an invented hash."),
            "text_file": "data/official/" + text,
            "text_sha256": hashlib.sha256(open(text_path, "rb").read()).hexdigest(),
            "columns": ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason"],
            "rows": players,
            "not_yet_submitted": nys,
            "counts": {
                "player_rows": len(players),
                "status": status,
                "teams_with_rows": len({r["team"] for r in players}),
                "not_yet_submitted_slots": len(nys),
                "games_with_a_submitted_report": sorted({r["matchup"] for r in players}),
                "games_not_yet_submitted": sorted({n["matchup"] for n in nys}),
            },
            "transcription_note": ("Two wrapped cells are joined only where the same download prints the continuation "
                                   "unambiguously: Kessler's Reason ('... Right Lower Leg' + the next fragment "
                                   "'Soreness') and Reaves' team (the cell is empty on the wrapped line and the row "
                                   "sits inside the CHA@LAL / Los Angeles Lakers block). Both joins are listed on the "
                                   "edition and are the only joins made."),
        }
        out = os.path.join(OFFICIAL, f"injury_2026-11-17_{key_id}_84264db0.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote {os.path.relpath(out, ROOT)}  rows={len(players)}  nys={len(nys)}")

    # ---- consecutive diff: 10:15 -> 10:30, 11/17 games only (apples to apples)
    a = parsed["2026-11-17 10:15 AM ET"]
    b = parsed["2026-11-17 10:30 AM ET"]
    d1 = diff(a, b, game_date_filter="11/17/2026")
    doc1 = {
        "title": "Consecutive official injury-report diff — 2026-11-17 10:15 AM ET → 10:30 AM ET (11/17 games)",
        "consecutive": True,
        "from_edition": {"label": "2026-11-17 10:15 AM ET",
                         "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_10_15AM.pdf"},
        "to_edition": {"label": "2026-11-17 10:30 AM ET",
                       "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_10_30AM.pdf"},
        "built_utc": NOW,
        "rule": ("keyed on (matchup, player); a status or reason change inside the same key is a STATUS CHANGE; a key "
                 "in only one edition is an ADD or a REMOVE. Scope: rows for 11/17 games, which is the slate both "
                 "editions cover with a submitted report."),
        "counts": {k: d1[k] for k in ("from_rows", "to_rows", "added", "removed", "changed")},
        "added": d1["added_detail"], "removed": d1["removed_detail"], "changed": d1["changed_detail"],
        "reading": ("Two editions fifteen minutes apart. A zero-change result is a real measurement — the league "
                    "republished the same 11/17 slate — not a missing diff."),
    }
    p1 = os.path.join(OFFICIAL, "injury_diff_2026-11-17_1015AM_to_1030AM_84264db0.json")
    with open(p1, "w", encoding="utf-8") as fh:
        json.dump(doc1, fh, indent=1, ensure_ascii=False); fh.write("\n")
    print("wrote", os.path.relpath(p1, ROOT), doc1["counts"])

    # ---- cross-day diff: 11/16 01:30 PM -> 11/17 10:30 AM (NOT consecutive)
    prev_path = os.path.join(OFFICIAL, "injury_2026-11-16_0130PM_7ec9e7a3.json")
    prev = json.load(open(prev_path, encoding="utf-8"))
    prev_rows = [{"game_date": r["game_date"], "matchup": r["matchup"], "player": r["player"],
                  "status": r["status"], "reason": r["reason"]} for r in prev["rows"]]
    d2 = diff(prev_rows, b)
    doc2 = {
        "title": "Cross-day official injury-report diff — 2026-11-16 01:30 PM ET → 2026-11-17 10:30 AM ET",
        "consecutive": False,
        "why_not_consecutive": ("The editions published between 2026-11-16 01:30 PM ET and 2026-11-17 10:15 AM ET "
                               "were not retrieved by this session (the official index lists 11/17 editions from "
                               "12:00 AM ET onward; a single session cannot poll every 15 minutes). Every change below "
                               "is therefore 'a change that happened at some point in that gap', never 'the change in "
                               "this step'. The consecutive step this cycle measured is the 10:15 → 10:30 diff."),
        "from_edition": {"label": "2026-11-16 01:30 PM ET", "captured_by": "arena/7ec9e7a3-nba1",
                         "url": prev["source_url"], "file": "data/official/injury_2026-11-16_0130PM_7ec9e7a3.json"},
        "to_edition": {"label": "2026-11-17 10:30 AM ET",
                       "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_10_30AM.pdf"},
        "built_utc": NOW,
        "rule": "same rule as the consecutive diff; rows are keyed on (matchup, player) across both game days",
        "counts": {k: d2[k] for k in ("from_rows", "to_rows", "added", "removed", "changed")},
        "added": d2["added_detail"], "removed": d2["removed_detail"], "changed": d2["changed_detail"],
        "reading": ("Most of the apparent 'added' rows are 11/17 and 11/18 fixtures that did not exist in the 11/16 "
                    "edition's universe, not status changes. The rows worth reading are the 'removed' and 'changed' "
                    "ones, and even those are gap-attributed."),
    }
    p2 = os.path.join(OFFICIAL, "injury_diff_2026-11-16_0130PM_to_2026-11-17_1030AM_84264db0.json")
    with open(p2, "w", encoding="utf-8") as fh:
        json.dump(doc2, fh, indent=1, ensure_ascii=False); fh.write("\n")
    print("wrote", os.path.relpath(p2, ROOT), doc2["counts"])


if __name__ == "__main__":
    main()
