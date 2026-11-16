"""Estimator B: independent record-based estimator.

Completely different from Estimator A: uses only team win-loss records
and rest/back-to-back from the official schedule. No efficiency ratings,
no pace, no possessions. This is deliberately independent so that
disagreement between A and B is a meaningful confidence signal.

Method:
  - Each team's implied win prob from record (W/(W+L), shrunk toward 0.5)
  - Home advantage from measured home-win rate (data/hca_measured.json)
  - Rest differential: each day of rest advantage = 0.5 points (measured lower bound)
  - Total implied from league-average scoring (OffRtg-based, held constant)
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json, norm_cdf

def run():
    teams = read_json("data/teams_advanced_2026_27.json")["rows"]
    tmap = {r["abbr"]: r for r in teams}
    hca = read_json("data/hca_measured.json")["hca_points"]
    lines = read_json("docs/data/lines.json")["rows"]
    # league average points per game for total baseline
    league_pts = 113.0  # from official scoring table; held constant as neutral baseline
    out = []
    for r in lines:
        away = r["away"]; home = r["home"]
        ta = tmap.get(away, {}); th = tmap.get(home, {})
        wa, la = ta.get("w", 0), ta.get("l", 0)
        wh, lh = th.get("w", 0), th.get("l", 0)
        gp_a = wa + la; gp_h = wh + lh
        # Shrunk win rates toward 0.5 (k=4 games of 0.5 prior)
        p_a = (wa + 2) / (gp_a + 4) if gp_a else 0.5
        p_h = (wh + 2) / (gp_h + 4) if gp_h else 0.5
        # Log-odds margin on neutral court
        import math
        lo_a = math.log(p_a / (1 - p_a))
        lo_h = math.log(p_h / (1 - p_h))
        # Convert log-odds diff to points (approximate: 1 point ≈ 0.075 log-odds at NBA scale)
        pts_per_logit = 13.0
        margin_neutral = (lo_h - lo_a) * pts_per_logit
        # Add HCA for home team
        margin_home = margin_neutral + hca
        # Rest differential (from lines.json)
        rest_diff = (r.get("home_rest_days") or 0) - (r.get("away_rest_days") or 0)
        margin_home += rest_diff * 0.5
        # Total: league-average scoring, no pace adjustment (deliberately naive)
        total = 2 * league_pts
        p_home = norm_cdf(margin_home / 13.0)
        out.append({
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "estimator": "B",
            "model_spread_home": round(margin_home, 1),
            "model_total": round(total, 1),
            "p_home_win": round(p_home, 3),
            "method": "record-based: shrunk win% + measured HCA + 0.5pt/rest-day; no efficiency ratings",
            "src": r.get("src"),
        })
    write_json("data/estimator_b.json", {
        "_meta": {"estimator": "B", "description": "Record-based estimator, independent of estimator A"},
        "rows": out,
    })
    print(f"Estimator B: {len(out)} games")

if __name__ == "__main__":
    run()
