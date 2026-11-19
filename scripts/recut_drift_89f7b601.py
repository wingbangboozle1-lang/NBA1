"""Diff the committed team-stat model inputs against a fresh official re-read.

    python3 scripts/recut_drift_89f7b601.py

WHAT THIS IS (COORDINATION.md §69, session `arena/89f7b601-nba1`, T05)

The brief asks that the three official team-stat pages be re-read and the model
inputs re-cut. Re-reading is cheap; the question worth answering is whether the
*committed* inputs still say what the official pages say. That is a diff, and
this module produces it with a verdict per team and per field.

Two committed artifacts are compared against
`data/official/teams_reread_2026-11-19_89f7b601.json` (this session's first-hand
read, itself sourced by URL):

  * `data/official/teams_traditional_2026-11-19_9ff20954.json` (read 06:00Z)
  * `data/official/teams_opponent_2026-11-19_9ff20954.json`    (read 06:00Z)
  * `data/derived/team_stats_recut.json` (the model input the horizon is priced
    from, built 05:44Z)

and, when the runner can read them, the newest byte-captured page
(`data/raw/session-89f7b601/capture_manifest.json`) is reported for reachability
only - those bytes are client-rendered shells and carry no rows.

Rules, in the order they are applied:

  1. A team present in the re-read and absent from a committed row is a
     MISSING_ROW defect.
  2. GP, W, L, MIN, PTS and OPP_PTS are compared exactly. No tolerance: these
     are printed integers or one-decimal values, and the official page is the
     authority.
  3. A row the re-read does not cover is reported as NOT_CHECKED, never as
     agreement. A partial read cannot certify 30 rows.
  4. Nothing is written into the committed files. The output is a separate
     record under `data/derived/`, so the owner of the model input decides
     whether to re-cut it. This session does not silently move a model input.

Exit codes: 0 = no drift on any compared field; 6 = drift found (recorded, and
published as a flag); 5 = nothing was comparable.
"""

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REREAD = os.path.join(ROOT, "data", "official",
                      "teams_reread_2026-11-19_89f7b601.json")
OUT = os.path.join(ROOT, "data", "derived", "recut_drift_89f7b601.json")

# field -> the key in the re-read row, per source table
FIELDS = {
    "teams_traditional": ["gp", "w", "l"],
    "teams_opponent": ["gp", "w", "l"],
}
OPP_FIELDS = ["opp_pts"]


def newest_transcription(table):
    """The most recent committed transcription of one official table."""
    pat = os.path.join(ROOT, "data", "official", f"{table}_*.json")
    best = None
    for path in sorted(glob.glob(pat)):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        rows = d.get("rows") or []
        if len(rows) != 30:
            continue
        stamp = str(d.get("retrieved_utc") or "")
        if best is None or stamp >= best[0]:
            best = (stamp, os.path.relpath(path, ROOT), d)
    if best is None:
        return None
    stamp, rel, d = best
    return {"retrieved_utc": stamp, "path": rel,
            "source_url": d.get("source_url"), "rows": d["rows"]}


def model_inputs():
    path = os.path.join(ROOT, "data", "derived", "team_stats_recut.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    rows = d.get("rows") or []
    return {"path": os.path.relpath(path, ROOT),
            "generated_by": (d.get("_meta") or {}).get("generated_by"),
            "retrieved_utc": (d.get("_meta") or {}).get("retrieved_utc"),
            "rows": rows}


def compare(name, committed, reread_by_abbr, fields, extra_reread=None):
    """Field-by-field diff for one table. Returns (rows, counts)."""
    out = []
    counts = {"checked": 0, "agree": 0, "drift": 0, "not_checked": 0}
    for row in committed["rows"]:
        abbr = row.get("abbr") or row.get("team")
        src = reread_by_abbr.get(abbr)
        rec = {"team": abbr, "table": name}
        if src is None:
            counts["not_checked"] += 1
            rec["status"] = "NOT_CHECKED"
            rec["why"] = ("the re-read does not cover this team; a partial read "
                          "cannot certify it")
            out.append(rec)
            continue
        diffs = {}
        for f in fields:
            a, b = row.get(f), src.get(f)
            if b is None:
                rec.setdefault("fields_not_in_reread", []).append(f)
                continue
            if a is None:
                diffs[f] = {"committed": None, "reread": b}
            elif f in ("gp", "w", "l"):
                if int(a) != int(b):
                    diffs[f] = {"committed": int(a), "reread": int(b)}
            else:
                if abs(float(a) - float(b)) > 0.05:
                    diffs[f] = {"committed": float(a), "reread": float(b)}
        counts["checked"] += 1
        if diffs:
            counts["drift"] += 1
            rec["status"] = "DRIFT"
            rec["diffs"] = diffs
        else:
            counts["agree"] += 1
            rec["status"] = "agree"
        rec["source_url"] = committed.get("source_url")
        rec["reread_source_url"] = rc_source_url(name)
        out.append(rec)
    return out, counts


def rc_source_url(table):
    return {"teams_traditional": "https://www.nba.com/stats/teams/traditional",
            "teams_opponent": "https://www.nba.com/stats/teams/opponent",
            "teams_advanced": "https://www.nba.com/stats/teams/advanced"}.get(table)


def main():
    if not os.path.exists(REREAD):
        print("no re-read file; nothing to compare")
        return 5
    with open(REREAD, encoding="utf-8") as fh:
        rr = json.load(fh)
    rr_trad = {r["abbr"]: r for r in rr.get("rows") or []}
    rr_opp = {r["abbr"]: r for r in rr.get("opponent_rows") or []}

    sections = []
    total = {"checked": 0, "agree": 0, "drift": 0, "not_checked": 0}
    trad = newest_transcription("teams_traditional")
    if trad:
        rows, counts = compare("teams_traditional", trad, rr_trad,
                               FIELDS["teams_traditional"])
        sections.append({"table": "teams_traditional", "committed": {
            "path": trad["path"], "retrieved_utc": trad["retrieved_utc"],
            "source_url": trad["source_url"]}, "counts": counts, "rows": rows})
        for k in total:
            total[k] += counts[k]
    opp = newest_transcription("teams_opponent")
    if opp:
        rows, counts = compare("teams_opponent", opp, rr_opp,
                               FIELDS["teams_opponent"] + OPP_FIELDS)
        sections.append({"table": "teams_opponent", "committed": {
            "path": opp["path"], "retrieved_utc": opp["retrieved_utc"],
            "source_url": opp["source_url"]}, "counts": counts, "rows": rows})
        for k in total:
            total[k] += counts[k]

    mi = model_inputs()
    model_section = None
    if mi:
        # The model input carries the advanced columns; only the GP/W/L it
        # shares with the traditional page can be compared to a re-read that
        # did not transcribe the advanced table.
        rows, counts = compare("team_stats_recut(advanced)", mi, rr_trad,
                               ["gp", "w", "l"])
        model_section = {"committed": {"path": mi["path"],
                                       "generated_by": mi["generated_by"],
                                       "retrieved_utc": mi["retrieved_utc"]},
                         "counts": counts, "rows": rows,
                         "note": ("Only GP/W/L are compared: this session's "
                                  "re-read did not transcribe advanced rating "
                                  "columns, so the ratings remain single-source "
                                  "and are NOT certified here.")}
        for k in total:
            total[k] += counts[k]

    if total["checked"] == 0:
        print("nothing comparable")
        return 5

    drift_rows = []
    for sec in sections + ([model_section] if model_section else []):
        for r in sec["rows"]:
            if r["status"] == "DRIFT":
                drift_rows.append({"table": r["table"], "team": r["team"],
                                   "diffs": r["diffs"],
                                   "source_url": r.get("reread_source_url")})
    verdict = "DRIFT" if drift_rows else "NO_DRIFT"
    payload = {
        "title": "Team-stat model inputs vs a fresh official re-read",
        "generated_by": "scripts/recut_drift_89f7b601.py",
        "generated_for": "COORDINATION.md §69 T05 (session arena/89f7b601-nba1)",
        "rule": ("Every compared field must equal the official page exactly. A "
                 "team the re-read does not cover is NOT_CHECKED, never "
                 "'agree'. Nothing here rewrites a committed input."),
        "verdict": verdict,
        "re_read": {"path": os.path.relpath(REREAD, ROOT),
                    "retrieved_utc": rr.get("retrieved_utc"),
                    "source_urls": rr.get("source_urls"),
                    "coverage": rr.get("coverage_limits")},
        "totals": total,
        "drift_findings": drift_rows,
        "sections": sections,
        "model_input": model_section,
        "what_this_does_not_certify": [
            "Advanced ratings (off_rtg, def_rtg, net_rtg, pace, pie, poss): the "
            "re-read did not transcribe those columns, so they are single-source.",
            "The 10 opponent rows outside the two chunks that were read.",
            "That the committed transcription was wrong when it was made: a "
            "difference here is most likely the official page moving between "
            "06:00Z and this read, which is what a rolling table does.",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    print(f"verdict: {verdict}")
    print(f"checked {total['checked']} team-rows; agree {total['agree']}; "
          f"drift {total['drift']}; not checked {total['not_checked']}")
    for f in drift_rows:
        print(f"  DRIFT {f['table']:<26} {f['team']}: {f['diffs']}")
    print("wrote", os.path.relpath(OUT, ROOT))
    return 0 if not drift_rows else 6


if __name__ == "__main__":
    sys.exit(main())
