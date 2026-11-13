# NBA1

Two independent implementations of the same brief live in this repository, both
published by GitHub Pages from the repository root. Neither was discarded; see
`COORDINATION.md` for how the collision was resolved.

| Build | Session | Entry point | Character |
| --- | --- | --- | --- |
| **A — NBA Edge Lab** | `arena-7cfd203a` | [`index.html`](index.html) | Research workspace: originated lines for the Nov 13–16 window, six conjoined validation gates, an official-injury impact and game-flow layer, and a dated official-source snapshot under [`docs/`](docs/index.html). |
| **B — Line Origination Desk** | `arena/91270bb6-nba1` | [`docs/b/index.html`](docs/b/index.html) | Backtested build: 51 out-of-sample games, a ten-strategy library with seven gates, measured correlations, a luck decomposition, and a leaderboard with reward tiers. |

Both are static HTML/CSS/JS with no build step at deploy time, and both follow
the same verification rule: every table row links to the official source it came
from, and a value that could not be confirmed is left blank rather than
estimated.

---

# NBA Edge Lab

A static, evidence-first NBA research workspace. It distinguishes official-source observations from hypotheses and missing data. The Edge Lab publishes **originated lines and paper model picks** (model RecordLine-1, assumptions flagged) for the Nov 13–16, 2026 window, plus an official-injury impact / game-flow layer. **No market-validated bets, player-minute projections, empirical correlation values, leaderboard results, or skill claims are published**, because odds/game-log evidence is not present — market gates stay blocked and unsettled results stay blank.

## Start here

- [Root decision dashboard](index.html) — executive overview and research framework.
- [Originated lines & picks](lines.html) — RecordLine-1 lines, gated paper picks, parlay cards with Fréchet correlation bounds, prop combos, gated leaderboard (Nov 13–16).
- [Injuries & game flow](gameflow.html) — official 11/13 5:15 PM ET report transcription, per-game impact context, rest/back-to-back matrix from the official schedule.
- [Official-source snapshot dashboard](docs/index.html) — a dated 13–15 November 2026 schedule and 13 November 2026 12:00 PM ET injury-report transcription, with source links and flags. This is an archival snapshot, not a live feed.
- [Strategy lab](research.html) — single-bet, player-prop, combo and parlay hypotheses; validation gates and correlation reporting design.
- [Upcoming slate shell](slate.html) — requested maximum 72-hour horizon. The static page is a template; it does not automatically refresh.
- [Questions and suggestions](suggestions.html) — knowns, missing information and recommended discovery paths.
- [Flagged for review](review.html) — unresolved capabilities, sources and values.
- [Source register](sources.html) — official sources used in the static framework.
- [Coordination / audit log](COORDINATION.md).

## Data and evidence limits

- The `docs/` snapshot displays games and injury-report fields copied from official NBA pages/PDFs as of the dates stated on those pages. Injury rows with absent or ambiguous source text are flagged; do not assume a printed status predicts minutes or production.
- `lines.html` model parameters (smoothing, home court, scale, pick gate) are this project's documented assumptions (flag E-01), not official values. Paper picks are not market-validated (E-02); team totals are not originated (E-03); unsettled record/ROI columns are blank, never zero.
- A matchup value inferred from schedule context is not an official injury-report field; the data owner has been asked to leave such values blank and flag them, consistent with the no-inference rule. See `COORDINATION.md`.
- There is no connected live NBA schedule or injury feed, licensed sportsbook quote feed, historical odds dataset, verified player-minute history, prediction service, backtest, or correlation sample here.
- A blank/em dash means unavailable or unverified, never zero. Source links document provenance only; they do not establish a betting edge.
- Candidate signals and validation gates are proposals, not proven strategies or betting recommendations.

## Rebuild and verify

- `python3 scripts/build_site.py` regenerates the official-source pages in `docs/` from `data/*.json` and applies that session's source/link checks.
- `python3 scripts/build_edge_site.py` regenerates the Edge Lab pages `lines.html` + `gameflow.html` (rest math, model RecordLine-1, parlays, props, injury impact) and writes the audit record `data/originated_lines.json`. It fails on any data row without an allowed official source host.
- `python3 scripts/check_site.py` checks root and additional static pages for existing local links and at least one official NBA/GitHub source per table row.
- `python3 scripts/verify_all.py` runs the full pipeline end-to-end (both builders + checker + row/link/source audits) — run it before any PR.
- `git diff --check` checks patch whitespace. These structural checks do not verify the external source's continued availability, data rights, timeliness, or any model results.

## Official reference links

- [NBA Stats glossary](https://www.nba.com/stats/help/glossary)
- [NBA Stats FAQ](https://www.nba.com/stats/help/faq)
- [NBA team advanced statistics](https://www.nba.com/stats/teams/advanced)
- [NBA player statistics](https://www.nba.com/stats/players)
- [NBA schedule](https://www.nba.com/schedule)
- [NBA official 2026–27 injury-report policy](https://official.nba.com/nba-injury-report-2026-27-season/)
- [NBA Rule No. 5: Scoring and Timing](https://official.nba.com/rule-no-5-scoring-and-timing/)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## GitHub Pages

The current integration merged in PR [#4](https://github.com/wingbangboozle1-lang/NBA1/pull/4). Post-merge Actions run [43520295487](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43520295487) passed validation and deployment; GitHub Pages reports the site as built at <https://wingbangboozle1-lang.github.io/NBA1/>. The schedule/injury section is still a dated snapshot, not a live feed.
