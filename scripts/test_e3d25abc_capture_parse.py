#!/usr/bin/env python3
"""Tests for scripts/capture_official_e3d25abc.py - the runner-side capture.

These pin the two defects that made this seat's first capture run return
nothing useful.  Both are silent-failure classes: the run exited 0, the
manifest said "0 failure(s)", and yet zero injury editions and zero gamebooks
were fetched.  A capture that quietly fetches nothing is worse than one that
fails, because the pages built on top of it look current.

Run:  python3 -m unittest scripts.test_e3d25abc_capture_parse -v
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import capture_official_e3d25abc as cap  # noqa: E402


def card(away, home, gid, inner):
    return (f'<a class="gameCard" href="/game/{away.lower()}-vs-{home.lower()}-{gid}">'
            f'{inner}</a>')


class ScoreboardStatusRead(unittest.TestCase):
    """The Final marker must be read from inside its own card, case-insensitively."""

    def test_uppercase_final_marks_the_card_final(self):
        # This is the shape a completed card prints: " - FINAL ".  The first run
        # of the capture saw exactly this and still reported 0/17 gamebooks.
        html = card("NYK", "TOR", "0022600253",
                     '<span>Knicks</span><span>111</span> FINAL '
                     '<span>102</span><span>Raptors</span>')
        day = cap.parse_scoreboard(html, "2026-11-17")
        self.assertEqual(1, len(day["games"]))
        self.assertTrue(day["games"][0]["marked_final_on_page"],
                        "an uppercase FINAL on the card must count as final")
        self.assertEqual(1, day["final_count"])

    def test_mixed_case_final_and_ot(self):
        html = (card("CHA", "LAL", "0022600256", "Hornets 114 Final/OT 118 Lakers")
                + card("UTA", "LAC", "0022600257", "Jazz 132 final 107 Clippers"))
        day = cap.parse_scoreboard(html, "2026-11-17")
        self.assertEqual(2, day["final_count"],
                         f"Final, Final/OT and lower-case final all mark the card: "
                         f"{[g['marked_final_on_page'] for g in day['games']]}")

    def test_tip_time_does_not_mark_a_game_final(self):
        html = card("GSW", "MEM", "0022600270", "Warriors 8-7 8:00 PM ET Grizzlies 11-4")
        day = cap.parse_scoreboard(html, "2026-11-19")
        self.assertFalse(day["games"][0]["marked_final_on_page"])
        self.assertEqual(0, day["final_count"])

    def test_status_cannot_bleed_from_the_neighbouring_card(self):
        html = (card("NYK", "TOR", "0022600253", "Knicks 111 FINAL 102 Raptors")
                + card("POR", "MIN", "0022600254", "Trail Blazers 11:00 PM ET Timberwolves"))
        day = cap.parse_scoreboard(html, "2026-11-17")
        flags = {g["game_id"]: g["marked_final_on_page"] for g in day["games"]}
        self.assertEqual({"0022600253": True, "0022600254": False}, flags)

    def test_duplicate_links_collapse_to_one_game(self):
        gid = "0022600253"
        html = card("NYK", "TOR", gid, "Knicks FINAL Raptors") * 3
        day = cap.parse_scoreboard(html, "2026-11-17")
        self.assertEqual(1, len(day["games"]))


class EditionSelection(unittest.TestCase):
    """Which editions a run fetches, and the ordering it fetches them in."""

    LISTED = ["Injury-Report_2026-11-19_12_45AM.pdf",
              "Injury-Report_2026-11-19_12_30AM.pdf",
              "Injury-Report_2026-11-18_05_45PM.pdf",
              "Injury-Report_2026-11-17_11_30AM.pdf"]

    def test_iso_date_matching_not_underscored_date(self):
        # Regression: the first run compared "_2026_11_19_" against a name that
        # contains "_2026-11-19_", so it selected nothing and said nothing about it.
        got = cap.select_todo(self.LISTED, ["2026-11-19"], set(), 120)
        self.assertEqual(["Injury-Report_2026-11-19_12_45AM.pdf",
                          "Injury-Report_2026-11-19_12_30AM.pdf"], got)

    def test_already_archived_editions_are_skipped(self):
        got = cap.select_todo(self.LISTED, ["2026-11-19"],
                              {"Injury-Report_2026-11-19_12_45AM.pdf"}, 120)
        self.assertEqual(["Injury-Report_2026-11-19_12_30AM.pdf"], got)

    def test_empty_day_list_selects_everything_listed(self):
        got = cap.select_todo(self.LISTED, [], set(), 120)
        self.assertEqual(len(self.LISTED), len(got))

    def test_cap_is_honoured_and_newest_first(self):
        got = cap.select_todo(self.LISTED, [], set(), 2)
        self.assertEqual(2, len(got))
        self.assertGreater(cap.edition_key(got[0]), cap.edition_key(got[1]))

    def test_revision_ordering_across_am_pm(self):
        self.assertGreater(cap.edition_key("Injury-Report_2026-11-18_05_45PM.pdf"),
                           cap.edition_key("Injury-Report_2026-11-18_11_00AM.pdf"))
        self.assertGreater(cap.edition_key("Injury-Report_2026-11-18_12_15AM.pdf"),
                           cap.edition_key("Injury-Report_2026-11-18_12_00AM.pdf"))


class HostAllowlist(unittest.TestCase):
    """The capture must be incapable of contacting a non-official host."""

    def test_rejects_unknown_host(self):
        for url in ("https://evil.example.com/x.pdf",
                    "https://cdn.nba.com/static/json/anything.json",
                    "http://www.nba.com/games"):
            with self.assertRaises(ValueError, msg=url):
                cap.get(url)

    def test_allows_exactly_the_four_official_hosts(self):
        self.assertEqual({"www.nba.com", "official.nba.com",
                          "ak-static.cms.nba.com", "statsdmz.nba.com"},
                         cap.ALLOWED_HOSTS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
