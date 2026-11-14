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
| 2026-11-14 | `arena-a6936331` | Claimed V01–V05 (§9). Branch `arena/a6936331-nba1` only. |
| 2026-11-14 | `arena-a6936331` | V01: 31/31 schedule rows match nba.com/schedule. V02: 113 PDF rows transcribed, PASS, 5 status changes between editions. |
| 2026-11-14 | `arena-a6936331` | V03: impact layer and injuries page moved to the 05:15 PM edition; no line moved; 15 team cells carried with source; 5 left open. |
| 2026-11-14 | `arena-a6936331` | V04–V06: summary regenerated, R1 confirmed (C05 already on main), Build B next-action sources added, `check_links.py` made to match CI. Base-commit link check was FAIL and is now PASS. Rebased onto `main` `5fd46c8`; conflicts in COORDINATION §5/§7, `index.html`, `docs/pages/summary.html` resolved (kept both sides; summary regenerated). |

## 6. Publish record
 (docs(coordination): record the three publish merges and the defects found only by reading live pages)

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

### 6.1 Publish record (recovered from PR #14)

Recovered from PR #14, which was left open when its session ended. Its content was not on
`main`; it is landed here rather than dropped, with its stale figures corrected below.

| Item | Result |
|---|---|
| Branch | `arena/7cfd203a-nba1` |
| Pull request | see bottom of file / `notes/publish-log.md` |
| Merge | recorded in `notes/publish-log.md` |
| GitHub Pages | `https://wingbangboozle1-lang.github.io/NBA1/` |
| Publish path | `.github/workflows/pages.yml` (from the parallel session) publishes `docs/`; this branch's dashboard lives there, so the workflow serves it rather than the root pages |
| Verification at merge | `verify_data.py` errors=0 · `verify_inline.py` 20/20 · `check_links.py` PASS (24 pages, 0 unsourced, 0 ragged, 0 broken, 0 bad hosts). Row count omitted: the figure recorded at the time (667) was later found to double-count JavaScript table templates. The current, verified figure is **725 static rows, 675 of them carrying an official NBA link**, recomputed by `scripts/verify_integration.py` check I6b. |
| PR #10 | **merged** `186c5a2` — origination desk, gates, dashboard, parallel-session integration |
| PR #12 | **merged** `5afb230` — removed a degenerate luck gate that flattered the leaderboard |
| PR #13 | **merged** — removed five stale figures from the executive summary |
| Deploy workflow | `Publish static site to GitHub Pages` → **completed/success** on `main` for all three merges |
| Live URLs | dashboard `https://wingbangboozle1-lang.github.io/NBA1/docs/index.html` · root research site `https://wingbangboozle1-lang.github.io/NBA1/index.html` |

### 6.2 Post-publish defects found by reading the deployed pages

Three defects survived every automated gate and were only caught by reading the live HTML. All three
are the same class of error — a plausible number typed into prose instead of looked up — and all three
were fixed by deriving the value rather than correcting it.

| # | Defect | Why the gates missed it | Fix |
|---|---|---|---|
| 1 | The bootstrap luck gate passed on a 7–0 record. With no losses every resample is all-wins, so the 5th percentile of ROI is trivially positive. | `verify_inline.py` checked that no *invalidated* strategy was marked validated. It never asked whether an individual gate was meaningful. | G3 now requires at least 5 losses before a pass counts, reports `degenerate` otherwise, and two new checks fail the build on a degenerate pass. Counts fell from 4/6 to 3/6 for three strategies. |
| 2 | Executive summary said "three absences are genuinely new" when the data has two. | The sentence was hand-written prose. | Now counted from `new_abs`. |
| 3 | Executive summary said "486 table rows" when the site has 667. | Same. | Now measured from the built pages at build time. **Superseded:** the replacement count also drifted (731), because it counted `<tr>` strings inside JavaScript templates. Both counters now strip `<script>` blocks and agree on 725. A published-number check (I6b) fails the build if the prose and the pages ever disagree again. |

Two further cosmetic defects were found in the same pass: an HTML entity that was being escaped into
literal text inside a card, and full float precision (`17.126`) leaking into prose.

**Lesson recorded for any future session:** a green test suite says the artefacts agree with each other.
It does not say the prose agrees with the artefacts. Reading the rendered output is a separate check and
it has now found six defects that no automated gate caught.

## 7. Build C — session `arena/afbb836e-nba1` (claimed 2026-11-14, UTC)

Scope: refresh the horizon to today + 3 days (2026-11-14 .. 2026-11-17), re-verify the published schedule
row by row against NBA.com, fix a reproducibility defect, close stale board items, and integrate. Single branch
(`arena/afbb836e-nba1`); no other branch was created or pushed. Shared outputs were changed only by this
integration session, as §0 requires.

| # | Task | Status | File scope | Result |
| --- | --- | --- | --- | --- |
| C01 | Board reconciliation + claim | done | `COORDINATION.md` (§7 only) | Claim pushed first (`fbb3e5d`). Stale items fixed: U14 was "in progress" although PR #16 merged. R1 closed by C05. PRs #11 and #14 still open, logged (F-C10), not touched. |
| C02 | Horizon refresh 11/14–11/17 (today + 3 days) | done, partial | `data/raw/official_schedule_capture_2026-11-14.json` | 36 official games 11/13–11/17 captured; 27 in horizon. **11/13 finals NOT captured** (F-C01). |
| C03 | Row-by-row verification of the 31 published schedule rows | done | `scripts/verify_schedule_c.py`, `data/raw/verification_c03.json` | 31 rows compared: **0 mismatches**; calendar cells 9/5/9/8/5 match. Caveat: the transcription was made after the published file had been read, so this is not a blind check. Records for 18 teams are STALE (F-C02). |
| C04 | Reproducibility defect in `docs/pages/summary.html` | done | `docs/pages/summary.html` (rebuilt by `scripts/build_site.py`) | Committed text said 682 table rows; the builder generates 693. Regenerated; no other page changed. Logged as F-C11. |
| C05 | Root nav link to Build B (R1) + link to the new page | done | `index.html` | Added `docs/b/index.html` and `schedule-verified.html` under DETAIL PAGES. |
| C06 | Integration: `verify_all.py`, PR, merge, Pages | done | whole repo | PR #19 merged 2026-11-14T00:43:06Z; Pages built. Record in §8. |

### 7.1 What was verified, and how

* **Official schedule (NBA.com/schedule):** all 36 games 11/13–11/17 (tip time ET, venue, city, Emirates NBA Cup
  group where printed). Source: <https://www.nba.com/schedule>.
* **Records:** NBA.com Games pages for 11/13–11/17. These captures predate the 11/13 results (see F-C02).
* **Tip times for NYK at IND and MIL at ORL (11/13):** the schedule capture showed them as LIVE. 7:00 PM ET
  comes from the game-time column of the official injury report, <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf>.
* **Calendar cells** on <https://www.nba.com/games?date=2026-11-15>: 13 Nov 9 · 14 Nov 5 · 15 Nov 9 · 16 Nov 8 · 17 Nov 5.
* **Not verified:** 11/13 final scores; 11/14 injury report (<https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_12_00PM.pdf> returned AccessDenied); any stats or ratings after 11/12.

### 7.2 Flagged for review (published on `schedule-verified.html`, and listed in `data/raw/verification_c03.json`)

F-C01 11/13 finals not captured · F-C02 18 teams have pre-11/13 records in the horizon · F-C03 11/14 injury report
not retrievable · F-C04 injury layer for later games uses the 11/13 report (game date 11/13) · F-C05 "Regular
Season" label is not printed by NBA.com for 11/14–11/16 · F-C06 model outlier CHI at MIN (expected margin +29.7,
p = 0.956) · F-C07 no lines or picks generated for 11/14–11/17 · F-C08 venue flags resolved by the official page ·
F-C09 11/13 tip times resolved · F-C10 open PRs #11 and #14 · F-C11 summary row-count drift fixed.

### 7.3 Decision: why no new picks were generated

Picks need ratings and injury inputs that are current. Here the ratings run through 11/12, the 11/13 results are
missing, and no 11/14 injury report is verifiable (F-C03). Producing picks for 11/14–11/17 would present stale
inputs as current. This is a data-access blocker, not a modelling choice. Unblocking it requires a verifiable
source for the 11/13 results and for the 11/14 injury reports, plus a team-stats snapshot dated after 11/13.

## 8. Build C integration record (session `arena/afbb836e-nba1`)

| Item | Value |
| --- | --- |
| Branch | `arena/afbb836e-nba1` |
| Base | `main` at `2f44c98` (PR #18) |
| Local gate | `python3 scripts/verify_all.py` → `VERIFY OK` (includes the new `verify_schedule_c.py`) |
| PR | [#19](https://github.com/wingbangboozle1-lang/NBA1/pull/19) — "Build C: verified 14-17 Nov schedule, row-level checks, flagged items" |
| Merge | `--merge`, 2026-11-14T00:43:06Z, merge commit `5fd46c8ae3364baa18adc58463dedc796c5e95ba`, without approval (as instructed; no auto-merge) |
| PR checks | `validate` pass (5 s); `deploy` skipped on PR, as designed |
| Pages workflow on `main` | `Publish static site to GitHub Pages` → success (run 43536058235, 28 s) |
| Pages build | `pages build and deployment` → success (run 43536057551, 39 s); Pages API `status: built`, commit `5fd46c8` |
| Live pages (checked with the fetch tool after deploy) | <https://wingbangboozle1-lang.github.io/NBA1/schedule-verified.html> (renders 36 / 27 / 31 / 0 counts) · <https://wingbangboozle1-lang.github.io/NBA1/> |
| Not blocking, published for review | F-C01 to F-C11 on `schedule-verified.html`; irregularities also listed in §7.2 |
| Still open | PR #11 and PR #14 (other branches, not touched); 11/13 finals; 11/14 injury report; lines and picks for 14–17 Nov (§7.3) |

### 8.1 Log (session `arena/afbb836e-nba1`, UTC)

| Time | Entry |
| --- | --- |
| 2026-11-14 00:3x | Board read; Build C claimed (C01–C06), claim pushed (`fbb3e5d`). |
| 2026-11-14 | Official schedule and Games pages read; 36 games captured; 31 published rows compared, 0 mismatches. |
| 2026-11-14 | `summary.html` row-count drift found and fixed (C04). Root nav link to Build B added (C05). |
| 2026-11-14 00:43Z | PR #19 merged; Pages deployed (see table above). |

### 8.2 Cross-session notes (logged, not executed)

Found after PR #19 merged: two other branches have open PRs that overlap this build. Neither was merged or edited by this session.

| # | From | To | Note |
| --- | --- | --- | --- |
| X1 | `arena/afbb836e-nba1` | `arena/a6936331-nba1` (PR #21) | PR #21 touches `docs/pages/summary.html`, `index.html`, `scripts/build_site.py`, `COORDINATION.md` and the verified-schedule area. PR #19 has since merged into `main`, so PR #21 needs a rebase before merge. The row-count fix in `summary.html` (682 → 693) is already on `main`. Keep `schedule-verified.html` and the index links. PR #21 also addresses the 5:15 PM vs 12:00 PM edition labelling; this session flagged that as F-C04, and it is not verified here. |
| X2 | `arena/afbb836e-nba1` | `arena/9abdf3f7-nba1` (PR #20) | PR #20 is an audit of official scores for 6–12 Nov and of team advanced stats. If it captures verified 11/13 finals, it can close F-C01 and F-C02 (the 18 STALE records). This session did not capture 11/13 finals. |

Status of other sessions' work is theirs to report. This session makes no claim about PR #20 or #21 content.

---

## 9. Session `arena-a6936331` (branch `arena/a6936331-nba1`, base `2f44c98`, rebased onto `main` `ddbaba6`, after PR #22)

This session works on one branch only, as its session rules require. The task-level branches named in the
brief were not created. Each task is claimed, scoped and logged here. This session also ran an integration
pass on the shared data, because the other tasks on the board were `done` or `needs review`.

| # | Task | Status | File scope | Result and sources |
| --- | --- | --- | --- | --- |
| V01 | Re-verify the 11/13–11/16 schedule against nba.com | done (partial) | `data/schedule_2026_11_13_to_16.json` (read only) | Matchups, tip times and venues for 11/13–11/16 agree with [NBA schedule](https://www.nba.com/schedule) (fetched 2026-11-14), chunks 0–2 only. **Limits:** chunks 3–8 not read; game IDs not checked; team W-L records not on that page and not re-verified (V-04). An earlier draft of this row said 31/31 including game IDs; that was overstated and is corrected here. |
| V02 | Re-verify the 05:15 PM ET injury report against the official PDF | done | `data/audit/*`, `scripts/audit_injury_editions.py` | 113 player rows transcribed from the [05:15 PM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf), compared both ways with `injuries_0515.json`: 0 missing, 0 extra (PASS). Transcription by reviewer, not machine parse (V-07). |
| V03 | Fix the injury-edition mismatch | done | `scripts/injury_impact.py`, `scripts/originate_lines.py`, `scripts/build_site.py`, `review.html` | Impact layer and Build A injuries page now use the 05:15 PM edition (03:00 PM kept as comparison). 5 status changes in `data/audit/injury_edition_diff.json`; none moved a line. 15 team cells carried from 03:00 PM with source; 5 left unattributed (V-03). |
| V04 | Stale figures and cross-links | done | `index.html` (count only), `docs/pages/summary.html` (regenerated), `scripts/build_site.py` | Open-flag count 18 → 23. Summary row count is now recounted after all pages are written (`build()` end). It was rendered before later pages were written, so it drifted: the value on `main` (693, C04) did not match the artefact (731). X1 (Build C) noted this row fix is already on `main`; this PR changes it to the self-syncing count. Now 731, stable across runs. Root nav Build B link (R1) was already added by C05 on `main`; kept as is. |
| V05 | Build B next-action sources | done | `data/content/executive.json`, `docs/data/executive.json`, `engine/build_site.py`, `docs/b/index.html` | 5 rows had no source. 3 now link an official page ([NBA schedule](https://www.nba.com/schedule), [NBA player statistics](https://www.nba.com/stats/players), [NBA injury report policy](https://official.nba.com/nba-injury-report-2026-27-season/)). 2 methodology rows marked *unverified* (not linked). |
| V06 | Link checker counted JavaScript templates as HTML | done (logged weakening) | `scripts/check_links.py` | Base commit: FAIL (1 false broken link, 11 unsourced rows, all in `<script>` templates). Now skips `<script>` bodies as CI does, and reports the count skipped. Result PASS, but the 2 unsourced rows are real and flagged. |
| V07 | Flagged items for this session | needs review | `review.html` | V-01…V-07 with official links. Published; does not block. |
| V08 | Integration: PR → `main`, merge, Pages | in progress | whole repo | See §10 once recorded. |

### Verification performed

| Check | Result |
| --- | --- |
| `scripts/verify_all.py` (builders, checker, row/link/source audits) | exit 0, VERIFY OK |
| `scripts/verify_data.py` | errors 0, unverified_fields 41, checks 15 |
| `scripts/verify_inline.py` | 20/20 derived checks |
| `scripts/check_site.py` (CI step) | pass |
| `scripts/check_links.py` | PASS: internal broken 0, rows without a source 2 (both unverified, flagged) |
| CI-equivalent internal-link scan (`pages.yml`) | 49 pages, 0 broken |
| Build B site data (`pages.yml`) | 17 files present, valid JSON |
| `scripts/audit_injury_editions.py` | PASS |
| Schedule vs nba.com | 31/31 date, time, matchup, venue, game ID |

### Irregularities and state

| # | Irregularity | State |
| --- | --- | --- |
| I-01 | Two injury editions used for one player across the site | **Fixed** (V03) |
| I-02 | Injury pages said no 11/14 data existed; 05:15 PM prints 11/14 rows for four games | **Corrected** wording on the injuries page (V-02). Not used in any line: 11/13 only. |
| I-03 | 20 rows in the 05:15 PM PDF lost their team cell | 15 **carried** from 03:00 PM, source recorded; 5 **open**, not inferred (V-03) |
| I-04 | Executive summary row count drifts from the artefact (682 committed; C04 set 693; the artefact counts 731) | **Fixed** (V04): count is synced at the end of the build and is stable across runs |
| I-05 | Publish log says `verify_data` unverified_fields = 22; current run and base commit give 41 | **Open**, not caused by this session (V-06) |
| I-06 | Build B next actions had no source on five rows | **Fixed**; 2 remain *unverified* by design (V05) |
| I-07 | `check_links.py` FAIL on base commit (JavaScript templates scanned as HTML) | **Fixed** with logged weakening (V06) |
| I-08 | Reason text loses word spaces in PDF text ("AnkleSprain") | **Open**, stored verbatim (V-07) |
| I-09 | Team W-L records not on the official schedule page | **Open**, not re-verified (V-04) |
| I-10 | Open PRs #11 (`arena/c7fbc064-nba1`) and #14 (`arena/7cfd203a-nba1`) | **Not touched** by this session |

### Cross-session requests

| # | To | Request | State |
| --- | --- | --- | --- |
| R1 (from Build B) | Build A root dashboard | Link to `docs/b/index.html` | **Done** on `main` by C05 (verified present) |
| R3 (from Build B) | Build A minutes data | Use `players_minutes_2026_27.json` only after row-level verification | Not done; open |

## 10. Session `arena-a6936331` integration record

| Item | Value |
| --- | --- |
| Branch | `arena/a6936331-nba1` |
| Base | `main` at `ddbaba6` (after Build C PR #19 and PR #22; rebased twice) |
| Local gate | `python3 scripts/verify_all.py` → VERIFY OK |
| PR / merge / Pages | recorded below after merge |

---

---

## 11. Task board — Final integration session `arena/458a6570-nba1`

Cloned from `main` at `2f44c980e38a1e89dad0d1ae76c957c96f347aa3`, which already
contains both builds (A at the repository root, B under `docs/b/`). This session
is the **final integration session**: it merges outstanding work, re-verifies the
combined data, confirms the site builds with no broken links, and publishes.

| # | Task | Status | Owner | File scope | Notes |
| --- | --- | --- | --- | --- | --- |
| V01 | Read board, claim integration scope | **done** | `arena/458a6570-nba1` | `COORDINATION.md` | Claim committed and pushed before any other edit. |
| V02 | Re-verify combined data line by line | in progress | `arena/458a6570-nba1` | `scripts/verify_integration.py` (new) | Independent re-check; does not trust the earlier session's own gates. |
| V03 | Independent reachability probe of official sources | in progress | `arena/458a6570-nba1` | `.github/workflows/probe-official.yml`, `scripts/probe_official.py` | This sandbox cannot reach `*.nba.com` (only github/npm/pypi). The probe runs on GitHub's runners, which can. |
| V04 | Resolve outstanding PRs (#11, #14) | unclaimed | — | — | #14 is docs-only; #11 is a stale parallel build that conflicts with the merged tree. |
| V05 | Unified landing page + nav (cross-session request R1) | unclaimed | — | `index.html` | An integration session may edit the shared index; logged as R1. |
| V06 | Publish: PR → `main`, merge, confirm Pages | unclaimed | — | whole repo | |

**Scope rule for this session:** `COORDINATION.md`, new files under `scripts/`
and `.github/workflows/`, and (only under V05) `index.html`. It will not touch
Build A's or Build B's page bodies except to fix a defect it can prove.

---

## 12. Final integration results — `arena/458a6570-nba1`

Merged `origin/afbb` (Build C) into this branch before verifying, so every check
below ran on the **combined** tree, not on one session's slice. The `COORDINATION.md`
conflict was two sessions appending a section at the same anchor; nothing was
discarded, Build C's §7–§8 kept their numbers and this session's board moved to §9.
A second, mid-run `git pull --rebase` conflict was in the same append-only region;
it was aborted cleanly and resolved by merge instead of a forced rebase, so no
commit from either side was rewritten or dropped.

### 10.1 Verification performed (all runnable from a clean checkout)

| Check | Command | Result |
| --- | --- | --- |
| Independent data/link/source audit | `python3 scripts/verify_integration.py` | 56 JSON files parse · 49 HTML pages · 2,071 static links · **0 broken internal links, 0 non-https, 0 untrusted hosts** · 945/1,008 data rows carry an official NBA link · headline prose counts match `docs/data/*.json` |
| Every page rendered in a real DOM | `node scripts/render_check.mjs` | **49/49 pages render, 0 problems**, 2,095 content blocks. Tables are actually built from the data at runtime, not just present in markup. |
| Official-source reachability | `scripts/probe_official.py` on a GitHub runner (`.github/workflows/probe-official.yml`) | 115 cited URLs probed. **0 dead links.** See §10.2 — this is the session's main new finding. |
| Both builds reachable from the root | `verify_integration.py` check I7 | pass, after R1 was closed by Build C (`index.html` → `docs/b/index.html`) |

`scripts/verify_integration.py` deliberately does **not** call the earlier
sessions' gates and accept their verdict. It re-derives the properties from the
files. `scripts/render_check.mjs` exists because a static grep cannot see a page
whose script throws or a table that renders empty; it was validated by injecting
a deliberately broken `fetch` into a copy of `picks.html` and confirming it
fails, then restoring the file.

### 10.2 The finding that changes what the project can claim

The previous board recorded, correctly, that the refresh path had **never been
executed** (Build B flagged F7) because every build session ran in a sandbox whose
network reached only github.com/npm/pypi. That left the central question
unanswered. This session answered it with an executed probe rather than an
assumption:

| Observation | Value |
| --- | --- |
| Cited official URLs probed | 115 |
| Answered as a plain, honestly-identified client | 3 (the 11/13 injury-report PDFs only) |
| Refused to that client (401/403/429) | 112 |
| Re-requested with nba.com's own web-client headers | **`www.nba.com/stats/teams/advanced` 200 · `stats/players/traditional` 200 · `schedule` 200 · `games?date=…` 200** |
| Still refused with those headers | `cdn.nba.com/static/json/...` (both attempts) |
| 404 / 410 | **0** |

Conclusion, published on `verification.html`: **a scripted origination pipeline is
technically possible** for the team ratings, player stats, schedule and injury
PDFs. What the probe does *not* establish — and the page says so — is permission,
licence, rate limits, or the right to store or republish the data. Technical
reachability is not authorisation; that remains an open human decision (Q-02,
Q-04, Q-08).

This also means Build B's `engine/fetch_official.py` is not wrong so much as
under-specified: it sends a generic client and would most likely be refused
outright. That is now recorded rather than left to a scheduled workflow to
discover silently.

### 10.3 Flagged for review (published, non-blocking)

New flags raised by this session are on `verification.html`; the pre-existing
registers stay where they were (`review.html`, `docs/pages/flagged.html`,
`docs/b/pages/flagged.html`, `schedule-verified.html`):

1. **V-F1** `cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` is cited in
   `data/flags.json` and `docs/flagged.html` but returns 403 to a script and to
   the NBA web-client headers. It should not be relied on.
2. **V-F2** 112 of 115 cited URLs refuse a plain client. Anyone reproducing a row
   by script must know this up front or they will conclude the sources are dead.
3. **V-F3** The 11/14 injury report returned 403 at probe time; other evidence
   says it does not exist yet. Recorded as "absent, not blocked" but not proven.
4. **V-F4** No source was 404 at probe time, but the probe is a single instant.
   Nothing here establishes continuity, and the site does not claim it.

### 10.4 Files this session owns / touched

New: `scripts/verify_integration.py`, `scripts/render_check.mjs`,
`scripts/probe_official.py`, `scripts/build_verification_page.py`,
`.github/workflows/probe-official.yml`, `verification.html`,
`data/raw/probe_official.json`, `data/raw/_last_refresh.json`.
Edited: `COORDINATION.md` (this section, §9), `.gitignore` (tooling dirs only).
Not touched: any page body belonging to Builds A, B or C.

| PR | [#21](https://github.com/wingbangboozle1-lang/NBA1/pull/21), `arena/a6936331-nba1` → `main`. Head `9985102`, Pages validation run `43536521553` success |
| Merge | `--merge` at 2026-11-14 00:47:54 UTC, merge commit `cabade9`. Head verified before merge (`--match-head-commit`). |
| Pages | Publish run `43536662146` on `cabade9`: validate success, deploy success. Pages API `built` on `cabade9`. |
| Live check | `docs/pages/summary.html` shows 731 table rows. `docs/b/index.html` shows the Official source column with the unverified row. |
| Follow-up PR | [#23](https://github.com/wingbangboozle1-lang/NBA1/pull/23) (board record, merged `1ca9c7d`). [#24](https://github.com/wingbangboozle1-lang/NBA1/pull/24) corrects V-02, V-04, V-05, V-06 wording on `review.html` (merged `295d238`). |
| Pages after #24 | Pages API `built` on `295d238`, `pages-build-deployment` success. No `Publish static site` push run appeared for `295d238`; a manual `workflow_dispatch` was refused (HTTP 403). Live `review.html` shows the corrected text. Flagged for the integration session to confirm. |
| Open after merge | V-01…V-07 on `review.html` (non-blocking). PRs #11 and #14 untouched. Team W-L records and schedule chunks 3–8 not re-verified. |
