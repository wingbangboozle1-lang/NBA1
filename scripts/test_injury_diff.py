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
        # A row-count floor pinned to "whatever PDF is newest" is a calendar trap,
        # not a parser test.  Before roughly 09:00 ET the report lists only the
        # games whose teams have submitted yet, so the 2026-11-19 12:45 AM edition
        # legitimately holds 44 rows where the 2026-11-18 17:45 edition holds 126.
        # The same defect is recorded for the transcription test below (F-DFA-02):
        # a slate roll or an early edition is not a regression.  So the floor is
        # asserted against the newest *late-day* edition, and the newest edition of
        # any hour is asserted for the invariant that always holds: it parses, it
        # yields rows, and nothing in it is unparsed.  (Pinned by session
        # arena/e3d25abc-nba1, COORDINATION §68.5, after the 11/19 capture tripped it.)
        paths = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")),
                       key=lambda p: ij.edition_key(os.path.basename(p)))
        late = None
        for p in reversed(paths):
            key = ij.edition_key(os.path.basename(p))
            if isinstance(key, tuple) and len(key) == 2 and key[1] >= 1500:
                late = p
                break
        self.assertIsNotNone(late, "no archived edition at or after 15:00 ET to size against")
        self.assertGreater(ij.load_edition(late)["row_count"], 50)
        self.assertGreaterEqual(self.rec["row_count"], 1)
        self.assertEqual(len(self.rec.get("unparsed") or []), 0,
                         "the newest archived edition reports cells the parser could not read")

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


class CellReaderRecoversDroppedRowsTests(unittest.TestCase):
    """Regression pin for flag F-X01 (COORDINATION §60.2, session
    arena/07920bdc-nba1; fix landed by session arena/ca442d3d-nba1).

    engine/injury_diff.parse_rows (the word-band line parser) returns 80 rows
    and reports unparsed: 0 for the 2026-11-16 01:00/01:15 PM editions while
    seven player rows are missing from its output: Jerome, Pippen Jr., Post,
    Saunders and Stewart (Memphis, MEM@WAS) and Reese and Watford (New
    Orleans, GSW@NOP). load_edition now reads the same bytes a second way - the
    report's own clipped cell rectangles - and publishes that pass, so those
    rows are present and a disagreement between the two readers can never again
    be silent.
    """

    EDITION = "Injury-Report_2026-11-16_01_15PM"
    MISSING = [("Memphis Grizzlies", "Jerome, Ty"),
               ("Memphis Grizzlies", "Pippen Jr., Scotty"),
               ("Memphis Grizzlies", "Post, Quinten"),
               ("Memphis Grizzlies", "Saunders, Richie"),
               ("Memphis Grizzlies", "Stewart, Isaiah"),
               ("New Orleans Pelicans", "Reese, Julian"),
               ("New Orleans Pelicans", "Watford, Trendon")]

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdfs = [p for p in glob.glob(os.path.join(
            root, "data", "raw", "injury_pdfs", "*.pdf"))
            if cls.EDITION in os.path.basename(p)]
        if not pdfs:
            raise unittest.SkipTest(f"{cls.EDITION} not archived in this checkout")
        cls.rec = ij.load_edition(sorted(pdfs)[0])

    def test_dropped_player_rows_are_recovered(self):
        have = {(r[3], r[4]) for r in self.rec["rows"] if len(self.rec["rows"][0]) > 4}
        for team, player in self.MISSING:
            self.assertIn((team, player), have,
                          f"{player} ({team}) dropped from the parsed edition")

    def test_cell_reader_is_the_published_pass(self):
        audit = self.rec["row_audit"]
        self.assertGreaterEqual(audit["cell_reader_player_rows"],
                                audit["line_parser_player_rows"])
        self.assertGreaterEqual(self.rec["row_count"], 87)
        self.assertTrue(audit["selected"].startswith("clipped-cell reader"))

    def test_no_silent_drop_and_no_unassigned_text(self):
        audit = self.rec["row_audit"]
        self.assertFalse(audit["silent_drop_detected"],
                         f"a reader saw rows the output lacks: "
                         f"{audit['rows_only_in_cell_reader']} / "
                         f"{audit['rows_only_in_line_parser']}")
        self.assertEqual(audit["cell_reader_audit"].get("unassigned_count"), 0)
