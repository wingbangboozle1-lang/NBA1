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
| Verified source extracts: (a) official schedule for the 3-day window 2026-11-13 to 2026-11-15 (ET); (b) official NBA injury report rows for 2026-11-13 (04:15 PM version); (c) Netherlands licensing constraint for setting odds; (d) repository irregularities | done (needs integration) | `arena/d3892d13-nba1` | `research/**`, `COORDINATION.md` | No site/index/navigation edits. Integration session decides which dashboard consumes `research/data/*.json`. |
| Site shell, landing page, navigation, README, Pages workflow, final integration and PR/merge | unclaimed (claimed in principle by `4f997533` and `c2b0ebb8`) | — | `index.html`, `README.md`, `.github/workflows/**`, `docs/**`, `data/` | Owned by whichever of the two sessions completes its claim first. Not touched by `d3892d13`. |

## Handoff / conflict log

- 2026-11-13, `d3892d13`: Found two existing claims for the full site task on the remote before starting. Did not start that scope. Claimed `research/**` only. Expect a `COORDINATION.md` conflict at merge time; resolve by keeping every session's rows.
- Irregularity: the task brief asks for `session-<id>/<task>` branch names, but the Arena environment fixes the branch as `arena/<id>-nba1`. Followed the environment.

## Verification log (this session)

- Sources: S1 https://www.nba.com/schedule ; S2 https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf ; S3 https://kansspelautoriteit.nl/ksa-wijst-aanbieders-op-grenzen-vergunning-voor-sportweddenschappen ; S4 https://zoek.officielebekendmakingen.nl/kst-33996-3.html (2014 background only) ; S5 https://api.github.com/repos/wingbangboozle1-lang/NBA1/pages . Full register: `research/data/sources.json`.
- Verification performed: schedule read in full across both page chunks (23 games: Fri 9, Sat 5, Sun 9 match the day headings). Injury report read in full across both PDF chunks (91 rows; 17 with blank team cell → team null, `team_unverified`). Every injury matchup matches a schedule matchup. Counts re-checked with a script. Nothing inferred or filled in.
- Not verified / blank: betting odds and lines; player minutes and rotations; historical results; correlations; any strategy validation; 14–15 Nov injury data (NOT YET SUBMITTED on the report).
- Irregularities: see `research/flags.md` (R1–R8, D1–D7, L1–L3).
- Handoff: the integration session should (1) reconcile the two overlapping site claims, (2) consume `research/data/*.json` for the schedule and injury tables, (3) keep the Ksa constraint (L1–L3) visible on the Flagged for Review page.
