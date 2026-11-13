# Repo Review — line-by-line verification

Session branch: `arena/c7fbc064-nba1` · Reviewed: 2026-11-13

## 1. Starting state

The repository at base commit `f73edd2` contained a single file:

- `README.md` — the single line `# NBA1`.

There was no code, no data, no site, and no `COORDINATION.md`. The project was greenfield.

## 2. Repo structure after work

```
NBA1/
├── README.md                      # project overview
├── COORDINATION.md                # shared task board (required by the brief)
├── requirements.md                # full numbered requirements spec
├── .gitignore
├── data/                          # verified seed data + derived outputs
│   ├── standings_2026_27.json     # VERIFIED — Basketball-Reference
│   ├── slate_upcoming.json        # VERIFIED — NBA.com schedule
│   ├── results_2026_11_12.json   # VERIFIED — Basketball-Reference
│   ├── correlations.json          # derived (inputs verified)
│   ├── lines.json                 # derived (originated)
│   ├── picks.json                 # derived (originated)
│   ├── strategies.json            # derived
│   ├── leaderboard.json           # derived
│   └── injuries.json              # derived (injury inputs flagged)
├── src/nba1/                      # the engine (no manual input)
│   ├── __init__.py
│   ├── model.py                   # originated lines + correlation
│   ├── strategies.py              # strategies + gates + skill/luck
│   ├── injuries.py                # rotation/production + game flow
│   └── run.py                     # orchestrator
├── tools/build_site.py            # generates the docs/ site from data/
├── docs/                          # GitHub Pages site (landing + subpages)
│   ├── assets/style.css
│   └── *.html
└── verification/                  # this review + sources + log
```

## 3. Line-by-line verification method

Every data value was checked against an official, trusted source before being
recorded. The two official sources used are:

- **Basketball-Reference (Sports Reference)** — standings, schedule, box scores.
  https://www.basketball-reference.com/
- **NBA.com** — schedule, stats portal, injury report. https://www.nba.com/

Verification rule applied throughout: **if a value could not be confirmed from
an official source, it was left blank and flagged unverified — never inferred.**

## 4. Verified values and their sources

| Data | Values verified | Official source |
|------|-----------------|-----------------|
| 2026-27 season | Season label, Emirates NBA Cup group stage | [NBA.com schedule](https://www.nba.com/schedule) |
| Standings (all 30 teams) | W, L, W/L%, PS/G, PA/G, SRS | [Basketball-Reference 2026-27 standings](https://www.basketball-reference.com/leagues/NBA_2027_standings.html) |
| Season leaders | PPG Luka Dončić 38.6 · RPG Karl-Anthony Towns 13.5 · APG Nikola Jokić 9.0 · WS Victor Wembanyama 2.6 | [Basketball-Reference standings page](https://www.basketball-reference.com/leagues/NBA_2027_standings.html) |
| Upcoming slate (Nov 13–16) | 9 + 5 + 9 + (8 count) games, matchups, times, arenas, NBA Cup groups | [NBA.com schedule](https://www.nba.com/schedule) |
| Recent completed slate (Nov 12) | 4 games, final scores, quarter scores, box-score leaders | [Basketball-Reference Nov 12 boxscore index](https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=12&year=2026) |

## 5. Irregularities flagged

1. **Leader "A. Davis" listed with Washington (WAS)** in the 2026-11-12
   DET@WAS box score — a star-caliber player on an unexpected team. Recorded
   as-is from the source and flagged for roster/trade review before relying on
   production projections.
   [box score](https://www.basketball-reference.com/boxscores/202611120WAS.html)
2. **Basketball-Reference boxscore index shows "No games played" for future
   dates** — it lists only completed games. Scheduled (not-yet-played) games
   were therefore taken from NBA.com, not BBR.
   [Nov 13 index](https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=13&year=2026)
3. **Spread edge is structurally near-zero** — our originated spread equals the
   model's expected margin, so cover probability is ~0.5 by construction. Real
   spread edges require a verified market line (not available in this session).
4. **Live injury statuses, live odds, and per-player stats are unverified** —
   left blank and flagged; see [Flagged for Review](../docs/flagged.html).

## 6. Code review notes

- `src/nba1/*` is pure-Python, dependency-free, and runs end-to-end with
  `python3 src/nba1/run.py`. It reads only the verified seed data in `data/`.
- `tools/build_site.py` regenerates the entire `docs/` site from `data/*.json`,
  so the site and data can never drift out of sync.
- All internal links and asset links were checked (no broken links).
- Every data table row in the site carries a `Source` column linking to the
  official source backing that row.
