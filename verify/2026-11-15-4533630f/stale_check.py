#!/usr/bin/env python3
"""stale_check.py — which published model-input rows are stale at the moment of the
2026-11-15 slate?

The published model-input captures were taken BEFORE the 11/15 games. The official
pages are read AFTER two of the 11/15 games went final. A row whose printed GP
differs between the two reads is a row that played on 11/15, i.e. a row whose
numbers have changed since the model was cut.

This script does not decide policy; it computes the set and writes it out.
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
cap = json.load(open(os.path.join(HERE, "capture_stats.json")))
adv = {r["team"]: r for r in cap["advanced"]}

# teams that played on 2026-11-15 (from capture.json, official rail)
sched = json.load(open(os.path.join(HERE, "capture.json")))["schedule"]
played_1115 = sorted({t for r in sched if r["date"] == "2026-11-15" for t in (r["away"], r["home"])})

ABBR = {"ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GSW","HOU","IND","LAC","LAL",
        "MEM","MIA","MIL","MIN","NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS"}

def abbr_of(team_name):
    # the site's own abbr column is authoritative; reuse it from the published file
    return None

pub = json.load(open(os.path.join(ROOT, "data/official/teams_advanced_2026-11-15.json")))
by_abbr = {r["abbr"]: r for r in pub["rows"]}

rows = []
for ab in played_1115:
    p = by_abbr.get(ab)
    o = adv.get(p["team"]) if p else None
    rows.append({
        "abbr": ab,
        "team": p["team"] if p else None,
        "published_gp": p["gp"] if p else None,
        "official_gp_now": o["gp"] if o else None,
        "changed_since_model_cut": (p and o and p["gp"] != o["gp"]),
        "published_off_rtg": p["off_rtg"] if p else None,
        "official_off_rtg_now": o["off_rtg"] if o else None,
        "published_def_rtg": p["def_rtg"] if p else None,
        "official_def_rtg_now": o["def_rtg"] if o else None,
        "published_pace": p["pace"] if p else None,
        "official_pace_now": o["pace"] if o else None,
        "source_url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
    })

changed = [r for r in rows if r["changed_since_model_cut"]]
out = {
    "title": "Model-input staleness at the 2026-11-15 slate",
    "question": ("The published team ratings were cut from the official pages before the 11/15 tips. "
                 "Which of those rows have already changed because the team played on 11/15?"),
    "published_capture_retrieved_utc": pub.get("retrieved_utc"),
    "this_capture_retrieved_utc": cap.get("retrieved_utc"),
    "teams_playing_2026_11_15": played_1115,
    "rows": rows,
    "changed_count": len(changed),
    "consequence": ("Every one of the 34 published 11/15..11/18 games is modelled from these rows. "
                    "The games whose model inputs already moved are listed above; the site must say so "
                    "on every affected row rather than presenting the line as current."),
}
json.dump(out, open(os.path.join(HERE, "stale_inputs.json"), "w"), indent=1)
print("teams that played 11/15:", len(played_1115))
print("model-input rows already changed:", len(changed), [r["abbr"] for r in changed])
for r in rows:
    if r["changed_since_model_cut"]:
        print(f'  {r["abbr"]}: GP {r["published_gp"]}->{r["official_gp_now"]}, '
              f'OffRtg {r["published_off_rtg"]}->{r["official_off_rtg_now"]}, '
              f'DefRtg {r["published_def_rtg"]}->{r["official_def_rtg_now"]}, '
              f'Pace {r["published_pace"]}->{r["official_pace_now"]}')
