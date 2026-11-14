#!/usr/bin/env python3
"""gameday_capture_2026_11_14.py — game-day official capture, written by hand from the
league's own documents and nothing else.

Session `arena/95c1cb23-nba1` (COORDINATION.md §30, tasks G01/G02).

WHAT THIS IS
-----------
A verbatim transcription of four official NBA sources, each read directly on
2026-11-14 between 18:38Z and 19:05Z (1:38 PM - 2:05 PM ET):

  1. NBA Official Injury Report, 11/14/26 01:30 PM ET edition (the league's game-day
     report for tonight's slate) - https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf
  2. NBA Official Injury Report, 11/14/26 04:15 AM ET edition (the edition every
     published line in docs/data/lines.json was actually built from) -
     https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf
  3. NBA.com Games & Scores for 2026-11-14, -15, -16 and -17 (matchup, tip time,
     game id, displayed records, displayed season leaders) -
     https://www.nba.com/games?date=YYYY-MM-DD
  4. NBA.com 2026-27 Regular Season Standings (all 30 club records) -
     https://www.nba.com/standings

Nothing here is derived from a third-party site, an API that is not NBA-operated, or
a model. Nothing is inferred: where the PDF does not carry a value, the field is null
and the row is flagged by scripts/gameday_read_2026_11_14.py.

THE ONE EXTRACTION HAZARD WORTH KNOWING ABOUT
--------------------------------------------
The report is a multi-page PDF whose table RE-FLOWS: page 1 carries the full seven
columns; later pages drop the Game Date / Game Time / Matchup / Team cells for rows
that continue a block started on the previous page. Rows marked
`attribution: "block"` below are those rows. Their team was assigned from the block
structure (the team label that opens the block) and from the league's own ordering
rule inside a block - players are listed alphabetically by surname within their club -
not guessed from a name. Every "block" row is then cross-checked against an official
source in the read-out script where a cross-check exists, and left flagged where none
does. Rows marked `attribution: "explicit"` carry the team cell in the PDF itself.

Run:  python3 scripts/gameday_capture_2026_11_14.py
Writes: data/captures/2026-11-14-pm/*.json
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "captures", "2026-11-14-pm")

SRC_1330 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"
SRC_0415 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf"
SRC_HUB = "https://official.nba.com/nba-injury-report-2026-27-season/"

# ---------------------------------------------------------------------------
# Edition: 11/14/26 01:30 PM ET  (newest published at capture time)
# Fields: date, time_et, matchup, team, player, status, reason, attribution
# "NOT YET SUBMITTED" rows carry player=None exactly as the PDF prints them.
# ---------------------------------------------------------------------------
E_1330 = [
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", "Missi, Yves", "Probable", "Injury/Illness - Left Knee Contusion / Bone Bruise", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Doubtful", "Injury/Illness - Left Ankle Sprain", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Allen, Jarrett", "Questionable", "Injury/Illness - Right Knee Injury", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Harden, James", "Questionable", "Injury/Illness - Left Lower Leg/Calf Tightness", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Mitchell, Donovan", "Questionable", "Injury/Illness - Left Knee Contusion/Injury Management", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way", "block"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Hamstring Injury Management", "block"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Probable", "Injury/Illness - Illness", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness", "block"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Memphis Grizzlies", None, "NOT YET SUBMITTED", None, "explicit"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation", "explicit"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Claxton, Nic", "Questionable", "Injury/Illness - Left Hamstring Injury Management", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Powell, Norman", "Questionable", "Injury/Illness - Low Back Injury Management", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Swain, Dailyn", "Out", "G League - On Assignment", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", "explicit"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "explicit"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Available", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Available", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Miami Heat", "Antetokounmpo, Giannis", "Probable", "Injury/Illness - Right Wrist Sprain", "block"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way", "block"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Miami Heat", "Larsson, Pelle", "Doubtful", "Injury/Illness - Illness", "block"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Miami Heat", "Thompson, Klay", "Probable", "Injury/Illness - Left Ankle Sprain", "block"),
]
# 11/15 rows of the 01:30 PM edition: eighteen clubs, every one "NOT YET SUBMITTED".
E_1330 += [
    ("11/15/2026", t, m, team, None, "NOT YET SUBMITTED", None, "explicit")
    for (t, m, team) in [
        ("01:00 (ET)", "IND@PHI", "Indiana Pacers"), ("01:00 (ET)", "IND@PHI", "Philadelphia 76ers"),
        ("04:00 (ET)", "LAL@PHX", "Los Angeles Lakers"), ("04:00 (ET)", "LAL@PHX", "Phoenix Suns"),
        ("04:30 (ET)", "CHA@LAC", "Charlotte Hornets"), ("04:30 (ET)", "CHA@LAC", "LA Clippers"),
        ("05:00 (ET)", "SAS@UTA", "San Antonio Spurs"), ("05:00 (ET)", "SAS@UTA", "Utah Jazz"),
        ("06:00 (ET)", "DAL@BOS", "Dallas Mavericks"), ("06:00 (ET)", "DAL@BOS", "Boston Celtics"),
        ("06:00 (ET)", "NYK@TOR", "New York Knicks"), ("06:00 (ET)", "NYK@TOR", "Toronto Raptors"),
        ("07:00 (ET)", "HOU@WAS", "Houston Rockets"), ("07:00 (ET)", "HOU@WAS", "Washington Wizards"),
        ("08:00 (ET)", "ATL@MIL", "Atlanta Hawks"), ("08:00 (ET)", "ATL@MIL", "Milwaukee Bucks"),
        ("09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder"), ("09:00 (ET)", "OKC@SAC", "Sacramento Kings"),
    ]
]

# ---------------------------------------------------------------------------
# Edition: 11/14/26 04:15 AM ET - the edition the published lines used.
# Transcribed from the same PDF structure; every row here carried the team cell
# except the six continuation rows marked "block".
# ---------------------------------------------------------------------------
E_0415 = [
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "07:00 (ET)", "DEN@NOP", "New Orleans Pelicans", None, "NOT YET SUBMITTED", None, "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint", "explicit"),
    ("11/14/2026", "07:30 (ET)", "DAL@CLE", "Cleveland Cavaliers", None, "NOT YET SUBMITTED", None, "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Brooklyn Nets", "Traore, Nolan", "Probable", "Injury/Illness - Right Calf Tightness / Soreness", "block"),
    ("11/14/2026", "08:00 (ET)", "BKN@MEM", "Memphis Grizzlies", None, "NOT YET SUBMITTED", None, "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Chicago Bulls", None, "NOT YET SUBMITTED", None, "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery", "block"),
    ("11/14/2026", "08:00 (ET)", "CHI@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy", "block"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way", "explicit"),
    ("11/14/2026", "08:00 (ET)", "DET@MIA", "Miami Heat", None, "NOT YET SUBMITTED", None, "explicit"),
]
E_0415 += [
    ("11/15/2026", t, m, team, None, "NOT YET SUBMITTED", None, "explicit")
    for (t, m, team) in [
        ("01:00 (ET)", "IND@PHI", "Indiana Pacers"), ("01:00 (ET)", "IND@PHI", "Philadelphia 76ers"),
        ("04:00 (ET)", "LAL@PHX", "Los Angeles Lakers"), ("04:00 (ET)", "LAL@PHX", "Phoenix Suns"),
        ("04:30 (ET)", "CHA@LAC", "Charlotte Hornets"), ("04:30 (ET)", "CHA@LAC", "LA Clippers"),
        ("05:00 (ET)", "SAS@UTA", "San Antonio Spurs"), ("05:00 (ET)", "SAS@UTA", "Utah Jazz"),
        ("06:00 (ET)", "DAL@BOS", "Dallas Mavericks"), ("06:00 (ET)", "DAL@BOS", "Boston Celtics"),
        ("06:00 (ET)", "NYK@TOR", "New York Knicks"), ("06:00 (ET)", "NYK@TOR", "Toronto Raptors"),
        ("07:00 (ET)", "HOU@WAS", "Houston Rockets"), ("07:00 (ET)", "HOU@WAS", "Washington Wizards"),
        ("08:00 (ET)", "ATL@MIL", "Atlanta Hawks"), ("08:00 (ET)", "ATL@MIL", "Milwaukee Bucks"),
        ("09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder"), ("09:00 (ET)", "OKC@SAC", "Sacramento Kings"),
    ]
]

# ---------------------------------------------------------------------------
# Slate: 27 games, read live off NBA.com Games & Scores on 2026-11-14.
# `away_record` / `home_record` are exactly what the card displayed at read time.
# leaders_* are the card's "Season Leaders" widget (name, ppg, rpg, apg).
# ---------------------------------------------------------------------------
G = "https://www.nba.com/games?date="


def slate_row(date, time_et, away, home, ar, hr, gid, la, lap, lar, laa, lh, lhp, lhr, hha, hasrc=None):
    return {
        "date": date, "time_et": time_et, "away": away, "home": home,
        "away_record": ar, "home_record": hr,
        "game_id": gid,
        "game_url": "https://www.nba.com/game/%s-vs-%s-%s" % (away.lower(), home.lower(), gid),
        "source_url": G + date,
        "leader_away": {"player": la, "ppg": lap, "rpg": lar, "apg": laa},
        "leader_home": {"player": lh, "ppg": lhp, "rpg": lhr, "apg": hha},
        "read_at_utc": hasrc or "2026-11-14T18:39Z",
    }


SLATE = [
    # ---- 2026-11-14 (5 games), read 18:39Z
    slate_row("2026-11-14", "7:00 PM ET", "DEN", "NOP", "6-4", "4-9", "0022600231",
              "Nikola Jokić", 23.5, 10.8, 9.0, "Zion Williamson", 21.8, 5.2, 2.8),
    slate_row("2026-11-14", "7:30 PM ET", "DAL", "CLE", "7-5", "6-7", "0022600232",
              "Cooper Flagg", 24.6, 6.9, 6.5, "Donovan Mitchell", 23.0, 4.9, 5.6),
    slate_row("2026-11-14", "8:00 PM ET", "BKN", "MEM", "3-8", "8-4", "0022600234",
              "Julius Randle", 19.7, 6.5, 5.0, "Ty Jerome", 25.4, 3.4, 5.3),
    slate_row("2026-11-14", "8:00 PM ET", "DET", "MIA", "8-3", "6-6", "0022600233",
              "Cade Cunningham", 25.0, 5.2, 7.9, "Giannis Antetokounmpo", 28.5, 12.3, 4.9),
    slate_row("2026-11-14", "8:00 PM ET", "CHI", "MIN", "2-9", "9-3", "0022600235",
              "Caleb Wilson", 18.9, 6.2, 1.9, "LaMelo Ball", 18.6, 3.3, 6.3),
    # ---- 2026-11-15 (9 games), read 18:52Z
    slate_row("2026-11-15", "1:00 PM ET", "IND", "PHI", "5-8", "10-3", "0022600236",
              "Pascal Siakam", 22.4, 6.6, 4.2, "Tyrese Maxey", 26.7, 3.4, 5.5, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "4:00 PM ET", "LAL", "PHX", "11-2", "5-6", "0022600237",
              "Luka Doncic", 38.6, 7.5, 7.6, "Devin Booker", 25.5, 2.5, 5.0, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "4:30 PM ET", "CHA", "LAC", "4-8", "3-8", "0022600238",
              "Naz Reid", 17.3, 8.5, 2.2, "Darius Garland", 20.7, 2.0, 6.9, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "5:00 PM ET", "SAS", "UTA", "11-2", "1-12", "0022600239",
              "Victor Wembanyama", 28.8, 11.7, 3.1, "Keyonte George", 20.9, 4.5, 6.5, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "6:00 PM ET", "DAL", "BOS", "7-5", "10-2", "0022600240",
              "Cooper Flagg", 24.6, 6.9, 6.5, "Jayson Tatum", 26.3, 6.1, 7.5, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "6:00 PM ET", "NYK", "TOR", "6-6", "5-7", "0022600241",
              "Karl-Anthony Towns", 21.1, 13.7, 3.7, "RJ Barrett", 21.3, 6.7, 4.1, hasrc="2026-11-14T18:52Z"),
    slate_row("2026-11-15", "7:00 PM ET", "HOU", "WAS", "10-3", "4-9", "0022600242",
              "Alperen Sengun", 23.1, 9.6, 7.6, "Anthony Davis", 25.6, 10.5, 2.0, hasrc="2026-11-14T19:10Z"),
    slate_row("2026-11-15", "8:00 PM ET", "ATL", "MIL", "7-6", "1-12", "0022600243",
              "Jalen Johnson", 20.0, 8.8, 7.5, "Tyler Herro", 21.6, 4.1, 4.3, hasrc="2026-11-14T19:10Z"),
    slate_row("2026-11-15", "9:00 PM ET", "OKC", "SAC", "8-5", "1-11", "0022600244",
              "Shai Gilgeous-Alexander", 30.5, 4.2, 4.5, "Darius Acuff Jr.", 25.4, 3.8, 7.2,
              hasrc="2026-11-14T19:10Z"),
    # ---- 2026-11-16 (8 games), read 18:58Z
    slate_row("2026-11-16", "7:00 PM ET", "ORL", "BOS", "5-7", "10-2", "0022600245",
              "Franz Wagner", 24.4, 6.8, 8.3, "Jayson Tatum", 26.3, 6.1, 7.5, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "7:00 PM ET", "CHI", "CLE", "2-9", "6-7", "0022600246",
              "Caleb Wilson", 18.9, 6.2, 1.9, "Donovan Mitchell", 23.0, 4.9, 5.6, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "7:00 PM ET", "MEM", "WAS", "8-4", "4-9", "0022600247",
              "Ty Jerome", 25.4, 3.4, 5.3, "Anthony Davis", 25.6, 10.5, 2.0, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "7:30 PM ET", "PHI", "BKN", "10-3", "3-8", "0022600248",
              "Tyrese Maxey", 26.7, 3.4, 5.5, "Julius Randle", 19.7, 6.5, 5.0, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "7:30 PM ET", "HOU", "MIA", "10-3", "6-6", "0022600249",
              "Alperen Sengun", 23.1, 9.6, 7.6, "Giannis Antetokounmpo", 28.5, 12.3, 4.9, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "8:00 PM ET", "POR", "MIN", "9-3", "9-3", "0022600250",
              "Deni Avdija", 23.9, 6.1, 6.3, "Anthony Edwards", 33.3, 4.8, 3.5, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "8:00 PM ET", "GSW", "NOP", "8-5", "4-9", "0022600251",
              "Stephen Curry", 27.8, 3.7, 3.9, "Zion Williamson", 21.8, 5.2, 2.8, hasrc="2026-11-14T18:58Z"),
    slate_row("2026-11-16", "9:00 PM ET", "PHX", "DEN", "5-6", "6-4", "0022600252",
              "Devin Booker", 25.5, 2.5, 5.0, "Nikola Jokić", 23.5, 10.8, 9.0, hasrc="2026-11-14T18:58Z"),
    # ---- 2026-11-17 (5 games), read 19:03Z
    slate_row("2026-11-17", "7:30 PM ET", "NYK", "TOR", "6-6", "5-7", "0022600253",
              "Karl-Anthony Towns", 21.1, 13.7, 3.7, "RJ Barrett", 21.3, 6.7, 4.1, hasrc="2026-11-14T19:03Z"),
    slate_row("2026-11-17", "8:00 PM ET", "POR", "MIN", "9-3", "9-3", "0022600254",
              "Deni Avdija", 23.9, 6.1, 6.3, "LaMelo Ball", 18.6, 3.3, 6.3, hasrc="2026-11-14T19:03Z"),
    slate_row("2026-11-17", "8:00 PM ET", "DET", "SAS", "8-3", "11-2", "0022600255",
              "Cade Cunningham", 25.0, 5.2, 7.9, "Victor Wembanyama", 28.8, 11.7, 3.1, hasrc="2026-11-14T19:03Z"),
    slate_row("2026-11-17", "10:30 PM ET", "UTA", "LAC", "1-12", "3-8", "0022600257",
              "Keyonte George", 20.9, 4.5, 6.5, "Darius Garland", 20.7, 2.0, 6.9, hasrc="2026-11-14T19:03Z"),
    slate_row("2026-11-17", "11:00 PM ET", "CHA", "LAL", "4-8", "11-2", "0022600256",
              "Naz Reid", 17.3, 8.5, 2.2, "Luka Doncic", 38.6, 7.5, 7.6, hasrc="2026-11-14T19:03Z"),
]

# ---------------------------------------------------------------------------
# Standings: NBA.com 2026-27 Regular Season Standings, read 18:56Z.
# (team, w, l, win_pct, gb, conf, div, home, road, last10, streak)
# ---------------------------------------------------------------------------
STANDINGS = [
    ("BOS", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "9-1", "W 5"),
    ("PHI", 10, 3, ".769", "0.5", "10-3", "3-1", "5-2", "5-1", "7-3", "W 1"),
    ("DET", 8, 3, ".727", "1.5", "8-2", "0-0", "3-2", "5-1", "7-3", "W 2"),
    ("ATL", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "5-5", "L 2"),
    ("MIA", 6, 6, ".500", "4", "3-2", "1-1", "2-3", "4-3", "6-4", "W 3"),
    ("NYK", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "6-4", "L 2"),
    ("CLE", 6, 7, ".462", "4.5", "5-5", "1-0", "4-2", "2-5", "4-6", "L 1"),
    ("TOR", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "3-7", "L 3"),
    ("ORL", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "5-5", "W 3"),
    ("IND", 5, 8, ".385", "5.5", "3-5", "0-1", "2-4", "3-3", "3-7", "W 2"),
    ("CHA", 4, 8, ".333", "6", "4-7", "2-2", "3-4", "1-4", "3-7", "L 1"),
    ("WAS", 4, 9, ".308", "6.5", "4-8", "2-3", "2-3", "2-6", "2-8", "L 6"),
    ("BKN", 3, 8, ".273", "6.5", "2-7", "0-2", "1-3", "2-5", "3-7", "W 1"),
    ("CHI", 2, 9, ".182", "7.5", "2-8", "1-0", "1-4", "1-5", "2-8", "W 1"),
    ("MIL", 1, 12, ".077", "9.5", "1-9", "1-2", "1-6", "0-6", "1-9", "L 9"),
    ("SAS", 11, 2, ".846", "--", "10-2", "2-1", "5-2", "6-0", "10-0", "W 11"),
    ("LAL", 11, 2, ".846", "--", "6-2", "4-1", "5-1", "6-1", "8-2", "W 7"),
    ("HOU", 10, 3, ".769", "1", "6-3", "2-1", "7-1", "3-2", "7-3", "W 3"),
    ("POR", 9, 3, ".750", "1.5", "9-3", "4-0", "3-2", "6-1", "7-3", "W 3"),
    ("MIN", 9, 3, ".750", "1.5", "5-2", "1-0", "5-1", "4-2", "7-3", "W 5"),
    ("MEM", 8, 4, ".667", "2.5", "7-3", "1-1", "2-4", "6-0", "6-4", "W 1"),
    ("GSW", 8, 5, ".615", "3", "6-5", "3-2", "6-1", "2-4", "8-2", "L 2"),
    ("OKC", 8, 5, ".615", "3", "5-5", "1-2", "5-0", "3-5", "5-5", "L 3"),
    ("DEN", 6, 4, ".600", "3.5", "4-4", "0-2", "2-2", "3-2", "6-4", "W 1"),
    ("DAL", 7, 5, ".583", "3.5", "3-5", "1-3", "5-2", "2-3", "6-4", "L 1"),
    ("PHX", 5, 6, ".455", "5", "3-6", "2-1", "5-3", "0-3", "5-5", "W 2"),
    ("NOP", 4, 9, ".308", "7", "3-7", "1-1", "3-5", "1-4", "4-6", "L 5"),
    ("LAC", 3, 8, ".273", "7", "3-6", "1-4", "3-3", "0-5", "2-8", "W 1"),
    ("SAC", 1, 11, ".083", "9.5", "1-9", "0-2", "0-7", "1-4", "1-9", "L 5"),
    # Utah is the last row of the Western table. The first fetched chunk of the
    # standings page ended before it could be read, so this row comes from the
    # second chunk of the same page (read 19:14Z) and was cross-read against the
    # official 11/15 SAS@UTA game card, which also displayed "1-12".
    ("UTA", 1, 12, ".077", "10", "1-10", "0-2", "1-6", "0-6", "0-10", "L 11"),
]

FIELDS = ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason", "attribution"]
STANDINGS_COLS = ["team", "w", "l", "win_pct", "gb", "conf", "div", "home", "road", "last10", "streak"]


def rows(block):
    return [dict(zip(FIELDS, r)) for r in block]


def main():
    os.makedirs(OUT, exist_ok=True)
    hdr = {
        "captured_by_session": "arena/95c1cb23-nba1",
        "captured_utc_range": "2026-11-14T18:38Z to 2026-11-14T19:05Z",
        "method": "Manual verbatim transcription from the official document named in "
                  "source_url. No third-party source, no inference, no fill-in.",
    }
    for name, report, src, block in (
        ("injury_2026-11-14_1330PM.json", "NBA Official Injury Report, 11/14/26 01:30 PM ET edition", SRC_1330, E_1330),
        ("injury_2026-11-14_0415AM.json", "NBA Official Injury Report, 11/14/26 04:15 AM ET edition", SRC_0415, E_0415),
    ):
        doc = dict(hdr)
        doc.update({
            "report": report,
            "source_url": src,
            "edition_index_url": SRC_HUB,
            "note": "The 01:30 PM ET link is the last one the hub listed when it was read at "
                    "18:44Z; the hub updates on a continual basis, so a newer edition may exist "
                    "by the time this file is read. Rows for clubs that had not filed are recorded "
                    "as NOT YET SUBMITTED with player null, exactly as printed.",
            "cols": FIELDS,
            "rows": rows(block),
        })
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")

    slate_doc = dict(hdr)
    slate_doc.update({
        "source_name": "NBA.com Games & Scores (official)",
        "source_urls": [G + d for d in ("2026-11-14", "2026-11-15", "2026-11-16", "2026-11-17")],
        "calendar_block_check": "The official month calendar printed on every one of those four "
                                "pages reads 14 -> 5 GAMES, 15 -> 9 GAMES, 16 -> 8 GAMES, 17 -> 5 GAMES. "
                                "The game cards read below contain 5, 9, 8 and 5 games respectively, so "
                                "the count on each page agrees with the league's own calendar block.",
        "reading_note": "On an NBA.com game card the first club listed is the AWAY team and the second "
                        "is the HOME team; confirmed independently by the URL pattern "
                        "nba.com/game/<away>-vs-<home>-<game_id>.",
        "leader_note": "The Season Leaders widget is a season-average read-out, not an availability "
                       "statement. The 11/16 card for POR@MIN lists Anthony Edwards, who the 11/14 "
                       "1:30 PM ET report rules Out - the widget is not injury-aware and must never be "
                       "read as a probable-lineup signal.",
        "games": SLATE,
    })
    with open(os.path.join(OUT, "slate_2026-11-14_to_17.json"), "w", encoding="utf-8") as fh:
        json.dump(slate_doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    st_doc = dict(hdr)
    st_doc.update({
        "source_name": "NBA.com 2026-27 Regular Season Standings (official)",
        "source_url": "https://www.nba.com/standings",
        "cols": ["team", "w", "l", "win_pct", "gb", "conf", "div", "home", "road", "last10", "streak"],
        "rows": [dict(zip(STANDINGS_COLS, r)) for r in STANDINGS],
        "note": "Records are as displayed at 18:56Z on 2026-11-14 (Utah read at 19:14Z from the "
                "second chunk of the same page), i.e. after the 2026-11-13 slate went final and "
                "before any 2026-11-14 game tips. The page also publishes Neutral and OT split "
                "columns, which are not transcribed here; the columns named in cols are the only "
                "ones claimed.",
    })
    with open(os.path.join(OUT, "standings_2026-11-14.json"), "w", encoding="utf-8") as fh:
        json.dump(st_doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("wrote 4 capture files to", os.path.relpath(OUT, ROOT))
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print("  %-40s %6d bytes" % (f, os.path.getsize(p)))


if __name__ == "__main__":
    main()
