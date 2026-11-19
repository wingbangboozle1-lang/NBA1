# Verification log — session `arena/d66245d4-nba1`, 2026-11-19

This is the running record of what was read, when, from where, and what it was compared against.
It exists so that every claim on `live/live-horizon.html`, `live/decision-register.html` and
`live/requirement-coverage.html` can be audited back to an official page and a UTC time.

The rule this file obeys, taken from the board: **a value that could not be confirmed from an
official source is left blank and flagged, never inferred.** Where this seat's own reasoning
turned out to be wrong, the wrong version is kept in the record below with the correction beside
it, rather than edited away.

---

## 1. Access conditions, measured before any read was attempted

| Attempt | Result | Time (UTC) |
| --- | --- | --- |
| `curl https://www.nba.com/schedule` from the sandbox shell | `curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL`; HTTP status never received | 2026-11-19 06:58 |
| `curl https://api.github.com` | HTTP 200 | 2026-11-19 06:58 |
| `fetch_page https://www.nba.com/games?date=2026-11-19` through the platform channel | success, full scoreboard rendered | 2026-11-19 06:59 |

Consequence, stated because it bounds every claim: **all official reads in this pass were made
through the platform `fetch_page` channel, not from the sandbox.** The sandbox cannot open a TLS
session to `www.nba.com`. Byte-exact artifacts (PDF hashes, gamebook files) therefore cannot be
produced from here and are out of scope; the archive-integrity work belongs to COORDINATION §68.

---

## 2. Official pages read, with times

| # | Page | URL | Read (UTC) | What was extracted |
| --- | --- | --- | --- | --- |
| 1 | Games & scores, 2026-11-19 | https://www.nba.com/games?date=2026-11-19 | 06:59 | 4 games: ids, matchups, tips, records |
| 2 | Games & scores, 2026-11-20 | https://www.nba.com/games?date=2026-11-20 | 07:05 | 9 games, same fields, plus Cup group labels |
| 3 | Games & scores, 2026-11-21 | https://www.nba.com/games?date=2026-11-21 | 07:06 | 6 games |
| 4 | Games & scores, 2026-11-22 | https://www.nba.com/games?date=2026-11-22 | 07:08 | 7 games |
| 5 | Standings, all 30 teams | https://www.nba.com/standings?GroupTeam=league&Season=2026-27&Section=home | 07:10 | W-L for 30 teams |
| 6 | Teams Advanced, 30 rows | https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season | 07:14 | GP, W, L, OffRtg, DefRtg, NetRtg, PACE per team |
| 7 | Official injury-report index | https://official.nba.com/nba-injury-report-2026-27-season/ | 07:16 | the edition list for 2026-11-19 (8 editions, newest 01:45 AM ET) |
| 8 | One game page, as a spot check | https://www.nba.com/game/uta-vs-lal-0022600268 | 07:12 | Final, UTA 109 @ LAL 97, and the 11/19-11/22 cards with records |

The month grid printed on each games page was also read: November 19 = 4, 20 = 9, 21 = 6, 22 = 7,
and for the historical check, days 1–18 with 0 to 15 games each.

---

## 3. What each read was compared against, and the outcome

| Comparison | Repository file | Rows | Outcome |
| --- | --- | --- | --- |
| Game ids on the horizon | `data/derived/horizon_lines.json` | 26 | **26/26 PASS** — every id matches the official scoreboard |
| Tip times | same | 26 | **26/26 PASS** — matched to the minute, including the 1:00 PM and 3:30 PM matinees |
| Games per day | same + month grid | 4 days | **4/4 PASS** — 4 / 9 / 6 / 7 |
| Team records on each card | same (`records_as_captured`) | 26 | **23 PASS, 3 MISMATCH** — LAL printed 13-2 vs official 13-3; UTA printed 2-13 vs official 3-13 (two rows) |
| Standings, 30 teams | `data/official/standings_2026-11-19_9ff20954.json` | 30 | **30/30 PASS** |
| Team ratings (OffRtg, DefRtg, PACE) | `data/derived/team_stats_recut.json` | 30 | **28 PASS, 2 MISMATCH** — LAL and UTA, both the documented F-929-01 one-game lag, now absorbed by the official table |
| Result feed day counts | `data/official/results_feed_2026_27.json` | 18 days, 222 rows | **18/18 PASS**, and every row's quarters sum to its printed final |
| Ledger chain | `data/ledger/ledger.json` | 17 entries | **PASS** — `verify_ledger.py` exits 0 and prints `ledger chain OK` |
| Line formula | `data/derived/horizon_lines.json` | 26 | **26/26 PASS** — each published spread and total reproduced from the published formula to within 0.06 point |
| Injury edition basis | same (`_meta.inputs.injury_edition`) | 1 | **STALE** — the lines name 12:30 AM ET; the index lists 8 editions through 01:45 AM ET |

Total: **111 field-level comparisons passed**, 5 recorded findings.

---

## 4. The recomputation that turned a "lag" into a number

The repository already flagged the LAL/UTA lag (F-929-01) but had no measure of what it costs.
Using the model's own published formula —

    POSS   = (PACE_h + PACE_a) / 2
    PPP_h  = (OffRtg_h / 100) * (DefRtg_a / LEAGUE_DEF)
    PTS    = POSS * PPP
    SPREAD = PTS_h - PTS_a + HCA
    TOTAL  = POSS * (PPP_h + PPP_a)

— every game was re-priced twice: once with the ratings the file used, once with the ratings read
at 07:14Z. 23 of 26 games move by 0.05 point or less. Three move by more than one:

| Game | Δ spread | Δ total |
| --- | --- | --- |
| PHX@UTA (11/20) | +1.21 | −1.34 |
| SAC@LAL (11/20) | −1.41 | −2.19 |
| DAL@UTA (11/22) | +1.20 | −1.35 |

The first run of this recomputation reported residuals of up to 0.05 on the untouched games. That
was traced to rounding in the published line (one decimal place), not to a formula defect, and the
tolerance in the verifier is set to 0.06 for that reason — stated here rather than quietly
loosened.

---

## 5. The settlement record, re-measured

Nothing was taken from a summary block without re-adding it. The five settlement files were summed:

| Slate | Record | Singles units | Parlay units | SGP published / settled |
| --- | --- | --- | --- | --- |
| 2026-11-14 | 1-2-1 | −1.20 | −3.30 | 2 / 0 |
| 2026-11-15 | 5-4-0 | +0.60 | −3.30 | 2 / 0 |
| 2026-11-16 | 3-5-0 | −2.50 | −3.30 | 2 / 0 |
| 2026-11-17 | 1-4-0 | −3.40 | −3.30 | 2 / 0 |
| 2026-11-18 | 4-8-0 | −4.80 | −3.30 | 2 / 0 |
| **total** | **14-23-1** | **−11.30** | **−16.50** | **10 / 0** |

The 11/14 file leaves `total_units_settled` null, so the −23.30 figure quoted on the site is the sum
of the four files that carry the field. That limitation is printed on the page, not hidden.

Two further readings came out of the same pass and are the reason the decision register exists:

* **Calibration is inverted.** Mean published pick probability 0.7197 against a realised hit rate
  of 0.3784. The 0.70+ bucket went 7-11 while claiming 0.795.
* **The cause is measurable, not hypothetical.** The probability divides the spread by the standard
  deviation of *game margins* (16.714). The quantity that belongs there is the standard deviation of
  the *error in the spread*, which on these 38 settled tickets is sd 16.09 with a mean bias of
  +8.72 points. Required sigma: 18.303, i.e. 9.5% larger than the one used. The pick gate keeps
  |spread| >= 3.0, so it preferentially keeps the games where that bias is largest.

---

## 6. This seat's own errors, kept in the record

1. **A false flag was written and withdrawn.** This seat briefly recorded that
   `scripts/build_dashboard.py` built no `site/pages/strategies.html` while the navigation linked
   to it. Measured afterwards: the builder writes it at line 2394, the file exists, all 39 nav page
   entries exist on disk, and every external nav target resolves. The finding is retained in
   `data/content/verify_2026-11-19_d66245d4.json` as **V-D66-06 "withdrawn"** rather than deleted.
2. **A first pass of this report cited the wrong basis for the injury flag** — the script read
   `hz["inputs"]` when the field lives at `hz["_meta"]["inputs"]`, so the comparison ran against
   `None`. Fixed, re-run, and the corrected output is what the site now publishes.
3. **Four generated files belonging to another session's scope were committed by accident**
   (`data/derived/surface_gates.json`, `site/pages/bet.html`, `bet-surface.html`, `roll.html`) when
   `verify_all.py` re-derived wall-clock staleness. Reverted in their own commit, before any push.

---

## 7. Gates run on the final tree

| Gate | Result |
| --- | --- |
| `scripts/verify_all.py` | **VERIFY OK** — builders, checker and data audits, 0 failures |
| `scripts/verify_dashboard.py` | **VERIFY OK** — every table row has an official source link or an explicit no-source mark; 0 unmarked |
| `scripts/check_links.py` | **RESULT: PASS** |
| `scripts/check_rendered.py` | **RESULT: PASS** |
| `scripts/verify_integration.py` | **PASSED** — 0 errors |
| repo-wide broken-internal-link scan | **166 HTML pages, 0 broken** |
| unit tests (`scripts/test_*.py`) | **13 files, 0 failing** |
| ledger | `verify_ledger.py` → ledger chain OK, exit 0 |
| headless DOM render of the three new pages | all parse; tables, rows and links present |

---

## 8. What is deliberately not claimed

* No sportsbook price was observed, because none exists in this repository or on any official NBA
  page. Every "cover" in this pass means beating **the model's own published number**.
* The probabilities on this site are **not** shown to be better than the base rate; this pass shows
  they are worse than the ticket outcomes they were attached to.
* Byte-level PDF integrity was not re-verified here; the sandbox cannot reach the PDF host. That is
  §68's 154-file audit, cited as such.
* The two-estimator model internals were re-derived from their published formula but not re-fitted.
  A re-fit is a model decision, and the decision register explains why it should not precede a
  decision on the denominator.
