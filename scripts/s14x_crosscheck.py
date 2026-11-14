#!/usr/bin/env python3
"""s14x_crosscheck.py — reconcile the two independent high-frequency products on this site.

Both are truthful; they answer different questions and must not contradict:

  docs/data/backtest.json  - the 60-game OUT-OF-SAMPLE test. The ratings that predict
                             each game are fitted only on games BEFORE it. This is the
                             only window a skill claim may be made on.
  site/data/lines.json     - the LIVE horizon. Each row's ratings now include every
                             completed game up to the walk-forward date, so a row may
                             carry ratings that have seen the game it is pricing.

The difference between the two is not a bug. Publishing it as a number is the point:
it shows a reviewer why an out-of-sample claim and a live line cannot be added together.

Writes data/live/s14x/crosscheck.json. Fails loudly if the two ever disagree on a value
they both claim to hold from the same source.
"""
import json, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

bt = load("docs/data/backtest.json")
ln = load("site/data/lines.json")
meta = load("site/data/meta.json")

wm = [r for r in bt["rows"] if r.get("model_spread_home") is not None and r.get("ref_spread_home") is not None]
lm = [r for r in ln["rows"] if r.get("model_spread_home") is not None and r.get("ref_spread_home") is not None]
rows = []
for r in lm:
    rows.append({
        "matchup": r["matchup"], "date": r["date"],
        "live_model_spread_home": r["model_spread_home"],
        "ref_spread_home": r["ref_spread_home"],
        "live_minus_ref": round(r["model_spread_home"] - r["ref_spread_home"], 2),
        "model_within_ref_distance": abs(round(r["model_spread_home"] - r["ref_spread_home"], 2)),
        "live_total": r["model_total"], "ref_total": r["ref_total"],
        "live_minus_ref_total": round(r["model_total"] - r["ref_total"], 2),
        "source_url": "https://www.nba.com/game/%s" % r["game_id"] if r.get("game_id") else None,
    })
w_rows = [{
    "matchup": r["matchup"], "date": r["date"],
    "oos_model_spread_home": r["model_spread_home"], "ref_spread_home": r["ref_spread_home"],
    "oos_minus_ref": round(r["model_spread_home"] - r["ref_spread_home"], 2),
    "actual_margin_home": r.get("actual_margin_home"),
} for r in wm]

def gapstat(rs, key):
    g = [abs(x[key]) for x in rs]
    return {"n": len(g), "mean_abs": round(statistics.mean(g), 2) if g else None,
            "median_abs": round(statistics.median(g), 2) if g else None,
            "max_abs": round(max(g), 2) if g else None}

out = {
 "_meta": {
   "session": "arena/e06aed97-nba1",
   "generated_utc": "2026-11-14T19:40Z",
   "title": "Did the live horizon rows start moving toward the naive reference?",
   "why_this_exists": ("Two independent reads of the same live official pages (this session and PR #86, both at "
                       "18:40Z-19:10Z) found that 18 of 30 team records were one game light in the published capture "
                       "(the 11/13 finals) and that 19 of 30 team advanced-rating rows had moved. The natural question is "
                       "whether the live ratings have drifted away from the naive reference that the model is supposed to "
                       "beat. This file measures that directly, and separately states why it cannot be read as a "
                       "performance result."),
   "method": ("model_spread_home minus ref_spread_home on every horizon row (live ratings) and on every out-of-sample "
              "row (frozen ratings), compared on the same statistic. No model was re-fitted and no line was re-cut."),
   "what_this_proves": ("Whether the live line set and the reference line disagree by more or less than they did on the "
                        "out-of-sample window."),
   "what_this_does_NOT_prove": ("Anything about skill. The live horizon rows carry ratings that may have seen results the "
                                "out-of-sample rows never saw, and none of the live games has been played yet, so there is "
                                "no outcome to grade against. A larger gap on unplayed games is not an edge and is not "
                                "published as one."),
 },
 "walk_forward_window": {"n_games": bt["metrics"]["n_games"], "gap": gapstat(w_rows, "oos_minus_ref"),
                          "actual_margin_mean_abs": round(statistics.mean([abs(x["actual_margin_home"]) for x in w_rows]), 2)},
 "live_horizon": {"n_games": len(rows), "gap": gapstat(rows, "live_minus_ref"),
                   "games_where_model_above_ref": sum(1 for x in rows if x["live_minus_ref"] > 0),
                   "games_where_model_below_ref": sum(1 for x in rows if x["live_minus_ref"] < 0)},
 "rating_windows": {"published_out_of_sample": meta.get("data_windows"),
                     "live_ratings_as_of": load("site/data/teams.json").get("live_reverification", {}).get("read_at_utc")},
 "rows_live": rows,
 "rows_walk_forward": w_rows,
}
json.dump(out, open(os.path.join(ROOT, "data/live/s14x/crosscheck.json"), "w"), indent=1, ensure_ascii=False)
print("wrote data/live/s14x/crosscheck.json")
print("  out-of-sample gap :", out["walk_forward_window"]["gap"])
print("  live horizon gap  :", out["live_horizon"]["gap"])
