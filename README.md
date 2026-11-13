# NBA1

Original NBA line origination, validation and analysis, published as a static
GitHub Pages site.

**Live site:** deployed from `docs/` to GitHub Pages on every push to `main`.

## What this is

A system that originates its own NBA lines from official NBA data, defines
strategies that bet those lines, and grades those strategies against a strictly
out-of-sample window. It covers single bets, parlays, same-game parlays and
player-prop combos. Every published value is traceable to an official source;
anything that could not be confirmed is left blank and recorded on the
**Flagged for Review** page rather than estimated.

## Current status (2026-11-13)

**Provisional — not funded.** The model beats its naive reference on margin and
total accuracy but loses to it on picking winners, and no strategy has reached
the 30-play sample gate. Every strategy is capped at quarter-unit or
research-only. See the site's Executive Summary for the reasoning.

## Repository layout

```
data/raw/            official snapshots, each with its source URL and capture time
  team_advanced.json       NBA.com Stats > Teams > Advanced (two windows)
  games_completed.json     official final scores
  schedule_upcoming.json   official schedule, venues, tip times
  injuries.json            official league injury report, transcribed
  players_traditional.json official player per-game averages
  sources.json             every source, in machine-readable form
data/content/        authored pages (flagged items, questions, suggestions, summary)
engine/              the model, the strategies, the validation, the site builder
docs/                the published site (GitHub Pages serves this directory)
  data/              generated JSON consumed by the pages
  pages/             subpages by category
  assets/            CSS and JS (no framework, no build step)
.github/workflows/   Pages deploy + scheduled data refresh
COORDINATION.md      shared task board for parallel sessions
REPO_REVIEW.md       line-by-line review of the repository at the base commit
```

## Running it locally

```bash
python3 engine/pipeline.py     # data/raw -> docs/data   (no network needed)
python3 engine/build_site.py   # docs/data -> docs/*.html
python3 -m http.server 8000 --directory docs
```

`engine/pipeline.py` uses the standard library only — no install step.
`engine/fetch_official.py` re-fetches the official sources; it is optional and
the committed snapshots are sufficient to rebuild the site.

## Coordination between sessions

Read `COORDINATION.md` first. It carries the task board (status, owning session,
file scope), the handoff rule for stale claims, and the log. Claim a task by
writing your session ID into the Owner column and committing immediately; keep
file scopes disjoint; run `git pull --rebase` before every push.

## Sources and attribution

Every table row on the site links to the official page or PDF it came from:
nba.com, official.nba.com and the league's own injury-report PDFs. The
underlying data is © NBA. This project is not affiliated with or endorsed by the
National Basketball Association.

## A caution worth repeating

The word **edge** on this site means the gap between the originated line and a
naive reference model — not edge against a sportsbook. No book price is
published by an NBA-operated source, so none is linked and none is used. Until
real prices are logged, nothing here can be called profitable.
