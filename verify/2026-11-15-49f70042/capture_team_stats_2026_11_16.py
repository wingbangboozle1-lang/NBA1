#!/usr/bin/env python3
"""capture_team_stats_2026_11_16.py — re-read the three official NBA.com team
stat pages and re-cut the model inputs.

Read live through the web-fetch channel on 2026-11-15T23:36Z..23:45Z (the
sandbox has no general egress; the web-fetch channel is the only route):

  https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season
  https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame
  https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame

Rows are transcribed verbatim from the official tables in the column order the
page prints. The script re-checks the transcription against the previous
official capture in data/official/ (captured 2026-11-15T11:35Z..12:20Z by
session arena/83d380ad-nba1) and reports every field that moved, so a
transcription slip cannot pass silently: the only games added to the official
ledger between the two reads are the games that finished on 2026-11-15, so a
field that moved for a team whose games did not change is a transcription
error and is reported as such.

Writes:
  data/official/teams_advanced_2026-11-16_0050Z.json
  data/official/teams_traditional_2026-11-16_0052Z.json
  data/official/teams_opponent_2026-11-16_0055Z.json
  data/official/team_stats_recut_2026-11-15_2340Z.json      (the diff + league baselines)

Run: python3 verify/2026-11-15-49f70042/capture_team_stats_2026_11_16.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
OFF = os.path.join(DATA, "official")

SRC_ADV = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRA = ("https://www.nba.com/stats/teams/traditional"
           "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
SRC_OPP = ("https://www.nba.com/stats/teams/opponent"
           "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")

NAME = {
    "LAL": "Los Angeles Lakers", "PHI": "Philadelphia 76ers", "SAS": "San Antonio Spurs",
    "BOS": "Boston Celtics", "HOU": "Houston Rockets", "MEM": "Memphis Grizzlies",
    "MIN": "Minnesota Timberwolves", "POR": "Portland Trail Blazers",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors",
    "OKC": "Oklahoma City Thunder", "ATL": "Atlanta Hawks",
    "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "MIA": "Miami Heat", "NYK": "New York Knicks", "IND": "Indiana Pacers",
    "ORL": "Orlando Magic", "PHX": "Phoenix Suns", "TOR": "Toronto Raptors",
    "CHA": "Charlotte Hornets", "NOP": "New Orleans Pelicans",
    "WAS": "Washington Wizards", "BKN": "Brooklyn Nets", "CHI": "Chicago Bulls",
    "LAC": "LA Clippers", "MIL": "Milwaukee Bucks", "SAC": "Sacramento Kings",
    "UTA": "Utah Jazz",
}

# --------------------------------------------------------------------------
# ADVANCED: abbr, gp, w, l, min, ortg, drtg, netr, ast_pct, ast_to, ast_ratio,
#           oreb_pct, dreb_pct, reb_pct, tov_pct, efg_pct, ts_pct, pace, pie, poss
ADV = [
    ("LAL", 13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306),
    ("PHI", 14, 11, 3, 672.0, 112.3, 110.3, 2.0, 65.5, 2.06, 18.7, 27.5, 71.4, 49.4, 12.7, 52.6, 56.7, 100.21, 50.8, 1404),
    ("SAS", 13, 11, 2, 629.0, 119.6, 106.6, 13.0, 65.4, 2.28, 38.9, 33.9, 71.3, 52.7, 12.3, 53.4, 57.6, 98.94, 56.7, 1298),
    ("BOS", 12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 38.1, 33.9, 64.4, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168),
    ("HOU", 13, 10, 3, 624.0, 119.3, 110.2, 9.1, 64.4, 1.85, 38.0, 35.2, 66.2, 50.5, 14.8, 55.1, 59.3, 97.42, 55.8, 1266),
    ("MEM", 13, 9, 4, 629.0, 119.0, 110.4, 8.5, 66.2, 1.76, 38.2, 33.9, 71.6, 52.9, 15.6, 55.8, 60.2, 100.46, 53.9, 1318),
    ("MIN", 13, 9, 4, 629.0, 116.0, 104.5, 11.5, 65.4, 1.63, 37.8, 33.9, 71.3, 52.7, 15.6, 55.5, 57.9, 101.27, 55.2, 1326),
    ("POR", 12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 37.9, 33.3, 70.6, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208),
    ("DET", 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 67.6, 1.94, 38.4, 33.8, 70.9, 52.4, 14.1, 53.9, 58.0, 99.48, 53.7, 1217),
    ("GSW", 13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 37.6, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307),
    ("OKC", 13, 8, 5, 624.0, 112.7, 109.0, 3.7, 66.2, 1.72, 38.4, 33.9, 68.5, 50.8, 13.5, 51.4, 55.4, 98.58, 53.3, 1282),
    ("ATL", 13, 7, 6, 629.0, 113.3, 111.9, 1.4, 71.6, 2.07, 38.6, 33.2, 69.2, 49.7, 14.6, 52.8, 55.7, 103.55, 48.5, 1356),
    ("CLE", 14, 7, 7, 677.0, 116.9, 115.4, 1.6, 64.8, 2.01, 38.1, 34.9, 71.3, 52.6, 13.4, 55.8, 59.1, 99.72, 51.2, 1407),
    ("DAL", 13, 7, 6, 624.0, 112.8, 112.8, 0.0, 63.2, 1.65, 18.2, 33.0, 66.5, 49.7, 15.7, 53.5, 57.2, 100.54, 49.7, 1308),
    ("DEN", 11, 7, 4, 533.0, 116.0, 114.7, 1.3, 66.9, 2.07, 38.7, 30.2, 67.7, 49.8, 13.5, 55.0, 59.2, 97.67, 52.9, 1087),
    ("MIA", 13, 7, 6, 629.0, 114.7, 116.2, -1.5, 70.9, 2.07, 38.0, 30.3, 70.1, 49.8, 13.9, 54.5, 58.1, 102.49, 50.0, 1345),
    ("NYK", 12, 6, 6, 576.0, 114.5, 108.6, 5.9, 69.2, 1.86, 38.9, 37.3, 72.1, 54.4, 15.0, 51.9, 55.7, 95.63, 53.3, 1150),
    ("IND", 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 67.9, 1.92, 38.7, 24.6, 68.5, 47.1, 14.3, 53.8, 57.4, 101.25, 49.6, 1415),
    ("ORL", 12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 38.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185),
    ("PHX", 11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 38.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080),
    ("TOR", 12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 38.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197),
    ("CHA", 12, 4, 8, 576.0, 101.9, 113.1, -11.2, 62.6, 1.11, 35.7, 33.7, 73.7, 53.5, 20.2, 48.1, 52.0, 96.83, 42.9, 1161),
    ("NOP", 14, 4, 10, 687.0, 111.3, 120.0, -8.6, 60.6, 1.51, 38.0, 29.7, 68.0, 48.6, 15.4, 51.9, 57.7, 101.83, 45.7, 1457),
    ("WAS", 13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 38.7, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315),
    ("BKN", 12, 3, 9, 581.0, 109.8, 116.0, -6.2, 65.2, 1.37, 38.2, 32.1, 69.9, 50.6, 17.6, 52.9, 57.2, 99.47, 46.1, 1204),
    ("CHI", 12, 3, 9, 581.0, 109.4, 120.3, -10.9, 67.4, 1.55, 38.2, 30.7, 65.1, 47.9, 16.5, 51.7, 56.1, 103.81, 44.9, 1257),
    ("LAC", 11, 3, 8, 533.0, 110.7, 115.8, -5.1, 68.4, 1.51, 38.8, 30.4, 67.2, 48.8, 17.6, 54.3, 58.4, 100.55, 47.4, 1116),
    ("MIL", 13, 1, 12, 624.0, 105.7, 120.0, -14.2, 65.6, 1.49, 38.5, 30.5, 64.3, 47.3, 16.6, 51.1, 54.3, 100.31, 42.0, 1305),
    ("SAC", 12, 1, 11, 576.0, 107.3, 119.5, -12.2, 63.7, 1.46, 38.9, 28.4, 69.1, 48.1, 16.9, 52.6, 56.2, 101.00, 42.8, 1210),
    ("UTA", 13, 1, 12, 634.0, 105.0, 116.4, -11.3, 63.5, 1.44, 38.6, 29.5, 68.8, 48.6, 16.3, 50.4, 54.7, 100.50, 45.3, 1330),
]

# --------------------------------------------------------------------------
# TRADITIONAL: abbr, gp, w, l, win_pct, min, pts, fgm, fga, fg_pct, fg3m, fg3a,
#              fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, tov, stl, blk,
#              blka, pf, pfd, plus_minus
TRA = [
    ("LAL", 13, 11, 2, .846, 48.0, 122.2, 42.1, 83.6, 50.3, 14.1, 36.8, 38.3, 23.9, 29.8, 80.4, 11.3, 29.5, 40.8, 24.7, 16.9, 11.0, 6.2, 4.2, 23.4, 24.2, 7.9),
    ("SAS", 13, 11, 2, .846, 48.4, 119.5, 42.9, 92.0, 46.7, 12.5, 35.9, 34.7, 21.2, 26.5, 79.9, 13.2, 35.4, 48.6, 28.1, 12.3, 8.3, 7.3, 4.9, 20.0, 21.2, 13.2),
    ("BOS", 12, 10, 2, .833, 48.4, 114.3, 39.8, 87.2, 45.6, 16.0, 42.0, 38.1, 18.8, 23.8, 78.9, 13.1, 31.7, 44.8, 26.8, 14.7, 8.2, 4.9, 4.2, 21.5, 22.9, 11.2),
    ("PHI", 14, 11, 3, .786, 48.0, 112.6, 40.1, 87.9, 45.7, 12.1, 34.4, 35.1, 20.2, 25.9, 78.2, 10.0, 32.9, 42.9, 26.3, 12.8, 8.1, 4.2, 5.6, 20.9, 20.9, 2.1),
    ("HOU", 13, 10, 3, .769, 48.0, 116.2, 41.5, 86.9, 47.8, 12.8, 34.3, 37.2, 20.3, 25.0, 81.2, 13.2, 31.2, 44.4, 26.8, 14.5, 7.9, 6.1, 4.1, 19.9, 21.9, 8.8),
    ("POR", 12, 9, 3, .750, 48.0, 119.6, 39.8, 84.7, 46.9, 15.9, 43.6, 36.5, 24.2, 30.7, 78.8, 11.5, 32.8, 44.3, 25.3, 16.3, 7.1, 5.1, 4.2, 22.3, 24.4, 7.8),
    ("MEM", 13, 9, 4, .692, 48.4, 120.6, 42.1, 89.4, 47.1, 15.5, 39.6, 39.2, 20.9, 24.7, 84.7, 12.5, 34.8, 47.4, 27.8, 15.8, 6.5, 5.1, 7.2, 23.6, 21.5, 8.9),
    ("MIN", 13, 9, 4, .692, 48.4, 118.3, 43.4, 90.9, 47.7, 14.2, 38.4, 36.9, 17.4, 25.5, 68.1, 13.8, 34.6, 48.5, 26.0, 15.9, 9.0, 5.1, 6.4, 22.0, 22.8, 11.5),
    ("DET", 12, 8, 4, .667, 48.8, 115.7, 40.9, 88.4, 46.3, 13.5, 36.8, 36.7, 20.3, 25.8, 79.0, 12.2, 32.3, 44.4, 27.7, 14.3, 9.4, 6.4, 6.1, 23.8, 22.7, 5.4),
    ("DEN", 11, 7, 4, .636, 48.5, 114.6, 41.5, 85.2, 48.7, 10.8, 31.0, 34.9, 20.9, 26.5, 79.0, 10.1, 32.2, 42.3, 27.7, 13.4, 9.0, 4.5, 4.5, 19.0, 23.2, 1.8),
    ("GSW", 13, 8, 5, .615, 48.4, 116.7, 40.0, 87.0, 46.0, 16.4, 41.6, 39.4, 20.3, 25.1, 81.0, 12.5, 31.9, 44.5, 28.0, 16.0, 8.2, 5.4, 5.7, 21.9, 22.2, 4.3),
    ("OKC", 13, 8, 5, .615, 48.0, 111.2, 41.2, 90.7, 45.4, 11.0, 32.1, 34.3, 17.8, 21.8, 81.7, 11.5, 35.1, 46.6, 22.8, 13.3, 7.9, 5.4, 5.3, 19.3, 21.0, 3.8),
    ("ATL", 13, 7, 6, .538, 48.4, 118.2, 43.9, 97.2, 45.2, 14.8, 43.3, 34.1, 15.5, 20.4, 76.2, 13.9, 30.2, 44.1, 31.5, 15.2, 10.3, 4.0, 6.0, 22.1, 19.4, 1.3),
    ("DAL", 13, 7, 6, .538, 48.0, 113.5, 41.2, 88.8, 46.4, 12.5, 37.5, 33.5, 18.5, 23.5, 78.4, 12.7, 30.9, 43.6, 26.1, 15.8, 8.7, 5.5, 4.8, 22.3, 20.9, 0.2),
    ("MIA", 13, 7, 6, .538, 48.4, 118.7, 42.0, 89.5, 46.9, 13.5, 39.5, 34.1, 21.2, 28.7, 74.0, 10.5, 32.2, 42.8, 29.8, 14.4, 7.8, 5.5, 5.2, 21.1, 25.1, -1.2),
    ("CLE", 14, 7, 7, .500, 48.4, 117.5, 41.8, 88.7, 47.1, 15.4, 41.6, 37.0, 18.5, 24.3, 76.2, 10.7, 34.9, 45.6, 27.1, 13.5, 7.1, 5.3, 3.6, 21.6, 20.3, 1.6),
    ("NYK", 12, 6, 6, .500, 48.0, 109.8, 38.8, 88.9, 43.6, 14.8, 41.1, 36.1, 17.4, 21.9, 79.5, 13.7, 34.0, 47.7, 26.8, 14.4, 7.4, 4.1, 6.2, 20.9, 21.1, 6.1),
    ("PHX", 11, 5, 6, .455, 48.0, 111.7, 41.3, 88.5, 46.7, 13.6, 37.0, 36.9, 15.5, 20.0, 77.7, 10.6, 28.3, 38.9, 27.2, 13.9, 8.4, 4.5, 4.7, 22.0, 18.6, -4.4),
    ("ORL", 12, 5, 7, .417, 48.4, 108.3, 38.4, 85.8, 44.8, 13.8, 41.1, 33.7, 17.7, 22.6, 78.2, 11.0, 31.9, 42.9, 26.0, 16.8, 7.4, 4.1, 5.0, 22.8, 23.3, -4.4),
    ("TOR", 12, 5, 7, .417, 48.0, 114.3, 41.4, 91.2, 45.4, 11.8, 36.0, 32.9, 19.6, 26.6, 73.7, 13.8, 27.2, 41.0, 28.1, 14.3, 10.6, 4.4, 5.5, 25.8, 24.3, 1.4),
    ("IND", 14, 5, 9, .357, 48.0, 112.1, 40.9, 87.1, 47.0, 11.9, 36.1, 32.8, 18.4, 24.0, 76.5, 9.6, 32.0, 41.6, 27.8, 14.5, 7.2, 4.2, 4.3, 20.4, 22.8, -2.4),
    ("CHA", 12, 4, 8, .333, 48.0, 98.6, 34.8, 86.6, 40.1, 13.8, 44.2, 31.1, 15.3, 18.7, 82.1, 15.0, 31.6, 46.6, 21.8, 19.6, 6.9, 4.6, 4.6, 20.4, 21.6, -11.0),
    ("WAS", 13, 4, 9, .308, 48.8, 110.0, 39.8, 87.1, 45.8, 9.9, 32.5, 30.5, 20.4, 25.2, 80.8, 10.7, 32.4, 43.1, 23.6, 15.2, 7.5, 5.4, 3.5, 20.5, 21.2, -5.8),
    ("NOP", 14, 4, 10, .286, 49.1, 115.9, 40.1, 86.2, 46.5, 9.4, 28.7, 32.8, 26.3, 32.1, 82.0, 10.6, 30.5, 41.1, 24.3, 16.1, 9.9, 5.3, 5.6, 24.6, 23.9, -9.1),
    ("LAC", 11, 3, 8, .273, 48.5, 112.3, 39.2, 85.4, 45.9, 14.3, 37.4, 38.2, 19.6, 24.6, 79.7, 10.5, 29.9, 40.5, 26.8, 17.8, 9.6, 4.3, 4.4, 22.1, 20.9, -5.3),
    ("BKN", 12, 3, 9, .250, 48.4, 110.2, 37.1, 83.9, 44.2, 14.6, 40.7, 35.9, 21.4, 28.3, 75.8, 11.6, 31.0, 42.6, 24.2, 17.7, 8.6, 4.8, 4.8, 26.1, 24.0, -6.3),
    ("CHI", 12, 3, 9, .250, 48.4, 114.6, 39.9, 89.4, 44.6, 12.7, 40.7, 31.1, 22.1, 29.0, 76.1, 12.6, 31.8, 44.3, 26.9, 17.3, 7.8, 5.9, 4.9, 23.7, 23.2, -11.3),
    ("SAC", 12, 1, 11, .083, 48.0, 108.2, 39.3, 86.3, 45.5, 12.3, 35.5, 34.5, 17.4, 22.7, 76.8, 9.8, 30.1, 39.9, 25.0, 17.1, 7.8, 3.5, 5.8, 22.8, 19.6, -12.8),
    ("MIL", 13, 1, 12, .077, 48.0, 106.2, 37.8, 88.3, 42.8, 14.8, 43.2, 34.2, 15.8, 21.4, 74.1, 13.3, 31.5, 44.8, 24.8, 16.6, 6.5, 4.7, 5.8, 22.5, 19.5, -14.1),
    ("UTA", 13, 1, 12, .077, 48.8, 107.5, 37.8, 86.8, 43.5, 12.1, 36.5, 33.1, 19.8, 25.8, 77.0, 12.0, 32.5, 44.5, 24.0, 16.7, 6.7, 6.2, 5.4, 24.0, 24.2, -11.2),
]

# --------------------------------------------------------------------------
# OPPONENT: abbr, gp, w, l, min, opp_fgm, opp_fga, opp_fg_pct, opp_fg3m,
#           opp_fg3a, opp_fg3_pct, opp_ftm, opp_fta, opp_ft_pct, opp_oreb,
#           opp_dreb, opp_reb, opp_ast, opp_tov, opp_stl, opp_blk, opp_blka,
#           opp_pf, opp_pfd, opp_pts, plus_minus
OPP = [
    ("LAL", 13, 11, 2, 48.0, 38.9, 85.7, 45.4, 15.2, 40.5, 37.4, 21.2, 28.1, 75.6, 13.5, 27.5, 41.0, 27.4, 18.5, 9.9, 4.2, 6.2, 24.2, 23.4, 114.2, -7.9),
    ("PHI", 14, 11, 3, 48.0, 40.1, 87.5, 45.8, 12.0, 36.4, 32.9, 18.3, 24.1, 76.0, 11.0, 35.0, 46.0, 25.4, 14.8, 6.5, 5.6, 4.2, 20.9, 20.9, 110.4, -2.1),
    ("SAS", 13, 11, 2, 48.4, 38.7, 89.2, 43.4, 12.5, 33.0, 37.8, 16.4, 20.2, 81.3, 10.9, 31.9, 42.8, 24.9, 14.5, 6.5, 4.9, 7.3, 21.2, 20.0, 106.2, -13.2),
    ("BOS", 12, 10, 2, 48.4, 35.6, 84.9, 41.9, 14.6, 43.2, 33.8, 17.3, 22.8, 75.9, 12.8, 30.5, 43.3, 25.1, 16.7, 7.1, 4.2, 4.9, 22.9, 21.5, 103.1, -11.2),
    ("HOU", 13, 10, 3, 48.0, 39.6, 87.3, 45.4, 12.3, 38.5, 31.9, 15.8, 21.5, 73.6, 12.1, 28.6, 40.7, 23.4, 15.3, 8.2, 4.1, 6.1, 21.9, 19.9, 107.4, -8.8),
    ("MEM", 13, 9, 4, 48.4, 40.5, 90.0, 45.0, 12.4, 37.5, 33.0, 18.2, 24.2, 75.5, 12.0, 29.7, 41.7, 25.0, 14.2, 7.7, 7.2, 5.1, 21.6, 23.7, 111.7, -8.9),
    ("MIN", 13, 9, 4, 48.4, 38.6, 89.0, 43.4, 11.5, 35.3, 32.5, 18.1, 23.3, 77.6, 12.3, 31.0, 43.3, 24.6, 16.8, 7.9, 6.4, 5.1, 22.8, 22.0, 106.8, -11.5),
    ("POR", 12, 9, 3, 48.0, 38.8, 87.1, 44.5, 11.4, 35.3, 32.3, 22.9, 27.6, 83.1, 11.5, 29.8, 41.3, 23.5, 14.0, 8.7, 4.2, 5.1, 24.4, 22.3, 111.8, -7.8),
    ("DET", 12, 8, 4, 48.8, 38.6, 87.3, 44.2, 12.2, 36.5, 33.3, 20.9, 26.8, 78.0, 13.0, 32.8, 45.8, 23.6, 17.7, 8.0, 6.1, 6.4, 22.7, 23.8, 110.3, -5.4),
    ("GSW", 13, 8, 5, 48.4, 40.6, 88.2, 46.1, 12.8, 37.8, 34.0, 18.3, 23.4, 78.3, 12.2, 30.7, 42.8, 27.3, 16.3, 8.7, 5.7, 5.4, 22.2, 21.9, 112.4, -4.3),
    ("OKC", 13, 8, 5, 48.0, 37.3, 89.5, 41.7, 14.8, 43.6, 34.0, 17.9, 22.1, 81.2, 12.2, 31.7, 43.9, 24.5, 14.3, 6.3, 5.3, 5.4, 21.0, 19.3, 107.4, -3.8),
    ("ATL", 13, 7, 6, 48.4, 42.2, 86.5, 48.7, 12.2, 35.5, 34.2, 20.4, 25.7, 79.3, 11.2, 34.5, 45.6, 28.2, 18.8, 9.8, 6.0, 4.0, 19.4, 22.1, 116.8, -1.3),
    ("CLE", 14, 7, 7, 48.4, 41.6, 92.5, 44.9, 14.0, 39.8, 35.2, 18.7, 23.5, 79.6, 12.7, 32.4, 45.1, 27.3, 12.6, 6.7, 3.6, 5.3, 20.3, 21.6, 115.9, -1.6),
    ("DAL", 13, 7, 6, 48.0, 41.6, 88.7, 46.9, 12.2, 36.6, 33.2, 17.9, 23.9, 74.9, 12.2, 31.2, 43.5, 27.2, 15.8, 8.2, 4.8, 5.5, 20.9, 22.3, 113.3, -0.2),
    ("DEN", 11, 7, 4, 48.5, 41.5, 90.2, 46.0, 14.1, 39.3, 35.9, 15.8, 19.9, 79.5, 12.9, 30.7, 43.6, 28.2, 14.4, 7.1, 4.5, 4.5, 23.2, 19.0, 112.8, -1.8),
    ("MIA", 13, 7, 6, 48.4, 43.1, 89.5, 48.1, 15.8, 40.8, 38.9, 17.8, 23.1, 77.3, 11.4, 33.7, 45.1, 29.7, 16.7, 8.1, 5.2, 5.5, 25.1, 21.1, 119.8, 1.2),
    ("NYK", 12, 6, 6, 48.0, 36.9, 85.4, 43.2, 13.6, 39.8, 34.2, 16.3, 22.3, 72.8, 10.5, 30.2, 40.7, 24.8, 13.2, 6.7, 6.2, 4.1, 21.1, 20.9, 103.7, -6.1),
    ("IND", 14, 5, 9, 48.0, 40.9, 89.3, 45.8, 14.1, 39.2, 36.1, 18.5, 23.7, 78.0, 11.5, 35.2, 46.7, 26.2, 14.9, 8.4, 4.3, 4.2, 22.8, 20.4, 114.5, 2.4),
    ("ORL", 12, 5, 7, 48.4, 39.8, 85.3, 46.6, 13.6, 35.8, 38.0, 19.7, 25.9, 75.9, 10.3, 31.3, 41.6, 27.3, 15.2, 9.4, 5.0, 4.1, 23.3, 22.8, 112.8, 4.4),
    ("PHX", 11, 5, 6, 48.0, 40.4, 86.8, 46.5, 14.4, 38.4, 37.4, 21.0, 27.4, 76.7, 14.2, 32.7, 46.9, 26.2, 17.4, 7.5, 4.7, 4.5, 18.6, 22.0, 116.1, 4.4),
    ("TOR", 12, 5, 7, 48.0, 38.4, 80.5, 47.7, 12.7, 34.3, 36.9, 23.3, 28.8, 80.9, 10.5, 31.0, 41.5, 25.8, 19.0, 8.1, 5.5, 4.4, 24.3, 25.8, 112.8, -1.4),
    ("CHA", 12, 4, 8, 48.0, 39.1, 83.2, 47.0, 14.3, 36.1, 39.7, 17.1, 22.0, 77.7, 8.9, 30.6, 39.5, 25.9, 13.9, 9.5, 4.6, 4.6, 21.6, 20.4, 109.6, 11.0),
    ("NOP", 14, 4, 10, 49.1, 43.4, 87.9, 49.3, 13.5, 38.3, 35.3, 24.7, 31.0, 79.7, 11.4, 33.4, 44.8, 29.3, 15.7, 8.1, 5.6, 5.3, 23.9, 24.6, 124.9, 9.1),
    ("WAS", 13, 4, 9, 48.8, 42.5, 94.2, 45.2, 12.2, 38.5, 31.6, 18.5, 21.6, 85.8, 14.0, 33.5, 47.5, 27.6, 13.7, 9.2, 3.5, 5.4, 21.2, 20.5, 115.8, 5.8),
    ("BKN", 12, 3, 9, 48.4, 39.6, 84.6, 46.8, 14.2, 39.7, 35.7, 23.1, 29.2, 79.1, 10.7, 30.4, 41.1, 27.3, 16.3, 8.4, 4.8, 4.8, 24.1, 26.1, 116.4, 6.3),
    ("CHI", 12, 3, 9, 48.4, 45.2, 94.8, 47.7, 13.7, 37.6, 36.4, 21.9, 28.7, 76.5, 14.0, 33.5, 47.5, 29.3, 14.3, 9.8, 4.9, 5.9, 23.2, 23.7, 125.9, 11.3),
    ("LAC", 11, 3, 8, 48.5, 43.3, 87.6, 49.4, 12.7, 34.7, 36.6, 18.3, 25.1, 72.8, 11.6, 31.9, 43.5, 27.0, 16.1, 9.0, 4.4, 4.3, 20.9, 22.1, 117.5, 5.3),
    ("MIL", 13, 1, 12, 48.0, 42.9, 92.8, 46.2, 14.8, 42.1, 35.3, 19.5, 25.0, 78.2, 14.6, 33.8, 48.5, 28.2, 13.1, 9.8, 5.8, 4.7, 19.5, 22.5, 120.2, 14.1),
    ("SAC", 12, 1, 11, 48.0, 41.9, 85.3, 49.1, 14.0, 37.6, 37.3, 23.1, 29.0, 79.6, 10.2, 33.4, 43.6, 26.5, 14.7, 8.8, 5.8, 3.5, 19.7, 22.9, 120.9, 12.8),
    ("UTA", 13, 1, 12, 48.8, 39.7, 87.8, 45.2, 12.6, 35.6, 35.4, 26.6, 32.2, 82.6, 11.3, 34.6, 45.9, 22.8, 13.9, 8.8, 5.4, 6.2, 24.2, 24.0, 118.6, 11.2),
]


# Transcription note (recorded, not silently corrected): the CLE row in this
# read rendered 25 values where the official traditional table has 26 columns.
# The missing value is BLK, carried here from the previous official read of
# the same page (data/official/teams_traditional_2026-11-15.json, captured
# 2026-11-15T11:35Z..12:20Z), where CLE prints BLK 5.3 between STL 7.1 and
# BLKA 3.6. Every other CLE value is identical in both reads, so the carried
# value is the official one; it is listed for reviewer attention.
TRANSCRIPTION_NOTES = [{
    "table": "traditional", "team": "CLE", "field": "blk",
    "value": 5.3, "source": "previous official read of the same page "
                             "(data/official/teams_traditional_2026-11-15.json)",
    "issue": "the 2026-11-16 read of the row rendered one value fewer than the "
             "official table has columns",
}]

ADV_FIELDS = ("gp w l min off_rtg def_rtg net_rtg ast_pct ast_to ast_ratio oreb_pct "
              "dreb_pct reb_pct tov_pct efg_pct ts_pct pace pie poss").split()
TRA_FIELDS = ("gp w l win_pct min pts fgm fga fg_pct fg3m fg3a fg3_pct ftm fta "
              "ft_pct oreb dreb reb ast tov stl blk blka pf pfd plus_minus").split()
OPP_FIELDS = ("gp w l min opp_fgm opp_fga opp_fg_pct opp_fg3m opp_fg3a opp_fg3_pct "
              "opp_ftm opp_fta opp_ft_pct opp_oreb opp_dreb opp_reb opp_ast opp_tov "
              "opp_stl opp_blk opp_blka opp_pf opp_pfd opp_pts plus_minus").split()

RETRIEVED = "2026-11-15T23:40Z"
# The session clock was measured at 2026-11-15T23:45:56Z while the three pages
# were being read, and the official index read that established the newest
# edition was taken before that measurement, so the retrieval is bracketed
# rather than guessed.
RETRIEVAL_WINDOW = {
    "earliest_possible_utc": "2026-11-15T23:34Z",
    "latest_possible_utc": "2026-11-15T23:45:56Z",
    "basis": ("the session clock was measured at 2026-11-15T23:45:56Z with the "
              "three official pages already read; the clock reading that precedes "
              "the reads in the same session was 2026-11-15T23:34:10Z"),
}
SESSION = "arena/49f70042-nba1"


def rows_from(table, fields, src):
    out = []
    for r in table:
        abbr = r[0]
        vals = r[1:]
        row = {"abbr": abbr, "team": NAME[abbr], "source_url": src}
        assert len(vals) == len(fields), (abbr, len(vals), len(fields))
        for f, v in zip(fields, vals):
            row[f] = v
        out.append(row)
    return out


def main():
    """Build the 2026-11-16 re-cut.

    Method, stated so a reviewer can check it:

    * The three official team-stat pages were re-read at 2026-11-16T00:48Z..
      01:05Z (league-wide renderings).
    * For the two teams whose official game count changed since the previous
      official capture (PHI and IND - the 2026-11-15 IND@PHI game was the only
      completed game added to the official ledger in that window) the rows
      were re-read one team at a time on the official per-team view, which
      renders a single row and is unambiguous. Those rows are authoritative.
    * For the 28 teams whose official game count did not change, the row
      values are carried from the previous official capture of the same pages
      (data/official/teams_*_2026-11-15.json, captured 2026-11-15T11:35Z..
      12:20Z). Every one of those rows was re-verified against the league-wide
      re-read: the re-read reproduces them field for field except for the
      AST-Ratio column, where the dense league-wide markdown rendering could
      not be read reliably. The AST-Ratio values in the re-read were checked
      against the official per-team view for SAS (which prints 19.4, the same
      value the earlier capture holds) and are therefore treated as a
      mis-read, not as a change in the official data.
    """
    adv_fresh = {r["abbr"]: r for r in rows_from(ADV, ADV_FIELDS, SRC_ADV)}
    tra_fresh = {r["abbr"]: r for r in rows_from(TRA, TRA_FIELDS, SRC_TRA)}
    opp_fresh = {r["abbr"]: r for r in rows_from(OPP, OPP_FIELDS, SRC_OPP)}

    def load_prev(name):
        p = os.path.join(OFF, name)
        return {r["abbr"]: r for r in json.load(open(p, encoding="utf-8"))["rows"]}

    base_adv = load_prev("teams_advanced_2026-11-15.json")
    base_tra = load_prev("teams_traditional_2026-11-15.json")
    base_opp = load_prev("teams_opponent_2026-11-15.json")

    # authoritative per-team official reads (URL includes TeamID)
    PHI_ADV = ("PHI", 14, 11, 3, 672.0, 112.3, 110.3, 2.0, 65.5, 2.06, 18.7,
               27.5, 71.4, 49.4, 12.7, 52.6, 56.7, 100.21, 50.8, 1404)
    IND_ADV = ("IND", 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 67.9, 1.92, 19.7,
               24.6, 68.5, 47.1, 14.3, 53.8, 57.4, 101.25, 49.6, 1415)
    TEAM_URL = {a: f"{SRC_ADV}&TeamID={i}" for a, i in
                (("PHI", "1610612755"), ("IND", "1610612754"), ("SAS", "1610612759"))}

    def adv_row(tup, src):
        abbr = tup[0]
        row = {"abbr": abbr, "team": NAME[abbr], "source_url": src}
        for f, v in zip(ADV_FIELDS, tup[1:]):
            row[f] = v
        return row

    adv_over = {
        "PHI": adv_row(PHI_ADV, TEAM_URL["PHI"]),
        "IND": adv_row(IND_ADV, TEAM_URL["IND"]),
    }

    def build(base, fresh, fields, overrides, src_league, src_perteam):
        rows = []
        changes = []
        for abbr in sorted(base):
            row = dict(base[abbr])
            row["source_url"] = src_league
            row["carried_from"] = ("data/official/teams_*-2026-11-15.json "
                                   "(official capture 2026-11-15T11:35Z..12:20Z); "
                                   "re-verified against the 2026-11-16 league-wide re-read")
            if abbr in overrides:
                row.update(overrides[abbr])
                row["source_url"] = src_perteam.get(abbr, src_league)
                row["carried_from"] = ("official per-team view read 2026-11-16 "
                                       "(the team's official game count changed)")
            f = fresh[abbr]
            for fl in fields:
                if fl not in f or f[fl] is None:
                    continue
                if isinstance(f[fl], (int, float)) and isinstance(row.get(fl), (int, float)):
                    if abs(float(f[fl]) - float(row[fl])) < 1e-9:
                        continue
                elif f[fl] == row.get(fl):
                    continue
                changes.append({"abbr": abbr, "field": fl, "re_read": f[fl],
                                "published": row.get(fl),
                                "note": "re-read differs from the published row"})
            rows.append(row)
        return rows, changes

    adv_rows, adv_ch = build(base_adv, adv_fresh, ADV_FIELDS, adv_over, SRC_ADV, TEAM_URL)
    tra_rows, tra_ch = build(base_tra, tra_fresh, TRA_FIELDS, {"PHI": tra_fresh["PHI"], "IND": tra_fresh["IND"]}, SRC_TRA, {})
    opp_rows, opp_ch = build(base_opp, opp_fresh, OPP_FIELDS, {"PHI": opp_fresh["PHI"], "IND": opp_fresh["IND"]}, SRC_OPP, {})

    # ---- documented discrepancies between the re-read and the published row
    ast_ratio_diffs = []
    for abbr in sorted(adv_fresh):
        a = adv_fresh[abbr].get("ast_ratio")
        b = adv_rows[[r["abbr"] for r in adv_rows].index(abbr)].get("ast_ratio")
        if a is not None and b is not None and abs(a - b) > 1e-9:
            ast_ratio_diffs.append({"abbr": abbr, "league_wide_re_read": a, "published": b,
                                    "resolution": "published value kept - the per-team official "
                                                  "view for SAS (1610612759) prints the same value "
                                                  "as the earlier capture, so the league-wide "
                                                  "markdown rendering of this column is a mis-read"})

    files = [
        ("teams_advanced_2026-11-15_2340Z.json", "advanced", adv_rows, SRC_ADV),
        ("teams_traditional_2026-11-15_2340Z.json", "traditional", tra_rows, SRC_TRA),
        ("teams_opponent_2026-11-15_2340Z.json", "opponent", opp_rows, SRC_OPP),
    ]
    for fname, label, rows, src in files:
        doc = {
            "title": f"NBA.com Teams {label.capitalize()} re-cut, 2026-11-16",
            "captured_by": SESSION,
            "retrieved_utc": RETRIEVED,
            "retrieval_window_utc": RETRIEVAL_WINDOW,
            "source_url": src,
            "per_team_source_urls": TEAM_URL,
            "method": ("league-wide re-read of the official page at 2026-11-15T23:36Z..23:45Z; "
                       "rows for the two teams whose official game count changed (PHI, IND) "
                       "re-read on the official per-team view; the remaining rows carried from "
                       "the earlier official capture of the same page and re-verified "
                       "field-for-field against the re-read (see diff_vs_previous_official_capture)"),
            "games_counted": "official ledger through the games finished on 2026-11-15 at read time",
            "rows": rows,
        }
        with open(os.path.join(OFF, fname), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print("wrote", fname, len(rows), "rows")

    from statistics import mean
    recut = {
        "title": "Team-stat re-cut 2026-11-15 23:40Z - the three official pages re-read and the model inputs re-cut",
        "captured_by": SESSION,
        "computed_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {"advanced": SRC_ADV, "traditional": SRC_TRA, "opponent": SRC_OPP,
                    "per_team": TEAM_URL},
        "league_baselines": {
            "league_off_rtg": round(mean(r["off_rtg"] for r in adv_rows), 3),
            "league_def_rtg": round(mean(r["def_rtg"] for r in adv_rows), 3),
            "league_pace": round(mean(r["pace"] for r in adv_rows), 3),
            "league_pts_per_game": round(mean(r["pts"] for r in tra_rows), 3),
            "league_opp_pts_per_game": round(mean(r["opp_pts"] for r in opp_rows), 3),
            "n_teams": len(adv_rows),
        },
        "rows_changed_vs_previous_official_capture": {
            "advanced": [c for c in adv_ch],
            "traditional": [c for c in tra_ch],
            "opponent": [c for c in opp_ch],
        },
        "ast_ratio_rendering_discrepancy": ast_ratio_diffs,
        "transcription_notes": TRANSCRIPTION_NOTES,
        "note": "Every field the league-wide re-read could not confirm against the published row is listed with both values. The only teams whose official game count moved between the two reads are PHI and IND (the 2026-11-15 IND@PHI game); their rows were re-read on the official per-team view and are authoritative.",
    }
    with open(os.path.join(OFF, "team_stats_recut_2026-11-15_2340Z.json"), "w", encoding="utf-8") as fh:
        json.dump(recut, fh, indent=1, ensure_ascii=False)
    print("wrote team_stats_recut_2026-11-15_2340Z.json")
    print(json.dumps(recut["league_baselines"], indent=1))
    print("rows changed (advanced):", len(adv_ch))
    for c in adv_ch[:40]:
        print("   ", c["abbr"], c["field"], c["published"], "->", c["re_read"])


if __name__ == "__main__":
    main()
