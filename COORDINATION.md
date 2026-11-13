# COORDINATION — Shared Task Board

**Repo:** `wingbangboozle1-lang/NBA1`
**Mode:** Single active session for this build (no other session claims were present at start).
**Session ID:** `arena-7cfd203a` (branch `arena/7cfd203a-nba1`, base commit `f73edd2`)
**Last updated:** 2026-11-13

---

## 0. Ground rules used in this board

1. A task is only `unclaimed`, `in progress`, `done`, or `needs review`.
2. `needs review` means the item is published on `docs/pages/flagged.html` (Flagged for Review) and **does not block** anything.
3. Each task lists the **file scope** it owns. No session edits outside its scope; cross-scope needs are logged as *requests* in §4.
4. Claims are committed and pushed immediately after writing.
5. A claim older than 60 minutes with no commits may be taken over by another session (handoff logged in §5).

---

## 1. Task board

| # | Task | Status | Owner (session) | Branch | File scope | Notes |
|---|------|--------|-----------------|--------|------------|-------|
| T01 | Repo audit + coordination board | done | arena-7cfd203a | arena/7cfd203a-nba1 | `COORDINATION.md`, `README.md`, `notes/` | Repo was empty (README stub only). |
| T02 | Verified data acquisition (teams, schedule, injuries, players) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `data/*.json`, `data/*.csv` | All rows carry an official `source_url`. |
| T03 | Line origination engine (totals / spreads / props) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/originate_lines.py`, `data/derived/lines.json` | HCA unavailable from official sources → flagged. v2: dispersion measured from 14 real finals (total sd 17.13, margin sd 16.13) after the first version produced ±30 spreads from a guessed sd. |
| T04 | Correlation model + empirical checks | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/compute_correlations.py`, `data/derived/correlations.json` | Empirically computable parts computed from official team stats; SGP table labelled by derivation type. |
| T05 | Validation gates + strategy leaderboard | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/strategies.py`, `data/derived/strategies.json`, `docs/pages/strategies.html`, `docs/pages/gates.html` | 8 strategies graded against 14 real finals through 6 conjoined gates → **0 validated**. Null control passes 4/6 gates, which is documented as a gate-calibration finding, not a result. No gate was loosened. |
| T06 | Injury / rotation / game-flow analysis | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/injury_impact.py`, `data/player_absence_evidence.json`, `data/derived/injury_impact.json`, `docs/pages/injuries.html`, `docs/pages/gameflow.html` | Key correction: season stats already contain past absences, so only `NEW_ABSENCE` players move a line. 9 players individually verified; 79 of 88 report rows have no verified minutes and produce no adjustment. |
| T07 | Open-questions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/questions.html` | Q/A table with "known / unknown / how to obtain". |
| T08 | Improvement suggestions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/suggestions.html` | Decision-ready proposals with effort/impact/trade-off. |
| T09 | Executive summary | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/executive-summary.html` | |
| T10 | Static site build (dashboard + subpages) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/**`, `scripts/build_site.py` | 14 pages, fully generated from `data/`. 486 table rows, **every one** carrying an official source link. |
| T11 | Link + provenance verification | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/verify_data.py`, `scripts/verify_inline.py`, `scripts/check_links.py`, `notes/verification-log.md` | Three gates: `verify_data.py` (15 checks, errors=0), `verify_inline.py` (18 checks, 18/18), `check_links.py` (0 broken internal, 0 bad hosts, 0 unsourced rows). |
| T12 | **Integration + publish** | done | arena-7cfd203a | arena/7cfd203a-nba1 | merge → `main`, Pages settings | PR + merge + Pages deploy verification. |

### Integration session note
Only one session touched this repo during this build, so the integration pass was performed in the
same session (T12): the combined dataset was re-verified row-by-row, the link checker was run, the
site was built, and Pages was republished. All results are recorded in §3.

---

## 2. Verification standard applied to every table row

* Each row carries a `source_url`.
* A value that could not be read from an official source is **blank** and flagged `unverified`.
* No value is interpolated, estimated, or carried over from memory.
* "Derived" values (e.g. projected totals) are labelled `DERIVED` and show their formula and inputs,
  because a derived number is not an official statistic.

---

## 3. Log of results (sources, verification, irregularities)

### 3.0 Second working pass — 2026-11-13 (commits `a7f9e41`, `b639cfe`)

This pass replaced guessed parameters with measured ones and added the analysis, gate and site layers.
Everything below is reproduced by running the scripts in order.

**Order of execution (each step depends on the previous):**
```
python3 scripts/originate_lines.py      # lines.json
python3 scripts/compute_correlations.py # correlations.json
python3 scripts/backtest.py             # backtest.json
python3 scripts/injury_impact.py        # injury_impact.json
python3 scripts/strategies.py           # strategies.json
python3 scripts/build_site.py           # docs/**
python3 scripts/verify_data.py          # errors=0
python3 scripts/verify_inline.py        # 18/18
python3 scripts/check_links.py          # PASS
```

**Measured, replacing guesses:**
| Quantity | First version | Measured value | Source |
|---|---|---|---|
| Total dispersion (sd) | guessed `√2·σ_teams·0.75` | **17.13** points (n=13, OT excluded) | https://www.nba.com/games?date=2026-11-11 and `?date=2026-11-12` |
| Margin dispersion (sd) | same guess | **16.13** points (n=14) | same |
| Mean game total | league proxy | **226.31** points | same |
| Mean home margin | 0 (HCA not modelled) | **−0.14** points (n=14 — too noisy to use) | same |

**Correlations measured (n=30 teams, Bonferroni-aware):** pace↔total r=0.792, OffRtg↔win% r=0.828,
DefRtg↔win% r=−0.800, eFG%↔OffRtg r=0.819, FG3%↔OffRtg r=0.684, TOV%↔OffRtg r=−0.473,
OREB%↔OffRtg r=0.372. Six same-game/prop correlations left **null** (tier C) because the required
player game-log corpus was not reachable.

**Irregularities found and how each was handled:**
| # | Finding | Handling |
|---|---|---|
| 1 | **Fabricated row, self-caught.** A Darius Garland (LAC) absence row was drafted into `player_absence_evidence.json`. | He is **not on the 11/13 report** (LAC rows are Beal, Ingram, Martinelli, Miller, Niederhauser). Removed by cross-check; retraction recorded in the data file and on `flagged.html`. |
| 2 | `injury_impact.py` multiplied lost production by *play probability*, which is 0 for an `Out` player, so every adjustment was silently zero. | Changed to `(1 − play probability)`. Caught by inspecting output, not by luck. |
| 3 | `backtest.py` totals grading compared projections against the actual total of the same game — look-ahead. | Replaced with a fixed pre-game baseline so the bet could actually exist. |
| 4 | `line_total` did not always equal `proj_home_pts + proj_away_pts` because of rounding order. | Round the two point projections first, then derive total and spread. |
| 5 | Nav links were correct at one page depth only. | Nav hrefs computed from page depth. |
| 6 | The null control passes 4 of 6 validation gates on 14 games. | Documented on `gates.html`; gates **not** loosened. G1 (sample floor) kept first. |
| 7 | 79 of 88 injury-report rows have no verified minutes/points. | Left blank, produce no adjustment, counted on `flagged.html`. |
| 8 | No sportsbook price reachable, so every ROI assumes −110. | Stated in `strategies.json["_meta"]` and on the leaderboard page. Logged as blocking question Q01. |

**Backtest result (explicitly contaminated):** n=14, total MAE 14.06 vs 16.10 baseline, margin MAE
12.36, straight-up 78.6%, ATS vs own line 57.1%. Team ratings were captured on 11/13 and therefore
contain the tested games — the label `CONTAMINATED` is carried in the data and on the site.

**Gate outcome:** 0 of 8 strategies validated. 4 ungraded (no outcomes exist yet). Reward payable: none.

### T02 — Data acquisition
| Dataset | Source (official) | Rows | Retrieved (UTC) |
|---|---|---|---|
| Team advanced stats 2026-27 | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 30 | 2026-11-13 |
| Schedule / slate (11/13–11/16) | https://www.nba.com/schedule and https://www.nba.com/games | 31 games | 2026-11-13 |
| Injury report 11/13 03:00 PM ET | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_03_00PM.pdf (index: https://official.nba.com/nba-injury-report-2026-27-season/) | 88 entries (3 withheld) | 2026-11-13 |
| Played games 11/11–11/12 | https://www.nba.com/games?date=2026-11-11 and `?date=2026-11-12` | 14 finals | 2026-11-13 |
| Player minutes leaderboard | https://www.nba.com/stats/players/traditional?...&sort=MIN | 24 players | 2026-11-13 |
| Season leaders (per-game) | https://www.nba.com/games (Season Leaders blocks) | 18 players | 2026-11-13 |
| Playing rules (OT, timeouts, shot clock, roster) | https://official.nba.com/rulebook/ (Rules 3, 5, 7) | 12 rules | 2026-11-13 |
| Stat definitions | https://www.nba.com/stats/help/glossary | 14 definitions | 2026-11-13 |

### T12 — Publish
* Combined data re-verified line by line against the source URLs above: **no value changed**.
* Link check: run `python3 scripts/check_links.py` → see `notes/verification-log.md`.
* PR: see §6. Pages: `https://wingbangboozle1-lang.github.io/NBA1/`.

---

## 4. Cross-session requests
_None outstanding._

---

## 5. Handoff log
_None._

---

## 6. Publish record
| Item | Result |
|---|---|
| Branch | `arena/7cfd203a-nba1` |
| Pull request | see bottom of file / `notes/publish-log.md` |
| Merge | recorded in `notes/publish-log.md` |
| GitHub Pages | `https://wingbangboozle1-lang.github.io/NBA1/` |
