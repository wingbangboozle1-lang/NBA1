# NBA1

Research dashboard for NBA games: official schedule and injury data, validation framework, questions, suggestions, and flagged items.

Live site (GitHub Pages, from `main` → `/docs` once merged): https://wingbangboozle1-lang.github.io/NBA1/

## What is in here

- `data/*.json` — the data behind every table. Each row carries an official source link.
- `scripts/build_site.py` — builds the static site in `docs/` and fails on missing source links, disallowed hosts, or broken internal links.
- `docs/` — generated site (published by GitHub Pages).
- `COORDINATION.md` — task board, sources, verification, and the integration log.

## Rebuild

```bash
python3 scripts/build_site.py
```

## Status

- Schedule (Nov 13–15, 2026) and the 11/13 12:00 PM injury report are included with sources.
- Strategies, correlation values, originated lines, and picks are **not** produced. The required verified inputs are missing (see the Questions page).
- Nothing here is betting advice. Gambling in NL is regulated by the Kansspelautoriteit (Ksa).
