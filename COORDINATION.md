# Coordination board

This repository had no coordination board or other active task claims at session start. The current Arena-managed branch `arena/0684edd4-nba1` is fixed for this session; no other branches/worktrees are created.

| Task | Status | Owner | File scope |
|---|---|---|---|
| Build verified NBA lines research/dashboard, methodology, decision questions, and review flags | done | arena session (current session) | `index.html`, `styles.css`, `app.js`, `README.md`, `COORDINATION.md`, `.github/workflows/pages.yml` |

## Source and verification log
- Official NBA Stats glossary: https://www.nba.com/stats/help/glossary (fetched and checked; official stats terms).
- NBA Stats FAQ: https://www.nba.com/stats/help/faq; team/player stats https://www.nba.com/stats/teams/advanced and https://www.nba.com/stats/players; schedule https://www.nba.com/schedule.
- Current official injury report page verified at https://official.nba.com/nba-injury-report-2026-27-season/ (fetched; report cadence described there). No report data ingested.
- Verification: internal HTML anchors checked (none broken); source links added to displayed research rows; `git diff --check` passed; static HTTP requests for `/`, `/index.html`, `/styles.css`, `/app.js` returned 200; GitHub Pages deployment workflow 43518760512 completed successfully; public URL https://wingbangboozle1-lang.github.io/NBA1/.
- PR #1 https://github.com/wingbangboozle1-lang/NBA1/pull/1 merged 2026-11-13 (merge commit).

## Irregularities
- Initial repository contained only a six-byte README; no application, data, task board, or existing source material was present. No verified current-game, injury, odds, or historical bet dataset is available, so none will be invented.
- No additional agent session/claim information is available in this checkout; this work is scoped to the current Arena branch.

---

# Session arena-83ba89cf — task board (added after merge with main)

Session `arena-83ba89cf` works on branch `arena/83ba89cf-nba1` (base `f73edd2`). It merged `origin/main` (PRs #1 and #2 from `arena/0684edd4-nba1`) on 2026-11-13 and kept that session's root dashboard unchanged.

**Coordination log**
- 2026-11-13: `main` gained the root dashboard and Pages workflow from `arena/0684edd4-nba1` after this branch was cut. Merge conflicts were in `COORDINATION.md` and `README.md` only. Resolution: both sections kept, nothing from the other session deleted. Merge commit used instead of rebase because the conflict had to be resolved once for both sides.
- Scope split: the other session owns the root (`index.html`, `styles.css`, `app.js`, `README.md`, `.github/workflows/pages.yml`). This session owns `data/`, `scripts/`, `docs/`, and its own sections of this file.
- Request logged (not implemented): two landing pages now exist (root "NBA Edge Lab" and this session's `docs/` site). Consolidating them into one landing page needs your decision; see Suggestion S-11 on the Suggestions page.

Repo: `wingbangboozle1-lang/NBA1` · Working branch: `arena/83ba89cf-nba1` (base `main` @ `f73edd2`)
Session ID: `arena-83ba89cf` (single session running this board; no parallel sessions were detected in this checkout)

Status values: `unclaimed` · `in progress` · `done` · `needs review` (published on the Flagged for Review page; does not block) · `blocked`

Rule applied to every table row: a value that could not be confirmed from an official source is left blank and flagged. Nothing is inferred and filled in silently.

## Task board

| ID | Task | Status | Owner | Files touched | Notes |
|----|------|--------|-------|---------------|-------|
| T1 | Repo review (structure, files, irregularities) | done | arena-83ba89cf | COORDINATION.md, data/flags.json | Repo held only `README.md` ("# NBA1") and one commit. See Flags F-01..F-03. |
| T2 | Upcoming slate, Nov 13–15 2026 (3-day window) | done | arena-83ba89cf | data/games.json | 23 games from official NBA games pages. Records as displayed at retrieval. |
| T3 | Injury report, game-day 11/13/26 12:00 PM | done (with flags) | arena-83ba89cf | data/injuries.json | 75 rows with team attribution. Rows missing a reason or team are flagged, not filled in. Rotation-minute impact NOT computed (no verified minutes data). |
| T4 | Strategy framework + validation gates (single, parlay, prop combos) | done (framework only) | arena-83ba89cf | data/strategies.json | No leaderboard results. No verified line or game-log dataset was available. |
| T5 | Correlation values, originated lines, picks | blocked | arena-83ba89cf | — | Blocked: no verified historical game logs, player props, or odds source. Nothing generated. See Q-06..Q-09. |
| T6 | Executive summary | done | arena-83ba89cf | data/summary.json | |
| T7 | Improvement suggestions (decision list, no changes made) | done | arena-83ba89cf | data/suggestions.json | Nothing implemented until you choose. |
| T8 | Questions / answered / unanswered | done | arena-83ba89cf | data/questions.json | |
| T9 | GitHub Pages site (landing + category subpages) | done | arena-83ba89cf | scripts/build_site.py, docs/** | Static, generated from data/*.json. Build validates source links and internal links. |
| T10 | Integration: build, link check, PR, merge, Pages deploy | in progress | arena-83ba89cf | — | See the Integration log below. |

## Sources used (all official unless marked)

| ID | Source | URL | Used for |
|----|--------|-----|----------|
| S1 | NBA.com games page, 2026-11-13 | https://www.nba.com/games?date=2026-11-13 | T2 schedule, records |
| S2 | NBA.com games page, 2026-11-14 | https://www.nba.com/games?date=2026-11-14 | T2 schedule, records |
| S3 | NBA.com games page, 2026-11-15 | https://www.nba.com/games?date=2026-11-15 | T2 schedule |
| S4 | NBA injury report, 11/13/26 12:00 PM (PDF) | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf | T3 injuries |
| S5 | NBA Official — injury report rules and submission times | https://official.nba.com/nba-injury-report-2026-27-season/ | T3 method |
| S6 | Kansspelautoriteit (Ksa) home page | https://kansspelautoriteit.nl/ | T8 legal context |
| S7 | Ksa — Online kansspel aanbieden | https://kansspelautoriteit.nl/online-kansspel-aanbieden | T8 legal context |
| S8 | GitHub Docs — configuring a Pages publishing source | https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site | T9 deploy method |

Also consulted and NOT used for any values: `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` (HTTP 500 on fetch) and `https://www.nba.com/stats/teams/traditional` (partial page, team-level stats not extracted in full).

## Integration log

- Claimed T1–T10 in this file, commit `claim: T1–T10 arena-83ba89cf`.
- Each task's sources and verification are recorded in the Sources table and the "Verification" section below.
- Integration (T10) steps: build the site with `python3 scripts/build_site.py`, which fails on rows without a source link, on unknown source IDs, and on broken internal links. Then open a PR to `main`, merge with a merge commit, and confirm the GitHub Pages build status.

## Verification performed

- Schedule: 9 games on 11/13, 5 on 11/14, 9 on 11/15, matching the day counts shown in the official NBA games calendar (S1 header: 9, 5, 9 for 13, 14, 15). Times are as printed (ET).
- Injury rows: each row copied from the S4 PDF text. Team attribution is taken from the team name printed on the row. Matchup is taken from the printed matchup where present, otherwise implied by the official schedule (every team plays exactly one game on 11/13, so the implication is unambiguous). Reason is copied only where printed.
- Two text-extraction issues in S4 were not resolved and are listed as flags.

## Flagged for review (summary; full list on the site)

See `data/flags.json`. Highlights:
- F-02: 7 injury rows (Golden State Warriors and Fox, De'Aaron) have no printed reason in the extracted text.
- F-03: 14 injury rows have no printed team, so they are excluded from the table.
- F-04: 75 injury rows are text-extracted from a PDF. Spot-check against the PDF before relying on them.
- F-05: 9 rows dated 11/14 are "NOT YET SUBMITTED" and are excluded.

## Pull request

- PR: https://github.com/wingbangboozle1-lang/NBA1/pull/5 (`arena/83ba89cf-nba1` → `main`)
- Local verification before PR: `python3 scripts/build_site.py` → built 10 pages; games=23, injuries=75, flags=14; no build errors, no broken internal links.
- Merge result and Pages deploy status: recorded on PR #5 (see its comments).

---

# Session arena-c2b0ebb8-nba1 — coordination and review log

## Branch/rebase coordination
- This branch was cut from `f73edd2` before the other dashboard sessions' work landed. The initial checkout had no `COORDINATION.md`; a claim commit and duplicate site PR #3 were created before remote `main` advanced.
- On 2026-11-13, remote `main` advanced through PRs #1, #2, and #5 while this branch's PR #3 was open. The PR became conflicting because it changed the same shared landing page, README, Pages workflow, and coordination file.
- Conflict resolution: rebased this branch onto `origin/main` (`792cbc3`) and kept the existing integrated versions of `index.html`, `README.md`, `.github/workflows/pages.yml`, and `COORDINATION.md`. The duplicate assets/docs/checker authored on this branch were discarded; no upstream session work was removed. PR #3 must be closed as superseded, not merged.

## Integration review request — no shared site files edited
- Request to session `arena-83ba89cf` / T10 owner: audit the root landing page's table-source requirement before marking integration fully verified. A read-only parser of `origin/main:index.html` found 25 table data rows; 16 rows (1-based indices 6–17, 20, 22, 24, 25) did not contain an HTTPS link to an official NBA domain. The inspection was read-only; no root site, `docs/`, `data/`, or `scripts/` file was edited in this session.
- Please add a verified official source link to every factual table row, or explicitly make a row non-factual/proposal outside a data table; add this omission to the site's Flagged for Review list; then rerun the existing source/link validator against all pages that are published. This request is not itself a verification of the unsupported rows.
- Public official references manually checked during this session: [NBA schedule](https://www.nba.com/schedule), [NBA Stats glossary](https://www.nba.com/stats/help/glossary), [NBA official injury-report policy](https://official.nba.com/nba-injury-report-2026-27-season/), [NBA rulebook](https://official.nba.com/rulebook/). These pages do not substantiate all 16 rows; they are review starting points only.
- PR #5 and subsequent Pages workflows are merged/successful, but the coordination board still lists T10 as `in progress`; please update it after checking the source-row issue and current deployment. Current site URL: https://wingbangboozle1-lang.github.io/NBA1/.
