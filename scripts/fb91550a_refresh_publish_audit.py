"""R01 audit: why the scheduled refresh has never reached the rebuild step.

Every number this script prints is read from artefacts that exist in the
repository or from the git history itself (COORDINATION.md section 74). Nothing
is typed by hand, and nothing is inferred: a fact that cannot be read is
reported as UNREADABLE rather than assumed.

What it measures
----------------
1. `git log --all` commit counts for every path the freshness gate requires.
   The declared-unreadable rule (COORDINATION.md section 69/73) requires a
   snapshot to have ZERO commits in the entire history before a declaration is
   admissible. Zero is a measured number here, not a claim in prose.
2. Whether the publish step's `git add` file list can succeed: `git add` aborts
   the WHOLE invocation when any pathspec matches nothing, so a single missing
   path (for example a declared-unreadable source's snapshot, which by
   definition does not exist) silently drops every capture, settlement and
   promoted input from the commit. That is a mechanism, so it is demonstrated
   by running it, not asserted.
3. Whether a pull request was ever opened for a scheduled run's
   `auto/refresh-*` branch. Thirteen such branches exist; the count of pull
   requests ever opened from any of them is the measurement that settles
   "scheduled captures reach main" as false rather than "unproven".

Usage
-----
    python3 scripts/fb91550a_refresh_publish_audit.py            # measure
    python3 scripts/fb91550a_refresh_publish_audit.py --write    # + JSON record
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(ROOT, "data", "raw", "refresh_publish_audit.json")

# Every path the gate requires, plus the three declared-unreadable snapshots and
# the promotion outputs the publish step stages.
GATE_PATHS = [
    "data/raw/_capture_S1_season.json",
    "data/raw/_capture_S2_train.json",
    "data/raw/_capture_S4_schedule.json",
    "data/raw/_capture_S5_injury_index.json",
    "data/raw/_capture_S7_players.json",
    "data/raw/team_advanced.json",
    "data/raw/standings.json",
    "data/raw/team_traditional.json",
    "data/raw/team_opponent.json",
    "data/raw/schedule_upcoming.json",
    "data/raw/injuries.json",
    "data/raw/games_completed.json",
    "data/raw/unreadable_sources.json",
    "data/raw/refresh_path_audit.json",
    "data/raw/refresh_publish_audit.json",
]


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def commits_touching(path: str) -> int:
    return len([ln for ln in git("log", "--all", "--oneline", "--", path).splitlines() if ln])


def tracked(path: str) -> bool:
    try:
        git("ls-files", "--error-unmatch", path)
        return True
    except RuntimeError:
        return False


def main() -> int:
    write = "--write" in sys.argv[1:]
    facts: dict = {"generated_by": "scripts/fb91550a_refresh_publish_audit.py",
                   "board": "COORDINATION.md section 74",
                   "paths": {}, "git_add": {}, "auto_branches": {}}

    for path in GATE_PATHS:
        facts["paths"][path] = {
            "tracked_now": tracked(path),
            "commits_in_history": commits_touching(path),
        }

    # Demonstrate the pathspec behaviour instead of describing it. The probe
    # path is a file that provably has never existed (the gate itself blocks on
    # its absence); if it is ever created this measurement becomes stale, so
    # the probe reports that instead of guessing.
    probe = "data/raw/_capture_S1_season.json"
    facts["git_add"]["probe_path"] = probe
    facts["git_add"]["probe_tracked"] = tracked(probe)
    if not tracked(probe):
        res = subprocess.run(["git", "add", "--dry-run", probe, "data/raw/unreadable_sources.json"],
                             cwd=ROOT, capture_output=True, text=True)
        facts["git_add"]["combined_dry_run_exit"] = res.returncode
        facts["git_add"]["combined_stderr"] = res.stderr.strip()[:400]
        facts["git_add"]["conclusion"] = (
            "git add aborts the entire invocation when any one pathspec matches "
            "nothing, so the publish step's list - which names paths that can "
            "never exist while a source is declared unreadable - commits "
            "nothing at all"
            if res.returncode != 0 else
            "git add accepted every path this run; the failure is elsewhere")

    heads = [ln.split("refs/heads/")[1] for ln in
             git("ls-remote", "--heads", "origin").splitlines()
             if "refs/heads/auto/refresh-" in ln]
    facts["auto_branches"] = {"count": len(heads), "branches": sorted(heads)}
    if heads:
        try:
            prs = json.loads(subprocess.run(
                ["gh", "api",
                 "/repos/wingbangboozle1-lang/NBA1/pulls?state=all&per_page=100",
                 "--jq", "[.[] | {number, head: .head.ref, state}]"],
                cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            from_auto = [p for p in prs if str(p.get("head", "")).startswith("auto/refresh-")]
            facts["auto_branches"]["pull_requests_ever_opened"] = len(from_auto)
            facts["auto_branches"]["pr_numbers"] = [p["number"] for p in from_auto]
        except Exception as exc:                       # noqa: BLE001
            facts["auto_branches"]["pull_requests_ever_opened"] = \
                f"UNREADABLE ({type(exc).__name__}: {exc})"

    missing_in_publish_step = [p for p, f in facts["paths"].items()
                               if not f["tracked_now"] and f["commits_in_history"] == 0]
    facts["publish_step_names_nonexistent_paths"] = missing_in_publish_step

    print(json.dumps(facts, indent=1))
    if write:
        with open(RECORD, "w", encoding="utf-8") as stream:
            json.dump(facts, stream, indent=1)
            stream.write("\n")
        print(f"\nwrote {os.path.relpath(RECORD, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
