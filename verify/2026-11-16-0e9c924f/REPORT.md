# Line-by-line verification — session `arena/0e9c924f-nba1` (COORDINATION §50, N03)

Read first-hand with the page-fetch channel on **2026-11-16 between 14:15Z and 15:05Z**.
Nothing on this page is copied from another session's claim; every value below was read from
the linked official URL in this session or is explicitly marked otherwise.

## 1. The nine 2026-11-15 finals — `finals_2026-11-15.json`

| Game | Official final | Quarters (away / home) | Sum | Source |
|---|---|---|---|---|
| IND @ PHI | 124 – 131 | 33,30,30,31 / 33,31,30,37 | ✅ | [games?date=2026-11-15](https://www.nba.com/games?date=2026-11-15) |
| LAL @ PHX | 131 – 123 | 33,28,40,30 / 26,35,32,30 | ✅ | same listing |
| CHA @ LAC | 105 – 113 | 26,27,26,26 / 36,27,22,28 | ✅ | same listing |
| SAS @ UTA | 110 – 102 | 34,21,31,24 / 30,24,27,21 | ✅ | same listing |
| NYK @ TOR (OT) | 112 – 108 | 34,25,28,15,10 / 30,24,26,22,6 | ✅ (4Q 102–102, OT 10–6) | same listing |
| DAL @ BOS | 94 – 131 | 27,20,25,22 / 37,32,32,30 | ✅ | same listing |
| HOU @ WAS | 147 – 119 | 36,37,46,28 / 31,23,34,31 | ✅ | [box-score](https://www.nba.com/game/hou-vs-was-0022600242/box-score) (second pass) |
| ATL @ MIL | 113 – 106 | 18,37,32,26 / 37,16,27,26 | ✅ | [box-score](https://www.nba.com/game/atl-vs-mil-0022600243/box-score) (second pass) |
| OKC @ SAC | 125 – 103 | 32,30,32,31 / 24,26,30,23 | ✅ | [box-score](https://www.nba.com/game/okc-vs-sac-0022600244/box-score) (second pass) |

9/9 rows: official page printed Final **and** the quarter sums equal the printed final
(the settlement's own `verify_final()` also passes 9/9). The three late rows were completed in
this session; the settlement was written from exactly this file at 2026-11-16T14:34Z.

## 2. Rolling-window schedule — `schedule_2026-11-16-18.json`

All 25 games of the 11/16–11/18 window read from the three official day pages
(`games?date=2026-11-16`, `…-11-17`, `…-11-18`), including tips and the records printed on
each card. Comparison against the published roll
(`data/derived/horizon_lines_v2.json`, generated 02:40Z):

- **matchups: 25/25 exact** — no site row is off the official slate, no official game is
  missing from the site;
- **tip times: 25/25 exact** — including **GSW @ NOP 8:00 PM ET**, which re-confirms F92's
  official value, and BOS @ DEN 9:30 PM ET;
- two observations recorded verbatim rather than resolved: `POR@MIN` appears on both 11/16
  and 11/17 official pages with distinct game ids, and some cards print pre-late-final records
  while others print post (no reconciliation attempted).

F92 stays open: the flag's job is to fix the *published* tip value, and the affected
pre-registration rows are frozen, so this session did not silently patch them.

## 3. Injury-report currency — `injury_index_2026-11-16.json`

Official index read at 14:45Z: **25 editions for 2026-11-16 (12:00AM–9:30AM ET)** already
published; the repository's newest edition was
`Injury-Report_2026-11-15_09_30PM.pdf`. Root cause found in this session:
`engine/fetch_official.py:parse_injury_index` required a literal `PM` suffix, so **every AM
edition was invisible to the scheduled refresh** — the 12:17Z run's "no new capture payloads"
is explained by that one regex. Fixed on this branch (both suffixes parsed; unit-checked
in-session); the banner's revision/retrieval stamps (R18) were already correct *for the
edition they display*. The next scheduled fetch (15:15Z / 22:15Z) captures today's editions
once this branch lands.

## 4. Settlement and ledger (N04 — its own section)

- `data/official/results_2026-11-15.json` → 9/9 FINAL, `verify_final` PASS;
- `data/settlement/settlement_2026-11-15.json` → record **5-4-0**, singles +0.6u,
  parlays 0/3 −3.3u, 2 SGP candidates honestly left unsettled (they need official box-score
  player-appearance checks the script does not have), total **−2.7u** paper at −110;
- ledger entries 6+7 appended, head
  `45aad9f894f6b695cf8311f0ecf810885a91beebe16f353710685d6b6f1088a8`, `verify_ledger` OK;
- an idempotency guard was added to `settle_slate.py` so the scheduled run cannot duplicate
  the settlement or break entry 7's digest (the still-open structural piece is **F126 (F115 at authoring)**).

## 5. Fixes and findings this session published

- `engine/fetch_official.py` — AM/PM injury-index regex (measured before/after above);
- `scripts/settle_slate.py` — idempotent skip when no new date is settleable;
- `scripts/build_pages_801ba27f.py` — `build_settlement` patched to the real settlement schema
  (it referenced keys no settlement file ever had);
- new flags **F124 (F113 at authoring)** (results-feed builder inputs absent from the repo — feed not
  reproducible here; poss/rtg/pace left null on re-cut rows rather than invented),
  **F125 (F114 at authoring)** (main re-squashed to a single root commit 047103e at 11:51:15Z; PRs #130/#136 had
  no merge base, content carried file-by-file with credit), **F115** (future re-settlements
  overwrite the record and will break `verify_ledger`'s digest of entry 7 — guard in place,
  structural fix open);
- executive text updated from "11/15 cannot be settled" to the settled state, with both
  readings preserved; open-flag tile now 111.

## 6. What was deliberately NOT done

- No frozen pre-registration row, pick archive, or ledger entry was rewritten;
- no official value was written into a data file without a URL read in this session;
- the two SGP candidates were left unsettled rather than graded on inference;
- stale records elsewhere on the site (capture predating the three late finals) were
  recorded as observations, not silently patched.
