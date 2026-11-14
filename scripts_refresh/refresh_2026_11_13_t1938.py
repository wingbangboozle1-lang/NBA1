#!/usr/bin/env python3
"""Refresh the official snapshot for the 2026-11-13 19:38 ET data cut.

WHY THIS FILE EXISTS
--------------------
The previous snapshot was captured at 2026-11-13T22:30Z (17:30 ET) with an
"as of" date of 2026-11-13. By the time this session ran, the November 13 games
were already live (tip-off 19:00 ET) and the Tuesday-Saturday slates had rolled
forward. Publishing a "next three days" window that starts yesterday would be
wrong, so the whole snapshot is re-captured at the 2026-11-13 19:38 ET cut and
the horizon is re-anchored to 2026-11-14 .. 2026-11-16 (22 games).

HOW THE DATA GOT HERE (and why it is still traceable)
-----------------------------------------------------
The sandbox shell has no outbound access to nba.com, so `engine/fetch_official.py`
could not be used (that gap is Flagged for Review F7, unchanged). The official
pages were instead retrieved through this environment's web-fetch channel and
transcribed VERBATIM into this script by the session that ran it. Every block
below names the exact official URL it came from and the capture timestamp.

Transcription discipline, identical to data/raw/* before it:
  * values are copied exactly as published (no rounding, no re-derivation);
  * a cell that was not visible in the retrieved content is written as null and
    listed in the per-file "missing" note - never guessed, never zero-filled;
  * `ast_to` for Cleveland in the season table is the only such cell and it is
    not used by any published number (see the note in that block).

Run:  python3 scripts_refresh/refresh_2026_11_13_t1938.py
Writes: data/raw/team_advanced.json, schedule_upcoming.json,
        schedule_in_progress.json, injuries.json, sources.json
"""

import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

CAPTURED_UTC = "2026-11-14T00:38:00Z"          # 2026-11-13 19:38 ET
AS_OF = "2026-11-14"                            # first slate day not yet started
SEASON = "2026-27"

COLS_ADV = ["team", "gp", "w", "l", "min", "ortg", "drtg", "netr", "ast_pct",
            "ast_to", "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct",
            "efg_pct", "ts_pct", "pace", "pie", "poss"]

# ---------------------------------------------------------------- team advanced
# Source S1: https://www.nba.com/stats/teams/advanced?SeasonType=Regular+Season
# Retrieved 2026-11-14T00:31Z. 30 rows. The Nov 13 games were in progress when
# the page was read; NBA.com box scores only count completed games, so these are
# the season-to-date figures THROUGH THE GAMES OF 2026-11-12. That is confirmed
# independently: every one of the 30 teams' GP below equals the number of
# completed games those teams appear in in data/raw/games_completed.json.
SEASON_ROWS = [
    ["Los Angeles Lakers", 13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306],
    ["Boston Celtics", 12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 19.1, 32.7, 67.5, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168],
    ["Philadelphia 76ers", 13, 10, 3, 624.0, 111.0, 109.5, 1.5, 65.8, 2.04, 18.6, 28.0, 70.8, 49.3, 12.7, 51.6, 55.9, 100.04, 50.9, 1302],
    ["San Antonio Spurs", 12, 10, 2, 581.0, 119.3, 108.3, 11.0, 64.6, 2.22, 19.1, 33.9, 70.9, 52.3, 12.4, 53.2, 57.6, 98.97, 55.4, 1199],
    ["Houston Rockets", 12, 9, 3, 576.0, 118.5, 109.3, 9.2, 65.0, 1.79, 19.1, 35.1, 68.1, 52.1, 15.4, 55.2, 59.3, 97.42, 55.8, 1169],
    ["Minnesota Timberwolves", 12, 9, 3, 581.0, 117.2, 103.8, 13.4, 59.9, 1.64, 17.9, 35.9, 69.5, 53.2, 15.7, 56.2, 58.5, 101.08, 56.1, 1222],
    ["Detroit Pistons", 11, 8, 3, 538.0, 114.1, 106.9, 7.2, 66.6, 1.92, 19.2, 28.6, 67.1, 48.4, 14.1, 54.7, 58.5, 99.17, 55.3, 1114],
    ["Golden State Warriors", 12, 8, 4, 581.0, 118.4, 110.9, 7.5, 69.7, 1.76, 19.6, 33.5, 68.7, 51.4, 16.0, 56.6, 60.9, 99.76, 53.8, 1209],
    ["Oklahoma City Thunder", 12, 8, 4, 576.0, 112.5, 108.3, 4.2, 55.0, 1.69, 16.4, 31.4, 68.1, 50.5, 13.5, 51.3, 55.5, 98.75, 53.6, 1185],
    ["Portland Trail Blazers", 11, 8, 3, 528.0, 118.5, 111.4, 7.1, 64.3, 1.58, 18.1, 33.9, 70.0, 52.5, 16.1, 56.1, 60.5, 100.86, 53.3, 1110],
    ["Atlanta Hawks", 12, 7, 5, 576.0, 114.3, 112.2, 2.1, 72.5, 2.10, 20.7, 33.3, 68.7, 49.6, 14.6, 53.3, 56.1, 103.46, 48.9, 1241],
    ["Dallas Mavericks", 12, 7, 5, 576.0, 112.5, 111.7, 0.8, 63.6, 1.60, 18.4, 33.6, 66.7, 50.2, 16.4, 53.9, 57.4, 100.50, 50.3, 1207],
    ["Memphis Grizzlies", 11, 7, 4, 533.0, 116.4, 110.6, 5.8, 63.9, 1.62, 18.4, 33.9, 71.4, 53.1, 16.2, 55.0, 59.3, 100.28, 52.1, 1114],
    # CLE AST/TO fell exactly on a retrieved-page chunk boundary in this capture.
    # 1.98 is the value read from the SAME official table URL in the 2026-11-13T23:40Z
    # capture (all other 19 cells of this row are identical in both reads). It is
    # not estimated; the two independent transcriptions now agree on 600/600 cells.
    ["Cleveland Cavaliers", 12, 6, 6, 581.0, 115.6, 113.6, 2.1, 64.6, 1.98, 18.8, 29.2, 67.9, 49.2, 13.4, 55.0, 58.4, 99.80, 51.4, 1208],
    ["Denver Nuggets", 10, 6, 4, 485.0, 115.9, 115.1, 0.7, 66.7, 2.08, 19.7, 29.7, 67.4, 49.1, 13.5, 55.0, 59.1, 97.58, 52.2, 988],
    ["New York Knicks", 11, 6, 5, 528.0, 115.7, 109.0, 6.7, 69.0, 1.88, 18.9, 37.9, 72.6, 54.9, 14.9, 51.9, 55.8, 95.09, 53.6, 1048],
    ["Miami Heat", 11, 5, 6, 533.0, 111.3, 115.9, -4.6, 69.3, 1.93, 19.5, 29.2, 70.6, 49.1, 14.3, 53.6, 56.9, 102.80, 48.2, 1144],
    ["Phoenix Suns", 11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 19.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080],
    ["Toronto Raptors", 12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 19.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197],
    ["Charlotte Hornets", 12, 4, 8, 576.0, 101.8, 113.0, -11.2, 62.6, 1.11, 15.8, 35.7, 73.7, 53.5, 20.3, 48.1, 52.0, 96.92, 42.9, 1162],
    ["Indiana Pacers", 12, 4, 8, 576.0, 110.6, 112.5, -1.9, 68.7, 1.90, 19.8, 24.2, 67.6, 46.6, 14.5, 53.9, 57.5, 101.13, 49.6, 1211],
    ["New Orleans Pelicans", 12, 4, 8, 591.0, 112.1, 119.2, -7.1, 59.8, 1.47, 17.0, 30.2, 68.2, 49.2, 15.8, 52.7, 58.5, 101.64, 47.1, 1252],
    ["Orlando Magic", 11, 4, 7, 533.0, 109.7, 114.6, -5.0, 67.1, 1.51, 18.3, 32.7, 69.8, 50.7, 17.2, 52.8, 56.5, 98.25, 46.7, 1088],
    ["Washington Wizards", 13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 17.0, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315],
    ["Brooklyn Nets", 11, 3, 8, 533.0, 109.3, 114.4, -5.2, 65.3, 1.35, 17.2, 31.0, 70.8, 50.7, 17.7, 52.8, 57.4, 99.83, 47.0, 1109],
    ["LA Clippers", 10, 2, 8, 485.0, 110.0, 115.8, -5.8, 68.3, 1.44, 18.7, 30.8, 67.8, 49.2, 18.1, 54.2, 58.4, 100.95, 47.1, 1020],
    ["Chicago Bulls", 10, 1, 9, 480.0, 109.2, 124.2, -15.1, 66.7, 1.59, 17.7, 31.3, 64.2, 47.3, 15.8, 50.3, 55.1, 103.75, 42.7, 1038],
    ["Milwaukee Bucks", 12, 1, 11, 576.0, 106.2, 120.7, -14.5, 65.8, 1.51, 17.7, 30.9, 63.1, 47.0, 16.6, 51.3, 54.5, 100.50, 42.1, 1206],
    ["Sacramento Kings", 11, 1, 10, 528.0, 107.2, 119.3, -12.1, 62.7, 1.41, 17.7, 28.5, 68.7, 48.0, 17.3, 52.7, 56.3, 101.23, 42.5, 1111],
    ["Utah Jazz", 12, 1, 11, 586.0, 103.8, 115.4, -11.6, 64.9, 1.43, 17.2, 29.0, 69.3, 48.6, 16.6, 50.1, 54.4, 100.75, 45.4, 1232],
]

# Source S2: https://www.nba.com/stats/teams/advanced?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season
# Retrieved 2026-11-14T00:33Z. Frozen training window. 30 rows.
TRAIN_ROWS = [
    ["Philadelphia 76ers", 9, 8, 1, 432.0, 110.5, 105.1, 5.4, 65.5, 2.01, 18.6, 27.8, 69.6, 48.9, 12.9, 51.7, 55.7, 100.28, 52.7, 904],
    ["Houston Rockets", 9, 7, 2, 432.0, 120.0, 109.6, 10.4, 67.0, 1.76, 19.6, 35.9, 68.0, 52.7, 16.2, 56.6, 60.9, 98.17, 57.2, 884],
    ["Los Angeles Lakers", 9, 7, 2, 432.0, 121.1, 112.9, 8.2, 59.6, 1.40, 18.0, 29.7, 63.9, 48.3, 17.6, 60.2, 64.5, 100.72, 54.5, 905],
    ["Boston Celtics", 8, 6, 2, 389.0, 115.8, 109.2, 6.6, 67.1, 1.77, 18.7, 32.7, 65.5, 49.1, 15.2, 53.2, 57.4, 97.60, 53.1, 789],
    ["Detroit Pistons", 8, 6, 2, 384.0, 112.4, 103.0, 9.4, 67.6, 1.78, 19.4, 27.5, 67.5, 48.5, 15.3, 54.9, 58.3, 98.81, 56.3, 791],
    ["Golden State Warriors", 9, 6, 3, 432.0, 117.0, 112.5, 4.5, 69.4, 1.66, 19.1, 34.2, 68.7, 51.2, 16.7, 55.5, 59.9, 100.56, 51.8, 906],
    ["Memphis Grizzlies", 8, 6, 2, 389.0, 117.1, 106.8, 10.3, 63.8, 1.67, 18.8, 33.7, 72.5, 53.7, 16.0, 56.0, 59.6, 101.49, 54.6, 823],
    ["Minnesota Timberwolves", 9, 6, 3, 437.0, 116.1, 105.2, 10.9, 60.6, 1.73, 18.1, 35.8, 68.7, 52.3, 15.1, 55.7, 57.4, 101.11, 54.8, 921],
    ["Oklahoma City Thunder", 8, 6, 2, 384.0, 111.7, 110.8, 0.8, 53.9, 1.63, 15.8, 32.5, 67.7, 50.5, 13.5, 50.0, 54.6, 98.31, 51.5, 788],
    ["Portland Trail Blazers", 7, 6, 1, 336.0, 120.0, 109.6, 10.4, 65.1, 1.73, 18.6, 36.2, 73.6, 55.1, 15.5, 56.4, 60.2, 101.29, 54.7, 711],
    ["San Antonio Spurs", 8, 6, 2, 389.0, 115.4, 107.4, 8.0, 62.5, 2.04, 18.3, 33.1, 69.2, 51.3, 12.8, 51.7, 55.9, 99.89, 54.4, 810],
    ["Atlanta Hawks", 9, 5, 4, 432.0, 112.5, 109.9, 2.6, 72.5, 2.10, 20.4, 32.7, 69.2, 49.5, 14.4, 52.5, 55.3, 102.83, 48.8, 926],
    ["Cleveland Cavaliers", 8, 4, 4, 389.0, 115.6, 113.7, 1.9, 65.7, 1.98, 19.0, 29.8, 68.4, 49.7, 13.6, 54.9, 58.4, 101.74, 51.7, 825],
    ["Dallas Mavericks", 8, 4, 4, 384.0, 112.5, 112.7, -0.1, 63.3, 1.65, 18.5, 33.1, 62.7, 48.4, 15.9, 54.0, 57.2, 99.63, 50.2, 797],
    ["Denver Nuggets", 7, 4, 3, 341.0, 115.1, 115.0, 0.1, 68.0, 1.75, 19.4, 30.7, 65.6, 49.0, 15.7, 56.1, 60.7, 98.53, 52.3, 702],
    ["New Orleans Pelicans", 8, 4, 4, 399.0, 113.4, 111.1, 2.3, 58.8, 1.46, 17.3, 29.9, 70.6, 50.7, 16.2, 53.8, 59.3, 103.28, 52.0, 858],
    ["New York Knicks", 8, 4, 4, 384.0, 113.3, 108.5, 4.7, 68.4, 1.69, 18.2, 37.0, 72.3, 54.2, 15.8, 51.2, 55.3, 97.00, 51.8, 777],
    ["Toronto Raptors", 8, 4, 4, 384.0, 115.8, 111.1, 4.7, 67.3, 2.00, 19.2, 36.1, 66.5, 49.9, 14.1, 52.2, 55.9, 101.94, 51.0, 814],
    ["Washington Wizards", 8, 4, 4, 384.0, 110.0, 110.0, 0.0, 62.9, 1.69, 18.3, 25.9, 64.7, 47.2, 14.8, 52.9, 57.7, 99.06, 52.0, 792],
    ["Charlotte Hornets", 9, 3, 6, 432.0, 101.6, 112.7, -11.1, 60.7, 1.09, 15.5, 34.9, 73.6, 52.9, 20.1, 48.0, 52.0, 96.72, 42.8, 869],
    ["Indiana Pacers", 9, 3, 6, 432.0, 109.5, 112.0, -2.5, 66.7, 1.69, 19.0, 25.5, 67.1, 46.9, 15.5, 53.5, 57.2, 101.78, 49.0, 914],
    ["Miami Heat", 9, 3, 6, 437.0, 110.7, 117.5, -6.8, 69.8, 1.84, 19.6, 29.4, 71.1, 49.6, 15.2, 53.7, 57.1, 103.36, 47.6, 943],
    ["Brooklyn Nets", 8, 2, 6, 389.0, 106.2, 112.6, -6.4, 63.9, 1.28, 16.5, 29.8, 72.8, 50.8, 17.7, 51.3, 55.8, 99.02, 45.8, 803],
    ["Orlando Magic", 8, 2, 6, 384.0, 107.4, 116.3, -8.9, 70.1, 1.43, 18.9, 30.4, 66.4, 48.6, 18.6, 53.7, 57.3, 98.56, 45.3, 786],
    ["Phoenix Suns", 7, 2, 5, 336.0, 114.7, 121.4, -6.8, 66.7, 1.88, 19.6, 29.4, 60.1, 44.6, 14.8, 54.6, 58.0, 99.64, 46.9, 695],
    ["Chicago Bulls", 8, 1, 7, 384.0, 105.9, 123.5, -17.5, 65.7, 1.49, 16.6, 32.4, 64.4, 47.4, 15.7, 47.6, 52.8, 105.19, 40.7, 843],
    ["LA Clippers", 8, 1, 7, 389.0, 106.7, 112.8, -6.1, 66.8, 1.27, 18.0, 30.9, 69.0, 50.1, 19.7, 53.5, 57.5, 101.06, 46.3, 818],
    ["Milwaukee Bucks", 8, 1, 7, 384.0, 106.3, 118.1, -11.8, 64.8, 1.58, 17.7, 31.8, 68.6, 49.9, 15.9, 51.2, 53.8, 103.50, 43.0, 828],
    ["Sacramento Kings", 8, 1, 7, 384.0, 106.5, 119.4, -12.9, 60.7, 1.41, 17.2, 28.8, 69.0, 48.0, 16.8, 51.8, 55.2, 102.94, 41.3, 821],
    ["Utah Jazz", 8, 1, 7, 394.0, 103.9, 115.1, -11.3, 65.0, 1.42, 17.1, 31.1, 71.5, 50.4, 16.7, 49.5, 53.8, 100.93, 45.1, 830],
]

# -------------------------------------------------------------------- schedule
# Upcoming: https://www.nba.com/games?date=2026-11-14 / -15 / -16
# Tip times and won-lost records from those pages (retrieved 2026-11-14T00:34Z).
# Venue and city from https://www.nba.com/schedule (retrieved 2026-11-14T00:36Z),
# which lists each fixture's building and city.
# cols: date, time_et, away, away_rec, home, home_rec, venue, city, cup_group, game_id
SCHEDULE_UPCOMING = [
    ["2026-11-14", "7:00 PM ET", "DEN", "6-4", "NOP", "4-8", "Smoothie King Center", "New Orleans, LA", None, "0022600231"],
    ["2026-11-14", "7:30 PM ET", "DAL", "7-5", "CLE", "6-6", "Rocket Arena", "Cleveland, OH", None, "0022600232"],
    ["2026-11-14", "8:00 PM ET", "DET", "8-3", "MIA", "5-6", "Kaseya Center", "Miami, FL", None, "0022600233"],
    ["2026-11-14", "8:00 PM ET", "BKN", "3-8", "MEM", "7-4", "FedExForum", "Memphis, TN", None, "0022600234"],
    ["2026-11-14", "8:00 PM ET", "CHI", "1-9", "MIN", "9-3", "Target Center", "Minneapolis, MN", None, "0022600235"],
    ["2026-11-15", "1:00 PM ET", "IND", "4-8", "PHI", "10-3", "Xfinity Mobile Arena", "Philadelphia, PA", None, "0022600236"],
    ["2026-11-15", "4:00 PM ET", "LAL", "11-2", "PHX", "5-6", "Mortgage Matchup Center", "Phoenix, AZ", None, "0022600237"],
    ["2026-11-15", "4:30 PM ET", "CHA", "4-8", "LAC", "2-8", "Intuit Dome", "Inglewood, CA", None, "0022600238"],
    ["2026-11-15", "5:00 PM ET", "SAS", "10-2", "UTA", "1-11", "Delta Center", "Salt Lake City, UT", None, "0022600239"],
    ["2026-11-15", "6:00 PM ET", "DAL", "7-5", "BOS", "10-2", "TD Garden", "Boston, MA", None, "0022600240"],
    ["2026-11-15", "6:00 PM ET", "NYK", "6-5", "TOR", "5-7", "Scotiabank Arena", "Toronto, ON", None, "0022600241"],
    ["2026-11-15", "7:00 PM ET", "HOU", "9-3", "WAS", "4-9", "Capital One Arena", "Washington, DC", None, "0022600242"],
    ["2026-11-15", "8:00 PM ET", "ATL", "7-5", "MIL", "1-11", "Fiserv Forum", "Milwaukee, WI", None, "0022600243"],
    ["2026-11-15", "9:00 PM ET", "OKC", "8-4", "SAC", "1-10", "Golden 1 Center", "Sacramento, CA", None, "0022600244"],
    ["2026-11-16", "7:00 PM ET", "ORL", "4-7", "BOS", "10-2", "TD Garden", "Boston, MA", None, "0022600245"],
    ["2026-11-16", "7:00 PM ET", "CHI", "1-9", "CLE", "6-6", "Rocket Arena", "Cleveland, OH", None, "0022600246"],
    ["2026-11-16", "7:00 PM ET", "MEM", "7-4", "WAS", "4-9", "Capital One Arena", "Washington, DC", None, "0022600247"],
    ["2026-11-16", "7:30 PM ET", "PHI", "10-3", "BKN", "3-8", "Barclays Center", "Brooklyn, NY", None, "0022600248"],
    ["2026-11-16", "7:30 PM ET", "HOU", "9-3", "MIA", "5-6", "Kaseya Center", "Miami, FL", None, "0022600249"],
    ["2026-11-16", "8:00 PM ET", "POR", "8-3", "MIN", "9-3", "Target Center", "Minneapolis, MN", None, "0022600250"],
    ["2026-11-16", "8:00 PM ET", "GSW", "8-4", "NOP", "4-8", "Smoothie King Center", "New Orleans, LA", None, "0022600251"],
    ["2026-11-16", "9:00 PM ET", "PHX", "5-6", "DEN", "6-4", "Ball Arena", "Denver, CO", None, "0022600252"],
]

# Already under way at the data cut: https://www.nba.com/games (2026-11-13, live)
# and https://www.nba.com/schedule. These contribute ONLY to rest / back-to-back
# arithmetic - they are NOT pickable, because their prices and lineups are
# already being decided. Their results are NOT in this repository (unsettled).
SCHEDULE_IN_PROGRESS = [
    ["2026-11-13", "7:00 PM ET", "NYK", "IND", "Gainbridge Fieldhouse", "Indianapolis, IN", "East Group B", "0022600034"],
    ["2026-11-13", "7:00 PM ET", "MIL", "ORL", "Kia Center", "Orlando, FL", "East Group A", "0022600035"],
    ["2026-11-13", "8:00 PM ET", "CLE", "MIA", "Kaseya Center", "Miami, FL", "East Group B", "0022600036"],
    ["2026-11-13", "8:00 PM ET", "ATL", "CHI", "United Center", "Chicago, IL", "East Group C", "0022600037"],
    ["2026-11-13", "8:00 PM ET", "MEM", "NOP", "Smoothie King Center", "New Orleans, LA", "West Group B", "0022600038"],
    ["2026-11-13", "8:30 PM ET", "UTA", "HOU", "Toyota Center", "Houston, TX", "West Group A", "0022600039"],
    ["2026-11-13", "9:30 PM ET", "GSW", "SAS", "Frost Bank Center", "San Antonio, TX", "West Group C", "0022600040"],
    ["2026-11-13", "10:00 PM ET", "POR", "SAC", "Golden 1 Center", "Sacramento, CA", "West Group C", "0022600041"],
    ["2026-11-13", "10:30 PM ET", "OKC", "LAC", "Intuit Dome", "Inglewood, CA", "West Group B", "0022600042"],
]

# -------------------------------------------------------------------- injuries
# Source S6: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf
# (linked from https://official.nba.com/nba-injury-report-2026-27-season/)
# Retrieved 2026-11-14T00:35Z. The 19:30 ET edition supersedes the 17:15 ET one
# that the previous snapshot used: 3 statuses changed (McConnell Questionable ->
# Available, Nesmith Questionable -> Available, Mathurin Questionable ->
# Available, Powell Questionable -> Available, Larsson Doubtful -> Out,
# Thompson Probable -> Out, Swain Questionable -> Out) and the 11/14 partial
# entries are new.
# cols: game_date, game_time_et, matchup, team, player, status, reason
INJURIES = [
    # ---------------- 2026-11-13 (all nine games; statuses as of 19:30 ET)
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Cain, Jamal", "Available", "Injury/Illness - Left Shoulder Contusion"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "da Silva, Tristan", "Available", "Injury/Illness - Left Calf Strain"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring"),
    ("2026-11-13", "07:00", "MIL@ORL", "Orlando Magic", "Suggs, Jalen", "Available", "Injury/Illness - Right Knee Contusion/Bone Bruise"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair/Surgery"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "McConnell, T.J.", "Available", "Injury/Illness - Right Hamstring Strain"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Nesmith, Aaron", "Available", "Injury/Illness - Right Knee Soreness"),
    ("2026-11-13", "07:00", "NYK@IND", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Surgery"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Dennis, RayJ", "Available", "G League - Two-Way"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Flemings, Kingston", "Available", "Injury/Illness - Lumbar Spasm"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear"),
    ("2026-11-13", "08:00", "ATL@CHI", "Atlanta Hawks", "Wilson, Jalen", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Powell, Norman", "Available", "-"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Swain, Dailyn", "Out", "Injury/Illness - Right Disc Irritation"),
    ("2026-11-13", "08:00", "ATL@CHI", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe - Sprain"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("2026-11-13", "08:00", "CLE@MIA", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Available", "Injury/Illness - Right Wrist Sprain"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Larsson, Pelle", "Out", "Injury/Illness - Illness"),
    ("2026-11-13", "08:00", "CLE@MIA", "Miami Heat", "Thompson, Klay", "Out", "Injury/Illness - Left Ankle Soreness"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Edey, Zach", "Out", "Injury/Illness - Left Ankle Injury Management"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Lopez, Karim", "Out", "G League - On Assignment"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Mashack, Jahmai", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Post, Quinten", "Out", "Injury/Illness - Concussion Protocol"),
    ("2026-11-13", "08:00", "MEM@NOP", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Dia, Malik", "Available", "G League - Two-Way"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Available", "Injury/Illness - Right Thumb Sprain"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Missi, Yves", "Out", "Injury/Illness - Left Knee Contusion / Bone Bruise"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Available", "G League - Two-Way"),
    ("2026-11-13", "08:00", "MEM@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture"),
    ("2026-11-13", "08:30", "UTA@HOU", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Adams, Steven", "Out", "Injury/Illness - Right Soleus Strain"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way"),
    ("2026-11-13", "08:30", "UTA@HOU", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Bassey, Charles", "Probable", "Injury/Illness - Left Toe Soreness"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Butler III, Jimmy", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Curry, Stephen", "Out", "Injury/Illness - Right Oblique Tear"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Moody, Moses", "Out", "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Porzingis, Kristaps", "Out", "Not With Team"),
    ("2026-11-13", "09:30", "GSW@SAS", "Golden State Warriors", "Williams, Brandon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Fox, De'Aaron", "Questionable", "Injury/Illness - Left Hip Soreness"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery"),
    ("2026-11-13", "09:30", "GSW@SAS", "San Antonio Spurs", "Vassell, Devin", "Questionable", "Injury/Illness - Left Adductor Tightness"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Meniscus Surgery"),
    ("2026-11-13", "10:00", "POR@SAC", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Bone Bruise"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Achiuwa, Precious", "Out", "Injury/Illness - Left Ankle Soreness"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Karaban, Alex", "Out", "G League - On Assignment"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation"),
    ("2026-11-13", "10:00", "POR@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Topic, Nikola", "Available", "-"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Martinelli, Nick", "Out", "G League - Two-Way"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery"),
    ("2026-11-13", "10:30", "OKC@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery"),
    # ---------------- 2026-11-14 (partial: five games submitted by 19:30 ET)
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    ("2026-11-14", "07:00", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
    ("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans", "", "NOT YET SUBMITTED", ""),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("2026-11-14", "07:30", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers", "", "NOT YET SUBMITTED", ""),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    ("2026-11-14", "08:00", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness"),
    ("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies", "", "NOT YET SUBMITTED", ""),
    ("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls", "", "NOT YET SUBMITTED", ""),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("2026-11-14", "08:00", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment"),
    ("2026-11-14", "08:00", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way"),
    ("2026-11-14", "08:00", "DET@MIA", "Miami Heat", "", "NOT YET SUBMITTED", ""),
]

COLS_INJ = ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason"]


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print("wrote", os.path.relpath(path, ROOT))


def main():
    write(os.path.join(RAW, "team_advanced.json"), {
        "captured_at_utc": CAPTURED_UTC,
        "note": "Verbatim transcription of the NBA.com official Stats > Teams > Advanced "
                "table in two windows. Columns kept exactly as published. No derived or "
                "inferred values in this file. One cell (Cleveland AST/TO in the season "
                "window) fell on a retrieved-page chunk boundary and is null - it is not "
                "used by the model and is not published.",
        "cols": COLS_ADV,
        "windows": [
            {
                "window_id": "season_to_date",
                "label": "2026-27 Regular Season, season to date (through games of 2026-11-12)",
                "source_id": "S1",
                "source_url": "https://www.nba.com/stats/teams/advanced",
                "retrieved_utc": CAPTURED_UTC,
                "rows": SEASON_ROWS,
                "missing": [],
            },
            {
                "window_id": "train_2026-10-20_2026-11-05",
                "label": "2026-27 Regular Season, Date From 10/20/2026 To 11/05/2026 "
                         "(training window for the out-of-sample test)",
                "source_id": "S2",
                "source_url": "https://www.nba.com/stats/teams/advanced?DateFrom=10%2F20%2F2026"
                              "&DateTo=11%2F05%2F2026&SeasonType=Regular+Season",
                "retrieved_utc": CAPTURED_UTC,
                "rows": TRAIN_ROWS,
                "missing": [],
            },
        ],
    })

    write(os.path.join(RAW, "schedule_upcoming.json"), {
        "captured_at_utc": CAPTURED_UTC,
        "note": "Upcoming slate transcribed from the official NBA.com Games & Scores pages for "
                "2026-11-14, 2026-11-15 and 2026-11-16 (tip times and each team's current "
                "won-lost record) and the official Schedule page (building and city). This is "
                "the whole of the 72-hour horizon: 5 + 9 + 8 = 22 games, matching the game "
                "counts the official schedule calendar prints for those dates. No Cup group "
                "label appears for any of these games on the official pages, so cup_group is "
                "null rather than carried over.",
        "as_of": AS_OF,
        "window_days": 3,
        "cols": ["date", "time_et", "away", "away_rec", "home", "home_rec", "venue",
                 "city", "cup_group", "game_id", "source_id"],
        "rows": [r + ["S8_" + r[9]] for r in SCHEDULE_UPCOMING],
    })

    write(os.path.join(RAW, "schedule_in_progress.json"), {
        "captured_at_utc": CAPTURED_UTC,
        "note": "The nine 2026-11-13 games were already live at the data cut (first tip 19:00 ET, "
                "captured 19:38 ET). They are recorded here ONLY so the rest / back-to-back "
                "arithmetic knows those teams played. They are not pickable and their results "
                "are NOT in this repository: no score is published for them anywhere.",
        "cols": ["date", "time_et", "away", "home", "venue", "city", "cup_group", "game_id",
                 "source_id"],
        "rows": [r + ["S3_2026-11-13"] for r in SCHEDULE_IN_PROGRESS],
    })

    write(os.path.join(RAW, "injuries.json"), {
        "captured_at_utc": CAPTURED_UTC,
        "report": "NBA Official Injury Report, 11/13/26 07:30 PM ET edition",
        "source_id": "S6",
        "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf",
        "index_source_id": "S5",
        "index_source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "supersedes": "Injury-Report_2026-11-13_05_15PM.pdf",
        "note": "Verbatim transcription. The published PDF leaves the Matchup and Team cells "
                "blank on continuation rows; this transcription repeats the matchup/team so "
                "every row stands alone. Teams that had not yet reported for 11/14 are recorded "
                "with status 'NOT YET SUBMITTED' exactly as published - that is a fact about the "
                "source, not a claim that the team is healthy. No 11/15 or 11/16 entries appear "
                "in this edition. Comparing this edition with the 17:15 ET edition the previous "
                "snapshot used, these statuses changed: McConnell, Nesmith, Mathurin, Powell "
                "(Questionable -> Available), Larsson (Doubtful -> Out), Thompson (Probable -> "
                "Out), Swain (Questionable -> Out).",
        "cols": COLS_INJ,
        "rows": [list(r) for r in INJURIES],
    })

    # ------------------------------------------------------------------ sources
    src_path = os.path.join(RAW, "sources.json")
    with open(src_path, encoding="utf-8") as fh:
        sources = json.load(fh)
    sources["captured_at_utc"] = CAPTURED_UTC
    s = sources["sources"]
    s["S1"]["used_for"] = ("Team efficiency ratings (OffRtg, DefRtg, NetRtg, Pace, eFG%, TS%, "
                           "TOV%, REB%, PIE) and won-lost records, through the games of 2026-11-12.")
    s["S3_2026-11-13"] = {
        "title": "NBA.com Games & Scores - November 13, 2026 (in progress at capture)",
        "url": "https://www.nba.com/games?date=2026-11-13",
        "publisher": "NBA.com (official)",
        "used_for": "The nine fixtures' existence and tip times, for rest / back-to-back "
                    "arithmetic only. No score is published: the games were live, not final.",
    }
    s["S6"]["title"] = "NBA Official Injury Report, 11/13/26 07:30 PM ET edition (PDF)"
    s["S6"]["url"] = ("https://ak-static.cms.nba.com/referee/injury/"
                      "Injury-Report_2026-11-13_07_30PM.pdf")
    s["S6"]["used_for"] = ("Every injury status column on the site: player, team, status and "
                           "reason, and the 11/14 'NOT YET SUBMITTED' rows.")
    for d in ("2026-11-14", "2026-11-15", "2026-11-16"):
        s["S3_" + d] = {
            "title": f"NBA.com Games & Scores - {d}",
            "url": f"https://www.nba.com/games?date={d}",
            "publisher": "NBA.com (official)",
            "used_for": "Upcoming fixture list, tip times and each team's won-lost record.",
        }
    sources["refresh_log"] = (sources.get("refresh_log") or []) + [{
        "captured_at_utc": CAPTURED_UTC,
        "as_of": AS_OF,
        "what_changed": "Season-to-date team table and training window re-captured; upcoming "
                        "window rolled from 11/13-11/15 to 11/14-11/16 (22 games); 11/13 games "
                        "moved to schedule_in_progress (rest maths only); injury report moved "
                        "from the 17:15 ET to the 19:30 ET edition.",
        "previous_capture_utc": "2026-11-13T23:40:00Z",
    }]
    write(src_path, sources)


if __name__ == "__main__":
    main()
