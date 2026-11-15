#!/usr/bin/env python3
"""README.md and EXECUTIVE_SUMMARY.md for the 2026-11-15 day roll.

Both documents state commitments (horizon length, window length, which injury edition is in
force) that a data roll moves. This script updates the commitments in place and adds a dated
section describing what the roll did, so the previous session's numbers stay readable as the
state at that freeze instead of being silently rewritten.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

README_EDITS = [
    ("| **Build D — this build** | [`index.html`](index.html) → [`site/`](site/pages/picks.html) | 27 games, 14–17 Nov |",
     "| **Build D — this build** | [`index.html`](index.html) → [`site/`](site/pages/picks.html) | 34-game rolling horizon (15–18 Nov); 27 priced lines in the 14 Nov freeze |"),
]

EXEC_EDITS = [
    ("**As of** 2026-11-14 (UTC) · **Session** `arena/934ca56f-nba1` · **Live site**",
     "**As of** 2026-11-15 (UTC) · **Session** `arena/934ca56f-nba1`, rolled forward by `arena/e3ebc423-nba1` · **Live site**"),
    ("It covers 27 games across the full three-day horizon\n(2026-11-14 to 2026-11-17), with an originated spread, total and fair moneyline for every\ngame, and a gated paper pick.",
     "It prices 27 games in the 2026-11-14 freeze (that slate is now settled:\n3-10 on its 13 gradable picks, −5.80 units at the repo's −110 convention, 4 rows left ungraded\nfor want of a citable per-player box score) and carries a rolling horizon of 34 games, 2026-11-15\nto 2026-11-18, re-read from the official date cards on 2026-11-15. Every priced game has an\noriginated spread, total and fair moneyline, and a gated paper pick."),
]

SECTION = """
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
"""


def patch(path, edits):
    p = os.path.join(ROOT, path)
    t = open(p, encoding="utf-8").read()
    n = 0
    for old, new in edits:
        if old in t:
            t = t.replace(old, new, 1)
            n += 1
        elif new.split("\n")[0][:60] not in t:
            print("  ! pattern not found in %s: %r" % (path, old[:70]))
    return t, n


readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
if "34-game rolling horizon" not in readme:
    t, n = patch("README.md", README_EDITS)
    open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(t)
    print("README.md: %d commitment line(s) updated" % n)
else:
    print("README.md: already rolled")

ex = open(os.path.join(ROOT, "EXECUTIVE_SUMMARY.md"), encoding="utf-8").read()
if "## 0. What changed on 2026-11-15" not in ex:
    t, n = patch("EXECUTIVE_SUMMARY.md", EXEC_EDITS)
    anchor = "\n---\n"
    i = t.find("## 2.")
    if i > 0:
        t = t[:i].rstrip() + "\n" + SECTION.rstrip() + "\n\n" + t[i:]
    else:
        j = t.find("\n## ")
        j = t.find("\n## ", j + 5)
        t = t[:j] + "\n" + SECTION.rstrip() + t[j:]
    open(os.path.join(ROOT, "EXECUTIVE_SUMMARY.md"), "w", encoding="utf-8").write(t)
    print("EXECUTIVE_SUMMARY.md: %d line(s) updated + dated section inserted" % n)
else:
    print("EXECUTIVE_SUMMARY.md: already rolled")
