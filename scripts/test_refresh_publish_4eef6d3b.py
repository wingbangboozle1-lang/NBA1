"""Pins for two refresh-workflow shell defects (COORDINATION.md section 74).

Both defects were measured on real run 44520339923 (2026-11-19T12:03Z,
`Refresh official data`) and reproduced locally before being fixed:

1. **Publish staging (T02).** The publish step staged the digest-bound
   promoted inputs with ONE compound ``git add`` that listed the three
   declared-unreadable snapshots first (``standings.json``,
   ``team_traditional.json``, ``team_opponent.json`` - 0 commits in
   repository history; the promote step can never write them).  Git's
   ``add`` is atomic per invocation: one unmatched pathspec aborts the
   whole list, and ``2>/dev/null || true`` swallowed the abort.  Result:
   ``schedule_upcoming.json``, ``injuries.json``, ``games_completed.json``,
   ``team_advanced.json`` and ``data/parsed/`` were never staged by any run
   since the step existed (proved on branch ``auto/refresh-20261119-120839``:
   its run record says "promoted" for those items; its commit contains none
   of the files).  The fix stages every pathspec in its own ``git add``.

2. **Settle-step exit-3 abort (T03).**  The step tolerates
   ``scripts/settle_slate.py`` exit 3 ("nothing settleable") in its own
   shell logic, but Actions runs step scripts as ``bash -eo pipefail``, so
   the previous ``python3 ...; rc=$?`` pattern died at the command and the
   tolerance never executed: the step reported ``failure`` on every run
   whose newest window was incomplete (run annotation: "Process completed
   with exit code 3"), and - because slates are iterated in ascending order
   - an un-settleable slate aborted the loop before later slates ran.  The
   fix captures the exit code with ``|| rc=$?``.

These tests re-run the ACTUAL shell blocks extracted from
``.github/workflows/refresh-data.yml`` against stubs, so the pinned
behaviour is the shipped script's, not a paraphrase.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "refresh-data.yml"


def _step_block(text: str, id_marker: str) -> str:
    """Return the `run: |` script of the step whose body contains id_marker."""
    seg = text.split(id_marker, 1)[1].split("\n      - name:", 1)[0]
    lines = seg.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("run:"):
            body = lines[i + 1:]
            break
    else:
        raise AssertionError(f"no run: block after {id_marker!r}")
    indents = [len(ln) - len(ln.lstrip()) for ln in body if ln.strip()]
    cut = min(indents) if indents else 0
    return "\n".join(ln[cut:] if len(ln) >= cut else ln for ln in body)


class GitAddAtomicityTests(unittest.TestCase):
    """The bug class itself, reproduced (section 74.2)."""

    def _git(self, cwd, *args, check=True):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=cwd, env=env,
                              capture_output=True, text=True, check=check)

    def _repo(self):
        d = tempfile.mkdtemp(prefix="nba1-add-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self._git(d, "init", "-q", ".")
        os.makedirs(os.path.join(d, "data", "raw"))
        Path(d, "data", "raw", "exists.json").write_text('{"a": 1}')
        Path(d, "data", "parsed_file.json").write_text('{"b": 2}')
        self._git(d, "add", "-A")
        self._git(d, "commit", "-qm", "init")
        Path(d, "data", "raw", "exists.json").write_text('{"a": 2}')
        Path(d, "data", "parsed_file.json").write_text('{"b": 3}')
        return d

    def test_compound_add_with_one_missing_pathspec_stages_nothing(self):
        d = self._repo()
        self._git(d, "add", "data/raw/standings.json", "data/raw/exists.json",
                  "data/parsed_file.json", check=False)
        staged = self._git(d, "diff", "--cached", "--name-only").stdout.split()
        self.assertEqual(staged, [],
                         "git add is atomic per invocation: one unmatched "
                         "pathspec must abort the whole list (this is the "
                         "bug class the workflow fix removes)")

    def test_per_path_adds_survive_missing_pathspecs(self):
        d = self._repo()
        for p in ("data/raw/standings.json", "data/raw/exists.json",
                  "data/parsed_file.json"):
            self._git(d, "add", "--", p, check=False)
        staged = self._git(d, "diff", "--cached", "--name-only").stdout.split()
        self.assertEqual(sorted(staged),
                         ["data/parsed_file.json", "data/raw/exists.json"],
                         "per-path git add must stage every existing path "
                         "even when sibling paths can never exist")


class PublishStepStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.script = _step_block(cls.text, "Publish captures")

    def test_staging_loop_present(self):
        self.assertIn("for p in ", self.script)
        self.assertIn('git add -- "${p}" 2>/dev/null || true', self.script)
        self.assertIn("done", self.script)

    def test_no_compound_add_mixes_missing_snapshots_with_promotable_paths(self):
        # No single `git add` invocation may name one of the never-existing
        # snapshots together with a promotable input (that is exactly the
        # abort that lost them all).  The per-path loop is the only staging
        # mechanism left in the step.
        for m in re.finditer(r"^(\s*)git add\b[^\n]*(\\\n[^\n]*)*", self.script,
                             re.MULTILINE):
            cmd = m.group(0)
            self.assertNotIn("standings.json", cmd)
            self.assertNotIn("team_traditional.json", cmd)
            self.assertNotIn("team_opponent.json", cmd)

    def test_every_promotable_path_is_in_the_staging_loop(self):
        loop = re.search(r"for p in (.*?); do", self.script, re.DOTALL)
        self.assertIsNotNone(loop, "staging loop missing")
        blob = loop.group(1)
        for name in ("schedule_upcoming.json", "injuries.json",
                     "games_completed.json", "team_advanced.json",
                     "data/parsed/", "unreadable_sources.json",
                     "refresh_path_audit.json"):
            self.assertIn(name, blob)

    def test_staged_output_survives_missing_snapshots_in_real_git(self):
        """Run the workflow's own staging loop in a repo where the three
        declared-unreadable snapshots do not exist (they never have)."""
        d = tempfile.mkdtemp(prefix="nba1-publish-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        def git(*args, check=True):
            return subprocess.run(["git", *args], cwd=d, env=env,
                                  capture_output=True, text=True, check=check)
        git("init", "-q", ".")
        os.makedirs(os.path.join(d, "data", "raw"))
        os.makedirs(os.path.join(d, "data", "parsed"))
        for p in ("data/raw/_capture_S4_schedule.json",
                  "data/raw/schedule_upcoming.json",
                  "data/raw/injuries.json",
                  "data/raw/games_completed.json",
                  "data/raw/team_advanced.json",
                  "data/parsed/promotion_report.json"):
            Path(d, p).write_text("{}")
        Path(d, "x").write_text("x")
        git("add", "-A")
        git("commit", "-qm", "init")
        for p in ("data/raw/_capture_S4_schedule.json",
                  "data/raw/schedule_upcoming.json",
                  "data/raw/injuries.json",
                  "data/raw/games_completed.json",
                  "data/raw/team_advanced.json",
                  "data/parsed/promotion_report.json"):
            Path(d, p).write_text('{"changed": 1}')
        loop = re.search(r"^(\s*)for p in .*?^\s*done", self.script,
                         re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(loop)
        indents = [len(ln) - len(ln.lstrip())
                   for ln in loop.group(0).splitlines() if ln.strip()]
        body = "\n".join(ln[min(indents):] for ln in loop.group(0).splitlines())
        Path(d, "stage.sh").write_text("set -u\n" + body + "\n")
        run = subprocess.run(["bash", "-eo", "pipefail", "stage.sh"], cwd=d,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        staged = git("diff", "--cached", "--name-only").stdout.split()
        for name in ("data/raw/schedule_upcoming.json",
                     "data/raw/injuries.json",
                     "data/raw/games_completed.json",
                     "data/raw/team_advanced.json",
                     "data/parsed/promotion_report.json",
                     "data/raw/_capture_S4_schedule.json"):
            self.assertIn(name, staged,
                          "the promoted input must be staged even though "
                          "standings.json / team_traditional.json / "
                          "team_opponent.json cannot exist")


class SettleStepTests(unittest.TestCase):
    """Run the settle step's own shell against a stubbed settle_slate."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.script = _step_block(cls.text, "Settle every game day")

    def _sandbox(self, codes, ledger_rc=0, slate_dates=("2026-11-14", "2026-11-15")):
        """codes: dict slate-date -> exit code of settle_slate."""
        d = tempfile.mkdtemp(prefix="nba1-settle-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        os.makedirs(os.path.join(d, "scripts"))
        os.makedirs(os.path.join(d, "data", "archive"))
        for date in slate_dates:
            Path(d, "data", "archive", f"horizon_picks_{date}.json").write_text("{}")
        calls = Path(d, "calls.log")
        calls.write_text("")
        # Stub settle_slate: scripted per-slate exit codes, records the call.
        Path(d, "scripts", "settle_slate.py").write_text(
            "import re, sys\n"
            "args = ' '.join(sys.argv[1:])\n"
            "m = re.search(r'--slate (\\S+)', args)\n"
            "date = m.group(1) if m else '?'\n"
            f"open({str(calls)!r}, 'a').write(date + '\\n')\n"
            "codes = " + repr({k: int(v) for k, v in codes.items()}) + "\n"
            "sys.exit(codes.get(date, 0))\n")
        Path(d, "scripts", "verify_ledger.py").write_text(
            "import sys\n"
            f"open({str(calls)!r}, 'a').write('verify_ledger\\n')\n"
            f"sys.exit({int(ledger_rc)})\n")
        Path(d, "step.sh").write_text(self.script)
        return d, calls

    def _run(self, d):
        # The step's first heredoc writes /tmp/slates.txt from the CWD glob.
        return subprocess.run(["bash", "-eo", "pipefail", "step.sh"], cwd=d,
                              capture_output=True, text=True)

    def test_tolerated_exit_3_does_not_fail_the_step_under_bash_e(self):
        d, calls = self._sandbox({"2026-11-15": 3})
        run = self._run(d)
        self.assertEqual(run.returncode, 0,
                         "settle_slate exit 3 ('nothing settleable') is "
                         "documented as success for the step: " + run.stdout)
        self.assertIn("2026-11-14", calls.read_text())
        self.assertIn("2026-11-15", calls.read_text())
        self.assertIn("verify_ledger", calls.read_text())

    def test_empty_slate_does_not_skip_later_slates(self):
        # The old `python3 ...; rc=$?` died at the first exit 3 (ascending
        # sort), so every later slate was silently skipped.
        d, calls = self._sandbox({"2026-11-14": 3}, slate_dates=(
            "2026-11-14", "2026-11-15", "2026-11-16"))
        run = self._run(d)
        self.assertEqual(run.returncode, 0, run.stdout)
        order = [ln for ln in calls.read_text().splitlines() if ln != "verify_ledger"]
        self.assertEqual(order, ["2026-11-14", "2026-11-15", "2026-11-16"],
                         "every slate must be attempted, in order, even after "
                         "an un-settleable one")

    def test_real_failure_still_fails_the_step(self):
        d, calls = self._sandbox({"2026-11-15": 1})
        run = self._run(d)
        self.assertEqual(run.returncode, 1,
                         "a settle failure other than 0/3 must still fail: "
                         + run.stdout)

    def test_ledger_check_is_mandatory(self):
        d, calls = self._sandbox({}, ledger_rc=1)
        run = self._run(d)
        self.assertEqual(run.returncode, 1)
        self.assertIn("verify_ledger", calls.read_text())

    def test_step_captures_exit_code_with_or(self):
        # Structural pin: the settle invocation must be failure-tolerant at
        # the shell level (`|| rc=$?`), not only in the `if` below it.
        self.assertRegex(
            self.script,
            r"python3 scripts/settle_slate\.py[^\n]*\|\|\s*rc=\$\?",
            "the settle call must capture its exit code with `|| rc=$?` so "
            "bash -e cannot kill the loop at exit 3")


if __name__ == "__main__":
    unittest.main()
