# I03 — Live official re-verification pass (2026-11-15, 23:45–23:58 UTC)

Session `arena/8f64e94c-nba1`, branch `arena/8f64e94c-nba1`, COORDINATION §41 task I03.
Every value below was read from an official NBA page during this pass. Nothing is
inferred; unconfirmed fields are null and flagged. Reproduce the comparison with
`python3 verify/2026-11-15-8f64e94c/compare.py` (regenerates `compare.json`).

**Method note.** The sandbox shell has no route to nba.com; the page-fetch tool does.
All live reads below were made through that tool at the stated timestamps. The shell's
restricted network is why earlier sessions recorded "no live NBA host was fetched" — that
statement is historical; this pass fetched live official pages and says exactly which.

---

## 1. What was checked, and the result

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | 2026-11-15 slate: 9 games on the official date page | **9/9 present**, game ids 0022600236–0022600244 match the published horizon | [games?date=2026-11-15](https://www.nba.com/games?date=2026-11-15) |
| 2 | Published horizon (34 games, 15–18 Nov) vs live official schedule listing | **33/34 rows agree** on date, matchup and tip; 1 disagreement (GSW@NOP tip time → **F92**) | `compare.json`, [games?date=2026-11-16](https://www.nba.com/games?date=2026-11-16) |
| 3 | Published schedule capture (`data/official/schedule_2026-11-15_to_18.json`, 34 rows) vs live listing | **33/34 agree**; the same single disagreement | `compare.json` |
| 4 | 2026-11-15 games already final at read time | **2 finals verified**: IND@PHI 124–131, LAL@PHX 131–123; both LINESCORES quarters sum to the printed final | [IND@PHI](https://www.nba.com/game/ind-vs-phi-0022600236), [LAL@PHX](https://www.nba.com/game/lal-vs-phx-0022600237) |
| 5 | Per-game result feed kept current | `data/official/results_2026-11-15.json` written: 2 FINAL rows (date, teams, final score, quarter scores, officials, attendance, gamebook PDF links) + 7 NOT FINAL stubs with observed state and null scores | same rows, one source URL each |
| 6 | Injury-report edition currency | Basis edition 11/15 06:15 AM ET confirmed on the official index; **newer 11/15 editions exist** (≥ 4:15 PM ET at read time) and are not captured → **F93** | [official injury index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| 7 | Horizon flag F-W01 (repeated matchups) | **Confirmed as printed by the official feed**: POR@MIN on 11/16 (0022600250) and 11/17 (0022600254); NYK@TOR on 11/15 (0022600241) and 11/17 (0022600253) — distinct game ids and tips, not a capture artifact | `live_schedule_2026-11-15T2352Z.json` |
| 8 | Settlement discipline | **No pick graded in this pass.** The 11/15 ledger settlement runs at game-day end after all 9 games are final (the slate's last tip is OKC@SAC 09:00 PM ET). The two verified finals are recorded in the feed now, exactly as the rule allows | `data/official/results_2026-11-15.json` `settlement_note` |

## 2. The two verified finals (row-level)

**IND 124 @ PHI 131** — [official game page](https://www.nba.com/game/ind-vs-phi-0022600236) ·
[box score](https://www.nba.com/game/ind-vs-phi-0022600236/box-score#box-score) ·
[gamebook PDF](https://statsdmz.nba.com/pdfs/20261115/20261115_INDPHI_book.pdf)

| Team | Q1 | Q2 | Q3 | Q4 | Final | Sum check |
| --- | --- | --- | --- | --- | --- | --- |
| IND | 35 | 22 | 30 | 37 | 124 | 124 ✓ |
| PHI | 29 | 29 | 39 | 34 | 131 | 131 ✓ |

Xfinity Mobile Arena, Philadelphia PA · 1:00 PM ET · attendance 21,024 · officials
Sean Corbin, Karl Lane, Matt Myers · page headline: "LeBron James moves past Jason Kidd
for 3rd in NBA's career assist list, 76ers top Pacers 131-124" (AP, 4:32 PM).

**LAL 131 @ PHX 123** — [official game page](https://www.nba.com/game/lal-vs-phx-0022600237) ·
[box score](https://www.nba.com/game/lal-vs-phx-0022600237/box-score#box-score) ·
[gamebook PDF](https://statsdmz.nba.com/pdfs/20261115/20261115_LALPHX_book.pdf)

| Team | Q1 | Q2 | Q3 | Q4 | Final | Sum check |
| --- | --- | --- | --- | --- | --- | --- |
| LAL | 33 | 31 | 40 | 27 | 131 | 131 ✓ |
| PHX | 24 | 30 | 26 | 43 | 123 | 123 ✓ |

Mortgage Matchup Center, Phoenix AZ · 4:00 PM ET · attendance 17,071 · officials
James Williams, John Butler, Sha'Rae Mitchell. The page's article slot shows the pre-game
preview (Field Level Media, 11:54 AM), not a recap; the LINESCORES and GAME INFO blocks
are the official record used, and this is stated on the row.

## 3. Irregularities (published on Flagged for Review, non-blocking)

Both flags were conceived as F78/F79 and renumbered at merge to F92/F93 (F78-F91 were published first by `arena/513516f6-nba1` in PR #108).

1. **F92 — GSW@NOP 2026-11-16 tip time disagreement.** The published capture and the
   frozen pre-tip horizon row say **09:00 PM ET** (read 2026-11-15T11:35Z..12:20Z); three
   live reads at 23:45Z–23:58Z — two scoreboard strips and a direct read of the 11/16
   date page — say **8:00 PM ET** for game id 0022600251. Either the official page moved
   the tip after the capture or the capture mis-read it. Neither reading is discarded and
   the frozen pre-tip row is **not** edited (a pick re-priced after publication cannot be
   graded); the next rolling re-cut should take the live page's value.
   Source: [games?date=2026-11-16](https://www.nba.com/games?date=2026-11-16).
2. **F93 — injury-edition capture gap.** The league published 11/15 editions in
   15-minute steps through at least 4:15 PM ET; the site's basis edition is 06:15 AM ET
   (revision 2026-11-15 06:15 AM ET, retrieved 2026-11-15T11:52Z, 101 rows). Lines are
   deliberately **not** re-priced (SG29/F72). The Injuries page banner already states the
   edition, revision time and retrieval time. Capture the remaining editions at the next
   refresh (SG30 cadence).
   Source: [official injury index](https://official.nba.com/nba-injury-report-2026-27-season/).
3. **Cross-reference irregularity (repo-internal, logged not edited).** Flag **F74**'s
   detail points at question **Q22** for "the merged-cell reading", but Q22 is the SGP
   void-convention question ("When a same-game-parlay player is inactive at tip…"). No
   open question in `data/content/questions.json` covers the PDF merged-cell reading. The
   register is append-only in this pass (ground rule 3), so the pointer is logged here for
   the content owner rather than silently rewritten.
4. **F-W01 upgraded from "printed by the capture" to "confirmed by the official feed".**
   The repeated matchups (POR@MIN 11/16 and 11/17; NYK@TOR 11/15 and 11/17) appear on the
   live official pages with distinct game ids and tips. The flag remains open (the
   scheduling reason is still unknown) but its "is this a capture artifact?" branch is
   now answered: no.

## 4. Files in this namespace

| File | What it is |
| --- | --- |
| `live_state_2026-11-15T2352Z.json` | Verbatim live observation record for all 9 games of the 11/15 slate + the injury-index read |
| `live_schedule_2026-11-15T2352Z.json` | Verbatim live schedule listing for 15–18 Nov (34 rows) with the confirming read for 0022600251 |
| `compare.py` / `compare.json` | The reproducible comparison (34 horizon rows, 34 capture rows, 2 finals) |
| `REPORT.md` / `index.html` | This report and its static twin |
| `../../data/official/results_2026-11-15.json` | The per-game result feed (2 verified finals + 7 pending stubs) |

## 5. Manual-review links (official sources only)

- [NBA games 2026-11-15](https://www.nba.com/games?date=2026-11-15) ·
  [11-16](https://www.nba.com/games?date=2026-11-16) ·
  [11-17](https://www.nba.com/games?date=2026-11-17) ·
  [11-18](https://www.nba.com/games?date=2026-11-18)
- [IND@PHI game page](https://www.nba.com/game/ind-vs-phi-0022600236) ·
  [LAL@PHX game page](https://www.nba.com/game/lal-vs-phx-0022600237)
- [Official injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) ·
  [11/15 06:15 AM ET basis PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf)
