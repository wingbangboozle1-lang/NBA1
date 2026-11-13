# NBA Lines Lab

A source-first NBA forecasting and bet-validation dashboard concept. The repository currently has no historical data, live schedule feed, injury ingestion, sportsbook odds feed, or prediction service; consequently it publishes **no current lines, picks, injury impacts, correlations, win probabilities, or performance claims**. Unknown numeric fields are intentionally blank and identified as unverified.

## Project

- **Executive summary and current-state assessment:** [`index.html`](index.html)
- **Model and validation design:** [`research.html`](research.html)
- **Upcoming slates (data intentionally blank):** [`slate.html`](slate.html)
- **Decision questions and improvement proposals:** [`suggestions.html`](suggestions.html)
- **Flagged/unverified items:** [`review.html`](review.html)
- **Shared source register:** [`sources.html`](sources.html)
- **Task board and verification notes:** [`COORDINATION.md`](COORDINATION.md)

## Run locally

Open `index.html` in a browser. No build step, package install, network call, or API key is required. All pages are plain static HTML/CSS/JavaScript.

## Publish with GitHub Pages

The included GitHub Actions workflow builds/publishes the repository root when changes reach `main` (or when manually dispatched). In GitHub, Pages must be enabled with **GitHub Actions** as its deployment source. A successful workflow run is required before claiming the site is live. This session cannot truthfully assert that Pages is enabled or deployed without checking the repository's Pages deployment status.

## Data integrity rules

1. NBA schedule, stats, and injury report rows link directly to official NBA sources.
2. A source link establishes the provenance of an input; it does **not** itself establish predictive value or a betting edge.
3. Do not infer missing values. Unavailable or unverified values remain blank, are marked, and appear on Flagged for Review.
4. Estimates must be time-stamped and reproducible with source snapshot, season, filters, model version, and market quote timestamp.
5. Strategy results must be out-of-sample and compared with explicit baselines before being ranked or rewarded.

## Important limitation

This is a research and governance shell, not a live wagering product. No current sportsbook prices or official NBA data are pulled into the static site. Predictions should remain disabled until an authorized data pipeline, historical snapshots, market inputs, validation evidence, and operational controls are implemented and independently checked.
