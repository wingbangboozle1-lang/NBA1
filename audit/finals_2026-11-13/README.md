# 2026-11-13 official finals — verification record (session `arena/cfb25ff0-nba1`)

**What this closes.** The committed finals snapshot `data/raw/games_completed.json` ends at 2026-11-12.
The nine games of 2026-11-13 (game IDs `0022600034`–`0022600042`) were recorded as *not final* by the
02:05Z refresh capture (`data/raw/_capture_results_2026-11-13.json`). They are Final on the official
schedule now. This record gives each game a row-level verified result, with sources, so the integration
session can promote them. Nothing in the shared snapshot, the settlement file or the site was edited.

**Outputs**

| File | What it is |
| --- | --- |
| `data/verified/finals_2026-11-13.json` | One row per game, sources on every row (promotion-ready) |
| `audit/finals_2026-11-13/capture.json` | Every value as read from the official pages, with the URL it came from |
| `audit/finals_2026-11-13/check.py` | Re-runs C1–C5 (schedule vs game page, arithmetic, status, URL slug, not-yet-committed). 41 checks, 0 failed |
| `audit/finals_2026-11-13/report.json` | Output of `check.py` |
| `audit/finals_2026-11-13/records_check.py` + `records.json` | Post-11/13 records for the 18 teams that played (see §3) |

## 1. Results and sources

Primary source for every row: the nba.com schedule (<https://www.nba.com/schedule>, Week 4, Fri Nov 13).
Second source: the nba.com game page linked from each card. "Two pages agree" means the schedule card
score equals the game-page LINESCORES final.

| Game ID | Away @ Home | Final (away–home) | Quarters (away / home) | Verification | Sources (open to check) |
| --- | --- | --- | --- | --- | --- |
| 0022600034 | NYK @ IND | 104–106 | 27-22-35-20 / 26-32-27-21 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/nyk-vs-ind-0022600034) |
| 0022600035 | MIL @ ORL | 99–107 | 15-22-35-27 / 23-29-32-23 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/mil-vs-orl-0022600035) |
| 0022600036 | CLE @ MIA | 121–133 | 27-30-34-30 / 29-25-38-41 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/cle-vs-mia-0022600036) |
| 0022600037 | ATL @ CHI | 117–125 (Final/OT) | not returned by the fetch tool | **single official source**; OT count not confirmed | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/atl-vs-chi-0022600037) |
| 0022600038 | MEM @ NOP | 142–111 | 35-35-35-37 / 28-30-28-25 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/mem-vs-nop-0022600038) |
| 0022600039 | UTA @ HOU | 118–125 | 27-26-36-29 / 27-36-29-33 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/uta-vs-hou-0022600039) |
| 0022600040 | GSW @ SAS | 85–123 | 14-19-27-25 / 38-25-34-26 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/gsw-vs-sas-0022600040) |
| 0022600041 | POR @ SAC | 120–107 | not returned by the fetch tool | **single official source** | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/por-vs-sac-0022600041) |
| 0022600042 | OKC @ LAC | 112–113 | 27-17-40-28 / 33-24-25-31 | two official pages agree | [schedule](https://www.nba.com/schedule) · [game](https://www.nba.com/game/okc-vs-lac-0022600042) |

Every quarter-by-quarter total in the table re-adds to the final score (check C2). The schedule card
agrees with the game page wherever both were read (check C1).

**Method limits (stated, not hidden).** The fetch tool returned the page header only for ATL–CHI and
POR–SAC. Their scores come from the schedule card alone, so those two rows are marked single-source.
For ATL–CHI the schedule label reads `Final/OT`; the number of overtime periods is not printed in
anything read here, so `ot` is left null.

## 2. Comparison with the committed data

* The committed snapshot `data/raw/games_completed.json` has none of these nine games (check C5). They
  are promotion candidates, not corrections. No committed value was changed.
* No published pick is on a 2026-11-13 game. The picks in `integration/out/picks.json`,
  `data/derived/horizon_picks.json` and `data/derived/picks_d.json` are dated 11/14–11/17 only (checked
  by date field on every singles, parlay, prop and horizon-game row). Settlement therefore does not change
  any published pick.
* `integration/out/settlement.json` lists the nine games under `cannot_settle` with state
  `IN PROGRESS`/`PREGAME`/`NOT TIPPED`, and says "re-fetch … after the games end and re-run settle.py".
  This record is the re-fetch; the settlement run itself belongs to the integration session.

## 3. Consequence for the 11/14–11/17 horizon (18 teams)

Every team that played on 11/13 is on a horizon card with a pre-11/13 record. The repo already
discloses this ("stale-record teams in horizon: 18", `scripts/verify_schedule_c.py`). The
post-11/13 record is pre-11/13 record plus the verified result:

| Team | Pre-11/13 | Result | Post-11/13 (derived) | Official card read | Agrees |
| --- | --- | --- | --- | --- | --- |
| NYK | 6-5 | L | 6-6 | 6-6 ([schedule](https://www.nba.com/schedule)) | yes |
| IND | 4-8 | W | 5-8 | 5-8 ([schedule](https://www.nba.com/schedule)) | yes |
| MIL | 1-11 | L | 1-12 | not on the cards read; the official game-page recap says "Milwaukee (1-12)" ([game](https://www.nba.com/game/mil-vs-orl-0022600035)) | consistent |
| ORL | 4-7 | W | 5-7 | not read | derived only |
| CLE | 6-6 | L | 6-7 | 6-7 ([schedule](https://www.nba.com/schedule)) | yes |
| MIA | 5-6 | W | 6-6 | 6-6 ([schedule](https://www.nba.com/schedule)) | yes |
| ATL | 7-5 | L | 7-6 | not read | derived only |
| CHI | 1-9 | W | 2-9 | 2-9 ([schedule](https://www.nba.com/schedule)) | yes |
| MEM | 7-4 | W | 8-4 | 8-4 ([schedule](https://www.nba.com/schedule)) | yes |
| NOP | 4-8 | L | 4-9 | 4-9 ([schedule](https://www.nba.com/schedule)) | yes |
| UTA | 1-11 | L | 1-12 | 1-12 ([schedule](https://www.nba.com/schedule)) | yes |
| HOU | 9-3 | W | 10-3 | 10-3 ([schedule](https://www.nba.com/schedule)) | yes |
| GSW | 8-4 | L | 8-5 | not read | derived only |
| SAS | 10-2 | W | 11-2 | 11-2 ([schedule](https://www.nba.com/schedule)) | yes |
| POR | 8-3 | W | 9-3 | not read | derived only |
| SAC | 1-10 | L | 1-11 | not read | derived only |
| OKC | 8-4 | L | 8-5 | not read | derived only |
| LAC | 2-8 | W | 3-8 | 3-8 ([schedule](https://www.nba.com/schedule)) | yes |

11 of 18 derived records agree with an official card; 0 disagree. The seven "derived only" records have
not been checked against an official card in this session. They should be confirmed before the
horizon page is refreshed.

## 4. Irregularities found (for the Flagged for Review register)

1. **Wrong source link on all nine 11/13 settlement rows.** Every `cannot_settle` row for 2026-11-13 in
   `integration/out/settlement.json` has `source_url` `https://www.nba.com/game/cha-vs-phx-0022600230/box-score`,
   which is the Charlotte–Phoenix game (ID `0022600230`, 11/12), not the game in the row. Checked: the URL
   does not contain the row's `game_id` in any of the nine rows. Owner: integration seat.
2. **Finals not yet committed.** `data/raw/games_completed.json` stops at 2026-11-12; the 9 games of
   11/13 are Final on the official schedule. Flag F-C01 stays open until promotion. Promotion candidates
   are in `data/verified/finals_2026-11-13.json`.
3. **Two rows single-source.** ATL–CHI (OT count not confirmed) and POR–SAC (no game-page linescore
   returned by the fetch tool). Marked in the data.
4. **Seven horizon team records are derived, not yet read from an official card** (ORL, ATL, GSW,
   POR, SAC, OKC, and MIL on the card view). See §3.
5. **Official-page text inconsistency (minor).** The CLE–MIA game-page recap (nba.com) says the game
   was played "Tuesday night", but the page header dates the game Friday, November 13, 2026. The score
   and linescore on the same page agree with the schedule card, so no score value is affected. The
   inconsistency is in the AP recap text and is logged, not corrected.
6. **Incomplete page for two games.** The ATL–CHI and POR–SAC game pages returned only the header to the
   fetch tool. Not an irregularity in NBA data, but it limits the second-source check (item 3).

## 5. Limits

* These values were read through the `fetch_page` tool from public nba.com pages on 2026-11-14. This
  is a point-in-time read: the schedule and game pages can change, so a later re-read should be logged
  as its own capture.
* Quarter-level values appear only where the game page returned its LINESCORES table.
* The sandbox allowlist blocks direct HTTP from the shell to nba.com, so the captures were made with
  the page-fetch tool. The raw page text is not stored here; `capture.json` keeps the values and the
  URLs, and each URL is public.
