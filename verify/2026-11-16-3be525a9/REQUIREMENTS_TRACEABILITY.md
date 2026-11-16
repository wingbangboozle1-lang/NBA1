# Requirements traceability — session `arena/3be525a9-nba1`

**Date:** 2026-11-16 (UTC). **Base:** `main` `047103e`. **Scope:** read-only audit of the repo against the brief, plus one first-hand official spot-check. No data files, site pages, or shared outputs were edited.

## How this was checked

- **Repo inspection** (`git`, `ls`, `grep`, `python3`) for whether each brief item has an artifact on `main`.
- **`python3 scripts/verify_all.py`** → exit 0, `VERIFY OK`. Caveat from the script's own footer: *"this checks provenance/link structure only; it does not fetch sources or compare their values to the published rows."* It is a consistency check, not a source re-verification.
- **First-hand official spot-check** of the 2026-11-15 slate using the web-fetch channel (not the sandbox shell). Result: `https://www.nba.com/games?date=2026-11-15` **is reachable** and returned server-rendered finals. (The sandbox shell itself returns HTTP 000 for nba.com; the two channels differ, which the board's F-47-A finding also notes.)
- Sandbox outbound allow-list (github, npm, pypi) means no other official host was tested from the shell.

## Register

Status key: **Present** = artifact exists on `main` and was not re-verified here · **Partial** = exists but a gap is confirmed · **Missing** = no artifact at the path or under any name found · **Not verified** = exists, value/behaviour not checked in this session.

| # | Brief item | Artifact(s) on `main` | Status | Irregularity / gap (confirmed) |
|---|---|---|---|---|
| 1 | Scheduled job refreshes schedule, standings, team stats, injuries; rebuild only after gates | `.github/workflows/refresh-data.yml` (cron 11:15, 15:15, 22:15 UTC); `engine/refresh_gate.py`; `engine/verify_refresh.py` | Present (Not verified) | Board named `.github/workflows/refresh.yml` and `scripts/refresh_gate.py`; actual names differ. Not executed here. |
| 2 | Official per-game result feed: date, teams, final score, quarter scores; one row per game | `data/official/results_2026-11-15.json` (quarters present), `data/official/results_2026-11-15_dfef26dc.json` | **Partial — stale** | 3 of 9 games on 11/15 are recorded as not-final although the official page shows Final (see spot-check). Board's named path `data/results_feed.json` does not exist. |
| 3 | Settle only after finals are verified | `data/settlement/settlement_2026-11-14.json`; `scripts/settle_slate.py`, `scripts/settle_2026_11_14.py` | **Partial — gap** | No `settlement_2026-11-15.json`. All 9 11/15 games are Final on the official page, so the 11/15 day is settleable now but not settled. Stale feed (item 2) is the blocker. |
| 4 | Store every injury PDF with timestamp; diff consecutive reports | `data/raw/injury_pdfs/` (8 PDFs + JSON sidecars, content-hashed names); `engine/injury_diff.py`; `data/official/injury_diff_*.json` | Present | Board's named path `data/injury_pdfs/` and `scripts/diff_injury_pdfs.py` do not exist; the actual locations are used. |
| 5 | Pre-registration file per strategy before first bet | `data/prereg/S01…S08.json`, `data/prereg/T-PARLAY.json`, `data/prereg/Prereg_index.json`; `scripts/freeze_prereg.py`; archives `data/archive/prereg_2026-11-15/`, `…_2026-11-16/` | Present (Not verified) | Freeze timestamps and hashes not checked in this session. |
| 6 | Tamper-evident ledger: hash picks, publish before tip, verify after settlement | `data/ledger/ledger.json` (head + entries), `scripts/verify_ledger.py`, `scripts/verify_inline.py` | Present (Not verified) | Ledger verification command not re-run here. |
| 7 | Two independent estimators; disagreement as headline | `engine/estimator_a.py`, `engine/estimator_b.py`, `engine/disagreement.py`; `data/estimator_a.json`, `data/estimator_b.json`, `data/disagreement.json` | Present (Not verified) | Logic not audited line by line in this session. |
| 8 | Home-court advantage pinned to measured home-win rate | `engine/hca.py`, `data/hca_measured.json` | Present (Not verified) | — |
| 9 | Luck z-score per team; refuse strategies leaning on out-of-band teams | `engine/luck_zscore.py`, `data/luck_zscores.json` | Present (Not verified) | — |
| 10 | Rest, B2B, 3-in-4 from official schedule; travel distance from sourced arena coordinates | Schedule: `data/schedule_2026_11_13_to_16.json`, `data/official/schedule_*.json`; travel: `scripts/travel_distance.py`, `data/arenas.json` | **Partial — sourcing gap** | `data/arenas.json` `source_note` says coordinates come from *"publicly available arena location data"* and are *"Not an official NBA-published coordinate table - flagged for review."* No per-row official URL. The brief requires a sourced table; this does not meet it. |
| 11 | Minutes redistribution: top-8 shares and replacement shares | `engine/minutes_redist.py`, `data/minutes_redistribution.json`, `data/players_minutes_2026_27.json` | Present (Not verified) | — |
| 12 | Market-anchored prior weighted by out-of-sample log-loss | `engine/market_prior.py`, `scripts/market_anchor.py`, `data/market_prior.json` | Present (Not verified) | OOS log-loss measurement not checked. |
| 13 | Total = possessions × points-per-possession | `engine/total_model.py` | Present (Not verified) | — |
| 14 | Parlays priced with measured rho; naive product printed beside it | `engine/parlay.py`, `scripts/measure_rho.py`, `data/parlay_pricing.json` | Present (Not verified) | — |
| 15 | Site split into **projection** (publishable) and **bet** (gated) surfaces, never mixed | **No `site/projection/` or `site/bet/` directories.** `site/pages/` holds mixed pages (e.g. `picks.html`, `props.html`, `decisions.html`). | **Missing** | Split was not implemented under the board's named paths; the pages mix surfaces. This is a real gap against the brief. |
| 16 | Rotation availability as its own column on the picks page | `site/pages/picks.html` contains "rotation" | Present (Not verified) | Column header not checked visually in this session. |
| 17 | Injury-report revision time and retrieval time in the Injuries banner | `site/pages/injuries.html` contains "revision and retrieval time" | Present (Not verified) | Values in the banner not checked against the PDF headers. |
| 18 | Sealed ledger settled at game-day end; settlement stamp visible | `site/pages/results.html`, `site/pages/decisions.html` mention settlement | **Partial** | Settlement stamp exists for 11/14 only; 11/15 unsettled (item 3). |
| 19 | Re-read the three official team-stat pages (traditional, opponent, advanced) and re-cut inputs | `data/official/teams_traditional_2026-11-15.json`, `teams_opponent_2026-11-15*.json`, `teams_advanced_2026-11-15*.json`, `data/official/team_stats_recut_2026-11-15_2340Z.json`, `scripts/recut_model_inputs.py` | Present (Not verified) | Captures are dated 11/15 — they are older than the 11/16 slate. |
| 20 | Per-player game logs (minutes, pts, rebs, asts, opponent) for injured players | `data/player_gamelogs/`, `data/official/player_game_logs_2026-11-15.json`, `scripts/capture_gamelogs.py` | Present (Not verified) | Completeness for every injury-report player not checked. |
| 21 | Originated lines + picks for every slate up to 3 days ahead | `data/originated_lines.json`, `data/originated_lines_refresh.json`, `data/archive/horizon_picks_2026-11-1{4,5,6}.json`, `scripts/originate_lines.py`, `scripts/generate_picks.py` | Present (Not verified) | Horizon picks published for 11/14–11/16; the 11/17 slate is not in the archive set checked. |
| 22 | Executive summary | `EXECUTIVE_SUMMARY.md`, `site/pages/` | Present | — |
| 23 | Suggestions section (review before implementing) | `suggestions.html`, `site/pages/suggestions.html`, `data/suggestions.json` | Present | — |
| 24 | Questions / information / answers register | `site/pages/questions.html`, `data/questions.json`, `data/questions_modelling.json` | Present | — |
| 25 | Flagged-for-Review page with source links | `site/pages/flagged.html`, `data/flags.json` | Present | — |
| 26 | Landing page and category subpages on GitHub Pages | Root `index.html` (published by `.github/workflows/pages.yml`, which uploads `.`); `site/pages/*.html` (27 pages) | Present | Pages deploy status not re-checked in this session. |
| 27 | Every table row has an official source link; unverifiable values blank and flagged | `scripts/verify_all.py` (1,966 rows, 1,888 with allowed official link; 78 explicit no-source marks) | Present, **with caveat** | 78 rows are *explicitly marked no-source* rather than blank; the script checks structure, not that the linked source supports the value. |

## Verification performed on the 2026-11-15 slate

Full table: [`spotcheck_2026-11-15.md`](spotcheck_2026-11-15.md); script: [`spotcheck_2026-11-15.py`](spotcheck_2026-11-15.py).
Official page read: https://www.nba.com/games?date=2026-11-15 (pages 1–2).

- 6 of 9 repo rows match the official page exactly (game ID, status, final score).
- 3 of 9 repo rows (HOU@WAS, ATL@MIL, OKC@SAC) are recorded as not-final, but the official page prints Final: HOU 147–119 WAS, ATL 113–106 MIL, OKC 125–103 SAC. **Stale rows; no value was changed in this session** (the feed is owned by another session — see COORDINATION §50).
- Quarter scores for the three stale games were **not** read (not on the list page) and were **not** filled in.

## Irregularities to review

1. `data/results_2026-11-15` feed stale for 3 of 9 games (above).
2. No 11/15 settlement file although all 9 games are Final on the official page.
3. No `site/projection/` / `site/bet/` split (brief item 15).
4. `data/arenas.json` coordinates not sourced to an official or per-row URL (brief item 10 requires sourced coordinates).
5. Board paths named in the brief (`scripts/refresh_gate.py`, `scripts/settle_ledger.py`, `data/results_feed.json`, `data/injury_pdfs/`, `scripts/diff_injury_pdfs.py`) do not exist under those names; equivalents are at other paths (listed above). Naming should be reconciled in the board.
6. COORDINATION.md (5,473 lines) carries 10 `ACTIVE CLAIM` headers and several overlapping full-cycle claims for the same scope (M01–M25 in §44 and others). Several are stale. Open PRs at check time: #130 (`arena/c348e6c7-nba1`, integration publish) and #136 (`arena/3242d896-nba1`). Integration ownership is unresolved on the board.

## Not done in this session (honest scope)

- Re-running the refresh, settlement, ledger verification, pre-registration hash check, or the model estimators.
- Settling 11/15 — blocked on item 2 and on the integration seat's ownership of `data/settlement/`.
- Creating the projection/bet site split — shared site output, owned by the integration seat.
- Merging to `main` — not done; the integration session must do it.
