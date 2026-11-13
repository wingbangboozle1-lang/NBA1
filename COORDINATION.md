# COORDINATION — Shared Task Board

Repo: `wingbangboozle1-lang/NBA1`
Current session branch: `arena/c7fbc064-nba1` (base: `f73edd2` of `main`)
Session ID: `c7fbc064-nba1`
Status convention: `unclaimed` · `in progress` · `needs review` · `done`

## Session / branch note

This environment tracks the session by its branch, so all work for this session is committed
directly on `arena/c7fbc064-nba1` (per the branch-tracking requirement) rather than on separate
`session-<id>/<task>` branches. There is a single active session in this environment, so there is
no cross-session conflict risk. File scopes below are still kept non-overlapping by area so any
future session can pick a task cleanly. Where the multi-session protocol would require editing a
file owned by another session, this session instead logs the request here.

## Task board

| # | Task | Status | Owner (session ID) | File scope | Notes |
|---|------|--------|-------------------|------------|-------|
| 1 | Full requirements list (spec) | done | c7fbc064-nba1 | `requirements.md`, `docs/requirements.html` | Numbered spec R1–R19 with status + sources. |
| 2 | Repo review + line-by-line verification | done | c7fbc064-nba1 | `verification/repo-review.md` | Starting repo was empty (README only); structure + verification documented. |
| 3 | Originated lines + methodology | done | c7fbc064-nba1 | `data/lines.json`, `src/nba1/model.py`, `docs/lines.html` | Simple-rating model; 26/26 slate games originated. |
| 4 | Strategy research + leaderboard | done | c7fbc064-nba1 | `data/strategies.json`, `data/leaderboard.json`, `src/nba1/strategies.py`, `docs/strategies.html` | 6 strategies; 4 gates; correlations; luck removed via shrinkage. |
| 5 | Pick generation (≤3 days) | done | c7fbc064-nba1 | `data/picks.json`, `src/nba1/run.py`, `docs/picks.html` | Picks for 2026-11-13..16 window. |
| 6 | Injuries, rotation, game-flow | needs review | c7fbc064-nba1 | `data/injuries.json`, `src/nba1/injuries.py`, `docs/injuries.html` | Game-flow verified; live injury statuses unverified (blank + flagged). |
| 7 | Executive summary | done | c7fbc064-nba1 | `docs/summary.html` | Key figures, risks, next steps. |
| 8 | Suggestions section (review before implementing) | done | c7fbc064-nba1 | `docs/suggestions.html` | 10 suggestions with effort + status; review workflow. |
| 9 | Questions / information / answers register | done | c7fbc064-nba1 | `docs/qanda.html` | What we know vs lack + discovery suggestions. |
| 10 | GitHub Pages site (landing + subpages) | done | c7fbc064-nba1 | `docs/`, `tools/build_site.py` | Dashboard landing + 10 subpages; all tables sourced. |
| 11 | Verification: every row has official source link | done | c7fbc064-nba1 | `verification/`, all `docs/*.html` | Unverifiable = blank + flagged; never inferred. |
| 12 | Sources registry | done | c7fbc064-nba1 | `verification/sources.md`, `docs/sources.html` | Official sources used, with links. |
| 13 | Integration, PR, merge, Pages deploy | in progress | c7fbc064-nba1 | `COORDINATION.md`, `.github/` | PR → merge → deploy; result recorded below. |

## Claims log

- `c7fbc064-nba1` claimed all tasks 1–12 (single active session; no competing claims). Committed with the claim.
- No cross-session file-ownership conflicts encountered.

## Verification log

- **Standings (30 teams, W/L/PS-PA/SRS + leaders):** verified vs
  https://www.basketball-reference.com/leagues/NBA_2027_standings.html
- **Upcoming slate (Nov 13–16):** verified vs https://www.nba.com/schedule
- **Recent completed slate (Nov 12):** verified vs
  https://www.basketball-reference.com/boxscores/index.fcgi?month=11&day=12&year=2026
- **Correlations:** model-computed from verified standings inputs.
- **Originated lines / picks / strategies / leaderboard:** model outputs from verified inputs;
  each site row links to NBA.com + Basketball-Reference.
- **Injuries:** game-flow from verified inputs; live injury statuses UNVERIFIED (blank + flagged),
  official source https://www.nba.com/news/injury-report
- **Site link check:** all internal + asset links resolve; no `None`/placeholder leaks.

## Irregularities flagged (also on the Flagged for Review page)

1. "A. Davis" listed with Washington (WAS) in the 2026-11-12 DET@WAS box — roster/trade review.
   https://www.basketball-reference.com/boxscores/202611120WAS.html
2. BBR boxscore index shows "No games played" for future dates (completed games only);
   scheduled slate taken from NBA.com.
3. Spread edge structurally ~0 against our own fair line (no verified market line available).
4. Live injury statuses, live odds, per-player stats unverified — blank + flagged.
5. 5 of 8 games on 2026-11-16 not captured in detail — needs a live re-pull.

## Handoffs / incidents

- None.

## Final integration record

- PR: (filled after PR is opened)
- Merge result: (filled after merge)
- GitHub Pages deploy: (filled after deploy)
