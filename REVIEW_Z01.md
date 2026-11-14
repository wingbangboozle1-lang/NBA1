# REVIEW_Z01 — independent line-by-line verification (session `arena/212c2298-nba1`)

Date: 2026-11-14 (captures read 10:25–11:00 UTC). Scope: claims Z01–Z03 in
[COORDINATION.md](COORDINATION.md) §27. Every value below was read from an official NBA.com
page or the official injury-report PDF by this session, transcribed into
[`verify/212c2298/official_capture_2026-11-14.json`](verify/212c2298/official_capture_2026-11-14.json),
and compared row by row against the repository's published data by
[`verify/212c2298/check_all.py`](verify/212c2298/check_all.py) (results:
[`verify/212c2298/checks.json`](verify/212c2298/checks.json)). Nothing was inferred; values that
could not be confirmed are reported as unverified and left blank.

## 1. Official sources read this session (manual-review links)

| Input | Official source (read 2026-11-14 UTC) | Result |
| --- | --- | --- |
| 9 finals of 2026-11-13 (score, status, post-game records, game IDs) | <https://www.nba.com/games?date=2026-11-13> | 9/9 transcribed |
| ATL–CHI game page (headline, venue, status) | <https://www.nba.com/game/atl-vs-chi-0022600037> | "Bulls outlast Hawks in OT", United Center, Chicago, IL |
| ATL–CHI box score (period structure) | <https://www.nba.com/game/atl-vs-chi-0022600037/box-score> | period filter prints `Q1 Q2 Q3 Q4 OT1` → **exactly 1 overtime** |
| 27 horizon games 11/14–11/17 (pairings, tips ET, records, game IDs) | <https://www.nba.com/game/atl-vs-chi-0022600037> sidebar (read twice, identical) + per-game links | 27/27 transcribed |
| Calendar badges (games per day) | <https://www.nba.com/games?date=2026-11-13> | 11/13=9, 11/14=5, 11/15=9, 11/16=8, 11/17=5 |
| Injury report, 11/14/26 04:15 AM ET edition (current at read time) | <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf> | full table transcribed (21 player rows + team statuses) |
| Live GitHub Pages deployment | <https://wingbangboozle1-lang.github.io/NBA1/> (+ `site/pages/flagged.html`, `site/pages/source-check.html`) | renders; headline tiles and registers match the repository |

## 2. The nine 11/13 finals — 9/9 rows verified

| Game | Official | Repo (`data/verified/finals_2026-11-13.json`) | Status | Source |
| --- | --- | --- | --- | --- |
| NYK@IND | NYK 104 – IND 106, Final | same | VERIFIED | [0022600034](https://www.nba.com/game/nyk-vs-ind-0022600034) |
| MIL@ORL | MIL 99 – ORL 107, Final | same | VERIFIED | [0022600035](https://www.nba.com/game/mil-vs-orl-0022600035) |
| CLE@MIA | CLE 121 – MIA 133, Final | same | VERIFIED | [0022600036](https://www.nba.com/game/cle-vs-mia-0022600036) |
| ATL@CHI | ATL 117 – CHI 125, Final/OT | same score/status; repo `ot: null` | VERIFIED; **OT count resolved: 1** | [0022600037](https://www.nba.com/game/atl-vs-chi-0022600037) |
| MEM@NOP | MEM 142 – NOP 111, Final | same | VERIFIED | [0022600038](https://www.nba.com/game/mem-vs-nop-0022600038) |
| UTA@HOU | UTA 118 – HOU 125, Final | same | VERIFIED | [0022600039](https://www.nba.com/game/uta-vs-hou-0022600039) |
| GSW@SAS | GSW 85 – SAS 123, Final | same | VERIFIED | [0022600040](https://www.nba.com/game/gsw-vs-sas-0022600040) |
| POR@SAC | POR 120 – SAC 107, Final | same | VERIFIED | [0022600041](https://www.nba.com/game/por-vs-sac-0022600041) |
| OKC@LAC | OKC 112 – LAC 113, Final | same | VERIFIED | [0022600042](https://www.nba.com/game/okc-vs-lac-0022600042) |

**Resolved irregularity (was open):** the ATL–CHI `ot` field was left `null` ("not confirmed") in
the verified-finals file and in the §20 audit. The official box-score period filter
(`Q1 Q2 Q3 Q4 OT1`) and the official recap headline ("Bulls outlast Hawks in OT") confirm
**1 overtime**. Fix request **R-Y2** logged in COORDINATION.md §27 (data owners apply it).

Post-game records printed on the 11/13 cards cross-check against the horizon sidebar
(all 18 teams agree on both official readings — `finals: post-game records cross-consistent` PASS).

## 3. The 27-game horizon (11/14–11/17) — structure 27/27 verified

Date, tip time, matchup and game ID for all 27 games match the official schedule exactly
(`site/data/lines.json`, `data/derived/horizon_lines.json`, `data/official/slate.json` (22 rows),
and every published pick row maps 1:1 to an official game). Per-day counts match the official
calendar badges (5 / 9 / 8 / 5). Independent agreement with the deployed
[Source Check](https://wingbangboozle1-lang.github.io/NBA1/site/pages/source-check.html) page:
identical split (see §5).

**Team-record cells (54):** 25 match the current official card; **29 are stale and every one is
explained exactly** by the team's 11/13 result (repo value + W/L = official value); **0
unexplained**. The stale cells are the known F29/F-C02 disclosure (records frozen pre-11/13);
they are listed row by row in `checks.json` → `explained_stale` with each game's official URL.

**Repeated pairings (F33) re-checked:** the official schedule itself prints NYK@TOR twice
(11/15 `0022600241`, 11/17 `0022600253`) and POR@MIN twice (11/16 `0022600250`, 11/17
`0022600254`), each with a distinct game ID. Verified as printed; still worth a human glance
(same-venue repeats in 3 days are unusual), stays on the register.

## 4. Injury designations — 21/21 player rows verified against the current official edition

Compared `site/data/injuries.json` and the injury columns of `site/data/lines.json` with the
**11/14/26 04:15 AM ET** official PDF (the newest edition at read time):

| Game | Site (11/13 07:30 PM ET edition) | Official 11/14 04:15 AM ET edition | Status |
| --- | --- | --- | --- |
| DEN@NOP | DEN 4 listed (Holmes II Out, Nembhard Out, Strawther Out, Whitmore Out); NOP NOT YET SUBMITTED | identical names/statuses/reasons | VERIFIED |
| DAL@CLE | DAL 6 listed (Biberovic Out, Christie Questionable, de Larrea Out, Johnson Jr. Probable, Lively II Out, Martin Available); CLE NOT YET SUBMITTED | identical | VERIFIED |
| DET@MIA | DET 7 listed (Duren Out, Harkless Questionable, Joe Out, Jones Questionable, Lanier Out, Okorie Out, Onyenso Out); MIA NOT YET SUBMITTED | identical | VERIFIED |
| BKN@MEM | BKN 6 listed (Bilodeau Out, Brown Jr. Questionable, Jefferson Out, Nelson Out, Saraf Out, Traore Probable); MEM NOT YET SUBMITTED | identical (the Traore row's dropped Team cell in the PDF is the known F27; the site's Brooklyn attribution is disclosed) | VERIFIED |
| CHI@MIN | MIN 3 listed (Beringer Available, DiVincenzo Out, Edwards Out); CHI NOT YET SUBMITTED | identical | VERIFIED |
| 11/15–11/17 games | "NO ENTRY IN THE 11/13/26 07:30 PM ET EDITION" | 04:15 AM edition prints NOT YET SUBMITTED for every 11/15+ team (day-before reports not due) | VERIFIED (equivalent state; wording differs) |

Consequences recorded:

- **No designation changed between the edition the site used and the current edition.** An
  edition refresh changes labels, not values. (Cross-note to X01, `arena/2ef89703-nba1`.)
- **F32 (DET@MIA time mismatch) is resolved by the newer edition:** the 04:15 AM PDF prints
  `08:00 (ET)` for DET@MIA, matching the schedule. The `07:00` print belonged to older editions.
  Fix request **R-Y3** (update the F32 row to resolved).

## 5. Statistics — independently recomputed

| Check | Result |
| --- | --- |
| Exact two-sided binomial p, Wilson 95% CI, hit rate for all 10 strategies (`site/data/validation.json`) | **PASS** — all 10 reproduce exactly (e.g. S1 16-7 → p = 0.0931, Wilson [0.491, 0.844]) |
| Units per strategy = sum of its graded play rows | **PASS** for all 10. Note: for S9 (parlay) and S10 (same-game parlay) the published `units_at_minus110` is the parlay-priced sum (−0.147 and +2.919), **not** flat −110 grading (−1.273 and −3.727). The metric name is misleading for those two rows (irregularity **R-Y4**). |
| Window metrics (MAE/RMSE/bias/straight-up, 51 games) | **PASS** — reproduce exactly from the published `docs/data/backtest.json` rows (MAE margin 12.89, MAE total 14.86, RMSE 17.10/19.88, bias −0.2, straight-up 37-14; home-margin sign convention per F27 used) |
| Settlement ledger arithmetic (`integration/out/settlement.json`) | **PASS** — every settled row's `actual_margin_home`/`actual_total` recompute from its official score string |
| Correlation register Tier A (10 pairs, n = 30) | **PASS** — all 10 `r` and normal-approximation p-values reproduce exactly from the committed `teams_advanced_2026_27.json` / `teams_scoring_2026_27.json` rows (each of which carries its own official source URL) |

**New irregularity R-Y1 (cross-ledger, F26-class):** the settlement ledger
(`integration/out/settlement.json`) carries **different model numbers than the backtest ledger**
for the same 51 games (e.g. BKN@ATL 11/07: +7.23 vs +3.4; NYK@CLE: −1.54 vs −5.4; only 1 of 51
games agrees within 0.05 pts). Each ledger is internally consistent, but the two published
"model margin" columns disagree per game and would give different MAE for the same window
(12.79 vs 12.89). This is the same defect class as F26 (two engine lineages); the pages do not
label which engine produced which column. Suggested action: label every model column with its
engine and freeze one ledger as canonical for settlement.

## 6. Live site (Z03)

- GitHub Pages status: `built` for `main`; live at
  <https://wingbangboozle1-lang.github.io/NBA1/>.
- Landing page tiles read off the live site: 27 games · 27 lines · 63 paper picks · 10 strategies ·
  51 out-of-sample games · 37 open flags — all agree with the committed data.
- [Flagged for Review](https://wingbangboozle1-lang.github.io/NBA1/site/pages/flagged.html)
  renders 37 rows (F1–F37) with source links, as does
  [Source Check](https://wingbangboozle1-lang.github.io/NBA1/site/pages/source-check.html)
  (27 horizon rows, 29 stale-record rows). The Source Check row split (25 match / 29 stale /
  0 unexplained) is independently reproduced by this session's capture — same numbers.
- One staleness note: the live executive summary says the newest injury edition is
  "11/13/26 07:30 PM ET"; the 11/14 04:15 AM edition has since been published (values unchanged,
  §4). Owner: the injury-currency claim (X01).

## 7. What this session did NOT verify (left blank, not inferred)

| Item | Why | Where it is flagged |
| --- | --- | --- |
| Sportsbook prices / true market edges | no NBA-operated source publishes a price; the sandbox policy forbids non-official odds sources | F3 (register) |
| Player minutes outside the official top-50 table | official table exposes only page 1 (50 players) to a plain fetch | F2 |
| Player-prop / SGP leg correlations | needs play-by-play corpus; Tier C rows stay `null` | F6, correlations page Tier C |
| Venue strings on the 27 horizon rows | not printed on the schedule sidebar read this session; carried from earlier captures with their own sources | not re-verified here |
| 11/13 game times | official games page does not print tip times for completed games | n/a |
| Model constants (k, alpha, weights, prop multipliers) | modelling choices, not official measurements — verified only for disclosure, not for truth | F4 |

## 8. Verdict

Every published score, status, pairing, tip time, game ID and injury designation that this
session checked against an official source **matches or is exactly explained** (29 stale record
cells, each pinned to the 11/13 result that caused it). The strategy statistics are internally
sound and reproduce exactly from their rows. Four irregularities are recorded above
(**R-Y1** cross-ledger numbers, **R-Y2** ATL–CHI OT now resolvable, **R-Y3** F32 resolvable,
**R-Y4** misleading units label); none blocks the site; all are logged in COORDINATION.md §27
for the data owners and the Flagged register.
