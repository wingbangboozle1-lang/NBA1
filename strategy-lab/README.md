# strategy-lab — the season-wide skill audit

Everything in this directory is read-only with respect to the rest of the repository: it reads committed
official captures and writes only inside `strategy-lab/`. It exists because every published verdict in
this project has been reached on a 51-game window (2026-11-06..11-12), the only window a point-in-time
team rating was ever captured for — while the repository already holds **160 scored games**, every one of
them transcribed from `nba.com/games`.

## Run it

```bash
python3 strategy-lab/run.py       # recomputes data/*.json   (deterministic, stdlib only, seed 20261114)
python3 strategy-lab/build.py     # renders index.html and pages/*.html from that JSON
python3 strategy-lab/check.py     # the repository's own page gates, applied to this directory
```

No network access at run time. A clean checkout at the commit stamped in each page footer reproduces every
table. Nothing here is a build step for `site/**`; folding it into the site nav is cross-session request
R-29-6 in `COORDINATION.md`.

## The verdict, in three sentences

1. The season game log is complete **for published scores** and its 23 missing results are games the official
   page prints as FINAL with an empty score cell; three independent official instruments now prove that, and
   no score was inferred.
2. Putting a back-to-back penalty of 6.096 points into every line is not supported: the season measures the
   same effect at **+0.016 ± 4.426** points on 144 games.
3. Across a 13-strategy library graded **against the probability the originated line itself implied**, nothing
   beats it — best case +3.84 wins on 58 plays (z 1.14, exact Poisson-binomial p 0.160, Benjamini-Hochberg
   q 0.639), and a shared-draw simulation shows a pure-luck library of the same size reaches that best on
   essentially every draw. The rating underneath does have skill (margin MAE 12.87 vs 14.31 naive, Brier
   skill 0.142, AUC 0.730); no overlay on top of it does.

## Files

| file | what it is |
| --- | --- |
| `statools.py` | exact statistics with no scipy: Poisson-binomial tails by dynamic program, exact binomial p-values, Wilson intervals, Benjamini-Hochberg, moving-block bootstrap, OLS with a numerically integrated t-density |
| `labdata.py` | the one schedule layer every module shares: 160 scored + 23 fixture + 27 unplayed games, plus the rest lookup with and without the fixture list |
| `backfill.py` | module 1 — completeness proof on three official instruments |
| `restaudit.py` | module 2 — rest and back-to-back recomputed on the complete schedule, and the `rest_days` definition conflict |
| `tournament.py` | module 3 — the walk-forward library: 13 rules, every play graded against the model's own probability, luck controls |
| `correlations.py` | module 4 — measured effects and correlations replacing assumed ones |
| `impact.py` | module 6 — what the parameter decision is worth, game by game, on the 27 unplayed games |
| `gates.py` | module 5 — the seven gates, the reward tiers, and the audit of the site's published probabilities |
| `content.py` | the question, suggestion and flag register that `pages/decision.html` renders |
| `build.py` | the renderer: token templates, no client-side JavaScript, and rules that make a source-linked table the default rather than an afterthought |
| `check.py` | this directory's gate check: link resolution, approved hosts, one official link per row, rectangular tables, no sentinel text |
| `data/*.json` | the numbers themselves, one file per module |
| `pages/*.html` | the readable version of those numbers |

## Reading the tables

* **Excess** is the only quantity here that corresponds to a decision: wins minus the wins the originated
  line already expected. A raw hit rate is also shown, and is exactly what it looks like — betting heavy
  favourites wins often and pays almost nothing for it.
* **Exact p** is a Poisson-binomial tail over each play's own probability, not a normal approximation and
  not a coin flip.
* A value the official page did not publish is printed as an em dash. It never means zero, and it is never
  filled in from an adjacent quantity.
* `GG`, the market gate, is **blocked for the whole repository**: no NBA-operated source publishes a closing
  price. Nothing here claims a market edge, and no strategy can be marked funded until R-29-7 is resolved.
