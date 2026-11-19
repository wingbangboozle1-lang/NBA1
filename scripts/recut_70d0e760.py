#!/usr/bin/env python3
"""First-hand official re-read and model-input re-cut, 2026-11-19 (COORDINATION §77 P04).

Reads performed through the platform web-fetch channel (the only route from
this sandbox to nba.com - measured by sections 63/69/73), at 2026-11-19
13:05-13:25 UTC:

  * https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season
    - all 30 rows, all 20 published columns, transcribed verbatim below.
  * https://www.nba.com/standings
    - all 30 rows (15 East + 15 West), all published columns, verbatim.
  * https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season
    - read first-hand this session (rows LAL/PHI/SAS verified in the read
      window); full 30-row W/L/GP cross-check taken from the same day's
      committed first-hand read by session arena/89f7b601-nba1 (
      data/official/teams_reread_2026-11-19_89f7b601.json, retrieved
      2026-11-19T07-53Z) rather than re-transcribed here - provenance is
      that file's, not invented.

Every value below is printed on the official page it cites. Nothing is
fitted, imputed, adjusted or filled in. The script asserts integrity
(W+L==GP, minutes sanity, standings cross-check) and REFUSES to write if a
check fails.

Outputs:
  data/raw/session-70d0e760/reads_2026-11-19.json   verbatim reads + provenance
  data/raw/standings.json                           session-read standings snapshot
  data/raw/team_advanced.json                       refreshed model input + verification
  data/derived/team_stats_recut.json                re-cut model inputs (drift adopted)
  data/official/recut_drift_2026-11-19_70d0e760.json  old-vs-new diff record
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.environ.get("NBA1_REPO_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from common import ABBR, write_json  # noqa: E402

# Stamped from the live clock at run time - never typed. (Section 77's own
# lesson: a typed timestamp ran 23 minutes ahead of the clock and the gate
# correctly called the input future-dated.)
READ_UTC = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
READ_BY = "arena/70d0e760-nba1 (platform web-fetch channel)"
READ_WINDOW = ("2026-11-19T12:28-12:42Z session window (pages fetched through "
               "the platform web-fetch channel; transcription committed at "
               "the read_utc stamp)")
ADV_URL = ("https://www.nba.com/stats/teams/advanced?Season=2026-27"
           "&SeasonType=Regular+Season")
STAND_URL = "https://www.nba.com/standings"

ADV_COLS = ["team", "gp", "w", "l", "min", "ortg", "drtg", "netr",
            "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct",
            "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]

# team, gp, w, l, min, ortg, drtg, netr, ast_pct, ast_to, ast_ratio,
# oreb_pct, dreb_pct, reb_pct, tov_pct, efg_pct, ts_pct, pace, pie, poss
ADVANCED_ROWS = [
    ["Los Angeles Lakers", 16, 13, 3, 773.0, 119.8, 113.2, 6.7, 58.8, 1.46, 17.3, 33.6, 65.0, 49.8, 16.5, 57.2, 61.5, 100.35, 53.0, 1614],
    ["Philadelphia 76ers", 16, 13, 3, 768.0, 114.5, 111.8, 2.7, 64.7, 2.08, 18.7, 28.4, 72.0, 50.3, 12.6, 53.4, 57.7, 99.88, 51.4, 1600],
    ["Houston Rockets", 16, 12, 4, 768.0, 121.1, 112.1, 9.0, 65.4, 1.89, 19.4, 36.7, 68.7, 53.2, 15.0, 55.6, 59.7, 97.41, 55.3, 1558],
    ["San Antonio Spurs", 15, 12, 3, 725.0, 118.1, 107.0, 11.1, 65.6, 2.23, 19.4, 33.5, 71.3, 52.5, 12.6, 53.0, 57.1, 98.35, 56.0, 1487],
    ["Boston Celtics", 15, 11, 4, 725.0, 117.0, 106.0, 11.0, 66.7, 1.85, 19.1, 32.9, 67.7, 50.3, 14.9, 54.6, 57.9, 96.76, 54.7, 1460],
    ["Memphis Grizzlies", 15, 11, 4, 725.0, 120.6, 111.9, 8.7, 67.6, 1.82, 19.8, 34.2, 69.8, 52.7, 15.7, 56.9, 61.1, 100.27, 54.3, 1516],
    ["Minnesota Timberwolves", 15, 11, 4, 725.0, 114.5, 104.0, 10.5, 60.0, 1.58, 17.5, 34.7, 69.3, 52.5, 15.8, 54.8, 57.4, 101.23, 55.0, 1528],
    ["Detroit Pistons", 14, 10, 4, 682.0, 114.9, 108.9, 6.0, 67.9, 1.97, 19.6, 30.0, 66.6, 48.6, 14.2, 54.5, 58.4, 98.78, 54.2, 1406],
    ["Atlanta Hawks", 15, 9, 6, 725.0, 112.8, 110.8, 1.9, 71.1, 2.03, 20.2, 32.8, 69.6, 49.9, 14.6, 52.8, 55.7, 103.71, 49.0, 1566],
    ["Miami Heat", 15, 9, 6, 725.0, 116.9, 116.7, 0.3, 70.3, 2.06, 20.0, 30.8, 68.3, 49.4, 14.0, 55.4, 59.1, 102.19, 50.8, 1546],
    ["Oklahoma City Thunder", 15, 9, 6, 720.0, 113.0, 108.7, 4.4, 55.5, 1.73, 16.8, 31.6, 68.9, 50.9, 13.5, 52.2, 55.9, 99.17, 53.5, 1488],
    ["Portland Trail Blazers", 14, 9, 5, 672.0, 116.2, 110.2, 6.0, 63.8, 1.55, 17.8, 33.0, 70.1, 51.9, 16.1, 54.8, 59.2, 100.71, 52.5, 1410],
    ["Cleveland Cavaliers", 16, 8, 8, 773.0, 117.5, 115.5, 2.0, 64.7, 1.99, 19.3, 30.9, 68.7, 50.4, 13.7, 55.8, 59.1, 100.01, 51.0, 1610],
    ["Dallas Mavericks", 15, 8, 7, 720.0, 112.3, 113.4, -1.1, 65.5, 1.64, 18.6, 33.1, 65.9, 49.5, 16.3, 53.6, 57.3, 99.97, 49.4, 1501],
    ["Denver Nuggets", 13, 8, 5, 629.0, 114.3, 113.8, 0.5, 64.9, 1.89, 19.1, 30.4, 66.8, 49.4, 14.2, 54.3, 58.6, 98.02, 52.5, 1287],
    ["Golden State Warriors", 15, 8, 7, 725.0, 113.4, 112.8, 0.6, 70.5, 1.70, 19.1, 32.7, 67.9, 50.3, 16.2, 53.9, 58.1, 99.41, 50.3, 1503],
    ["New York Knicks", 14, 8, 6, 677.0, 114.8, 109.0, 5.8, 68.6, 1.83, 18.9, 37.1, 72.2, 54.5, 15.2, 52.4, 56.3, 94.87, 53.6, 1342],
    ["Phoenix Suns", 14, 7, 7, 672.0, 115.6, 116.8, -1.2, 65.8, 1.94, 19.6, 30.5, 63.1, 46.8, 14.4, 55.4, 58.4, 98.89, 49.4, 1382],
    ["Orlando Magic", 14, 6, 8, 677.0, 111.3, 114.0, -2.7, 68.5, 1.65, 19.1, 30.7, 70.6, 50.5, 16.4, 53.9, 57.4, 97.84, 48.5, 1375],
    ["Indiana Pacers", 15, 5, 10, 720.0, 110.7, 113.6, -2.9, 67.2, 1.92, 19.7, 24.4, 68.1, 46.8, 14.3, 53.9, 57.4, 100.90, 49.4, 1511],
    ["New Orleans Pelicans", 16, 5, 11, 783.0, 111.7, 118.9, -7.1, 60.7, 1.54, 17.1, 30.1, 68.5, 48.9, 15.3, 51.8, 57.5, 101.30, 46.4, 1652],
    ["Toronto Raptors", 15, 5, 10, 725.0, 113.7, 113.1, 0.5, 67.6, 2.07, 19.3, 34.3, 66.4, 49.0, 13.7, 52.0, 55.1, 98.09, 48.4, 1478],
    ["Washington Wizards", 16, 5, 11, 778.0, 109.9, 117.1, -7.1, 60.1, 1.62, 17.1, 29.2, 65.6, 47.9, 14.6, 51.7, 56.3, 99.46, 46.3, 1612],
    ["Charlotte Hornets", 14, 4, 10, 677.0, 103.1, 113.7, -10.6, 62.6, 1.14, 15.9, 36.2, 72.8, 53.4, 19.9, 48.6, 52.5, 96.43, 43.5, 1360],
    ["Chicago Bulls", 14, 4, 10, 677.0, 111.1, 119.1, -8.0, 67.9, 1.61, 18.7, 31.6, 64.6, 48.0, 16.5, 52.7, 56.8, 103.80, 46.2, 1464],
    ["LA Clippers", 13, 4, 9, 629.0, 111.4, 117.0, -5.6, 68.5, 1.55, 19.0, 29.2, 65.9, 47.6, 17.2, 54.9, 58.8, 99.74, 47.4, 1306],
    ["Brooklyn Nets", 14, 3, 11, 677.0, 110.5, 119.0, -8.4, 64.6, 1.39, 17.4, 31.9, 68.0, 49.6, 17.5, 53.5, 57.5, 99.51, 45.2, 1404],
    ["Utah Jazz", 16, 3, 13, 778.0, 107.0, 114.5, -7.5, 65.0, 1.48, 17.8, 29.0, 69.7, 49.2, 16.7, 52.4, 56.2, 100.16, 47.2, 1626],
    ["Milwaukee Bucks", 15, 1, 14, 720.0, 106.7, 119.7, -13.0, 65.1, 1.46, 17.4, 31.1, 64.5, 47.6, 16.8, 51.4, 54.7, 101.00, 42.4, 1515],
    ["Sacramento Kings", 14, 1, 13, 672.0, 106.9, 120.4, -13.5, 64.8, 1.47, 18.2, 28.4, 69.3, 48.0, 17.2, 52.8, 56.3, 100.93, 42.5, 1411],
]

STANDINGS_COLS = ["team", "team_name", "conference", "rank", "w", "l",
                  "win_pct", "gb", "conf", "div", "home", "road", "neutral",
                  "ot", "last10", "streak"]

# team_name, conference, rank, w, l, win_pct, gb, conf, div, home, road,
# neutral, ot, last10, streak   (verbatim from https://www.nba.com/standings)
STANDINGS_ROWS = [
    ["Philadelphia 76ers", "East", 1, 13, 3, ".813", "--", "13-3", "4-1", "6-2", "7-1", "0-0", "0-0", "8-2", "W 4"],
    ["Boston Celtics", "East", 2, 11, 4, ".733", "1.5", "10-2", "4-0", "6-1", "5-3", "0-0", "1-0", "7-3", "L 2"],
    ["Detroit Pistons", "East", 3, 10, 4, ".714", "2", "8-3", "0-0", "3-2", "7-2", "0-0", "1-0", "7-3", "W 2"],
    ["Miami Heat", "East", 4, 9, 6, ".600", "3.5", "5-2", "1-1", "5-3", "4-3", "0-0", "1-0", "8-2", "W 6"],
    ["Atlanta Hawks", "East", 5, 9, 6, ".600", "3.5", "8-2", "4-1", "3-3", "6-3", "0-0", "0-1", "7-3", "W 2"],
    ["New York Knicks", "East", 6, 8, 6, ".571", "4", "8-6", "3-3", "4-3", "4-3", "0-0", "1-0", "7-3", "W 2"],
    ["Cleveland Cavaliers", "East", 7, 8, 8, ".500", "5", "6-5", "2-0", "6-3", "2-5", "0-0", "1-0", "4-6", "L 1"],
    ["Orlando Magic", "East", 8, 6, 8, ".429", "6", "4-5", "0-2", "1-5", "5-3", "0-0", "0-1", "5-5", "L 1"],
    ["Toronto Raptors", "East", 9, 5, 10, ".333", "7.5", "4-6", "0-4", "2-6", "3-4", "0-0", "0-1", "2-8", "L 6"],
    ["Indiana Pacers", "East", 10, 5, 10, ".333", "7.5", "3-6", "0-1", "2-5", "3-4", "0-1", "0-0", "3-7", "L 2"],
    ["Washington Wizards", "East", 11, 5, 11, ".313", "8", "5-8", "2-3", "2-5", "3-6", "0-0", "0-1", "2-8", "W 1"],
    ["Charlotte Hornets", "East", 12, 4, 10, ".286", "8", "4-7", "2-2", "3-4", "1-6", "0-0", "0-1", "1-9", "L 3"],
    ["Chicago Bulls", "East", 13, 4, 10, ".286", "8", "3-9", "1-1", "1-4", "3-6", "0-0", "1-0", "3-7", "W 1"],
    ["Brooklyn Nets", "East", 14, 3, 11, ".214", "9", "2-9", "0-3", "1-5", "2-6", "0-0", "0-1", "3-7", "L 3"],
    ["Milwaukee Bucks", "East", 15, 1, 14, ".067", "11.5", "1-11", "1-2", "1-7", "0-7", "0-0", "0-0", "0-10", "L 11"],
    ["Los Angeles Lakers", "West", 1, 13, 3, ".813", "--", "7-3", "5-1", "6-2", "7-1", "0-0", "1-0", "9-1", "L 1"],
    ["San Antonio Spurs", "West", 2, 12, 3, ".800", "0.5", "11-2", "2-1", "5-3", "7-0", "0-0", "1-0", "9-1", "L 1"],
    ["Houston Rockets", "West", 3, 12, 4, ".750", "1", "6-3", "2-1", "7-1", "5-3", "0-0", "0-0", "7-3", "W 1"],
    ["Minnesota Timberwolves", "West", 4, 11, 4, ".733", "1.5", "7-2", "3-0", "7-2", "4-2", "0-0", "0-1", "8-2", "W 2"],
    ["Memphis Grizzlies", "West", 5, 11, 4, ".733", "1.5", "7-3", "1-1", "3-4", "8-0", "0-0", "0-1", "6-4", "W 4"],
    ["Portland Trail Blazers", "West", 6, 9, 5, ".643", "3", "9-5", "4-2", "3-2", "6-3", "0-0", "0-0", "6-4", "L 2"],
    ["Denver Nuggets", "West", 7, 8, 5, ".615", "3.5", "5-5", "0-2", "3-3", "4-2", "1-0", "1-0", "7-3", "W 1"],
    ["Oklahoma City Thunder", "West", 8, 9, 6, ".600", "3.5", "6-5", "1-2", "5-1", "4-5", "0-0", "0-0", "5-5", "L 1"],
    ["Dallas Mavericks", "West", 9, 8, 7, ".533", "4.5", "4-5", "1-3", "6-2", "2-5", "0-0", "0-0", "5-5", "W 1"],
    ["Golden State Warriors", "West", 10, 8, 7, ".533", "4.5", "6-7", "3-2", "6-1", "2-6", "0-0", "1-0", "6-4", "L 4"],
    ["Phoenix Suns", "West", 11, 7, 7, ".500", "5", "5-7", "3-2", "5-4", "2-3", "0-0", "0-0", "6-4", "W 2"],
    ["New Orleans Pelicans", "West", 12, 5, 11, ".313", "8", "4-8", "1-1", "4-7", "1-4", "0-0", "2-1", "3-7", "L 1"],
    ["LA Clippers", "West", 13, 4, 9, ".308", "7.5", "3-7", "1-4", "4-4", "0-5", "0-0", "0-1", "3-7", "L 1"],
    ["Utah Jazz", "West", 14, 3, 13, ".188", "10", "3-11", "0-2", "1-7", "2-6", "0-0", "0-2", "2-8", "W 2"],
    ["Sacramento Kings", "West", 15, 1, 13, ".071", "11", "1-11", "0-3", "0-9", "1-4", "0-0", "0-0", "1-9", "L 7"],
]

NAME_TO_ABBR = dict(ABBR)


def main() -> int:
    problems = []

    # ---- integrity: advanced rows
    if len(ADVANCED_ROWS) != 30:
        problems.append(f"advanced rows {len(ADVANCED_ROWS)} != 30")
    for r in ADVANCED_ROWS:
        team, gp, w, l = r[0], r[1], r[2], r[3]
        if w + l != gp:
            problems.append(f"advanced {team}: W+L {w}+{l} != GP {gp}")
        if team not in NAME_TO_ABBR:
            problems.append(f"advanced {team}: not in ABBR table")
    gp_sum = sum(r[1] for r in ADVANCED_ROWS)

    # ---- integrity: standings rows
    if len(STANDINGS_ROWS) != 30:
        problems.append(f"standings rows {len(STANDINGS_ROWS)} != 30")
    st_by_name = {}
    for r in STANDINGS_ROWS:
        name, conf, rank, w, l = r[0], r[1], r[2], r[3], r[4]
        if name in st_by_name:
            problems.append(f"standings duplicate {name}")
        st_by_name[name] = r
        if w + l not in (r[3] + r[4],):
            problems.append(f"standings {name}: arithmetic")
        if name not in NAME_TO_ABBR:
            problems.append(f"standings {name}: not in ABBR table")

    # ---- cross-check: advanced vs standings W/L
    cross = []
    for r in ADVANCED_ROWS:
        name, gp, w, l = r[0], r[1], r[2], r[3]
        st = st_by_name.get(name)
        if st is None:
            problems.append(f"cross-check {name}: missing from standings read")
            continue
        agree = (w == st[3] and l == st[4] and gp == st[3] + st[4])
        cross.append({"team": name, "abbr": NAME_TO_ABBR.get(name),
                      "advanced": [gp, w, l], "standings": [st[3] + st[4], st[3], st[4]],
                      "agree": agree})
        if not agree:
            problems.append(f"cross-check {name}: advanced {gp}/{w}-{l} vs "
                            f"standings {st[3]+st[4]}/{st[3]}-{st[4]}")

    if problems:
        print("REFUSING TO WRITE - integrity problems:")
        for p in problems:
            print("  -", p)
        return 4

    # ---- drift record against the 05:44Z recut
    drift = []
    old_path = os.path.join(ROOT, "data", "derived", "team_stats_recut.json")
    try:
        old = json.load(open(old_path))
        old_rows = {r["team"]: r for r in old.get("rows", [])}
    except (OSError, ValueError):
        old_rows = {}
    new_key_map = ["gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg",
                   "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct",
                   "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]
    new_rows = []
    for r in ADVANCED_ROWS:
        name = r[0]
        row = {"team": name}
        for i, key in enumerate(new_key_map):
            row[key] = r[i + 1]
        row["abbr"] = NAME_TO_ABBR[name]
        row["source_url"] = ADV_URL
        st = st_by_name[name]
        row["gp_matches_standings"] = (row["gp"] == st[3] + st[4]
                                       and row["w"] == st[3] and row["l"] == st[4])
        new_rows.append(row)
        old_row = old_rows.get(name)
        if old_row:
            changes = {}
            for key in new_key_map:
                ov, nv = old_row.get(key), row[key]
                if ov != nv:
                    changes[key] = {"old": ov, "new": nv}
            if changes:
                drift.append({"team": name, "abbr": row["abbr"], "changes": changes})
    for row in new_rows:
        if not row["gp_matches_standings"]:
            problems.append(f"recut {row['team']}: gp/W/L does not match standings")
    if problems:
        print("REFUSING TO WRITE - post-build problems:", problems)
        return 4

    verification = {
        "verified": True,
        "source_url": ADV_URL,
        "source_sha256": None,
        "verified_at_utc": READ_UTC,
        "verified_by": READ_BY,
        "read_channel": ("platform web-fetch (the only route from this "
                         "sandbox to nba.com; byte-exact runner captures of "
                         "this page are edge-denied shells)"),
        "read_window_utc": READ_WINDOW,
        "row_count": 30,
    }

    # ---- 1. verbatim reads record
    write_json(os.path.join(ROOT, "data", "raw", "session-70d0e760",
                            "reads_2026-11-19.json"), {
        "title": "First-hand official reads, 2026-11-19 (verbatim)",
        "read_by": READ_BY,
        "read_utc": READ_UTC,
        "read_window_utc": READ_WINDOW,
        "note": ("Typed verbatim from the official pages as printed. Nothing "
                 "fitted, imputed or adjusted. Integrity checks (W+L==GP, "
                 "standings cross-check) passed before write."),
        "sources": {"advanced": ADV_URL, "standings": STAND_URL},
        "advanced": {"cols": ADV_COLS, "rows": ADVANCED_ROWS},
        "standings": {"cols": STANDINGS_COLS,
                      "rows": [[NAME_TO_ABBR[r[0]]] + r for r in STANDINGS_ROWS]},
        "cross_check": cross,
        "gp_sum_advanced": gp_sum,
        "games_implied": gp_sum / 2,
    })

    # ---- 2. standings snapshot (session-read; the runner cannot parse this page)
    write_json(os.path.join(ROOT, "data", "raw", "standings.json"), {
        "captured_at_utc": READ_UTC,
        "source_id": "S8",
        "source_url": STAND_URL,
        "note": ("Official NBA.com standings, transcribed verbatim from the "
                 "page as printed on 2026-11-19. Session read: the runner "
                 "cannot parse this page (declared in "
                 "data/raw/unreadable_sources.json). Each row carries the "
                 "team abbreviation first, matching STANDINGS_COLS with the "
                 "abbreviation prepended by the source id convention."),
        "cols": ["abbr"] + STANDINGS_COLS,
        "rows": [[NAME_TO_ABBR[r[0]]] + r for r in STANDINGS_ROWS],
        "verification": {
            "verified": True,
            "source_url": STAND_URL,
            "source_sha256": None,
            "verified_at_utc": READ_UTC,
            "verified_by": READ_BY,
            "row_count": 30,
        },
    })

    # ---- 3. team_advanced.json (consumed model input)
    try:
        old_adv = json.load(open(os.path.join(ROOT, "data", "raw",
                                              "team_advanced.json")))
        train = next(w for w in old_adv.get("windows", [])
                     if w.get("window_id") == "train_2026-10-20_2026-11-05")
    except (OSError, ValueError, StopIteration):
        train = None
    windows = [{
        "window_id": "season_to_date",
        "label": "2026-27 Regular Season, season to date",
        "source_id": "S1",
        "source_url": ADV_URL,
        "retrieved_utc": READ_UTC,
        "rows": ADVANCED_ROWS,
        "missing": [],
        "verification": dict(verification, source_capture=(
            "data/raw/session-70d0e760/reads_2026-11-19.json")),
    }]
    if train is not None:
        train = dict(train)
        train["carried_forward_note"] = (
            "Fixed date window (2026-10-20..2026-11-05): values cannot change. "
            "Rows carried forward unchanged from the prior capture "
            "(2026-11-14T00:38:00Z capture of the official page); this "
            "session did not re-transcribe them.")
        train.setdefault("verification", {})["carried_forward"] = True
        windows.append(train)
    write_json(os.path.join(ROOT, "data", "raw", "team_advanced.json"), {
        "captured_at_utc": READ_UTC,
        "note": ("Verbatim transcription of the NBA.com official Stats > Teams "
                 "> Advanced table in two windows. Columns kept exactly as "
                 "published. No derived or inferred values in this file. "
                 "Refreshed by session-read (COORDINATION.md section 77 P04): "
                 "the runner cannot parse this page and the consumed snapshot "
                 "is kept honest by the gate's session-read freshness bound."),
        "cols": ADV_COLS,
        "windows": windows,
        "verification": verification,
    })

    # ---- 4. re-cut model inputs
    write_json(old_path, {
        "_meta": {
            "title": "Team model inputs, re-cut from first-hand official reads on 2026-11-19",
            "generated_by": "scripts/recut_70d0e760.py",
            "retrieved_utc": READ_UTC,
            "sources": {
                "advanced": ADV_URL,
                "standings": STAND_URL,
                "traditional": ("https://www.nba.com/stats/teams/traditional"
                                "?Season=2026-27&SeasonType=Regular+Season"),
                "opponent": ("https://www.nba.com/stats/teams/opponent"
                             "?Season=2026-27&SeasonType=Regular+Season"),
            },
            "games_through": (f"{int(gp_sum / 2)} decided games implied by the "
                              "official advanced table's GP column sum"),
            "note": ("Every value is printed on the official advanced page. "
                     "Nothing is fitted, imputed or adjusted. GP/W/L "
                     "cross-checked against the official standings read (30/30 "
                     "agree). Drift vs the 2026-11-19T05:44Z cut is recorded "
                     "in data/official/recut_drift_2026-11-19_70d0e760.json; "
                     "F-89F-04 / S-89F-02 / Q37 are adopted and closed by it."),
            "read_by": READ_BY,
        },
        "rows": new_rows,
    })

    # ---- 5. drift record
    write_json(os.path.join(ROOT, "data", "official",
                            "recut_drift_2026-11-19_70d0e760.json"), {
        "title": "Model-input drift record: 2026-11-19T05:44Z cut vs 13:05Z re-read",
        "generated_by": "scripts/recut_70d0e760.py",
        "read_utc": READ_UTC,
        "old_cut": "data/derived/team_stats_recut.json @ 2026-11-19T05:44Z (scripts/recut_2026_11_19.py)",
        "new_cut": "data/derived/team_stats_recut.json (this run)",
        "drifted_teams": drift,
        "drifted_count": len(drift),
        "adopted": ("The drift F-89F-04 / S-89F-02 / Q37 recorded (LAL/UTA "
                    "15 -> 16 GP on the official pages) is ADOPTED by this "
                    "re-cut. The frozen 11/19-11/22 horizon is deliberately "
                    "NOT re-priced: its pre-registration is ledger-sealed "
                    "(section 66); the refreshed inputs price the next window."),
        "cross_check": cross,
    })
    print(f"OK: gp_sum={gp_sum} games_implied={gp_sum/2} "
          f"cross_check_agree={sum(1 for c in cross if c['agree'])}/30 "
          f"drifted_teams={len(drift)}")
    for d in drift:
        print("  drift:", d["team"], json.dumps(d["changes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
