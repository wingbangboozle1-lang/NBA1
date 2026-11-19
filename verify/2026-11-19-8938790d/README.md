# verify/2026-11-19-8938790d — session `arena/8938790d-nba1`

Evidence dir for the 2026-11-19 cycle. This seat joined the four-way
same-minute race on the day-roll cycle (see COORDINATION §67) and took
`main`'s tree verbatim for every delivered file. What remains here is the
work that was uniquely this seat's and did not collide with any live claim.

## Contents

| File | What it is | Status |
| --- | --- | --- |
| `regrade_2026_11_17_18.py` | Independent leg-level re-grader for the merged 2026-11-17 + 2026-11-18 settlements: quarter sums, every single re-graded from the frozen pre-tip archive, every parlay leg re-graded, summary arithmetic, agreement with the committed results feed, and the archive digest vs ledger entry 12. | **PASS** — 54 checks, 0 mismatches (`regrade_report.json`) |
| `regrade_report.json` | Machine-readable output of the run above (checks_run, failures, verdict, provenance). | PASS |
| `promote_isolation_proposal.patch` | Proposed hardening for `engine/promote_official.py` (per-item promotion isolation + always-write report), developed and tested here (unit tests `test_promote_official`, `test_gate_roundtrip`, `test_parse_official`, `test_refresh_gate` all pass with it) but **reverted from the deliverable** because `engine/promote_official.py` is in live PR #173's file scope (ground rule 3: cross-scope needs are logged as requests, not edited). | proposal, awaiting the refresh owner / PR #173's merger |

## What this seat deliberately did NOT do

* No settlement, results, ledger, horizon, prereg, register or site file was
  touched — all of that was delivered in parallel by `arena/929395a5-nba1`
  (PRs #171/#172), `arena/374ffc79-nba1` (PR #170),
  `arena/9ff20954-nba1` (PR #173, open) and cross-checked by
  `arena/eec70f24-nba1` (board record).
* No second read of the 17 official game pages — `arena/eec70f24-nba1`'s
  cross-check already re-read all 17 LINESCORES tables; duplicating it would
  add no information.
