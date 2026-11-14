# COORDINATION — shared task board for NBA1

Repo: `wingbangboozle1-lang/NBA1`
Base commit for both builds: `f73edd2166257df22c91dfb198d27a04cd022c15` (`main`)

---

## ⚠ Read this first: two sessions, two builds, one repository

Two sessions worked on this repository in parallel without seeing each other's
claims, because each created `COORDINATION.md` from scratch (the file did not
exist at the base commit, so neither could read the other's board). Both built a
complete implementation of the same brief, and **both publish to `docs/`**.

| | Build A | Build B |
| --- | --- | --- |
| Session ID | `arena-7cfd203a` | `arena/91270bb6-nba1` |
| Branch | `arena/7cfd203a-nba1` | `arena/91270bb6-nba1` |
| Merged via | PR #15, PR #17 | PR #16 (this merge) |
| Entry point | `index.html` (repository root) | `docs/b/index.html` |
| Publish root for Pages | `.` (repository root) | `.` (same — B lives at `/docs/b/`) |
| Site data | `data/*.json`, `data/derived/*.json` | `docs/data/*.json` |
| Code | `scripts/*.py`, `app.js` | `engine/*.py`, `docs/assets/site.js` |
| Raw snapshots | `data/*.json`, `data/injuries_0515.json`, … | `data/raw/*.json`, `data/content/*.json` |
| Out-of-sample window | 14 finished games (floor 100) | **51** games, all after the ratings cut-off |
| Strategies | 8, six conjoined gates, **0 validated** | 10, seven gates, **0 funded** (all capped at quarter-unit) |
| Headline | "Look-ahead contaminated; the gates were left alone and the failure is reported." | "Model ahead on margin, behind on totals and winners; one strategy at 16-7 with p = 0.093 — not enough." |

**Both are preserved.** Neither was deleted, renamed or overwritten.

### The collision and how it was resolved

Eleven paths collided exactly:

```
docs/index.html
docs/pages/backtest.html      docs/pages/correlations.html
docs/pages/flagged.html       docs/pages/gameflow.html
docs/pages/injuries.html      docs/pages/lines.html
docs/pages/picks.html         docs/pages/questions.html
docs/pages/sources.html       docs/pages/suggestions.html
```

Resolution: **Build B moved to `docs/b/`.** Build A's root dashboard links to
`docs/index.html`, `docs/injuries.html`, `docs/flagged.html` and
`docs/sources.html`, so keeping A's paths intact is what keeps its links
working. B's entry point is `docs/b/index.html`; its pages are at
`docs/b/pages/`; its assets (`docs/assets/site.css`, `site.js`) and data
(`docs/data/`) never collided and are shared from `docs/`.

`.gitignore`, `README.md`, `COORDINATION.md` and
`.github/workflows/pages.yml` also collided and were merged (both sides kept,
nothing discarded).

**Cross-session request (logged, not executed):** Build B is not linked from
Build A's root dashboard. Adding a single nav entry —
`<a href="docs/b/index.html">◈ &nbsp; Second build: backtested desk</a>` under
the `DETAIL PAGES` heading of `index.html` — would make it discoverable. That
file is owned by session `arena-7cfd203a` and was not edited.

---

## 0. Ground rules

1. A task is `unclaimed`, `in progress`, `done`, or `needs review`.
2. `needs review` means the item is published on a **Flagged for Review** page and
   **does not block** anything.
3. Each task lists the **file scope** it owns. No session edits outside its
   scope; cross-scope needs are logged as *requests* (see §4).
4. Claims are committed and pushed immediately after writing.
5. A claim older than 60 minutes with no commits may be taken over by another
   session (handoff logged in §5).
6. Share the board: if `COORDINATION.md` exists, **read it and add a row before
   starting anything**. Both sessions here failed to do that only because the
   file did not yet exist.

---

## 1. Task board — Build A (`arena-7cfd203a`)

| # | Task | Status | File scope | Notes |
| --- | --- | --- | --- | --- |
| T01 | Repo audit + coordination board | done | `COORDINATION.md`, `README.md`, `notes/` | Repo was empty (README stub only). |
| T02 | Verified data acquisition | done | `data/*.json`, `data/*.csv` | All rows carry an official `source_url`. |
| T03 | Line origination engine | done | `scripts/originate_lines.py`, `data/derived/lines.json` | HCA unavailable from official sources → flagged. v2 measured dispersion from 14 real finals (total sd 17.13, margin sd 16.13) after v1 produced ±30 spreads from a guessed sd. |
| T04 | Correlation model + empirical checks | done | `scripts/compute_correlations.py`, `data/derived/correlations.json` | SGP table labelled by derivation type. |
| T05 | Validation gates + strategy leaderboard | done | `scripts/strategies.py`, `data/derived/strategies.json`, `docs/pages/strategies.html`, `docs/pages/gates.html` | 8 strategies, 6 conjoined gates → **0 validated**. Null control passes 4/6, documented as a gate-calibration finding. No gate was loosened. |
| T06 | Injury / rotation / game-flow analysis | done | `scripts/injury_impact.py`, `data/player_absence_evidence.json`, `data/derived/injury_impact.json` | Season stats already contain past absences, so only `NEW_ABSENCE` players move a line. 9 players individually verified; 79 of 88 report rows have no verified minutes. |
| T07 | Open-questions register | done | `docs/pages/questions.html` | known / unknown / how to obtain. |
| T08 | Improvement suggestions register | done | `docs/pages/suggestions.html` | effort / impact / trade-off. |
| T09 | Executive summary | done | `docs/pages/summary.html` | |
| T10 | Static site build | done | `docs/**`, `scripts/build_site.py` | 14 pages, 486 table rows, every one carrying an official source link. |
| T11 | Link + provenance verification | done | `scripts/verify_data.py`, `scripts/verify_inline.py`, `scripts/check_links.py` | `verify_data.py` 15 checks / 0 errors; `verify_inline.py` 18/18; `check_links.py` 0 broken, 0 bad hosts, 0 unsourced rows. |
| T12 | Integration + publish | done | merge → `main`, Pages settings | PR #15 + #17. |

## 2. Task board — Build B (`arena/91270bb6-nba1`)

| # | Task | Status | File scope | Notes |
| --- | --- | --- | --- | --- |
| U01 | Repo review + coordination board | done | `COORDINATION.md`, `REPO_REVIEW.md` | Line-by-line review of the base commit: one 6-byte `README.md`, nothing else. No irregularities found. |
| U02 | Official data capture | done | `data/raw/*.json` | 6 verbatim snapshots, each with its URL and capture time. 37 sources registered. |
| U03 | Line-origination engine | done | `engine/model_core.py` | Additive efficiency model + empirical-Bayes shrinkage (derived k = 2.9 with a fixed-k sweep) + HCA + B2B + availability. |
| U04 | Strategy library | done | `engine/strategies.py` | 10 strategies: singles, parlays, SGPs, prop combos. |
| U05 | Validation gates + backtest | done | `engine/validate.py`, `docs/data/validation.json` | 51 out-of-sample games, ratings from 10/20–11/05 only. 7 gates. |
| U06 | Correlation study | done | `engine/correlate.py`, `docs/data/correlations.json` | 13 measured pairs on n = 30; parlay/SGP values labelled MODEL-DERIVED. |
| U07 | Leaderboard + reward tiers | done | `engine/leaderboard.py` | Composite score with a hard cap: failing G4 or not passing G1 blocks promotion past Tier 3 regardless of score. |
| U08 | Injury / rotation / game flow | done | `engine/injuries.py`, `docs/data/injuries.json`, `docs/data/gameflow.json` | Impact is a measured lower bound; minutes-coverage column published beside every figure. |
| U09 | Site build | done | `docs/b/**`, `docs/data/`, `docs/assets/site.*` | 17 pages, static, no build step. |
| U10 | Daily refresh automation | done | `.github/workflows/refresh-data.yml`, `engine/fetch_official.py` | **Never executed** — written in a sandbox with outbound network restricted to github.com/npm/pypi. The workflow uses `continue-on-error`, so a failure leaves the last snapshot live. Flagged F7. |
| U11 | Suggestions + open questions | done | `data/content/suggestions.json`, `data/content/questions.json` | Decision-path format: option, effort, risk, unlocks, recommendation. |
| U12 | Flagged-for-review register | needs review | `data/content/flagged.json`, `docs/b/pages/flagged.html` | 12 items, each with an official source link. |
| U13 | Executive summary | done | `docs/b/index.html` | |
| U14 | Integration + publish | in progress | whole repo | Merging, re-verifying, confirming the build, publishing Pages. |

## 3. Combined verification (integration pass, `arena/91270bb6-nba1`)

Run on the merged tree:

| Check | Result |
| --- | --- |
| All 17 build-B site data files present and valid JSON | pass |
| Internal link check across **all** HTML in the repository (both builds) | **0 broken** |
| Build-B pages render with data (headless DOM, every page loaded) | 17 / 17 ok |
| Inline script syntax check (node `vm.Script`) | 0 errors |
| External links: all HTTPS, all on `*.nba.com` | pass |

Build A's own gates (`scripts/check_site.py`, `verify_data.py`,
`verify_inline.py`, `check_links.py`) were left in place and still run in CI.

### Numbers that changed when Build B's window grew from 28 to 51 games

| Metric | 28 games | 51 games |
| --- | --- | --- |
| Margin MAE (model / reference) | 12.56 / 12.72 | 12.89 / 13.19 |
| Total MAE (model / reference) | 14.50 / 14.75 | 14.86 / 14.75 |
| Straight up (model / reference) | 20-8 / 21-7 | 37-14 / 37-14 |
| Brier (model / reference) | 0.1992 / 0.1893 | 0.1970 / 0.1889 |

The totals conclusion **flipped**. That is recorded here as the strongest
available argument for not promoting anything on a small window.

## 4. Cross-session requests (logged, not executed)

| # | From | To | Request | Why not done |
| --- | --- | --- | --- | --- |
| R1 | `arena/91270bb6-nba1` | `arena-7cfd203a` | Add a nav link to `docs/b/index.html` from the root dashboard's `DETAIL PAGES` list | `index.html` is owned by Build A. An integration session may add it. |
| R2 | `arena/91270bb6-nba1` | `arena-7cfd203a` | Consider adopting Build B's 51-game out-of-sample log (`docs/data/backtest.json`) to lift Build A past its 14-game sample floor | Different data model; needs a deliberate port, not a copy. |
| R3 | `arena/91270bb6-nba1` | `arena-7cfd203a` | Build A's `data/players_minutes_2026_27.json` may close Build B's F2 gap (minutes known for only 50 of 465 players) | Needs verification that every row traces to an official source before Build B consumes it. |

## 5. Log

| Timestamp (UTC) | Session | Entry |
| --- | --- | --- |
| 2026-11-13 | `arena-7cfd203a` | Board created from scratch (file did not exist). Claimed T01–T12. |
| 2026-11-13 | `arena-7cfd203a` | T03 v1 produced ±30 spreads from a guessed sd; replaced with sd measured from 14 real finals. |
| 2026-11-13 | `arena-7cfd203a` | T05: 8 strategies × 6 conjoined gates → 0 validated. Null control passes 4/6 gates — recorded as a calibration finding, gates not loosened. |
| 2026-11-13 | `arena-7cfd203a` | PR #15 and PR #17 merged into `main`. |
| 2026-11-13 | `arena/91270bb6-nba1` | Board created from scratch (file did not exist at the base commit). Claimed U01–U14. |
| 2026-11-13 | `arena/91270bb6-nba1` | U02: 6 raw snapshots captured from nba.com / official.nba.com / ak-static.cms.nba.com. |
| 2026-11-13 | `arena/91270bb6-nba1` | Out-of-sample window extended 28 → 51 games by capturing 2026-11-06 and 2026-11-07 results. Totals conclusion flipped. |
| 2026-11-13 | `arena/91270bb6-nba1` | 2026-11-07 DEN@IND identified as a neutral-site game (NBA Mexico City Game); HCA zeroed for it. Flagged F12. |
| 2026-11-13 | `arena/91270bb6-nba1` | **CONFLICT detected.** `main` had moved on with `arena-7cfd203a`'s build; 15 paths collided. Stopped, did not discard either side. |
| 2026-11-13 | `arena/91270bb6-nba1` | **CONFLICT resolved.** Build B namespaced to `docs/b/`; Build A's paths kept intact so its links keep working; `.gitignore`, `README.md`, `COORDINATION.md` and `pages.yml` merged with both sides kept. |
| 2026-11-13 | `arena/91270bb6-nba1` | Combined verification re-run on the merged tree: 0 broken internal links across all HTML, 17/17 Build-B pages render, all Build-B data valid. |
| 2026-11-13 | `arena/91270bb6-nba1` | Cross-session requests R1–R3 logged rather than executed. |
| 2026-11-13 | `arena/91270bb6-nba1` | PR #16 merged into `main` without waiting for approval, as instructed. Merge commit `eef5117`. |
| 2026-11-13 | `arena/91270bb6-nba1` | **Pages deploy confirmed.** Workflow `Publish static site to GitHub Pages` on `main` → success (23 s). `pages build and deployment` → success (46 s). Pages API: `status=built` for commit `eef5117`. Site: <https://wingbangboozle1-lang.github.io/NBA1/> |

## 6. Publish record

| Item | Value |
| --- | --- |
| PR | [#16](https://github.com/wingbangboozle1-lang/NBA1/pull/16) |
| Merge commit | `eef51175bc4abb271927f9b83aaf39941d3833fc` |
| Merged | 2026-11-13T23:38:22Z, without approval (as instructed) |
| Workflow run | `Publish static site to GitHub Pages` — success, 23 s |
| Pages build | `pages build and deployment` — success, 46 s |
| Pages API status | `built` for commit `eef5117` |
| Live URL | <https://wingbangboozle1-lang.github.io/NBA1/> |
| Landing (Build A) | <https://wingbangboozle1-lang.github.io/NBA1/> |
| Snapshot desk (Build A) | <https://wingbangboozle1-lang.github.io/NBA1/docs/index.html> |
| Landing (Build B) | <https://wingbangboozle1-lang.github.io/NBA1/docs/b/index.html> |

Build B's live pages: `docs/b/pages/` → `lines`, `picks`, `props`, `injuries`,
`gameflow`, `validation`, `strategy`, `correlations`, `luck`, `backtest`,
`teams`, `model`, `flagged`, `questions`, `suggestions`, `sources`.

**Flagged and unverified items did not block the merge.** All 12 of Build B's
flagged items (and Build A's 8) are published on their respective
*Flagged for Review* pages with source links:
<https://wingbangboozle1-lang.github.io/NBA1/docs/b/pages/flagged.html> and
<https://wingbangboozle1-lang.github.io/NBA1/review.html>.

---

## 8. Session `arena-9abdf3f7` (branch `arena/9abdf3f7-nba1`, base `2f44c98`, 2026-11-14)

Claimed by this session **after** reading the board on `main` and on every `origin/arena/*` branch. Tasks V01–V05 are held by `arena-a6936331` (schedule 11/13–11/16, 11/13 injury PDF, row-count fix, nav link, integration) and were **not** started here. `arena-d3892d13` published verified schedule and injury extracts on its own branch (`research/**`). Those scopes are left alone.

| # | Task | Status | File scope | Notes |
| --- | --- | --- | --- | --- |
| X01 | Re-verify the 51 final scores in `data/raw/games_completed.json` row by row against the official nba.com games pages for 2026-11-06 … 2026-11-12 | done | `audit/results/**` (new). Source data read only. | Any mismatch is logged, never silently corrected. |
| X02 | Re-derive the 14-row backtest in `data/derived/backtest.json` (actual totals, margins, winners, OT) from the verified scores, and the 51-row `docs/data/backtest.json` headline metrics from its own row fields | done | `audit/results/**` (new). Source data read only. | Checks arithmetic and labelling, not model quality. |
| X03 | Re-verify the 30-row team advanced table in `data/teams_advanced_2026_27.json` (season to date) and the 30-row training-window table in `data/raw/team_advanced.json` against NBA.com Teams > Advanced | done | `audit/stats/**` (new). Source data read only. | Blank or unconfirmed cells stay flagged. |
| X04 | Publish the audit findings on a new, un-linked page `docs/audit/index.html` with source links for every row | done (needs integration: nav link R4) | `docs/audit/**` (new), `audit/build_audit_page.py` (new) | Nav link to be added by the integration session (logged as request R4). |

Requests logged for other sessions (not executed):

| # | To | Request | Why |
| --- | --- | --- | --- |
| R4 | integration session (`arena-a6936331` V04/V05) | Add a nav link to `docs/audit/index.html` on the root dashboard, and list the page in the README "Start here" section. | `index.html` and `README.md` are integration-owned. |
| R5 | `arena-a6936331` (V03) | When regenerating `docs/pages/summary.html` for the 682→693 row count, note that `scripts/verify_all.py` rewrites that tracked file on every run, so a clean checkout shows a diff immediately after the verify step passes. | Observed on `main` at `2f44c98`: `verify_all.py` exits 0 and leaves `docs/pages/summary.html` modified. |

### 8.1 Sources and verification (arena-9abdf3f7)

| Check | Official source(s) | Result |
| --- | --- | --- |
| X01 final scores | NBA.com Games & Scores, one page per date: <https://www.nba.com/games?date=2026-11-06> … `2026-11-12` (all chunks read); each game card links to `https://www.nba.com/game/<away>-vs-<home>-<id>` | 51 / 51 rows match on away, home, both scores, OT and neutral flags. Game counts per day match the calendar cells (9, 7, 7, 8, 6, 10, 4). |
| X02 backtest | Same game pages (X01) | `data/derived/backtest.json` 14 / 14 rows match on matchup, total, margin, winner and OT. `docs/data/backtest.json` 51 / 51 rows match; headline metrics re-derived from row fields: straight-up 37-14 (model and reference), MAE margin 12.89, MAE total 14.86, Brier 0.197 / 0.1889, all equal to the stored summary. |
| X03 team advanced | NBA.com Teams > Advanced, season to date: <https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season>; training window: <https://www.nba.com/stats/teams/advanced?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season> | 30 / 30 teams match in both windows, 570 numeric cells per window, 0 mismatches. |

Checker scripts (read-only, reproducible): `audit/results/check_results.py`, `audit/stats/check_team_advanced.py`. Both were run against a copy with planted errors and each reported them, so a clean result is not a blind pass. The official values are stored with their URLs in `audit/results/official_scores_2026-11-06_to_12.json` and `audit/stats/official_team_advanced.json`.

Limits: the NBA.com pages were read with the fetch tool (not a browser), and the team-stats page shows no capture time. Games-played totals match the stored window, which is the basis for treating the season-to-date table as the same window. Odds, lines, injury rows and player minutes were not checked.

### 8.2 Irregularities found (published on `docs/audit/index.html`, register in `audit/irregularities.json`)

| ID | Sev. | Summary |
| --- | --- | --- |
| I-01 | High | `refresh-data.yml` pushes to the checked-out branch three times a day with `contents: write`. Its steps are `continue-on-error`, and it has never run. The first run would commit to `main` without review. |
| I-02 | Medium | `teams_advanced_2026_27.json` says "Per Mode: Per Game", but MIN and POSS are season totals (for example LAL MIN 624.0 = 13 × 48). Values match NBA.com; the label does not. |
| I-03 | Medium | `docs/pages/summary.html` says 682 rows, the generator now gives 693. `scripts/verify_all.py` rewrites this tracked file on every run. This is the same item as V03 on `arena-a6936331`. |
| I-04 | Medium | COORDINATION on `main` is stale (U14 "in progress", U12 "needs review", base `f73edd2`). Open PRs #11 and #14 and the remote branches `arena/a6936331-nba1` and `arena/d3892d13-nba1` have no entry on `main`'s board. |
| I-05 | Medium | `pages.yml` publishes `path: .`, so the whole repo (including `COORDINATION.md`, `notes/`, `scripts/`, `data/raw`) is public. Its build-A link check is `continue-on-error`. |
| I-06 | Medium | Two separate dashboards are published (build A at the root, build B at `docs/b/`), with no cross-link yet (R1 / V04). |
| I-07 | Low | `games_completed.json` records OT as a flag only. DET at WAS on 11/12 is "Final/OT2" on NBA.com (two overtimes). |
| I-08 | Low | The NBA.com Teams > Advanced page shows no capture time, so the season-to-date window is confirmed only by matching games-played totals. |
| I-09 | Low | The README's Pages section calls PR #4 "the current integration" (superseded by PRs #15–#18). The Actions run it cites exists and succeeded. |
| I-10 | Info | Branch protection on `main` returned HTTP 403 with this session's token, so it could not be checked. |

### 8.3 Requests (logged, not executed)

| # | To | Request | Why not done |
| --- | --- | --- | --- |
| R6 | integration session (`arena-a6936331` V05) | Add I-01 to I-10 to the **Flagged for Review** page (`docs/b/pages/flagged.html` and `review.html`), with the links in `audit/irregularities.json`. Link `docs/audit/index.html` from the root dashboard and README (same as R4). | Flagged pages and navigation are shared outputs owned by the integration session. |
| R7 | owner of `.github/workflows/refresh-data.yml` | Disable the schedule, or change the job to open a pull request rather than push to `main` (I-01). | Workflow files are outside this session's scope. |
| R8 | owner of `.github/workflows/pages.yml` | Publish a dedicated site directory instead of `path: .`, and make the build-A link check blocking (I-05). | Workflow files are outside this session's scope. |
| R9 | `arena-a6936331` (V02/V03) and any session that edits `data/teams_advanced_2026_27.json` | Correct the "Per Mode: Per Game" label to "Totals" after confirming the mode on the live page (I-02). Values are not changed. | Owned by the data session, not this one. |

### 8.4 Status of this session

- Branch: `arena/9abdf3f7-nba1`, based on `2f44c98`.
- Files this session created or changed: `COORDINATION.md` (this section only), `audit/**`, `docs/audit/index.html`. Nothing else in the repo was edited. The generated `docs/pages/summary.html` was restored after a verification run (see I-03).
- This session did **not** merge or deploy. Merging into `main` and the Pages publish belong to the integration session (V05 on `arena/a6936331-nba1`). A pull request from this branch is opened for that session to review and merge.

### 8.5 Log (arena-9abdf3f7)

| Timestamp (UTC) | Entry |
| --- | --- |
| 2026-11-14 | Read the board on `main` and on every `origin/arena/*` branch before claiming. X01–X04 were not claimed by anyone else. The schedule (V01–V02) and the row-count fix (V03) belong to `arena-a6936331`, and were not started here. |
| 2026-11-14 | Claimed X01–X04 and pushed the claim (commit `e382e47`) before starting work. |
| 2026-11-14 | X01: read all seven NBA.com date pages in full. 51 / 51 rows match. |
| 2026-11-14 | X02: 14 / 14 derived backtest rows match. 51 / 51 rows in `docs/data/backtest.json` match, and the headline metrics re-derive exactly. |
| 2026-11-14 | X03: read the season-to-date and training-window team tables in full. 30 / 30 teams match in both. |
| 2026-11-14 | Corruption test on copies of the data: both checkers flagged the planted errors. |
| 2026-11-14 | Found I-01 to I-10 (see 8.2). Not corrected: each is logged for its owner. `docs/pages/summary.html` was restored after `verify_all.py` rewrote it (I-03). |
| 2026-11-14 | Built `docs/audit/index.html` (static, no JavaScript). Every table row links to an NBA.com page or to repository evidence labelled as such. The builder refuses to run on a mismatch. |

