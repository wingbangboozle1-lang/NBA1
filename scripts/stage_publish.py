#!/usr/bin/env python3
"""Existence-checked git staging for the scheduled refresh's publish step.

Why this exists (COORDINATION.md section 77.1, measured 2026-11-19):

    git add a.json missing.json b.json   ->  stages NOTHING AT ALL

git aborts the whole add on the first unmatched pathspec, and the publish
step's multi-pathspec ``git add`` listed ``data/raw/standings.json`` - a file
that has never existed in the repository's history. ``2>/dev/null || true``
hid the fatal error, so every verified promotion of every scheduled run was
silently discarded while the run record claimed ``promoted``. The committed
``schedule_upcoming.json`` sat three days stale, ``injuries.json`` two
editions stale, and the freshness gate correctly refused them ("promoted
input is not verified against this run's capture") run after run.

This helper stages each path individually, skipping paths that do not exist
and expanding globs itself, so one missing file can never discard the rest.
It reports what it staged and what was absent, and exits 0 either way: the
caller decides whether anything was staged via ``git diff --cached``.

Usage:
    python3 scripts/stage_publish.py evidence    # captures, PDFs, settlement, ledger
    python3 scripts/stage_publish.py promoted    # promoted snapshots + parsed records
    python3 scripts/stage_publish.py derived     # the rebuild's committed outputs
    python3 scripts/stage_publish.py record      # the run record itself

Standard library only.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys

# Each mode lists the paths the publish step may stage. Paths are matched
# per-file: a missing path is reported and skipped, never fatal.
EVIDENCE = [
    "data/raw/_capture_*.json",
    "data/raw/injury_pdfs/",
    "data/settlement/",
    "data/ledger/ledger.json",
]

PROMOTED = [
    "data/raw/standings.json",
    "data/raw/team_traditional.json",
    "data/raw/team_opponent.json",
    "data/raw/team_advanced.json",
    "data/raw/unreadable_sources.json",
    "data/raw/refresh_path_audit.json",
    "data/raw/schedule_upcoming.json",
    "data/raw/injuries.json",
    "data/raw/games_completed.json",
    "data/raw/sources.json",
    "data/parsed/",
]

DERIVED = [
    "data/hca_measured.json",
    "data/derived/",
]

RECORD = [
    "data/raw/_last_refresh.json",
]

MODES = {
    "evidence": EVIDENCE,
    "promoted": PROMOTED,
    "derived": DERIVED,
    "record": RECORD,
}


def expand(path: str, root: str) -> list[str]:
    """Expand one entry to concrete files that exist under root."""
    if any(ch in path for ch in "*?["):
        matches = sorted(glob.glob(os.path.join(root, path)))
        return [os.path.relpath(p, root) for p in matches if os.path.exists(p)]
    full = os.path.join(root, path)
    if os.path.isdir(full):
        out = []
        for base, _dirs, files in os.walk(full):
            for name in files:
                out.append(os.path.relpath(os.path.join(base, name), root))
        return sorted(out)
    if os.path.exists(full):
        return [path]
    return []


def stage(paths: list[str], root: str, add=None) -> tuple[list[str], list[str]]:
    """Stage every existing file individually. Returns (staged, absent)."""
    if add is None:
        def add(args):
            subprocess.run(["git", "add", "--"] + args, cwd=root, check=True)

    staged, absent = [], []
    for entry in paths:
        files = expand(entry, root)
        if not files:
            absent.append(entry)
            continue
        # One add call per concrete file: git aborts atomically on an
        # unmatched pathspec, so batching is exactly the defect this module
        # exists to remove.
        for rel in files:
            add([rel])
            staged.append(rel)
    return staged, absent


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in MODES:
        print(__doc__)
        return 2
    root = os.environ.get("NBA1_REPO_ROOT") or os.getcwd()
    staged, absent = stage(MODES[argv[1]], root)
    print(f"stage_publish[{argv[1]}]: {len(staged)} file(s) staged")
    for rel in staged:
        print(f"  + {rel}")
    for entry in absent:
        print(f"  - absent, skipped: {entry}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
