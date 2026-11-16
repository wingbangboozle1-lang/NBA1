#!/usr/bin/env python3
"""Parse the official injury-report PDF transcription into structured rows.

Input : raw/injury_2026-11-15_0900PM.md  (verbatim markdown rendering of the
        official PDF at
        https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf)
Output: raw/injury_2026-11-15_0900PM_rows.json

The PDF uses merged cells: Game Date / Game Time / Matchup / Team are printed once
and left blank on continuation rows. This parser never invents a value. It records
what was printed, what it carried forward, and flags every carried-forward field.

Cell classification is content-based, not positional, because the markdown renderer
emits a variable number of cells per row (5 to 8) for merged rows.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "raw", "injury_2026-11-15_0900PM.md")
OUT = os.path.join(HERE, "raw", "injury_2026-11-15_0900PM_rows.json")

EDITION = "2026-11-15_09_00PM"
PDF_URL = ("https://ak-static.cms.nba.com/referee/injury/"
           "Injury-Report_2026-11-15_09_00PM.pdf")
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

TEAMS = {
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
    "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans",
    "New York Knicks", "Oklahoma City Thunder", "Orlando Magic",
    "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz",
    "Washington Wizards",
}
STATUSES = {"Out", "Available", "Questionable", "Doubtful", "NOT YET SUBMITTED"}

RE_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}\s*\(ET\)$")
RE_MATCHUP = re.compile(r"^[A-Z]{3}@[A-Z]{3}$")


def cells_of(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    parts = s.split("|")
    # markdown: leading and trailing empties are the pipe delimiters
    if len(parts) < 3:
        return None
    return [p.strip() for p in parts[1:-1]]


def is_separator(cells):
    return all(set(c) <= set("-: ") and c for c in cells) or all(
        re.fullmatch(r":?-{2,}:?", c) for c in cells if c)


def main():
    if not os.path.exists(SRC):
        print("missing transcription:", SRC, file=sys.stderr)
        return 1

    text = open(SRC, encoding="utf-8").read()
    rows = []
    cur = {"game_date": None, "game_time_et": None, "matchup": None, "team": None}
    page = 0
    skipped = []

    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("## Page "):
            page = int(re.search(r"(\d+)", line).group(1))
            continue
        cells = cells_of(line)
        if cells is None:
            continue
        if not any(cells):
            continue
        if cells[0].lower() == "game date" or is_separator(cells):
            continue

        # classify
        date = time_ = matchup = team = status = None
        rest = []
        for c in cells:
            if c == "":
                rest.append(("blank", c))
                continue
            if date is None and RE_DATE.match(c):
                date = c
                continue
            if time_ is None and RE_TIME.match(c):
                time_ = c
                continue
            if matchup is None and RE_MATCHUP.match(c):
                matchup = c
                continue
            if team is None and c in TEAMS:
                team = c
                continue
            rest.append(("val", c))

        # status: the first value cell that is a known status token
        status_idx = None
        for i, (kind, c) in enumerate(rest):
            if kind == "val" and c in STATUSES:
                status_idx = i
                status = c
                break

        player = None
        reason = None
        if status_idx is None:
            skipped.append({"line": lineno, "cells": cells,
                            "why": "no status token found"})
            continue
        before = [c for kind, c in rest[:status_idx] if kind == "val"]
        after = [c for kind, c in rest[status_idx + 1:] if kind == "val"]
        player = before[-1] if before else None
        # a carrier team name can also sit before the player (merged header row)
        if before and before[0] in TEAMS and team is None:
            team = before[0]
            before = before[1:]
            player = before[-1] if before else None
        reason = " ".join(after).strip() if after else ""
        if reason == "-":
            reason = ""

        # carry-forward. A new matchup WITHOUT a printed date/time resets them:
        # carrying 06:00 (ET) from DAL@BOS onto NYK@TOR would fabricate a tip time.
        inherited = []
        if matchup and matchup != cur["matchup"]:
            cur["matchup"] = matchup
            cur["game_date"] = date or None
            cur["game_time_et"] = time_ or None
            if date is None:
                inherited.append("game_date")
            if time_ is None:
                inherited.append("game_time_et")
        else:
            if matchup:
                cur["matchup"] = matchup
            if date:
                cur["game_date"] = date
            elif cur["game_date"] is None:
                inherited.append("game_date")
            if time_:
                cur["game_time_et"] = time_
            elif cur["game_time_et"] is None:
                inherited.append("game_time_et")
            if cur["matchup"] is None:
                inherited.append("matchup")

        if team:
            cur["team"] = team
        elif cur["team"] is None:
            inherited.append("team")

        rows.append({
            "row_no": len(rows) + 1,
            "pdf_page": page,
            "game_date": cur["game_date"],
            "game_time_et": cur["game_time_et"],
            "matchup": cur["matchup"],
            "team": cur["team"],
            "team_printed": team,
            "team_inherited": "team" in inherited,
            "player": player,
            "status": status,
            "reason": reason,
            "inherited_fields": inherited,
            "source_url": PDF_URL,
        })

    if skipped:
        print("SKIPPED rows (published, not silently dropped):", json.dumps(skipped, indent=2))

    doc = {
        "_meta": {
            "title": "Official NBA injury report — edition 2026-11-15 09:00 PM ET, structured",
            "edition": EDITION,
            "edition_file": "Injury-Report_2026-11-15_09_00PM.pdf",
            "revision_time_et": "11/15/2026 09:00 PM",
            "source_url": PDF_URL,
            "index_url": INDEX_URL,
            "transcribed_utc": "2026-11-16T02:20Z",
            "transcribed_by": "session arena/4ff440c7-nba1",
            "transcription_method": ("the official PDF was retrieved from ak-static.cms.nba.com "
                                     "and rendered to markdown; the markdown table lines are "
                                     "reproduced verbatim in "
                                     "raw/injury_2026-11-15_0900PM.md"),
            "parse_method": ("content-based cell classification (date / time / matchup / team / "
                             "status) because merged rows emit 5-8 cells; carry-forward with "
                             "reset-on-new-matchup; inherited fields flagged per row"),
            "row_count": len(rows),
            "note": ("game_date and game_time_et are left None where the PDF did not print them "
                     "on that row; they are never filled in here"),
        },
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", OUT, "rows:", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
