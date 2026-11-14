#!/usr/bin/env python3
"""Transcribe + compare the 2026-11-14 18:40-19:10Z live official reads.

Every table below is a verbatim transcription of what the official page printed at
read time. Nothing is computed here; the only derived step is a row-by-row
comparison against the copy already committed to the repository, which is printed
and written to compare.json so a reviewer can check each line.

Sources (all fetched live in session arena/cc5a6652-nba1, 2026-11-14):
  SLATE  https://www.nba.com/games?date=<date>           (11/13 .. 11/17)
  STD    https://www.nba.com/standings
  ADV    https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season
  INJ    https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf
         https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf
  IDX    https://official.nba.com/nba-injury-report-2026-27-season/
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.dirname(os.path.abspath(__file__))
READ_AT = "2026-11-14T18:40Z..19:10Z"

SLATE_URL = "https://www.nba.com/games?date=%s"
STANDINGS_URL = "https://www.nba.com/standings"
ADV_URL = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
PDF_0415 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf"
PDF_0130 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"
IDX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# --------------------------------------------------------------- 1. the slate
# (date, time_et printed on the card, away_abbr, away_record, home_abbr, home_record, game_id)
SLATE = [
    # ---- 2026-11-13: nine FINAL results, read off the same day page
    ("2026-11-13", "Final", "NYK", "6-6", "IND", "5-8", "0022600034", 104, 106, ""),
    ("2026-11-13", "Final", "MIL", "1-12", "ORL", "5-7", "0022600035", 99, 107, ""),
    ("2026-11-13", "Final", "CLE", "6-7", "MIA", "6-6", "0022600036", 121, 133, ""),
    ("2026-11-13", "Final/OT", "ATL", "7-6", "CHI", "2-9", "0022600037", 117, 125, "OT"),
    ("2026-11-13", "Final", "MEM", "8-4", "NOP", "4-9", "0022600038", 142, 111, ""),
    ("2026-11-13", "Final", "UTA", "1-12", "HOU", "10-3", "0022600039", 118, 125, ""),
    ("2026-11-13", "Final", "GSW", "8-5", "SAS", "11-2", "0022600040", 85, 123, ""),
    ("2026-11-13", "Final", "POR", "9-3", "SAC", "1-11", "0022600041", 120, 107, ""),
    ("2026-11-13", "Final", "OKC", "8-5", "LAC", "3-8", "0022600042", 112, 113, ""),
    # ---- 2026-11-14 horizon (5 games, all scheduled)
    ("2026-11-14", "7:00 PM ET", "DEN", "6-4", "NOP", "4-9", "0022600231", None, None, ""),
    ("2026-11-14", "7:30 PM ET", "DAL", "7-5", "CLE", "6-7", "0022600232", None, None, ""),
    ("2026-11-14", "8:00 PM ET", "DET", "8-3", "MIA", "6-6", "0022600233", None, None, ""),
    ("2026-11-14", "8:00 PM ET", "BKN", "3-8", "MEM", "8-4", "0022600234", None, None, ""),
    ("2026-11-14", "8:00 PM ET", "CHI", "2-9", "MIN", "9-3", "0022600235", None, None, ""),
    # ---- 2026-11-15 horizon (9 games)
    ("2026-11-15", "1:00 PM ET", "IND", "5-8", "PHI", "10-3", "0022600236", None, None, ""),
    ("2026-11-15", "4:00 PM ET", "LAL", "11-2", "PHX", "5-6", "0022600237", None, None, ""),
    ("2026-11-15", "4:30 PM ET", "CHA", "4-8", "LAC", "3-8", "0022600238", None, None, ""),
    ("2026-11-15", "5:00 PM ET", "SAS", "11-2", "UTA", "1-12", "0022600239", None, None, ""),
    ("2026-11-15", "6:00 PM ET", "DAL", "7-5", "BOS", "10-2", "0022600240", None, None, ""),
    ("2026-11-15", "6:00 PM ET", "NYK", "6-6", "TOR", "5-7", "0022600241", None, None, ""),
    ("2026-11-15", "7:00 PM ET", "HOU", "10-3", "WAS", "4-9", "0022600242", None, None, ""),
    ("2026-11-15", "8:00 PM ET", "ATL", "7-6", "MIL", "1-12", "0022600243", None, None, ""),
    ("2026-11-15", "9:00 PM ET", "OKC", "8-5", "SAC", "1-11", "0022600244", None, None, ""),
    # ---- 2026-11-16 horizon (8 games)
    ("2026-11-16", "7:00 PM ET", "ORL", "5-7", "BOS", "10-2", "0022600245", None, None, ""),
    ("2026-11-16", "7:00 PM ET", "CHI", "2-9", "CLE", "6-7", "0022600246", None, None, ""),
    ("2026-11-16", "7:00 PM ET", "MEM", "8-4", "WAS", "4-9", "0022600247", None, None, ""),
    ("2026-11-16", "7:30 PM ET", "PHI", "10-3", "BKN", "3-8", "0022600248", None, None, ""),
    ("2026-11-16", "7:30 PM ET", "HOU", "10-3", "MIA", "6-6", "0022600249", None, None, ""),
    ("2026-11-16", "8:00 PM ET", "POR", "9-3", "MIN", "9-3", "0022600250", None, None, ""),
    ("2026-11-16", "8:00 PM ET", "GSW", "8-5", "NOP", "4-9", "0022600251", None, None, ""),
    ("2026-11-16", "9:00 PM ET", "PHX", "5-6", "DEN", "6-4", "0022600252", None, None, ""),
    # ---- 2026-11-17 horizon (5 games)
    ("2026-11-17", "7:30 PM ET", "NYK", "6-6", "TOR", "5-7", "0022600253", None, None, ""),
    ("2026-11-17", "8:00 PM ET", "POR", "9-3", "MIN", "9-3", "0022600254", None, None, ""),
    ("2026-11-17", "8:00 PM ET", "DET", "8-3", "SAS", "11-2", "0022600255", None, None, ""),
    ("2026-11-17", "11:00 PM ET", "CHA", "4-8", "LAL", "11-2", "0022600256", None, None, ""),
    ("2026-11-17", "10:30 PM ET", "UTA", "1-12", "LAC", "3-8", "0022600257", None, None, ""),
]

# ------------------------------------------------ 2. the standings page (live)
# (team, conf, w, l, win_pct, gb, conf_rec, div_rec, home, road, neutral, ot, last10, streak)
STANDINGS = [
    ("Boston Celtics", "East", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("Philadelphia 76ers", "East", 10, 3, ".769", "0.5", "10-3", "3-1", "5-2", "5-1", "0-0", "0-0", "7-3", "W 1"),
    ("Detroit Pistons", "East", 8, 3, ".727", "1.5", "8-2", "0-0", "3-2", "5-1", "0-0", "1-0", "7-3", "W 2"),
    ("Atlanta Hawks", "East", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("Miami Heat", "East", 6, 6, ".500", "4", "3-2", "1-1", "2-3", "4-3", "0-0", "1-0", "6-4", "W 3"),
    ("New York Knicks", "East", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("Cleveland Cavaliers", "East", 6, 7, ".462", "4.5", "5-5", "1-0", "4-2", "2-5", "0-0", "1-0", "4-6", "L 1"),
    ("Toronto Raptors", "East", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("Orlando Magic", "East", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("Indiana Pacers", "East", 5, 8, ".385", "5.5", "3-5", "0-1", "2-4", "3-3", "0-1", "0-0", "3-7", "W 2"),
    ("Charlotte Hornets", "East", 4, 8, ".333", "6", "4-7", "2-2", "3-4", "1-4", "0-0", "0-0", "3-7", "L 1"),
    ("Washington Wizards", "East", 4, 9, ".308", "6.5", "4-8", "2-3", "2-3", "2-6", "0-0", "0-1", "2-8", "L 6"),
    ("Brooklyn Nets", "East", 3, 8, ".273", "6.5", "2-7", "0-2", "1-3", "2-5", "0-0", "0-1", "3-7", "W 1"),
    ("Chicago Bulls", "East", 2, 9, ".182", "7.5", "2-8", "1-0", "1-4", "1-5", "0-0", "1-0", "2-8", "W 1"),
    ("Milwaukee Bucks", "East", 1, 12, ".077", "9.5", "1-9", "1-2", "1-6", "0-6", "0-0", "0-0", "1-9", "L 9"),
    ("San Antonio Spurs", "West", 11, 2, ".846", "--", "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("Los Angeles Lakers", "West", 11, 2, ".846", "--", "6-2", "4-1", "5-1", "6-1", "0-0", "0-0", "8-2", "W 7"),
    ("Houston Rockets", "West", 10, 3, ".769", "1", "6-3", "2-1", "7-1", "3-2", "0-0", "0-0", "7-3", "W 3"),
    ("Portland Trail Blazers", "West", 9, 3, ".750", "1.5", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("Minnesota Timberwolves", "West", 9, 3, ".750", "1.5", "5-2", "1-0", "5-1", "4-2", "0-0", "0-1", "7-3", "W 5"),
    ("Memphis Grizzlies", "West", 8, 4, ".667", "2.5", "7-3", "1-1", "2-4", "6-0", "0-0", "0-1", "6-4", "W 1"),
    ("Golden State Warriors", "West", 8, 5, ".615", "3", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("Oklahoma City Thunder", "West", 8, 5, ".615", "3", "5-5", "1-2", "5-0", "3-5", "0-0", "0-0", "5-5", "L 3"),
    ("Denver Nuggets", "West", 6, 4, ".600", "3.5", "4-4", "0-2", "2-2", "3-2", "1-0", "1-0", "6-4", "W 1"),
    ("Dallas Mavericks", "West", 7, 5, ".583", "3.5", "3-5", "1-3", "5-2", "2-3", "0-0", "0-0", "6-4", "L 1"),
    ("Phoenix Suns", "West", 5, 6, ".455", "5", "3-6", "2-1", "5-3", "0-3", "0-0", "0-0", "5-5", "W 2"),
    ("New Orleans Pelicans", "West", 4, 9, ".308", "7", "3-7", "1-1", "3-5", "1-4", "0-0", "2-1", "4-6", "L 5"),
    ("LA Clippers", "West", 3, 8, ".273", "7", "3-6", "1-4", "3-3", "0-5", "0-0", "0-1", "2-8", "W 1"),
    ("Sacramento Kings", "West", 1, 11, ".083", "9.5", "1-9", "0-2", "0-7", "1-4", "0-0", "0-0", "1-9", "L 5"),
    ("Utah Jazz", "West", 1, 12, ".077", "10", "1-9", "0-2", "2-3", "0-6", "0-0", "0-0", "2-8", "L 3"),
]

# --------------------------------- 3. teams advanced (live), column order as printed
ADV_COLS = ["gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
            "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
            "pace", "pie", "poss"]
ADV = [
    ("LAL", [13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306]),
    ("SAS", [13, 11, 2, 629.0, 119.6, 106.6, 13.0, 65.4, 2.28, 19.4, 33.9, 71.3, 52.7, 12.3, 53.4, 57.6, 98.94, 56.7, 1298]),
    ("BOS", [12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 19.1, 32.7, 67.5, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168]),
    ("HOU", [13, 10, 3, 624.0, 119.3, 110.2, 9.1, 64.4, 1.85, 19.0, 35.2, 67.8, 52.0, 14.8, 55.1, 59.3, 97.42, 55.8, 1266]),
    ("PHI", [13, 10, 3, 624.0, 111.0, 109.5, 1.5, 65.8, 2.04, 18.6, 28.0, 70.8, 49.3, 12.7, 51.6, 55.9, 100.04, 50.9, 1302]),
    ("MIN", [12, 9, 3, 581.0, 117.2, 103.8, 13.4, 59.9, 1.64, 17.9, 35.9, 69.5, 53.2, 15.7, 56.2, 58.5, 101.08, 56.1, 1222]),
    ("POR", [12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 17.9, 33.3, 70.2, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208]),
    ("DET", [11, 8, 3, 538.0, 114.1, 106.9, 7.2, 66.6, 1.92, 19.2, 28.6, 67.1, 48.4, 14.1, 54.7, 58.5, 99.17, 55.3, 1114]),
    ("GSW", [13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 19.4, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307]),
    ("MEM", [12, 8, 4, 581.0, 117.8, 110.0, 7.8, 65.5, 1.71, 18.8, 33.6, 71.8, 53.2, 15.7, 55.3, 59.8, 100.87, 53.2, 1222]),
    ("OKC", [13, 8, 5, 624.0, 112.7, 109.0, 3.7, 55.5, 1.72, 16.6, 31.9, 68.5, 50.8, 13.5, 51.4, 55.4, 98.58, 53.3, 1282]),
    ("ATL", [13, 7, 6, 629.0, 113.3, 111.9, 1.4, 71.6, 2.07, 20.5, 33.2, 69.2, 49.7, 14.6, 52.8, 55.7, 103.55, 48.5, 1356]),
    ("DAL", [12, 7, 5, 576.0, 112.5, 111.7, 0.8, 63.6, 1.60, 18.4, 33.6, 66.7, 50.2, 16.4, 53.9, 57.4, 100.50, 50.3, 1207]),
    ("CLE", [13, 6, 7, 629.0, 116.2, 115.3, 0.9, 64.8, 2.02, 19.0, 28.7, 67.7, 48.8, 13.2, 55.3, 58.7, 99.62, 50.7, 1306]),
    ("DEN", [10, 6, 4, 485.0, 115.9, 115.1, 0.7, 66.7, 2.08, 19.7, 29.7, 67.4, 49.1, 13.5, 55.0, 59.1, 97.58, 52.2, 988]),
    ("MIA", [12, 6, 6, 581.0, 113.2, 116.4, -3.2, 70.3, 2.04, 19.9, 29.6, 71.2, 49.7, 13.9, 54.0, 57.5, 102.44, 49.0, 1242]),
    ("NYK", [12, 6, 6, 576.0, 114.5, 108.6, 5.9, 69.2, 1.86, 18.9, 37.3, 72.1, 54.4, 15.0, 51.9, 55.7, 95.63, 53.3, 1150]),
    ("IND", [13, 5, 8, 624.0, 110.1, 111.7, -1.5, 68.0, 1.85, 19.5, 24.9, 67.7, 47.0, 14.7, 53.5, 57.1, 101.15, 49.6, 1312]),
    ("ORL", [12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 18.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185]),
    ("PHX", [11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 19.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080]),
    ("TOR", [12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 19.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197]),
    ("CHA", [12, 4, 8, 576.0, 101.9, 113.1, -11.2, 62.6, 1.11, 15.8, 35.7, 73.7, 53.5, 20.2, 48.1, 52.0, 96.83, 42.9, 1161]),
    ("NOP", [13, 4, 9, 639.0, 111.4, 120.2, -8.8, 60.1, 1.47, 17.0, 29.7, 68.3, 49.0, 15.7, 52.2, 58.2, 102.08, 46.2, 1359]),
    ("WAS", [13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 17.0, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315]),
    ("BKN", [11, 3, 8, 533.0, 109.3, 114.4, -5.2, 65.3, 1.35, 17.2, 31.0, 70.8, 50.7, 17.7, 52.8, 57.4, 99.83, 47.0, 1109]),
    ("LAC", [11, 3, 8, 533.0, 110.7, 115.8, -5.1, 68.4, 1.51, 18.8, 30.4, 67.2, 48.8, 17.6, 54.3, 58.4, 100.55, 47.4, 1116]),
    ("CHI", [11, 2, 9, 533.0, 109.0, 122.0, -12.9, 67.6, 1.56, 18.1, 30.7, 64.6, 47.5, 16.4, 51.3, 55.8, 103.83, 44.0, 1154]),
    ("MIL", [13, 1, 12, 624.0, 105.7, 120.0, -14.2, 65.6, 1.49, 17.5, 30.5, 64.3, 47.3, 16.6, 51.1, 54.3, 100.31, 42.0, 1305]),
    ("SAC", [12, 1, 11, 576.0, 107.3, 119.5, -12.2, 63.7, 1.46, 17.9, 28.4, 69.1, 48.1, 16.9, 52.6, 56.2, 101.00, 42.8, 1210]),
    ("UTA", [13, 1, 12, 634.0, 105.0, 116.4, -11.3, 63.5, 1.44, 17.0, 29.5, 68.8, 48.6, 16.3, 50.4, 54.7, 100.50, 45.3, 1330]),
]

# ------------------------------------ 4. the 11/14 01:30 PM ET edition (newest)
# Only the rows that A) are for 11/14 games and B) carry a named player/status.
# "NOT YET SUBMITTED" team rows are recorded separately in submission_state.
INJ_NEWEST_14 = [
    ("DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    ("DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    ("DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    ("DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
    ("DEN@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    ("DEN@NOP", "New Orleans Pelicans", "Missi, Yves", "Probable", "Injury/Illness - Left Knee Contusion / Bone Bruise"),
    ("DEN@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy"),
    ("DEN@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("DEN@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("DAL@CLE", "Dallas Mavericks", "Christie, Max", "Doubtful", "Injury/Illness - Left Ankle Sprain"),
    ("DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion"),
    ("DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("DAL@CLE", "Cleveland Cavaliers", "Allen, Jarrett", "Questionable", "Injury/Illness - Right Knee Injury"),
    ("DAL@CLE", "Cleveland Cavaliers", "Harden, James", "Questionable", "Injury/Illness - Left Lower Leg/Calf Tightness"),
    ("DAL@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    ("DAL@CLE", "Cleveland Cavaliers", "Mitchell, Donovan", "Questionable", "Injury/Illness - Left Knee Contusion/Injury Management"),
    ("DAL@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain"),
    ("DAL@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("DAL@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way"),
    ("DAL@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Hamstring Injury Management"),
    ("BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Probable", "Injury/Illness - Illness"),
    ("BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    ("BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness"),
    ("CHI@MIN", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    ("CHI@MIN", "Chicago Bulls", "Claxton, Nic", "Questionable", "Injury/Illness - Left Hamstring Injury Management"),
    ("CHI@MIN", "Chicago Bulls", "Powell, Norman", "Questionable", "Injury/Illness - Low Back Injury Management"),
    ("CHI@MIN", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way"),
    ("CHI@MIN", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain"),
    ("CHI@MIN", "Chicago Bulls", "Swain, Dailyn", "Out", "G League - On Assignment"),
    ("CHI@MIN", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    ("CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Available", "G League - Two-Way"),
    ("DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    ("DET@MIA", "Detroit Pistons", "Jones, Isaac", "Available", "G League - Two-Way"),
    ("DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment"),
    ("DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment"),
    ("DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way"),
    ("DET@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Probable", "Injury/Illness - Right Wrist Sprain"),
    ("DET@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way"),
    ("DET@MIA", "Miami Heat", "Larsson, Pelle", "Doubtful", "Injury/Illness - Illness"),
    ("DET@MIA", "Miami Heat", "Thompson, Klay", "Probable", "Injury/Illness - Left Ankle Sprain"),
]

# team rows that print NOT YET SUBMITTED in the newest edition, and for which date
NYS_NEWEST = [("11/14/2026", "BKN@MEM", "Memphis Grizzlies")]
# 11/15 team-slots printed NOT YET SUBMITTED in the newest edition (15 teams; the
# 16th, Sacramento, is printed on the continuation page without its date cell)
NYS_1115 = ["Indiana Pacers", "Philadelphia 76ers", "Los Angeles Lakers", "Phoenix Suns",
            "Charlotte Hornets", "LA Clippers", "San Antonio Spurs", "Utah Jazz",
            "Dallas Mavericks", "Boston Celtics", "New York Knicks", "Toronto Raptors",
            "Houston Rockets", "Washington Wizards", "Atlanta Hawks", "Milwaukee Bucks",
            "Oklahoma City Thunder", "Sacramento Kings"]

# ---------------------------- 5. the edition the site prices from (04:15 AM ET)
# transcribed only to show what changed between that edition and the newest one
INJ_0415_14 = [
    ("DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    ("DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    ("DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    ("DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
    ("DEN@NOP", "New Orleans Pelicans", None, "NOT YET SUBMITTED", None),
    ("DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion"),
    ("DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("DAL@CLE", "Cleveland Cavaliers", None, "NOT YET SUBMITTED", None),
    ("BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness"),
    ("BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    ("BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness"),
    ("BKN@MEM", "Memphis Grizzlies", None, "NOT YET SUBMITTED", None),
    ("CHI@MIN", "Chicago Bulls", None, "NOT YET SUBMITTED", None),
    ("CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way"),
    ("DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    ("DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way"),
    ("DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment"),
    ("DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment"),
    ("DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way"),
    ("DET@MIA", "Miami Heat", None, "NOT YET SUBMITTED", None),
]


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    checks = []

    def chk(section, item, committed, live, url, ok, note=""):
        checks.append({"section": section, "item": item, "committed": committed,
                       "live": live, "match": bool(ok), "source_url": url, "note": note})

    # ------------------------------------------------ A. 11/13 finals vs verified
    finals = {r["game_id"]: r for r in load("data/verified/finals_2026-11-13.json")["rows"]}
    for date, label, away, arec, home, hrec, gid, ap, hp, ot in SLATE:
        if date != "2026-11-13":
            continue
        c = finals.get(gid)
        chk("A. 2026-11-13 finals", "%s %s @ %s" % (gid, away, home),
            None if not c else "%s %s-%s %s" % (c["status_label"], c["away_pts"], c["home_pts"], c["home"]),
            "%s %s-%s %s" % (label, ap, hp, home),
            "https://www.nba.com/games?date=2026-11-13",
            c is not None and c["away_pts"] == ap and c["home_pts"] == hp,
            "OT counted separately" if ot else "")

    # ------------------------------- B. horizon records vs the game cards (live)
    horizon = load("data/derived/horizon_lines.json")["games"]
    by_id = {g["game_id"]: g for g in horizon}
    lines = {r["game_id"]: r for r in load("site/data/lines.json")["rows"]}
    for date, tip, away, arec, home, hrec, gid, ap, hp, ot in SLATE:
        if ap is not None:
            continue
        g = by_id.get(gid)
        chk("B. horizon schedule", "%s %s @ %s" % (gid, away, home),
            None if not g else "%s / %s, %s" % (g["matchup"], g["tip_et"], g["date"]),
            "%s@%s, %s, %s" % (away, home, tip, date),
            SLATE_URL % date,
            g is not None and g["matchup"] == "%s@%s" % (away, home) and g["date"] == date,
            "matchup + date + tip")
        l = lines.get(gid)
        chk("C. horizon records (site table)",
            "%s %s @ %s" % (gid, away, home),
            None if not l else "%s / %s" % (l["away_rec"], l["home_rec"]),
            "%s / %s" % (arec, hrec),
            SLATE_URL % date,
            l is not None and l["away_rec"] == arec and l["home_rec"] == hrec,
            "record printed on the official game card")

    # --------------------------------------- D. standings page vs committed copy
    std = {r[0]: r for r in load("data/official/standings.json")["rows"]}
    for team, conf, w, l, pct, gb, crec, drec, h, r, n, ot, l10, stk in STANDINGS:
        c = std.get(team)
        chk("D. standings W-L", team,
            None if not c else "%d-%d (%s)" % (c[3], c[4], c[2]),
            "%d-%d (%s)" % (w, l, conf), STANDINGS_URL,
            c is not None and c[3] == w and c[4] == l and c[2] == conf, "")

    # ----------------------------- E. teams advanced vs committed teams file
    adv = {r["abbr"]: r for r in load("data/teams_advanced_2026_27.json")["rows"]}
    for abbr, vals in ADV:
        c = adv.get(abbr)
        diffs = []
        for col, v in zip(ADV_COLS, vals):
            cv = None if c is None else c.get(col)
            if cv is None or abs(float(cv) - float(v)) > 1e-9:
                diffs.append("%s: %r -> %r" % (col, cv, v))
        chk("E. teams advanced", abbr,
            None if c is None else "%d teams in committed file" % len(adv),
            "%s, %s" % (abbr, "no field differs" if not diffs else "; ".join(diffs)),
            ADV_URL, c is not None and not diffs, "all 19 printed columns compared")

    # ---------------------- F. injury edition drift: 04:15 AM ET vs 01:30 PM ET
    old = {}
    for m, t, p, s, why in INJ_0415_14:
        old[(m, t, p)] = (s, why)
    new = {}
    for m, t, p, s, why in INJ_NEWEST_14:
        new[(m, t, p)] = (s, why)
    for key in sorted(set(old) | set(new), key=lambda k: (str(k[0]), str(k[1]), str(k[2]))):
        o, n = old.get(key), new.get(key)
        chk("F. injury status change 04:15 -> 01:30 PM ET",
            "%s %s %s" % (key[0], key[1], key[2] or "(team row)"),
            "absent" if o is None else "%s - %s" % (o[0], o[1]),
            "absent" if n is None else "%s - %s" % (n[0], n[1]),
            PDF_0130, (o or (None,))[0] == (n or (None,))[0],
            "a status or reason that moved between editions")

    # ---------------------------------------------- G. injury edition currency
    site_inj = load("site/data/injuries.json")
    chk("G. edition the site prices from", "site/data/injuries.json report stamp",
        site_inj["report"], "Injury Report: 11/14/26 01:30 PM", PDF_0130, False,
        "the site uses 04:15 AM ET (S10); four newer editions exist, newest 01:30 PM ET")
    chk("G. edition the site prices from", "site/data/meta.json data_windows",
        load("site/data/meta.json")["data_windows"]["injury_report"],
        "11/14/26 01:30 PM ET edition", IDX_URL, False, "9h15m stale at read time")
    # the 5 teams the site says have not filed by 04:15
    old_nys = {(m, t) for m, t, p, s, _ in INJ_0415_14 if s == "NOT YET SUBMITTED" and p is None}
    for m, t in sorted(old_nys):
        filed = any(x[0] == m and x[1] == t for x in INJ_NEWEST_14)
        chk("H. teams that filed after 04:15 AM ET", "%s %s" % (m, t),
            "NOT YET SUBMITTED at 04:15 AM ET",
            "filed: %d player row(s) at 01:30 PM ET" % sum(1 for x in INJ_NEWEST_14 if x[0] == m and x[1] == t) if filed else "still NOT YET SUBMITTED",
            PDF_0130, not filed, "the site renders these as 'team had not filed'")

    matched = sum(1 for c in checks if c["match"])
    doc = {
        "generated_by": "verify/2026-11-14-cc5a6652/capture_live.py",
        "session": "arena/cc5a6652-nba1",
        "read_at_utc": READ_AT,
        "method": ("Each row is a verbatim transcription of the official page read live on 2026-11-14 "
                   "between 18:40Z and 19:10Z, compared to the copy committed in this repository. "
                   "No value is inferred; where a page does not print a value it is recorded as absent."),
        "sources": {"slate": SLATE_URL % "<date>", "standings": STANDINGS_URL,
                    "teams_advanced": ADV_URL, "injury_newest": PDF_0130,
                    "injury_site_edition": PDF_0415, "injury_index": IDX_URL},
        "counts": {"checks": len(checks), "match": matched, "differ": len(checks) - matched},
        "checks": checks,
    }
    with open(os.path.join(OUT, "compare.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)

    from collections import Counter
    c = Counter((x["section"], x["match"]) for x in checks)
    print("checks: %d  match: %d  differ: %d" % (len(checks), matched, len(checks) - matched))
    for sec in sorted({x["section"] for x in checks}):
        print("  %-44s match %3d  differ %3d" % (sec, c[(sec, True)], c[(sec, False)]))
    print("\n--- rows that differ ---")
    for x in checks:
        if not x["match"]:
            print("%-46s committed=%r live=%r" % (x["item"], x["committed"], x["live"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
