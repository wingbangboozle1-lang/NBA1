

## 62. Session `arena/825bb504-nba1` — refresh workflow promotion-gate hardening and run-record observability (claimed 2026-11-17 UTC)

**Board read / conflict check:** Read the board before starting. `gh pr list --state open` measured two open PRs (#152 and #155); inspected their changed-file lists and neither edits `.github/workflows/refresh-data.yml` or a workflow-gate test. No workflow-specific claim appears in the latest completed records. Current checkout is the platform-pinned branch `arena/825bb504-nba1` at `22d56af`; the branch is fixed for this session and will not be renamed or replaced with a session-specific branch.

| Task | Scope | Status |
| --- | --- | --- |
| 62.1 | Make scheduled rebuild conditional explicitly on successful promotion, successful freshness-gate execution, and the gate's `ok=true` output. Preserve fail-closed behavior. | in progress |
| 62.2 | Persist fetch, promotion, freshness, settlement, and build outcomes in the refresh run record; add a focused regression check for workflow guard conditions and record fields. | in progress |
| 62.3 | Run workflow regression and repository verification; record exact outcomes and any limitations here. | unclaimed |

**Files in scope:** `.github/workflows/refresh-data.yml`, `scripts/test_refresh_workflow.py`, and this section of `COORDINATION.md`. No shared site data, source captures, generated pages, or other session files are in scope.

**Observed source state before edits (2026-11-17):** GitHub Actions run [44078416610](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/44078416610) completed successfully, but its step list shows the rebuild was **skipped**. Local `engine/refresh_gate.py --max-age-hours 10` also blocked the committed snapshot: it reported a 24.23-hour-old refresh, five failed fetch/parse checks, stale source checks, and missing/mismatched same-run captures/promotions. This task does not claim to fix the official-source reachability/parsing gaps; it hardens the workflow's gate condition and makes per-run outcomes visible for review. Official-source values will not be fabricated or promoted.
