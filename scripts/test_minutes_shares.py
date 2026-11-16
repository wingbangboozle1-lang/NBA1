#!/usr/bin/env python3
"""Checks for scripts/build_minutes_shares.py (COORDINATION section 50, task Q02)."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "derived", "minutes_shares.json")
PAGE = os.path.join(ROOT, "site", "pages", "minutes.html")


class MinutesSharesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_minutes_shares.py")], check=True,
                       stdout=subprocess.DEVNULL)
        with open(DATA, encoding="utf-8") as fh:
            cls.doc = json.load(fh)

    def test_scope_is_six_gamebooks(self):
        self.assertEqual(self.doc["sample"]["games"], 6)
        self.assertEqual(self.doc["sample"]["team_games"], 12)

    def test_every_row_has_official_sources(self):
        for r in self.doc["rows"]:
            self.assertTrue(r["source_game_page"].startswith("https://www.nba.com/game/"), r["game"])
            self.assertTrue(r["source_gamebook_pdf"].startswith("https://statsdmz.nba.com/pdfs/"), r["game"])

    def test_top8_is_at_most_eight_and_sorted(self):
        for r in self.doc["rows"]:
            self.assertLessEqual(len(r["top8"]), 8)
            mins = [t["min"] for t in r["top8"]]
            self.assertEqual(mins, sorted(mins, reverse=True))

    def test_shares_are_consistent_with_printed_total(self):
        for r in self.doc["rows"]:
            m, s = map(int, r["printed_team_total"].split(":"))
            printed = m * 60 + s
            top8_secs = 0
            for t in r["top8"]:
                mm, ss = map(int, t["min"].split(":"))
                top8_secs += mm * 60 + ss
            self.assertAlmostEqual(r["top8_share"], round(top8_secs / printed, 4), places=3, msg=r["game"])

    def test_mismatches_are_flagged_not_fixed(self):
        flagged = {(f["game"], f["team"]) for f in self.doc["flags"]}
        for r in self.doc["rows"]:
            if r["player_minutes_sum"] != r["printed_team_total"]:
                self.assertIn((r["game"], r["team"]), flagged, r["game"])

    def test_overtime_total_is_265(self):
        nyk = [r for r in self.doc["rows"] if r["team"] == "NYK"][0]
        self.assertEqual(nyk["printed_team_total"], "265:00")
        self.assertEqual(nyk["overtime_periods"], 1)

    def test_replacement_shares_are_explicitly_blocked(self):
        self.assertEqual(self.doc["replacement_shares"]["status"], "blocked")
        with open(PAGE, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("blocked", html)
        self.assertIn("Replacement share", html)

    def test_page_has_a_row_per_team_game(self):
        with open(PAGE, encoding="utf-8") as fh:
            html = fh.read()
        self.assertEqual(html.count("<tr><td>") - 1, len(self.doc["rows"]))


if __name__ == "__main__":
    unittest.main()
