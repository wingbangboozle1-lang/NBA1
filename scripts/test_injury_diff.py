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
    # The edition this test audits is named, not "whichever PDF is newest". The
    # transcription it is cross-checked against is the 11/15 06:15 AM ET edition, so
    # asking the newest archived PDF to still contain Furphy's row made the test fail
    # the moment the archive advanced past that edition - a real 11/16 report simply
    # does not list an 11/15 injury. Pinning the edition keeps the assertion about the
    # parser (a reason cell wrapped across three text lines) instead of about the
    # calendar. (session arena/3ff8ff0f-nba1, flag F133)
    AUDIT_EDITION = "Injury-Report_2026-11-15_06_15AM.pdf"

    @classmethod
    def setUpClass(cls):
        paths = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                       key=lambda p: ij.edition_key(os.path.basename(p)))
        want = next((p for p in paths
                     if os.path.basename(p).startswith(cls.AUDIT_EDITION[:-4])), None)
        if want is None:
            raise unittest.SkipTest(
                "the edition this test cross-checks (%s) is not in the archive; the "
                "archive has grown past it and the parser is still exercised by the "
                "other tests here" % cls.AUDIT_EDITION)
        cls.rec = ij.load_edition(want)
        with open(os.path.join(ROOT, "data", "official",
                               "injury_2026-11-15_0615AM.json")) as fh:
            cls.cross = json.load(fh)

    def test_rows_extracted(self):
        self.assertGreater(self.rec["row_count"], 50)

    def test_wrapped_reason_matches_independent_transcription(self):
        # Furphy's reason wraps across three text lines around his name row;
        # the independent 06:15 AM transcription of the same slate confirms
        # the full phrase.
        rows = {r[4]: r for r in self.rec["rows"]}
        furphy = rows.get("Furphy, Johnny")
        self.assertIsNotNone(furphy)
        cross_rows = self.cross.get("rows") or []
        cross = next((r for r in cross_rows
                      if r.get("player") == "Furphy, Johnny"), None)
        if cross:
            self.assertEqual(furphy[6], cross["reason"])

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
