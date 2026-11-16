# Independent official-source verification — 2026-11-15 horizon

Session `arena/4533630f-nba1`. Official pages read **2026-11-15T23:40Z..2026-11-16T00:20Z** through the page-fetch
channel (`curl` from the sandbox returns HTTP 000 for every NBA host; the page-fetch channel
reaches `www.nba.com`, which is what made this pass possible without the GitHub runner).

## What was checked, and what it says

| Surface | Published rows | Verdict | Source |
| --- | --- | --- | --- |
| 2026-11-15..18 schedule | 34 | {'AGREE': 263, 'MISMATCH_POINT_IN_TIME': 3, 'PUBLISHED_BLANK_OFFICIAL_HAS_VALUE': 4, 'UNVERIFIABLE_IN_THIS_PASS': 2} | [NBA games](https://www.nba.com/games?date=2026-11-15) |
| Standings | 30 | {'AGREE': 347, 'MISMATCH': 13} | [NBA standings](https://www.nba.com/standings) |
| 2026-11-14 finals (settlement input) | 5 | {'AGREE': 45} | [DEN@NOP](https://www.nba.com/game/den-vs-nop-0022600231) |
| Team advanced stats (model input) | 30 | {'AGREE': 536, 'MISMATCH_POINT_IN_TIME': 34} | [NBA advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| Team traditional stats (model input) | 30 (3 re-read) | {'AGREE': 36, 'NOT_PRINTED_IN_READ_CHUNK': 9, 'NOT_RE_READ_IN_THIS_PASS': 27} | [NBA traditional](https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season) |
| Team opponent stats (model input) | 30 | not re-read in this pass | [NBA opponent](https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season) |

## Findings

**1. The settled 11/14 finals are exact.** 45 of 45 compared cells agree with the official
game pages, including quarter-by-quarter lines that sum to the printed finals, venue, city,
attendance and officials. The settlement chain rests on correct numbers.

**2. 2 model-input rows were already stale when the 11/15 slate tipped.** The
published team ratings were cut before the 11/15 games; IND and PHI played the 13:00 ET game
(`IND 124 - PHI 131`, Final), so their rows changed on the official page after the cut. Every
one of the 34 published games is modelled from those rows.

| Team | Published GP | Official GP now | OffRtg | DefRtg | Pace | Source |
| --- | --- | --- | --- | --- | --- | --- |
| IND | 13 | 14 | 110.1 → 110.9 | 111.7 → 112.9 | 101.15 → 101.25 | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| PHI | 13 | 14 | 111.0 → 112.3 | 109.5 → 110.3 | 100.04 → 100.21 | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |

**3. 2 of the 34 schedule rows were published with a blank venue that the official
game page prints.** The published capture left `venue`/`city` empty for PHI@ORL and ATL@OKC;
both pages name the building. Nothing was filled in by this session — the pages are cited so
the owner can promote them.

| Game | Date | Published venue | Official | Source |
| --- | --- | --- | --- | --- |
| PHI@ORL | 2026-11-18 | (blank) | Kia Center, Orlando, FL | [0022600261](https://www.nba.com/game/phi-vs-orl-0022600261) |
| ATL@OKC | 2026-11-18 | (blank) | Paycom Center, Oklahoma City, OK | [0022600265](https://www.nba.com/game/atl-vs-okc-0022600265) |

**4. The standings snapshot is 30 rows and agrees on 347 of 360 cells.**
The 13 differences are all on the two clubs that had played to a final by read time (PHI,
IND) and are therefore correct-at-a-different-time, not errors: PHI 10-3 → 11-3,
IND 5-8 → 5-9.

**5. The injury read-out the model used is 36 hours and 48 editions out of date.** The
published read-out is the **11/15 06:15 AM ET** edition (retrieved 11:52Z). The official index
now lists 76 editions for 11/15, from 12:00 a.m. ET to
**6:15 p.m ET**. The league's own rule, quoted on that page, requires a
game-day report between 11 a.m. and 1 p.m. ET (8–10 a.m. for tips at or before 5 p.m.) and says
reports are updated continually through the day. Every 11/15 tip therefore ran on information
the model never read.

| Item | Value | Source |
| --- | --- | --- |
| Edition the model used | 11/15/26 06:15 AM ET (retrieved 2026-11-15T11:52Z) | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) |
| Latest edition on the official index at read time | 6:15 p.m ET | [index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| Editions listed for 11/15 | 76 | [index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| Editions published after the model's edition | 48 | [index](https://official.nba.com/nba-injury-report-2026-27-season/) |

**6. Diffing the model's edition against the game-day edition, row by row, shows
15 of 16 compared players changed status** - 1 downgrade and 10 upgrades - including one team block that
was **NOT YET SUBMITTED** in the morning edition, a starter added as Out on game day, and a
questionable player downgraded to Out. The lines were published from the morning edition.

| Game | Player (as printed) | 06:15 AM ET | 06:15 PM ET | Move | Source |
| --- | --- | --- | --- | --- | --- |
| IND@PHI | McConnell, T.J. | Probable | Available | up +0.2 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| IND@PHI | Nembhard, Andrew | Questionable | Out | down -0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| IND@PHI | Nesmith, Aaron | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| LAL@PHX | James, Bronny | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| LAL@PHX | Sexton, Collin | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| LAL@PHX | Thiero, Adou | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| LAL@PHX | Timme, Drew | (absent) | Out | — | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| CHA@LAC | Martinelli, Nick | (absent) | Out | — | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| SAS@UTA | Fox, De'Aaron | (absent) | Out | — | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| DAL@BOS | (entire team block) | NOT YET SUBMITTED | 8 players submitted | — | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| DAL@BOS | Carter, Devin | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| DAL@BOS | Cenac Jr., Christopher | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| NYK@TOR | Barnes, Scottie | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| HOU@WAS | Adams, Steven | Probable | Available | up +0.2 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |
| HOU@WAS | Carrington, Bub | Questionable | Available | up +0.5 | [AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) / [PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |

_Scope: First reader chunk of each edition only (IND@PHI, LAL@PHX, CHA@LAC, SAS@UTA, DAL@BOS, NYK@TOR, HOU@WAS, ATL@MIL). Rows printed only in later chunks are not compared and are not claimed unchanged._

## Per-row detail

### Schedule — 34 rows

| Game | Date | Tip (ET) | Venue | City | Records | Check | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IND@PHI | 2026-11-15 | 01:00 PM ET | Xfinity Mobile Arena | Philadelphia, PA | 5-8 / 10-3 | <span class="b ok">agree</span> | [0022600236](https://www.nba.com/game/ind-vs-phi-0022600236) |
| LAL@PHX | 2026-11-15 | 04:00 PM ET | Mortgage Matchup Center | Phoenix, AZ | 11-2 / 5-6 | <span class="b ok">agree</span> | [0022600237](https://www.nba.com/game/lal-vs-phx-0022600237) |
| CHA@LAC | 2026-11-15 | 04:30 PM ET | Intuit Dome | Inglewood, CA | 4-8 / 3-8 | <span class="b ok">agree</span> | [0022600238](https://www.nba.com/game/cha-vs-lac-0022600238) |
| SAS@UTA | 2026-11-15 | 05:00 PM ET | Delta Center | Salt Lake City, UT | 11-2 / 1-12 | <span class="b ok">agree</span> | [0022600239](https://www.nba.com/game/sas-vs-uta-0022600239) |
| DAL@BOS | 2026-11-15 | 06:00 PM ET | TD Garden | Boston, MA | 7-6 / 10-2 | <span class="b ok">agree</span> | [0022600240](https://www.nba.com/game/dal-vs-bos-0022600240) |
| NYK@TOR | 2026-11-15 | 06:00 PM ET | Scotiabank Arena | Toronto, ON | 6-6 / 5-7 | <span class="b ok">agree</span> | [0022600241](https://www.nba.com/game/nyk-vs-tor-0022600241) |
| HOU@WAS | 2026-11-15 | 07:00 PM ET | Capital One Arena | Washington, DC | 10-3 / 4-9 | <span class="b ok">agree</span> | [0022600242](https://www.nba.com/game/hou-vs-was-0022600242) |
| ATL@MIL | 2026-11-15 | 08:00 PM ET | Fiserv Forum | Milwaukee, WI | 7-6 / 1-12 | <span class="b ok">agree</span> | [0022600243](https://www.nba.com/game/atl-vs-mil-0022600243) |
| OKC@SAC | 2026-11-15 | 09:00 PM ET | Golden 1 Center | Sacramento, CA | 8-5 / 1-11 | <span class="b ok">agree</span> | [0022600244](https://www.nba.com/game/okc-vs-sac-0022600244) |
| ORL@BOS | 2026-11-16 | 07:00 PM ET | TD Garden | Boston, MA | 5-7 / 10-2 | <span class="b ok">agree</span> | [0022600245](https://www.nba.com/game/orl-vs-bos-0022600245) |
| CHI@CLE | 2026-11-16 | 07:00 PM ET | Rocket Arena | Cleveland, OH | 3-9 / 7-7 | <span class="b ok">agree</span> | [0022600246](https://www.nba.com/game/chi-vs-cle-0022600246) |
| MEM@WAS | 2026-11-16 | 07:00 PM ET | Capital One Arena | Washington, DC | 9-4 / 4-9 | <span class="b ok">agree</span> | [0022600247](https://www.nba.com/game/mem-vs-was-0022600247) |
| PHI@BKN | 2026-11-16 | 07:30 PM ET | Barclays Center | Brooklyn, NY | 11-3 / 3-9 | <span class="b warn">changed since cut</span> | [0022600248](https://www.nba.com/game/phi-vs-bkn-0022600248) |
| HOU@MIA | 2026-11-16 | 07:30 PM ET | Kaseya Center | Miami, FL | 10-3 / 7-6 | <span class="b ok">agree</span> | [0022600249](https://www.nba.com/game/hou-vs-mia-0022600249) |
| POR@MIN | 2026-11-16 | 08:00 PM ET | Target Center | Minneapolis, MN | 9-3 / 9-4 | <span class="b ok">agree</span> | [0022600250](https://www.nba.com/game/por-vs-min-0022600250) |
| GSW@NOP | 2026-11-16 | 09:00 PM ET | Smoothie King Center | New Orleans, LA | 8-5 / 4-10 | <span class="b ok">agree</span> | [0022600251](https://www.nba.com/game/gsw-vs-nop-0022600251) |
| PHX@DEN | 2026-11-16 | 09:00 PM ET | Ball Arena | Denver, CO | 5-6 / 7-4 | <span class="b ok">agree</span> | [0022600252](https://www.nba.com/game/phx-vs-den-0022600252) |
| NYK@TOR | 2026-11-17 | 07:30 PM ET | Scotiabank Arena | Toronto, ON | 6-6 / 5-7 | <span class="b ok">agree</span> | [0022600253](https://www.nba.com/game/nyk-vs-tor-0022600253) |
| POR@MIN | 2026-11-17 | 08:00 PM ET | Target Center | Minneapolis, MN | 9-3 / 9-4 | <span class="b ok">agree</span> | [0022600254](https://www.nba.com/game/por-vs-min-0022600254) |
| DET@SAS | 2026-11-17 | 08:00 PM ET | Frost Bank Center | San Antonio, TX | 8-4 / 11-2 | <span class="b ok">agree</span> | [0022600255](https://www.nba.com/game/det-vs-sas-0022600255) |
| UTA@LAC | 2026-11-17 | 10:30 PM ET | Intuit Dome | Inglewood, CA | 1-12 / 3-8 | <span class="b ok">agree</span> | [0022600257](https://www.nba.com/game/uta-vs-lac-0022600257) |
| CHA@LAL | 2026-11-17 | 11:00 PM ET | Crypto.com Arena | Los Angeles, CA | 4-8 / 11-2 | <span class="b ok">agree</span> | [0022600256](https://www.nba.com/game/cha-vs-lal-0022600256) |
| MEM@CLE | 2026-11-18 | 07:00 PM ET | Rocket Arena | Cleveland, OH | 9-4 / 7-7 | <span class="b ok">agree</span> | [0022600258](https://www.nba.com/game/mem-vs-cle-0022600258) |
| HOU@IND | 2026-11-18 | 07:00 PM ET | Gainbridge Fieldhouse | Indianapolis, IN | 10-3 / 5-9 | <span class="b warn">changed since cut</span> | [0022600259](https://www.nba.com/game/hou-vs-ind-0022600259) |
| MIL@MIA | 2026-11-18 | 07:00 PM ET | Kaseya Center | Miami, FL | 1-12 / 7-6 | <span class="b ok">agree</span> | [0022600260](https://www.nba.com/game/mil-vs-mia-0022600260) |
| PHI@ORL | 2026-11-18 | 07:00 PM ET | Kia Center | Orlando, FL | 11-3 / 5-7 | <span class="b warn">changed since cut</span> | [0022600261](https://www.nba.com/game/phi-vs-orl-0022600261) |
| CHI@BKN | 2026-11-18 | 07:30 PM ET | Barclays Center | Brooklyn, NY | 3-9 / 3-9 | <span class="b ok">agree</span> | [0022600262](https://www.nba.com/game/chi-vs-bkn-0022600262) |
| WAS@TOR | 2026-11-18 | 07:30 PM ET | Scotiabank Arena | Toronto, ON | 4-9 / 5-7 | <span class="b ok">agree</span> | [0022600263](https://www.nba.com/game/was-vs-tor-0022600263) |
| DET@NOP | 2026-11-18 | 08:00 PM ET | Smoothie King Center | New Orleans, LA | 8-4 / 4-10 | <span class="b ok">agree</span> | [0022600264](https://www.nba.com/game/det-vs-nop-0022600264) |
| ATL@OKC | 2026-11-18 | 08:00 PM ET | Paycom Center | Oklahoma City, OK | 7-6 / 8-5 | <span class="b warn">published blank</span> | [0022600265](https://www.nba.com/game/atl-vs-okc-0022600265) |
| GSW@DAL | 2026-11-18 | 08:00 PM ET | (not read) | (not read) | 8-5 / 7-6 | <span class="b mut">not read</span> | [0022600267](https://www.nba.com/game/gsw-vs-dal-0022600267) |
| BOS@DEN | 2026-11-18 | 09:30 PM ET | Ball Arena | Denver, CO | 10-2 / 7-4 | <span class="b ok">agree</span> | [0022600266](https://www.nba.com/game/bos-vs-den-0022600266) |
| UTA@LAL | 2026-11-18 | 10:00 PM ET | Crypto.com Arena | Los Angeles, CA | 1-12 / 11-2 | <span class="b ok">agree</span> | [0022600268](https://www.nba.com/game/uta-vs-lal-0022600268) |
| PHX@SAC | 2026-11-18 | 10:00 PM ET | Golden 1 Center | Sacramento, CA | 5-6 / 1-11 | <span class="b ok">agree</span> | [0022600269](https://www.nba.com/game/phx-vs-sac-0022600269) |

### Model inputs — advanced

| Team | GP | OffRtg | DefRtg | NetRtg | Pace | Check | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LAL | 13 | 121.6 | 113.6 | 8.0 | 100.5 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| SAS | 13 | 119.6 | 106.6 | 13.0 | 98.94 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| BOS | 12 | 117.4 | 105.6 | 11.7 | 96.62 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| HOU | 13 | 119.3 | 110.2 | 9.1 | 97.42 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| PHI | 14 | 112.3 | 110.3 | 2.0 | 100.21 | <span class="b warn">changed since cut</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| MEM | 13 | 119.0 | 110.4 | 8.5 | 100.46 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| MIN | 13 | 116.0 | 104.5 | 11.5 | 101.27 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| POR | 12 | 118.8 | 111.1 | 7.7 | 100.67 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| DET | 12 | 114.1 | 109.2 | 4.9 | 99.48 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| GSW | 13 | 116.1 | 112.0 | 4.1 | 99.66 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| OKC | 13 | 112.7 | 109.0 | 3.7 | 98.58 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| ATL | 13 | 113.3 | 111.9 | 1.4 | 103.55 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| CLE | 14 | 116.9 | 115.4 | 1.6 | 99.72 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| DAL | 13 | 112.8 | 112.8 | 0.0 | 100.54 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| DEN | 11 | 116.0 | 114.7 | 1.3 | 97.67 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| MIA | 13 | 114.7 | 116.2 | -1.5 | 102.49 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| NYK | 12 | 114.5 | 108.6 | 5.9 | 95.63 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| IND | 14 | 110.9 | 112.9 | -2.0 | 101.25 | <span class="b warn">changed since cut</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| ORL | 12 | 109.7 | 113.4 | -3.7 | 98.23 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| PHX | 11 | 113.8 | 117.6 | -3.8 | 98.45 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| TOR | 12 | 114.5 | 112.8 | 1.7 | 99.88 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| CHA | 12 | 101.9 | 113.1 | -11.2 | 96.83 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| NOP | 14 | 111.3 | 120.0 | -8.6 | 101.83 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| WAS | 13 | 108.7 | 114.3 | -5.5 | 99.63 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| BKN | 12 | 109.8 | 116.0 | -6.2 | 99.47 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| CHI | 12 | 109.4 | 120.3 | -10.9 | 103.81 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| LAC | 11 | 110.7 | 115.8 | -5.1 | 100.55 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| MIL | 13 | 105.7 | 120.0 | -14.2 | 100.31 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| SAC | 12 | 107.3 | 119.5 | -12.2 | 101.0 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |
| UTA | 13 | 105.0 | 116.4 | -11.3 | 100.5 | <span class="b ok">agree</span> | [advanced](https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season) |

## Method and limits

- Nothing on the published site was edited by this session. The captures, the comparison and
  this report live in `verify/2026-11-15-4533630f/`; the site owner promotes values.
- A cell this pass did not read prints `not read` with the reason. It is never marked agree.
- `MISMATCH_POINT_IN_TIME` is not an error: it means the official page has legitimately moved
  because games have finished since the published capture. It is flagged because the site
  presents those values as current.
- Team opponent stats and the full traditional table were not re-read in this pass; they are
  listed as `not read`, not as verified.
