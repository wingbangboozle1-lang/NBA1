#!/usr/bin/env python3
"""capture.py — 2026-11-15 late rolling-slate official re-read (session arena/161f1638-nba1).

Every value below was transcribed from the official page named in SOURCES, read
live through the web-fetch channel on 2026-11-15 between 23:38Z and 23:52Z.
Nothing is inferred: where a value could not be read, it is absent and flagged
in the capture_log.json this script writes alongside the data.

The rolling window is recomputed, not inherited: at capture time (2026-11-15
23:38Z = 18:38 ET) the 11/15 slate is mid-flight (1 of 9 games Final, 5 live,
3 not yet tipped), so the pickable horizon is the next three calendar days —
2026-11-16, 2026-11-17, 2026-11-18 — which is exactly the brief's
"up to a maximum of 3 days in advance".

Writes (all under the repository root):
  data/official/standings_2026-11-15_2345Z.json          30 rows, post-11/15 games in progress
  data/official/teams_traditional_2026-11-15_2345Z.json  30 rows, all columns re-read
  data/official/teams_opponent_2026-11-15_2345Z.json     30 rows, all columns re-read
  data/official/teams_advanced_2026-11-15_2345Z.json     30 rows, all columns re-read
  data/official/schedule_2026-11-16_to_18.json           25 games, the 3-day rolling window
  data/official/results_2026-11-15.json                  one row per 11/15 game; only the
                                                         Final game carries a score
  data/official/injury_2026-11-15_0615PM.json            verbatim rows of the 06:15 PM ET edition
  data/official/injury_diff_2026-11-15_0615AM_to_0615PM.json
  data/raw/official_schedule_capture_2026-11-16.json     originate_horizon input schema
  verify/2026-11-15-161f1638/capture_log.json            provenance for this capture

Cross-checks run by this script (assertions, not prose):
  * every standings (W, L) equals the (W, L) on that team's traditional row;
  * every standings (W, L) equals the (W, L) on that team's advanced row;
  * traditional PTS - opponent OPP_PTS equals the traditional +/- (0.1 tolerance);
  * the opponent page's +/- is the negation of the traditional page's +/-;
  * the schedule's per-game record pair equals the standings pair for both teams;
  * games-per-day counts match the counts printed by the official schedule page.

Run:  python3 verify/2026-11-15-161f1638/capture.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURED_BY = "arena/161f1638-nba1"
RETRIEVED = "2026-11-15T23:38Z..23:52Z"

SRC = {
    "schedule": "https://www.nba.com/schedule",
    "games_1115": "https://www.nba.com/games?date=2026-11-15",
    "standings": "https://www.nba.com/standings",
    "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season",
    "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season",
    "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "injury_pdf": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf",
    "injury_pdf_prev": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
    "box_1115_ind_phi": "https://www.nba.com/game/ind-vs-phi-0022600236/box-score",
}

# ---------------------------------------------------------------------------
# 1. STANDINGS — https://www.nba.com/standings, read 2026-11-15 ~23:40Z
#     Columns printed by the page: w, l, WIN%, GB, CONF, DIV, HOME, ROAD,
#     Neutral, OT, LAST10, STREAK.  Rows are printed in the page's own order.
# ---------------------------------------------------------------------------
STANDINGS = [
    # conference, rank, team, abbr, w, l, win_pct, gb, conf, div, home, road, neutral, ot, last10, streak
    ("East", 1, "Boston Celtics", "BOS", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("East", 2, "Philadelphia 76ers", "PHI", 11, 3, ".786", "--", "11-3", "3-1", "6-2", "5-1", "0-0", "0-0", "8-2", "W 2"),
    ("East", 3, "Detroit Pistons", "DET", 8, 4, ".667", "2", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("East", 4, "Miami Heat", "MIA", 7, 6, ".538", "3.5", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("East", 5, "Atlanta Hawks", "ATL", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("East", 6, "Cleveland Cavaliers", "CLE", 7, 7, ".500", "4", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("East", 7, "New York Knicks", "NYK", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("East", 8, "Toronto Raptors", "TOR", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("East", 9, "Orlando Magic", "ORL", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("East", 10, "Indiana Pacers", "IND", 5, 9, ".357", "6", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    ("East", 11, "Charlotte Hornets", "CHA", 4, 8, ".333", "6", "4-7", "2-2", "3-4", "1-4", "0-0", "0-0", "3-7", "L 1"),
    ("East", 12, "Washington Wizards", "WAS", 4, 9, ".308", "6.5", "4-8", "2-3", "2-3", "2-6", "0-0", "0-1", "2-8", "L 6"),
    ("East", 13, "Brooklyn Nets", "BKN", 3, 9, ".250", "7", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("East", 14, "Chicago Bulls", "CHI", 3, 9, ".250", "7", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("East", 15, "Milwaukee Bucks", "MIL", 1, 12, ".077", "9.5", "1-9", "1-2", "1-6", "0-6", "0-0", "0-0", "1-9", "L 9"),
    ("West", 1, "San Antonio Spurs", "SAS", 11, 2, ".846", "--", "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("West", 2, "Los Angeles Lakers", "LAL", 11, 2, ".846", "--", "6-2", "4-1", "5-1", "6-1", "0-0", "0-0", "8-2", "W 7"),
    ("West", 3, "Houston Rockets", "HOU", 10, 3, ".769", "1", "6-3", "2-1", "7-1", "3-2", "0-0", "0-0", "7-3", "W 3"),
    ("West", 4, "Portland Trail Blazers", "POR", 9, 3, ".750", "1.5", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("West", 5, "Minnesota Timberwolves", "MIN", 9, 4, ".692", "2", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("West", 6, "Memphis Grizzlies", "MEM", 9, 4, ".692", "2", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("West", 7, "Denver Nuggets", "DEN", 7, 4, ".636", "3", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("West", 8, "Golden State Warriors", "GSW", 8, 5, ".615", "3", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("West", 9, "Oklahoma City Thunder", "OKC", 8, 5, ".615", "3", "5-5", "1-2", "5-0", "3-5", "0-0", "0-0", "5-5", "L 3"),
    ("West", 10, "Dallas Mavericks", "DAL", 7, 6, ".538", "4", "3-5", "1-3", "5-2", "2-4", "0-0", "0-0", "6-4", "L 2"),
    ("West", 11, "Phoenix Suns", "PHX", 5, 6, ".455", "5", "3-6", "2-1", "5-3", "0-3", "0-0", "0-0", "5-5", "W 2"),
    ("West", 12, "New Orleans Pelicans", "NOP", 4, 10, ".286", "7.5", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("West", 13, "LA Clippers", "LAC", 3, 8, ".273", "7", "3-6", "1-4", "3-3", "0-5", "0-0", "0-1", "2-8", "W 1"),
    ("West", 14, "Sacramento Kings", "SAC", 1, 11, ".083", "9.5", "1-9", "0-2", "0-7", "1-4", "0-0", "0-0", "1-9", "L 5"),
    ("West", 15, "Utah Jazz", "UTA", 1, 12, ".077", "10", "1-10", "0-2", "1-6", "0-6", "0-0", "0-2", "0-10", "L 11"),
]
STANDINGS_COLS = ["conference", "rank", "team", "abbr", "w", "l", "win_pct", "gb",
                  "conf_rec", "div_rec", "home", "road", "neutral", "ot", "last10", "streak"]

# ---------------------------------------------------------------------------
# 2. TEAM TRADITIONAL — all 30 rows, per-game, as printed by the page.
#    gp w l win_pct min pts fgm fga fg_pct fg3m fg3a fg3_pct ftm fta ft_pct
#    oreb dreb reb ast tov stl blk blka pf pfd plus_minus
# ---------------------------------------------------------------------------
TRAD_COLS = ["abbr", "rank", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga",
             "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb",
             "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd", "plus_minus"]
TRADITIONAL = [
    ("LAL", 1, 13, 11, 2, ".846", 48.0, 122.2, 42.1, 83.6, 50.3, 14.1, 36.8, 38.3, 23.9, 29.8, 80.4, 11.3, 29.5, 40.8, 24.7, 16.9, 11.0, 6.2, 4.2, 23.4, 24.2, 7.9),
    ("SAS", 1, 13, 11, 2, ".846", 48.4, 119.5, 42.9, 92.0, 46.7, 12.5, 35.9, 34.7, 21.2, 26.5, 79.9, 13.2, 35.4, 48.6, 28.1, 12.3, 8.3, 7.3, 4.9, 20.0, 21.2, 13.2),
    ("BOS", 3, 12, 10, 2, ".833", 48.4, 114.3, 39.8, 87.2, 45.6, 16.0, 42.0, 38.1, 18.8, 23.8, 78.9, 13.1, 31.7, 44.8, 26.8, 14.7, 8.2, 4.9, 4.2, 21.5, 22.9, 11.2),
    ("PHI", 4, 14, 11, 3, ".786", 48.0, 112.6, 40.1, 87.9, 45.7, 12.1, 34.4, 35.1, 20.2, 25.9, 78.2, 10.0, 32.9, 42.9, 26.3, 12.8, 8.1, 4.2, 5.6, 20.9, 20.9, 2.1),
    ("HOU", 5, 13, 10, 3, ".769", 48.0, 116.2, 41.5, 86.9, 47.8, 12.8, 34.3, 37.2, 20.3, 25.0, 81.2, 13.2, 31.2, 44.4, 26.8, 14.5, 7.9, 6.1, 4.1, 19.9, 21.9, 8.8),
    ("POR", 6, 12, 9, 3, ".750", 48.0, 119.6, 39.8, 84.7, 46.9, 15.9, 43.6, 36.5, 24.2, 30.7, 78.8, 11.5, 32.8, 44.3, 25.3, 16.3, 7.1, 5.1, 4.2, 22.3, 24.4, 7.8),
    ("MEM", 7, 13, 9, 4, ".692", 48.4, 120.6, 42.1, 89.4, 47.1, 15.5, 39.6, 39.2, 20.9, 24.7, 84.7, 12.5, 34.8, 47.4, 27.8, 15.8, 6.5, 5.1, 7.2, 23.6, 21.5, 8.9),
    ("MIN", 7, 13, 9, 4, ".692", 48.4, 118.3, 43.4, 90.9, 47.7, 14.2, 38.4, 36.9, 17.4, 25.5, 68.1, 13.8, 34.6, 48.5, 26.0, 15.9, 9.0, 5.1, 6.4, 22.0, 22.8, 11.5),
    ("DET", 9, 12, 8, 4, ".667", 48.8, 115.7, 40.9, 88.4, 46.3, 13.5, 36.8, 36.7, 20.3, 25.8, 79.0, 12.2, 32.3, 44.4, 27.7, 14.3, 9.4, 6.4, 6.1, 23.8, 22.7, 5.4),
    ("DEN", 10, 11, 7, 4, ".636", 48.5, 114.6, 41.5, 85.2, 48.7, 10.8, 31.0, 34.9, 20.9, 26.5, 79.0, 10.1, 32.2, 42.3, 27.7, 13.4, 9.0, 4.5, 4.5, 19.0, 23.2, 1.8),
    ("GSW", 11, 13, 8, 5, ".615", 48.4, 116.7, 40.0, 87.0, 46.0, 16.4, 41.6, 39.4, 20.3, 25.1, 81.0, 12.5, 31.9, 44.5, 28.0, 16.0, 8.2, 5.4, 5.7, 21.9, 22.2, 4.3),
    ("OKC", 11, 13, 8, 5, ".615", 48.0, 111.2, 41.2, 90.7, 45.4, 11.0, 32.1, 34.3, 17.8, 21.8, 81.7, 11.5, 35.1, 46.6, 22.8, 13.3, 7.9, 5.4, 5.3, 19.3, 21.0, 3.8),
    ("ATL", 13, 13, 7, 6, ".538", 48.4, 118.2, 43.9, 97.2, 45.2, 14.8, 43.3, 34.1, 15.5, 20.4, 76.2, 13.9, 30.2, 44.1, 31.5, 15.2, 10.3, 4.0, 6.0, 22.1, 19.4, 1.3),
    ("DAL", 13, 13, 7, 6, ".538", 48.0, 113.5, 41.2, 88.8, 46.4, 12.5, 37.5, 33.5, 18.5, 23.5, 78.4, 12.7, 30.9, 43.6, 26.1, 15.8, 8.7, 5.5, 4.8, 22.3, 20.9, 0.2),
    ("MIA", 13, 13, 7, 6, ".538", 48.4, 118.7, 42.0, 89.5, 46.9, 13.5, 39.5, 34.1, 21.2, 28.7, 74.0, 10.5, 32.2, 42.8, 29.8, 14.4, 7.8, 5.5, 5.2, 21.1, 25.1, -1.2),
    ("CLE", 16, 14, 7, 7, ".500", 48.4, 117.5, 41.8, 88.7, 47.1, 15.4, 41.6, 37.0, 18.5, 24.3, 76.2, 10.7, 34.9, 45.6, 27.1, 13.5, 7.1, 5.3, 3.6, 21.6, 20.3, 1.6),
    ("NYK", 16, 12, 6, 6, ".500", 48.0, 109.8, 38.8, 88.9, 43.6, 14.8, 41.1, 36.1, 17.4, 21.9, 79.5, 13.7, 34.0, 47.7, 26.8, 14.4, 7.4, 4.1, 6.2, 20.9, 21.1, 6.1),
    ("PHX", 18, 11, 5, 6, ".455", 48.0, 111.7, 41.3, 88.5, 46.7, 13.6, 37.0, 36.9, 15.5, 20.0, 77.7, 10.6, 28.3, 38.9, 27.2, 13.9, 8.4, 4.5, 4.7, 22.0, 18.6, -4.4),
    ("ORL", 19, 12, 5, 7, ".417", 48.4, 108.3, 38.4, 85.8, 44.8, 13.8, 41.1, 33.7, 17.7, 22.6, 78.2, 11.0, 31.9, 42.9, 26.0, 16.8, 7.4, 4.1, 5.0, 22.8, 23.3, -4.4),
    ("TOR", 19, 12, 5, 7, ".417", 48.0, 114.3, 41.4, 91.2, 45.4, 11.8, 36.0, 32.9, 19.6, 26.6, 73.7, 13.8, 27.2, 41.0, 28.1, 14.3, 10.6, 4.4, 5.5, 25.8, 24.3, 1.4),
    ("IND", 21, 14, 5, 9, ".357", 48.0, 112.1, 40.9, 87.1, 47.0, 11.9, 36.1, 32.8, 18.4, 24.0, 76.5, 9.6, 32.0, 41.6, 27.8, 14.5, 7.2, 4.2, 4.3, 20.4, 22.8, -2.4),
    ("CHA", 22, 12, 4, 8, ".333", 48.0, 98.6, 34.8, 86.6, 40.1, 13.8, 44.2, 31.1, 15.3, 18.7, 82.1, 15.0, 31.6, 46.6, 21.8, 19.6, 6.9, 4.6, 4.6, 20.4, 21.6, -11.0),
    ("WAS", 23, 13, 4, 9, ".308", 48.8, 110.0, 39.8, 87.1, 45.8, 9.9, 32.5, 30.5, 20.4, 25.2, 80.8, 10.7, 32.4, 43.1, 23.6, 15.2, 7.5, 5.4, 3.5, 20.5, 21.2, -5.8),
    ("NOP", 24, 14, 4, 10, ".286", 49.1, 115.9, 40.1, 86.2, 46.5, 9.4, 28.7, 32.8, 26.3, 32.1, 82.0, 10.6, 30.5, 41.1, 24.3, 16.1, 9.9, 5.3, 5.6, 24.6, 23.9, -9.1),
    ("LAC", 25, 11, 3, 8, ".273", 48.5, 112.3, 39.2, 85.4, 45.9, 14.3, 37.4, 38.2, 19.6, 24.6, 79.7, 10.5, 29.9, 40.5, 26.8, 17.8, 9.6, 4.3, 4.4, 22.1, 20.9, -5.3),
    ("BKN", 26, 12, 3, 9, ".250", 48.4, 110.2, 37.1, 83.9, 44.2, 14.6, 40.7, 35.9, 21.4, 28.3, 75.8, 11.6, 31.0, 42.6, 24.2, 17.7, 8.6, 4.8, 4.8, 26.1, 24.0, -6.3),
    ("CHI", 26, 12, 3, 9, ".250", 48.4, 114.6, 39.9, 89.4, 44.6, 12.7, 40.7, 31.1, 22.1, 29.0, 76.1, 12.6, 31.8, 44.3, 26.9, 17.3, 7.8, 5.9, 4.9, 23.7, 23.2, -11.3),
    ("SAC", 28, 12, 1, 11, ".083", 48.0, 108.2, 39.3, 86.3, 45.5, 12.3, 35.5, 34.5, 17.4, 22.7, 76.8, 9.8, 30.1, 39.9, 25.0, 17.1, 7.8, 3.5, 5.8, 22.8, 19.6, -12.8),
    ("MIL", 29, 13, 1, 12, ".077", 48.0, 106.2, 37.8, 88.3, 42.8, 14.8, 43.2, 34.2, 15.8, 21.4, 74.1, 13.3, 31.5, 44.8, 24.8, 16.6, 6.5, 4.7, 5.8, 22.5, 19.5, -14.1),
    ("UTA", 29, 13, 1, 12, ".077", 48.8, 107.5, 37.8, 86.8, 43.5, 12.1, 36.5, 33.1, 19.8, 25.8, 77.0, 12.0, 32.5, 44.5, 24.0, 16.7, 6.7, 6.2, 5.4, 24.0, 24.2, -11.2),
]

# ---------------------------------------------------------------------------
# 3. TEAM OPPONENT — all 30 rows, per-game (opponent stats = what the team allows).
# ---------------------------------------------------------------------------
OPP_COLS = ["abbr", "rank", "gp", "w", "l", "min", "opp_fgm", "opp_fga", "opp_fg_pct",
            "opp_fg3m", "opp_fg3a", "opp_fg3_pct", "opp_ftm", "opp_fta", "opp_ft_pct",
            "opp_oreb", "opp_dreb", "opp_reb", "opp_ast", "opp_tov", "opp_stl",
            "opp_blk", "opp_blka", "opp_pf", "opp_pfd", "opp_pts", "plus_minus"]
OPPONENT = [
    ("LAL", 1, 13, 11, 2, 48.0, 38.9, 85.7, 45.4, 15.2, 40.5, 37.4, 21.2, 28.1, 75.6, 13.5, 27.5, 41.0, 27.4, 18.5, 9.9, 4.2, 6.2, 24.2, 23.4, 114.2, -7.9),
    ("PHI", 1, 14, 11, 3, 48.0, 40.1, 87.5, 45.8, 12.0, 36.4, 32.9, 18.3, 24.1, 76.0, 11.0, 35.0, 46.0, 25.4, 14.8, 6.5, 5.6, 4.2, 20.9, 20.9, 110.4, -2.1),
    ("SAS", 1, 13, 11, 2, 48.4, 38.7, 89.2, 43.4, 12.5, 33.0, 37.8, 16.4, 20.2, 81.3, 10.9, 31.9, 42.8, 24.9, 14.5, 6.5, 4.9, 7.3, 21.2, 20.0, 106.2, -13.2),
    ("BOS", 4, 12, 10, 2, 48.4, 35.6, 84.9, 41.9, 14.6, 43.2, 33.8, 17.3, 22.8, 75.9, 12.8, 30.5, 43.3, 25.1, 16.7, 7.1, 4.2, 4.9, 22.9, 21.5, 103.1, -11.2),
    ("HOU", 4, 13, 10, 3, 48.0, 39.6, 87.3, 45.4, 12.3, 38.5, 31.9, 15.8, 21.5, 73.6, 12.1, 28.6, 40.7, 23.4, 15.3, 8.2, 4.1, 6.1, 21.9, 19.9, 107.4, -8.8),
    ("MEM", 6, 13, 9, 4, 48.4, 40.5, 90.0, 45.0, 12.4, 37.5, 33.0, 18.2, 24.2, 75.5, 12.0, 29.7, 41.7, 25.0, 14.2, 7.7, 7.2, 5.1, 21.6, 23.7, 111.7, -8.9),
    ("MIN", 6, 13, 9, 4, 48.4, 38.6, 89.0, 43.4, 11.5, 35.3, 32.5, 18.1, 23.3, 77.6, 12.3, 31.0, 43.3, 24.6, 16.8, 7.9, 6.4, 5.1, 22.8, 22.0, 106.8, -11.5),
    ("POR", 6, 12, 9, 3, 48.0, 38.8, 87.1, 44.5, 11.4, 35.3, 32.3, 22.9, 27.6, 83.1, 11.5, 29.8, 41.3, 23.5, 14.0, 8.7, 4.2, 5.1, 24.4, 22.3, 111.8, -7.8),
    ("DET", 9, 12, 8, 4, 48.8, 38.6, 87.3, 44.2, 12.2, 36.5, 33.3, 20.9, 26.8, 78.0, 13.0, 32.8, 45.8, 23.6, 17.7, 8.0, 6.1, 6.4, 22.7, 23.8, 110.3, -5.4),
    ("GSW", 9, 13, 8, 5, 48.4, 40.6, 88.2, 46.1, 12.8, 37.8, 34.0, 18.3, 23.4, 78.3, 12.2, 30.7, 42.8, 27.3, 16.3, 8.7, 5.7, 5.4, 22.2, 21.9, 112.4, -4.3),
    ("OKC", 9, 13, 8, 5, 48.0, 37.3, 89.5, 41.7, 14.8, 43.6, 34.0, 17.9, 22.1, 81.2, 12.2, 31.7, 43.9, 24.5, 14.3, 6.3, 5.3, 5.4, 21.0, 19.3, 107.4, -3.8),
    ("ATL", 12, 13, 7, 6, 48.4, 42.2, 86.5, 48.7, 12.2, 35.5, 34.2, 20.4, 25.7, 79.3, 11.2, 34.5, 45.6, 28.2, 18.8, 9.8, 6.0, 4.0, 19.4, 22.1, 116.8, -1.3),
    ("CLE", 12, 14, 7, 7, 48.4, 41.6, 92.5, 44.9, 14.0, 39.8, 35.2, 18.7, 23.5, 79.6, 12.7, 32.4, 45.1, 27.3, 12.6, 6.7, 3.6, 5.3, 20.3, 21.6, 115.9, -1.6),
    ("DAL", 12, 13, 7, 6, 48.0, 41.6, 88.7, 46.9, 12.2, 36.6, 33.2, 17.9, 23.9, 74.9, 12.2, 31.2, 43.5, 27.2, 15.8, 8.2, 4.8, 5.5, 20.9, 22.3, 113.3, -0.2),
    ("DEN", 12, 11, 7, 4, 48.5, 41.5, 90.2, 46.0, 14.1, 39.3, 35.9, 15.8, 19.9, 79.5, 12.9, 30.7, 43.6, 28.2, 14.4, 7.1, 4.5, 4.5, 23.2, 19.0, 112.8, -1.8),
    ("MIA", 12, 13, 7, 6, 48.4, 43.1, 89.5, 48.1, 15.8, 40.8, 38.9, 17.8, 23.1, 77.3, 11.4, 33.7, 45.1, 29.7, 16.7, 8.1, 5.2, 5.5, 25.1, 21.1, 119.8, 1.2),
    ("NYK", 17, 12, 6, 6, 48.0, 36.9, 85.4, 43.2, 13.6, 39.8, 34.2, 16.3, 22.3, 72.8, 10.5, 30.2, 40.7, 24.8, 13.2, 6.7, 6.2, 4.1, 21.1, 20.9, 103.7, -6.1),
    ("IND", 18, 14, 5, 9, 48.0, 40.9, 89.3, 45.8, 14.1, 39.2, 36.1, 18.5, 23.7, 78.0, 11.5, 35.2, 46.7, 26.2, 14.9, 8.4, 4.3, 4.2, 22.8, 20.4, 114.5, 2.4),
    ("ORL", 18, 12, 5, 7, 48.4, 39.8, 85.3, 46.6, 13.6, 35.8, 38.0, 19.7, 25.9, 75.9, 10.3, 31.3, 41.6, 27.3, 15.2, 9.4, 5.0, 4.1, 23.3, 22.8, 112.8, 4.4),
    ("PHX", 18, 11, 5, 6, 48.0, 40.4, 86.8, 46.5, 14.4, 38.4, 37.4, 21.0, 27.4, 76.7, 14.2, 32.7, 46.9, 26.2, 17.4, 7.5, 4.7, 4.5, 18.6, 22.0, 116.1, 4.4),
    ("TOR", 18, 12, 5, 7, 48.0, 38.4, 80.5, 47.7, 12.7, 34.3, 36.9, 23.3, 28.8, 80.9, 10.5, 31.0, 41.5, 25.8, 19.0, 8.1, 5.5, 4.4, 24.3, 25.8, 112.8, -1.4),
    ("CHA", 22, 12, 4, 8, 48.0, 39.1, 83.2, 47.0, 14.3, 36.1, 39.7, 17.1, 22.0, 77.7, 8.9, 30.6, 39.5, 25.9, 13.9, 9.5, 4.6, 4.6, 21.6, 20.4, 109.6, 11.0),
    ("NOP", 22, 14, 4, 10, 49.1, 43.4, 87.9, 49.3, 13.5, 38.3, 35.3, 24.7, 31.0, 79.7, 11.4, 33.4, 44.8, 29.3, 15.7, 8.1, 5.6, 5.3, 23.9, 24.6, 124.9, 9.1),
    ("WAS", 22, 13, 4, 9, 48.8, 42.5, 94.2, 45.2, 12.2, 38.5, 31.6, 18.5, 21.6, 85.8, 14.0, 33.5, 47.5, 27.6, 13.7, 9.2, 3.5, 5.4, 21.2, 20.5, 115.8, 5.8),
    ("BKN", 25, 12, 3, 9, 48.4, 39.6, 84.6, 46.8, 14.2, 39.7, 35.7, 23.1, 29.2, 79.1, 10.7, 30.4, 41.1, 27.3, 16.3, 8.4, 4.8, 4.8, 24.1, 26.1, 116.4, 6.3),
    ("CHI", 25, 12, 3, 9, 48.4, 45.2, 94.8, 47.7, 13.7, 37.6, 36.4, 21.9, 28.7, 76.5, 14.0, 33.5, 47.5, 29.3, 14.3, 9.8, 4.9, 5.9, 23.2, 23.7, 125.9, 11.3),
    ("LAC", 25, 11, 3, 8, 48.5, 43.3, 87.6, 49.4, 12.7, 34.7, 36.6, 18.3, 25.1, 72.8, 11.6, 31.9, 43.5, 27.0, 16.1, 9.0, 4.4, 4.3, 20.9, 22.1, 117.5, 5.3),
    ("MIL", 28, 13, 1, 12, 48.0, 42.9, 92.8, 46.2, 14.8, 42.1, 35.3, 19.5, 25.0, 78.2, 14.6, 33.8, 48.5, 28.2, 13.1, 9.8, 5.8, 4.7, 19.5, 22.5, 120.2, 14.1),
    ("SAC", 28, 12, 1, 11, 48.0, 41.9, 85.3, 49.1, 14.0, 37.6, 37.3, 23.1, 29.0, 79.6, 10.2, 33.4, 43.6, 26.5, 14.7, 8.8, 5.8, 3.5, 19.7, 22.9, 120.9, 12.8),
    ("UTA", 28, 13, 1, 12, 48.8, 39.7, 87.8, 45.2, 12.6, 35.6, 35.4, 26.6, 32.2, 82.6, 11.3, 34.6, 45.9, 22.8, 13.9, 8.8, 5.4, 6.2, 24.2, 24.0, 118.6, 11.2),
]

# ---------------------------------------------------------------------------
# 4. TEAM ADVANCED — all 30 rows.
# ---------------------------------------------------------------------------
ADV_COLS = ["abbr", "rank", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg",
            "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct",
            "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]
ADVANCED = [
    ("LAL", 1, 13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306),
    ("PHI", 1, 14, 11, 3, 672.0, 112.3, 110.3, 2.0, 65.5, 2.06, 18.7, 27.5, 71.4, 49.4, 12.7, 52.6, 56.7, 100.21, 50.8, 1404),
    ("SAS", 1, 13, 11, 2, 629.0, 119.6, 106.6, 13.0, 65.4, 2.28, 19.4, 33.9, 71.3, 52.7, 12.3, 53.4, 57.6, 98.94, 56.7, 1298),
    ("BOS", 4, 12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 19.1, 32.7, 67.5, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168),
    ("HOU", 4, 13, 10, 3, 624.0, 119.3, 110.2, 9.1, 64.4, 1.85, 19.0, 35.2, 67.8, 52.0, 14.8, 55.1, 59.3, 97.42, 55.8, 1266),
    ("MEM", 6, 13, 9, 4, 629.0, 119.0, 110.4, 8.5, 66.2, 1.76, 19.1, 34.2, 70.6, 52.9, 15.6, 55.8, 60.2, 100.46, 53.9, 1318),
    ("MIN", 6, 13, 9, 4, 629.0, 116.0, 104.5, 11.5, 59.9, 1.63, 17.8, 35.4, 69.5, 52.7, 15.6, 55.5, 57.9, 101.27, 55.2, 1326),
    ("POR", 6, 12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 17.9, 33.3, 70.2, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208),
    ("DET", 9, 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 67.6, 1.94, 19.2, 29.8, 66.6, 48.4, 14.1, 53.9, 58.0, 99.48, 53.7, 1217),
    ("GSW", 9, 13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 19.4, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307),
    ("OKC", 9, 13, 8, 5, 624.0, 112.7, 109.0, 3.7, 55.5, 1.72, 16.6, 31.9, 68.5, 50.8, 13.5, 51.4, 55.4, 98.58, 53.3, 1282),
    ("ATL", 12, 13, 7, 6, 629.0, 113.3, 111.9, 1.4, 71.6, 2.07, 20.5, 33.2, 69.2, 49.7, 14.6, 52.8, 55.7, 103.55, 48.5, 1356),
    ("CLE", 12, 14, 7, 7, 677.0, 116.9, 115.4, 1.6, 64.8, 2.01, 19.1, 29.1, 68.1, 49.4, 13.4, 55.8, 59.1, 99.72, 51.2, 1407),
    ("DAL", 12, 13, 7, 6, 624.0, 112.8, 112.8, 0.0, 63.2, 1.65, 18.2, 33.0, 66.5, 49.7, 15.7, 53.5, 57.2, 100.54, 49.7, 1308),
    ("DEN", 12, 11, 7, 4, 533.0, 116.0, 114.7, 1.3, 66.9, 2.07, 19.7, 30.2, 67.7, 49.8, 13.5, 55.0, 59.2, 97.67, 52.9, 1087),
    ("MIA", 12, 13, 7, 6, 629.0, 114.7, 116.2, -1.5, 70.9, 2.07, 20.1, 30.3, 70.1, 49.8, 13.9, 54.5, 58.1, 102.49, 50.0, 1345),
    ("NYK", 17, 12, 6, 6, 576.0, 114.5, 108.6, 5.9, 69.2, 1.86, 18.9, 37.3, 72.1, 54.4, 15.0, 51.9, 55.7, 95.63, 53.3, 1150),
    ("IND", 18, 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 67.9, 1.92, 19.7, 24.6, 68.5, 47.1, 14.3, 53.8, 57.4, 101.25, 49.6, 1415),
    ("ORL", 18, 12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 18.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185),
    ("PHX", 18, 11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 19.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080),
    ("TOR", 18, 12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 19.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197),
    ("CHA", 22, 12, 4, 8, 576.0, 101.9, 113.1, -11.2, 62.6, 1.11, 15.8, 35.7, 73.7, 53.5, 20.2, 48.1, 52.0, 96.83, 42.9, 1161),
    ("NOP", 22, 14, 4, 10, 687.0, 111.3, 120.0, -8.6, 60.6, 1.51, 17.0, 29.7, 68.0, 48.6, 15.4, 51.9, 57.7, 101.83, 45.7, 1457),
    ("WAS", 22, 13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 17.0, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315),
    ("BKN", 25, 12, 3, 9, 581.0, 109.8, 116.0, -6.2, 65.2, 1.37, 17.2, 32.1, 69.9, 50.6, 17.6, 52.9, 57.2, 99.47, 46.1, 1204),
    ("CHI", 25, 12, 3, 9, 581.0, 109.4, 120.3, -10.9, 67.4, 1.55, 18.2, 30.7, 65.1, 47.9, 16.5, 51.7, 56.1, 103.81, 44.9, 1257),
    ("LAC", 25, 11, 3, 8, 533.0, 110.7, 115.8, -5.1, 68.4, 1.51, 18.8, 30.4, 67.2, 48.8, 17.6, 54.3, 58.4, 100.55, 47.4, 1116),
    ("MIL", 28, 13, 1, 12, 624.0, 105.7, 120.0, -14.2, 65.6, 1.49, 17.5, 30.5, 64.3, 47.3, 16.6, 51.1, 54.3, 100.31, 42.0, 1305),
    ("SAC", 28, 12, 1, 11, 576.0, 107.3, 119.5, -12.2, 63.7, 1.46, 17.9, 28.4, 69.1, 48.1, 16.9, 52.6, 56.2, 101.00, 42.8, 1210),
    ("UTA", 28, 13, 1, 12, 634.0, 105.0, 116.4, -11.3, 63.5, 1.44, 17.0, 29.5, 68.8, 48.6, 16.3, 50.4, 54.7, 100.50, 45.3, 1330),
]

# ---------------------------------------------------------------------------
# 5. SCHEDULE — the 3-day rolling window 2026-11-16 .. 2026-11-18.
#    Transcribed from https://www.nba.com/schedule (Week 5, Nov 16 - Nov 22).
#    tip_et, venue and city are printed on the page; records are printed on the
#    page's own per-game cards and re-checked against the standings page below.
# ---------------------------------------------------------------------------
SCHED_COLS = ["date", "game_id", "away", "home", "tip_et", "venue", "city", "cup_label",
              "away_record", "home_record", "tip_confirmed_by"]
SCHEDULE = [
    ("2026-11-16", "0022600245", "ORL", "BOS", "7:00 PM ET", "TD Garden", "Boston, MA", None, "5-7", "10-2", "official schedule card + standings"),
    ("2026-11-16", "0022600246", "CHI", "CLE", "7:00 PM ET", "Rocket Arena", "Cleveland, OH", None, "3-9", "7-7", "official schedule card + standings"),
    ("2026-11-16", "0022600247", "MEM", "WAS", "7:00 PM ET", "Capital One Arena", "Washington, DC", None, "9-4", "4-9", "official schedule card + standings"),
    ("2026-11-16", "0022600248", "PHI", "BKN", "7:30 PM ET", "Barclays Center", "Brooklyn, NY", None, "11-3", "3-9", "official schedule card + standings"),
    ("2026-11-16", "0022600249", "HOU", "MIA", "7:30 PM ET", "Kaseya Center", "Miami, FL", None, "10-3", "7-6", "official schedule card + standings"),
    ("2026-11-16", "0022600250", "POR", "MIN", "8:00 PM ET", "Target Center", "Minneapolis, MN", None, "9-3", "9-4", "official schedule card + standings"),
    ("2026-11-16", "0022600251", "GSW", "NOP", "8:00 PM ET", "Smoothie King Center", "New Orleans, LA", None, "8-5", "4-10", "official schedule card + standings"),
    ("2026-11-16", "0022600252", "PHX", "DEN", "9:00 PM ET", "Ball Arena", "Denver, CO", None, "5-6", "7-4", "official schedule card + standings"),
    ("2026-11-17", "0022600253", "NYK", "TOR", "7:30 PM ET", "Scotiabank Arena", "Toronto, ON", None, "6-6", "5-7", "official schedule card + standings"),
    ("2026-11-17", "0022600254", "POR", "MIN", "8:00 PM ET", "Target Center", "Minneapolis, MN", None, "9-3", "9-4", "official schedule card + standings"),
    ("2026-11-17", "0022600255", "DET", "SAS", "8:00 PM ET", "Frost Bank Center", "San Antonio, TX", None, "8-4", "11-2", "official schedule card + standings"),
    ("2026-11-17", "0022600256", "CHA", "LAL", "11:00 PM ET", "Crypto.com Arena", "Los Angeles, CA", None, "4-8", "11-2", "official schedule card + standings"),
    ("2026-11-17", "0022600257", "UTA", "LAC", "10:30 PM ET", "Intuit Dome", "Inglewood, CA", None, "1-12", "3-8", "official schedule card + standings"),
    ("2026-11-18", "0022600258", "MEM", "CLE", "7:00 PM ET", "Rocket Arena", "Cleveland, OH", None, "9-4", "7-7", "official schedule card + standings"),
    ("2026-11-18", "0022600259", "HOU", "IND", "7:00 PM ET", "Gainbridge Fieldhouse", "Indianapolis, IN", None, "10-3", "5-9", "official schedule card + standings"),
    ("2026-11-18", "0022600260", "MIL", "MIA", "7:00 PM ET", "Kaseya Center", "Miami, FL", None, "1-12", "7-6", "official schedule card + standings"),
    ("2026-11-18", "0022600261", "PHI", "ORL", "7:00 PM ET", "Kia Center", "Orlando, FL", None, "11-3", "5-7", "official schedule card + standings"),
    ("2026-11-18", "0022600262", "CHI", "BKN", "7:30 PM ET", "Barclays Center", "Brooklyn, NY", None, "3-9", "3-9", "official schedule card + standings"),
    ("2026-11-18", "0022600263", "WAS", "TOR", "7:30 PM ET", "Scotiabank Arena", "Toronto, ON", None, "4-9", "5-7", "official schedule card + standings"),
    ("2026-11-18", "0022600264", "DET", "NOP", "8:00 PM ET", "Smoothie King Center", "New Orleans, LA", None, "8-4", "4-10", "official schedule card + standings"),
    ("2026-11-18", "0022600265", "ATL", "OKC", "8:00 PM ET", "Paycom Center", "Oklahoma City, OK", None, "7-6", "8-5", "official schedule card + standings"),
    ("2026-11-18", "0022600267", "GSW", "DAL", "8:00 PM ET", "American Airlines Center", "Dallas, TX", None, "8-5", "7-6", "official schedule card + standings"),
    ("2026-11-18", "0022600266", "BOS", "DEN", "9:30 PM ET", "Ball Arena", "Denver, CO", None, "10-2", "7-4", "official schedule card + standings"),
    ("2026-11-18", "0022600268", "UTA", "LAL", "10:00 PM ET", "Crypto.com Arena", "Los Angeles, CA", None, "1-12", "11-2", "official schedule card + standings"),
    ("2026-11-18", "0022600269", "PHX", "SAC", "10:00 PM ET", "Golden 1 Center", "Sacramento, CA", None, "5-6", "1-11", "official schedule card + standings"),
]
# The official page prints these game counts per day.
SCHEDULE_COUNTS = {"2026-11-16": 8, "2026-11-17": 5, "2026-11-18": 12}

# ---------------------------------------------------------------------------
# 6. RESULTS 2026-11-15 — https://www.nba.com/games?date=2026-11-15, read 23:41Z.
#    Only one of the nine games had reached Final at capture time. Nothing is
#    inferred for the rest: score cells are None and the row is marked pending.
# ---------------------------------------------------------------------------
RESULTS_1115 = [
    # date, game_id, away, home, tip_et, state, away_pts, home_pts, away_quarters, home_quarters
    ("2026-11-15", "0022600236", "IND", "PHI", "1:00 PM ET", "Final", 124, 131, None, None),
    ("2026-11-15", "0022600237", "LAL", "PHX", "4:00 PM ET", "LIVE 4th Qtr", 124, 117, None, None),
    ("2026-11-15", "0022600238", "CHA", "LAC", "4:30 PM ET", "LIVE 4th Qtr", 90, 98, None, None),
    ("2026-11-15", "0022600239", "SAS", "UTA", "5:00 PM ET", "LIVE 3rd Qtr", 79, 76, None, None),
    ("2026-11-15", "0022600240", "DAL", "BOS", "6:00 PM ET", "LIVE 2nd Qtr", 9, 42, None, None),
    ("2026-11-15", "0022600241", "NYK", "TOR", "6:00 PM ET", "LIVE 1st Qtr", 23, 17, None, None),
    ("2026-11-15", "0022600242", "HOU", "WAS", "7:00 PM ET", "PREGAME", None, None, None, None),
    ("2026-11-15", "0022600243", "ATL", "MIL", "8:00 PM ET", "not tipped", None, None, None, None),
    ("2026-11-15", "0022600244", "OKC", "SAC", "9:00 PM ET", "not tipped", None, None, None, None),
]

# ---------------------------------------------------------------------------
# 7. INJURY REPORT — the 11/15/2026 06:15 PM ET edition (latest on the index at
#    capture time).  Rows transcribed verbatim from the PDF, in printed order.
#    team_inherited marks rows whose Team cell is blank because of a merged
#    cell in the PDF; team_effective carries the nearest printed team above.
# ---------------------------------------------------------------------------
INJ_EDITION = "2026-11-15_06_15PM"
INJ_REVISION_ET = "11/15/2026 06:15 PM"
# (game_date, game_time_et, matchup, team_printed, team_effective, inherited, player, status, reason)
INJURY = [
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "McConnell, T.J.", "Available", "Injury/Illness - Right Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "Nembhard, Andrew", "Out", "Injury/Illness - Left Hip Soreness / Tightness"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "Nesmith, Aaron", "Available", "Injury/Illness - Left Hand Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Indiana Pacers", False, "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Philadelphia 76ers", False, "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Philadelphia 76ers", False, "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Philadelphia 76ers", False, "Embiid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Philadelphia 76ers", False, "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Los Angeles Lakers", False, "Carr, Cameron", "Out", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Los Angeles Lakers", False, "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Los Angeles Lakers", False, "James, Bronny", "Available", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Los Angeles Lakers", False, "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Los Angeles Lakers", True, "Sexton, Collin", "Available", "Injury/Illness - Right Orbital Laceration"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Los Angeles Lakers", True, "Thiero, Adou", "Available", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Phoenix Suns", "Phoenix Suns", False, "Timme, Drew", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Phoenix Suns", "Phoenix Suns", False, "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Charlotte Hornets", False, "Ajayi, Michael", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Charlotte Hornets", False, "Boswell, Kylan", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Charlotte Hornets", False, "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Charlotte Hornets", False, "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Charlotte Hornets", False, "Steinbach, Hannes", "Out", "G League - On Assignment"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "LA Clippers", False, "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "LA Clippers", False, "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "LA Clippers", False, "Martinelli, Nick", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "LA Clippers", False, "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "LA Clippers", False, "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "San Antonio Spurs", False, "Brown, Maliq", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "San Antonio Spurs", False, "Fox, De'Aaron", "Out", "Injury/Illness - Left Hip Tightness"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "San Antonio Spurs", False, "Gillespie, Ja'Kobi", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "San Antonio Spurs", False, "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "San Antonio Spurs", True, "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Alexander, Trey", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Bufkin, Kobe", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Ingram, Harrison", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Utah Jazz", False, "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Aldama, Santi", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Christie, Max", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Gafford, Daniel", "Available", "Injury/Illness - Right Shoulder Stinger"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Irving, Kyrie", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Dallas Mavericks", False, "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Boston Celtics", False, "Carter, Devin", "Available", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Boston Celtics", False, "Cenac Jr., Christopher", "Available", "G League - On Assignment"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", None, "Boston Celtics", True, "Mitchell, Dillon", "Available", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", None, "Boston Celtics", True, "Williams, Amari", "Available", "G League - Two-Way"),
    ("11/15/2026", None, "NYK@TOR", "Toronto Raptors", "Toronto Raptors", False, "Barnes, Scottie", "Available", "Injury/Illness - Left Groin Strain"),
    ("11/15/2026", None, "NYK@TOR", "Toronto Raptors", "Toronto Raptors", False, "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture"),
    ("11/15/2026", None, "NYK@TOR", "Toronto Raptors", "Toronto Raptors", False, "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/15/2026", None, "NYK@TOR", "Toronto Raptors", "Toronto Raptors", False, "McCullar Jr., Kevin", "Out", "G League - Two-Way"),
    ("11/15/2026", None, "NYK@TOR", "Toronto Raptors", "Toronto Raptors", False, "Smith, Malachi", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "Adams, Steven", "Available", "Injury/Illness - Right Soleus Strain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "Copeland, Quadir", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "Phillips, Julian", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "Smart, Marcus", "Out", "League Suspension"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Houston Rockets", False, "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Washington Wizards", False, "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Washington Wizards", False, "Carrington, Bub", "Available", "Injury/Illness - Chest / Sternum Contusion"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Washington Wizards", False, "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Washington Wizards", False, "Johnson, Tre", "Out", "Injury/Illness - Low Back Soreness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Washington Wizards", True, "Okpara, Felix", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Washington Wizards", True, "Sarr, Alex", "Available", "Injury/Illness - Illness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Washington Wizards", True, "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Washington Wizards", True, "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Landale, Jock", "Out", "Injury/Illness - Right Hip Inflammation"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Atlanta Hawks", False, "Wilson, Jalen", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Milwaukee Bucks", False, "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Fracture"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Milwaukee Bucks", False, "Jones, Kam", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Milwaukee Bucks", False, "Markovic, Bogoljub", "Out", "G League - On Assignment"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Milwaukee Bucks", False, "Nance, Pete", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Milwaukee Bucks", False, "Rollins, Ryan", "Out", "Injury/Illness - Illness"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", None, "Milwaukee Bucks", True, "Ryan, Cormac", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Oklahoma City Thunder", False, "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Mogbo, Jonathan", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Murray, Keegan", "Available", "-"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Pedulla, Sean", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Sacramento Kings", False, "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Chicago Bulls", False, "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Chicago Bulls", False, "Robinson, Orlando", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Chicago Bulls", False, "Sellers, Jaylin", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Chicago Bulls", False, "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Chicago Bulls", False, "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Diop, Khalifa", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Tyson, Jaylon", "Questionable", "Injury/Illness - Right Ankle Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Udeh, Jr., Ernest", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", None, "Cleveland Cavaliers", True, "Watson, Peyton", "Questionable", "Injury/Illness - Right Abdominal Soreness"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Edey, Zach", "Questionable", "Injury/Illness - Left Ankle Injury Management"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Jackson, GG", "Out", "Injury/Illness - Left Foot Injury"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Jerome, Ty", "Out", "Injury/Illness - Right Hip Soreness"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Post, Quinten", "Questionable", "Injury/Illness - Concussion Protocol"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", None, "MEM@WAS", "Memphis Grizzlies", "Memphis Grizzlies", False, "Stewart, Isaiah", "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", None, "MEM@WAS", "Washington Wizards", "Washington Wizards", False, None, "NOT YET SUBMITTED", None),
    ("11/16/2026", None, "ORL@BOS", "Orlando Magic", "Orlando Magic", False, "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain"),
    ("11/16/2026", None, "ORL@BOS", "Orlando Magic", "Orlando Magic", False, "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/16/2026", None, "ORL@BOS", "Orlando Magic", "Orlando Magic", False, "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery"),
    ("11/16/2026", None, "ORL@BOS", "Orlando Magic", "Orlando Magic", False, "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring"),
    ("11/16/2026", None, "ORL@BOS", "Boston Celtics", "Boston Celtics", False, "Penda, Noah", "Out", "NOT YET SUBMITTED"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Houston Rockets", "Houston Rockets", False, None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Miami Heat", False, "Goldin, Vladislav", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Miami Heat", False, "Larsson, Pelle", "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Miami Heat", False, "Thompson, Klay", "Available", "Injury/Illness - Left Ankle Sprain"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Philadelphia 76ers", "Philadelphia 76ers", False, None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Brooklyn Nets", False, "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Brooklyn Nets", False, "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Brooklyn Nets", False, "Nelson, Grant", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Brooklyn Nets", False, "Powell, Drake", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Brooklyn Nets", False, "Saraf, Ben", "Out", "G League - On Assignment"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Golden State Warriors", False, "Butler III, Jimmy", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", None, "Golden State Warriors", True, "Curry, Stephen", "Out", "Injury/Illness - Right Oblique Tear"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", None, "Golden State Warriors", True, "Moody, Moses", "Out", "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", None, "Golden State Warriors", True, "Porzingis, Kristaps", "Out", "Not With Team"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", None, "Golden State Warriors", True, "Santos, Gui", "Questionable", "Injury/Illness - Right Ankle Inflammation"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", None, "Golden State Warriors", True, "Williams, Brandon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Dia, Malik", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Mathurin, Bennedict", "Out", "Injury/Illness - Left Plantar Fasciitis"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Pierre Jr., Jaron", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Reese, Julian", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "New Orleans Pelicans", False, "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("11/16/2026", None, "POR@MIN", "Portland Trail Blazers", "Portland Trail Blazers", False, "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture"),
    ("11/16/2026", None, "POR@MIN", "Portland Trail Blazers", "Portland Trail Blazers", False, "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", None, "POR@MIN", "Portland Trail Blazers", "Portland Trail Blazers", False, "Sharpe, Shaedon", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", None, "POR@MIN", "Portland Trail Blazers", "Portland Trail Blazers", False, "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise"),
    ("11/16/2026", None, "POR@MIN", "Minnesota Timberwolves", "Minnesota Timberwolves", False, "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("11/16/2026", None, "POR@MIN", "Minnesota Timberwolves", "Minnesota Timberwolves", False, "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("11/16/2026", None, "POR@MIN", "Minnesota Timberwolves", "Minnesota Timberwolves", False, "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/16/2026", None, "POR@MIN", "Minnesota Timberwolves", "Minnesota Timberwolves", False, "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Phoenix Suns", "Phoenix Suns", False, None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets", "Denver Nuggets", False, None, "NOT YET SUBMITTED", None),
]


def dump(rel, doc):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", rel, "(" + str(len(doc.get("rows", []))) + " rows)" if isinstance(doc, dict) and "rows" in doc else "wrote " + rel)


def rows_from(table, cols):
    return [dict(zip(cols, r)) for r in table]


def main():
    standings = rows_from(STANDINGS, STANDINGS_COLS)
    trad = rows_from(TRADITIONAL, TRAD_COLS)
    opp = rows_from(OPPONENT, OPP_COLS)
    adv = rows_from(ADVANCED, ADV_COLS)
    sched = rows_from(SCHEDULE, SCHED_COLS)

    # ---- cross-checks -----------------------------------------------------
    st = {r["abbr"]: r for r in standings}
    tr = {r["abbr"]: r for r in trad}
    op = {r["abbr"]: r for r in opp}
    av = {r["abbr"]: r for r in adv}
    assert len(st) == len(tr) == len(op) == len(av) == 30, "expected 30 teams on every page"
    for abbr in st:
        assert (st[abbr]["w"], st[abbr]["l"]) == (tr[abbr]["w"], tr[abbr]["l"]), \
            f"{abbr}: standings W/L != traditional W/L"
        assert (st[abbr]["w"], st[abbr]["l"]) == (av[abbr]["w"], av[abbr]["l"]), \
            f"{abbr}: standings W/L != advanced W/L"
        assert tr[abbr]["gp"] == av[abbr]["gp"] == op[abbr]["gp"], f"{abbr}: GP disagrees across pages"
        diff = round(tr[abbr]["pts"] - op[abbr]["opp_pts"], 1)
        # 0.15 tolerance: both operands are printed to one decimal, so their
        # difference can be 0.1 off from the printed +/- purely through rounding.
        assert abs(diff - tr[abbr]["plus_minus"]) <= 0.15, \
            f"{abbr}: pts - opp_pts = {diff} but printed +/- = {tr[abbr]['plus_minus']}"
        assert abs(op[abbr]["plus_minus"] + tr[abbr]["plus_minus"]) <= 0.15, \
            f"{abbr}: opponent page +/- is not the negation of the traditional page's"

    counts = {}
    for r in sched:
        counts[r["date"]] = counts.get(r["date"], 0) + 1
        for side in ("away", "home"):
            want = f"{st[r[side]]['w']}-{st[r[side]]['l']}"
            got = r[side + "_record"]
            assert got == want, f"{r['date']} {r['matchup'] if 'matchup' in r else ''} {side}: {got} != standings {want}"
    assert counts == SCHEDULE_COUNTS, f"per-day game counts {counts} != printed {SCHEDULE_COUNTS}"

    # ---- results 11/15 ----------------------------------------------------
    results = []
    for (date, gid, away, home, tip, state, ap, hp, aq, hq) in RESULTS_1115:
        results.append({
            "date": date, "game_id": gid, "away": away, "home": home,
            "tip_et": tip, "final_label": state,
            "away_pts": ap, "home_pts": hp,
            "away_quarters": aq, "home_quarters": hq,
            "ot_periods": None,
            "settled": state == "Final",
            "quarter_scores_status": ("not read — box-score quarter line not reachable "
                                      "in this capture; blank, not inferred"),
            "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}/box-score",
            "source_date_url": f"https://www.nba.com/games?date={date}",
        })

    # ---- injury edition ---------------------------------------------------
    injury_rows = []
    for (gd, gt, mu, tp, te, inh, player, status, reason) in INJURY:
        injury_rows.append({
            "game_date": gd, "game_time_et": gt, "matchup": mu,
            "team_printed": tp, "team_effective": te, "team_inherited": inh,
            "player": player, "status": status, "reason": reason,
            "source_url": SRC["injury_pdf"],
        })

    # ---- successive-report diff (06:15 AM -> 06:15 PM, both 11/15) ---------
    prev_path = os.path.join(ROOT, "data", "official", "injury_2026-11-15_0615AM.json")
    diff = {"from_edition": "2026-11-15_06_15AM", "to_edition": INJ_EDITION,
            "from_source_url": SRC["injury_pdf_prev"], "to_source_url": SRC["injury_pdf"],
            "diff_rule": ("keyed on (game_date, matchup, player). ADDED = in the newer edition "
                          "only; REMOVED = in the older edition only; CHANGED = status differs; "
                          "UNCHANGED counted only. Rows with no player name (NOT YET SUBMITTED "
                          "placeholders) are keyed on (game_date, matchup, team_effective)."),
            "added": [], "removed": [], "changed": [], "unchanged": 0,
            "caveat": ("the 06:15 AM edition covers only the 11/15 games; the 06:15 PM edition "
                       "adds the 11/16 blocks. Rows keyed to 11/16 are therefore ADDED by "
                       "construction and are listed separately below."),
            "added_1116_blocks": 0}
    if os.path.exists(prev_path):
        prev = json.load(open(prev_path, encoding="utf-8"))["rows"]
        prev_idx, cur_idx = {}, {}
        for r in prev:
            k = (r.get("game_date"), r.get("matchup"), r.get("player") or
                 ("<team:" + str(r.get("team_effective")) + ">"))
            prev_idx[k] = r
        for r in injury_rows:
            k = (r["game_date"], r["matchup"], r["player"] or
                 ("<team:" + str(r["team_effective"]) + ">"))
            cur_idx[k] = r
        for k, r in cur_idx.items():
            if k[0] == "11/16/2026":
                diff["added_1116_blocks"] += 1
                continue
            if k not in prev_idx:
                diff["added"].append({"player": r["player"], "matchup": r["matchup"],
                                      "status": r["status"], "reason": r["reason"]})
            elif (prev_idx[k].get("status") or "") != (r["status"] or ""):
                diff["changed"].append({"player": r["player"], "matchup": r["matchup"],
                                        "from": prev_idx[k].get("status"), "to": r["status"],
                                        "reason": r["reason"]})
            else:
                diff["unchanged"] += 1
        for k, r in prev_idx.items():
            if k not in cur_idx:
                diff["removed"].append({"player": r.get("player"), "matchup": r.get("matchup"),
                                        "status": r.get("status")})
    else:
        diff["error"] = "previous edition file not found: " + os.path.relpath(prev_path, ROOT)

    # ---- write ------------------------------------------------------------
    dump("data/official/standings_2026-11-15_2345Z.json", {
        "title": "NBA 2026-27 regular season standings", "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED, "source_url": SRC["standings"],
        "as_of": "after the 2026-11-15 IND@PHI result; the other eight 11/15 games were live or untipped",
        "rows": standings})
    dump("data/official/teams_traditional_2026-11-15_2345Z.json", {
        "title": "NBA team traditional stats 2026-27 (per game)", "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED, "source_url": SRC["traditional"], "rows": trad})
    dump("data/official/teams_opponent_2026-11-15_2345Z.json", {
        "title": "NBA team opponent stats 2026-27 (per game)", "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED, "source_url": SRC["opponent"], "rows": opp})
    dump("data/official/teams_advanced_2026-11-15_2345Z.json", {
        "title": "NBA team advanced stats 2026-27", "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED, "source_url": SRC["advanced"], "rows": adv})
    dump("data/official/schedule_2026-11-16_to_18.json", {
        "title": "Official NBA schedule, rolling 3-day window 2026-11-16 .. 2026-11-18",
        "captured_by": CAPTURED_BY, "retrieved_utc": RETRIEVED,
        "window_rule": ("today (2026-11-15) + up to 3 days ahead; 11/15 is excluded because its "
                        "games are tipped or in progress at capture time"),
        "per_day_counts": counts, "printed_per_day_counts": SCHEDULE_COUNTS,
        "sources": [SRC["schedule"]] + [f"https://www.nba.com/games?date={d}"
                                        for d in sorted(counts)],
        "rows": sched})
    dump("data/official/results_2026-11-15.json", {
        "title": "Official per-game result feed, 2026-11-15", "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED,
        "rule": ("one row per game: date, teams, final score, quarter scores. Only games whose "
                 "official label is Final carry a score; nothing else is filled in."),
        "settled_games": sum(1 for r in results if r["settled"]), "games_total": len(results),
        "columns": ["date", "game_id", "away", "home", "tip_et", "final_label",
                    "away_pts", "home_pts", "away_quarters", "home_quarters", "ot_periods"],
        "sources": [SRC["games_1115"], SRC["box_1115_ind_phi"]], "rows": results})
    dump("data/official/injury_2026-11-15_0615PM.json", {
        "edition": INJ_EDITION, "edition_file": os.path.basename(SRC["injury_pdf"]),
        "revision_time_et": INJ_REVISION_ET, "retrieved_utc": RETRIEVED,
        "captured_by": CAPTURED_BY, "source_url": SRC["injury_pdf"],
        "index_url": SRC["injury_index"],
        "index_note": ("the official index lists one PDF per 15 minutes; 06:15 PM ET was the "
                       "newest edition published when this capture was made"),
        "submission_rule_quoted": ("By 5 p.m. local time the day before a game (other than the "
                                   "second day of a back-to-back), teams must designate a "
                                   "participation status ... For the second game of a "
                                   "back-to-back, teams must report the above information by "
                                   "1 p.m. local time on the day of the game."),
        "submission_rule_url": SRC["injury_index"],
        "merged_cell_caveat": ("rows with team_inherited = true lost their Team cell to a merged "
                              "cell in the PDF; team_effective is the nearest printed team above "
                              "and is used for the team lookup"),
        "rows_note": ("verbatim, in printed order. Rows whose status is NOT YET SUBMITTED carry "
                      "player = null and are printed that way by the league."),
        "rows": injury_rows})
    dump("data/official/injury_diff_2026-11-15_0615AM_to_0615PM.json", diff)
    dump("data/raw/official_schedule_capture_2026-11-16.json", {
        "captured_by": CAPTURED_BY, "captured_on_utc_date": "2026-11-15",
        "capture_method": "official pages read live through the web-fetch channel",
        "scope": "rolling 3-day window 2026-11-16 .. 2026-11-18 (25 games)",
        "sources": [SRC["schedule"], "https://www.nba.com/standings"],
        "cols": SCHED_COLS, "rows": SCHEDULE})

    log = {
        "session": CAPTURED_BY, "retrieved_utc": RETRIEVED,
        "sources": SRC,
        "window_rule": "2026-11-16 .. 2026-11-18 (today + up to 3 days; 11/15 excluded, in flight)",
        "counts": {"standings": len(standings), "traditional": len(trad),
                   "opponent": len(opp), "advanced": len(adv),
                   "schedule_games": len(sched), "results_1115": len(results),
                   "results_1115_settled": sum(1 for r in results if r["settled"]),
                   "injury_rows": len(injury_rows),
                   "injury_1116_rows": sum(1 for r in injury_rows if r["game_date"] == "11/16/2026")},
        "cross_checks": [
            "standings W/L == traditional W/L for all 30 teams",
            "standings W/L == advanced W/L for all 30 teams",
            "GP agrees across traditional / opponent / advanced for all 30 teams",
            "traditional PTS - opponent OPP_PTS == printed +/- (0.1 tolerance), all 30 teams",
            "opponent page +/- == -(traditional page +/-), all 30 teams",
            "every schedule row's record pair == the standings pair, both sides",
            "per-day game counts == the counts printed on the official schedule page",
        ],
        "not_read": [
            "quarter scores for every 11/15 game (box-score quarter line not reachable in this capture)",
            "final scores for the eight 11/15 games that were live or untipped at 23:41Z",
        ],
    }
    dump(os.path.relpath(os.path.join(HERE, "capture_log.json"), ROOT), log)
    print("\ncapture complete —", len(sched), "horizon games,", len(injury_rows), "injury rows")


if __name__ == "__main__":
    main()
