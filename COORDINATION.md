# Coordination board

The board was absent on initial inspection of `arena/4f997533-nba1`; after the initial claim/push, concurrent merged work was found on `main`. This current-branch integration preserves that work and adds the source-linked subpages and checks. Session IDs below are branch identifiers supplied by Arena; separate IDs were not available.

| Task | Status | Owner | File scope |
|---|---|---|---|
| Build verified NBA lines research/dashboard, methodology, decision questions, and review flags | done (previous merged work) | `arena/0684edd4-nba1` (per merged main coordination history) | `index.html`, `styles.css`, `app.js`, `README.md`, `.github/workflows/pages.yml` |
| Extend dashboard into source-linked subpages, verification/source register, and integrate without discarding merged work | done locally; current PR/deploy follow-up pending | `arena/4f997533-nba1` | `COORDINATION.md`, `README.md`, `index.html`, `research.html`, `slate.html`, `suggestions.html`, `review.html`, `sources.html`, `subpages.css`, `scripts/check_site.py`, `.github/workflows/pages.yml` |

## Source and verification log

- Official source references checked 2026-11-13: NBA schedule https://www.nba.com/schedule; official 2026–27 injury report policy https://official.nba.com/nba-injury-report-2026-27-season/; NBA Stats glossary https://www.nba.com/stats/help/glossary; NBA player box scores https://www.nba.com/stats/players/boxscores; NBA team advanced stats https://www.nba.com/stats/teams/advanced; NBA Rule No. 5 https://official.nba.com/rule-no-5-scoring-and-timing/; GitHub Pages custom workflows https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages.
- The merged `main` coordination history records that PR #1 merged on 2026-11-13 and that Pages workflow run 43518760512 completed, with public URL https://wingbangboozle1-lang.github.io/NBA1/. This session has not independently re-run or re-verified that earlier deployment after the new changes.
- Current work preserves the existing single-page dashboard, styling, JavaScript, prior source/verification notes, and Pages deployment implementation. Added separate detail pages and a separate stylesheet to avoid overwriting existing shared assets.
- Verification: Python HTML parsing succeeded for the added pages; final `python3 scripts/check_site.py` passes across the landing page plus five subpages, all local links, and all 81 table-body rows with official NBA/GitHub source links. `git diff --cached --check` passed. External link availability/data rights are not represented by this structural check.

## Concurrency / conflict log

- 2026-11-13: After this branch's PR was opened, `origin/main` had advanced through merged PRs #1 and #2 from `arena/0684edd4-nba1`; the PR showed merge conflicts in the workflow, coordination board, README, landing page and stylesheet. This work paused and inspected the merged files before resolving.
- Resolved by retaining the merged `main` versions of the shared landing page, stylesheet, README, Pages workflow and existing coordination history, then adding this session's distinct subpages, `subpages.css`, source/link validator, and navigation links as integration additions. No prior session files were intentionally removed.
- A required pre-push `git pull --rebase origin arena/4f997533-nba1` attempted to replay the already-merged main history and conflicted in coordination/README/index/styles. Rebase was aborted without discarding the resolved integration merge; local history retains origin/main as a merge parent, and the current session changes are preserved. The branch's remote had not advanced beyond the commit already included.

## Open limitations

No current slate, injury snapshots, market odds, projections, correlations, backtests, or skill evidence are available. Sportsbook feed rights, legal scope and data-use rights need review. Numerical values stay blank and picks remain disabled. See `review.html` (F-01–F-10).

## PR / deployment follow-up

Current PR and post-merge Pages workflow/deployment verification are pending. Do not claim updated deployment until the GitHub run and public site are checked.
