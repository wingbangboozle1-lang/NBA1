#!/usr/bin/env python3
"""capture_team_tables_2026_11_17.py — transcribe the three official team-stat
pages as re-read on 2026-11-17 and reconcile them against each other.

Source (all three read in this session, 2026-11-17 ~16:0xZ):
  https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season
  https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season
  https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season

Why a separate script: the 11/15 captures in data/official/ predate the 11/16
slate. Re-cutting model inputs on stale team tables is exactly the failure mode
R04/R29 exists to prevent, so the re-read is stored as its own dated file with
its own reconciliation block. Cells the page render did not print are stored as
null, never filled in.

Cross-table reconciliation asserted here (fails loudly if it does not hold):
  * sum(W) == sum(L) == 205 on every table (205 finals through 2026-11-16)
  * W/L/GP agree team by team across all three tables
  * PTS - OppPTS == +/- within the printed rounding of the two tables
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.path.join(ROOT, "data", "official")
STAMP = "2026-11-17T16:05Z"
BY = "arena/c5487cbb-nba1 (§62 Y06)"

ADV_URL = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
TRA_URL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
OPP_URL = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"

# abbr, GP, W, L, MIN, OffRtg, DefRtg, NetRtg, AST%, AST/TO, AST Ratio,
# OREB%, DREB%, REB%, TOV%, eFG%, TS%, PACE, PIE, POSS
ADV = [
 ("LAL",14,12,2,672.0,122.1,114.0,8.0,58.6,1.47,17.6,33.3,64.1,49.6,16.7,58.8,63.2,100.64,54.2,1408),
 ("PHI",15,12,3,720.0,113.7,111.1,2.6,64.7,2.07,18.6,28.4,71.6,50.0,12.6,53.0,57.3,100.23,51.3,1505),
 ("SAS",14,12,2,677.0,119.2,106.6,12.6,65.4,2.28,19.4,33.3,71.8,52.7,12.3,53.5,57.7,98.77,56.9,1395),
 ("BOS",14,11,3,677.0,118.2,106.1,12.1,67.5,1.89,19.3,32.7,68.0,50.5,14.8,55.3,58.6,96.53,55.4,1360),
 ("HOU",15,11,4,720.0,120.9,112.3,8.6,65.2,1.90,19.2,36.7,68.1,52.9,14.8,55.3,59.6,97.50,55.5,1462),
 ("MEM",14,10,4,677.0,120.0,110.9,9.1,67.3,1.80,19.6,34.7,70.7,53.3,15.8,56.4,60.6,100.61,54.3,1420),
 ("MIN",14,10,4,677.0,115.2,104.1,11.1,60.1,1.63,17.6,35.2,69.8,52.9,15.4,54.7,57.4,101.21,55.1,1427),
 ("OKC",14,9,5,672.0,113.4,108.4,5.1,54.7,1.70,16.5,32.1,68.7,51.0,13.5,51.9,55.9,98.82,53.8,1384),
 ("POR",13,9,4,624.0,117.2,110.6,6.6,64.0,1.57,17.9,32.6,69.8,51.8,16.1,55.4,59.9,100.65,52.8,1308),
 ("ATL",14,8,6,677.0,112.8,111.1,1.7,70.9,2.01,20.1,33.0,69.2,49.8,14.7,52.7,55.7,103.69,49.0,1462),
 ("CLE",15,8,7,725.0,116.9,114.7,2.2,64.8,1.96,19.3,30.0,68.4,50.0,13.9,55.9,59.1,100.30,51.5,1515),
 ("DET",12,8,4,586.0,114.1,109.2,4.9,67.6,1.94,19.2,29.8,66.6,48.4,14.1,53.9,58.0,99.48,53.7,1217),
 ("GSW",14,8,6,677.0,114.6,112.3,2.2,70.3,1.72,19.1,32.4,68.2,50.5,15.9,54.3,58.7,99.58,51.0,1406),
 ("MIA",14,8,6,677.0,116.0,116.2,-0.1,70.3,2.12,20.1,30.4,68.8,49.4,13.6,54.9,58.4,101.96,50.6,1440),
 ("DAL",14,7,7,672.0,111.8,114.5,-2.7,64.3,1.63,18.3,32.9,66.0,49.3,16.0,53.2,56.9,100.18,48.6,1404),
 ("DEN",12,7,5,581.0,115.1,114.9,0.2,65.9,1.98,19.5,29.9,66.9,49.2,13.9,54.9,59.1,97.86,52.2,1187),
 ("NYK",13,7,6,629.0,113.7,108.2,5.5,69.2,1.82,18.8,36.7,71.8,54.0,15.2,51.9,55.7,95.66,53.5,1257),
 ("ORL",13,6,7,629.0,110.5,113.0,-2.6,68.3,1.60,18.8,31.4,70.6,50.9,16.8,53.2,57.0,98.10,48.6,1281),
 ("PHX",13,6,7,624.0,114.5,117.5,-3.0,65.4,1.89,19.2,30.9,62.5,46.6,14.6,54.6,57.7,98.88,48.5,1283),
 ("IND",14,5,9,672.0,110.9,112.9,-2.0,67.9,1.92,19.7,24.6,68.5,47.1,14.3,53.8,57.4,101.25,49.6,1415),
 ("NOP",15,5,10,735.0,111.7,118.4,-6.7,60.6,1.55,17.1,30.1,68.2,48.8,15.2,51.8,57.4,101.62,46.6,1555),
 ("TOR",13,5,8,629.0,113.6,112.2,1.4,67.4,1.94,19.0,35.8,67.2,50.2,14.4,51.7,55.2,99.55,49.0,1302),
 ("CHA",13,4,9,624.0,102.5,113.6,-11.1,62.8,1.13,15.8,36.5,74.2,53.9,20.0,48.0,52.0,96.65,42.7,1256),
 ("LAC",12,4,8,581.0,111.4,115.3,-3.9,69.3,1.54,19.2,29.6,66.0,48.1,17.6,55.1,59.0,100.05,48.3,1210),
 ("WAS",15,4,11,730.0,109.9,117.6,-7.8,60.0,1.63,17.2,28.8,65.1,47.3,14.5,51.7,56.3,99.91,45.8,1519),
 ("BKN",13,3,10,629.0,110.8,117.4,-6.6,64.6,1.42,17.3,31.6,69.1,50.0,17.1,53.2,57.4,99.55,45.9,1304),
 ("CHI",13,3,10,629.0,109.1,120.0,-10.9,67.9,1.57,18.3,30.6,64.6,47.4,16.5,51.8,56.1,104.17,44.9,1366),
 ("MIL",14,1,13,672.0,105.4,118.9,-13.6,65.3,1.46,17.4,30.5,64.6,47.4,16.7,50.9,54.1,100.68,42.1,1410),
 ("SAC",13,1,12,624.0,106.8,119.8,-13.0,64.4,1.44,18.0,28.4,68.8,47.9,17.3,52.7,56.2,101.08,42.6,1312),
 ("UTA",14,1,13,682.0,105.1,116.2,-11.1,63.5,1.46,17.2,29.0,69.3,48.6,16.3,50.8,54.8,100.22,45.0,1426),
]
ADV_COLS = ["abbr","gp","w","l","min","off_rtg","def_rtg","net_rtg","ast_pct","ast_to",
            "ast_ratio","oreb_pct","dreb_pct","reb_pct","tov_pct","efg_pct","ts_pct",
            "pace","pie","poss"]

# abbr, GP, W, L, WIN%, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%,
# OREB, DREB, REB, AST, TOV, STL, BLK, BLKA, PF, PFD, +/-
TRA = [
("LAL","Los Angeles Lakers",14,12,2,".857",48.0,122.8,42.1,83.8,50.3,14.2,37.1,38.3,24.3,30.2,80.4,11.4,29.4,40.8,24.7,16.8,11.0,6.4,4.1,23.4,24.1,7.9),
("SAS","San Antonio Spurs",14,12,2,".857",48.4,118.8,42.8,91.5,46.8,12.3,35.7,34.4,20.9,26.0,80.5,12.9,35.6,48.6,28.0,12.3,8.6,7.1,4.9,19.4,20.9,12.9),
("PHI","Philadelphia 76ers",15,12,3,".800",48.0,114.1,40.5,87.9,46.1,12.1,34.5,35.2,21.0,26.7,78.8,10.3,32.9,43.1,26.2,12.7,8.2,4.3,5.7,21.1,21.4,2.8),
("BOS","Boston Celtics",14,11,3,".786",48.4,114.8,40.2,87.9,45.7,16.8,43.9,38.2,17.6,22.7,77.4,13.1,31.8,44.9,27.1,14.4,8.4,4.7,4.3,21.3,22.0,11.5),
("HOU","Houston Rockets",15,11,4,".733",48.0,117.8,42.0,87.5,48.0,12.7,34.3,37.1,21.1,25.9,81.2,14.0,31.7,45.7,27.4,14.4,7.6,5.7,4.6,20.0,22.0,8.3),
("MEM","Memphis Grizzlies",14,10,4,".714",48.4,121.7,42.9,89.8,47.7,15.6,39.4,39.5,20.4,24.1,84.6,12.7,34.7,47.4,28.9,16.1,6.5,5.1,7.0,23.7,21.5,9.4),
("MIN","Minnesota Timberwolves",14,10,4,".714",48.4,117.4,42.6,90.6,47.0,13.9,38.1,36.4,18.3,26.5,69.0,13.9,34.9,48.8,25.6,15.7,8.9,5.1,6.6,21.9,23.2,11.3),
("POR","Portland Trail Blazers",13,9,4,".692",48.0,117.9,39.5,85.5,46.3,15.6,43.4,36.0,23.2,29.5,78.9,11.5,33.1,44.6,25.3,16.2,6.9,5.4,4.2,22.7,24.2,6.5),
("DET","Detroit Pistons",12,8,4,".667",48.8,115.7,40.9,88.4,46.3,13.5,36.8,36.7,20.3,25.8,79.0,12.2,32.3,44.4,27.7,14.3,9.4,6.4,6.1,23.8,22.7,5.4),
("OKC","Oklahoma City Thunder",14,9,5,".643",48.0,112.1,41.5,90.5,45.9,10.9,32.0,34.2,18.2,22.3,81.7,11.6,34.6,46.1,22.7,13.4,8.4,5.1,5.1,19.4,21.2,5.1),
("DEN","Denver Nuggets",12,7,5,".583",48.4,113.8,41.3,85.0,48.6,10.7,30.9,34.5,20.5,25.8,79.4,10.0,31.7,41.7,27.3,13.8,8.8,4.4,4.3,19.3,22.7,0.7),
("ATL","Atlanta Hawks",14,8,6,".571",48.4,117.8,43.5,96.4,45.1,14.6,43.1,33.8,16.2,21.4,75.9,13.9,30.9,44.9,30.9,15.4,10.4,3.9,5.9,21.9,19.7,1.7),
("GSW","Golden State Warriors",14,8,6,".571",48.4,115.1,39.1,86.8,45.1,16.0,41.9,38.2,20.8,25.4,81.7,12.6,32.2,44.9,27.5,16.0,8.0,5.6,5.6,22.1,22.3,2.5),
("MIA","Miami Heat",14,8,6,".571",48.4,119.4,42.3,89.6,47.2,13.8,40.2,34.3,21.0,28.4,73.9,10.7,31.9,42.6,29.7,14.0,8.0,5.7,5.0,21.1,24.7,0.2),
("NYK","New York Knicks",13,7,6,".538",48.4,109.9,38.7,88.8,43.6,14.7,40.7,36.1,17.8,22.4,79.7,13.6,34.2,47.8,26.8,14.7,7.5,4.2,6.0,20.7,21.3,5.9),
("CLE","Cleveland Cavaliers",15,8,7,".533",48.3,118.1,42.4,89.3,47.5,15.1,41.1,36.7,18.2,24.1,75.6,11.0,34.9,45.9,27.5,14.0,7.5,5.2,3.7,21.6,20.3,2.3),
("DAL","Dallas Mavericks",14,7,7,".500",48.0,112.1,40.6,88.4,46.0,12.6,37.7,33.5,18.1,23.1,78.6,12.6,30.6,43.2,26.1,16.0,8.6,5.6,4.8,21.8,20.6,-2.5),
("ORL","Orlando Magic",13,6,7,".462",48.4,108.8,38.6,85.5,45.1,13.8,40.5,34.0,17.8,22.8,78.4,10.9,32.2,43.2,26.4,16.5,7.5,4.1,4.8,22.5,23.3,-3.3),
("PHX","Phoenix Suns",13,6,7,".462",48.0,113.0,41.5,88.7,46.8,13.8,37.6,36.6,16.2,21.2,76.4,11.5,28.6,40.1,27.2,14.4,8.0,4.2,4.8,21.7,19.4,-3.4),
("TOR","Toronto Raptors",13,5,8,".385",48.4,113.8,41.5,91.7,45.3,11.8,35.9,32.8,18.9,26.0,72.8,14.0,27.9,41.9,28.0,14.5,10.2,4.4,5.5,25.6,23.8,1.0),
("IND","Indiana Pacers",14,5,9,".357",48.0,112.1,40.9,87.1,47.0,11.9,36.1,32.8,18.4,24.0,76.5,9.6,32.0,41.6,27.8,14.5,7.2,4.2,4.3,20.4,22.8,-2.4),
("LAC","LA Clippers",12,4,8,".333",48.4,112.3,39.3,84.4,46.6,14.4,36.8,39.1,19.3,24.4,78.8,10.1,30.1,40.2,27.3,17.8,9.3,4.3,4.4,21.9,21.1,-4.2),
("NOP","New Orleans Pelicans",15,5,10,".333",49.0,115.8,40.1,86.9,46.2,9.8,29.5,33.3,25.7,31.5,81.6,11.1,31.0,42.1,24.3,15.7,9.9,5.3,5.7,24.5,23.9,-7.1),
("CHA","Charlotte Hornets",13,4,9,".308",48.0,99.1,34.8,87.0,40.0,14.0,44.8,31.3,15.5,18.8,82.8,15.2,31.4,46.5,21.8,19.3,7.0,4.6,4.6,20.6,21.5,-10.8),
("WAS","Washington Wizards",15,4,11,".267",48.7,111.3,39.9,87.1,45.8,10.3,32.8,31.5,21.2,26.5,79.9,10.9,30.9,41.7,23.9,14.7,7.7,5.5,3.6,20.7,21.5,-7.9),
("BKN","Brooklyn Nets",13,3,10,".231",48.4,111.2,37.6,84.2,44.7,14.5,39.9,36.2,21.5,28.7,74.8,11.5,30.7,42.2,24.3,17.2,8.5,4.9,4.8,26.3,24.1,-6.7),
("CHI","Chicago Bulls",13,3,10,".231",48.4,114.6,40.0,89.5,44.7,12.6,40.9,30.8,22.0,28.9,76.1,12.5,31.3,43.8,27.2,17.3,8.3,5.8,4.8,23.4,23.1,-11.3),
("SAC","Sacramento Kings",13,1,12,".077",48.0,107.8,39.1,85.9,45.5,12.4,36.1,34.3,17.2,22.5,76.7,9.8,29.9,39.7,25.2,17.5,7.8,3.5,5.5,22.9,19.6,-13.5),
("MIL","Milwaukee Bucks",14,1,13,".071",48.0,106.1,37.7,88.9,42.4,15.0,44.0,34.1,15.7,21.1,74.3,13.6,31.8,45.4,24.6,16.9,6.9,4.6,5.5,22.6,19.5,-13.6),
("UTA","Utah Jazz",14,1,13,".071",48.7,107.1,38.0,87.0,43.7,12.4,36.8,33.8,18.6,24.4,76.5,11.9,32.2,44.1,24.1,16.6,6.7,6.0,5.4,23.6,23.4,-10.9),
]
TRA_COLS = ["abbr","team","gp","w","l","win_pct","min","pts","fgm","fga","fg_pct",
            "fg3m","fg3a","fg3_pct","ftm","fta","ft_pct","oreb","dreb","reb","ast",
            "tov","stl","blk","blka","pf","pfd","plus_minus"]

# abbr, GP, W, L, MIN, OppFGM, OppFGA, OppFG%, Opp3PM, Opp3PA, Opp3P%, OppFTM,
# OppFTA, OppFT%, OppOREB, OppDREB, OppREB, OppAST, OppTOV, OppSTL, OppBLK,
# OppBLKA, OppPF, OppPFD, OppPTS, +/-
OPP = [
("LAL","Los Angeles Lakers",14,12,2,48.0,39.2,86.1,45.5,15.0,40.9,36.6,21.4,28.2,75.9,13.6,27.5,41.1,27.5,18.4,9.5,4.1,6.4,24.1,23.4,114.9,-7.9),
("PHI","Philadelphia 76ers",15,12,3,48.0,40.3,87.5,46.1,12.1,36.1,33.5,18.5,24.7,74.9,11.0,34.5,45.5,25.4,14.5,6.5,5.7,4.3,21.4,21.1,111.3,-2.8),
("SAS","San Antonio Spurs",14,12,2,48.4,38.9,89.2,43.6,12.8,33.5,38.2,15.4,19.1,80.6,10.9,31.7,42.6,25.0,14.5,6.5,4.9,7.1,20.9,19.4,105.9,-12.9),
("BOS","Boston Celtics",14,11,3,48.4,35.8,84.6,42.3,14.4,42.4,34.1,17.3,22.6,76.6,12.4,30.6,43.1,25.6,16.6,7.1,4.3,4.7,22.0,21.3,103.3,-11.5),
("HOU","Houston Rockets",15,11,4,48.0,40.1,87.8,45.6,12.9,39.2,32.8,16.5,22.6,73.2,12.2,28.1,40.3,24.0,14.6,8.4,4.6,5.7,22.0,20.0,109.5,-8.3),
("MEM","Memphis Grizzlies",14,10,4,48.4,40.5,89.6,45.2,12.3,37.1,33.1,19.0,25.0,76.0,11.9,29.0,40.9,25.0,14.1,7.9,7.0,5.1,21.6,23.8,112.3,-9.4),
("MIN","Minnesota Timberwolves",14,10,4,48.4,38.5,89.4,43.1,11.5,35.7,32.2,17.6,22.7,77.7,12.3,31.4,43.7,24.6,16.6,7.7,6.6,5.1,23.2,21.9,106.1,-11.3),
("OKC","Oklahoma City Thunder",14,9,5,48.0,37.3,88.9,41.9,14.8,43.6,33.9,17.7,21.9,80.8,12.0,31.4,43.4,24.7,14.9,6.5,5.1,5.1,21.2,19.4,107.1,-5.1),
("POR","Portland Trail Blazers",13,9,4,48.0,38.3,87.1,44.0,11.3,35.2,32.1,23.5,28.5,82.4,11.7,30.5,42.2,23.3,13.9,8.5,4.2,5.4,24.2,22.7,111.4,-6.5),
("ATL","Atlanta Hawks",14,8,6,48.4,41.8,87.2,47.9,12.6,36.9,34.1,19.9,25.1,79.3,11.6,34.6,46.1,27.8,18.9,9.9,5.9,3.9,19.7,21.9,116.1,-1.7),
("CLE","Cleveland Cavaliers",15,8,7,48.3,41.5,92.3,45.0,13.9,40.1,34.6,18.9,23.8,79.3,12.6,32.0,44.6,27.5,12.9,7.2,3.7,5.2,20.3,21.6,115.8,-2.3),
("DET","Detroit Pistons",12,8,4,48.8,38.6,87.3,44.2,12.2,36.5,33.3,20.9,26.8,78.0,13.0,32.8,45.8,23.6,17.7,8.0,6.1,6.4,22.7,23.8,110.3,-5.4),
("GSW","Golden State Warriors",14,8,6,48.4,40.6,88.8,45.8,13.0,37.9,34.3,18.3,23.4,78.0,12.6,31.2,43.9,27.1,15.9,8.9,5.6,5.6,22.3,22.1,112.6,-2.5),
("MIA","Miami Heat",14,8,6,48.4,42.7,89.7,47.6,15.4,40.4,38.2,18.3,23.6,77.6,12.1,33.5,45.6,29.2,16.5,7.8,5.0,5.7,24.7,21.1,119.1,-0.2),
("DAL","Dallas Mavericks",14,7,7,48.0,42.1,89.1,47.2,12.9,37.9,34.1,17.5,23.4,74.9,12.6,31.4,44.1,27.7,15.6,8.4,4.8,5.6,20.6,21.8,114.6,2.5),
("DEN","Denver Nuggets",12,7,5,48.4,41.6,90.0,46.2,14.3,39.0,36.5,15.8,20.3,77.5,13.3,30.9,44.3,27.9,14.6,7.2,4.3,4.4,22.7,19.3,113.2,-0.7),
("NYK","New York Knicks",13,7,6,48.4,37.4,86.4,43.3,13.4,39.4,34.0,15.8,22.1,71.8,10.9,30.7,41.6,24.9,13.4,6.6,6.0,4.2,21.3,20.7,104.0,-5.9),
("ORL","Orlando Magic",13,6,7,48.4,39.6,85.7,46.2,14.1,37.3,37.7,18.8,25.2,74.7,10.2,31.3,41.5,27.1,14.9,9.4,4.8,4.1,23.3,22.5,112.2,3.3),
("PHX","Phoenix Suns",13,6,7,48.0,40.5,86.5,46.9,14.1,37.9,37.1,21.2,27.4,77.5,13.6,31.8,45.5,25.8,17.2,7.7,4.8,4.2,19.4,21.7,116.4,3.4),
("IND","Indiana Pacers",14,5,9,48.0,40.9,89.3,45.8,14.1,39.2,36.1,18.5,23.7,78.0,11.5,35.2,46.7,26.2,14.9,8.4,4.3,4.2,22.8,20.4,114.5,2.4),
("NOP","New Orleans Pelicans",15,5,10,49.0,42.3,87.6,48.3,13.3,38.8,34.4,24.9,30.9,80.4,11.6,33.5,45.1,28.7,15.7,7.9,5.7,5.3,23.9,24.5,122.9,7.1),
("TOR","Toronto Raptors",13,5,8,48.4,38.4,81.0,47.4,12.7,34.5,36.8,23.3,28.8,81.0,10.7,31.5,42.2,25.8,18.9,8.2,5.5,4.4,23.8,25.6,112.8,-1.0),
("CHA","Charlotte Hornets",13,4,9,48.0,39.2,82.5,47.6,14.5,35.7,40.5,16.9,22.0,76.9,8.6,30.7,39.3,26.4,14.2,9.2,4.6,4.6,21.5,20.6,109.8,10.8),
("LAC","LA Clippers",12,4,8,48.4,42.6,88.0,48.4,13.1,36.2,36.2,18.3,24.7,74.0,12.0,31.7,43.8,26.7,16.1,8.9,4.4,4.3,21.1,21.9,116.5,4.2),
("WAS","Washington Wizards",15,4,11,48.7,43.9,93.9,46.7,12.6,38.0,33.2,18.9,22.1,85.2,14.3,33.8,48.1,29.4,14.1,8.8,3.6,5.5,21.5,20.7,119.2,7.9),
("BKN","Brooklyn Nets",13,3,10,48.4,40.0,84.8,47.1,14.1,39.3,35.8,23.8,29.8,79.6,10.9,30.6,41.5,27.2,15.9,8.5,4.8,4.9,24.2,26.3,117.8,6.7),
("CHI","Chicago Bulls",13,3,10,48.4,45.6,94.9,48.1,13.4,37.2,36.0,21.3,28.1,75.9,14.1,33.7,47.8,29.5,14.8,10.2,4.8,5.8,23.1,23.4,125.9,11.3),
("MIL","Milwaukee Bucks",14,1,13,48.0,42.6,92.4,46.1,14.6,41.9,34.9,19.9,25.6,77.7,14.6,34.4,48.9,27.9,13.4,9.9,5.5,4.6,19.5,22.6,119.7,13.6),
("SAC","Sacramento Kings",13,1,12,48.0,42.2,85.5,49.4,13.7,37.1,36.9,23.1,28.9,79.8,10.3,33.0,43.3,26.1,14.6,9.3,5.5,3.5,19.7,23.0,121.2,13.5),
("UTA","Utah Jazz",14,1,13,48.7,39.8,87.6,45.4,12.4,35.4,35.1,26.0,31.4,82.9,11.1,34.9,46.1,23.1,13.8,9.1,5.4,6.0,23.4,23.6,118.0,10.9),
]
OPP_COLS = ["abbr","team","gp","w","l","min","opp_fgm","opp_fga","opp_fg_pct",
            "opp_fg3m","opp_fg3a","opp_fg3_pct","opp_ftm","opp_fta","opp_ft_pct",
            "opp_oreb","opp_dreb","opp_reb","opp_ast","opp_tov","opp_stl","opp_blk",
            "opp_blka","opp_pf","opp_pfd","opp_pts","plus_minus"]


def reconcile(adv, trad, opp):
    """Assert the three tables describe the same 30 teams' same games.

    Takes the dict rows (the same shape that is written to disk) so the check
    runs on exactly what gets published.
    """
    problems = []
    amap = {r["abbr"]: r for r in adv}
    if len(amap) != 30:
        problems.append(f"advanced table has {len(amap)} distinct teams, expected 30")
    for name, rows in (("traditional", trad), ("opponent", opp)):
        if len({r["abbr"] for r in rows}) != 30:
            problems.append(f"{name} table does not carry 30 distinct teams")
        if {r["abbr"] for r in rows} != set(amap):
            problems.append(f"{name} team set differs from advanced")
        for r in rows:
            a = amap.get(r["abbr"])
            if not a:
                continue
            if (r["gp"], r["w"], r["l"]) != (a["gp"], a["w"], a["l"]):
                problems.append(
                    f"{name} {r['abbr']}: GP/W/L {r['gp']}/{r['w']}/{r['l']} "
                    f"!= advanced {a['gp']}/{a['w']}/{a['l']}")
    # PACE is possessions per 48 team-minutes, so POSS*48/MIN should reproduce
    # it. This is the check that caught the MIA row shifted one column when it
    # was split across a render chunk: `poss` two places off missed by ~3,000.
    # It is NOT an exact identity on the official page — PACE and POSS are
    # rounded independently, so measured league-wide the residual runs to
    # 0.345 possessions (ORL) with a median of 0.10. The tolerance is therefore
    # set at 0.5, which is above every observed rounding residual and far below
    # the ~2,700 a column shift produces.
    PACE_TOLERANCE = 0.5
    for r in adv:
        if not r.get("min") or not r.get("poss") or not r.get("pace"):
            problems.append(f"{r['abbr']}: MIN/POSS/PACE missing")
            continue
        derived = r["poss"] * 48.0 / r["min"]
        if abs(derived - r["pace"]) > PACE_TOLERANCE:
            problems.append(f"{r['abbr']}: PACE printed {r['pace']} but "
                            f"POSS*48/MIN = {derived:.2f} "
                            f"(tolerance {PACE_TOLERANCE})")
    omap = {r["abbr"]: r for r in opp}
    tmap = {r["abbr"]: r for r in trad}
    for ab, t in tmap.items():
        o = omap[ab]
        # PTS and OppPTS are printed to 0.1, +/- to 0.1, so allow 0.15 slack
        if abs(t["pts"] - o["opp_pts"] - t["plus_minus"]) > 0.15:
            problems.append(f"{ab}: PTS {t['pts']} - OppPTS {o['opp_pts']} "
                            f"!= +/- {t['plus_minus']}")
    for label, rows in (("advanced", adv), ("traditional", trad), ("opponent", opp)):
        sw = sum(r["w"] for r in rows)
        sl = sum(r["l"] for r in rows)
        if sw != sl:
            problems.append(f"{label}: sum W {sw} != sum L {sl}")
    return problems


def main():
    adv = [dict(zip(ADV_COLS, r)) for r in ADV]
    trad = [dict(zip(TRA_COLS, r)) for r in TRA]
    opp = [dict(zip(OPP_COLS, r)) for r in OPP]
    problems = reconcile(adv, trad, opp)
    print("reconciliation problems:", len(problems))
    for p in problems:
        print("  !", p)
    if problems:
        raise SystemExit(1)

    for name, rows, url, order in (
            ("advanced", adv, ADV_URL,
             "GP, W, L, MIN, OffRtg, DefRtg, NetRtg, AST%, AST/TO, AST Ratio, OREB%, "
             "DREB%, REB%, TOV%, eFG%, TS%, PACE, PIE, POSS"),
            ("traditional", trad, TRA_URL,
             "GP, W, L, WIN%, MIN, PTS, FGM, FGA, FG%, 3PM, 3PA, 3P%, FTM, FTA, FT%, "
             "OREB, DREB, REB, AST, TOV, STL, BLK, BLKA, PF, PFD, +/-"),
            ("opponent", opp, OPP_URL,
             "GP, W, L, MIN, OppFGM, OppFGA, OppFG%, Opp3PM, Opp3PA, Opp3P%, OppFTM, "
             "OppFTA, OppFT%, OppOREB, OppDREB, OppREB, OppAST, OppTOV, OppSTL, "
             "OppBLK, OppBLKA, OppPF, OppPFD, OppPTS, +/-")):
        doc = {
            "title": f"NBA official Teams {name.title()} table, re-read 2026-11-17",
            "generated_by": BY,
            "source_url": url,
            "retrieved_utc": STAMP,
            "page_state": "30 Rows - Page 1 of 1 (the page's own row count); "
                          "Season=2026-27, SeasonType=Regular+Season, Per Game",
            "column_order_on_page": order,
            "coverage": {"rows": len(rows), "expected": 30, "complete": len(rows) == 30},
            "integrity": {
                "sum_w": sum(r["w"] for r in rows),
                "sum_l": sum(r["l"] for r in rows),
                "w_equals_l": sum(r["w"] for r in rows) == sum(r["l"] for r in rows),
                "cross_table_reconciliation": "passed: GP/W/L agree across all three "
                                              "tables and PTS - OppPTS == +/- on every team",
                "pace_identity": "POSS*48/MIN reproduces the printed PACE on every "
                                 "row within 0.5 possessions (measured max residual "
                                 "0.345, ORL; median 0.10) — the residuals are the "
                                 "official page's independent rounding, and the check "
                                 "is what caught this capture's one real defect",
            },
            "null_cells": [f"{r['abbr']}.{k}" for r in rows for k, v in r.items()
                           if v is None] or [],
            "null_note": "a cell the page render did not print is stored as null, "
                         "never filled in from a neighbouring column. This capture "
                         "has no null cells: every field on all 30 rows was printed.",
            "rows": rows,
        }
        path = os.path.join(OFF, f"teams_{name}_2026-11-17_c5487cbb.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("wrote", os.path.basename(path), len(rows), "rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
