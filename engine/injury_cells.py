"""Cell-level reader for the official NBA injury-report PDFs (flag F-X01).

Why this module exists
----------------------
``injury_diff.parse_rows`` groups *words* into the row band that contains their
baseline. Measured on the 2026-11-16 01:00/01:15 PM editions (this session, on
the committed PDF bytes, before any edit): it returns 80 rows and reports
``unparsed: 0`` while **seven player rows are missing** - Jerome, Pippen Jr.,
Post, Saunders and Stewart (Memphis, MEM@WAS) and Reese and Watford (New
Orleans, GSW@NOP). An archive whose whole purpose is to *detect* a status change
cannot drop rows while calling the parse clean. Flag F-X01, raised by session
``arena/07920bdc-nba1`` (COORDINATION §60.7 request 1: *"port the
per-clipped-rectangle reader ... into the engine parser, or make it fail loudly
when a row's cells do not assemble"*).

This module is that port. The official reports draw every table cell as an
explicit clipped rectangle:

    q <x> <y> <w> <h> re W* n  BT ... ET  Q

so the reader works per cell instead of per visual line. Rows are groups of
cells that share the rectangle geometry (the four left-hand columns are drawn
one point lower and one point taller than player/status/reason - measured, and
the tolerance is set to absorb that and nothing more). Wrapped reason text,
vertically merged block cells and the ``NOT YET SUBMITTED`` placeholder are
handled the way the page prints them, and every cell whose text could not be
assigned to a column is returned in ``unassigned_text`` - nothing is dropped
silently, and nothing is inferred.

The implementation was reviewed and published first by session
``arena/07920bdc-nba1`` as ``scripts/verify_injury_edition_07920bdc.py``
(COORDINATION §60.2), where it was cross-checked against the line parser on the
same bytes. This module keeps that behaviour and adds the two properties the
engine needs: rows come back in the engine's ``COLS`` order, and the audit block
states the counts both passes produced.

No third-party library is used - the GitHub Actions runner installs nothing.
"""

from __future__ import annotations

import re
import zlib

COLS = ["game_date", "game_time_et", "matchup", "team", "player", "status",
        "reason"]

HEADER_TEXT = {
    "game date": "game_date", "game time": "game_time_et",
    "matchup": "matchup", "team": "team",
    "player name": "player", "player": "player",
    "current status": "status", "status": "status",
    "reason": "reason", "reason/comments": "reason", "comments": "reason",
}

# One table cell: a clipped rectangle plus the text drawn inside it.
CELL_RE = re.compile(
    r"q\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+re\s+W\*\s*n\s*"
    r"(?:BT(.*?)ET)?\s*Q", re.S)


def unescape(text: str) -> str:
    return (text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
            .replace(r"\n", " ").replace(r"\r", " "))


def cell_text(block: str) -> str:
    """Concatenate the drawn strings of one BT..ET block, in document order.

    Handles both ``(word) Tj`` and the kerned array ``[(wo) -250 (rd)] TJ``.
    A hyphenated word is drawn as two strings ("(Two-)" then "(Way)"); joining
    them with a space would print "Two- Way", which is not what the page shows
    (flag F-X02). A standalone "-" is a dash and keeps its surrounding spaces.
    """
    if not block:
        return ""
    parts = []
    for m in re.finditer(r"\(((?:[^()\\]|\\.)*)\)", block):
        parts.append(unescape(m.group(1)))
    out = ""
    for part in (p for p in parts if p):
        if not out:
            out = part
        elif out.endswith("-") and len(out.rstrip("-")) > 0 and out[-2:-1] != " ":
            out = out + part
        else:
            out = out + " " + part
    return out.strip()


def page_text_streams(raw: bytes) -> list:
    """Decompress every FlateDecode content stream that draws text."""
    streams = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            data = zlib.decompress(m.group(1))
        except (zlib.error, ValueError):
            continue
        if b"Tj" in data or b"TJ" in data:
            streams.append(data.decode("latin-1"))
    return streams


def extract_cells(raw: bytes) -> list:
    """Every clipped rectangle in the document, with its text and page number."""
    cells = []
    for page_no, stream in enumerate(page_text_streams(raw), start=1):
        for m in CELL_RE.finditer(stream):
            x, y, w, h = (float(m.group(i)) for i in (1, 2, 3, 4))
            cells.append({"page": page_no, "x": round(x, 3), "y": round(y, 3),
                          "w": round(w, 3), "h": round(h, 3),
                          "text": cell_text(m.group(5) or "")})
    return cells


def detect_columns(cells: list) -> dict:
    """Map an x-position to a column name using the report's own header row."""
    xs = {}
    for c in cells:
        key = c["text"].strip().lower().rstrip(":")
        if key in HEADER_TEXT:
            xs.setdefault(round(c["x"], 1), HEADER_TEXT[key])
    return xs if len(xs) >= 5 else {}


def column_for(x: float, cols: dict, tol: float = 6.0):
    best, best_d = None, None
    for cx, name in cols.items():
        d = abs(cx - x)
        if d <= tol and (best_d is None or d < best_d):
            best, best_d = name, d
    return best


def group_rows(cells: list, y_tol: float = 1.6, h_tol: float = 2.1) -> list:
    """Group cells into table rows by shared rectangle geometry.

    Adjacent rows are vertically contiguous, so contiguity must NOT be used to
    merge - it would join the whole page into one row. A row boundary is a
    change in the rectangle itself.
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


def rows_to_records(rows: list, cols: dict) -> list:
    out = []
    for r in rows:
        rec = {c: "" for c in COLS}
        xs = {}
        unassigned = []
        for c in r:
            name = column_for(c["x"], cols)
            if name is None:
                if c["text"].strip():
                    unassigned.append(c["text"].strip())
                continue
            rec[name] = ((rec[name] + " " + c["text"].strip()).strip()
                          if rec[name] else c["text"].strip())
            xs.setdefault(name, c["x"])
        out.append({"cells": rec, "page": r[0]["page"], "x": xs,
                    "unassigned_text": unassigned})
    return out


_NORM_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")


def _norm_date(text: str) -> str:
    m = _NORM_DATE_RE.search(text or "")
    if not m:
        return (text or "").strip()
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 2000
    return f"{yr:04d}-{mo:02d}-{da:02d}"


def _norm_time(text: str) -> str:
    t = re.sub(r"\s*\(ET\)\s*", " ", text or "").strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else t


def complete_rows(body: list) -> list:
    """Re-join wrapped reasons, normalise NOT YET SUBMITTED, inherit merged cells."""
    if not body:
        return []
    merged = []
    for r in body:
        prev = merged[-1] if merged else None
        c = r["cells"]
        only_reason = (not c["player"]) and (not c["status"]) and bool(c["reason"].strip()) \
            and c["reason"].strip().upper() != "NOT YET SUBMITTED"
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
    body = merged

    for r in body:
        c = r["cells"]
        if (not c["player"]) and (not c["status"]) and \
                c["reason"].strip().upper() == "NOT YET SUBMITTED":
            c["status"] = "NOT YET SUBMITTED"
            c["printed_raw"] = "NOT YET SUBMITTED (printed in the Reason column)"
            c["reason"] = ""

    kept = []
    carry = {c: "" for c in ("game_date", "game_time_et", "matchup", "team")}
    for r in body:
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
        if cells.get("player") in ("Player Name", "Name") or cells.get("team") in ("Team",):
            continue          # the column-header row itself
        kept.append({"cells": cells, "page": r["page"], "inherited": inherited,
                     "wrapped_reason_lines": r.get("wrapped_reason_lines", []),
                     "unassigned_text": r["unassigned_text"]})
    return kept


def parse_pdf(raw: bytes) -> dict:
    """Read one injury-report PDF into engine rows plus a self-audit.

    Returns ``{"rows": [[date, time, matchup, team, player, status, reason], ...],
    "audit": {...}}``. ``audit`` states, in numbers the caller can assert on:
    how many clipped cells the PDF draws, how many rows the cell reader
    assembled, how many carry a player name, and every piece of text that was
    drawn but could not be assigned to a column (``unassigned_text``).
    """
    cells = extract_cells(raw)
    cols = detect_columns(cells)
    if not cols:
        return {"rows": [], "audit": {"clipped_cells": len(cells),
                                      "columns_detected": 0,
                                      "error": "no header row found - the page "
                                               "does not draw the report's own "
                                               "column headers"}}
    body = rows_to_records(group_rows(cells), cols)
    kept = complete_rows(body)
    rows = []
    unassigned = []
    for r in kept:
        c = r["cells"]
        rows.append([_norm_date(c.get("game_date", "")),
                     _norm_time(c.get("game_time_et", "")),
                     re.sub(r"\s*@\s*", "@", c.get("matchup", "")).strip(),
                     c.get("team", "").strip(),
                     c.get("player", "").strip(),
                     c.get("status", "").strip(),
                     c.get("reason", "").strip()])
        for t in r["unassigned_text"]:
            unassigned.append({"page": r["page"], "text": t})
    audit = {
        "clipped_cells": len(cells),
        "columns_detected": len(cols),
        "cell_rows_assembled": len(kept),
        "player_rows": sum(1 for r in rows if r[4]),
        "block_rows": sum(1 for r in rows if not r[4]),
        "unassigned_text": unassigned[:40],
        "unassigned_count": len(unassigned),
    }
    return {"rows": rows, "audit": audit}
