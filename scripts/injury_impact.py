#!/usr/bin/env python3
"""
injury_impact.py — injury -> rotation minutes -> production -> game projection.

THE CENTRAL CORRECTION IN THIS MODULE
-------------------------------------
The first version of this script simply added up the production of every player on the injury
report and called the total "impact". That is wrong, and the fix matters more than the model.

Team statistics on NBA.com are SEASON-TO-DATE and already include every game a player has missed.
If a player has been out for nine games, his absence is already inside his team's rating. Deducting
his production again double-counts it.

So every injured player is first classified (data/player_absence_evidence.json):
  NEW_ABSENCE       last played 11/11 or 11/12  -> his absence is NOT yet in team form
  ALREADY_BAKED_IN  last played before 11/09    -> his absence IS already in team form
  SEASON_LONG       has not played this season  -> fully baked in
  UNKNOWN           not verified                -> excluded, flagged

Only NEW_ABSENCE rows move the projection, and even then the adjustment is a labelled model
assumption, not a measured effect.

WHAT IS OFFICIAL vs ASSUMED
---------------------------
OFFICIAL: the injury report (who/status/reason), player per-game stats, roster and foul rules.
ASSUMED : the share of a lost player's production that actually leaves the team's output, the
          minutes redistribution rule, and the play-probability attached to each status label.
"""
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

RULE_SOURCES = {
    "roster_fouls": "https://official.nba.com/rule-no-3-players-substitutes-and-coaches/",
    "timing": "https://official.nba.com/rule-no-5-scoring-and-timing/",
    "injury_policy": "https://official.nba.com/nba-injury-report-2026-27-season/",
}

STATUS_PLAY_PROB = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
                    "Probable": 0.80, "Available": 1.00}

# Fraction of a lost player's scoring that actually leaves the team's output.
# 1.0 would mean the team simply loses his points. It does not: usage is redistributed and
# replacement minutes score something. 0.55 is a modelled midpoint, NOT a measured parameter.
PRODUCTION_TRANSFER = 0.55

TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)


def norm(name):
    """'Mobley, Evan' -> 'evan mobley' so it can be matched against NBA.com display names."""
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
        return f"{first} {last}".lower().replace("  ", " ")
    return name.strip().lower()



OFFICIAL_EDITION_FILE = "injuries_0515.json"   # NBA injury report 11/13/26 05:15 PM ET (newest official edition in repo)
OFFICIAL_EDITION_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"


def load_official_injuries():
    """Rows of the latest official injury-report edition that this layer may use.

    Replaces the 03:00 PM edition (injury_report_2026_11_13.json), which was stale: five statuses
    changed by 05:15 PM (see data/audit/injury_edition_diff.json).
    Excluded, never inferred: rows with no player (NOT YET SUBMITTED) and rows whose team cell was
    lost in PDF extraction (unless a roster-verified team exists, see below). Only 11/13 rows are used: these layers apply adjustments to 11/13 games
    only; 11/14 rows stay in injuries_0515.json for the Edge Lab.
    """
    doc = load(OFFICIAL_EDITION_FILE)
    rows = doc["rows"] + doc.get("unattributed_rows", [])
    # 05:15 PM extraction lost the Team cell on some rows. The 03:00 PM edition printed or roster-verified
    # the team for those players. Carry that team forward ONLY where the 05:15 PM team is missing and
    # record its source; the status always stays the 05:15 PM status.
    roster_ref = {r["player"]: r for r in load("injury_report_2026_11_13.json")["rows"]
                  if r.get("team") and r.get("player")}
    out = []
    for r in rows:
        if not r.get("player") or r.get("game_date") != "2026-11-13":
            continue
        if not r.get("team") and r["player"] in roster_ref:
            ref = roster_ref[r["player"]]
            r = dict(r, team=ref["team"], matchup=r.get("matchup") or ref.get("matchup"),
                     team_source="carried from 03:00 PM edition (%s); 05:15 PM team cell lost" % ref.get("team_source", "pdf"),
                     team_source_url=ref.get("team_source_url") or ref.get("source_url"))
        if r.get("team"):
            out.append(r)
    return out


def main():
    inj = load_official_injuries()
    players = load("players_2026_27.json")["players"]
    evidence = {norm(r["player"]): r for r in load("player_absence_evidence.json")["rows"]}
    sched = load("schedule_2026_11_13_to_16.json")["games"]
    pidx = {}
    for p in players:
        if p.get("min") is not None:
            pidx[norm(p["player"])] = p
    # Second source: the minutes leaderboard, which covers high-usage players the
    # roster table above does not. Kept separate so its coverage limit stays visible.
    minidx = {}
    for p in load("players_minutes_2026_27.json")["rows"]:
        minidx[norm(p["player"])] = {"min": p["min"], "pts": p["pts"], "_src": "players_minutes_2026_27.json"}

    by_team = defaultdict(list)
    for r in inj:
        abbr = TEAM_NAME_TO_ABBR.get(r["team"])
        if abbr:
            by_team[abbr].append(r)

    rows = []
    for abbr, rs in sorted(by_team.items()):
        for r in rs:
            key = norm(r["player"])
            p = pidx.get(key)
            ev = evidence.get(key)
            if p is None:
                p = minidx.get(key)
            # Evidence-file statistics override, used only where the leaderboard does not reach.
            if ev and ev.get("season_min") is not None:
                p = {"min": ev["season_min"], "pts": ev["season_pts"],
                     "_src": ev.get("stat_source_url", "player_absence_evidence.json")}
            cls = ev["class"] if ev else "UNKNOWN"
            play_prob = STATUS_PLAY_PROB.get(r["status"], 0.0)
            pts = p["pts"] if p else None
            mins = p["min"] if p else None
            # expected production removed, only for a genuinely new absence
            if pts is None or cls != "NEW_ABSENCE":
                adj = 0.0
            else:
                # production lost = (chance he does NOT play) x his scoring x transfer share
                adj = (1.0 - play_prob) * pts * PRODUCTION_TRANSFER
            rows.append({
                "team": abbr,
                "player": r["player"],
                "status": r["status"],
                "reason": r["reason"],
                "season_min": mins,
                "season_pts": pts,
                "absence_class": cls,
                "last_game_date": ev["last_game_date"] if ev else None,
                "play_probability": play_prob,
                "expected_points_removed": round(adj, 2),
                "adjustment_source": "MODEL ASSUMPTION: (1 - play probability) x season PPG x "
                                     f"{PRODUCTION_TRANSFER} transfer" if adj else
                                     "none — absence already inside team's season stats, or "
                                     "production not verified",
                "stat_source": (p or {}).get("_src", "players_2026_27.json" if p else None),
                "absence_evidence_url": ev["evidence_url"] if ev else None,
                "report_source_url": OFFICIAL_EDITION_URL,
            })

    # ---- team-level adjustment, applied to the 11/13 games only --------------
    team_adj = defaultdict(float)
    for r in rows:
        team_adj[r["team"]] += r["expected_points_removed"]

    lines = load("derived/lines.json")["games"]
    adjusted = []
    for g in lines:
        ha = team_adj.get(g["home"], 0.0)
        aa = team_adj.get(g["away"], 0.0)
        new_total = g["line_total"] - ha - aa
        new_margin = g["line_spread_home"] - ha + aa   # spread is home - away
        adjusted.append({
            "date": g["date"], "game_id": g["game_id"],
            "matchup": f"{g['away']}@{g['home']}",
            "originated_total": g["line_total"], "home_points_removed": round(ha, 2),
            "away_points_removed": round(aa, 2),
            "injury_adjusted_total": round(new_total, 1),
            "originated_spread": g["line_spread_home"],
            "injury_adjusted_spread": round(new_margin, 1),
            "total_shift": round(new_total - g["line_total"], 1),
            "spread_shift": round(new_margin - g["line_spread_home"], 1),
            "applies": g["date"] == "2026-11-13",
            "note": "Adjustment uses the 11/13 injury report only. Games on 11/14-11/16 have no "
                    "report yet (league PDF still read NOT YET SUBMITTED), so no adjustment is applied.",
        })

    # ---- rotation minutes, regulation total from the rulebook ----------------
    # 5 players on the floor (Rule 3 Sec I; Rule 5 Sec II) x 48 regulation minutes = 240.
    rotation = []
    for abbr in sorted(by_team):
        new_absent_min = sum((r["season_min"] or 0) * (1 - r["play_probability"])
                             for r in rows
                             if r["team"] == abbr and r["absence_class"] == "NEW_ABSENCE")
        rotation.append({
            "team": abbr,
            "regulation_minutes_available": 240,
            "minutes_vacated_by_new_absences": round(new_absent_min, 1),
            "share_of_regulation_minutes": round(new_absent_min / 240, 4),
            "redistribution_rule": "Spread across the remaining rotation in proportion to each "
                                   "teammate's existing minutes-per-game. MODEL RULE, not measured.",
            "minutes_available_source": RULE_SOURCES["roster_fouls"],
            "caveat": "240 is regulation only. Overtime adds 5 minutes per extra period (Rule 5).",
        })

    # ---- 3-day availability view -------------------------------------------
    availability = []
    for g in sched:
        for abbr in (g["away"], g["home"]):
            rs = by_team.get(abbr, [])
            has = g["date"] == "2026-11-13" and bool(rs)
            availability.append({
                "date": g["date"], "game_id": g["game_id"],
                "matchup": f"{g['away']}@{g['home']}", "team": abbr,
                "status": "REPORTED" if has else "NO REPORT YET",
                "reported_count": len(rs) if has else 0,
                "out": sorted(r["player"] for r in rows if r["team"] == abbr and r["status"] == "Out") if has else [],
                "questionable": sorted(r["player"] for r in rows if r["team"] == abbr
                                       and r["status"] in ("Questionable", "Doubtful")) if has else [],
                "blank_reason": None if has else
                    "The official league report read NOT YET SUBMITTED for 11/14 at the 11/13 "
                    "03:00 PM ET edition, and no report can exist yet for 11/15-11/16.",
                "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf",
            })

    # ---- sensitivity: the transfer assumption is the largest lever -----------
    sensitivity = []
    for alt in (0.35, 0.45, 0.55, 0.65, 0.75):
        for g in lines:
            if g["date"] != "2026-11-13":
                continue
            ha = alt * sum((r["season_pts"] or 0) * (1 - r["play_probability"])
                           for r in rows if r["team"] == g["home"]
                           and r["absence_class"] == "NEW_ABSENCE")
            aa = alt * sum((r["season_pts"] or 0) * (1 - r["play_probability"])
                           for r in rows if r["team"] == g["away"]
                           and r["absence_class"] == "NEW_ABSENCE")
            if ha or aa:
                sensitivity.append({
                    "matchup": f"{g['away']}@{g['home']}",
                    "production_transfer": alt,
                    "total": round(g["line_total"] - ha - aa, 1),
                    "spread": round(g["line_spread_home"] - ha + aa, 1),
                })

    out = {
        "_meta": {
            "title": "Injury, rotation and production impact",
            "generated_by": "scripts/injury_impact.py",
            "generated_utc": "2026-11-13",
            "central_correction": "Season-to-date team stats already contain past absences. Only "
                                  "NEW_ABSENCE players move the line. See data/player_absence_evidence.json.",
            "model_assumptions": {
                "status_play_probability": STATUS_PLAY_PROB,
                "production_transfer": PRODUCTION_TRANSFER,
                "minute_redistribution": "proportional to teammates' existing minutes",
                "not_modelled_because_no_official_source": [
                    "games-until-return by injury type",
                    "pace change when a creator is out",
                    "defensive rating change from a lost rim protector",
                    "replacement-player production quality",
                ],
            },
            "coverage_limitation": "Season per-game minutes and points are available only for the "
                                   "players in data/players_2026_27.json. Players not in that file "
                                   "carry blank stats rather than estimated ones.",
        },
        "players": rows,
        "team_adjustment": [{"team": k, "expected_points_removed": round(v, 2)}
                            for k, v in sorted(team_adj.items()) if v > 0],
        "lines_injury_adjusted": adjusted,
        "sensitivity": sensitivity,
        "rotation": rotation,
        "availability_3_day": availability,
    }
    with open(os.path.join(DATA, "derived", "injury_impact.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"{'team':5} {'player':26} {'status':11} {'class':17} {'pts_removed':>11}")
    for r in rows:
        if r["absence_class"] == "NEW_ABSENCE" or r["season_pts"] is not None:
            print(f"{r['team']:5} {r['player'][:26]:26} {r['status']:11} "
                  f"{r['absence_class']:17} {r['expected_points_removed']:11.2f}")
    print("\nTeams with a non-zero adjustment (11/13 only):")
    for t in out["team_adjustment"]:
        print(f"   {t['team']}: -{t['expected_points_removed']} pts")
    print("\nLines moved by the injury adjustment (11/13):")
    for a in adjusted:
        if a["applies"] and (a["total_shift"] or a["spread_shift"]):
            print(f"   {a['matchup']:10} total {a['originated_total']:6.1f} -> "
                  f"{a['injury_adjusted_total']:6.1f}   spread {a['originated_spread']:+5.1f} -> "
                  f"{a['injury_adjusted_spread']:+5.1f}")


if __name__ == "__main__":
    main()
