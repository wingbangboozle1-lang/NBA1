"""The bet page must fail closed when the scheduled refresh proof is stale or blocked."""
import datetime as dt
import unittest
from unittest.mock import patch

from scripts import build_surfaces


class BetSurfaceFreshnessTests(unittest.TestCase):
    def test_freshness_gate_passes_only_when_full_refresh_gate_passes(self):
        record = {"captured_at_utc": "fixture"}
        now = dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.timezone.utc)
        with patch.object(build_surfaces, "_load", return_value=record), \
             patch.object(build_surfaces.dt, "datetime") as clock, \
             patch.object(build_surfaces, "evaluate_refresh_gate", return_value=[]) as evaluate:
            clock.now.return_value = now
            gate = build_surfaces.gate_freshness()

        self.assertTrue(gate["passed"])
        self.assertEqual(gate["id"], "G5_freshness_provenance")
        evaluate.assert_called_once_with(record, now, max_age_hours=10)

    def test_freshness_gate_closes_and_reports_full_gate_errors(self):
        record = {"captured_at_utc": "old"}
        errors = ["refresh run is stale", "capture awaits verified promotion"]
        with patch.object(build_surfaces, "_load", return_value=record), \
             patch.object(build_surfaces, "evaluate_refresh_gate", return_value=errors):
            gate = build_surfaces.gate_freshness()

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["observed"], "BLOCKED")
        self.assertEqual(gate["observed_detail"], errors)

    def test_unexpected_refresh_evaluator_error_fails_closed(self):
        with patch.object(build_surfaces, "_load", return_value={"captured_at_utc": "bad"}), \
             patch.object(build_surfaces, "evaluate_refresh_gate", side_effect=RuntimeError("bad proof")):
            gate = build_surfaces.gate_freshness()

        self.assertFalse(gate["passed"])
        self.assertIn("bad proof", gate["observed_detail"][0])

    def test_closed_freshness_gate_suppresses_pick_table(self):
        gates = {
            "open": False,
            "closed_by": ["G5_freshness_provenance"],
            "gates": [{
                "id": "G5_freshness_provenance",
                "requirement": "fresh verified inputs",
                "observed": "BLOCKED",
                "observed_detail": ["refresh run is stale", "capture awaits verified promotion"],
                "passed": False,
                "source": "data/raw/_last_refresh.json + engine/refresh_gate.py",
            }],
        }
        page = build_surfaces.render_bet(gates, picks=[])
        self.assertIn("G5_freshness_provenance", page)
        self.assertIn("No picks are shown", page)
        self.assertIn("refresh run is stale", page)
        self.assertNotIn("<th>Pick</th>", page)


if __name__ == "__main__":
    unittest.main()
