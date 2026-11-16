"""Unit tests for engine/injury_diff.py (RFG4, COORDINATION.md section 42).

The PDF tests run against the REAL archived official report bytes in
data/raw/injury_pdfs/ (content-addressed, retrieved by the scheduled fetcher
from ak-static.cms.nba.com). Expected values are cross-checked against the
independent transcription data/official/injury_2026-11-15_0615AM.json where
the two editions share players. Standard library only.
"""

import glob
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "engine"))

import injury_diff as ij  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")


class ScannerTests(unittest.TestCase):
    def test_bt_blocks_ignore_operator_names_in_strings(self):
        # The official reports contain "NOT YET SUBMITTED"; a naive BT..ET
        # regex truncates at the "ET" of "(YET)". This is a regression test
        # for that exact failure (found against the 2026-11-15 05:15 PM PDF).
        text = ("BT\n0 g\n100 200 Td (NOT) Tj\n20 0 Td (YET) Tj\n"
                "16 0 Td (SUBMITTED) Tj\nET\n")
        blocks = list(ij._iter_bt_blocks(text))
        self.assertEqual(len(blocks), 1)
        self.assertIn("(SUBMITTED) Tj", blocks[0])

    def test_pdf_unescape(self):
        self.assertEqual(ij._pdf_unescape(r"A\(B\) \\ C"), "A(B) \\ C")
        self.assertEqual(ij._pdf_unescape(r"\101"), "A")


@unittest.skipUnless(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                     "no archived injury PDFs in the repository")
class RealPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                       key=lambda p: ij.edition_key(os.path.basename(p)))
        cls.rec = ij.load_edition(paths[-1])
        with open(os.path.join(ROOT, "data", "official",
                               "injury_2026-11-15_0615AM.json")) as fh:
            cls.cross = json.load(fh)
        # F-DFA-02 (session arena/07920bdc-nba1, COORDINATION §56 X06): the
        # Furphy assertion below is a comparison against an INDEPENDENT
        # transcription of one named edition, so it must be run against that
        # edition's PDF - not against whatever happens to be newest in the
        # archive. Pinned to the newest, it failed the moment the league rolled
        # to an 11/16 slate whose report no longer lists that player: a stale
        # fixture, not a parser fault. Load the edition the transcription was
        # made from, and skip the comparison cleanly if those bytes are absent.
        cls.cross_rec = None
        cross_edition = cls.cross.get("source_url", "").rsplit("/", 1)[-1]
        for p in paths:
            if os.path.basename(p).split("__")[0] + ".pdf" == cross_edition:
                cls.cross_rec = ij.load_edition(p)
                break

    def test_rows_extracted(self):
        self.assertGreater(self.rec["row_count"], 50)

    def test_wrapped_reason_matches_independent_transcription(self):
        # Furphy's reason wraps across three text lines around his name row;
        # the independent 06:15 AM transcription of the same slate confirms
        # the full phrase.
        #
        # F-DFA-02: run it against the edition the independent transcription
        # was made from (see setUpClass), never against "the newest archived
        # PDF". A slate roll is not a regression, and this test exists to catch
        # a parsing regression, not the calendar.
        if self.cross_rec is None:
            self.skipTest("the PDF behind the independent transcription is not "
                          "archived in this checkout")
        # Both readers of these PDFs split a hyphenated word into two kerned
        # strings and re-join them with a space, printing "Two- Way" for
        # "Two-Way" (flag F-X02). That is a rendering artifact in both, not a
        # disagreement about content, so it is normalised before comparing -
        # and only that, so any other difference still fails the test.
        def norm(text):
            return re.sub(r"(\w)-\s+(\w)", r"\1-\2", text or "")

        rows = {r[4]: r for r in self.cross_rec["rows"]}
        cross_rows = self.cross.get("rows") or []
        checked = 0
        for cross in cross_rows:
            player = cross.get("player")
            if not player or not cross.get("reason"):
                continue
            parsed = rows.get(player)
            if parsed is None:
                continue
            checked += 1
            self.assertEqual(norm(parsed[6]), norm(cross["reason"]),
                             "reason mismatch for %s" % player)
        self.assertGreaterEqual(checked, 20,
                                "expected the two independent reads of the same "
                                "edition to share at least 20 player rows")

    def test_not_yet_submitted_blocks_present(self):
        nys = [r for r in self.rec["rows"] if r[5] == "NOT YET SUBMITTED"]
        self.assertGreaterEqual(len(nys), 1)

    def test_provenance_carried(self):
        self.assertTrue(self.rec["source_url"].startswith(
            "https://ak-static.cms.nba.com/referee/injury/"))
        self.assertRegex(self.rec["sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(self.rec["retrieved_at_utc"])


class DiffTests(unittest.TestCase):
    def test_status_change_detected(self):
        a = {"rows": [["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers",
                       "Doe, John", "Questionable", "Ankle"],
                      ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers",
                       "", "NOT YET SUBMITTED", ""]],
             "row_count": 2, "edition": "a", "label": "A",
             "source_url": "u", "retrieved_at_utc": "t", "sha256": "s"}
        b = {"rows": [["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers",
                       "Doe, John", "Out", "Ankle"],
                      ["2026-11-15", "01:00", "IND@PHI", "Indiana Pacers",
                       "", "Out", ""]],
             "row_count": 2, "edition": "b", "label": "B",
             "source_url": "u2", "retrieved_at_utc": "t2", "sha256": "s2"}
        d = ij.diff_editions(a, b)
        self.assertEqual(len(d["status_or_reason_changes"]), 1)
        self.assertEqual(d["status_or_reason_changes"][0]["after_status"], "Out")
        self.assertEqual(len(d["team_block_filing_changes"]), 1)


if __name__ == "__main__":
    unittest.main()
