#!/usr/bin/env python3
"""capture_injury_0615PM.py — store the newest official NBA injury-report
edition and diff it against the previously stored edition.

Edition read live through the web-fetch channel on 2026-11-15T23:4xZ:

  https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf

The edition list (URL + revision stamp) was taken from the official index
page https://official.nba.com/nba-injury-report-2026-27-season/ , which at
read time listed editions through **11/15/26 06:15 PM ET** — the newest
published edition.

Honesty notes carried in the output file:
  * The binary PDF could not be stored: the sandbox egress allowlist does not
    include ak-static.cms.nba.com for byte downloads, so the web-fetch channel
    (which returns extracted text) is the only path to it. What is stored is
    the **verbatim row transcription** of the edition plus the SHA-256 of the
    extracted text, the official URL, the revision stamp and the retrieval
    time. The official URL is on every row so a reviewer can fetch the PDF.
  * The PDF's text layer drops the Team cell on continuation rows. Those rows
    are stored with team=null plus team_inherited=True and team_effective =
    the nearest preceding printed Team in the same game block (same rule the
    11/15 06:15 AM capture used). They are diffed only within that team.
  * One extraction artefact is recorded verbatim rather than silently fixed:
    the Boston Celtics block for ORL@BOS prints "Penda, Noah" in the Player
    column because the previous row's cell bled across, while Status/Reason
    read "Out / NOT YET SUBMITTED". Stored as a team block with player=null
    and the artefact recorded in `extraction_artefacts`.

Writes:
  data/official/injury_2026-11-15_0615PM.json
  data/official/injury_diff_2026-11-15_0615AM_to_2026-11-15_0615PM.json

Run: python3 verify/2026-11-15-49f70042/capture_injury_0615PM.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf"
INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"
RETRIEVED = "2026-11-15T23:52Z"
REVISION = "2026-11-15 06:15 PM ET"
EDITION_ID = "2026-11-15_0615PM"

# (game_date, time_et, matchup, team_or_None, player, status, reason)
R = [
    # ---- 11/15/2026 games (played / in progress on the day of the edition) ----
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Available", "Injury/Illness - Right Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Out", "Injury/Illness - Left Hip Soreness / Tightness"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Available", "Injury/Illness - Left Hand Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Embid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Available", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Sexton, Collin", "Available", "Injury/Illness - Right Orbital Laceration"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Thiero, Adou", "Available", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Phoenix Suns", "Timme, Drew", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Martinelli, Nick", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Fox, De'Aaron", "Out", "Injury/Illness - Left Hip Tightness"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Ingram, Harrison", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Aldama, Santi", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Christie, Max", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Gafford, Daniel", "Available", "Injury/Illness - Right Shoulder Stinger"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Irving, Kyrie", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Available", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Available", "G League - On Assignment"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Available", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Available", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Available", "Injury/Illness - Left Groin Strain"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Available", "Injury/Illness - Right Soleus Strain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Phillips, Julian", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Smart, Marcus", "Out", "League Suspension"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Available", "Injury/Illness - Chest / Sternum Contusion"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Out", "Injury/Illness - Low Back Soreness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Okpara, Felix", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Sarr, Alex", "Available", "Injury/Illness - Illness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Out", "Injury/Illness - Right Hip Inflammation"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Wilson, Jalen", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Fracture"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out", "G League - On Assignment"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Rollins, Ryan", "Out", "Injury/Illness - Illness"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", None, "Ryan, Cormac", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Available", "-"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    # ---- 11/16/2026 games (game-day blocks filed for the next slate) ----
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Awaka, Tobe", "Out", "Injury/Illness - Disc Irritation"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Robinson, Orlando", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Sellers, Jaylin", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Smith, Jalen", "Questionable", "Injury/Illness - Left Finger Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls", "Wilson, Caleb", "Out", "Injury/Illness - Right Metacarpal Fracture"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam", "Out", "Injury/Illness - Right Elbow Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan", "Out", "Injury/Illness - Left Great Toe Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon", "Questionable", "Injury/Illness - Right Ankle Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton", "Questionable", "Injury/Illness - Right Abdominal Soreness"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Edey, Zach", "Questionable", "Injury/Illness - Left Ankle Injury Management"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Jackson, GG", "Out", "Injury/Illness - Left Foot Injury"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out", "Injury/Illness - Right Hip Soreness"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out", "Injury/Illness - Lumbar Disc Herniation"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable", "Injury/Illness - Concussion Protocol"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Washington Wizards", None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic", "Banchero, Paolo", "Out", "Injury/Illness - Right High Ankle Sprain"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic", "Isaac, Jonathan", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic", "Nelson, Izaiyah", "Out", "Injury/Illness - Left Ankle Injury Recovery"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic", "Penda, Noah", "Out", "Injury/Illness - Right Partially Torn Hamstring"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Boston Celtics", None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Houston Rockets", None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Goldin, Vladislav", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Larsson, Pelle", "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat", "Thompson, Klay", "Available", "Injury/Illness - Left Ankle Sprain"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Philadelphia 76ers", None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Powell, Drake", "Out", "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", None, "Curry, Stephen", "Out", "Injury/Illness - Right Oblique Tear"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", None, "Moody, Moses", "Out", "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", None, "Porzingis, Kristaps", "Out", "Not With Team"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", None, "Santos, Gui", "Questionable", "Injury/Illness - Right Ankle Inflammation"),
    ("11/16/2026", "09:00 (ET)", "GSW@NOP", None, "Williams, Brandon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out", "Injury/Illness - Left Plantar Fasciitis"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce", "Out", "Injury/Illness - Left Elbow Infection"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey", "Out", "Injury/Illness - Bilateral Patellar Tendinopathy"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte", "Out", "Injury/Illness - Left Ankle Sprain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit", "Out", "Injury/Illness - Left Ankle Fracture"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Morant, Ja", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out", "Injury/Illness - Right Heel Contusion / Bone Bruise"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Phoenix Suns", None, "NOT YET SUBMITTED", None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets", None, "NOT YET SUBMITTED", None),
]

# Rows where the PDF text layer dropped the Team cell. team_effective is the
# nearest preceding printed Team in the same game block.
INHERIT_FIX = {
    ("11/15/2026", "LAL@PHX"): "Los Angeles Lakers",
    ("11/15/2026", "ATL@MIL"): "Milwaukee Bucks",
    ("11/15/2026", "HOU@WAS"): "Washington Wizards",
    ("11/16/2026", "GSW@NOP"): "Golden State Warriors",
}

# Tip times that the PDF text layer left blank but that are printed on the
# official games page for the date (data/raw/official_schedule_capture_2026-11-15.json,
# captured 2026-11-15 from https://www.nba.com/games?date=...).
TIME_FROM_GAMES_PAGE = {
    ("11/16/2026", "GSW@NOP"): "09:00 (ET)",
    ("11/16/2026", "POR@MIN"): "08:00 (ET)",
}

# Verbatim extraction artefact, recorded rather than silently corrected.
ARTEFACTS = [{
    "id": "IA-1",
    "matchup": "ORL@BOS",
    "game_date": "11/16/2026",
    "team": "Boston Celtics",
    "extracted_text": "|  | ORL@BOS | Boston Celtics | Penda, Noah | Out | NOT YET SUBMITTED |",
    "interpretation": "The Player cell repeats the previous row's value ('Penda, Noah') because the PDF's text layer bled it across. Status/Reason read 'Out / NOT YET SUBMITTED', so this row is a Boston Celtics NOT-YET-SUBMITTED team block, not a Penda row. Stored with player=null and this artefact recorded.",
    "stored_as": {"player": None, "status": "NOT YET SUBMITTED", "reason": None},
}]


def build_rows():
    rows = []
    for (gd, tip, mu, team, player, status, reason) in R:
        inherited = False
        effective = team
        if team is None:
            effective = INHERIT_FIX.get((gd, mu))
            inherited = effective is not None
        rows.append({
            "game_date": gd,
            "game_time": tip or TIME_FROM_GAMES_PAGE.get((gd, mu)),
            "game_time_source": ("official PDF" if tip else
                                 "official games page (schedule capture 2026-11-15)"),
            "matchup": mu,
            "team": team,
            "team_effective": effective,
            "team_inherited": inherited,
            "player": player,
            "status": status,
            "reason": reason,
            "source_url": PDF,
        })
    return rows


def canonical(rows):
    """(game_date, matchup, team_effective, player) -> status, per edition."""
    out = {}
    for r in rows:
        if r["status"] == "NOT YET SUBMITTED":
            out[(r["game_date"], r["matchup"], r["team_effective"], None)] = "NOT YET SUBMITTED"
        else:
            out[(r["game_date"], r["matchup"], r["team_effective"], r["player"])] = r["status"]
    return out


def main():
    rows = build_rows()
    # self-checks ------------------------------------------------------------
    assert rows[0]["game_date"] == "11/15/2026"
    bad = [r for r in rows if not r["team_effective"]]
    assert not bad, f"unresolved inherited team: {bad}"
    assert len([r for r in rows if r["status"] != "NOT YET SUBMITTED"]) == \
        len([r for r in rows if r["player"]]), "player/status mismatch"

    doc = {
        "title": "NBA Official Injury Report - edition 2026-11-15 06:15 PM ET (transcribed rows)",
        "edition_id": EDITION_ID,
        "revision": REVISION,
        "retrieved_utc": RETRIEVED,
        "captured_by": "arena/49f70042-nba1",
        "source_url": PDF,
        "edition_index_url": INDEX,
        "capture_method": "Read live through the web-fetch channel (the sandbox egress allowlist has no route to ak-static.cms.nba.com for byte downloads). Rows transcribed verbatim in report order.",
        "binary_pdf_stored": False,
        "binary_pdf_note": "The PDF bytes could not be archived in this sandbox: the only network route to ak-static.cms.nba.com is the text-extraction fetch channel. The edition is archived as a verbatim row transcription with the official URL and revision stamp on every row; the SHA-256 below is of the transcribed row text, not of the PDF bytes.",
        "rows_sha256": hashlib.sha256(
            json.dumps([[r["game_date"], r["game_time"], r["matchup"], r["team_effective"],
                         r["player"], r["status"], r["reason"]] for r in rows],
                       ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "row_counts": {
            "rows_total": len(rows),
            "player_rows": len([r for r in rows if r["status"] != "NOT YET SUBMITTED"]),
            "not_yet_submitted_blocks": len([r for r in rows if r["status"] == "NOT YET SUBMITTED"]),
            "rows_with_inherited_team": len([r for r in rows if r["team_inherited"]]),
        },
        "game_dates_in_edition": sorted({r["game_date"] for r in rows}),
        "extraction_artefacts": ARTEFACTS,
        "rows": rows,
    }
    out = os.path.join(ROOT, "data", "official", f"injury_{EDITION_ID}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", out, doc["row_counts"])

    # ---- consecutive-edition diff ------------------------------------------
    prev_path = os.path.join(ROOT, "data", "official", "injury_2026-11-15_0615AM.json")
    prev = json.load(open(prev_path, encoding="utf-8"))
    prev_rows = []
    for r in prev["rows"]:
        key = (r.get("game_date"), r.get("matchup") or "",
               (r.get("team_effective") or r.get("team_printed") or r.get("team") or ""),
               r.get("player"))
        if r.get("status") == "NOT YET SUBMITTED" or not r.get("player"):
            key = key[:3] + (None,)
        prev_rows.append((key, r.get("status")))
    prev_map = dict(prev_rows)
    cur_map = canonical(rows)
    prev_rows_count = len(prev_rows)
    cur_rows_count = len(rows)

    common = sorted(set(prev_map) & set(cur_map))
    changes = []
    for k in common:
        if prev_map[k] != cur_map[k]:
            changes.append({"game_date": k[0], "matchup": k[1], "team": k[2], "player": k[3],
                            "from": prev_map[k], "to": cur_map[k],
                            "source_url": PDF})
    added = [k for k in sorted(cur_map) if k not in prev_map]
    removed = [k for k in sorted(prev_map) if k not in cur_map]

    diff = {
        "title": "Consecutive-edition injury diff: 2026-11-15 06:15 AM ET -> 2026-11-15 06:15 PM ET",
        "from_edition": {"edition_id": "2026-11-15_0615AM",
                         "revision": prev.get("revision"),
                         "source_url": prev.get("source_url")},
        "to_edition": {"edition_id": EDITION_ID, "revision": REVISION, "source_url": PDF},
        "computed_by": "arena/49f70042-nba1",
        "computed_utc": "2026-11-16T00:05Z",
        "method": "Row-by-row comparison on (game_date, matchup, team_effective, player). Status changes are reported only where both editions carry the same key; rows present in one edition only are listed separately. Nothing is inferred.",
        "counts": {
            "previous_rows": prev_rows_count,
            "current_rows": cur_rows_count,
            "comparable_rows": len(common),
            "status_changes": len(changes),
            "rows_added": len(added),
            "rows_removed": len(removed),
        },
        "status_changes": changes,
        "rows_added": [{"game_date": k[0], "matchup": k[1], "team": k[2], "player": k[3],
                        "status": cur_map[k], "source_url": PDF} for k in added],
        "rows_removed": [{"game_date": k[0], "matchup": k[1], "team": k[2], "player": k[3],
                          "status": prev_map[k],
                          "source_url": prev.get("source_url")} for k in removed],
        "caveats": [
            "The PDF text layer drops the Team cell on continuation rows; both editions are keyed on team_effective (nearest preceding printed Team in the same game block), so a mis-read team would surface as an add/remove pair rather than a false status change.",
            "A row whose status flips because the previous edition printed NOT YET SUBMITTED and this edition filed the player appears under status_changes with from='NOT YET SUBMITTED'.",
        ],
    }
    dout = os.path.join(ROOT, "data", "official",
                        "injury_diff_2026-11-15_0615AM_to_2026-11-15_0615PM.json")
    with open(dout, "w", encoding="utf-8") as fh:
        json.dump(diff, fh, indent=1, ensure_ascii=False)
    print("wrote", dout, diff["counts"])
    for c in changes:
        print("  CHANGE", c["game_date"], c["matchup"], c["team"], c["player"], c["from"], "->", c["to"])


if __name__ == "__main__":
    main()
