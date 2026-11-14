#!/usr/bin/env python3
"""verify_horizon_s934ca56f.py — line-by-line check of the 27-game horizon against
an independent official NBA.com capture made by session arena/934ca56f-nba1.

What it does
  1. Holds the official capture (date, matchup, game_id, tip time, post-11/13 records)
     transcribed by hand from https://www.nba.com/games?date=2026-11-14 … 2026-11-17.
  2. Compares every published horizon row (data/raw/schedule_upcoming.json, which is what
     engine/pipeline.py reads) with that capture, field by field.
  3. Compares the team records the site prints with the official standings page
     https://www.nba.com/standings (also transcribed here) so a stale record is
     identified as stale rather than assumed to be right.
  4. Writes nothing. It only reports, so it is safe to run at any time.

Reading rule: a value is only ever compared with a value read from an official page.
Nothing is inferred. A field that the official page does not print is reported as
"not printed", never as a match.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- official capture
# Transcribed by session arena/934ca56f-nba1 from the official NBA.com Games & Scores
# pages, read 2026-11-14 between 10:24Z and 10:40Z. First team = away, second = home,
# confirmed by the game URL nba.com/game/<away>-vs-<home>-<id>.
# Records are the ones PRINTED ON THE CARD at capture (i.e. after the 11/13 games).
HORIZON_SOURCE = {
    "2026-11-14": "https://www.nba.com/games?date=2026-11-14",
    "2026-11-15": "https://www.nba.com/games?date=2026-11-15",
    "2026-11-16": "https://www.nba.com/games?date=2026-11-16",
    "2026-11-17": "https://www.nba.com/games?date=2026-11-17",
}

OFFICIAL_HORIZON = [
    # (date, away, away_rec, home, home_rec, tip, game_id)
    ("2026-11-14", "DEN", "6-4",  "NOP", "4-9",  "7:00 PM ET",  "0022600231"),
    ("2026-11-14", "DAL", "7-5",  "CLE", "6-7",  "7:30 PM ET",  "0022600232"),
    ("2026-11-14", "DET", "8-3",  "MIA", "6-6",  "8:00 PM ET",  "0022600233"),
    ("2026-11-14", "BKN", "3-8",  "MEM", "8-4",  "8:00 PM ET",  "0022600234"),
    ("2026-11-14", "CHI", "2-9",  "MIN", "9-3",  "8:00 PM ET",  "0022600235"),
    ("2026-11-15", "IND", "5-8",  "PHI", "10-3", "1:00 PM ET",  "0022600236"),
    ("2026-11-15", "LAL", "11-2", "PHX", "5-6",  "4:00 PM ET",  "0022600237"),
    ("2026-11-15", "CHA", "4-8",  "LAC", "3-8",  "4:30 PM ET",  "0022600238"),
    ("2026-11-15", "SAS", "11-2", "UTA", "1-12", "5:00 PM ET",  "0022600239"),
    ("2026-11-15", "DAL", "7-5",  "BOS", "10-2", "6:00 PM ET",  "0022600240"),
    ("2026-11-15", "NYK", "6-6",  "TOR", "5-7",  "6:00 PM ET",  "0022600241"),
    ("2026-11-15", "HOU", "10-3", "WAS", "4-9",  "7:00 PM ET",  "0022600242"),
    ("2026-11-15", "ATL", "7-6",  "MIL", "1-12", "8:00 PM ET",  "0022600243"),
    ("2026-11-15", "OKC", "8-5",  "SAC", "1-11", "9:00 PM ET",  "0022600244"),
    ("2026-11-16", "ORL", "5-7",  "BOS", "10-2", "7:00 PM ET",  "0022600245"),
    ("2026-11-16", "CHI", "2-9",  "CLE", "6-7",  "7:00 PM ET",  "0022600246"),
    ("2026-11-16", "MEM", "8-4",  "WAS", "4-9",  "7:00 PM ET",  "0022600247"),
    ("2026-11-16", "PHI", "10-3", "BKN", "3-8",  "7:30 PM ET",  "0022600248"),
    ("2026-11-16", "HOU", "10-3", "MIA", "6-6",  "7:30 PM ET",  "0022600249"),
    ("2026-11-16", "POR", "9-3",  "MIN", "9-3",  "8:00 PM ET",  "0022600250"),
    ("2026-11-16", "GSW", "8-5",  "NOP", "4-9",  "8:00 PM ET",  "0022600251"),
    ("2026-11-16", "PHX", "5-6",  "DEN", "6-4",  "9:00 PM ET",  "0022600252"),
    ("2026-11-17", "NYK", "6-6",  "TOR", "5-7",  "7:30 PM ET",  "0022600253"),
    ("2026-11-17", "POR", "9-3",  "MIN", "9-3",  "8:00 PM ET",  "0022600254"),
    ("2026-11-17", "DET", "8-3",  "SAS", "11-2", "8:00 PM ET",  "0022600255"),
    ("2026-11-17", "CHA", "4-8",  "LAL", "11-2", "11:00 PM ET", "0022600256"),
    ("2026-11-17", "UTA", "1-12", "LAC", "3-8",  "10:30 PM ET", "0022600257"),
]

# Official standings, https://www.nba.com/standings, read 2026-11-14 (after 11/13).
OFFICIAL_STANDINGS_SOURCE = "https://www.nba.com/standings"
OFFICIAL_STANDINGS = {
    "BOS": (10, 2), "PHI": (10, 3), "DET": (8, 3), "ATL": (7, 6), "MIA": (6, 6),
    "NYK": (6, 6), "CLE": (6, 7), "TOR": (5, 7), "ORL": (5, 7), "IND": (5, 8),
    "CHA": (4, 8), "WAS": (4, 9), "BKN": (3, 8), "CHI": (2, 9), "MIL": (1, 12),
    "SAS": (11, 2), "LAL": (11, 2), "HOU": (10, 3), "POR": (9, 3), "MIN": (9, 3),
    "MEM": (8, 4), "GSW": (8, 5), "OKC": (8, 5), "DEN": (6, 4), "DAL": (7, 5),
    "PHX": (5, 6), "NOP": (4, 9), "LAC": (3, 8), "SAC": (1, 11), "UTA": (1, 12),
}

# The five 11/13 games that were still UNPLAYED at the 11/13 07:30 PM ET injury edition
# are irrelevant here; what matters is which teams played on 11/13 at all, because only
# those teams' records can have gone stale since the pre-11/13 capture.
PLAYED_11_13 = {"NYK", "IND", "MIL", "ORL", "CLE", "MIA", "ATL", "CHI",
                "MEM", "NOP", "UTA", "HOU", "GSW", "SAS", "POR", "SAC", "OKC", "LAC"}


def rec(s):
    try:
        w, l = s.split("-")
        return int(w), int(l)
    except (ValueError, AttributeError):
        return None


def main():
    published = json.load(open(os.path.join(ROOT, "data", "raw", "schedule_upcoming.json"),
                              encoding="utf-8"))
    cols = published["cols"]
    rows = [dict(zip(cols, r)) for r in published["rows"]]

    official = {}
    for d, a, ar, h, hr, tip, gid in OFFICIAL_HORIZON:
        official[(d, a, h)] = dict(date=d, away=a, away_rec=ar, home=h, home_rec=hr,
                                   tip=tip, game_id=gid)

    print("=" * 78)
    print("HORIZON CHECK — data/raw/schedule_upcoming.json vs official NBA.com capture")
    print("=" * 78)
    print("official rows : %d" % len(official))
    print("published rows: %d" % len(rows))

    errors = []
    date_mismatch, rec_mismatch = [], []

    if len(rows) != len(official):
        errors.append("row count %d != official %d" % (len(rows), len(official)))

    seen = set()
    for r in rows:
        key = (r["date"], r["away"], r["home"])
        seen.add(key)
        o = official.get(key)
        if o is None:
            errors.append("PUBLISHED ROW NOT ON OFFICIAL SCHEDULE: %s %s@%s (game_id %s)"
                          % (r["date"], r["away"], r["home"], r["game_id"]))
            continue
        if r["game_id"] != o["game_id"]:
            errors.append("game_id %s %s@%s: published %s, official %s"
                          % (r["date"], r["away"], r["home"], r["game_id"], o["game_id"]))
        if r["time_et"] != o["tip"]:
            date_mismatch.append("%s %s@%s: published tip %s, official %s"
                                 % (r["date"], r["away"], r["home"], r["time_et"], o["tip"]))
        for side in ("away", "home"):
            p, off = r[side + "_rec"], o[side + "_rec"]
            if p != off:
                # is the published value the pre-11/13 record, i.e. stale rather than random?
                stale = r[side] in PLAYED_11_13
                rec_mismatch.append((r["date"], "%s@%s" % (r["away"], r["home"]), side,
                                     r[side], p, off, stale))
        for side in ("away", "home"):
            st = OFFICIAL_STANDINGS.get(r[side])
            if st and rec(o[side + "_rec"]) != st:
                errors.append("STANDINGS DISAGREE %s: horizon card says %s, standings says %d-%d"
                              % (r[side], o[side + "_rec"], st[0], st[1]))

    for key in official:
        if key not in seen:
            errors.append("OFFICIAL GAME MISSING FROM PUBLISHED ROWS: %s %s@%s"
                          % (key[0], key[1], key[2]))

    print("\n-- structure --")
    print("error(s): %d" % len(errors))
    for e in errors:
        print("  ERROR:", e)

    print("\n-- printed team records --")
    print("record mismatches: %d" % len(rec_mismatch))
    stale = [m for m in rec_mismatch if m[6]]
    fresh_bad = [m for m in rec_mismatch if not m[6]]
    print("  of which the team DID play 11/13 (explained by a stale capture): %d" % len(stale))
    print("  of which the team did NOT play 11/13 (NOT explained): %d" % len(fresh_bad))
    for m in fresh_bad:
        print("    UNEXPLAINED", m)
    for m in stale[:6]:
        print("    stale  %s %s %s: site %s, official %s" % (m[0], m[1], m[2], m[4], m[5]))
    if len(stale) > 6:
        print("    ... and %d more stale records" % (len(stale) - 6))

    print("\n-- tip times --")
    print("tip-time mismatches: %d" % len(date_mismatch))
    for d in date_mismatch:
        print("  ", d)

    print("\nsources:")
    for d, u in HORIZON_SOURCE.items():
        print("  %s  %s" % (d, u))
    print("  standings  %s" % OFFICIAL_STANDINGS_SOURCE)

    ok = (not errors) and (not fresh_bad) and (not stale) and (not date_mismatch)
    print("\nRESULT:", "OK — every horizon row matches the official capture" if ok else
          "MISMATCH — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
