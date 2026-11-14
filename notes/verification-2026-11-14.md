# Verification report — 2026-11-14 (session arena/2329cb68-nba1)

Line-by-line reverification of the merged repository's published data against the
official NBA sources, performed with an **independent second transcription**.
Evidence file: `data/refresh_2026_11_14/official_captures_2026-11-14.json`.
Re-run this report at any time: `python3 engine/verify_refresh.py`.

## Method

Every row published by either build was re-read on the official source on 2026-11-14
and transcribed again, from scratch, into the evidence file. The two transcriptions
(2026-11-13 capture vs 2026-11-14 re-read) were then compared row by row. A row passes
only if player/team/matchup/status/reason (injuries) or date/matchup/tip time/both
records (slates) agree exactly after whitespace normalisation.

Sources re-read (all official):

- Injury reports 2026-11-13, five editions:
  [12:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf),
  [3:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf),
  [5:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_00PM.pdf),
  [5:15 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf),
  [7:30 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf)
  (hub: [official.nba.com injury reports](https://official.nba.com/nba-injury-report-2026-27-season/))
- Slates: [11/13](https://www.nba.com/games?date=2026-11-13) (via live game-page strip),
  [11/14](https://www.nba.com/games?date=2026-11-14),
  [11/15](https://www.nba.com/games?date=2026-11-15),
  [11/16](https://www.nba.com/games?date=2026-11-16),
  [11/17](https://www.nba.com/games?date=2026-11-17)
- Game pages: [NYK@TOR 0022600253](https://www.nba.com/game/nyk-vs-tor-0022600253),
  [POR@MIN 0022600254](https://www.nba.com/game/por-vs-min-0022600254),
  [ORL@BOS 0022600245](https://www.nba.com/game/orl-vs-bos-0022600245)

## Repo review findings (line by line)

- The repository carries **two complete builds** (Build A 'Edge Lab', Build B
  'Backtested Desk'), both preserved after the 2026-11-13 merge. Each is internally
  consistent and each passes its own verification suite (`scripts/verify_all.py` ->
  VERIFY OK; Build B data validated by the Pages workflow checks).
- The three injury datasets that looked contradictory are three **different official
  editions** (12:00 PM = 75-row legacy page `docs/injuries.html`; 3:00 PM = 88-row
  Build A data with a 12:00 PM movement column; 5:15 PM = 119-row interim capture;
  7:30 PM = 122-row Build B data). Each
  row-set verifies against its own edition, and every difference between editions is a
  documented status movement — no unexplained difference remains.
- Build A and Build B use different transcription policies for PDF continuation rows
  with blank team cells (Build A keeps 3 rows unattributed and flagged; Build B fills
  the team from the PDF's own row context and documents it). Both are faithful to the
  PDF; the difference is policy and is recorded for review.

## Irregularities flagged (none corrected, all published for review)

1. **Repeat matchups (F21)** — NBA.com publishes NYK@TOR on 11/15 and 11/17 and
   POR@MIN on 11/16 and 11/17 (same arenas, distinct game ids). Confirmed on the
   official game-page titles. Left exactly as published.
   Review: <https://www.nba.com/games?date=2026-11-17>
2. **11/17 competition labels blank (F23)** — not printed on the official pages and
   therefore never inferred (venues/cities were later verified from https://www.nba.com/schedule
   by session arena/f80dcc4a-nba1 and filled with that source). Review: <https://www.nba.com/games?date=2026-11-17>
3. **Official PDF typo + extraction quirks (F22)** — the 12:00 PM edition prints
   'Suggs, Jalan'; some continuation rows lose reason cells in text extraction. Both
   transcriptions normalise the name and keep printed reasons where legible.
   Review: <https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf>
4. **11/13 games were in progress at capture** (Q2 of NYK@IND and MIL@ORL live at
   00:52Z); every result/grade cell for 11/13 stays blank (never zero) until official
   finals publish.
5. Still open from the 2026-11-13 builds and unchanged: F2 (player minutes known for
   50 of 465 players), F3 (no official book prices, so no market-validated ROI), F7
   (the automated refresh workflow has never executed), F5 (no archived report
   editions before 11/13).

## What remains blank / unverified on purpose

- 2 of 88 Build A rows have no `status_12pm` cell (they are outside the 12:00 PM
  edition or unattributed) — left blank.
- 11/17 competition labels — blank (F23); venues/cities verified from the official schedule page.
- All settled-record/ROI columns for 11/13-11/17 — blank pending official finals.
- Player per-game stats and market prices — not machine-readable from an official
  source from this environment (F1/F3); never inferred.

## Injury rows — Build B `data/raw/injuries.json` vs 7:30 PM official PDF (122 rows)
- PASS: all 122 rows match the independent 2026-11-14 transcription (player, status, reason, team, matchup), including the 5 NOT YET SUBMITTED team rows.

## Injury rows — Build A `data/injury_report_2026_11_13.json` vs 3:00 PM official PDF
- PASS: all 88 attributed rows match the 3:00 PM transcription with the five documented edition deltas applied (Cain/da Silva/Suggs/Achiuwa/Murray).
- PASS: 3 rows kept unattributed (blank team in the PDF, no-inference rule) and 5 matchup-grouped NOT YET SUBMITTED entries recorded as published.
- PASS: Build A accounting closes: 88 attributed + 3 unattributed = 91 player rows, matching the 3:00 PM PDF exactly.
- PASS: all 9 moved status_12pm cells match the 12:00 PM edition PDF re-fetched 2026-11-14 (9 status movements confirmed row by row).

## Slate rows — official NBA.com pages vs captured schedules (36 rows)
- PASS: Build B upcoming: 27 rows match the official slate pages on date, matchup, tip time and records where carried.
- PASS: Build B in-progress 11/13: 9 rows match the official slate pages on date, matchup, tip time and records where carried.
- PASS: Build A: 36 rows match the official slate pages on date, matchup, tip time and records where carried.
- PASS: every official slate row in the evidence file is present in the repo schedules.

## Cross-checks
- PASS: NBA.com per-day game counts (9/5/9/8/5 for 11/13-11/17) equal the slate row counts captured.
- PASS: NYK@TOR (11/15 & 11/17) and POR@MIN (11/16 & 11/17) repeat matchups confirmed on official game pages (titles read 'Nov 17, 2026' for 0022600253 / 0022600254). Flagged as an irregularity for human review, not corrected.
- PASS: Injury report editions chain (12:00 -> 03:00 -> 05:00 -> 05:15 -> 07:30 PM) explains every status difference between the transcriptions (incl. 8 moves 5:15->7:30 PM and Denver's NYS team row replaced by 4 named players); no unexplained difference remains.

## Totals

- Verifications failing: **0**
- Rows re-verified line by line against official sources on 2026-11-14: 122 + 91 (injury rows, two editions) + 36 (slate rows) = **249**
- Sources: see `data/refresh_2026_11_14/official_captures_2026-11-14.json` → `meta.sources`.
