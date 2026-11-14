# Official captures taken in this session (2026-11-14, after 18:38 UTC)

These are the reads the `verified/` section is built from. Every row published in
`verified/verification.html` points at one of these URLs. Nothing in this directory
is a snapshot of a third-party site: all URLs are NBA-operated.

| # | Source (official) | URL | Retrieved (UTC) | What was read |
| --- | --- | --- | --- | --- |
| C1 | NBA Official Injury Report index + edition PDFs | https://official.nba.com/nba-injury-report-2026-27-season/ | 2026-11-14T18:45Z | The index lists every edition for 11/14/26 from 12:00 AM ET to 1:30 PM ET; confirms which editions exist |
| C2 | Injury Report 11/14/26 01:30 PM (latest edition on the index at read time) | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf | 2026-11-14T18:47Z | 5 games on 11/14, 14 games on 11/15, all 11/15 team-slots NOT YET SUBMITTED |
| C3 | Injury Report 11/14/26 01:00 PM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_00PM.pdf | 2026-11-14T18:46Z | Edition-diff: what changed between 12:00 PM and 1:30 PM |
| C4 | Injury Report 11/14/26 12:00 PM | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_12_00PM.pdf | 2026-11-14T18:44Z | 11/14 rows before the 1:00 PM game-day deadline |
| C5 | Injury Report 11/14/26 04:15 AM (the edition the site's injury page cites) | https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf | 2026-11-14T19:32Z | Re-read to check the site's own 75-row transcription |
| C6 | Teams Advanced, 2026-27, regular season, per game | https://www.nba.com/stats/teams/advanced | 2026-11-14T18:52Z | All 30 teams: GP, W, L, OffRtg, DefRtg, NetRtg, PACE, eFG%, TS%, TOV%, PIE |
| C7 | Boston Celtics team advanced (single-team confirmation of C6) | https://www.nba.com/stats/team/1610612738/advanced | 2026-11-14T19:10Z | BOS: GP 12, 117.4 / 105.6 / 11.7, PACE 96.62 — matches C6 exactly |
| C8 | Cleveland Cavaliers team advanced | https://www.nba.com/stats/team/1610612739/advanced | 2026-11-14T19:20Z | CLE: GP 13, 116.2 / 115.3 / 0.9, PACE 99.62 — matches C6 exactly |
| C9 | Games & Scores, 11/13 | https://www.nba.com/games?date=2026-11-13 | 2026-11-14T18:56Z | All 9 finals with scores, OT flag, records |
| C10 | Games & Scores, 11/12 | https://www.nba.com/games?date=2026-11-12 | 2026-11-14T19:28Z | All 4 finals (corpus check) |
| C11 | Games & Scores, 11/06 | https://www.nba.com/games?date=2026-11-06 | 2026-11-14T19:36Z | 6 of 9 finals visible in the returned page |
| C12 | Games & Scores, 11/07 | https://www.nba.com/games?date=2026-11-07 | 2026-11-14T19:37Z | Page returned with every score rendered as "-" (not readable as a score source this session) |
| C13 | Schedule, 11/15 window page (holds 11/14 → 11/19) | https://www.nba.com/schedule?date=2026-11-15 | 2026-11-14T19:00Z | 27 games 11/14–11/17 with tip times, venues, game ids, and the printed per-day counts (5/9/8/5) |
| C14 | Player page: Jamal Murray (DEN) | https://www.nba.com/player/1627750 | 2026-11-14T19:24Z | PPG 26.2 (the site's prop "line" for him) |
| C15 | Player page: Giannis Antetokounmpo (MIA) | https://www.nba.com/player/203507 | 2026-11-14T19:25Z | PPG 28.5 |
| C16 | Player page: Shai Gilgeous-Alexander (OKC) | https://www.nba.com/player/1628983 | 2026-11-14T19:26Z | PPG 30.5 |
| C17 | Player page: Donovan Mitchell (CLE) | https://www.nba.com/player/1628378 | 2026-11-14T19:27Z | PPG 23.0 |
| C18 | Player page: LaMelo Ball (MIN) | https://www.nba.com/player/1630163/lamelo-ball | 2026-11-14T19:13Z | PPG 18.6, team MIN |
| C19 | Player page: Cooper Flagg (DAL) | https://www.nba.com/player/1642843/cooper-flagg | 2026-11-14T19:30Z (via search index of the page) | PPG 21.0 (indexed copy) / 24.6 (an earlier indexed copy) — two different official values, so treated as UNVERIFIED |

## Rules applied to these reads

1. A URL that returned content is not automatically "verified" — the value has to be
   read off the page in that read. Where a page returned an unrendered score ("-"),
   that date is recorded as **not readable this session**, not as verified.
2. Where two reads of the same official page disagree (Cooper Flagg's PPG), the value
   is **unverified** and flagged, never averaged and never guessed.
3. The injury designations are recorded **with the edition stamp**. Designations move
   within a day (Christie: Questionable at 12:00 PM → Doubtful at 1:00 PM), so an
   undated designation is not a fact.
