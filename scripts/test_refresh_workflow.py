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

    def test_promotion_runs_after_completed_fetch_and_freshness_is_success_only(self):
        promote = self.text.split("id: promote", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("if: always()", promote)
        self.assertIn("steps.fetch.outcome != 'cancelled'", promote)
        self.assertIn("steps.fetch.outcome != 'skipped'", promote)
        self.assertIn("continue-on-error: true", promote)
        freshness = self.text.split("id: freshness", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("if: steps.fetch.outcome == 'success'", freshness)
        self.assertIn("continue-on-error: true", freshness)

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

    def test_a_declaration_pass_is_surfaced_in_the_run_log(self):
        """A green gate on a declaration must never look like a green gate on data."""
        freshness = self.text.split("id: freshness", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("_capture_gate_report.json", freshness)
        self.assertIn("declarations_applied", freshness)
        self.assertIn("::warning title=Gate passed by declaration::", freshness)

    def test_the_declaration_register_is_staged_for_publication(self):
        # If the bot cannot stage it, a live declaration could be silently
        # reverted by the next automated commit and the gate would block again.
        publish = self.text.split("name: Publish captures", 1)[1]
        self.assertIn("data/raw/unreadable_sources.json", publish)
        self.assertIn("data/raw/refresh_path_audit.json", publish)

    def test_the_gate_step_cannot_fail_the_job_on_a_declaration_note(self):
        """The gate keeps its own exit code out of the step's status.

        The step must not become a silent pass: the rebuild still requires
        `steps.freshness.outputs.ok == 'true'`, which only engine/refresh_gate.py
        writes, and that is asserted separately below.
        """
        freshness = self.text.split("id: freshness", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("exit 0", freshness)
        build = self.text.split("id: build", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("steps.freshness.outputs.ok == 'true'", build)


if __name__ == "__main__":
    unittest.main()
