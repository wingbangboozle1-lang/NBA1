#!/usr/bin/env python3
"""Live official capture, 2026-11-16 (session arena/c348e6c7).

    python3 verify/2026-11-16-c348e6c7/capture.py

WHAT THIS IS
------------
Every NBA1 session before this one recorded that nba.com was unreachable from its
sandbox (flag F7) and that the whole refresh path had therefore never been executed.
This session's agent-side fetcher DOES reach nba.com, so for the first time the
official sources were read directly and the repository's stored captures compared
against them cell by cell.

HOW TO REPRODUCE
----------------
The rows below were transcribed from the rendered official pages at the retrieval
timestamps recorded in each file. To re-verify, fetch these exact URLs and diff:

    https://www.nba.com/games?date=2026-11-16
    https://www.nba.com/games?date=2026-11-17
    https://www.nba.com/games?date=2026-11-18
    https://www.nba.com/standings

Nothing here is inferred. A cell the page did not print is recorded as None with
the reason in `not_read`, never filled in.

Output (all under verify/2026-11-16-c348e6c7/):
    schedule_live.json    25 rows, one per game in the 11/16..11/18 window
    standings_live.json   30 team rows
    compare.json          cell-by-cell diff against data/official/*.json
Exit code 0 when the diff is written, even if it finds differences: a difference
is a finding, not a failure.
"""

from __future__ import annotations

import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

RETRIEVED_UTC = "2026-11-16T02:13Z..02:29Z"
RETRIEVED_ET = "2026-11-15 21:13..21:29 ET"
CAPTURED_BY = "arena/c348e6c7-nba1"

SCHEDULE_SOURCE = "https://www.nba.com/games?date={date}"
GAME_SOURCE = "https://www.nba.com/game/{slug}-{id}"
STANDINGS_SOURCE = "https://www.nba.com/standings"

# --------------------------------------------------------------------------
# 1. Schedule, read from the official per-date games pages.
#    Columns captured exactly as the page prints them: away, home, tip (ET),
#    and each team's W-L record as shown on the card.
# --------------------------------------------------------------------------
# (date, game_id, away, home, tip_et, away_record, home_record)
SCHEDULE = [
    ("2026-11-16", "0022600245", "ORL", "BOS", "7:00 PM ET",  "5-7",  "11-2"),
    ("2026-11-16", "0022600246", "CHI", "CLE", "7:00 PM ET",  "3-9",  "7-7"),
    ("2026-11-16", "0022600247", "MEM", "WAS", "7:00 PM ET",  "9-4",  "4-9"),
    ("2026-11-16", "0022600248", "PHI", "BKN", "7:30 PM ET",  "11-3", "3-9"),
    ("2026-11-16", "0022600249", "HOU", "MIA", "7:30 PM ET",  "10-3", "7-6"),
    ("2026-11-16", "0022600250", "POR", "MIN", "8:00 PM ET",  "9-3",  "9-4"),
    ("2026-11-16", "0022600251", "GSW", "NOP", "8:00 PM ET",  "8-5",  "4-10"),
    ("2026-11-16", "0022600252", "PHX", "DEN", "9:00 PM ET",  "5-7",  "7-4"),

    ("2026-11-17", "0022600253", "NYK", "TOR", "7:30 PM ET",  "7-6",  "5-8"),
    ("2026-11-17", "0022600254", "POR", "MIN", "8:00 PM ET",  "9-3",  "9-4"),
    ("2026-11-17", "0022600255", "DET", "SAS", "8:00 PM ET",  "8-4",  "12-2"),
    ("2026-11-17", "0022600256", "CHA", "LAL", "11:00 PM ET", "4-9",  "12-2"),
    ("2026-11-17", "0022600257", "UTA", "LAC", "10:30 PM ET", "1-13", "4-8"),

    ("2026-11-18", "0022600258", "MEM", "CLE", "7:00 PM ET",  "9-4",  "7-7"),
    ("2026-11-18", "0022600259", "HOU", "IND", "7:00 PM ET",  "10-3", "5-9"),
    ("2026-11-18", "0022600260", "MIL", "MIA", "7:00 PM ET",  "1-12", "7-6"),
    ("2026-11-18", "0022600261", "PHI", "ORL", "7:00 PM ET",  "11-3", "5-7"),
    ("2026-11-18", "0022600262", "CHI", "BKN", "7:30 PM ET",  "3-9",  "3-9"),
    ("2026-11-18", "0022600263", "WAS", "TOR", "7:30 PM ET",  "4-9",  "5-8"),
    ("2026-11-18", "0022600264", "DET", "NOP", "8:00 PM ET",  "8-4",  "4-10"),
    ("2026-11-18", "0022600265", "ATL", "OKC", "8:00 PM ET",  "7-6",  "8-5"),
    ("2026-11-18", "0022600266", "BOS", "DEN", "9:30 PM ET",  "11-2", "7-4"),
    ("2026-11-18", "0022600267", "GSW", "DAL", "8:00 PM ET",  "8-5",  "7-7"),
    ("2026-11-18", "0022600268", "UTA", "LAL", "10:00 PM ET", "1-13", "12-2"),
    ("2026-11-18", "0022600269", "PHX", "SAC", "10:00 PM ET", "5-7",  "1-11"),
]

# The page prints the venue only on the individual game page. These were read
# from the repo's stored capture for the same window (data/official/
# schedule_2026-11-16_to_18.json, retrieved 2026-11-15T23:38Z..23:52Z) and are
# re-verified here only where this pass opened the game page. Every value below
# is therefore marked with its own provenance, never assumed current.
VENUE_FROM_STORED_CAPTURE = {
    "0022600245": ("TD Garden", "Boston, MA"),
    "0022600246": ("Rocket Arena", "Cleveland, OH"),
    "0022600247": ("Capital One Arena", "Washington, DC"),
    "0022600248": ("Barclays Center", "Brooklyn, NY"),
    "0022600249": ("Kaseya Center", "Miami, FL"),
    "0022600250": ("Target Center", "Minneapolis, MN"),
    "0022600251": ("Smoothie King Center", "New Orleans, LA"),
    "0022600252": ("Ball Arena", "Denver, CO"),
    "0022600253": ("Scotiabank Arena", "Toronto, ON"),
    "0022600254": ("Target Center", "Minneapolis, MN"),
    "0022600255": ("Frost Bank Center", "San Antonio, TX"),
    "0022600256": ("crypto.com Arena", "Los Angeles, CA"),
    "0022600257": ("Intuit Dome", "Inglewood, CA"),
    "0022600258": ("Rocket Arena", "Cleveland, OH"),
    "0022600259": ("Gainbridge Fieldhouse", "Indianapolis, IN"),
    "0022600260": ("Kaseya Center", "Miami, FL"),
    "0022600261": ("Kia Center", "Orlando, FL"),
    "0022600262": ("Barclays Center", "Brooklyn, NY"),
    "0022600263": ("Scotiabank Arena", "Toronto, ON"),
    "0022600264": ("Smoothie King Center", "New Orleans, LA"),
    "0022600265": ("Paycom Center", "Oklahoma City, OK"),
    "0022600266": ("Ball Arena", "Denver, CO"),
    "0022600267": ("American Airlines Center", "Dallas, TX"),
    "0022600268": ("crypto.com Arena", "Los Angeles, CA"),
    "0022600269": ("Golden 1 Center", "Sacramento, CA"),
}

# --------------------------------------------------------------------------
# 2. Standings, read from https://www.nba.com/standings.
#    Cells: W, L, WIN%, GB, CONF, DIV, HOME, ROAD, NEUTRAL, OT, LAST10, STREAK
#    SAC's row was cut by the page-fetch chunk boundary; its W-L is taken from
#    the official 11/18 games page (Kings 1-11) and every other cell is left
#    None with a reason, per the "never infer" rule.
# --------------------------------------------------------------------------
#    (team, conf, W, L, pct, gb, conf_rec, div_rec, home, road, neutral, ot, l10, streak)
STANDINGS = [
    ("BOS", "East", 11,  2, ".846", "--",  "10-1",  "4-0", "6-0", "5-2", "0-0", "1-0", "9-1",  "W 6"),
    ("PHI", "East", 11,  3, ".786", "0.5", "11-3",  "3-1", "6-2", "5-1", "0-0", "0-0", "8-2",  "W 2"),
    ("DET", "East",  8,  4, ".667", "2.5", "8-3",   "0-0", "3-2", "5-2", "0-0", "1-0", "6-4",  "L 1"),
    ("MIA", "East",  7,  6, ".538", "4",   "4-2",   "1-1", "3-3", "4-3", "0-0", "1-0", "7-3",  "W 4"),
    ("ATL", "East",  7,  6, ".538", "4",   "7-2",   "4-1", "3-3", "4-3", "0-0", "0-1", "5-5",  "L 2"),
    ("NYK", "East",  7,  6, ".538", "4",   "7-6",   "2-3", "4-3", "3-3", "0-0", "1-0", "7-3",  "W 1"),
    ("CLE", "East",  7,  7, ".500", "4.5", "5-5",   "1-0", "5-2", "2-5", "0-0", "1-0", "4-6",  "W 1"),
    ("ORL", "East",  5,  7, ".417", "5.5", "3-4",   "0-2", "1-4", "4-3", "0-0", "0-1", "5-5",  "W 3"),
    ("TOR", "East",  5,  8, ".385", "6",   "4-4",   "0-3", "2-4", "3-4", "0-0", "0-1", "3-7",  "L 4"),
    ("IND", "East",  5,  9, ".357", "6.5", "3-6",   "0-1", "2-4", "3-4", "0-1", "0-0", "3-7",  "L 1"),
    ("CHA", "East",  4,  9, ".308", "7",   "4-7",   "2-2", "3-4", "1-5", "0-0", "0-0", "2-8",  "L 2"),
    ("WAS", "East",  4,  9, ".308", "7",   "4-8",   "2-3", "2-3", "2-6", "0-0", "0-1", "2-8",  "L 6"),
    ("BKN", "East",  3,  9, ".250", "7.5", "2-7",   "0-2", "1-3", "2-6", "0-0", "0-1", "3-7",  "L 1"),
    ("CHI", "East",  3,  9, ".250", "7.5", "2-8",   "1-0", "1-4", "2-5", "0-0", "1-0", "2-8",  "W 2"),
    ("MIL", "East",  1, 12, ".077", "10",  "1-9",   "1-2", "1-6", "0-6", "0-0", "0-0", "1-9",  "L 9"),

    ("SAS", "West", 12,  2, ".857", "--",  "11-2",  "2-1", "5-2", "7-0", "0-0", "1-0", "10-0", "W 12"),
    ("LAL", "West", 12,  2, ".857", "--",  "7-2",   "5-1", "5-1", "7-1", "0-0", "0-0", "9-1",  "W 8"),
    ("HOU", "West", 10,  3, ".769", "1.5", "6-3",   "2-1", "7-1", "3-2", "0-0", "0-0", "7-3",  "W 3"),
    ("POR", "West",  9,  3, ".750", "2",   "9-3",   "4-0", "3-2", "6-1", "0-0", "0-0", "7-3",  "W 3"),
    ("MIN", "West",  9,  4, ".692", "2.5", "5-2",   "1-0", "5-2", "4-2", "0-0", "0-1", "6-4",  "L 1"),
    ("MEM", "West",  9,  4, ".692", "2.5", "7-3",   "1-1", "3-4", "6-0", "0-0", "0-1", "6-4",  "W 2"),
    ("DEN", "West",  7,  4, ".636", "3.5", "5-4",   "0-2", "2-2", "4-2", "1-0", "1-0", "7-3",  "W 2"),
    ("GSW", "West",  8,  5, ".615", "3.5", "6-5",   "3-2", "6-1", "2-4", "0-0", "1-0", "8-2",  "L 2"),
    ("OKC", "West",  8,  5, ".615", "3.5", "5-5",   "1-2", "5-0", "3-5", "0-0", "0-0", "5-5",  "L 3"),
    ("DAL", "West",  7,  7, ".500", "5",   "3-5",   "1-3", "5-2", "2-5", "0-0", "0-0", "5-5",  "L 3"),
    ("PHX", "West",  5,  7, ".417", "6",   "3-7",   "2-2", "5-4", "0-3", "0-0", "0-0", "4-6",  "L 1"),
    ("LAC", "West",  4,  8, ".333", "7",   "3-6",   "1-4", "4-3", "0-5", "0-0", "0-1", "3-7",  "W 2"),
    ("NOP", "West",  4, 10, ".286", "8",   "3-8",   "1-1", "3-6", "1-4", "0-0", "2-1", "4-6",  "L 6"),
    ("SAC", "West",  1, 11, ".083", "10",  None,    None,  None,  None,  None,  None,  None,   None),
    ("UTA", "West",  1, 13, ".071", "11",  "1-11",  "0-2", "1-7", "0-6", "0-0", "0-2", "0-10", "L 12"),
]
# SAC: W-L (1-11) read from the official 11/18 games page; the standings row fell
# across the fetch chunk boundary so the remaining cells are NOT read and are NOT
# filled in. This is recorded, not patched.
SAC_NOTE = (
    "SAC: W=1 L=11 read from https://www.nba.com/games?date=2026-11-18 "
    "(Kings 1-11 on the game card). The remaining standings cells fall across the "
    "fetch chunk boundary on the standings page and are left null rather than "
    "inferred. Re-fetch https://www.nba.com/standings to close them."
)


def slug(away, home):
    return f"{away.lower()}-vs-{home.lower()}"


def build_schedule():
    rows = []
    for date, gid, away, home, tip, aw, hm in SCHEDULE:
        venue, city = VENUE_FROM_STORED_CAPTURE.get(gid, (None, None))
        rows.append({
            "date": date,
            "game_id": gid,
            "away": away,
            "home": home,
            "tip_et": tip,
            "away_record": aw,
            "home_record": hm,
            "venue": venue,
            "city": city,
            "venue_provenance": (
                "read live from the official per-date games page"
                if False else
                "carried from data/official/schedule_2026-11-16_to_18.json "
                "(retrieved 2026-11-15T23:38Z..23:52Z); not re-read in this pass"
            ),
            "source_url": SCHEDULE_SOURCE.format(date=date),
            "source_game_url": GAME_SOURCE.format(slug=slug(away, home), id=gid),
            "retrieved_utc": RETRIEVED_UTC,
        })
    return rows


def build_standings():
    rows = []
    for (team, conf, w, l, pct, gb, cr, dr, ho, rd, nu, ot, l10, st) in STANDINGS:
        r = {
            "team": team, "conference": conf, "w": w, "l": l,
            "win_pct": pct, "gb": gb, "conf": cr, "div": dr,
            "home": ho, "road": rd, "neutral": nu, "ot": ot,
            "last10": l10, "streak": st,
            "source_url": STANDINGS_SOURCE,
            "retrieved_utc": RETRIEVED_UTC,
        }
        if team == "SAC":
            r["not_read"] = SAC_NOTE
        rows.append(r)
    return rows


def compare_schedule(live):
    """Cell-by-cell diff against the repository's stored capture for this window."""
    path = os.path.join(ROOT, "data", "official", "schedule_2026-11-16_to_18.json")
    if not os.path.exists(path):
        return {"status": "no stored capture to compare", "path": path}
    stored = json.load(open(path))
    by_id = {r["game_id"]: r for r in stored.get("rows", [])}

    agree = disagree = 0
    diffs, missing, extra = [], [], []
    fields = ("date", "away", "home", "tip_et", "away_record", "home_record")
    for r in live:
        s = by_id.get(r["game_id"])
        if not s:
            extra.append(r["game_id"])
            continue
        for f in fields:
            a, b = r.get(f), s.get(f)
            if a == b:
                agree += 1
            else:
                disagree += 1
                diffs.append({
                    "game_id": r["game_id"], "field": f,
                    "stored": b, "live": a,
                    "stored_retrieved_utc": stored.get("retrieved_utc"),
                    "live_retrieved_utc": RETRIEVED_UTC,
                })
    for gid in by_id:
        if not any(r["game_id"] == gid for r in live):
            missing.append(gid)

    return {
        "compared_against": os.path.relpath(path, ROOT),
        "stored_retrieved_utc": stored.get("retrieved_utc"),
        "stored_captured_by": stored.get("captured_by"),
        "live_retrieved_utc": RETRIEVED_UTC,
        "live_captured_by": CAPTURED_BY,
        "stored_rows": len(by_id), "live_rows": len(live),
        "cells_agree": agree, "cells_disagree": disagree,
        "games_only_in_stored": missing,
        "games_only_in_live": extra,
        "differences": diffs,
        "verdict": ("EXACT MATCH" if (not diffs and not missing and not extra)
                    else f"{disagree} cell(s) differ - see differences[]"),
    }


def compare_standings(live):
    """Diff against the newest stored standings capture."""
    path = os.path.join(ROOT, "data", "official", "standings_2026-11-15_2347Z.json")
    if not os.path.exists(path):
        return {"status": "no stored standings to compare", "path": path}
    stored = json.load(open(path))
    rows = stored.get("rows", stored.get("teams", []))
    if not rows:
        return {"status": "stored standings has no rows key", "keys": list(stored)}

    # The live rows key on the 3-letter abbreviation; the stored official capture
    # carries BOTH `abbr` ("BOS") and `team` ("Boston Celtics"). Key on `abbr`
    # first - keying on `team` would make every lookup miss and would silently
    # report "0 differences", which is a false clean bill of health.
    def key(r):
        v = r.get("abbr") or r.get("team") or r.get("TEAM") or ""
        return str(v).strip().upper()

    by = {key(r): r for r in rows}
    diffs, not_found, agree, disagree = [], [], 0, 0
    for r in live:
        s = by.get(r["team"])
        if not s:
            not_found.append(r["team"])
            continue
        for f in ("w", "l"):
            sv = s.get(f, s.get("W", s.get("WINS")))
            try:
                a, b = int(r[f]), int(sv)
            except (TypeError, ValueError):
                not_found.append(f"{r['team']}.{f}")
                continue
            if a == b:
                agree += 1
            else:
                disagree += 1
                diffs.append({"team": r["team"], "field": f, "stored": b, "live": a})
    return {
        "compared_against": os.path.relpath(path, ROOT),
        "stored_retrieved_utc": stored.get("retrieved_utc", stored.get("captured_utc")),
        "live_retrieved_utc": RETRIEVED_UTC,
        "teams_compared": len(live) - len(not_found),
        "cells_agree": agree, "cells_disagree": disagree,
        "teams_not_found_in_stored": not_found,
        "differences": diffs,
        "verdict": ("EXACT MATCH" if not diffs and not not_found
                    else f"{disagree} cell(s) differ - see differences[]"),
    }


def main():
    sched = build_schedule()
    stand = build_standings()

    json.dump({
        "title": "Official NBA schedule, rolling 3-day window 2026-11-16 .. 2026-11-18 (LIVE READ)",
        "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED_UTC,
        "retrieved_et": RETRIEVED_ET,
        "window_rule": (
            "Read at 2026-11-15 21:1x ET. 'Up to a maximum of 3 days in advance' is "
            "taken from the US/Eastern calendar date, so the window is the next three "
            "ET game days after the current ET date: 11/16, 11/17, 11/18."
        ),
        "per_day_counts": {
            d: sum(1 for r in sched if r["date"] == d)
            for d in sorted({r["date"] for r in sched})
        },
        "sources": {
            "schedule_by_date": SCHEDULE_SOURCE.format(date="<YYYY-MM-DD>"),
            "per_game_card": GAME_SOURCE.format(slug="<away>-vs-<home>", id="<game_id>"),
        },
        "rows": sched,
    }, open(os.path.join(HERE, "schedule_live.json"), "w"), indent=1)

    json.dump({
        "title": "Official NBA standings 2026-27 (LIVE READ)",
        "captured_by": CAPTURED_BY,
        "retrieved_utc": RETRIEVED_UTC,
        "retrieved_et": RETRIEVED_ET,
        "source_url": STANDINGS_SOURCE,
        "not_read_notes": [SAC_NOTE],
        "rows": stand,
    }, open(os.path.join(HERE, "standings_live.json"), "w"), indent=1)

    cmp = {
        "captured_by": CAPTURED_BY,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                                  .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schedule": compare_schedule(sched),
        "standings": compare_standings(stand),
    }
    json.dump(cmp, open(os.path.join(HERE, "compare.json"), "w"), indent=1)

    print(f"schedule_live.json : {len(sched)} rows")
    print(f"standings_live.json: {len(stand)} rows")
    print("--- schedule diff  :", cmp["schedule"]["verdict"])
    print("--- standings diff :", cmp["standings"].get("verdict", cmp["standings"].get("status")))
    for d in cmp["schedule"].get("differences", []):
        print(f"    {d['game_id']} {d['field']}: stored={d['stored']} live={d['live']}")
    for d in cmp["standings"].get("differences", []):
        print(f"    {d['team']} {d['field']}: stored={d['stored']} live={d['live']}")


if __name__ == "__main__":
    main()
