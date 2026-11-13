# NBA1 — Full Requirements List

The project brief was converted into a numbered, verifiable requirements spec.
Status is recorded per item. Verification sources are listed per item.

| ID | Requirement | Status | How it is met | Verification source |
|----|-------------|--------|--------------|---------------------|
| R1 | Collect, organize, and analyze NBA data against a full list of requirements. | done | This spec; data captured into `data/*.json`; engine in `src/nba1`. | Basketball-Reference / NBA.com |
| R2 | Originate our own NBA lines (not copy a book's line). | done | Simple-rating model originates spread + total + player props from verified PS/G & PA/G. | Basketball-Reference standings |
| R3 | Research & develop strategies that generate useful signals. | done | Six strategies across single bet, parlay, and player-prop combos. | Model + verified standings |
| R4 | Leaderboard competition with rewards for top-performing strategies. | done | Leaderboard ranks by luck-adjusted skill; reward tiers defined. | Model |
| R5 | Cover single bet, parlays, and player-prop bet combos. | done | S1–S4 single; S5 two-team parlay; S6 player-prop + team parlay. | Model |
| R6 | Each strategy must pass validation gates. | done | Four gates: edge, sample size, correlation, skill significance. | Model |
| R7 | Determine correlation values. | done | Pearson correlation matrix on verified team metrics. | Basketball-Reference standings |
| R8 | Remove luck; build selectively skill-based strategies. | done | Bayesian shrinkage of hit rate toward 0.5; z-score significance gate. | Model |
| R9 | Generate picks for every upcoming slate up to 3 days in advance using originated lines. | done | Picks generated for 2026-11-13..16 from originated lines. | NBA.com schedule + model |
| R10 | Track injuries affecting rotation minutes & production; game-flow analysis. | needs review | Game-flow computed from verified inputs; live injury statuses unverified (blank + flagged). | NBA.com injury report (flagged) |
| R11 | Executive summary outlining important details. | done | `docs/summary.html` + `verification/`. | — |
| R12 | Suggestions to improve the site for decision-making; dedicated review section. | done | Suggestions section with review workflow. | — |
| R13 | Clear list of questions / information / answers needed before decisions; suggestions to discover missing info. | done | Questions & Answers register. | — |
| R14 | No manual input; work autonomously. | done | Pipeline fully scripted: data → model → picks → site. | — |
| R15 | Review the repo line by line; verify from official trusted sources; provide links; flag irregularities. | done | `verification/repo-review.md`; every row sourced; irregularities logged. | Basketball-Reference / NBA.com |
| R16 | GitHub Pages live site: clean landing + subpages by category, dashboard UI, tables with findings. | done | `docs/` dashboard landing + category subpages. | — |
| R17 | Verification: every table row has an official source link; unverifiable = blank + flagged; never infer. | done | All data tables include a Source column; unverified fields blank + flagged. | — |
| R18 | Coordinate via COORDINATION.md shared task board. | done | `COORDINATION.md` created; tasks claimed; deviations logged. | — |
| R19 | PR, merge, deploy to GitHub Pages, record results. | in progress | PR → merge → Pages deploy; result recorded in `COORDINATION.md`. | GitHub |

## Gate thresholds (model parameters, documented)

- **G1 Edge** — minimum model edge to fire a pick: **0.05**
- **G2 Sample** — minimum graded picks before ranking: **30**
- **G3 Correlation** — max absolute leg correlation for parlays/combos: **0.70**
- **G4 Skill** — significance bar (two-sided 95%): **z = 1.96**
- **Luck removal** — Bayesian shrinkage prior: **12** (hit rate pulled toward 0.5)
