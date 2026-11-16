"""Capture per-player game logs (minutes, points, rebounds, assists, opponent)
for players who appear on an injury report.

Usage:  python3 scripts/capture_gamelogs.py [injury_json] [output_dir]

Reads:  injury rows from data/injuries.json (or the pipeline output)
        player data from data/raw/players_traditional.json
Writes: data/player_gamelogs/<abbr>/<player>.json with per-game logs
"""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from common import read_json, write_json

def norm(name):
    return re.sub(r"\s+", " ", name.strip().lower())

def main():
    inj_path = sys.argv[1] if len(sys.argv) > 1 else "docs/data/injuries.json"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data/player_gamelogs"

    injuries = read_json(inj_path)
    rows = injuries["rows"] if isinstance(injuries, dict) and "rows" in injuries else injuries

    # Collect unique injured player names per team
    players_by_team = {}
    for r in rows:
        team = r.get("team")
        player = r.get("player")
        if team and player and r.get("status") not in (None, "NOT YET SUBMITTED"):
            players_by_team.setdefault(team, set()).add(player)

    # Load the official players traditional table (has season totals, not game logs)
    # The NBA.com players traditional table is season-to-date aggregates, not game-by-game.
    # True per-game logs require the NBA stats API which is not an official HTML page.
    # We record what we can: season minutes/pts/reb/ast per injured player.
    try:
        pl = read_json("data/raw/players_traditional.json")
        pl_rows = pl["rows"] if isinstance(pl, dict) and "rows" in pl else pl
        pl_cols = pl["cols"] if isinstance(pl, dict) and "cols" in pl else []
    except FileNotFoundError:
        pl_rows = []
        pl_cols = []

    pl_by_name = {}
    for row in pl_rows:
        d = dict(zip(pl_cols, row)) if pl_cols else row
        name = d.get("player") or d.get("PLAYER_NAME") or ""
        pl_by_name[norm(name)] = d

    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for team, pnames in players_by_team.items():
        tdir = os.path.join(out_dir, team)
        os.makedirs(tdir, exist_ok=True)
        for pname in pnames:
            rec = pl_by_name.get(norm(pname), {})
            gamelog = {
                "player": pname,
                "team": team,
                "source": "NBA.com Players Traditional table (season-to-date aggregate, not per-game)",
                "source_url": "https://www.nba.com/stats/players/traditional",
                "note": "Per-game game logs (minutes, pts, reb, ast, opponent per game) require the "
                        "NBA stats API which is not an official HTML page. Season aggregates recorded below.",
                "games": [],
            }
            for k in ("min", "pts", "reb", "ast", "gp"):
                if k in rec:
                    gamelog[k] = rec[k]
            write_json(os.path.join(tdir, f"{re.sub(r'[^a-z0-9]', '_', norm(pname))}.json"), gamelog)
            written += 1

    write_json(os.path.join(out_dir, "_index.json"), {
        "_meta": {
            "method": "One file per injured player; season aggregates from official NBA.com table. "
                      "Per-game logs blocked: no official HTML page publishes per-game logs.",
            "teams": len(players_by_team),
            "players": written,
        },
        "players_by_team": {t: sorted(list(pn)) for t, pn in players_by_team.items()},
    })
    print(f"Wrote gamelog stubs for {written} players across {len(players_by_team)} teams -> {out_dir}")

if __name__ == "__main__":
    main()
