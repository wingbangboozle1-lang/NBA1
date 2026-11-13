# Verification Log

Per-task record of what was verified, against which official source, and any
irregularities. Recorded by session `c7fbc064-nba1` on 2026-11-13.

## Standings (data/standings_2026_27.json)

- **Checked:** All 30 teams — W, L, W/L%, GB, PS/G, PA/G, SRS.
- **Source:** https://www.basketball-reference.com/leagues/NBA_2027_standings.html
- **Result:** Verified. Captured East + West conference tables.
- **Irregularity:** None.

## Season leaders

- **Checked:** PPG Luka Dončić 38.6 · RPG Karl-Anthony Towns 13.5 ·
  APG Nikola Jokić 9.0 · WS Victor Wembanyama 2.6.
- **Source:** https://www.basketball-reference.com/leagues/NBA_2027_standings.html
- **Result:** Verified.

## Upcoming slate (data/slate_upcoming.json)

- **Checked:** 2026-11-13 (9 games), 11-14 (5), 11-15 (9), 11-16 (8 count,
  3 captured in detail). Matchups, times, arenas, NBA Cup groups.
- **Source:** https://www.nba.com/schedule
- **Result:** Verified for captured games.
- **Irregularity:** Basketball-Reference's boxscore index shows "No games
  played" for future dates (it lists only completed games), so the scheduled
  slate was taken from NBA.com instead. 5 of 8 Nov-16 games were not captured
  in detail — flagged for a live re-pull.

## Recent completed slate (data/results_2026_11_12.json)

- **Checked:** 4 games — final scores, quarter scores, box-score leaders.
- **Source:** https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=12&year=2026
- **Result:** Verified.
- **Irregularity:** Leader "A. Davis" listed with Washington (WAS) — a
  star-caliber player on an unexpected team; flagged for roster/trade review.

## Derived outputs

- **Correlations** — computed from verified standings inputs. Verified inputs;
  values are model-computed. Source: Basketball-Reference standings.
- **Originated lines** — model outputs from verified PS/G & PA/G. No market
  line compared (no verified odds source) — spread edges measured only against
  our own line. Flagged as a method limitation.
- **Picks** — generated from originated lines + verified schedule. Each pick
  links to NBA.com schedule + Basketball-Reference standings.
- **Strategies / leaderboard** — model logic; skill via Bayesian shrinkage.
- **Injuries / game-flow** — game-flow from verified inputs; live injury
  statuses unverified (blank + flagged). Source for injuries: NBA.com injury
  report (flagged).

## Site link check

- All internal `*.html` links resolve to existing files.
- All `assets/style.css` links resolve.
- No `None` values or unfilled placeholders in rendered HTML.

## Summary of unverified / flagged items

See `docs/flagged.html` (Flagged for Review page) for the full list with
source links: live injury statuses, live odds, per-player stats, Nov-16
detail, the A. Davis roster irregularity, the BBR future-date behavior, and
the spread-edge method limitation.
