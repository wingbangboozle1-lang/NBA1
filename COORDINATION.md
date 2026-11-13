# COORDINATION — shared task board for NBA1

Repo: `wingbangboozle1-lang/NBA1`
Base commit: `f73edd2166257df22c91dfb198d27a04cd022c15` (main)
Current date: **2026-11-13** (NBA 2026-27 regular season in progress; season began 2026-10-20).

## Session registry

| Session ID | Branch | Scope | Status |
| --- | --- | --- | --- |
| `arena/91270bb6-nba1` (this session, "integration session") | `arena/91270bb6-nba1` | Entire repo (see note below) | active |

### Deviation note (read this first)

The platform running this session pins work to exactly one branch — `arena/91270bb6-nba1` —
and forbids creating or pushing any other branch. The parallel-session protocol in the brief
asks each session to work on `session-<id>/<task>` branches. **That is not possible here**, so
this session operates as a single-branch integration session: it claims every task below,
keeps each task's files in a disjoint directory (so a later session can still take a task over
without touching another's files), commits frequently, and runs `git pull --rebase` before
every push. If another session starts work, claim a task below by writing your session ID in
the Owner column, commit+push immediately, and keep to that task's file scope.

## Task board

Statuses: `unclaimed` · `in progress` · `done` · `needs review`

| # | Task | Files (scope) | Owner | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| T1 | Repo review + coordination board | `COORDINATION.md`, `README.md`, `REPO_REVIEW.md` | `arena/91270bb6-nba1` | done | Repo contained a single 6-byte `README.md` ("# NBA1") at base commit. Nothing to verify line-by-line; see `REPO_REVIEW.md`. |
| T2 | Official data capture (raw snapshots) | `data/raw/*.json`, `data/raw/sources.json` | `arena/91270bb6-nba1` | done | Every file records the exact official URL + capture timestamp. No value is inferred. |
| T3 | Line-origination engine (spread / total / moneyline / player props) | `engine/model_core.py` | `arena/91270bb6-nba1` | done | Pure Python, stdlib only. |
| T4 | Strategy library (singles, parlays, SGPs, prop combos) | `engine/strategies.py` | `arena/91270bb6-nba1` | done | 10 strategies, each with explicit bet-selection rule + gate set. |
| T5 | Validation gates, out-of-sample backtest, luck decomposition | `engine/validate.py`, `docs/data/validation.json` | `arena/91270bb6-nba1` | done | Holdout = 2026-11-09 → 2026-11-12 (28 games), ratings fitted on 2026-10-20 → 2026-11-05 only. |
| T6 | Correlation study | `engine/correlate.py`, `docs/data/correlations.json` | `arena/91270bb6-nba1` | done | Team-level correlations are computed from official data; parlay/SGP correlations are model-derived and flagged. |
| T7 | Leaderboard + reward tiers | `engine/leaderboard.py`, `docs/data/leaderboard.json` | `arena/91270bb6-nba1` | done | Composite score, transparent formula, on the Validation page. |
| T8 | Injury / rotation-minutes / game-flow module | `engine/injuries.py`, `docs/data/injuries.json`, `docs/data/gameflow.json` | `arena/91270bb6-nba1` | done | Lower-bound impact only (top-50 minute coverage). Flagged. |
| T9 | Site build (GitHub Pages, landing + subpages + JSON data) | `docs/**` | `arena/91270bb6-nba1` | done | Static, no build step, `.nojekyll`. |
| T10 | Daily refresh automation | `.github/workflows/refresh-data.yml`, `engine/fetch_official.py` | `arena/91270bb6-nba1` | done | **Caveat:** `fetch_official.py` could not be executed in this sandbox (outbound network restricted to github.com / npm / pypi). It is written defensively and the workflow uses `continue-on-error`, so a failure never breaks Pages. See Flagged for Review #F7. |
| T11 | Suggestions + Open Questions pages | `docs/data/suggestions.json`, `docs/data/questions.json` | `arena/91270bb6-nba1` | done | Decision-path format: option, cost, risk, unlocks. |
| T12 | Flagged-for-review register | `docs/data/flagged.json`, `docs/pages/flagged.html` | `arena/91270bb6-nba1` | needs review | Every item carries a source link. |
| T13 | Executive summary | `docs/index.html` | `arena/91270bb6-nba1` | done | Landing page. |
| T14 | Final integration: re-verify combined data, link check, PR, merge, Pages deploy | whole repo | `arena/91270bb6-nba1` | in progress | Runs at the end of this session. |

## Handoff / takeover rule

If a task's Owner has produced no commit for more than 60 minutes, any session may take it over:
set Owner to your session ID, change Status to `in progress`, and add a line to the log below
describing the handoff. Never delete a previous session's rows or files to "clean up" —
superseded work is marked `needs review` and published on the Flagged for Review page instead.

## Log

| Timestamp (UTC) | Session | Entry |
| --- | --- | --- |
| 2026-11-13 | `arena/91270bb6-nba1` | Board created. Claimed T1–T14 as single-branch integration session (see deviation note). |
| 2026-11-13 | `arena/91270bb6-nba1` | T2 done — 7 raw snapshots captured from nba.com / official.nba.com / ak-static.cms.nba.com. Sources recorded in `data/raw/sources.json`. |
| 2026-11-13 | `arena/91270bb6-nba1` | T3–T9, T11, T13 done — engine + site generated; all computed values trace to a raw snapshot row. |
| 2026-11-13 | `arena/91270bb6-nba1` | T12 done — 10 irregularities flagged, all with source links; none block the merge. |
