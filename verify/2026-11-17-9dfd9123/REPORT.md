# §62 verification record — 11/16 official finals and sealed-ledger settlement

Session: `arena/9dfd9123-nba1`. Scope: data/official/results_2026-11-16.json, data/settlement/settlement_2026-11-16.json, data/ledger/ledger.json (append-only), this folder, and evidence rows R02/R03/R19.

## 1. Official finals (all eight games FINAL)

Each final was read twice from official sources: the LINESCORES block on the nba.com game page, and the SCORE BY PERIOD row of the official gamebook PDF on statsdmz.nba.com. A third read was the final score on https://www.nba.com/games?date=2026-11-16. Every quarter line sums to the printed final. All eight gamebook quarter lines agree with the game pages; for HOU@MIA the gamebook chunk read printed only the HEAT line, so the HOU line rests on the game page and its total matches the gamebook box total.

| Game | Final | Quarters (away / home) | Game page | Gamebook |
| --- | --- | --- | --- | --- |
| 0022600245 ORL@BOS | 115–105 | 20-30-25-40 / 17-24-36-28 | https://www.nba.com/game/orl-vs-bos-0022600245 | https://statsdmz.nba.com/pdfs/20261116/20261116_ORLBOS_book.pdf |
| 0022600247 MEM@WAS | 136–120 | 33-26-42-35 / 35-34-18-33 | https://www.nba.com/game/mem-vs-was-0022600247 | https://statsdmz.nba.com/pdfs/20261116/20261116_MEMWAS_book.pdf |
| 0022600246 CHI@CLE | 115–126 | 31-17-31-36 / 25-32-31-38 | https://www.nba.com/game/chi-vs-cle-0022600246 | https://statsdmz.nba.com/pdfs/20261116/20261116_CHICLE_book.pdf |
| 0022600249 HOU@MIA | 110–128 | 15-31-35-29 / 29-33-39-27 | https://www.nba.com/game/hou-vs-mia-0022600249 | https://statsdmz.nba.com/pdfs/20261116/20261116_HOUMIA_book.pdf |
| 0022600248 PHI@BKN | 135–123 | 33-45-27-30 / 26-33-36-28 | https://www.nba.com/game/phi-vs-bkn-0022600248 | https://statsdmz.nba.com/pdfs/20261116/20261116_PHIBKN_book.pdf |
| 0022600251 GSW@NOP | 94–115 | 11-25-29-29 / 35-26-32-22 | https://www.nba.com/game/gsw-vs-nop-0022600251 | https://statsdmz.nba.com/pdfs/20261116/20261116_GSWNOP_book.pdf |
| 0022600250 POR@MIN | 98–106 | 26-25-22-25 / 26-33-28-19 | https://www.nba.com/game/por-vs-min-0022600250 | https://statsdmz.nba.com/pdfs/20261116/20261116_PORMIN_book.pdf |
| 0022600252 PHX@DEN | 117–105 | 20-36-34-27 / 24-29-29-23 | https://www.nba.com/game/phx-vs-den-0022600252 | https://statsdmz.nba.com/pdfs/20261116/20261116_PHXDEN_book.pdf |

Not captured and therefore blank and flagged in the file: tip times, AP recap headlines (not read this session), and the ORL@BOS officials line.

## 2. Settlement

- `settle_slate.py --dry-run` reported 2026-11-16 ready to settle, with all eight games verified FINAL. It made no writes.
- The real run wrote data/settlement/settlement_2026-11-16.json and appended ledger entries 8 and 9. The git diff of ledger.json is append-only apart from the `head` pointer, which the script updates by design.
- The pre-tip archive matched ledger entry 5 (sha256 9b43d77b…).
- Hand check of all eight singles against the official margins: BOS −14.5 lost by 10 (LOSS); CLE −13.2 won by 11 (LOSS); MEM −14.2 won by 16 (WIN); PHI −8.1 won by 12 (WIN); HOU −10.8 lost by 18 (LOSS); MIN −4.3 won by 8 (WIN); GSW −13.2 lost by 21 (LOSS); DEN −5.0 lost by 12 (LOSS). Result: 3-5, −2.5u on singles. Parlays 0-3 (−3.3u). SGP not settled. Total −5.8u.
- Units are paper: every ticket is MODEL OUTPUT, unvalidated, zero stake. No strategy is funded.

## 3. Checks

- `scripts/verify_all.py`: VERIFY OK, FAILURES 0 (see checks.json).
- `scripts/verify_ledger.py`: ledger chain OK.

## 4. Flags (not blocking)

- F-62-01: data/official/results_feed_2026_27.json still shows the eight 11/16 games as scheduled rows (status 1, 0-0). It is the model-corpus feed. Changing it moves published model numbers, so it is left for the integration seat.
- F-62-02: the settlement rules text in settlement_2026-11-16.json names data/official/results_2026-11-14.json as the finals source. This copies the frozen rules verbatim, as 11/15 did. The `official_finals_files` field points to the correct 11/16 file.
- F-62-03: the tip times, AP headlines, and ORL@BOS officials on the 11/16 results file are blank because they were not captured this session.
- F-62-04: probe-official workflow runs were cancelled after about 25 minutes (noted in §61; not investigated here).
