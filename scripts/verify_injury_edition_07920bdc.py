#!/usr/bin/env python3
"""Independent, cell-based extraction of an official injury-report PDF (§56 / X03).

Why this exists
---------------
``engine/injury_diff.py`` recovers report text by grouping words into *visual
lines* and assigning them to column bands. Reading the 2026-11-16 01:15 PM
edition with it returns 80 rows and **zero** unparsed cells - but the PDF's own
content stream contains player rows the parser never returns (measured: the five
Memphis rows Jerome / Pippen Jr. / Post / Saunders / Stewart, and the two New
Orleans rows Reese / Watford). A parser that drops rows silently is worse than
a parser that reports them as unparsed, because the count looks complete.

The official reports draw their table as **explicit clipped rectangles**: every
populated cell is

    q
    <x> <y> <w> <h> re
    W* n
    BT ... (text) Tj ... ET
    Q

and every empty cell is the same block without the ``BT..ET``. That structure is
independent of how the text happens to wrap, so this module extracts per *cell*
and groups cells into rows by their vertical intervals. It is written as a
second, independent reader so the two can be cross-checked: a row is published
only when the bytes say it is there, and any row one reader finds and the other
does not is reported instead of being resolved by guesswork.

Output: ``verify/2026-11-16-07920bdc/injury_edition_crosscheck_<label>.json``.

Rules: standard library only; nothing inferred; a cell whose text cannot be
recovered is recorded as unreadable, never filled in.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")
PARSED_DIR = os.path.join(ROOT, "data", "parsed", "injury_diffs", "editions")
OUT_DIR = os.path.join(ROOT, "verify", "2026-11-16-07920bdc")

COLS = ["game_date", "game_time_et", "matchup", "team", "player", "status", "reason"]
HEADER_TEXT = {
    "game date": "game_date", "game time": "game_time_et", "matchup": "matchup",
    "team": "team", "player name": "player", "current status": "status",
    "reason": "reason", "reason/comments": "reason", "comments": "reason",
}

# One table cell, clipped rectangle plus optional text.
CELL_RE = re.compile(
    r"q\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+re\s+W\*\s*n\s*"
    r"(?:BT(.*?)ET)?\s*Q", re.S)

# A drawn string: either "x y Td (text) Tj" or "dx dy Td (text) Tj".
TJ_RE = re.compile(r"(-?[\d.]+)\s+(-?[\d.]+)\s+Td\s*\((.*?)\)\s*Tj", re.S)
TJ_ARRAY_RE = re.compile(r"(-?[\d.]+)\s+(-?[\d.]+)\s+Td\s*\[(.*?)\]\s*TJ", re.S)


def cell_text(block: str) -> str:
    """Concatenate the drawn strings of one BT..ET block, in document order.

    Both text operators are handled: ``(word) Tj`` (a single string) and
    ``[(wo) -250 (rd)] TJ`` (a kerned array). Only the parenthesised strings are
    taken, and only in the order they are drawn, so a wrapped cell reads back the
    way the page prints it.
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
            # A hyphenated word is drawn as two kerned strings, "(Two-)" then
            # "(Way)". Joining them with a space prints "Two- Way", which is not
            # what the page shows. A standalone "-" is a dash, not a hyphen, so
            # it keeps its surrounding spaces. (Both readers of these PDFs had
            # this artifact; flag F-X02.)
            out = out + part
        else:
            out = out + " " + part
    return out.strip()


def unescape(text: str) -> str:
    return (text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
            .replace(r"\n", " ").replace(r"\r", " "))


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
            text = cell_text(m.group(5) or "")
            cells.append({"page": page_no, "x": round(x, 3), "y": round(y, 3),
                          "w": round(w, 3), "h": round(h, 3), "text": text})
    return cells


def detect_columns(cells: list) -> dict:
    """Map an x-position to a column name using the page's own header row."""
    xs = {}
    for c in cells:
        key = c["text"].strip().lower().rstrip(":")
        if key in HEADER_TEXT:
            xs.setdefault(round(c["x"], 1), HEADER_TEXT[key])
    if len(xs) >= 5:
        return xs
    return {}


def column_for(x: float, cols: dict, tol: float = 6.0) -> str:
    best, best_d = None, None
    for cx, name in cols.items():
        d = abs(cx - x)
        if d <= tol and (best_d is None or d < best_d):
            best, best_d = name, d
    return best


def group_rows(cells: list, y_tol: float = 1.6, h_tol: float = 2.1) -> list:
    """Group cells into rows.

    Every cell of one table row is drawn with the same rectangle geometry: the
    four left-hand columns sit one point lower and one point taller than the
    player/status/reason cells (measured on the 2026-11-16 editions), so the
    tolerances below are set to absorb that and nothing more. Adjacent rows are
    vertically contiguous - the next row's bottom edge is this row's top edge -
    which is exactly why contiguity must NOT be used to merge: it would join the
    whole page into one row. A row boundary is a change in the rectangle itself.
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
            rec[name] = (rec[name] + " " + c["text"].strip()).strip() if rec[name] else c["text"].strip()
            xs.setdefault(name, c["x"])
        out.append({"cells": rec, "page": r[0]["page"], "x": xs,
                    "unassigned_text": unassigned})
    return out


def edition_key(name: str):
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0, 0)
    y, mo, d, hh, mm, ap = m.groups()
    return (f"{y}-{mo}-{d}", int(hh) % 12 + (12 if ap == "PM" else 0), mm)


def label_from_filename(name: str) -> str:
    return re.sub(r"\.pdf$", "", name.split("__")[0])


def find_pdf(label: str) -> str:
    hits = [p for p in glob.glob(os.path.join(PDF_DIR, "*.pdf"))
            if label_from_filename(os.path.basename(p)) == label]
    if not hits:
        raise SystemExit(f"no archived PDF for edition {label}")
    return sorted(hits)[0]


def parsed_rows_for(label: str) -> list:
    path = os.path.join(PARSED_DIR, label + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("rows")


def complete_rows(body: list) -> list:
    """Re-join wrapped reasons, normalise NOT YET SUBMITTED, and inherit
    the merged Game Date / Game Time / Matchup / Team cells.

    Kept as a function so the unit test can exercise the same pipeline the
    report writer uses, rather than a copy of it.
    """
    if not body:
        return []
    # A reason that wraps is drawn as a second clipped rectangle in the same
    # x-band, immediately below: the grouper sees it as a row of its own.
    # Re-join it to the row it continues, and only when the continuation
    # carries nothing but reason text in the same column on the same page -
    # otherwise it is left alone and reported, never merged by guesswork.
    merged = []
    for r in body:
        prev = merged[-1] if merged else None
        c = r["cells"]
        only_reason = (not c["player"]) and (not c["status"]) and bool(c["reason"].strip()) \
            and c["reason"].strip().upper() != "NOT YET SUBMITTED"
        # Same x-band, and on the same page or the page immediately before:
        # the report's table continues across a page break, and a wrapped
        # reason can break exactly at the boundary (measured: "Injury/Illness
        # - Left 5th Metatarsal / Fracture" for Jackson, GG, 2026-11-16).
        same_band = (prev is not None
                     and 0 <= r["page"] - prev["page"] <= 1
                     and prev["x"].get("reason") is not None
                     and r["x"].get("reason") is not None
                     and abs(prev["x"]["reason"] - r["x"]["reason"]) <= 6.0)
        if (only_reason and same_band and prev is not None
                and prev["cells"]["player"]
                and (not c["matchup"] or c["matchup"] == prev["cells"]["matchup"])):
            prev["cells"]["reason"] = (prev["cells"]["reason"] + " " + c["reason"].strip()).strip()
            prev.setdefault("wrapped_reason_lines", []).append(c["reason"].strip())
            continue
        merged.append(r)
    body = merged

    # NOT YET SUBMITTED is printed in the Reason column of a team block that
    # has not filed: it is a filing-status placeholder for the whole block,
    # not a player status and not a reason. Transcribe it into `status` (the
    # column semantics the rest of the repository uses) and keep the printed
    # text verbatim in `printed_raw` so the move is auditable rather than
    # silent. Nothing else is moved between columns.
    for r in body:
        c = r["cells"]
        if (not c["player"]) and (not c["status"]) and \
                c["reason"].strip().upper() == "NOT YET SUBMITTED":
            c["status"] = "NOT YET SUBMITTED"
            c["printed_raw"] = "NOT YET SUBMITTED (printed in the Reason column)"
            c["reason"] = ""

    # The PDF merges the Game Date, Game Time, Matchup and Team cells
    # vertically: they are drawn once at the top of a block and every
    # following row in the block clips an empty rectangle. Inherit them from
    # the row above, and say so per row. This is the same property the
    # repository already records as `merged_cell_caveat`; it is transcription
    # of what the page prints, not inference of a value that is absent.
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
        kept.append({"cells": cells, "page": r["page"],
                     "inherited": inherited,
                     "wrapped_reason_lines": r.get("wrapped_reason_lines", []),
                     "unassigned_text": r["unassigned_text"]})
    return kept


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edition", default=None,
                    help="edition label, e.g. Injury-Report_2026-11-16_01_15PM "
                         "(default: the newest archived edition)")
    ap.add_argument("--newest-n", type=int, default=3,
                    help="also cross-check the N newest archived editions")
    args = ap.parse_args()

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                  key=lambda p: edition_key(os.path.basename(p)))
    if not pdfs:
        raise SystemExit("no archived injury PDFs")
    labels = [label_from_filename(os.path.basename(p)) for p in pdfs]
    targets = [args.edition] if args.edition else labels[-args.newest_n:]

    os.makedirs(OUT_DIR, exist_ok=True)
    for label in targets:
        pdf_path = find_pdf(label)
        raw = open(pdf_path, "rb").read()
        cells = extract_cells(raw)
        cols = detect_columns(cells)
        data_cells = [c for c in cells if c["text"].strip()]
        rows = group_rows(data_cells)
        recs = rows_to_records(rows, cols)

        # Drop the repeated per-page header rows and the printed title rows.
        body = []
        for r in recs:
            joined = " ".join(r["cells"][c] for c in COLS).lower()
            if "player name" in joined or "current status" in joined:
                continue
            if not any(r["cells"][c] for c in COLS):
                continue
            if joined.startswith("injury report"):
                continue
            body.append(r)

        kept = complete_rows(body)


        line_rows = parsed_rows_for(label) or []
        # Key on (matchup, team, player) - the identity of a report row. A team
        # block that has not filed has no player, so it is keyed on its own team
        # block and compared as a block.
        cell_keys = {}
        for r in kept:
            c = r["cells"]
            key = (c["matchup"], c["team"], c["player"] or "<team block>")
            cell_keys[key] = c["status"] or ("NOT YET SUBMITTED"
                                             if c["reason"].strip().upper()
                                             == "NOT YET SUBMITTED" else "")
        line_keys = {}
        for r in line_rows:
            key = (r[2], r[3], r[4] or "<team block>")
            line_keys[key] = r[5] or (r[6] if "NOT YET SUBMITTED" in (r[6] or "")
                                      else "")

        only_cell = sorted(k for k in cell_keys if k not in line_keys)
        only_line = sorted(k for k in line_keys if k not in cell_keys)
        disagree = sorted(k for k in cell_keys
                          if k in line_keys and cell_keys[k] != line_keys[k])

        report = {
            "session": "arena/07920bdc-nba1",
            "purpose": ("COORDINATION §56 / X03 - independent cell-based re-read "
                        "of an official injury-report PDF, cross-checked against "
                        "engine/injury_diff.py's visual-line parser, so a dropped "
                        "row is detected instead of being published as complete."),
            "checked_at_utc": datetime.datetime.now(
                datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "edition": label,
            "pdf": os.path.relpath(pdf_path, ROOT).replace(os.sep, "/"),
            "pdf_sha256": __import__("hashlib").sha256(raw).hexdigest(),
            "extraction": {
                "method": ("per clipped-rectangle cell; cells grouped into rows by "
                           "vertical contiguity; columns mapped from each page's own "
                           "header row"),
                "columns_detected": {str(k): v for k, v in sorted(cols.items())},
                "clipped_cells": len(cells),
                "populated_cells": len(data_cells),
                "rows_recovered": len(kept),
                "player_rows": sum(1 for r in kept if r["cells"]["player"]),
                "wrapped_reason_rows_rejoined": sum(
                    1 for r in kept if r["wrapped_reason_lines"]),
                "team_blocks_not_yet_submitted": sum(
                    1 for r in kept
                    if r["cells"]["status"].strip().upper() == "NOT YET SUBMITTED"),
            },
            "engine_line_parser": {"rows": len(line_rows),
                                   "player_rows": len(line_keys)},
            "cross_check": {
                "in_both": len(cell_keys) - len(only_cell),
                "cell_extractor_only": [
                    {"matchup": k[0], "team": k[1], "player": k[2],
                     "status": cell_keys[k]} for k in only_cell],
                "line_parser_only": [
                    {"matchup": k[0], "team": k[1], "player": k[2],
                     "status": line_keys[k]} for k in only_line],
                "status_disagreements": [
                    {"matchup": k[0], "team": k[1], "player": k[2],
                     "cell_extractor": cell_keys[k],
                     "line_parser": line_keys[k]} for k in disagree],
            },
            "rule": ("Nothing is inferred. A row is published only when the PDF "
                     "bytes contain it; rows recovered by one reader and not the "
                     "other are listed here and flagged, never silently merged."),
            "rows": [dict(r["cells"],
                          **{"_inherited": sorted(r["inherited"]),
                             "_wrapped_reason": r["wrapped_reason_lines"],
                             "_page": r["page"]}) for r in kept],
        }
        out = os.path.join(OUT_DIR, f"injury_edition_crosscheck_{label}.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
            fh.write("\n")
        print(f"{label}: clipped cells {len(cells)}, rows {len(kept)}, "
              f"keys {len(cell_keys)}; line parser {len(line_keys)} keys")
        print(f"   cell-extractor only: {len(only_cell)} | line-parser only: "
              f"{len(only_line)} | status disagreements: {len(disagree)}")
        for k in only_cell:
            print(f"     + {k[0]} | {k[1]} | {k[2]} | {cell_keys[k]}")
        for k in only_line:
            print(f"     - {k[0]} | {k[1]} | {k[2]} | {line_keys[k]}")
        print(f"   -> {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
