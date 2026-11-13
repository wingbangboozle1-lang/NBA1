# NBA1

Originate our own NBA lines, build validated, skill-based betting strategies,
and generate picks for every upcoming slate up to 3 days in advance — with a
live GitHub Pages dashboard and full line-by-line verification against official
sources.

## What it does

- **Originates lines** — spreads, totals, and player props from a simple-rating
  model using verified team scoring/defense (not copied from a sportsbook).
- **Builds strategies** — single bet, parlay, and player-prop combos, each
  passing four validation gates (edge, sample size, correlation, skill).
- **Removes luck** — hit rates are Bayesian-shrunk toward 0.5 and tested for
  significance, so small-sample results are not over-credited.
- **Determines correlation values** — Pearson correlation among verified team
  metrics; parlay legs are correlation-gated.
- **Generates picks** — for every game in the 3-day advance window, from our
  originated lines.
- **Tracks injuries & game flow** — injury → rotation minutes → production
  model, plus game-flow analysis (live injury statuses flagged unverified).
- **Leaderboard** — ranks strategies by luck-adjusted skill with reward tiers.

## Repo layout

- `src/nba1/` — the engine (no manual input). Run `python3 src/nba1/run.py`.
- `data/` — verified seed data + derived outputs (all JSON).
- `tools/build_site.py` — regenerates the `docs/` site from `data/`.
- `docs/` — the GitHub Pages site (landing + subpages).
- `verification/` — repo review, sources, and verification log.
- `COORDINATION.md` — shared task board.
- `requirements.md` — full numbered requirements spec.

## Build & regenerate

```bash
python3 src/nba1/run.py       # regenerate derived data in data/
python3 tools/build_site.py   # regenerate the docs/ site
```

## Sources & verification

Every data table row links to the official source it was verified against
(Basketball-Reference and NBA.com). Unverifiable values are left blank and
flagged — never inferred. See `verification/sources.md` and the site's
**Sources** and **Flagged for Review** pages.

## Live site

Published via GitHub Pages from the `docs/` directory. See `COORDINATION.md`
for the deploy record.
