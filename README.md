# NBA Edge Lab

A static, evidence-first NBA research workspace. It distinguishes official-source observations from hypotheses and missing data. **No originated betting lines, picks, player-minute projections, correlations, leaderboard results, or skill claims are published**, because odds/history/model evidence is not present.

## Start here

- [Root decision dashboard](index.html) — executive overview and research framework.
- [Official-source snapshot dashboard](docs/index.html) — a dated 13–15 November 2026 schedule and 13 November 2026 12:00 PM ET injury-report transcription, with source links and flags. This is an archival snapshot, not a live feed.
- [Strategy lab](research.html) — single-bet, player-prop, combo and parlay hypotheses; validation gates and correlation reporting design.
- [Upcoming slate shell](slate.html) — requested maximum 72-hour horizon. The static page is a template; it does not automatically refresh.
- [Questions and suggestions](suggestions.html) — knowns, missing information and recommended discovery paths.
- [Flagged for review](review.html) — unresolved capabilities, sources and values.
- [Source register](sources.html) — official sources used in the static framework.
- [Coordination / audit log](COORDINATION.md).

## Data and evidence limits

- The `docs/` snapshot displays games and injury-report fields copied from official NBA pages/PDFs as of the dates stated on those pages. Injury rows with absent or ambiguous source text are flagged; do not assume a printed status predicts minutes or production.
- A matchup value inferred from schedule context is not an official injury-report field; the data owner has been asked to leave such values blank and flag them, consistent with the no-inference rule. See `COORDINATION.md`.
- There is no connected live NBA schedule or injury feed, licensed sportsbook quote feed, historical odds dataset, verified player-minute history, prediction service, backtest, or correlation sample here.
- A blank/em dash means unavailable or unverified, never zero. Source links document provenance only; they do not establish a betting edge.
- Candidate signals and validation gates are proposals, not proven strategies or betting recommendations.

## Rebuild and verify

- `python3 scripts/build_site.py` regenerates the official-source pages in `docs/` from `data/*.json` and applies that session's source/link checks. It is owned by the data/site session; follow the ownership note in `COORDINATION.md` before changing its source data.
- `python3 scripts/check_site.py` checks root and additional static pages for existing local links and at least one official NBA/GitHub source per table row.
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

The main branch's coordination history records a successful prior deployment at <https://wingbangboozle1-lang.github.io/NBA1/>. This branch's additions are not live until its PR is merged and the post-merge Pages workflow succeeds. Do not treat the earlier deployment status as confirmation of the updated site.
