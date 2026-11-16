# Executive summary — NBA1 line origination and strategy lab

**As of** 2026-11-15 (UTC) · **Latest rebuild** session `arena/801ba27f-nba1` ·
**Live site** <https://wingbangboozle1-lang.github.io/NBA1/>

> **2026-11-15 update — read this first.** The model inputs were re-cut from first
> principles out of official box scores (§0 below). Sections 1 onward are the
> 2026-11-14 statement and are preserved unchanged for the audit trail; where they
> disagree with §0, §0 is the current position.

This document states what the system does, what it has actually established, what it has
not, and what a decision-maker needs in front of them before choosing anything. Every
number here is traceable to an official source; the source for each claim is named inline.
Where a value could not be confirmed it is described as unconfirmed rather than filled in.

---

## 0. The 2026-11-15 re-cut — current position

**Session** `arena/801ba27f-nba1` · **COORDINATION.md §41** · **Requirements coverage**:
<https://wingbangboozle1-lang.github.io/NBA1/site/pages/brief-coverage.html>

### 0.1 Why the inputs were rebuilt

The brief asks for the three official team-stat pages (traditional, opponent,
advanced) to be re-read and the model inputs re-cut. All three were fetched. **None
carries data in an HTTP response** — they render their tables in the browser, so the
raw response contains no team rows (evidence: `data/raw/html/2026-11-15-801ba27f/
team_advanced.html.gz`, zero `resultSets`, two `<table>` elements, both date-picker
calendars). The official **box score** pages, by contrast, are server-rendered and carry
the complete official team and player statistics, so the same quantities were rebuilt
from those instead:

```
POSS    = FGA - OREB + TOV + 0.44 * FTA        (official box score terms)
OFF_RTG = 100 * PTS / POSS
DEF_RTG = the opponent's OFF_RTG in the same game
PACE    = POSS per game
```

**222 games** were captured (2026-10-20 to 2026-11-18), **190** of them Final. On every
Final game the quarter scores were asserted to sum to the final score; there are no
failures. Every rating on the site now traces to an official game page.

### 0.2 What changed

| Change | Before | Now | Source |
| --- | --- | --- | --- |
| Home court | fitted freely: +3.51 pts, standard error 2.28 | **pinned to the measured home-win rate**: 0.5263 over 190 finals → **1.108 pts** | `data/derived/measured_constants_2026_27.json` |
| Confidence signal | one blended rating | **disagreement between two independent estimators**, mean **4.05 pts** on the spread | `data/derived/estimators_2026_27.json` |
| Ratings | scraped from a page that returns no data | rebuilt from official box scores, 190 finals | `data/derived/team_ratings_2026_27.json` |
| Injury handling | one edition transcribed by hand | **75 editions** downloaded, hashed, stored, parsed; **28 status changes** computed between consecutive editions | `data/injury_reports/diff_2026-11-15.json` |
| Parlay pricing | model-derived rho | **measured** rho (cross-game 0.0142 over 1,546 pairs; team-mates -0.0975 over 374), naive product printed beside it | `data/derived/rho_2026_27.json` |
| Rotation | minutes known for 50 players | measured top-8 minutes shares for all 30 teams, with a worked replacement | `data/derived/rotation_2026_27.json` |
| Surfaces | one mixed page | **projection** (safe) and **bet** (gated) as separate pages, never merged | `site/pages/projection.html`, `site/pages/bet-surface.html` |

### 0.3 The rolling window

Today plus three days, per the brief: **2026-11-15 to 2026-11-18, 34 games**, of which
**28 had not tipped** at publication. Games that had already tipped are excluded from the
bet surface and are shown on the projection surface with their official status.

### 0.4 Settlement

The 2026-11-15 slate was settled from official finals only. At capture **2 of 9 games
were Final** and both published tickets on them won (**+2.00** paper units); four games
were in progress and three had not tipped, so their **7 tickets remain PENDING**. Nothing
was graded from a live score. The pre-tip anchor (SHA-256 of the publication file) and
the hash chain are on the Settlement page.

### 0.5 What is still blocked

1. **Market-anchored prior (F95).** No closing line exists anywhere in this repository
   and no NBA-operated source publishes one, so the prior weight is 0 and no
   market-blended price is published. Two validation gates are blocked on the same
   missing input.
2. **Travel distance (F94).** Arena name, city and state are official; latitude and
   longitude are not published by any NBA page, so the distances are derived and flagged.
   No travel value moves a line.
3. **The official stats pages (F96).** They cannot be read by a script. Either a headless
   browser is added to the refresh job or the box-score rebuild is adopted as the
   official path. Silently straddling the two is not an option.

### 0.6 Requirements

**16 of 21** numbered instructions in the brief are fully delivered; the remaining five
are partial or blocked, and each says exactly what is missing. One page, one row per
instruction: <https://wingbangboozle1-lang.github.io/NBA1/site/pages/brief-coverage.html>

### 0.7 Verification performed

All gates pass on the merged tree: `check_site` · `check_links` · `check_rendered` ·
`verify_all` (VERIFY OK) · `verify_integration` (0 errors, 44 pre-existing warnings) ·
`render_check` (151 pages / 9,602 rendered rows / 0 problems) · `verify_ledger`
(chain OK) · `build_verification_page` idempotent.

### 0.8 What was found and corrected after the first publication (F100)

The first publication of the parlay page priced every parlay and same-game parlay
**three times too high**. The joint-probability routine used composite Simpson weights
without the `h/3` factor, so joint probabilities above 1.000 were published — the
ORL@BOS / MIL@MIA two-leg was printed as **1.6171** against a naive independent product
of 0.5375. The factor has been restored and the routine was checked against two closed
forms: `rho = 0` now reproduces the independent product exactly, and `rho = 0.5` at
`a = b = 0` reproduces `1/4 + arcsin(rho)/(2*pi) = 0.333333`. Every parlay and SGP row
has been recomputed and re-published, still before the tip of the earliest game they
cover (2026-11-16). **No single-leg ticket changed** — singles are priced from the
normal CDF directly and were never affected.

This is recorded, not hidden: it is flag **F100** on the Flagged for Review page, a
correction banner at the top of the parlay-pricing page, and ledger entry 10. Ledger
entries 6 and 8 are marked **superseded** by entry 9 rather than edited — the chain is
append-only, so the earlier entries remain in it and are reported as superseded instead
of being silently rewritten. Entry 5 is superseded by entry 7 for the same reason (a
re-run 27 seconds later rewrote the settlement file's timestamp); entry 7 was restored
to verify again once the settlement stamp was redefined as the moment of *first*
settlement rather than the last builder run.

The lesson is the point of the ledger: an error that makes a probability larger than
one is exactly the kind of thing a hash-chained, independently verified publication
process is supposed to catch, and it did — one review pass after publication.

---

## 1. The one-paragraph version

The system originates its own NBA lines from official NBA.com data and then tries hard to
prove those lines carry skill. It covers 27 games across the full three-day horizon
(2026-11-14 to 2026-11-17), with an originated spread, total and fair moneyline for every
game, and a gated paper pick. **No strategy has cleared every gate.** The best, S1 (side
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
