"""Regression test for injury-edition promotion after partial fetch failures.

The fetcher captures sources independently. A failure parsing an unrelated NBA
client-rendered page must not suppress verified injury PDF promotion, although
it must continue to prevent a model/site rebuild.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/refresh-data.yml"


class RefreshWorkflowInjuryTriggerTests(unittest.TestCase):
    def test_promotion_runs_after_any_completed_fetch_attempt(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = text.split("- name: Promote verified structured inputs", 1)[1].split(
            "- name: Require fresh provenance", 1
        )[0]
        self.assertIn("if: always() && steps.fetch.outcome != 'cancelled'", step)
        self.assertIn("steps.fetch.outcome != 'skipped'", step)
        self.assertIn("python3 engine/promote_official.py", step)

    def test_rebuild_still_requires_successful_fetch_promotion_and_freshness(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = text.split("- name: Rebuild only after all freshness", 1)[1].split(
            "- name: Settle every game day", 1
        )[0]
        condition = next(line for line in step.splitlines() if line.strip().startswith("if:"))
        self.assertIn("steps.fetch.outcome == 'success'", condition)
        self.assertNotIn("steps.promote.outcome == 'success'", condition,
                         "promote exit code must not gate the rebuild (section 74)")
        self.assertIn("steps.freshness.outcome == 'success'", condition)
        self.assertIn("steps.freshness.outputs.ok == 'true'", condition)


if __name__ == "__main__":
    unittest.main()
