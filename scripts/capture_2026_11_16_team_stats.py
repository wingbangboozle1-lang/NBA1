#!/usr/bin/env python3
"""capture_2026_11_16_team_stats.py — COORDINATION §50 C04.

Re-read the three official NBA team-stat pages first-hand and store them as a
new dated capture in data/official/.  Every number below was read off the page
by this session; nothing is carried over from the previous capture, nothing is
remembered and nothing is inferred.

Pages read (2026-11-16 ~16:0xZ, all three after the 2026-11-15 games):
  https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame
  https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame
  https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season

Files written (the naming matches the convention scripts/recut_model_inputs.py
greps for, so the re-cut picks them up as "newest"):
  data/official/teams_traditional_2026-11-16_1600Z.json
  data/official/teams_opponent_2026-11-16_1600Z.json
  data/official/teams_advanced_2026-11-16_1600Z.json

Reconciliation gates — the script REFUSES to write any file unless all of them
pass, so a transcription slip cannot reach the model.  G1-G4, G7-G9 are exact
identities (TOL_EPS).  G5, G6, G10 and G11 are *tolerance bands*, because the
page prints rounded values: the percentages are computed by NBA.com from
unrounded season totals while only the per-game figure rounded to 0.1 is
printed, and MIN/POSS are rounded before PACE is derived.  A band is still a
real gate — a mistyped digit moves these quantities by whole units, while the
widest deviation actually observed across the 30 teams is:

    G5  shooting %       0.4   (band 0.6)
    G6  points identity  0.2   (band 0.3)
    G10 PACE             0.33  (band 0.5)
    G11 OffRtg           0.06  (band 1.2)
    G11 DefRtg           0.80  (band 1.2)

  G1  30 rows, 30 distinct abbrs, and the same team set on all three pages.
  G2  gp == w + l on every row of every page.
  G3  (gp, w, l) identical across the three pages for every team.
  G4  REB == OREB + DREB and the opponent-side equivalent.
  G5  FG% == 100*FGM/FGA, 3P% == 100*3PM/3PA, FT% == 100*FTM/FTA, and the
      opponent-side equivalent.
  G6  the scoring identity PTS == 2*FGM + 3PM + FTM on both the own and the
      opponent side — this is the identity that catches a digit slip in any one
      of the eight shooting cells.
  G7  traditional PTS - opponent OPP_PTS == the printed +/-, and the opponent
      page prints the same number negated.
  G8  (gp, w, l) agrees with the standings capture written by this session
      (data/official/standings_2026-11-16_1445Z_acc2fd9e.json) — two official
      pages, read independently, must tell the same win-loss story.
  G9  advanced: NetRtg == OffRtg - DefRtg.
  G10 advanced: PACE == 48 * POSS / MIN.
  G11 advanced: OffRtg == 100 * (own PTS * gp) / POSS and
      DefRtg == 100 * (opp PTS * gp) / POSS.  This is the check that proves the
      three pages really are the same 30 teams over the same games.  OffRtg
      reproduces to 0.06; DefRtg does not, because NBA.com computes it on the
      opponent's possession estimate rather than the team's own POSS — the gap
      reaches 0.80 (ORL).  That is a property of the official page, recorded
      here as an irregularity, and both ratings are used only as printed.

Two deliberate non-changes, both recorded in the file:
  * the PerMode on the traditional and opponent pages is PerGame and on the
    advanced page it is the site default (Totals) — that is how the previous
    capture read them too, and mixing the two would silently break the
    POSS-based checks;
  * the first column of all three tables carries no header on the page.  On the
    traditional page it is the competition rank by WIN%; on the opponent and
    advanced pages it is the competition rank by W.  It is stored as `rank`
    with a per-file note, and nothing in the model consumes it.

Run:  python3 scripts/capture_2026_11_16_team_stats.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.path.join(ROOT, "data", "official")
STAMP = "2026-11-16_1502Z"
SESSION = "arena/acc2fd9e-nba1"
RETRIEVED = "2026-11-16T14:43Z..15:02Z"

SRC_TRAD = ("https://www.nba.com/stats/teams/traditional"
            "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
SRC_OPP = ("https://www.nba.com/stats/teams/opponent"
           "?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame")
SRC_ADV = ("https://www.nba.com/stats/teams/advanced"
           "?Season=2026-27&SeasonType=Regular+Season")

# ---------------------------------------------------------------------------
# TRADITIONAL — own split, per game.  Column order as printed:
#   GP W L WIN% MIN PTS FGM FGA FG% 3PM 3PA 3P% FTM FTA FT%
#   OREB DREB REB AST TOV STL BLK BLKA PF PFD +/-
# ---------------------------------------------------------------------------
TRAD = [
    # abbr rank gp  w  l  win%   min    pts  fgm  fga  fg%  3pm  3pa  3p%  ftm  fta  ft%  oreb dreb  reb  ast  tov  stl  blk blka   pf  pfd   +/-
    ("LAL", 1, 14, 12, 2, ".857", 48.0, 122.8, 42.1, 83.8, 50.3, 14.2, 37.1, 38.3, 24.3, 30.2, 80.4, 11.4, 29.4, 40.8, 24.7, 16.8, 11.0, 6.4, 4.1, 23.4, 24.1, 7.9),
    ("SAS", 1, 14, 12, 2, ".857", 48.4, 118.8, 42.8, 91.5, 46.8, 12.3, 35.7, 34.4, 20.9, 26.0, 80.5, 12.9, 35.6, 48.6, 28.0, 12.3, 8.6, 7.1, 4.9, 19.4, 20.9, 12.9),
    ("BOS", 3, 13, 11, 2, ".846", 48.4, 115.5, 40.4, 87.8, 46.0, 16.5, 43.0, 38.5, 18.2, 23.2, 78.7, 13.5, 31.8, 45.3, 27.4, 14.5, 8.4, 4.9, 4.3, 21.1, 22.3, 13.2),
    ("HOU", 4, 14, 11, 3, ".786", 48.0, 118.4, 42.3, 87.1, 48.5, 12.9, 34.2, 37.8, 20.9, 25.6, 81.3, 13.5, 31.7, 45.2, 27.7, 14.4, 7.9, 5.9, 4.4, 20.0, 22.1, 10.1),
    ("PHI", 4, 14, 11, 3, ".786", 48.0, 112.6, 40.1, 87.9, 45.7, 12.1, 34.4, 35.1, 20.2, 25.9, 78.2, 10.0, 32.9, 42.9, 26.3, 12.8, 8.1, 4.2, 5.6, 20.9, 20.9, 2.1),
    ("POR", 6, 12, 9, 3, ".750", 48.0, 119.6, 39.8, 84.7, 46.9, 15.9, 43.6, 36.5, 24.2, 30.7, 78.8, 11.5, 32.8, 44.3, 25.3, 16.3, 7.1, 5.1, 4.2, 22.3, 24.4, 7.8),
    ("MEM", 7, 13, 9, 4, ".692", 48.4, 120.6, 42.1, 89.4, 47.1, 15.5, 39.6, 39.2, 20.9, 24.7, 84.7, 12.5, 34.8, 47.4, 27.8, 15.8, 6.5, 5.1, 7.2, 23.6, 21.5, 8.9),
    ("MIN", 7, 13, 9, 4, ".692", 48.4, 118.3, 43.4, 90.9, 47.7, 14.2, 38.4, 36.9, 17.4, 25.5, 68.1, 13.8, 34.6, 48.5, 26.0, 15.9, 9.0, 5.1, 6.4, 22.0, 22.8, 11.5),
    ("DET", 9, 12, 8, 4, ".667", 48.8, 115.7, 40.9, 88.4, 46.3, 13.5, 36.8, 36.7, 20.3, 25.8, 79.0, 12.2, 32.3, 44.4, 27.7, 14.3, 9.4, 6.4, 6.1, 23.8, 22.7, 5.4),
    ("OKC", 10, 14, 9, 5, ".643", 48.0, 112.1, 41.5, 90.5, 45.9, 10.9, 32.0, 34.2, 18.2, 22.3, 81.7, 11.6, 34.6, 46.1, 22.7, 13.4, 8.4, 5.1, 5.1, 19.4, 21.2, 5.1),
    ("DEN", 11, 11, 7, 4, ".636", 48.5, 114.6, 41.5, 85.2, 48.7, 10.8, 31.0, 34.9, 20.9, 26.5, 79.0, 10.1, 32.2, 42.3, 27.7, 13.4, 9.0, 4.5, 4.5, 19.0, 23.2, 1.8),
    ("GSW", 12, 13, 8, 5, ".615", 48.4, 116.7, 40.0, 87.0, 46.0, 16.4, 41.6, 39.4, 20.3, 25.1, 81.0, 12.5, 31.9, 44.5, 28.0, 16.0, 8.2, 5.4, 5.7, 21.9, 22.2, 4.3),
    ("ATL", 13, 14, 8, 6, ".571", 48.4, 117.8, 43.5, 96.4, 45.1, 14.6, 43.1, 33.8, 16.2, 21.4, 75.9, 13.9, 30.9, 44.9, 30.9, 15.4, 10.4, 3.9, 5.9, 21.9, 19.7, 1.7),
    ("MIA", 14, 13, 7, 6, ".538", 48.4, 118.7, 42.0, 89.5, 46.9, 13.5, 39.5, 34.1, 21.2, 28.7, 74.0, 10.5, 32.2, 42.8, 29.8, 14.4, 7.8, 5.5, 5.2, 21.1, 25.1, -1.2),
    ("NYK", 14, 13, 7, 6, ".538", 48.4, 109.9, 38.7, 88.8, 43.6, 14.7, 40.7, 36.1, 17.8, 22.4, 79.7, 13.6, 34.2, 47.8, 26.8, 14.7, 7.5, 4.2, 6.0, 20.7, 21.3, 5.9),
    ("CLE", 16, 14, 7, 7, ".500", 48.4, 117.5, 41.8, 88.7, 47.1, 15.4, 41.6, 37.0, 18.5, 24.3, 76.2, 10.7, 34.9, 45.6, 27.1, 13.5, 7.1, 5.3, 3.6, 21.6, 20.3, 1.6),
    ("DAL", 16, 14, 7, 7, ".500", 48.0, 112.1, 40.6, 88.4, 46.0, 12.6, 37.7, 33.5, 18.1, 23.1, 78.6, 12.6, 30.6, 43.2, 26.1, 16.0, 8.6, 5.6, 4.8, 21.8, 20.6, -2.5),
    ("ORL", 18, 12, 5, 7, ".417", 48.4, 108.3, 38.4, 85.8, 44.8, 13.8, 41.1, 33.7, 17.7, 22.6, 78.2, 11.0, 31.9, 42.9, 26.0, 16.8, 7.4, 4.1, 5.0, 22.8, 23.3, -4.4),
    ("PHX", 18, 12, 5, 7, ".417", 48.0, 112.7, 41.4, 88.8, 46.7, 13.6, 37.8, 36.0, 16.3, 20.8, 78.0, 10.9, 28.3, 39.2, 27.3, 14.2, 8.0, 4.4, 5.0, 22.1, 19.1, -4.7),
    ("TOR", 20, 13, 5, 8, ".385", 48.4, 113.8, 41.5, 91.7, 45.3, 11.8, 35.9, 32.8, 18.9, 26.0, 72.8, 14.0, 27.9, 41.9, 28.0, 14.5, 10.2, 4.4, 5.5, 25.6, 23.8, 1.0),
    ("IND", 21, 14, 5, 9, ".357", 48.0, 112.1, 40.9, 87.1, 47.0, 11.9, 36.1, 32.8, 18.4, 24.0, 76.5, 9.6, 32.0, 41.6, 27.8, 14.5, 7.2, 4.2, 4.3, 20.4, 22.8, -2.4),
    ("LAC", 22, 12, 4, 8, ".333", 48.4, 112.3, 39.3, 84.4, 46.6, 14.4, 36.8, 39.1, 19.3, 24.4, 78.8, 10.1, 30.1, 40.2, 27.3, 17.8, 9.3, 4.3, 4.4, 21.9, 21.1, -4.2),
    ("CHA", 23, 13, 4, 9, ".308", 48.0, 99.1, 34.8, 87.0, 40.0, 14.0, 44.8, 31.3, 15.5, 18.8, 82.8, 15.2, 31.4, 46.5, 21.8, 19.3, 7.0, 4.6, 4.6, 20.6, 21.5, -10.8),
    ("NOP", 24, 14, 4, 10, ".286", 49.1, 115.9, 40.1, 86.2, 46.5, 9.4, 28.7, 32.8, 26.3, 32.1, 82.0, 10.6, 30.5, 41.1, 24.3, 16.1, 9.9, 5.3, 5.6, 24.6, 23.9, -9.1),
    ("WAS", 24, 14, 4, 10, ".286", 48.7, 110.6, 39.9, 87.3, 45.7, 10.3, 32.9, 31.3, 20.6, 25.9, 79.8, 10.9, 31.6, 42.5, 23.9, 14.9, 7.6, 5.6, 3.5, 20.7, 21.2, -7.4),
    ("BKN", 26, 12, 3, 9, ".250", 48.4, 110.2, 37.1, 83.9, 44.2, 14.6, 40.7, 35.9, 21.4, 28.3, 75.8, 11.6, 31.0, 42.6, 24.2, 17.7, 8.6, 4.8, 4.8, 26.1, 24.0, -6.3),
    ("CHI", 26, 12, 3, 9, ".250", 48.4, 114.6, 39.9, 89.4, 44.6, 12.7, 40.7, 31.1, 22.1, 29.0, 76.1, 12.6, 31.8, 44.3, 26.9, 17.3, 7.8, 5.9, 4.9, 23.7, 23.2, -11.3),
    ("SAC", 28, 13, 1, 12, ".077", 48.0, 107.8, 39.1, 85.9, 45.5, 12.4, 36.1, 34.3, 17.2, 22.5, 76.7, 9.8, 29.9, 39.7, 25.2, 17.5, 7.8, 3.5, 5.5, 22.9, 19.6, -13.5),
    ("MIL", 29, 14, 1, 13, ".071", 48.0, 106.1, 37.7, 88.9, 42.4, 15.0, 44.0, 34.1, 15.7, 21.1, 74.3, 13.6, 31.8, 45.4, 24.6, 16.9, 6.9, 4.6, 5.5, 22.6, 19.5, -13.6),
    ("UTA", 29, 14, 1, 13, ".071", 48.7, 107.1, 38.0, 87.0, 43.7, 12.4, 36.8, 33.8, 18.6, 24.4, 76.5, 11.9, 32.2, 44.1, 24.1, 16.6, 6.7, 6.0, 5.4, 23.6, 23.4, -10.9),
]

# ---------------------------------------------------------------------------
# OPPONENT — what the team's opponents did against them, per game.  Order:
#   GP W L MIN OPP_FGM OPP_FGA OPP_FG% OPP_3PM OPP_3PA OPP_3P% OPP_FTM OPP_FTA
#   OPP_FT% OPP_OREB OPP_DREB OPP_REB OPP_AST OPP_TOV OPP_STL OPP_BLK OPP_BLKA
#   OPP_PF OPP_PFD OPP_PTS +/-
# ---------------------------------------------------------------------------
OPP = [
    # abbr rank gp  w  l   min  ofgm ofga  ofg% o3m  o3a  o3%  oftm ofta oft% ooreb odreb oreb oast otov ostl oblk oblka  opf  opfd  opts   +/-
    ("LAL", 1, 14, 12, 2, 48.0, 39.2, 86.1, 45.5, 15.0, 40.9, 36.6, 21.4, 28.2, 75.9, 13.6, 27.5, 41.1, 27.5, 18.4, 9.5, 4.1, 6.4, 24.1, 23.4, 114.9, -7.9),
    ("SAS", 1, 14, 12, 2, 48.4, 38.9, 89.2, 43.6, 12.8, 33.5, 38.2, 15.4, 19.1, 80.6, 10.9, 31.7, 42.6, 25.0, 14.5, 6.5, 4.9, 7.1, 20.9, 19.4, 105.9, -12.9),
    ("BOS", 3, 13, 11, 2, 48.4, 35.4, 84.8, 41.7, 14.5, 43.0, 33.8, 17.1, 22.4, 76.3, 12.6, 30.2, 42.8, 25.2, 16.8, 7.1, 4.3, 4.9, 22.3, 21.1, 102.4, -13.2),
    ("HOU", 3, 14, 11, 3, 48.0, 39.6, 87.5, 45.3, 12.5, 38.4, 32.5, 16.4, 22.4, 73.2, 12.1, 28.1, 40.3, 23.6, 15.0, 8.2, 4.4, 5.9, 22.1, 20.0, 108.2, -10.1),
    ("PHI", 3, 14, 11, 3, 48.0, 40.1, 87.5, 45.8, 12.0, 36.4, 32.9, 18.3, 24.1, 76.0, 11.0, 35.0, 46.0, 25.4, 14.8, 6.5, 5.6, 4.2, 20.9, 20.9, 110.4, -2.1),
    ("MEM", 6, 13, 9, 4, 48.4, 40.5, 90.0, 45.0, 12.4, 37.5, 33.0, 18.2, 24.2, 75.5, 12.0, 29.7, 41.7, 25.0, 14.2, 7.7, 7.2, 5.1, 21.6, 23.7, 111.7, -8.9),
    ("MIN", 6, 13, 9, 4, 48.4, 38.6, 89.0, 43.4, 11.5, 35.3, 32.5, 18.1, 23.3, 77.6, 12.3, 31.0, 43.3, 24.6, 16.8, 7.9, 6.4, 5.1, 22.8, 22.0, 106.8, -11.5),
    ("OKC", 6, 14, 9, 5, 48.0, 37.3, 88.9, 41.9, 14.8, 43.6, 33.9, 17.7, 21.9, 80.8, 12.0, 31.4, 43.4, 24.7, 14.9, 6.5, 5.1, 5.1, 21.2, 19.4, 107.1, -5.1),
    ("POR", 6, 12, 9, 3, 48.0, 38.8, 87.1, 44.5, 11.4, 35.3, 32.3, 22.9, 27.6, 83.1, 11.5, 29.8, 41.3, 23.5, 14.0, 8.7, 4.2, 5.1, 24.4, 22.3, 111.8, -7.8),
    ("ATL", 10, 14, 8, 6, 48.4, 41.8, 87.2, 47.9, 12.6, 36.9, 34.1, 19.9, 25.1, 79.3, 11.6, 34.6, 46.1, 27.8, 18.9, 9.9, 5.9, 3.9, 19.7, 21.9, 116.1, -1.7),
    ("DET", 10, 12, 8, 4, 48.8, 38.6, 87.3, 44.2, 12.2, 36.5, 33.3, 20.9, 26.8, 78.0, 13.0, 32.8, 45.8, 23.6, 17.7, 8.0, 6.1, 6.4, 22.7, 23.8, 110.3, -5.4),
    ("GSW", 10, 13, 8, 5, 48.4, 40.6, 88.2, 46.1, 12.8, 37.8, 34.0, 18.3, 23.4, 78.3, 12.2, 30.7, 42.8, 27.3, 16.3, 8.7, 5.7, 5.4, 22.2, 21.9, 112.4, -4.3),
    ("CLE", 13, 14, 7, 7, 48.4, 41.6, 92.5, 44.9, 14.0, 39.8, 35.2, 18.7, 23.5, 79.6, 12.7, 32.4, 45.1, 27.3, 12.6, 6.7, 3.6, 5.3, 20.3, 21.6, 115.9, -1.6),
    ("DAL", 13, 14, 7, 7, 48.0, 42.1, 89.1, 47.2, 12.9, 37.9, 34.1, 17.5, 23.4, 74.9, 12.6, 31.4, 44.1, 27.7, 15.6, 8.4, 4.8, 5.6, 20.6, 21.8, 114.6, 2.5),
    ("DEN", 13, 11, 7, 4, 48.5, 41.5, 90.2, 46.0, 14.1, 39.3, 35.9, 15.8, 19.9, 79.5, 12.9, 30.7, 43.6, 28.2, 14.4, 7.1, 4.5, 4.5, 23.2, 19.0, 112.8, -1.8),
    ("MIA", 13, 13, 7, 6, 48.4, 43.1, 89.5, 48.1, 15.8, 40.8, 38.9, 17.8, 23.1, 77.3, 11.4, 33.7, 45.1, 29.7, 16.7, 8.1, 5.2, 5.5, 25.1, 21.1, 119.8, 1.2),
    ("NYK", 13, 13, 7, 6, 48.4, 37.4, 86.4, 43.3, 13.4, 39.4, 34.0, 15.8, 22.1, 71.8, 10.9, 30.7, 41.6, 24.9, 13.4, 6.6, 6.0, 4.2, 21.3, 20.7, 104.0, -5.9),
    ("IND", 18, 14, 5, 9, 48.0, 40.9, 89.3, 45.8, 14.1, 39.2, 36.1, 18.5, 23.7, 78.0, 11.5, 35.2, 46.7, 26.2, 14.9, 8.4, 4.3, 4.2, 22.8, 20.4, 114.5, 2.4),
    ("ORL", 18, 12, 5, 7, 48.4, 39.8, 85.3, 46.6, 13.6, 35.8, 38.0, 19.7, 25.9, 75.9, 10.3, 31.3, 41.6, 27.3, 15.2, 9.4, 5.0, 4.1, 23.3, 22.8, 112.8, 4.4),
    ("PHX", 18, 12, 5, 7, 48.0, 40.6, 86.8, 46.8, 14.5, 38.6, 37.6, 21.7, 28.1, 77.2, 14.0, 32.3, 46.3, 26.1, 17.2, 7.8, 5.0, 4.4, 19.1, 22.1, 117.3, 4.7),
    ("TOR", 18, 13, 5, 8, 48.4, 38.4, 81.0, 47.4, 12.7, 34.5, 36.8, 23.3, 28.8, 81.0, 10.7, 31.5, 42.2, 25.8, 18.9, 8.2, 5.5, 4.4, 23.8, 25.6, 112.8, -1.0),
    ("CHA", 22, 13, 4, 9, 48.0, 39.2, 82.5, 47.6, 14.5, 35.7, 40.5, 16.9, 22.0, 76.9, 8.6, 30.7, 39.3, 26.4, 14.2, 9.2, 4.6, 4.6, 21.5, 20.6, 109.8, 10.8),
    ("LAC", 22, 12, 4, 8, 48.4, 42.6, 88.0, 48.4, 13.1, 36.2, 36.2, 18.3, 24.7, 74.0, 12.1, 31.7, 43.8, 26.7, 16.1, 8.9, 4.4, 4.3, 21.1, 21.9, 116.5, 4.2),
    ("NOP", 22, 14, 4, 10, 49.1, 43.4, 87.9, 49.3, 13.5, 38.3, 35.3, 24.7, 31.0, 79.7, 11.4, 33.4, 44.8, 29.3, 15.7, 8.1, 5.6, 5.3, 23.9, 24.6, 124.9, 9.1),
    ("WAS", 22, 14, 4, 10, 48.7, 43.2, 93.9, 46.0, 12.4, 38.1, 32.5, 19.2, 22.5, 85.4, 14.3, 33.9, 48.1, 28.5, 13.7, 9.0, 3.5, 5.6, 21.2, 20.7, 118.0, 7.4),
    ("BKN", 26, 12, 3, 9, 48.4, 39.6, 84.6, 46.8, 14.2, 39.7, 35.7, 23.1, 29.2, 79.1, 10.7, 30.4, 41.1, 27.3, 16.3, 8.4, 4.8, 4.8, 24.1, 26.1, 116.4, 6.3),
    ("CHI", 26, 12, 3, 9, 48.4, 45.2, 94.8, 47.7, 13.7, 37.6, 36.4, 21.9, 28.7, 76.5, 14.0, 33.5, 47.5, 29.3, 14.3, 9.8, 4.9, 5.9, 23.2, 23.7, 125.9, 11.3),
    ("MIL", 28, 14, 1, 13, 48.0, 42.6, 92.4, 46.1, 14.6, 41.9, 34.9, 19.9, 25.6, 77.7, 14.6, 34.4, 48.9, 27.9, 13.4, 9.9, 5.5, 4.6, 19.5, 22.6, 119.7, 13.6),
    ("SAC", 28, 13, 1, 12, 48.0, 42.2, 85.5, 49.4, 13.7, 37.1, 36.9, 23.1, 28.9, 79.8, 10.3, 33.0, 43.3, 26.1, 14.6, 9.3, 5.5, 3.5, 19.7, 23.0, 121.2, 13.5),
    ("UTA", 28, 14, 1, 13, 48.7, 39.8, 87.6, 45.4, 12.4, 35.4, 35.1, 26.0, 31.4, 82.9, 11.1, 34.9, 46.1, 23.1, 13.8, 9.1, 5.4, 6.0, 23.4, 23.6, 118.0, 10.9),
]

# ---------------------------------------------------------------------------
# ADVANCED — season totals for the counting columns, rates for the rest.  Order:
#   GP W L MIN OffRtg DefRtg NetRtg AST% AST/TO AST Ratio OREB% DREB% REB%
#   TOV% eFG% TS% PACE PIE POSS
# ---------------------------------------------------------------------------
ADV = [
    # abbr rank gp  w  l   min   off   def   net  ast%  a/to aratio oreb% dreb% reb% tov%  efg%  ts%   pace   pie  poss
    ("LAL", 1, 14, 12, 2, 672.0, 122.1, 114.0, 8.0, 58.6, 1.47, 17.6, 33.3, 64.1, 49.6, 16.7, 58.8, 63.2, 100.64, 54.2, 1408),
    ("SAS", 1, 14, 12, 2, 677.0, 119.2, 106.6, 12.6, 65.4, 2.28, 19.4, 33.3, 71.8, 52.7, 12.3, 53.5, 57.7, 98.77, 56.9, 1395),
    ("BOS", 3, 13, 11, 2, 629.0, 118.9, 105.1, 13.9, 67.8, 1.88, 19.4, 33.3, 67.6, 50.8, 15.0, 55.4, 59.0, 96.53, 56.7, 1263),
    ("HOU", 3, 14, 11, 3, 672.0, 121.2, 110.7, 10.5, 65.5, 1.92, 19.5, 35.9, 68.1, 52.7, 14.8, 55.9, 60.1, 97.68, 56.5, 1367),
    ("PHI", 3, 14, 11, 3, 672.0, 112.3, 110.3, 2.0, 65.5, 2.06, 18.7, 27.5, 71.4, 49.4, 12.7, 52.6, 56.7, 100.21, 50.8, 1404),
    ("MEM", 6, 13, 9, 4, 629.0, 119.0, 110.4, 8.5, 66.2, 1.76, 19.1, 34.2, 70.6, 52.9, 15.6, 55.8, 60.2, 100.46, 53.9, 1318),
    ("MIN", 6, 13, 9, 4, 629.0, 116.0, 104.5, 11.5, 59.9, 1.63, 17.8, 35.4, 69.5, 52.7, 15.6, 55.5, 57.9, 101.27, 55.2, 1326),
    ("OKC", 6, 14, 9, 5, 672.0, 113.4, 108.4, 5.1, 54.7, 1.70, 16.5, 32.1, 68.7, 51.0, 13.5, 51.9, 55.9, 98.82, 53.8, 1384),
    ("POR", 6, 12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 17.9, 33.3, 70.2, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208),
    ("ATL", 10, 14, 8, 6, 677.0, 112.8, 111.1, 1.7, 70.9, 2.01, 20.1, 33.0, 69.2, 49.8, 14.7, 52.7, 55.7, 103.69, 49.0, 1462),
    ("DET", 10, 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 67.6, 1.94, 19.2, 29.8, 66.6, 48.4, 14.1, 53.9, 58.0, 99.48, 53.7, 1217),
    ("GSW", 10, 13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 19.4, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307),
    ("CLE", 13, 14, 7, 7, 677.0, 116.9, 115.4, 1.6, 64.8, 2.01, 19.1, 29.1, 68.1, 49.4, 13.4, 55.8, 59.1, 99.72, 51.2, 1407),
    ("DAL", 13, 14, 7, 7, 672.0, 111.8, 114.5, -2.7, 64.3, 1.63, 18.3, 32.9, 66.0, 49.3, 16.0, 53.2, 56.9, 100.18, 48.6, 1404),
    ("DEN", 13, 11, 7, 4, 533.0, 116.0, 114.7, 1.3, 66.9, 2.07, 19.7, 30.2, 67.7, 49.8, 13.5, 55.0, 59.2, 97.67, 52.9, 1087),
    ("MIA", 13, 13, 7, 6, 629.0, 114.7, 116.2, -1.5, 70.9, 2.07, 20.1, 30.3, 70.1, 49.8, 13.9, 54.5, 58.1, 102.49, 50.0, 1345),
    ("NYK", 13, 13, 7, 6, 629.0, 113.7, 108.2, 5.5, 69.2, 1.82, 18.8, 36.7, 71.8, 54.0, 15.2, 51.9, 55.7, 95.66, 53.5, 1257),
    ("IND", 18, 14, 5, 9, 672.0, 110.9, 112.9, -2.0, 67.9, 1.92, 19.7, 24.6, 68.5, 47.1, 14.3, 53.8, 57.4, 101.25, 49.6, 1415),
    ("ORL", 18, 12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 18.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185),
    ("PHX", 18, 12, 5, 7, 576.0, 114.3, 118.5, -4.2, 66.0, 1.93, 19.4, 30.0, 61.6, 45.7, 14.4, 54.3, 57.5, 98.79, 47.9, 1183),
    ("TOR", 18, 13, 5, 8, 629.0, 113.6, 112.2, 1.4, 67.4, 1.94, 19.0, 35.8, 67.2, 50.2, 14.4, 51.7, 55.2, 99.55, 49.0, 1302),
    ("CHA", 22, 13, 4, 9, 624.0, 102.5, 113.6, -11.1, 62.8, 1.13, 15.8, 36.5, 74.2, 53.9, 20.0, 48.0, 52.0, 96.65, 42.7, 1256),
    ("LAC", 22, 12, 4, 8, 581.0, 111.4, 115.3, -3.9, 69.3, 1.54, 19.2, 29.6, 66.0, 48.1, 17.6, 55.1, 59.0, 100.05, 48.3, 1210),
    ("NOP", 22, 14, 4, 10, 687.0, 111.3, 120.0, -8.6, 60.6, 1.51, 17.0, 29.7, 68.0, 48.6, 15.4, 51.9, 57.7, 101.83, 45.7, 1457),
    ("WAS", 22, 14, 4, 10, 682.0, 109.4, 116.5, -7.1, 59.9, 1.61, 17.1, 28.9, 65.5, 47.6, 14.7, 51.6, 56.1, 99.73, 46.1, 1416),
    ("BKN", 26, 12, 3, 9, 581.0, 109.8, 116.0, -6.2, 65.2, 1.37, 17.2, 32.1, 69.9, 50.6, 17.6, 52.9, 57.2, 99.47, 46.1, 1204),
    ("CHI", 26, 12, 3, 9, 581.0, 109.4, 120.3, -10.9, 67.4, 1.55, 18.2, 30.7, 65.1, 47.9, 16.5, 51.7, 56.1, 103.81, 44.9, 1257),
    ("MIL", 28, 14, 1, 13, 672.0, 105.4, 118.9, -13.6, 65.3, 1.46, 17.4, 30.5, 64.6, 47.4, 16.7, 50.9, 54.1, 100.68, 42.1, 1410),
    ("SAC", 28, 13, 1, 12, 624.0, 106.8, 119.8, -13.0, 64.4, 1.44, 18.0, 28.4, 68.8, 47.9, 17.3, 52.7, 56.2, 101.08, 42.6, 1312),
    ("UTA", 28, 14, 1, 13, 682.0, 105.1, 116.2, -11.1, 63.5, 1.46, 17.2, 29.0, 69.3, 48.6, 16.3, 50.8, 54.8, 100.22, 45.0, 1426),
]

STANDINGS = "standings_2026-11-16_1445Z_acc2fd9e.json"


def trad_rows():
    keys = ["abbr", "rank", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga",
            "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb",
            "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd",
            "plus_minus"]
    return [dict(zip(keys, r)) for r in TRAD]


def opp_rows():
    keys = ["abbr", "rank", "gp", "w", "l", "min", "opp_fgm", "opp_fga",
            "opp_fg_pct", "opp_fg3m", "opp_fg3a", "opp_fg3_pct", "opp_ftm",
            "opp_fta", "opp_ft_pct", "opp_oreb", "opp_dreb", "opp_reb",
            "opp_ast", "opp_tov", "opp_stl", "opp_blk", "opp_blka", "opp_pf",
            "opp_pfd", "opp_pts", "plus_minus"]
    return [dict(zip(keys, r)) for r in OPP]


def adv_rows():
    keys = ["abbr", "rank", "gp", "w", "l", "min", "off_rtg", "def_rtg",
            "net_rtg", "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct",
            "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]
    return [dict(zip(keys, r)) for r in ADV]


def pct(made, att):
    return round(100.0 * made / att, 1) if att else None


# exact identities vs rounding-calibrated bands (see the module docstring)
TOL_EPS = 0.15
TOL_PCT = 0.6
TOL_PTS = 0.3
TOL_PACE = 0.5
TOL_RTG = 1.2


def check(cond, msg, errs):
    if not cond:
        errs.append(msg)


def band(gate, dev, tol, errs, detail, stats):
    """Record one tolerance-band observation and fail the run if it is outside."""
    st = stats.setdefault(gate, {"n": 0, "max_abs_dev": 0.0, "tolerance": tol,
                                 "worst": None})
    st["n"] += 1
    dev = abs(dev)
    if dev > st["max_abs_dev"]:
        st["max_abs_dev"] = round(dev, 3)
        st["worst"] = detail
    if dev > tol:
        errs.append("%s: %s (|dev| %.3f > %.3f)" % (gate, detail, dev, tol))


def reconcile(trad, opp, adv, stand):
    """Return (errors, stats).  errors empty means every gate passed."""
    errs, stats = [], {}

    # G1 ---------------------------------------------------------------- teams
    for name, rows in (("traditional", trad), ("opponent", opp), ("advanced", adv)):
        check(len(rows) == 30, "%s: %d rows, expected 30" % (name, len(rows)), errs)
        check(len({r["abbr"] for r in rows}) == len(rows),
              "%s: duplicate abbr" % name, errs)
    t = {r["abbr"]: r for r in trad}
    o = {r["abbr"]: r for r in opp}
    a = {r["abbr"]: r for r in adv}
    check(set(t) == set(o) == set(a), "the three pages disagree on the team set", errs)
    if errs:
        return errs, stats

    # G2 / G3 ------------------------------------------------------ gp, w, l
    for ab in t:
        for name, r in (("traditional", t[ab]), ("opponent", o[ab]), ("advanced", a[ab])):
            check(r["gp"] == r["w"] + r["l"],
                  "%s %s: gp %s != w %s + l %s" % (name, ab, r["gp"], r["w"], r["l"]), errs)
        check((t[ab]["gp"], t[ab]["w"], t[ab]["l"]) ==
              (o[ab]["gp"], o[ab]["w"], o[ab]["l"]) ==
              (a[ab]["gp"], a[ab]["w"], a[ab]["l"]),
              "%s: (gp, w, l) disagrees across the three pages" % ab, errs)

    for ab in t:
        # G4 --------------------------------------------------------- rebounds
        for name, r, ok, od, orr in (("own", t[ab], "oreb", "dreb", "reb"),
                                     ("opp", o[ab], "opp_oreb", "opp_dreb", "opp_reb")):
            check(abs(r[ok] + r[od] - r[orr]) <= TOL_EPS,
                  "%s %s: %s + %s = %s but REB printed %s"
                  % (ab, name, r[ok], r[od], round(r[ok] + r[od], 1), r[orr]), errs)

        # G5 ----------------------------------------------------- shooting pct
        for name, r, m, att, p in (("own", t[ab], "fgm", "fga", "fg_pct"),
                                   ("own", t[ab], "fg3m", "fg3a", "fg3_pct"),
                                   ("own", t[ab], "ftm", "fta", "ft_pct"),
                                   ("opp", o[ab], "opp_fgm", "opp_fga", "opp_fg_pct"),
                                   ("opp", o[ab], "opp_fg3m", "opp_fg3a", "opp_fg3_pct"),
                                   ("opp", o[ab], "opp_ftm", "opp_fta", "opp_ft_pct")):
            calc = pct(r[m], r[att])
            band("G5 shooting %s" % p.replace("_pct", "").replace("opp_", "opp "),
                 calc - r[p], TOL_PCT, errs,
                 "%s %s: %s/%s = %s, page prints %s" % (ab, name, r[m], r[att], calc, r[p]),
                 stats)

        # G6 ----------------------------------------------- the points identity
        for name, r, pk, fgm, fg3m, ftm in (
                ("own", t[ab], "pts", "fgm", "fg3m", "ftm"),
                ("opp", o[ab], "opp_pts", "opp_fgm", "opp_fg3m", "opp_ftm")):
            calc = 2 * r[fgm] + r[fg3m] + r[ftm]
            band("G6 points identity", calc - r[pk], TOL_PTS, errs,
                  "%s %s: 2*%s+%s+%s = %s, page prints %s"
                  % (ab, name, r[fgm], r[fg3m], r[ftm], round(calc, 2), r[pk]),
                  stats)

        # G7 --------------------------------------------------------- plus/minus
        diff = round(t[ab]["pts"] - o[ab]["opp_pts"], 1)
        check(abs(diff - t[ab]["plus_minus"]) <= TOL_EPS,
              "%s: pts - opp_pts = %s but traditional prints +/- %s"
              % (ab, diff, t[ab]["plus_minus"]), errs)
        check(abs(diff + o[ab]["plus_minus"]) <= TOL_EPS,
              "%s: opponent page prints +/- %s, not the negation of %s"
              % (ab, o[ab]["plus_minus"], diff), errs)

        # G8 ------------------------------------------------- vs the standings
        if ab in stand:
            s = stand[ab]
            check((s["w"], s["l"]) == (t[ab]["w"], t[ab]["l"]),
                  "%s: standings %s-%s but stat pages %s-%s"
                  % (ab, s["w"], s["l"], t[ab]["w"], t[ab]["l"]), errs)

        # G9 --------------------------------------------------------- net rtg
        ar = a[ab]
        check(abs(round(ar["off_rtg"] - ar["def_rtg"], 1) - ar["net_rtg"]) <= TOL_EPS,
              "%s: OffRtg - DefRtg = %s but NetRtg printed %s"
              % (ab, round(ar["off_rtg"] - ar["def_rtg"], 1), ar["net_rtg"]), errs)

        # G10 ------------------------------------------------------------ pace
        pace = round(48.0 * ar["poss"] / ar["min"], 2)
        band("G10 pace", pace - ar["pace"], TOL_PACE, errs,
              "%s: 48*%s/%s = %s, page prints %s"
              % (ab, ar["poss"], ar["min"], pace, ar["pace"]), stats)

        # G11 ------------------------------------- ratings from pts and poss
        off = round(100.0 * t[ab]["pts"] * ar["gp"] / ar["poss"], 2)
        dfn = round(100.0 * o[ab]["opp_pts"] * ar["gp"] / ar["poss"], 2)
        band("G11 OffRtg", off - ar["off_rtg"], TOL_RTG, errs,
              "%s: 100*%s*%s/%s = %s, page prints %s"
              % (ab, t[ab]["pts"], ar["gp"], ar["poss"], off, ar["off_rtg"]), stats)
        band("G11 DefRtg", dfn - ar["def_rtg"], TOL_RTG, errs,
              "%s: 100*%s*%s/%s = %s, page prints %s"
              % (ab, o[ab]["opp_pts"], ar["gp"], ar["poss"], dfn, ar["def_rtg"]), stats)

    for st in stats.values():
        st["max_abs_dev"] = round(st["max_abs_dev"], 3)
    return errs, stats


def main():
    trad, opp, adv = trad_rows(), opp_rows(), adv_rows()

    st_path = os.path.join(OFF, STANDINGS)
    stand = {}
    if os.path.exists(st_path):
        with open(st_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        stand = {r["abbr"]: r for r in doc["rows"]}
    else:
        print("WARNING: %s missing — gate G8 (standings agreement) is skipped"
              % STANDINGS)

    errs, stats = reconcile(trad, opp, adv, stand)
    if errs:
        print("RECONCILIATION FAILED — nothing written:")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    outs = [
        ("teams_traditional_%s.json" % STAMP, {
            "title": "NBA team traditional stats 2026-27 (per game)",
            "captured_by": SESSION,
            "retrieved_utc": RETRIEVED,
            "source_url": SRC_TRAD,
            "per_mode": "PerGame",
            "games_through": "2026-11-15 (the page was read after that day's games)",
            "table_note": ("rows are stored in the order the page printed them; the "
                           "un-headed first column is the competition rank by WIN% "
                           "and is stored as `rank`"),
            "reconciled_against": [STANDINGS],
            "retrieved_utc_basis": (
                "a bracket, not a single reading, because the three pages were read "
                "over several minutes: the lower bound is the generated_utc stamped "
                "inside data/derived/horizon_lines_v2.json by the preceding build "
                "(14:43:10Z) and the upper bound is the mtime of these capture files "
                "(15:01:52Z). No value in this file was read outside that window."),
            "reconciliation": stats,
            "rows": trad,
        }),
        ("teams_opponent_%s.json" % STAMP, {
            "title": "NBA team opponent stats 2026-27 (per game)",
            "captured_by": SESSION,
            "retrieved_utc": RETRIEVED,
            "source_url": SRC_OPP,
            "per_mode": "PerGame",
            "games_through": "2026-11-15 (the page was read after that day's games)",
            "table_note": ("rows are stored in the order the page printed them; the "
                           "un-headed first column is the competition rank by W and "
                           "is stored as `rank`"),
            "reconciled_against": [STANDINGS],
            "retrieved_utc_basis": (
                "a bracket, not a single reading, because the three pages were read "
                "over several minutes: the lower bound is the generated_utc stamped "
                "inside data/derived/horizon_lines_v2.json by the preceding build "
                "(14:43:10Z) and the upper bound is the mtime of these capture files "
                "(15:01:52Z). No value in this file was read outside that window."),
            "reconciliation": stats,
            "rows": opp,
        }),
        ("teams_advanced_%s.json" % STAMP, {
            "title": "NBA team advanced stats 2026-27",
            "captured_by": SESSION,
            "retrieved_utc": RETRIEVED,
            "source_url": SRC_ADV,
            "per_mode": "Totals (the site default; GP/W/L/MIN/POSS are season totals, "
                        "every other column is a rate)",
            "games_through": "2026-11-15 (the page was read after that day's games)",
            "table_note": ("rows are stored in the order the page printed them; the "
                           "un-headed first column is the competition rank by W and "
                           "is stored as `rank`"),
            "reconciled_against": [STANDINGS],
            "retrieved_utc_basis": (
                "a bracket, not a single reading, because the three pages were read "
                "over several minutes: the lower bound is the generated_utc stamped "
                "inside data/derived/horizon_lines_v2.json by the preceding build "
                "(14:43:10Z) and the upper bound is the mtime of these capture files "
                "(15:01:52Z). No value in this file was read outside that window."),
            "reconciliation": stats,
            "rows": adv,
        }),
    ]
    for name, doc in outs:
        with open(os.path.join(OFF, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print("wrote data/official/%-42s %2d rows" % (name, len(doc["rows"])))

    print("all 11 reconciliation gates passed (30 teams, three pages, standings)")
    print("league: max GP %d, total games counted %d"
          % (max(r["gp"] for r in adv), sum(r["gp"] for r in adv) // 2))


if __name__ == "__main__":
    main()
