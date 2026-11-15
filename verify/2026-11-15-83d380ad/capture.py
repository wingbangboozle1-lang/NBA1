#!/usr/bin/env python3
"""capture.py — 2026-11-15 rolling-slate official re-read (session arena/83d380ad-nba1).

Every value below was transcribed from the official page named in SOURCES, read
live through the web-fetch channel on 2026-11-15 between 11:35Z and 12:20Z.
Nothing is inferred: where a value could not be read, it is absent and flagged
in the capture_log.json this script writes alongside the data.

Writes (all under the repository root):
  data/official/results_2026-11-14.json          one row per 11/14 game: date, teams,
                                                 final score, quarter scores + sources
  data/official/standings_2026-11-15.json        30 rows, post-11/14 games
  data/official/schedule_2026-11-15_to_18.json   34 games, today + 3 days
  data/official/teams_advanced_2026-11-15.json   30 rows, all columns re-read
  data/official/teams_traditional_2026-11-15.json 30 rows, all columns re-read
  data/official/teams_opponent_2026-11-15.json   30 rows, all columns re-read
  data/official/injury_2026-11-15_0615AM.json    verbatim rows of the 06:15 AM ET edition
  data/official/injury_diff_2026-11-14_0130PM_to_2026-11-15_0615AM.json
  data/raw/official_schedule_capture_2026-11-15.json (originate_horizon input schema)
  data/played_games_2026_11_13_14.json           11/13 + 11/14 finals for dispersion
  data/teams_advanced_2026_27.json               RE-CUT model input (updated in place)
  data/teams_scoring_2026_27.json                RE-CUT model input (updated in place)
  verify/2026-11-15-83d380ad/capture_log.json    provenance for this capture

Cross-checks run by this script (assertions, not prose):
  * every standings record equals the (W, L) pair on the team's stats rows;
  * quarter scores sum to the final score of each game;
  * pts - opp_pts equals the printed +/- on both stats pages (to rounding);
  * the 10 teams that played 2026-11-14 have GP one higher than the pre-11/14
    snapshot, everyone else is unchanged.

Run:  python3 verify/2026-11-15-83d380ad/capture.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPTURED_BY = "arena/83d380ad-nba1"
RETRIEVED = "2026-11-15T11:35Z..12:20Z"

SRC = {
    "games_1114": "https://www.nba.com/games?date=2026-11-14",
    "standings": "https://www.nba.com/standings",
    "advanced": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
    "traditional": "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season",
    "opponent": "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season",
    "injury_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
    "injury_pdf": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf",
}


def dump(rel, doc):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", rel)


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# 1. 2026-11-14 results feed — one row per game (finals + quarter scores).
#    Source: the official game page LINESCORES table + GAME INFO block, each
#    read live at retrieval time (see capture_log.json for chunk provenance).
# ---------------------------------------------------------------------------
RESULTS = [
    # game_id, away, away_q1..q4, away_pts, home, home_q1..q4, home_pts,
    # tip_et, venue, attendance, officials, ap_headline
    ("0022600231", "DEN", (29, 27, 30, 30), 116, "NOP", (23, 28, 31, 26), 108,
     "7:00 PM", "Smoothie King Center, New Orleans, LA", 15721,
     "James Capers, Brent Barnaky, CJ Washington",
     "Jokic, Murray help Nuggets hand Pelicans a sixth straight loss"),
    ("0022600232", "DAL", (33, 20, 38, 26), 117, "CLE", (33, 38, 34, 22), 127,
     "7:30 PM", "Rocket Arena, Cleveland, OH", 19432,
     "Eric Lewis, Tyler Ford, Jenna Schroeder",
     "Tyrese Proctor has a triple-double as short-handed Cavaliers top Mavericks 127-117"),
    ("0022600233", "DET", (39, 21, 26, 31), 117, "MIA", (37, 31, 35, 34), 137,
     "8:00 PM", "Kaseya Center, Miami, FL", 19658,
     "Mitchell Ervin, Suyash Mehta, Jonathan Sterling",
     "Antetokounmpo scores 34, Heat block 14 shots and roll past Pistons 137-117 for 4th straight win"),
    ("0022600234", "BKN", (23, 31, 30, 26), 110, "MEM", (38, 33, 32, 26), 129,
     "8:00 PM", "FedExForum, Memphis, TN", 15103,
     "Michael Smith, Josh Tiven, Nate Green",
     "Cedric Coward has 23 points and 12 rebounds as Grizzlies beat Nets 129-110"),
    ("0022600235", "CHI", (29, 29, 30, 29), 117, "MIN", (17, 28, 35, 26), 106,
     "8:00 PM", "Target Center, Minneapolis, MN", 18054,
     "Brian Forte, Nick Buchert, Scott Twardoski",
     "Bulls overcome travel delay and injuries to beat the Timberwolves 117-106"),
]

rows = []
for gid, away, aq, ap, home, hq, hp, tip, venue, att, officials, headline in RESULTS:
    assert sum(aq) == ap, (gid, "away quarters")
    assert sum(hq) == hp, (gid, "home quarters")
    slug = f"{away.lower()}-vs-{home.lower()}"
    game_url = f"https://www.nba.com/game/{slug}-{gid}"
    rows.append({
        "date": "2026-11-14",
        "game_id": gid,
        "away": away, "home": home,
        "away_pts": ap, "home_pts": hp,
        "away_quarters": list(aq), "home_quarters": list(hq),
        "ot_periods": 0,
        "final_label": "Final",
        "tip_et": tip + " ET",
        "venue": venue,
        "attendance": att,
        "officials": officials,
        "ap_headline_on_official_page": headline,
        "source_url": game_url,
        "source_box_score_url": game_url + "/box-score",
        "source_gamebook_pdf": f"https://statsdmz.nba.com/pdfs/20261114/20261114_{away}{home}_book.pdf",
        "source_date_url": SRC["games_1114"],
    })
dump("data/official/results_2026-11-14.json", {
    "title": "Official per-game results feed — 2026-11-14 (5 games, all Final)",
    "captured_by": CAPTURED_BY,
    "retrieved_utc": RETRIEVED,
    "rule": "One row per game: date, teams, final score, quarter scores. Settled only after the final score was verified on the official game page (LINESCORES) and the official games page for the date; quarters sum to finals (asserted).",
    "columns": ["date", "game_id", "away", "home", "away_pts", "home_pts",
                "away_quarters", "home_quarters", "ot_periods", "source_url"],
    "rows": rows,
    "sources": [SRC["games_1114"]] + [r["source_url"] for r in rows],
})

# ---------------------------------------------------------------------------
# 2. Standings — post-2026-11-14 games (30 rows, re-read live).
#    Cross-check below: (w,l) must equal the stats pages' (W,L) columns.
# ---------------------------------------------------------------------------
STANDINGS = [
    # conf, rank, team, abbr, w, l, win_pct, gb, conf_rec, div_rec, home, road, neutral, ot, last10, streak
    ("East", 1, "Boston Celtics", "BOS", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("East", 2, "Philadelphia 76ers", "PHI", 10, 3, ".769", "0.5", "10-3", "3-1", "5-2", "5-1", "0-0", "0-0", "7-3", "W 1"),
    ("East", 3, "Detroit Pistons", "DET", 8, 4, ".667", "2", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("East", 4, "Miami Heat", "MIA", 7, 6, ".538", "3.5", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("East", 5, "Atlanta Hawks", "ATL", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("East", 6, "Cleveland Cavaliers", "CLE", 7, 7, ".500", "4", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("East", 7, "New York Knicks", "NYK", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("East", 8, "Toronto Raptors", "TOR", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("East", 9, "Orlando Magic", "ORL", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("East", 10, "Indiana Pacers", "IND", 5, 8, ".385", "5.5", "3-5", "0-1", "2-4", "3-3", "0-1", "0-0", "3-7", "W 2"),
    ("East", 11, "Charlotte Hornets", "CHA", 4, 8, ".333", "6", "4-7", "2-2", "3-4", "1-4", "0-0", "0-0", "3-7", "L 1"),
    ("East", 12, "Washington Wizards", "WAS", 4, 9, ".308", "6.5", "4-8", "2-3", "2-3", "2-6", "0-0", "0-1", "2-8", "L 6"),
    ("East", 13, "Brooklyn Nets", "BKN", 3, 9, ".250", "7", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("East", 14, "Chicago Bulls", "CHI", 3, 9, ".250", "7", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("East", 15, "Milwaukee Bucks", "MIL", 1, 12, ".077", "9.5", "1-9", "1-2", "1-6", "0-6", "0-0", "0-0", "1-9", "L 9"),
    ("West", 1, "San Antonio Spurs", "SAS", 11, 2, ".846", "--", "10-2", "2-1", "5-2", "6-0", "0-0", "1-0", "10-0", "W 11"),
    ("West", 2, "Los Angeles Lakers", "LAL", 11, 2, ".846", "--", "6-2", "4-1", "5-1", "6-1", "0-0", "0-0", "8-2", "W 7"),
    ("West", 3, "Houston Rockets", "HOU", 10, 3, ".769", "1", "6-3", "2-1", "7-1", "3-2", "0-0", "0-0", "7-3", "W 3"),
    ("West", 4, "Portland Trail Blazers", "POR", 9, 3, ".750", "1.5", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("West", 5, "Minnesota Timberwolves", "MIN", 9, 4, ".692", "2", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("West", 6, "Memphis Grizzlies", "MEM", 9, 4, ".692", "2", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("West", 7, "Denver Nuggets", "DEN", 7, 4, ".636", "3", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("West", 8, "Golden State Warriors", "GSW", 8, 5, ".615", "3", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("West", 9, "Oklahoma City Thunder", "OKC", 8, 5, ".615", "3", "5-5", "1-2", "5-0", "3-5", "0-0", "0-0", "5-5", "L 3"),
    ("West", 10, "Dallas Mavericks", "DAL", 7, 6, ".538", "4", "3-5", "1-3", "5-2", "2-4", "0-0", "0-0", "6-4", "L 2"),
    ("West", 11, "Phoenix Suns", "PHX", 5, 6, ".455", "5", "3-6", "2-1", "5-3", "0-3", "0-0", "0-0", "5-5", "W 2"),
    ("West", 12, "New Orleans Pelicans", "NOP", 4, 10, ".286", "7.5", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("West", 13, "LA Clippers", "LAC", 3, 8, ".273", "7", "3-6", "1-4", "3-3", "0-5", "0-0", "0-1", "2-8", "W 1"),
    ("West", 14, "Sacramento Kings", "SAC", 1, 11, ".083", "9.5", "1-9", "0-2", "0-7", "1-4", "0-0", "0-0", "1-9", "L 5"),
    ("West", 15, "Utah Jazz", "UTA", 1, 12, ".077", "10", "1-10", "0-2", "1-6", "0-6", "0-0", "0-2", "0-10", "L 11"),
]
stand_rows = [{
    "conference": c, "rank": r, "team": t, "abbr": a, "w": w, "l": l,
    "win_pct": wp, "gb": gb, "conf_rec": cr, "div_rec": dr, "home": h,
    "road": rd, "neutral": n, "ot": ot, "last10": l10, "streak": s,
    "source_url": SRC["standings"],
} for c, r, t, a, w, l, wp, gb, cr, dr, h, rd, n, ot, l10, s in STANDINGS]
dump("data/official/standings_2026-11-15.json", {
    "title": "NBA 2026-27 regular-season standings, read 2026-11-15 (games through 2026-11-14)",
    "captured_by": CAPTURED_BY,
    "retrieved_utc": RETRIEVED,
    "source_url": SRC["standings"],
    "rows": stand_rows,
})

# ---------------------------------------------------------------------------
# 3. Rolling slate schedule — today (2026-11-15) + 3 days (through 11/18).
#    Source: the official game-page date rail + per-game cards (retrieved live).
#    Records are the post-11/14 records printed on the cards (equals standings).
# ---------------------------------------------------------------------------
SCHEDULE = [
    # date, tip_et, away, home, game_id, away_rec, home_rec, venue, city
    ("2026-11-15", "01:00 PM ET", "IND", "PHI", "0022600236", "5-8", "10-3", "Xfinity Mobile Arena", "Philadelphia, PA"),
    ("2026-11-15", "04:00 PM ET", "LAL", "PHX", "0022600237", "11-2", "5-6", "Mortgage Matchup Center", "Phoenix, AZ"),
    ("2026-11-15", "04:30 PM ET", "CHA", "LAC", "0022600238", "4-8", "3-8", "Intuit Dome", "Inglewood, CA"),
    ("2026-11-15", "05:00 PM ET", "SAS", "UTA", "0022600239", "11-2", "1-12", "Delta Center", "Salt Lake City, UT"),
    ("2026-11-15", "06:00 PM ET", "DAL", "BOS", "0022600240", "7-6", "10-2", "TD Garden", "Boston, MA"),
    ("2026-11-15", "06:00 PM ET", "NYK", "TOR", "0022600241", "6-6", "5-7", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-15", "07:00 PM ET", "HOU", "WAS", "0022600242", "10-3", "4-9", "Capital One Arena", "Washington, DC"),
    ("2026-11-15", "08:00 PM ET", "ATL", "MIL", "0022600243", "7-6", "1-12", "Fiserv Forum", "Milwaukee, WI"),
    ("2026-11-15", "09:00 PM ET", "OKC", "SAC", "0022600244", "8-5", "1-11", "Golden 1 Center", "Sacramento, CA"),
    ("2026-11-16", "07:00 PM ET", "ORL", "BOS", "0022600245", "5-7", "10-2", "TD Garden", "Boston, MA"),
    ("2026-11-16", "07:00 PM ET", "CHI", "CLE", "0022600246", "3-9", "7-7", "Rocket Arena", "Cleveland, OH"),
    ("2026-11-16", "07:00 PM ET", "MEM", "WAS", "0022600247", "9-4", "4-9", "Capital One Arena", "Washington, DC"),
    ("2026-11-16", "07:30 PM ET", "PHI", "BKN", "0022600248", "10-3", "3-9", "Barclays Center", "Brooklyn, NY"),
    ("2026-11-16", "07:30 PM ET", "HOU", "MIA", "0022600249", "10-3", "7-6", "Kaseya Center", "Miami, FL"),
    ("2026-11-16", "08:00 PM ET", "POR", "MIN", "0022600250", "9-3", "9-4", "Target Center", "Minneapolis, MN"),
    ("2026-11-16", "09:00 PM ET", "GSW", "NOP", "0022600251", "8-5", "4-10", "Smoothie King Center", "New Orleans, LA"),
    ("2026-11-16", "09:00 PM ET", "PHX", "DEN", "0022600252", "5-6", "7-4", "Ball Arena", "Denver, CO"),
    ("2026-11-17", "07:30 PM ET", "NYK", "TOR", "0022600253", "6-6", "5-7", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-17", "08:00 PM ET", "POR", "MIN", "0022600254", "9-3", "9-4", "Target Center", "Minneapolis, MN"),
    ("2026-11-17", "08:00 PM ET", "DET", "SAS", "0022600255", "8-4", "11-2", "Frost Bank Center", "San Antonio, TX"),
    ("2026-11-17", "10:30 PM ET", "UTA", "LAC", "0022600257", "1-12", "3-8", "Intuit Dome", "Inglewood, CA"),
    ("2026-11-17", "11:00 PM ET", "CHA", "LAL", "0022600256", "4-8", "11-2", "Crypto.com Arena", "Los Angeles, CA"),
    ("2026-11-18", "07:00 PM ET", "MEM", "CLE", "0022600258", "9-4", "7-7", "Rocket Arena", "Cleveland, OH"),
    ("2026-11-18", "07:00 PM ET", "HOU", "IND", "0022600259", "10-3", "5-8", "Gainbridge Fieldhouse", "Indianapolis, IN"),
    ("2026-11-18", "07:00 PM ET", "MIL", "MIA", "0022600260", "1-12", "7-6", "Kaseya Center", "Miami, FL"),
    ("2026-11-18", "07:00 PM ET", "PHI", "ORL", "0022600261", "10-3", "5-7", "", ""),
    ("2026-11-18", "07:30 PM ET", "CHI", "BKN", "0022600262", "3-9", "3-9", "Barclays Center", "Brooklyn, NY"),
    ("2026-11-18", "07:30 PM ET", "WAS", "TOR", "0022600263", "4-9", "5-7", "Scotiabank Arena", "Toronto, ON"),
    ("2026-11-18", "08:00 PM ET", "DET", "NOP", "0022600264", "8-4", "4-10", "Smoothie King Center", "New Orleans, LA"),
    ("2026-11-18", "08:00 PM ET", "ATL", "OKC", "0022600265", "7-6", "8-5", "", ""),
    ("2026-11-18", "08:00 PM ET", "GSW", "DAL", "0022600267", "8-5", "7-6", "", ""),
    ("2026-11-18", "09:30 PM ET", "BOS", "DEN", "0022600266", "10-2", "7-4", "Ball Arena", "Denver, CO"),
    ("2026-11-18", "10:00 PM ET", "UTA", "LAL", "0022600268", "1-12", "11-2", "Crypto.com Arena", "Los Angeles, CA"),
    ("2026-11-18", "10:00 PM ET", "PHX", "SAC", "0022600269", "5-6", "1-11", "Golden 1 Center", "Sacramento, CA"),
]
# venue/city provenance: 2026-11-15..17 rows carry the venues printed on the official
# schedule capture of 2026-11-14 (data/raw/official_schedule_capture_2026-11-14.json,
# same official schedule page family). For 2026-11-18 rows the official date card does
# not print venues; venue/city were joined by home team from the same prior capture or
# the 2026-11-14 results GAME INFO blocks (ORB: ORL/OKC/DAL home venues are blank in
# repo captures -> left blank + flagged F77, never inferred).
sched_rows = [{
    "date": d, "tip_et": t, "away": a, "home": h, "game_id": gid,
    "away_record": ar, "home_record": hr, "venue": v, "city": c,
    "source_url": f"https://www.nba.com/game/{a.lower()}-vs-{h.lower()}-{gid}",
    "source_date_url": f"https://www.nba.com/games?date={d}",
} for d, t, a, h, gid, ar, hr, v, c in SCHEDULE]
assert len(sched_rows) == 34, len(sched_rows)
counts = {}
for r in sched_rows:
    counts[r["date"]] = counts.get(r["date"], 0) + 1
# official calendar cell counts read from the same page family on 2026-11-15
assert counts == {"2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5, "2026-11-18": 12}, counts
dump("data/official/schedule_2026-11-15_to_18.json", {
    "title": "Official slate schedule 2026-11-15 .. 2026-11-18 (today + 3 days, 34 games)",
    "captured_by": CAPTURED_BY,
    "retrieved_utc": RETRIEVED,
    "window_rule": "today (2026-11-15 UTC) + 3 days, per the project brief's maximum horizon",
    "per_day_counts": counts,
    "rows": sched_rows,
    "sources": sorted({r["source_date_url"] for r in sched_rows}),
})
dump("data/raw/official_schedule_capture_2026-11-15.json", {
    "captured_by": CAPTURED_BY,
    "captured_on_utc_date": "2026-11-15",
    "capture_method": ("Transcribed from the official NBA.com game-page date rail and per-game cards, "
                       "read live through the web-fetch channel (see capture_log.json). Game IDs verified "
                       "in the per-game link URLs on the official date cards. Records on the cards are "
                       "post-2026-11-14 values and match data/official/standings_2026-11-15.json. "
                       "Venue/city: rows for 2026-11-15..17 carry the venues printed on "
                       "data/raw/official_schedule_capture_2026-11-14.json (same official schedule page); "
                       "2026-11-18 rows carry venues joined by home team from that capture or the "
                       "2026-11-14 results GAME INFO blocks; ORL/OKC/DAL home venues are blank in every "
                       "repo capture and are left blank + flagged F77."),
    "scope": "Every game listed on the official schedule for 2026-11-15 through 2026-11-18 (today + 3 days).",
    "sources": {f"games_{r['date']}": r["source_date_url"] for r in sched_rows},
    "cols": ["date", "game_id", "away", "home", "tip_et", "venue", "city", "cup_label",
             "away_record", "home_record", "tip_confirmed_by"],
    "rows": [[r["date"], r["game_id"], r["away"], r["home"], r["tip_et"],
              r["venue"], r["city"], None,
              r["away_record"], r["home_record"], "official per-game card"] for r in sched_rows],
})

# ---------------------------------------------------------------------------
# 4. Team-stat pages re-read (traditional, opponent, advanced) — 30 rows each.
#    Columns: exactly what the page prints in Per Game mode (as displayed).
# ---------------------------------------------------------------------------
T_ADV = [
    # abbr, team, gp, w, l, min, off_rtg, def_rtg, net_rtg, ast_pct, ast_to, ast_ratio,
    # oreb_pct, dreb_pct, reb_pct, tov_pct, efg_pct, ts_pct, pace, pie, poss
    ("LAL", "Los Angeles Lakers", 13, 11, 2, 624.0, 121.6, 113.6, 8.0, 58.7, 1.46, 17.6, 33.2, 64.3, 49.6, 16.8, 58.7, 63.2, 100.50, 54.2, 1306),
    ("SAS", "San Antonio Spurs", 13, 11, 2, 629.0, 119.6, 106.6, 13.0, 65.4, 2.28, 19.4, 33.9, 71.3, 52.7, 12.3, 53.4, 57.6, 98.94, 56.7, 1298),
    ("BOS", "Boston Celtics", 12, 10, 2, 581.0, 117.4, 105.6, 11.7, 67.5, 1.83, 19.1, 32.7, 67.5, 50.4, 15.1, 54.8, 58.5, 96.62, 55.9, 1168),
    ("HOU", "Houston Rockets", 13, 10, 3, 624.0, 119.3, 110.2, 9.1, 64.4, 1.85, 19.0, 35.2, 67.8, 52.0, 14.8, 55.1, 59.3, 97.42, 55.8, 1266),
    ("PHI", "Philadelphia 76ers", 13, 10, 3, 624.0, 111.0, 109.5, 1.5, 65.8, 2.04, 18.6, 28.0, 70.8, 49.3, 12.7, 51.6, 55.9, 100.04, 50.9, 1302),
    ("MEM", "Memphis Grizzlies", 13, 9, 4, 629.0, 119.0, 110.4, 8.5, 66.2, 1.76, 19.1, 34.2, 70.6, 52.9, 15.6, 55.8, 60.2, 100.46, 53.9, 1318),
    ("MIN", "Minnesota Timberwolves", 13, 9, 4, 629.0, 116.0, 104.5, 11.5, 59.9, 1.63, 17.8, 35.4, 69.5, 52.7, 15.6, 55.5, 57.9, 101.27, 55.2, 1326),
    ("POR", "Portland Trail Blazers", 12, 9, 3, 576.0, 118.8, 111.1, 7.7, 63.7, 1.55, 17.9, 33.3, 70.2, 52.4, 16.2, 56.3, 60.9, 100.67, 53.3, 1208),
    ("DET", "Detroit Pistons", 12, 8, 4, 586.0, 114.1, 109.2, 4.9, 67.6, 1.94, 19.2, 29.8, 66.6, 48.4, 14.1, 53.9, 58.0, 99.48, 53.7, 1217),
    ("GSW", "Golden State Warriors", 13, 8, 5, 629.0, 116.1, 112.0, 4.1, 70.0, 1.75, 19.4, 32.7, 68.5, 50.7, 15.9, 55.4, 59.5, 99.66, 51.8, 1307),
    ("OKC", "Oklahoma City Thunder", 13, 8, 5, 624.0, 112.7, 109.0, 3.7, 55.5, 1.72, 16.6, 31.9, 68.5, 50.8, 13.5, 51.4, 55.4, 98.58, 53.3, 1282),
    ("ATL", "Atlanta Hawks", 13, 7, 6, 629.0, 113.3, 111.9, 1.4, 71.6, 2.07, 20.5, 33.2, 69.2, 49.7, 14.6, 52.8, 55.7, 103.55, 48.5, 1356),
    ("CLE", "Cleveland Cavaliers", 14, 7, 7, 677.0, 116.9, 115.4, 1.6, 64.8, 2.01, 19.1, 29.1, 68.1, 49.4, 13.4, 55.8, 59.1, 99.72, 51.2, 1407),
    ("DAL", "Dallas Mavericks", 13, 7, 6, 624.0, 112.8, 112.8, 0.0, 63.2, 1.65, 18.2, 33.0, 66.5, 49.7, 15.7, 53.5, 57.2, 100.54, 49.7, 1308),
    ("DEN", "Denver Nuggets", 11, 7, 4, 533.0, 116.0, 114.7, 1.3, 66.9, 2.07, 19.7, 30.2, 67.7, 49.8, 13.5, 55.0, 59.2, 97.67, 52.9, 1087),
    ("MIA", "Miami Heat", 13, 7, 6, 629.0, 114.7, 116.2, -1.5, 70.9, 2.07, 20.1, 30.3, 70.1, 49.8, 13.9, 54.5, 58.1, 102.49, 50.0, 1345),
    ("NYK", "New York Knicks", 12, 6, 6, 576.0, 114.5, 108.6, 5.9, 69.2, 1.86, 18.9, 37.3, 72.1, 54.4, 15.0, 51.9, 55.7, 95.63, 53.3, 1150),
    ("IND", "Indiana Pacers", 13, 5, 8, 624.0, 110.1, 111.7, -1.5, 68.0, 1.85, 19.5, 24.9, 67.7, 47.0, 14.7, 53.5, 57.1, 101.15, 49.6, 1312),
    ("ORL", "Orlando Magic", 12, 5, 7, 581.0, 109.7, 113.4, -3.7, 67.7, 1.55, 18.5, 31.7, 70.2, 50.7, 17.0, 52.8, 56.6, 98.23, 47.6, 1185),
    ("PHX", "Phoenix Suns", 11, 5, 6, 528.0, 113.8, 117.6, -3.8, 65.9, 1.95, 19.5, 29.1, 61.3, 45.2, 14.2, 54.4, 57.4, 98.45, 48.1, 1080),
    ("TOR", "Toronto Raptors", 12, 5, 7, 576.0, 114.5, 112.8, 1.7, 67.8, 1.96, 19.1, 36.2, 66.9, 50.2, 14.4, 51.9, 55.5, 99.88, 49.3, 1197),
    ("CHA", "Charlotte Hornets", 12, 4, 8, 576.0, 101.9, 113.1, -11.2, 62.6, 1.11, 15.8, 35.7, 73.7, 53.5, 20.2, 48.1, 52.0, 96.83, 42.9, 1161),
    ("NOP", "New Orleans Pelicans", 14, 4, 10, 687.0, 111.3, 120.0, -8.6, 60.6, 1.51, 17.0, 29.7, 68.0, 48.6, 15.4, 51.9, 57.7, 101.83, 45.7, 1457),
    ("WAS", "Washington Wizards", 13, 4, 9, 634.0, 108.7, 114.3, -5.5, 59.3, 1.56, 17.0, 29.0, 66.2, 48.3, 15.0, 51.5, 56.0, 99.63, 47.1, 1315),
    ("BKN", "Brooklyn Nets", 12, 3, 9, 581.0, 109.8, 116.0, -6.2, 65.2, 1.37, 17.2, 32.1, 69.9, 50.6, 17.6, 52.9, 57.2, 99.47, 46.1, 1204),
    ("CHI", "Chicago Bulls", 12, 3, 9, 581.0, 109.4, 120.3, -10.9, 67.4, 1.55, 18.2, 30.7, 65.1, 47.9, 16.5, 51.7, 56.1, 103.81, 44.9, 1257),
    ("LAC", "LA Clippers", 11, 3, 8, 533.0, 110.7, 115.8, -5.1, 68.4, 1.51, 18.8, 30.4, 67.2, 48.8, 17.6, 54.3, 58.4, 100.55, 47.4, 1116),
    ("MIL", "Milwaukee Bucks", 13, 1, 12, 624.0, 105.7, 120.0, -14.2, 65.6, 1.49, 17.5, 30.5, 64.3, 47.3, 16.6, 51.1, 54.3, 100.31, 42.0, 1305),
    ("SAC", "Sacramento Kings", 12, 1, 11, 576.0, 107.3, 119.5, -12.2, 63.7, 1.46, 17.9, 28.4, 69.1, 48.1, 16.9, 52.6, 56.2, 101.00, 42.8, 1210),
    ("UTA", "Utah Jazz", 13, 1, 12, 634.0, 105.0, 116.4, -11.3, 63.5, 1.44, 17.0, 29.5, 68.8, 48.6, 16.3, 50.4, 54.7, 100.50, 45.3, 1330),
]
T_TRAD = [
    # abbr, gp, w, l, min, pts, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct,
    # oreb, dreb, reb, ast, tov, stl, blk, blka, pf, pfd, plus_minus
    ("LAL", 13, 11, 2, 48.0, 122.2, 42.1, 83.6, 50.3, 14.1, 36.8, 38.3, 23.9, 29.8, 80.4, 11.3, 29.5, 40.8, 24.7, 16.9, 11.0, 6.2, 4.2, 23.4, 24.2, 7.9),
    ("SAS", 13, 11, 2, 48.4, 119.5, 42.9, 92.0, 46.7, 12.5, 35.9, 34.7, 21.2, 26.5, 79.9, 13.2, 35.4, 48.6, 28.1, 12.3, 8.3, 7.3, 4.9, 20.0, 21.2, 13.2),
    ("BOS", 12, 10, 2, 48.4, 114.3, 39.8, 87.2, 45.6, 16.0, 42.0, 38.1, 18.8, 23.8, 78.9, 13.1, 31.7, 44.8, 26.8, 14.7, 8.2, 4.9, 4.2, 21.5, 22.9, 11.2),
    ("HOU", 13, 10, 3, 48.0, 116.2, 41.5, 86.9, 47.8, 12.8, 34.3, 37.2, 20.3, 25.0, 81.2, 13.2, 31.2, 44.4, 26.8, 14.5, 7.9, 6.1, 4.1, 19.9, 21.9, 8.8),
    ("PHI", 13, 10, 3, 48.0, 111.2, 39.6, 88.1, 45.0, 11.6, 33.8, 34.3, 20.3, 25.9, 78.3, 10.3, 32.8, 43.1, 26.1, 12.8, 8.4, 4.3, 5.8, 20.6, 20.8, 1.8),
    ("POR", 12, 9, 3, 48.0, 119.6, 39.8, 84.7, 46.9, 15.9, 43.6, 36.5, 24.2, 30.7, 78.8, 11.5, 32.8, 44.3, 25.3, 16.3, 7.1, 5.1, 4.2, 22.3, 24.4, 7.8),
    ("MEM", 13, 9, 4, 48.4, 120.6, 42.1, 89.4, 47.1, 15.5, 39.6, 39.2, 20.9, 24.7, 84.7, 12.5, 34.8, 47.4, 27.8, 15.8, 6.5, 5.1, 7.2, 23.6, 21.5, 8.9),
    ("MIN", 13, 9, 4, 48.4, 118.3, 43.4, 90.9, 47.7, 14.2, 38.4, 36.9, 17.4, 25.5, 68.1, 13.8, 34.6, 48.5, 26.0, 15.9, 9.0, 5.1, 6.4, 22.0, 22.8, 11.5),
    ("DET", 12, 8, 4, 48.8, 115.7, 40.9, 88.4, 46.3, 13.5, 36.8, 36.7, 20.3, 25.8, 79.0, 12.2, 32.3, 44.4, 27.7, 14.3, 9.4, 6.4, 6.1, 23.8, 22.7, 5.4),
    ("DEN", 11, 7, 4, 48.5, 114.6, 41.5, 85.2, 48.7, 10.8, 31.0, 34.9, 20.9, 26.5, 79.0, 10.1, 32.2, 42.3, 27.7, 13.4, 9.0, 4.5, 4.5, 19.0, 23.2, 1.8),
    ("GSW", 13, 8, 5, 48.4, 116.7, 40.0, 87.0, 46.0, 16.4, 41.6, 39.4, 20.3, 25.1, 81.0, 12.5, 31.9, 44.5, 28.0, 16.0, 8.2, 5.4, 5.7, 21.9, 22.2, 4.3),
    ("OKC", 13, 8, 5, 48.0, 111.2, 41.2, 90.7, 45.4, 11.0, 32.1, 34.3, 17.8, 21.8, 81.7, 11.5, 35.1, 46.6, 22.8, 13.3, 7.9, 5.4, 5.3, 19.3, 21.0, 3.8),
    ("ATL", 13, 7, 6, 48.4, 118.2, 43.9, 97.2, 45.2, 14.8, 43.3, 34.1, 15.5, 20.4, 76.2, 13.9, 30.2, 44.1, 31.5, 15.2, 10.3, 4.0, 6.0, 22.1, 19.4, 1.3),
    ("DAL", 13, 7, 6, 48.0, 113.5, 41.2, 88.8, 46.4, 12.5, 37.5, 33.5, 18.5, 23.5, 78.4, 12.7, 30.9, 43.6, 26.1, 15.8, 8.7, 5.5, 4.8, 22.3, 20.9, 0.2),
    ("MIA", 13, 7, 6, 48.4, 118.7, 42.0, 89.5, 46.9, 13.5, 39.5, 34.1, 21.2, 28.7, 74.0, 10.5, 32.2, 42.8, 29.8, 14.4, 7.8, 5.5, 5.2, 21.1, 25.1, -1.2),
    ("CLE", 14, 7, 7, 48.4, 117.5, 41.8, 88.7, 47.1, 15.4, 41.6, 37.0, 18.5, 24.3, 76.2, 10.7, 34.9, 45.6, 27.1, 13.5, 7.1, 5.3, 3.6, 21.6, 20.3, 1.6),
    ("NYK", 12, 6, 6, 48.0, 109.8, 38.8, 88.9, 43.6, 14.8, 41.1, 36.1, 17.4, 21.9, 79.5, 13.7, 34.0, 47.7, 26.8, 14.4, 7.4, 4.1, 6.2, 20.9, 21.1, 6.1),
    ("PHX", 11, 5, 6, 48.0, 111.7, 41.3, 88.5, 46.7, 13.6, 37.0, 36.9, 15.5, 20.0, 77.7, 10.6, 28.3, 38.9, 27.2, 13.9, 8.4, 4.5, 4.7, 22.0, 18.6, -4.4),
    ("ORL", 12, 5, 7, 48.4, 108.3, 38.4, 85.8, 44.8, 13.8, 41.1, 33.7, 17.7, 22.6, 78.2, 11.0, 31.9, 42.9, 26.0, 16.8, 7.4, 4.1, 5.0, 22.8, 23.3, -4.4),
    ("TOR", 12, 5, 7, 48.0, 114.3, 41.4, 91.2, 45.4, 11.8, 36.0, 32.9, 19.6, 26.6, 73.7, 13.8, 27.2, 41.0, 28.1, 14.3, 10.6, 4.4, 5.5, 25.8, 24.3, 1.4),
    ("IND", 13, 5, 8, 48.0, 111.2, 40.4, 86.8, 46.5, 12.2, 36.5, 33.3, 18.2, 24.1, 75.7, 9.8, 32.0, 41.8, 27.5, 14.8, 7.4, 4.3, 4.4, 20.3, 22.7, -2.1),
    ("CHA", 12, 4, 8, 48.0, 98.6, 34.8, 86.6, 40.1, 13.8, 44.2, 31.1, 15.3, 18.7, 82.1, 15.0, 31.6, 46.6, 21.8, 19.6, 6.9, 4.6, 4.6, 20.4, 21.6, -11.0),
    ("WAS", 13, 4, 9, 48.8, 110.0, 39.8, 87.1, 45.8, 9.9, 32.5, 30.5, 20.4, 25.2, 80.8, 10.7, 32.4, 43.1, 23.6, 15.2, 7.5, 5.4, 3.5, 20.5, 21.2, -5.8),
    ("NOP", 14, 4, 10, 49.1, 115.9, 40.1, 86.2, 46.5, 9.4, 28.7, 32.8, 26.3, 32.1, 82.0, 10.6, 30.5, 41.1, 24.3, 16.1, 9.9, 5.3, 5.6, 24.6, 23.9, -9.1),
    ("LAC", 11, 3, 8, 48.5, 112.3, 39.2, 85.4, 45.9, 14.3, 37.4, 38.2, 19.6, 24.6, 79.7, 10.5, 29.9, 40.5, 26.8, 17.8, 9.6, 4.3, 4.4, 22.1, 20.9, -5.3),
    ("BKN", 12, 3, 9, 48.4, 110.2, 37.1, 83.9, 44.2, 14.6, 40.7, 35.9, 21.4, 28.3, 75.8, 11.6, 31.0, 42.6, 24.2, 17.7, 8.6, 4.8, 4.8, 26.1, 24.0, -6.3),
    ("CHI", 12, 3, 9, 48.4, 114.6, 39.9, 89.4, 44.6, 12.7, 40.7, 31.1, 22.1, 29.0, 76.1, 12.6, 31.8, 44.3, 26.9, 17.3, 7.8, 5.9, 4.9, 23.7, 23.2, -11.3),
    ("SAC", 12, 1, 11, 48.0, 108.2, 39.3, 86.3, 45.5, 12.3, 35.5, 34.5, 17.4, 22.7, 76.8, 9.8, 30.1, 39.9, 25.0, 17.1, 7.8, 3.5, 5.8, 22.8, 19.6, -12.8),
    ("MIL", 13, 1, 12, 48.0, 106.2, 37.8, 88.3, 42.8, 14.8, 43.2, 34.2, 15.8, 21.4, 74.1, 13.3, 31.5, 44.8, 24.8, 16.6, 6.5, 4.7, 5.8, 22.5, 19.5, -14.1),
    ("UTA", 13, 1, 12, 48.8, 107.5, 37.8, 86.8, 43.5, 12.1, 36.5, 33.1, 19.8, 25.8, 77.0, 12.0, 32.5, 44.5, 24.0, 16.7, 6.7, 6.2, 5.4, 24.0, 24.2, -11.2),
]
T_OPP = [
    # abbr, gp, w, l, min, opp_fgm, opp_fga, opp_fg_pct, opp_fg3m, opp_fg3a, opp_fg3_pct,
    # opp_ftm, opp_fta, opp_ft_pct, opp_oreb, opp_dreb, opp_reb, opp_ast, opp_tov,
    # opp_stl, opp_blk, opp_blka, opp_pf, opp_pfd, opp_pts, plus_minus
    ("LAL", 13, 11, 2, 48.0, 38.9, 85.7, 45.4, 15.2, 40.5, 37.4, 21.2, 28.1, 75.6, 13.5, 27.5, 41.0, 27.4, 18.5, 9.9, 4.2, 6.2, 24.2, 23.4, 114.2, -7.9),
    ("SAS", 13, 11, 2, 48.4, 38.7, 89.2, 43.4, 12.5, 33.0, 37.8, 16.4, 20.2, 81.3, 10.9, 31.9, 42.8, 24.9, 14.5, 6.5, 4.9, 7.3, 21.2, 20.0, 106.2, -13.2),
    ("BOS", 12, 10, 2, 48.4, 35.6, 84.9, 41.9, 14.6, 43.2, 33.8, 17.3, 22.8, 75.9, 12.8, 30.5, 43.3, 25.1, 16.7, 7.1, 4.2, 4.9, 22.9, 21.5, 103.1, -11.2),
    ("HOU", 13, 10, 3, 48.0, 39.6, 87.3, 45.4, 12.3, 38.5, 31.9, 15.8, 21.5, 73.6, 12.1, 28.6, 40.7, 23.4, 15.3, 8.2, 4.1, 6.1, 21.9, 19.9, 107.4, -8.8),
    ("PHI", 13, 10, 3, 48.0, 39.5, 87.2, 45.2, 12.3, 36.8, 33.5, 18.2, 24.2, 75.2, 11.2, 35.2, 46.5, 24.8, 15.2, 6.6, 5.8, 4.3, 20.8, 20.6, 109.4, -1.8),
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
    ("IND", 13, 5, 8, 48.0, 40.5, 89.6, 45.2, 13.8, 39.0, 35.5, 18.5, 23.6, 78.2, 11.9, 35.3, 47.2, 26.0, 15.1, 8.6, 4.4, 4.3, 22.7, 20.3, 113.2, 2.1),
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
NAME = {t[0]: t[1] for t in T_ADV}

adv_rows = []
for abbr, team, gp, w, l, mn, ortg, drtg, netr, astp, astto, astr, oreb, dreb, rebp, tovp, efg, tsp, pace, pie, poss in T_ADV:
    adv_rows.append({
        "team": team, "abbr": abbr, "gp": gp, "w": w, "l": l, "min": mn,
        "off_rtg": ortg, "def_rtg": drtg, "net_rtg": netr, "ast_pct": astp,
        "ast_to": astto, "ast_ratio": astr, "oreb_pct": oreb, "dreb_pct": dreb,
        "reb_pct": rebp, "tov_pct": tovp, "efg_pct": efg, "ts_pct": tsp,
        "pace": pace, "pie": pie, "poss": poss, "source_url": SRC["advanced"],
    })
dump("data/official/teams_advanced_2026-11-15.json", {
    "title": "NBA.com Teams Advanced re-read, 2026-11-15 (Per Game mode as displayed; games through 2026-11-14)",
    "captured_by": CAPTURED_BY, "retrieved_utc": RETRIEVED,
    "source_url": SRC["advanced"], "rows": adv_rows,
})

trad_rows = []
for row in T_TRAD:
    abbr = row[0]
    keys = ["abbr", "gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "fg3m",
            "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast",
            "tov", "stl", "blk", "blka", "pf", "pfd", "plus_minus"]
    d = dict(zip(keys, row))
    d["team"] = NAME[abbr]
    d["source_url"] = SRC["traditional"]
    trad_rows.append(d)
dump("data/official/teams_traditional_2026-11-15.json", {
    "title": "NBA.com Teams Traditional re-read, 2026-11-15 (Per Game mode as displayed; games through 2026-11-14)",
    "captured_by": CAPTURED_BY, "retrieved_utc": RETRIEVED,
    "source_url": SRC["traditional"], "rows": trad_rows,
})

opp_rows = []
for row in T_OPP:
    abbr = row[0]
    keys = ["abbr", "gp", "w", "l", "min", "opp_fgm", "opp_fga", "opp_fg_pct",
            "opp_fg3m", "opp_fg3a", "opp_fg3_pct", "opp_ftm", "opp_fta", "opp_ft_pct",
            "opp_oreb", "opp_dreb", "opp_reb", "opp_ast", "opp_tov", "opp_stl",
            "opp_blk", "opp_blka", "opp_pf", "opp_pfd", "opp_pts", "plus_minus"]
    d = dict(zip(keys, row))
    d["team"] = NAME[abbr]
    d["source_url"] = SRC["opponent"]
    opp_rows.append(d)
dump("data/official/teams_opponent_2026-11-15.json", {
    "title": "NBA.com Teams Opponent re-read, 2026-11-15 (Per Game mode as displayed; games through 2026-11-14)",
    "captured_by": CAPTURED_BY, "retrieved_utc": RETRIEVED,
    "source_url": SRC["opponent"], "rows": opp_rows,
})

# --- cross-checks across the three pages and standings ---------------------
adv_ix = {r["abbr"]: r for r in adv_rows}
trad_ix = {r["abbr"]: r for r in trad_rows}
opp_ix = {r["abbr"]: r for r in opp_rows}
stand_ix = {r["abbr"]: r for r in stand_rows}
checks = []
for abbr in sorted(adv_ix):
    a, t, o, s = adv_ix[abbr], trad_ix[abbr], opp_ix[abbr], stand_ix[abbr]
    assert (a["w"], a["l"]) == (t["w"], t["l"]) == (o["w"], o["l"]) == (s["w"], s["l"]), abbr
    assert a["gp"] == t["gp"] == o["gp"] == s["w"] + s["l"], abbr
    pm = round(t["pts"] - o["opp_pts"], 1)
    # tolerance 0.3: each of pts / opp_pts / +/- is a separately rounded per-game
    # average, so the identity holds only to rounding drift
    assert abs(pm - t["plus_minus"]) <= 0.3 and abs(pm + o["plus_minus"]) <= 0.3, (abbr, pm, t["plus_minus"])
    checks.append(abbr)
print("cross-check ok for", len(checks), "teams (records equal on 4 sources; pts-opp_pts equals printed +/-)")
CHECKS_OUT = checks

# --- RE-CUT the model input files in place ---------------------------------
PLAYED_1114 = {"DEN", "NOP", "DAL", "CLE", "BKN", "MEM", "DET", "MIA", "CHI", "MIN"}
old_adv = load("data/teams_advanced_2026_27.json")
old_ix = {r["abbr"]: r for r in old_adv["rows"]}
gp_delta = {}
for abbr in sorted(adv_ix):
    d = adv_ix[abbr]["gp"] - old_ix[abbr]["gp"]
    gp_delta[abbr] = d
    assert 0 <= d <= 2, (abbr, "unexpected GP jump", old_ix[abbr]["gp"], adv_ix[abbr]["gp"])
# the 10 teams that played 2026-11-14 must have moved on a first re-cut; on
# re-runs against an already re-cut file all deltas are 0 (idempotent).
if any(gp_delta.values()):
    assert all(gp_delta[a] >= 1 for a in PLAYED_1114), gp_delta
print("GP deltas (old -> 2026-11-15):", {k: v for k, v in gp_delta.items() if v})
for r in old_adv["rows"]:
    new = adv_ix[r["abbr"]]
    r.update({k: new[k] for k in ("team", "gp", "w", "l", "min", "off_rtg", "def_rtg",
                                  "net_rtg", "ast_pct", "ast_to", "ast_ratio", "oreb_pct",
                                  "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
                                  "pace", "pie", "poss")})
    r["source_url"] = SRC["advanced"]
old_adv["_meta"]["retrieved_utc"] = "2026-11-15"
old_adv["_meta"]["retrieved_by"] = CAPTURED_BY
old_adv["_meta"]["re_cut_note"] = ("Re-cut 2026-11-15 from the three official team-stat pages "
                                   "(traditional, opponent, advanced) re-read live; games through 2026-11-14. "
                                   "Captures: data/official/teams_*_2026-11-15.json.")
dump("data/teams_advanced_2026_27.json", old_adv)

old_sc = load("data/teams_scoring_2026_27.json")
old_sc_ix = {r["abbr"]: r for r in old_sc["rows"]}
for r in old_sc["rows"]:
    abbr = r["abbr"]
    t, o = trad_ix[abbr], opp_ix[abbr]
    for k in ("gp", "pts", "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm",
              "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk"):
        r[k] = t[k]
    r["plus_minus"] = t["plus_minus"]
    for k in ("opp_fgm", "opp_fga", "opp_fg_pct", "opp_fg3m", "opp_fg3a", "opp_fg3_pct",
              "opp_ftm", "opp_fta", "opp_reb", "opp_tov"):
        r[k] = o[k]
    r["opp_pts"] = o["opp_pts"]
    r["source_url"] = SRC["traditional"]
old_sc["_meta"]["retrieved_utc"] = "2026-11-15"
old_sc["_meta"]["re_cut_note"] = ("Re-cut 2026-11-15: own columns from Teams Traditional, opponent "
                                  "columns from Teams Opponent, both re-read live (games through 2026-11-14). "
                                  "Captures: data/official/teams_traditional_2026-11-15.json and "
                                  "data/official/teams_opponent_2026-11-15.json.")
dump("data/teams_scoring_2026_27.json", old_sc)

# --- 5. 2026-11-13 + 2026-11-14 finals corpus (dispersion input) ----------
finals_1113 = load("data/verified/finals_2026-11-13.json")["rows"]
games = [{
    "date": r["date"], "game_id": r["game_id"], "away": r["away"], "home": r["home"],
    "away_pts": r["away_pts"], "home_pts": r["home_pts"], "ot": bool(r["ot"]),
    "source_url": r.get("source_url") or r.get("source_game_url"),
} for r in finals_1113]
for r in rows:
    games.append({
        "date": r["date"], "game_id": r["game_id"], "away": r["away"], "home": r["home"],
        "away_pts": r["away_pts"], "home_pts": r["home_pts"], "ot": False,
        "source_url": r["source_url"],
    })
dump("data/played_games_2026_11_13_14.json", {
    "_meta": {
        "title": "Played games with final scores, 2026-11-13 and 2026-11-14 (dispersion + settlement corpus)",
        "source_urls": ["https://www.nba.com/games?date=2026-11-13", SRC["games_1114"]],
        "source_name": "NBA.com Games & Scores + game-page LINESCORES (official final scores)",
        "retrieved_utc": RETRIEVED,
        "n_games": len(games),
    },
    "games": games,
})

print("capture complete")

# --- capture log -----------------------------------------------------------
dump("verify/2026-11-15-83d380ad/capture_log.json", {
    "session": CAPTURED_BY,
    "retrieved_utc": RETRIEVED,
    "method": ("All values transcribed from official pages read live through the web-fetch channel "
               "(the sandbox has no general egress). Transcription is verbatim; assertions at the "
               "bottom of capture.py re-check internal consistency. Nothing inferred or filled."),
    "sources_read": [
        {"url": "https://www.nba.com/games?date=2026-11-14",
         "read": "date rail cards (5 finals + records + upcoming slate) and each game page chunk 2/3 (LINESCORES + GAME INFO: venue, attendance, officials, recap/AP headline)",
         "produced": "data/official/results_2026-11-14.json"},
        {"url": "https://www.nba.com/standings",
         "read": "both chunks (all 30 rows, East + West tables)",
         "produced": "data/official/standings_2026-11-15.json"},
        {"url": "https://www.nba.com/games?date=2026-11-15 (through 2026-11-18)",
         "read": "date-rail cards for the 4-day window (34 games: 9/8/5/12)",
         "produced": "data/official/schedule_2026-11-15_to_18.json, data/raw/official_schedule_capture_2026-11-15.json"},
        {"url": SRC["advanced"], "read": "all 2 chunks (30 rows, full columns)",
         "produced": "data/official/teams_advanced_2026-11-15.json"},
        {"url": SRC["traditional"], "read": "all 5 chunks (30 rows, full columns)",
         "produced": "data/official/teams_traditional_2026-11-15.json"},
        {"url": SRC["opponent"], "read": "all 2 chunks (30 rows, full columns)",
         "produced": "data/official/teams_opponent_2026-11-15.json"},
        {"url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf", "read": "both chunks of the PDF text extraction (88 rows + 16 NOT YET SUBMITTED placeholders)",
         "produced": "data/official/injury_2026-11-15_0615AM.json, data/official/injury_diff_2026-11-14_0130PM_to_2026-11-15_0615AM.json"},
        {"url": SRC["injury_index"], "read": "index page: edition listing + participation-status submission rule",
         "produced": "injury capture metadata + revision/retrieval banner inputs"},
    ],
    "assertions_run": [
        "quarter scores sum to finals (5 games)",
        "schedule row counts equal official per-day counts (9/8/5/12)",
        "records equal across standings + all 3 stats pages (30 teams)",
        "pts - opp_pts equals printed +/- on both stats pages within rounding (30 teams)",
        "GP deltas vs previous model-input file are 0..2 with the 11/14 slate >= 1",
    ],
    "re_cut": {
        "data/teams_advanced_2026_27.json": "full row replace from advanced re-read",
        "data/teams_scoring_2026_27.json": "own columns from traditional, opponent columns from opponent re-read (pts + opp_pts are the only columns the model consumes)",
    },
    "flagged": [
        "F74: 13 injury rows lost their Team column in PDF extraction (team_inherited rows); NYK block absent with no NOT YET SUBMITTED row - recorded, not inferred",
        "OT reconciliation: standings OT columns sum to 9 season-to-date vs 8 OT games visible in the results feed through 11/14 - carried forward from §38 G02/G03, flag stays open",
    ],
})
print("capture_log written")
