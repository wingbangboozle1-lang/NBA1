#!/usr/bin/env python3
"""Gate: the published home-court advantage must still equal the measurement.

Requirement R09 says home-court advantage is pinned to the MEASURED home-win rate
instead of being fitted freely.  A pin is only real if something checks that it is
still the measurement: the published model sat on 102/193 = 0.5285 for sixteen hours
after the league's own standings had moved to 102/196 = 0.5204, the capture that
produced it carried a caveat naming three games still in progress, and nothing failed
(COORDINATION 54/52 request R-50-B).  This is that something.

It recomputes everything from the committed captures - it does not read the anchor
block and agree with itself:

  1. the home-win rate from the HOME column of the newest official standings capture;
  2. the same rate from the independent finals corpus, through the shared
     verified-finals predicate (a 0-0 placeholder for an unplayed game is not a game);
  3. sigma from the finals margins;
  4. the pin from sigma * Phi^-1(rate);

and then requires the published block to match, with each measurement carrying its own
denominator (that pairing was flag F116).

Exit 0 = the published pin is the current measurement.  Exit 1 = stale, mismatched or
unverifiable, with the numbers printed.

Run:  python3 scripts/test_hca_pin.py [--relax-currency]
"""
import argparse
import glob
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from model_v2 import is_verified_final, load_results  # noqa: E402


def ppf(p):
    """Acklam's inverse normal CDF approximation (same one the engine uses)."""
    a = [-3.96968302866e+01, 2.20946098427e+02, -2.75928510446e+02,
         1.38357751867e+02, -3.06647980661e+01, 2.50662827745e+00]
    b = [-5.44760987982e+01, 1.61585836858e+02, -1.55698979859e+02,
         6.68013118877e+01, -1.32806815528e+01]
    c = [-7.78489400243e-03, -3.22396458041e-01, -2.40075827716e+00,
         -2.54973253934e+00, 4.37466414146e+00, 2.93816398286e+00]
    d = [7.78469570904e-03, 3.22467129070e-01, 2.44513413714e+00,
         3.75440866190e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relax-currency", action="store_true",
                    help="warn instead of failing when the newest standings capture is "
                         "older than the newest settled game day")
    args = ap.parse_args()
    fails, notes = [], []

    caps = sorted(glob.glob(os.path.join(ROOT, "data", "official", "standings_2026-*.json")))
    if not caps:
        print("FAIL: no official standings capture in data/official/")
        return 1
    cap = caps[-1]
    doc = json.load(open(cap, encoding="utf-8"))
    hw = hg = 0
    for r in doc["rows"]:
        h, l = str(r["home"]).split("-")
        hw += int(h)
        hg += int(h) + int(l)
    assert hg, "no home games in the standings capture"
    rate = hw / hg
    notes.append("standings capture %s: %d home wins in %d home games = %.4f"
                 % (os.path.basename(cap), hw, hg, rate))
    # the capture's own identity checks must hold before anything is trusted
    if hw != sum(int(str(r["road"]).split("-")[1]) for r in doc["rows"]):
        fails.append("standings capture's home_wins != road_losses - the read itself is bad")

    finals = [g for g in load_results() if is_verified_final(g) and not g.get("neutral")]
    fhw = sum(1 for g in finals if g["home_pts"] > g["away_pts"])
    f_rate = fhw / len(finals) if finals else None
    notes.append("finals corpus: %d verified finals, %d home wins = %s"
                 % (len(finals), fhw, ("%.4f" % f_rate) if f_rate else "n/a"))
    if any(not is_verified_final(g) for g in finals):
        fails.append("a non-final row is in the finals set")
    sigma = statistics.pstdev([g["home_pts"] - g["away_pts"] for g in finals])
    expected = round(sigma * ppf(rate), 2)
    notes.append("sigma(finals margins) = %.4f -> expected pin = %.2f points" % (sigma, expected))

    pub = json.load(open(os.path.join(ROOT, "data", "derived", "horizon_lines_v2.json"),
                         encoding="utf-8"))
    blk = (pub.get("_meta") or {}).get("home_court_anchor")
    if not blk:
        blk_path = os.path.join(ROOT, "data", "derived", "model_report_v2.json")
        blk = (json.load(open(blk_path, encoding="utf-8")) or {}).get("home_court_anchor")
    if not blk:
        print("FAIL: no published home_court_anchor block to check")
        return 1

    if round(blk.get("measured_home_win_rate") or -1, 4) != round(rate, 4):
        fails.append("published home-win rate %s != current measurement %.4f "
                     "(re-run scripts/build_horizon_v2.py after re-reading the standings)"
                     % (blk.get("measured_home_win_rate"), rate))
    if abs((blk.get("hca_points") or -99) - expected) > 0.02:
        fails.append("published pin %s points != derived %s points"
                     % (blk.get("hca_points"), expected))
    if abs((blk.get("sigma_margin_used") or -99) - round(sigma, 2)) > 0.02:
        fails.append("published sigma %s != measured %s" % (blk.get("sigma_margin_used"),
                                                             round(sigma, 2)))
    fin = blk.get("final_scores_measurement") or {}
    if not fin:
        fails.append("the published block no longer labels the finals measurement with its "
                     "own denominators (regression of flag F116)")
    else:
        if fin.get("home_games") != len(finals):
            fails.append("published finals denominator %s != %d finals in the corpus"
                         % (fin.get("home_games"), len(finals)))
        if fin.get("corpus_rows", 0) < fin.get("finals_counted", 0):
            fails.append("the finals measurement counts more games than the corpus holds")
        if "rows_excluded_as_unplayed" not in fin:
            fails.append("the finals measurement does not disclose how many unplayed rows "
                         "it excluded - the exclusion is the point of the predicate")
        if fin.get("finals_counted") is not None and \
                fin.get("corpus_rows") != fin.get("finals_counted") + sum(
                    (fin.get("rows_excluded_as_unplayed") or {}).values()):
            fails.append("corpus rows != finals + excluded: the exclusion count does not "
                         "account for the whole corpus")
    sm = blk.get("standings_measurement") or {}
    if sm and sm.get("home_games") not in (None, hg):
        fails.append("published standings denominator %s != %d home games in the capture"
                     % (sm.get("home_games"), hg))

    # currency: the capture must not be older than the newest settled game day
    settled = sorted(glob.glob(os.path.join(ROOT, "data", "settlement", "settlement_*.json")))
    if settled and doc.get("retrieved_utc"):
        newest_day = os.path.basename(settled[-1]).replace("settlement_", "").replace(".json", "")
        retrieved_day = str(doc["retrieved_utc"])[:10]
        if retrieved_day < newest_day:
            msg = ("the standings capture was read %s, before the newest settled game day %s"
                   % (retrieved_day, newest_day))
            (notes if args.relax_currency else fails).append(
                ("WARN: " if args.relax_currency else "") + msg)

    for n in notes:
        print("  " + n)
    if fails:
        print("HCA PIN GATE FAILED (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("HCA PIN OK - the published pin (%.2f points) is the current measurement "
          "(%.4f from the standings, %.4f from %d verified finals, sigma %.2f)"
          % (expected, rate, f_rate, len(finals), sigma))
    return 0


if __name__ == "__main__":
    sys.exit(main())
