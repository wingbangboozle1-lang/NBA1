# NBA1 — independent audit and handoff

**Audit date:** 2026-11-14 UTC  
**Tree audited:** `main` at `76e9632` (current merged tree; this audit adds no NBA data).  
**Scope:** Re-ran repository checks and reviewed the static refresh path on `76e9632`. I did not edit or re-verify the unmerged changes in PR [#31](https://github.com/wingbangboozle1-lang/NBA1/pull/31) or PR [#33](https://github.com/wingbangboozle1-lang/NBA1/pull/33).

## Executive summary

The repository already contains a substantial static NBA research desk: two dashboards, originated game lines, paper picks, parlays and player-prop combinations, injury and game-flow pages, backtests, correlations, validation gates, a strategy leaderboard, open questions, suggestions, and flagged-review registers. The current merged site builds and renders cleanly under the checks listed below.

**It is not yet an automatically refreshed or market-validated pick service.** The committed schedule/stat/injury snapshots are dated; the published reward tiers are paper/research labels, not payable rewards; there is no connected market-price feed; and no strategy passes all of its validation gates. Most importantly, the scheduled refresh workflow currently captures metadata but does not promote refreshed official data into the raw inputs consumed by the model. Its refresh/build steps also continue on errors. A green scheduled run therefore would not prove that lines and picks were refreshed.

The code and site should continue to label existing outputs as dated research/paper outputs. Do not present them as current recommendations or evidence of a profitable edge until the missing feed, data-rights, price, and validation questions are resolved.

## Checks actually run

- `python3 scripts/verify_all.py` — **PASS**. Both site builders, row/source checks, and data audits completed. The build reported 31 games, 26 model picks, 12 parlays, 62 props, and 62 impact rows, including 20 unattributed impact rows. The schedule verifier compared 31 published rows with the local official capture of 36 games for 13–17 Nov: 0 mismatches; it separately reports 18 teams with stale records in that horizon.
- `python3 scripts/verify_integration.py` — **0 errors, 42 warnings**. It parsed 97 JSON files and 51 HTML files and checked 2,432 static links. It reports 1,230 of 1,298 table/data rows with an official source link; the remaining 68 are not sourced by that check and must remain visibly identified as methodology/decision rows or be flagged, not assigned invented NBA sources. It also flagged a literal `None` in `docs/pages/strategies.html`.
- `node scripts/render_check.mjs` — **51/51 pages rendered, 0 page problems**, 2,391 content blocks and 1,946 rendered table rows. The first local attempt could not import `jsdom`; after installing the CI dependency into ignored `node_modules` (no tracked dependency files), the render check passed.
- `python3 scripts/check_links.py` — **0 broken internal links, 0 unapproved external hosts, 0 ragged rows** across 41 `docs/` pages. It counted 725 static rows and 2 rows without source links on `docs/b/index.html` (the two methodology proposals about closing prices and probability calibration). The script also reports 42 client-side scripts that its static table scan does not inspect.
- `python3 scripts/verify_data.py` — **0 errors; 15 checks passed**. It lists 41 groups of blank/null fields as `UNVERIFIED`; those are field groups, not a count of all missing cells. Blanks must stay blank until their source is confirmed.
- `python3 scripts/verify_inline.py` — **20/20 checks passed**, including row/source provenance, arithmetic, probabilities, correlations, injury double-counting, and the strategy gates. The ledger has 0 validated Build A strategies.
- `python3 scripts/audit_injury_editions.py` — **PASS**: 113 player rows in the 05:15 PM PDF transcription; 93 with a team attributed and 20 with the team cell not printed; 0 missing/extra against its audit file; 5 status changes between the 03:00 PM and 05:15 PM editions.
- `git diff --check` — **PASS**.

These are repository/structure checks, not a claim that I fetched every NBA URL from this sandbox. The local link checker explicitly says outbound access to `nba.com` is blocked here; it checks HTTPS and approved hosts, not current HTTP status or the truth of each external page. The repository's separate GitHub-runner probe record, [`data/raw/probe_official.json`](data/raw/probe_official.json), is a one-time reachability observation (134 URLs; 3 returned success to its plain client, 131 were blocked, and 0 were classified as 404/410). Reachability does not establish permission, licence, continuity, or data rights.

## Current data coverage and limits

- The root RecordLine-1 snapshot in [`data/originated_lines.json`](data/originated_lines.json) says it was generated `2026-11-13T22:45Z`, contains 31 schedule rows, and records 26 model picks. Its own assumptions state that all model parameters are project choices, totals are not originated in that model, and market comparison gates are blocked without odds.
- Build B metadata in [`docs/data/meta.json`](docs/data/meta.json) is generated `2026-11-13T23:25:15Z`, has `as_of: 2026-11-13`, and lists 23 upcoming games on 13–15 Nov. It is a dated snapshot, not a current 14–17 Nov feed.
- The merged schedule verification record reports 36 official schedule games across 13–17 Nov, including a 27-game 14–17 Nov horizon. The underlying official review is linked from [`schedule-verified.html`](schedule-verified.html) and the [NBA schedule](https://www.nba.com/schedule). On the audited `main` tree, no originated lines were present for the 11/17 slate. PR [#31](https://github.com/wingbangboozle1-lang/NBA1/pull/31) is open and claims a fresh 14–17 Nov capture plus paper lines; those unmerged changes are **not** counted as live or verified in this audit.
- A second open branch, PR [#33](https://github.com/wingbangboozle1-lang/NBA1/pull/33), also describes itself as final integration and proposes a unified dashboard plus 14–17 Nov lines/injury changes. It overlaps PR #31's shared schedule, picks, navigation and review outputs. Neither PR was merged or independently validated here. Choose one integration path, reconcile source rows and preserve both builds before publishing; do not merge their competing snapshots blindly.
- Build A's backtest ledger labels its 14-game results **contaminated**; Build B's committed [`validation.json`](docs/data/validation.json) uses a 51-game out-of-sample window, but its comparison is against a model reference, not sportsbook closing prices. The stored results are mixed: margin MAE 12.89 vs 13.19 for the reference; total MAE 14.86 vs 14.73; straight-up 37–14 for both; Brier 0.197 vs 0.1889. Treat these as small-sample research metrics, not evidence of a betting edge.
- Build A has 0 of 8 strategies marked `VALIDATED`. Build B lists 6 graded strategies capped at “Tier 3 - Quarter unit” and 4 “Not funded - research only”; none clears every gate, and the site says reward allocation is zero. The top record is not a payout or a skill conclusion. The market data needed to compute real ROI/EV is absent.
- The official injury source is the [NBA 2026–27 injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and the 11/13 05:15 PM ET [official PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf). The transcription audit leaves 20 team cells unassigned where the PDF did not print a team. The root minutes table has only 24 rows; Build B's flagged register also describes its player-minute coverage as partial. Rotation impact is therefore a lower bound for uncovered players, not a complete minutes forecast.
- Parlay/SGP and player-combo correlation entries are not uniformly empirical. The site labels some as model-derived and leaves Tier-C correlations null; no play-by-play sample is present to promote those values to measured NBA correlations.

## Current integration/deployment state at the final check

At 2026-11-14 01:07 UTC, GitHub reported `main` at `76e9632` and Pages API status `building`. The last completed `pages build and deployment` run visible in the Actions history was successful for `57b4284`; the later main deployment was still in progress when checked. PR #31 had its `validate` and source-probe checks in progress. PR #33 had a cancelled validation run after a new push and a source probe in progress. Therefore I cannot claim the latest site revision is deployed or that either new slate PR has passed its final gates. The live base URL remains [GitHub Pages](https://wingbangboozle1-lang.github.io/NBA1/); re-check its build and deployment after one integration PR is selected and merged.

## High-priority implementation gap: the scheduled refresh does not refresh model inputs

This is a code-path finding, not an NBA-data inference:

1. [`.github/workflows/refresh-data.yml`](.github/workflows/refresh-data.yml) sets `continue-on-error: true` for the fetch step, the pipeline step, and the page-build step. It then proceeds to the commit step. GitHub documents that step-level `continue-on-error` prevents a failing step from failing its job: [GitHub Actions workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error).
2. [`engine/fetch_official.py`](engine/fetch_official.py) writes `_capture_*.json` summaries (for example, row counts, byte counts, or game links). Its own summary says “Raw captures only” and “Nothing in `data/raw/*.json` is overwritten by this script automatically.” It also returns exit code 0 even when its `failed` list is non-empty.
3. [`engine/pipeline.py`](engine/pipeline.py) reads the existing `data/raw/team_advanced.json`, `games_completed.json`, `schedule_upcoming.json`, `injuries.json`, and `players_traditional.json`. It does not consume the `_capture_*.json` summaries. Rebuilding after the fetch therefore recomputes from the committed snapshots, not the newly fetched contents.

**Result:** the current scheduled job can appear successful while the official source snapshots, originated lines, injuries, and picks remain stale. This does not meet the requested automatic generation of every upcoming slate up to 72 hours. The specific request to the active integration owner is recorded in [`COORDINATION.md`](COORDINATION.md) §14 and was sent on PR #31; no other session's files were changed here.

## Questions that still need answers before a reasonable implementation decision

1. **Source permission and data rights:** Is NBA data permitted to be fetched, stored, transformed, and republished by this project? The probe is a reachability test only. Resolve this with NBA's applicable terms/permissions or a licensed provider before turning on a recurring collector. Start with the official [NBA schedule](https://www.nba.com/schedule), [NBA team advanced stats](https://www.nba.com/stats/teams/advanced), [NBA player statistics](https://www.nba.com/stats/players/traditional), and [injury-report policy/index](https://official.nba.com/nba-injury-report-2026-27-season/); none of those links alone grants republishing rights.
2. **Market benchmark:** Which licensed odds source and timestamp (preferably closing price) will grade sides, totals, props, and parlays? Without that, `units`, ROI, and “edge” are model-vs-reference comparisons, not market profit.
3. **Refresh safety:** What is the required freshness threshold for schedule, ratings, player stats, and each injury-report edition? What should the UI do when an official endpoint is blocked, malformed, or late? Recommended default: fail closed, retain the last known-good snapshot with its timestamp, and suppress current-slate picks when inputs exceed the threshold.
4. **Validation policy:** What minimum out-of-sample sample, walk-forward design, multiple-testing correction, calibration tolerance, and gate-reset policy should be required before any strategy can enter a reward tier? Existing gates correctly leave all strategies unvalidated; do not loosen them to create a leaderboard winner.
5. **Injury/rotation evidence:** Which official source supplies complete player minutes and historical role changes, including players outside the captured top-50 table? Until resolved, leave unverified minutes blank and keep the impact estimate labelled as a lower bound.
6. **Correlation evidence:** What official play-by-play or box-score history and sample size will be used to estimate player and same-game correlation with confidence intervals? Do not relabel model-derived values as empirical.
7. **Reward/legal governance:** Who would fund and adjudicate rewards, what constitutes a valid/push/void pick, and what legal review is required for an NL-facing leaderboard or wagering-related service? The repository flags the [Dutch Gaming Authority's online-gambling licensing guidance](https://kansspelautoriteit.nl/online-kansspel-aanbieden); this audit is not legal advice.

## Recommended next path — suggestions only, not implemented here

1. Keep the current dashboard clearly labelled **dated research / paper output**. Suppress or visibly stale-tag any slate if its official inputs are outside the approved freshness window.
2. After source-rights review, build an ingestion pipeline that stores the actual response or a reproducible official snapshot, records URL/time/status/hash, parses into staging, checks dates/game IDs/row counts/schema, and promotes atomically only after validation. Test parsers against committed official fixtures; make failed fetches/parses fail the job and never produce a green “refreshed” status from an empty capture.
3. Make the refresh job generate a rolling 72-hour schedule, use the latest applicable injury edition, rebuild line/pick/projection pages, and publish an explicit freshness indicator. If an input is missing, emit no pick for that game rather than reusing an unlabeled stale pick.
4. Add a licensed market-price capture with line movement and closing-price settlement before presenting expected value or any real reward. Keep paper performance in a separate ledger.
5. Continue walk-forward testing and empirical correlation estimation only when enough sourced observations exist. Keep the leaderboard in research-only mode until every gate passes on a predeclared sample and its price/settlement data is complete.

## Official sources and review links

- [NBA schedule](https://www.nba.com/schedule)
- [NBA Games & Scores — 2026-11-12](https://www.nba.com/games?date=2026-11-12) (the project source register links the individual game dates used in the backtest)
- [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced)
- [NBA Stats — Players Traditional](https://www.nba.com/stats/players/traditional)
- [NBA 2026–27 injury-report index and policy](https://official.nba.com/nba-injury-report-2026-27-season/)
- [Official 2026-11-13 05:15 PM ET injury-report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf)
- [Dutch Gaming Authority — offering online gambling](https://kansspelautoriteit.nl/online-kansspel-aanbieden)
- [GitHub Actions workflow syntax — `continue-on-error`](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error)
- [Live GitHub Pages site](https://wingbangboozle1-lang.github.io/NBA1/)
