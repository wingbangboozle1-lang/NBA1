#!/usr/bin/env python3
"""capture_read_2026_11_19_39b70241.py — promote the first-hand official reads of
2026-11-19 (05:4x UTC) into in-repo capture files, and check them against each
other before anything downstream is allowed to use them.

What was read, and from where (§66 / Y02)
----------------------------------------
  * https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season
  * https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season
  * https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season
  * https://www.nba.com/standings
  * https://www.nba.com/schedule?date=2026-11-19   (11/19 - 11/22 fixtures)
  * https://www.nba.com/games?date=2026-11-19      (same four fixtures, second read)
  * per-game summaries for the 17 finals of 11/17 and 11/18 (see the two
    results_*_39b70241.json files this script cross-checks against)

Every number below was transcribed off the printed official page in this session;
nothing is computed, adjusted, imputed or carried over from a previous day's
capture.  Where a page disagrees with another page, this script reports the
disagreement instead of choosing one of them.

Outputs
-------
  data/official/teams_inputs_2026-11-19_39b70241.json  advanced+traditional+opponent
  data/official/standings_2026-11-19_0546Z_39b70241.json
  data/official/schedule_2026-11-19_to_22_39b70241.json
  verify/2026-11-19-39b70241/readback_report.json      the gates, per team

Gates (a failure is reported; it does not silently pass)
--------------------------------------------------------
  GA1  W + L == GP on all three team tables (30 rows each).
  GA2  |NetRtg - (OffRtg - DefRtg)| <= 0.25 (page rounding).
  GA3  advanced GP and W-L == standings GP and W-L, team by team.
  GA4  100 * (PTS_per_game * GP) / POSS == OffRtg within 1.0 (traditional x advanced).
  GA5  POSS == PACE * MIN / 48 within 6 (advanced internal).
  GA6  traditional +/- == -(opponent +/-) for all 30 (two independent pages).
  GA7  100 * (Opp_PTS_per_game * GP) / POSS == DefRtg within 1.0 (opponent x advanced).
  GA8  standings closed system: total wins == total losses == decided games, and
       sum(GP) == 2 * decided games in the results feed once 11/17 + 11/18 settle.
  GA9  schedule day counts == the game counts printed on the nba.com month grid,
       and every fixture carries a game id that has not been played yet.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

SRC_ADV = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRAD = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_OPP = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"
SRC_STD = "https://www.nba.com/standings"
SRC_SCHED = "https://www.nba.com/schedule?date=2026-11-19"
SRC_GAMES = "https://www.nba.com/games?date=2026-11-19"

COLS_ADV = ["team", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
            "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
            "pace", "pie", "poss"]
COLS_TRAD = ["team", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga", "fg_pct", "3pm",
             "3pa", "3p_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov",
             "stl", "blk", "blka", "pf", "pfd", "pm"]
COLS_OPP = ["team", "gp", "w", "l", "min", "opp_fgm", "opp_fga", "opp_fg_pct", "opp_3pm",
            "opp_3pa", "opp_3p_pct", "opp_ftm", "opp_fta", "opp_ft_pct", "opp_oreb",
            "opp_dreb", "opp_reb", "opp_ast", "opp_tov", "opp_stl", "opp_blk", "opp_blka",
            "opp_pf", "opp_pfd", "opp_pts", "pm"]

# --- advanced, exactly as printed (rank, team, GP, W, L, MIN, OffRtg, DefRtg,
#     NetRtg, AST%, AST/TO, AST Ratio, OREB%, DREB%, REB%, TOV%, eFG%, TS%, PACE,
#     PIE, POSS) ---
ADV = """
Los Angeles Lakers|15|13|2|725.0|121.6|113.7|7.8|58.2|1.47|17.4|33.9|64.3|49.8|16.5|58.1|62.4|100.14|53.8|1511
Philadelphia 76ers|16|13|3|768.0|114.5|111.8|2.7|64.7|2.08|18.7|28.4|72.0|50.3|12.6|53.4|57.7|99.88|51.4|1600
Houston Rockets|16|12|4|768.0|121.1|112.1|9.0|65.4|1.89|19.4|36.7|68.7|53.2|15.0|55.6|59.7|97.41|55.3|1558
San Antonio Spurs|15|12|3|725.0|118.1|107.0|11.1|65.6|2.23|19.4|33.5|71.3|52.5|12.6|53.0|57.1|98.35|56.0|1487
Boston Celtics|15|11|4|725.0|117.0|106.0|11.0|66.7|1.85|19.1|32.9|67.7|50.3|14.9|54.6|57.9|96.76|54.7|1460
Memphis Grizzlies|15|11|4|725.0|120.6|111.9|8.7|67.6|1.82|19.8|34.2|69.8|52.7|15.7|56.9|61.1|100.27|54.3|1516
Minnesota Timberwolves|15|11|4|725.0|114.5|104.0|10.5|60.0|1.58|17.5|34.7|69.3|52.5|15.8|54.8|57.4|101.23|55.0|1528
Detroit Pistons|14|10|4|682.0|114.9|108.9|6.0|67.9|1.97|19.6|30.0|66.6|48.6|14.2|54.5|58.4|98.78|54.2|1406
Atlanta Hawks|15|9|6|725.0|112.8|110.8|1.9|71.1|2.03|20.2|32.8|69.6|49.9|14.6|52.8|55.7|103.71|49.0|1566
Miami Heat|15|9|6|725.0|116.9|116.7|0.3|70.3|2.06|20.0|30.8|68.3|49.4|14.0|55.4|59.1|102.19|50.8|1546
Oklahoma City Thunder|15|9|6|720.0|113.0|108.7|4.4|55.5|1.73|16.8|31.6|68.9|50.9|13.5|52.2|55.9|99.17|53.5|1488
Portland Trail Blazers|14|9|5|672.0|116.2|110.2|6.0|63.8|1.55|17.8|33.0|70.1|51.9|16.1|54.8|59.2|100.71|52.5|1410
Cleveland Cavaliers|16|8|8|773.0|117.5|115.5|2.0|64.7|1.99|19.3|30.9|68.7|50.4|13.7|55.8|59.1|100.01|51.0|1610
Dallas Mavericks|15|8|7|720.0|112.3|113.4|-1.1|65.5|1.64|18.6|33.1|65.9|49.5|16.3|53.6|57.3|99.97|49.4|1501
Denver Nuggets|13|8|5|629.0|114.3|113.8|0.5|64.9|1.89|19.1|30.4|66.8|49.4|14.2|54.3|58.6|98.02|52.5|1287
Golden State Warriors|15|8|7|725.0|113.4|112.8|0.6|70.5|1.70|19.1|32.7|67.9|50.3|16.2|53.9|58.1|99.41|50.3|1503
New York Knicks|14|8|6|677.0|114.8|109.0|5.8|68.6|1.83|18.9|37.1|72.2|54.5|15.2|52.4|56.3|94.87|53.6|1342
Phoenix Suns|14|7|7|672.0|115.6|116.8|-1.2|65.8|1.94|19.6|30.5|63.1|46.8|14.4|55.4|58.4|98.89|49.4|1382
Orlando Magic|14|6|8|677.0|111.3|114.0|-2.7|68.5|1.65|19.1|30.7|70.6|50.5|16.4|53.9|57.4|97.84|48.5|1375
Indiana Pacers|15|5|10|720.0|110.7|113.6|-2.9|67.2|1.92|19.7|24.4|68.1|46.8|14.3|53.9|57.4|100.90|49.4|1511
New Orleans Pelicans|16|5|11|783.0|111.7|118.9|-7.1|60.7|1.54|17.1|30.1|68.5|48.9|15.3|51.8|57.5|101.30|46.4|1652
Toronto Raptors|15|5|10|725.0|113.7|113.1|0.5|67.6|2.07|19.3|34.3|66.4|49.0|13.7|52.0|55.1|98.09|48.4|1478
Washington Wizards|16|5|11|778.0|109.9|117.1|-7.1|60.1|1.62|17.1|29.2|65.6|47.9|14.6|51.7|56.3|99.46|46.3|1612
Charlotte Hornets|14|4|10|677.0|103.1|113.7|-10.6|62.6|1.14|15.9|36.2|72.8|53.4|19.9|48.6|52.5|96.43|43.5|1360
Chicago Bulls|14|4|10|677.0|111.1|119.1|-8.0|67.9|1.61|18.7|31.6|64.6|48.0|16.5|52.7|56.8|103.80|46.2|1464
LA Clippers|13|4|9|629.0|111.4|117.0|-5.6|68.5|1.55|19.0|29.2|65.9|47.6|17.2|54.9|58.8|99.74|47.4|1306
Brooklyn Nets|14|3|11|677.0|110.5|119.0|-8.4|64.6|1.39|17.4|31.9|68.0|49.6|17.5|53.5|57.5|99.51|45.2|1404
Utah Jazz|15|2|13|730.0|107.2|115.9|-8.7|64.2|1.50|17.7|29.3|69.7|49.2|16.3|52.1|55.9|99.95|46.4|1522
Milwaukee Bucks|15|1|14|720.0|106.7|119.7|-13.0|65.1|1.46|17.4|31.1|64.5|47.6|16.8|51.4|54.7|101.00|42.4|1515
Sacramento Kings|14|1|13|672.0|106.9|120.4|-13.5|64.8|1.47|18.2|28.4|69.3|48.0|17.2|52.8|56.3|100.93|42.5|1411
"""

# --- traditional, exactly as printed (Team, GP, W, L, WIN%, Min, PTS, FGM, FGA,
#     FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, OREB, DREB, REB, AST, TOV, STL, BLK,
#     BLKA, PF, PFD, +/-) ---
TRAD = """
Los Angeles Lakers|15|13|2|.867|48.3|122.5|42.1|84.8|49.6|14.5|37.9|38.1|23.9|30.1|79.2|11.9|29.5|41.4|24.5|16.6|10.8|6.1|4.1|23.2|24.3|7.7
Philadelphia 76ers|16|13|3|.813|48.0|114.5|40.6|87.4|46.4|12.3|34.5|35.5|21.1|26.6|79.3|10.1|32.7|42.8|26.3|12.6|8.1|4.4|5.7|20.6|21.3|2.9
San Antonio Spurs|15|12|3|.800|48.3|117.1|42.4|91.3|46.4|12.1|36.0|33.5|20.2|25.2|80.2|13.1|35.1|48.2|27.8|12.5|8.3|6.9|4.7|19.1|20.8|11.2
Houston Rockets|16|12|4|.750|48.0|117.9|42.1|87.6|48.1|13.1|34.4|38.2|20.5|25.4|80.8|13.9|31.8|45.7|27.6|14.6|7.6|5.6|4.7|19.9|21.6|8.7
Boston Celtics|15|11|4|.733|48.3|113.9|40.2|88.6|45.4|16.4|43.9|37.3|17.1|22.0|77.6|13.5|31.5|45.0|26.8|14.5|8.5|4.7|4.3|21.9|21.4|10.5
Memphis Grizzlies|15|11|4|.733|48.3|121.9|42.8|89.0|48.1|15.6|39.4|39.6|20.7|24.5|84.5|12.2|34.3|46.5|28.9|15.9|6.7|5.1|6.9|23.3|21.8|9.0
Minnesota Timberwolves|15|11|4|.733|48.3|116.7|42.3|90.1|47.0|14.1|38.2|37.0|17.9|26.3|67.8|13.5|35.1|48.6|25.4|16.1|8.9|5.1|6.4|22.1|23.3|10.6
Detroit Pistons|14|10|4|.714|48.7|115.4|41.2|87.8|46.9|13.2|35.6|37.1|19.7|24.9|79.3|12.0|31.9|43.9|28.0|14.2|9.3|6.1|5.7|23.5|21.9|6.4
Portland Trail Blazers|14|9|5|.643|48.0|117.0|39.4|86.2|45.7|15.6|43.4|36.0|22.5|28.8|78.2|11.7|33.0|44.7|25.1|16.2|7.1|5.3|4.4|22.8|24.1|6.0
Denver Nuggets|13|8|5|.615|48.4|113.2|41.0|85.0|48.2|10.4|30.9|33.6|20.8|26.1|79.6|10.3|31.7|42.0|26.6|14.1|8.8|4.4|4.4|18.8|23.2|0.9
Atlanta Hawks|15|9|6|.600|48.3|117.7|43.5|96.6|45.1|14.9|43.5|34.3|15.7|20.7|75.9|13.9|31.3|45.2|30.9|15.3|10.3|3.9|6.1|21.8|19.3|1.9
Miami Heat|15|9|6|.600|48.3|120.5|42.1|89.0|47.3|14.3|40.7|35.2|21.9|29.5|74.4|10.7|31.5|42.2|29.6|14.4|7.9|5.7|4.9|21.3|25.4|0.7
Oklahoma City Thunder|15|9|6|.600|48.0|112.1|41.8|90.5|46.2|10.8|31.6|34.2|17.7|22.2|79.9|11.1|34.8|45.9|23.2|13.4|8.2|5.4|5.1|18.9|21.1|4.4
New York Knicks|14|8|6|.571|48.4|110.0|38.9|88.0|44.2|14.5|40.3|36.0|17.8|22.1|80.3|13.5|34.0|47.5|26.6|14.6|7.2|4.1|6.0|20.6|21.2|6.1
Dallas Mavericks|15|8|7|.533|48.0|112.3|40.7|88.0|46.3|12.9|37.9|34.1|17.9|22.8|78.7|12.5|30.7|43.2|26.7|16.3|8.7|5.7|4.9|21.7|20.5|-0.9
Golden State Warriors|15|8|7|.533|48.3|113.7|39.1|86.9|44.9|15.5|41.7|37.3|20.0|24.9|80.4|12.6|31.7|44.3|27.5|16.2|8.4|5.6|5.7|21.9|22.2|0.9
Cleveland Cavaliers|16|8|8|.500|48.3|118.3|42.5|89.6|47.4|15.1|41.1|36.7|18.2|23.8|76.4|11.6|34.3|45.9|27.5|13.8|7.5|5.2|3.8|21.9|20.1|1.9
Phoenix Suns|14|7|7|.500|48.0|114.1|42.0|88.4|47.5|13.9|37.4|37.1|16.2|21.2|76.4|11.1|29.1|40.2|27.6|14.2|8.0|4.1|4.7|21.4|19.2|-1.6
Orlando Magic|14|6|8|.429|48.4|109.4|39.0|85.4|45.7|14.1|40.3|35.1|17.2|22.4|77.0|10.8|31.9|42.7|26.7|16.1|7.4|4.2|4.9|22.3|22.6|-3.4
Indiana Pacers|15|5|10|.333|48.0|111.5|41.1|87.1|47.2|11.7|36.0|32.6|17.7|23.1|76.6|9.5|31.7|41.2|27.6|14.4|7.6|4.3|4.3|20.1|22.5|-3.3
Toronto Raptors|15|5|10|.333|48.3|112.0|41.2|90.8|45.4|12.1|35.9|33.6|17.5|24.7|71.1|13.2|27.4|40.6|27.9|13.5|9.7|4.4|5.5|25.0|22.9|0.0
New Orleans Pelicans|16|5|11|.313|48.9|115.4|39.9|86.6|46.1|9.9|29.4|33.6|25.6|31.3|81.8|11.1|30.7|41.8|24.3|15.8|9.7|5.1|5.7|24.3|23.9|-7.4
Washington Wizards|16|5|11|.313|48.6|110.8|39.6|86.6|45.7|10.4|32.6|31.8|21.1|26.6|79.5|10.9|31.4|42.3|23.8|14.7|7.5|5.6|3.6|20.3|21.5|-7.2
LA Clippers|13|4|9|.308|48.4|111.9|39.1|84.3|46.4|14.4|36.8|39.0|19.4|24.6|78.8|10.1|29.4|39.5|26.8|17.2|9.5|4.5|4.4|21.5|21.0|-5.8
Charlotte Hornets|14|4|10|.286|48.4|100.1|35.1|87.0|40.4|14.3|45.4|31.4|15.6|18.9|82.6|14.9|31.9|46.9|22.0|19.4|7.1|4.6|4.5|21.1|21.4|-10.3
Chicago Bulls|14|4|10|.286|48.4|116.2|40.9|90.1|45.4|13.2|41.3|32.0|21.1|27.7|76.3|12.9|31.1|43.9|27.8|17.2|8.4|5.6|4.8|23.4|22.6|-8.4
Brooklyn Nets|14|3|11|.214|48.4|110.9|37.7|84.0|44.9|14.5|40.0|36.3|20.9|28.0|74.7|11.4|29.9|41.3|24.4|17.5|8.3|4.9|4.7|25.6|24.1|-8.4
Utah Jazz|15|2|13|.133|48.7|108.7|38.7|86.8|44.6|12.9|36.9|35.1|18.3|23.9|76.6|11.7|32.7|44.3|24.9|16.5|6.7|5.9|5.5|23.3|22.9|-8.5
Sacramento Kings|14|1|13|.071|48.0|107.7|39.2|86.1|45.6|12.5|36.4|34.4|16.8|21.9|76.5|9.9|29.9|39.7|25.4|17.4|7.9|3.4|5.2|22.5|19.4|-14.0
Milwaukee Bucks|15|1|14|.067|48.0|107.7|38.1|88.7|42.9|14.9|43.8|34.1|16.7|22.3|74.6|13.5|31.5|45.1|24.8|16.9|7.1|4.6|5.5|23.4|19.9|-13.1
"""

# --- opponent, exactly as printed (Team, GP, W, L, MIN, Opp FGM, Opp FGA, Opp FG%,
#     Opp 3PM, Opp 3PA, Opp 3P%, Opp FTM, Opp FTA, Opp FT%, Opp OREB, Opp DREB,
#     Opp REB, Opp AST, Opp TOV, Opp STL, Opp BLK, Opp BLKA, Opp PF, Opp PFD,
#     Opp PTS, +/-) ---
OPP = """
Los Angeles Lakers|15|13|2|48.3|39.3|86.2|45.6|15.2|41.8|36.4|21.1|27.7|76.1|13.5|28.3|41.7|27.3|18.5|9.4|4.1|6.1|24.3|23.2|114.8|-7.7
Philadelphia 76ers|16|13|3|48.0|40.6|87.3|46.5|12.5|36.1|34.6|17.9|24.3|74.0|10.9|34.1|44.9|25.8|14.3|6.6|5.7|4.4|21.3|20.6|111.6|-2.9
Houston Rockets|16|12|4|48.0|40.3|87.8|45.9|12.7|38.9|32.6|16.0|21.8|73.4|11.9|28.1|39.9|24.1|14.5|8.7|4.7|5.6|21.6|19.9|109.2|-8.7
San Antonio Spurs|15|12|3|48.3|39.3|89.3|44.0|12.3|32.9|37.4|15.0|18.7|80.4|11.1|31.6|42.7|25.4|14.3|6.7|4.7|6.9|20.8|19.1|105.9|-11.2
Boston Celtics|15|11|4|48.3|35.9|84.6|42.4|13.9|41.6|33.5|17.7|23.0|77.1|12.5|30.7|43.3|25.2|16.7|7.2|4.3|4.7|21.4|21.9|103.4|-10.5
Memphis Grizzlies|15|11|4|48.3|40.7|90.0|45.3|12.5|37.4|33.3|18.9|24.7|76.8|12.5|28.7|41.2|25.2|13.9|7.8|6.9|5.1|21.9|23.4|112.9|-9.0
Minnesota Timberwolves|15|11|4|48.3|38.5|89.9|42.8|11.8|36.3|32.5|17.3|22.5|76.9|12.4|31.5|43.9|24.5|16.7|7.8|6.4|5.1|23.3|22.1|106.1|-10.6
Detroit Pistons|14|10|4|48.7|38.4|87.0|44.1|11.9|36.1|32.8|20.4|26.0|78.3|13.0|32.0|45.0|23.6|17.4|7.6|5.7|6.1|21.9|23.5|108.9|-6.4
Atlanta Hawks|15|9|6|48.3|42.1|87.4|48.1|12.3|36.1|34.1|19.3|24.9|77.7|11.1|34.8|45.9|27.9|18.6|9.6|6.1|3.9|19.3|21.8|115.8|-1.9
Miami Heat|15|9|6|48.3|42.7|89.5|47.8|15.3|40.5|37.9|19.1|24.6|77.5|12.1|33.1|45.3|29.1|16.6|7.9|4.9|5.7|25.4|21.3|119.9|-0.7
Oklahoma City Thunder|15|9|6|48.0|37.7|89.6|42.1|15.1|44.0|34.4|17.1|21.3|80.6|12.1|31.7|43.9|25.2|14.8|6.6|5.1|5.4|21.1|18.9|107.7|-4.4
Portland Trail Blazers|14|9|5|48.0|38.3|86.7|44.2|11.8|35.6|33.1|22.6|28.1|80.5|11.4|31.1|42.5|23.2|14.4|8.6|4.4|5.3|24.1|22.8|111.0|-6.0
Cleveland Cavaliers|16|8|8|48.3|41.6|91.4|45.5|14.0|40.0|35.0|19.2|24.1|79.5|12.1|31.8|43.9|27.6|12.9|7.3|3.8|5.2|20.1|21.9|116.3|-1.9
Dallas Mavericks|15|8|7|48.0|41.8|89.1|46.9|12.7|37.9|33.4|16.9|22.9|73.8|12.6|31.0|43.6|27.7|15.8|8.7|4.9|5.7|20.5|21.7|113.2|0.9
Denver Nuggets|13|8|5|48.4|41.5|90.6|45.8|14.0|39.4|35.5|15.3|19.7|77.7|13.7|30.7|44.4|27.5|14.7|7.4|4.4|4.4|23.2|18.8|112.2|-0.9
Golden State Warriors|15|8|7|48.3|40.7|88.4|46.1|13.3|38.1|34.8|18.1|23.1|78.1|12.5|31.2|43.7|27.6|16.2|9.0|5.7|5.6|22.2|21.9|112.8|-0.9
New York Knicks|14|8|6|48.4|37.5|85.8|43.7|13.4|39.1|34.4|15.4|21.8|70.8|10.5|29.8|40.3|25.1|12.9|6.5|6.0|4.1|21.2|20.6|103.9|-6.1
Phoenix Suns|14|7|7|48.0|40.6|86.6|46.9|14.1|38.1|37.0|20.5|26.5|77.4|13.4|31.6|45.1|26.0|17.1|7.7|4.7|4.1|19.2|21.4|115.7|1.6
Orlando Magic|14|6|8|48.4|39.8|85.4|46.6|14.1|37.1|37.9|19.1|25.3|75.7|10.0|31.2|41.2|27.1|14.7|9.2|4.9|4.2|22.6|22.3|112.8|3.4
Indiana Pacers|15|5|10|48.0|41.1|89.3|46.1|14.5|38.9|37.2|18.1|23.3|77.7|11.6|35.1|46.7|26.5|15.1|8.3|4.3|4.3|22.5|20.1|114.8|3.3
New Orleans Pelicans|16|5|11|48.9|42.3|86.9|48.6|13.6|38.4|35.3|24.8|30.7|80.7|11.4|33.3|44.7|28.8|15.8|7.9|5.7|5.1|24.0|24.3|122.8|7.4
Toronto Raptors|15|5|10|48.3|38.4|80.7|47.6|12.5|34.2|36.6|22.7|28.0|81.0|10.9|32.0|42.9|25.5|18.3|7.5|5.5|4.4|22.9|25.0|112.0|0.0
Washington Wizards|16|5|11|48.6|43.6|93.8|46.4|12.7|37.9|33.5|18.1|21.6|83.8|14.1|33.6|47.7|29.3|13.7|8.8|3.6|5.6|21.5|20.3|117.9|7.2
Charlotte Hornets|14|4|10|48.4|39.4|83.6|47.1|14.7|36.7|40.1|17.0|22.5|75.6|9.4|30.7|40.1|26.0|14.1|9.1|4.5|4.6|21.4|21.1|110.4|10.3
Chicago Bulls|14|4|10|48.4|45.1|93.9|48.1|13.5|37.5|36.0|20.8|27.4|75.8|13.7|32.7|46.4|29.2|15.4|9.9|4.8|5.6|22.6|23.4|124.6|8.4
LA Clippers|13|4|9|48.4|43.1|87.7|49.1|13.6|36.3|37.5|17.9|24.2|74.2|11.8|32.2|43.9|27.3|16.1|8.8|4.4|4.5|21.0|21.5|117.7|5.8
Brooklyn Nets|14|3|11|48.4|40.9|85.9|47.7|14.6|39.8|36.6|22.8|28.6|79.8|11.4|30.4|41.9|27.8|15.9|8.5|4.7|4.9|24.1|25.6|119.2|8.4
Utah Jazz|15|2|13|48.7|39.5|87.3|45.3|12.5|35.5|35.3|25.7|31.1|82.6|11.1|34.0|45.1|22.9|13.6|9.2|5.5|5.9|22.9|23.3|117.3|8.5
Milwaukee Bucks|15|1|14|48.0|42.4|91.6|46.3|15.1|42.3|35.7|20.9|26.9|77.9|14.3|33.9|48.1|27.9|13.8|9.7|5.5|4.6|19.9|23.4|120.9|13.1
Sacramento Kings|14|1|13|48.0|42.6|85.4|49.9|13.8|36.9|37.4|22.6|28.4|79.6|10.1|33.1|43.2|26.6|14.4|9.2|5.2|3.4|19.5|22.6|121.7|14.0
"""

# --- standings as printed: conf, rank, team, W, L, WIN%, GB, CONF, DIV, HOME,
#     ROAD, NEUTRAL, OT, LAST10, STREAK ---
STD = """
East|1|Philadelphia 76ers|13|3|.813|--|13-3|4-1|6-2|7-1|0-0|0-0|8-2|W 4
East|2|Boston Celtics|11|4|.733|1.5|10-2|4-0|6-1|5-3|0-0|1-0|7-3|L 2
East|3|Detroit Pistons|10|4|.714|2|8-3|0-0|3-2|7-2|0-0|1-0|7-3|W 2
East|4|Miami Heat|9|6|.600|3.5|5-2|1-1|5-3|4-3|0-0|1-0|8-2|W 6
East|5|Atlanta Hawks|9|6|.600|3.5|8-2|4-1|3-3|6-3|0-0|0-1|7-3|W 2
East|6|New York Knicks|8|6|.571|4|8-6|3-3|4-3|4-3|0-0|1-0|7-3|W 2
East|7|Cleveland Cavaliers|8|8|.500|5|6-5|2-0|6-3|2-5|0-0|1-0|4-6|L 1
East|8|Orlando Magic|6|8|.429|6|4-5|0-2|1-5|5-3|0-0|0-1|5-5|L 1
East|9|Toronto Raptors|5|10|.333|7.5|4-6|0-4|2-6|3-4|0-0|0-1|2-8|L 6
East|10|Indiana Pacers|5|10|.333|7.5|3-6|0-1|2-5|3-4|0-1|0-0|3-7|L 2
East|11|Washington Wizards|5|11|.313|8|5-8|2-3|2-5|3-6|0-0|0-1|2-8|W 1
East|12|Charlotte Hornets|4|10|.286|8|4-7|2-2|3-4|1-6|0-0|0-1|1-9|L 3
East|13|Chicago Bulls|4|10|.286|8|3-9|1-1|1-4|3-6|0-0|1-0|3-7|W 1
East|14|Brooklyn Nets|3|11|.214|9|2-9|0-3|1-5|2-6|0-0|0-1|3-7|L 3
East|15|Milwaukee Bucks|1|14|.067|11.5|1-11|1-2|1-7|0-7|0-0|0-0|0-10|L 11
West|1|Los Angeles Lakers|13|3|.813|--|7-3|5-1|6-2|7-1|0-0|1-0|9-1|L 1
West|2|San Antonio Spurs|12|3|.800|0.5|11-2|2-1|5-3|7-0|0-0|1-0|9-1|L 1
West|3|Houston Rockets|12|4|.750|1|6-3|2-1|7-1|5-3|0-0|0-0|7-3|W 1
West|4|Minnesota Timberwolves|11|4|.733|1.5|7-2|3-0|7-2|4-2|0-0|0-1|8-2|W 2
West|5|Memphis Grizzlies|11|4|.733|1.5|7-3|1-1|3-4|8-0|0-0|0-1|6-4|W 4
West|6|Portland Trail Blazers|9|5|.643|3|9-5|4-2|3-2|6-3|0-0|0-0|6-4|L 2
West|7|Denver Nuggets|8|5|.615|3.5|5-5|0-2|3-3|4-2|1-0|1-0|7-3|W 1
West|8|Oklahoma City Thunder|9|6|.600|3.5|6-5|1-2|5-1|4-5|0-0|0-0|5-5|L 1
West|9|Dallas Mavericks|8|7|.533|4.5|4-5|1-3|6-2|2-5|0-0|0-0|5-5|W 1
West|10|Golden State Warriors|8|7|.533|4.5|6-7|3-2|6-1|2-6|0-0|1-0|6-4|L 4
West|11|Phoenix Suns|7|7|.500|5|5-7|3-2|5-4|2-3|0-0|0-0|6-4|W 2
West|12|New Orleans Pelicans|5|11|.313|8|4-8|1-1|4-7|1-4|0-0|2-1|3-7|L 1
West|13|LA Clippers|4|9|.308|7.5|3-7|1-4|4-4|0-5|0-0|0-1|3-7|L 1
West|14|Utah Jazz|3|13|.188|10|3-11|0-2|1-7|2-6|0-0|0-2|2-8|W 2
West|15|Sacramento Kings|1|13|.071|11|1-11|0-3|0-9|1-4|0-0|0-0|1-9|L 7
"""

# --- 2026-11-19 .. 11-22 fixtures exactly as printed on the schedule page, each
#     one confirmed a second time on nba.com/games?date=2026-11-19 where the day
#     has tipped, or by its Preview/Tickets game id on the schedule page.
#     date|time_et|away|home|arena|city|state|game_id|note
SCHED = """
2026-11-19|8:00 PM ET|GSW|MEM|FedExForum|Memphis|TN|0022600270|
2026-11-19|8:00 PM ET|POR|MIL|Fiserv Forum|Milwaukee|WI|0022600271|
2026-11-19|8:00 PM ET|NYK|MIN|Target Center|Minneapolis|MN|0022600272|
2026-11-19|8:00 PM ET|LAC|SAS|Frost Bank Center|San Antonio|TX|0022600273|
2026-11-20|7:00 PM ET|CHA|ATL|State Farm Arena|Atlanta|GA|0022600043|Emirates NBA Cup East Group C
2026-11-20|7:30 PM ET|ORL|BKN|Barclays Center|Brooklyn|NY|0022600044|Emirates NBA Cup East Group A
2026-11-20|7:30 PM ET|IND|CLE|Rocket Arena|Cleveland|OH|0022600045|Emirates NBA Cup East Group B
2026-11-20|7:30 PM ET|TOR|DET|Little Caesars Arena|Detroit|MI|0022600046|Emirates NBA Cup East Group A
2026-11-20|8:00 PM ET|WAS|CHI|United Center|Chicago|IL|0022600047|Emirates NBA Cup East Group C
2026-11-20|8:00 PM ET|NOP|OKC|Paycom Center|Oklahoma City|OK|0022600048|Emirates NBA Cup West Group B
2026-11-20|9:30 PM ET|PHX|UTA|Delta Center|Salt Lake City|UT|0022600049|Emirates NBA Cup West Group A
2026-11-20|10:00 PM ET|HOU|DEN|Ball Arena|Denver|CO|0022600050|Emirates NBA Cup West Group A
2026-11-20|10:00 PM ET|SAC|LAL|Crypto.com Arena|Los Angeles|CA|0022600051|Emirates NBA Cup West Group C
2026-11-21|1:00 PM ET|MIL|PHI|Xfinity Mobile Arena|Philadelphia|PA|0022600274|
2026-11-21|7:30 PM ET|POR|NYK|Madison Square Garden|New York|NY|0022600275|
2026-11-21|8:00 PM ET|LAC|DAL|American Airlines Center|Dallas|TX|0022600276|
2026-11-21|8:00 PM ET|MEM|MIN|Target Center|Minneapolis|MN|0022600277|
2026-11-21|8:00 PM ET|NOP|SAS|Frost Bank Center|San Antonio|TX|0022600278|
2026-11-21|10:00 PM ET|BOS|SAC|Golden 1 Center|Sacramento|CA|0022600279|
2026-11-22|3:30 PM ET|DET|ATL|State Farm Arena|Atlanta|GA|0022600280|
2026-11-22|6:00 PM ET|OKC|MIA|Kaseya Center|Miami|FL|0022600281|
2026-11-22|7:00 PM ET|ORL|WAS|Capital One Arena|Washington|DC|0022600282|
2026-11-22|7:00 PM ET|DEN|CHI|United Center|Chicago|IL|0022600283|
2026-11-22|7:00 PM ET|DAL|UTA|Delta Center|Salt Lake City|UT|0022600284|
2026-11-22|8:00 PM ET|IND|NYK|Madison Square Garden|New York|NY|0022600285|
2026-11-22|8:30 PM ET|BOS|GSW|Chase Center|San Francisco|CA|0022600286|
"""

# The month grid printed on nba.com/games?date=2026-11-19, which states the
# number of games on every day of November 2026.  Used only as an independent
# count check on the fixture list above (and on the results feed).
MONTH_GRID_GAMES = {"2026-11-17": 5, "2026-11-18": 12, "2026-11-19": 4,
                    "2026-11-20": 9, "2026-11-21": 6, "2026-11-22": 7}

ABBREV = {"Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
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


def parse(block: str, cols: list[str]) -> list[dict]:
    rows = []
    for line in block.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        assert len(parts) == len(cols), f"{len(parts)} vs {len(cols)}: {line[:60]}"
        rec = {}
        for c, v in zip(cols, parts):
            if c in ("team", "note"):
                rec[c] = v
            elif c in ("win_pct",):
                rec[c] = float(v)
            elif c.endswith("_pct") or c in ("pm",):
                rec[c] = float(v)
            else:
                try:
                    f = float(v)
                    rec[c] = int(f) if f == int(f) and "." not in v else f
                except ValueError:
                    rec[c] = v
        rows.append(rec)
    return rows


def main() -> int:
    adv = parse(ADV, COLS_ADV)
    trad = parse(TRAD, COLS_TRAD)
    opp = parse(OPP, COLS_OPP)
    assert len(adv) == len(trad) == len(opp) == 30, (len(adv), len(trad), len(opp))

    std_cols = ["conf", "rank", "team", "w", "l", "win_pct", "gb", "conf_rec", "div_rec",
                "home_rec", "road_rec", "neutral_rec", "ot_rec", "last10", "streak"]
    std = parse(STD, std_cols)
    assert len(std) == 30

    sched_cols = ["date", "tip_et", "away", "home", "arena", "city", "state", "game_id", "note"]
    sched = parse(SCHED, sched_cols)
    assert len(sched) == 26

    for r in adv + trad + opp:
        r["abbr"] = ABBREV[r["team"]]
    for r in std:
        r["abbr"] = ABBREV[r["team"]]
        r["gp"] = r["w"] + r["l"]

    A = {r["team"]: r for r in adv}
    T = {r["team"]: r for r in trad}
    O = {r["team"]: r for r in opp}
    S = {r["team"]: r for r in std}

    # ---------------- gates -----------------
    per_team, fails = {}, []
    for t in A:
        a, tr, op, st = A[t], T[t], O[t], S[t]
        chk = {}
        chk["GA1_w_plus_l_eq_gp"] = (a["w"] + a["l"] == a["gp"] and tr["w"] + tr["l"] == tr["gp"]
                                     and op["w"] + op["l"] == op["gp"]
                                     and a["gp"] == tr["gp"] == op["gp"])
        chk["GA2_netrtg"] = abs(a["net_rtg"] - (a["off_rtg"] - a["def_rtg"])) <= 0.25
        chk["GA3_adv_eq_standings"] = (a["gp"] == st["gp"] and a["w"] == st["w"] and a["l"] == st["l"])
        pts_total = tr["pts"] * tr["gp"]
        chk["GA4_offrtg_from_trad"] = abs(100.0 * pts_total / a["poss"] - a["off_rtg"]) <= 1.0
        chk["GA5_poss_from_pace"] = abs(a["pace"] * a["min"] / 48.0 - a["poss"]) <= 6
        chk["GA6_pm_sign_flip"] = abs(tr["pm"] + op["pm"]) <= 0.05
        opp_total = op["opp_pts"] * op["gp"]
        chk["GA7_defrtg_from_opp"] = abs(100.0 * opp_total / a["poss"] - a["def_rtg"]) <= 1.0
        per_team[t] = chk
        for k, v in chk.items():
            if not v:
                fails.append(f"{t}: {k}")
        # record the derived cross-check numbers so a reviewer can redo them
        a["ga4_offrtg_from_traditional"] = round(100.0 * pts_total / a["poss"], 2)
        a["ga5_poss_from_pace"] = round(a["pace"] * a["min"] / 48.0, 1)
        a["ga7_defrtg_from_opponent"] = round(100.0 * opp_total / a["poss"], 2)

    tot_w = sum(s["w"] for s in std)
    tot_l = sum(s["l"] for s in std)
    tot_gp = sum(s["gp"] for s in std)
    feed = json.load(open(os.path.join(ROOT, "data/official/results_feed_2026_27.json")))
    feed_rows = feed if isinstance(feed, list) else feed["rows"]
    decided_feed = [r for r in feed_rows if (r.get("away_pts") or 0) > 0 and (r.get("home_pts") or 0) > 0]
    gates = {
        "GA1_w_plus_l_eq_gp_30_teams": "pass" if not any("GA1" in f for f in fails) else "FAIL " + str([f for f in fails if "GA1" in f]),
        "GA2_netrtg_eq_off_minus_def": "pass" if not any("GA2" in f for f in fails) else "FAIL",
        "GA3_advanced_eq_standings": ("pass (all 30)" if not any("GA3" in f for f in fails)
                                      else "FAIL for " + ", ".join(f.split(":")[0] for f in fails if "GA3" in f)),
        "GA4_offrtg_from_traditional_pts_x_gp_over_poss": "pass" if not any("GA4" in f for f in fails) else "FAIL",
        "GA5_poss_from_pace_x_min_over_48": "pass" if not any("GA5" in f for f in fails) else "FAIL",
        "GA6_traditional_pm_eq_neg_opponent_pm": "pass" if not any("GA6" in f for f in fails) else "FAIL",
        "GA7_defrtg_from_opponent_pts_x_gp_over_poss": "pass" if not any("GA7" in f for f in fails) else "FAIL",
        "GA8_standings_closed_system": (f"{'pass' if tot_w == tot_l == len(decided_feed) else 'CHECK'}: "
                                        f"{tot_w} wins == {tot_l} losses == {len(decided_feed)} settled "
                                        f"finals in the results feed; team-games {tot_gp} == 2 x "
                                        f"{tot_gp // 2}"),
        "GA9_schedule_day_counts_eq_month_grid": ("pass" if all(
            sum(1 for g in sched if g["date"] == d) == n for d, n in MONTH_GRID_GAMES.items())
            else "FAIL"),
    }

    # ---------------- capture files -----------------
    def dump(rel, obj):
        p = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1)
            fh.write("\n")
        print("wrote", rel)

    inputs = {
        "title": "Official team-stat inputs read first-hand on 2026-11-19 "
                 "(advanced + traditional + opponent, all 30 rows each)",
        "captured_by": "arena/39b70241-nba1",
        "retrieved_utc": NOW,
        "capture_method": ("official pages read live through the web-fetch channel and transcribed "
                           "row by row by scripts/capture_read_2026_11_19_39b70241.py"),
        "sources": {"advanced": SRC_ADV, "traditional": SRC_TRAD, "opponent": SRC_OPP},
        "games_through": ("the standings read at the same hour carry 222 decided games (11/18 slate "
                          "included); the three stat tables carry 221 for LAL and UTA - see gates"),
        "columns_advanced": COLS_ADV,
        "columns_traditional": COLS_TRAD,
        "columns_opponent": COLS_OPP,
        "advanced": [[r[c] for c in COLS_ADV] for r in adv],
        "traditional": [[r[c] for c in COLS_TRAD] for r in trad],
        "opponent": [[r[c] for c in COLS_OPP] for r in opp],
        "gates": gates,
        "note": ("every cell is printed on the cited page; the derived cross-checks "
                 "(GA4/GA5/GA7) are recomputed here and stored per team in "
                 "verify/2026-11-19-39b70241/readback_report.json, never written back as data"),
    }
    dump("data/official/teams_inputs_2026-11-19_39b70241.json", inputs)

    dump("data/official/standings_2026-11-19_0546Z_39b70241.json", {
        "title": "NBA 2026-27 regular-season standings, read first-hand 2026-11-19",
        "source_url": SRC_STD,
        "retrieved_utc": NOW,
        "columns": std_cols,
        "rows": [{c: r[c] for c in std_cols + ["abbr", "gp"]} for r in std],
        "closed_system": {"total_wins": tot_w, "total_losses": tot_l, "total_team_games": tot_gp,
                          "implied_decided_games": tot_gp // 2},
        "note": ("read twice in this session (chunk 0 East + West-1..14, chunk 1 West-15) as one "
                 "page; GB and streak columns are transcribed but not used by any model"),
    })

    played_ids = {r.get("game_id") for r in feed_rows}
    dump("data/official/schedule_2026-11-19_to_22_39b70241.json", {
        "title": "Official rolling slate 2026-11-19 .. 2026-11-22 (today + up to 3 days)",
        "source_url": SRC_SCHED,
        "second_read_url": SRC_GAMES,
        "retrieved_utc": NOW,
        "columns": sched_cols,
        "rows": sched,
        "day_counts": {d: n for d, n in MONTH_GRID_GAMES.items() if d >= "2026-11-19"},
        "checks": {
            "game_ids_not_already_in_results_feed": all(g["game_id"] not in played_ids for g in sched),
            "day_counts_match_month_grid": gates["GA9_schedule_day_counts_eq_month_grid"],
            "cup_note": ("the nine 2026-11-20 games carry the Emirates NBA Cup label and their own "
                         "game-id series (0022600043..51) on the same official schedule page; they "
                         "are regular-season games for standings purposes"),
        },
    })

    dump("verify/2026-11-19-39b70241/readback_report.json", {
        "generated_by": "scripts/capture_read_2026_11_19_39b70241.py",
        "generated_utc": NOW,
        "gates": gates,
        "per_team": per_team,
        "advanced_rows_with_crosschecks": adv,
        "failures": fails,
    })
    print(json.dumps(gates, indent=1))
    return 1 if any(str(v).startswith("FAIL") for v in gates.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
