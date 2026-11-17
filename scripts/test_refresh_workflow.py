"""Regression checks for the scheduled refresh workflow's fail-closed gate.

These are structural checks against the workflow source; the behavior of the
freshness/provenance calculation itself is exercised by test_refresh_gate.py.
"""
from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/refresh-data.yml"


class RefreshWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_build_requires_successful_fetch_promotion_and_freshness(self):
        self.assertIn(
            "if: steps.fetch.outcome == 'success' && steps.promote.outcome == 'success' "
            "&& steps.freshness.outcome == 'success' && steps.freshness.outputs.ok == 'true'",
            self.text,
        )

    def test_promotion_and_freshness_are_fail_closed_steps(self):
        for step_id in ("promote", "freshness"):
            marker = f"id: {step_id}\n        if:"
            self.assertIn(marker, self.text)
            section = self.text.split(marker, 1)[1].split("\n      - name:", 1)[0]
            self.assertIn("continue-on-error: true", section)

    def test_run_record_and_refresh_pr_report_expose_gate_outcomes(self):
        for field in (
            's["fetch_outcome"]',
            's["promote_outcome"]',
            's["freshness_outcome"]',
            's["freshness_ok"]',
            's["settlement_outcome"]',
            's["build_outcome"]',
        ):
            self.assertIn(field, self.text)
        for field in ("promotion step", "freshness step", "freshness gate `ok`", "settlement step"):
            self.assertIn(field, self.text)


if __name__ == "__main__":
    unittest.main()
