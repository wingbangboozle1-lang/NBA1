# E03 — 2026-11-15 settlement, fully verified (2026-11-16)

Re-read the three remaining official game pages with fetch_page (live render, nba.com):

| Game | Official page | Linescores (Q1/Q2/Q3/Q4) | Sum check | Final |
| --- | --- | --- | --- | --- |
| HOU@WAS 0022600242 | https://www.nba.com/game/hou-vs-was-0022600242 | HOU 36/37/46/28, WAS 31/23/34/31 | 147 ✓ / 119 ✓ | Final (Capital One Arena, 7:00 PM ET, att. 18,041) |
| ATL@MIL 0022600243 | https://www.nba.com/game/atl-vs-mil-0022600243 | ATL 18/37/32/26, MIL 37/16/27/26 | 113 ✓ / 106 ✓ | Final (Fiserv Forum, 8:00 PM ET, att. 11,474) |
| OKC@SAC 0022600244 | https://www.nba.com/game/okc-vs-sac-0022600244 | OKC 32/30/32/31, SAC 24/26/30/23 | 125 ✓ / 103 ✓ | Final (Golden 1 Center, 9:00 PM ET, att. 13,021) |

`data/official/results_2026-11-15.json` updated: all 9 rows FINAL, quarter sums
asserted per row (`quarters_sum_check`), prior NOT-FINAL states preserved in
`prior_status` / `state_at_retrieval`, previous feed_update kept under
`feed_update.previous_update`.

Settlement (`python3 scripts/settle_slate.py --slate 2026-11-15`, 2026-11-16T14:46Z):
- pre-tip archive verified against ledger entry 4 (sha 82974ede…)
- 9 singles: 5-4-0 → +0.6 units at −110 (wins: PHI −3.1, LAC −6.2, BOS −11.5, HOU −14.3, OKC −15.6; losses: LAL −12.1 (margin 8), SAS −24.1 (margin 8), NYK −4.1 (margin 4), ATL −16.3 (margin 7))
- 3 parlays: 0-3 → −3.3 units (every parlay's SAS@UTA leg lost: SAS won by only 8 vs −24.1)
- 2 SGPs: UNSETTLED — player appearance requires the official box score (flagged, not blocking)
- total settled: −2.7 units; validation_note: MODEL OUTPUT — UNVALIDATED, unfunded, zero-stake paper
- wrote `data/settlement/settlement_2026-11-15.json`; ledger entries 6+7 appended; head `4d649ab153cc6af41b305135472d00e86313660970b7bd693f08790712fb424f`
- `scripts/verify_ledger.py` → "ledger chain OK" (exit 0)

Unsettled dates remaining: 2026-11-16/17/18 (future games — correct).
