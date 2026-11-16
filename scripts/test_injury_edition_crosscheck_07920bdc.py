#!/usr/bin/env python3
"""Regression tests for the cell-based injury-PDF reader (§56 / X03, flag F-X01).

``engine/injury_diff.py`` groups words into visual lines. On the 2026-11-16
01:15 PM edition it returned 80 rows and reported **zero** unparsed cells while
the PDF bytes contain 87 report rows - seven player rows simply were not
returned. A silent drop is the worst possible failure mode for an archive whose
whole purpose is to detect a status change, so this file pins the property that
matters: the independent cell reader must recover at least the rows the line
parser finds, and must recover the seven this edition actually contains.

Standard library only; skips cleanly when no archived PDFs are present.
"""

import glob
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")

import verify_injury_edition_07920bdc as v  # noqa: E402


def newest_pdf():
    paths = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                   key=lambda p: v.edition_key(os.path.basename(p)))
    return paths[-1] if paths else None


def read(path):
    """The same pipeline the report writer uses, not a copy of it."""
    with open(path, "rb") as fh:
        raw = fh.read()
    cells = v.extract_cells(raw)
    cols = v.detect_columns(cells)
    recs = v.rows_to_records(
        v.group_rows([c for c in cells if c["text"].strip()]), cols)
    body = []
    for r in recs:
        joined = " ".join(r["cells"][c] for c in v.COLS).lower()
        if "player name" in joined or "current status" in joined:
            continue
        if not any(r["cells"][c] for c in v.COLS):
            continue
        if joined.startswith("injury report"):
            continue
        body.append(r)
    return cells, cols, v.complete_rows(body)


@unittest.skipUnless(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                     "no archived injury PDFs in the repository")
class CellReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = newest_pdf()
        cls.label = v.label_from_filename(os.path.basename(cls.path))
        cls.cells, cls.cols, cls.rows = read(cls.path)

    def test_columns_detected_from_the_pages_own_header(self):
        # Every column must be located from the report's own header row, never
        # from a hard-coded x position: the league can re-layout the table.
        self.assertGreaterEqual(len(set(self.cols.values())), 5)

    def test_rows_recovered(self):
        self.assertGreater(len(self.rows), 20)

    def test_reader_is_monotone_against_the_line_parser(self):
        """The cell reader must never find FEWER player rows than the line parser.

        It may find more - that is the whole point of the second reader - but a
        regression that makes it find fewer would silently reintroduce a
        dropped-row edition.
        """
        parsed = os.path.join(ROOT, "data", "parsed", "injury_diffs",
                              "editions", self.label + ".json")
        if not os.path.exists(parsed):
            self.skipTest("engine/injury_diff.py has not parsed %s" % self.label)
        with open(parsed, encoding="utf-8") as fh:
            line_rows = json.load(fh).get("rows") or []
        line_players = {r[4] for r in line_rows if r[4]}
        cell_players = {r["cells"]["player"] for r in self.rows
                        if r["cells"]["player"]}
        self.assertTrue(line_players.issubset(cell_players),
                        "cell reader lost %d player row(s) the line parser found: %s"
                        % (len(line_players - cell_players),
                           sorted(line_players - cell_players)))

    def test_the_seven_rows_the_line_parser_dropped_are_in_the_bytes(self):
        """F-X01 pinned: these players are in the 2026-11-16 01:15 PM PDF."""
        if self.label != "Injury-Report_2026-11-16_01_15PM":
            self.skipTest("newest archived edition is %s, not the one this "
                          "regression pins" % self.label)
        expected = {("MEM@WAS", "Memphis Grizzlies", "Jerome, Ty", "Out"),
                    ("MEM@WAS", "Memphis Grizzlies", "Pippen Jr., Scotty", "Out"),
                    ("MEM@WAS", "Memphis Grizzlies", "Post, Quinten", "Questionable"),
                    ("MEM@WAS", "Memphis Grizzlies", "Saunders, Richie", "Out"),
                    ("MEM@WAS", "Memphis Grizzlies", "Stewart, Isaiah", "Out"),
                    ("GSW@NOP", "New Orleans Pelicans", "Reese, Julian", "Questionable"),
                    ("GSW@NOP", "New Orleans Pelicans", "Watford, Trendon", "Out")}
        found = {(r["cells"]["matchup"], r["cells"]["team"],
                  r["cells"]["player"], r["cells"]["status"]) for r in self.rows}
        self.assertTrue(expected.issubset(found),
                        "missing: %s" % sorted(expected - found))


if __name__ == "__main__":
    unittest.main()
