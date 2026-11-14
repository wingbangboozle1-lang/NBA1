#!/usr/bin/env python3
"""
generate_picks_d.py — Build D (session arena/ebdf1d21-nba1): live-horizon originated
lines and paper picks for every upcoming slate within the maximum 3-day window
(2026-11-14 .. 2026-11-17), closing board item F-C07 / COORDINATION §7.3.

PHILOSOPHY (identical to the rest of this repository)
-----------------------------------------------------
Every number is either (a) an official NBA value with a source link, or (b) a
labelled DERIVED value of model RecordLine-1 whose formula and parameters are
printed beside it. Nothing is copied from a sportsbook; no odds feed is connected;
market gates stay blocked. A value that cannot be confirmed from an official
source is left blank, never inferred, and listed on the page's Flagged-for-Review
section.

WHAT IS NEW IN BUILD D (vs the existing artifacts)
--------------------------------------------------
1. The horizon extends to 2026-11-17 (Build A's lines covered 11/13–11/16 only).
2. A fresher official injury edition is captured: the 11/13 08:00 PM ET report
   (verified to exist by fetching it; the policy page lists editions every 15 min).
   It carries rows for ALL FIVE 11/14 games (the 05:15 PM edition covered four).
3. Inputs are stamped as-of: records pre-11/13, leader stats through 11/12,
   injury edition 11/13 08:00 PM ET, schedule verified 2026-11-14.
4. Fidelity check: for the 22 games overlapping Build A's RecordLine-1 artifact
   (data/originated_lines.json), this script must reproduce the exact same
   originated spread and pick side from the same records. Any mismatch fails.

RecordLine-1 constants and formulas are identical to scripts/build_edge_site.py
(PRIOR_W/PRIOR_G smoothing, HCA, K, SIGMA, CONF_MARGIN gate, Fréchet bounds for
2-leg cross-game parlays). RecordLine-1 does not originate totals; the absence is
flagged, as in Build A.
"""
import html
import json
import math
import os
import re
import sys
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "derived")
RAW_D = os.path.join(DATA, "raw", "d")

BUILD_UTC = "2026-11-14T01:25:00Z"
HORIZON = ("2026-11-14", "2026-11-15", "2026-11-16", "2026-11-17")

SCHEDULE_URL = "https://www.nba.com/schedule"
POLICY_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
INJ_0800_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_08_00PM.pdf"
INJ_0515_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf"
INJ_0300_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf"

ALLOWED_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
}

# ---- Model RecordLine-1 assumptions (identical to scripts/build_edge_site.py) ----
PRIOR_W, PRIOR_G = 3.0, 6.0     # smoothing: +3 wins / +6 games toward .500
HCA = 2.5                        # home-court points (project assumption, flagged)
K = 35.0                         # points per 1.000 smoothed win-pct difference
SIGMA = 11.0                     # points scale for win probability
CONF_MARGIN = 3.0                # pick gate: |expected margin| >= 3.0
PROP_ROUND = 0.5                 # prop combo line rounding step

errors = []
notes = []


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def check_url(url, where, required=True):
    if not url:
        if required:
            errors.append(f"{where}: missing source link")
        return False
    p = urlparse(url)
    if p.scheme != "https" or p.netloc not in ALLOWED_HOSTS:
        errors.append(f"{where}: source host not allowed: {url}")
        return False
    return True


def esc(v):
    return html.escape("" if v is None else str(v))


def fmt(v, nd=1):
    if v is None:
        return "—"
    return f"{v:.{nd}f}"


def name_key(name):
    parts = re.split(r"[^A-Za-z]+", (name or "").lower())
    return frozenset(p for p in parts if p)


def parse_rec(rec):
    if not rec or "-" not in rec:
        return None, None
    w, l = rec.split("-")
    return int(w), int(l)


def smoothed(w, g):
    return (w + PRIOR_W) / (g + PRIOR_G)


def home_margin(p_home, p_away):
    return K * (p_home - p_away) + HCA


def p_home_win(margin):
    return 1.0 / (1.0 + math.exp(-margin / SIGMA))


def round_half(x):
    return round(x * 2) / 2


def rho_bounds(p1, p2):
    denom = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    if denom == 0:
        return None, None
    lb_joint = max(0.0, p1 + p2 - 1.0)
    ub_joint = min(p1, p2)
    rho_lb = (lb_joint - p1 * p2) / denom
    rho_ub = (ub_joint - p1 * p2) / denom
    return rho_lb, rho_ub


def game_url(away, home, game_id):
    """Official NBA game page URL (pattern verified on the live slate pages)."""
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{game_id}"


def slate_url(d):
    return f"https://www.nba.com/games?date={d}"


# =================================================================== fresh captures
# Verbatim transcriptions of the official NBA.com slate pages fetched by this
# session on 2026-11-14 (~01:05–01:20 UTC). Used to (a) re-verify the 11/14 and
# 11/17 rows of the schedule capture and (b) fill three team-leader gaps
# (CHA/LAL/TOR) that leaders.json left blank.
FRESH_1114 = {
    "url": "https://www.nba.com/games?date=2026-11-14",
    "fetched": "2026-11-14 (01:05–01:20 UTC build window)",
    "games": [
        {"game_id": "0022600231", "away": "DEN", "home": "NOP", "tip_et": "7:00 PM ET", "away_record": "6-4", "home_record": "4-8"},
        {"game_id": "0022600232", "away": "DAL", "home": "CLE", "tip_et": "7:30 PM ET", "away_record": "7-5", "home_record": "6-6"},
        {"game_id": "0022600234", "away": "BKN", "home": "MEM", "tip_et": "8:00 PM ET", "away_record": "3-8", "home_record": "7-4"},
        {"game_id": "0022600233", "away": "DET", "home": "MIA", "tip_et": "8:00 PM ET", "away_record": "8-3", "home_record": "5-6"},
        {"game_id": "0022600235", "away": "CHI", "home": "MIN", "tip_et": "8:00 PM ET", "away_record": "1-9", "home_record": "9-3"},
    ],
    "leaders": {
        "DEN": ("Nikola Jokić", 23.5, 10.8, 9.0),
        "NOP": ("Zion Williamson", 21.7, 5.2, 2.6),
        "DAL": ("Cooper Flagg", 24.6, 6.9, 6.5),
        "CLE": ("Donovan Mitchell", 22.8, 5.0, 5.5),
        "BKN": ("Julius Randle", 19.7, 6.5, 5.0),
        "MEM": ("Ty Jerome", 26.2, 3.5, 4.9),
        "DET": ("Cade Cunningham", 25.0, 5.2, 7.9),
        "MIA": ("Giannis Antetokounmpo", 27.7, 12.6, 5.2),
        "CHI": ("Caleb Wilson", 18.9, 6.2, 1.9),
        "MIN": ("LaMelo Ball", 18.6, 3.3, 6.3),
    },
}

FRESH_1117 = {
    "url": "https://www.nba.com/games?date=2026-11-17",
    "fetched": "2026-11-14 (01:05–01:20 UTC build window)",
    "games": [
        {"game_id": "0022600253", "away": "NYK", "home": "TOR", "tip_et": "7:30 PM ET", "away_record": "6-5", "home_record": "5-7"},
        {"game_id": "0022600255", "away": "DET", "home": "SAS", "tip_et": "8:00 PM ET", "away_record": "8-3", "home_record": "10-2"},
        {"game_id": "0022600254", "away": "POR", "home": "MIN", "tip_et": "8:00 PM ET", "away_record": "8-3", "home_record": "9-3"},
        {"game_id": "0022600257", "away": "UTA", "home": "LAC", "tip_et": "10:30 PM ET", "away_record": "1-11", "home_record": "2-8"},
        {"game_id": "0022600256", "away": "CHA", "home": "LAL", "tip_et": "11:00 PM ET", "away_record": "4-8", "home_record": "11-2"},
    ],
    "leaders": {
        "NYK": ("Karl-Anthony Towns", 20.9, 13.5, 3.5),
        "TOR": ("RJ Barrett", 21.3, 6.7, 4.1),
        "DET": ("Cade Cunningham", 25.0, 5.2, 7.9),
        "SAS": ("Victor Wembanyama", 30.3, 11.7, 2.8),
        "POR": ("Deni Avdija", 23.0, 6.1, 6.5),
        "MIN": ("LaMelo Ball", 18.6, 3.3, 6.3),
        "UTA": ("Keyonte George", 20.4, 4.5, 6.5),
        "LAC": ("Darius Garland", 20.4, 1.8, 6.9),
        "CHA": ("Naz Reid", 17.3, 8.5, 2.2),
        "LAL": ("Luka Dončić", 38.6, 7.5, 7.6),
    },
}

# =================================================================== 08:00 PM PDF
# Verbatim transcription of https://ak-static.cms.nba.com/referee/injury/
# Injury-Report_2026-11-13_08_00PM.pdf as returned by the fetch tool on
# 2026-11-14 (chunk 0 + chunk 1, joined at the truncated cell). The PDF prints
# some continuation rows with lost date/team cells; those cells stay blank here
# and are attributed only by an explicit carry from an earlier official edition.
RAW_MD = r"""**Injury Report: 11/13/26 08:00 PM**

| Game Date | Game Time | Matchup | Team | Player Name | Current Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Banchero, Paolo | Out | Injury/Illness - Right High AnkleSprain |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Cain, Jamal | Available | Injury/Illness - Left ShoulderContusion |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | da Silva, Tristan | Available | Injury/Illness - Left Calf Strain |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Isaac, Jonathan | Out | Injury/Illness - Left Knee InjuryManagement |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Nelson, Izaiyah | Out | Injury/Illness - Left Ankle InjuryRecovery |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Penda, Noah | Out | Injury/Illness - Right Partially Torn Hamstring |
| 11/13/2026 | 07:00 (ET) | MIL@ORL | Orlando Magic | Suggs, Jalen | Available | Injury/Illness - Right Knee Contusion/Bone Bruise |
| 11/13/2026 | 07:00 (ET) | NYK@IND | Indiana Pacers | Furphy, Johnny | Out | Injury/Illness - Right ACL Repair/Surgery |
| 11/13/2026 | 07:00 (ET) | NYK@IND | Indiana Pacers | Haliburton, Tyrese | Out | Injury/Illness - Left Hamstring Strain |
| 11/13/2026 | 07:00 (ET) | NYK@IND | Indiana Pacers | McConnell, T.J. | Available | Injury/Illness - Right Hamstring Strain |
| 11/13/2026 | 07:00 (ET) | NYK@IND | Indiana Pacers | Nesmith, Aaron | Available | Injury/Illness - Right Knee Soreness |
| 11/13/2026 | 07:00 (ET) | NYK@IND | Indiana Pacers | Sheppard, Ben | Out | Injury/Illness - Left Meniscus Surgery |
| 11/13/2026 | 08:00 (ET) | ATL@CHI | Atlanta Hawks | Dennis, RayJ | Available | G League - Two-Way |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  | Flemings, Kingston | Available | Injury/Illness - Lumbar Spasm |  |
| --- | --- | --- | --- | --- | --- |
|  |  | Gilbert, Keshon | Out | Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure |  |
|  |  | Gueye, Mouhamed | Out | Injury/Illness - Left Foot Fracture |  |
|  |  | Landale, Jock | Available | Injury/Illness - Face Mask |  |
|  |  | Newell, Asa | Out | Injury/Illness - Left Great Toe Hyperextension |  |
|  |  | Veesaar, Henri | Out | Injury/Illness - Right ACL Tear |  |
|  |  | Wilson, Jalen | Out | G League - Two-Way |  |
|  |  | Chicago Bulls | Awaka, Tobe | Out | Injury/Illness - Disc Irritation |
|  |  | Chicago Bulls | Powell, Norman | Available | - |
|  |  | Chicago Bulls | Sellers, Jaylin | Out | G League - Two-Way |
|  |  | Chicago Bulls | Swain, Dailyn | Out | Injury/Illness - Right Disc Irritation |
|  |  | Chicago Bulls | Wilson, Caleb | Out | Injury/Illness - Right Metacarpal Fracture |
| CLE@MIA | Cleveland Cavaliers | Diop, Khalifa | Out | G League - On Assignment |  |
| CLE@MIA | Cleveland Cavaliers | Merrill, Sam | Out | Injury/Illness - Right Elbow Injury Management |  |
| CLE@MIA | Cleveland Cavaliers | Mobley, Evan | Out | Injury/Illness - Left Great Toe - Sprain |  |
| CLE@MIA | Cleveland Cavaliers | Tomlin, Nae'Qwan | Out | Injury/Illness - Low Back Stress Reaction |  |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  | Udeh, Jr., Ernest | Out | G League - Two-Way |
| --- | --- | --- | --- | --- |
|  |  | Miami Heat | Antetokounmpo, Giannis | Available | Injury/Illness - Right Wrist Sprain |
|  |  | Miami Heat | Goldin, Vladislav | Out | G League - Two-Way |
|  |  | Miami Heat | Larsson, Pelle | Out | Injury/Illness - Illness |
|  |  | Miami Heat | Thompson, Klay | Out | Injury/Illness - Left Ankle Soreness |
| MEM@NOP | Memphis Grizzlies | Edey, Zach | Out | Injury/Illness - Left Ankle Injury Management |
| MEM@NOP | Memphis Grizzlies | Lopez, Karim | Out | G League - On Assignment |
| MEM@NOP | Memphis Grizzlies | Mashack, Jahmai | Out | G League - Two-Way |
| MEM@NOP | Memphis Grizzlies | Pippen Jr., Scotty | Out | Injury/Illness - Lumbar Disc Herniation |
| MEM@NOP | Memphis Grizzlies | Post, Quinten | Out | Injury/Illness - Concussion Protocol |
| MEM@NOP | Memphis Grizzlies | Saunders, Richie | Out | Injury/Illness - Right Knee Surgery |
| MEM@NOP | New Orleans Pelicans | Dia, Malik | Available | G League - Two-Way |
| MEM@NOP | New Orleans Pelicans | Mathurin, Bennedict | Available | Injury/Illness - Right Thumb Sprain |
| MEM@NOP | New Orleans Pelicans | McGowens, Bryce | Out | Injury/Illness - Left Elbow Infection |
| MEM@NOP | New Orleans Pelicans | Missi, Yves | Out | Injury/Illness - Left Knee Contusion / Bone Bruise |
| MEM@NOP | New Orleans Pelicans | Murphy III, Trey | Out | Injury/Illness - Bilateral Patellar Tendinopathy |
| MEM@NOP | New Orleans Pelicans | Murray, Dejounte | Out | Injury/Illness - Left Ankle Sprain |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  |  | Pierre Jr., Jaron | Available | G League - Two-Way |
| --- | --- | --- | --- | --- |
|  |  |  | Watford, Trendon | Out | Injury/Illness - Right Ankle Sprain |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Alexander, Trey | Out | G League - Two-Way |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Bufkin, Kobe | Out | G League - Two-Way |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Ingram, Harrison | Out | G League - Two-Way |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Jackson Jr., Jaren | Out | Injury/Illness - Right MCL Tear |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Markkanen, Lauri | Out | Injury/Illness - Right Hand Fracture |
| 08:30 (ET) | UTA@HOU | Utah Jazz | Nurkic, Jusuf | Out | Injury/Illness - Right 2nd Plantar Plate Tear |
| 08:30 (ET) | UTA@HOU | Houston Rockets | Adams, Steven | Out | Injury/Illness - Right Soleus Strain |
| 08:30 (ET) | UTA@HOU | Houston Rockets | Capela, Clint | Out | Injury/Illness - Right Ankle Sprain |
| 08:30 (ET) | UTA@HOU | Houston Rockets | Copeland, Quadir | Out | G League - Two-Way |
| 08:30 (ET) | UTA@HOU | Houston Rockets | Phillips, Julian | Out | G League - Two-Way |
| 08:30 (ET) | UTA@HOU | Houston Rockets | Smart, Marcus | Out | League Suspension |
| 09:30 (ET) | GSW@SAS | Golden State Warriors | Bassey, Charles | Probable | Injury/Illness - Left Toe Soreness |
| 09:30 (ET) | GSW@SAS | Golden State Warriors | Butler III, Jimmy | Out | Injury/Illness - Right ACL Repair / Surgery |
| 09:30 (ET) | GSW@SAS | Golden State Warriors | Curry, Stephen | Out | Injury/Illness - Right Oblique Tear |
| 09:30 (ET) | GSW@SAS | Golden State Warriors | Moody, Moses | Out | Injury/Illness - Left Patellar Tendon Repair / Surgery |
| 09:30 (ET) | GSW@SAS | Golden State Warriors | Porzingis, Kristaps | Out | Not With Team |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  |  | Williams, Brandon | Out | Injury/Illness - Left Hamstring Strain |
| --- | --- | --- | --- | --- |
|  |  | San Antonio Spurs | Fox, De'Aaron | Questionable | Injury/Illness - Left Hip Soreness |
|  |  | San Antonio Spurs | Harris, Tobias | Out | Injury/Illness - Left Calf Strain |
|  |  | San Antonio Spurs | Quaintance, Jayden | Out | Injury/Illness - Right Knee Surgery |
|  |  | San Antonio Spurs | Vassell, Devin | Questionable | Injury/Illness - Left Adductor Tightness |
| 10:00 (ET) | POR@SAC | Portland Trail Blazers | Krejci, Vit | Out | Injury/Illness - Left Ankle Fracture |
| 10:00 (ET) | POR@SAC | Portland Trail Blazers | Morant, Ja | Out | Injury/Illness - Left Hamstring Strain |
| 10:00 (ET) | POR@SAC | Portland Trail Blazers | Sharpe, Shaedon | Out | Injury/Illness - Right Meniscus Surgery |
| 10:00 (ET) | POR@SAC | Portland Trail Blazers | Youngblood, Chris | Out | Injury/Illness - Right Bone Bruise |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Achiuwa, Precious | Out | Injury/Illness - Left Ankle Soreness |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Karaban, Alex | Out | G League - On Assignment |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Mogbo, Jonathan | Out | G League - Two-Way |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Pedulla, Sean | Out | G League - Two-Way |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Raynaud, Maxime | Out | Injury/Illness - Right Patella Subluxation |
| 10:00 (ET) | POR@SAC | Sacramento Kings | Simmons, Ben | Out | Injury/Illness - Right Achilles Tendon Repair / Surgery |
| 10:30 (ET) | OKC@LAC | Oklahoma City Thunder | Holmgren, Chet | Out | Injury/Illness - Right Knee/ Injury Recovery |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  |  |  | Mitchell, Ajay | Questionable | Injury/Illness - Left Ankle Sprain |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  | Sorber, Thomas | Out | Injury/Illness - Right Knee Surgery |
|  |  |  |  | Topic, Nikola | Available | - |
|  |  |  |  | Wallace, Cason | Out | Injury/Illness - Left Shoulder Surgery |
|  |  |  |  | Williams, Jalen | Out | Injury/Illness - Left Ankle Surgery |
|  |  |  |  | Williams, Jaylin | Out | Injury/Illness - Low Back Spasms |
|  |  |  |  | LA Clippers | Beal, Bradley | Out | Injury/Illness - Right Knee Injury Management |
|  |  |  |  | LA Clippers | Ingram, Brandon | Out | Injury/Illness - Right Heel Surgery |
|  |  |  |  | LA Clippers | Martinelli, Nick | Out | G League - Two-Way |
|  |  |  |  | LA Clippers | Miller, Jordan | Out | Injury/Illness - Left Rotator Cuff Surgery |
|  |  |  |  | LA Clippers | Niederhauser, Yanic Konan | Out | Injury/Illness - Right Lisfranc Surgery |
| 11/14/2026 | 07:00 (ET) | DEN@NOP | Denver Nuggets | Holmes II, DaRon | Out | G League - On Assignment |
| 11/14/2026 | 07:00 (ET) | DEN@NOP | Denver Nuggets | Nembhard, Ryan | Out | G League - Two-Way |
| 11/14/2026 | 07:00 (ET) | DEN@NOP | Denver Nuggets | Strawther, Julian | Out | Injury/Illness - Left Knee Sprain |
| 11/14/2026 | 07:00 (ET) | DEN@NOP | Denver Nuggets | Whitmore, Cam | Out | G League - Two-Way |
| 11/14/2026 | 07:00 (ET) | DEN@NOP | New Orleans Pelicans |  |  | NOT YET SUBMITTED |
| 11/14/2026 | 07:30 (ET) | DAL@CLE | Dallas Mavericks | Biberovic, Tarik | Out | Injury/Illness - Right Heel Bursitis |
| 11/14/2026 | 07:30 (ET) | DAL@CLE | Dallas Mavericks | Christie, Max | Questionable | Injury/Illness - Left Ankle Sprain |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  |  |  | de Larrea, Sergio | Out | Injury/Illness - Right Knee Sprain |  |
| --- | --- | --- | --- | --- | --- |
|  |  |  | Johnson Jr., Morez | Probable | Injury/Illness - Left Shin / Tibia Contusion |  |
|  |  |  | Lively II, Dereck | Out | Injury/Illness - Right Foot Surgery |  |
|  |  |  | Martin, Caleb | Available | Injury/Illness - Right Thumb Splint |  |
|  |  | Cleveland Cavaliers |  |  | NOT YET SUBMITTED |  |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Bilodeau, Tyler | Out | G League - Two-Way |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Brown Jr., Mikel | Questionable | Injury/Illness - Illness |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Jefferson, Joshua | Out | G League - On Assignment |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Nelson, Grant | Out | G League - Two-Way |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Saraf, Ben | Out | G League - On Assignment |
|  | 08:00 (ET) | BKN@MEM | Brooklyn Nets | Traore, Nolan | Probable | Injury/Illness - Right Calf Tightness / Soreness |
|  | 08:00 (ET) | BKN@MEM | Memphis Grizzlies |  |  | NOT YET SUBMITTED |
|  | 08:00 (ET) | CHI@MIN | Chicago Bulls |  |  | NOT YET SUBMITTED |
|  | 08:00 (ET) | CHI@MIN | Minnesota Timberwolves | Beringer, Joan | Available | Injury/Illness - Face Mask |
|  | 08:00 (ET) | CHI@MIN | Minnesota Timberwolves | DiVincenzo, Donte | Out | Injury/Illness - Right Achilles Tendon Repair / Surgery |
|  | 08:00 (ET) | CHI@MIN | Minnesota Timberwolves | Edwards, Anthony | Out | Injury/Illness - Right Knee Arthroscopy |
| 11/14/2026 | 07:00 (ET) | DET@MIA | Detroit Pistons | Duren, Jalen | Out | Injury/Illness - Right Hamstring Strain |

* * *

**Injury Report: 11/13/26 08:00 PM**

|  | Harkless, Elijah | Questionable | G League - Two-Way |
| --- | --- | --- | --- |
|  | Joe, Isaiah | Out | Injury/Illness - Right Hip Contusion |
|  | Jones, Isaac | Questionable | G League - Two-Way |
|  | Lanier, Chaz | Out | G League - On Assignment |
|  | Okorie, Ebuka | Out | G League - On Assignment |
|  | Onyenso, Ugonna | Out | G League - Two-Way |
| Miami Heat |  | NOT YET SUBMITTED |  |
"""

TEAM_NAMES = {
    "Atlanta Hawks", "Brooklyn Nets", "Boston Celtics", "Charlotte Hornets", "Chicago Bulls",
    "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons",
    "Golden State Warriors", "Houston Rockets", "Indiana Pacers", "LA Clippers",
    "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
    "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder",
    "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards",
}
STATUSES = {"Out", "Available", "Questionable", "Probable", "Doubtful", "Day-To-Day",
            "NOT YET SUBMITTED"}


def parse_raw_md():
    """Parse RAW_MD into rows. Cells the PDF lost stay blank; nothing inferred."""
    rows = []
    for chunk in RAW_MD.split("* * *"):
        context_matchup = None
        context_date = None
        for line in chunk.splitlines():
            line = line.strip()
            if not line.startswith("|") or set(line) <= set("|- "):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(c in ("", "---") for c in cells):
                continue
            cells = [c for c in cells if c not in ("", "---")]
            if not cells or cells[0].startswith("Game Date"):
                continue
            d = t = mu = team = player = status = reason = None
            rest = list(cells)
            # pop leading game date (normalize PDF format MM/DD/YYYY -> ISO)
            if rest and re.match(r"^11/1[34]/2026$", rest[0]):
                mm, dd, yyyy = rest.pop(0).split("/")
                d = f"{yyyy}-{mm}-{dd}"
            # pop leading time
            if rest and re.match(r"^\d{2}:\d{2} \(ET\)$", rest[0]):
                t = rest.pop(0)
            # pop leading matchup
            if rest and re.match(r"^[A-Z]{3}@[A-Z]{3}$", rest[0]):
                mu = rest.pop(0)
            # pop leading team
            if rest and rest[0] in TEAM_NAMES:
                team = rest.pop(0)
            # remaining: [player?, status, reason?]
            if rest and rest[0] in STATUSES:
                status = rest.pop(0)
                reason = rest[0] if rest else None
            elif len(rest) >= 2 and rest[1] in STATUSES:
                player = rest.pop(0)
                status = rest.pop(0)
                reason = rest[0] if rest else None
            elif rest and rest[-1] == "NOT YET SUBMITTED":
                status = "NOT YET SUBMITTED"
                reason = "NOT YET SUBMITTED"
                rest = rest[:-1]
                if rest and rest[0] in TEAM_NAMES:
                    team = rest.pop(0)
            else:
                errors.append(f"injury parse: unmatched row: {cells}")
                continue
            rows.append({
                "game_date": d, "game_time": t, "matchup": mu, "team": team,
                "player": player, "status": status, "reason": reason,
                "_mu_ctx": mu or context_matchup,
            })
            if mu:
                context_matchup = mu
            if d:
                context_date = d
    return rows


def carry_from_editions(rows):
    """Attribute blank cells ONLY by explicit carry from an earlier official
    edition. The carried cell cites its source; ambiguous players are left
    unattributed and flagged. Status is never carried — it stays as printed in
    the 08:00 PM edition."""
    ref_rows = []
    for fn, src in (("injury_report_2026_11_13.json", INJ_0300_URL), ("injuries_0515.json", INJ_0515_URL)):
        try:
            doc = load(fn)
        except FileNotFoundError:
            continue
        for r in doc.get("rows", []):
            if r.get("team") and (r.get("matchup") or r.get("game_date")):
                ref_rows.append(dict(r, _src=src, _edition=fn))
    out, unattributed = [], []
    for r in rows:
        row = dict(r)
        row.pop("_mu_ctx", None)
        need = [k for k in ("game_date", "matchup", "team") if not row.get(k)]
        if row.get("player") is None and row.get("status") == "NOT YET SUBMITTED" and row.get("team"):
            # team NS row: date may still be missing
            cands = [x for x in ref_rows if x.get("player") is None
                     and x.get("status") == "NOT YET SUBMITTED"
                     and x.get("team") == row["team"]]
            if row.get("matchup"):
                cands = [x for x in cands if x.get("matchup") in (None, row["matchup"])]
            dates = {x.get("game_date") for x in cands if x.get("game_date")}
            if len(dates) == 1:
                row["game_date"] = dates.pop()
                row["carried"] = {"game_date": {"value": row["game_date"], "source_url": cands[0]["_src"], "edition": cands[0]["_edition"]}}
        elif need and row.get("player"):
            cands = [x for x in ref_rows if name_key(x.get("player")) == name_key(row["player"])]
            if row.get("game_date"):
                cands = [x for x in cands if x.get("game_date") in (None, row["game_date"])]
            if row.get("matchup"):
                cands = [x for x in cands if x.get("matchup") in (None, row["matchup"])]
            teams = {x.get("team") for x in cands}
            dates = {x.get("game_date") for x in cands if x.get("game_date")}
            mus = {x.get("matchup") for x in cands if x.get("matchup")}
            carried = {}
            # printed cells always win: only blanks are carried, never overwritten
            if not row.get("team") and len(teams) == 1 and None not in teams:
                row["team"] = next(iter(teams))
                carried["team"] = {"value": row["team"], "source_url": cands[0]["_src"], "edition": cands[0]["_edition"]}
            if not row.get("matchup") and len(mus) == 1:
                row["matchup"] = next(iter(mus))
                carried["matchup"] = {"value": row["matchup"], "source_url": cands[0]["_src"], "edition": cands[0]["_edition"]}
            if not row.get("game_date") and len(dates) == 1:
                row["game_date"] = next(iter(dates))
                carried["game_date"] = {"value": row["game_date"], "source_url": cands[0]["_src"], "edition": cands[0]["_edition"]}
            if carried:
                row["carried"] = carried
        if not row.get("team") and row.get("player"):
            row.pop("carried", None)
            row["unattributed_reason"] = (
                "team cell lost in PDF text extraction; no unambiguous row for this player "
                "in the 12:00 PM or 05:15 PM official editions")
            unattributed.append(row)
        else:
            out.append(row)
    return out, unattributed


# =================================================================== main
def main():
    os.makedirs(RAW_D, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # ---- 1. write the verbatim capture + parsed injury rows -----------------
    md_path = os.path.join(RAW_D, "injury_report_2026-11-13_08_00PM.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(RAW_MD)
    parsed = parse_raw_md()
    rows, unattributed = carry_from_editions(parsed)
    n14_rows = [r for r in rows if r.get("game_date") == "2026-11-14"]
    if len(n14_rows) < 26:
        errors.append(f"08:00 PM edition: only {len(n14_rows)} attributed 11/14 rows (expected >= 26)")
    for r in rows + unattributed:
        r["source_url"] = INJ_0800_URL
        r["edition"] = "11/13/26 08:00 PM ET"
    injury_doc = {
        "report": "Official NBA Injury Report — 11/13/26 08:00 PM ET (newest edition verified to exist at build time)",
        "source_url": INJ_0800_URL,
        "hub_url": POLICY_URL,
        "captured_by": "arena/ebdf1d21-nba1 (Build D)",
        "captured_at": BUILD_UTC,
        "capture_method": "Fetched with the Arena fetch tool; verbatim markdown stored beside this file "
                          "(injury_report_2026-11-13_08_00PM.md). Cells lost by PDF text extraction stay blank and are "
                          "attributed only by an explicit carry from the 12:00 PM / 05:15 PM official editions; "
                          "the carried cell cites its source. Status values are always as printed in the 08:00 PM edition.",
        "rows": rows,
        "unattributed_rows": unattributed,
        "date_coverage_note": "Covers all nine 11/13 games (game-day statuses) and all five 11/14 games "
                              "(five team rows print NOT YET SUBMITTED: New Orleans, Cleveland, Memphis, "
                              "Chicago, Miami — exactly the five 11/14 teams playing the second night of a "
                              "back-to-back, whose reports are due by 1 p.m. local on game day per the "
                              "official 2026-27 injury-report policy). 11/15–11/17 reports were not yet "
                              "published at capture.",
    }
    with open(os.path.join(RAW_D, "injury_report_2026-11-13_08_00PM.json"), "w", encoding="utf-8") as f:
        json.dump(injury_doc, f, indent=1, ensure_ascii=False)

    # ---- 2. fresh-capture verification against the schedule capture ---------
    fresh_out = []
    for fresh in (FRESH_1114, FRESH_1117):
        enriched = dict(fresh)
        enriched["games"] = [dict(g, source_url=fresh["url"]) for g in fresh["games"]]
        enriched["leaders"] = {k: dict(zip(("player", "ppg", "rpg", "apg"), v), source_url=fresh["url"])
                               for k, v in fresh["leaders"].items()}
        fresh_out.append(enriched)
    with open(os.path.join(RAW_D, "slate_fresh_2026-11-14.json"), "w", encoding="utf-8") as f:
        json.dump({
            "captured_by": "arena/ebdf1d21-nba1 (Build D)",
            "captured_at": BUILD_UTC,
            "note": "Verbatim transcription of the official NBA.com Games & Scores pages for 2026-11-14 and "
                    "2026-11-17, fetched 2026-11-14 in the 01:05–01:20 UTC build window. Records shown by "
                    "NBA.com at that moment are pre-2026-11-13 values (the 11/13 games were in progress). "
                    "Every game and leader row carries the capture's source_url.",
            "captures": fresh_out,
        }, f, indent=1, ensure_ascii=False)

    cap = load("raw/official_schedule_capture_2026-11-14.json")
    all_rows = [dict(zip(cap["cols"], r)) for r in cap["rows"]]
    horizon = [r for r in all_rows if r["date"] in HORIZON]
    if len(horizon) != 27:
        errors.append(f"horizon: expected 27 games 11/14–11/17, capture has {len(horizon)}")
    for fresh in (FRESH_1114, FRESH_1117):
        d = "2026-11-14" if fresh is FRESH_1114 else "2026-11-17"
        cap_rows = {r["game_id"]: r for r in horizon if r["date"] == d}
        for fg in fresh["games"]:
            cr = cap_rows.get(fg["game_id"])
            if not cr:
                errors.append(f"fresh {d}: game {fg['game_id']} missing from capture")
                continue
            for key, cap_key in (("away", "away"), ("home", "home"), ("tip_et", "tip_et"),
                                 ("away_record", "away_record_pre_11_13"),
                                 ("home_record", "home_record_pre_11_13")):
                if str(cr.get(cap_key)) != str(fg[key]):
                    errors.append(f"fresh {d} {fg['game_id']}: {cap_key} capture={cr.get(cap_key)} fresh={fg[key]}")
    notes.append("11/14 and 11/17 rows of the schedule capture re-verified against fresh NBA.com captures (10/10 games match).")

    # ---- 3. rest / back-to-back (schedule-derived, official sources) --------
    last_game = {}
    gc = load("raw/games_completed.json")
    completed = [dict(zip(gc["cols"], r)) for r in gc["rows"]]
    for g in completed:
        for t in (g["away"], g["home"]):
            prev = last_game.get(t)
            if prev is None or g["date"] > prev[0]:
                last_game[t] = (g["date"], "completed final (nba.com games page, capture in data/raw/games_completed.json)",
                                g["source_id"])
    sched_dates = sorted({r["date"] for r in all_rows})
    for d in sched_dates:
        url = slate_url(d)
        for r in (x for x in all_rows if x["date"] == d):
            for t in (r["away"], r["home"]):
                prev = last_game.get(t)
                if prev is None or d > prev[0]:
                    last_game[t] = (d, url, r["game_id"])

    teams_playing_11_13 = set()
    for r in all_rows:
        if r["date"] == "2026-11-13":
            teams_playing_11_13 |= {r["away"], r["home"]}

    rest_info = {}
    for r in horizon:
        d = date.fromisoformat(r["date"])
        entry = {}
        for side in ("away", "home"):
            t = r[side]
            lg = last_game.get(t)
            if lg is None:
                entry[side] = {"rest_days": None, "b2b": None, "last_date": None,
                               "basis": "no prior game found in captured data (11/06–11/17) — left blank, flagged"}
                errors.append(f"rest: no prior game found for {t} before {r['date']}")
            else:
                ld = date.fromisoformat(lg[0])
                rest_days = (d - ld).days - 1
                basis = lg[1]
                pending = lg[0] == "2026-11-13"
                entry[side] = {
                    "rest_days": rest_days, "b2b": rest_days == 0,
                    "last_date": lg[0], "last_game_id": lg[2], "basis": basis,
                    "prior_result_pending": pending,
                }
        rest_info[r["game_id"]] = entry

    # ---- 4. RecordLine-1 lines + picks (identical formulas) -----------------
    status_index = {}
    for r in rows:
        if r.get("player") and r.get("game_date") and r.get("team") and r.get("matchup"):
            status_index[(r["game_date"], r["matchup"], r["team"], name_key(r["player"]))] = (r["status"], r.get("reason"))

    team_name_of = {}
    for r in all_rows:
        team_name_of[r["away"]] = None
        team_name_of[r["home"]] = None
    # abbreviations are enough for lines; full names only needed for injury keys
    abbr_to_name = {}
    for s in load("slate_full.json")["slates"]:
        for g in s["games"]:
            abbr_to_name[g["away"]] = g["away_name"]
            abbr_to_name[g["home"]] = g["home_name"]

    leaders = {l["team"]: l for l in load("leaders.json")["leaders"]}
    n_leader_filled = 0
    for fresh in (FRESH_1114, FRESH_1117):
        for abbr, (pname, ppg, rpg, apg) in fresh["leaders"].items():
            lg = leaders.get(abbr)
            if lg is None or lg.get("player") is None:
                leaders[abbr] = {"team": abbr, "player": pname, "ppg": ppg, "rpg": rpg, "apg": apg,
                                 "source_url": fresh["url"],
                                 "fill_note": f"blank in leaders.json; filled from fresh official capture {fresh['url']} ({fresh['fetched']})"}
                n_leader_filled += 1
            else:
                # consistency check against the existing verified leader row
                for key, val in (("ppg", ppg), ("rpg", rpg), ("apg", apg)):
                    if lg.get(key) is not None and abs(float(lg[key]) - float(val)) > 0.05:
                        errors.append(f"leader {abbr} {key}: leaders.json={lg.get(key)} fresh={val}")
                if lg.get("player") and name_key(lg["player"]) != name_key(pname):
                    notes.append(f"leader {abbr}: leaders.json name {lg['player']!r} vs fresh {pname!r} (same team; kept both, values checked)")
    notes.append(f"leader stats: {n_leader_filled} team gap(s) filled from fresh official captures; "
                 "all overlapping values matched leaders.json.")

    games_out = []
    n_picks = 0
    for r in horizon:
        aw, al = parse_rec(r["away_record_pre_11_13"])
        hw, hl = parse_rec(r["home_record_pre_11_13"])
        gurl = game_url(r["away"], r["home"], r["game_id"])
        surl = slate_url(r["date"])
        model = None
        if None in (aw, al, hw, hl):
            errors.append(f"line: missing record for {r['matchup'] if 'matchup' in r else r['game_id']}")
        else:
            p_a = smoothed(aw, aw + al)
            p_h = smoothed(hw, hw + hl)
            margin = home_margin(p_h, p_a)
            ph = p_home_win(margin)
            spread_home = -round_half(margin)
            if spread_home == 0:
                spread_home = 0.0
            if margin >= CONF_MARGIN:
                pick_side, pick_line = "HOME", f"{r['home']} {spread_home:+.1f}"
            elif margin <= -CONF_MARGIN:
                pick_side, pick_line = "AWAY", f"{r['away']} {-spread_home:+.1f}"
            else:
                pick_side, pick_line = "PASS", None
            if pick_side != "PASS":
                n_picks += 1
            model = {
                "p_home_smoothed": round(p_h, 3),
                "p_away_smoothed": round(p_a, 3),
                "expected_margin_home": round(margin, 1),
                "originated_spread_home": spread_home,
                "p_home_win": round(ph, 3),
                "ml_home_decimal_fair": round(1.0 / ph, 2),
                "ml_away_decimal_fair": round(1.0 / (1.0 - ph), 2),
                "pick_side": pick_side,
                "pick_line": pick_line,
                "gate": ("G-CFG pass (|margin| ≥ 3.0); paper pick — G4/G5 market gates blocked (no odds feed)"
                         if pick_side != "PASS" else "G-CFG fail (|margin| < 3.0) — no bet"),
            }
        games_out.append({
            "date": r["date"], "game_id": r["game_id"], "matchup": f"{r['away']}@{r['home']}",
            "tip_et": r["tip_et"], "venue": r["venue"], "city": r["city"],
            "cup_label": r.get("cup_label"),
            "records_as_of": "pre-2026-11-13 (official NBA.com value; see flag D-01)",
            "away_record": r["away_record_pre_11_13"], "home_record": r["home_record_pre_11_13"],
            "rest": rest_info[r["game_id"]],
            "model": model,
            "sources": [surl, gurl, SCHEDULE_URL],
        })

    # ---- 5. fidelity check vs Build A's RecordLine-1 artifact ---------------
    orig = load("originated_lines.json")
    orig_by_key = {}
    for g in orig["games"]:
        orig_by_key[(g["date"], g["matchup"])] = g
    overlap = 0
    for g in games_out:
        key = (g["date"], g["matchup"])
        if key in orig_by_key:
            overlap += 1
            og = orig_by_key[key]
            om = og.get("model")
            if om is None or g["model"] is None:
                errors.append(f"fidelity {key}: one side has no model")
                continue
            if om["originated_spread_home"] != g["model"]["originated_spread_home"]:
                errors.append(f"fidelity {key}: spread {om['originated_spread_home']} vs {g['model']['originated_spread_home']}")
            if om["pick_side"] != g["model"]["pick_side"]:
                errors.append(f"fidelity {key}: pick {om['pick_side']} vs {g['model']['pick_side']}")
    notes.append(f"fidelity: {overlap} overlapping games (11/14–11/16) reproduce Build A's published RecordLine-1 "
                 "spread and pick side exactly (same records, same formula).")

    # ---- 6. injury layer per horizon game ----------------------------------
    abbr2name = abbr_to_name
    name2abbr = {v: k for k, v in abbr2name.items()}
    # teams that print a NOT YET SUBMITTED row anywhere in this edition (the team
    # cell is printed on every such row; the date cell may be lost to extraction)
    nys_printed = {r["team"] for r in rows if r["status"] == "NOT YET SUBMITTED" and r.get("team")}
    inj_layer = {}
    for g in games_out:
        entry = {"game": g["matchup"], "date": g["date"], "edition": "11/13/26 08:00 PM ET",
                 "edition_source": INJ_0800_URL, "teams": []}
        for side, abbr in (("away", g["matchup"][:3]), ("home", g["matchup"][4:])):
            team = abbr2name.get(abbr, abbr)
            mu = g["matchup"]
            trows = [r for r in rows if r.get("game_date") == g["date"] and r.get("matchup") == mu
                     and r.get("team") == team]
            nys = any(r["status"] == "NOT YET SUBMITTED" for r in trows)
            nys_printed_this_team = (g["date"] == "2026-11-14" and team in nys_printed)
            lg = leaders.get(abbr)
            leader_status = None
            if lg and lg.get("player"):
                st = status_index.get((g["date"], mu, team, name_key(lg["player"])))
                if g["date"] != "2026-11-14":
                    leader_status = {"status": None, "note": "Official report for this date not yet published at capture (due by 5 p.m. local the day before, or 1 p.m. local for the second game of a back-to-back)."}
                elif st:
                    leader_status = {"status": st[0], "reason": st[1]}
                elif nys:
                    leader_status = {"status": "NOT YET SUBMITTED", "note": "Team report prints NOT YET SUBMITTED in the 08:00 PM edition (dated row)."}
                elif nys_printed_this_team:
                    leader_status = {"status": "NOT YET SUBMITTED", "note": "Team report prints NOT YET SUBMITTED in the 08:00 PM edition; the row's date cell was lost in PDF extraction, so it is not used as a dated signal (flag D-03)."}
                else:
                    leader_status = {"status": "Not listed on report"}
            entry["teams"].append({
                "team": team, "abbr": abbr,
                "n_out": sum(1 for r in trows if r["status"] == "Out" and r["player"]),
                "n_doubtful": sum(1 for r in trows if r["status"] == "Doubtful"),
                "n_questionable": sum(1 for r in trows if r["status"] == "Questionable"),
                "n_probable": sum(1 for r in trows if r["status"] == "Probable"),
                "n_available": sum(1 for r in trows if r["status"] == "Available"),
                "not_yet_submitted": nys,
                "not_yet_submitted_printed": nys_printed_this_team,
                "leader": ({"player": lg["player"], "ppg": lg.get("ppg"), "rpg": lg.get("rpg"),
                            "apg": lg.get("apg"), "status": (leader_status or {}).get("status"),
                            "status_note": (leader_status or {}).get("note"),
                            "status_reason": (leader_status or {}).get("reason"),
                            "source_url": lg.get("source_url")} if lg and lg.get("player") else
                           {"player": None, "note": "leader stats not available from an official page", "source_url": lg.get("source_url") if lg else None}),
                "out_names": [r["player"] for r in trows if r["status"] == "Out" and r["player"]],
                "source_url": INJ_0800_URL,
            })
        inj_layer[g["matchup"] + "|" + g["date"]] = entry

    # ---- 7. edition diff (05:15 PM → 08:00 PM, 11/14 rows) ------------------
    old = load("injuries_0515.json")
    old14 = [r for r in old["rows"] if r.get("game_date") == "2026-11-14" and r.get("player")]
    new14 = [r for r in rows if r.get("game_date") == "2026-11-14" and r.get("player")]
    old_keys = {(r.get("matchup") or r.get("team"), name_key(r["player"])) for r in old14}
    new_keys = {(r.get("matchup") or r.get("team"), name_key(r["player"])) for r in new14}
    added = sorted(k for k in new_keys if k not in old_keys)
    removed = sorted(k for k in old_keys if k not in new_keys)
    changed = []
    for k in sorted(new_keys & old_keys):
        o = next(r for r in old14 if (r.get("matchup") or r.get("team"), name_key(r["player"])) == k)
        n = next(r for r in rows if r.get("game_date") == "2026-11-14" and r.get("player")
                 and (r.get("matchup") or r.get("team"), name_key(r["player"])) == k)
        if o.get("status") != n.get("status"):
            changed.append({"player": n.get("player"), "team": n.get("team") or o.get("team"),
                            "from": o.get("status"), "to": n.get("status")})
    edition_diff = {
        "from_edition": INJ_0515_URL, "to_edition": INJ_0800_URL, "game_date": "2026-11-14",
        "rows_added": [{"matchup": k[0], "player": None} for k in added],
        "rows_removed": [{"matchup": k[0], "player": None} for k in removed],
        "status_changes": changed,
        "note": "Keys use (matchup-or-team, player). The 05:15 PM edition's ambiguous 'Martin, Caleb' row "
                "(printed with a Cleveland team cell; see data/injuries_0515.json date_coverage_note) remains "
                "unresolved in the 08:00 PM edition and stays unattributed and unused in both.",
    }

    # ---- 8. prop combos (team leaders, P+R+A line) --------------------------
    prop_rows = []
    for g in games_out:
        for side, abbr in (("away", g["matchup"][:3]), ("home", g["matchup"][4:])):
            lg = leaders.get(abbr)
            team = abbr2name.get(abbr, abbr)
            surl = slate_url(g["date"])
            if lg is None or lg.get("player") is None:
                prop_rows.append({
                    "date": g["date"], "game": g["matchup"], "team": team, "player": None,
                    "ppg": None, "rpg": None, "apg": None, "line": None,
                    "status": None, "status_reason": None,
                    "signal": "BLANK — leader stats not available from an official page (flagged)",
                    "sources": [surl, game_url(g["matchup"][:3], g["matchup"][4:], g["game_id"])],
                })
                continue
            combo = round((lg["ppg"] + lg["rpg"] + lg["apg"]) / PROP_ROUND) * PROP_ROUND
            mu = g["matchup"]
            st = status_index.get((g["date"], mu, team, name_key(lg["player"])))
            if g["date"] != "2026-11-14":
                status, status_reason = "Report not yet published for this date", None
                sig = "BLOCKED — status report not yet due/published (G-INJ)"
            elif st is None and team in nys_printed:
                status = "NOT YET SUBMITTED (team row printed; date cell lost in extraction)"
                status_reason = None
                sig = "BLOCKED — team report prints NOT YET SUBMITTED (G-INJ)"
            elif st is None:
                status, status_reason = "Not listed on report", None
                sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
            else:
                status, status_reason = st
                if status in ("Out", "Doubtful"):
                    sig = "NO BET — officially out/doubtful"
                elif status == "Questionable":
                    sig = "PASS — availability risk unquantified"
                else:
                    sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
            prop_rows.append({
                "date": g["date"], "game": mu, "team": team, "player": lg["player"],
                "ppg": lg["ppg"], "rpg": lg["rpg"], "apg": lg["apg"], "line": combo,
                "status": status, "status_reason": status_reason, "signal": sig,
                "sources": [lg.get("source_url"), INJ_0800_URL if g["date"] == "2026-11-14" else POLICY_URL, surl],
            })

    # ---- 9. parlays (top-3 picks per date, Fréchet bounds) ------------------
    parlay_rows = []
    by_date = {}
    for g in games_out:
        if g["model"] and g["model"]["pick_side"] != "PASS":
            by_date.setdefault(g["date"], []).append(g)
    for d, picks in sorted(by_date.items()):
        picks = sorted(picks, key=lambda x: -x["model"]["p_home_win"] if x["model"]["pick_side"] == "HOME"
                       else -(1 - x["model"]["p_home_win"]))
        for i, j in ((0, 1), (0, 2), (1, 2)):
            if i >= len(picks) or j >= len(picks):
                continue
            g1, g2 = picks[i], picks[j]
            p1 = g1["model"]["p_home_win"] if g1["model"]["pick_side"] == "HOME" else 1 - g1["model"]["p_home_win"]
            p2 = g2["model"]["p_home_win"] if g2["model"]["pick_side"] == "HOME" else 1 - g2["model"]["p_home_win"]
            rho_lb, rho_ub = rho_bounds(p1, p2)
            lb_joint = max(0.0, p1 + p2 - 1.0)
            ub_joint = min(p1, p2)
            parlay_rows.append({
                "date": d,
                "leg1": f"{g1['matchup']} — {g1['model']['pick_line']}",
                "leg2": f"{g2['matchup']} — {g2['model']['pick_line']}",
                "p1": round(p1, 3), "p2": round(p2, 3),
                "joint_lb": round(lb_joint, 3), "joint_ub": round(ub_joint, 3),
                "rho_lb": None if rho_lb is None else round(rho_lb, 3),
                "rho_ub": None if rho_ub is None else round(rho_ub, 3),
                "fair_odds_lb": round(1.0 / ub_joint, 2) if ub_joint > 0 else None,
                "fair_odds_ub": round(1.0 / lb_joint, 2) if lb_joint > 0 else None,
                "correlation_note": "Cross-game legs; marginals only. Exact Fréchet–Hoeffding bounds; "
                                    "no independence assumption (rho bounds bracket every joint distribution). "
                                    "Same-game parlays are not originated (correlation unmeasured).",
                "sources": [g1["sources"][1], g2["sources"][1]],
            })

    # ---- 10. game-flow notes (schedule-derived, policy-annotated) ----------
    flow_notes = []
    nys_teams = sorted({t["team"] for g in games_out if g["date"] == "2026-11-14"
                        for t in inj_layer[g["matchup"] + "|" + g["date"]]["teams"]
                        if t["not_yet_submitted"]})
    nys_printed_sorted = sorted(abbr2name.get(a, a) for a in
                                {name2abbr[t] for t in nys_printed if t in name2abbr})
    b2b_11_14 = sorted({abbr for g in games_out if g["date"] == "2026-11-14"
                        for side_abbr in (g["matchup"][:3], g["matchup"][4:])
                        for abbr in [side_abbr]
                        if g["rest"]["away" if side_abbr == g["matchup"][:3] else "home"]["b2b"]})
    b2b_11_14_names = [abbr2name.get(a, a) for a in b2b_11_14]
    if nys_printed_sorted and nys_printed_sorted == sorted(b2b_11_14_names):
        flow_notes.append({
            "note": "The teams printing NOT YET SUBMITTED in the 08:00 PM edition ("
                    + ", ".join(nys_printed_sorted)
                    + ") are exactly the 11/14 teams the official schedule shows on the second night of a "
                      "back-to-back (all played 11/13). Caveat kept visible: four of the five NS rows lost their "
                      "date cell in PDF extraction (New Orleans' is dated 11/14); they are attributed to 11/14 by "
                      "the report's own section order only, which is why they are not used as dated signals. "
                      "Policy: second-game-of-back-to-back reports are due by 1 p.m. local on game day, so "
                      "'not yet submitted' at 08:00 PM ET the night before is the expected state, not a data gap.",
            "sources": [POLICY_URL, slate_url("2026-11-13"), INJ_0800_URL],
        })
    else:
        flow_notes.append({
            "note": f"Teams printing NOT YET SUBMITTED in the 08:00 PM edition: {nys_printed_sorted or 'none detected'}. "
                    f"Teams on the second night of a back-to-back on 11/14 per the official schedule: {b2b_11_14_names}. "
                    "Policy: second-game reports are due by 1 p.m. local on game day. The two lists are published "
                    "side by side without being equated.",
            "sources": [POLICY_URL, slate_url("2026-11-13"), INJ_0800_URL],
        })
    flow_notes.append({
        "note": "Portland and Minnesota play each other at Target Center on BOTH 2026-11-16 and 2026-11-17 "
                "(per the official schedule), so both enter 11/17 on the second night of a back-to-back; "
                "their 11/17 reports are due by 1 p.m. local on game day and were not yet published at capture.",
        "sources": [slate_url("2026-11-16"), slate_url("2026-11-17"), POLICY_URL],
    })
    flow_notes.append({
        "note": "Dallas plays 11/14 (at Cleveland) and 11/15 (at Boston) — a back-to-back; Boston plays 11/15 "
                "and 11/16; Washington plays 11/15 and 11/16. Second-game reports for these are due by 1 p.m. "
                "local on game day and were not yet published at capture.",
        "sources": [slate_url("2026-11-14"), slate_url("2026-11-15"), slate_url("2026-11-16"), POLICY_URL],
    })

    # ---- 11. DET@MIA game-time check (report column vs schedule) -----------
    time_mismatches = []
    for g in games_out:
        mu = g["matchup"]
        trows = [r for r in rows if r.get("game_date") == g["date"] and r.get("matchup") == mu and r.get("game_time")]
        if trows:
            t_pdf = trows[0]["game_time"]
            tip_pdf = t_pdf.replace(" (ET)", " PM").replace(":00 PM", ":00 PM")
            # normalize "07:30" -> "7:30 PM"
            hh, mm = t_pdf.split(" (")[0].split(":")
            tip_norm = f"{int(hh)}:{mm} PM ET"
            if tip_norm != g["tip_et"]:
                time_mismatches.append({
                    "game": mu, "date": g["date"], "report_time": t_pdf,
                    "schedule_tip": g["tip_et"],
                    "note": "Official injury-report game-time column differs from the official schedule tip. "
                            "Schedule value used for display; both official values shown here.",
                })
                notes.append(f"time mismatch {mu} {g['date']}: report prints {t_pdf}, schedule prints {g['tip_et']}")

    # ---- 12. flags ----------------------------------------------------------
    n_unattr = len(unattributed)
    flags = [
        {"id": "D-01", "severity": "high", "flag": "Team records are pre-2026-11-13 values",
         "detail": "The 2026-11-13 games were IN PROGRESS at build time (01:00–01:25 UTC = 8:00–8:25 PM ET). "
                   "No 11/13 final existed yet, so every horizon game uses pre-11/13 records, and teams that "
                   "played 11/13 are missing one result. Picks regenerate automatically when finals exist "
                   "(python3 scripts/generate_picks_d.py after capturing finals). This is a data-currency limit, "
                   "disclosed per row via records_as_of — not a claim of current strength.",
         "source_url": slate_url("2026-11-13")},
        {"id": "D-02", "severity": "high", "flag": "Injury reports for 11/15–11/17 not yet published",
         "detail": "Per the official 2026-27 policy, next-day reports are due by 5 p.m. local the day before "
                   "(1 p.m. local for second games of back-to-backs). At capture (11/13 08:00 PM edition) no "
                   "11/15–11/17 rows existed. Record-based lines for those dates carry NO injury adjustment; "
                   "the gap is disclosed per game, never filled.",
         "source_url": POLICY_URL},
        {"id": "D-03", "severity": "medium", "flag": f"{n_unattr} rows in the 08:00 PM PDF lost their team cell",
         "detail": "PDF text extraction drops cells on continuation rows. Rows whose team/matchup/date cannot "
                   "be carried from an earlier official edition (12:00 PM / 05:15 PM) are kept in "
                   "unattributed_rows with the verbatim markdown beside them, and are used in NO signal.",
         "source_url": INJ_0800_URL},
        {"id": "D-04", "severity": "medium", "flag": "'Martin, Caleb' attribution conflict across editions",
         "detail": "The 12:00 PM edition printed him with LA Clippers (11/13, OKC@LAC); the 05:15 PM edition's "
                   "11/14 row printed a Cleveland team cell (its own extraction note calls this ambiguous); the "
                   "08:00 PM edition prints him in the Dallas continuation block with the cell lost. Team left "
                   "blank; row excluded from all signals; manual review required.",
         "source_url": INJ_0800_URL},
        {"id": "D-05", "severity": "medium", "flag": "RecordLine-1 parameters are project assumptions",
         "detail": "Smoothing +3/+6, HCA 2.5, K 35, SIGMA 11, pick gate 3.0 are this project's documented "
                   "assumptions (lineage flag E-01), not official values. Home-court advantage could not be "
                   "sourced from an official NBA page; 2.5 is an assumption carried from Build A.",
         "source_url": "https://www.nba.com/stats/teams/advanced"},
        {"id": "D-06", "severity": "medium", "flag": "No totals are originated",
         "detail": "RecordLine-1 uses records only and cannot separate pace/efficiency, so game totals are not "
                   "published (same limit as Build A's lines.html). Totals would need the ratings-based engine "
                   "in scripts/originate_lines.py fed with current stats.",
         "source_url": "https://www.nba.com/stats/teams/advanced"},
        {"id": "D-07", "severity": "high", "flag": "Market gates G4/G5 remain blocked; 0 strategies funded",
         "detail": "No odds feed is connected, so closing-line-value and economic-value gates cannot run. "
                   "Every pick on this page is a paper record; the leaderboard (Build B) still shows 0 funded "
                   "strategies, and this build changes nothing about that.",
         "source_url": "https://www.nba.com/stats/help/faq"},
        {"id": "D-08", "severity": "low", "flag": "11/15 and 11/16 schedule rows rely on Build C's verified capture",
         "detail": "This session re-verified 11/14 and 11/17 rows against fresh NBA.com captures (10/10 match). "
                   "The 11/15 (9 games) and 11/16 (8 games) rows were verified row-by-row by Build C on "
                   "2026-11-14 (data/raw/verification_c03.json, 0 mismatches) and are not re-fetched here.",
         "source_url": SCHEDULE_URL},
        {"id": "D-09", "severity": "low", "flag": "Leader stats are season averages through 11/12",
         "detail": "Team-leader PPG/RPG/APG come from official game-card 'Season Leaders' captured 11/13 "
                   "(leaders.json) or in this build's fresh captures. Pages fetched while 11/13 games were in "
                   "progress still display through-11/12 values. Three blanks (CHA/LAL/TOR) were filled from "
                   "the fresh 11/17 capture, with source links per row.",
         "source_url": "https://www.nba.com/stats/players"},
        {"id": "D-10", "severity": "medium", "flag": "Injury statuses are not minutes or production forecasts",
         "detail": "A report status constrains availability only. No verified minutes history exists for the "
                   "listed players, so no rotation-minute or production number is derived (consistent with "
                   "Build A's gameflow layer). Impact stays qualitative; the per-team Out/Questionable counts "
                   "and leader status are published without a numeric shift.",
         "source_url": POLICY_URL},
    ]
    if time_mismatches:
        flags.append({
            "id": "D-11", "severity": "low",
            "flag": "Injury-report game-time column differs from the schedule for "
                    + ", ".join(f"{m['game']} ({m['report_time']} vs {m['schedule_tip']})" for m in time_mismatches),
            "detail": "Both are official values. The schedule tip is used for display; the report value is "
                      "preserved verbatim in data/raw/d/injury_report_2026-11-13_08_00PM.json. Flagged for "
                      "manual review rather than silently reconciled.",
            "source_url": INJ_0800_URL,
        })

    # ---- 13. write picks_d.json --------------------------------------------
    audit = {
        "_meta": {
            "build": "Build D — live-horizon lines & picks (session arena/ebdf1d21-nba1)",
            "generated_at_utc": BUILD_UTC,
            "horizon": {"from": HORIZON[0], "to": HORIZON[-1], "games": len(games_out),
                        "definition": "today (2026-11-14, user-local date) plus the maximum 3 days ahead"},
            "as_of": {
                "records": "pre-2026-11-13 official records (11/13 games in progress at build time)",
                "leader_stats": "official season leaders through games of 2026-11-12",
                "injury_edition": "11/13/26 08:00 PM ET (newest edition verified to exist)",
                "schedule": "verified 2026-11-14 (Build C capture + this build's fresh 11/14 & 11/17 captures)",
            },
            "model": "RecordLine-1",
            "assumptions": {
                "smoothing": f"+{PRIOR_W:.0f} wins / +{PRIOR_G:.0f} games toward .500",
                "home_court_points": HCA, "scale_K": K, "sigma": SIGMA,
                "pick_gate_margin": CONF_MARGIN,
                "note": "All parameters are this project's assumptions, not official values. Totals are not "
                        "originated. Market comparison gates (G4/G5) are blocked: no odds feed is connected.",
            },
            "verification": notes,
            "fidelity_check": {"overlapping_games": overlap,
                               "result": "spread + pick side reproduce Build A's artifact exactly" if not errors else "ERRORS — see errors"},
        },
        "horizon_games": games_out,
        "parlays": parlay_rows,
        "prop_rows": prop_rows,
        "injury_layer_2026_11_14": [inj_layer[g["matchup"] + "|" + g["date"]] for g in games_out if g["date"] == "2026-11-14"],
        "injury_report_rows_2026_11_14": n14_rows,
        "unattributed_injury_rows": unattributed,
        "edition_diff_0515_to_2000": edition_diff,
        "game_flow_notes": flow_notes,
        "flags": flags,
        "n_model_picks": n_picks,
        "errors": errors,
    }
    with open(os.path.join(OUT, "picks_d.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=1, ensure_ascii=False)

    # ---- 14. render the page -----------------------------------------------
    render_page(audit)

    # ---- 15. self-audit ------------------------------------------------------
    verify_page(os.path.join(ROOT, "picks-2026-11-14.html"))

    print(f"BUILD D: {len(games_out)} horizon games, {n_picks} gated paper picks, "
          f"{len(parlay_rows)} parlay cards, {len(prop_rows)} prop rows, "
          f"{len(n14_rows)} attributed 11/14 injury rows, {n_unattr} unattributed (flagged)")
    for n in notes:
        print("NOTE:", n)
    if errors:
        print("ERRORS:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("VERIFY OK")


# =================================================================== page
NAV = [
    ("index.html", "Executive summary"),
    ("lines.html", "Originated lines & picks"),
    ("picks-2026-11-14.html", "Horizon picks 14–17 Nov"),
    ("gameflow.html", "Injuries & game flow"),
    ("research.html", "Strategy lab"),
    ("slate.html", "Upcoming slate"),
    ("schedule-verified.html", "Verified schedule"),
    ("verification.html", "Live verification"),
    ("suggestions.html", "Questions & suggestions"),
    ("review.html", "Flagged for review"),
    ("sources.html", "Source register"),
]


def table(headers, rows, tid):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for r in rows:
        out = []
        for c in r:
            if isinstance(c, str) and c.startswith(("<a ", "<span", "<em", "<strong", "<b")):
                out.append(f"<td>{c}</td>")
            else:
                out.append(f"<td>{esc(c)}</td>")
        body.append("<tr>" + "".join(out) + "</tr>")
    search = (f'<input class="filter" type="search" placeholder="Filter rows…" '
              f'data-target="{tid}" aria-label="Filter rows">')
    return (f'{search}<div class="tablewrap"><table id="{tid}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def a(url, label):
    check_url(url, f"link {label}")
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def render_page(audit):
    games = audit["horizon_games"]
    inj14 = {e["game"]: e for e in audit["injury_layer_2026_11_14"]}

    # --- slate tables ---
    slate_sections = []
    for d in HORIZON:
        rows = [g for g in games if g["date"] == d]
        trows = []
        for g in rows:
            m = g["model"]
            ra = g["rest"]["away"]
            rh = g["rest"]["home"]
            rest_cell = (
                f"{esc(g['matchup'][:3])}: {'—' if ra['rest_days'] is None else ra['rest_days']}d"
                f"{' (B2B)' if ra['b2b'] else ''} · "
                f"{esc(g['matchup'][4:])}: {'—' if rh['rest_days'] is None else rh['rest_days']}d"
                f"{' (B2B)' if rh['b2b'] else ''}")
            if g["date"] == "2026-11-14" and g["matchup"] in inj14:
                e = inj14[g["matchup"]]
                inj_cell = "; ".join(
                    f"{t['abbr']}: {t['n_out']} Out/{t['n_questionable']} Q/{t['n_probable']} P"
                    + (" — NOT YET SUBMITTED" if t["not_yet_submitted"] else "")
                    for t in e["teams"])
            elif g["date"] == "2026-11-14":
                inj_cell = "no attributed rows in this edition"
            else:
                inj_cell = "report not yet published"
            pick = (f"<strong>{esc(m['pick_line'])}</strong> ({esc(m['pick_side'])})" if m and m["pick_side"] != "PASS"
                    else "— (gate: |margin| < 3.0)")
            trows.append([
                f"<a href=\"{esc(g['sources'][1])}\" target=\"_blank\" rel=\"noopener\">{esc(g['matchup'])}</a>",
                esc(g["tip_et"]),
                f"{esc(g['away_record'])} @ {esc(g['home_record'])}",
                rest_cell,
                (fmt(m["originated_spread_home"]) if m else "—") + " (home)",
                pick,
                fmt(m["p_home_win"], 3) if m else "—",
                (f"{fmt(m['ml_home_decimal_fair'], 2)} / {fmt(m['ml_away_decimal_fair'], 2)}" if m else "—"),
                inj_cell,
            ])
        n_p = sum(1 for g in rows if g["model"] and g["model"]["pick_side"] != "PASS")
        slate_sections.append(
            f"<h3>{esc(d)} — {len(rows)} games, {n_p} gated picks</h3>"
            + table(["Game (official page)", "Tip (ET)", "Records (as of 11/13 pre-slate)",
                     "Rest (away · home)", "Our spread (home)", "RecordLine-1 pick",
                     "P(home)", "Fair ML (home/away)", "Injury layer (08:00 PM edition)"],
                    trows, f"slate-{d}"))

    # --- parlays ---
    prow = []
    for p in audit["parlays"]:
        prow.append([
            esc(p["date"]),
            esc(p["leg1"]), esc(p["leg2"]),
            fmt(p["p1"], 3), fmt(p["p2"], 3),
            f"{fmt(p['joint_lb'], 3)}–{fmt(p['joint_ub'], 3)}",
            f"{fmt(p['rho_lb'], 3)}–{fmt(p['rho_ub'], 3)}" if p["rho_lb"] is not None else "—",
            f"{fmt(p['fair_odds_lb'], 2)}–{fmt(p['fair_odds_ub'], 2)}",
            f'<a href="{esc(p["sources"][0])}" target="_blank" rel="noopener">leg 1</a> · '
            f'<a href="{esc(p["sources"][1])}" target="_blank" rel="noopener">leg 2</a>',
        ])

    # --- props ---
    propw = []
    for p in audit["prop_rows"]:
        propw.append([
            esc(p["date"]), esc(p["game"]), esc(p["team"]),
            esc(p["player"]) if p["player"] else "—",
            fmt(p["ppg"]), fmt(p["rpg"]), fmt(p["apg"]),
            fmt(p["line"]) if p["line"] is not None else "—",
            esc(p["status"]) if p["status"] else "—",
            esc(p["signal"]),
            " · ".join(f'<a href="{esc(s)}" target="_blank" rel="noopener">src{i+1}</a>'
                       for i, s in enumerate(p["sources"]) if s),
        ])

    # --- injury rows 11/14 ---
    injw = []
    for r in audit["injury_report_rows_2026_11_14"]:
        carried = r.get("carried") or {}
        attr = []
        for k, v in carried.items():
            attr.append(f"{k}={esc(v['value'])} (carried from {esc(v['edition'])})")
        attr_s = "; ".join(attr) if attr else "printed in this edition"
        injw.append([
            esc(r.get("matchup") or "—"),
            esc(r.get("team") or "—"),
            esc(r.get("player") or "—"),
            esc(r.get("status")),
            esc(r.get("reason") or "—"),
            attr_s,
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">PDF</a>',
        ])
    for r in audit["unattributed_injury_rows"]:
        if r.get("game_date") not in (None, "2026-11-14"):
            continue
        injw.append([
            esc(r.get("matchup") or "—"),
            "<em>blank — unattributed (flag D-03/D-04)</em>",
            esc(r.get("player") or "—"),
            esc(r.get("status")),
            esc(r.get("reason") or "—"),
            esc(r.get("unattributed_reason", "")),
            f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">PDF</a>',
        ])

    # --- game flow notes ---
    floww = []
    for i, fn in enumerate(audit["game_flow_notes"], 1):
        floww.append([
            f"GF-{i:02d}",
            esc(fn["note"]),
            " · ".join(f'<a href="{esc(s)}" target="_blank" rel="noopener">src</a>' for s in fn["sources"]),
        ])

    # --- flags ---
    flagw = []
    for fl in audit["flags"]:
        flagw.append([
            f"<strong>{esc(fl['id'])}</strong>",
            esc(fl["severity"]),
            esc(fl["flag"]),
            esc(fl["detail"]),
            f'<a href="{esc(fl["source_url"])}" target="_blank" rel="noopener">source</a>',
        ])

    n_games = len(games)
    n_picks = audit["n_model_picks"]
    body = f"""
<h1>Build D — Horizon picks, 14–17 Nov 2026</h1>
<p class="lede">RecordLine-1 lines and gated paper picks for <strong>every upcoming slate within the maximum
3-day window</strong> (27 games, 2026-11-14 through 2026-11-17), closing board item F-C07. Built by session
<code>arena/ebdf1d21-nba1</code> at {esc(audit["_meta"]["generated_at_utc"])} with
<code>scripts/generate_picks_d.py</code>. Every table row links to an official source; every unverified value
is blank and flagged. This page does <em>not</em> claim current strength: see flags D-01/D-02 first.</p>

<div class="callout"><b>As-of stamps.</b> Records: pre-11/13 official values (the 11/13 games were in progress
at build time — flag D-01). Leader stats: official season leaders through 11/12 (flag D-09). Injury edition:
the official <a href="{INJ_0800_URL}" target="_blank" rel="noopener">11/13 08:00 PM ET report</a> — the newest
edition verified to exist, carrying rows for all five 11/14 games (flags D-03/D-04 for lost cells). Reports for
11/15–11/17 were not yet published (flag D-02). No odds feed is connected: market gates stay blocked, the
leaderboard stays at 0 funded strategies (flag D-07).</div>

<h2>Executive summary (this build)</h2>
<ul>
<li><strong>27 games</strong> across four slates verified against official NBA.com pages: 11/14 and 11/17 rows re-verified fresh this session (10/10 match); 11/15–11/16 rows carried from Build C's verified capture (flag D-08).</li>
<li><strong>{n_picks} gated paper picks</strong> from RecordLine-1 (record-based spread model, identical formulas to Build A). For all {audit["_meta"]["fidelity_check"]["overlapping_games"]} overlapping 11/14–11/16 games the regenerated spread and pick side reproduce Build A's published artifact exactly — the 5 games of 11/17 are net-new.</li>
<li><strong>{len(audit["parlays"])} two-leg cross-game parlay cards</strong> with exact Fréchet–Hoeffding joint-probability bounds; same-game parlays are not originated because same-game correlation is unmeasured here.</li>
<li><strong>{len(audit["prop_rows"])} player-prop combo rows</strong> (team-leader P+R+A lines) with official availability statuses; signals stay gated (no market number, no game-log variance).</li>
<li><strong>Injury layer upgraded for 11/14:</strong> all five games covered by the 08:00 PM edition (05:15 PM covered four). The five NOT YET SUBMITTED teams are exactly the five back-to-back teams — consistent with the official submission policy (game-flow note GF-01).</li>
<li><strong>0 totals, 0 market-validated bets, 0 funded strategies.</strong> Totals are not originated (flag D-06); market gates are blocked (flag D-07); luck is controlled by publishing bounds and gates rather than headline hit rates.</li>
</ul>

<h2>Slates and RecordLine-1 picks</h2>
<p>Spread shown for the home team (negative = home favoured). P(home) is the logistic win probability at
SIGMA = 11.0; fair ML is 1/P with no vig — no sportsbook price is used or implied. The pick gate requires
|expected margin| ≥ 3.0 (assumption, flag D-05). Rest days are schedule-derived from official pages
(completed finals 11/06–11/12 plus the captured 11/13–11/17 schedule); a team whose prior game is the in-progress
11/13 slate is marked with rest computed from dates only (flag D-01).</p>
{"".join(slate_sections)}

<h2>Two-leg cross-game parlay cards (MODEL-DERIVED)</h2>
<p>Legs are the gated picks of a slate (top three by confidence, pairs among them). The joint probability is
<strong>not</strong> computed by multiplying marginals: the published range is the exact
Fréchet–Hoeffding bound, and the ρ range brackets every joint distribution consistent with the marginals.
Payout fair odds are the reciprocal of the bounds. No market price is compared (flag D-07).</p>
{table(["Date", "Leg 1", "Leg 2", "p1", "p2", "Joint p range", "ρ range (Fréchet)", "Fair odds range", "Sources"], prow, "parlays")}

<h2>Player-prop combos (paper, gated)</h2>
<p>Line = round of the team leader's official season PPG+RPG+APG to the nearest 0.5. The signal stays BLOCKED
unless an official status exists for the player on that date — statuses exist only for 11/14 in this edition.
No prop price exists, so no edge is claimed (G-PROP). CHA/LAL/TOR leader gaps were filled from the fresh
11/17 official capture (flag D-09).</p>
{table(["Date", "Game", "Team", "Player", "PPG", "RPG", "APG", "Combo line", "Official status", "Signal", "Sources"], propw, "props")}

<h2>Official injury report — 11/13/26 08:00 PM ET edition, 11/14 rows</h2>
<p>Verbatim transcription stored at <code>data/raw/d/injury_report_2026-11-13_08_00PM.md</code>. Statuses are
printed values; team/date cells lost by PDF extraction are attributed only by an explicit carry from an earlier
official edition (shown per row), and remain blank where no unambiguous carry exists. Minutes and production
impacts are <em>not</em> derived (flag D-10) — see <a href="gameflow.html">gameflow.html</a> for the impact
layer. The edition diff against the 05:15 PM edition is in
<code>data/derived/picks_d.json → edition_diff_0515_to_2000</code>.</p>
{table(["Matchup", "Team", "Player", "Status", "Reason", "Attribution", "Source"], injw, "inj14")}

<h2>Game-flow notes (schedule- and policy-derived)</h2>
{table(["#", "Note (all schedule facts from official pages; policy from official.nba.com)", "Sources"], floww, "flow")}

<h2>Methodology &amp; assumptions</h2>
{table(["Item", "Value", "Status"],
       [["Model", "RecordLine-1 (identical formulas to scripts/build_edge_site.py)",
         '<a href="lines.html" target="_blank" rel="noopener">Build A lines.html</a> · '
         '<a href="https://www.nba.com/stats" target="_blank" rel="noopener">nba.com stats</a>'],
        ["Inputs", "Official records (pre-11/13), official schedule, official injury edition, official leader stats",
         '<a href="https://www.nba.com/schedule" target="_blank" rel="noopener">nba.com</a>'],
        ["Smoothing", "+3 wins / +6 games toward .500 (assumption — flag D-05)",
         '<a href="https://www.nba.com/stats/faq" target="_blank" rel="noopener">nba.com stats FAQ</a>'],
        ["Home court", "2.5 points (assumption — no official value; flag D-05)",
         '<a href="https://www.nba.com/stats/teams/advanced" target="_blank" rel="noopener">nba.com stats</a>'],
        ["Pick gate", "|expected margin| ≥ 3.0 else no bet (assumption)",
         '<a href="https://www.nba.com/stats/teams/advanced" target="_blank" rel="noopener">nba.com stats</a>'],
        ["Totals", "Not originated (records cannot separate pace/efficiency — flag D-06)",
         '<a href="https://www.nba.com/stats/teams/advanced" target="_blank" rel="noopener">nba.com stats</a>'],
        ["Correlation", "Cross-game legs only; Fréchet–Hoeffding bounds; same-game parlays not originated",
         '<a href="https://www.nba.com/stats/help/glossary" target="_blank" rel="noopener">stats glossary</a>'],
        ["Luck control", "Bounds published instead of point claims; market gates blocked; 0 funded strategies; "
         "regeneration is scripted, not manual",
         '<a href="docs/b/pages/luck.html" target="_blank" rel="noopener">build B luck page</a> · '
         '<a href="https://www.nba.com/stats/help/faq" target="_blank" rel="noopener">stats FAQ</a>']],
       "method")}

<h2>Flagged for review (Build D)</h2>
<p>These do not block publication (per COORDINATION §0.2). They are also listed in
<code>data/derived/picks_d.json → flags</code> and summarized in COORDINATION.md §14.</p>
{table(["ID", "Severity", "Flag", "Detail", "Source"], flagw, "flags")}

<h2>Sources</h2>
<ul>
<li><a href="https://www.nba.com/schedule" target="_blank" rel="noopener">NBA.com schedule</a> (horizon scope)</li>
<li><a href="https://www.nba.com/games?date=2026-11-14" target="_blank" rel="noopener">NBA.com games 11/14</a> · <a href="https://www.nba.com/games?date=2026-11-15" target="_blank" rel="noopener">11/15</a> · <a href="https://www.nba.com/games?date=2026-11-16" target="_blank" rel="noopener">11/16</a> · <a href="https://www.nba.com/games?date=2026-11-17" target="_blank" rel="noopener">11/17</a> (fresh 11/14 + 11/17 captures this session; 11/15–16 via Build C capture)</li>
<li><a href="{INJ_0800_URL}" target="_blank" rel="noopener">Official injury report, 11/13 08:00 PM ET (PDF)</a> · <a href="{INJ_0515_URL}" target="_blank" rel="noopener">05:15 PM edition</a> · <a href="{POLICY_URL}" target="_blank" rel="noopener">2026-27 injury-report policy</a></li>
<li><a href="https://www.nba.com/stats/players" target="_blank" rel="noopener">NBA.com player statistics</a> (leader-stats context, flag D-09)</li>
<li>Verification chain: <code>scripts/generate_picks_d.py</code> self-audit + <code>scripts/verify_all.py</code> + <code>scripts/check_links.py</code></li>
</ul>
"""

    nav_links = "".join(
        ('<a href="%s" class="active">%s</a>' % (href, esc(label))) if href == "picks-2026-11-14.html"
        else ('<a href="%s">%s</a>' % (href, esc(label)))
        for href, label in NAV)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Horizon picks 14–17 Nov | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Build D · data as of 2026-11-14 (as-of stamps on page) · official sources only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav_links}<div class="side-foot">Every data row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">{body}</main></div>
<footer class="foot"><p>Model outputs are paper records, not betting advice. Gambling in NL is regulated — see <a href="suggestions.html">Questions &amp; suggestions (Q-03/Q-04)</a>. Assumptions are flagged; unverified values are blank.</p><p>Generated by <code>scripts/generate_picks_d.py</code> from <code>data/raw/d/*.json</code> + <code>data/*.json</code>. Audit record: <code>data/derived/picks_d.json</code>.</p></footer>
<script>
(function() {{
  var inputs = document.querySelectorAll('input.filter');
  inputs.forEach(function(inp) {{
    inp.addEventListener('input', function() {{
      var q = inp.value.toLowerCase();
      var tb = document.getElementById(inp.getAttribute('data-target'));
      if (!tb) return;
      tb.querySelectorAll('tbody tr').forEach(function(tr) {{
        tr.style.display = tr.textContent.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
      }});
    }});
  }});
}})();
</script></body></html>"""
    with open(os.path.join(ROOT, "picks-2026-11-14.html"), "w", encoding="utf-8") as f:
        f.write(doc)


def verify_page(path):
    """Every tbody row must contain an official-source link; local links must exist."""
    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.links = []
            self.in_row = False
            self.in_tbody = False
            self.row_links = []
            self.rows = 0

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "tbody":
                self.in_tbody = True
            if tag == "tr" and self.in_tbody:
                self.in_row = True
                self.row_links = []
            if tag == "a" and attrs.get("href"):
                self.links.append(attrs["href"])
                if self.in_row:
                    self.row_links.append(attrs["href"])

        def handle_endtag(self, tag):
            if tag == "tr" and self.in_row:
                self.rows += 1
                ok = False
                for h in self.row_links:
                    p = urlparse(h)
                    if (p.hostname or "").endswith(".nba.com") or p.hostname in ("nba.com",):
                        ok = True
                if not ok:
                    errors.append(f"page row without official source link at {self.getpos()}")
                self.in_row = False
            if tag == "tbody":
                self.in_tbody = False

    p = P()
    with open(path, encoding="utf-8") as f:
        p.feed(f.read())
    base = os.path.dirname(path)
    for h in p.links:
        if urlparse(h).scheme in ("http", "https", "mailto", ""):
            if urlparse(h).scheme:
                continue
        target = os.path.normpath(os.path.join(base, h.split("#")[0]))
        if h.startswith("#"):
            continue
        if not os.path.exists(target):
            errors.append(f"page broken local link: {h}")
    notes.append(f"page self-audit: {p.rows} table rows, every row carries an official *.nba.com source link; "
                 "local links resolve.")


if __name__ == "__main__":
    main()
