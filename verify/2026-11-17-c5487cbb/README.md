# Verification record — session `arena/c5487cbb-nba1`, 2026-11-17

Scope: settle the now-final 2026-11-16 slate, keep the official per-game result feed current,
archive the 2026-11-17 injury edition with revision + retrieval stamps and diff it against the
previous edition, roll the origination horizon to 11/17–11/19 before tip, refresh the model
inputs from the three official team-stat pages, and publish the requirement-register state.

Nothing in this directory is inferred. Every number below was read first-hand in this session
from the URL printed beside it.

## Sources read first-hand in this session (UTC 15:4x–16:xx, 2026-11-17)

| Source | URL | What was read |
| --- | --- | --- |
| Official games page (11/16) | https://www.nba.com/games?date=2026-11-16 | All 8 finals, both scores, `Final` label on each |
| Gamebook PDF (official, per game) | https://statsdmz.nba.com/pdfs/20261116/20261116_<AWAY><HOME>_book.pdf | `SCORE BY PERIOD` (quarter scores) + full box score per player |
| Official injury index | https://official.nba.com/nba-injury-report-2026-27-season/ | 2026-11-17 editions listed 12:00 AM → 10:30 AM ET |
| Injury PDF (11/17 10:30 AM) | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-17_10_30AM.pdf | Full row set, transcribed into `data/official/injury_2026-11-17_1030AM_c5487cbb.json` |
| Team stats — advanced | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 30 team rows (GP/W/L/OffRtg/DefRtg/NetRtg/PACE/POSS…) |
| Standings | https://www.nba.com/standings | Win-loss by team, home/road splits |

## Gamebooks read (all 8 games of 2026-11-16)

Each row below was cross-checked twice: the final printed on the games page and the `FINAL` column
of the gamebook's `SCORE BY PERIOD` table, with the four quarters summed to the printed final.

| Game | Away Q1-Q4 | Away | Home Q1-Q4 | Home | Quarters sum to final |
| --- | --- | --- | --- | --- | --- |
| ORL@BOS 0022600245 | 20 30 25 40 | 115 | 17 24 36 28 | 105 | 115/105 ✓ |
| CHI@CLE 0022600246 | 31 17 31 36 | 115 | 25 32 31 38 | 126 | 115/126 ✓ |
| MEM@WAS 0022600247 | 33 26 42 35 | 136 | 35 34 18 33 | 120 | 136/120 ✓ |
| PHI@BKN 0022600248 | 33 45 27 30 | 135 | 26 33 36 28 | 123 | 135/123 ✓ |
| HOU@MIA 0022600249 | 15 31 35 29 | 110 | 29 33 39 27 | 128 | 110/128 ✓ |
| POR@MIN 0022600250 | 26 25 22 25 | 98 | 26 33 28 19 | 106 | 98/106 ✓ |
| GSW@NOP 0022600251 | 11 25 29 29 | 94 | 35 26 32 22 | 115 | 94/115 ✓ |
| PHX@DEN 0022600252 | 20 36 34 27 | 117 | 24 29 29 23 | 105 | 117/105 ✓ |

Note on HOU@MIA: the gamebook prints the first half and each later period on separate pages
(`Rockets 15 31 46 / HEAT 29 33 62` at the half, then Q3 35-39 and Q4 29-27). The quarter array
above reconciles to the printed final both ways (46+35+29 = 110; 62+39+27 = 128), so the split
is reconstructed from the official page rather than assumed.

## Irregularities found and flagged (published on the Flagged page, non-blocking)

1. **`data/official/results_feed_2026_27.json` still carries 25 scheduled `0-0` placeholder rows**
   for 11/16–11/18 (the F113/F-W02 class of defect). `engine/model_v2.py:load_results()` ingests
   them as decided games with a zero margin, which biases the measured road-win rate and deflates
   `sigma_margin`. This session refills the 11/16 rows from the verified finals and marks the
   remaining unplayed rows as scheduled with **null** scores, and adds a loader-side guard test.
2. **A.1 — one box-score row per game does not assemble into fixed columns** (HOU@MIA prints some
   rows with a collapsed cell, e.g. Isaiah Crawford / Jae'Sean Tate). Those rows are left out of the
   per-player capture and listed here rather than parsed by guess.
3. **A.2 — the 11/17 10:30 AM injury PDF's text render splits merged cells** across pages (a
   "Soreness" fragment and a bare `Reaves, Austin` row appear detached from their headers). The
   rows are transcribed with their matchup inferred **only** where the game-day block they sit in is
   unambiguous; the two detached fragments are recorded with `matchup: null` and flagged.
