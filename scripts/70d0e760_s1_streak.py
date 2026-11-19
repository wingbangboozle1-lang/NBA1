#!/usr/bin/env python3
"""Measure the S1_season/S2_train runner-side parse streak from committed history.

COORDINATION.md section 77.3: the declaration admission rule needs evidence
that the S1/S2 parse failure is terminal for the RUNNER rather than a
transient timeout. This script reads `data/raw/_last_refresh.json` out of
every commit that ever touched it (the same method section 73.8 established
for rebuild history) and reports, per committed run record: the capture
timestamp, whether S1_season and S2_train appear in the record's `failed`
list, and whether either ever produced a parsed payload. The output is the
`data/raw/session-70d0e760/s1_parse_streak.json` artifact the declaration
cites. Nothing here is typed by hand.

Refuses to answer from a shallow clone: history counts are the whole point.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.environ.get("NBA1_REPO_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "session-70d0e760", "s1_parse_streak.json")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def unshallowed() -> bool:
    out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return out == "false"


def main() -> int:
    if not unshallowed():
        print("SHALLOW CLONE: history counts are not trustworthy; "
              "run `git fetch --unshallow origin` first")
        return 2
    commits = git("log", "--all", "--format=%H", "--",
                  "data/raw/_last_refresh.json").split()
    records = []
    for sha in commits:
        try:
            blob = git("show", f"{sha}:data/raw/_last_refresh.json")
        except subprocess.CalledProcessError:
            continue
        try:
            rec = json.loads(blob)
        except ValueError:
            continue
        failed_keys = {entry[0] for entry in rec.get("failed", [])
                       if isinstance(entry, (list, tuple)) and entry}
        checks = {c.get("key"): c for c in rec.get("source_checks", [])
                  if isinstance(c, dict)}
        records.append({
            "commit": sha,
            "captured_at_utc": rec.get("captured_at_utc"),
            "S1_season_failed": "S1_season" in failed_keys,
            "S2_train_failed": "S2_train" in failed_keys,
            "S1_http_status": (checks.get("S1_season") or {}).get("http_status"),
            "S2_http_status": (checks.get("S2_train") or {}).get("http_status"),
        })
    records.sort(key=lambda r: str(r["captured_at_utc"]))
    s1_fail = [r for r in records if r["S1_season_failed"]]
    s2_fail = [r for r in records if r["S2_train_failed"]]
    s1_checked = [r for r in records if r["S1_http_status"] is not None]
    s1_ok_200 = [r for r in s1_checked if r["S1_http_status"] == 200]
    streak = {
        "title": "S1_season / S2_train runner-side parse streak",
        "measured_by": "scripts/70d0e760_s1_streak.py",
        "purpose": ("Declaration evidence for data/raw/unreadable_sources.json "
                    "(COORDINATION.md section 77): proves the S1/S2 parse "
                    "failure is terminal for the GitHub Actions runner "
                    "(every committed run record since the first failure) "
                    "rather than a transient timeout."),
        "method": ("data/raw/_last_refresh.json read from every commit that "
                   "ever touched it; a run counts as a parse failure when the "
                   "source key appears in the record's failed[] list."),
        "commits_touching_record": len(commits),
        "records_parsed": len(records),
        "s1_records_with_parse_failure": len(s1_fail),
        "s2_records_with_parse_failure": len(s2_fail),
        "s1_records_checked_http": len(s1_checked),
        "s1_records_http_200": len(s1_ok_200),
        "first_record_utc": records[0]["captured_at_utc"] if records else None,
        "last_record_utc": records[-1]["captured_at_utc"] if records else None,
        "first_failure_utc": s1_fail[0]["captured_at_utc"] if s1_fail else None,
        "last_failure_utc": s1_fail[-1]["captured_at_utc"] if s1_fail else None,
        "records": records,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(streak, fh, indent=1)
        fh.write("\n")
    print(f"wrote {OUT}")
    print(json.dumps({k: v for k, v in streak.items() if k != "records"},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
