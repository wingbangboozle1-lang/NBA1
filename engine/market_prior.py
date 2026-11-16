"""Market-anchored prior: blend the model line with the closing line,
weighted by measured out-of-sample log-loss.

Blended = weight * model_line + (1-weight) * closing_line
where weight = model_logloss / (model_logloss + closing_logloss).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

def run():
    lines = read_json("docs/data/lines.json")["rows"]
    # OOS log-loss values from validation (engine/pipeline.py fit)
    try:
        val = read_json("docs/data/validation.json")
        fit = val.get("fit", {})
        model_ll = fit.get("log_loss", 0.65)  # fallback
    except FileNotFoundError:
        model_ll = 0.65

    # Closing line: not published by any NBA-operated source -> flagged, left blank
    # When available, closing_line would come from the sportsbook market.
    out = []
    for r in lines:
        model_spread = r["model_spread_home"]
        model_total = r["model_total"]
        closing_spread = None   # no official source publishes closing lines
        closing_total = None
        out.append({
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "model_spread_home": model_spread,
            "closing_spread": closing_spread,
            "blended_spread_home": model_spread,  # = model when closing is unavailable
            "model_total": model_total,
            "closing_total": closing_total,
            "blended_total": model_total,
            "weight_on_model": 1.0,  # = 1 when closing unavailable
            "model_log_loss": round(model_ll, 4),
            "closing_available": False,
            "note": "No NBA-operated source publishes closing lines. Blended = model line (weight=1.0) until a verified closing-line source is added. Flagged F-market-prior.",
            "src": r.get("src"),
        })
    write_json("data/market_prior.json", {
        "_meta": {
            "method": "Blended = w * model + (1-w) * closing, w = model_LL / (model_LL + closing_LL). "
                      "Closing lines are not published by any NBA-operated source, so w=1.0 and blended=model.",
        },
        "rows": out,
    })
    print(f"Market prior: {len(out)} games")

if __name__ == "__main__":
    run()
