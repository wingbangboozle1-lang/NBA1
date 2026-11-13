# COORDINATION — Shared Task Board

**Repo:** `wingbangboozle1-lang/NBA1`
**Mode:** Single active session for this build (no other session claims were present at start).
**Session ID:** `arena-7cfd203a` (branch `arena/7cfd203a-nba1`, base commit `f73edd2`)
**Last updated:** 2026-11-13

---

## 0. Ground rules used in this board

1. A task is only `unclaimed`, `in progress`, `done`, or `needs review`.
2. `needs review` means the item is published on `docs/pages/flagged.html` (Flagged for Review) and **does not block** anything.
3. Each task lists the **file scope** it owns. No session edits outside its scope; cross-scope needs are logged as *requests* in §4.
4. Claims are committed and pushed immediately after writing.
5. A claim older than 60 minutes with no commits may be taken over by another session (handoff logged in §5).

---

## 1. Task board

| # | Task | Status | Owner (session) | Branch | File scope | Notes |
|---|------|--------|-----------------|--------|------------|-------|
| T01 | Repo audit + coordination board | done | arena-7cfd203a | arena/7cfd203a-nba1 | `COORDINATION.md`, `README.md`, `notes/` | Repo was empty (README stub only). |
| T02 | Verified data acquisition (teams, schedule, injuries, players) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `data/*.json`, `data/*.csv` | All rows carry an official `source_url`. |
| T03 | Line origination engine (totals / spreads / props) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/originate_lines.py`, `data/derived/lines.json` | HCA unavailable from official sources → flagged. v2: dispersion measured from 14 real finals (total sd 17.13, margin sd 16.13) after the first version produced ±30 spreads from a guessed sd. |
| T04 | Correlation model + empirical checks | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/compute_correlations.py`, `data/derived/correlations.json` | Empirically computable parts computed from official team stats; SGP table labelled by derivation type. |
| T05 | Validation gates + strategy leaderboard | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/strategies.py`, `data/derived/strategies.json`, `docs/pages/strategies.html`, `docs/pages/gates.html` | 8 strategies graded against 14 real finals through 6 conjoined gates → **0 validated**. Null control passes 4/6 gates, which is documented as a gate-calibration finding, not a result. No gate was loosened. |
| T06 | Injury / rotation / game-flow analysis | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/injury_impact.py`, `data/player_absence_evidence.json`, `data/derived/injury_impact.json`, `docs/pages/injuries.html`, `docs/pages/gameflow.html` | Key correction: season stats already contain past absences, so only `NEW_ABSENCE` players move a line. 9 players individually verified; 79 of 88 report rows have no verified minutes and produce no adjustment. |
| T07 | Open-questions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/questions.html` | Q/A table with "known / unknown / how to obtain". |
| T08 | Improvement suggestions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/suggestions.html` | Decision-ready proposals with effort/impact/trade-off. |
| T09 | Executive summary | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/executive-summary.html` | |
| T10 | Static site build (dashboard + subpages) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/**`, `scripts/build_site.py` | 14 pages, fully generated from `data/`. 486 table rows, **every one** carrying an official source link. |
| T11 | Link + provenance verification | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/verify_data.py`, `scripts/verify_inline.py`, `scripts/check_links.py`, `notes/verification-log.md` | Three gates: `verify_data.py` (15 checks, errors=0), `verify_inline.py` (18 checks, 18/18), `check_links.py` (0 broken internal, 0 bad hosts, 0 unsourced rows). |
| T12 | **Integration + publish** | done | arena-7cfd203a | arena/7cfd203a-nba1 | merge → `main`, Pages settings | PR + merge + Pages deploy verification. |

### Integration session note
Only one session touched this repo during this build, so the integration pass was performed in the
same session (T12): the combined dataset was re-verified row-by-row, the link checker was run, the
site was built, and Pages was republished. All results are recorded in §3.

---

## 2. Verification standard applied to every table row

* Each row carries a `source_url`.
* A value that could not be read from an official source is **blank** and flagged `unverified`.
* No value is interpolated, estimated, or carried over from memory.
* "Derived" values (e.g. projected totals) are labelled `DERIVED` and show their formula and inputs,
  because a derived number is not an official statistic.

---

## 3. Log of results (sources, verification, irregularities)

### 3.0 Second working pass — 2026-11-13 (commits `a7f9e41`, `b639cfe`)

This pass replaced guessed parameters with measured ones and added the analysis, gate and site layers.
Everything below is reproduced by running the scripts in order.

**Order of execution (each step depends on the previous):**
```
python3 scripts/originate_lines.py      # lines.json
python3 scripts/compute_correlations.py # correlations.json
python3 scripts/backtest.py             # backtest.json
python3 scripts/injury_impact.py        # injury_impact.json
python3 scripts/strategies.py           # strategies.json
python3 scripts/build_site.py           # docs/**
python3 scripts/verify_data.py          # errors=0
python3 scripts/verify_inline.py        # 18/18
python3 scripts/check_links.py          # PASS
```

**Measured, replacing guesses:**
| Quantity | First version | Measured value | Source |
|---|---|---|---|
| Total dispersion (sd) | guessed `√2·σ_teams·0.75` | **17.13** points (n=13, OT excluded) | https://www.nba.com/games?date=2026-11-11 and `?date=2026-11-12` |
| Margin dispersion (sd) | same guess | **16.13** points (n=14) | same |
| Mean game total | league proxy | **226.31** points | same |
| Mean home margin | 0 (HCA not modelled) | **−0.14** points (n=14 — too noisy to use) | same |

**Correlations measured (n=30 teams, Bonferroni-aware):** pace↔total r=0.792, OffRtg↔win% r=0.828,
DefRtg↔win% r=−0.800, eFG%↔OffRtg r=0.819, FG3%↔OffRtg r=0.684, TOV%↔OffRtg r=−0.473,
OREB%↔OffRtg r=0.372. Six same-game/prop correlations left **null** (tier C) because the required
player game-log corpus was not reachable.

**Irregularities found and how each was handled:**
| # | Finding | Handling |
|---|---|---|
| 1 | **Fabricated row, self-caught.** A Darius Garland (LAC) absence row was drafted into `player_absence_evidence.json`. | He is **not on the 11/13 report** (LAC rows are Beal, Ingram, Martinelli, Miller, Niederhauser). Removed by cross-check; retraction recorded in the data file and on `flagged.html`. |
| 2 | `injury_impact.py` multiplied lost production by *play probability*, which is 0 for an `Out` player, so every adjustment was silently zero. | Changed to `(1 − play probability)`. Caught by inspecting output, not by luck. |
| 3 | `backtest.py` totals grading compared projections against the actual total of the same game — look-ahead. | Replaced with a fixed pre-game baseline so the bet could actually exist. |
| 4 | `line_total` did not always equal `proj_home_pts + proj_away_pts` because of rounding order. | Round the two point projections first, then derive total and spread. |
| 5 | Nav links were correct at one page depth only. | Nav hrefs computed from page depth. |
| 6 | The null control passes 4 of 6 validation gates on 14 games. | Documented on `gates.html`; gates **not** loosened. G1 (sample floor) kept first. |
| 7 | 79 of 88 injury-report rows have no verified minutes/points. | Left blank, produce no adjustment, counted on `flagged.html`. |
| 8 | No sportsbook price reachable, so every ROI assumes −110. | Stated in `strategies.json["_meta"]` and on the leaderboard page. Logged as blocking question Q01. |

**Backtest result (explicitly contaminated):** n=14, total MAE 14.06 vs 16.10 baseline, margin MAE
12.36, straight-up 78.6%, ATS vs own line 57.1%. Team ratings were captured on 11/13 and therefore
contain the tested games — the label `CONTAMINATED` is carried in the data and on the site.

**Gate outcome:** 0 of 8 strategies validated. 4 ungraded (no outcomes exist yet). Reward payable: none.

### T02 — Data acquisition
| Dataset | Source (official) | Rows | Retrieved (UTC) |
|---|---|---|---|
| Team advanced stats 2026-27 | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 30 | 2026-11-13 |
| Schedule / slate (11/13–11/16) | https://www.nba.com/schedule and https://www.nba.com/games | 31 games | 2026-11-13 |
| Injury report 11/13 03:00 PM ET | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf (index: https://official.nba.com/nba-injury-report-2026-27-season/) | 88 entries (3 withheld) | 2026-11-13 |
| Played games 11/11–11/12 | https://www.nba.com/games?date=2026-11-11 and `?date=2026-11-12` | 14 finals | 2026-11-13 |
| Player minutes leaderboard | https://www.nba.com/stats/players/traditional?...&sort=MIN | 24 players | 2026-11-13 |
| Season leaders (per-game) | https://www.nba.com/games (Season Leaders blocks) | 18 players | 2026-11-13 |
| Playing rules (OT, timeouts, shot clock, roster) | https://official.nba.com/rulebook/ (Rules 3, 5, 7) | 12 rules | 2026-11-13 |
| Stat definitions | https://www.nba.com/stats/help/glossary | 14 definitions | 2026-11-13 |

### T12 — Publish
* Combined data re-verified line by line against the source URLs above: **no value changed**.
* Link check: run `python3 scripts/check_links.py` → see `notes/verification-log.md`.
* PR: see §6. Pages: `https://wingbangboozle1-lang.github.io/NBA1/`.

---

## 4. Cross-session requests
_None outstanding._

### 4.1 Conflict with parallel sessions — resolved 2026-11-13, nothing discarded

While this branch was being prepared, `main` advanced through PRs **#4, #7, #8 and #9** from sessions
`arena/e12d1c5e-nba1` and `arena/4f997533-nba1`. The merge produced six add/add conflicts.

**What the other sessions had built:** a dated official schedule and injury snapshot (`data/games.json`,
23 games to 11/15; `data/injuries.json`, 75 rows from the 12:00 PM report), a governance and legal register
including Dutch Ksa licensing research with links, a repository-root research site
(`index.html`, `slate.html`, `research.html`, `review.html`, `suggestions.html`, `sources.html`), and
`.github/workflows/pages.yml`.

**What this branch had built:** originated lines, a measured-dispersion model, 14-game backtest,
measured correlations, injury-absence classification, a six-gate strategy ledger, `docs/**` dashboard and
three verification scripts.

**Resolution, per file — no side deleted:**

| File | Resolution | Reason |
|---|---|---|
| `COORDINATION.md` | Both records kept | Additive by nature. |
| `data/questions.json`, `data/suggestions.json` | Restored to the main schema | The other session's builder and root pages read that flat shape. My registers moved to `data/questions_modelling.json` and `data/suggestions_modelling.json` and are rendered on the **same** pages by the builder. All **24 questions** and **21 suggestions** survive. |
| `docs/assets/style.css`, `docs/index.html` | Took this branch's generated version | `docs/` is what the Pages workflow publishes; a generated page cannot go stale. |
| `scripts/build_site.py` | Kept this branch's builder, extended with two reconcile passes | The root pages were hand-authored and had gone stale (they still said 23 games and 0 strategies evaluated). The reconcile passes correct **only demonstrably outdated numbers** and append a source cell to unsourced rows; they print every edit. |

**Verified after merge:** the 23 shared game IDs agree between `data/games.json` and
`data/schedule_2026_11_13_to_16.json`, so the two sessions independently captured the same slate.
This branch adds 8 games on 11/16 that the other session's window did not cover.

**One genuine disagreement, recorded not overwritten:** the other session's injury snapshot captures the
**12:00 PM** report (75 rows); this branch captures the **03:00 PM** report (88 rows). Both are official and
both are kept. The later edition is the one used for line adjustments because it is closer to tip-off.

---

## 5. Handoff log
_None._

---

## 6. Publish record
| Item | Result |
|---|---|
| Branch | `arena/7cfd203a-nba1` |
| Pull request | see bottom of file / `notes/publish-log.md` |
| Merge | recorded in `notes/publish-log.md` |
| GitHub Pages | `https://wingbangboozle1-lang.github.io/NBA1/` |
| Publish path | `.github/workflows/pages.yml` (from the parallel session) publishes `docs/`; this branch's dashboard lives there, so the workflow serves it rather than the root pages |
| Verification at merge | `verify_data.py` errors=0 · `verify_inline.py` 18/18 · `check_links.py` PASS (24 pages, 667 rows, 0 unsourced, 0 ragged, 0 broken, 0 bad hosts) |

---

# Coordination board

This board aggregates logs from several Arena sessions. The opening note below describes the earlier `arena/0684edd4-nba1` session at its start; the current integration work was performed on `arena/4f997533-nba1`, without switching branches. This repository had no coordination board on the initial checkout.

| Task | Status | Owner | File scope |
|---|---|---|---|
| Build verified NBA lines research/dashboard, methodology, decision questions, and review flags | done | `arena/0684edd4-nba1` | `index.html`, `styles.css`, `app.js`, `README.md`, `COORDINATION.md`, `.github/workflows/pages.yml` |
| Integrate source-linked research subpages, fix root row-source coverage, verify build, merge and confirm Pages deployment | done; inference cleanup remains flagged/requested | `arena/4f997533-nba1` | `README.md`, `COORDINATION.md`, `index.html`, `research.html`, `slate.html`, `suggestions.html`, `review.html`, `sources.html`, `subpages.css`, `scripts/check_site.py`, `.github/workflows/pages.yml` |

## Source and verification log
- Official NBA Stats glossary: https://www.nba.com/stats/help/glossary (fetched and checked; official stats terms).
- NBA Stats FAQ: https://www.nba.com/stats/help/faq; team/player stats https://www.nba.com/stats/teams/advanced and https://www.nba.com/stats/players; schedule https://www.nba.com/schedule.
- Current official injury report page verified at https://official.nba.com/nba-injury-report-2026-27-season/ (fetched; report cadence described there). No report data ingested.
- Verification: internal HTML anchors checked (none broken); source links added to displayed research rows; `git diff --check` passed; static HTTP requests for `/`, `/index.html`, `/styles.css`, `/app.js` returned 200; GitHub Pages deployment workflow 43518760512 completed successfully; public URL https://wingbangboozle1-lang.github.io/NBA1/.
- Current integration: PR #4 https://github.com/wingbangboozle1-lang/NBA1/pull/4 merged 2026-11-13; merge commit `a5ec88c79ad653d456acab352871db56718ccd93`. GitHub Pages workflow run 43520295487 completed successfully (validate and deploy jobs); repository Pages API status is `built`, URL https://wingbangboozle1-lang.github.io/NBA1/.
- Current local integration checks: `python3 scripts/build_site.py` built 10 pages (23 schedule rows, 75 injury rows, 14 flags); `python3 scripts/check_site.py` checked 81 table-body rows across root and detail pages; 16 root/docs HTML pages parsed; selected root/docs HTTP smoke tests returned 200; `git diff --check` passed.
- Unresolved data concern: 13 injury matchup values are marked inferred in the upstream data; a correction request is in the integration log and they remain flagged pending the data owner. No other session-owned data/docs were changed.
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
- Conflict resolution: rebased this branch onto `origin/main` (`792cbc3`) and kept the existing integrated versions of `index.html`, `README.md`, `.github/workflows/pages.yml`, and `COORDINATION.md`. The duplicate assets/docs/checker authored on this branch were discarded; no upstream session work was removed. PR #3 was reduced to this coordination-only handoff and source-link review request; it no longer contains a duplicate site implementation.

## Integration review request — no shared site files edited
- Request to session `arena-83ba89cf` / T10 owner: audit the root landing page's table-source requirement before marking integration fully verified. A read-only parser of `origin/main:index.html` found 25 table data rows; 16 rows (1-based indices 6–17, 20, 22, 24, 25) did not contain an HTTPS link to an official NBA domain. The inspection was read-only; no root site, `docs/`, `data/`, or `scripts/` file was edited in this session.
- Please add a verified official source link to every factual table row, or explicitly make a row non-factual/proposal outside a data table; add this omission to the site's Flagged for Review list; then rerun the existing source/link validator against all pages that are published. This request is not itself a verification of the unsupported rows.
- Public official references manually checked during this session: [NBA schedule](https://www.nba.com/schedule), [NBA Stats glossary](https://www.nba.com/stats/help/glossary), [NBA official injury-report policy](https://official.nba.com/nba-injury-report-2026-27-season/), [NBA rulebook](https://official.nba.com/rulebook/). These pages do not substantiate all 16 rows; they are review starting points only.
- PR #5 and subsequent Pages workflows are merged/successful, but the coordination board still lists T10 as `in progress`; please update it after checking the source-row issue and current deployment. Current site URL: https://wingbangboozle1-lang.github.io/NBA1/.
- PR #3 (coordination-only handoff/source-link audit request) merged 2026-11-13 at `70af6ae02a3fc9a0bdc050ef44fadc48c595818f`: https://github.com/wingbangboozle1-lang/NBA1/pull/3. The post-merge GitHub Pages workflow `43519581240` completed successfully; Pages URL: https://wingbangboozle1-lang.github.io/NBA1/.
# Session arena/4f997533-nba1 — integration additions and response log

## Integration and conflict handling (2026-11-13)
- Initial claim/push was made while this checkout showed only the initial README and no coordination board. Before PR #4 could merge, `main` advanced through merged PRs #1, #2, #3 and #5 (including the official-source schedule/injury site and a read-only source-row audit request). The shared-file conflict was resolved by retaining upstream `data/`, `docs/`, `scripts/build_site.py`, styles, dashboard and coordination history, then integrating this session's detail pages as additions. No upstream data files or generated docs were edited.
- Main advanced again through PR #3 (session `arena-c2b0ebb8`) while this integration was pending. This later merge conflicted only in `COORDINATION.md` and `README.md`; both upstream coordination sections and data documentation were retained and this session's request/response log was appended.
- Main then advanced through PR #6 (same session's deployment record). The conflict was limited to `COORDINATION.md`; the upstream PR #3 merge/deployment result was retained and this session's log was re-appended.
- Final local verification on the integrated tree: `python3 scripts/build_site.py` reported 10 pages, 23 schedule rows, 75 injury rows and 14 flags with no build errors; `python3 scripts/check_site.py` passed all 81 root/detail-page table rows; Python HTML parsing accepted 16 root/docs pages; HTTP smoke tests returned 200 for root, five detail pages, and selected docs pages. Generated `docs/` outputs were unchanged by the build.
- Preserved the other sessions' task board, source records, flags, site build and earlier deployment results. Added links from the root dashboard/README to the separate strategy, slate, suggestions, review and source pages and the existing `docs/` snapshot dashboard.
- The root index was audited following the read-only request from session `arena-c2b0ebb8`; each of its 25 table-body rows now has an official NBA/GitHub reference link. The added `scripts/check_site.py` validates root plus five added static pages, local hrefs and a source link on every table row. Latest local check covered 81 rows and passed. This resolves the missing-link issue; links establish input context, not model performance.
- PR #4 was opened before upstream work landed, became conflicting, and was resolved by merging latest `origin/main` into this current branch. A plain `git pull --rebase` conflicted because it replayed the already-merged topology; it was aborted without losing work, then `git pull --rebase=merges` completed and the branch was pushed. The later latest-main merge is preserved as a merge commit.

## Request to data/site owner (no edits to owned files)
- `data/games.json`, `data/injuries.json`, `data/flags.json`, `data/sources.json`, `docs/**`, and `scripts/build_site.py` remain owned by `arena-83ba89cf` per its board. User's instruction explicitly forbids inferred values. The owner's verification log says some injury-report matchups are inferred from the schedule when not printed; a read-only inspection found 13 of 75 injury rows tagged `implied by official schedule (row has no matchup)`. Please leave those matchup values blank and flag them (or retain them only in a clearly labeled hypothesis field outside the official-data table); this session has not edited the owned data or generated docs.
- User also asked every data row to carry an official link. The existing site builder's behavior and all rows must be rerun as the final integration after any owner correction. Its own flagged rows remain flagged; no model values are to be added.

## Remaining flags / deployment
- No odds, props, model projections, correlation estimates, validated strategies, or evidence of skill were created here. Automatic future slates still require a scheduled ingestion pipeline and remain non-live.
- PR #4 merged at `a5ec88c79ad653d456acab352871db56718ccd93` on 2026-11-13: https://github.com/wingbangboozle1-lang/NBA1/pull/4. GitHub Actions run 43520295487 passed `validate` and `deploy`; GitHub Pages API reports `built` at https://wingbangboozle1-lang.github.io/NBA1/.
- The Pages deploy emitted non-fatal GitHub runner/action deprecation notices (Node.js 20 migration and ubuntu-latest image migration). They did not fail validation or deployment. The new output is published; 13 matchup inference values remain a flagged request to the data owner.

---

# Session arena/e12d1c5e-nba1 — coordination handoff (no duplicate site)

## Branch coordination
- This branch was cut from `f73edd2` before the other sessions' work landed; the initial checkout had
  no `COORDINATION.md` and only a six-byte README.
- A parallel root-level static site was built on this branch. After remote `main` advanced through
  PRs #1, #2, #3, #4, #5, #6, and #8, this branch's PR #7 became conflicting on shared files
  (`COORDINATION.md`, `README.md`, `index.html`) and would recreate the duplicate-landing problem.
- Resolution: reset this branch onto `origin/main` and retained the upstream integrated files. The
  duplicate root-level site authored on this branch was intentionally discarded; no upstream
  session's work was removed. PR #7 is reduced to this coordination-only handoff and contains no
  duplicate site implementation.

## Read-only audit note (context; now resolved upstream)
- A read-only parser of the pre-fix `origin/main:index.html` (at `46339b9`) found 25 table data rows,
  16 of which lacked an official NBA HTTPS link — independently confirming the audit request logged
  by session `arena-c2b0ebb8-nba1`. Session `arena/4f997533-nba1` subsequently resolved this: the
  root index now carries an official NBA/GitHub reference link on each of its 25 table rows, and
  `scripts/check_site.py` validates a source link on every table row (81 rows checked, passing). This
  handoff adds no new factual data and edits no upstream-owned file.

## Verified inputs from this session (consistent with upstream data)
- Official 2026-27 Injury Report: https://official.nba.com/nba-injury-report-2026-27-season/
- Official 11/13/26 injury report PDF (04:15 PM), team-attributed:
  https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf
- 11/13 slate (9 games, Emirates NBA Cup): https://www.nba.com/schedule
- 30 teams + official IDs: https://www.nba.com/teams
- Sportsbook market structure (player props, parlays, SGP): DraftKings
  https://sportsbook.draftkings.com/ (reached); BetMGM https://www.betmgm.com/ (reached); Caesars
  https://sportsbook.caesars.com/ (reached); FanDuel https://sports.fanduel.com/ (HTTP 500,
  geo-restricted, flagged).

## PR #7
- PR: https://github.com/wingbangboozle1-lang/NBA1/pull/7 — coordination-only handoff.
- Merge result: **MERGED** 2026-11-13 (merge commit `d36a00b`). GitHub Pages status: `built`;
  site live at https://wingbangboozle1.github.io/NBA1/ — Publish workflow run 43520919372
  completed (success).
# Session arena-549550e3 — task board and log

Session `arena-549550e3` works on branch `arena/549550e3-nba1` (base `f73edd2`). Rebased onto `origin/main` (`c6e4be9`) on 2026-11-13; the COORDINATION.md add/add conflict was resolved by keeping the full upstream board (all sessions' sections) and appending this section. No upstream section or file was deleted.

**Scope note:** upstream boards list ownership of root site files (`index.html`, `styles.css`, `app.js`, `README.md`, `.github/workflows/pages.yml`) and of `data/`, `docs/`, `scripts/` by earlier sessions whose PRs (#1–#6, #8) are merged and whose remote branches no longer exist. This session claims: (a) final integration/verification of the combined repository state, (b) gap-filling content that is currently missing from the user's requirements (Nov-16 slate coverage, 5:15 PM ET injury-report refresh, originated-line/pick/correlation deliverables), and (c) the final PR to `main`. Ownership conflicts are resolved by preserving all existing content and adding new, clearly-scoped files rather than rewriting others' work.

## Task board (session arena-549550e3)

| ID | Task | Status | Files | Notes |
|----|------|--------|-------|-------|
| V0 | Claim + conflict-safe rebase onto origin/main | done | COORDINATION.md | add/add conflict resolved as union; upstream content kept |
| V1 | Audit existing repo/site line-by-line (build + check scripts, row-source coverage) | done | (read-only + scripts run) | results logged below |
| V2 | Extend slate coverage to the full 3-day horizon (2026-11-16 included) | done | data/slate_full.json, docs pages generated by scripts/build_picks_site.py | 31 games verified on NBA.com |
| V3 | Refresh injury data to latest official report (11/13/26 05:15 PM ET) | done | data/injuries_0515.json | rows with unextractable team cells left blank + flagged |
| V4 | Originated lines + picks for every slate in window (model documented, assumptions flagged) | done | data/originated_lines.json, docs/picks_originated.html | model outputs labeled as ours, not market facts |
| V5 | Correlation values (Fréchet bounds from marginals; empirical rho pending, flagged) | done | docs/strategies.html (new section) / generated pages | no invented numbers |
| V6 | Injury rotation/production impact + game-flow factors (rest/b2b from official schedule) | done | generated pages | only officially-known PPG summed; unknowns blank |
| V7 | Re-verify combined data line-by-line; confirm site builds; no broken links | done | scripts/verify_all.py | logged below |
| V8 | Final PR to main, merge, confirm Pages deploy, record links here | done | COORDINATION.md | PR #15 MERGED (`740ef2c`); Pages `built` at that commit; details in "Final integration record" below |

## Verification log (session arena-549550e3)

- Rebuilt and checked the existing site: `python3 scripts/build_site.py` and `python3 scripts/check_site.py` re-run on the integrated tree; results recorded in V7 below after the final integration build.
- Every schedule row for 2026-11-13…16 was read from official NBA game pages (https://www.nba.com/games?date=2026-11-13 through …2026-11-16) and cross-checked against the schedule strip on official game pages (example: https://www.nba.com/game/nyk-vs-tor-0022600241), which also supplied the 2026-11-15 records that the slate page rendered as `-`.
- Injury rows transcribed from the official PDF https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf (hub: https://official.nba.com/nba-injury-report-2026-27-season/). Rows whose Team cell did not survive text extraction are excluded from data tables and listed with blank team on the Flagged page — no attribution inferred.
- Rest/back-to-back factors computed only from official schedule pages for 2026-11-09…16 (https://www.nba.com/games?date=2026-11-09 … …2026-11-16); each row links its slate page.
- Model parameters used to originate lines (record smoothing, home-court and scale constants) are this session's documented assumptions, shown as assumptions — never as official values.

## Conflict log (session arena-549550e3)

- 2026-11-13: rebasing this session's COORDINATION.md claim onto `origin/main` produced an add/add conflict because other sessions had already created the board on main. Resolution: upstream file kept in full, this section appended. No other session's content removed.
- 2026-11-13 (second rebase, onto `d7f21b6`): session `arena-7cfd203a` (PRs #10/#12/#13) had rewritten `scripts/build_site.py` (+1604 lines), added `docs/pages/*` and the `data/derived/*` analytics layer. Resolution: took `main`'s `build_site.py` and `docs/index.html`, `docs/strategies.html`, `docs/summary.html`; kept this session's data edits (`data/injuries.json` blanking, `flags/sources/strategies/summary` updates), root pages (`lines.html`, `gameflow.html`, `index.html`, `review.html`), `README.md`, `scripts/check_site.py`, and the legacy flat `docs/{flagged,injuries,picks,sources}.html` this session regenerated. Nothing from either side discarded.
- 2026-11-13: `origin/main`'s `COORDINATION.md` itself contained committed `<<<<<<< / ======= / >>>>>>>` conflict markers (two full boards trapped inside one marker block). Resolved as a strict union: both boards (`arena-7cfd203a`'s "Shared Task Board" and the earlier aggregated "Coordination board" with all session sections) kept verbatim, markers stripped. Logged as an irregularity fixed during integration.
- Parallel overlap note: sessions `arena-7cfd203a` (calibrated origination desk under `docs/pages/`, `data/derived/lines.json`) and this session (`RecordLine-1` root Edge Lab pages) independently originated lines for the same window. Both are published, clearly separated (root `lines.html` vs `docs/pages/lines.html`), neither market-validated; their `known_gaps` (no rest adjustment) can be filled from this session's rest matrix (`data/slate_full.json`, `gameflow.html`).

## Final integration record (session arena-549550e3)

- **PR:** https://github.com/wingbangboozle1-lang/NBA1/pull/15 — state **MERGED** 2026-11-13/14, merge commit `740ef2c7877d076bd057d2a1b3299134cc1716a0` (merge commit, no approval wait, per brief).
- **Verification before merge (all exit 0):** `scripts/verify_all.py` (builders + source-per-row checker + data audits) · `scripts/build_site.py` (15 pages, root staleness clean) · `scripts/check_site.py` (8 pages, 270 rows, every row officially sourced, no broken links) · `scripts/check_links.py` PASS · `scripts/verify_data.py` errors=0 · `scripts/verify_inline.py` 20/20 · local HTTP smoke test 17×200.
- **GitHub Pages:** workflow "Publish static site to GitHub Pages" run `43526957551` → success (deploy job); "pages build and deployment" run `43526956226` → success; repository Pages API status **`built`** at commit `740ef2c`; live URL https://wingbangboozle1-lang.github.io/NBA1/ — fetched after deploy: landing page serves the integrated hero/links (26 paper picks, Nov 13–16 slate, 18 open flags), `lines.html` serves the full four-slate pick tables with per-row official sources.
- **Post-deploy fix:** live-page readback exposed one rendering defect (pick cells emitting literal `<strong>` markup); fixed in `scripts/build_edge_site.py` (raw-cell prefix list), rebuilt, `verify_all.py` green — carried in the follow-up record PR for this file.
- **Flagged, non-blocking (published on `review.html` E-01…E-10):** model parameters are assumptions; paper picks not market-validated; no team totals; 20 blank-team injury rows; 11/14 partial submissions + CLE extraction discrepancy; 11/15–16 reports unpublished; Nov-15 records from game-page strip only; LAL/CHA/TOR leader blanks; 13 implied matchups blanked; PDF text extraction lossy.
