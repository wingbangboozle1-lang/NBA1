# Integration desk — report for 2026-11-14

Capture: 2026-11-14T00:37Z to 2026-11-14T01:05Z · session `arena/2edb85af-nba1` · 22 games priced, 51 graded out of sample.

## Executive summary

1. **The margin carries information; the total does not.** Mean absolute error on the final margin is **12.787** points against **15.276** for predicting a single constant across the same 51 official finals — a gain of 2.489 points. On totals the model scores **14.693** where a constant scores **14.375**, so the possession-based total is 0.318 points *worse* than doing no work. Gate V3b fails on purpose and is published as a failure.
2. **No component earns its keep at this sample size.** Removing home court moves the margin error by +0.052, removing the back-to-back penalty by +0.013, and removing shrinkage by +0.358 points — all inside a ±2.8 interval. They stay in the model because the theory supports them, and they are flagged because the data cannot yet confirm them.
3. **What withholds picks is the injury report, not the model.** Of 22 priced games: 0 pass every rule, 5 are refused because one side had filed and the other had not, 9 are provisional until their date's report exists, and 8 sit inside the model's own noise. Every rejection is printed with its reason rather than dropped.
4. **Rotation impact could not be sized.** Of 26 official absences for 11/14, exactly one has verified season minutes anywhere in this repository. Vacated minutes reduce the named player's team and are *not* re-spread across his teammates — re-spreading them would have meant inventing the numbers that make a rotation model look good.
5. **Prop dispersion is measured now, and still unusable.** 12 official game-log rows across 3 players give a real σ where the repo previously used a constant; every prop and parlay row carries `usable_for_staking: false`, and within-player correlations have intervals that cross zero.
6. **Nothing here is a bet.** No sportsbook price is reachable from this environment, so break-even, hold, ROI and CLV are blank everywhere: 3 gates are BLANK for that reason and 4 FAIL. The leaderboard's top row is not validated and no reward is payable to any row of it.

## Gate ledger

| Gate | Requirement | Status |
| --- | --- | --- |
| V1 | Out-of-sample, no look-ahead | **PASS** — fit ends 2026-11-05, first graded game 2026-11-06 |
| V2 | Sample floor | **FAIL** — 51 |
| V3 | Beat a constant on the margin | **PASS** — 12.787 vs 15.276 |
| V3b | Beat a constant on the total | **FAIL** — 14.693 vs 14.375 |
| V4 | Calibration of the win probability | **PASS** — 0.1885 |
| V5 | Stability across halves | **PASS** — 23/28 games, MAE 12.893 vs 12.7 |
| V6 | Uncertainty published | **PASS** — MAE margin 95% CI [10.0735, 15.6461] |
| V7 | Provenance of every row | **PASS** — enforced by common.assert_official at load time |
| V8 | Rotation reassignment | **BLANK** — None |
| V9 | Availability completeness | **FAIL** — 0 of 5 games have both sides filed; 5 of 5 have exactly one side filed |
| V10 | Market comparison / closing line value | **BLANK** — None |
| V11 | Pricing of props and parlays | **FAIL** — 3 of 465 players have logs captured |
| V12 | Reproducibility | **PASS** — deterministic: fixed-seed LCG bootstrap, no RNG, no wall-clock in any figure |
| V13 | Out-of-sample test of the absence adjustment | **BLANK** — None |

## The slate, in one table

| Date | Matchup | Spread (home) | Total | P(home) | Tier |
| --- | --- | --- | --- | --- | --- |
| 2026-11-14 | [DEN@NOP](https://www.nba.com/games?date=2026-11-14) | +5.8 | 233.5 | 0.369 | REJECTED-DATA |
| 2026-11-14 | [DAL@CLE](https://www.nba.com/games?date=2026-11-14) | -1.6 | 227.6 | 0.536 | REJECTED-DATA |
| 2026-11-14 | [DET@MIA](https://www.nba.com/games?date=2026-11-14) | +9.1 | 225.3 | 0.301 | REJECTED-DATA |
| 2026-11-14 | [BKN@MEM](https://www.nba.com/games?date=2026-11-14) | -9.3 | 225.2 | 0.704 | REJECTED-DATA |
| 2026-11-14 | [CHI@MIN](https://www.nba.com/games?date=2026-11-14) | -27.9 | 233.4 | 0.945 | REJECTED-DATA |
| 2026-11-15 | [IND@PHI](https://www.nba.com/games?date=2026-11-15) | -5.3 | 220.5 | 0.620 | LEAN-ONLY |
| 2026-11-15 | [LAL@PHX](https://www.nba.com/games?date=2026-11-15) | +7.1 | 236.8 | 0.341 | LEAN-ONLY |
| 2026-11-15 | [CHA@LAC](https://www.nba.com/games?date=2026-11-15) | -7.0 | 214.5 | 0.657 | LEAN-ONLY |
| 2026-11-15 | [SAS@UTA](https://www.nba.com/games?date=2026-11-15) | +15.9 | 221.6 | 0.180 | PROVISIONAL |
| 2026-11-15 | [DAL@BOS](https://www.nba.com/games?date=2026-11-15) | -13.3 | 219.0 | 0.777 | PROVISIONAL |
| 2026-11-15 | [NYK@TOR](https://www.nba.com/games?date=2026-11-15) | +1.4 | 220.4 | 0.468 | LEAN-ONLY |
| 2026-11-15 | [HOU@WAS](https://www.nba.com/games?date=2026-11-15) | +9.4 | 221.8 | 0.295 | PROVISIONAL |
| 2026-11-15 | [ATL@MIL](https://www.nba.com/games?date=2026-11-15) | +11.3 | 231.8 | 0.258 | PROVISIONAL |
| 2026-11-15 | [OKC@SAC](https://www.nba.com/games?date=2026-11-15) | +10.6 | 222.3 | 0.271 | PROVISIONAL |
| 2026-11-16 | [ORL@BOS](https://www.nba.com/games?date=2026-11-16) | -13.7 | 216.6 | 0.785 | PROVISIONAL |
| 2026-11-16 | [CHI@CLE](https://www.nba.com/games?date=2026-11-16) | -16.3 | 238.7 | 0.826 | PROVISIONAL |
| 2026-11-16 | [MEM@WAS](https://www.nba.com/games?date=2026-11-16) | +8.7 | 224.3 | 0.308 | PROVISIONAL |
| 2026-11-16 | [PHI@BKN](https://www.nba.com/games?date=2026-11-16) | +0.9 | 219.6 | 0.479 | LEAN-ONLY |
| 2026-11-16 | [HOU@MIA](https://www.nba.com/games?date=2026-11-16) | +6.7 | 228.8 | 0.350 | LEAN-ONLY |
| 2026-11-16 | [POR@MIN](https://www.nba.com/games?date=2026-11-16) | -7.8 | 227.3 | 0.673 | LEAN-ONLY |
| 2026-11-16 | [GSW@NOP](https://www.nba.com/games?date=2026-11-16) | +9.5 | 234.8 | 0.293 | PROVISIONAL |
| 2026-11-16 | [PHX@DEN](https://www.nba.com/games?date=2026-11-16) | -8.0 | 229.7 | 0.678 | LEAN-ONLY |

## What to do next, in order

- **S-01** — Add a fetch step for the player per-game tables and finish the minutes leaderboard, then re-run the availability layer. *(cost: Ten to fifteen page fetches, no new infrastructure.)*
- **S-02** — Promote the desk's capture pattern into a scheduled job: read the slate page, the injury PDF and the date-filtered team windows; write dated JSON; refuse to overwrite a file whose stamp is newer. *(cost: One workflow plus a writer that no-ops on stale reads.)*
- **S-03** — Keep the gates unweighted and unscored. Build B's LBS blends five components into one number out of 100; a pass/fail ledger with a blank column is harder to game and easier to argue with. *(cost: Nothing — a policy choice.)*
- **S-04** — Rebuild both builds' ratings on DateFrom/DateTo windows rather than season-to-date files, and delete the contaminated 14-game backtest rather than keeping a labelled version of it. *(cost: One careful afternoon; every downstream number moves slightly.)*
- **S-05** — Put the blank list on the landing page instead of a subpage: which numbers do not exist, and what would produce them. *(cost: Copy work.)*
- **S-06** — Before any parlay work, decide the correlation floor: an r whose Fisher interval crosses zero is not a correlation, and a Fréchet band that spans 0.0–0.4 is not a price. *(cost: A written threshold; the desk proposes |r| with a 95% interval that excludes 0 at n≥30 games.)*
- **S-07** — Register the desk pages in the checkers (PAGES in check_site.py, NAV in build_edge_site.py) rather than leaving them as loose HTML. *(cost: Two list edits.)*
- **S-08** — Capture the arena with each slate row. *(cost: One extra column on a fetch already being made.)*

## Files

```
data/live/            6 official captures + the register (capture_meta.json)
integration/*.py      model, props, settle, gates, picks, review, site, leaderboard, common
integration/out/      lines, props, settlement, gates, picks, crosscheck, review,
                      leaderboard, transform_test
desk*.html            5 published pages, generated by integration/site.py
REPO_REVIEW.md        the line-by-line repo read, generated by integration/review.py
```

Reproduce with:

```
python3 integration/model.py && python3 integration/props.py && python3 integration/settle.py
python3 integration/gates.py && python3 integration/picks.py && python3 integration/transform.py
python3 integration/crosscheck.py && python3 integration/review.py
python3 integration/leaderboard.py && python3 integration/site.py && python3 integration/report.py
```
