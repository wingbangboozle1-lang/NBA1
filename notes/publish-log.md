# Publish log

Session `arena-7cfd203a` · branch `arena/7cfd203a-nba1` · season 2026-27 · built 2026-11-13.

## Commits in this build

| Commit | What it contains |
|---|---|
| `cbea9d1` | `COORDINATION.md` task board; claimed T01–T12 for this session |
| `b649450` | Verified datasets: team advanced, team scoring + opponent, players, schedule 11/13–11/16, injury report 11/13, `verify_data.py` |
| `a7f9e41` | Analytics layer: calibrated line origination, correlations, backtest, injury impact, gated strategies, rules/glossary/questions/suggestions, `verify_inline.py` |
| `b639cfe` | Site build: 14 pages generated from `data/`, `check_links.py` |
| (this) | Publish record, `COORDINATION.md` §3/§6 backfill |

## Verification run before publish

Run in this order; every command must exit 0:

| Command | Expected | Observed |
|---|---|---|
| `python3 scripts/verify_data.py` | `errors=0` | `errors=0  unverified_fields=22  passed_checks=15` |
| `python3 scripts/verify_inline.py` | all checks pass | `18/18 passed, failures=0` |
| `python3 scripts/check_links.py` | `RESULT: PASS` | `internal broken 0`, `non-approved hosts 0`, `rows without a source 0` |
| `python3 scripts/build_site.py` | pages written | `wrote 14 pages` |

Verification scripts, in order of what they protect:

1. **`verify_data.py`** — captured data against official sources. Provenance hosts, blank-field
   accounting, schedule W-L reconciliation, pace against possessions, ratings against scoring, the
   scoring identity, played-game integrity, minutes monotonicity, absence-class consistency.
2. **`verify_inline.py`** — derived outputs. Invented values, rounding reconstruction, probability
   ranges, per-row sourcing, backtest self-consistency, correlation tiers, double-counted injuries,
   false validations, the null control, and implausible totals.
3. **`check_links.py`** — the published site. Broken internal links, non-approved external hosts, and
   table rows without a source link.

## What is deliberately not claimed

* **No sportsbook price was reachable**, so every ROI figure assumes a standard −110 price. This is
  stated in `data/derived/strategies.json` and on the leaderboard page.
* **The 14-game backtest is look-ahead contaminated.** Team ratings were captured on 11/13 and therefore
  include the 11/11 and 11/12 games being predicted. The `CONTAMINATED` label is carried in the data and
  shown on the site; the 78.6% straight-up rate is not presented as skill.
* **External link HTTP status was not tested.** Outbound access to `*.nba.com` is blocked from this
  sandbox. `check_links.py` verifies the approved host, and says so in its output.
* **No strategy is validated.** 0 of 8. Reward payable is zero.

## Irregularities carried forward

Logged in full in `COORDINATION.md` §3.0 and on `docs/pages/flagged.html`. Summary: one fabricated row
found and removed by cross-check (Darius Garland was never on the 11/13 report), a play-probability
inversion bug, a look-ahead grading method, a rounding-order defect, a nav-depth defect, the null control
passing 4/6 gates, 79/88 injury rows without verified minutes, and the absence of any price source.

None of these blocked publication, which is the rule the brief sets: they are published, labelled, and
left visible rather than hidden or silently corrected.
