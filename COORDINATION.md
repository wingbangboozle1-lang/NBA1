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

## 0b. Session registry

| Session ID | Branch | Registered (UTC) | Status |
| --- | --- | --- | --- |
| `arena-7cfd203a` | `arena/7cfd203a-nba1` | 2026-11-13 | Build A, merged (PRs #10/#12/#13/#15/#17). PR #14 left open (conflicting). |
| `arena/91270bb6-nba1` | `arena/91270bb6-nba1` | 2026-11-13 | Build B, merged (PRs #16/#18). |
| `arena/c7fbc064-nba1` | `arena/c7fbc064-nba1` | 2026-11-14 (logged retroactively by `arena-0de855e5`) | Third build, PR #11 OPEN — conflicting with `main`; see V01. |
| `arena-0de855e5` | `arena/0de855e5-nba1` | 2026-11-14 | Integration follow-up session (current). Branch note: platform pins this session to `arena/0de855e5-nba1`; it may not create, switch to, or push to other branches, so session-`<id>`/`<task>` branch naming is satisfied by this single pre-named branch. |

---

## 0c. Task board — integration follow-up (`arena-0de855e5`)

| # | Task | Status | File scope | Notes |
| --- | --- | --- | --- | --- |
| V01 | Triage open PRs #11 and #14; log disposition | done | `COORDINATION.md`, `review.html` | Neither may be merged from this session: platform forbids pushing to other sessions' branches, and both are CONFLICTING. PR #14's content incorporated into §6.1 and PR closed as superseded; PR #11 left open and flagged (would overwrite Build A's dashboard). See §4b. |
| V02 | Execute cross-session request R1 (nav link from root dashboard to `docs/b/index.html`) | done | `index.html` (root, Build A-owned — integration session authorised by R1) | Exact link text from R1 added under DETAIL PAGES. |
| V03 | Fresh official slate capture for the current 3-day window (2026-11-14 → 2026-11-17) from nba.com | done | `data/slate_2026_11_14.json`, `slate.html`, `scripts/build_slate_refresh.py`, `data/originated_lines_refresh.json` | 27 games, records, venues, season leaders, first 11/14 injury designations (07:30 PM ET edition). RecordLine-1 (unchanged constants) + engine-v0 totals → 23 paper picks. All 30 captured records cross-checked against teams_advanced (independent official capture) — exact match. |
| V04 | Full-tree verification re-run (all verify scripts, link checks, JSON validity, live-site smoke test) | done | verification outputs in `COORDINATION.md` | `scripts/verify_all.py` PASS (builders + checker + data audits; 132 slate rows sourced). |
| V05 | Final integration PR → `main`, merge, confirm Pages deploy, record publish result | in progress | PR from `arena/0de855e5-nba1` | Flagged/unverified items do not block the merge. |

## 4b. Open-PR triage (2026-11-14, `arena-0de855e5`)

Both PRs open at the start of this session were CONFLICTING with `main`. This session cannot push
to other sessions' branches, so neither could be rebased/merged directly.

| PR | Owner | Contents | Disposition |
| --- | --- | --- | --- |
| #14 | `arena-7cfd203a` | Docs-only: publish records for PRs #10/#12/#13 + post-publish defect log (3 defects that survived every automated gate) | **Content incorporated verbatim into §6.1 below by the integration session; PR closed as superseded** with a comment crediting the source. No work discarded. |
| #11 | `arena/c7fbc064-nba1` | Third parallel build (35 files): `src/nba1/` engine, its own root `index.html`/README/COORDINATION.md, docs pages colliding with Build A's paths, own data files | **Left OPEN, flagged for review, not merged.** Merging as-is would overwrite Build A's root dashboard and snapshot pages (same collision class previously resolved by namespacing Build B to `docs/b/`). Recommended path: its owner (or a future integration session with branch access) rebases onto `main` and namespaces to `docs/c/`, preserving the work. Published on the Flagged for Review page: `review.html`. |

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
| 2026-11-14T00:48Z | `arena-0de855e5` | Session registered; claimed V01–V05. Found two builds already merged and live, plus two open CONFLICTING PRs (#11, #14). |
| 2026-11-14T00:48Z | `arena-0de855e5` | V03: fresh official capture — 27 window games (11/14: 5, 11/15: 9, 11/16: 8, 11/17: 5) from nba.com schedule + games pages; season leaders; first 11/14 injury designations from the league PDF 11/13 07:30 PM ET edition (5 teams NOT YET SUBMITTED). Ten PDF rows with lost team cells attributed only via official roster pages. |
| 2026-11-14T00:55Z | `arena-0de855e5` | V03 integrity gates: all 30 captured records match `teams_advanced_2026_27.json` (independent official capture) exactly; per-date counts match the official calendar strip. RecordLine-1 (unchanged constants) → 23 paper picks (5 provisional on missing opposing reports); engine-v0 totals added (HCA=0, flagged). A first build double-processed 2026-11-14 and briefly under-counted B2B games (7 vs 12); fixed and re-run before any commit. |
| 2026-11-14T01:00Z | `arena-0de855e5` | V01/V02/V04: R1 nav link added to root `index.html`; PR #14 content incorporated (§6.1) and PR closed as superseded; PR #11 left open and flagged; integration addenda published on `review.html` (E-09–E-12) and `suggestions.html` (items 7–9); `scripts/verify_all.py` PASS on the full tree. | |

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

## 6.1 Post-publish defect log (content of PR #14, incorporated verbatim by `arena-0de855e5`)

Three defects survived every automated gate and were only caught by reading the live HTML. All
three are the same class of error — a plausible number typed into prose instead of looked up —
and all three were fixed by deriving the value rather than correcting it.

| # | Defect | Why the gates missed it | Fix |
| --- | --- | --- | --- |
| 1 | The bootstrap luck gate passed on a 7–0 record. With no losses every resample is all-wins, so the 5th percentile of ROI is trivially positive. | `verify_inline.py` checked that no *invalidated* strategy was marked validated. It never asked whether an individual gate was meaningful. | G3 now requires at least 5 losses before a pass counts, reports `degenerate` otherwise, and two new checks fail the build on a degenerate pass. Counts fell from 4/6 to 3/6 for three strategies. |
| 2 | Executive summary said "three absences are genuinely new" when the data has two. | The sentence was hand-written prose. | Now counted from `new_abs`. |
| 3 | Executive summary said "486 table rows" when the site has 667. | Same. | Now measured from the built pages at build time. |

Two further cosmetic defects were found in the same pass: an HTML entity that was being escaped
into literal text inside a card, and full float precision (`17.126`) leaking into prose.

**Lesson recorded for any future session:** a green test suite says the artefacts agree with each
other. It does not say the prose agrees with the artefacts. Reading the rendered output is a
separate check and it has now found five defects that no automated gate caught.
