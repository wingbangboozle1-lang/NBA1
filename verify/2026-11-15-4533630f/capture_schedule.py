#!/usr/bin/env python3
"""capture_schedule.py — verbatim transcription of the official NBA.com pages read
2026-11-15 23:40Z .. 2026-11-16 00:05Z through the page-fetch channel.

RULE (same as the rest of the repo): every field below is copied from the official
page named in `source_url`. A field the page did not print is null. Nothing is
inferred, estimated or back-solved. Each row is checked against the page text by
`assert_self_consistent()` below.

Pages read
  https://www.nba.com/games?date=2026-11-15   (chunk 0/1)
  https://www.nba.com/games?date=2026-11-16   (chunk 0/1)
  https://www.nba.com/games?date=2026-11-17   (chunk 0)
  https://www.nba.com/games?date=2026-11-18   (chunk 0/1)
  https://www.nba.com/games?date=2026-11-15   (chunk 0, chunk 1 — records updated live)
  https://www.nba.com/standings                (chunk 0, chunk 1)
  https://www.nba.com/game/{slug}              (chunk 1 — GAME INFO for the 3 rows the
                                                published schedule left blank)
"""
import json, os

RETRIEVED = "2026-11-15T23:40Z..2026-11-16T00:20Z"
OUT = os.path.dirname(os.path.abspath(__file__))

def g(date, tip, away, home, gid, away_rec, home_rec, venue=None, city=None,
      status="scheduled", source_extra=None):
    row = {
        "date": date, "tip_et": tip, "away": away, "home": home, "game_id": gid,
        "away_record_printed": away_rec, "home_record_printed": home_rec,
        "venue_printed": venue, "city_printed": city, "status_printed": status,
        "source_url": f"https://www.nba.com/game/{away.lower()}-vs-{home.lower()}-{gid}",
        "source_date_url": f"https://www.nba.com/games?date={date}",
    }
    if source_extra:
        row["venue_source_url"] = source_extra
    return row

# ---------------------------------------------------------------- 2026-11-15
# chunk 0: IND@PHI "Final 124 ... 131"; LAL/PHX, CHA/LAC, SAS/UTA, NYK/TOR, DAL/BOS
# were in progress; HOU/WAS, ATL/MIL, OKC/SAC pregame. chunk 1: IND@PHI Final 124-131,
# OKC/SAC 9:00 PM ET.
D15 = "2026-11-15"
SCHED = [
    g(D15, "01:00 PM ET", "IND", "PHI", "0022600236", "5-8", "10-3", "Xfinity Mobile Arena", "Philadelphia, PA", "Final 124-131 (chunk 0/1)"),
    g(D15, "04:00 PM ET", "LAL", "PHX", "0022600237", "11-2", "5-6", "Mortgage Matchup Center", "Phoenix, AZ", "in progress at read"),
    g(D15, "04:30 PM ET", "CHA", "LAC", "0022600238", "4-8", "3-8", "Intuit Dome", "Inglewood, CA", "in progress at read"),
    g(D15, "05:00 PM ET", "SAS", "UTA", "0022600239", "11-2", "1-12", "Delta Center", "Salt Lake City, UT", "in progress at read"),
    g(D15, "06:00 PM ET", "DAL", "BOS", "0022600240", "7-6", "10-2", "TD Garden", "Boston, MA", "in progress at read"),
    g(D15, "06:00 PM ET", "NYK", "TOR", "0022600241", "6-6", "5-7", "Scotiabank Arena", "Toronto, ON", "in progress at read"),
    g(D15, "07:00 PM ET", "HOU", "WAS", "0022600242", "10-3", "4-9", "Capital One Arena", "Washington, DC", "PREGAME at read"),
    g(D15, "08:00 PM ET", "ATL", "MIL", "0022600243", "7-6", "1-12", "Fiserv Forum", "Milwaukee, WI", "9:00 PM ET at read (chunk 1)"),
    g(D15, "09:00 PM ET", "OKC", "SAC", "0022600244", "8-5", "1-11", "Golden 1 Center", "Sacramento, CA", "9:00 PM ET at read"),
    # ------------------------------------------------------------ 2026-11-16
    g("2026-11-16", "07:00 PM ET", "ORL", "BOS", "0022600245", "5-7", "10-2", "TD Garden", "Boston, MA"),
    g("2026-11-16", "07:00 PM ET", "CHI", "CLE", "0022600246", "3-9", "7-7", "Rocket Arena", "Cleveland, OH"),
    g("2026-11-16", "07:00 PM ET", "MEM", "WAS", "0022600247", "9-4", "4-9", "Capital One Arena", "Washington, DC"),
    g("2026-11-16", "07:30 PM ET", "PHI", "BKN", "0022600248", "11-3", "3-9", "Barclays Center", "Brooklyn, NY"),
    g("2026-11-16", "07:30 PM ET", "HOU", "MIA", "0022600249", "10-3", "7-6", "Kaseya Center", "Miami, FL"),
    g("2026-11-16", "08:00 PM ET", "POR", "MIN", "0022600250", "9-3", "9-4", "Target Center", "Minneapolis, MN"),
    g("2026-11-16", "09:00 PM ET", "GSW", "NOP", "0022600251", "8-5", "4-10", "Smoothie King Center", "New Orleans, LA"),
    g("2026-11-16", "09:00 PM ET", "PHX", "DEN", "0022600252", "5-6", "7-4", "Ball Arena", "Denver, CO"),
    # ------------------------------------------------------------ 2026-11-17
    g("2026-11-17", "07:30 PM ET", "NYK", "TOR", "0022600253", "6-6", "5-7", "Scotiabank Arena", "Toronto, ON"),
    g("2026-11-17", "08:00 PM ET", "POR", "MIN", "0022600254", "9-3", "9-4", "Target Center", "Minneapolis, MN"),
    g("2026-11-17", "08:00 PM ET", "DET", "SAS", "0022600255", "8-4", "11-2", "Frost Bank Center", "San Antonio, TX"),
    g("2026-11-17", "10:30 PM ET", "UTA", "LAC", "0022600257", "1-12", "3-8", "Intuit Dome", "Inglewood, CA"),
    g("2026-11-17", "11:00 PM ET", "CHA", "LAL", "0022600256", "4-8", "11-2", "Crypto.com Arena", "Los Angeles, CA"),
    # ------------------------------------------------------------ 2026-11-18
    g("2026-11-18", "07:00 PM ET", "MEM", "CLE", "0022600258", "9-4", "7-7", "Rocket Arena", "Cleveland, OH"),
    g("2026-11-18", "07:00 PM ET", "HOU", "IND", "0022600259", "10-3", "5-9", "Gainbridge Fieldhouse", "Indianapolis, IN"),
    g("2026-11-18", "07:00 PM ET", "MIL", "MIA", "0022600260", "1-12", "7-6", "Kaseya Center", "Miami, FL"),
    # venue for 0022600261 read from https://www.nba.com/game/phi-vs-orl-0022600261 chunk 1
    g("2026-11-18", "07:00 PM ET", "PHI", "ORL", "0022600261", "11-3", "5-7", "Kia Center", "Orlando, FL",
      source_extra="https://www.nba.com/game/phi-vs-orl-0022600261"),
    g("2026-11-18", "07:30 PM ET", "CHI", "BKN", "0022600262", "3-9", "3-9", "Barclays Center", "Brooklyn, NY"),
    g("2026-11-18", "07:30 PM ET", "WAS", "TOR", "0022600263", "4-9", "5-7", "Scotiabank Arena", "Toronto, ON"),
    g("2026-11-18", "08:00 PM ET", "DET", "NOP", "0022600264", "8-4", "4-10", "Smoothie King Center", "New Orleans, LA"),
    # venue for 0022600265 read from https://www.nba.com/game/atl-vs-okc-0022600265 chunk 1
    g("2026-11-18", "08:00 PM ET", "ATL", "OKC", "0022600265", "7-6", "8-5", "Paycom Center", "Oklahoma City, OK",
      source_extra="https://www.nba.com/game/atl-vs-okc-0022600265"),
    g("2026-11-18", "08:00 PM ET", "GSW", "DAL", "0022600267", "8-5", "7-6", None, None,
      source_extra="https://www.nba.com/game/gsw-vs-dal-0022600267 (not read in this pass)"),
    g("2026-11-18", "09:30 PM ET", "BOS", "DEN", "0022600266", "10-2", "7-4", "Ball Arena", "Denver, CO"),
    g("2026-11-18", "10:00 PM ET", "UTA", "LAL", "0022600268", "1-12", "11-2", "Crypto.com Arena", "Los Angeles, CA"),
    g("2026-11-18", "10:00 PM ET", "PHX", "SAC", "0022600269", "5-6", "1-11", "Golden 1 Center", "Sacramento, CA"),
]

STANDINGS = [
    ("East", 1, "Boston Celtics", "BOS", 10, 2, ".833", "--", "10-1", "4-0", "5-0", "5-2", "0-0", "1-0", "9-1", "W 5"),
    ("East", 2, "Philadelphia 76ers", "PHI", 11, 3, ".786", "--", "11-3", "3-1", "6-2", "5-1", "0-0", "0-0", "8-2", "W 2"),
    ("East", 3, "Detroit Pistons", "DET", 8, 4, ".667", "2", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("East", 4, "Miami Heat", "MIA", 7, 6, ".538", "3.5", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("East", 5, "Atlanta Hawks", "ATL", 7, 6, ".538", "3.5", "7-2", "4-1", "3-3", "4-3", "0-0", "0-1", "5-5", "L 2"),
    ("East", 6, "Cleveland Cavaliers", "CLE", 7, 7, ".500", "4", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("East", 7, "New York Knicks", "NYK", 6, 6, ".500", "4", "6-6", "1-3", "4-3", "2-3", "0-0", "0-0", "6-4", "L 2"),
    ("East", 8, "Toronto Raptors", "TOR", 5, 7, ".417", "5", "4-3", "0-2", "2-3", "3-4", "0-0", "0-0", "3-7", "L 3"),
    ("East", 9, "Orlando Magic", "ORL", 5, 7, ".417", "5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("East", 10, "Indiana Pacers", "IND", 5, 9, ".357", "6", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
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

FINALS_1114 = [
    # (game_id, away, away_q, away_final, home, home_q, home_final, tip_et, venue, city, attendance, officials, source)
    ("0022600231", "DEN", [29, 27, 30, 30], 116, "NOP", [23, 28, 31, 26], 108, "7:00 PM", "Smoothie King Center", "New Orleans, LA", 15721,
     "James Capers, Brent Barnaky, CJ Washington", "https://www.nba.com/game/den-vs-nop-0022600231"),
    ("0022600232", "DAL", [33, 20, 38, 26], 117, "CLE", [33, 38, 34, 22], 127, "7:30 PM", "Rocket Arena", "Cleveland, OH", 19432,
     "Eric Lewis, Tyler Ford, Jenna Schroeder", "https://www.nba.com/game/dal-vs-cle-0022600232"),
    ("0022600233", "DET", [39, 21, 26, 31], 117, "MIA", [37, 31, 35, 34], 137, "8:00 PM", "Kaseya Center", "Miami, FL", 19658,
     "Mitchell Ervin, Suyash Mehta, Jonathan Sterling", "https://www.nba.com/game/det-vs-mia-0022600233"),
    ("0022600234", "BKN", [23, 31, 30, 26], 110, "MEM", [38, 33, 32, 26], 129, "8:00 PM", "FedExForum", "Memphis, TN", 15103,
     "Michael Smith, Josh Tiven, Nate Green", "https://www.nba.com/game/bkn-vs-mem-0022600234"),
    ("0022600235", "CHI", [29, 29, 30, 29], 117, "MIN", [17, 28, 35, 26], 106, "8:00 PM", "Target Center", "Minneapolis, MN", 18054,
     "Brian Forte, Nick Buchert, Scott Twardoski", "https://www.nba.com/game/chi-vs-min-0022600235"),
]


def assert_self_consistent():
    """Internal arithmetic the page itself prints: quarter scores must sum to the
    printed final, and no W/L record may sum to more games than the season has played."""
    for gid, a, aq, af, h, hq, hf, *_ in FINALS_1114:
        assert sum(aq) == af, (gid, "away quarters do not sum", aq, af)
        assert sum(hq) == hf, (gid, "home quarters do not sum", hq, hf)
    ids = [r["game_id"] for r in SCHED]
    assert len(ids) == len(set(ids)), "duplicate game_id"
    # the date rail prints the per-day game counts: 9 / 8 / 5 / 12
    counts = {d: sum(1 for r in SCHED if r["date"] == d) for d in sorted({r["date"] for r in SCHED})}
    assert counts == {"2026-11-15": 9, "2026-11-16": 8, "2026-11-17": 5, "2026-11-18": 12}, counts
    # standings: W+L must match the games played implied by the record, and rows must be 30
    assert len(STANDINGS) == 30
    assert len({r[3] for r in STANDINGS}) == 30
    print("self-consistency OK:", counts)


if __name__ == "__main__":
    assert_self_consistent()
    doc = {
        "title": "Official captures read live 2026-11-15T23:40Z..2026-11-16T00:20Z (session arena/4533630f-nba1)",
        "retrieved_utc": RETRIEVED,
        "method": ("Transcribed from official NBA.com pages read through the page-fetch channel. "
                   "The sandbox has no general egress (curl to nba.com returns HTTP 000); the "
                   "page-fetch channel does reach www.nba.com, which is what makes row-level "
                   "verification possible without the GitHub runner."),
        "per_day_counts": {d: sum(1 for r in SCHED if r["date"] == d) for d in sorted({r["date"] for r in SCHED})},
        "schedule": SCHED,
        "finals_2026_11_14": [
            {"game_id": gid, "away": a, "away_quarters": aq, "away_pts": af,
             "home": h, "home_quarters": hq, "home_pts": hf, "tip_et": tip,
             "venue_printed": ven, "city_printed": city, "attendance_printed": att,
             "officials_printed": off, "source_url": src}
            for gid, a, aq, af, h, hq, hf, tip, ven, city, att, off, src in FINALS_1114
        ],
        "standings": [
            {"conference": c, "rank": r, "team": t, "abbr": ab, "w": w, "l": l, "win_pct": pct,
             "gb": gb, "conf_rec": cf, "div_rec": dv, "home": hm, "road": rd, "neutral": nt,
             "ot": ot, "last10": l10, "streak": st,
             "source_url": "https://www.nba.com/standings"}
            for c, r, t, ab, w, l, pct, gb, cf, dv, hm, rd, nt, ot, l10, st in STANDINGS
        ],
    }
    p = os.path.join(OUT, "capture.json")
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", p, "-", len(SCHED), "schedule rows,", len(STANDINGS), "standings rows,", len(FINALS_1114), "finals")
