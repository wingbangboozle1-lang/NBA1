# X01 — Is the 11/14 injury data on the site the newest official edition?

Session `arena/2ef89703-nba1` · task X01 on `COORDINATION.md` §24 · checked 2026-11-14 at about 10:20–10:30 UTC.
Read-only. Nothing under `data/`, `docs/`, `index.html` or any shared output was changed.

## Sources (all official)

| What | Link |
| --- | --- |
| Newest edition at check time: NBA injury report, 11/14/26 04:30 AM ET (PDF) | [Injury-Report_2026-11-14_04_30AM.pdf](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf) |
| League index of 11/14 editions (12:00 AM to 4:30 AM ET listed) | [official.nba.com/nba-injury-report-2026-27-season](https://official.nba.com/nba-injury-report-2026-27-season/) |
| Site edition used before this check: 11/13/26 07:30 PM ET (PDF) | [Injury-Report_2026-11-13_07_30PM.pdf](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf) |
| Repo's NBA.com games capture used to place undated matchups by date | `data/official/slate.json` (captured from [nba.com/games?date=](https://www.nba.com/games?date=2026-11-14), not re-fetched here) |

## Result

1. **All 26 player rows on the site match the 04:30 AM edition.** Same player, same status, same reason, same team, matchup and time. 0 rows differ, 0 rows are missing from the edition, 0 edition player rows are missing from the site. Row-by-row detail: [ROWS.md](ROWS.md) (each row links to the PDF).
2. **The site's "most recent edition" label is one edition behind.** `data/live/injury_report_2026_11_14.json` names the 07:30 PM 11/13 edition as the newest. The 04:30 AM 11/14 edition exists and is listed on the league index. The player rows did not change, but the label and source should cite the newer edition.
3. **Club filing state is unchanged.** The site says five clubs had not filed for 11/14 (NOP, CLE, MEM, CHI, MIA) and that one club per game had filed. The 04:30 AM edition shows the same five "NOT YET SUBMITTED" lines and the same filed clubs (DEN, DAL, BKN, MIN, DET).
4. **Matchups outside the 11/14 slate are not on the site, and that is correct.** The 04:30 AM edition lists 7 more matchups (CHA@LAC, SAS@UTA, DAL@BOS, NYK@TOR, HOU@WAS, ATL@MIL, OKC@SAC). Their 4:30–9:00 PM ET times match the repo's NBA.com capture for **11/15**, not 11/14, so they are not part of the 11/14 slate.

## Flags (for review; none blocks the merge)

| ID | Severity | Item | Evidence (link) |
| --- | --- | --- | --- |
| X01-F1 | Medium | The site labels the 07:30 PM 11/13 edition as the most recent. A newer 04:30 AM 11/14 edition exists. | [04:30 AM PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_30AM.pdf), [index](https://official.nba.com/nba-injury-report-2026-27-season/) |
| X01-F2 | Medium | Parser risk in the PDF: on the page-break continuation rows, the date column and sometimes the team column are blank. The row for **Traore, Nolan** (site: Brooklyn, Probable, right calf) has no team or matchup printed on the 04:30 edition. The site's team assignment rests on the 07:30 PM edition. | `capture_2026-11-14_0430AM.md`, lines under "Injury Report: 11/14/26 04:30 AM" |
| X01-F3 | Low | Date not printed on 11 continuation rows (CHI@MIN, DET@MIA player rows). Their date (11/14) is taken from the site and the repo's schedule capture, matched by matchup and time (08:00 PM ET). They are not confirmed from the PDF's own date column. | `ROWS.md` section A, "Team / matchup / time" column |
| X01-F4 | Low | Time format: the report prints `07:00 (ET)` (24-hour clock), the schedule prints `7:00 PM ET`. Both agree on every 11/14 game. | `ROWS.md` |
| X01-F5 | Time-sensitive | The 11/14 game-day editions (8–10 AM local time for tip-offs at 5 PM or earlier; 11 AM–1 PM local time for others, per the [league policy](https://official.nba.com/nba-injury-report-2026-27-season/)) were not yet published at check time. Designations for 11/14 can still change. | league index |

## Limits

- The league index capture lists editions up to 4:30 AM ET. Later editions may exist and were not checked. The check ran at about 5:20 AM ET.
- The check used `fetch_page` (a text fetch), not a browser. Table cells were read from the tool's text output and saved verbatim in `capture_2026-11-14_0430AM.md`.
- This check covers only the 11/14 player rows. It does not verify minutes, production impact, odds or lines.
- Nothing was inferred. Blank printed cells stay blank in `compare.json`.

## Files

| File | What it is |
| --- | --- |
| `capture_2026-11-14_0430AM.md` | Verbatim text of the 04:30 AM edition, with its source link |
| `compare.py` | Re-runs the comparison from the capture and `data/live/injury_report_2026_11_14.json` |
| `compare.json` | Machine-readable result, with counts and per-row checks |
| `ROWS.md` | Row-level table; every row links to the PDF |
| `REPORT.md` | This file |

Reproduce from the repository root: `python3 verify/2026-11-14-injury-currency/compare.py`
