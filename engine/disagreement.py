"""Disagreement between Estimator A and Estimator B as the headline confidence signal.

For each game: spread_disagreement = |spread_A - spread_B|, total_disagreement = |total_A - total_B|.
High disagreement = low confidence; publish disagreement as headline, blend underneath.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

def run():
    a = {r["matchup"]: r for r in read_json("data/estimator_a.json")["rows"]}
    b = {r["matchup"]: r for r in read_json("data/estimator_b.json")["rows"]}
    out = []
    for m, ra in a.items():
        rb = b.get(m)
        if not rb:
            continue
        spr_a = ra["model_spread_home"]; spr_b = rb["model_spread_home"]
        tot_a = ra["model_total"]; tot_b = rb["model_total"]
        spr_dis = abs(spr_a - spr_b)
        tot_dis = abs(tot_a - tot_b)
        # Disagreement score: combined, normalised
        dis_score = spr_dis + tot_dis / 10.0
        blend_spread = (spr_a + spr_b) / 2.0
        blend_total = (tot_a + tot_b) / 2.0
        blend_p_home = (ra["p_home_win"] + rb["p_home_win"]) / 2.0
        out.append({
            "date": ra["date"], "matchup": m, "away": ra["away"], "home": ra["home"],
            "spread_a": spr_a, "spread_b": spr_b, "spread_disagreement": round(spr_dis, 1),
            "total_a": tot_a, "total_b": tot_b, "total_disagreement": round(tot_dis, 1),
            "disagreement_score": round(dis_score, 2),
            "confidence": "LOW" if dis_score > 6.0 else ("MEDIUM" if dis_score > 3.0 else "HIGH"),
            "blend_spread_home": round(blend_spread, 1),
            "blend_total": round(blend_total, 1),
            "blend_p_home": round(blend_p_home, 3),
            "headline": f"Disagreement {round(dis_score,1)} - {('LOW' if dis_score > 6.0 else ('MEDIUM' if dis_score > 3.0 else 'HIGH'))} confidence",
            "src": ra.get("src"),
        })
    out.sort(key=lambda x: -x["disagreement_score"])
    write_json("data/disagreement.json", {
        "_meta": {
            "method": "Headline = disagreement between independent estimators A (efficiency) and B (record-based). "
                      "Blend underneath. High disagreement = low confidence. Not a single blended rating as headline.",
        },
        "rows": out,
    })
    print(f"Disagreement: {len(out)} games")

if __name__ == "__main__":
    run()
