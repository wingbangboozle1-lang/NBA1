# Verification record — session arena/cdf3a108-nba1 (2026-11-19, COORDINATION §74)

## Sources read first-hand (platform web-fetch channel; the agent sandbox reaches only github.com / npm / pypi)

| Source | URL | Read (UTC) | What was taken |
| --- | --- | --- | --- |
| Teams Advanced | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 12:2x | 30 rows x 20 columns, typed verbatim |
| Teams Traditional | https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season | 12:3x | 30 rows (GP/W/L/MIN/PTS/+/-) |
| Teams Opponent | https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season | 12:3x | 30 rows (GP/W/L/OppPTS) |
| Standings | https://www.nba.com/standings | 12:2x | 30 rows incl. HOME/ROAD/Neutral columns |
| Injury index | https://official.nba.com/nba-injury-report-2026-27-season/ | 12:45 | edition list 12:00 AM-7:15 AM ET (11/19) |

All rows carry `source_url` + `verified_at_utc` in
`data/official/teams_reread_2026-11-19_cdf3a108.json` and
`data/official/standings_reread_2026-11-19_cdf3a108.json`.

## Cross-checks performed

1. 28 of 30 advanced rows byte-equal to the 05:55Z capture; exactly 14 field changes on LAL + UTA
   (the 11/18 UTA 109 @ LAL 97 game) — printed by `scripts/recut_cdf3a108.py`, never hidden.
2. GP/W/L agree across all three team-stat pages and the standings (gate G3 PASS for the first time).
3. PTS - OppPTS vs +/- within 0.2 for all 30 teams (page rounding).
4. Standings identity: home wins 111 == road losses 111; home games 221; rate 0.5023 = the pinned HCA rate (unchanged).
5. The three moved lines match session arena/d66245d4-nba1's independent re-price to the published rounding.
6. Re-originated line diff published per game (26 rows) in the §74 delivery record.

## Gates (run locally, 2026-11-19T13:0x-13:2xZ)

| Gate | Result |
| --- | --- |
| scripts/verify_all.py | VERIFY OK — FAILURES: 0 |
| scripts/verify_dashboard.py | VERIFY OK |
| scripts/verify_integration.py | PASSED (0 errors) |
| scripts/check_links.py | PASS |
| scripts/check_site.py | PASS |
| scripts/check_rendered.py | PASS |
| scripts/check_registers.py | REGISTERS OK (2,248 fields) |
| scripts/check_build_data.py | PASS |
| scripts/verify_ledger.py | ledger chain OK (18 entries) |
| scripts/test_*.py (15 files) | 0 failures (incl. new test_settle_seal_cdf3a108.py, 3 cases) |
| scripts/render_check.mjs | 167 pages, 13,174 content blocks, 0 problems |
| engine/refresh_gate.py | PASS with 5 PASS BY DECLARATION (0 BLOCK) |
| engine/promote_official.py | exit 0 — 20 promoted, 0 blocked, 5 declared unreadable |
| engine/pipeline.py + engine/build_site.py | exit 0 (the rebuild commands) |

## R01 operational proof

Production run https://github.com/wingbangboozle1-lang/NBA1/actions/runs/44526320610
(Refresh official data, push-triggered on this branch): **Rebuild only after all freshness and
provenance gates pass — SUCCESS**; Report-why-blocked — SKIPPED. Step outcomes are transcribed in
`refresh_run_44526320610_steps.json`. First rebuild execution since 2026-11-15T12:43:11Z.

## Irregularities found and published (not hidden)

- F-CDF-02: the publish step's single `git add` aborted on never-existing pathspecs and silently
  dropped every verified promotion (measured against auto/refresh-20261119-120839's own run record).
  Fixed (per-path staging).
- F-CDF-01: 11/19 editions after 07:00 AM ET not yet archived; the stranded auto-refresh branch was
  adopted (10 PDFs + diffs) and injuries.json re-promoted digest-bound to the 07:00 AM edition.
- F-CDF-04/05: adopted from d66245d4's seat (calibration sigma basis; two S1 records) into the shared
  registers with Q38/Q39.
- The trailing `cancelled` on run 44526320610 is the shared concurrency group cancelling the post
  steps after Publish completed; recorded rather than dressed up.
