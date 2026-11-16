| `arena/fbf3ff57-nba1` | `arena/fbf3ff57-nba1` | 2026-11-16 02:12 UTC | Integration seat (§47): fresh capture, 11/15 settlement, injury-PDF diff, Pages backlog. Live at this session's claim time — its file scope is read-only for this session. |
| `arena/dfef26dc-nba1` | `arena/dfef26dc-nba1` | 2026-11-16 02:1x UTC | **Site / shared-output rebuild seat** (§48): roll the horizon to 11/16–11/18, rebuild `scripts/**` → `site/**` + `index.html`, re-cut strategy/decisions/executive content, row-level verification, PR → `main`, Pages. Scope is non-overlapping with §47 by construction (§48.2). |

| `arena/754e9e54-nba1` | `arena/754e9e54-nba1` | 2026-11-16 (this session) | Full-cycle build: projection/bet site split, two independent estimators with disagreement headline, HCA pinned to measured home-win rate, luck z-score per team, arena-coordinate travel table, player game logs for injured players, market-anchored prior, possessions × ppp total model, refresh pipeline with freshness/provenance gates, sealed-ledger settlement at game-day end, pre-registration freeze, tamper-evident ledger, injury-PDF archive + diff, per-game result feed with quarter scores, clean landing page + category subpages, GitHub Pages publish (§44). Platform pins this session to its branch (deviation logged, as above). |
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
