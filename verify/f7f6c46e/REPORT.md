# Independent verification pass — session `arena/f7f6c46e-nba1` (F03, 2026-11-14)

**Read window:** 2026-11-14 19:15–19:40 UTC (≈ 2:15–2:40 PM ET), i.e. after every prior session on
this board went idle. **Method:** every value below was read in this session from the official
URL listed with it; nothing is inferred. Values that could not be confirmed are left blank and
flagged. Machine-readable artifacts live beside this file:

| Artifact | Contents |
| --- | --- |
| `official_horizon_2026-11-14_17.json` | 27 horizon rows transcribed from the four official day pages, each with its source URL |
| `horizon_compare.json` | row-by-row diff of that capture against `site/data/lines.json` (id, matchup, date, tip, records) |
| `injury_2026-11-14_0145PM.json` | verbatim capture of the newest official injury edition, 69 rows, `printed_fields_complete=false` wherever the PDF prints no team |
| `injury_compare.json` | diff of the 01:45 PM ET edition against the site's published 04:15 AM ET rows |

---

## 1. Horizon schedule — 27/27 rows verified, 0 mismatches

Sources (read 19:20 UTC): [11/14](https://www.nba.com/games?date=2026-11-14) ·
[11/15](https://www.nba.com/games?date=2026-11-15) ·
[11/16](https://www.nba.com/games?date=2026-11-16) ·
[11/17](https://www.nba.com/games?date=2026-11-17).

| Check | Result |
| --- | --- |
| Game count per day | 5 + 9 + 8 + 5 = **27** — matches the site's horizon tile and `site/data/lines.json` (27 rows); the official calendar block prints the same per-day counts |
| `game_id` set | **27/27 identical**, no id only-official, no id only-site |
| `matchup` + `date` | **27/27 match** |
| Tip time (`time_et` vs printed `7:00 PM ET` / `7:00 pm ET`) | **27/27 match** after format normalisation (the two official formats are documented as F50) |
| Team records printed on the day pages (11/14, 11/15, 11/17 rows) | **all match** `away_rec`/`home_rec` on the site — 0 mismatches. The 11/16 pages print `-` for both records, so those cells were **not compared and not inferred** (recorded `not-printed-on-official` in the artifact) |

Per-row detail with both readings and the source URL: `horizon_compare.json`.

## 2. Injury-report edition currency — drift found, published as F47–F51

Sources: [official index](https://official.nba.com/nba-injury-report-2026-27-season/) (read 19:15 UTC)
· newest edition [01:45 PM ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_45PM.pdf)
· site's edition `S10_2026-11-14-0415AM` ([04:15 AM ET PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf)).

| Finding | Measured value |
| --- | --- |
| Editions listed for 11/14 at read time | **56**, at a 15-minute cadence, through **01:45 PM ET**; **38** of them are later than the 04:15 AM edition the site prices against |
| Filing state | at 04:15 AM: NOP, CLE, MEM, CHI, MIA = NOT YET SUBMITTED. At 01:45 PM: **NOP, CLE, CHI, MIA have filed; MEM still has not** |
| Status changes on players the site lists | **4**: Christie (DAL) Questionable→**Doubtful**; Brown Jr. (BKN) Questionable→**Probable**; Harkless (DET) Questionable→**Available**; Jones (DET) Questionable→**Available** |
| Site players that disappeared by 01:45 PM | **0** |
| New designations at 01:45 PM (11/14 slate, incl. newly-filed clubs) | 24 rows not present in the site's edition (players: NOP 5, CLE 1 + 7 continuation, CHI 6 continuation + 1, MIA 4 — full list in `injury_compare.json`) |
| Unattributed continuation rows (no team printed in the PDF) | **13** — captured with `team_printed: null`, never inferred (known class X01-F2) |
| 11/15 slate on the same edition | all 19 clubs with printed rows = NOT YET SUBMITTED, as expected pre-filing |

**Published on the Flagged for Review page as F47 (High) through F51**, with the PDF/index links
above. The Executive Summary headline and the settled-slate finding were corrected to name the
04:15 AM edition as *the edition priced against* (not "the newest"), with the 01:45 PM drift
referenced to F47. Suggestion **SG19** (archive every edition; re-price on the last pre-tip
edition) and **SG20** (promotion only through the gate suite, request R-A6 of §33) were added to
the Suggestions register; Q14 gained the observed 04:15→01:45 movement data.

## 3. What was re-verified as already correct

| Check | Result |
| --- | --- |
| 2026-11-13 finals | not re-read in this pass — three prior independent captures agree 9/9 (§20 X02–X05, §27.1, §34.1 of this board); settlement ledger arithmetic re-checked by §27.1 |
| Pick rows ↔ horizon rows | every pick row maps to a verified horizon row (27/27 id match above covers the join key) |
| Row-level source links (structural) | `scripts/verify_dashboard.py`: **1041 rows, 1023 official links, 18 explicit explained no-source marks, 0 unmarked** after this session's fixes (was 1033/1012/18/3 pre-fix — the 3 title-only URLs are now clickable context links, request R26-2 done) |
| Repository-wide audit | `scripts/verify_integration.py`: **0 errors**, 44 warnings (all published on the Flagged page), 5808/6015 data rows officially sourced |

## 4. Flags and corrections opened by this pass

| id | What | Where it landed |
| --- | --- | --- |
| F47 | Lines priced on 04:15 AM edition; 38 later editions, 4 status changes, 4 late filings measured | `data/content/flagged.json`, rendered on `site/pages/flagged.html` |
| F48 | 13 continuation rows print no team; captured unattributed | same |
| F49 | Continuation rows carry no printed date; header-date rule stated | same |
| F50 | Two official tip-time formats; normalisation rule stated (0 mismatches after normalisation) | same |
| F51 | Game-day cadence = 15 minutes; every "newest edition" label must carry its capture time | same |
| F34 (updated) | Gate now reports four counts and still checks structure, not values — current numbers inlined | same |
| F37 (updated) | Dated addendum with current whole-site counts; historical per-page counts kept | same |
| R26-1 (done) | README checker row now states the measured rule and counts | `README.md` |
| R26-2 (done) | Q14–Q16 approved context URLs render as clickable links, unverified marker retained | `scripts/build_dashboard.py` (`nomark`) |
| R26-4 (done) | Sidebar reading rule now states link-or-explicit-mark | `scripts/build_dashboard.py` |
| R-A2 | F28 already corrected on `main` by PR #66 (composition text) — verified current, no action | — |
| R-A1 | Root banner/verdict read in full: the current text states both the luck-gate pass *and* the two failed gates and "PROVISIONAL – not funded"; no stale "validated" claim found on the current tree | — |

## 5. Limits of this pass (stated, not hidden)

- NBA.com pages were read through the platform's page-fetch tool, not a browser; PDF text is the
  tool's extraction of the official file, with the known column-split behaviour on page breaks
  (which is exactly why F48/F49 exist).
- The 01:45 PM edition was the newest **listed** at 19:15 UTC; a later edition may exist by the
  time this is read — that is the point of F51.
- No odds/price source exists in the NBA-operated sphere (F3, gate GG) — nothing here is checked
  against a market price.
- Records on the 11/16 official page print `-` and were left uncompared.
- This pass verified schedule/records/edition currency and provenance structure; it did **not**
  re-derive model numbers (verified independently by §27.1 and §29.1) and did not fetch box
  scores or player stats tables.
