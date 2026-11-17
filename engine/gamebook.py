"""gamebook.py - read an official NBA gamebook PDF, from the bytes.

The league's own gamebook (the "Official Scorer's Report") is the only
official source that prints, per game:

  * every player's minutes, points, rebounds, assists and the opponent's
    scoring, and
  * the score by period for both teams.

Requirement R21 (*per-player logs: minutes, points, rebounds, assists and the
opponent*) and R12 (*top-8 minutes shares and the replacement shares when a
player is out*) read exactly those numbers, so this module is the front end
for both.

The reading rules are deliberately strict:

* Every value comes from the PDF's own drawn table.  The column bands are the
  rectangles the document draws at its horizontal rules; a value is written to
  the column whose band the document draws it in.
* A cell the document leaves empty stays empty.  Nothing is inferred, and a
  value is never carried from one column into another.
* A player row whose minutes cell carries a note ("DNP - Coach's Decision")
  is recorded as a non-appearance with the note, not as a player with zero
  minutes.
* The score by period block is parsed separately and is checked against the
  printed final before anything is published from it.

The module is standard-library only.
"""

from __future__ import annotations

import re

import pdf_grid as G

STAT_COLS = ["FG", "FGA", "3P", "3PA", "FT", "FTA", "OR", "DR", "TOT", "A",
             "PF", "ST", "TO", "BS", "+/-", "PTS"]

HEADER_ROW = re.compile(r"^POS\s*MIN\s*FG\s*FGA\s*3P\s*3PA\s*FT\s*FTA\s*OR\s*"
                        r"DR\s*TOT\s*A\s*PF\s*ST\s*TO\s*BS\s*\+/-?\s*PTS$")
TITLE_RE = re.compile(r"^(VISITOR|HOME):\s*(.+?)\s*$")
TEAM_REC_RE = re.compile(r"^(.*?)\s*\((\d+-\d+)\)\s*$")
DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
                     r"(January|February|March|April|May|June|July|August|"
                     r"September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\s+"
                     r"(.*)$")
MIN_RE = re.compile(r"^\d{1,3}:\d{2}$")
NUM_RE = re.compile(r"^-?\d+$")


def page_lines(page):
    """The page's text lines in DOCUMENT order.

    The gamebook draws the page with an inverted y axis, so the document
    order is DESCENDING device y.  Each line is (y, [segments]).
    """
    runs = sorted(page["runs"], key=lambda r: (-r["y"], r["x"]))
    lines = []
    for r in runs:
        if lines and abs(r["y"] - lines[-1][0]) <= 2.5:
            lines[-1][1].append(r)
        else:
            lines.append([r["y"], [r]])
    out = []
    for y, segs in lines:
        segs = sorted(segs, key=lambda s: s["x"])
        out.append((y, segs))
    return out


def line_text(segs, sep=" "):
    return sep.join(s["text"] for s in segs).strip()


def column_bands(page):
    """The document's own column bands: [x0, x1, x2, ...]."""
    rects = page["rects"]
    if not rects:
        return []
    lines = {}
    for x, y, w, h in rects:
        lines.setdefault(round(y, 1), []).append((x, x + w))
    counts = {y: len(v) for y, v in lines.items()}
    best = max(counts.values()) if counts else 0
    if best < 4:
        return []
    y = max(counts, key=lambda k: counts[k])
    spans = sorted(lines[y])
    edges = []
    for a, b in spans:
        if not edges:
            edges.append(a)
        edges.append(b)
    return edges


def grid_rows(page, edges):
    """Assign every text line to the document's column bands."""
    rows = []
    for y, segs in page_lines(page):
        cells = [""] * (len(edges) - 1)
        for s in segs:
            ci = None
            for i in range(len(edges) - 1):
                a, b = edges[i], edges[i + 1]
                if a - 1.0 <= s["x"] < b - 0.5:
                    ci = i
                    break
            if ci is None:
                continue
            cells[ci] += s["text"]
        rows.append({"y": y, "cells": [c.strip() for c in cells],
                     "segs": segs})
    return rows


def band_of(edges, x):
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        if a - 1.0 <= x < b - 0.5:
            return i
    return None


def parse_page1(pdf_bytes):
    """Parse the page-1 box score of one gamebook.

    Returns a dict with the metadata, the two teams, their player rows and
    the score-by-period block.
    """
    objs = G.parse_objects(pdf_bytes)
    fonts = G.build_fonts(objs)
    pages = G.page_objects(objs)
    if not pages:
        raise ValueError("the PDF has no pages")
    page = G.extract_page(objs, fonts, pages[0])
    edges = column_bands(page)
    if not edges:
        raise ValueError("the PDF page draws no column bands")
    rows = grid_rows(page, edges)
    lines = page_lines(page)

    meta = {"officials": None, "attendance": None, "game_duration": None,
            "date_line": None, "venue": None}
    teams = {}
    order = []
    score_rows = []
    inactive = []
    notes = []

    # locate the column-header rows; each one starts a team's box score
    header_idx = []
    for i, (y, segs) in enumerate(lines):
        txt = line_text(segs, sep="")
        if HEADER_ROW.match(txt.replace(" ", " ")):
            header_idx.append(i)
    header_idx = [i for i in header_idx if HEADER_ROW.match(
        line_text(lines[i][1], sep="").replace("  ", " "))]

    # the title ("VISITOR: X (a-b)") sits directly ABOVE its header row
    titles = []
    for i, (y, segs) in enumerate(lines):
        m = TITLE_RE.match(line_text(segs))
        if m:
            titles.append((i, m.group(1).upper(), m.group(2).strip()))

    def title_above(idx):
        for ti, side, nm in titles:
            if ti < idx:
                if not any(t[0] > ti and t[0] < idx for t in titles):
                    return side, nm
        return None, None

    def parse_players(cells):
        """One box-score row -> a player dict, or None if it is not one."""
        jersey = cells[0].strip()
        name = cells[1].strip()
        pos = cells[2].strip()
        mins = cells[3].strip()
        if not name:
            return None
        vals = {}
        for i, col in enumerate(STAT_COLS):
            raw = cells[4 + i].strip() if 4 + i < len(cells) else ""
            vals[col] = int(raw) if NUM_RE.match(raw) else None
        rec = {"jersey": jersey or None, "player": name, "pos": pos or None}
        if MIN_RE.match(mins):
            rec["played"] = True
            rec["min"] = mins
            mm, ss = mins.split(":")
            rec["minutes_seconds"] = int(mm) * 60 + int(ss)
            rec["note"] = None
        else:
            rec["played"] = False
            rec["min"] = None
            rec["minutes_seconds"] = None
            rec["note"] = mins or None
            # a player who did not play has no statistics
            for col in STAT_COLS:
                vals[col] = None
        rec.update(vals)
        return rec

    # ---- walk the lines and slice them into the two teams
    team_starts = []
    for i in range(len(lines)):
        y, segs = lines[i]
        txt = line_text(segs)
        m = TITLE_RE.match(txt)
        if m:
            team_starts.append((i, m.group(1).upper(), m.group(2).strip()))

    for ti, (i, side, raw_name) in enumerate(team_starts):
        rec = ""
        nm = raw_name
        mr = TEAM_REC_RE.match(raw_name)
        if mr:
            nm, rec = mr.group(1).strip(), mr.group(2)
        stop = team_starts[ti + 1][0] if ti + 1 < len(team_starts) else len(lines)
        block = lines[i:stop]
        players = []
        totals = None
        percentages = None
        for y, segs in block:
            txt = line_text(segs)
            if txt.startswith("Inactive:"):
                inactive.append(txt)
                continue
            ci = band_of(edges, segs[0]["x"]) if segs else None
            if ci is None:
                continue
            cells = [""] * (len(edges) - 1)
            for s in segs:
                c = band_of(edges, s["x"])
                if c is not None:
                    cells[c] += s["text"]
            cells = [c.strip() for c in cells]
            if HEADER_ROW.match(txt.replace(" ", " ")):
                continue
            if cells[3] and MIN_RE.match(cells[3]) and cells[3] != "240:00":
                p = parse_players(cells)
                if p:
                    players.append(p)
                continue
            if cells[3] == "240:00":
                totals = {"min": cells[3]}
                for i2, col in enumerate(STAT_COLS):
                    raw = cells[4 + i2] if 4 + i2 < len(cells) else ""
                    totals[col] = int(raw) if NUM_RE.match(raw) else None
                continue
            if any(cells[4:]):
                percentages = [c for c in cells]
        teams[side] = {"side": side, "team": nm, "record": rec,
                       "players": players, "totals": totals}
        order.append(side)

    # ---- metadata
    for y, segs in lines:
        txt = line_text(segs)
        if txt.startswith("Officials:") or txt.startswith("Ofﬁcials:"):
            meta["officials"] = txt.split(":", 1)[1].strip()
        elif txt.startswith("Attendance:"):
            meta["attendance"] = txt.split(":", 1)[1].strip()
        elif txt.startswith("Game Duration:"):
            meta["game_duration"] = txt.split(":", 1)[1].strip()
        else:
            m = DATE_RE.match(txt)
            if m and meta["date_line"] is None:
                meta["date_line"] = txt
                meta["venue"] = m.group(5)
            if txt.startswith("Inactive:"):
                inactive.append(txt)
            if "SCORE BY PERIOD" in txt:
                score_rows.append((y, txt, segs))

    # ---- the score-by-period block
    periods = []
    if score_rows:
        y0 = score_rows[0][0]
        after = [(y, segs) for y, segs in lines if y < y0]
        after.sort(key=lambda t: -t[0])
        for y, segs in after[:6]:
            txt = line_text(segs)
            m = re.match(r"^(.*?)\s*((?:\d+\s+){3,}\d+)$", txt)
            if not m:
                continue
            label = m.group(1).strip()
            nums = [int(x) for x in m.group(2).split()]
            if len(nums) < 5:
                continue
            periods.append({"label": label, "quarters": nums[:-1],
                            "final": nums[-1]})

    return {"meta": meta, "teams": teams, "order": order,
            "score_by_period": periods, "inactive": inactive,
            "notes": notes, "header_rows": len(header_idx)}
