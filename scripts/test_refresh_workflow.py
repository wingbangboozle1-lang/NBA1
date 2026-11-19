"""Regression checks for the scheduled refresh workflow's fail-closed gate.

These are structural checks against the workflow source; the behavior of the
freshness/provenance calculation itself is exercised by test_refresh_gate.py.
"""
from pathlib import Path
import os
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/refresh-data.yml"


class RefreshWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_build_requires_successful_fetch_and_freshness(self):
        """The gate decides, not promote's exit code (COORDINATION.md section 74).

        This test previously required `steps.promote.outcome == 'success'` in
        the rebuild condition. That was the defect, not the requirement:
        engine/promote_official.py exits 1 whenever ANY item is blocked, so one
        permanently blocked item (S1_season, whose capture has never existed)
        made the rebuild unreachable in every scheduled run. The freshness gate
        below re-reads the promotion records and blocks unless every required
        input is verified against this run's capture, which is the property that
        actually matters. Asserted positively AND negatively so the condition
        cannot silently regress in either direction.
        """
        self.assertIn(
            "if: steps.fetch.outcome == 'success' && steps.freshness.outcome == 'success' "
            "&& steps.freshness.outputs.ok == 'true'",
            self.text,
        )
        self.assertNotIn("steps.promote.outcome == 'success'", self.text,
                         "promote's exit code must not gate the rebuild")

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
        for path in ("data/raw/unreadable_sources.json",
                     "data/raw/refresh_path_audit.json",
                     "data/raw/sources.json"):
            self.assertIn(path, publish)

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


class PublishStagingTests(unittest.TestCase):
    """The atomic `git add` abort defect and its landed fix.

    Measured (sections 74 T02 and 78.1 independently): `git add
    a.json missing.json b.json` stages NOTHING and the publish step hid that
    behind `2>/dev/null || true`, so every verified promotion of every
    scheduled run was silently discarded while the run record claimed
    `promoted`. The landed fix stages each path in its own `git add`,
    warns on absent paths, and expands globs only when they match. These
    tests pin the mechanism in the workflow source and the underlying git
    property that made the old form fatal.
    """

    def test_publish_staging_is_per_path_and_tolerates_absent_paths(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        publish = text.split("name: Publish captures", 1)[1]
        # Per-path adds inside the candidates loop.
        self.assertIn('git add -- "$p"', publish)
        self.assertIn("Publish path absent", publish)
        # Globs are expanded only when non-empty (an empty glob is also an
        # unmatched pathspec and would abort the add).
        self.assertIn("compgen -G", publish)
        # The defect's exact shape must not reappear: a multi-pathspec
        # git add where one absent path aborts the batch.
        self.assertNotIn("git add data/raw/standings.json", publish)

    def test_rebuild_outputs_are_staged_only_when_the_rebuild_ran(self):
        publish = WORKFLOW.read_text(encoding="utf-8").split(
            "name: Publish captures", 1)[1]
        self.assertIn('BUILD_OUTCOME: ${{ steps.build.outcome }}', publish)
        self.assertIn('os.environ.get("BUILD_OUTCOME") == "success"', publish)
        self.assertIn("data/hca_measured.json", publish)
        self.assertIn("data/derived/", publish)

    def test_git_add_is_atomic_per_invocation(self):
        """The root cause, pinned: one unmatched pathspec voids the batch.

        This is a property of git itself; it is why the publish step must
        never batch paths with possibly-absent pathspecs. If a future edit
        re-batches the add, the two tests above catch the workflow text and
        this test documents why the old text was fatal.
        """
        import subprocess
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        for args in (["git", "init", "-q"],
                     ["git", "config", "user.email", "t@t"],
                     ["git", "config", "user.name", "t"]):
            subprocess.run(args, cwd=root, check=True, capture_output=True)
        for name in ("a.json", "b.json"):
            with open(os.path.join(root, name), "w") as fh:
                fh.write("{}")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True,
                       capture_output=True)
        for name in ("a.json", "b.json"):
            with open(os.path.join(root, name), "w") as fh:
                fh.write("{changed}")
        # THE defect, reproduced verbatim: one missing pathspec, whole batch
        # aborted silently.
        subprocess.run(["git", "add", "a.json", "missing.json", "b.json"],
                       cwd=root, capture_output=True)
        out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             cwd=root, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "",
                         "expected the batch to abort atomically")
        # The landed pattern: one add per existing path.
        for name in ("a.json", "b.json"):
            subprocess.run(["git", "add", "--", name], cwd=root, check=True,
                           capture_output=True)
        out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             cwd=root, capture_output=True, text=True)
        self.assertEqual(sorted(out.stdout.split()), ["a.json", "b.json"])


if __name__ == "__main__":
    unittest.main()
