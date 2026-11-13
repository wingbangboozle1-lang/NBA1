# NBA Edge Lab

A static, evidence-first dashboard prototype for researching independent NBA lines. It makes data gaps explicit and outlines test gates for single bets, parlays, player props and combos. It does **not** generate picks: this repository currently has no connected data feed, historical prices, results, model, or validated strategy.

## Preview locally

Open `index.html` in a browser, or serve the directory with any static file server. No build step or dependency installation is required.

## Dashboard and research pages

- [Executive dashboard](index.html) — summary, signal research, validation, correlation, injury/game-flow, leaderboard, questions, suggestions and review flags.
- [Strategy lab](research.html) — candidate single, prop, combo and parlay tests; proposed validation gates and correlation ledger.
- [Upcoming slate](slate.html) — target rolling window up to 72 hours; no game rows are populated until an official schedule feed is implemented.
- [Questions and suggestions](suggestions.html) — knowns, missing information and proposed discovery path.
- [Flagged for review](review.html) — unresolved evidence and operational gaps.
- [Source register](sources.html) — official source links, scope notes and verification method.

## GitHub Pages

The site is plain static HTML/CSS/JS and can be served from the repository root via GitHub Pages. Repository settings/workflow configuration and a successful deployment must be checked in GitHub; this checkout alone does not prove that the updated site is published. See the flagged review section on the site (F-09).

## Research and evidence policy

- A blank/em dash means unverified or unavailable; it is never a zero or inferred value.
- Each reported research row links to an official NBA reference page. Those pages document NBA schedules/statistics/injury-report access, not a model edge or historical bookmaker odds.
- No current slate, line, player status, rotation forecast, probability, correlation, ROI or leaderboard result is represented as verified.
- Do not treat a candidate feature or validation protocol as a proven strategy or betting advice.
- Predictions must remain disabled until authorized, timestamped data and market feeds, reproducible out-of-sample evidence, and operational controls are in place.

## Official references

- [NBA Stats glossary](https://www.nba.com/stats/help/glossary) — official definitions for NBA statistics.
- [NBA Stats FAQ](https://www.nba.com/stats/help/faq) — NBA Stats data/metric context.
- [NBA team advanced statistics](https://www.nba.com/stats/teams/advanced).
- [NBA player statistics](https://www.nba.com/stats/players).
- [NBA schedule](https://www.nba.com/schedule).
- [NBA official injury report page (2026–27)](https://official.nba.com/nba-injury-report-2026-27-season/) — season-specific official reporting reference; not an ingested live feed.
- [NBA Rule No. 5](https://official.nba.com/rule-no-5-scoring-and-timing/) — official scoring/timing provisions.
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Verification

`python3 scripts/check_site.py` checks that project pages exist, local links resolve, and each table row includes an official NBA/GitHub source link. `git diff --check` checks whitespace. These structural checks do not verify every external page's continued availability, data completeness, licensed use, or any model result. Official-source URLs do not certify that a value is current or copied into the site.
