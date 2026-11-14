# Session notes — arena/f80dcc4a-nba1 (task W01–W08, window 2026-11-13 → 2026-11-17)

Session ID: `arena/f80dcc4a-nba1` · Branch: `arena/f80dcc4a-nba1` · Board: COORDINATION.md §13.
Data captured 2026-11-14T00:52–01:32Z. Every number below is re-derived from a stored capture by
`python3 scripts/verify_session_w.py` (502 checks, all passing at publication).

## 1. What this batch changed

| Area | Before | After |
|---|---|---|
| Game window | 31 games, 11/13–11/16 | 36 games, 11/13–11/17 (9 / 5 / 9 / 8 / 5) |
| RecordLine-1 picks | 26 picks | 30 picks (11/13 batch frozen and reproduced; 25 new rows 11/14–11/17) |
| Prop-combo rows | 62 (LAL/CHA/TOR blank) | 72, zero blanks |
| Injury basis | one edition (05:15 PM ET, 11/13 only) | per-date: 11/13 → 05:15 PM ET; 11/14 → 08:00 PM ET; 11/15–17 → gated (not yet published) |
| Unattributed injury rows | 20 (5:15 PM edition) | 20 + 11 (both editions shown with own source links) |

## 2. Sources captured (verbatim, in `data/raw/captures/session-w/`)

| File | URL | Read (UTC) | Used for |
|---|---|---|---|
| `games_2026-11-13_state_2026-11-14T0055Z.txt` | nba.com/games?date=2026-11-13 | 00:55Z | 11/13 live state (2 games in Q2, 4 pregame); no finals at capture |
| `games_2026-11-14_2026-11-14T0052Z.txt` | nba.com/games?date=2026-11-14 | 00:52Z | 5 games, records, leaders |
| `games_2026-11-15_2026-11-14T0131Z.txt` | nba.com/games?date=2026-11-15 | 01:31Z | 9 games, records, leaders |
| `games_2026-11-16_2026-11-14T0132Z.txt` | nba.com/games?date=2026-11-16 | 01:32Z | 8 games, records, leaders |
| `games_2026-11-17_2026-11-14T0109Z.txt` | nba.com/games?date=2026-11-17 | 01:09Z | 5 games (calendar 5 GAMES cell), venues, records, leaders |
| `injury_hub_2026-11-14T0108Z.txt` | official.nba.com/nba-injury-report-2026-27-season/ | 01:08Z | edition list + submission policy |
| `injury_report_2026-11-13_08_00PM_chunk0/1.txt` | ak-static.cms.nba.com/.../Injury-Report_2026-11-13_08_00PM.pdf | 01:10Z | newest published edition; rows for all five 11/14 games |

Key facts from the captures, in the exact form the pages print them:
- 11/17 slate: NYK@TOR (Scotiabank Arena), POR@MIN (Target Center), DET@SAS (Frost Bank Center),
  UTA@LAC (Intuit Dome), CHA@LAL (Crypto.com Arena) — IDs 0022600253–0022600257, tip times 7:30/8:00/
  8:00/10:30/11:00 PM ET; the 11/17 calendar strip prints "5 GAMES".
- LAL/CHA/TOR season leaders are now displayed on the official pages (they read "-" on 11/13):
  Luka Dončić (LAL) 38.6 7.5 7.6 · Naz Reid (CHA) 17.3 8.5 2.2 · RJ Barrett (TOR) 21.3 6.7 4.1.
- 08:00 PM ET injury edition prints rows for all five 11/14 games. NOT YET SUBMITTED teams:
  New Orleans, Cleveland, Memphis, Chicago, Miami. Newest edition on the hub at 01:08Z.
  The 11/14 12:00 PM file returns AccessDenied = not yet published (dead end, do not retry now).

## 3. Structured files written

- `data/raw/records_2026-11-14.json` — 30 teams, W-L as printed on the official slate pages at
  00:52–01:32Z (11/13 games were still in progress and are in no record). `displayed_on_date_pages`
  lists each team's second source; GSW/OKC/SAC appear on one fetched page each → single-source,
  cross-checked against `injuries_0515.json` and flagged (W-F3).
- `data/raw/injury_report_2026-11-13_08_00PM.json` — 111 attributed rows + 11 unattributed.
  Team attribution was carried ONLY from an edition that printed the row (03:00 PM / 05:15 PM ET),
  with the carry source recorded per row in `team_source`. Section/alphabetical continuity is
  recorded as a note only and never used (W-F4).
- `data/raw/official_results_2026-11-13.json` — 9 games, game state at 00:55Z (NYK@IND 35–44 Q2,
  MIL@ORL 33–49 Q2, 4 pregame, 3 cards not shown mid-chunk). `followup_captures: []` — finals are
  captured at the queued T2 passes (≈02:00Z and ≈05:00Z) and appended there (W-F5).
- `data/raw/official_schedule_capture_2026-11-14.json` — 36 rows 11/13–11/17 with venues and
  `tip_confirmed_by` provenance.
- `data/leaders.json` — 30 rows, 0 blanks; 27 values re-verified identical to the 11/13 capture;
  3 filled from the official pages (above). "Nikola Jokić" now matches the official spelling
  (was ASCII "Jokic"; corrected under the verify_session_w W3 check).
- `data/slate_full.json` — 5 slates / 36 games; per-slate `records_as_of` basis stamps; 11/13 rows
  frozen at the published basis.
- `data/schedule_2026_11_13_to_16.json` — 36 rows (11/17 appended; filename kept for continuity).
- `data/archive/originated_lines_2026-11-13T2245Z.json` — verbatim archive of the published 11/13
  batch before regeneration.

## 4. Generation & verification

Order: `build_edge_site.py` (RecordLine-1 → `data/originated_lines.json`, lines.html, gameflow.html)
→ `injury_impact.py` (rotation layer, 11/13-only adjustment semantics kept) → `originate_lines.py`
(efficiency model → `data/derived/lines.json`, now 36 games / 92 props) → `build_site.py` (15 docs
pages + root-page count/prose sync).

Verification, both green at publication:
- `python3 scripts/verify_session_w.py` — 502 value checks + link/row audit: schedule field-by-field
  vs the capture; every record and leader re-parsed from capture text; every injury player line found
  verbatim in its source chunk; frozen 11/13 game/parlay rows byte-identical to the archive (prop
  rows identical modulo the documented Jokić spelling); per-date status gates in prop rows; every
  table row on lines/gameflow/review carries an official source link; W-F1…W-F8 published.
- `python3 scripts/verify_all.py` — VERIFY OK: builders + checkers, 36 games, 36 published rows
  compared vs the official games pages, 0 mismatches, calendar counts 9/5/9/8/5 match.

## 5. Irregularities (flagged, not silently resolved)

Flags W-F1…W-F8 live on `review.html` (session section "arena-f80dcc4a-nba1"): mixed pick bases
(frozen 11/13 vs re-stamped 11/14–17), 11/14 injury basis = the 11/13 08:00 PM edition (game-day
editions will supersede), page-break rows kept unattributed
(six OKC, two DET despite extraction-order clues), post-final record refresh queued (W-F5/F-C02),
duplicate matchups NYK@TOR and POR@MIN inside 48h as officially scheduled (W-F6), Martin, Caleb
team-cell conflict between editions (05:15 PM prints CLE — cross-source wins, W-F7), and the
corrected 11/14 back-to-back list (Miami was missing; now CLE/MIA/CHI/MEM/NOP, W-F8). W-F3
(GSW/OKC/SAC single-source records) was resolved at the T2 early pass, which printed the three
missing game cards with identical record strings.

## 6. What is deliberately NOT done here

- No pick is re-derived after tip (generate-once rule); results enter `official_results_2026-11-13.json`
  only, and refreshed records (W-F5) update records only.
- No injury status is shown for 11/15–11/17 games: those rows say "report not yet published (G-INJ)"
  and gate everything; blank never means "no injuries".
- No team cell is inferred for page-break rows, no totals/props beyond what official pages print,
  no market numbers (no odds feed — gates G4/G5 stay blocked).
