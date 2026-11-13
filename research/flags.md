# Flagged for review (research extracts, 2026-11-13)

Items here are not blocking. Each one names the source checked so it can be reviewed directly.

## A. Repository review (checked on 2026-11-13)

| # | Finding | How checked | Review link |
|---|---|---|---|
| R1 | `README.md` is 6 bytes (`# NBA1`) with no description, usage or structure. | `wc -c README.md` | https://github.com/wingbangboozle1-lang/NBA1/blob/main/README.md |
| R2 | No `LICENSE` file; GitHub API reports `license: null`. | `git ls-tree -r main` and GitHub API `repos/wingbangboozle1-lang/NBA1` | https://api.github.com/repos/wingbangboozle1-lang/NBA1 |
| R3 | No `.gitignore`. | `git ls-tree -r main` | https://github.com/wingbangboozle1-lang/NBA1 |
| R4 | `main` has one commit ("Initial commit", `f73edd2`). | `git rev-list --count main` | https://github.com/wingbangboozle1-lang/NBA1/commits/main |
| R5 | GitHub Pages is already enabled on `main` at `/` (legacy build, status `built`, public). Live URL: https://wingbangboozle1-lang.github.io/NBA1/ . | GitHub API `repos/wingbangboozle1-lang/NBA1/pages` | https://api.github.com/repos/wingbangboozle1-lang/NBA1/pages |
| R6 | Three agent branches are on the remote and each claims the same overall site task: `arena/4f997533-nba1`, `arena/c2b0ebb8-nba1`, `arena/d3892d13-nba1` (this one). Their claims overlap on `index.html`, `README.md`, `COORDINATION.md` and `.github/workflows/`. | `git ls-remote origin` | https://github.com/wingbangboozle1-lang/NBA1/branches |
| R7 | The brief asks for branch names `session-<id>/<task>`. The environment fixes the branch as `arena/<id>-nba1`; the environment rule was followed. | Session branch note | — |
| R8 | The brief's Pages requirement ("github page live site") is met by R5, but the site content itself does not exist yet on `main` (owned by the integration session). | `git ls-tree` | — |

## B. Data irregularities

| # | Finding | Source | Review link |
|---|---|---|---|
| D1 | The injury report title says 04:15 PM and gives no time zone. Assumed ET from the schedule. | S2 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf |
| D2 | 17 of 91 injury rows have a blank team cell in the PDF text extract (under team headings or page breaks). Team left null, marked `team_unverified`. | S2 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf |
| D3 | Saturday 14 Nov games show no NBA Cup group label on the schedule page; left blank. | S1 | https://www.nba.com/schedule |
| D4 | Injury reports for 14 Nov games say "NOT YET SUBMITTED" (5 games, 10 teams). No injury data for those games. | S2 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf |
| D5 | The schedule page contains odds controls ("Hide Odds") but no odds values were captured. No betting lines are in this data set. | S1 | https://www.nba.com/schedule |
| D6 | The official NBA injury-report page (https://www.nba.com/injury-report) returned "Content Unavailable". The PDF was used instead. | fetch on 2026-11-13 | https://www.nba.com/injury-report |
| D7 | Official injury PDF text was split across page columns; some reasons had words run together (e.g. "AnkleSprain"). Spaces were added between those words. Nothing else changed. | S2 | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_04_15PM.pdf |

## C. Regulatory constraint (Netherlands)

| # | Finding | Source | Review link |
|---|---|---|---|
| L1 | Under Dutch law, offering online sports betting requires a Ksa licence. Licensed sports-betting providers may only offer bets on events in or results of sports matches. | S3 | https://kansspelautoriteit.nl/ksa-wijst-aanbieders-op-grenzen-vergunning-voor-sportweddenschappen |
| L2 | Fixed-odds betting is defined as the licensee setting the odds before the match. This comes from a 2014 bill memorandum (background only); the current law must be checked. | S4 | https://zoek.officielebekendmakingen.nl/kst-33996-3.html |
| L3 | Publishing the project's own "lines" to people in NL as an offer is likely to be regulated gambling activity. Research and private analysis are a different matter. Legal review is needed before any public line or pick service. | S3, S4 | https://kansspelautoriteit.nl/ |

## D. Not verified (left blank on purpose)

- Betting lines, odds, implied probabilities and any "edge".
- Player minutes, rotation data, production, or injury impact on minutes or output.
- Historical results used to validate any strategy; correlation values; parlay or prop combination performance.
- Any claim that a strategy is skill-based. Nothing in this repository has passed a validation gate.
