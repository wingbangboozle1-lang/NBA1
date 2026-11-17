#!/usr/bin/env python3
"""Re-measure the home-court pin on the current official finals corpus (R09).

The published pin was measured through 2026-11-15. Game day 2026-11-16 added
eight verified finals, so the number the site pins to has to be re-derived from
the corpus rather than carried forward. This script does exactly one thing:
read the official per-game feed, keep only rows the league marks Final whose
quarter scores sum to the printed final (the same rule the feed itself states),
and print the home-win rate, its Wilson 95% lower bound, and the points
equivalent HCA = sigma_margin * Phi^-1(rate).

Neutral-site games are excluded from the rate (the feed labels the 2026-11-07
Denver-Indiana game 'Neutral Site'); a game whose score the page does not print
is left out, never filled in.
"""
from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "official", "results_feed_2026_27.json")


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155043200e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def wilson_lower(k: int, n: int, z: float = 1.959963984540054) -> float:
    if n == 0:
        return 0.0
    p = k / n
    den = 1 + z*z/n
    centre = p + z*z/(2*n)
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (centre - margin) / den


def main() -> int:
    feed = json.load(open(FEED, encoding="utf-8"))
    rows = feed.get("rows", [])
    kept, skipped = [], {"not_final": 0, "zero_placeholder": 0,
                         "quarter_sum_mismatch": 0, "neutral_site": 0}
    for r in rows:
        if r.get("game_status") != 3:
            skipped["not_final"] += 1
            continue
        hp, ap = r.get("home_pts"), r.get("away_pts")
        if hp is None or ap is None:
            skipped["not_final"] += 1
            continue
        if hp == 0 and ap == 0:
            skipped["zero_placeholder"] += 1
            continue
        hq = r.get("home_quarters") or []
        aq = r.get("away_quarters") or []
        if hq and (sum(v or 0 for v in hq) != hp):
            skipped["quarter_sum_mismatch"] += 1
            continue
        if aq and (sum(v or 0 for v in aq) != ap):
            skipped["quarter_sum_mismatch"] += 1
            continue
        if r.get("neutral"):
            skipped["neutral_site"] += 1
            continue
        kept.append(r)
    n = len(kept)
    if not n:
        print("::error:: no decided games in the feed - refusing to publish a pin")
        return 2
    hw = sum(1 for r in kept if r["home_pts"] > r["away_pts"])
    rate = hw / n
    margins = sorted(r["home_pts"] - r["away_pts"] for r in kept)
    mu = sum(margins) / n
    sigma = math.sqrt(sum((m - mu) ** 2 for m in margins) / (n - 1)) if n > 1 else 0.0
    hca = sigma * norm_ppf(rate)
    out = {
        "title": "Home-court advantage pinned to the measured home-win rate (R09)",
        "generated_by": "scripts/measure_hca_ca442d3d.py",
        "session": "arena/ca442d3d-nba1",
        "corpus": {
            "source_file": "data/official/results_feed_2026_27.json",
            "source_url": "https://www.nba.com/games?date=YYYY-MM-DD (per game day)",
            "rows_in_feed": len(rows),
            "decided_rows_used": n,
            "skipped": skipped,
            "date_range": [min(r["date"] for r in kept), max(r["date"] for r in kept)],
        },
        "home_wins": hw,
        "home_win_rate": round(rate, 4),
        "wilson_lower_95": round(wilson_lower(hw, n), 4),
        "sigma_margin": round(sigma, 3),
        "mean_home_margin": round(mu, 3),
        "home_court_points": round(hca, 2),
        "rule": ("HCA is NOT fitted. It is the points equivalent of the measured "
                 "home-win rate: sigma_margin * Phi^-1(home_win_rate), computed on "
                 "finals whose quarter scores sum to the printed final."),
        "comparison": {},
    }
    published = os.path.join(ROOT, "data", "derived", "measured_constants_2026_27.json")
    if os.path.exists(published):
        mc = json.load(open(published, encoding="utf-8"))
        out["comparison"]["data/derived/measured_constants_2026_27.json"] = {
            "home_win_rate": mc.get("home_win_rate"),
            "home_court_points": mc.get("home_court_points"),
            "sigma_margin": mc.get("sigma_margin"),
            "n_final_games": mc.get("n_final_games"),
            "built_utc": mc.get("built_utc"),
        }
    legacy = os.path.join(ROOT, "data", "hca_measured.json")
    if os.path.exists(legacy):
        lm = json.load(open(legacy, encoding="utf-8"))
        out["comparison"]["data/hca_measured.json (legacy engine pin)"] = {
            "home_win_rate": lm.get("home_win_rate"),
            "hca_points": lm.get("hca_points"),
            "games": lm.get("_meta", {}).get("games"),
            "sigma_margin": lm.get("_meta", {}).get("sigma_margin"),
        }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
