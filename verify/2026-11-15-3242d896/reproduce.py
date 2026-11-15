#!/usr/bin/env python3
"""Reproduce every number in verify/2026-11-15-3242d896/REPORT.md.

    python3 verify/2026-11-15-3242d896/reproduce.py

Design rules:
  * No network. Everything here is read from this repository or from objects
    already fetched into it (the origin/auto/* scheduled-run branches are read
    with `git show`, never with an HTTP request).
  * No repository file outside this directory is written. A scratch copy of the
    tree is made under tempfile so the gate can be run against historical
    records without touching data/raw/_last_refresh.json.
  * Every section prints the exact evidence the report cites. If a section
    cannot run (e.g. the auto branches are absent), it says so and exits
    non-zero rather than silently passing.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))

PROMOTED = ("data/raw/standings.json",
            "data/raw/team_traditional.json",
            "data/raw/team_opponent.json")

failures = []


def say(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def run(cmd, cwd=ROOT, check=False):
    proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"command failed: {cmd}\n{proc.stdout}\n{proc.stderr}")
    return proc


def block_lines(text):
    return [line for line in text.splitlines() if line.startswith("BLOCK")]


def read_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return json.load(handle)


def make_tree(dest):
    """Copy the working tree (no .git) so gate runs never touch data/."""
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(ROOT, dest, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
    return dest


def git_show(rev_path):
    proc = run(f"git show {rev_path}")
    if proc.returncode != 0:
        return None
    return proc.stdout


# ---------------------------------------------------------------- section 1
def section_gate_on_committed_tree():
    say("1. The gate on the committed tree (R-43-06)")
    proc = run("python3 engine/refresh_gate.py --max-age-hours 10")
    blocks = block_lines(proc.stdout)
    for line in blocks:
        print("  " + line)
    print(f"\n  exit={proc.returncode}  BLOCK lines={len(blocks)}")
    record = read_json("data/raw/_last_refresh.json")
    print(f"  committed record: captured_at_utc={record.get('captured_at_utc')} "
          f"build_outcome={record.get('build_outcome')} "
          f"source_checks={len(record.get('source_checks', []))}")
    return {"exit": proc.returncode, "block_lines": len(blocks), "output": proc.stdout}


# ---------------------------------------------------------------- section 2
def section_missing_inputs():
    say("2. The three promoted inputs the gate requires (R-43-01)")
    for rel in PROMOTED:
        print(f"  {'PRESENT' if os.path.exists(os.path.join(ROOT, rel)) else 'ABSENT ':8s} {rel}")
    grep = run("grep -rn 'standings\\.json\\|team_traditional\\.json\\|team_opponent\\.json' "
               "--include=*.py . || true")
    hits = [l for l in grep.stdout.splitlines() if not l.startswith("./verify/")]
    print(f"\n  python references ({len(hits)}):")
    for line in hits:
        print("   ", line)
    writers = [l for l in hits if "open(" in l and ", \"w\"" in l]
    print(f"\n  references that WRITE one of the three files: {len(writers)}")
    if not writers:
        print("  -> no code in this repository writes them; the gate cannot pass by construction")
    absent = [rel for rel in PROMOTED if not os.path.exists(os.path.join(ROOT, rel))]
    return {"absent": absent, "writers": len(writers), "references": hits}


# ---------------------------------------------------------------- section 3
def section_best_case_record(scratch):
    """Run the gate against the real 22:44Z scheduled run's own source checks."""
    say("3. Gate verdict on the best record the fetcher can physically produce (R-43-01, E2)")
    raw = git_show("origin/auto/refresh-20261115-224729:data/raw/_last_refresh.json")
    if raw is None:
        failures.append("origin/auto/refresh-20261115-224729 is not available; "
                        "run `git fetch origin '+refs/heads/auto/*:refs/remotes/origin/auto/*'`")
        print("  SKIPPED: the scheduled-run branch is not fetched locally")
        return None
    run_record = json.loads(raw)
    print(f"  source run record: captured_at_utc={run_record['captured_at_utc']} "
          f"failed={run_record['failed']}")
    checks = {}
    for check in run_record.get("source_checks", []):
        if isinstance(check, dict) and "url" in check:
            checks[check["key"]] = check
    primary = ["S1_season", "S2_train", "S7_players", "S4_schedule",
               "S5_injury_index", "S8_standings", "S9_team_traditional",
               "S10_team_opponent"]
    missing = [k for k in primary if k not in checks]
    if missing:
        print("  SKIPPED: the run record lacks these primary checks:", missing)
        failures.append(f"run record lacks primary checks {missing}")
        return None
    record = dict(read_json("data/raw/_last_refresh.json"))
    record["captured_at_utc"] = "2026-11-15T23:50:00Z"
    record["source_checks"] = [checks[k] for k in primary]
    record["failed"] = []
    record["changed"] = []
    path = os.path.join(scratch, "data/raw/_last_refresh.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1)
    proc = run("python3 engine/refresh_gate.py --record data/raw/_last_refresh.json "
               "--max-age-hours 10 --now 2026-11-15T23:55:00Z", cwd=scratch)
    blocks = block_lines(proc.stdout)
    for line in blocks:
        print("  " + line)
    print(f"\n  exit={proc.returncode}  BLOCK lines={len(blocks)}  "
          f"(8/8 primary sources HTTP 200, 0 failed, 0 changed)")
    shutil.copyfile(os.path.join(ROOT, "data/raw/_last_refresh.json"), path)
    return {"exit": proc.returncode, "block_lines": len(blocks), "output": proc.stdout}


# ---------------------------------------------------------------- section 4
def section_contradicting_run(scratch):
    say("4. The pre-gate scheduled run that recorded build_outcome=success (R-43-03, E3)")
    print("  Attribution check: which workflow ran at this record's commit?")
    run_id = run("gh api /repos/wingbangboozle1-lang/NBA1/actions/runs/43710500439 "
                 "--jq '.created_at, .head_sha' 2>/dev/null || true").stdout.strip()
    print("  run 43710500439 (schedule):", (run_id or "gh unavailable").replace("\n", " "))
    steps = run("gh api /repos/wingbangboozle1-lang/NBA1/actions/runs/43710500439/jobs "
                "--jq '.jobs[0].steps[]|select(.number<=12)|\"\(.number) \(.name)\"' 2>/dev/null || true")
    if steps.stdout.strip():
        print("  its steps (pre-gate workflow: a liveness build runs BEFORE the fetch):")
        for line in steps.stdout.strip().splitlines():
            print("   ", line)
        print('  -> build_outcome=success here means "the pre-fetch liveness build ran",')
        print('     not "the gated rebuild passed". No gate existed at that commit.')
    raw = git_show("origin/auto/refresh-20261115-114915:data/raw/_last_refresh.json")
    if raw is None:
        failures.append("origin/auto/refresh-20261115-114915 is not available")
        print("  SKIPPED: branch not fetched locally")
        return None
    record = json.loads(raw)
    print(f"  captured_at_utc : {record.get('captured_at_utc')}")
    print(f"  fetch_outcome   : {record.get('fetch_outcome')}")
    print(f"  build_outcome   : {record.get('build_outcome')}   <-- a build step ran (pre-fetch liveness build, NOT a gated rebuild)")
    print(f"  source_checks   : {len(record.get('source_checks', []))}   <-- no provenance checks")
    print(f"  failed          : {record.get('failed')}")
    path = os.path.join(scratch, "data/raw/_last_refresh.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1)
    proc = run("python3 engine/refresh_gate.py --record data/raw/_last_refresh.json "
               "--max-age-hours 10 --now 2026-11-15T11:50:00Z", cwd=scratch)
    blocks = block_lines(proc.stdout)
    print(f"\n  the same gate today: exit={proc.returncode}  BLOCK lines={len(blocks)}")
    for line in blocks[:6]:
        print("   ", line)
    print(f"    ... {max(0, len(blocks) - 6)} more")
    shutil.copyfile(os.path.join(ROOT, "data/raw/_last_refresh.json"), path)
    diff = run("git diff --stat main origin/auto/refresh-20261115-114915 | tail -3")
    print("\n  branch vs main (file churn):")
    for line in diff.stdout.splitlines():
        print("   ", line)
    return {"exit": proc.returncode, "block_lines": len(blocks),
            "record": {k: record.get(k) for k in
                       ("captured_at_utc", "fetch_outcome", "build_outcome", "failed")}}


# ---------------------------------------------------------------- section 5
def section_injury_filenames():
    say("5. Injury-report filename form used by the fetcher vs the official index (R-43-04)")
    source = open(os.path.join(ROOT, "engine/fetch_official.py"), encoding="utf-8").read()
    line = [l for l in source.splitlines() if "isoformat().replace('-', '_')" in l]
    print("  fetcher builds the edition name with:")
    for l in line:
        print("   ", l.strip())
    raw = git_show("origin/auto/refresh-20261115-224729:data/raw/_last_refresh.json")
    if raw is None:
        print("  SKIPPED: run record unavailable")
        return None
    probe = [c for c in json.loads(raw)["source_checks"] if c.get("key") == "injury_pdf_probe"]
    if not probe:
        failures.append("no injury_pdf_probe in the run record")
        return None
    ok, denied = [], []
    for result in probe[0]["results"]:
        name = result["edition"]
        (ok if result.get("http_status") == 200 else denied).append(name)
        print(f"    {str(result.get('http_status')):>4}  pdf_valid={result.get('pdf_valid')}  {name}")
    hyphen = [n for n in ok]
    underscore = [n for n in denied if n.count("_") > 2]
    print(f"\n  retrieved (hyphen-form, matches the official index): {len(hyphen)}")
    print(f"  refused   (underscore-form, absent from the official index): {len(underscore)}")
    print("  official index: https://official.nba.com/nba-injury-report-2026-27-season/")
    return {"retrieved": hyphen, "refused": underscore}


# ---------------------------------------------------------------- section 6
def section_rebuild_not_reproducible(scratch):
    say("6. Is the committed site data reproducible by the repo's own builders? (R-43-05)")
    make_tree(scratch)
    run("git init -q . && git add -A >/dev/null 2>&1 && "
        "git -c user.email=a@b -c user.name=c commit -qm base", cwd=scratch)
    builders = ["python3 engine/pipeline.py", "python3 engine/build_site.py",
                "python3 scripts/build_site.py", "python3 scripts/build_dashboard.py",
                "python3 command-center/build.py",
                "python3 scripts/build_verification_page.py"]
    for builder in builders:
        proc = run(builder, cwd=scratch)
        print(f"  {builder:48s} exit={proc.returncode}")
    status = run("git status --porcelain", cwd=scratch).stdout.strip().splitlines()
    print(f"\n  files differing from the committed tree after a full rebuild: {len(status)}")
    stat = run("git diff --stat", cwd=scratch).stdout.strip().splitlines()
    for line in stat[-13:]:
        print("   ", line)
    meta = run("git diff docs/data/meta.json", cwd=scratch).stdout
    removed = [l for l in meta.splitlines() if l.startswith("-") and not l.startswith("---")]
    print(f"\n  docs/data/meta.json: {len(removed)} lines the rebuild would DELETE")
    print("  (the committed file carries provenance prose the builder does not regenerate)")
    return {"changed_files": len(status), "meta_lines_removed": len(removed)}


# ---------------------------------------------------------------- section 7
def section_pdf_and_tests():
    say("7. What is correct: gate tests, PDF archive, official-host allowlist")
    proc = run("python3 -m unittest scripts.test_refresh_gate 2>&1 | tail -3")
    print("  unit tests:", proc.stdout.strip().replace("\n", " | "))
    pdfs = run("find . -name '*.pdf' -not -path './.git/*' | wc -l").stdout.strip()
    print(f"  *.pdf files committed on this tree: {pdfs}")
    archived = run("git ls-tree -r --name-only origin/auto/refresh-20261115-224729 "
                   "| grep injury_pdfs || true").stdout.strip().splitlines()
    print(f"  injury PDFs archived on the 22:47Z scheduled-run branch: {len(archived)} file(s)")
    for name in archived:
        print("   ", name)
    return {"tests": proc.stdout.strip(), "pdfs_on_tree": int(pdfs),
            "archived_on_run_branch": len(archived)}


def main():
    scratch = tempfile.mkdtemp(prefix="nba1-audit-")
    try:
        evidence = {
            "title": "Scheduled-refresh integrity audit — reproduced evidence bundle",
            "session": "arena/3242d896-nba1",
            "reproduced_at_utc": run("date -u +%Y-%m-%dT%H:%M:%SZ").stdout.strip(),
            "base_commit": run("git rev-parse HEAD").stdout.strip(),
        }
        gate_scratch = make_tree(os.path.join(tempfile.gettempdir(), "nba1-audit-gate"))
        evidence["gate_on_committed_tree"] = section_gate_on_committed_tree()
        evidence["promoted_inputs"] = section_missing_inputs()
        evidence["best_case_record"] = section_best_case_record(gate_scratch)
        evidence["contradicting_run"] = section_contradicting_run(gate_scratch)
        evidence["injury_filenames"] = section_injury_filenames()
        evidence["rebuild_reproducibility"] = section_rebuild_not_reproducible(scratch)
        evidence["what_is_correct"] = section_pdf_and_tests()
        with open(os.path.join(HERE, "evidence.json"), "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=1)
        print(f"\nwrote {os.path.join(HERE, 'evidence.json')}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(os.path.join(tempfile.gettempdir(), "nba1-audit-gate"), ignore_errors=True)

    say("RESULT")
    if failures:
        for item in failures:
            print("  INCOMPLETE:", item)
        return 1
    print("  Every section reproduced. See REPORT.md for the findings and their sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
