# verify/2026-11-16-23ec1e32 — session arena/23ec1e32-nba1 (COORDINATION §55)

Evidence for the measured-HCA re-derivation (W01), measured-rho pricing (W02),
Lines & Picks disagreement headline + rotation column (W03), projection/bet split (W04),
register refresh (W05), captured 2026-11-16 ~19:1xZ.

## First-hand official reads
- https://www.nba.com/standings read via fetch_page at 18:3xZ, transcribed to
  data/official/standings_2026-11-16_1835Z_23ec1e32.json (30 rows; cross-checks
  home_wins==road_losses (102==102), road_wins==home_losses (94==94); delta vs the
  02:13Z capture exactly +3 games / +0 home wins / +3 road wins = the three late
  11/15 away wins HOU@WAS, ATL@MIL, OKC@SAC).
- Re-derivation checks run in-session (python, engine/model_v2 + committed corpus):
  - load_results() after the unplayed-row fix: 197 decided finals through 11/15
    (196 home/road + 1 neutral), 0 tied rows.
  - side/total r on the full 197-game corpus: -0.0354; on measured_rho's 74-final
    window after re-running scripts/measure_rho.py: -0.105 (p=0.370).
  - cross-game same-date margin pairs: r = 0.0120 on 808 pairs / 26 dates
    (register rho_2026_27.json says 0.0142 on n_pairs 1546 — confirmed in substance).
  - parlay pricing invariants: naive == round(p1*p2,4) on all 12 rows; every price
    inside the Frechet-Hoeffding band; joint at rho=0 reduces to the naive product
    to <1e-6.

## Gate battery (final, after register refresh) — all exit 0
- verify_hca_anchor.out — RESULT: the published anchor is current and reconciled
  (zero drift); sources agree at 0.5204; HCA published 0.87 == recomputed 0.87.
- check_links.out — RESULT: PASS
- check_rendered.out — RESULT: PASS
- verify_ledger.out — ledger chain OK
- verify_integration.out — PASSED, warnings published on the Flagged page (non-blocking)
- verify_dashboard.out — VERIFY OK (2701 official links + 104 explained no-source marks)
- check_site.out — every table row carries an official NBA/GitHub source link
- verify_all.out — FAILURES: 0 — VERIFY OK
- build_surfaces.py — gates G1 CLOSED, G2 CLOSED, G3 PASS, G4 PASS; projection rows 29;
  separation checks OK (no picks on bet-surface.html/bet.html while closed)

## Flags published this session
- F128 (Medium) — two measured-rho registers disagree (measurability + values);
  both published, reviewer picks the register of record.
- F129 (Low) — measured_rho.json had gone stale against its own corpus (66 vs 74
  finals); refreshed, with the process gap flagged.
- F116, F90, F83 annotated RESOLVED; F84 annotated ADVANCED (legacy path remains);
  F82 annotated (PDF retention claim stale; diff-chain gap restated).
