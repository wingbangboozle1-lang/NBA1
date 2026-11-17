"""Consecutive-edition diffs of the official NBA injury-report PDFs (RFG4).

The scheduled fetcher archives every retrieved report byte-for-byte under
``data/raw/injury_pdfs/<edition>__<sha256>.pdf`` with a retrieval sidecar.
This module extracts the status text from each archived PDF (standard library
only - the GitHub Actions runner installs nothing), parses the league's table
into rows, and diffs consecutive editions player by player so a status change
is *detected*, never hand-written.

Extraction approach: the official reports draw their table as **explicit
clipped rectangles** - every cell is emitted as ``q <x> <y> <w> <h> re W* n
BT ... ET Q``.  That rectangle is the report's own statement of where the cell
is and how wide it is, so the authoritative reader works *per cell*: it reads
the text drawn inside each clip, sorts the cells into rows by their rectangle
geometry, and maps each cell to a column by the x-position of the column
headers the report prints on its first page (Game Date, Game Time, Matchup,
Team, Player Name, Current Status, Reason / Comments).

A second reader is kept as a cross-check: it recovers the same text as
positioned words, groups them into visual lines and assigns them to the
report's row bands.  The two readers are compared on every edition and the
comparison is published with the parse, because the line reader was measured
to **drop player rows that the cell reader recovers** (flag F-X01: seven
player rows per 2026-11-16 edition, every one of them on a continuation page,
while the line reader reported zero unparsed cells).  The cell reader is now
the primary reader; the line reader is retained so the disagreement stays
visible instead of being silently resolved.

A value that cannot be read is left blank and listed under ``unparsed`` - it
is never inferred.

Every parsed row carries its provenance: the official PDF URL, the file's
SHA-256 and the retrieval timestamp from the fetcher's sidecar.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")
OUT_DIR = os.path.join(ROOT, "data", "parsed", "injury_diffs")

COLS = ["game_date", "game_time_et", "matchup", "team", "player", "status",
        "reason"]
HEADER_WORDS = {
    "game_date": ("Game", "Date"),
    "game_time": ("Game", "Time"),
    "matchup": ("Matchup",),
    "team": ("Team",),
    "player": ("Player", "Name"),
    "status": ("Current", "Status"),
    "reason": ("Reason", "Comments"),
    "reason_alt": ("Reason/Comments", "Reasons/Comments", "Comments"),
}

STREAM_RE = re.compile(rb"<<((?:[^<>]|<[^>]*>)*)>>\s*stream\r?\n(.*?)\r?\nendstream",
                       re.S)
def _iter_bt_blocks(text):
    """Yield the content of each BT..ET text block.

    A regex cannot delimit these blocks reliably: the drawn strings live in
    parentheses and can contain the operator names themselves (the official
    reports contain the word "YET" - "NOT YET SUBMITTED" - whose letters make
    a naive ``BT(.*?)ET`` stop in the middle of a line). This scanner tracks
    parenthesis nesting so operator names inside strings are ignored.
    """
    i, n = 0, len(text)
    while i < n - 1:
        if text[i] == "(":
            depth = 1
            i += 1
            while i < n and depth:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                i += 1
            continue
        if text[i:i + 2] == "BT" and not (text[i - 1].isalnum() if i else False) \
                and not text[i + 2].isalnum():
            j = i + 2
            while j < n - 1:
                if text[j] == "(":
                    depth = 1
                    j += 1
                    while j < n and depth:
                        if text[j] == "\\":
                            j += 2
                            continue
                        if text[j] == "(":
                            depth += 1
                        elif text[j] == ")":
                            depth -= 1
                        j += 1
                    continue
                if text[j:j + 2] == "ET" and not text[j - 1].isalnum() \
                        and not (j + 2 < n and text[j + 2].isalnum()):
                    yield text[i + 2:j]
                    i = j + 2
                    break
                j += 1
            else:
                return
            continue
        i += 1
TD_RE = re.compile(r"(-?[\d.]+)\s+(-?[\d.]+)\s+Td")
TJ_RE = re.compile(r"\[(.*?)\]\s*TJ", re.S)
TJ_STR_RE = re.compile(r"\((.*?)(?<!\\)\)\s*Tj", re.S)
HEX_RE = re.compile(r"<([0-9A-Fa-f\s]+)>\s*Tj")
RECT_RE = re.compile(r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+re")


def _pdf_unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n in "nrtbf":
                out.append({"n": "\n", "r": "\r", "t": "\t", "b": "\b",
                            "f": "\f"}[n])
                i += 2
                continue
            if n in "()\\":
                out.append(n)
                i += 2
                continue
            if n.isdigit():
                oct_ = s[i + 1:i + 4]
                m = re.match(r"[0-7]{1,3}", oct_)
                if m:
                    out.append(chr(int(m.group(0), 8)))
                    i += 1 + len(m.group(0))
                    continue
            out.append(n)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def extract_pages(pdf_bytes):
    """Return per-page {"words": [(x, y, word)], "rects": [(x, y, w, h)]}.

    Each text-bearing content stream is one page (the official reports are
    generated PDFs, one content stream per page). Words inside one BT..ET
    block are positioned by emulating the block's Td chain (first Td is the
    block's absolute anchor, later Tds shift the pen). Some documents draw
    each string twice (shadow + fill) at identical coordinates - exact
    duplicates are removed. The ``re`` rectangles are the report's own cell
    backgrounds/clips: they delimit the table's row bands and are the
    authority for which wrapped text lines belong to which row.
    """
    pages = []
    for m in STREAM_RE.finditer(pdf_bytes):
        params, data = m.group(1), m.group(2)
        if b"FlateDecode" in params:
            try:
                data = zlib.decompress(data)
            except zlib.error:
                continue
        try:
            text = data.decode("latin-1")
        except UnicodeDecodeError:
            continue
        if "Tj" not in text and "TJ" not in text:
            continue
        page_words = []
        for block in _iter_bt_blocks(text):
            x = y = 0.0
            first = True
            for tok in re.finditer(
                    r"(-?[\d.]+)\s+(-?[\d.]+)\s+Td|\((.*?)(?<!\\)\)\s*Tj|"
                    r"\[(.*?)\]\s*TJ|<([0-9A-Fa-f\s]+)>\s*Tj", block, re.S):
                if tok.group(1) is not None:
                    dx, dy = float(tok.group(1)), float(tok.group(2))
                    if first:
                        x, y = dx, dy
                        first = False
                    else:
                        x += dx
                        y += dy
                elif tok.group(3) is not None:
                    word = _pdf_unescape(tok.group(3))
                    if word.strip():
                        page_words.append((x, y, word))
                elif tok.group(4) is not None:
                    parts = re.findall(r"\((.*?)(?<!\\)\)", tok.group(4), re.S)
                    word = "".join(_pdf_unescape(p) for p in parts)
                    if word.strip():
                        page_words.append((x, y, word))
                elif tok.group(5) is not None:
                    hx = re.sub(r"\s+", "", tok.group(5))
                    try:
                        word = bytes.fromhex(hx).decode("latin-1")
                    except ValueError:
                        continue
                    if word.strip():
                        page_words.append((x, y, word))
        rects = []
        for a, b, c, d in RECT_RE.findall(text):
            x, y, w, h = float(a), float(b), float(c), float(d)
            if 15 <= h <= 80 and 30 <= w <= 800 and x < 760:
                rects.append((x, y, w, h))
        pages.append({"words": sorted(set(page_words)), "rects": rects,
                      "raw": text})
    return pages


def extract_words(pdf_bytes):
    """Back-compat wrapper: positioned words per page."""
    return [p["words"] for p in extract_pages(pdf_bytes)]


# --------------------------------------------------------------------------
# Primary reader: the report's own clipped rectangles (flag F-X01)
# --------------------------------------------------------------------------

# One clipped cell: "q x y w h re W* n [BT ... ET] Q".
CELL_RE = re.compile(
    r"q\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+re\s+W\*\s*n\s*"
    r"(?:BT(.*?)ET)?\s*Q", re.S)

# The header text the report prints on its first page, mapped to a column.
HEADER_TEXT = {
    "game date": "game_date",
    "game time": "game_time_et",
    "matchup": "matchup",
    "team": "team",
    "player name": "player",
    "current status": "status",
    "reason": "reason",
    "reason / comments": "reason",
    "reason/comments": "reason",
    "reasons/comments": "reason",
    "comments": "reason",
}


def _cell_unescape(text: str) -> str:
    return (text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
            .replace(r"\n", " ").replace(r"\r", " "))


def _cell_text(block: str) -> str:
    """Concatenate the strings drawn inside one clipped cell, in order.

    Both ``(word) Tj`` and the kerned ``[(wo) -250 (rd)] TJ`` form are read.
    A hyphenated word the report draws as two kerned strings ("(Two-)" then
    "(Way)") is re-joined without the space, because that is what the page
    prints; every other pair is joined with a space.
    """
    if not block:
        return ""
    parts = [_cell_unescape(m.group(1))
             for m in re.finditer(r"\(((?:[^()\\]|\\.)*)\)", block)]
    out = ""
    for part in (p for p in parts if p):
        if not out:
            out = part
        elif out.endswith("-") and not out.endswith(" -") and len(out) > 1:
            out = out + part
        else:
            out = out + " " + part
    return out.strip()


def extract_cells(pdf_bytes):
    """Every clipped rectangle in the document, with its text and page number.

    This is the report's own cell geometry, not an estimate: the PDF draws one
    clip per table cell and puts that cell's text inside the clip.
    """
    cells = []
    for page_no, page in enumerate(extract_pages(pdf_bytes), start=1):
        text = page.get("raw", "")
        for m in CELL_RE.finditer(text):
            x, y, w, h = (float(m.group(i)) for i in (1, 2, 3, 4))
            cells.append({"page": page_no, "x": round(x, 3), "y": round(y, 3),
                          "w": round(w, 3), "h": round(h, 3),
                          "text": _cell_text(m.group(5) or "")})
    return cells


def detect_columns(cells):
    """Map an x-position to a column name using the report's own header row."""
    xs = {}
    for c in cells:
        key = c["text"].strip().lower().rstrip(":")
        if key in HEADER_TEXT:
            xs.setdefault(round(c["x"], 1), HEADER_TEXT[key])
    return xs if len(xs) >= 5 else {}


def _column_for(x, cols, tol=6.0):
    best, best_d = None, None
    for cx, name in cols.items():
        d = abs(cx - x)
        if d <= tol and (best_d is None or d < best_d):
            best, best_d = name, d
    return best


def group_rows(cells, y_tol=1.6, h_tol=2.1):
    """Group clipped cells into table rows.

    Every cell of one table row is drawn with the same rectangle geometry - the
    four left-hand columns sit one point lower and one point taller than the
    player/status/reason cells - so the tolerances absorb that and nothing
    more.  Adjacent rows are vertically contiguous, which is exactly why
    contiguity must not be used to merge them.
    """
    if not cells:
        return []
    items = sorted(cells, key=lambda c: (c["page"], c["y"], c["x"]))
    rows, current = [], [items[0]]
    for c in items[1:]:
        same = (c["page"] == current[0]["page"]
                and abs(c["y"] - current[0]["y"]) <= y_tol
                and abs(c["h"] - current[0]["h"]) <= h_tol)
        if same:
            current.append(c)
        else:
            rows.append(sorted(current, key=lambda z: z["x"]))
            current = [c]
    rows.append(sorted(current, key=lambda z: z["x"]))
    return rows


def _rows_to_records(rows, cols):
    out = []
    for r in rows:
        rec = {c: "" for c in COLS}
        xs = {}
        unassigned = []
        for c in r:
            name = _column_for(c["x"], cols)
            if name is None:
                if c["text"].strip():
                    unassigned.append(c["text"].strip())
                continue
            text = c["text"].strip()
            rec[name] = (rec[name] + " " + text).strip() if rec[name] else text
            xs.setdefault(name, c["x"])
        out.append({"cells": rec, "page": r[0]["page"], "x": xs,
                    "unassigned_text": unassigned})
    return out


def _assemble_cell_rows(records):
    """Re-join wrapped reasons, normalise the filing placeholder, inherit the
    merged Game Date / Game Time / Matchup / Team cells.

    Kept as a function so the unit test can exercise the same pipeline the
    diff writer uses rather than a copy of it.
    """
    if not records:
        return [], []
    # A reason that wraps is drawn as a second clipped rectangle in the same
    # x-band immediately below, so the grouper sees it as a row of its own.
    # It is re-joined only when the continuation carries nothing but reason
    # text in the same column on the same page (or the page immediately
    # before - the table continues across a page break).
    merged = []
    for r in records:
        prev = merged[-1] if merged else None
        c = r["cells"]
        only_reason = ((not c["player"]) and (not c["status"])
                       and bool(c["reason"].strip())
                       and c["reason"].strip().upper() != "NOT YET SUBMITTED")
        same_band = (prev is not None
                     and 0 <= r["page"] - prev["page"] <= 1
                     and prev["x"].get("reason") is not None
                     and r["x"].get("reason") is not None
                     and abs(prev["x"]["reason"] - r["x"]["reason"]) <= 6.0)
        if (only_reason and same_band and prev is not None
                and prev["cells"]["player"]
                and (not c["matchup"] or c["matchup"] == prev["cells"]["matchup"])):
            prev["cells"]["reason"] = (prev["cells"]["reason"] + " "
                                        + c["reason"].strip()).strip()
            prev.setdefault("wrapped_reason_lines", []).append(c["reason"].strip())
            continue
        merged.append(r)
    records = merged

    # "NOT YET SUBMITTED" is printed in the Reason column of a team block that
    # has not filed.  It is a filing-status placeholder for the whole block,
    # not a player status and not a reason, so it is transcribed into the
    # status column with the printed text kept verbatim alongside it.  Nothing
    # else is moved between columns.
    for r in records:
        c = r["cells"]
        if ((not c["player"]) and (not c["status"])
                and c["reason"].strip().upper() == "NOT YET SUBMITTED"):
            c["status"] = "NOT YET SUBMITTED"
            c["printed_raw"] = "NOT YET SUBMITTED (printed in the Reason column)"
            c["reason"] = ""

    # The PDF merges the Game Date, Game Time, Matchup and Team cells
    # vertically: they are drawn once at the top of a block and every row
    # below the block clips an empty rectangle.  Inherit them from the row
    # above and record which fields were inherited, per row.
    rows, unparsed, carry = [], [], {c: "" for c in
                                     ("game_date", "game_time_et", "matchup", "team")}
    for r in records:
        cells = dict(r["cells"])
        inherited = {}
        for c in ("game_date", "game_time_et", "matchup", "team"):
            if cells.get(c):
                carry[c] = cells[c]
            elif carry[c]:
                cells[c] = carry[c]
                inherited[c] = True
        if not (cells.get("player") or cells.get("status") or cells.get("reason")):
            continue
        # The report's own column-header row and its page furniture are not
        # data rows; the line reader drops them too.
        if (cells.get("player", "").strip() in ("Player Name", "Name")
                or cells.get("status", "").strip() in ("Current Status", "Status")
                or cells.get("team", "").strip() == "Page"):
            continue
        if r.get("unassigned_text"):
            unparsed.append({"page": r["page"],
                             "unassigned_text": r["unassigned_text"][:8]})
        date = _norm_date(cells.get("game_date", "")) or cells.get("game_date", "")
        time_et = _norm_time(cells.get("game_time_et", "")) or cells.get("game_time_et", "")
        matchup = re.sub(r"\s*@\s*", "@", cells.get("matchup", "")).strip()
        rows.append([date, time_et, matchup, cells.get("team", "").strip(),
                     cells.get("player", "").strip(), cells.get("status", "").strip(),
                     cells.get("reason", "").strip()])
    return rows, unparsed


def _group_lines(words, tol=2.0):
    """Group positioned words into visual lines: [(y, [(x, word), ...]), ...].

    Lines come out in reading order (top of page first: the reports use the
    flipped coordinate space where y grows downward).
    """
    lines = []
    for x, y, w in sorted(words, key=lambda t: (t[1], t[0])):
        placed = False
        for line in lines:
            if abs(line[0] - y) <= tol:
                line[1].append((x, w))
                placed = True
                break
        if not placed:
            lines.append((y, [(x, w)]))
    for _, cells in lines:
        cells.sort()
    lines.sort(key=lambda line: line[0])
    return lines


def _find_header(lines):
    """Locate the report's column header line and return column x anchors."""
    for _, cells in lines:
        words = [w for _, w in cells]
        joined = " ".join(words)
        if "Matchup" in words and "Team" in words and "Status" in joined:
            anchors = {}
            for name, want in HEADER_WORDS.items():
                for i in range(len(cells) - len(want) + 1):
                    if tuple(w for _, w in cells[i:i + len(want)]) == want:
                        base = name.replace("_alt", "")
                        anchors.setdefault(base, cells[i][0])
                        break
            if {"game_date", "team", "status"} <= set(anchors):
                if "reason" not in anchors and "status" in anchors:
                    # Reason column sits right of Status; anchor it at the
                    # observed start of reason strings when the header word
                    # itself is absent from the extract.
                    anchors["reason"] = anchors["status"] + 80
                return anchors
    return None


def _row_bands(rects):
    """Cluster the report's cell rectangles into row bands [(y0, y1), ...].

    Cells of one row share y and h within ~1pt (fill and clip rectangles are
    drawn as offset pairs). Clusters are merged when their y-ranges overlap
    by at least half of the shorter band.
    """
    uniq = sorted({(round(y, 1), round(h, 1)) for _x, y, _w, h in rects})
    bands = []
    for y, h in uniq:
        placed = False
        for band in bands:
            lo, hi = band
            ov = min(hi, y + h) - max(lo, y)
            if ov > 0.5 * min(hi - lo, h):
                band[0] = min(lo, y)
                band[1] = max(hi, y + h)
                placed = True
                break
        if not placed:
            bands.append([y, y + h])
    return [tuple(b) for b in bands]


def parse_rows(pages):
    """Parse positioned words into report rows (COLS) + unparsed evidence.

    The report's own cell rectangles delimit each table row: a reason cell
    wraps over several text lines, and the player's name sits between those
    lines, so line-based grouping is wrong - every word is assigned to the
    row band that contains its baseline. Within a row, cells are assigned to
    the column bands located from the header line (Game Date, Game Time,
    Matchup, Team, Player Name, Current Status, Reason). Column values that
    the report prints once per team block (date/time/matchup/team) are
    inherited by the player rows below the block's first row. A word that
    falls in no row band (page furniture) or no column band is recorded
    under ``unparsed`` and never guessed.
    """
    rows, unparsed = [], []
    bands_used = 0
    block = {"game_date": "", "game_time_et": "", "matchup": "", "team": ""}
    for page in pages:
        words = page["words"] if isinstance(page, dict) else page
        rects = page.get("rects", []) if isinstance(page, dict) else []
        lines = _group_lines(words)
        anchors = _find_header(lines)
        if not anchors:
            if not rows:
                continue
            # continuation page: reuse the column anchors found earlier
            anchors = parse_rows.last_anchors
        parse_rows.last_anchors = anchors
        bands_used = sorted(((x, name) for name, x in anchors.items()))
        row_bands = _row_bands(rects) if rects else []
        if not row_bands:
            continue
        for y0, y1 in row_bands:
            col_words = {name: [] for name in anchors}
            outside = []
            for x, y, w in words:
                if not (y0 - 2 <= y <= y1 + 2):
                    continue
                name = None
                for i, (bx, bname) in enumerate(bands_used):
                    nxt = bands_used[i + 1][0] if i + 1 < len(bands_used) else float("inf")
                    if bx - 6 <= x < nxt - 6:
                        name = bname
                        break
                if name:
                    col_words[name].append((y, x, w))
                else:
                    outside.append(w)
            if outside:
                unparsed.append({"band": [y0, y1], "outside_bands": outside[:8]})
            vals = {}
            for k, ws in col_words.items():
                ws.sort()
                vals[k] = " ".join(w for _y, _x, w in ws)
            if not any(vals.values()):
                continue
            date = _norm_date(vals.get("game_date", "")) or block["game_date"]
            time_et = _norm_time(vals.get("game_time", "")) or block["game_time_et"]
            matchup = re.sub(r"\s*@\s*", "@", vals.get("matchup", "")).strip() \
                or block["matchup"]
            team = vals.get("team", "").strip() or block["team"]
            if vals.get("game_date") or vals.get("team"):
                block = {"game_date": date, "game_time_et": time_et,
                         "matchup": matchup, "team": team}
            player = vals.get("player", "").strip()
            status = vals.get("status", "").strip()
            reason = vals.get("reason", "").strip()
            if re.fullmatch(r"Page|\d+ of \d+", player) or team == "Page":
                continue  # page furniture
            if team in ("Team", "Injury Report:") or player in ("Player Name", "Name") \
                    or status in ("Current Status", "Status"):
                continue  # title row / column-header row
            if not player and "NOT YET SUBMITTED" in (status + " " + reason):
                # The league prints the block placeholder where its layout
                # puts status text; store it in the status column to match
                # the published schema, with the reason blank.
                status, reason = "NOT YET SUBMITTED", ""
            if not status and not player:
                unparsed.append({"band": [y0, y1], "cells": vals})
                continue
            rows.append([date, time_et, matchup, team, player, status, reason])
    return rows, unparsed


parse_rows.last_anchors = None


def _norm_date(text):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text)
    if not m:
        return text.strip()
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 2000
    return f"{yr:04d}-{mo:02d}-{da:02d}"


def _norm_time(text):
    """Normalise the report's printed game time.

    The league prints the 12-hour clock value with a ``(ET)`` suffix and no
    meridiem ("01:00 (ET)" = 1:00 PM ET). The value is kept exactly as
    printed (hours zero-padded) - converting to 24-hour would diverge from
    the published schema, which stores the report's own value.
    """
    t = re.sub(r"\s*\(ET\)\s*", " ", text).strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return t


def edition_key(filename):
    """Newest-first sort key for an archived edition filename."""
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", filename)
    if not m:
        return (filename, 0)
    year, mo, day, hh, mm, ampm = m.groups()
    hour24 = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return (f"{year}-{mo}-{day}", hour24 * 100 + int(mm))


def edition_label(filename):
    m = re.search(r"(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM))",
                  filename)
    return m.group(1) if m else filename


def load_edition(pdf_path):
    """Parse one archived PDF into a metadata+rows record.

    The primary reader is the report's own clipped-rectangle reader.  The
    visual-line reader is run as well and the two are compared, because the
    line reader was measured to drop player rows that the cell reader
    recovers (flag F-X01).  The comparison travels with the record so the
    disagreement stays visible to a reviewer instead of being resolved
    silently.
    """
    stem = pdf_path[:-4]
    sidecar = {}
    if os.path.exists(stem + ".json"):
        with open(stem + ".json", encoding="utf-8") as fh:
            sidecar = json.load(fh)
    with open(pdf_path, "rb") as fh:
        raw = fh.read()
    import hashlib

    pages = extract_pages(raw)

    cells = extract_cells(raw)
    cols = detect_columns(cells)
    cell_rows, cell_unparsed = _assemble_cell_rows(
        _rows_to_records(group_rows(cells), cols)) if cols else ([], [])
    cell_players = {r[4] for r in cell_rows if r[4]}

    line_rows, line_unparsed = parse_rows(pages)
    line_players = {r[4] for r in line_rows if r[4]}

    reader = "clipped-rectangle"
    rows, unparsed = cell_rows, cell_unparsed
    if not cell_rows and line_rows:
        # No clipped geometry in this document - fall back to the line reader
        # and say so in the record.
        reader = "visual-line (fallback: no clipped cells found)"
        rows, unparsed = line_rows, line_unparsed

    cross_check = {
        "primary_reader": reader,
        "secondary_reader": "visual-line",
        "cell_reader_rows": len(cell_rows),
        "line_reader_rows": len(line_rows),
        "cell_only_players": sorted(cell_players - line_players),
        "line_only_players": sorted(line_players - cell_players),
        "both_readers_players": len(cell_players & line_players),
        "status_disagreements": [],
    }
    by_cell = {r[4]: r for r in cell_rows if r[4]}
    by_line = {r[4]: r for r in line_rows if r[4]}
    for player in sorted(cell_players & line_players):
        if by_cell[player][5] != by_line[player][5]:
            cross_check["status_disagreements"].append({
                "player": player,
                "cell_reader_status": by_cell[player][5],
                "line_reader_status": by_line[player][5],
            })

    return {
        "edition": sidecar.get("edition") or os.path.basename(pdf_path),
        "label": edition_label(os.path.basename(pdf_path)),
        "source_url": sidecar.get("source_url"),
        "retrieved_at_utc": sidecar.get("retrieved_at_utc"),
        "sha256": sidecar.get("sha256") or hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "pages": len(pages),
        "cols": COLS,
        "reader": reader,
        "rows": rows,
        "row_count": len(rows),
        "unparsed": unparsed[:20],
        "reader_cross_check": cross_check,
    }


def diff_editions(before, after):
    """Diff two consecutive editions, keyed by (team, player).

    Detects: status changes, reason changes, added and removed listings, and
    team-block filing transitions (NOT YET SUBMITTED -> filed). Games slates
    differ between editions, so only players listed in both can change status;
    that limitation is recorded in the output, never worked around by guess.
    """
    def keyset(rec):
        out = {}
        for r in rec["rows"]:
            _d, _t, _m, team, player, status, reason = r
            if not player:
                continue
            out[(team, player)] = {"status": status, "reason": reason,
                                   "matchup": _m, "game_date": _d}
        return out

    b, a = keyset(before), keyset(after)
    changes, added, removed = [], [], []
    for k in sorted(set(b) & set(a)):
        if b[k]["status"] != a[k]["status"] or b[k]["reason"] != a[k]["reason"]:
            changes.append({
                "team": k[0], "player": k[1],
                "before_status": b[k]["status"], "after_status": a[k]["status"],
                "before_reason": b[k]["reason"], "after_reason": a[k]["reason"],
                "before_matchup": b[k]["matchup"], "after_matchup": a[k]["matchup"],
            })
    for k in sorted(set(a) - set(b)):
        added.append({"team": k[0], "player": k[1], "status": a[k]["status"],
                      "reason": a[k]["reason"], "matchup": a[k]["matchup"]})
    for k in sorted(set(b) - set(a)):
        removed.append({"team": k[0], "player": k[1], "status": b[k]["status"],
                        "matchup": b[k]["matchup"]})

    def blocks(rec):
        out = {}
        for r in rec["rows"]:
            _d, _t, _m, team, player, status, _r = r
            if team and not player:
                out[(team, _m)] = status
        return out

    bb, ab = blocks(before), blocks(after)
    filing = [{"team": k[0], "matchup": k[1], "before": bb[k], "after": ab[k]}
              for k in sorted(set(bb) & set(ab)) if bb[k] != ab[k]]
    return {
        "title": "Injury-report consecutive-edition diff (status-change detection)",
        "before": {"edition": before["edition"], "label": before["label"],
                   "source_url": before["source_url"],
                   "retrieved_at_utc": before["retrieved_at_utc"],
                   "sha256": before["sha256"], "rows": before["row_count"]},
        "after": {"edition": after["edition"], "label": after["label"],
                  "source_url": after["source_url"],
                  "retrieved_at_utc": after["retrieved_at_utc"],
                  "sha256": after["sha256"], "rows": after["row_count"]},
        "comparability_note": (
            "Consecutive editions cover different game slates. A player-level "
            "status change can only be observed for players listed in both "
            "editions; listed-additions and listed-removals usually reflect "
            "the slate change, not a status change."),
        "status_or_reason_changes": changes,
        "listed_in_after_only": added,
        "listed_in_before_only": removed,
        "team_block_filing_changes": filing,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-dir", default=PDF_DIR)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()
    paths = sorted(glob.glob(os.path.join(args.pdf_dir, "*.pdf")),
                   key=lambda p: edition_key(os.path.basename(p)))
    if not paths:
        print("no archived injury PDFs found - nothing to diff")
        return 0
    os.makedirs(os.path.join(args.out_dir, "editions"), exist_ok=True)
    editions = []
    for p in paths:
        rec = load_edition(p)
        out = os.path.join(args.out_dir, "editions",
                           rec["label"] + ".json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)
            fh.write("\n")
        print(f"{rec['label']}: {rec['row_count']} rows, "
              f"{len(rec['unparsed'])} unparsed cells, {rec['pages']} pages")
        editions.append(rec)
    diffs = []
    for before, after in zip(editions, editions[1:]):
        d = diff_editions(before, after)
        out = os.path.join(args.out_dir,
                           f"diff_{before['label']}_to_{after['label']}.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
            fh.write("\n")
        diffs.append(os.path.basename(out))
        print(f"  diff -> {os.path.basename(out)}: "
              f"{len(d['status_or_reason_changes'])} status/reason changes, "
              f"{len(d['team_block_filing_changes'])} filing changes")
    index = {"editions": [{"label": e["label"], "rows": e["row_count"],
                           "source_url": e["source_url"],
                           "retrieved_at_utc": e["retrieved_at_utc"],
                           "sha256": e["sha256"]} for e in editions],
             "diffs": diffs,
             "rule": "Parsed verbatim from the official PDFs archived under "
                     "data/raw/injury_pdfs/; unparseable cells are recorded "
                     "under unparsed and never inferred."}
    with open(os.path.join(args.out_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
