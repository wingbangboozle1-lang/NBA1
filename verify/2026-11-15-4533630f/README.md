# verify/2026-11-15-4533630f — independent official-source verification, 15–18 Nov horizon

Session `arena/4533630f-nba1`. Board claim: `COORDINATION.md` §42.

## Why this pass exists

Every earlier session recorded that official NBA hosts are unreachable from the sandbox
(`curl` → HTTP 000). This session's page-fetch channel *does* reach `www.nba.com` and
`ak-static.cms.nba.com`, so the published values can be checked against the official pages
directly — without the GitHub runner, and without relying on the run artifact (whose log
download returns EOF: `gh run view 43770932084 --log`).

## Run order

```bash
python3 capture_schedule.py    # schedule + standings + 11/14 finals  -> capture.json
python3 capture_stats.py       # team advanced (30 rows) + traditional (3 rows) -> capture_stats.json
python3 capture_injury.py      # official injury index listing -> capture_injury.json
python3 capture_injury_diff.py # two editions, row by row -> injury_diff.json
python3 stale_check.py         # model rows that moved at tip-off -> stale_inputs.json
python3 compare.py             # published vs captured, per cell -> compare.json
python3 build_report.py        # REPORT.md + index.html
```

## Findings

| # | Finding | Where |
| --- | --- | --- |
| 1 | The settled 11/14 finals are exact: 45/45 compared cells agree (scores, quarters, venue, attendance, officials). | `compare.json` → `finals_2026_11_14` |
| 2 | 2 published model-input rows (IND, PHI) had already changed when the 11/15 slate tipped. | `stale_inputs.json` |
| 3 | 2 of 34 schedule rows were published with a blank venue the official page prints (PHI@ORL, ATL@OKC). | `compare.json` → `schedule` |
| 4 | Standings: 347/360 cells agree; the 13 differences are all on the two clubs that finished a game during the read. | `compare.json` → `standings` |
| 5 | The model's injury edition (11/15 06:15 AM ET) is 48 editions behind the last one listed for 11/15 (06:15 PM ET). | `capture_injury.json` |
| 6 | Diffing those two editions: 15 of 16 compared players changed status; one team block was NOT YET SUBMITTED in the morning edition. | `injury_diff.json` |

## Scope limits — stated, not implied

- Rows this pass did not read print `not read` with a reason and are never marked agree.
- The injury diff covers the **first reader chunk** of each PDF (IND@PHI, LAL@PHX, CHA@LAC,
  SAS@UTA, DAL@BOS, NYK@TOR, HOU@WAS, ATL@MIL). Later-chunk rows are not claimed unchanged.
- Team opponent stats and 27 of 30 traditional rows were not re-read in this pass.
- Only IND@PHI was Final on 11/15 at read time; no 11/15 settlement is possible yet.
- Nothing in `data/**` was edited. Promotion of any value is the owner's, not this pass's.
