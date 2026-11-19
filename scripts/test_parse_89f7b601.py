"""Regression tests for the §69 parse/observability findings (session 89f7b601).

These tests exist because of five specific measured failures, each of which is
reproduced here from committed artifacts rather than from invented fixtures:

  * the delivered official pages contain no team rows (HTML <tr>=12, /team/=0,
    rowSet=0; standings <tr>=0) - `data/raw/session-89f7b601/capture_manifest.json`
  * headless Chromium on a runner receives Akamai "Access Denied"
    (`data/raw/session-89f7b601/render/render_manifest.json`)
  * the parse layer therefore returns 0 rows AND, before this session, threw
    away the diagnostics that named the cause
  * the official games feed DOES print every team's record, and a check against
    it corroborates the transcribed standings without elevating it

Standard library only. No network. If the captured artifacts are not present the
byte-dependent tests skip with a reason rather than passing silently.
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import parse_official as po  # noqa: E402

CAP = os.path.join(ROOT, "data", "raw", "session-89f7b601",
                   "capture_manifest.json")
RENDER = os.path.join(ROOT, "data", "raw", "session-89f7b601", "render",
                      "render_manifest.json")
CORROB = os.path.join(ROOT, "data", "official",
                      "standings_corroboration_89f7b601.json")


def _capture_manifest():
    if not os.path.exists(CAP):
        return None
    with open(CAP, encoding="utf-8") as fh:
        return json.load(fh)


class DiagnosticsSurviveFailure(unittest.TestCase):
    """The defect that cost this session a capture round-trip.

    `parse_team_table`/`parse_standings` used to return only the first 12
    problem strings, and `fetch_official` printed only "parsed 0" - so five
    sources failed for a full day with no recorded reason. The counts are now
    part of the returned metadata and the total is never truncated away.
    """

    def test_problems_total_is_reported_even_when_empty_of_rows(self):
        cols, rows, meta = po.parse_team_table("<html><body>shell</body></html>",
                                               variant="traditional")
        self.assertEqual(rows, [])
        self.assertIn("problems_total", meta)
        self.assertGreaterEqual(meta["problems_total"], 1)
        self.assertEqual(meta["problems_total"], len(meta["problems"]))

    def test_unresolvable_rows_are_reported_not_silently_dropped(self):
        """A document full of unidentifiable rows is not an empty document.

        Before §69, 20 rows whose team cell could not be resolved to a club
        produced exactly {"rows": [], "problems": []} - the same result as an
        empty page, and therefore useless as a diagnosis.
        """
        body = "".join(
            '<table><tr><th>Team</th><th>GP</th><th>W</th><th>L</th></tr>'
            '<tr><td>Nowhere United</td><td>x</td><td>1</td><td>2</td></tr>'
            '</table>' for _ in range(20))
        _, rows, meta = po.parse_team_table(
            body, cols=["team", "gp", "w", "l"], int_cols={"gp", "w", "l"},
            variant="traditional")
        self.assertEqual(rows, [])
        self.assertGreaterEqual(meta["problems_total"], 1)
        joined = " ".join(meta["problems"])
        self.assertIn("did not resolve to a club", joined)
        # The total is the count of what was seen, not the truncated sample.
        self.assertIn("20 rows in total", joined)

    def test_problems_list_stays_bounded(self):
        """The returned list is capped so a 100k-row page cannot flood a log."""
        body = "".join(
            '<table><tr><th>Team</th><th>GP</th><th>W</th><th>L</th></tr>'
            f'<tr><td>Nowhere {i}</td><td>x</td><td>1</td><td>2</td></tr>'
            '</table>' for i in range(400))
        _, rows, meta = po.parse_team_table(
            body, cols=["team", "gp", "w", "l"], int_cols={"gp", "w", "l"},
            variant="traditional")
        self.assertEqual(rows, [])
        self.assertLessEqual(len(meta["problems"]), 12)

    def test_standings_meta_reports_a_total_too(self):
        _, rows, meta = po.parse_standings("<html></html>")
        self.assertEqual(rows, [])
        self.assertIn("problems_total", meta)
        self.assertGreaterEqual(meta["problems_total"], 1)


class DeliveredPagesCarryNoTeamRows(unittest.TestCase):
    """Pin the measurement, so a future session cannot 'fix' it by guessing.

    If a later capture DOES contain team rows, this test fails on purpose: that
    would mean the page changed shape and the byte-capture finding must be
    re-measured before any parser work is believed.
    """

    def test_every_page_body_has_zero_team_links(self):
        m = _capture_manifest()
        if m is None:
            self.skipTest("no capture manifest committed yet")
        pages = [r for r in m["results"] if not r["name"].startswith("A")]
        self.assertEqual(len(pages), 5, "expected the five page sources")
        for r in pages:
            if r.get("status") != "stored":
                self.fail(f"{r['name']} was not captured: {r.get('attempts')}")
            s = r["structure"]
            self.assertEqual(s["team_links"], 0,
                             f"{r['name']}: the delivered HTML gained team links")
            self.assertEqual(s["stats_team_links"], 0,
                             f"{r['name']}: the delivered HTML gained stats links")
            self.assertEqual(s["rowSet"], 0,
                             f"{r['name']}: the delivered HTML gained a rowSet")
            self.assertTrue(s["bytes_delivered"] > 200000,
                            f"{r['name']}: body implausibly small")

    def test_standings_body_has_no_table_rows_at_all(self):
        m = _capture_manifest()
        if m is None:
            self.skipTest("no capture manifest committed yet")
        st = [r for r in m["results"] if r["name"] == "S8_standings"][0]
        self.assertEqual(st["structure"]["html_tr_elements"], 0)

    def test_stats_api_is_unreachable_and_that_is_recorded(self):
        m = _capture_manifest()
        if m is None:
            self.skipTest("no capture manifest committed yet")
        apis = [r for r in m["results"] if r["name"].startswith("A")]
        self.assertEqual(len(apis), 4)
        for r in apis:
            # Either it worked, or every attempt failed with a recorded error.
            if r.get("status") == "stored":
                continue
            self.assertEqual(r["status"], "unavailable")
            self.assertTrue(r.get("attempts"))
            for a in r["attempts"]:
                self.assertIsNone(a.get("http_status"),
                                  "a failure with an HTTP status is a refusal, "
                                  "not a timeout - re-measure this finding")
                self.assertIn("TimeoutError", a.get("error", ""))


class RenderedDomIsAnAccessDenial(unittest.TestCase):
    """Chromium on a runner is blocked at the edge. Recorded, not worked around."""

    def test_render_manifest_shows_zero_tables(self):
        if not os.path.exists(RENDER):
            self.skipTest("no render manifest committed yet")
        with open(RENDER, encoding="utf-8") as fh:
            m = json.load(fh)
        for r in m["results"]:
            self.assertEqual(r.get("status"), "stored")
            self.assertFalse(r.get("selector_found"),
                             f"{r['name']}: a table appeared; re-measure")
            self.assertEqual(r.get("n_tables"), 0, r["name"])
            self.assertEqual(r.get("n_rows_total"), 0, r["name"])
            # The denial page is a few hundred bytes, not the 200 KB+ the
            # non-browser fetch received.
            self.assertLess(r["bytes"], 5000, r["name"])

    def test_denial_body_names_the_edge_and_says_access_denied(self):
        if not os.path.exists(RENDER):
            self.skipTest("no render manifest committed yet")
        with open(RENDER, encoding="utf-8") as fh:
            m = json.load(fh)
        path = os.path.join(ROOT, m["results"][0]["artifact"])
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("Access Denied", body)
        self.assertIn("errors.edgesuite.net", body)


class StandingsCorroboration(unittest.TestCase):
    """The check that turns 'cannot parse' into a stated coverage fact."""

    def test_corroboration_record_is_consistent_with_itself(self):
        if not os.path.exists(CORROB):
            self.skipTest("corroboration record not generated yet")
        with open(CORROB, encoding="utf-8") as fh:
            d = json.load(fh)
        s = d["summary"]
        self.assertEqual(s["teams_in_standings"], 30)
        self.assertEqual(s["agree"] + s["disagree"], s["teams_checked"],
                         "checked must equal agree + disagree")
        self.assertEqual(s["teams_checked"] + s["not_named_by_feed"], 30)
        self.assertEqual(len(d["per_team"]), 30)
        for row in d["per_team"]:
            self.assertIn(row["status"],
                          ("agree", "DISAGREE", "not_named_by_feed"))
            if row["status"] == "agree":
                self.assertEqual(row["feed_record"],
                                 f"{row['standings_w']}-{row['standings_l']}")
            if row["status"] == "agree":
                # Every corroborated row must carry the URL of the official
                # feed page that printed it - a row without a source link is
                # not corroborated, it is asserted.
                self.assertTrue(row["feed_source_url"].startswith(
                    "https://www.nba.com/games?date="))
            self.assertTrue(row["uncorroborated_fields"],
                            "the feed cannot corroborate these fields and the "
                            "record must say so per team")

    def test_verdict_matches_the_counts(self):
        if not os.path.exists(CORROB):
            self.skipTest("corroboration record not generated yet")
        with open(CORROB, encoding="utf-8") as fh:
            d = json.load(fh)
        s = d["summary"]
        if s["disagree"]:
            self.assertEqual(d["verdict"], "DISAGREEMENT")
        elif s["teams_checked"] < 30:
            self.assertEqual(d["verdict"], "INCONCLUSIVE")
        else:
            self.assertEqual(d["verdict"], "CORROBORATED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
