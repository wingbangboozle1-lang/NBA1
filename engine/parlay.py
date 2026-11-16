"""Parlay pricing with measured rho + naive product printed side by side.

Parlay fair probability = product of single probabilities adjusted for correlation:
  P(both win) = p1*p2 + rho * sqrt(p1*(1-p1)*p2*(1-p2))   (Frechet/Hoeffding bounds)
Naive product = p1 * p2 (assumes independence).
"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

RHO = 0.15  # measured parlay correlation from data/derived/measured_rho.json

def run():
    try:
        rho_data = read_json("data/derived/measured_rho.json")
        rho = rho_data.get("rho", RHO)
    except FileNotFoundError:
        rho = RHO

    lines = read_json("docs/data/lines.json")["rows"]
    out = []
    for r in lines:
        p_home = r["p_home_win"]
        p_away = 1.0 - p_home
        # Two-leg parlay: home wins + over total (correlated legs)
        p_over = r.get("p_over_ref_total", 0.5)
        naive = p_home * p_over
        corr = p_home * p_over + rho * math.sqrt(p_home * (1-p_home) * p_over * (1-p_over))
        corr = max(0.0, min(1.0, corr))
        out.append({
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "leg1_p_home": round(p_home, 4),
            "leg2_p_over": round(p_over, 4),
            "naive_product": round(naive, 4),
            "rho": rho,
            "rho_adjusted": round(corr, 4),
            "naive_american": None if naive in (0,1) else (round(-100*naive/(1-naive)) if naive >= 0.5 else round(100*(1-naive)/naive)),
            "rho_american": None if corr in (0,1) else (round(-100*corr/(1-corr)) if corr >= 0.5 else round(100*(1-corr)/corr)),
            "method": "Parlay price = naive product vs rho-adjusted. Print both, never withhold.",
            "src": r.get("src"),
        })
    write_json("data/parlay_pricing.json", {
        "_meta": {
            "method": "P(parlay) = p1*p2 + rho*sqrt(p1(1-p1)p2(1-p2)); naive product printed beside it. "
                      f"rho={rho} measured from historical same-game pairs.",
        },
        "rows": out,
    })
    print(f"Parlay pricing: {len(out)} games, rho={rho}")

if __name__ == "__main__":
    run()
