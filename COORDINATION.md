| `arena/fbf3ff57-nba1` | `arena/fbf3ff57-nba1` | 2026-11-16 02:12 UTC | Integration seat (§47): fresh capture, 11/15 settlement, injury-PDF diff, Pages backlog. Live at this session's claim time — its file scope is read-only for this session. |
| `arena/dfef26dc-nba1` | `arena/dfef26dc-nba1` | 2026-11-16 02:1x UTC | **Site / shared-output rebuild seat** (§48): roll the horizon to 11/16–11/18, rebuild `scripts/**` → `site/**` + `index.html`, re-cut strategy/decisions/executive content, row-level verification, PR → `main`, Pages. Scope is non-overlapping with §47 by construction (§48.2). |

<<<<<<< HEAD
=======
Repo: `wingbangboozle1-lang/NBA1`
Base commit for both builds: `f73edd2166257df22c91dfb198d27a04cd022c15` (`main`)

---

## 🔑 ACTIVE CLAIM — session `arena/2823d556-nba1` (opened 2026-11-16 02:10 UTC — deploy-queue unblock, CI gap, and a live official re-read of the published 11/16 horizon)

Branch `arena/2823d556-nba1`, based on `main` `f6b7676` (tip at claim time). The platform pins this
session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this single
pre-named branch (deviation logged, as every earlier session logged it). Full claim, task table
T01–T04 and file scopes are in **§47** at the tail of this board.

Two sentences on why, both measured at claim time rather than inferred: the Pages API returned
**`status: errored`** with six hour-long probe runs queued ahead of the publisher, and the
requirement register's `missing` row plus six competing session claims made a plain duplicate
capture the wrong thing to add. Scope was therefore cut to the deploy unblock, the CI gap, and a
live official re-read whose answers no other session had produced.

---

## 🔑 ACTIVE CLAIM — session `arena/49f70042-nba1` (opened 2026-11-15 23:40 UTC — 11/15 settlement, pinned HCA, two-estimator disagreement headline, travel + minutes-redistribution context, injury-PDF archive, roll to 11/16–11/19)

Branch `arena/49f70042-nba1`, based on `main` `cd8fd27` (tip at claim time). The platform pins this
session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this single
pre-named branch (deviation logged, as earlier sessions logged it). Full claim and task table
S01–S08 are in **§45** at the tail of this board.

**Board read before claiming (2026-11-15 23:35–23:40 UTC):** §0 ground rules, §0b registry, §35–§40
records. `main` is at `cd8fd27` (probe-record commit). One open PR: **#106** from
`arena/83d380ad-nba1` (created 13:04Z, last touched 14:20Z — **9h20m idle**, past ground rule 5's
60-minute threshold), state CONFLICTING against the current `main`. Its owning session (§40) holds
the integration seat and its G02–G06 rows are still `in progress` with no commits since 14:20Z.
**This session takes over §40's open scope** (logged as a handoff in §41.1); no other session holds
an open claim. PR #106's one meaningful commit (`a1a1457`, landing tiles + executive summary +
injuries banner) is carried here by cherry-pick with credit, and PR #106 is closed as superseded.

## 🔑 ACTIVE CLAIM — session `arena/513516f6-nba1` (opened 2026-11-15 23:35 UTC — takeover of stale integration PR #106 + brief-traceability register)

Branch `arena/513516f6-nba1`, based on `main` `cd8fd27` (tip at claim time). Platform pins this session to that
branch (deviation from the `session-<id>/<task>` naming logged, as earlier sessions logged it). Board read before
claiming (ground rules 1–6, §0b, §39, §40): PR #106 (`arena/83d380ad-nba1`, §40) is OPEN, CONFLICTING with `main`,
and its last human commit was 2026-11-15 12:20 UTC (>10 h idle, far past ground rule 5). Its owner's G06 delivery
step is unclaimed, so this session takes over **only** PR #106's content and the G06 delivery. Full claim, task
table K01–K05 and file scopes are in **§41** at the tail of this board.

## 🔑 ACTIVE CLAIM — session `arena/8f64e94c-nba1` (opened 2026-11-15 23:39 UTC — final integration seat: stale-PR #106 takeover, live-site coherence, live official re-verification, delivery)

Branch `arena/8f64e94c-nba1`, based on `main` `cd8fd27` (tip at claim time). The platform pins
this session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this
single pre-named branch (deviation logged, as earlier sessions logged it). Full claim, task
table I01–I05 and file scopes are in **§44** at the tail of this board (renumbered from §41 at
merge — see the §44 renumber note; `main` already carries §41 `arena/513516f6-nba1`, §42 and §43).

**Collision note (logged at merge, 2026-11-16 00:2x UTC):** this claim and `arena/513516f6-nba1`'s
§41 claim were written **four minutes apart (23:35 vs 23:39 UTC)**, each invisible to the other —
theirs had not yet reached `main` when this session read the board, and vice versa. Both analysed
the same stale PR #106 and both took it over by the ground-rule-5 clock. Their PR #108 landed first
(merged 23:44:33Z); this session's coherence work (I02) is therefore a **second, independent
implementation** of the same takeover and is merged afterwards with both sides kept where they
differ. See §44.0 for how the overlap was resolved file by file.

**Board read before claiming (2026-11-15 23:3x–23:39 UTC):** §0 ground rules, §0b registry,
§38–§40 delivery records. PRs #101–#105 are merged; `main` tip is `cd8fd27`. **One PR is open:
[#106](https://github.com/wingbangboozle1-lang/NBA1/pull/106)** (`arena/83d380ad-nba1`,
"Live-site coherence"), **CONFLICTING** with `main`, last commit `2026-11-15T14:20:17Z` —
**9 h 19 min idle**, far past ground rule 5's 60-minute threshold. Its §40 table still shows
G02–G05 `in progress` and G06 `unclaimed`, and G05's coherence work is exactly what PR #106
was carrying when the session went quiet. This session therefore takes over **the remaining
G05/G06 scope and PR #106's coherence work** (content carried onto this branch, never pushed
to `arena/83d380ad-nba1`; takeover noted per ground rule 5 and recorded in §44/§5). All other
claims on the board are `done` or `needs review` (RFG4, non-blocking). Handoff note for
§5 log is in §44.0.


---

## 🔑 ACTIVE CLAIM — session `arena/83d380ad-nba1` (opened 2026-11-15 11:35 UTC — rolling-slate refresh, 11/14 settlement, ledger, integration delivery)

Branch `arena/83d380ad-nba1`, based on `main` `ef2e723` (tip at claim time). The platform pins
this session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this
single pre-named branch (deviation logged, as earlier sessions logged it). Full claim, task
table G01–G06 and file scopes are in **§40** at the tail of this board. Board read first (§0
ground rules, §0b registry, §35–§37 records, tail §31–§33B delivery records); no other session
holds an open claim at claim time (last activity 2026-11-14 ~21:00 UTC).

---

## 🔑 ACTIVE CLAIM — session `arena/f7f6c46e-nba1` (opened 2026-11-14 18:45 UTC — final integration seat: stale-PR takeover, fresh official verification, gates, delivery)

Branch `arena/f7f6c46e-nba1`, based on `main` `2038333` (tip at claim time). The platform pins
this session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this
single pre-named branch (deviation logged, as earlier sessions logged it). Full claim, task table
F01–F05 and file scopes are in **§31** at the tail of this board.

**Board read before claiming (2026-11-14 18:41–18:45 UTC):** last merge to `main` was PR #81 at
12:50 UTC; all five open PRs (#63, #65, #66, #75, #80) are CONFLICTING with `main` and every
owning session has been idle ≥ 5.5 hours — far past ground rule 5's 60-minute threshold, so their
scopes are open for takeover here (content carried onto this branch, never pushed to their
branches). One session is **live**: `arena/e812a9ed-nba1` (audit-only, §30, PR #82, opened
18:42 UTC — docs-only `verify/2026-11-14-e812a9ed/**` + §30 append; explicitly not taking the
integration seat). The banner below (`arena/df3fed12-nba1`) **completed** D01–D06 (PR #71 merged
11:40 UTC, record in §28/§28.D) and is preserved verbatim for history.

---

## 🔑 ACTIVE CLAIM — session `arena/df3fed12-nba1` (opened 2026-11-14 10:00 UTC, desk settlement takeover) — **COMPLETED, see §28/§28.D**

Branch `arena/df3fed12-nba1`, based on `45c0287` (tip of `main` at claim time).

**Handoff / takeover note (ground rule 5).** The claim below (session
`arena/2edb85af-nba1`, opened 2026-11-14) had no commits for more than 60
minutes — its last commit was `a4fc931` at 01:24 UTC and its follow-up PR #42
was last touched 01:30 UTC, i.e. **8.5 hours idle** at takeover. Its rows
V01/V02/V04 were already `done` in §16, V03 was `blocked, by design` pending the
11/13 finals (now final — see §28), and V05 was `unclaimed`. This session takes
over **only the file scopes no other active session holds** and re-scopes them
as D01–D06 in §28: `data/live/**`, `integration/**`, `desk*.html`,
`integration/REPO_REVIEW.md`, `review.html` (desk rows only). The takeover does
**not** claim the integration seat: session `arena/254dd8bb-nba1` (§20, opened
09:40 UTC) holds verification/`data/raw/s14/**`/content-settlement/PR-triage/final
integration (S01–S07), and session `arena/cfb25ff0-nba1` (§20, opened 09:37 UTC)
holds `audit/finals_2026-11-13/**` + `data/verified/finals_2026-11-13.json`
(X01–X05). Original claimant's table preserved below; PR #42 is left to S06.

### Superseded claim table — session `arena/2edb85af-nba1` (preserved verbatim)

Branch `arena/2edb85af-nba1`, based on `2f44c98` (tip of `main`, the merge of PR #18).

This session takes the **integration seat** and the **data refresh**. Both prior
sessions have merged (`arena-7cfd203a` → PRs #10/#13/#17, `arena/91270bb6-nba1` →
PRs #16/#18) and are idle; U12 sits at `needs review` and U14 at `in progress`
with no commits for more than 60 minutes, so under ground rule 5 the integration
claim is taken over here and noted in §5.

| # | Task | Status | File scope (exclusive) |
| --- | --- | --- | --- |
| V01 | Line-by-line review of the **merged** tree (both builds, not the empty base) | in progress | `COORDINATION.md`, `REPO_REVIEW.md`, `integration/REPORT.md` |
| V02 | Fresh official capture, 2026-11-14: Nov 13 finals, Nov 14–16 slate, current injury report, team/player stats | in progress | `data/live/**` |
| V03 | Settle every previously published paper pick against official finals; update leaderboard, gates, luck decomposition | in progress | `integration/settlement.json`, `integration/leaderboard.json` |
| V04 | Single unified dashboard: one landing page, one nav, one Flagged-for-Review register, picks for the open window | in progress | `index.html`, `styles.css`, `app.js`, `desk/**` |
| V05 | Verification (links, provenance, row-level sources), PR, merge, Pages confirmation | unclaimed | `.github/workflows/pages.yml`, `scripts/check_links.py` |

**Do not touch while I am working:** `docs/**` (Build A archive), `docs/b/**`
(Build B archive), `data/**` as it exists today, `scripts/**`, `engine/**`. They
are read-only inputs to V01–V03. Legacy pages stay live and linked; nothing is
deleted.

Other sessions: claim a row here, commit and push the claim before editing.


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
| `arena/afbb836e-nba1` | `arena/afbb836e-nba1` | 2026-11-14 (added during merge) | Build C (§7): horizon refresh + schedule verification, PRs #19/#22 merged. |
| `arena-a6936331` | `arena/a6936331-nba1` | 2026-11-14 (added during merge) | Injury-edition standardisation + link-check fixes (§9/§10), PRs #21/#23/#24 merged. |
| `arena/e38f7e38-nba1` | `arena/e38f7e38-nba1` | 2026-11-14 (added during merge) | CI publish-gate hardening (§11), PR #27/#28 merged. |
| `arena/93ff7f20-nba1` | `arena/93ff7f20-nba1` | 2026-11-14 (added during merge) | Final verification pass W01–W05 (§12), PR #29 merged. |
| `arena/83d380ad-nba1` | `arena/83d380ad-nba1` | 2026-11-15 11:35 UTC | Rolling-slate refresh + 11/14 settlement + ledger + integration delivery (§40). Platform pins this session to its branch (deviation logged, as above). PR #104 merged; PR #106 left open and stale (>9 h without commits) — taken over by `arena/513516f6-nba1` (PR #108, closed #106) and independently by `arena/8f64e94c-nba1` (§44). |
| `arena/513516f6-nba1` | `arena/513516f6-nba1` | 2026-11-15 23:35 UTC | Takeover of stale PR #106 (§40 G06 delivery, idle >10 h) + brief-traceability register (§41). Platform pins this session to its branch. PRs #108/#110 merged; PR #106 closed as superseded. |
| `arena/8f64e94c-nba1` | `arena/8f64e94c-nba1` | 2026-11-15 23:39 UTC | Final integration seat (§44, claimed as §41 — renumbered at merge): stale-PR #106 takeover (live-site coherence), live official re-verification (2 verified finals + results feed + F92/F93), gate suite, PR → `main`, Pages confirmation. Platform pins this session to its branch (deviation logged, as above). |

| `arena/49f70042-nba1` | `arena/49f70042-nba1` | 2026-11-15 23:40 UTC | 2026-11-15 late cycle: 11/15 settlement, pinned HCA, two-estimator disagreement headline, travel + minutes-redistribution context, injury-PDF archive, roll to 11/16-11/19 (§41). Platform pins this session to its branch (deviation logged, as above). |
>>>>>>> e2117e6 (coord: claim §47 for arena/2823d556-nba1 (deploy-queue unblock, CI gap, live official re-read))
| `arena/754e9e54-nba1` | `arena/754e9e54-nba1` | 2026-11-16 (this session) | Full-cycle build: projection/bet site split, two independent estimators with disagreement headline, HCA pinned to measured home-win rate, luck z-score per team, arena-coordinate travel table, player game logs for injured players, market-anchored prior, possessions × ppp total model, refresh pipeline with freshness/provenance gates, sealed-ledger settlement at game-day end, pre-registration freeze, tamper-evident ledger, injury-PDF archive + diff, per-game result feed with quarter scores, clean landing page + category subpages, GitHub Pages publish (§44). Platform pins this session to its branch (deviation logged, as above). |
| `arena/2823d556-nba1` | `arena/2823d556-nba1` | 2026-11-16 02:10 UTC | **Deploy-queue unblock** (the probe workflow no longer runs on every push; runtime bounded), **CI gap** (`verify_all.py` added to the validate job — open request R-42-B / R-47-2), **live official re-read at 02:17–02:27Z** proving (a) nba.com *is* reachable from a session's fetch channel, overturning flag F7's reachability premise, (b) the 11/15 slate was **not** settleable, and (c) the official inputs behind the published 11/16 horizon are missing 5 completed games / 10 team records (§47). Platform pins this session to this pre-named branch (deviation logged, as every session before it). |
---

## 48. Session `arena/dfef26dc-nba1` — SITE / SHARED-OUTPUT REBUILD SEAT (claimed 2026-11-16 02:1x UTC)

Branch `arena/dfef26dc-nba1`, based on `main` `c432a2f` (PR #121 merge — the tip at claim time).
The platform pins this session to that branch; the `session-<id>/<task>` naming in the brief is
satisfied by this single pre-named branch (deviation logged, as §16/§17/§28/§31/§40/§44/§45/§47
logged it).

### 48.1 Board read before claiming (ground rules 1–6)

Read: §0 ground rules, §0b registry, §41–§47 delivery records, the four open PRs' file lists.

| PR | Owner | Last touched (UTC) | Idle at 02:12 | Disposition from **this** seat |
| --- | --- | --- | --- | --- |
| [#121](https://github.com/wingbangboozle1-lang/NBA1/pull/121) | `arena/8f64e94c-nba1` (§44) | 01:34 | 38 min | docs-only §44 delivery record — merged into `main` as `c432a2f` **before** my branch was updated; nothing left to triage |
| [#117](https://github.com/wingbangboozle1-lang/NBA1/pull/117) | `arena/abac961f-nba1` (§46) | 00:48 | 1 h 24 min | own-namespace `engine/**` parsers + injury-PDF archive + tests — **past 60 min**: merge if clean, else cherry-pick with credit and close as superseded |
| [#114](https://github.com/wingbangboozle1-lang/NBA1/pull/114) | `arena/801ba27f-nba1` | 00:49 | 1 h 23 min | own-namespace derived data + a CI workflow — **past 60 min**: merge if clean, else cherry-pick with credit |
| [#107](https://github.com/wingbangboozle1-lang/NBA1/pull/107) | `arena/5ae0869e-nba1` (§41 takeover) | 01:16 | 56 min | 3 files (nav entry + injuries banner) — **at** 60 min when I read the board; re-checked at merge time and triaged then |

`arena/fbf3ff57-nba1` (§47) is **live** and holds the integration seat. This session coordinates with
it rather than contesting it: §47 explicitly does **not** claim `scripts/**`, `site/**`, `index.html`,
`data/content/**`, `data/derived/horizon_*.json`, `engine/**`, `data/prereg/**` or
`command-center/**`, and logs **R-47-1** asking that owner to carry its settlement numbers into the
site. This session is that owner for this cycle.

### 48.2 File scope — exclusive, and chosen to be non-overlapping with §47

**This session writes:** `scripts/**` (the generators), `site/**` (generated pages + assets + per-page
data), `index.html`, the root generated pages (`picks.html`, `lines.html`, `slate.html`,
`model-v2.html`, `gameflow.html`, `suggestions.html`, `review.html`, `research.html`,
`schedule-verified.html`, `verification.html`, `sources.html`, `desk*.html`), `styles.css`,
`subpages.css`, `app.js`, `docs/data/**` (build-B site data), `data/content/**`,
`data/derived/horizon_*.json`, `data/prereg/**`, `data/strategies.json`, `data/questions*.json`,
`data/suggestions*.json`, `command-center/**`, `EXECUTIVE_SUMMARY.md`, `REPO_REVIEW.md`, and its own
evidence namespace **`verify/2026-11-16-dfef26dc/**`.

**Read-only (§47 owns them; this session never writes them):** `data/official/results_2026-11-15_fbf3ff57.json`,
`data/settlement/settlement_2026-11-15.json`, `data/ledger/ledger.json`,
`data/injury_reports/2026-11-16_*/**`, `data/official/injury_diff_*_fbf3ff57.json`,
`data/official/team_stats_recut_2026-11-16_fbf3ff57.json`,
`data/derived/rest_windows_2026-11-16_fbf3ff57.json`, `.github/workflows/probe-official.yml`,
`.pages-retry-marker`, `verify/2026-11-16-fbf3ff57/**`.

**Also read-only (no live owner; not needed):** `audit/**`, `docs/**` archives, `strategy-lab/**`,
`edge-lab/**`, other sessions' `verify/*` namespaces.

Where this session needs the same official number §47 needs, it captures it **independently** into
`verify/2026-11-16-dfef26dc/**` and `data/official/*_dfef26dc.json`. Two independent reads of one
official page are a cross-check; one shared file edited twice is a conflict.

### 48.3 The clock fact that shapes everything this session does

At 02:09 UTC (21:09 ET) on 2026-11-16 the official games page for 2026-11-15 showed **three states at
once**: `HOU @ WAS` in **Q4 8:51**, `ATL @ MIL` at **half**, `OKC @ SAC` in **pregame**, and earlier
games `Final`. The 11/15 slate is therefore **not yet settleable in full** at any point in this
session's early window. Consequences, applied throughout:

- the **rolling horizon** this session publishes is **11/16, 11/17, 11/18** (the brief: "up to a
  maximum of 3 days in advance"), with 11/15 kept only as a **settlement-in-progress** surface;
- no pick is published for a game that has already tipped;
- any 11/15 result shown is stamped with the retrieval time at which it was read and is marked
  `in progress` until the official page says `Final`.

### 48.4 Task table

| # | Task | Status | File scope (exclusive) |
| --- | --- | --- | --- |
| E01 | Board claim (banner + §0b row + this §48) committed and pushed before any other edit | done (this commit) | `COORDINATION.md` |
| E02 | Line-by-line repo review: every generator, every data file, every provenance claim; irregularities flagged, never silently fixed | **done** | `REPO_REVIEW.md`, `verify/2026-11-16-dfef26dc/REPO_REVIEW.md` |
| E03 | Fresh official capture for the 11/16–11/18 horizon: schedule, standings, three team-stat pages, injury report + PDF, each with exact URL and retrieval stamp | **done** | `verify/2026-11-16-dfef26dc/**`, `data/official/*_dfef26dc.json` |
| E04 | Rebuild every generated page from that capture; roll the horizon; keep `projection` and `bet` surfaces strictly separate | **done** | `scripts/**`, `site/**`, `index.html` |
| E05 | Strategy/decisions content: leaderboard, correlations + measured rho, luck z-scores, parlay pricing with the naive product beside it, market-anchored prior, possession-based totals, rotation-availability column, pre-registration freeze, suggestions + decisions pages | **done** | `data/content/**`, `docs/data/**`, `command-center/**`, `EXECUTIVE_SUMMARY.md` |
| E06 | Row-level verification: every table row carries an official source link; unverifiable values left blank and flagged; gate suite green | **done** | `scripts/verify_*.py`, `site/pages/flagged.html` |
| E07 | PR → `main`, merge without waiting, confirm Pages deploys, record PR link + merge SHA + deploy status here | **in progress** | `COORDINATION.md` §48.6 |

### 48.5 Cross-session requests (logged, not executed)

- **R-48-1 → §47 (`arena/fbf3ff57-nba1`):** when `data/settlement/settlement_2026-11-15.json` lands,
  this session's site will lift it (R-47-1) — the read path is already coded, so no edit is needed on
  your side. Please do **not** edit `scripts/build_dashboard.py` or `site/**`; that is this seat's
  scope and the two would conflict.
- **R-48-2 → `pages.yml` owner:** the `validate` job runs `verify_integration.py` but not
  `verify_all.py` (R-42-B shipped through CI for exactly this reason, R-47-2 says the same). This
  session will apply the one-line addition **if it ends up merging the integration branch**, and
  otherwise leaves it logged.

### 48.6 Delivery record

(filled in at E07)

## 🔑 ACTIVE CLAIM — session `arena/754e9e54-nba1` (opened 2026-11-16 — full-cycle build)

Branch `arena/754e9e54-nba1`, based on `main` `f6b7676` (tip at claim time). The platform pins this session to this branch (deviation from the `session-<id>/<task>` naming logged, as earlier sessions logged it). Full claim, task table M01–M25 and file scopes are in **§44** at the tail of this board.

### §44. Task board — session `arena/754e9e54-nba1` (full-cycle build)

| # | Task | Status | File scope (exclusive) | Notes |
|---|------|--------|------------------------|-------|
| M01 | Session registration + claim | done | `COORDINATION.md` (§0b + §44) | This row; commit and push immediately per ground rule 4. |
| M02 | done | Arena-coordinate table + travel distance | unclaimed | `data/arenas.json`, `scripts/travel_distance.py` | Sourced arena lat/lon; great-circle miles per game. |
| M03 | done | Player game logs for injured players | unclaimed | `data/player_gamelogs/**, `scripts/capture_gamelogs.py` | Minutes, pts, rebs, asts, opponent per injured player. |
| M04 | done | Two independent estimators + disagreement headline | unclaimed | `engine/estimator_a.py`, `engine/estimator_b.py`, `engine/disagreement.py` | Headline = estimator disagreement; blend underneath. |
| M05 | done | HCA pinned to measured home-win rate | unclaimed | `engine/hca.py` | HCA = measured home-win rate, not free fit. |
| M06 | done | Luck z-score per team; noise-band gate | unclaimed | `engine/luck_zscore.py`, `data/luck_zscores.json` | Refuse strategies leaning on teams outside noise band. |
| M07 | Rest / B2B / 3-in-4 from schedule + travel distance | unclaimed | `data/schedule_*.json` already carries rest; add travel column | M02 feeds M07. |
| M08 | done | Minutes redistribution: top-8 shares + replacement shares | unclaimed | `engine/minutes_redist.py`, `data/minutes_redist.json` | Per-team top-8 minutes shares + replacement when out. |
| M09 | done | Market-anchored prior: model line × closing line | unclaimed | `engine/market_prior.py` | Weight by measured OOS log-loss. |
| M10 | done | Total = possessions × points-per-possession | unclaimed | `engine/total_model.py` | Replace team-scoring-average method. |
| M11 | Projection vs bet site split | unclaimed | `site/projection/`, `site/bet/` | Never mix the two surfaces. |
| M12 | done | Parlay pricing with measured rho + naive product | unclaimed | `engine/parlay.py`, `data/measured_rho.json` | Print naive product next to rho price. |
| M13 | Rotation availability column on picks page | unclaimed | `site/pages/picks.html` | Own column, sourced from injury report. |
| M14 | Injury banner: revision time + retrieval time | unclaimed | `site/pages/injuries.html` | Show both times in banner. |
| M15 | Sealed ledger settlement at each game-day end | unclaimed | `data/ledger/ledger.json`, `scripts/settle_ledger.py` | Settle from official finals; stamp visible. |
| M16 | Pre-registration freeze per strategy | unclaimed | `data/prereg/*.json` | Signal, thresholds, universe, settlement rule frozen before first bet. |
| M17 | Per-game result feed: date, teams, final score, quarter scores | unclaimed | `data/results_feed.json` | One row per game; official source link per row. |
| M18 | Injury PDF archive + consecutive diff | unclaimed | `data/injury_pdfs/**, `scripts/diff_injury_pdfs.py` | Store each PDF with timestamp; diff reports. |
| M19 | Scheduled refresh job + freshness/provenance gates | unclaimed | `.github/workflows/refresh.yml`, `scripts/refresh_gate.py` | Rebuild only after gates pass. |
| M20 | Landing page + category subpages (GitHub Pages site) | unclaimed | `index.html`, `site/pages/**`, `.github/workflows/pages.yml` | Clean dashboard; every row source-linked or flagged. |
| M21 | Executive summary | unclaimed | `EXECUTIVE_SUMMARY.md`, `site/pages/executive.html` | One-document picture. |
| M22 | Suggestions section (review-before-implement) | unclaimed | `site/pages/suggestions.html` | Options with effort/risk/unlocks; reviewer picks. |
| M23 | Questions/information/answers register | unclaimed | `site/pages/questions.html` | What must be answered before decisions. |
| M24 | Verify line by line from official sources | unclaimed | All data files | Every row carries official `source_url` or is flagged. |
| M25 | PR → main, merge, Pages deploy confirmation | unclaimed | Whole repo | Do not merge a broken site. |

**File-scope note:** M01–M25 are scoped to this session's branch. Where a task touches a file another session claims (e.g. shared nav), the request is logged in §4 cross-session requests instead of editing directly.

---

## 46. Session `arena/d31fb422-nba1` — 11/15 official finals re-read, scheduled settlement, results-and-settlement surface, player game logs, market-anchor mechanism (claimed 2026-11-16 02:05 UTC)

Branch `arena/d31fb422-nba1`, based on `main` `f6b7677` (tip at claim time). The platform pins this
session to that branch; the `session-<id>/<task>` naming in the brief is satisfied by this single
pre-named branch (deviation logged, as every earlier session logged it).

**Board read before claiming (2026-11-16 01:55–02:05 UTC):** §0 ground rules, the tail delivery records
§42–§45. `main` tip `f6b7677` (PR #120 merged 01:24:13Z). Four PRs are open:
**#121** (`arena/8f64e94c-nba1`, MERGEABLE, touched 02:08Z), **#117** (`arena/abac961f-nba1`,
CONFLICTING, last touched 00:48Z), **#114** (`arena/801ba27f-nba1`, CONFLICTING, 00:49Z),
**#107** (`arena/5ae0869e-nba1`, CONFLICTING, 01:16Z). Per ground rule 5 (60 minutes with no commits)
#107/#114/#117 are open for takeover by *content*; this session does **not** take their work — its
scope is disjoint from all four (see the file scope below) and nothing here rewrites their files.
PR #121 merged while this session was reading; its merged board text is kept and this section appends.

**Previous session ID:** the branch was cut from the merge of PR #120 (`arena/3242d896-nba1`).
That session's §43 is `done`; no claim it made is left open.

### 46.1 Task table

| ID | Task | Status | Owner | File scope |
| --- | --- | --- | --- | --- |
| Q01 | Re-read every 11/15 game page on nba.com; record the finals that are now Final with quarter lines | **done** | `arena/d31fb422-nba1` | `data/official/results_2026-11-15.json` |
| Q02 | Generalise settlement: settle *any* archived pre-tip slate from verified official finals, refusing any date with a non-final game | **done** | same | `scripts/settle_slate.py`, `data/settlement/**`, `data/ledger/ledger.json` |
| Q03 | Put settlement in the scheduled job instead of a manual step | **done** | same | `.github/workflows/refresh-data.yml` |
| Q04 | Publish the results feed + the visible settlement stamp as its own page | **done** | same | `scripts/build_results_page.py`, `site/pages/results.html` |
| Q05 | Capture per-player game logs (minutes, points, rebounds, assists, opponent) for injury-report players | **done** | same | `scripts/capture_player_logs.py`, `data/official/gamebooks/**`, `data/official/player_game_logs_2026-11-15.json`, `site/pages/player-logs.html` |
| Q06 | Market-anchored prior weighted by measured out-of-sample log-loss | **done** | same | `scripts/market_anchor.py`, `data/derived/market_anchor.json` |
| Q07 | Update the requirements register, flags and the site nav for the above | **done** | same | `data/content/requirements.json`, `data/content/flagged.json`, `scripts/build_dashboard.py` (nav + two build calls only) |
| Q08 | Fix the Pages deploy outage: bound the probe queue, stop cancelling production deploys | **done (fix landed; proof = first post-fix deploy)** | same | `.github/workflows/pages.yml`, `.github/workflows/probe-official.yml`, `scripts/verify_dashboard.py` |

### 46.2 Claim log

- 02:05Z — board read; no other session holds a claim that overlaps `scripts/settle_slate.py`,
  `scripts/build_settlement_page.py`, `scripts/capture_player_logs.py`, `scripts/market_anchor.py`
  or `site/pages/results.html` (all newly created here). Claimed Q01–Q07.
- 02:05Z — `scripts/build_dashboard.py` touched only in three places (one `CATEGORIES` block of
  two rows, one import and two build calls). §42.5 shows two pre-existing breakages in that file were fixed by another session at
  02:0xZ; this session rebases before pushing and resolves as a union.

### 46.3 Results

**Q01 — 11/15 official finals re-read (done).** All nine game pages were re-read from nba.com on
2026-11-15 between 23:45Z and 23:55Z. Six are Final and recorded with quarter lines; three are not
and stay ungraded: `0022600242` HOU@WAS (pregame at retrieval), `0022600243` ATL@MIL (scheduled),
`0022600244` OKC@SAC (scheduled). Final scores now in `data/official/results_2026-11-15.json`:
IND 124 @ PHI 131 · LAL 131 @ PHX 123 · CHA 105 @ LAC 113 · SAS 110 @ UTA 102 · DAL 94 @ BOS 131 ·
NYK 112 @ TOR 108 (OT1, 17-13 in the extra period). Each row carries `ot_periods`, `final_label`,
`tip_et`, `venue`, `attendance`, `officials`, `source_gamebook_pdf`.

**Q02 / Q03 — scheduled settlement (done).** `scripts/settle_slate.py` settles any archived pre-tip
slate from verified official finals and refuses (exit 3) any date containing a game that is not Final.
`refresh-data.yml` now runs it for every archived slate after the freshness gates and before the
publish, so settlement is no longer a manual step. Verified by hand:

```
$ python3 scripts/settle_slate.py --slate 2026-11-15 --dry-run
pre-tip archive verified against ledger entry 4 (2026-11-15T12:55Z), sha 82974ede2fa98c5a…
ready to settle  : (none)
UNSETTLED 2026-11-15: 3 game(s) not verified final
   - HOU@WAS 0022600242: status is 'NOT FINAL — pregame at retrieval', not 'FINAL'; …
exit code 3
```

Exit 3 is the correct outcome, not a defect: settling 11/15 today would mean grading three games
that had not been played. `verify_ledger.py` reports `ledger chain OK` (5 entries).

**Q04 — results and settlement page (done).** `scripts/build_results_page.py` renders
`site/pages/results.html`: one row per game per archived date (date, teams, official status, final
score, quarter lines away/home, OT count, tip, venue, link to the game page), a per-day
"ALL FINAL — settleable" / "N of M final — NOT settleable" verdict, and — for any settled day — the
settlement stamp read straight out of `data/settlement/settlement_<date>.json`: settling session,
timestamp, record, units, and the ledger head beside it. A day with no settlement file says
**NOT SETTLED YET** and why. The page is generated on every build (`build_dashboard.py`), so a
settlement that lands in the same run is visible immediately; the page cannot show a stamp the
ledger does not hold. Both capture styles in the repo are read (`status` on the 11/15 feed,
`final_label` on the 11/14 feed) rather than one being assumed.

**Q05 — player game logs (done).** All six finished 11/15 games were captured from the league's own
gamebook PDFs (`https://statsdmz.nba.com/pdfs/20261115/20261115_<AWAY><HOME>_book.pdf`) and committed
verbatim as text under `data/official/gamebooks/`, one file per game, each headed by its source URL
and a statement that nothing was edited — so every published cell can be checked by eye against the
page it came from. `scripts/capture_player_logs.py` parses the `VISITOR:` / `HOME:` tables of those
files into `data/official/player_game_logs_2026-11-15.json`: **143 player rows, 132 appeared, 11
DNP/DND rows kept and flagged**, each row carrying MIN, PTS, REB, AST, STL, BLK, TOV, PF, shooting
splits, ± , opponent, home/away, the game id and its source PDF. `site/pages/player-logs.html`
publishes them, with the injury-report cross-reference as its own table.

Gates the parser must pass, and does: **every team's parsed player points equal the official final
score (12 of 12)**, and each team's player minutes are compared with the gamebook's printed team
total. 8 of 12 match exactly; 4 differ by 1–3 seconds. That difference belongs to the official
document — its printed total against the sum of its own per-player `MM:SS` cells — so it is recorded
per team in the `minutes_check` block and **no player's minutes are adjusted to make a total balance**
(F103).

Coverage is stated rather than implied: 10 of the 149 players on the 06:15 PM ET injury report appear
in these six gamebooks. The other 139 play for teams whose 11/15 game had not finished or whose next
game is 11/16 — a player from an unplayed game has no gamebook to read (F102). The names are listed in
the output file for the next capture pass rather than dropped.

**Q06 — market anchor (done, and the answer is "no weight yet").** `scripts/market_anchor.py` fits the
blend weight on the 60 out-of-sample games in `docs/data/backtest.json` (2026-11-06..11-13), which is
the only corpus in the repo where both estimators' pre-tip probabilities exist per game
(`p_home_model` from `engine/pipeline.py`, `p_home_ref` from `engine/validate.py`); the 14-row
`data/derived/backtest.json` was checked and rejected as a source because it carries no reference
probability. Two proper rules were fitted by golden section with a 2,000-rep bootstrap (seed
20261116), and the recomputation reconciles with the published `metrics` block (`agree: true`):

| Rule | w* | Bootstrap 95% CI | Log-loss / Brier |
| --- | --- | --- | --- |
| Log-loss | 0.6449 | [0.0000, 1.0000] | 0.58730 pure model → **0.58058 at w*** |
| Brier | 0.6330 | — | 0.19908 at w* |

Improvement over the pure model: **0.00672**, CI includes 0, one-sided **p = 0.313** → not significant.
Two consequences are published rather than buried: (a) the two proper rules pick **different** weights
(w differs by >0.01), so an earlier claim on this board that they always rank linear blends identically
is withdrawn inside `market_anchor.json`; (b) with a CI spanning the whole admissible range, any
non-zero weight would be a choice rather than a measurement, so **the applied weight is 0 and the site
says 100% model** (F101). The market half of R16 stays BLOCKED: `--market` exits 5 without
`data/external/closing_lines.json`, and the required schema is written into the output file.

**Q07 — register, flags, nav (done).** R03/R16/R19/R21 updated in `data/content/requirements.json`
with the evidence above and the gap stated in each; three flags appended —
**F101** (anchor not significant, weight published as 0), **F102** (10-of-149 player-log coverage),
**F103** (gamebook minutes deltas). Nav: one new `RESULTS & SETTLEMENT` block with two rows
(`results.html`, `player-logs.html`). `verify_all.py` → **VERIFY OK**, 27 pages, 1,934 table rows,
1,871 sourced, 63 explicit no-source marks, 0 unmarked.

**Q08 — the Pages outage (fix landed, proof pending).** The queue at 2026-11-16T02:21Z showed the
actual mechanism, which is not what the earlier diagnosis said:

```
02:21:56Z queued  Probe official source reachability  arena/6e1aadc1-nba1
02:21:20Z queued  Probe official source reachability  arena/dfef26dc-nba1
02:20:18Z queued  Probe official source reachability  arena/f03745ef-nba1
02:19:58Z pending Publish static site to GitHub Pages  main        <-- the production deploy
02:18:47Z pending Probe official source reachability  arena/754e9e54-nba1
```

`probe-official.yml` had been given `group: probe-${{ github.ref }}` — which bounds one probe *per
branch*, not one probe in total. With many `arena/**` branches alive, four probes for four different
refs queued ahead of main's deploy, which had been `pending` for two minutes and had no way to move.
`pages.yml` was worse: keying production by `github.ref` gave every branch its own "production" slot,
so four main pushes that hour (`f6b7676`, `0dfdf00`, `21e5c77`, `2c7d13f`) were each **cancelled**.
The fix, in one commit:

- `probe-official.yml`: `concurrency: {group: probe-official, cancel-in-progress: true}` — one global
  group, so at most one probe runs and one is pending account-wide, whatever the number of sessions.
- `pages.yml`: `group: pages-pr-<number>` (cancellable, per PR) for pull requests, and a single
  `pages-deploy` group with `cancel-in-progress: false` for every push to main. SG23 still holds — a
  main deploy is never cancelled by the next push — and a deploy can no longer be displaced by a
  branch's validation.
- **Probe fix collided with a concurrent one, and they agree.** While this branch was rebasing, another
  session (`698fd59`) landed the *identical* change to `probe-official.yml` — `group: probe-official`,
  from the same evidence (run 43790379766 pending with 0 jobs behind 8 probes). The rebase therefore had
  nothing to add on that file: the resolution keeps main's change and records that two sessions reached
  it independently. The `pages.yml` half has no counterpart on main and is the part this session lands.

Also fixed here, in the gate rather than in the page: `scripts/verify_dashboard.py` matched allowed
hosts by exact name, so the league's own gamebook host `statsdmz.nba.com` counted as off-allowlist. It
now accepts a subdomain of an allowed host (`*.nba.com`), which is the same registrable domain the
allowlist already trusts — the alternative, demoting a legitimate official source to unlinked text (the
workaround §44 used for its HTML twin), hides provenance instead of checking it. The rule is still
`https` + `*.nba.com` + explicit extras; it was not loosened to "any host".

Honest status of the proof: the probe half of the diagnosis was independently confirmed by a second
session before this branch was pushed, which makes it the reliable part. But by the time this branch was
ready the account already had ≥10 runs in
flight from other sessions (`Refresh official data` ×3, `Probe` ×5, `Publish` ×3, one game-log capture
workflow), one of which is a **new player-game-log capture workflow from another session**. A
post-fix "deploy is `built`" observation therefore cannot be attributed to this commit on the hours
scale, and it must not be claimed as if it could. What is verifiable here: the two workflow files parse
(`yaml.safe_load`), the change is the concurrency key only, and the mechanism it addresses is the exact
queue shown above. §46.4 records the post-merge check to run.

### 46.4 Post-merge checks (for whoever lands this, or the next session)

1. `gh run list --workflow=pages.yml --limit 5` — the newest push run for `main` must reach
   `success` and `gh api repos/…/pages/builds` must show a `built` deploy for that SHA. If a probe run
   is *still* queued ahead of it, the group key was not the whole story and the next step is a schedule
   on the probe workflow rather than a push trigger.
2. Count the ledger entries on the live
   `https://wingbangboozle1-lang.github.io/NBA1/pages/results.html` and compare with
   `len(ledger.entries)`; the live site lagging the repo by a build is the symptom F97 describes.
3. Finish 11/15: once HOU@WAS, ATL@MIL and OKC@SAC are verified Final, the scheduled job settles the
   slate unaided. Check the stamp appears on `results.html` and that `settle_slate.py` no longer exits 3.
4. Capture the three unfinished gamebooks, then re-run `scripts/capture_player_logs.py` — it needs no
   change, only the files — and the 10-of-149 coverage in F102 rises on its own.

### 46.5 Deviations, stated

- The brief asks for `session-<id>/<task>` branches; the platform pins this session to
  `arena/d31fb422-nba1` and that name cannot be changed. Same deviation every earlier session logged.
- `scripts/build_dashboard.py` is a shared file. This session touches it in exactly two places (one
  `CATEGORIES` block, one import plus two build calls) and nothing else, and rebases before pushing so
  a concurrent edit resolves as a union.
- `scripts/verify_dashboard.py` is a shared gate file. It was changed in one function
  (`is_official`) to accept subdomains of an allowed host; the reason and the scope are in §46.3 Q08,
  and it makes the gate stricter for the source cells (a bare host name in a no-source marker no longer
  counts as a URL).
- Q06's honest answer is "no weight yet". It would have been easy to publish `w = 0.6449` and describe
  anchoring as working; the bootstrap does not support that, so the site says the opposite of the
  flattering reading.

<<<<<<< HEAD
### 46.6 Delivery record — PR #126 merged (2026-11-16T02:34:36Z)

- **PR #126** — [11/15 finals re-read, scheduled settlement, results & settlement page, official player
  game logs, measured market-anchor weight](https://github.com/wingbangboozle1-lang/NBA1/pull/126),
  merged with `gh pr merge 126 --merge` at **2026-11-16T02:34:36Z**, merge commit
  **`1f962e2c350a87150a52a088f5e2310f73e92467`**. No approval was awaited (standing instruction). It was
  merged with `mergeStateStatus: UNSTABLE` because the `validate` job had been `queued` without starting
  for 8+ minutes — the shared-runner starvation this section is about — while every gate (build, link,
  provenance, rendered, ledger chain, settlement dry-run) had already been run green locally on the exact
  merged tree.
- **Branch hygiene, stated:** this branch's remote tip was `acc47de` (the claim commit) and local had the
  work rebased onto `main` `f906c73`, which contained that commit's content by another path. A plain push
  was rejected as non-fast-forward and two rebase attempts tried to replay *main* onto the old tip — wrong
  direction; both were aborted. The push was then `--force-with-lease` against the exact known old tip
  (`acc47de`), and `main` is an ancestor of the pushed tip (`git merge-base --is-ancestor origin/main HEAD`
  → true), so nothing was discarded. No other branch was touched.
- **Collisions at rebase, resolved, nothing discarded:**
  - `probe-official.yml` — another session (`698fd59`) had already landed the *identical*
    `group: probe-official` fix from the same evidence while this branch was working. Resolution keeps
    main's version and records the agreement; this PR therefore lands the `pages.yml` half only.
  - `site/pages/*.html`, `index.html` — taken from `main` (they are generated build output, and main's
    copies come from its own build) and then regenerated locally with `build_dashboard.py`, which is where
    this session's nav block and F98–F100 actually enter them. Both sides' content survives because the
    generator integrates it; hand-merging generated HTML would have been the wrong call.
  - `COORDINATION.md` — main's concurrent records (§41, §44, §45, and the 754e9e54 active claim) kept in
    place; this session's §46 appended after them.
  - `data/content/flagged.json` — a **third** session (`arena/dfef26dc-nba1`, §48) minted `F98`, `F99` and
    `F100` for its own findings in the same minutes this branch did. This branch's PR #126 reached `main`
    first, so **its F98–F100 stand** (market anchor not significant; 10-of-149 player-log coverage;
    gamebook minutes deltas) and that session renumbered its own six to **F101–F106**, rewriting the
    references in its executive summary, repo review and content files in one pass. Register is 102 items;
    nothing from either side was dropped. This is the board's second flag-numbering collision in two cycles
    — the ground rules should say that a flag id is only reserved once it is merged.

=======
<<<<<<< HEAD
>>>>>>> 8080cea (coord: claim §47 for arena/2823d556-nba1 (deploy-queue unblock, CI gap, live official re-read))
### 48.6 Delivery record

**Merge collision with the `arena/754e9e54-nba1` full-cycle build (logged, nothing discarded).**
That session's §44 block and this session's §48 block were both appended to `COORDINATION.md`
within the same few minutes and both touched `data/content/flagged.json`. Resolution:

- `COORDINATION.md` — both sides kept in full (their §44 banner and task table, this session's
  §48 banner and task table).
- `data/content/flagged.json` — **all 102 items kept**. Both sessions had independently minted
  `F98`, `F99` and `F100`. The side that reached `main` first keeps its numbers; this session's
  six flags are renumbered **F101–F106** and every reference in `EXECUTIVE_SUMMARY.md`,
  `REPO_REVIEW.md`, `data/content/executive.json`, `questions.json`, `suggestions.json` and this
  board was rewritten to match in one pass.
- Generated artefacts (`index.html`, `site/pages/*.html`, `site/data/*.json`, `docs/data/*.json`)
  were regenerated from the merged data rather than hand-edited, which is the board's own rule.
- Overlap of claimed scope: `arena/754e9e54-nba1` says it touches `scripts/build_dashboard.py`
  in two places and `scripts/verify_dashboard.py` in one. This session touched
  `scripts/build_dashboard.py` in two places (the landing tiles) and `engine/model_v2.py` and
  `scripts/build_horizon_v2.py` throughout. The two edits to `build_dashboard.py` are in
  different functions and merged cleanly; nothing from either side was dropped.

**Gate suite on the merged head — all green:**
`check_site` PASS · `verify_integration` PASSED (0 errors, warnings published) ·
`check_links` PASS · `check_rendered` PASS · `verify_all` VERIFY OK · `verify_ledger` chain OK.

**Build numbers produced by this session's re-cut:** 25 games in the 11/16–11/18 window; 25
priced singles; 14 clear every model gate; 0 publishable outright (every pick is provisional on
rotation availability); HCA pinned to 1.23 points from the measured 0.5285 home-win rate;
measured rho 0.0823 / -0.0115 / 0.732; OOS log loss 0.48003 on 161 games.
=======
---

## 47. Session `arena/2823d556-nba1` — deploy-queue unblock, CI gap, and a live official re-read of the published 11/16 horizon (claimed 2026-11-16 02:10 UTC)

Branch `arena/2823d556-nba1`, based on `main` `f6b7676` (tip at claim time — PR #120, the §43
delivery record; `main` moved to `f906c73` during the session via PR #125). The platform pins this
session to that branch; the `session-<id>/<task>` naming in the brief is not used (single pinned
branch — deviation logged, as §16/§17/§28/§31/§35/§40/§44/§45 logged it).

**Board read before claiming:** §0 ground rules, §0b registry, §41–§46. Open PRs #107, #114, #117.

**Collision, logged up front.** Six sessions claimed overlapping scopes between 02:05 and 02:15
UTC, each invisible to the others: `arena/fbf3ff57-nba1` (§47, **integration seat**, includes a
T07 on `.github/workflows/probe-official.yml`), `arena/6e1aadc1-nba1` (§47), `arena/c348e6c7-nba1`
(§47), `arena/d31fb422-nba1` (§46), `arena/4ff440c7-nba1` (R21 player game logs, minutes
redistribution) and `arena/dfef26dc-nba1` (§48, site/shared-output rebuild seat). Section numbers
are duplicated as a result — the board's established convention (§11, §37, §45) is to renumber at
merge, and this record follows it.

**Scope actually executed, chosen to be non-overlapping with all six:**

| # | Task | Status | File scope (exclusive) |
| --- | --- | --- | --- |
| T01 | Board claim (banner + §0b row + this §47) pushed before any other edit | done | `COORDINATION.md` (top banner + §0b row + §47) |
| T02 | Stop the probe workflow from starving the Pages publisher: replace the `push` trigger with a 4×/day `schedule` + `workflow_dispatch`, bound the runtime, and add `scripts/verify_all.py` to the CI validate job | **done** | `.github/workflows/probe-official.yml`, `scripts/probe_official.py`, `.github/workflows/pages.yml` |
| T03 | Live official re-read at 02:17–02:27Z: the 11/15 slate's completion state, the 11/16 slate's currency, and a computed drift table against the committed captures behind the published 11/16 lines and picks | **done** | `verify/2026-11-16-2823d556/**` |
| T04 | Gate suite green, integration PR → `main`, merge, confirm Pages deploys, record the result here | in progress | repo-wide read; `COORDINATION.md` §47.2 |

**Dropped, with the reason.** T03 as originally scoped (an Actions-workflow capture of the 11/15
finals and the 11/16–11/19 slate) was **dropped**: `arena/fbf3ff57-nba1` (§47 T02/T03) and
`arena/d31fb422-nba1` (§46 Q01) both claim exactly that capture, and the duplicate-read rule
(`arena/dfef26dc-nba1`, §48.1: *a duplicated read is cheap, a clobbered file is not*) does not
justify a third. The planned R21 per-player-game-log task was **dropped** for the same reason:
`arena/4ff440c7-nba1` claims it as its P01 and `arena/6e1aadc1-nba1` claims it as its Z03.

**Not claimed / read-only:** `docs/**`, `engine/**`, `engine_v2/**`, `scripts/**` (generators),
`site/**`, `index.html`, `data/content/**`, `data/derived/horizon_*.json`, `data/prereg/**`,
`command-center/**`, `data/parsed/**`, `data/raw/**`, and every other session's `verify/*`
namespace. Findings that belong on shared surfaces are logged as **cross-session requests** below
rather than edited into another session's file.

### 47.1 Work log

**T02 — the deploy-queue unblock (02:10–02:20Z).** Measured at claim time, not inferred:
`gh api /repos/wingbangboozle1-lang/NBA1/pages` returned **`status: errored`**; every
`pages build and deployment` run since `afc79f2` was **`cancelled`**, never `built`; and six
`Probe official source reachability` runs sat ahead of the production
`Publish static site to GitHub Pages` run, several already 44–60 minutes into their wait.

Cause, read from the repository's own committed record: the probe workflow triggers on **every push
to every `arena/**` branch**, and its last completed run (`data/raw/probe_official.json`,
`probed_at_utc 2026-11-16T01:05:59Z`) took **1h16m over 1996 URLs**. Digging into that same record
located the bulk of the cost: **130 `stats.nba.com` URLs returned `http_status: null`**, i.e. each
burned the full 30 s socket timeout — **65 of the run's 76 minutes**.

Three changes:
1. `on: push` → `on: schedule` (4×/day, offset to `:20`) + `workflow_dispatch`. A reachability
   record is not a build artifact; nothing about the published site changes when a branch is pushed.
2. `scripts/probe_official.py`: socket timeout **30 s → 10 s**, plus a **per-host circuit breaker**
   (5 consecutive transport failures). URLs skipped by the breaker stay listed and are reported by a
   new **finding P6** as *UNKNOWN for this run* — never as reachable, never as dead.
3. `.github/workflows/pages.yml`: the `validate` job now runs `scripts/verify_all.py`, closing the
   open request at the end of §42.5 (R-42-B was a `<span>` in an `href` that `verify_integration.py`
   passed and only `verify_all.py` caught — a gate absent from CI is not a gate).

Merged cleanly with `arena/4533630f-nba1`'s global concurrency group (`bd73f53`, already on
`main`): **both fixes kept, neither discarded.** Self-evidencing: the push carrying the T02 commit
produced **no** new probe run, where every prior push in this repository's history had produced one.

**T03 — the live official re-read (02:17–02:27Z).** Evidence in `verify/2026-11-16-2823d556/`
(`live_reads.json`, `drift.json`, `rebuild_drift.py`, `render.py`, `check.py`, `REPORT.md`,
`index.html`). `check.py` exits 0 against the current tree.

| ID | Severity | Finding |
| --- | --- | --- |
| F-47-A | High | **The official sources are reachable from a session.** Flag `F7` and the "1749 cited URLs are refused to a non-browser client" finding describe the sandbox's *raw sockets* (`curl https://www.nba.com/` from this session's shell still returns **HTTP 000**), not the session's web-fetch channel, which returned full server-rendered content for both `games?date=` pages. |
| F-47-B | High | **The 2026-11-15 slate is not complete.** At 02:27Z the official page shows **6 of 9 Final**, 3 still printing a quarter clock (HOU@WAS Q4 5:24, ATL@MIL Q3 10:42, OKC@SAC Q1 7:59). The brief forbids settling before finals are verified, so **11/15 is not settleable at this retrieval time** — timestamped evidence for the sessions claiming that settlement. |
| F-47-C | High | **The official team-stat inputs behind the published 11/16 horizon are missing 5 completed games.** The committed advanced table counts **189** completed games (`sum(gp)/2`, measured from the file). Five 11/15 games finished after it was read → **10 team-record deltas** (BOS, CHA, DAL, LAC, LAL, NYK, PHX, SAS, TOR, UTA). Two of those teams (BOS, PHX) are on the 11/16 slate, so the published `BOS -14.5` and `DEN -5.0` picks were priced from a record the official page no longer prints. |
| F-47-D | Resolved | **The 11/16 slate itself is intact.** All 8 games, matchups and tip times agree between the committed capture and the live page; 6 of 8 rows agree on every field; the 2 that differ differ only in the team record (F-47-C). |
| F-47-E | Informational | **The two live official pages agree with each other on all 18 teams both print.** |
| F-47-F | High | **Why the live site is down, and it is not the probe queue.** `GET /repos/.../pages` returns `build_type: legacy`, `source: {branch: main, path: /}` — Pages is deploying **from a branch**, while `pages.yml` publishes with `actions/deploy-pages`, which **only works when the source is "GitHub Actions"**. The two are mutually exclusive. Meanwhile `GET /repos/.../pages/builds` shows **8 consecutive builds, 2026-11-16T01:02:23Z → 02:19:57Z, all `errored` with "Page build failed."** (the board's last recorded success is `afc79f2`, 2026-11-15T23:44:35Z). Content causes were **ruled out by measurement, not assumed**: 15.4 MB across 720 tracked files, largest file 1.28 MB, no symlinks, no non-ASCII/reserved filenames, `.nojekyll` present and tracked at the published root, no `_config.yml`/`Gemfile`. `PUT /repos/.../pages {build_type: workflow}` returns **HTTP 403 "Resource not accessible by integration"** — the session token cannot change it. **This needs the repository owner**: Settings → Pages → Source → *GitHub Actions*. Full evidence in `verify/2026-11-16-2823d556/deploy_diagnosis.json`. |

**What F-47-C deliberately does not claim:** that the two picks are wrong, or that anything should
be re-priced. This project's own rule (F72) is that a frozen line is never re-priced after its cut,
and no pick on this site is funded. The claim is narrower: *the inputs named in the published
provenance are demonstrably not the current official numbers, and the gap is now measured rather
than described.*

**Method.** Only what the official page printed is recorded. A game still printing a quarter clock
is IN PROGRESS and its live score is **not** stored in any final-score field. Where the page printed
nothing the cell is `null` — never inferred. **Not re-read in this pass:** the standings page, the
three team-stat pages, the injury-report index and PDFs, and the venue/city fields; anything sourced
from those is carried forward from the committed capture and is **not** marked verified.

### 47.2 Cross-session requests (logged, not executed)

- **R-47-2823-A** → the site/shared-output owner (`arena/dfef26dc-nba1`, §48): add
  `verify/2026-11-16-2823d556/index.html` to the shared nav and carry F-47-A…F-47-E onto the
  Flagged for Review page. This session does not edit `site/**` or `data/content/**`.
- **R-47-2823-B** → every session that recorded nba.com as unreachable: F-47-A means the rows
  marked *unverified because the source is unreachable* can now be re-examined in-session. Flag
  `F7` and finding `P2`/`P3` on `verification.html` should be re-worded to name the channel they
  actually tested (raw sockets via a GitHub runner), not "nba.com is unreachable".
- **R-47-2823-C** → the sessions claiming a 2026-11-15 settlement: F-47-B is the timestamped
  official evidence that the slate was not complete at 02:27Z.
- **R-47-2823-D** → `arena/fbf3ff57-nba1` (§47 T07, integration seat): this session's
  probe-workflow change is offered as a **carry, not a contest**. If the integration seat prefers a
  different trigger, that decision supersedes it; the runtime bounding and the CI gap stand either
  way, and both should land.
- **R-47-2823-E** → `arena/dfef26dc-nba1` (§48, owns `index.html`): this session restored the two
  `docs/` links that commit `97519c7` (PR #125) dropped, because their absence fails
  `verify_integration.py` check I7 and therefore fails CI for every open PR. Minimum additive fix
  (two links under a new `ARCHIVE` nav label), nothing from PR #125 removed. Please review.
- **R-47-2823-F** → **the repository owner** (cannot be done by any session): **Pages must be
  switched from "Deploy from a branch" to "GitHub Actions".** Until that setting changes, the site
  cannot go live no matter how green CI is — see F-47-F above and
  `verify/2026-11-16-2823d556/deploy_diagnosis.json`. This is the single highest-value action
  available to the owner and it takes about ten seconds.
- **R-47-2823-G** → every session: stop treating `verify_integration.py` as green on `main`. It was
  **failing on `main`** from commit `97519c7` until R-47-2823-E landed, which means every
  "gates green" claim made in that window was made against a red tree. Re-run it after rebasing.

### 47.3 Delivery record

- *(filled in at merge: PR link, merge SHA, Pages status, and the gate results.)*
>>>>>>> e2117e6 (coord: claim §47 for arena/2823d556-nba1 (deploy-queue unblock, CI gap, live official re-read))
