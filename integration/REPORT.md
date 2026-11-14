# Integration desk — report for 2026-11-14

Capture: 2026-11-14T10:45Z · session `arena/2edb85af-nba1` · 22 games priced, 60 graded out of sample.

## Executive summary

1. **The margin carries information; the total does not.** Mean absolute error on the final margin is **12.913** points against **14.886** for predicting a single constant across the same 60 official finals — a gain of 1.973 points. On totals the model scores **14.636** where a constant scores **14.658** — a lead of 0.022 points, so V3b now PASSES — by 14.636 vs 14.658, i.e. within any sensible reading of the noise. The pass is published exactly as measured, not rounded into a claim.
2. **No component earns its keep at this sample size.** Removing home court moves the margin error by +0.252, removing the back-to-back penalty by +0.011, and removing shrinkage by +0.629 points — all inside a ±2.5 interval. They stay in the model because the theory supports them, and they are flagged because the data cannot yet confirm them.
3. **What withholds picks is the injury report, not the model.** Of 22 priced games: 0 pass every rule, 5 are refused because one side had filed and the other had not, 8 are provisional until their date's report exists, and 9 sit inside the model's own noise. Every rejection is printed with its reason rather than dropped.
4. **Rotation impact could not be sized.** Of 26 official player rows in the newest edition (Injury Report: 11/14/26 05:00 AM), 1 have verified season minutes anywhere in this repository — gate V8 stays BLANK with that count. Vacated minutes reduce the named player's team and are *not* re-spread across his teammates — re-spreading them would have meant inventing the numbers that make a rotation model look good.
5. **Prop dispersion is measured now, and still unusable.** 12 official game-log rows across 3 players give a real σ where the repo previously used a constant; every prop and parlay row carries `usable_for_staking: false`, and within-player correlations have intervals that cross zero.
6. **Nothing here is a bet.** No sportsbook price is reachable from this environment, so break-even, hold, ROI and CLV are blank everywhere: 3 gates are BLANK for that reason and 3 FAIL. The leaderboard's top row is not validated and no reward is payable to any row of it.

## Gate ledger

| Gate | Requirement | Status |
| --- | --- | --- |
| V1 | Out-of-sample, no look-ahead | **PASS** — fit ends 2026-11-05, first graded game 2026-11-06 |
| V2 | Sample floor | **FAIL** — 60 |
| V3 | Beat a constant on the margin | **PASS** — 12.913 vs 14.886 |
| V3b | Beat a constant on the total | **PASS** — 14.636 vs 14.658 |
| V4 | Calibration of the win probability | **PASS** — 0.1975 |
| V5 | Stability across halves | **PASS** — 31/29 games, MAE 13.141 vs 12.669 |
| V6 | Uncertainty published | **PASS** — MAE margin 95% CI [10.5173, 15.4998] |
| V7 | Provenance of every row | **PASS** — enforced by common.assert_official at load time |
| V8 | Rotation reassignment | **BLANK** — None |
| V9 | Availability completeness | **FAIL** — 0 of 14 games with an edition have both sides filed; 5 have exactly one side filed; 9 have neither |
| V10 | Market comparison / closing line value | **BLANK** — None |
| V11 | Pricing of props and parlays | **FAIL** — 3 of 465 players have logs captured |
| V12 | Reproducibility | **PASS** — deterministic: fixed-seed LCG bootstrap, no RNG, no wall-clock in any figure |
| V13 | Out-of-sample test of the absence adjustment | **BLANK** — None |

## The slate, in one table

| Date | Matchup | Spread (home) | Total | P(home) | Tier |
| --- | --- | --- | --- | --- | --- |
| 2026-11-14 | [DEN@NOP](https://www.nba.com/games?date=2026-11-14) | +7.3 | 234.2 | 0.338 | REJECTED-DATA |
| 2026-11-14 | [DAL@CLE](https://www.nba.com/games?date=2026-11-14) | -0.6 | 229.2 | 0.513 | REJECTED-DATA |
| 2026-11-14 | [DET@MIA](https://www.nba.com/games?date=2026-11-14) | +7.9 | 226.8 | 0.325 | REJECTED-DATA |
| 2026-11-14 | [BKN@MEM](https://www.nba.com/games?date=2026-11-14) | -11.0 | 226.5 | 0.737 | REJECTED-DATA |
| 2026-11-14 | [CHI@MIN](https://www.nba.com/games?date=2026-11-14) | -26.2 | 231.6 | 0.934 | REJECTED-DATA |
| 2026-11-15 | [IND@PHI](https://www.nba.com/games?date=2026-11-15) | -5.0 | 219.4 | 0.613 | LEAN-ONLY |
| 2026-11-15 | [LAL@PHX](https://www.nba.com/games?date=2026-11-15) | +7.1 | 236.7 | 0.342 | LEAN-ONLY |
| 2026-11-15 | [CHA@LAC](https://www.nba.com/games?date=2026-11-15) | -7.5 | 214.6 | 0.666 | LEAN-ONLY |
| 2026-11-15 | [SAS@UTA](https://www.nba.com/games?date=2026-11-15) | +17.5 | 221.8 | 0.158 | PROVISIONAL |
| 2026-11-15 | [DAL@BOS](https://www.nba.com/games?date=2026-11-15) | -13.2 | 219.0 | 0.776 | PROVISIONAL |
| 2026-11-15 | [NYK@TOR](https://www.nba.com/games?date=2026-11-15) | +0.8 | 219.7 | 0.481 | LEAN-ONLY |
| 2026-11-15 | [HOU@WAS](https://www.nba.com/games?date=2026-11-15) | +9.3 | 223.2 | 0.295 | PROVISIONAL |
| 2026-11-15 | [ATL@MIL](https://www.nba.com/games?date=2026-11-15) | +10.6 | 229.5 | 0.271 | PROVISIONAL |
| 2026-11-15 | [OKC@SAC](https://www.nba.com/games?date=2026-11-15) | +10.4 | 222.7 | 0.274 | PROVISIONAL |
| 2026-11-16 | [ORL@BOS](https://www.nba.com/games?date=2026-11-16) | -12.7 | 215.6 | 0.767 | PROVISIONAL |
| 2026-11-16 | [CHI@CLE](https://www.nba.com/games?date=2026-11-16) | -13.7 | 238.6 | 0.785 | PROVISIONAL |
| 2026-11-16 | [MEM@WAS](https://www.nba.com/games?date=2026-11-16) | +10.4 | 225.6 | 0.275 | PROVISIONAL |
| 2026-11-16 | [PHI@BKN](https://www.nba.com/games?date=2026-11-16) | +0.9 | 219.6 | 0.480 | LEAN-ONLY |
| 2026-11-16 | [HOU@MIA](https://www.nba.com/games?date=2026-11-16) | +5.6 | 231.7 | 0.374 | LEAN-ONLY |
| 2026-11-16 | [POR@MIN](https://www.nba.com/games?date=2026-11-16) | -7.2 | 227.2 | 0.660 | LEAN-ONLY |
| 2026-11-16 | [GSW@NOP](https://www.nba.com/games?date=2026-11-16) | +8.2 | 234.4 | 0.318 | LEAN-ONLY |
| 2026-11-16 | [PHX@DEN](https://www.nba.com/games?date=2026-11-16) | -8.0 | 229.6 | 0.677 | LEAN-ONLY |

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
