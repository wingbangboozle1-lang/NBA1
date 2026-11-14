# NBA1

A research workspace for **originating NBA lines** and testing whether the
resulting signal is skill or luck. It produces its own spread, total and
moneyline from official NBA data, runs a library of strategies against a
strictly out-of-sample window, and publishes every gap it cannot close.

The live site is published by GitHub Pages from the repository root:
**<https://wingbangboozle1-lang/NBA1/>**

---

## The site

| Section | Page | What it holds |
| --- | --- | --- |
| Overview | [`index.html`](index.html) | Landing page: horizon at a glance, executive summary, status tiles, category index |
| Horizon | [`site/pages/picks.html`](site/pages/picks.html) | Originated lines for every game 14–17 Nov 2026, and the gated paper picks |
| Horizon | [`site/pages/props.html`](site/pages/props.html) | Player projections and prop combinations, with minutes coverage stated |
| Horizon | [`site/pages/injuries.html`](site/pages/injuries.html) | The official injury report, rotation minutes and measured production impact |
| Horizon | [`site/pages/gameflow.html`](site/pages/gameflow.html) | Pace, expected margin and total, blow-out and overtime probability, rest context |
| Evidence | [`site/pages/strategies.html`](site/pages/strategies.html) | Ten strategies, reward tiers, leaderboard |
| Evidence | [`site/pages/validation.html`](site/pages/validation.html) | The seven gates, the gate matrix, the out-of-sample metrics |
| Evidence | [`site/pages/correlations.html`](site/pages/correlations.html) | Measured correlations, model-derived ones, the parlay rho table |
| Evidence | [`site/pages/luck.html`](site/pages/luck.html) | Luck decomposition: expected wins vs actual, per team |
| Evidence | [`site/pages/backtest.html`](site/pages/backtest.html) | The 51-game out-of-sample window, game by game |
| Evidence | [`site/pages/model.html`](site/pages/model.html) | Team ratings and every model assumption |
| Verification | [`site/pages/source-check.html`](site/pages/source-check.html) | Every horizon game and every 11/13 final compared with NBA.com on 2026-11-14, the 11/13 settlement, and the conflicts between builds |
| Decision | [`site/pages/questions.html`](site/pages/questions.html) | Answered and open questions |
| Decision | [`site/pages/suggestions.html`](site/pages/suggestions.html) | Improvements as options with effort, risk and what each unlocks |
| Decision | [`site/pages/flagged.html`](site/pages/flagged.html) | Everything that could not be confirmed from an official source |
| Decision | [`site/pages/sources.html`](site/pages/sources.html) | The source register: 63 official URLs |
| Decision | [`site/pages/repo-review.html`](site/pages/repo-review.html) | Line-by-line repository review, irregularities, verification log |

### The rule the whole site runs on

Every table row links to the official source it came from. A value that could
not be confirmed from an official source is rendered as an em dash, marked
*not published*, and listed on **Flagged for Review**. Nothing is inferred,
and no blank cell is ever quietly filled in.

### The honest headline

As of this build **no strategy has cleared the skill gate**. The best one is
16-7, worth +7.55 model units, with an exact binomial p-value of 0.093 and a
Wilson lower bound of 0.491 against a 0.524 break-even. It is inside what luck
alone produces, so every strategy is capped at a quarter unit or held back as
research-only. That is the result, reported rather than worked around.

No sportsbook price is used anywhere, because no NBA-operated source publishes
one. "Edge" on this site means the originated model against a deliberately
naive reference model built from the same official ratings. It does **not** mean
an edge against a book, and no pick is described as market-validated.

---

## Every build in this repository

Five implementations of the same brief live here. All are preserved and all
are online, so the audit trail stays intact. They read the same official
captures and differ in presentation, data cut, and how much of the pipeline
they exercise:

| Build | Entry point | Horizon | Character |
| --- | --- | --- | --- |
| **Build D — this build** | [`index.html`](index.html) → [`site/`](site/pages/picks.html) | 27 games, 14–17 Nov | The current build: landing page, 15 category pages, 63 paper picks |
| **Command Center** | [`command-center/index.html`](command-center/index.html) | 22 games, 14–16 Nov | A second consolidated site, built in session `arena/791c9114-nba1` from the same captures, with its own rendered-page checks |
| **A — NBA Edge Lab** | [`edge-lab/index.html`](edge-lab/index.html) | 23 games, 13–15 Nov | Build A's original decision dashboard, frozen at the 11/13 cut and archived unchanged |
| **Integration Desk** | [`desk.html`](desk.html) | 14–16 Nov | The origination, gate, settlement and prop pipeline published at the repository root by session `arena/2edb85af-nba1` |
| **A — dated NBA snapshot** | [`docs/index.html`](docs/index.html) | 13–15 Nov | The dated official schedule and 12:00 PM injury-report transcription, source-linked |
| **B — Line Origination Desk** | [`docs/b/index.html`](docs/b/index.html) | — | The earlier backtested build: 51 out-of-sample games, ten strategies, seven gates |

The root `index.html` is a **switcher**: it links every one of them, so no
build is hidden and none is deleted.

Also live: [`schedule-verified.html`](schedule-verified.html) (row-by-row
schedule check and its flags), [`verification.html`](verification.html) (the
official-source reachability probe) and [`review.html`](review.html) (the
earlier build's flagged register).

---

## Rebuild and verify

```bash
python3 engine/pipeline.py       # captured snapshots  -> docs/data/*.json
python3 engine/build_site.py     # docs/data/*.json   -> docs/b/pages/*.html
python3 scripts/build_dashboard.py # docs/data/*.json -> index.html + site/**
python3 scripts/verify_all.py    # the whole gate, end to end
```

`verify_all.py` runs both earlier builders, the dashboard builder, the
row/link/source audits for every build, and fails on the first problem. The
current run reports **0 broken internal links**, **0 table rows without a
source link**, and `VERIFY OK`.

Supporting scripts:

| Script | Purpose |
| --- | --- |
| `scripts/build_dashboard.py` | Generates the unified site |
| `scripts/verify_dashboard.py` | Every row source-linked, every link resolves, every row's column count matches its header |
| `scripts/verify_all.py` | The end-to-end gate |
| `scripts/verify_integration.py` | Repository-wide audit: every JSON, every HTML page, every link, every data row's source |
| `scripts/originate_lines.py`, `scripts/strategies.py`, `scripts/compute_correlations.py`, `scripts/injury_impact.py`, `scripts/backtest.py` | The earlier build's pipeline |
| `scripts/verify_data.py`, `scripts/verify_inline.py`, `scripts/check_site.py`, `scripts/check_links.py`, `scripts/verify_schedule_c.py` | The earlier build's audits |

These are structural checks. They do not verify that an external source stays
available, that the data may be used, or that any model result is correct.

---

## Official reference links

- [NBA Schedule](https://www.nba.com/schedule) · [NBA Games & Scores](https://www.nba.com/games)
- [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced) · [Players Traditional](https://www.nba.com/stats/players/traditional)
- [NBA Stats glossary](https://www.nba.com/stats/help/glossary) · [FAQ](https://www.nba.com/stats/help/faq)
- [NBA official injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/)
- [NBA Cup 2026](https://www.nba.com/nba-cup/2026)
- [NBA Rule No. 5: Scoring and Timing](https://official.nba.com/rule-no-5-scoring-and-timing/)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

---

## Start here

**[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** is the one-document picture: what was
verified and how, what the model has and has not shown, the limits that matter, and the
seven decisions waiting on a reviewer before anything else can sensibly proceed. It is also
linked from every page of the site.

## Known limits

- **Resolved 2026-11-14.** The nine 2026-11-13 games are Final. They were read from
  <https://www.nba.com/games?date=2026-11-13>, transcribed independently by two
  sessions that agree 9/9, and used to settle the nine published 11/13 lines
  (3 WIN, 4 LOSS, 2 NO BET) and to refresh the 29 stale team records on the horizon
  rows. `scripts/verify_horizon_s934ca56f.py` reports 0 record mismatches against
  NBA.com. Flags F13, F14 and F29 are closed on
  [Flagged for Review](site/pages/flagged.html).
- **Still open: the ratings window ends at 2026-11-12.** The 11/13 finals have not
  been fed back into the model's team ratings, so every originated line still rests
  on ratings one night short (flag F19). This is the single most important limit on
  the lines themselves.
- At the newest official injury-report edition (11/13/26 07:30 PM ET), five of
  the ten teams playing on 11/14 had not filed, and no edition covers the games
  on 11/15–11/17. Those lines carry no injury adjustment and say so.
- Player minutes are known for 50 of the 465 players in the official Players
  Traditional table, so the availability impact is a measured lower bound.
- There is no live NBA feed, licensed odds feed, verified game-log history or
  prediction service in this repository.
- A blank or an em dash means unavailable or unverified. It never means zero.

See [`COORDINATION.md`](COORDINATION.md) for the task board, the build log and
the publish record.

---

## NBA Line Origination Desk — `origination/`

Session `arena/e32856d8-nba1`. A self-contained build that lives in one
namespace and touches nothing else in the repository.

Live: <https://wingbangboozle1-lang.github.io/NBA1/origination/>

It originates its own spreads, totals and moneylines from one input — the
official final scores published by NBA.com — then runs a leaderboard
competition in which every strategy must beat that originated line using
information the line itself does not use.

**No strategy is funded.** 39 cells across singles, parlays, same-game parlays
and prop combos; only 4 reach the 25-bet floor. The best cell returns 27.3% ROI
on 11 bets against a luck line of 45.5%, and the minimum detectable ROI at 80%
power is 85.2%. The one live signal (rest-day differential, +2.82 points per
day, p = 0.130) needs about 340 games; there are 101 today.

| Page | What it shows |
| --- | --- |
| `origination/index.html` | Executive dashboard: six findings, the three-day slate, standing limitations |
| `pages/lines.html` | 22 originated lines for 2026-11-14 to 11-16 |
| `pages/gameflow.html` | Rest, back-to-backs, schedule density, per-game injury counts, team form |
| `pages/strategies.html` | The 39-cell strategy library and what each one claims |
| `pages/leaderboard.html` | Every cell ranked, with its reward tier and stake |
| `pages/gates.html` | The seven conjoined gates and every cell against each one |
| `pages/luck.html` | Monte-Carlo nulls, luck lines and statistical power |
| `pages/signals.html` | Does the signal carry information the line missed? |
| `pages/teams.html` | Ratings, and the shrinkage sensitivity that justifies them |
| `pages/backtest.html` | All 101 walk-forward forecasts, each fitted only on earlier games |
| `pages/gamelog.html` | All 151 verified final scores, plus the 23 games published without scores |
| `pages/correlations.html` | Measured correlations and what they mean for parlay pricing |
| `pages/method.html` | Exactly how each number is produced |
| `pages/injuries.html` | Official participation status, and what cannot be sized |
| `pages/props.html` | Why player props are blocked rather than approximated |
| `pages/questions.html` | 14 decisions blocked by missing information |
| `pages/suggestions.html` | 12 ranked options, none implemented |
| `pages/sources.html` | The source register |
| `pages/flagged.html` | 12 items flagged for review |
| `pages/repo-review.html` | The line-by-line repository review |

Verification: 151 captured scores + 23 unpublished fixtures = 174 = the sum of
official wins, and per-team game counts match for all 30 teams. 913 data rows
across 27 tables, every one carrying an official-host link. 0 broken internal
links across all 93 HTML files. No value is inferred: a number that cannot be
confirmed from an official page is left blank and flagged.

```
python3 -m engine_v2.pipeline      # rebuild every number
python3 -m engine_v2.build_site    # rebuild every page
python3 -m engine_v2.check_site    # links, hosts, row provenance, placeholders
```

Files owned by this build: `origination/**`, `engine_v2/**`, `data/official/**`,
`REVIEW_2026-11-14.md`. No root `*.html`, no `.github/`, no `docs/`, no
`command-center/`, no `integration/`, no `engine/`, no `scripts/`.
