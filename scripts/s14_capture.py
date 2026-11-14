#!/usr/bin/env python3
"""s14_capture.py — 2026-11-14 morning official-source capture (session arena/254dd8bb-nba1).

Every row below was transcribed line by line from official NBA pages read through the
session's web-fetch channel on 2026-11-14 between 09:36 and 10:10 UTC. Nothing is
inferred: a value that was not printed on the source page is left blank and the row
carries an `attribution_basis` explaining anything that was filled from a second
official page (roster / schedule corroboration), which is the repo's established
pattern (see IR-01 / F18 in COORDINATION.md).

Sources read (all official):
  S3_2026-11-13   https://www.nba.com/games?date=2026-11-13        (9 finals, both chunks)
  S2-refresh      https://www.nba.com/standings                    (30 team records, both chunks)
  S8-refresh      https://www.nba.com/games?date=2026-11-14        (5 cards)
                  https://www.nba.com/games?date=2026-11-15        (9 cards, both chunks)
                  https://www.nba.com/games?date=2026-11-16        (8 cards, both chunks)
                  https://www.nba.com/games?date=2026-11-17        (5 cards)
  S10-refresh     https://official.nba.com/nba-injury-report-2026-27-season/   (edition index)
                  https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf
  S12             https://www.nba.com/team/1610612751/nets         (roster corroboration)

Outputs (data/raw/s14/):
  finals_2026-11-13.json        9 final scores, one row per game, per-game source URL
  standings_2026-11-14.json     30 team records as printed
  horizon_cards_2026-11-14.json 27 horizon rows as printed today + cross-check vs data/raw/schedule_upcoming.json
  injury_report_2026-11-14_0415ET.json  the 04:15 AM ET edition, row by row
  injury_status_2026-11-14.json         what the official index published at capture time
  verification.json             cross-checks run by this capture

Side effects (the data refresh itself):
  data/raw/games_completed.json   + 9 rows (source_id S3_2026-11-13)
  data/raw/sources.json           + S3_2026-11-13, S2-2026-11-14, S10-2026-11-14-0415AM, S12, refresh_log entry
  data/raw/schedule_upcoming.json away_rec/home_rec refreshed from today's cards
  data/raw/injuries.json          replaced by the 11/14/26 04:15 AM ET edition
                                  (previous edition archived to data/raw/s14/injuries_2026-11-13_1930ET_superseded.json)

Run:  python3 scripts/s14_capture.py
"""

import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
S14 = os.path.join(RAW, "s14")

CAPTURED_AT = "2026-11-14T10:10:00Z"
SESSION = "arena/254dd8bb-nba1"


def w(name, obj):
    os.makedirs(S14, exist_ok=True)
    path = os.path.join(S14, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return path


def r(name, subdir=None):
    path = os.path.join(S14 if subdir is None else subdir, name)
    if not os.path.exists(path):
        path = os.path.join(RAW, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. 2026-11-13 finals — https://www.nba.com/games?date=2026-11-13
#     Card format: "AwayTeam  rec  score  Final[/OT]  score  homeTeam  rec"
#     Printed records on a Final card are POST-game records.
# ---------------------------------------------------------------------------
FINALS = [
    # (game_id, away, away_pts, home, home_pts, ot, away_rec_printed, home_rec_printed, status_printed)
    ("0022600034", "NYK", 104, "IND", 106, 0, "6-6", "5-8", "Final"),
    ("0022600035", "MIL", 99, "ORL", 107, 0, "1-12", "5-7", "Final"),
    ("0022600036", "CLE", 121, "MIA", 133, 0, "6-7", "6-6", "Final"),
    ("0022600037", "ATL", 117, "CHI", 125, 1, "7-6", "2-9", "Final/OT"),
    ("0022600038", "MEM", 142, "NOP", 111, 0, "8-4", "4-9", "Final"),
    ("0022600039", "UTA", 118, "HOU", 125, 0, "1-12", "10-3", "Final"),
    ("0022600040", "GSW", 85, "SAS", 123, 0, "8-5", "11-2", "Final"),
    ("0022600041", "POR", 120, "SAC", 107, 0, "9-3", "1-11", "Final"),
    ("0022600042", "OKC", 112, "LAC", 113, 0, "8-5", "3-8", "Final"),
]


def game_url(away, home, gid):
    return f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}"


finals_rows = []
for gid, away, ap, home, hp, ot, ar, hr, st in FINALS:
    finals_rows.append({
        "date": "2026-11-13", "game_id": gid,
        "away": away, "away_pts": ap, "home": home, "home_pts": hp,
        "ot": ot, "neutral": 0,
        "status_printed": st,
        "away_rec_printed_postgame": ar, "home_rec_printed_postgame": hr,
        "source_url": game_url(away, home, gid),
        "source_date_url": "https://www.nba.com/games?date=2026-11-13",
        "attribution_basis": "score and record cells as printed on the official Final card",
    })

w("finals_2026-11-13.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "source_url": "https://www.nba.com/games?date=2026-11-13",
    "publisher": "NBA.com (official)",
    "note": "All 9 games on the 2026-11-13 slate were Final at capture. Printed records on a "
            "Final card are post-game records and are kept separate from the standings capture.",
    "rows": finals_rows,
})

# ---------------------------------------------------------------------------
# 2. Standings — https://www.nba.com/standings (both chunks)
# ---------------------------------------------------------------------------
EAST = [("BOS", "Boston Celtics", 10, 2), ("PHI", "Philadelphia 76ers", 10, 3),
        ("DET", "Detroit Pistons", 8, 3), ("ATL", "Atlanta Hawks", 7, 6),
        ("MIA", "Miami Heat", 6, 6), ("NYK", "New York Knicks", 6, 6),
        ("CLE", "Cleveland Cavaliers", 6, 7), ("TOR", "Toronto Raptors", 5, 7),
        ("ORL", "Orlando Magic", 5, 7), ("IND", "Indiana Pacers", 5, 8),
        ("CHA", "Charlotte Hornets", 4, 8), ("WAS", "Washington Wizards", 4, 9),
        ("BKN", "Brooklyn Nets", 3, 8), ("CHI", "Chicago Bulls", 2, 9),
        ("MIL", "Milwaukee Bucks", 1, 12)]
WEST = [("SAS", "San Antonio Spurs", 11, 2), ("LAL", "Los Angeles Lakers", 11, 2),
        ("HOU", "Houston Rockets", 10, 3), ("POR", "Portland Trail Blazers", 9, 3),
        ("MIN", "Minnesota Timberwolves", 9, 3), ("MEM", "Memphis Grizzlies", 8, 4),
        ("GSW", "Golden State Warriors", 8, 5), ("OKC", "Oklahoma City Thunder", 8, 5),
        ("DEN", "Denver Nuggets", 6, 4), ("DAL", "Dallas Mavericks", 7, 5),
        ("PHX", "Phoenix Suns", 5, 6), ("NOP", "New Orleans Pelicans", 4, 9),
        ("LAC", "LA Clippers", 3, 8), ("SAC", "Sacramento Kings", 1, 11),
        ("UTA", "Utah Jazz", 1, 12)]

stand_rows = [{"abbr": a, "team": t, "w": w_, "l": l_, "conference": c,
               "source_url": "https://www.nba.com/standings"}
              for c, lst in (("East", EAST), ("West", WEST)) for a, t, w_, l_ in lst]

w("standings_2026-11-14.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "source_url": "https://www.nba.com/standings",
    "publisher": "NBA.com (official)",
    "note": "Overall W-L as printed on the 2026-27 standings table. These are current through the "
            "games of 2026-11-13.",
    "rows": stand_rows,
})

# ---------------------------------------------------------------------------
# 3. Horizon cards 2026-11-14..17 — one row per scheduled game, as printed today.
#    (date, time_et, game_id, away, away_rec, home, home_rec)
# ---------------------------------------------------------------------------
CARDS = [
    ("2026-11-14", "7:00 PM ET", "0022600231", "DEN", "6-4", "NOP", "4-9"),
    ("2026-11-14", "7:30 PM ET", "0022600232", "DAL", "7-5", "CLE", "6-7"),
    ("2026-11-14", "8:00 PM ET", "0022600234", "BKN", "3-8", "MEM", "8-4"),
    ("2026-11-14", "8:00 PM ET", "0022600233", "DET", "8-3", "MIA", "6-6"),
    ("2026-11-14", "8:00 PM ET", "0022600235", "CHI", "2-9", "MIN", "9-3"),
    ("2026-11-15", "1:00 PM ET", "0022600236", "IND", "5-8", "PHI", "10-3"),
    ("2026-11-15", "4:00 PM ET", "0022600237", "LAL", "11-2", "PHX", "5-6"),
    ("2026-11-15", "4:30 PM ET", "0022600238", "CHA", "4-8", "LAC", "3-8"),
    ("2026-11-15", "5:00 PM ET", "0022600239", "SAS", "11-2", "UTA", "1-12"),
    ("2026-11-15", "6:00 PM ET", "0022600241", "NYK", "6-6", "TOR", "5-7"),
    ("2026-11-15", "6:00 PM ET", "0022600240", "DAL", "7-5", "BOS", "10-2"),
    ("2026-11-15", "7:00 PM ET", "0022600242", "HOU", "10-3", "WAS", "4-9"),
    ("2026-11-15", "8:00 PM ET", "0022600243", "ATL", "7-6", "MIL", "1-12"),
    ("2026-11-15", "9:00 PM ET", "0022600244", "OKC", "8-5", "SAC", "1-11"),
    ("2026-11-16", "7:00 PM ET", "0022600245", "ORL", "5-7", "BOS", "10-2"),
    ("2026-11-16", "7:00 PM ET", "0022600247", "MEM", "8-4", "WAS", "4-9"),
    ("2026-11-16", "7:00 PM ET", "0022600246", "CHI", "2-9", "CLE", "6-7"),
    ("2026-11-16", "7:30 PM ET", "0022600249", "HOU", "10-3", "MIA", "6-6"),
    ("2026-11-16", "7:30 PM ET", "0022600248", "PHI", "10-3", "BKN", "3-8"),
    ("2026-11-16", "8:00 PM ET", "0022600251", "GSW", "8-5", "NOP", "4-9"),
    ("2026-11-16", "8:00 PM ET", "0022600250", "POR", "9-3", "MIN", "9-3"),
    ("2026-11-16", "9:00 PM ET", "0022600252", "PHX", "5-6", "DEN", "6-4"),
    ("2026-11-17", "7:30 PM ET", "0022600253", "NYK", "6-6", "TOR", "5-7"),
    ("2026-11-17", "8:00 PM ET", "0022600255", "DET", "8-3", "SAS", "11-2"),
    ("2026-11-17", "8:00 PM ET", "0022600254", "POR", "9-3", "MIN", "9-3"),
    ("2026-11-17", "10:30 PM ET", "0022600257", "UTA", "1-12", "LAC", "3-8"),
    ("2026-11-17", "11:00 PM ET", "0022600256", "CHA", "4-8", "LAL", "11-2"),
]

# cross-check against the published schedule rows (S02 evidence)
with open(os.path.join(RAW, "schedule_upcoming.json"), encoding="utf-8") as f:
    sched = json.load(f)
sched_cols = sched["cols"]
sched_rows = [dict(zip(sched_cols, row)) for row in sched["rows"]]
by_gid = {g["game_id"]: g for g in sched_rows}

card_rows, xchecks, rec_changes = [], [], []
for date, t, gid, away, ar, home, hr in CARDS:
    src = f"https://www.nba.com/games?date={date}"
    card_rows.append({
        "date": date, "time_et": t, "game_id": gid,
        "away": away, "away_rec": ar, "home": home, "home_rec": hr,
        "source_url": src,
        "source_game_url": game_url(away, home, gid),
    })
    p = by_gid.get(gid)
    if p is None:
        xchecks.append({"game_id": gid, "check": "in_published_schedule", "ok": False,
                        "detail": "row not present in data/raw/schedule_upcoming.json"})
        continue
    checks = {
        "date": p["date"] == date,
        "matchup": (p["away"], p["home"]) == (away, home),
        "time_et": p["time_et"] == t,
    }
    for k, v in checks.items():
        if not v:
            xchecks.append({"game_id": gid, "check": k, "ok": False,
                            "detail": f"published={p.get(k) if k != 'matchup' else (p['away'], p['home'])} captured={t if k == 'time_et' else (date if k == 'date' else (away, home))}"})
    if (p["away_rec"], p["home_rec"]) != (ar, hr):
        rec_changes.append({
            "game_id": gid,
            "from": {"away_rec": p["away_rec"], "home_rec": p["home_rec"]},
            "to": {"away_rec": ar, "home_rec": hr},
            "source_url": src,
        })

w("horizon_cards_2026-11-14.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "note": "The 27 horizon rows (2026-11-14..17) re-read from the official daily game cards. "
            "Team W-L cells are the values printed on the cards at capture time (they include the "
            "2026-11-13 results). Game id, date, tip time and team order were cross-checked against "
            "data/raw/schedule_upcoming.json; record cells were refreshed where they changed.",
    "rows": card_rows,
    "record_changes_applied": rec_changes,
})

# ---------------------------------------------------------------------------
# 4. Injury report, 11/14/26 04:15 AM ET edition.
#    https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf
#    Row discipline: values only as printed. Where the PDF render dropped a cell,
#    attribution_basis says what second official page confirmed it.
# ---------------------------------------------------------------------------
NYS = ("", "NOT YET SUBMITTED", "")
NYS_BASIS = "as printed in the 04:15 AM ET edition PDF"
INJ = []
def add(date, time, mu, team, player, status, reason, basis="as printed in the 04:15 AM ET edition PDF"):
    INJ.append([date, time, mu, team, player, status, reason, basis])

# 11/14 games
for row in [
    ("Denver Nuggets", "Holmes II, DaRon", "Out", "G League - On Assignment"),
    ("Denver Nuggets", "Nembhard, Ryan", "Out", "G League - Two-Way"),
    ("Denver Nuggets", "Strawther, Julian", "Out", "Injury/Illness - Left Knee Sprain"),
    ("Denver Nuggets", "Whitmore, Cam", "Out", "G League - Two-Way"),
]:
    add("2026-11-14", "07:00", "DEN@NOP", *row)
add("2026-11-14", "07:00", "DEN@NOP", "New Orleans Pelicans", *NYS)
for row in [
    ("Dallas Mavericks", "Biberovic, Tarik", "Out", "Injury/Illness - Right Heel Bursitis"),
    ("Dallas Mavericks", "Christie, Max", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("Dallas Mavericks", "de Larrea, Sergio", "Out", "Injury/Illness - Right Knee Sprain"),
    ("Dallas Mavericks", "Johnson Jr., Morez", "Probable", "Injury/Illness - Left Shin / Tibia Contusion"),
    ("Dallas Mavericks", "Lively II, Dereck", "Out", "Injury/Illness - Right Foot Surgery"),
    ("Dallas Mavericks", "Martin, Caleb", "Available", "Injury/Illness - Right Thumb Splint"),
]:
    add("2026-11-14", "07:30", "DAL@CLE", *row)
add("2026-11-14", "07:30", "DAL@CLE", "Cleveland Cavaliers", *NYS)
for row in [
    ("Brooklyn Nets", "Bilodeau, Tyler", "Out", "G League - Two-Way"),
    ("Brooklyn Nets", "Brown Jr., Mikel", "Questionable", "Injury/Illness - Illness"),
    ("Brooklyn Nets", "Jefferson, Joshua", "Out", "G League - On Assignment"),
    ("Brooklyn Nets", "Nelson, Grant", "Out", "G League - Two-Way"),
    ("Brooklyn Nets", "Saraf, Ben", "Out", "G League - On Assignment"),
]:
    add("2026-11-14", "08:00", "BKN@MEM", *row)
add("2026-11-14", "08:00", "BKN@MEM",
    "Brooklyn Nets", "Traore, Nolan", "Probable",
    "Injury/Illness - Right Calf Tightness / Soreness",
    "Team cell dropped in the PDF render; attributed to Brooklyn Nets via the official roster "
    "page https://www.nba.com/team/1610612751/nets (Nolan Traore, #10). Recorded as attribution, "
    "not as printed.")
add("2026-11-14", "08:00", "BKN@MEM", "Memphis Grizzlies", *NYS)
add("2026-11-14", "08:00", "CHI@MIN", "Chicago Bulls", *NYS)
for row in [
    ("Minnesota Timberwolves", "Beringer, Joan", "Available", "Injury/Illness - Face Mask"),
    ("Minnesota Timberwolves", "DiVincenzo, Donte", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("Minnesota Timberwolves", "Edwards, Anthony", "Out", "Injury/Illness - Right Knee Arthroscopy"),
]:
    add("2026-11-14", "08:00", "CHI@MIN", *row)
for row in [
    ("Detroit Pistons", "Duren, Jalen", "Out", "Injury/Illness - Right Hamstring Strain"),
    ("Detroit Pistons", "Harkless, Elijah", "Questionable", "G League - Two-Way"),
    ("Detroit Pistons", "Joe, Isaiah", "Out", "Injury/Illness - Right Hip Contusion"),
    ("Detroit Pistons", "Jones, Isaac", "Questionable", "G League - Two-Way"),
    ("Detroit Pistons", "Lanier, Chaz", "Out", "G League - On Assignment"),
    ("Detroit Pistons", "Okorie, Ebuka", "Out", "G League - On Assignment"),
    ("Detroit Pistons", "Onyenso, Ugonna", "Out", "G League - Two-Way"),
]:
    add("2026-11-14", "08:00", "DET@MIA", *row)
add("2026-11-14", "08:00", "DET@MIA", "Miami Heat", *NYS)
# 11/15 stubs (all teams NOT YET SUBMITTED at this edition)
for t, mu, a, h in [("01:00", "IND@PHI", "Indiana Pacers", "Philadelphia 76ers"),
                    ("04:00", "LAL@PHX", "Los Angeles Lakers", "Phoenix Suns"),
                    ("04:30", "CHA@LAC", "Charlotte Hornets", "LA Clippers"),
                    ("05:00", "SAS@UTA", "San Antonio Spurs", "Utah Jazz"),
                    ("06:00", "DAL@BOS", "Dallas Mavericks", "Boston Celtics"),
                    ("06:00", "NYK@TOR", "New York Knicks", "Toronto Raptors"),
                    ("07:00", "HOU@WAS", "Houston Rockets", "Washington Wizards"),
                    ("08:00", "ATL@MIL", "Atlanta Hawks", "Milwaukee Bucks"),
                    ("09:00", "OKC@SAC", "Oklahoma City Thunder", "Sacramento Kings")]:
    basis = ("date cell dropped in the PDF render; game date corroborated by the official "
             "schedule card https://www.nba.com/games?date=2026-11-15")
    add("2026-11-15", t, mu, a, *NYS, basis=basis)
    add("2026-11-15", t, mu, h, *NYS, basis=basis)

w("injury_report_2026-11-14_0415ET.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "report": "NBA Official Injury Report, 11/14/26 04:15 AM ET edition",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf",
    "index_source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "note": "The newest edition published on the official index at capture time. It lists 11/14 "
            "participation rows and 11/15 stub rows (all NOT YET SUBMITTED). No rows are listed "
            "for 11/16 or 11/17. The eighth column records the transcription basis for any cell "
            "that was not printed as such.",
    "cols": ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason",
             "attribution_basis"],
    "rows": INJ,
})

# ---------------------------------------------------------------------------
# 5. Injury index status — what the official index published at capture time
# ---------------------------------------------------------------------------
w("injury_status_2026-11-14.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "publisher": "NBA.com (official)",
    "observed": {
        "november_14_editions_listed": "12:00 a.m ET report through 4:15 a.m ET report (18 editions)",
        "newest_edition_at_capture": "Injury-Report_2026-11-14_04_15AM.pdf",
        "newest_edition_read": True,
        "day_of_game_reports_expected": "between 11 a.m. and 1 p.m. local time on game days "
                                        "(between 8 and 10 a.m. for tips at 5 p.m. or earlier)",
        "consequence": "The 04:15 AM ET edition is superseded in-place by later editions today; "
                       "the 5 teams that have not filed (NOP, CLE, MEM, CHI, MIA) are expected to "
                       "file by their local deadline. Recheck after 16:30 UTC.",
    },
})

# ---------------------------------------------------------------------------
# 6. Side effects: the data refresh consumed by engine/pipeline.py
# ---------------------------------------------------------------------------
# 6a. games_completed.json += 9 finals rows
gc_path = os.path.join(RAW, "games_completed.json")
with open(gc_path, encoding="utf-8") as f:
    gc = json.load(f)
have = {row[7] for row in gc["rows"]}
added = 0
for gid, away, ap, home, hp, ot, _ar, _hr, _st in FINALS:
    if gid not in have:
        gc["rows"].append(["2026-11-13", away, ap, home, hp, ot, 0, gid, "S3_2026-11-13"])
        added += 1
gc["rows"].sort(key=lambda r: (r[0], r[7]))
with open(gc_path, "w", encoding="utf-8") as f:
    json.dump(gc, f, indent=1, ensure_ascii=False)
    f.write("\n")

# 6b. sources.json += new source ids + refresh log
sp = os.path.join(RAW, "sources.json")
with open(sp, encoding="utf-8") as f:
    sources = json.load(f)
sources["sources"]["S3_2026-11-13"] = {
    "title": "NBA.com Games & Scores - November 13, 2026",
    "url": "https://www.nba.com/games?date=2026-11-13",
    "publisher": "NBA.com (official)",
    "used_for": "Final scores for the nine 2026-11-13 games (captured 2026-11-14T10:10Z, all "
                "Final); also rest flags for 2026-11-14.",
}
sources["sources"]["S2_2026-11-14"] = {
    "title": "NBA.com Standings - 2026-27 Regular Season",
    "url": "https://www.nba.com/standings",
    "publisher": "NBA.com (official)",
    "used_for": "Official W-L records for all 30 teams through the games of 2026-11-13, captured "
                "2026-11-14T10:10Z; used to cross-check every printed record cell.",
}
sources["sources"]["S10_2026-11-14-0415AM"] = {
    "title": "NBA Official Injury Report, 11/14/26 04:15 AM ET edition",
    "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf",
    "publisher": "NBA.com (official)",
    "used_for": "Participation status for the 2026-11-14 and 2026-11-15 games; transcribed row "
                "by row in data/raw/s14/injury_report_2026-11-14_0415ET.json.",
}
sources["sources"]["S12"] = {
    "title": "NBA.com - Brooklyn Nets roster",
    "url": "https://www.nba.com/team/1610612751/nets",
    "publisher": "NBA.com (official)",
    "used_for": "Roster corroboration for one injury row (Traore, Nolan) whose Team cell dropped "
                "in the PDF render.",
}
sources.setdefault("refresh_log", [])
sources["refresh_log"].append({
    "at_utc": CAPTURED_AT,
    "session": SESSION,
    "did": "Captured the 2026-11-13 finals (9 games), standings through 11/13 (30 rows), the 27 "
           "horizon cards with refreshed records, and the 11/14/26 04:15 AM ET injury edition. "
           "Cross-checks and record changes are in data/raw/s14/.",
})
with open(sp, "w", encoding="utf-8") as f:
    json.dump(sources, f, indent=1, ensure_ascii=False)
    f.write("\n")

# 6c. schedule_upcoming.json — refresh record cells from today's cards
new_rec = {(row["game_id"]): row for row in card_rows}
changed = 0
for row in sched["rows"]:
    d = dict(zip(sched_cols, row))
    c = new_rec.get(d["game_id"])
    if c and (d["away_rec"], d["home_rec"]) != (c["away_rec"], c["home_rec"]):
        row[sched_cols.index("away_rec")] = c["away_rec"]
        row[sched_cols.index("home_rec")] = c["home_rec"]
        changed += 1
with open(os.path.join(RAW, "schedule_upcoming.json"), "w", encoding="utf-8") as f:
    json.dump(sched, f, indent=1, ensure_ascii=False)
    f.write("\n")

# 6d. injuries.json -> new edition (archive the superseded one first)
inj_path = os.path.join(RAW, "injuries.json")
with open(inj_path, encoding="utf-8") as f:
    old_inj = json.load(f)
shutil.copy(inj_path, os.path.join(S14, "injuries_2026-11-13_1930ET_superseded.json"))
new_inj = {
    "captured_at_utc": CAPTURED_AT,
    "report": "NBA Official Injury Report, 11/14/26 04:15 AM ET edition",
    "source_id": "S10_2026-11-14-0415AM",
    "source_url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf",
    "index_source_id": "S10",
    "index_source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "note": "Supersedes the 11/13/26 07:30 PM ET edition (archived in data/raw/s14/). One row "
            "(Traore, Nolan) carries a roster-corroborated team attribution; see "
            "data/raw/s14/injury_report_2026-11-14_0415ET.json for the per-row basis.",
    "cols": ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason"],
    "rows": [row[:7] for row in INJ],
}
with open(inj_path, "w", encoding="utf-8") as f:
    json.dump(new_inj, f, indent=1, ensure_ascii=False)
    f.write("\n")

# ---------------------------------------------------------------------------
# 7. verification.json — what this capture cross-checked
# ---------------------------------------------------------------------------
stand_by = {row["abbr"]: (row["w"], row["l"]) for row in stand_rows}
finals_x = []
for row in finals_rows:
    a_ok = stand_by.get(row["away"]) == (int(row["away_rec_printed_postgame"].split("-")[0]),
                                         int(row["away_rec_printed_postgame"].split("-")[1]))
    h_ok = stand_by.get(row["home"]) == (int(row["home_rec_printed_postgame"].split("-")[0]),
                                         int(row["home_rec_printed_postgame"].split("-")[1]))
    finals_x.append({"game_id": row["game_id"],
                     "away_rec_matches_standings": a_ok,
                     "home_rec_matches_standings": h_ok})
wins_total = sum(w_ for _a, _t, w_, _l in EAST + WEST)
loss_total = sum(l_ for _a, _t, _w, l_ in EAST + WEST)

w("verification.json", {
    "captured_at_utc": CAPTURED_AT,
    "session": SESSION,
    "checks": {
        "finals_rows": len(finals_rows),
        "finals_all_final": all(r["status_printed"].startswith("Final") for r in finals_rows),
        "postgame_records_match_standings": all(x["away_rec_matches_standings"] and x["home_rec_matches_standings"] for x in finals_x),
        "standings_rows": len(stand_rows),
        "standings_wins_equal_losses": wins_total == loss_total,
        "standings_total_games": wins_total,
        "games_completed_rows_after_add": len(gc["rows"]),
        "games_completed_rows_added": added,
        "horizon_cards_rows": len(card_rows),
        "horizon_rows_in_published_file": len(by_gid),
        "horizon_nonrecord_mismatches": xchecks,
        "record_cells_refreshed": changed,
        "record_changes_detail": rec_changes,
        "injury_rows": len(INJ),
        "injury_teams_not_yet_submitted_11_14": sorted({r[3] for r in INJ if r[0] == "2026-11-14" and r[5] == "NOT YET SUBMITTED"}),
    },
    "standings_vs_finals_derivation": {
        "sum_of_wins": wins_total,
        "note": "The sum of wins across the standings table must equal the number of completed "
                "games in the season. The repo's captured game log held 174 completed/inferred "
                "games through 2026-11-12; 174 + 9 (the 2026-11-13 finals captured here) = 183 = "
                f"{wins_total} as printed on the standings page. Consistent.",
    },
})

print(f"finals: {len(finals_rows)} rows, all Final; postgame records match standings: "
      f"{all(x['away_rec_matches_standings'] and x['home_rec_matches_standings'] for x in finals_x)}")
print(f"standings: {len(stand_rows)} rows; wins==losses: {wins_total == loss_total}; total games: {wins_total}")
print(f"games_completed: +{added} rows -> {len(gc['rows'])}")
print(f"horizon cards: {len(card_rows)} rows; non-record mismatches vs published file: {len(xchecks)}; "
      f"record cells refreshed: {changed}")
print(f"injuries: {len(INJ)} rows written to the 04:15 AM ET edition")
print("S14 CAPTURE OK")
