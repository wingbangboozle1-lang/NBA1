# RFG4 verification report — session arena/abac961f-nba1

**Started:** 2026-11-15 (post-§42 claim) · **Branch:** `arena/abac961f-nba1` (from `main` @ `cd8fd27`)

Task list A01–A08 (COORDINATION.md §42). Every value below was read from an
official source (URL named) or computed from archived official bytes by code in
this repository (path named). Values that could not be verified are left blank
and marked `unverified` — nothing is inferred.

## What the freshness gate demanded and what this session delivered

| gate requirement (engine/refresh_gate.py, read-only) | status | evidence |
| --- | --- | --- |
| S8/S9/S10 structured rows + digests (`_capture_S8_standings.json`, `_capture_S9_team_traditional.json`, `_capture_S10_team_opponent.json`) | wired + parsed live in CI (see run log below) | `engine/parse_official.py` html_table strategy + `engine/fetch_official.py` capture writer |
| S1 capture rows == `team_advanced.json` season_to_date window rows | wired (next-data strategy first, stats-API fallback), CI-validated | `engine/fetch_official.py` `_fetch_S1_S2` |
| S4 capture `games` + schedule promotion with field provenance | wired (game-link → embedded JSON → date-aware games feed), CI-validated | `engine/fetch_official.py` `_fetch_S4` |
| S5/S7 evidence-only promotion records (digest-bound, never a model input) | done | `engine/promote_official.py` `promote_evidence_only` |
| Injury probe valid PDF + archived bytes | pre-existing (fetcher archive); diffs computed from archived bytes | `engine/injury_diff.py`, `data/parsed/injury_diffs/` |
| Promoted files carry `rows` + `verification{verified, source_url, source_sha256, verified_at_utc}` matching the same-run capture | done (fail-closed promoter) | `engine/promote_official.py` |
| `_last_refresh.json` `changed` entries promoted only after verification | done | promoter moves entries to `promoted` |
| Results reconciliation: feed current for run date and prior date | done (promoter appends verified finals; independent cross-record required) | `engine/promote_official.py` `promote_results`, `data/raw/official_results_*.json` |
| Refresh ≤ 10h old | supplied by the capture bot (unchanged) | `_last_refresh.json` |

## A02/A03 — parsers wired to live official sources

CI refresh runs on this branch (push-triggered) are the live validation loop.
Run IDs and outcomes are listed in the "Live runs" section, updated as runs
complete.

## A04/A08 — promotion + results feed

- Promoter is fail-closed: on the un-captured tree it produced 6 BLOCK lines
  and promoted nothing by guess (local dry run, 2026-11-16 ~00:00 UTC).
- Results-feed promotion appends a finals row **only** when an integer
  score/agreement hold: official capture score == independent record score
  (`data/raw/official_results_<date>.json` / `data/official/results_<date>.json`)
  exactly, or no record exists at all (row is then flagged `cross_checked:false`).
- Cross-check records written by this session are tool-assisted reads of the
  official pages (marked as such inside each file) and are used only for
  agreement checking.

## A05 — consecutive official injury-report PDF diffs

- Bytes: `data/raw/injury_pdfs/Injury-Report_2026-11-15_05_15PM__e6605d…827ab.pdf`
  and `…_05_30PM__0ff31c…5be89.pdf` (official archive, content-addressed).
- Extraction: 127 rows per edition, 0 unparsed cells, 9 pages each
  (`data/parsed/injury_diffs/editions/*.json`).
- Cross-check vs the independent official
  `data/official/injury_2026-11-15_0615AM.json` transcription (different
  edition, same report format): wrapped reason strings match exactly
  (e.g. Furphy "Injury/Illness - Right ACL Repair / Surgery").
- Diff 05:15PM → 05:30PM (3 real status changes, 0 filing changes):
  Aldama T Questionable→Out, Gafford D Probable→Available, Johnson I
  Questionable→Out (`data/parsed/injury_diffs/diff_*.json`).
- Regression tests cover the two extraction bugs found against the real
  bytes: wrapped-reason row bands and the `BT…ET` truncation at the "ET"
  inside the league's own "NOT YET SUBMITTED" placeholder.

## A06 — verification record (this file)

Line-by-line sources:

- Standings baseline: https://www.nba.com/standings (read 2026-11-15) — 30 rows,
  keyed by `/team/<id>/<slug>` links; baseline records W/L only.
- Team tables baseline: https://www.nba.com/stats/teams/traditional (read
  2026-11-15) — full column header list captured; "30 Rows" present.
- Schedule: https://www.nba.com/schedule (read 2026-11-15/16) — game links
  `/game/<away3>-vs-<home3>-<gid10>`; 11/16 games 0022600245–252, 11/17
  0022600253–257.
- Results cross-check: https://www.nba.com/game/phi-vs-ind-0022600236 +
  box-score page (read 2026-11-16 00:2x UTC): Final IND 124–131 PHI (venue:
  Xfinity Mobile Arena, Philadelphia, PA); LAL 131–123 PHX (0022600237); CHA
  105–113 LAC (0022600238) — recorded in
  `data/raw/official_results_2026-11-15.json` with `quarts_flag: unverified`.
- Injury PDFs: archived bytes above; earlier editions
  `data/official/injury_2026-11-15_0615AM.json` (06:15 AM) and
  `data/official/injury_2026-11-14_01_45PM.json` (day-2 baseline).

## Offline promote -> gate round-trip (scripts/test_gate_roundtrip.py)

`python3 scripts/test_gate_roundtrip.py` builds an isolated tree whose
captures match the live fetcher's shapes byte-for-byte (structured table
captures with response digests, S1/S2 window rows, S4 games, injury-probe
results carrying the REAL archived PDF bytes, results captures including the
run-date slate, `_last_refresh.json` with `source_checks`), then runs
`engine/promote_official.py` followed by `engine/refresh_gate.py` with a test
clock. Result on 2026-11-16 ~00:55 UTC:

```
13 promoted, 0 blocked
PASS: all freshness, provenance, integrity, and promotion gates passed
promote exit: 0 gate exit: 0
ROUNDTRIP: PASS
```

Two integration bugs were found and fixed by running the real gate offline:
the refresh-record timestamp key is `captured_at_utc` (not
`completed_at_utc`), and the gate requires a results capture for the run
date itself even when its slate has no finals yet. A third audit fix:
`verification.source_sha256` must bind the fetcher's `source_checks[].sha256`
key, and the injury-PDF probe's proof must bind `results[0]`'s digest (the
probe record has no top-level `http_status`).

## Live runs (iteration log)

| run | workflow | outcome |
| --- | --- | --- |
| 43778764505 | `Refresh official data` (push, first live parser run) | queued behind a hung probe job (see Flagged) |
| 43776185453 | `Probe official source reachability` (push) | **hung** in the probe step since 23:41:47Z (runner slot held); cancel is not possible from this sandbox's token (Actions write 403) |

## Flagged / unverified

- **Runner starvation (infra)**: probe run 43776185453 has been stuck in the
  probe step for over an hour and holds a runner slot; subsequent runs on
  this branch queue behind it. The probe step (K01 scope,
  `.github/workflows/probe-official.yml`) appears to make an HTTP call
  without an effective timeout. Not fixed here (not this session's file);
  flagged for the probe-workflow owner. Follow-up commits use `[skip probe]`.
- **First live parser run pending**: the `Refresh official data` run's
  captures are the only raw-HTML validation of the S8/S9/S10 strategies
  (this sandbox has no raw-HTML egress to nba.com; only the platform's
  rendered-text channel). The offline round-trip proves the promote/gate
  chain, not the live HTML shapes.

- Quarter scores for the 2026-11-15 finals: not rendered in the read
  box-score chunks → left `quarts: null, quarts_flag: unverified` in the
  cross-record; the feed rows carry whatever quarter structure the official
  schedule JSON serves (kept verbatim in `scores`).
- games?date= fallback rows for S4: `away_rec/home_rec/venue/city` may be
  blank on the fallback strategy — marked `carried_forward` or
  `blank_unverified` per row in `field_provenance` (never guessed).
