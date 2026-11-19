"""Regression tests for the two defects fixed in COORDINATION.md section 74 (T02).

Each test is written against a *measured* fact, not a preference:

1. `test_absent_capture_for_declared_source_does_not_block` - a declared
   source never writes a rows-bearing capture (engine/fetch_official.py writes
   `_capture_<key>.json` only inside its `if rows:` branch), so the gate's
   missing-capture branch must not re-block the source its declaration just
   excused. Before the fix this test failed: the gate required
   `_capture_S1_season.json`, a file with 0 commits across the full history.

2. `test_snapshot_without_row_count_is_a_complete_table` - the capture schema
   is `rows`/`cols`; `row_count` is not a field any writer emits. The old
   predicate `payload.get("row_count") != 30 or len(...) != 30` was therefore
   true for every well-formed capture. Before the fix this test failed.

3. `test_declared_source_that_parses_is_still_refused` - the anti-rot rule from
   section 69 must survive both fixes: a source that starts parsing must fail
   the gate rather than be silently skipped. This test passed before and must
   keep passing.

Run: python3 scripts/test_fb91550a_gate.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.refresh_gate import evaluate_with_report  # noqa: E402
import datetime as dt  # noqa: E402

NOW = dt.datetime(2026, 11, 19, 12, 30, tzinfo=dt.timezone.utc)


def _write(root: str, rel: str, payload) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream)


def _record(*, fail_s1: bool = True, s1_rows: int = 0) -> dict:
    """A refresh record shaped exactly like data/raw/_last_refresh.json."""
    checks = []
    for key, url in (
        ("S1_season", "https://www.nba.com/stats/teams/advanced"),
        ("S2_train", "https://www.nba.com/stats/teams/advanced?DateFrom=x"),
        ("S4_schedule", "https://www.nba.com/schedule"),
        ("S5_injury_index", "https://official.nba.com/nba-injury-report-2026-27-season/"),
        ("S8_standings", "https://www.nba.com/standings"),
        ("S9_team_traditional", "https://www.nba.com/stats/teams/traditional"),
        ("S10_team_opponent", "https://www.nba.com/stats/teams/opponent"),
    ):
        checks.append({"key": key, "url": url, "http_status": 200,
                       "checked_at_utc": "2026-11-19T12:03:37Z", "sha256": "a" * 64})
    failed = []
    if fail_s1:
        failed.append(["S1_season", f"expected 30 team rows, parsed {s1_rows}"])
    return {
        "captured_at_utc": "2026-11-19T12:03:37Z",
        "failed": failed,
        "source_checks": checks,
    }


class GateDeclarationEscape(unittest.TestCase):
    """Defect 1 + 2: a declaration must actually let the rebuild run."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fb91550a-gate-")
        self.addCleanup(shutil.rmtree, self.root)
        os.environ["NBA1_REPO_ROOT"] = self.root
        self.addCleanup(os.environ.pop, "NBA1_REPO_ROOT", None)
        # The declaration register: S1 declared, with the same three-part
        # admissibility proof the real register carries.
        _write(self.root, "data/raw/unreadable_sources.json", {
            "declarations": [{
                "source_key": "S1_season",
                "expires_at_utc": "2026-12-19T00:00:00Z",
                "review_flag": "F-915-01",
                "required_snapshot": "data/raw/team_advanced.json",
            }]})
        _write(self.root, "data/raw/_capture_evidence_S1_season.json", {
            "captured_at_utc": "2026-11-19T12:03:37Z",
            "source_url": "https://www.nba.com/stats/teams/advanced",
            "status": "parse_failed",
        })
        # Everything the gate needs that IS producible and fresh.
        _write(self.root, "data/raw/_capture_S4_schedule.json",
               {"games": [{"game_id": "0022600301"}]})
        _write(self.root, "data/raw/schedule_upcoming.json", {
            "rows": [{}],
            "verification": {"verified": True,
                             "source_url": "https://www.nba.com/schedule",
                             "source_sha256": "a" * 64,
                             "verified_at_utc": "2026-11-19T12:08:36Z"}})
        _write(self.root, "data/raw/injuries.json", {
            "rows": [{}],
            "verification": {"verified": True,
                             "source_url": "https://ak-static.cms.nba.com/referee/injury/x.pdf",
                             "source_sha256": "b" * 64,
                             "verified_at_utc": "2026-11-19T12:08:36Z"}})
        for date in ("2026-11-19", "2026-11-18"):
            _write(self.root, f"data/raw/_capture_results_{date}.json", {
                "snapshot_comparison": {"mismatches": [],
                                        "promotion_candidates": [],
                                        "committed_finals_missed": []}})
        record = _record()
        record["source_checks"].append({
            "key": "injury_pdf_probe",
            "url": "https://ak-static.cms.nba.com/referee/injury/x.pdf",
            "http_status": 200, "checked_at_utc": "2026-11-19T12:03:37Z",
            "sha256": "b" * 64})
        self.record = record

    def _run(self):
        return evaluate_with_report(self.record, NOW, max_age_hours=10)

    def test_absent_capture_for_declared_source_does_not_block(self):
        """Defect 1: `_capture_S1_season.json` can never exist for a declared source."""
        errors, report = self._run()
        self.assertIn("S1_season", [d["source_key"] for d in report["declarations_applied"]])
        self.assertFalse([e for e in errors if "_capture_S1_season.json" in e],
                         f"absent capture must not block a declared source: {errors}")
        self.assertFalse([e for e in errors
                          if "advanced team input cannot be compared" in e],
                         f"no capture means no comparison: {errors}")

    def test_snapshot_without_row_count_is_a_complete_table(self):
        """Defect 2: the capture schema has no `row_count` field."""
        _write(self.root, "data/raw/_capture_S1_season.json",
               {"cols": [f"c{i}" for i in range(20)],
                "rows": [[f"Team {i}"] + [1] * 19 for i in range(30)]})
        errors, _ = self._run()
        self.assertFalse([e for e in errors if "not a complete 30-team table" in e],
                         f"30 rows is complete regardless of a missing row_count: {errors}")

    def test_declared_source_that_parses_is_still_refused(self):
        """The section 69 anti-rot rule survives both fixes."""
        _write(self.root, "data/raw/_capture_S1_season.json",
               {"cols": [f"c{i}" for i in range(20)],
                "rows": [[f"Team {i}"] + [1] * 19 for i in range(30)]})
        errors, report = self._run()
        self.assertEqual(report["declarations_applied"], [],
                         "a declaration must not survive a source that parsed rows")
        self.assertTrue([e for e in errors if "DECLARATION STALE" in " ".join(report["warnings"])
                         or "advanced team capture does not exactly match" in e],
                        f"a parsing declared source must block: {errors} {report['warnings']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
