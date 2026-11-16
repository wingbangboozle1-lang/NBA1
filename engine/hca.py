"""Home-court advantage pinned to the measured home-win rate.

HCA (in points) is derived from the official home-win rate across the
completed games window, not fitted freely. The conversion uses the model's
margin sigma: HCA_points = sigma_margin * norm_ppf(home_win_rate).
"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json, norm_ppf

def compute_hca(completed_games, sigma_margin):
    """completed_games: list of dicts with home_won (bool) or home_pts/away_pts."""
    n = len(completed_games)
    if n == 0:
        return 0.0, 0.0, 0, None
    home_wins = sum(1 for g in completed_games if g.get("home_won", g.get("home_pts",0) > g.get("away_pts",0)))
    rate = home_wins / n
    hca_points = sigma_margin * norm_ppf(rate)
    return round(hca_points, 2), round(rate, 4), n, None

def main():
    # Read completed games from the backtest data
    bt = read_json("docs/data/backtest.json") if os.path.exists("docs/data/backtest.json") else None
    if bt is None:
        # Try building from games.json
        games = read_json("data/games.json")
        completed = [g for g in games["games"] if "away_pts" in g and "home_pts" in g]
        for g in completed:
            g["home_won"] = g["home_pts"] > g["away_pts"]
    else:
        completed = bt["rows"]
        for g in completed:
            g["home_won"] = g["home_won"] if "home_won" in g else (g["home_pts"] > g["away_pts"])

    # sigma_margin from model fit
    fit = bt.get("fit", {}) if bt else {}
    sigma_m = fit.get("sigma_margin", 13.0) if bt else 13.0

    hca_pts, rate, n, _ = compute_hca(completed, sigma_m)
    write_json("data/hca_measured.json", {
        "_meta": {
            "method": "HCA_points = sigma_margin * norm_ppf(home_win_rate), "
                      "pinned to the measured home-win rate from official completed games. "
                      "Not a free parameter.",
            "home_win_rate": rate,
            "home_wins": sum(1 for g in completed if g.get("home_won")),
            "games": n,
            "sigma_margin": sigma_m,
            "source": "data/games.json + docs/data/backtest.json (official NBA.com scores)",
        },
        "hca_points": hca_pts,
        "home_win_rate": rate,
    })
    print(f"HCA: {hca_pts} points from home-win rate {rate:.4f} ({n} games, sigma={sigma_m})")

if __name__ == "__main__":
    main()
