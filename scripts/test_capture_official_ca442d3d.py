"""Unit tests for scripts/capture_official_ca442d3d.py (COORDINATION §62 N05).

The capture script runs on a runner, not in the sandbox, so its pure parts -
the scoreboard-page parser and the host allowlist - are tested here against
fixture text. The fixture strings are transcribed from the shape of the official
page (the canonical /game/<away>-vs-<home>-<id> link, the printed "Final"
marker, the "Neutral Site" label), which is what the parser keys on.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import capture_official_ca442d3d as cap  # noqa: E402


FINAL_CARD = (
    '<a href="https://www.nba.com/game/orl-vs-bos-0022600245">'
    '<span>Magic</span><span>6-7</span><span>115</span><span>Final</span>'
    '<span>105</span><span>Celtics</span></a>')

UPCOMING_CARD = (
    '<a href="https://www.nba.com/game/nyk-vs-tor-0022600253">'
    '<span>Knicks</span><span>7:30 PM ET</span><span>Raptors</span></a>')

NEUTRAL_CARD = (
    '<a href="https://www.nba.com/game/dal-vs-min-0022600100">'
    '<span>Mavericks</span><span>Final</span><span>Neutral Site</span></a>')


class HostAllowlistTests(unittest.TestCase):
    def test_only_official_hosts_are_allowed(self):
        self.assertEqual(cap.ALLOWED_HOSTS,
                         {"www.nba.com", "official.nba.com",
                          "ak-static.cms.nba.com", "statsdmz.nba.com"})

    def test_a_non_official_host_is_refused(self):
        with self.assertRaises(ValueError):
            cap.get("https://example.com/x")


class ScoreboardParseTests(unittest.TestCase):
    def setUp(self):
        self.day = cap.parse_scoreboard(FINAL_CARD + UPCOMING_CARD, "2026-11-16")

    def test_game_ids_teams_and_final_marker(self):
        self.assertEqual(len(self.day["games"]), 2)
        g = self.day["games"][0]
        self.assertEqual((g["game_id"], g["away"], g["home"]),
                         ("0022600245", "ORL", "BOS"))
        self.assertTrue(g["marked_final_on_page"])
        self.assertEqual(self.day["final_count"], 1)

    def test_a_final_marker_cannot_bleed_from_an_adjacent_card(self):
        # The two cards are adjacent in this fixture; a window-based reader used
        # to mark the unplayed card Final because the marker sat inside the
        # previous card. Each card is read from inside its own anchor.
        filler = "<span>" + ("x" * 3000) + "</span>"
        d = cap.parse_scoreboard(FINAL_CARD + filler + UPCOMING_CARD,
                                 "2026-11-16")
        self.assertTrue(d["games"][0]["marked_final_on_page"])
        self.assertFalse(d["games"][1]["marked_final_on_page"])
        self.assertEqual(d["final_count"], 1)

    def test_an_unplayed_game_is_not_marked_final(self):
        g = self.day["games"][1]
        self.assertFalse(g["marked_final_on_page"])
        self.assertEqual(g["game_id"], "0022600253")
        self.assertIn("7:30 PM ET", g["card_text"])

    def test_each_game_link_is_counted_once(self):
        dup = cap.parse_scoreboard(FINAL_CARD + FINAL_CARD, "2026-11-16")
        self.assertEqual(len(dup["games"]), 1)

    def test_neutral_site_label_is_carried(self):
        d = cap.parse_scoreboard(NEUTRAL_CARD, "2026-11-07")
        self.assertTrue(d["games"][0]["marked_neutral_on_page"])

    def test_empty_page_yields_no_games(self):
        d = cap.parse_scoreboard("", "2026-11-16")
        self.assertEqual(d["games"], [])
        self.assertEqual(d["final_count"], 0)


class StoreTests(unittest.TestCase):
    def test_sidecar_records_the_official_url_and_digest(self):
        import hashlib
        import json
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp()
        old = cap.OUT_ROOT
        try:
            cap.OUT_ROOT = tmp
            raw = b"%PDF-1.4 fake gamebook bytes\n"
            rec = cap.store("gamebooks/2026-12-31", raw,
                            {"url": "https://statsdmz.nba.com/pdfs/20261231/"
                                    "20261231_XYZAB_book.pdf",
                             "name": "2026-12-31_XYZAB"})
            self.assertEqual(rec["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(rec["bytes"], len(raw))
            self.assertTrue(rec["retrieved_at_utc"].endswith("Z"))
            files = os.listdir(os.path.join(tmp, "gamebooks/2026-12-31"))
            self.assertTrue(any(f.endswith(".sidecar.json") for f in files))
            sidecar = [f for f in files if f.endswith(".sidecar.json")][0]
            data = json.load(open(os.path.join(tmp, "gamebooks/2026-12-31",
                                               sidecar), encoding="utf-8"))
            self.assertEqual(data["url"], rec["url"])
            self.assertEqual(data["sha256"], rec["sha256"])
        finally:
            cap.OUT_ROOT = old
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
