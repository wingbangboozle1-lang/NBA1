# Executive summary — NBA1 line origination and strategy lab

**As of** 2026-11-19 (UTC) · **Sessions** `arena/934ca56f-nba1` (original), `arena/fb91550a-nba1`
(this update) · **Live site** <https://wingbangboozle1-lang.github.io/NBA1/>

This document states what the system does, what it has actually established, what it has
not, and what a decision-maker needs in front of them before choosing anything. Every
number here is traceable to an official source; the source for each claim is named inline.
Where a value could not be confirmed it is described as unconfirmed rather than filled in.

---

## 0c. Update — 2026-11-19T12:5xZ, session `arena/fb91550a-nba1` (read this first)

**The scheduled job was measured for the first time from inside its own publish path, and it
had never published or rebuilt anything.** This section supersedes any statement that the
scheduled refresh "runs" in the sense of *delivering* what it captures.

| Item | Was | Is now | Evidence |
| --- | --- | --- | --- |
| Scheduled publish path | assumed working; 13 runs, no PRs, attributed to "no changes" | **structurally broken**: a single `git add` named four paths that cannot exist, and `git add` aborts entirely (exit 128) on any unmatched pathspec — so every run committed nothing | `scripts/fb91550a_refresh_publish_audit.py` reproduces the abort; 13 `auto/refresh-*` branches, **0 pull requests ever** |
| Rebuild step | blocked by one unsatisfiable snapshot requirement (§69) | **three independent unsatisfiable predicates** plus a fourth latent one; all four fixed | `engine/refresh_gate.py`, `scripts/test_fb91550a_gate.py` (3/3 pass; 3 fail on the old code) |
| Rebuild gate dependence | `fetch ✓ && promote ✓ && freshness ✓` | `fetch ✓ && freshness ✓` — the freshness gate re-reads promotion records and is the authority; promote's exit code (1 whenever *any* item is blocked) can no longer disable the rebuild | `.github/workflows/refresh-data.yml` |
| Failed PR on a scheduled run | warning, run still green | **`::error` and exit 1** — a stranded capture is a failed refresh | same file |
| R01 (scheduled refresh + gated rebuild) | partial | **still partial, and now honestly so**: the only remaining block is S1 (official Advanced team table) | F-915-04 |
| Official results feed | 74 rows, current to 11/15 | **99 rows, current to 11/18** — the 25 finals the 12:03Z run captured and could not publish | every row re-checked against `data/official/results_*.json`: 0 mismatches |
| Horizon 11/19–11/22 | frozen pre-tip at 05:45Z, not re-read | **re-read from the official games pages**: 26/26 matchups present, **25/25 times agree**, 1 `NOT_CHECKED` | `verify/2026-11-19-fb91550a/horizon_reverification.json` |
| Official schedule rows with a source link | 3 rows rendered a blank Source cell | **all 26 rows carry their official game-page link** (22 missing `S4_<game_id>` registrations added and read back) | F-915-03 |

### What this session refused to do

**It refused to declare S1 unreadable.** That was the one-line path to a green gate: add
`S1_season` to `data/raw/unreadable_sources.json` exactly as S8/S9/S10 are declared. It
would have been false. Read first-hand through the platform fetch channel on 2026-11-19,
`https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season` returns
the complete 30-row Advanced table (Los Angeles Lakers first, 16 GP, 1,614 possessions),
current through 11/18. The page is not unreadable; the *runner's HTTP client* cannot read
it, and its stats.nba.com fallback times out. Those are different problems with different
fixes, and only one of them justifies a declaration. So R01 stays `partial` and the gate
keeps blocking on S1 — that is the gate doing its job, not a defect.

### What is proven, and what is not

**Proven:** the publish step could not have worked, by a mechanism reproduced on demand;
the gate had four defects, three of which independently disabled the rebuild; the 25 finals
now in the feed match official captures exactly; the horizon matches the official pages on
every row checked. **Not proven:** no scheduled run has yet been *observed* reaching the
rebuild step. That remains the single open measurement in R01, and the honest state of this
repo is that the fix is in place and untested by the scheduler until its next tick.

---

## 0b. Update — 2026-11-19T05:45Z, session `arena/929395a5-nba1` (read this first)

**11/17 and 11/18 are settled, and the horizon has rolled to 11/19–11/22.** Every other
section of this document that describes 11/17 or 11/18 as pending is superseded by this
one, and by the data files that now carry the later observation.

| Item | Was | Is now | Official source |
| --- | --- | --- | --- |
| 11/17 games final | 0 of 5 at the 11/17 capture | **5 of 5** | <https://www.nba.com/games?date=2026-11-17> |
| 11/17 finals | — | **NYK 111–TOR 102, DET 105–SAS 93, POR 105–MIN 106, UTA 132–LAC 107, CHA 114–LAL 118 (OT)** | [game pages](https://www.nba.com/game/cha-vs-lal-0022600256) |
| 11/18 games final | 0 of 12 at the 11/17 capture | **12 of 12** | <https://www.nba.com/games?date=2026-11-18> |
| 11/18 finals | — | **HOU 119–IND 104, PHI 121–ORL 116, MIL 130–MIA 137, MEM 124–CLE 121, CHI 137–BKN 107, WAS 103–TOR 99, DET 122–NOP 109, ATL 117–OKC 112, BOS 101–DEN 105, GSW 94–DAL 116, UTA 109–LAL 97, PHX 128–SAC 107** | [game pages](https://www.nba.com/game/uta-vs-lal-0022600268) |
| 11/17 settlement | refused (0 final) | **SETTLED**, record **1-4-0** singles, **0/3** parlays, **−6.7u** paper at −110 | `data/settlement/settlement_2026-11-17.json` |
| 11/18 settlement | refused (0 final) | **SETTLED**, record **4-8-0** singles, **0/3** parlays, **−8.1u** paper at −110 | `data/settlement/settlement_2026-11-18.json` |
| Results feed | 205 of 222 final | **222 of 222 final**, quarter-sum failures `[]` | `data/official/results_feed_2026_27.json` |
| Ledger | 12 entries | **17 entries**, chain verified OK | `python3 scripts/verify_ledger.py` |
| Horizon | 2026-11-17 to 2026-11-20 (30 games) | **2026-11-19 to 2026-11-22 (26 games)** | [schedule](https://www.nba.com/schedule?date=2026-11-19) |
| Home-court pin | 0.83 points (0.5196, 106 of 204) | **0.09 points (0.5023, 111 of 221)** | [standings](https://www.nba.com/standings) |
| Pre-tip freeze | 2026-11-17T15:54Z | **2026-11-19T05:45Z**, 19+ hours before the first tip (2026-11-20T01:00Z) | `data/ledger/ledger.json` entry 17 |

**Four irregularities were found by reading the official pages, not by a gate.** All gates
were green while all four were live.

| Finding | What it was | Status |
| --- | --- | --- |
| **F-929-01** | The advanced/traditional/opponent team tables are one game behind the standings for LAL and UTA (missing 11/18 UTA 109 @ LAL 97). The recut records gates G3/G4 as FAIL rather than repairing the tables. | Open; lines for PHX@UTA and SAC@LAL on 11/20 inherit the lag. [source](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| **F-929-02** | The 11/20 and 11/22 date pages print stale UTA 2-13 / LAL 13-2 records. | Open; the capture records the printed records verbatim and names the standings as the record of record. [source](https://www.nba.com/games?date=2026-11-20) |
| **F-929-03** | The 11/19 12:30 AM ET injury PDF text render has blank-matchup rows (Kuminga, Pullin) and a garbled 11/20 block. | Open; garbled rows recorded as NOT YET SUBMITTED per the printed text; no row invented or dropped. [source](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-19_12_30AM.pdf) |
| **F-929-04** | LAL and UTA both played back-to-back on 11/17 and 11/18. | Open (informational); the rest model reads the finals corpus, so both show rest_days=0. [source](https://www.nba.com/games?date=2026-11-18) |

**What is still not true, and is not being claimed:** no strategy is funded; no market price
exists anywhere in this repository, so every unit figure is a paper figure at a stated −110
convention; the LAL/UTA ratings are one game stale (F-929-01); and the 11/20 injury rows
beyond ORL@BKN are garbled in the render (F-929-03).

---
## 0a. Update — 2026-11-16T14:40–15:20Z, session `arena/23b323a3-nba1` (read this first)

**The 2026-11-15 slate is complete and settled.** Every other section of this document that
describes 11/15 as "6 of 9 final" or "not settleable" is superseded by this one, and by the
data files that now carry the later observation.

| Item | Was | Is now | Official source |
| --- | --- | --- | --- |
| 11/15 games final | 6 of 9 at the 23:45Z capture | **9 of 9** | <https://www.nba.com/games?date=2026-11-15> |
| The three that were unfinished | HOU@WAS, ATL@MIL, OKC@SAC stored as not tipped | **147-119, 113-106, 125-103**, each with its SCORE BY PERIOD row transcribed and its quarter sums checked against the printed final | [HOUWAS](https://statsdmz.nba.com/pdfs/20261115/20261115_HOUWAS_book.pdf) · [ATLMIL](https://statsdmz.nba.com/pdfs/20261115/20261115_ATLMIL_book.pdf) · [OKCSAC](https://statsdmz.nba.com/pdfs/20261115/20261115_OKCSAC_book.pdf) |
| 11/15 settlement | refused (3 games not final) | **SETTLED**, stamp `2026-11-16T14:45Z`, record **5-4-0** on nine singles, −2.7 units total at paper −110 | `data/settlement/settlement_2026-11-15.json` |
| Ledger | 5 entries | **7 entries** (6 settlement verification, 7 settlement record), chain verified OK | `python3 scripts/verify_ledger.py` |

**Two defects were found by reading the built site against the official source, not by a gate.**
All five gates were green while both were live.

| Finding | What it was | Status |
| --- | --- | --- |
| **F108** | `data/arenas.json` placed the **LA Clippers at Crypto.com Arena, Los Angeles**. The official schedule page puts them at **Intuit Dome, Inglewood, CA** — and the repository's own official capture already said so. PHI (Wells Fargo Center → Xfinity Mobile Arena) and PHX (Footprint Center → Mortgage Matchup Center) were stale in the same file. `scripts/travel_distance.py` read the wrong table, so travel miles inherited the error. | Table repointed at the official capture; discrepancy published, not quietly overwritten. [source](https://www.nba.com/schedule) |
| **F112** | The Results & Settlement page printed **"0 of 0 final — NOT settleable"** directly beneath the section saying the same game day *was* settled. Cause: a session-namespaced duplicate capture (`results_2026-11-15_dfef26dc.json`) became its own section, and matched zero rows against a date that cannot exist. | Builder fixed; the page now has exactly three sections and zero occurrences of "NOT settleable". [source](https://www.nba.com/games?date=2026-11-15) |

**What is still not true, and is not being claimed:** no strategy is funded; no market price
exists anywhere in this repository, so every unit figure is a paper figure at a stated −110
convention; travel miles rest on Wikipedia coordinates (F109); and per-player minutes cover 24
players, which is why 11 of 25 horizon picks fail the redistribution gate (F110).

---

## 0. Update — 2026-11-16, session `arena/dfef26dc-nba1` (read this first)

The window has rolled and the model has been re-cut from a fresh official capture. Sections
1–8 below are the 2026-11-14 record and are kept verbatim for provenance; where this update
supersedes them, it says so.

**What changed**

| Item | Was (2026-11-14) | Is now (2026-11-16) | Official source |
| --- | --- | --- | --- |
| Horizon | 2026-11-15 to 2026-11-18 (34 games) | **2026-11-16 to 2026-11-18 (25 games)** | [games pages](https://www.nba.com/games?date=2026-11-16) |
| Line window vs pick window | lines ran one day wider than picks | **identical**: nothing is originated for a game that has tipped, or beyond three days | — |
| Home-court advantage | fitted / pinned to 0.5319 | **pinned to the measured 0.5285** (102 of 193), worth **1.23 points** | [standings](https://www.nba.com/standings) |
| Headline per game | one blended rating | **the two estimators' disagreement** (max 1.37 pp, mean 0.45 pp; gate 4.0 pp), blend underneath | — |
| Rotation availability | 100% when the injury list was empty, labelled MEASURED | **blank with a stated reason** when no official edition covers the game date, or the team prints NOT YET SUBMITTED | [injury index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| Injury edition behind the cut | 11/15 06:15 PM | **11/15 09:00 PM**, diffed against the previous edition (2 real status changes) | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf) |
| 11/15 results | 2 of 9 final | **6 of 9 final**, 3 stored as in-progress and not settleable | [games page](https://www.nba.com/games?date=2026-11-15) |

**The three things a decision-maker needs to know**

1. **Nothing is staked and nothing is funded.** 14 of 25 picks clear every model gate, but
   0 are publishable outright: no official injury edition covers 11/17 or 11/18 yet, and five
   11/16 teams print NOT YET SUBMITTED, so every pick is provisional.
2. **Eleven of the twenty-five picks are held back by a data gap, not by the model.** Seven
   fail the minutes-redistribution gate because per-player minutes were captured for the
   league-wide top 50 only (F106). The gate is currently measuring whether the capture
   exists.
3. **A re-cut taken during a live slate is contaminated.** The official efficiency table
   already showed the Lakers at GP 14 while three other 11/15 games were still in progress,
   so the cut uses the last *clean* official snapshot (2026-11-15T23:45Z) and publishes that
   as the reason (F103).

**What I verified line by line this session** — every row below was read off the named
official page at 2026-11-16T02:12–02:17Z, not inferred:

- the 25-game schedule for 11/16, 11/17 and 11/18, team by team, with tip times — and one
  genuine conflict between two official captures (GSW@NOP, 09:00 vs 8:00 PM ET — **F101**);
- all 30 standings rows, summed to the measured home-win rate, with two internal
  cross-checks that hold;
- the nine 11/15 results, of which six are final;
- the newest injury PDF in full (160 rows across two game dates) and its diff against the
  previous edition;
- that POR@MIN appears on 11/16 **and** 11/17 under two different game ids — confirmed on the
  official game page, not a parsing artefact (**F102**).

---

## 0b. Update — 2026-11-16, session `arena/fec7d5ae-nba1` (first-hand three-page re-cut + re-verification)

This session re-read the official sources directly at 2026-11-16 ~14:35 UTC and closed the one
requirement that had been genuinely blocked. Sections 1–8 remain the prior record, kept for
provenance.

**What changed / what was verified this session**

| Item | Finding | Official source |
| --- | --- | --- |
| Three team-stat pages (R20, flag F24) | **Re-read and re-cut.** All three pages (traditional, opponent, advanced) returned the full 30-row table; F24 ("advanced table unreachable") is **CLOSED**. New capture `data/official/team_stats_recut_2026-11-16_fec7d5ae.json` + re-cut inputs `data/derived/team_stats_recut.json`. Cross-checks C1–C5 pass; league scoring balance 113.743 vs 113.763 ppg (0.02) validates the transcription. | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) · [traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season) · [opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season) |
| AST Ratio discrepancy (prior flag) | The "AST Ratio renders ~38.x vs published ~19.x" discrepancy recorded by `arena/49f70042-nba1` **does not reproduce** on a full-table read (SAS reads 19.4, matching the published value). It was a chunked-read artifact, not a page property. Recorded so it is not re-flagged. | same three pages |
| Horizon (R25) | **25 games re-verified first-hand, 0 mismatches** (11/16 = 8, 11/17 = 5, 11/18 = 12). F102 (POR@MIN on both 11/16 id `…250` and 11/17 id `…254`) and F101 (GSW@NOP 8:00 PM) independently confirmed. | [11/16](https://www.nba.com/games?date=2026-11-16) · [11/17](https://www.nba.com/games?date=2026-11-17) · [11/18](https://www.nba.com/games?date=2026-11-18) |
| Home-court advantage (R09) | **Pinned, not fitted** — confirmed in code (`engine/model_v2.py hca_from_measured_home_win_rate`, hca_points 1.23). Re-measured from [standings](https://www.nba.com/standings): the rate is now **102/196 = 0.5204**, down from the pinned 0.5285 (102/193). Home wins unchanged; three more home games played, all lost by the home team. The pin is one cycle stale — **reported, not silently applied**. | [standings](https://www.nba.com/standings) |
| Injury report (R04/R18) | A newer **11/16** edition now exists (newer than the 11/15 09:00 PM edition the build used). The injury layer is fresher than the published build reflects. | [injury index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| 11/15 results (R02/R03/R19) | **All 9 games are now Final** — the slate that was not settleable at 02:27Z can now be settled by `scripts/settle_slate.py`. | [11/15 games](https://www.nba.com/games?date=2026-11-15) |

**Requirements register** moved from 13 done / 20 partial to **14 done / 19 partial**: R09 (HCA
pinned to the measured home-win rate) and R20 (three team-stat pages re-read and re-cut) are
closed on verified evidence. Full line-by-line report:
`notes/verification-2026-11-16-fec7d5ae.md`; records in `verify/2026-11-16-fec7d5ae/`.

**Nothing is staked and nothing is funded.** The re-cut inputs are published as verified inputs;
they are not fed through the model or re-priced unilaterally here. The HCA pin update and the
11/16 injury-edition capture are deliberate changes for the integration seat, logged rather than
applied.

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
