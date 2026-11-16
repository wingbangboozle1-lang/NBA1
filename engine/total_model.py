"""Total model: possessions × points-per-possession, not average of team scoring averages.

Total = (PACE_home + PACE_away)/2 × (OffRtg_home + OffRtg_away)/2 / 100 × 2
      = possessions × league-average points per possession × 2
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

def run():
    teams = read_json("data/teams_advanced_2026_27.json")["rows"]
    tmap = {r["abbr"]: r for r in teams}
    lines = read_json("docs/data/lines.json")["rows"]
    out = []
    for r in lines:
        away = r["away"]; home = r["home"]
        ta = tmap.get(away, {}); th = tmap.get(home, {})
        pace_a = ta.get("pace", 100.0); pace_h = th.get("pace", 100.0)
        ortg_a = ta.get("ortg", 110.0); ortg_h = th.get("ortg", 110.0)
        possessions = (pace_a + pace_h) / 2.0
        # points per possession = average efficiency / 100
        ppp = (ortg_a + ortg_h) / 2.0 / 100.0
        total = possessions * ppp * 2.0  # both teams
        # naive alternative: average of team scoring averages (old method)
        ppg_a = ortg_a * pace_a / 100.0
        ppg_h = ortg_h * pace_h / 100.0
        naive_total = ppg_a + ppg_h
        out.append({
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "possessions": round(possessions, 1),
            "ppp": round(ppp, 4),
            "total_poss_x_ppp": round(total, 1),
            "naive_team_scoring_avg_total": round(naive_total, 1),
            "difference": round(total - naive_total, 1),
            "method": "possessions × points-per-possession (official pace × official OffRtg), not team-scoring-average average",
            "src": r.get("src"),
        })
    write_json("data/total_model.json", {
        "_meta": {
            "method": "Total = possessions × PPP, where possessions = avg(pace_home, pace_away) "
                      "and PPP = avg(OffRtg_home, OffRtg_away)/100. Replaces the old average-of-team-scoring-averages method.",
        },
        "rows": out,
    })
    print(f"Total model: {len(out)} games")

if __name__ == "__main__":
    run()
