# arena/4eef6d3b-nba1 — section 78 verification report (2026-11-19)

## The three defects (all reproduced before fixed)

1. Publish staging: compound `git add` with three never-existing paths aborted
   staging of every promoted input (local git reproduction: nothing re-staged).
   Live consequence measured on `auto/refresh-2026-11-19-120839` (run record says
   promoted; commit contains none of the files).
2. Settle step: `bash -eo pipefail` abort at `settle_slate` exit 3 before the
   step's own tolerance ran (run 44520339923 annotation "Process completed with
   exit code 3"; reproduced exactly).
3. S1/S2 runner-unobtainable + unsatisfiable gate compare (§69 byte evidence;
   `team_advanced.json` had no verification block at all).

## The rehearsal that caught this seat's own bug

Local full-chain simulation (worktree, promote → gate → pipeline → build_site)
before any push caught `KeyError: 'ortg'`: the first re-cut wrote
`team_advanced.json` in recut column names instead of `parse_official.ADVANCED_COLS`.
Fixed and re-measured before pushing.

## T07 — scheduled rebuild executed (run 44527302396, branch push, record ac6c3b6)

fetch 12:49:05Z · promote success (0 blocked) · freshness_ok TRUE (5 declarations
surfaced) · settle SUCCESS (first ever with an incomplete newest window) ·
**build_outcome SUCCESS — first rebuild execution since 2026-11-15T12:43:11Z** ·
gate blocking_errors [].

## Re-cut gates (scripts/recut_2026-11-19_4eef6d3b.py)

G1 pass 30/30 · G2 pass 30/30 · G3 pass 30/30 (was FAIL: LAL/UTA) · G4 pass
444 = 2x222 (was FAIL: one-game lag) · G5 pass. Drift vs baseline b8cf2cb:
exactly 2 rows (LAL, UTA 15→16 GP). UTA OppPTS 116.0 confirmed (F-89F-04).

## Gate battery on the merged tree (this merge commit)

| Gate | Result |
| --- | --- |
| unit suite (18 files, CI dispatch logic) | 0 failing |
| scripts/verify_all.py | VERIFY OK (FAILURES: 0) |
| scripts/check_site.py | PASS |
| scripts/check_links.py | RESULT: PASS |
| scripts/check_registers.py | 2,282 fields, 0 problems |
| scripts/verify_ledger.py | ledger chain OK |
| scripts/check_build_data.py | RESULT: PASS |
| scripts/verify_dashboard.py | VERIFY OK |
| scripts/check_rendered.py | RESULT: PASS |
| scripts/verify_integration.py | PASSED (no errors) |
| node scripts/render_check.mjs | 167 pages, 13,133 content blocks, 0 problems |

## Collision record (COORDINATION.md section 78.0)

Parallel sessions fb91550a/65bda668/232a9f86/7b8d624a/994186ba merged PRs
#194–#203 during this session's work window; two of them also used the "§74"
number. Resolution table in section 78.0; this seat's record renumbered §78;
main's board kept verbatim; register union by id (188 items, 0 duplicates);
their staging loop ships with this seat's behavioral tests; their gate fixes
ship with this seat's session-verified 72h freshness check; this seat's
settle fix and model-input re-cut are unique and ship as-is.
