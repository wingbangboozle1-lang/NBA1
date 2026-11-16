"""Unit tests for engine/parse_official.py (RFG4, COORDINATION.md section 42).

Fixtures are SYNTHETIC HTML/JSON shaped like the official pages' structures
(link patterns, header rows, rowSet shapes) - they test parser mechanics, not
data values. The live-data verification is the CI refresh run and the
verify/2026-11-15-abac961f/ record. Standard library only.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "engine"))

import parse_official as po  # noqa: E402


def _stats_rows():
    """30 synthetic team rows in the advanced schema (mechanics only)."""
    names = sorted(po.TEAM_NAME_TO_ABBR)
    out = []
    for i, name in enumerate(names):
        gp, w = 10 + i % 5, 5 + i % 4
        out.append([name, gp, w, gp - w, 48.0, 110.0 + i * 0.1, 108.0 + i * 0.1,
                    2.0 + i * 0.1, 20.0, 1.8, 18.0, 0.25, 0.75, 0.5, 0.13,
                    0.52, 0.56, 98.0 + i * 0.1, 0.5, 2000 + i])
    return out


class TeamTableTests(unittest.TestCase):
    def test_stats_api_rowset_roundtrip(self):
        cols = po.ADVANCED_COLS
        rows = _stats_rows()
        payload = {"resultSets": [{"name": "LeagueDashTeamStats",
                                   "headers": [po.ADVANCED_API_WANT[c]
                                               for c in cols],
                                   "rowSet": rows}]}
        got_cols, got_rows, meta = po.parse_team_table(
            json.dumps(payload), cols=cols, int_cols=po.ADVANCED_INT,
            variant="advanced")
        self.assertEqual(meta["strategy"], "stats_api")
        self.assertEqual(len(got_rows), 30)
        self.assertEqual(got_rows[0][0], po.TEAM_NAME_TO_ABBR[rows[0][0]])

    def test_partial_table_refused(self):
        cols = po.ADVANCED_COLS
        rows = _stats_rows()[:12]
        payload = {"resultSets": [{"name": "LeagueDashTeamStats",
                                   "headers": [po.ADVANCED_API_WANT[c]
                                               for c in cols],
                                   "rowSet": rows}]}
        _c, got, meta = po.parse_team_table(
            json.dumps(payload), cols=cols, int_cols=po.ADVANCED_INT,
            variant="advanced")
        self.assertEqual(got, [])
        self.assertIsNone(meta["strategy"])

    def test_w_plus_l_mismatch_refused(self):
        cols = po.ADVANCED_COLS
        rows = _stats_rows()
        rows[3] = list(rows[3])
        rows[3][1] += 1  # gp no longer w+l
        payload = {"resultSets": [{"name": "LeagueDashTeamStats",
                                   "headers": [po.ADVANCED_API_WANT[c]
                                               for c in cols],
                                   "rowSet": rows}]}
        _c, got, _m = po.parse_team_table(
            json.dumps(payload), cols=cols, int_cols=po.ADVANCED_INT,
            variant="advanced")
        self.assertEqual(got, [])

    def test_html_team_link_strategy(self):
        body = []
        for name in sorted(po.TEAM_NAME_TO_ABBR):
            abbr = po.TEAM_NAME_TO_ABBR[name]
            body.append(
                f'<tr><td><a href="/stats/team/16106127{abs(hash(abbr)) % 100:02d}/'
                f'{name.lower().replace(" ", "-")}">{name}</a></td>'
                f"<td>10</td><td>6</td><td>4</td></tr>")
        text = ("<table><tr><th>Team</th><th>GP</th><th>W</th><th>L</th></tr>"
                + "".join(body) + "</table>")
        _c, rows, meta = po.parse_team_table(text, variant="generic")
        self.assertEqual(meta["strategy"], "html_table")
        self.assertEqual(len(rows), 30)


class StandingsTests(unittest.TestCase):
    def _standings_html(self):
        def rows(conf, start):
            out = []
            for i, name in enumerate(sorted(po.TEAM_NAME_TO_ABBR)[:15]):
                w, l = 8 + i % 4, 2 + i % 3
                slug = name.lower().replace(" ", "-")
                out.append(
                    f'<tr><td>{i + 1}</td>'
                    f'<td><a href="/team/16106127{i:02d}/{slug}">{name}</a></td>'
                    f"<td>{w}</td><td>{l}</td><td>.{int(1000 * w / (w + l)):03d}"
                    f"</td><td>--</td><td>{w - 1}-{l}</td><td>2-1</td>"
                    f"<td>{w // 2}-{l // 2}</td><td>{w - w // 2}-{l - l // 2}</td>"
                    f"<td>0-0</td><td>0-0</td><td>5-5</td><td>W 1</td></tr>")
            return out
        east = rows("East", 0)
        west_names = sorted(po.TEAM_NAME_TO_ABBR)[15:]
        west = []
        for i, name in enumerate(west_names):
            w, l = 7 + i % 4, 3 + i % 3
            slug = name.lower().replace(" ", "-")
            west.append(
                f'<tr><td>{i + 1}</td>'
                f'<td><a href="/team/16106127{i:02d}/{slug}">{name}</a></td>'
                f"<td>{w}</td><td>{l}</td><td>.{int(1000 * w / (w + l)):03d}"
                f"</td><td>--</td><td>{w - 1}-{l}</td><td>2-1</td>"
                f"<td>{w // 2}-{l // 2}</td><td>{w - w // 2}-{l - l // 2}</td>"
                f"<td>0-0</td><td>0-0</td><td>5-5</td><td>L 2</td></tr>")
        return (f"<h2>Eastern Conference</h2><table>{''.join(east)}</table>"
                f"<h2>Western Conference</h2><table>{''.join(west)}</table>")

    def test_standings_html(self):
        cols, rows, meta = po.parse_standings(self._standings_html())
        self.assertEqual(meta["strategy"], "html_table")
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(1 for r in rows if r[2] == "East"), 15)
        self.assertEqual(sum(1 for r in rows if r[2] == "West"), 15)

    def test_standings_integrity_catches_home_sum(self):
        _c, rows, _m = po.parse_standings(self._standings_html())
        rows[0][10] = "9-0"  # home record no longer sums with road+neutral
        problems = po._standings_integrity(rows)
        self.assertTrue(any("home+road+neutral" in p for p in problems))


class ScheduleTests(unittest.TestCase):
    def test_game_links(self):
        text = ('<a href="/game/mem-vs-was-0022600247">Preview</a>'
                '<a href="/game/phi-vs-bkn-0022600248">Preview</a>')
        _c, games, meta = po.parse_schedule(text)
        self.assertEqual(meta["strategy"], "game_links")
        self.assertEqual([g["game_id"] for g in games],
                         ["0022600247", "0022600248"])
        self.assertEqual(games[0]["away"], "MEM")
        self.assertEqual(games[0]["home"], "WAS")

    def test_embedded_json_game_objects(self):
        payload = {"props": {"pageProps": {"games": [
            {"gameId": "0022600249",
             "homeTeam": {"teamTricode": "MIA", "teamSubtitle": "7-6"},
             "awayTeam": {"teamTricode": "HOU", "teamSubtitle": "10-3"},
             "gameDateEt": "2026-11-16"}]}}}
        text = '<script id="__NEXT_DATA__" type="application/json">' + \
            json.dumps(payload) + "</script>"
        _c, games, meta = po.parse_schedule(text)
        self.assertEqual(meta["strategy"], "embedded_json")
        self.assertEqual(games[0]["away"], "HOU")
        self.assertEqual(games[0]["date"], "2026-11-16")

    def test_unrecognised_team_never_guessed(self):
        text = '<a href="/game/zzz-vs-was-0022600247">Preview</a>'
        _c, games, _m = po.parse_schedule(text)
        self.assertEqual(games, [])


class CrossCheckTests(unittest.TestCase):
    def test_cross_check_detects_disagreement(self):
        st_cols = po.STANDINGS_COLS
        st_rows = [["ATL", "Atlanta Hawks", "East", 1, 8, 4, 0.667, 0.0,
                    "5-3", "1-0", "4-1", "4-3", "0-0", "0-0", "5-5", "W 1"]]
        t_cols = ["team", "gp", "w", "l"]
        t_rows = [["ATL", 12, 8, 4]]
        self.assertEqual(
            po.cross_check_standings_vs_traditional(st_rows, t_rows, t_cols), [])
        t_rows[0][2] = 9
        problems = po.cross_check_standings_vs_traditional(st_rows, t_rows, t_cols)
        self.assertEqual(len(problems), 1)


if __name__ == "__main__":
    unittest.main()
