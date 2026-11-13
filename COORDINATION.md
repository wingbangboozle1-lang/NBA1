# Coordination board

Shared task board for parallel agent sessions. Each session works only on its own branch (`arena/<id>-nba1`) and edits only files in its claimed scope.

## Sessions seen on the remote (2026-11-13)

| Session branch | Claimed scope (as written in its claim) | Notes |
|---|---|---|
| `arena/4f997533-nba1` | Audit, source-backed framework, static Pages dashboard, verification, final integration. Files: `COORDINATION.md`, `README.md`, `index.html`, `styles.css`, `app.js`, `data/`, `.github/workflows/` | Claimed the whole task first. |
| `arena/c2b0ebb8-nba1` | Coordination, source-honest decision-support site and review register. Files: `COORDINATION.md`, `README.md`, `docs/**`, `index.html`, `assets/**`, `.github/workflows/**`, `.nojekyll` | Overlaps `4f997533` on `index.html`, `README.md`, `COORDINATION.md`, `.github/workflows/`. |
| `arena/d3892d13-nba1` (this session) | Verified source extracts only. Files: `research/**` and this board | Chosen to avoid overlapping the two claims above. |

## Tasks

| Task | Status | Owner session | File scope | Notes |
|---|---|---|---|---|
| Verified source extracts: (a) official schedule for the 3-day window 2026-11-13 to 2026-11-15 (ET); (b) official NBA injury report rows for 2026-11-13 (04:15 PM ET version); (c) Netherlands licensing constraint for setting odds; (d) repository irregularities | in progress | `arena/d3892d13-nba1` | `research/**`, `COORDINATION.md` | No site/index/navigation edits. Integration session decides which dashboard consumes `research/data/*.json`. |
| Site shell, landing page, navigation, README, Pages workflow, final integration and PR/merge | unclaimed (claimed in principle by `4f997533` and `c2b0ebb8`) | — | `index.html`, `README.md`, `.github/workflows/**`, `docs/**`, `data/` | Owned by whichever of the two sessions completes its claim first. Not touched by `d3892d13`. |

## Handoff / conflict log

- 2026-11-13, `d3892d13`: Found two existing claims for the full site task on the remote before starting. Did not start that scope. Claimed `research/**` only. Expect a `COORDINATION.md` conflict at merge time; resolve by keeping every session's rows.
- Irregularity: the task brief asks for `session-<id>/<task>` branch names, but the Arena environment fixes the branch as `arena/<id>-nba1`. Followed the environment.

## Verification log (this session)

Sources and retrieval method are recorded per row in `research/data/*.json` and in `research/README.md`.
