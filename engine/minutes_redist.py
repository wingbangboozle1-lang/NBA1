"""Minutes redistribution: top-8 minutes shares + replacement shares when a player is out.

For each team: the top-8 players' minutes shares (from the official minutes table)
and the replacement shares (how those minutes are redistributed when a player is out).
"""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json

def norm(name):
    return re.sub(r"\s+", " ", name.strip().lower())

def main():
    try:
        pl = read_json("data/raw/players_traditional.json")
        pl_rows = pl["rows"] if isinstance(pl, dict) and "rows" in pl else pl
        pl_cols = pl["cols"] if isinstance(pl, dict) and "cols" in pl else []
    except FileNotFoundError:
        pl_rows = []; pl_cols = []

    by_team = {}
    for row in pl_rows:
        d = dict(zip(pl_cols, row)) if pl_cols else row
        team = d.get("team") or d.get("TEAM_ABBREVIATION") or ""
        min_val = d.get("min") or d.get("MIN") or 0
        by_team.setdefault(team, []).append({
            "player": d.get("player") or d.get("PLAYER_NAME") or "",
            "minutes": float(min_val) if min_val else 0.0,
        })

    out = {}
    for team, plist in by_team.items():
        plist.sort(key=lambda x: -x["minutes"])
        total_min = sum(p["minutes"] for p in plist) or 240.0 * 82  # fallback
        top8 = plist[:8]
        top8_shares = {p["player"]: round(p["minutes"] / total_min, 4) for p in top8}
        # Replacement share: if a top-8 player is out, their minutes go to the bench
        # Pro-rata to remaining top-8 players (simple model, flagged as assumption)
        top8_total_share = sum(top8_shares.values())
        bench_share = 1.0 - top8_total_share
        replacement = {}
        for p in top8:
            pshare = p["minutes"] / total_min
            replacement[p["player"]] = {
                "lost_share": round(pshare, 4),
                "replacement_to_bench": round(pshare * 0.6, 4),   # 60% to bench (assumption)
                "replacement_to_top8_remaining": round(pshare * 0.4, 4),  # 40% to other top-8
            }
        out[team] = {
            "total_minutes_captured": round(total_min, 1),
            "players_captured": len(plist),
            "top8_players": [p["player"] for p in top8],
            "top8_minutes_shares": top8_shares,
            "top8_total_share": round(top8_total_share, 4),
            "bench_share": round(bench_share, 4),
            "replacement_shares": replacement,
            "method": "Top-8 minutes shares from official minutes table; replacement = 60% bench / 40% pro-rata to remaining top-8 (modelling choice, flagged).",
            "source": "data/raw/players_traditional.json (NBA.com)",
        }

    write_json("data/minutes_redistribution.json", {
        "_meta": {
            "method": "Per-team top-8 minutes shares + replacement shares when a player is out.",
        },
        "teams": out,
    })
    print(f"Minutes redistribution: {len(out)} teams")

if __name__ == "__main__":
    main()
