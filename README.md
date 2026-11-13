# NBA Edge Lab

A static, evidence-first dashboard prototype for researching independent NBA lines. It makes data gaps explicit and outlines test gates for single bets, parlays, player props and combos. It does **not** generate picks: this repository currently has no connected data feed, historical prices, results, model, or validated strategy.

## Preview locally

Open `index.html` in a browser, or serve the directory with any static file server. No build step or dependency installation is required.

## GitHub Pages

The site is plain static HTML/CSS/JS and can be served from the repository root via GitHub Pages. Repository settings/workflow configuration and a successful deployment must be checked in GitHub; this checkout alone does not prove that the site is published. See the flagged review section on the site (F-08).

## Research and evidence policy

- A blank/em dash means unverified or unavailable; it is never a zero or inferred value.
- Each reported research row links to an official NBA reference page. Those pages document NBA schedules/statistics/injury-report access, not a model edge or historical bookmaker odds.
- No current slate, line, player status, rotation forecast, probability, correlation, ROI or leaderboard result is represented as verified.
- Do not treat a candidate feature or validation protocol as a proven strategy or betting advice.

## Official references

- [NBA Stats glossary](https://www.nba.com/stats/help/glossary) — official definitions for NBA statistics.
- [NBA Stats FAQ](https://www.nba.com/stats/help/faq) — NBA Stats data/metric context.
- [NBA team advanced statistics](https://www.nba.com/stats/teams/advanced).
- [NBA player statistics](https://www.nba.com/stats/players).
- [NBA schedule](https://www.nba.com/schedule).
- [NBA Communications injury report page (2026–27)](https://official.nba.com/nba-injury-report-2026-27-season/) — season-specific official reporting reference; not an ingested live feed.

## Verification

Static navigation targets and table row links were checked against the HTML; local serving and HTTP response are validated as part of this task. Verify external links and Pages deployment in the browser/GitHub before relying on them. Official-source URLs do not certify that a value is current or have been copied into the site.

## Official-source research dashboard (`docs/`)

Added by session `arena-83ba89cf`. A multi-page static site built from `data/*.json`:

- Schedule for Nov 13–15, 2026 (23 games) from NBA.com games pages.
- Injury rows (75) from the official 11/13/26 12:00 PM injury-report PDF, with rows that lack a printed reason or team flagged or excluded.
- Strategies, validation gates, questions, suggestions, flagged items, and sources.

Rebuild: `python3 scripts/build_site.py`. The build fails on any data row without an official source link, on a disallowed host, or on a broken internal link. No picks, correlation values, or leaderboard results are produced. The required verified inputs are missing (see the Questions page).

Pages URL for this section: https://wingbangboozle1-lang.github.io/NBA1/docs/
