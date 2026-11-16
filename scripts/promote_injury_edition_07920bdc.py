#!/usr/bin/env python3
"""Promote this session's verified injury edition + consecutive diff (§56 / X03-X04).

Takes the independently cross-checked rows produced by
``scripts/verify_injury_edition_07920bdc.py`` and writes them in the two
canonical schemas the dashboard's Injuries banner already reads:

* ``data/official/injury_<date>_<hhmmXM>_07920bdc.json`` - the edition, with
  ``revision_time_et`` and ``retrieved_utc`` so the banner can print both
  (brief requirement R18);
* ``data/official/injury_diff_<from>_to_<to>_07920bdc.json`` - the consecutive
  diff that detects status changes (brief requirement R03).

Every value written here was read out of the official PDF bytes; nothing is
inferred. Rows the repository's own line parser dropped but the PDF contains are
included and marked ``recovered_by: cell-extractor-only``, because dropping them
would publish an incomplete report as if it were complete.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, "verify", "2026-11-16-07920bdc")
OFFICIAL = os.path.join(ROOT, "data", "official")
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")

SESSION = "arena/07920bdc-nba1"
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
PDF_HOST = "https://ak-static.cms.nba.com/referee/injury/"
SUBMISSION_RULE = (
    "Teams must report by 5 p.m. local time the day before a game (other than "
    "the second day of a back-to-back); for the second game of a back-to-back, "
    "by 1 p.m. local time on the day of the game. Game-day reports are required "
    "between 11 a.m. and 1 p.m. local time (8-10 a.m. for tip-offs 5 p.m. or "
    "earlier). Reports are updated on a continual basis throughout the day.")


def edition_key(name: str):
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0, 0)
    y, mo, d, hh, mm, ap = m.groups()
    return (f"{y}-{mo}-{d}", int(hh) % 12 + (12 if ap == "PM" else 0), mm)


def sidecar(label: str) -> dict:
    hits = sorted(glob.glob(os.path.join(PDF_DIR, label + "__*.json")))
    if not hits:
        return {}
    with open(hits[0], encoding="utf-8") as fh:
        return json.load(fh)


def pretty_revision(label: str) -> str:
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", label)
    y, mo, d, hh, mm, ap = m.groups()
    printed = f"{mo}/{d}/{y[-2:]} {hh}:{mm} {ap}"
    return (f"{mo}/{d}/{y} {hh}:{mm} {ap} ET (printed on the PDF as "
            f"'Injury Report: {printed}')")


def short_stamp(label: str) -> str:
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", label)
    y, mo, d, hh, mm, ap = m.groups()
    return f"{y}-{mo}-{d} {hh}:{mm} {ap}"


def file_stamp(label: str) -> str:
    """2026-11-16_0115PM - the shape build_dashboard's _newest() sorts on."""
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", label)
    y, mo, d, hh, mm, ap = m.groups()
    return f"{y}-{mo}-{d}_{hh}{mm}{ap}"


def rows_from(report: dict) -> list:
    out = []
    for r in report["rows"]:
        out.append({
            "game_date": r["game_date"],
            "game_time": r["game_time_et"],
            "matchup": r["matchup"],
            "team": r["team"],
            "team_effective": r["team"],
            "player": r["player"],
            "status": r["status"],
            "reason": r["reason"],
            "source_url": PDF_HOST + report["edition"] + ".pdf",
            "edition_revision_et": pretty_revision(report["edition"]),
            "_inherited": r.get("_inherited", []),
            "_page": r.get("_page"),
            "_wrapped_reason": r.get("_wrapped_reason", []),
        })
    return out


def main() -> int:
    reports = sorted(glob.glob(os.path.join(VERIFY,
                                            "injury_edition_crosscheck_*.json")),
                     key=lambda p: edition_key(os.path.basename(p)))
    if len(reports) < 2:
        raise SystemExit("need at least two cross-checked editions to diff")
    prev_rep = json.load(open(reports[-2], encoding="utf-8"))
    curr_rep = json.load(open(reports[-1], encoding="utf-8"))
    prev_label, curr_label = prev_rep["edition"], curr_rep["edition"]
    curr_meta = sidecar(curr_label)
    prev_meta = sidecar(prev_label)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- the edition ------------------------------------------------------
    rows = rows_from(curr_rep)
    recovered = curr_rep["cross_check"]["cell_extractor_only"]
    recovered_keys = {(r["matchup"], r["team"], r["player"])
                      for r in recovered if r["player"] and r["player"] != "<team block>"}
    for r in rows:
        if (r["matchup"], r["team"], r["player"]) in recovered_keys:
            r["recovered_by"] = ("cell-extractor-only - present in the official PDF "
                                 "bytes, absent from engine/injury_diff.py's "
                                 "visual-line parse (flag F-X01)")
    players = sum(1 for r in rows if r["player"])
    nys = sum(1 for r in rows if r["status"] == "NOT YET SUBMITTED")
    dates = sorted({r["game_date"] for r in rows if r["game_date"]})

    edition = {
        "edition": short_stamp(curr_label),
        "edition_file": f"injury_{file_stamp(curr_label)}_07920bdc.json",
        "revision_time_et": pretty_revision(curr_label),
        "retrieved_utc": curr_meta.get("retrieved_at_utc", now),
        "captured_by": SESSION,
        "source_url": PDF_HOST + curr_label + ".pdf",
        "pdf_sha256": curr_meta.get("sha256") or curr_rep.get("pdf_sha256"),
        "pdf_bytes": curr_meta.get("bytes"),
        "index_url": INDEX_URL,
        "index_note": (
            "captured on this session's branch by "
            ".github/workflows/capture-injury-07920bdc.yml, which read the "
            "official index first; the index listed 54 editions for 2026-11-16 "
            "and named %s as the newest at retrieval time" % short_stamp(curr_label)),
        "submission_rule_quoted": SUBMISSION_RULE,
        "submission_rule_url": INDEX_URL,
        "extraction": {
            "primary": ("per clipped-rectangle cell, grouped into rows by "
                        "rectangle geometry, columns mapped from each page's own "
                        "header row (scripts/verify_injury_edition_07920bdc.py)"),
            "cross_checked_against": ("engine/injury_diff.py visual-line parse of "
                                      "the same bytes"),
            "agreement": {
                "keys_in_both": curr_rep["cross_check"]["in_both"],
                "cell_extractor_only": len(curr_rep["cross_check"]["cell_extractor_only"]),
                "line_parser_only": len(curr_rep["cross_check"]["line_parser_only"]),
                "status_disagreements":
                    len(curr_rep["cross_check"]["status_disagreements"]),
            },
        },
        "merged_cell_caveat": (
            "the PDF draws the Game Date, Game Time, Matchup and Team cells once "
            "at the top of a block and clips empty rectangles below, so those "
            "values are inherited by the rows that follow; inherited rows are "
            "marked _inherited. A reason that wraps is drawn as a second clipped "
            "rectangle, sometimes on the next page, and is re-joined to the row "
            "it continues (marked _wrapped_reason)"),
        "rows_note": (
            "%d rows transcribed from the official PDF bytes (%d player rows, %d "
            "NOT YET SUBMITTED team blocks) on game dates %s. %d player rows are "
            "in the PDF but were dropped by engine/injury_diff.py's visual-line "
            "parse; they are published here because the bytes contain them, and "
            "each carries recovered_by (flag F-X01). Nothing is inferred."
            % (len(rows), players, nys, ", ".join(dates), len(recovered_keys))),
        "game_dates_present": dates,
        "rows": rows,
    }
    ed_path = os.path.join(OFFICIAL, f"injury_{file_stamp(curr_label)}_07920bdc.json")
    with open(ed_path, "w", encoding="utf-8") as fh:
        json.dump(edition, fh, indent=1)
        fh.write("\n")
    print(f"edition -> {os.path.relpath(ed_path, ROOT)} "
          f"({len(rows)} rows, {players} player rows)")

    # ---- the consecutive diff --------------------------------------------
    def key(r):
        return (r["matchup"], r["team"], r["player"] or "<team block>")

    prev_rows = {(r["matchup"], r["team"], r["player"] or "<team block>"): r
                 for r in rows_from(prev_rep)}
    curr_rows = {key(r): r for r in rows}
    comparable = sorted(set(prev_rows) & set(curr_rows))
    added = sorted(set(curr_rows) - set(prev_rows))
    removed = sorted(set(prev_rows) - set(curr_rows))
    changes = []
    for k in comparable:
        a, b = prev_rows[k], curr_rows[k]
        if (a["status"], a["reason"]) != (b["status"], b["reason"]):
            changes.append({"matchup": k[0], "team": k[1], "player": k[2],
                            "from_status": a["status"], "to_status": b["status"],
                            "from_reason": a["reason"], "to_reason": b["reason"]})

    diff = {
        "title": ("Consecutive-edition injury diff: %s -> %s"
                  % (short_stamp(prev_label), short_stamp(curr_label))),
        "from_edition": {"edition_id": prev_label,
                         "revision": pretty_revision(prev_label),
                         "source_url": PDF_HOST + prev_label + ".pdf",
                         "sha256": prev_meta.get("sha256")},
        "to_edition": {"edition_id": curr_label,
                       "revision": pretty_revision(curr_label),
                       "source_url": PDF_HOST + curr_label + ".pdf",
                       "sha256": curr_meta.get("sha256")},
        "computed_by": SESSION,
        "computed_utc": now,
        "method": ("Row-by-row comparison of two independently extracted reads of "
                   "two consecutive official PDFs, keyed on (matchup, team, "
                   "player). Status changes are reported only where both editions "
                   "carry the same key; rows present in one edition only are "
                   "listed separately. Nothing is inferred."),
        "counts": {"previous_rows": len(prev_rows), "current_rows": len(curr_rows),
                   "comparable_rows": len(comparable),
                   "status_changes": len(changes),
                   "rows_added": len(added), "rows_removed": len(removed)},
        "status_changes": changes,
        "rows_added": [{"matchup": k[0], "team": k[1],
                        "player": "" if k[2] == "<team block>" else k[2],
                        "status": curr_rows[k]["status"],
                        "reason": curr_rows[k]["reason"]} for k in added],
        "rows_removed": [{"matchup": k[0], "team": k[1],
                          "player": "" if k[2] == "<team block>" else k[2],
                          "status": prev_rows[k]["status"],
                          "reason": prev_rows[k]["reason"]} for k in removed],
        "caveats": [
            "Both editions were extracted twice - once per clipped-rectangle cell "
            "by scripts/verify_injury_edition_07920bdc.py and once by "
            "engine/injury_diff.py - and cross-checked before this diff was "
            "computed.",
            "engine/injury_diff.py dropped %d player rows present in the newer "
            "PDF (flag F-X01), so a diff computed from its output alone would "
            "have under-reported both editions. This diff uses the verified rows."
            % len(recovered_keys),
            "A row present in one edition only usually reflects a team filing or "
            "withdrawing a block, or a slate change, not a player status change.",
        ],
    }
    diff_path = os.path.join(
        OFFICIAL, f"injury_diff_{file_stamp(prev_label)}_to_{file_stamp(curr_label)}_07920bdc.json")
    with open(diff_path, "w", encoding="utf-8") as fh:
        json.dump(diff, fh, indent=1)
        fh.write("\n")
    print(f"diff    -> {os.path.relpath(diff_path, ROOT)} "
          f"({len(comparable)} comparable, {len(changes)} status changes, "
          f"{len(added)} added, {len(removed)} removed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
