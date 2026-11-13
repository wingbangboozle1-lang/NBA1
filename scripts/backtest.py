#!/usr/bin/env python3
"""
backtest.py — walk-forward style check of the originating model on played games.

IMPORTANT HONESTY CONSTRAINT
----------------------------
The team statistics used as inputs are SEASON-TO-DATE as of 2026-11-13, which INCLUDES the
11/11 and 11/12 games being tested. That is look-ahead bias. A clean walk-forward backtest
requires point-in-time stats (each team's stats as of the morning of the game).

Because point-in-time snapshots were not captured before those games were played, this script
reports the result but LABELS IT CONTAMINATED and refuses to call it validation. It exists to
(a) prove the pipeline runs end to end, and (b) produce a number that a future session can
replace with a clean one.

Metrics reported
  - Mean absolute error of the projected total vs the actual total.
  - Mean absolute error of the projected margin vs the actual margin.
  - Straight-up winner accuracy.
  - Against-the-line accuracy using OUR own originated spread (not a sportsbook spread).
  - Whether the model beat a trivial baseline (league-average total / zero margin).
"""
import json
import os
import math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)


def model_game(home, away, adv, league_off, league_pace, margin_sd, total_sd):
    h, a = adv[home], adv[away]
    poss = h["pace"] + a["pace"] - league_pace
    pts_h = (h["off_rtg"] * a["def_rtg"] / league_off) * poss / 100.0
    pts_a = (a["off_rtg"] * h["def_rtg"] / league_off) * poss / 100.0
    return pts_h, pts_a, pts_h + pts_a, pts_h - pts_a


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main():
    teams = load("teams_advanced_2026_27.json")["rows"]
    played = load("played_games_2026_11_11_12.json")["games"]
    adv = {t["abbr"]: t for t in teams}
    league_off = sum(t["off_rtg"] for t in teams) / len(teams)
    league_pace = sum(t["pace"] for t in teams) / len(teams)

    lines = load("derived/lines.json")["_meta"]
    margin_sd = lines["empirical_dispersion"]["margin_sd"]
    total_sd = lines["empirical_dispersion"]["total_sd"]
    mean_total = lines["empirical_dispersion"]["mean_total"]

    rows = []
    for g in played:
        ph, pa, tot, mar = model_game(g["home"], g["away"], adv, league_off, league_pace, margin_sd, total_sd)
        actual_tot = g["away_pts"] + g["home_pts"]
        actual_mar = g["home_pts"] - g["away_pts"]
        p_home = norm_cdf(mar / margin_sd)
        rows.append({
            "date": g["date"], "game_id": g["game_id"], "matchup": f"{g['away']}@{g['home']}",
            "ot": g["ot"],
            "proj_total": round(tot, 1), "actual_total": actual_tot,
            "total_err": round(tot - actual_tot, 1),
            "proj_margin": round(mar, 1), "actual_margin": actual_mar,
            "margin_err": round(mar - actual_mar, 1),
            "model_p_home": round(p_home, 4),
            "model_pick": g["home"] if p_home >= 0.5 else g["away"],
            "actual_winner": g["home"] if actual_mar > 0 else g["away"],
            "ats_pick": g["home"] if mar >= 0 else g["away"],
            "ats_cover": (mar - actual_mar) * (1 if mar >= 0 else -1) > 0,
            "baseline_total": mean_total,
            "source_url": g["source_url"],
        })

    n = len(rows)
    mae_total = sum(abs(r["total_err"]) for r in rows) / n
    mae_margin = sum(abs(r["margin_err"]) for r in rows) / n
    mae_total_base = sum(abs(r["baseline_total"] - r["actual_total"]) for r in rows) / n
    su = sum(1 for r in rows if r["model_pick"] == r["actual_winner"]) / n
    ats = sum(1 for r in rows if r["ats_cover"]) / n
    n_atl = sum(1 for r in rows if abs(r["proj_margin"]) > abs(r["actual_margin"]))

    summary = {
        "n_games": n,
        "labelled": "CONTAMINATED — inputs are season-to-date and include the tested games",
        "mae_total_points": round(mae_total, 2),
        "mae_total_baseline_league_average": round(mae_total_base, 2),
        "mae_total_improvement_vs_baseline": round(mae_total_base - mae_total, 2),
        "mae_margin_points": round(mae_margin, 2),
        "straight_up_accuracy": round(su, 4),
        "straight_up_baseline_home_always": round(
            sum(1 for r in rows if r["actual_winner"] == r["matchup"].split("@")[1]) / n, 4),
        "ats_accuracy_vs_own_line": round(ats, 4),
        "n_close_calls_2pts": n_atl,
        "verdict": (
            "NOT VALIDATION. Look-ahead bias is present because the team stats cover the same "
            "games being predicted. Use this to confirm the pipeline runs, not to claim skill."
        ),
    }

    out = {"_meta": {"generated_by": "scripts/backtest.py", "generated_utc": "2026-11-13",
                     "sources": ["https://www.nba.com/games?date=2026-11-11",
                                 "https://www.nba.com/games?date=2026-11-12"]},
           "summary": summary, "rows": rows}
    with open(os.path.join(DATA, "derived", "backtest.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(json.dumps(summary, indent=2))
    print()
    for r in rows:
        print(f"{r['date']} {r['matchup']:9} proj {r['proj_total']:6.1f} act {r['actual_total']:4d} "
              f"err {r['total_err']:+6.1f} | margin proj {r['proj_margin']:+6.1f} act {r['actual_margin']:+4d} "
              f"| pick {r['model_pick']} {'OK' if r['model_pick'] == r['actual_winner'] else 'miss'}")


if __name__ == "__main__":
    main()
