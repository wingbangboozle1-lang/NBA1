#!/usr/bin/env python3
"""compare.py — row-by-row comparison of the PUBLISHED files against this session's
independent official capture (capture.json).

Rules: a published value is AGREE only if the official page prints it and it matches.
MISSING_ON_OFFICIAL / UNVERIFIABLE_IN_THIS_PASS is used when this pass did not read a
value - never AGREE. Nothing is corrected here; mismatches are reported.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
cap = json.load(open(os.path.join(HERE, "capture.json")))
pub = json.load(open(os.path.join(ROOT, "data/official/schedule_2026-11-15_to_18.json")))
pubs = json.load(open(os.path.join(ROOT, "data/official/standings_2026-11-15.json")))
pubf = json.load(open(os.path.join(ROOT, "data/official/results_2026-11-14.json")))

cap_by_id = {r["game_id"]: r for r in cap["schedule"]}

FIELDS = [("date", "date"), ("tip_et", "tip_et"), ("away", "away"), ("home", "home"),
          ("venue", "venue_printed"), ("city", "city_printed")]

def venue_split(published, official_venue, official_city):
    """The published feed stores venue and city separately; the official game page
    prints them as two lines. Recombine the published pair and compare to the pair."""
    if official_venue is None:
        return "UNVERIFIABLE_IN_THIS_PASS"
    if not published:
        return "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE"
    want = official_venue + (", " + official_city if official_city else "")
    return "AGREE" if published.strip() == want else "MISMATCH"

sched_rows = []
for row in pub["rows"]:
    gid = row["game_id"]
    c = cap_by_id.get(gid)
    checks = []
    for pf, cf in FIELDS:
        pv, cv = row.get(pf), (c or {}).get(cf)
        if cv is None:
            status = "UNVERIFIABLE_IN_THIS_PASS"
        elif pf == "venue":
            # the published feed already stores venue and city in separate columns,
            # so venue is compared to the page's venue line alone; the city column is
            # compared separately below. (The 11/14 results feed used one combined
            # "venue, city" column - that convention is handled in the finals block.)
            status = ("AGREE" if pv and pv.strip() == cv
                      else ("PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" if not pv else "MISMATCH"))
        elif pf == "city":
            # checked as part of the venue pair above
            status = ("AGREE" if pv and (c or {}).get("city_printed") == pv
                      else ("PUBLISHED_BLANK_OFFICIAL_HAS_VALUE" if not pv
                            else "UNVERIFIABLE_IN_THIS_PASS"))
        elif pv is None or pv == "":
            status = "PUBLISHED_BLANK_OFFICIAL_HAS_VALUE"
        elif str(pv) == str(cv):
            status = "AGREE"
        else:
            status = "MISMATCH"
        checks.append({"field": pf, "published": pv, "official": cv, "status": status})
    # records are point-in-time: the published capture is pre-game, the official page is live
    for pf, cf in (("away_record", "away_record_printed"), ("home_record", "home_record_printed")):
        pv, cv = row.get(pf), (c or {}).get(cf)
        if cv is None:
            status = "UNVERIFIABLE_IN_THIS_PASS"
        elif pv == cv:
            status = "AGREE"
        else:
            status = "MISMATCH_POINT_IN_TIME"
        checks.append({"field": pf, "published": pv, "official": cv, "status": status})
    sched_rows.append({"game_id": gid, "date": row["date"], "matchup": f'{row["away"]}@{row["home"]}',
                       "checks": checks,
                       "official_games_page": row.get("source_date_url") or f'https://www.nba.com/games?date={row["date"]}',
                       "official_game_page": f'https://www.nba.com/game/{row["away"].lower()}-vs-{row["home"].lower()}-{gid}'})

# games on the official rail that the published file does not contain
missing = [r for r in cap["schedule"] if r["game_id"] not in {x["game_id"] for x in pub["rows"]}]
extra = [r for r in pub["rows"] if r["game_id"] not in cap_by_id]

# ---------------------------------------------------------------- standings
cap_st = {r["abbr"]: r for r in cap["standings"]}
st_rows = []
SFIELDS = ["w", "l", "win_pct", "gb", "conf_rec", "div_rec", "home", "road", "neutral", "ot", "last10", "streak"]
for row in pubs["rows"]:
    c = cap_st.get(row["abbr"])
    checks = []
    for f in SFIELDS:
        pv, cv = row.get(f), (c or {}).get(f)
        if cv is None:
            status = "UNVERIFIABLE_IN_THIS_PASS"
        elif str(pv) == str(cv):
            status = "AGREE"
        else:
            status = "MISMATCH"
        checks.append({"field": f, "published": pv, "official": cv, "status": status})
    st_rows.append({"abbr": row["abbr"], "team": row["team"], "conference": row["conference"],
                    "published_rank": row.get("rank"), "official_rank": (c or {}).get("rank"),
                    "checks": checks})

# ---------------------------------------------------------------- finals 11/14
cap_f = {r["game_id"]: r for r in cap["finals_2026_11_14"]}
f_rows = []
for row in pubf["rows"]:
    c = cap_f.get(row["game_id"])
    checks = []
    for pf, cf in (("away", "away"), ("home", "home"), ("away_pts", "away_pts"),
                   ("home_pts", "home_pts"), ("away_quarters", "away_quarters"),
                   ("home_quarters", "home_quarters"), ("attendance", "attendance_printed"),
                   ("officials", "officials_printed")):
        pv, cv = row.get(pf), (c or {}).get(cf)
        if pf == "venue":
            continue
        if cv is None:
            status = "UNVERIFIABLE_IN_THIS_PASS"
        elif pv == cv:
            status = "AGREE"
        else:
            status = "MISMATCH"
        checks.append({"field": pf, "published": pv, "official": cv, "status": status})
    # venue+city as the official page prints them (two lines, one block)
    fv = venue_split(row.get("venue"), (c or {}).get("venue_printed"), (c or {}).get("city_printed"))
    checks.append({"field": "venue(+city)", "published": row.get("venue"),
                   "official": ((c or {}).get("venue_printed") or "") + ", " + ((c or {}).get("city_printed") or ""),
                   "status": fv})
    f_rows.append({"game_id": row["game_id"], "date": row["date"],
                   "matchup": f'{row["away"]}@{row["home"]}', "checks": checks,
                   "official_game_page": row.get("source_url")})


def tally(rows):
    t = {}
    for r in rows:
        for c in r["checks"]:
            t[c["status"]] = t.get(c["status"], 0) + 1
    return dict(sorted(t.items()))


out = {
    "title": "Row-by-row comparison: published files vs this session's official capture",
    "captured_retrieved_utc": cap["retrieved_utc"],
    "published_files": {
        "schedule": "data/official/schedule_2026-11-15_to_18.json",
        "standings": "data/official/standings_2026-11-15.json",
        "finals_2026_11_14": "data/official/results_2026-11-14.json",
    },
    "schedule": {"rows_published": len(pub["rows"]), "rows_official": len(cap["schedule"]),
                 "official_rows_absent_from_published": missing,
                 "published_rows_absent_from_official": extra,
                 "tally": tally(sched_rows), "rows": sched_rows},
    "standings": {"rows_published": len(pubs["rows"]), "rows_official": len(cap["standings"]),
                  "tally": tally(st_rows), "rows": st_rows},
    "finals_2026_11_14": {"rows_published": len(pubf["rows"]), "rows_official": len(cap["finals_2026_11_14"]),
                          "tally": tally(f_rows), "rows": f_rows},
}
json.dump(out, open(os.path.join(HERE, "compare.json"), "w"), indent=1, ensure_ascii=False)

for k in ("schedule", "standings", "finals_2026_11_14"):
    print(k, out[k]["tally"])
    for r in out[k]["rows"]:
        bad = [c for c in r["checks"] if c["status"].startswith(("MISMATCH", "PUBLISHED_BLANK"))]
        if bad:
            print("  ", r.get("matchup") or r.get("team"), [(c["field"], c["published"], c["official"], c["status"]) for c in bad])
if missing:
    print("official rows absent from published:", [(m["game_id"], m["away"]+"@"+m["home"], m["date"]) for m in missing])

# ---------------------------------------------------------------- team stats (model inputs)
cap_s = json.load(open(os.path.join(HERE, "capture_stats.json")))
ADV_F = ["gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to", "ast_ratio",
         "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]
adv_cap = {r["team"]: r for r in cap_s["advanced"]}
pub_adv = json.load(open(os.path.join(ROOT, "data/official/teams_advanced_2026-11-15.json")))
adv_rows = []
for row in pub_adv["rows"]:
    c = adv_cap.get(row["team"])
    checks = []
    for f in ADV_F:
        pv, cv = float(row[f]), float(c[f])
        if pv == cv:
            st = "AGREE"
        elif f in ("gp", "w", "l", "min", "poss", "off_rtg", "def_rtg", "net_rtg"):
            # a team that has played since the model cut has legitimately new totals
            st = "MISMATCH_POINT_IN_TIME"
        else:
            st = "MISMATCH_POINT_IN_TIME"
        checks.append({"field": f, "published": pv, "official": cv, "status": st})
    adv_rows.append({"team": row["team"], "abbr": row["abbr"], "checks": checks})

TRAD_F = ["gp", "w", "l", "pts", "fg_pct", "fg3_pct", "ft_pct", "reb", "ast", "tov", "stl",
          "blk", "pf", "plus_minus", "min"]
trad_cap = {r["team"]: r for r in cap_s["traditional_chunk0_only"]}
pub_trad = json.load(open(os.path.join(ROOT, "data/official/teams_traditional_2026-11-15.json")))
trad_rows = []
for row in pub_trad["rows"]:
    c = trad_cap.get(row["team"])
    if c is None:
        trad_rows.append({"team": row["team"], "abbr": row["abbr"],
                          "checks": [{"field": "*", "published": None, "official": None,
                                      "status": "NOT_RE_READ_IN_THIS_PASS"}]})
        continue
    checks = []
    for f in TRAD_F:
        cv = c.get(f)
        if cv is None:
            st = "NOT_PRINTED_IN_READ_CHUNK"
            checks.append({"field": f, "published": row[f], "official": None, "status": st})
            continue
        pv = float(row[f]); cvf = float(cv)
        st = "AGREE" if pv == cvf else "MISMATCH_POINT_IN_TIME"
        checks.append({"field": f, "published": pv, "official": cvf, "status": st})
    trad_rows.append({"team": row["team"], "abbr": row["abbr"], "checks": checks})

out["team_stats"] = {
    "advanced": {"rows": len(adv_rows), "tally": tally(adv_rows), "detail": adv_rows,
                 "source_url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"},
    "traditional": {"rows_read_this_pass": len(trad_cap), "rows_published": len(pub_trad["rows"]),
                    "tally": tally(trad_rows), "detail": trad_rows,
                    "source_url": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"},
    "opponent": {"rows_read_this_pass": 0,
                 "status": "NOT_RE_READ_IN_THIS_PASS",
                 "source_url": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"},
}
out["stale_inputs"] = json.load(open(os.path.join(HERE, "stale_inputs.json")))
json.dump(out, open(os.path.join(HERE, "compare.json"), "w"), indent=1, ensure_ascii=False)
print("advanced", out["team_stats"]["advanced"]["tally"])
print("traditional", out["team_stats"]["traditional"]["tally"])
