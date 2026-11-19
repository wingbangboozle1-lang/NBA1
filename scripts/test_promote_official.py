"""Tests for engine/promote_official.py - fail-closed, digest-bound promotion.

Mechanics are exercised on synthetic capture fixtures shaped exactly like the
live `_capture_*.json` files the fetcher writes (see engine/fetch_official.py)
and like the live results captures (`parse.finals_rows`). The promoter must
refuse rows it cannot re-validate, bind each promotion record to the capture's
exact response digest, and refuse to append a finals row that disagrees with
the independent record.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

import promote_official  # noqa: E402
from common import ABBR  # noqa: E402


def _page_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


TRAD_COLS = ["team", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga",
             "fg_pct", "3pm", "3pa", "3p_pct", "ftm", "fta", "ft_pct", "oreb",
             "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd",
             "+/-"]


def _traditionals_rows():
    rows = []
    for i, (name, abbr) in enumerate(sorted(ABBR.items())):
        w, l = 8 + i % 4, 2 + i % 3
        gp = w + l
        rows.append([
            abbr, gp, w, l, round(w / gp, 3), 241.0, 113.5, 41.5, 88.5,
            0.470, 13.5, 36.5, 0.370, 17.5, 22.5, 0.780, 9.5, 34.5, 44.0,
            26.5, 14.5, 8.5, 4.5, 4.5, 19.5, 19.5, 2.5])
    return TRAD_COLS, rows


class PromoteTeamTableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "data", "raw")
        os.makedirs(self.raw)
        self.real_raw = promote_official.RAW
        self.real_root = promote_official.ROOT
        promote_official.RAW = self.raw
        promote_official.ROOT = self.tmp.name
        self.record = {
            "completed_at_utc": "2026-11-15T22:44:31Z",
            "changed": [],
            "source_checks": [],
        }

    def tearDown(self):
        promote_official.RAW = self.real_raw
        promote_official.ROOT = self.real_root
        self.tmp.cleanup()

    def _write_capture(self, rows, cols, page_text, captured_at):
        with open(os.path.join(self.raw, "_capture_S9_team_traditional.json"),
                  "w") as fh:
            json.dump({
                "captured_at_utc": captured_at,
                "source_url": "https://www.nba.com/stats/teams/traditional",
                "page_sha256": _page_sha(page_text),
                "rows": rows, "cols": cols, "row_count": len(rows),
                "strategy": "html_table",
            }, fh)
        self.record["source_checks"] = [{
            "key": "S9_team_traditional",
            "url": "https://www.nba.com/stats/teams/traditional",
            "sha256": _page_sha(page_text),
            "http_status": 200,
            "captured_at_utc": captured_at,
        }]

    def _promote(self):
        p = promote_official.Promoter(self.record, "2026-11-15T23:00:00Z")
        out = p._promote_team_table(
            "S9_team_traditional", "_capture_S9_team_traditional.json",
            "team_traditional.json", "traditional")
        return p, out

    def test_valid_rows_promote_with_digest_bound_verification(self):
        cols, rows = _traditionals_rows()
        self._write_capture(rows, cols, "official-page-bytes",
                            "2026-11-15T22:44:31Z")
        p, out = self._promote()
        self.assertIsNotNone(out)
        rec = json.load(open(os.path.join(self.raw, "team_traditional.json")))
        self.assertTrue(rec["verification"]["verified"])
        self.assertEqual(rec["verification"]["source_sha256"],
                         _page_sha("official-page-bytes"))
        self.assertEqual(rec["verification"]["verified_at_utc"],
                         "2026-11-15T23:00:00Z")
        self.assertEqual(len(rec["rows"]), 30)

    def test_integrity_failure_blocks_promotion(self):
        cols, rows = _traditionals_rows()
        rows[5][2] = 99  # W wildly inconsistent with GP
        self._write_capture(rows, cols, "bad-page-bytes",
                            "2026-11-15T22:44:31Z")
        p, out = self._promote()
        self.assertIsNone(out)
        self.assertTrue(p.blocked)
        self.assertFalse(os.path.exists(
            os.path.join(self.raw, "team_traditional.json")))

    def test_empty_capture_blocks_promotion(self):
        self._write_capture([], [], "empty-page-bytes", "2026-11-15T22:44:31Z")
        p, out = self._promote()
        self.assertIsNone(out)
        self.assertTrue(p.blocked)


class ResultsFeedTests(unittest.TestCase):
    COLS = ["date", "away", "away_pts", "home", "home_pts", "ot", "neutral",
            "game_id", "source_id"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "data", "raw")
        os.makedirs(self.raw)
        self.real_raw = promote_official.RAW
        self.real_root = promote_official.ROOT
        promote_official.RAW = self.raw
        promote_official.ROOT = self.tmp.name
        self.record = {"completed_at_utc": "2026-11-15T22:44:31Z", "changed": [],
                       "source_checks": []}
        with open(os.path.join(self.raw, "games_completed.json"), "w") as fh:
            json.dump({"cols": self.COLS, "rows": [
                ["2026-11-13", "ATL", 110, "BOS", 120, 0, 0,
                 "0022600230", "S3_2026-11-13"]]}, fh)

    def tearDown(self):
        promote_official.RAW = self.real_raw
        promote_official.ROOT = self.real_root
        self.tmp.cleanup()

    def _write_results_capture(self):
        with open(os.path.join(self.raw, "_capture_results_2026-11-15.json"),
                  "w") as fh:
            json.dump({
                "captured_at_utc": "2026-11-15T22:44:31Z",
                "source_url": "https://www.nba.com/games?date=2026-11-15",
                "page_sha256": _page_sha("results-page"),
                "parse": {"finals_rows": [{
                    "game_id": "0022600236", "away": "IND", "home": "PHI",
                    "away_pts": 124, "home_pts": 131, "ot": 0,
                    "snapshot_match": True,
                }]},
                "snapshot_comparison": {"mismatches": []},
            }, fh)

    def _write_cross(self, away_pts, home_pts):
        with open(os.path.join(self.raw, "official_results_2026-11-15.json"),
                  "w") as fh:
            json.dump({"rows": [{"game_id": "0022600236", "away": "IND",
                                 "home": "PHI", "away_pts": away_pts,
                                 "home_pts": home_pts, "ot": 0}]}, fh)

    def _feed(self):
        return json.load(open(os.path.join(self.raw, "games_completed.json")))

    def test_agreeing_record_appends_cross_checked_row(self):
        self._write_results_capture()
        self._write_cross(124, 131)
        p = promote_official.Promoter(self.record, "2026-11-15T23:00:00Z")
        p.promote_results()
        feed = self._feed()
        self.assertEqual(len(feed["rows"]), 2)
        self.assertEqual(feed["rows"][-1][0:5],
                         ["2026-11-15", "IND", 124, "PHI", 131])
        self.assertTrue(feed["verification"]["appended_this_run"][0]
                        ["cross_checked"])

    def test_conflicting_record_blocks_and_appends_nothing(self):
        self._write_results_capture()
        self._write_cross(125, 131)  # disagrees with the official capture
        p = promote_official.Promoter(self.record, "2026-11-15T23:00:00Z")
        p.promote_results()
        feed = self._feed()
        self.assertEqual(len(feed["rows"]), 1)  # untouched
        self.assertTrue(p.blocked)

    def test_snapshot_mismatch_blocks_all_appends(self):
        """A capture-level mismatch is never papered over: no append at all."""
        self._write_results_capture()
        with open(os.path.join(self.raw, "_capture_results_2026-11-15.json")) as fh:
            cap = json.load(fh)
        cap["snapshot_comparison"]["mismatches"] = [
            {"game_id": "0022600236", "field": "away_pts",
             "committed": 120, "page": 124}]
        with open(os.path.join(self.raw, "_capture_results_2026-11-15.json"),
                  "w") as fh:
            json.dump(cap, fh)
        p = promote_official.Promoter(self.record, "2026-11-15T23:00:00Z")
        p.promote_results()
        feed = self._feed()
        self.assertEqual(len(feed["rows"]), 1)  # untouched
        self.assertTrue(p.blocked)

    def test_no_record_appends_single_source_row(self):
        self._write_results_capture()
        p = promote_official.Promoter(self.record, "2026-11-15T23:00:00Z")
        p.promote_results()
        feed = self._feed()
        self.assertEqual(len(feed["rows"]), 2)
        self.assertFalse(feed["verification"]["appended_this_run"][0]
                         ["cross_checked"])


class DeclaredUnreadableTests(unittest.TestCase):
    """COORDINATION.md section 69: a declared source must not poison the exit code.

    The promote step used to append an ordinary blocking entry for each of the
    three client-rendered pages on EVERY run, so it always exited 1 and the
    rebuild step in refresh-data.yml was unreachable. These tests pin the
    narrow replacement: a declared source is recorded, is never promoted, and
    does not make the run fail - while an UNDECLARED parse failure still does.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "data", "raw")
        os.makedirs(self.raw)
        self.real_raw = promote_official.RAW
        self.real_root = promote_official.ROOT
        promote_official.RAW = self.raw
        promote_official.ROOT = self.tmp.name

    def tearDown(self):
        promote_official.RAW = self.real_raw
        promote_official.ROOT = self.real_root
        self.tmp.cleanup()

    def _declare(self, keys):
        with open(os.path.join(self.raw, "unreadable_sources.json"), "w") as fh:
            json.dump({"declarations": [
                {"source_key": k, "expires_at_utc": "2026-12-19T00:00:00Z",
                 "review_flag": "F1"} for k in keys]}, fh)

    def _empty_capture(self, key, name):
        # Exactly what the fetcher leaves behind for a client-rendered page:
        # a page-level record with no parsed rows.
        with open(os.path.join(self.raw, name), "w") as fh:
            json.dump({"source_url": "https://www.nba.com/x", "page_sha256": "a" * 64}, fh)

    def _promoter(self):
        promoter = promote_official.Promoter.__new__(promote_official.Promoter)
        promoter.promoted, promoter.blocked = [], []
        promoter.unreadable = []
        promoter.warnings, promoter.rows_written = [], {}
        promoter.checks = {}
        promoter.now = "2026-11-15T22:44:31Z"
        return promoter

    def test_declared_source_is_recorded_not_blocked(self):
        self._declare(["S8_standings"])
        self._empty_capture("S8_standings", "_capture_S8_standings.json")
        promoter = self._promoter()
        promoter.promote_standings()
        self.assertEqual(promoter.blocked, [])
        self.assertEqual(len(promoter.unreadable), 1)
        entry = promoter.unreadable[0]
        self.assertEqual(entry["item"], "S8_standings")
        self.assertEqual(entry["expires_at_utc"], "2026-12-19T00:00:00Z")
        self.assertIn("Nothing was promoted", entry["detail"])
        # Critically: no snapshot was written from an unreadable page.
        self.assertFalse(os.path.exists(os.path.join(self.raw, "standings.json")))

    def test_undeclared_source_still_blocks(self):
        self._empty_capture("S8_standings", "_capture_S8_standings.json")
        promoter = self._promoter()
        promoter.promote_standings()
        self.assertEqual(promoter.unreadable, [])
        self.assertEqual(len(promoter.blocked), 1)
        self.assertEqual(promoter.blocked[0]["item"], "S8_standings")

    def test_a_declaration_does_not_excuse_a_missing_capture_file(self):
        """A declared page still must have been attempted this run."""
        self._declare(["S8_standings"])
        promoter = self._promoter()
        promoter.promote_standings()
        self.assertEqual(len(promoter.blocked), 1)
        self.assertEqual(promoter.unreadable, [])

    def test_exit_code_ignores_declared_items_but_not_real_blocks(self):
        import inspect
        source = inspect.getsource(promote_official.Promoter.run)
        self.assertIn("return 1 if self.blocked else 0", source)
        self.assertNotIn("self.unreadable", source.split("return 1 if")[1][:40])


if __name__ == "__main__":
    unittest.main()
