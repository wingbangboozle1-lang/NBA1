# Verification report — session `arena/fec7d5ae-nba1` (2026-11-16)

**Scope (COORDINATION §50):** first-hand official three-page team-stat re-cut + horizon /
standings / injury / results re-verification + requirements-register closure.
**Base:** `main` `047103e`. **Capture window:** 2026-11-16 ~14:35 UTC.

Every value below was read directly off the named official page at capture time. Nothing is
inferred, modelled or filled in. A value that could not be confirmed is left blank and flagged.

---

## 1. The three official team-stat pages — RE-READ and RE-CUT (closes R20 / F24)

| Official page | Result at 2026-11-16 ~14:3xZ | Source |
| --- | --- | --- |
| Teams **Advanced** | full 30-row table returned (GP, OffRtg, DefRtg, NetRtg, PACE, TS%, eFG%, PIE, POSS) | [nba.com/stats/teams/advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| Teams **Traditional** | full 30-row table returned (GP, W, L, PTS/PPG, …) | [nba.com/stats/teams/traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season) |
| Teams **Opponent** | full 30-row table returned (GP, W, L, Opp PTS/PPG allowed, …) | [nba.com/stats/teams/opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season) |

**Flag F24 is CLOSED.** Prior sessions recorded "the advanced-stats table is not retrievable
from this environment." All three pages now return the full official table. The re-cut is
written to:
- `data/official/team_stats_recut_2026-11-16_fec7d5ae.json` — the verbatim first-hand capture,
  one row per team, each with its per-team official source URL.
- `data/derived/team_stats_recut.json` — the re-cut model inputs (net rating, pace, points per
  possession, etc.).

**Cross-checks (all pass, enforced by `scripts/recut_team_stats.py`):**
- C1 `W + L = GP` for all 30 teams in all three tables.
- C2 `NetRtg = OffRtg − DefRtg` within 0.25 (rounding).
- C3 the 30-team abbreviation set is identical across the three tables.
- C4 league scoring balance: mean PTS 113.743 vs mean OppPTS 113.763 ppg — a 0.02 ppg gap,
  which is the strongest available internal evidence that the transcription is correct
  (every point scored is a point allowed league-wide).
- C5 GP / W / L agree across the three tables for every team.

**The AST Ratio rendering discrepancy flagged by `arena/49f70042-nba1` does NOT reproduce.**
That session's `team_stats_recut_2026-11-15_2340Z.json` recorded a league-wide re-read of the
AST Ratio column that read ~38.x against a published ~19.x, and resolved it by keeping the
published value. This session's independent full-table read renders AST Ratio correctly
(e.g. San Antonio 19.4, matching the published value), so the discrepancy was a chunked-read
artifact of that session, not a property of the page. Recorded so the next reader does not
re-flag it.

## 2. Horizon re-verification — 25 games (R25) — PASS

Read `nba.com/games?date=2026-11-16`, `=2026-11-17`, `=2026-11-18` directly and compared every
(date, game_id, matchup, tip) against the stored capture
`data/official/official_schedule_2026-11-16_to_18_dfef26dc.json`.

- **25 rows compared, 0 mismatches.** Per-day first-hand counts: 11/16 = 8, 11/17 = 5, 11/18 = 12.
- Sources: [11/16](https://www.nba.com/games?date=2026-11-16) · [11/17](https://www.nba.com/games?date=2026-11-17) · [11/18](https://www.nba.com/games?date=2026-11-18)

**Irregularities independently confirmed (not introduced by this session):**
- **F102 — POR@MIN double-booking.** Portland @ Minnesota appears on **11/16** (game id
  `0022600250`, 8:00 PM ET) **and** on **11/17** (game id `0022600254`, 8:00 PM ET), under two
  different official game ids. Confirmed on both official games pages — a real official
  scheduling entry, not a parsing artefact.
- **F101 — GSW@NOP tip-time conflict.** The 11/16 games page prints **8:00 PM ET** for
  `0022600251`; an earlier capture recorded 09:00 PM ET. Both values are published on Flagged.

## 3. Standings + home-court advantage (R09) — the pinned HCA is one cycle stale

Read [nba.com/standings](https://www.nba.com/standings) and recomputed the home-win rate from the
HOME column of all 30 teams.

| | Published (pinned) | Measured now (14:35Z) |
| --- | --- | --- |
| Home wins | 102 | 102 |
| Home games | 193 | 196 |
| Home-win rate | **0.5285** | **0.5204** |

Home **wins** are unchanged; three more **home games** have been played (the 11/15 late / 11/16
window) and the home team did not win them, so the rate fell 0.0081. The model pins HCA to the
measured home-win rate (R09); the pinned value 0.5285 is therefore one measurement cycle stale.
**Reported, not silently applied** — the model still carries 0.5285; updating the pin is a
deliberate model change, logged for the integration seat rather than made unilaterally here.

## 4. Injury report — a newer edition now exists (R04 / R18)

Read [official.nba.com/nba-injury-report-2026-27-season](https://official.nba.com/nba-injury-report-2026-27-season/).
The index now lists **November 16** editions (12:00 AM ET onward), newer than the **11/15 09:00 PM
ET** edition the site was built on. The injury layer is fresher than the published build reflects.
No injury values were re-transcribed this session (the injury-PDF capture is owned by the open
capture PR #136); the finding is recorded so the next capture pass uses the 11/16 edition.

## 5. 11/15 results — the slate is now fully settleable (R02 / R03 / R19)

Read [nba.com/games?date=2026-11-15](https://www.nba.com/games?date=2026-11-15). At 02:27Z three
games were still in progress and the slate was not settleable. **All 9 games are now Final:**

| Game | Final | Status |
| --- | --- | --- |
| IND @ PHI | 124–131 | Final |
| LAL @ PHX | 131–123 | Final |
| CHA @ LAC | 105–113 | Final |
| SAS @ UTA | 110–102 | Final |
| NYK @ TOR | 112–108 | Final/OT |
| DAL @ BOS | 94–131 | Final |
| HOU @ WAS | 147–119 | Final |
| ATL @ MIL | 113–106 | Final |
| OKC @ SAC | 125–103 | Final |

The 11/15 pre-tip archive can now be settled by `scripts/settle_slate.py` (exit-3 refusal no
longer applies). Settlement execution is owned by the refresh workflow / integration seat; this
session verifies the input state and does not run the settlement.

## 6. What this session did NOT do (scope discipline)

- Did **not** edit `data/raw/**`, `verification.html`, the broad `site/**` rebuild or `index.html`
  (owned by open PRs #130 / #136). A request to fold this verification onto the site is logged in
  COORDINATION §50.4 for the integration seat.
- Did **not** re-run the model pipeline or re-price lines; the re-cut inputs are published as
  verified inputs, not fed through the model unilaterally.
- Did **not** re-transcribe the injury PDFs (owned by the capture PR).

## 7. Artifacts produced

| File | What it holds |
| --- | --- |
| `scripts/recut_team_stats.py` | the first-hand three-page re-cut + cross-checks |
| `data/official/team_stats_recut_2026-11-16_fec7d5ae.json` | verbatim 30-team capture, source-linked |
| `data/derived/team_stats_recut.json` | re-cut model inputs |
| `scripts/verify_hca_fec7d5ae.py` | home-win-rate re-measurement |
| `scripts/verify_horizon_fec7d5ae.py` | 25-game horizon first-hand recheck |
| `verify/2026-11-16-fec7d5ae/hca_recheck.json` | HCA measurement record |
| `verify/2026-11-16-fec7d5ae/horizon_recheck.json` | horizon comparison record |
