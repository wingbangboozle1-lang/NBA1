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
| T03 | Line origination engine (totals / spreads / props) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/originate_lines.py`, `data/derived/lines.json` | HCA unavailable from official sources → flagged. |
| T04 | Correlation model + empirical checks | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/compute_correlations.py`, `data/derived/correlations.json` | Empirically computable parts computed from official team stats; SGP table labelled by derivation type. |
| T05 | Validation gates + strategy leaderboard | done | arena-7cfd203a | arena/7cfd203a-nba1 | `data/strategies.json`, `docs/pages/strategies.html`, `docs/pages/validation-gates.html` | No historical game-log corpus available in-sandbox → gates reported as NOT RUN, never as PASS. |
| T06 | Injury / rotation / game-flow analysis | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/injury_impact.py`, `data/derived/injury_impact.json`, `docs/pages/injuries.html`, `docs/pages/game-flow.html` | Impact weights are **model assumptions**, labelled as such. |
| T07 | Open-questions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/questions.html` | Q/A table with "known / unknown / how to obtain". |
| T08 | Improvement suggestions register | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/suggestions.html` | Decision-ready proposals with effort/impact/trade-off. |
| T09 | Executive summary | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/pages/executive-summary.html` | |
| T10 | Static site build (dashboard + subpages) | done | arena-7cfd203a | arena/7cfd203a-nba1 | `docs/**`, `scripts/build_site.py` | Built to `docs/`, served by GitHub Pages. |
| T11 | Link + provenance verification | done | arena-7cfd203a | arena/7cfd203a-nba1 | `scripts/check_links.py`, `notes/verification-log.md` | Fails build on broken internal links or a data row without a source. |
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

### T02 — Data acquisition
| Dataset | Source (official) | Rows | Retrieved (UTC) |
|---|---|---|---|
| Team advanced stats 2026-27 | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 30 | 2026-11-13 |
| Schedule / slate (11/13–11/15) | https://www.nba.com/schedule and https://www.nba.com/games | 23 games | 2026-11-13 |
| Injury report 11/13 12:00 PM ET | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_12_00PM.pdf (index: https://official.nba.com/nba-injury-report-2026-27-season/) | 82 entries | 2026-11-13 |
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
