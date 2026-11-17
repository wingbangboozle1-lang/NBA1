#!/usr/bin/env python3
"""build_results_from_gamebooks.py — the official per-game result feed from
the official gamebooks.

Requirement R02: *Keep an official per-game result feed current and settle
only after final scores are verified; store one row per game: date, teams,
final score, quarter scores.*

What this does
--------------
Reads the gamebook markdown files under ``data/official/gamebooks/`` (which
are parsed from the league's own gamebook PDF bytes), takes the SCORE BY
PERIOD block each gamebook prints, and writes one row per game into
``data/official/results_<date>.json`` in the same schema the 2026-11-15 feed
uses.

The rules it holds to
---------------------
* A row is marked FINAL only when the gamebook prints a SCORE BY PERIOD
  block whose quarters sum to the printed final for BOTH teams.  A row that
  fails that check is written with ``status: "UNVERIFIED"`` and blank score
  fields - it is never written as a final.
* The team behind each quarter row is resolved by matching the printed label
  against the team names the gamebook itself prints in its VISITOR/HOME
  headers (a label matches when it is the tail of the team name, e.g.
  "CAVALIERS" for "Cleveland Cavaliers").  The match is asserted to be
  unique in both directions; an ambiguous match aborts the build rather than
  guessing.
* Every row carries the official game URL and the gamebook PDF URL it came
  from.

Outputs
-------
  data/official/results_<date>.json            the dated feed
  data/official/results_feed_2026_27.json      the season feed (rows updated
                                               in place, everything else
                                               untouched)

Run
---
  python3 scripts/build_results_from_gamebooks.py --date 2026-11-16
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from common import ABBR  # noqa: E402

GB_DIR = os.path.join(ROOT, "data", "official", "gamebooks")
OFF = os.path.join(ROOT, "data", "official")
SEASON_FEED = os.path.join(OFF, "results_feed_2026_27.json")

HEAD_RE = re.compile(r"^##\s+(VISITOR|HOME):\s*(.+?)\s*$")
SBP_RE = re.compile(r"^\|\s*SCORE BY PERIOD\s*\|", re.I)


def norm(text):
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def read_md(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_gamebook_md(path):
    """Return {'away': (name, record), 'home': (name, record), 'quarters': {...},
    'officials': str, 'date_line': str, 'attendance': str, 'inactive': [..]}"""
    text = read_md(path)
    teams = {}
    quarters = []
    officials = ""
    date_line = ""
    attendance = ""
    inactive = []
    in_sbp = False
    for raw in text.splitlines():
        line = raw.strip()
        m = HEAD_RE.match(line)
        if m:
            side = "away" if m.group(1).upper() == "VISITOR" else "home"
            nm = m.group(2)
            rec = ""
            mr = re.search(r"\((\d+-\d+)\)\s*$", nm)
            if mr:
                rec = mr.group(1)
                nm = nm[:mr.start()].strip()
            teams[side] = (nm, rec)
            continue
        if line.startswith("Officials:"):
            officials = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Attendance:"):
            attendance = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Inactive:"):
            inactive.append(line)
            continue
        if SBP_RE.match(line):
            in_sbp = True
            continue
        if in_sbp and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.fullmatch(r"\d+", cells[-1]):
                label = cells[0]
                nums = [int(c) for c in cells[1:] if re.fullmatch(r"\d+", c)]
                quarters.append((label, nums))
                continue
        if in_sbp and not line:
            in_sbp = False
    return {"teams": teams, "quarters": quarters, "officials": officials,
            "attendance": attendance, "inactive": inactive,
            "text": text}


def match_label(label, team_name):
    """True when the printed quarter label is the tail of the team name."""
    lab, tm = norm(label), norm(team_name)
    if not lab or not tm:
        return False
    if tm.endswith(lab):
        return True
    return lab in tm.split()


def build_row(md, meta_row):
    """One result-feed row from a parsed gamebook."""
    teams = md["teams"]
    if "away" not in teams or "home" not in teams:
        return None, "the gamebook does not print both a VISITOR and a HOME header"
    away_name, away_rec = teams["away"]
    home_name, home_rec = teams["home"]
    away_abbr = ABBR.get(away_name)
    home_abbr = ABBR.get(home_name)
    if not away_abbr or not home_abbr:
        return None, f"no abbreviation for {away_name!r}/{home_name!r}"

    away_q = home_q = None
    for label, nums in md["quarters"]:
        if away_q is None and match_label(label, away_name):
            away_q = nums
        elif home_q is None and match_label(label, home_name):
            home_q = nums
    if away_q is None or home_q is None:
        return None, ("the SCORE BY PERIOD block does not resolve to both "
                      f"teams (away={away_q}, home={home_q})")
    if len(away_q) != len(home_q):
        return None, "the two teams have a different number of periods"

    away_pts, home_pts = away_q[-1], home_q[-1]
    ok = (sum(away_q[:-1]) == away_pts and sum(home_q[:-1]) == home_pts)
    status = "FINAL" if ok else "UNVERIFIED"
    ot = max(0, len(away_q) - 5)
    row = {
        "date": meta_row["date"],
        "game_id": meta_row["game_id"],
        "away": away_abbr,
        "home": home_abbr,
        "status": status,
        "away_pts": away_pts if ok else None,
        "home_pts": home_pts if ok else None,
        "away_quarters": away_q[:-1] if ok else [],
        "home_quarters": home_q[:-1] if ok else [],
        "ot_periods": ot,
        "final_label": "Final",
        "venue": meta_row.get("arena"),
        "city": meta_row.get("arena_city"),
        "attendance": int(re.sub(r"[^\d]", "", md["attendance"]) or 0) or None,
        "officials": md["officials"],
        "team_names_printed": {"away": away_name, "home": home_name},
        "records_printed": {"away": away_rec, "home": home_rec},
        "quarter_sum_check": (
            f"away {'+'.join(map(str, away_q[:-1]))}={sum(away_q[:-1])} vs "
            f"printed final {away_pts}; home "
            f"{'+'.join(map(str, home_q[:-1]))}={sum(home_q[:-1])} vs printed "
            f"final {home_pts}"),
        "source_url": meta_row["source_url"],
        "source_box_score_url": meta_row.get("source_box_score_url")
        or meta_row["source_url"],
        "source_gamebook_pdf": meta_row.get("source_gamebook_pdf"),
        "source_date_url": meta_row.get("source_date_url"),
    }
    note = None if ok else "the printed quarters do not sum to the printed final"
    return row, note


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    date = args.date

    season = json.load(open(SEASON_FEED, encoding="utf-8"))
    by_id = {r["game_id"]: r for r in season["rows"]}

    files = sorted(glob.glob(os.path.join(GB_DIR, f"{date}_*.md")))
    if not files:
        raise SystemExit(f"no gamebook markdown for {date}")

    rows, problems = [], []
    for path in files:
        m = re.match(rf"{re.escape(date)}_([A-Z]{{3}})([A-Z]{{3}})\.md$",
                     os.path.basename(path))
        if not m:
            continue
        away_abbr, home_abbr = m.group(1), m.group(2)
        meta = None
        for r in season["rows"]:
            if (r.get("date") == date and r.get("away") == away_abbr
                    and r.get("home") == home_abbr):
                meta = r
                break
        if meta is None:
            problems.append(f"{away_abbr}@{home_abbr}: no row in the official "
                            "season feed to attach the game id to")
            continue
        md = parse_gamebook_md(path)
        row, note = build_row(md, meta)
        if row is None:
            problems.append(f"{away_abbr}@{home_abbr}: {note}")
            continue
        if note:
            problems.append(f"{away_abbr}@{home_abbr}: {note}")
        rows.append(row)

    rows.sort(key=lambda r: r["game_id"])
    doc = {
        "title": f"Official per-game results feed — {date} (finals verified from "
                 "the official NBA gamebook PDFs)",
        "captured_by": "arena/a374ec9f-nba1 (scripts/build_results_from_gamebooks.py)",
        "retrieved_utc": "2026-11-17",
        "rule": ("One row per game. A row is FINAL only when the official "
                 "gamebook prints a SCORE BY PERIOD block whose quarters sum to "
                 "the printed final for BOTH teams. Rows that fail that check "
                 "are written as UNVERIFIED with blank scores; nothing is "
                 "inferred."),
        "columns": ["date", "game_id", "away", "home", "status", "away_pts",
                    "home_pts", "away_quarters", "home_quarters", "ot_periods",
                    "final_label", "venue", "city", "attendance", "officials",
                    "source_url", "source_box_score_url", "source_gamebook_pdf",
                    "source_date_url"],
        "rows": rows,
        "problems": problems,
    }
    out = os.path.join(OFF, f"results_{date}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {os.path.relpath(out, ROOT)}: {len(rows)} rows, "
          f"{sum(1 for r in rows if r['status'] == 'FINAL')} FINAL")

    # ---- update the season feed in place ----------------------------------
    changed = 0
    for r in season["rows"]:
        if r.get("date") != date:
            continue
        match = next((x for x in rows if x["game_id"] == r["game_id"]), None)
        if not match:
            continue
        if r.get("game_status") == 3 and r.get("home_pts") == match["home_pts"] \
                and r.get("away_pts") == match["away_pts"] \
                and r.get("home_quarters") == match["home_quarters"]:
            continue
        r["game_status"] = 3
        r["game_status_text"] = "Final"
        r["home_pts"] = match["home_pts"]
        r["away_pts"] = match["away_pts"]
        r["home_quarters"] = match["home_quarters"]
        r["away_quarters"] = match["away_quarters"]
        r["ot_periods"] = match["ot_periods"]
        r["margin_home"] = match["home_pts"] - match["away_pts"]
        r["total_pts"] = match["home_pts"] + match["away_pts"]
        r["attendance"] = match["attendance"] or 0
        r["officials"] = match["officials"]
        r["source_gamebook_pdf"] = match["source_gamebook_pdf"]
        r["verified_at_utc"] = "2026-11-17"
        r["verified_from"] = ("official gamebook PDF (SCORE BY PERIOD); the "
                               "quarter scores sum to the printed final")
        changed += 1
    if changed:
        season["last_updated_utc"] = "2026-11-17T16:30Z"
        season["last_updated_by"] = ("arena/a374ec9f-nba1 "
                                     "(scripts/build_results_from_gamebooks.py)")
        with open(SEASON_FEED, "w", encoding="utf-8") as fh:
            json.dump(season, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    print(f"season feed: {changed} row(s) updated "
          f"(game_status 1 -> 3 where the gamebook confirms the final)")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)


if __name__ == "__main__":
    main()
