#!/usr/bin/env python3
"""X03: compare the stored team advanced tables with the official NBA.com values in
official_team_advanced.json. Read-only. Writes audit/stats/x03_report.json.

Run from the repository root:  python3 audit/stats/check_team_advanced.py
"""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)

OFF = load("audit/stats/official_team_advanced.json")
COLS = OFF["_meta"]["columns"]          # team, gp, w, l, min, off_rtg, ... poss
NUM_COLS = COLS[1:]

def off_index(rows):
    return {r[0]: dict(zip(COLS, r)) for r in rows}

# Stored file 1: data/teams_advanced_2026_27.json (dict rows keyed by stored names)
stored1 = load("data/teams_advanced_2026_27.json")["rows"]
# Stored file 2: data/raw/team_advanced.json (windows: season_to_date, train_...)
raw = load("data/raw/team_advanced.json")
raw_cols = raw["cols"]        # ortg, drtg, netr ... naming differs from the display names
RAW_TO_OFF = {"ortg": "off_rtg", "drtg": "def_rtg", "netr": "net_rtg"}

def name_of_abbr_map(rows):
    return {r["abbr"]: r["team"] for r in rows}

report = {"checked_utc": "2026-11-14", "tables": {}, "mismatches": []}

def compare(table_id, stored_rows_by_team, off_by_team, is_raw_style=False):
    n_ok = 0
    n_cells = 0
    for team, off in off_by_team.items():
        st = stored_rows_by_team.get(team)
        if st is None:
            report["mismatches"].append({"table": table_id, "team": team, "field": "row", "stored": None, "official": "present"})
            continue
        row_ok = True
        for c in NUM_COLS:
            n_cells += 1
            stored_key = c
            if is_raw_style:
                inv = {v: k for k, v in RAW_TO_OFF.items()}
                stored_key = inv.get(c, c)
            sv = st.get(stored_key)
            ov = off[c]
            if sv is None or abs(float(sv) - float(ov)) > 1e-9:
                row_ok = False
                report["mismatches"].append({"table": table_id, "team": team, "field": c, "stored": sv, "official": ov})
        n_ok += row_ok
    stored_teams = set(stored_rows_by_team)
    extra = sorted(stored_teams - set(off_by_team))
    report["tables"][table_id] = {"official_rows": len(off_by_team), "stored_rows": len(stored_rows_by_team),
                                  "rows_matching_all_numeric_fields": n_ok, "cells_compared": n_cells,
                                  "stored_teams_not_on_official_table": extra}

# 1) season to date, file 1 (dict rows)
stored1_by_team = {r["team"]: r for r in stored1}
compare("data/teams_advanced_2026_27.json", stored1_by_team, off_index(OFF["season_to_date"]))

# 2) raw windows: convert raw rows (positional with raw_cols) to dicts keyed by raw names
def raw_rows_to_dicts(rows):
    out = {}
    for r in rows:
        d = dict(zip(raw_cols, r))
        out[d["team"]] = d
    return out

for w in raw["windows"]:
    wid = w["window_id"]
    off_key = "season_to_date" if wid == "season_to_date" else wid
    if off_key not in OFF:
        report["tables"][wid] = {"skipped": "no official transcription for this window"}
        continue
    rows = raw_rows_to_dicts(w["rows"])
    # map raw names to official display names
    compare(f"data/raw/team_advanced.json:{wid}", rows, off_index(OFF[off_key]), is_raw_style=True)

report["mismatch_count"] = len(report["mismatches"])
with open(os.path.join(ROOT, "audit/stats/x03_report.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print(json.dumps(report["tables"], indent=1))
print("mismatches:", report["mismatch_count"])
for m in report["mismatches"][:60]:
    print("  ", m)
