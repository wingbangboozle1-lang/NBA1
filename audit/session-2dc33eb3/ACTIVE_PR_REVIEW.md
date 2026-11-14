# Independent integration, provenance, and Pages-readiness review

**Audit cut:** 2026-11-14 10:36 UTC<br>
**Tree reviewed:** `main` after PR #59 (merge `564c2cd`) and PR #61 (current commit `a29e721`); this session branch is rebased on that tree.
**Scope:** read-only NBA data/model audit plus a separate Pages concurrency fix in `.github/workflows/pages.yml`. No lines, scores, injury statuses, picks, or strategy results were changed by this review.

## Executive summary

The repository already contains the requested NBA research workflow: originated spreads/totals/fair moneylines, single and parlay strategy tests, an injury/game-flow view, correlation analysis, validation gates, an executive landing page, and Questions, Suggestions, Sources, and Flagged-for-Review pages. The current root landing page groups its navigation into Horizon, Evidence, Verification, and Decision. The full captured horizon is 27 games for 2026-11-14 through 2026-11-17, i.e. today plus three calendar days. The official schedule evidence is linked from the rows and was checked against the committed official transcriptions by the repository's schedule checker: [Nov 14](https://www.nba.com/games?date=2026-11-14), [Nov 15](https://www.nba.com/games?date=2026-11-15), [Nov 16](https://www.nba.com/games?date=2026-11-16), and [Nov 17](https://www.nba.com/games?date=2026-11-17).

The honest model result is **not a funded betting strategy**. The updated 60-game holdout reports a 23-9 record for S1; its nominal luck gate passes, but its calibration and stability gates fail and its availability-robustness gate was not run. The displayed units and return use a fixed hypothetical -110 settlement, not a captured sportsbook price. No row should be described as market-validated, profitable, or a bet. See the committed validation and leaderboard data and the official game inputs: [validation JSON](../../docs/data/validation.json), [leaderboard JSON](../../docs/data/leaderboard.json), [NBA games Nov 6](https://www.nba.com/games?date=2026-11-06), [Nov 7](https://www.nba.com/games?date=2026-11-07), [Nov 8](https://www.nba.com/games?date=2026-11-08), [Nov 9](https://www.nba.com/games?date=2026-11-09), [Nov 10](https://www.nba.com/games?date=2026-11-10), [Nov 11](https://www.nba.com/games?date=2026-11-11), [Nov 12](https://www.nba.com/games?date=2026-11-12), and [Nov 13](https://www.nba.com/games?date=2026-11-13).

Two material limitations remain:

1. The live dashboard contains a contradictory, stale sentence about S1 and luck; the Flagged register still says there are 63 paper picks although the current pick file and headline count 60.
2. The scheduled refresh workflow captures new material into review PRs but does not automatically promote it into the published line/pick data. The live site's refresh is therefore not yet hands-off.

The Pages workflow also has a deployment race. The main-branch Pages run for `a29e721` was cancelled while a pull-request validation was starting; the workflow used the same literal concurrency group (`pages`) for both. The Pages API reported an errored build for `564c2cd` and a still-building attempt for `a29e721` at this audit cut. I changed the workflow group to separate each pull request from the production ref; this should prevent PR checks from cancelling a main deployment. The fix still needs its PR checks and a successful post-merge Pages run before the site can be called deployed at the new commit.

**Live-source limitation:** this session did not fetch NBA URLs directly. The sandbox's outbound allowlist does not include NBA domains. I used the official NBA source URLs embedded in the committed capture/verification files and ran local reproducibility checks; this is not a new, independent live NBA capture. The next injury-edition claim below is explicitly attributed to PR #62 until its evidence is reviewed/merged.

## What exists today

- **Landing and categories:** [`index.html`](../../index.html) links to the current lines/picks, props, injuries/rotation, game flow, strategies/leaderboard, gates, correlations, luck, backtest, model, Source Check, Questions, Suggestions, Flagged for Review, Sources, and repo review pages. The public Pages URL recorded by GitHub is <https://wingbangboozle1-lang.github.io/NBA1/>.
- **Originated lines / near-term slate:** the current dashboard has 27 line rows covering Nov 14–17. Those are model outputs from the committed NBA team ratings and schedule captures, not lines posted by the NBA or a sportsbook. Official NBA inputs are available at [Teams Advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) and the date-filtered [NBA schedule pages](https://www.nba.com/schedule).
- **Strategies / skill gates:** the current model family tests ten strategies on a 60-game out-of-sample window. S1 is 23-9 (32 graded plays), with a two-sided exact binomial p-value of 0.0201 and Wilson 95% interval [0.5463, 0.8444]. The stored gates say G2 calibration **FAIL**, G5 stability **FAIL**, and G7 availability robustness **NOT RUN**. These facts are in [`docs/data/validation.json`](../../docs/data/validation.json); the historic scores come from the official date pages linked above. The p-value is a derived statistic, not an NBA-published value.
- **Correlation / parlays:** the repository distinguishes measured team-statistic correlations from model-derived parlay/SGP correlations. The row-level methods and source labels are on the [Correlations page](../../site/pages/correlations.html) and in [the official NBA team advanced statistics table](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season). Do not read a model-derived correlation as an empirically observed one.
- **Injuries / minutes:** official status inputs are sourced from the [NBA injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) and the dated PDF editions. The main landing page currently names the 2026-11-14 04:15 AM ET edition. The [injury page](../../site/pages/injuries.html) correctly labels minute-impact coverage as incomplete; absence status is not the same as a verified rotation-minute reallocation.
- **Props:** the current pick data leaves player-prop probabilities blank where official player-game variance is not available and includes a reason in the row, e.g. [`site/data/picks.json`](../../site/data/picks.json). Do not present those rows as priced or validated prop bets. The official player-stat reference is [NBA Players Traditional](https://www.nba.com/stats/players/traditional).
- **Questions and suggested next actions:** [`Questions`](../../site/pages/questions.html), [`Suggestions`](../../site/pages/suggestions.html), and [`Flagged for Review`](../../site/pages/flagged.html) exist and are linked from the landing page. They should remain the place for unresolved decisions and explicitly unverified values; no suggestion should be implemented by silently filling a missing value.

## Verification performed on the merged tree

All of the following checks read the current tree. `scripts/verify_all.py` was run in a disposable copy so its builders could not overwrite another session's generated files.

- `python3 scripts/verify_all.py` — **VERIFY OK** in the disposable copy. The builder/checker pass reported 36 captured games from Nov 13–17, 27 horizon games, and no schedule mismatch against the committed official schedule transcriptions. This proves reproducibility and internal consistency of the snapshots, not live NBA reachability.
- `python3 scripts/verify_integration.py` — **0 errors**, 217 JSON files parsed, 113 HTML files, 10,797 static links. It counted 4,795 of 4,974 data rows with an NBA-domain link and emitted 44 grouped warnings; 179 rows do not have an NBA source link. Some are internal/design-register rows, but the count must not be paraphrased as “every row has an official NBA source.”
- `python3 scripts/check_site.py` — **PASS** across its 15 listed root pages. Its summary explicitly permits NBA **or GitHub** sources; it is not a strict NBA-only provenance proof.
- `python3 scripts/verify_dashboard.py` — **PASS**, 822 rows checked and 812 counted as linked to its allowlisted hosts; ten rows use the explicit not-published marker. Its allowlist contains non-NBA sites, so “source-linked” is not equivalent to “sourced from NBA.com.”
- `python3 scripts/check_links.py` — **PASS**, 59 pages and 879 static rows in `docs/` plus `command-center/`; zero broken internal links, unapproved hosts, or ragged rows. It identified one explicitly unverified row. Client-rendered rows are checked separately.
- `python3 scripts/check_rendered.py` — **PASS**, 17 Command Center pages, 707 rows, zero missing links or malformed cells. This is a DOM shim, not a visual browser/CSS check.
- `node scripts/render_check.mjs` — **PASS**, 113 HTML pages, 7,121 rendered content blocks, 6,331 table rows, zero detected page problems.
- `python3 -m engine_v2.check_site` — **PASS** on 20 Origination pages. Its allowed-host list includes GitHub/documentation hosts, so this also is not NBA-only row provenance.
- `git diff --check` — clean before this report was written.

The official-source links were checked for presence and consistency in committed records; this session did **not** make HTTP requests to NBA domains. A successful structural gate must not be described as live-source verification.

## Findings requiring integration follow-up

### A1 — Landing-page luck statement contradicts the validation record

At [`index.html`](../../index.html), the banner says no strategy has cleared the skill gate and calls the 23-9 S1 result “inside what luck alone produces.” In the executive summary immediately below it, S1 is said to have passed G4, with p = 0.020; the structured validation record says G4 **PASS**, G2 **FAIL**, G5 **FAIL**, and G7 **NOT RUN**. The reproducible arithmetic is 23 wins in 32 plays, two-sided exact binomial p = 0.02006 (rounded 0.0201), Wilson lower bound 0.5463, and fixed -110 model units +11.909. The homepage should say: **no strategy has passed every applicable gate or is funded; S1 passes the nominal luck gate but fails calibration and stability, and availability robustness is untested.**

The S1 p-value is not proof of a general or market edge. The current seven-gate definition has no multiple-testing adjustment, while ten strategies were evaluated; the result should be identified as nominal/provisional and not “skill proven.” This is a methodology limitation, not a reason to weaken the gates. Evidence: [`docs/data/validation.json`](../../docs/data/validation.json), [`engine/validate.py`](../../engine/validate.py), [NBA games Nov 6–13](https://www.nba.com/games?date=2026-11-13).

**Cross-scope request R-A1:** update the dashboard builder and its generated landing copy together; do not patch only the generated HTML. No change to `index.html` or `scripts/build_dashboard.py` was made here because those are shared integration outputs.

### A2 — Flag F28's “63 picks” count is stale

The current landing tile and `site/data/picks.json` count 60 pick rows, and the integration checker confirms the 60-row headline. The current Flagged register still describes “Paper picks: 63.” Reconcile the definition and counts by market, then mark the old flag resolved or replace it with an accurately scoped item. A paper-pick count is a repository-derived count, not an NBA statistic; game membership should still be linked to the official [Nov 14–17 NBA schedule pages](https://www.nba.com/games?date=2026-11-14).

**Cross-scope request R-A2:** update the Flagged page/data and regenerate the landing count in one integration change. No shared data or flagged page was edited here.

### A3 — Injury-report edition needs a fresh, explicit timestamp

The merged landing page records the 04:15 AM ET report. PR #62 (`arena/2ef89703-nba1`) is an active, independently sourced comparison claiming the 04:30 AM ET PDF matches the site's 26 11/14 injury rows and reports edition/timing irregularities. The PDF URL is [official NBA report, Nov 14 04:30 AM ET](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf); the official publication hub is [NBA Injury Report 2026–27](https://official.nba.com/nba-injury-report-2026-27-season/). This session did not retrieve or independently verify that PDF. Until PR #62 evidence is reviewed and integrated, label 04:15 as the site's captured edition, not “newest.”

**Cross-scope request R-A3:** after the official 04:30 comparison is accepted, update the shared edition label and stale injury flags through the integration owner; preserve non-printed team/date cells as unverified rather than inferring them.

### A4 — “Official source” gates are broader than NBA-only provenance

`verify_dashboard.py` accepts GitHub docs, GitHub, a regulator, and several non-NBA publisher/retailer domains as “official” hosts. `check_site.py` accepts GitHub documentation; `engine_v2.check_site.py` accepts GitHub and raw GitHub. Those may be appropriate for code provenance or legal scope, but they cannot verify an NBA score, status, team rating, injury, minute, or schedule row. Separately, the strict whole-tree scan found 179 rows without a linked NBA-domain source. Existing flags F34/F37 already describe this class of gap; the current counts need to be refreshed after the PR #59 data update.

**Cross-scope request R-A4:** use NBA-only hosts for NBA facts; classify internal findings/design rows separately and mark “no official NBA source applies” or “unverified” with a reason. Do not make GitHub links or an approved-host allowlist look like confirmation of NBA data. Official NBA references include the [schedule](https://www.nba.com/schedule), [team advanced stats](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season), [player stats](https://www.nba.com/stats/players/traditional), and [injury-report hub](https://official.nba.com/nba-injury-report-2026-27-season/).

### A5 — Scheduled refresh is capture-only, not automatic pick publication

`.github/workflows/refresh-data.yml` is scheduled, but it fetches to `_capture_*.json`, deliberately discards builder churn, and creates a review PR; it does not promote the captures into the snapshots that feed the public horizon or publish newly generated picks. This is conservative, but it means the current scheduled workflow does not satisfy a fully unattended refresh. A safe no-manual-input design is: promote only when independent official-source/schema checks and all required validation gates pass; otherwise keep the last valid slate and show an explicit stale timestamp/reason. Do not automatically publish a failed or unverified refresh.

Before implementing that policy, decide whether “three days” means through calendar date `D+3` (four date labels including today, as the current 14–17 Nov window does) or three dates total. The current window uses `D` through `D+3`; it is within the user's stated maximum three days ahead if `D+3` is permitted. Sources: [NBA schedule](https://www.nba.com/schedule) and [official injury-report publication rules](https://official.nba.com/nba-injury-report-2026-27-season/).

### A6 — Model/provenance decisions still block real-world performance claims

- Pick rows are model-vs-reference outputs. No NBA-operated source provides a sportsbook closing price; therefore true book edge, CLV, hold-adjusted ROI, and real-money returns remain blank. Obtain a lawful/licensed price feed before claiming those values; do not invent an official NBA link for market odds.
- Injury status is official, but minutes moved to replacement players are not established by the injury PDF alone. Use verified player game logs/box scores and role/minute history; leave unobserved substitutions blank. Official stat entry points: [NBA Players Traditional](https://www.nba.com/stats/players/traditional) and [NBA box scores](https://www.nba.com/games).
- Parlays/SGPs need a clear distinction between empirical correlation and model-derived joint probability. Keep all legs, rho/bounds, sample size, and method visible; do not treat independence as a measured fact.
- Player props need official per-game outcomes and minutes at sufficient coverage before publishing probabilities or a combo leaderboard. Current null probabilities and explanatory notes are the right behavior until then.

These are already represented in the current [Questions](../../site/pages/questions.html), [Suggestions](../../site/pages/suggestions.html), and [Flagged for Review](../../site/pages/flagged.html) pages; this report requests refreshed wording/counts, not a second parallel register.

## Parallel integration state at the audit cut

- [PR #59](https://github.com/wingbangboozle1-lang/NBA1/pull/59) merged at 2026-11-14 10:27:52 UTC as `564c2cd`. It refreshes the 11/13 finals/settlement and extends the Build B holdout to 60 games. The GitHub Pages build for `564c2cd` was reported errored; main's later commit `a29e721` had a build still in progress, and the Pages API's overall status was `errored` at 10:36 UTC.
- [PR #58](https://github.com/wingbangboozle1-lang/NBA1/pull/58) closed unmerged at 10:36 UTC. It overlapped PR #59 on 17 paths: `COORDINATION.md`, `README.md`, `engine_v2/build_site.py`, `index.html`, `origination/pages/method.html`, `origination/pages/props.html`, `scripts/build_dashboard.py`, and the `site/pages/` backtest, flagged, gameflow, injuries, luck, picks, questions, sources, strategies, and validation pages. Its final merge state was conflicting; no changes from #58 are assumed to be in main unless separately present in the merged tree.
- [PR #62](https://github.com/wingbangboozle1-lang/NBA1/pull/62) was open at the audit cut. Its `validate` check passed and `deploy` was skipped as expected for a PR; its new evidence is not yet part of the public site.
- This session did not edit another session's files. The `COORDINATION.md` request log records the shared-output handoffs.

## Pages deployment fix in this session

The Pages workflow previously used one concurrency key, `pages`, for every `push`, `pull_request`, and manual run. The `main` run for commit `a29e721` was cancelled at 10:28:49 UTC while PR #62 validation started; its validate/deploy jobs had no completed steps. The workflow definition now keys concurrency by PR number when present, otherwise by ref: `pages-${{ github.event.pull_request.number || github.ref }}`. Thus PR #62 uses `pages-62` while main uses `pages-refs/heads/main`; PR validation no longer cancels production deployment, while repeated updates to one ref can still supersede its older run.

**Not yet complete at this report cut:** the workflow change must pass the PR check, merge, and then produce a successful Pages deployment. The live URL is configured as <https://wingbangboozle1-lang.github.io/NBA1/> (GitHub Pages source: `main`, `/`). A Pages API “building” state or an older successful deploy is not confirmation that the latest commit is live.
