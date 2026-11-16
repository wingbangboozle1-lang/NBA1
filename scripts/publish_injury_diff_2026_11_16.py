#!/usr/bin/env python3
"""publish_injury_diff_2026_11_16.py — COORDINATION §50 C05 (follow-on).

The canonical consecutive-edition diff produced by this session lives at

    data/injury_reports/2026-11-16_0930AM/diff_vs_2026-11-15_0900PM.json

but the shared dashboard builder resolves the diff it prints on the Injuries
page with `_newest("injury_diff_*.json")`, which globs **data/official/**.  There
is no diff file for the 11/16 09:30 AM edition there, so `_newest` falls back to
the newest of the two 11/15 files and the page reports a diff against the
superseded 2026-11-15_0615AM edition — as "16 status changes, 0 comparable rows",
which is not the comparison this session computed.

This script publishes the SAME diff, unaltered in substance, into the place and
the schema that builder reads:

    data/official/injury_diff_2026-11-16_0930AM_to_2026-11-15_0900PM.json

with the `counts` block (comparable_player_rows / status_changes) and the
string `from_edition` that `scripts/build_dashboard.py` interpolates.  The
canonical file stays the record; this one is a rendered view of it, and it says
so in its own provenance fields.

Nothing is recomputed: every count is copied from the canonical diff, and the
script refuses to write if the numbers it copies do not add up.

Run:  python3 scripts/publish_injury_diff_2026_11_16.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION = "arena/acc2fd9e-nba1"

CANON = os.path.join(ROOT, "data", "injury_reports", "2026-11-16_0930AM",
                     "diff_vs_2026-11-15_0900PM.json")
OUT = os.path.join(ROOT, "data", "official",
                   "injury_diff_2026-11-16_0930AM_to_2026-11-15_0900PM.json")


def main():
    if not os.path.exists(CANON):
        sys.exit("canonical diff missing: %s" % os.path.relpath(CANON, ROOT))
    with open(CANON, encoding="utf-8") as fh:
        d = json.load(fh)

    prev = d["previous_edition"]
    cur = d["current_edition"]
    win = d["comparison_window"]
    n_chg = d["status_changes_count"]
    n_add = d["added_count"]
    n_rem = d["removed_count"]
    n_same = d["unchanged_rows"]
    n_nc = d["not_comparable_count"]

    # --- gate: the copied counts must be internally consistent ---------------
    problems = []
    if n_chg != len(d["status_changes"]):
        problems.append("status_changes_count %d != len(status_changes) %d"
                        % (n_chg, len(d["status_changes"])))
    if n_add != len(d["added"]) or n_rem != len(d["removed"]):
        problems.append("added/removed counts disagree with the lists")
    if n_nc != len(d["not_comparable"]):
        problems.append("not_comparable_count disagrees with the list")
    if n_same + n_chg + n_nc <= 0:
        problems.append("the comparison produced no rows at all")
    if not win.get("game_dates_compared"):
        problems.append("the canonical diff compared no shared game date")
    if problems:
        print("REFUSED to publish — the canonical diff does not reconcile:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    doc = {
        "title": ("Consecutive-edition injury diff: %s -> %s"
                  % (prev["edition"], cur["edition"])),
        "from_edition": "%s (file %s)" % (prev["edition"], prev["file"]),
        "to_edition": "%s (file %s)" % (cur["edition"], cur["file"]),
        "computed_by": SESSION,
        "computed_utc": d["diffed_at_utc"],
        "canonical_file": os.path.relpath(CANON, ROOT),
        "rendered_from": ("this file is a rendered view of the canonical diff named "
                          "above, in the schema scripts/build_dashboard.py reads; the "
                          "canonical file is the record and nothing here is recomputed"),
        "method": d["rule"],
        "counts": {
            "comparable_player_rows": n_same + n_chg + n_nc,
            "status_changes": n_chg,
            "unchanged": n_same,
            "not_comparable": n_nc,
        },
        "status_changes": d["status_changes"],
        "rows_added": d["added"],
        "rows_removed": d["removed"],
        "not_comparable": d["not_comparable"],
        "team_blocks_filed_since": d["not_yet_submitted_resolved"],
        "team_blocks_newly_not_submitted": d["not_yet_submitted_new"],
        "comparison_window": win,
        "caveats": [
            "The report is rolling: it lists the next two game dates. Rows are "
            "compared only on game dates BOTH editions print (%s); dates only one "
            "edition covers are counted separately and are not changes."
            % ", ".join(win["game_dates_compared"]),
            "A row whose status the PDF text layer lost is reported under "
            "not_comparable, never as a status change (%d such row here)." % n_nc,
            "Six Golden State rows and one more lost a status or reason cell in the "
            "PDF text layer; those cells are null in the edition file, never filled in.",
        ],
        "source_urls": {"previous": prev["source_url"], "current": cur["source_url"]},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    print("  %s -> %s" % (prev["edition"], cur["edition"]))
    print("  comparable %d | status changes %d | unchanged %d | not comparable %d | "
          "added %d | removed %d"
          % (doc["counts"]["comparable_player_rows"], n_chg, n_same, n_nc, n_add, n_rem))
    print("  window: compared %s | only previous %s | only current %s"
          % (", ".join(win["game_dates_compared"]),
             ", ".join(win["game_dates_only_in_previous"]) or "none",
             ", ".join(win["game_dates_only_in_current"]) or "none"))


if __name__ == "__main__":
    main()
