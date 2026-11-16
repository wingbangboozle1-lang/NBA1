# First-hand official verification pass — 2026-11-16 (session `arena/d361b9a5-nba1`, task Z03)

**Retrieval window:** 2026-11-16T02:08Z..02:24Z. **Method:** the session's own page-fetch tool
against official `www.nba.com` / `ak-static.cms.nba.com` pages. The sandbox's HTTP client cannot
reach those hosts (`curl` returns HTTP 000) — a tool limitation recorded here rather than papered
over, in the same spirit as F-42-1 on the board.

**Why this pass matters:** prior sessions repeatedly recorded that the sandbox could not reach
nba.com and that captures came indirectly (CI runners or transcripts). This session confirmed
before claiming (Z01 board note) that its tools reach the official pages directly, so every value
below was read **first-hand from an official page** at a stated time.

## What was verified

| # | Artifact | Official source (fetched this session) | Result |
| --- | --- | --- | --- |
| 1 | 2026-11-15 finals (6 of 9 games) | Official game-summary pages + scoreboard sidebar | 6 finals verified; 4 with quarter linescores asserted to sum (evidence_finals_2026-11-15.json); 2 re-confirmed against the §44 record |
| 2 | 11/15 in-progress games (3) | Same pages | HOU@WAS Q4, ATL@MIL Half, OKC@SAC Q1 — live scores observed but **not** recorded as finals |
| 3 | Published horizon rows 11/16 (8) | https://www.nba.com/games?date=2026-11-16 | 7 agree; **GSW@NOP official 8:00 PM ET vs published 09:00 PM ET** (F92 re-confirmed live) |
| 4 | Published horizon rows 11/17 (5) | https://www.nba.com/games?date=2026-11-17 | 5/5 agree |
| 5 | Published horizon rows 11/18 (12) | Official 11/18 sidebar | 12/12 agree (matchup + tip) |
| 6 | Published horizon rows 11/19 (4) | Official 11/19 sidebar | 4/4 agree |
| 7 | Repeat-matchup flags (F13) | Same pages | **Confirmed live**: POR@MIN on 11/16 **and** 11/17 (distinct game IDs 0022600250/0022600254); NYK@TOR on 11/15 and 11/17 |
| 8 | Live standings (30 teams) | https://www.nba.com/standings | Model inputs (23:45Z cut) agree 20/30; **all 10 disagreements are exactly the record movement of the six verified finals** — zero contradictions; W+L==GP holds 30/30 |
| 9 | Injury-edition currency | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_15PM.pdf | Newest official edition is **09:15 PM ET**; published banner cites 06:15 PM ET (3 h gap, low practical impact — see evidence_injury_currency_2026-11-16.json) |
| 10 | Roster attributions on official pages | Game recaps + leader cards + injury editions | Kawhi Leonard→TOR, Garland→LAC, Naz Reid→CHA, Ingram→LAC, LaMelo→MIN — **multiple independent official pages agree with each other**; recorded as facts, no judgment |

## Findings requiring review (all non-blocking, published here)

| ID | Finding | Evidence |
| --- | --- | --- |
| Z03-G1 | **Results-feed promotion gap (integration bug, not a data error).** The carried §46 promoter compares captured finals against *every* independent record; `data/official/results_2026-11-15.json` (owner §44, out of scope) still carries null scores for games that were in progress at its retrieval and are final now, and its rows overwrite the raw cross file in the promoter's merge order — so the four new verified finals would fail-closed as "disagrees with independent record None-None". Nothing was appended to `data/raw/games_completed.json`; no gate loosened; no out-of-scope file edited. Request logged in §47.4. | evidence_finals_2026-11-15.json `promotion_gap_flag` |
| Z03-G2 | `site/data/teams.json` is a stale display snapshot (28/30 records differ from live, all explained by the 11/15 finals). The model inputs were re-cut 23:45Z and are correct; only the display snapshot lags. Request: next refresh owner re-cuts teams.json from a fresh official capture. | evidence_standings_2026-11-16.json |
| Z03-G3 | Injury-edition currency: official newest = 11/15 09:15 PM ET, published basis = 06:15 PM ET. Low impact (09:15 PM covers the now-final 11/15 slate; 11/16 editions not yet published at retrieval). The carried CI refresh archives bytes + diffs on its next trigger; raw bytes could not be archived through this session's tools (recorded). | evidence_injury_currency_2026-11-16.json |
| Z03-G4 | F92 (GSW@NOP 11/16 tip: official 8:00 PM ET vs published 09:00 PM ET) **re-confirmed first-hand on two official surfaces**. Out of this session's file scope to correct; remains flagged for the horizon owner. | evidence_schedule_2026-11-16.json rows_11_16 |

## What was deliberately NOT done

- No values were inferred or back-filled. Rows whose team cells were dropped by the PDF→markdown
  rendering are left unattributed and unused (evidence_injury_currency_2026-11-16.json).
- No file outside this session's claimed scope was edited: the four new verified finals live in
  **this namespace only** (`evidence_finals_2026-11-15.json`), not in the shared results feed.
- The published pages were not re-priced or rebuilt after these checks (post-cut discipline, F72).

## Source links (official, all fetched this session)

- https://www.nba.com/standings
- https://www.nba.com/games?date=2026-11-16 · 17 · 18
- https://www.nba.com/game/cha-vs-lac-0022600238 (+ /box-score path implied by page nav)
- https://www.nba.com/game/sas-vs-uta-0022600239
- https://www.nba.com/game/dal-vs-bos-0022600240
- https://www.nba.com/game/nyk-vs-tor-0022600241
- https://www.nba.com/game/ind-vs-phi-0022600236 · https://www.nba.com/game/lal-vs-phx-0022600237
- https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_15PM.pdf
- Official gamebook PDFs (per final, in evidence_finals_2026-11-15.json `gamebook_pdf`)
