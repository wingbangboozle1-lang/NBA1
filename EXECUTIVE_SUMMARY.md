# Executive summary — NBA1 line origination and strategy lab

**As of** 2026-11-15 (UTC) · **Session** `arena/934ca56f-nba1`, rolled forward by `arena/e3ebc423-nba1` · **Live site**
<https://wingbangboozle1-lang.github.io/NBA1/>

This document states what the system does, what it has actually established, what it has
not, and what a decision-maker needs in front of them before choosing anything. Every
number here is traceable to an official source; the source for each claim is named inline.
Where a value could not be confirmed it is described as unconfirmed rather than filled in.

---

## 0. What changed on 2026-11-15 (data roll, settlement and two model inputs measured)

Session `arena/e3ebc423-nba1` ran one day of the data-ops loop end to end, behind gates.

- **Freshness + provenance gates first.** 17 checks — capture age, slate window (today + maximum
  three days), per-day game counts against the official calendar strip, one-row-per-game, official
  URL on every row, quarter sums, records cross-checked against the standings page, every injury
  row carrying a printed reason, page-break rows labelled rather than attributed. The roll script
  exits 1 and writes **nothing** if any check fails, so a stale or untraceable capture cannot
  reach a published page. Record: `data/live/gates_2026-11-15.json`.
- **The per-game result feed grew.** Five 2026-11-14 games appended with final, OT flag, venue,
  attendance, officials, recap link and quarter scores; 4 of 5 carry a LINESCORES split and each
  captured split sums to the printed final. CHI@MIN's split could not be read, so those cells say
  *not captured* — no quarter line was solved backwards from a final. The out-of-sample window is
  now 65 games, 2026-11-06 to 2026-11-14.
- **The injury report moved, and the job that reads it was fixed.** The site had been keyed to
  editions named `…PM.pdf`; the league republishes every 15 minutes from 12:00 a.m. ET, so the
  newest report on a game day is an **AM** file the parser could not see. `parse_injury_index`
  now accepts AM and PM, the hard-coded PM-only list is a labelled fallback used only when the
  index cannot be read, and `scripts/check_injury_editions.py` fails the build if either
  regresses. Both 11/15 editions (06:00 and 06:15 AM ET) were read in full and diffed: no status
  changed in the fifteen minutes between them, and the one structural difference — a row whose
  Team cell the earlier render dropped at a page break — is recorded as printed.
- **Settlement and the picks table are now the same object.** Every one of the 60 published rows
  carries a `settled` flag, the final, its distance to the line it was graded against, units at
  the −110 convention and a settlement stamp naming the **git blob** of the frozen picks file —
  grading reads that blob, not the working copy, so a settlement cannot move a line. Each of the
  60 picks also carries a sha256 over its frozen core fields, chained, head committed
  (`data/live/ledger_2026-11-15.json`). Parlays are graded leg by leg with the naive product
  printed beside the joint probability and Frechet bounds, as always with no official parlay
  price to price them at (F3 unchanged).
- **Home court is measured.** The model's `+2.5` was an assumption (flag E-01); the fitted
  residual intercept says 3.508; the **measured home-win rate pins it at 1.053 points**
  (0.5294 across 187 home games in the official standings HOME column, 0.5469 across the 64
  non-neutral games in our own feed, converted with sigma = 11.0). `scripts/pin_home_court.py`
  writes `data/derived/home_court_pin.json`, `engine/model_core.py` will price with it once a
  freeze adopts it, and the sensitivity for the un-tipped horizon is published as a table
  (−1.447 points on every home margin, zero on totals, favourite flips on a minority of rows)
  rather than applied to a hashed set. Flags F71 / Q22 / SG30.
- **Travel is still not modelled, and that is now a named gap rather than a silent one.** The
  term (`travel_load`), the great-circle arithmetic (`haversine_miles`, self-checked at 1,627
  miles New York→Denver) and the data contract all exist; the input does not — no NBA-operated
  page reachable from this build publishes arena coordinates, and copying them from memory would
  put an untraceable number in a table whose whole job is traceability. Coefficient stays 0.0;
  the printable travel fact (whether a team's next game is in the city it is already in) is
  published in its place. F70 / SG31.
- **Nothing was promoted that the site cannot cite.** Every new row on every new page links an
  official page; where a value could not be read, the cell says so. New flags F69–F74, new open
  questions Q22–Q25, new suggestions SG30–SG33, and the day-roll page
  ([`site/pages/day-roll.html`](site/pages/day-roll.html)) carries the gate record, the feed, the
  settlement, the ledger, the pin and the gap in one place.


---

## 1. The one-paragraph version

The system originates its own NBA lines from official NBA.com data and then tries hard to
prove those lines carry skill. It prices 27 games in the 2026-11-14 freeze (that slate is now settled:
3-10 on its 13 gradable picks, −5.80 units at the repo's −110 convention, 4 rows left ungraded
for want of a citable per-player box score) and carries a rolling horizon of 34 games, 2026-11-15
to 2026-11-18, re-read from the official date cards on 2026-11-15. Every priced game has an
originated spread, total and fair moneyline, and a gated paper pick. **No strategy has cleared every gate.** The best, S1 (side
edge versus a naive reference line), is **23-9 on 23 graded plays** with an exact binomial
p-value of **0.020** — the first record in this project that is statistically distinguishable
from a coin flip — but it **fails the calibration and stability gates**, so it stays capped
at a quarter unit. A hit rate the model's own probabilities did not predict is a calibration
failure, not a windfall. Nothing is funded, and that is the designed outcome.

## 2. What was verified in this session, and how

| Claim | How it was checked | Result |
| --- | --- | --- |
| All nine 2026-11-13 games are Final | Read <https://www.nba.com/games?date=2026-11-13> directly (chunks 0–1) | 9 / 9 Final, one of them Final/OT |
| The 11/13 transcription is correct | Compared with a second, independent transcription by another session (`data/verified/finals_2026-11-13.json`) | **9 / 9 agree**, 0 disagreements |
| The 27 horizon games are real, on the stated dates, with the stated tip times and game IDs | Read `?date=2026-11-14` … `?date=2026-11-17` and compared every row | **27 / 27 match**; 0 game-ID errors, 0 tip-time errors |
| The team records printed on the horizon were current | Same four pages, cross-checked against <https://www.nba.com/standings> | **29 of 54 were stale**; all 29 corrected; 0 remaining mismatches |
| The 11/13 lines settle as stated | Settled the nine published lines against the official finals | **3 WIN, 4 LOSS, 2 NO BET**; mean absolute margin error 12.39 pts |
| A newer injury edition than the site's exists | Read the 11/14/26 04:15 AM ET official PDF | Readable; **49 rows** transcribed; the site's 11/13 07:30 PM ET edition was one cycle old |
| The team ratings can be refreshed | Fetched <https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season> | **No** — the table renders client-side and returns no data |

Every one of these checks is re-runnable: `python3 scripts/verify_all.py` and
`python3 scripts/verify_horizon_s934ca56f.py`.

## 3. What the model has and has not shown

**Out-of-sample window:** 60 completed games, 2026-11-06 to 2026-11-13, every one predicted
using team ratings built only from 2026-10-20 to 2026-11-05. No game in the test window
contributes to the ratings that predict it.

*Provenance caveat, stated once and meant:* the 51 → 60 extension landed with PR #59. It
depends on a team-ratings refresh that **cannot be reproduced from this environment** —
`nba.com/stats/teams/advanced` renders client-side and returns no data table (flag F24,
re-tested 2026-11-14). The nine scores that extend the window are confirmed three times over;
the extended error metric is not independently re-derivable here. Treat it as reported, not
reproduced.

| Metric | Model | Naive reference | Reading |
| --- | --- | --- | --- |
| Margin MAE | 12.98 | 13.62 | Model better |
| Total MAE | 14.83 | 14.72 | **Reference better** |
| Brier (win prob.) | 0.1970 | 0.1889 | **Reference better** |
| Log loss | 0.5768 | 0.5567 | **Reference better** |

The honest reading: a small edge on the margin, **no** edge on totals or on picking
winners. The bootstrap intervals on margin MAE overlap almost completely (model
9.80–16.14, reference 10.05–16.53), so even the margin improvement is not statistically
established.

The single most useful event in this project was the window growing from 28 to 51 games and
**flipping the sign of the totals result**. That is exactly what a sample gate is for, and it
is why nothing was promoted on the earlier reading.

## 4. The leaderboard, and why nothing is funded

Ten strategies, seven gates. A tier is a **cap on stake**, not a profit forecast.

| Rank | ID | Strategy | Record | Units | Binding gate |
| --- | --- | --- | --- | --- | --- |
| 1 | S1 | Side edge vs reference | 23-9 | +11.91 | **G4 now PASSES** (Wilson lower bound 0.546 > 0.524); **G2 calibration FAIL** is the binding gate |
| 2 | S5 | Back-to-back fade | see data | see data | **G4 skill-not-luck: FAIL** |
| 3 | S3 | Moneyline value | 7-7 | −0.64 | **G2 calibration: FAIL** |
| 4 | S2 | Total edge vs reference | 5-5 | −0.46 | **G2 calibration: FAIL** |
| 5 | S10 | Same-game parlay (side + total) | 8-11 | +2.92 | **G2 calibration: FAIL** |
| 6 | S9 | Two-leg cross-game parlay | 3-4 | −0.15 | **G2 calibration: FAIL** |
| 7–10 | S4, S6, S7, S8 | Pace total, availability shock, player points, PRA combo | 0-0 | 0.00 | **G1: FAIL** (0 graded plays) |

The four at 0-0 are not losses: their own filters produced no plays in the window, which is
itself a finding about how restrictive those rules are. The live per-strategy figures are on
the [Leaderboard page](https://wingbangboozle1-lang.github.io/NBA1/site/pages/leaderboard.html),
which names the binding gate for each one.

## 5. The limits that matter most

1. **No sportsbook price exists anywhere in this system.** No NBA-operated source publishes
   one, so no official link can be attached to one. "Edge" here means *the model against a
   deliberately naive reference model built from the same official ratings*. It does not mean
   edge against a book. Until real closing prices are logged, "units" means model-versus-naive-model
   units and no expected value against a market can be stated. **(F3)**
2. **The ratings window ends 2026-11-12.** The 11/13 finals are now known, have settled the
   11/13 lines and refreshed every stale record, but **the advanced-stats table is not
   retrievable from this environment** (§2), so the ratings have not been re-fitted. Every
   forward line therefore rests on ratings one night short. **(F19, F24)**
3. **Two models publish two different lines for the same games.** They disagree on 17 of 17
   shared games and differ on which team is favourite in 2 of them. The site now labels which
   one is authoritative (the pipeline model, the only one with a measured out-of-sample
   error) and forbids averaging them — but choosing between them is an open decision.
   **(F26, SG15)**
4. **Player minutes are known for 50 of 465 players.** The availability-impact column is
   therefore a measured *floor* and reads 0.00 for several teams that are genuinely short-handed.
   The minutes-coverage column sits next to every figure so a 0.00 is never read as "healthy". **(F2)**
5. **The injury layer is one publication cycle behind.** A newer edition exists and is
   published on the site as evidence, but the same five of ten teams playing on 11/14 still
   show NOT YET SUBMITTED, and no 11/16 or 11/17 game appears in any edition. **(F15)**
6. **The 11/13 settlement is nine games.** It cannot show skill. Mean absolute margin error
   12.39 points over nine games is a sanity check, nothing more. **(F36)**

## 6. What was corrected in this session

Five published claims were false and have been corrected at source, with the evidence kept:

| Flag | Was | Now |
| --- | --- | --- |
| F13 | "No final score exists for 11/13" | Closed — 9/9 finals read, cross-checked twice |
| F14 | "18 team records are one night out of date" | Closed — 29 records corrected, 0 mismatches |
| F29 | "The site still shows 11/13 as unfinished" | Closed — every page corrected, README rewritten |
| F27 | Field described as a book-style spread | Labelled as the projected **home margin**; the old note was backwards |
| F28 | "Paper picks: 63" (mixed markets) | Now states 51 single-leg + 12 two-leg = 63, and 23 of 27 games |
| F15/F31 | "No newer injury edition exists" | Corrected — a newer edition was readable and is published |

Two of these were more serious than a stale label. **F27** meant a reader could read a
negative number as "home team favoured" when it meant the opposite. **F15/F31** generalised
a single `AccessDenied` into a blanket claim that no newer information existed, which is the
failure mode this project is supposed to guard against.

## 7. What a decision-maker must choose before anything else

These are not technical tasks. They are choices, and each blocks work that cannot sensibly
start until it is made. The full list with options, effort, risk and consequence is on the
[Suggestions page](https://wingbangboozle1-lang.github.io/NBA1/site/pages/suggestions.html).

| # | Decision | Blocks | Recommendation on the table |
| --- | --- | --- | --- |
| 1 | **Which line set is the published horizon** (SG15) | Publishing any pick as *the* pick | Option 1: keep the pipeline model, retire the second line set |
| 2 | **Do the gates allocate stake, or only report** (SG7) | Any staking rule | Option 1: tier-driven staking |
| 3 | **Is "edge" ever allowed to mean market edge here** (SG6) | Honest expected-value claims | Separate the two words in the UI |
| 4 | **Log real closing prices, or accept no EV claim** (SG2) | Any real expected-value statement | Log prices with a per-row source |
| 5 | **Backfill minutes for all 465 players** (SG3) | Injury impact above a floor | Backfill from the official table filtered by team |
| 6 | **Where decisions get recorded** (SG17) | Repeatability across sessions | Status field in `suggestions.json`, shown on the page |
| 7 | **Whether to run a gap-closure triage** (SG18) | Finding missing information on purpose | Triage by (what it blocks) ÷ (cost) |

**If only one decision is made:** number 1. Until one line set is authoritative, every game
on the site has two different numbers and no pick can honestly be called the site's pick.

## 8. How to read this site

- Every table row carries a link to the official source it came from.
- A blank or an em dash means **unavailable or unverified**. It never means zero.
- "Flagged for Review" is a register of everything not confirmed, published with the link
  that would resolve it. Nothing there blocks the site.
- The build checks that structure and links are sound, and says so honestly: it verifies that
  every row *has* a source, not that every value *matches* it. The value checks are separate
  scripts, named on each page they touch.
