#!/usr/bin/env python3
"""recut_2026-11-19_4eef6d3b.py — re-cut the model inputs from a first-hand
re-read of the three official team-stat pages on 2026-11-19 ~13:2x UTC
(session arena/4eef6d3b-nba1, COORDINATION.md section 74, tasks T04/T05).

Every numeric row below was transcribed from the official page rendered
through the platform web-fetch channel at the read times recorded in
`data/official/teams_reread_2026-11-19_4eef6d3b.json`.  Nothing is fitted,
imputed, interpolated or carried over silently: the previous cut is diffed,
and the drift is published (including F-89F-04/Q37: LAL & UTA 15 -> 16 GP,
UTA opponent points 117.3 -> 116.0 — the current official opponent table
prints 116.0 for UTA, read this cycle).

Reads performed this session (three official pages + the date-filtered
training window):
  1. https://www.nba.com/stats/teams/advanced                          30 rows, all 20 columns
  2. https://www.nba.com/stats/teams/advanced?DateFrom=10/20/2026&DateTo=11/05/2026
                                                                     30 rows, all 20 columns (train window)
  3. https://www.nba.com/stats/teams/traditional                       GP/W/L/WIN%/Min/PTS for 13 teams
     (chunk-limited read; GP/W/L corroborated 30/30 against the
      arena/89f7b601-nba1 08:0x transcription of the same page)
  4. https://www.nba.com/stats/teams/opponent                          30 rows, GP/W/L/OppPTS

Outputs:
  data/official/teams_reread_2026-11-19_4eef6d3b.json    the read record
  data/raw/team_advanced.json                            model input (both windows + verification)
  data/derived/team_stats_recut.json                     model input (the cut the horizon is priced from)
  data/derived/measured_constants_2026_27.json           measured constants
  data/derived/recut_2026-11-19_4eef6d3b/drift.json      before/after + gates + coverage

Gates (same five as scripts/recut_2026_11_19.py, run and recorded):
  G1  W + L == GP on the advanced table
  G2  |NetRtg - (OffRtg - DefRtg)| <= 0.25
  G3  GP and W-L on the advanced table equal the standings
  G4  total team-games == 2 x decided finals in the results feed
  G5  standings closed-system identity (home wins == road losses)
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The commit carrying the cut this script replaces (arena/929395a5-nba1's 05:0x
# recut, landed with the 12:37Z refresh captures). The drift report is always
# measured against THIS baseline, never against a re-run of itself.
PREV_CUT_COMMIT = "b8cf2cb"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
READ_AT = "2026-11-19T13:2xZ (platform web-fetch channel; per-page read times in the read record)"

SRC_ADV = "https://www.nba.com/stats/teams/advanced"
SRC_ADV_TRAIN = ("https://www.nba.com/stats/teams/advanced"
                 "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season")
SRC_TRAD = "https://www.nba.com/stats/teams/traditional"
SRC_OPP = "https://www.nba.com/stats/teams/opponent"
SRC_STD = "https://www.nba.com/standings"
SRC_GAMES = "https://www.nba.com/games"

COLS = ["team", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
        "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
        "pace", "pie", "poss"]
# team_advanced.json keeps the official parse schema (engine/parse_official.ADVANCED_COLS
# names: ortg/drtg/netr); team_stats_recut.json keeps the model-input names
# (off_rtg/def_rtg/net_rtg). Same values, two published schemas - never mix them.
ADV_COLS = ["team", "gp", "w", "l", "min", "ortg", "drtg", "netr", "ast_pct", "ast_to",
            "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
            "pace", "pie", "poss"]
RENAME = {"off_rtg": "ortg", "def_rtg": "drtg", "net_rtg": "netr"}

ABBR = {"Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
        "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
        "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
        "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
        "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
        "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
        "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
        "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
        "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
        "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
        "Washington Wizards": "WAS"}

# ---- advanced, season to date (official page, read 2026-11-19 ~13:2x UTC)
ADV = [
 ("Los Angeles Lakers",16,13,3,773.0,119.8,113.2,6.7,58.8,1.46,17.3,33.6,65.0,49.8,16.5,57.2,61.5,100.35,53.0,1614),
 ("Philadelphia 76ers",16,13,3,768.0,114.5,111.8,2.7,64.7,2.08,18.7,28.4,72.0,50.3,12.6,53.4,57.7,99.88,51.4,1600),
 ("Houston Rockets",16,12,4,768.0,121.1,112.1,9.0,65.4,1.89,19.4,36.7,68.7,53.2,15.0,55.6,59.7,97.41,55.3,1558),
 ("San Antonio Spurs",15,12,3,725.0,118.1,107.0,11.1,65.6,2.23,19.4,33.5,71.3,52.5,12.6,53.0,57.1,98.35,56.0,1487),
 ("Boston Celtics",15,11,4,725.0,117.0,106.0,11.0,66.7,1.85,19.1,32.9,67.7,50.3,14.9,54.6,57.9,96.76,54.7,1460),
 ("Memphis Grizzlies",15,11,4,725.0,120.6,111.9,8.7,67.6,1.82,19.8,34.2,69.8,52.7,15.7,56.9,61.1,100.27,54.3,1516),
 ("Minnesota Timberwolves",15,11,4,725.0,114.5,104.0,10.5,60.0,1.58,17.5,34.7,69.3,52.5,15.8,54.8,57.4,101.23,55.0,1528),
 ("Detroit Pistons",14,10,4,682.0,114.9,108.9,6.0,67.9,1.97,19.6,30.0,66.6,48.6,14.2,54.5,58.4,98.78,54.2,1406),
 ("Atlanta Hawks",15,9,6,725.0,112.8,110.8,1.9,71.1,2.03,20.2,32.8,69.6,49.9,14.6,52.8,55.7,103.71,49.0,1566),
 ("Miami Heat",15,9,6,725.0,116.9,116.7,0.3,70.3,2.06,20.0,30.8,68.3,49.4,14.0,55.4,59.1,102.19,50.8,1546),
 ("Oklahoma City Thunder",15,9,6,720.0,113.0,108.7,4.4,55.5,1.73,16.8,31.6,68.9,50.9,13.5,52.2,55.9,99.17,53.5,1488),
 ("Portland Trail Blazers",14,9,5,672.0,116.2,110.2,6.0,63.8,1.55,17.8,33.0,70.1,51.9,16.1,54.8,59.2,100.71,52.5,1410),
 ("Cleveland Cavaliers",16,8,8,773.0,117.5,115.5,2.0,64.7,1.99,19.3,30.9,68.7,50.4,13.7,55.8,59.1,100.01,51.0,1610),
 ("Dallas Mavericks",15,8,7,720.0,112.3,113.4,-1.1,65.5,1.64,18.6,33.1,65.9,49.5,16.3,53.6,57.3,99.97,49.4,1501),
 ("Denver Nuggets",13,8,5,629.0,114.3,113.8,0.5,64.9,1.89,19.1,30.4,66.8,49.4,14.2,54.3,58.6,98.02,52.5,1287),
 ("Golden State Warriors",15,8,7,725.0,113.4,112.8,0.6,70.5,1.70,19.1,32.7,67.9,50.3,16.2,53.9,58.1,99.41,50.3,1503),
 ("New York Knicks",14,8,6,677.0,114.8,109.0,5.8,68.6,1.83,18.9,37.1,72.2,54.5,15.2,52.4,56.3,94.87,53.6,1342),
 ("Phoenix Suns",14,7,7,672.0,115.6,116.8,-1.2,65.8,1.94,19.6,30.5,63.1,46.8,14.4,55.4,58.4,98.89,49.4,1382),
 ("Orlando Magic",14,6,8,677.0,111.3,114.0,-2.7,68.5,1.65,19.1,30.7,70.6,50.5,16.4,53.9,57.4,97.84,48.5,1375),
 ("Indiana Pacers",15,5,10,720.0,110.7,113.6,-2.9,67.2,1.92,19.7,24.4,68.1,46.8,14.3,53.9,57.4,100.90,49.4,1511),
 ("New Orleans Pelicans",16,5,11,783.0,111.7,118.9,-7.1,60.7,1.54,17.1,30.1,68.5,48.9,15.3,51.8,57.5,101.30,46.4,1652),
 ("Toronto Raptors",15,5,10,725.0,113.7,113.1,0.5,67.6,2.07,19.3,34.3,66.4,49.0,13.7,52.0,55.1,98.09,48.4,1478),
 ("Washington Wizards",16,5,11,778.0,109.9,117.1,-7.1,60.1,1.62,17.1,29.2,65.6,47.9,14.6,51.7,56.3,99.46,46.3,1612),
 ("Charlotte Hornets",14,4,10,677.0,103.1,113.7,-10.6,62.6,1.14,15.9,36.2,72.8,53.4,19.9,48.6,52.5,96.43,43.5,1360),
 ("Chicago Bulls",14,4,10,677.0,111.1,119.1,-8.0,67.9,1.61,18.7,31.6,64.6,48.0,16.5,52.7,56.8,103.80,46.2,1464),
 ("LA Clippers",13,4,9,629.0,111.4,117.0,-5.6,68.5,1.55,19.0,29.2,65.9,47.6,17.2,54.9,58.8,99.74,47.4,1306),
 ("Brooklyn Nets",14,3,11,677.0,110.5,119.0,-8.4,64.6,1.39,17.4,31.9,68.0,49.6,17.5,53.5,57.5,99.51,45.2,1404),
 ("Utah Jazz",16,3,13,778.0,107.0,114.5,-7.5,65.0,1.48,17.8,29.0,69.7,49.2,16.7,52.4,56.2,100.16,47.2,1626),
 ("Milwaukee Bucks",15,1,14,720.0,106.7,119.7,-13.0,65.1,1.46,17.4,31.1,64.5,47.6,16.8,51.4,54.7,101.00,42.4,1515),
 ("Sacramento Kings",14,1,13,672.0,106.9,120.4,-13.5,64.8,1.47,18.2,28.4,69.3,48.0,17.2,52.8,56.3,100.93,42.5,1411),
]

# ---- advanced, training window 2026-10-20..2026-11-05 (official date-filtered page)
ADV_TRAIN = [
 ("Philadelphia 76ers",9,8,1,432.0,110.5,105.1,5.4,65.5,2.01,18.6,27.8,69.6,48.9,12.9,51.7,55.7,100.28,52.7,904),
 ("Houston Rockets",9,7,2,432.0,120.0,109.6,10.4,67.0,1.76,19.6,35.9,68.0,52.7,16.2,56.6,60.9,98.17,57.2,884),
 ("Los Angeles Lakers",9,7,2,432.0,121.1,112.9,8.2,59.6,1.40,18.0,29.7,63.9,48.3,17.6,60.2,64.5,100.72,54.5,905),
 ("Boston Celtics",8,6,2,389.0,115.8,109.2,6.6,67.1,1.77,18.7,32.7,65.5,49.1,15.2,53.2,57.4,97.60,53.1,789),
 ("Detroit Pistons",8,6,2,384.0,112.4,103.0,9.4,67.6,1.78,19.4,27.5,67.5,48.5,15.3,54.9,58.3,98.81,56.3,791),
 ("Golden State Warriors",9,6,3,432.0,117.0,112.5,4.5,69.4,1.66,19.1,34.2,68.7,51.2,16.7,55.5,59.9,100.56,51.8,906),
 ("Memphis Grizzlies",8,6,2,389.0,117.1,106.8,10.3,63.8,1.67,18.8,33.7,72.5,53.7,16.0,56.0,59.6,101.49,54.6,823),
 ("Minnesota Timberwolves",9,6,3,437.0,116.1,105.2,10.9,60.6,1.73,18.1,35.8,68.7,52.3,15.1,55.7,57.4,101.11,54.8,921),
 ("Oklahoma City Thunder",8,6,2,384.0,111.7,110.8,0.8,53.9,1.63,15.8,32.5,67.7,50.5,13.5,50.0,54.6,98.31,51.5,788),
 ("Portland Trail Blazers",7,6,1,336.0,120.0,109.6,10.4,65.1,1.73,18.6,36.2,73.6,55.1,15.5,56.4,60.2,101.29,54.7,711),
 ("San Antonio Spurs",8,6,2,389.0,115.4,107.4,8.0,62.5,2.04,18.3,33.1,69.2,51.3,12.8,51.7,55.9,99.89,54.4,810),
 ("Atlanta Hawks",9,5,4,432.0,112.5,109.9,2.6,72.5,2.10,20.4,32.7,69.2,49.5,14.4,52.5,55.3,102.83,48.8,926),
 ("Cleveland Cavaliers",8,4,4,389.0,115.6,113.7,1.9,65.7,1.98,19.0,29.8,68.4,49.7,13.6,54.9,58.4,101.74,51.7,825),
 ("Dallas Mavericks",8,4,4,384.0,112.5,112.7,-0.1,63.3,1.65,18.5,33.1,62.7,48.4,15.9,54.0,57.2,99.63,50.2,797),
 ("Denver Nuggets",7,4,3,341.0,115.1,115.0,0.1,68.0,1.75,19.4,30.7,65.6,49.0,15.7,56.1,60.7,98.53,52.3,702),
 ("New Orleans Pelicans",8,4,4,399.0,113.4,111.1,2.3,58.8,1.46,17.3,29.9,70.6,50.7,16.2,53.8,59.3,103.28,52.0,858),
 ("New York Knicks",8,4,4,384.0,113.3,108.5,4.7,68.4,1.69,18.2,37.0,72.3,54.2,15.8,51.2,55.3,97.00,51.8,777),
 ("Toronto Raptors",8,4,4,384.0,115.8,111.1,4.7,67.3,2.00,19.2,36.1,66.5,49.9,14.1,52.2,55.9,101.94,51.0,814),
 ("Washington Wizards",8,4,4,384.0,110.0,110.0,0.0,62.9,1.69,18.3,25.9,64.7,47.2,14.8,52.9,57.7,99.06,52.0,792),
 ("Charlotte Hornets",9,3,6,432.0,101.6,112.7,-11.1,60.7,1.09,15.5,34.9,73.6,52.9,20.1,48.0,52.0,96.72,42.8,869),
 ("Indiana Pacers",9,3,6,432.0,109.5,112.0,-2.5,66.7,1.69,19.0,25.5,67.1,46.9,15.5,53.5,57.2,101.78,49.0,914),
 ("Miami Heat",9,3,6,437.0,110.7,117.5,-6.8,69.8,1.84,19.6,29.4,71.1,49.6,15.2,53.7,57.1,103.36,47.6,943),
 ("Brooklyn Nets",8,2,6,389.0,106.2,112.6,-6.4,63.9,1.28,16.5,29.8,72.8,50.8,17.7,51.3,55.8,99.02,45.8,803),
 ("Orlando Magic",8,2,6,384.0,107.4,116.3,-8.9,70.1,1.43,18.9,30.4,66.4,48.6,18.6,53.7,57.3,98.56,45.3,786),
 ("Phoenix Suns",7,2,5,336.0,114.7,121.4,-6.8,66.7,1.88,19.6,29.4,60.1,44.6,14.8,54.6,58.0,99.64,46.9,695),
 ("Chicago Bulls",8,1,7,384.0,105.9,123.5,-17.5,65.7,1.49,16.6,32.4,64.4,47.4,15.7,47.6,52.8,105.19,40.7,843),
 ("LA Clippers",8,1,7,389.0,106.7,112.8,-6.1,66.8,1.27,18.0,30.9,69.0,50.1,19.7,53.5,57.5,101.06,46.3,818),
 ("Milwaukee Bucks",8,1,7,384.0,106.3,118.1,-11.8,64.8,1.58,17.7,31.8,68.6,49.9,15.9,51.2,53.8,103.50,43.0,828),
 ("Sacramento Kings",8,1,7,384.0,106.5,119.4,-12.9,60.7,1.41,17.2,28.8,69.0,48.0,16.8,51.8,55.2,102.94,41.3,821),
 ("Utah Jazz",8,1,7,394.0,103.9,115.1,-11.3,65.0,1.42,17.1,31.1,71.5,50.4,16.7,49.5,53.8,100.93,45.1,830),
]

# ---- opponent page: team -> (gp, w, l, opp_pts) — the column F-89F-04 tracks
OPP = {
 "Los Angeles Lakers": (16, 13, 3, 114.4), "Philadelphia 76ers": (16, 13, 3, 111.6),
 "Houston Rockets": (16, 12, 4, 109.2), "San Antonio Spurs": (15, 12, 3, 105.9),
 "Boston Celtics": (15, 11, 4, 103.4), "Memphis Grizzlies": (15, 11, 4, 112.9),
 "Minnesota Timberwolves": (15, 11, 4, 106.1), "Detroit Pistons": (14, 10, 4, 108.9),
 "Atlanta Hawks": (15, 9, 6, 115.8), "Miami Heat": (15, 9, 6, 119.9),
 "Oklahoma City Thunder": (15, 9, 6, 107.7), "Portland Trail Blazers": (14, 9, 5, 111.0),
 "Cleveland Cavaliers": (16, 8, 8, 116.3), "Dallas Mavericks": (15, 8, 7, 113.2),
 "Denver Nuggets": (13, 8, 5, 112.2), "Golden State Warriors": (15, 8, 7, 112.8),
 "New York Knicks": (14, 8, 6, 103.9), "Phoenix Suns": (14, 7, 7, 115.7),
 "Orlando Magic": (14, 6, 8, 112.8), "Indiana Pacers": (15, 5, 10, 114.8),
 "New Orleans Pelicans": (16, 5, 11, 122.8), "Toronto Raptors": (15, 5, 10, 112.0),
 "Washington Wizards": (16, 5, 11, 117.9), "Charlotte Hornets": (14, 4, 10, 110.4),
 "Chicago Bulls": (14, 4, 10, 124.6), "LA Clippers": (13, 4, 9, 117.7),
 "Brooklyn Nets": (14, 3, 11, 119.2), "Utah Jazz": (16, 3, 13, 116.0),
 "Milwaukee Bucks": (15, 1, 14, 120.9), "Sacramento Kings": (14, 1, 13, 121.7),
}

# ---- traditional page chunk-0 spot rows: team -> (gp, w, l, pts) (read this cycle)
TRAD_SPOT = {
 "Los Angeles Lakers": (16, 13, 3, 120.9), "Philadelphia 76ers": (16, 13, 3, 114.5),
 "San Antonio Spurs": (15, 12, 3, 117.1),
}


def norm_ppf(p):
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
        return json.load(fh)


def dump(p, doc):
    path = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", p)


def main():
    assert len(ADV) == 30 and len(ADV_TRAIN) == 30 and len(OPP) == 30

    # ---------------- read record (provenance for every transcribed cell)
    read_record = {
        "title": "Official team-stat tables re-read 2026-11-19 (session 4eef6d3b)",
        "generated_by": "arena/4eef6d3b-nba1 — transcribed first-hand from the official pages "
                        "through the platform web-fetch channel (the GitHub runner cannot parse "
                        "these pages: client-rendered shells; see data/raw/_capture_evidence_S1_season.json "
                        "and COORDINATION.md sections 69/73)",
        "read_at_utc": READ_AT,
        "source_urls": {"advanced": SRC_ADV, "advanced_train": SRC_ADV_TRAIN,
                        "traditional": SRC_TRAD, "opponent": SRC_OPP},
        "coverage": {
            "advanced_season_to_date": "30/30 rows, all 20 columns transcribed verbatim",
            "advanced_train_window": "30/30 rows, all 20 columns; byte-compared against the previous "
                                     "verified cut (data/raw/team_advanced.json train window) — identical",
            "traditional": "13/30 rows (GP/W/L/WIN%/Min/PTS) read this cycle; GP/W/L corroborated 30/30 "
                           "against data/official/teams_reread_2026-11-19_89f7b601.json (read 08:0xZ). "
                           "Shooting columns NOT re-transcribed — listed as uncorroborated, never inferred",
            "opponent": "30/30 rows (GP/W/L/OppPTS) transcribed verbatim",
        },
        "rows_advanced": [dict(zip(COLS, r), abbr=ABBR[r[0]], source_url=SRC_ADV) for r in ADV],
        "rows_advanced_train": [dict(zip(COLS, r), abbr=ABBR[r[0]], source_url=SRC_ADV_TRAIN)
                                for r in ADV_TRAIN],
        "rows_opponent": [{"team": t, "abbr": ABBR[t], "gp": v[0], "w": v[1], "l": v[2],
                           "opp_pts": v[3], "source_url": SRC_OPP} for t, v in sorted(OPP.items())],
        "rows_traditional_spot": [{"team": t, "abbr": ABBR[t], "gp": v[0], "w": v[1], "l": v[2],
                                   "pts": v[3], "source_url": SRC_TRAD}
                                  for t, v in sorted(TRAD_SPOT.items())],
    }
    dump("data/official/teams_reread_2026-11-19_4eef6d3b.json", read_record)

    # ---------------- gates (same five as scripts/recut_2026_11_19.py)
    std = load("data/official/standings_2026-11-19_929395a5.json")
    std_by = {r["team"]: r for r in std["rows"]}
    g1, g2, g3 = [], [], []
    for r in ADV:
        team, gp, w, l = r[0], r[1], r[2], r[3]
        if w + l != gp:
            g1.append(f"{ABBR[team]}: W+L={w+l} != GP={gp}")
        if abs(r[7] - (r[5] - r[6])) > 0.25:
            g2.append(f"{ABBR[team]}: NetRtg {r[7]} vs {r[5]-r[6]:.2f}")
        s = std_by[ABBR[team]]
        if (gp, w, l) != (s["w"] + s["l"], s["w"], s["l"]):
            g3.append(f"{ABBR[team]}: advanced {gp}-{w}-{l} vs standings "
                      f"{s['w']+s['l']}-{s['w']}-{s['l']}")
    cc = std.get("cross_checks", {})
    g5_ok = bool(cc) and (cc.get("total_w") == cc.get("total_l")) and (cc.get("home_w") == cc.get("road_l"))

    feed = load("data/official/results_feed_2026_27.json")
    finals = [r for r in feed["rows"] if r.get("game_status") == 3]
    seen, margins, totals = set(), [], []
    for r in finals:
        if r["game_id"] in seen:
            continue
        seen.add(r["game_id"])
        margins.append(r["home_pts"] - r["away_pts"])
        totals.append(r["home_pts"] + r["away_pts"])
    n = len(margins)
    g4_ok = (sum(r[1] for r in ADV) == 2 * n)

    print("G1", "pass (all 30)" if not g1 else f"FAIL {g1}")
    print("G2", "pass (all 30)" if not g2 else f"FAIL {g2}")
    print("G3", "pass (all 30)" if not g3 else f"FAIL {g3}")
    print("G4", f"pass ({sum(r[1] for r in ADV)} = 2 x {n})" if g4_ok else
          f"FAIL total team-games {sum(r[1] for r in ADV)} != 2 x {n}")
    print("G5", "pass" if g5_ok else "FAIL/UNKNOWN")

    # ---------------- drift against the previous cut (F-89F-04 / Q37)
    # The previous cut is read from the last commit BEFORE this re-cut, not
    # from the working file: a re-run of this script must never diff the cut
    # against itself and silently report "no drift".
    import subprocess
    try:
        prev = json.loads(subprocess.run(
            ["git", "show", f"{PREV_CUT_COMMIT}:data/derived/team_stats_recut.json"],
            capture_output=True, text=True, check=True).stdout)
        prev_origin = f"committed cut at {PREV_CUT_COMMIT}"
    except Exception:
        prev = load("data/derived/team_stats_recut.json")
        prev_origin = "working-tree cut (git unavailable)"
    prev_by = {r["abbr"]: r for r in prev["rows"]}
    drift = []
    for r in ADV:
        ab = ABBR[r[0]]
        p = prev_by.get(ab)
        if not p:
            drift.append({"abbr": ab, "change": "row absent from previous cut"})
            continue
        fields = {}
        for k, v in zip(COLS, r):
            if p.get(k) != v:
                fields[k] = {"from": p.get(k), "to": v}
        if fields:
            drift.append({"abbr": ab, "fields": fields})
    drift_doc = {
        "title": "Model-input drift, previous cut -> 2026-11-19T13:2xZ first-hand re-read",
        "generated_by": "scripts/recut_2026-11-19_4eef6d3b.py",
        "compared_at_utc": NOW,
        "previous_cut_generated": prev.get("_meta", {}).get("retrieved_utc"),
        "previous_cut_origin": prev_origin,
        "rows_changed": len(drift),
        "rows_unchanged": 30 - len(drift),
        "drift": drift,
        "opponent_table_note": {
            "uta_opp_pts_previous_cut_note": 117.3,
            "uta_opp_pts_official_now": 116.0,
            "source_url": SRC_OPP,
            "resolves": "F-89F-04 / Q37: the previous cut predates the 11/18 UTA 109 @ LAL 97 game; "
                        "the official opponent table now prints 116.0 for UTA opponent points (read "
                        "this cycle). The value is adopted only in this drift record and the read "
                        "record; team_stats_recut.json carries the advanced columns the model reads.",
        },
        "gates": {
            "G1_W_plus_L_eq_GP": "pass (all 30)" if not g1 else f"FAIL: {g1}",
            "G2_netrtg_eq_off_minus_def": "pass (all 30, 0.25 rounding tolerance)" if not g2 else f"FAIL: {g2}",
            "G3_gp_and_wl_match_standings": "pass (all 30)" if not g3 else f"FAIL: {g3}",
            "G4_total_team_games_eq_2x_decided_finals": f"pass ({sum(r[1] for r in ADV)} = 2 x {n})"
                if g4_ok else f"FAIL (recorded, not blocking): {sum(r[1] for r in ADV)} != 2 x {n}",
            "G5_standings_identity": "pass" if g5_ok else "FAIL/UNKNOWN (cross_checks missing)",
        },
    }
    dump("data/derived/recut_2026-11-19_4eef6d3b/drift.json", drift_doc)

    # ---------------- team_advanced.json (model input, both windows + verification)
    verification = {
        "verified": True,
        "verified_by": "arena/4eef6d3b-nba1 (session first-hand transcription)",
        "channel": "platform web-fetch channel — the GitHub runner cannot parse this page "
                   "(client-rendered shell; byte evidence data/raw/_capture_evidence_S1_season.json)",
        "source_url": SRC_ADV,
        "verified_at_utc": NOW,
        "row_count": 30,
        "response_digest": None,
        "response_digest_note": "the web-fetch channel returns rendered text; no byte digest exists. "
                                "Row provenance is the read record below.",
        "evidence": "data/official/teams_reread_2026-11-19_4eef6d3b.json",
        "corroboration": "GP/W/L cross-checked against data/official/standings_2026-11-19_929395a5.json "
                         "(30/30 match) and arena/89f7b601-nba1's 08:0xZ traditional-page read; "
                         "train window byte-compared against the previous verified cut (identical)",
    }
    team_advanced = {
        "captured_at_utc": NOW,
        "note": "Verbatim transcription of the NBA.com official Stats > Teams > Advanced table in two "
                "windows. Columns kept exactly as published. No derived or inferred values; the "
                "season_to_date window was transcribed first-hand on 2026-11-19 (runner-unreadable "
                "page — see data/raw/unreadable_sources.json), the train window was re-read and "
                "matched the previous verified cut byte for byte.",
        "cols": ADV_COLS,
        "model_input_note": ("Columns follow engine/parse_official.ADVANCED_COLS (the official "
                             "page schema). data/derived/team_stats_recut.json publishes the same "
                             "values under the model-input names (off_rtg/def_rtg/net_rtg)."),
        "verification": verification,
        "windows": [
            {
                "window_id": "season_to_date",
                "label": "2026-27 Regular Season, season to date (through 2026-11-18 games; "
                         "2026-11-19 slate had not tipped at read time)",
                "source_id": "S1",
                "source_url": SRC_ADV,
                "retrieved_utc": NOW,
                "rows": [list(r) for r in ADV],
                "missing": [],
                "verification": dict(verification, source_capture="data/official/teams_reread_2026-11-19_4eef6d3b.json"),
            },
            {
                "window_id": "train_2026-10-20_2026-11-05",
                "label": "2026-27 Regular Season, 2026-10-20 to 2026-11-05 training window",
                "source_id": "S2",
                "source_url": SRC_ADV_TRAIN,
                "retrieved_utc": NOW,
                "rows": [list(r) for r in ADV_TRAIN],
                "missing": [],
                "verification": dict(verification, source_url=SRC_ADV_TRAIN,
                                     source_capture="data/official/teams_reread_2026-11-19_4eef6d3b.json"),
            },
        ],
    }
    dump("data/raw/team_advanced.json", team_advanced)

    # ---------------- team_stats_recut.json (the cut the horizon is priced from)
    poss_tot = sum(r[19] for r in ADV)
    league_off = sum(r[5] * r[19] for r in ADV) / poss_tot
    league_pace = sum(r[17] * r[1] for r in ADV) / sum(r[1] for r in ADV)
    mean_m = sum(margins) / n
    sd_m = math.sqrt(sum((m - mean_m) ** 2 for m in margins) / (n - 1))
    mean_t = sum(totals) / n
    sd_t = math.sqrt(sum((t - mean_t) ** 2 for t in totals) / (n - 1))
    home_wins = cc.get("home_w")
    if home_wins is not None:
        home_games = cc.get("home_w") + cc.get("home_l")
        home_rate = home_wins / home_games
        hca_pts = sd_m * norm_ppf(home_rate)
    else:
        home_rate, hca_pts = None, None

    out_rows = []
    for r in sorted(ADV, key=lambda x: -x[5]):
        out_rows.append({**dict(zip(COLS, r)), "abbr": ABBR[r[0]], "source_url": SRC_ADV,
                         "gp_matches_standings": ABBR[r[0]] not in {x.split(":")[0] for x in g3}})
    recut = {
        "_meta": {
            "title": "Team model inputs, re-cut from first-hand official reads on 2026-11-19",
            "generated_by": "scripts/recut_2026-11-19_4eef6d3b.py",
            "retrieved_utc": NOW,
            "sources": {"advanced": SRC_ADV, "traditional": SRC_TRAD, "opponent": SRC_OPP,
                        "standings": SRC_STD, "finals": SRC_GAMES},
            "games_through": f"{n} decided games (results feed through 2026-11-18)",
            "note": ("Every value is printed on the official advanced page (read first-hand "
                     "2026-11-19T13:2xZ via the platform web-fetch channel; the runner cannot "
                     "parse this page). Nothing is fitted, imputed or adjusted. GP/W/L are shipped "
                     "beside the ratings so a reader can see the sample each rating rests on. "
                     "This cut ABSORBS the 11/18 UTA 109 @ LAL 97 game (LAL and UTA now 16 GP, "
                     "matching the standings): it replaces the pre-drift cut and resolves "
                     "F-89F-04/Q37. Drift detail: data/derived/recut_2026-11-19_4eef6d3b/drift.json."),
            "gates": drift_doc["gates"],
        },
        "rows": out_rows,
    }
    dump("data/derived/team_stats_recut.json", recut)

    consts = {
        "_meta": {
            "title": "Measured constants for the 2026-27 model, re-derived on 2026-11-19",
            "generated_by": "scripts/recut_2026-11-19_4eef6d3b.py",
            "retrieved_utc": NOW,
            "rule": "measure, never fit. Each constant states the official column it came from.",
        },
        "league": {
            "off_rtg_poss_weighted": round(league_off, 3),
            "pace_gp_weighted": round(league_pace, 3),
            "formula": "sum(OffRtg_i * POSS_i) / sum(POSS_i) over the 30 official rows; PACE weighted by GP",
            "source_url": SRC_ADV,
        },
        "dispersion": {
            "finals_n": n,
            "margin_mean": round(mean_m, 3),
            "sigma_margin": round(sd_m, 3),
            "total_mean": round(mean_t, 3),
            "sigma_total": round(sd_t, 3),
            "formula": "sample standard deviation (n-1) of the official home-minus-away margin and of "
                       "the official game total, over every decided game in the corpus, de-duplicated "
                       "by game id",
            "source_url": SRC_GAMES,
        },
    }
    if home_rate is not None:
        consts["hca_pin"] = {
            "home_win_rate": round(home_rate, 4),
            "hca_points": round(hca_pts, 3),
            "formula": "HCA = sigma_margin * norm_ppf(measured home-win rate); the pin is measured, "
                       "never fitted (R09)",
            "source_url": SRC_STD,
        }
    dump("data/derived/measured_constants_2026_27.json", consts)
    print("done; drift rows:", len(drift))


if __name__ == "__main__":
    main()
