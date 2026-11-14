# NBA1 — independent integration audit

**Audit date:** 2026-11-14 UTC  
**Tree audited:** `main` at `175c8201e06b67be925e625c8dbb83ba440a3cf0` (after PRs #31 and #38).  
**Scope:** Re-ran the repository verification suite on that tree, inspected the current static refresh path and current published data metadata, and checked GitHub integration/deployment state. This audit changes documentation only; it does not edit NBA data, published site pages, or workflows.  
**Prior audit:** The earlier Z01 audit of `76e9632` remains in this branch's commit history. Its results are historical and are not represented as verification of the newer tree.

## Executive summary

The merged repository contains a sourced, multi-page NBA research dashboard and a separate, populated 27-game slate page for 2026-11-14 through 2026-11-17. The latest merged tree passed the local builders, integration checks, page rendering, static link checks, rendered Command Center checks, data checks, inline checks, and injury-edition fixture audit. GitHub Actions also reported a successful static-site publish and Pages deployment for `175c820`; the Pages API reported `built` at the time checked.

**This is a dated research/paper dashboard, not an automatically refreshed or market-validated pick service.** The newly merged slate is a snapshot, not an end-to-end live feed. The recurring refresh workflow still tolerates fetch/build errors, the fetcher writes capture summaries rather than promoting parsed source data into model inputs, and the model pipeline reads the existing committed raw snapshots. There is no sportsbook price feed; the prop-combo anchors are not book lines; and the strategy checks still report zero validated strategies. Injury and rotation inputs are partial or not yet published for later slates. These limits are non-blocking for publishing a clearly labeled research site, but they block claims of current, profitable recommendations.

## Evidence boundary and source discipline

This is an integration/code-path audit, not a new independent transcription of every NBA value. The 2026-11-14 slate snapshot links its game rows to the official [NBA schedule](https://www.nba.com/schedule) and [NBA Games & Scores pages for Nov 14](https://www.nba.com/games?date=2026-11-14), [Nov 15](https://www.nba.com/games?date=2026-11-15), [Nov 16](https://www.nba.com/games?date=2026-11-16), and [Nov 17](https://www.nba.com/games?date=2026-11-17). Its injury section links to the [official NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and the [Nov 13, 2026 7:30 PM ET report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf). The repository also links team-stat inputs to [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced) and player inputs to [NBA Stats — Players Traditional](https://www.nba.com/stats/players/traditional).

The sandbox could not independently fetch NBA pages during this audit. The local link checker explicitly reports that outbound `nba.com` access is blocked; it checks approved hosts and internal links, not external HTTP status or the truth of each NBA value. The snapshot's source metadata and the earlier integration session's row-by-row claims are recorded evidence, but this audit did **not** repeat those external lookups. Unknown NBA values remain unknown; no missing value was filled by inference. Probe reachability is not proof of source permission, data rights, correctness, or freshness.

## Current published coverage and limitations

- The committed capture [`data/slate_2026_11_14.json`](data/slate_2026_11_14.json) describes a 2026-11-14–17 window with 27 schedule rows (per-date counts 5/9/8/5). [`data/originated_lines_refresh.json`](data/originated_lines_refresh.json) describes 27 games, 23 model picks, 12 parlay cards, and 54 player-combo anchors. The source metadata labels the model constants as project assumptions, not official NBA values. The linked sources above are the authoritative references; this audit verifies the repository structure and counts, not a fresh source transcription.
- This refresh is not propagated consistently through all builds. The older root [`data/originated_lines.json`](data/originated_lines.json) is timestamped `2026-11-13T22:45Z`, covers 11/13–11/16, and explicitly says its totals are not originated and market-comparison gates are blocked without odds. Build B and Command Center metadata report 22 upcoming games for 11/14–11/16, not 11/17. Thus the 11/14–17 horizon exists in the separate `slate.html`/refresh snapshot, but the repository does not yet present one synchronized rolling horizon across all model/dashboard builds.
- The refresh JSON labels all 54 prop rows as blocked: 44 are `BLOCKED — status report not yet due/published`, five are `BLOCKED — team report not yet submitted`, and five are `BLOCKED — no market number, no game-log variance`. The status fields respectively say “Report not yet published for this date,” “NOT YET SUBMITTED (team),” and “Not listed on report.” These are blocked research anchors, not sportsbook prop lines or actionable bets. The injury snapshot is edition-specific; later dates have no report in that capture.
- The older model parameters are project assumptions, not official values. The historical/build-specific backtest and strategy summaries should remain research-only: no licensed closing-price benchmark is connected, and [`scripts/verify_inline.py`](scripts/verify_inline.py) confirms a declared/actual validated-strategy count of zero. Backtest arithmetic or a model-vs-reference comparison is not evidence of market profit.
- The main `verify_all.py` build reports 20 unattributed impact rows. Rotation/minutes coverage therefore remains incomplete; do not treat an unobserved or unattributed impact as zero. Correlation estimates identified by the site as model-derived must not be relabeled empirical without a sourced sample and method.

## Verification performed on `175c820`

All results below are from the current merged tree, not the earlier `76e9632` audit.

- `python3 scripts/verify_all.py` — **VERIFY OK**. Builders/checkers completed; the build reported 31 legacy originated-line rows, 26 model picks, 12 parlays, 62 props, 62 impact rows, and 20 unattributed impact rows. The schedule verifier compared 31 published rows with 36 rows in the local official capture for 11/13–11/17: **0 mismatches**; it still reports **18 teams with stale records** in that horizon. This fixture comparison does not mean all 36 rows were independently fetched during this audit.
- `python3 scripts/verify_integration.py` — **0 errors, 44 warnings**; 118 JSON files, 68 HTML files, and 3,192 static links checked. The generic scanner found official source links on 1,442 of 1,527 rows; 85 rows need triage under that scanner. It also reported three literal `None` renderings (two in `slate.html`, one in `docs/pages/strategies.html`). These are warnings, not proof that every affected row is an unsourced NBA fact; inspect/label them rather than infer a source or value.
- `node scripts/render_check.mjs` — **68 pages**, 3,269 content blocks, 2,740 rendered table rows, **0 pages with rendering problems**.
- `python3 scripts/check_links.py` — **PASS** across 58 `docs/` and Command Center pages: 1,904 links, 737 static table rows, 0 broken internal links, 0 unapproved external hosts, 0 rows without a source, and 2 rows explicitly marked unverified. This checker does not verify live external HTTP status and does not statically scan client-rendered rows.
- `python3 scripts/check_rendered.py` — **PASS**: 17 Command Center pages, 644 rendered table rows, 0 rows without a link and 0 bad cells. This uses a DOM shim; it does not validate CSS or replace a real-browser test.
- `python3 scripts/verify_data.py` — **0 errors**, 15 checks passed, 43 groups of fields explicitly reported `UNVERIFIED`.
- `python3 scripts/verify_inline.py` — **20/20 checks passed**.
- `python3 scripts/audit_injury_editions.py` — **PASS** for its committed fixture: 113 player rows compared (93 team-attributed and 20 with team not printed), no missing/extra rows, and five status changes between its audited editions. This is a fixture/transcription consistency check, not a new live fetch.
- `git diff --check` — **PASS** on the clean `175c820` verification tree.

The checkers have different scopes: in particular, `verify_integration.py` scans a broader set of rendered/static rows than `check_links.py`. Their counts should not be collapsed into a claim that every row across every build is sourced. The 85 broad-scanner warnings and the three `None` renderings remain review items.

## Refresh-path audit — current, reproducible code finding

This finding was rechecked directly against `175c820`:

1. [`.github/workflows/refresh-data.yml`](.github/workflows/refresh-data.yml) has `continue-on-error: true` on the fetch, pipeline, and page-build steps, then continues to its commit step. GitHub documents the step-level behavior in [workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error).
2. [`engine/fetch_official.py`](engine/fetch_official.py) writes `_capture_*.json` summaries and explicitly says it does not overwrite `data/raw/*.json`. It records failures in `_last_refresh.json` and returns exit code 0 even when its failure list is non-empty.
3. [`engine/pipeline.py`](engine/pipeline.py) reads the existing committed `team_advanced.json`, `games_completed.json`, `schedule_upcoming.json`, `injuries.json`, `players_traditional.json`, and related raw inputs; it does not consume the `_capture_*.json` summaries.

**Consequence:** a scheduled job can finish without a failing workflow while the model continues to use the previous raw snapshot. A green refresh run is not evidence that new official inputs, lines, injuries, or picks were promoted. No end-to-end source parser/promotion test was run as part of this audit. This gap should remain explicitly flagged until ingestion, validation, atomic promotion, and a failure-path test are implemented.

## Integration and deployment state checked

- PR [#31](https://github.com/wingbangboozle1-lang/NBA1/pull/31) is **merged** at `2026-11-14T01:14:06Z`, merge commit `35f05a8798c064353fbfee398ccc16121c6c6c20`. Its integration adds the separate 11/14–17 slate and its paper-pick output; the full current branch checks above were rerun after later main changes.
- PR [#38](https://github.com/wingbangboozle1-lang/NBA1/pull/38) is **merged** and records #31's integration result in `COORDINATION.md`.
- For `175c820`, the `Publish static site to GitHub Pages` run [43539728018](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43539728018) and the `pages build and deployment` run [43539726844](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43539726844) both reported **success**. The Pages API reported `built`; the configured site is [https://wingbangboozle1-lang.github.io/NBA1/](https://wingbangboozle1-lang.github.io/NBA1/).
- The official-source probe run [43539727725](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43539727725) was still **in progress** when checked. The committed probe file's preceding record is timestamped `2026-11-14T01:16:17Z` and records 266 URLs, 5 `ok`, 260 `blocked`, and zero classified `gone` or `unreachable`; this is a reachability record only, not data validation or a licensing decision.
- At the last open-PR list, #20, #33, #35, #36, and #37 remained open. They were not merged, rebased, or edited by this audit. In particular, PR #31 is no longer an active handoff; the unresolved sibling work must be reviewed against its current PR state before any further integration.

## Decisions still required; non-blocking for a dated research site

1. **Data rights:** confirm permission to fetch, store, transform, and republish NBA data, or select a licensed provider. A reachable URL is not permission.
2. **Market benchmark:** choose a licensed odds source and settlement/closing-price policy before displaying expected value, ROI, or profit claims.
3. **Refresh safety:** define freshness thresholds and fail-closed behavior; parse into staging, validate dates/IDs/schema/coverage, promote atomically, and suppress picks when inputs are missing or stale.
4. **Validation:** predeclare walk-forward design, sample-size and multiple-testing policy, calibration thresholds, and rules for zero/void picks; do not loosen gates to produce a validated strategy.
5. **Injury/minutes coverage:** identify a complete, licensed minutes/role history and leave unconfirmed values blank; current impact rows are incomplete.
6. **Correlation:** establish a sourced play-by-play/box-score sample and confidence method before calling model-derived correlations empirical.
7. **Governance/legal review:** define reward funding/adjudication and review any wagering-related or NL-facing use. See the [Dutch Gaming Authority's online-gambling guidance](https://kansspelautoriteit.nl/online-kansspel-aanbieden); this audit is not legal advice.

## Official and reproducible references

- [NBA schedule](https://www.nba.com/schedule) and the four dated [NBA Games & Scores pages](https://www.nba.com/games?date=2026-11-14), [Nov 15](https://www.nba.com/games?date=2026-11-15), [Nov 16](https://www.nba.com/games?date=2026-11-16), [Nov 17](https://www.nba.com/games?date=2026-11-17).
- [NBA 2026–27 injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and [Nov 13 7:30 PM ET report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf).
- [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced) and [NBA Stats — Players Traditional](https://www.nba.com/stats/players/traditional).
- [GitHub Actions workflow syntax — `continue-on-error`](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error).
- [Live GitHub Pages site](https://wingbangboozle1-lang.github.io/NBA1/).
