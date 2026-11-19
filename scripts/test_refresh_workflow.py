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
        self.assertIn("scripts/stage_publish.py", publish)
        helper = (Path(__file__).resolve().parents[1]
                  / "scripts" / "stage_publish.py").read_text(encoding="utf-8")
        for path in ("data/raw/unreadable_sources.json",
                     "data/raw/refresh_path_audit.json",
                     "data/raw/sources.json"):
            self.assertIn(path, helper)

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
    """COORDINATION.md section 77.1 - the atomic `git add` abort defect.

    Measured: `git add a.json missing.json b.json` stages NOTHING and the
    publish step hid that behind `2>/dev/null || true`, so every verified
    promotion of every scheduled run was silently discarded while the run
    record claimed `promoted`. These tests pin the fix: staging is per-file
    and existence-checked, one missing path can never cost the rest.
    """

    def test_publish_step_uses_the_staging_helper_not_batched_git_add(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        publish = text.split("name: Publish captures", 1)[1]
        self.assertIn("python3 scripts/stage_publish.py evidence", publish)
        self.assertIn("python3 scripts/stage_publish.py promoted", publish)
        self.assertIn("python3 scripts/stage_publish.py record", publish)
        # The defect's exact shape must not reappear: a multi-pathspec
        # git add where one absent path aborts the batch.
        self.assertNotIn("git add data/raw/standings.json", publish)

    def test_derived_outputs_are_staged_only_when_the_rebuild_ran(self):
        publish = WORKFLOW.read_text(encoding="utf-8").split(
            "name: Publish captures", 1)[1]
        self.assertIn('BUILD_OUTCOME: ${{ steps.build.outcome }}', publish)
        self.assertIn('if [ "${BUILD_OUTCOME}" = "success" ]', publish)
        self.assertIn("python3 scripts/stage_publish.py derived", publish)

    def _scratch_repo(self):
        import subprocess
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        root = tmp.name
        for args in (["git", "init", "-q"],
                     ["git", "config", "user.email", "t@t"],
                     ["git", "config", "user.name", "t"]):
            subprocess.run(args, cwd=root, check=True, capture_output=True)
        return tmp, root

    def test_stage_publish_skips_missing_paths_and_stages_the_rest(self):
        import subprocess
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import stage_publish
        tmp, root = self._scratch_repo()
        self.addCleanup(tmp.cleanup)
        for name in ("a.json", "b.json"):
            with open(os.path.join(root, name), "w") as fh:
                fh.write("{}")
        staged, absent = stage_publish.stage(
            ["a.json", "missing.json", "b.json"], root)
        self.assertEqual(sorted(staged), ["a.json", "b.json"])
        self.assertEqual(absent, ["missing.json"])
        out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             cwd=root, capture_output=True, text=True)
        self.assertEqual(sorted(out.stdout.split()), ["a.json", "b.json"])

    def test_stage_publish_globs_with_no_matches_are_skipped_not_fatal(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import stage_publish
        tmp, root = self._scratch_repo()
        self.addCleanup(tmp.cleanup)
        staged, absent = stage_publish.stage(["data/raw/_capture_*.json"], root)
        self.assertEqual(staged, [])
        self.assertEqual(absent, ["data/raw/_capture_*.json"])

    def test_stage_publish_walks_directories_file_by_file(self):
        import subprocess
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import stage_publish
        tmp, root = self._scratch_repo()
        self.addCleanup(tmp.cleanup)
        os.makedirs(os.path.join(root, "data/parsed/x"))
        for rel in ("data/parsed/one.json", "data/parsed/x/two.json"):
            with open(os.path.join(root, rel), "w") as fh:
                fh.write("{}")
        staged, absent = stage_publish.stage(["data/parsed/"], root)
        self.assertEqual(sorted(staged),
                         ["data/parsed/one.json", "data/parsed/x/two.json"])
        self.assertEqual(absent, [])


if __name__ == "__main__":
    unittest.main()
