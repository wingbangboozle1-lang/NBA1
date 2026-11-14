# NBA1 — final integration audit

**Audit date:** 2026-11-14 UTC  
**Tree audited:** `main` at `ff040a080f6eb4ea50b5ddb933699cf2a86397ea` (PR #49 plus the latest official-source probe record).
**Local integration point:** branch `arena/159ed109-nba1` includes this tree in merge commit `90d1670`. PR #49's checker/workflow changes were included at `9c0e93b`; the following #51/#52 commits only updated coordination/landing prose before the latest probe snapshot.
**Scope:** Re-ran the shared builders and audits, PR #35/#43 capture checks, the Integration Desk pipeline, and the separate `origination/` checks. Checked current links, rendering, probe and deployment state. This audit changes documentation only; it does not edit NBA data, published build outputs, workflows, or `notes/publish-log.md`.

This supersedes the earlier drafts at PR #39 / `f4cb034`, `1457e1c`, and `6eb0885`; those snapshots remain in branch history, not as the current result.

## Executive summary

NBA1 is a **set of distinct dated research builds**, not one synchronized pick service. The current tree contains the 27-game root dashboard, a separate 27-game Build D horizon page, the 36-row RecordLine data build, a distinct 27-game horizon model, the Integration Desk's 22-game cut, and the PR #40 `origination/` site with its own 101-game evaluation window. Their injury editions, records-as-of stamps, formulas, and pick gates differ. There is no safe global “best picks” list without an explicit model/horizon owner.

The repository now has a green custom Pages validation/deploy on the current mainline: `Publish static site` run [43544424833](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43544424833) succeeded for the PR #49 merge, `pages build and deployment` run [43544475544](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43544475544) succeeded for `ff040a0`, and the Pages API reports `built`. This is still **dated research/paper output**, not a live, market-priced, profitable, or independently validated pick service. No sportsbook price feed exists; strategy scores are model/sample-specific; injury and minutes coverage is incomplete. Keep these caveats attached to every result.

## Evidence boundary and source discipline

This audit verifies stored captures and reproducible local builds, not a fresh web-side transcription of every NBA value. Relevant source registers include the [NBA schedule](https://www.nba.com/schedule), dated [NBA Games & Scores pages](https://www.nba.com/games?date=2026-11-14), the [2026–27 NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/), the [Nov 13 8:00 PM ET injury-report PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_08_00PM.pdf), [NBA Stats team advanced data](https://www.nba.com/stats/teams/advanced), and [player traditional data](https://www.nba.com/stats/players/traditional). PR #43's capture text and read times are in [`data/raw/captures/session-w/`](data/raw/captures/session-w/) and [`docs/session-arena-f80dcc4a-nba1-w.md`](docs/session-arena-f80dcc4a-nba1-w.md). PR #35's 249-row recheck evidence is in [`data/refresh_2026_11_14/official_captures_2026-11-14.json`](data/refresh_2026_11_14/official_captures_2026-11-14.json). PR #40's source inputs are in [`data/official/`](data/official/); the Integration Desk's dated reads are in [`data/live/capture_meta.json`](data/live/capture_meta.json).

NBA-host egress is blocked from this sandbox. Link checks validate internal targets, approved hosts, or stored row comparisons; they do **not** establish current external HTTP response, NBA value freshness, permission, or data rights. PR #35/#40/#43 readings were rechecked from their committed capture files, not independently re-fetched by this audit. Unknown values remain unknown; no value was filled by inference.

## Published surfaces and separate inputs

| Surface | Current captured scope and generated outputs | Limitation / interpretation |
| --- | --- | --- |
| Root dashboard, [`site/`](site/) and [`index.html`](index.html) | Build D landing; 27 upcoming games for Nov 14–17; 63 paper-pick rows; 88 prop rows; 51 out-of-sample games; 122-row 11/13 7:30 PM injury edition in its data metadata. | Its model and 7:30 PM edition are distinct from the Build D one-page horizon's 8:00 PM edition. Partial player minutes and pending injury editions remain; the page is not a market benchmark. |
| Build D horizon page, [`picks-2026-11-14.html`](picks-2026-11-14.html) | 27 games; 23 gated paper picks, 12 parlay cards, 54 prop-combo rows; 28 attributed 11/14 injury rows and 5 unattributed rows from the 8:00 PM edition. `verify_all.py` self-audit reports 10/10 freshly rechecked schedule rows, 27-game fidelity, and 148 source-linked table rows. | No totals, no market-validated bets, and no funded strategies. Five PDF continuation rows stay unattributed. DET@MIA's report time (7:00) conflicts with the schedule's 8:00 PM and remains flagged. |
| RecordLine / Build A pages (`lines.html`, `gameflow.html`, `review.html`) | [`data/originated_lines.json`](data/originated_lines.json): 36 rows for Nov 13–17, 30 model picks, 15 parlays, 72 prop rows, 72 impact rows, 20 unattributed impact rows. | Nov 13 results were still in progress in the captured state; 18 team records remain flagged stale. This output has a frozen Nov 13 pick basis and a separate Nov 14–17 capture basis. |
| Horizon picks page, [`picks.html`](picks.html) | PR #41's separate 27-single horizon model: 26 model picks, 12 parlay cards, 8 SGP candidates in [`data/derived/horizon_picks.json`](data/derived/horizon_picks.json). | Picks are explicitly unvalidated and use their own input/gate rules and older 5:15 PM injury basis; do not merge them with the Build D 8:00 PM page. |
| Build B / Command Center (`docs/b/`, `command-center/`) | Updated metadata covers 27 Nov 14–17 games; `docs/data/picks.json` and `command-center/data/picks.json` each carry 63 rows. Build B's backtest has a 51-game test window and ten strategies. | README/root copy still calls Command Center a 22-game Nov 14–16 cut; its committed metadata now says 27 games. That stale descriptive text is a reconciliation task. |
| Integration Desk (`desk*.html`, `integration/`) | 22 games for Nov 14–16; 51-game out-of-sample grading set; 26 injury rows and logs for 3 players. | Rerun: 0 selected, 8 lean-only, 5 rejected for data/availability, 9 provisional; 31 settlements blocked; 0 prop rows usable for staking. |
| PR #40 `origination/` site | 20 pages; 22 upcoming games; 151 captured finals + 23 unpublished-score fixtures; 101 out-of-sample forecasts and a 30-team standings reconciliation. | Own model and source set; no injury adjustment; player props are blocked; its 39 strategy cells have no funded strategy. README has a direct URL, but the root switcher/build matrix omits this site. |

The horizons are not interchangeable. The root dashboard/Command Center/Build B metadata covers 27 games; RecordLine covers 36 rows including the in-progress Nov 13 slate; the desk and PR #40 site use narrower 22-game cuts. Picks, line assumptions, injury editions, and settlement samples differ. The current root switcher and README also disagree on build count: root prose says “four implementations,” README says “five” while its matrix has six rows, and the separately documented `origination/` site is not in that matrix or the root switcher (though the README later links it directly).

### Research interpretation

- **Integration Desk:** 51 graded games; side 37–14; margin MAE 12.787 and total MAE 14.693. Its reported constant baselines are 15.276 (margin) and 14.375 (total), so total MAE is worse than baseline. Gates: 7 pass, 4 fail, 3 blank; 0 validated strategies / rewards payable. This sample does not establish skill or profit.
- **PR #40 model:** 101 OOS games; 68–33 straight up; margin MAE 12.431 vs 14.256 naive, Brier 0.2086 vs 0.2494 naive, total MAE 14.767. The model's 39 strategy cells have no funded strategy; only four reach its 25-bet floor. This is a comparison to its own naive reference, not sportsbook odds.
- **Build D one-page horizon:** the 23 paper picks are gate-labelled; it explicitly originates no totals and has no market gates or funded strategies. Its 27-game fidelity check is a reproduction of a separate RecordLine output, not an external validation.
- Injury status is not minutes/production. Model-derived correlations, parlay bounds, and luck estimates remain tied to their own samples/methods. Do not call a model-derived correlation empirical without a sourced sample and method; do not treat missing player coverage as zero.

## Verification performed on main `ff040a0`

`verify_all.py` and the broad audits were rerun after the Build D, PR #35, PR #49, and probe updates. Builders regenerated committed outputs without leaving a non-document worktree diff. The `engine_v2.build_site` caveat below is reported separately because that builder did overwrite two checked-in pages during an earlier audit run; those files were restored to the committed version.

- `python3 scripts/verify_all.py` — **VERIFY OK**. RecordLine: 36 games, 30 model picks, 15 parlays, 72 props/impact rows, 20 unattributed rows; 36/36 schedule rows matched with 0 mismatches; 18 stale-record teams remain. Build D: 27 games, 23 paper picks, 12 parlay cards, 54 props, 28 attributed + 5 unattributed injury rows; 10/10 fresh slate rows match, 148 table rows source-linked. Dashboard check: 16 pages / 688 rows (682 approved-source links; other rows explicitly not published).
- `python3 engine/verify_refresh.py` — **0 failures** across 249 line-by-line rows: 122 Build B injury rows, 91 Build A 3:00 PM injury rows/accounting, and 36 slate rows, with edition movements and repeated matchups checked against stored evidence. This is reproducible capture evidence, not an independent fetch by this audit.
- `python3 scripts/verify_session_w.py` — **VERIFY SESSION W OK**, 534 value checks plus link/row audit; 36 games, 30 records, 30 leaders, 111 attributed + 11 unattributed injury rows.
- `audit/results/check_results.py` and `audit/stats/check_team_advanced.py` — **0 mismatches**; the stats audit compares 30 rows / 570 numeric cells in each of two stored team-advanced windows.
- `python3 scripts/verify_dashboard.py` — **PASS**, 16 pages and 688 rows, 682 with approved official-source links; remaining rows have explicit not-published markers.
- `python3 -m engine_v2.pipeline` and `python3 -m engine_v2.check_site` — **PASS** from committed PR #40 inputs: 20 pages and all data-table rows source-linked. The pipeline reports 151 captured finals, 23 unpublished-score fixtures, 101 OOS games, 68–33 SU, margin MAE 12.431, total MAE 14.767, Brier 0.2086.
- Integration Desk pipeline (`model`, `props`, `settle`, `gates`, `picks`, `transform`, `crosscheck`, `review`, `leaderboard`, `site`, `report`) completed: 51 graded / 31 blocked; 22/22 schedule cross-capture matches; 0 selected, 8 lean-only, 5 rejected, 9 provisional; 0 validated strategies / payable rewards. Tracked outputs did not change.
- `python3 scripts/verify_integration.py` — **0 errors, 44 warnings**; 178 JSON, 112 HTML, 10,308 static links, 4,362/4,523 rows tagged as carrying an official source. Its broad scan leaves 161 rows to triage and reports three literal `None` renderings (two in `slate.html`, one in `docs/pages/strategies.html`). Warnings do not prove every row is an unsourced NBA fact; inspect rather than inventing sources/values.
- `python3 scripts/check_links.py` — **PASS** across 59 `docs/` and Command Center pages: 2,076 links, 879 static rows, 0 broken internal links, 0 non-approved hosts, 0 rows without a source, 1 explicitly unverified row. It does not fetch NBA URLs.
- `node scripts/render_check.mjs` — **PASS**, 112 pages, 6,578 content blocks, 5,867 rendered table rows, 0 page problems. `python3 scripts/check_rendered.py` — **PASS**, 17 Command Center pages, 707 rows, 0 missing links/bad cells. Both use DOM shims, not CSS/real-browser tests.
- `python3 scripts/verify_data.py` — **0 errors**, 15 checks passed, 34 explicitly unverified field groups. `python3 scripts/verify_inline.py` — **20/20 passed**.
- `python3 scripts/audit_injury_editions.py` — **PASS** for its 113-row fixture (93 attributed, 20 team not printed; no missing/extra rows; five status changes between its audited 03:00 PM and 05:15 PM editions). PR #35/#43 cover additional editions; the fixture is not a substitute for those checks.
- `git diff --check` — **PASS** for the documentation-only changes.

### Rebuild fidelity caveat — PR #40 `origination/`

The checked-in `method.html` and `props.html` now have source-linked tables; `render_check.mjs` passes on the committed 112-page tree, and `engine_v2.check_site` passes its 20 pages. But running `python3 -m engine_v2.build_site` regenerated those two files from the old template and removed 27 lines of the committed table additions. I restored both files from the audited tree, leaving no site diff. Thus the checked-in output passes; the site builder does **not yet reproduce the latest page additions**. The still-open PR #45 touches this builder/pages; this audit did not edit it.

## Freshness, injury editions, and source-probe limits

PR #35 adds a line-by-line recheck for the 12:00, 3:00, 5:00, 5:15, and 7:30 PM report editions; PR #43 captures the 8:00 PM edition and applies date-specific gates on its RecordLine output. These are separate editions, not a single current injury feed. Nov 15–17 rows are gated when no report existed at capture; the 11/13 game state was in progress at the recorded cut, so stale records remain flagged.

The scheduled [`refresh-data.yml`](.github/workflows/refresh-data.yml) path was rechecked. It still tolerates fetch/build errors; [`engine/fetch_official.py`](engine/fetch_official.py) writes `_capture_*.json` summaries rather than promoting parsed values into raw inputs; [`engine/pipeline.py`](engine/pipeline.py) reads committed raw snapshots. PR #35's [`engine/verify_refresh.py`](engine/verify_refresh.py) is a useful audit of stored captures, not an end-to-end scheduled refresh. Keep freshness claims disabled until parsing, staging, validation, atomic promotion, and failure handling are tested together.

The latest committed reachability record in the audited tree is timestamped `2026-11-14T02:06:50Z`: 825 URLs; 7 `ok`, 816 `blocked`, 0 redirect/gone/unreachable. Those displayed categories account for 823 URLs, leaving two unaccounted for; do not infer their classification. This is reachability only. Probe run [43544424675](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43544424675) completed successfully for `9c0e93b`, but could not push its newer record after five retries; it remains available in that run's artifact, and the committed record above is the latest one on `main`. The collector scans repository JSON/HTML, including its own JSON and `verification.html`; its count is not a count of independent sources.

## Integration, deployment, and handoff

- Merged inputs represented by the audit include PR #39 (`f4cb034`), #40 (`5372f45`), #20 (`e01e83e`), #43 (`1457e1c`), #44 (`60e90c5`), #41 (`ce9d1a3`), #35 (`a4d47f8`), #48 (`bdbff69`), #50 (`6e12311`), #51 (`12606c9`), #52 (`6eb0885`), and #49 (`9c0e93b`).
- Current main custom validation/deploy [43544424833](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43544424833) succeeded; the subsequent Pages build/deployment [43544475544](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43544475544) succeeded for `ff040a0`. The Pages API reports `built`. Site: [GitHub Pages](https://wingbangboozle1-lang.github.io/NBA1/).
- **Navigation handoff:** root `index.html` says “four implementations”; README says “five” and its build matrix has six rows. The separate `origination/` build has a direct link later in README but is missing from the matrix and root switcher. Command Center's current metadata says 27 games, while the README/root prose still says 22. Reconcile the counts, horizons, and links in the landing/README owner session; no shared navigation was changed here.
- PR #45 remains open and the builder-fidelity issue above is unresolved. PRs #42, #37, and #36 also remained open at the last check; their changes are untouched. PR #49's host/fragment gate repair has merged, and main's full custom validation is green.
- The two root-level `None` renderings and the broad scan's 161 row-triage items remain review tasks. Do not fix by inferring values or replacing missing cells with zero.

## Decisions still required

1. **Data rights:** confirm permission to fetch, store, transform, and republish NBA data, or use a licensed provider. Reachability is not permission.
2. **Market benchmark:** select a licensed odds source and declare settlement/closing-price policy before publishing expected value, ROI, CLV, or profit claims.
3. **Refresh safety:** define freshness thresholds; stage parses; validate dates, game IDs, schema, and coverage; promote atomically; suppress picks for stale/incomplete inputs.
4. **Validation:** predeclare walk-forward design, minimum sample size, multiple-testing policy, calibration thresholds, and zero/void-pick rules. Do not loosen gates to produce a validated strategy.
5. **Injury/minutes coverage:** identify complete, licensed minutes/role history; leave unconfirmed values blank. Current coverage is incomplete and edition-specific.
6. **Correlation:** use a sourced play-by-play/box-score sample and declared confidence method before calling model-derived correlations empirical.
7. **Governance/legal review:** define reward funding/adjudication and review any wagering-related or NL-facing use. See the [Dutch Gaming Authority's online-gambling guidance](https://kansspelautoriteit.nl/online-kansspel-aanbieden); this is not legal advice.

## Official and reproducible references

- [NBA schedule](https://www.nba.com/schedule) and [Nov 14 NBA Games & Scores](https://www.nba.com/games?date=2026-11-14).
- [NBA 2026–27 injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and [Nov 13 8:00 PM ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_08_00PM.pdf).
- [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced) and [NBA Stats — Players Traditional](https://www.nba.com/stats/players/traditional).
- [GitHub Actions `continue-on-error` syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepscontinue-on-error).
- [Live GitHub Pages site](https://wingbangboozle1-lang.github.io/NBA1/).

---

## Postscript (2026-11-14T09:55Z, session `arena/ef6ff2a4-nba1`)

Two items in this audit were resolved after it was written; both are recorded here so the
document stays accurate as a snapshot with a pointer to the fix:

1. **Rebuild fidelity caveat (PR #40 `origination/`)** — resolved by commit `e506c65` on
   branch `arena/ef6ff2a4-nba1` (takeover of PR #45 under ground rule 5, credit
   `arena/e32856d8-nba1`). `engine_v2/build_site.py` now generates the source-linked
   *Parameter register* table (method page) and the *Required input / Closest official
   source* table (props page) that previously existed only as manual page edits, so
   `python3 -m engine_v2.build_site` reproduces the committed pages instead of deleting
   them. PR #45's *Declared constants* and *What a prop line needs* sections are also in
   the builder now. Verified: rebuild leaves zero diff on those pages;
   `render_check.mjs` 112 pages 0 problems; `verify_all.py` VERIFY OK;
   `verify_integration.py` PASSED 0 errors.
2. **PR #45** — closed as superseded by the above; content merged with credit.

Open at the time of this postscript and still tracked on the Flagged for Review page:
the navigation/count inconsistencies (root "four implementations" vs README "five" vs
six-row matrix; `origination/` missing from the root switcher; Command Center 22-vs-27
game prose), the two `slate.html` and one `docs/pages/strategies.html` literal `None`
renderings, and the broad-scan row-triage warnings. The integration session is addressing
the navigation items; none of them may be fixed by inferring values.
