"""Estimator A: additive efficiency model (the existing engine model).

Outputs: home margin, total, and win probability for each upcoming game.
Reads from: docs/data/lines.json (produced by engine/pipeline.py).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

def run():
    lines = read_json("docs/data/lines.json")["rows"]
    out = []
    for r in lines:
        out.append({
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "estimator": "A",
            "model_spread_home": r["model_spread_home"],
            "model_total": r["model_total"],
            "p_home_win": r["p_home_win"],
            "method": "additive efficiency (ORTG/DRTG/pace, shrinkage k=2.8, HCA=2.0 flat)",
            "src": r.get("src"), "src_ratings": "S1",
        })
    write_json("data/estimator_a.json", {
        "_meta": {"estimator": "A", "description": "Additive four-factor efficiency model"},
        "rows": out,
    })
    print(f"Estimator A: {len(out)} games")

if __name__ == "__main__":
    run()
