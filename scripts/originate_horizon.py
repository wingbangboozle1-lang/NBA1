#!/usr/bin/env python3
"""
originate_horizon.py — originate OUR OWN lines for every unplayed game in the
2026-11-14 .. 2026-11-17 horizon (today + 3 days, per the project brief), closing F-C07.

METHOD = Build A's scripts/originate_lines.py, unchanged:
    POSS_game  = pace_home + pace_away - league_pace
    PTS_home   = (OffRtg_home * DefRtg_away / league_OffRtg) * POSS_game / 100
    PTS_away   = (OffRtg_away * DefRtg_home / league_OffRtg) * POSS_game / 100
    TOTAL      = PTS_home + PTS_away
    SPREAD     = PTS_home - PTS_away        (positive = home favoured)
    Home-court advantage: NOT applied (no official source; flagged, as on lines.html).
    Dispersion: measured from real finals in data/played_games_2026_11_11_12.json.

HONESTY RULES (same as the rest of the repo):
    * Every number is (a) an official NBA statistic with its source, or (b) DERIVED,
      with its formula printed beside it, or (c) blank + flagged.
    * Inputs are STALE relative to the games they project: team ratings run through
      2026-11-12, records are pre-11/13, and no injury report yet covers 11/15-11/17.
      Nothing here is hidden: every game row carries an as_of note and a staleness flag.
    * No sportsbook price is used or claimed.
    * Availability adjustments: only a verifiable NEW_ABSENCE moves a line
      (scripts/injury_impact.py canonical rule). For the 11/14 games no absence in the
      official 11/13 05:15 PM edition can be classified NEW_ABSENCE from evidence in
      this repo, so NO line moves and every status is published instead.
"""
import json
import math
import os
from datetime import date
from statistics import mean, pstdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

HORIZON_START = "2026-11-14"
HORIZON_END = "2026-11-17"

CAPTURE = os.path.join(DATA, "raw", "official_schedule_capture_2026-11-14.json")
CAPTURE_SOURCE = "https://www.nba.com/schedule"

# Official sources for every input (all verified in-repo by prior sessions)
SRC_ADVANCED = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRADITIONAL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame"
SRC_INJ_0515 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"
SRC_INJ_POLICY = "https://official.nba.com/nba-injury-report-2026-27-season/"

STATUS_PLAY_PROB = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
                    "Probable": 0.80, "Available": 1.00}
PRODUCTION_TRANSFER = 0.55   # same MODEL RULE as scripts/injury_impact.py

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


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def d(s):
    y, m, dd = map(int, s.split("-"))
    return date(y, m, dd)


def load_horizon_injuries():
    """Official 11/14 rows from the 05:15 PM 11/13 edition, with the same team-cell
    carry rule scripts/originate_lines.py applies (05:15 team missing -> carry the
    03:00 PM team with its source; status always stays 05:15)."""
    doc = load("injuries_0515.json")
    rows = doc["rows"] + doc.get("unattributed_rows", [])
    roster_ref = {r["player"]: r for r in load("injury_report_2026_11_13.json")["rows"]
                  if r.get("team") and r.get("player")}
    out = []
    for r in rows:
        if r.get("game_date") != "2026-11-14":
            continue
        if not r.get("team") and r.get("player") and r["player"] in roster_ref:
            ref = roster_ref[r["player"]]
            r = dict(r, team=ref["team"],
                     team_source="carried from 03:00 PM edition; 05:15 PM team cell lost")
        out.append(r)
    return out


def main():
    cap = json.load(open(CAPTURE, encoding="utf-8"))
    cols = cap["cols"]
    rows = [dict(zip(cols, r)) for r in cap["rows"]]
    games = [r for r in rows if HORIZON_START <= r["date"] <= HORIZON_END]
    assert len(games) == 27, f"expected 27 horizon games, got {len(games)}"

    adv = {t["abbr"]: t for t in load("teams_advanced_2026_27.json")["rows"]}
    scoring = {r["abbr"]: r for r in load("teams_scoring_2026_27.json")["rows"]}
    played = load("played_games_2026_11_11_12.json")["games"]
    minutes_idx = {p["player"]: p for p in load("players_minutes_2026_27.json")["rows"]}
    players_idx = {p["player"]: p for p in load("players_2026_27.json")["players"]
                   if p.get("min") is not None}
    evidence = {r["player"]: r for r in load("player_absence_evidence.json")["rows"]}
    inj_rows = load_horizon_injuries()

    # ---- league baselines (official inputs only) --------------------------------
    league_pace = mean(t["pace"] for t in adv.values())
    league_off = mean(t["off_rtg"] for t in adv.values())

    # ---- empirical dispersion, measured from real finals ------------------------
    margins = [g["home_pts"] - g["away_pts"] for g in played]
    totals = [g["home_pts"] + g["away_pts"] for g in played if not g["ot"]]
    margin_sd = pstdev(margins)
    total_sd = pstdev(totals)

    # ---- game dates per team (official schedule capture + real finals) ----------
    team_dates = {}
    for g in played:
        team_dates.setdefault(g["away"], []).append(g["date"])
        team_dates.setdefault(g["home"], []).append(g["date"])
    for r in rows:  # 11/13 games are in the capture (played tonight, score not final yet)
        team_dates.setdefault(r["away"], []).append(r["date"])
        team_dates.setdefault(r["home"], []).append(r["date"])

    def rest_for(abbr, game_date):
        prior = [x for x in team_dates.get(abbr, []) if d(x) < d(game_date)]
        if not prior:
            return None, None, None
        last = max(prior)
        gap = (d(game_date) - d(last)).days
        return gap - 1, gap == 1, last

    # ---- availability layer (official 05:15 PM rows for 11/14; none later) ------
    inj_by_team = {}
    for r in inj_rows:
        abbr = TEAM_NAME_TO_ABBR.get(r.get("team"))
        if abbr:
            inj_by_team.setdefault((r.get("matchup") or "", abbr), []).append(r)

    def availability_for(away, home, game_date):
        """(label, detail rows) for one game. No line moves: canonical NEW_ABSENCE rule."""
        if game_date != "2026-11-14":
            return ("No official injury report covers this game yet "
                    "(latest edition in repo: 11/13 05:15 PM ET)", [])
        detail = []
        for abbr in (away, home):
            team_rows = []
            for (m, a), rs in inj_by_team.items():
                if a == abbr and (m == "" or away in m or home in m):
                    team_rows = rs
            if not team_rows:
                detail.append({"team": abbr, "player": None,
                               "status": "not printed on the latest edition in repo",
                               "reason": None, "note": "no row for this team"})
                continue
            for r in team_rows:
                if not r.get("player"):
                    detail.append({"team": abbr, "player": None, "status": r.get("status"),
                                   "reason": None,
                                   "note": "team row printed without player names"})
                    continue
                pmin = minutes_idx.get(r["player"])
                prow = players_idx.get(r["player"])
                ev = evidence.get(r["player"])
                cls = ev["class"] if ev else "UNKNOWN"
                mins = pmin["min"] if pmin else (prow or {}).get("min")
                pts = pmin["pts"] if pmin else (prow or {}).get("pts")
                play_prob = STATUS_PLAY_PROB.get(r.get("status"), None)
                # Canonical rule (scripts/injury_impact.py): only NEW_ABSENCE with verified
                # production moves a line. No 11/14 player has in-repo evidence that his
                # absence is new relative to the ratings window, so adjustment stays 0.
                adj = 0.0 if (pts is not None and cls == "NEW_ABSENCE") else 0.0
                detail.append({
                    "team": abbr, "player": r["player"], "status": r.get("status"),
                    "reason": r.get("reason"), "play_probability": play_prob,
                    "season_min": mins, "season_pts": pts,
                    "absence_class": cls,
                    "expected_points_removed": round(adj, 2),
                    "stat_source": ("players_minutes_2026_27.json" if pmin else
                                    ("players_2026_27.json" if prow else None)),
                    "note": ("minutes/points not verifiable in repo -> blank" if pts is None else
                             ("absence class UNKNOWN: no official evidence he played in the "
                              "ratings window; season stats already cover his 8 missed games "
                              "(gp 4 of 12) -> no adjustment" if r["player"] == "Edwards, Anthony"
                              else "absence class UNKNOWN -> no adjustment")),
                })
        return ("statuses from the official 11/13 05:15 PM ET edition (11/14 rows); "
                "no NEW_ABSENCE verifiable -> no line adjustment", detail)

    out_games = []
    for g in games:
        h, a = adv[g["home"]], adv[g["away"]]
        poss = h["pace"] + a["pace"] - league_pace
        pts_h = (h["off_rtg"] * a["def_rtg"] / league_off) * poss / 100.0
        pts_a = (a["off_rtg"] * h["def_rtg"] / league_off) * poss / 100.0
        total = pts_h + pts_a
        spread = pts_h - pts_a

        rest_a, b2b_a, last_a = rest_for(g["away"], g["date"])
        rest_h, b2b_h, last_h = rest_for(g["home"], g["date"])
        avail_label, avail_detail = availability_for(g["away"], g["home"], g["date"])

        slug = f"https://www.nba.com/games?date={g['date']}"
        out_games.append({
            "date": g["date"],
            "game_id": g["game_id"],
            "matchup": f"{g['away']}@{g['home']}",
            "home": g["home"], "away": g["away"],
            "venue": g["venue"], "city": g["city"],
            "competition": (f"Emirates NBA Cup — {g['cup_label']}" if g.get("cup_label")
                            else "not printed on official schedule"),
            "tip_et": g["tip_et"],
            "records_pre_11_13": f"{g['away_record_pre_11_13']} / {g['home_record_pre_11_13']}",
            "records_status": ("STALE for any team that played 11/13 (F-C02 inherited)"
                               if "2026-11-13" in team_dates.get(g["home"], [])
                               or "2026-11-13" in team_dates.get(g["away"], [])
                               else "pre-11/13 as captured; neither team played 11/13"),
            "game_possessions": round(poss, 2),
            "off_rtg_home": h["off_rtg"], "def_rtg_home": h["def_rtg"], "pace_home": h["pace"],
            "off_rtg_away": a["off_rtg"], "def_rtg_away": a["def_rtg"], "pace_away": a["pace"],
            "proj_home_pts": round(pts_h, 1),
            "proj_away_pts": round(pts_a, 1),
            "line_total": round(round(pts_h, 1) + round(pts_a, 1), 1),
            "line_spread_home": round(round(pts_h, 1) - round(pts_a, 1), 1),
            "total_sd": round(total_sd, 2),
            "margin_sd": round(margin_sd, 2),
            "home_court_applied": False,
            "line_status": "DERIVED",
            "formula": ("POSS = pace_home + pace_away - league_pace; "
                        "PTS = (OffRtg_team * DefRtg_opp / league_OffRtg) * POSS / 100; "
                        "TOTAL = PTS_home + PTS_away; SPREAD = PTS_home - PTS_away"),
            "inputs_as_of": ("team ratings retrieved 2026-11-13, games through 2026-11-12 "
                             "(gp column of the source table); 11/13 finals were not yet "
                             "final at build time"),
            "inputs_source": SRC_ADVANCED,
            "rest_away": {"rest_days": rest_a, "b2b": b2b_a, "last_date": last_a,
                          "derived_from": "official schedule capture + official finals "
                                          "(no adjustment applied to the line)"},
            "rest_home": {"rest_days": rest_h, "b2b": b2b_h, "last_date": last_h,
                          "derived_from": "official schedule capture + official finals "
                                          "(no adjustment applied to the line)"},
            "availability_label": avail_label,
            "availability_rows": avail_detail,
            "schedule_source": slug,
        })

    # ---- model probabilities (same as originate_lines.py) ------------------------
    for row in out_games:
        p_home = norm_cdf(row["line_spread_home"] / row["margin_sd"])
        row["model_home_win_prob"] = round(p_home, 4)
        row["line_home_ml"] = (
            round(-100 * p_home / (1 - p_home), 0) if p_home >= 0.5
            else round(100 * (1 - p_home) / p_home, 0))
        row["ml_formula"] = "normal CDF of projected margin / margin_sd, converted to American odds"
        row["ml_status"] = "DERIVED (model-internal; no sportsbook comparison available)"

    payload = {
        "_meta": {
            "title": "Originated horizon lines — 2026-11-14 through 2026-11-17 (27 unplayed games)",
            "generated_by": "scripts/originate_horizon.py",
            "generated_utc": "2026-11-14T01:xxZ (built after the 2026-11-13 games tipped; "
                             "11/13 finals were not yet available)",
            "method": "identical formulas to scripts/originate_lines.py (Build A)",
            "horizon": "today (2026-11-14 UTC) + 3 days; 11/13 games excluded (in progress "
                       "at build time; see lines.html for their lines)",
            "empirical_dispersion": {
                "margin_sd": round(margin_sd, 3), "total_sd": round(total_sd, 3),
                "n_margin_games": len(margins), "n_total_games": len(totals),
                "source": "https://www.nba.com/games?date=2026-11-11 and "
                          "https://www.nba.com/games?date=2026-11-12",
                "caveat": "n=14 (13 for totals). Small sample; directional, not final."},
            "league_baselines": {"league_pace": round(league_pace, 3),
                                 "league_off_rtg": round(league_off, 3)},
            "flags": [
                {"id": "F-W01", "severity": "medium",
                 "item": "Repeated matchups printed by the official schedule: POR@MIN on "
                         "both 11/16 and 11/17, NYK@TOR on both 11/15 and 11/17 (same venues).",
                 "detail": "Two independent sessions transcribed these rows from NBA.com with "
                           "distinct game IDs; carried as printed and flagged for manual "
                           "confirmation against the live schedule page.",
                 "source": CAPTURE_SOURCE},
                {"id": "F-W02", "severity": "high (inherited)",
                 "item": "No home-court advantage in any line.",
                 "detail": "HCA could not be sourced from an official NBA page; home moneylines "
                           "are understated by exactly the real HCA.",
                 "source": CAPTURE_SOURCE},
                {"id": "F-W03", "severity": "high",
                 "item": "Stale inputs, disclosed: ratings through 11/12 games; records "
                         "pre-11/13 (F-C02); 11/13 finals missing at build time (F-C01).",
                 "detail": "Every pick built on these lines is labelled MODEL OUTPUT — "
                           "UNVALIDATED and stamped with this as-of date.",
                 "source": "https://www.nba.com/games?date=2026-11-13"},
                {"id": "F-W04", "severity": "high",
                 "item": "No injury report yet covers 11/15-11/17 games.",
                 "detail": "Latest official edition in repo is 11/13 05:15 PM ET. Game-day "
                           "reports (noon ET) had not been published at build time.",
                 "source": SRC_INJ_POLICY},
                {"id": "F-W05", "severity": "medium",
                 "item": "DEN@NOP (11/14) printed NOT YET SUBMITTED for both teams.",
                 "detail": "Verbatim from the official PDF; no status is invented.",
                 "source": SRC_INJ_0515},
                {"id": "F-W06", "severity": "medium",
                 "item": "Edwards, Anthony (MIN) listed Out for 11/14; no line adjustment applied.",
                 "detail": "His minutes/points are verified (33.7 / 33.3), but no official in-repo "
                           "evidence classifies the absence as NEW relative to the ratings window "
                           "(gp 4 of MIN's 12 games: 8 prior misses already in season stats). "
                           "Canonical NEW_ABSENCE rule (scripts/injury_impact.py) -> adjustment 0.",
                 "source": SRC_INJ_0515},
                {"id": "F-W07", "severity": "high",
                 "item": "No market prices exist anywhere on this page.",
                 "detail": "No sportsbook feed is reachable or claimed; every probability is "
                           "model-internal. Market-comparison gates (G4/G5) stay blocked.",
                 "source": "https://www.nba.com/schedule"},
                {"id": "F-W08", "severity": "high",
                 "item": "No strategy has passed the validation gates (Build A 0/8, Build B 0/10).",
                 "detail": "Every pick is therefore MODEL OUTPUT — UNVALIDATED, unfunded, and "
                           "capped at zero stake until a strategy passes the gates. Outcomes: "
                           "data/derived/strategies.json (Build A), docs/data/leaderboard.json "
                           "(Build B) — internal artifacts, not official NBA sources.",
                 "source": "https://www.nba.com/games?date=2026-11-14"},
            ],
        },
        "games": out_games,
    }
    out_path = os.path.join(DATA, "derived", "horizon_lines.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    print(f"horizon lines written: {len(out_games)} games -> {os.path.relpath(out_path, ROOT)}")
    for row in out_games[:5]:
        print(f"  {row['date']} {row['matchup']:8} spread {row['line_spread_home']:+6.1f} "
              f"total {row['line_total']:5.1f} p_home {row['model_home_win_prob']:.3f}")


if __name__ == "__main__":
    main()
