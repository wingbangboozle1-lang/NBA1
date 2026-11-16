"""Compute travel distance (miles) for each team between consecutive road games,
using the arena-coordinate table and the official schedule.

Usage:  python3 scripts/travel_distance.py <schedule_json> [output_json]

Reads:  data/arenas.json (team -> arena lat/lon)
        schedule JSON with {_meta, games: [{date, home, away, ...}]}
Writes: per-team travel miles for each game.
"""
import sys, json, math, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from common import ABBR, read_json, write_json


def havelib_miles(lat1, lon1, lat2, lon2, R=3958.8):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    sched_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data/travel_distance.json"

    arenas = read_json("data/arenas.json")["arenas"]
    sched = read_json(sched_path)
    games = sched["games"]

    games_by_date = {}
    for g in games:
        games_by_date.setdefault(g["date"], []).append(g)

    dates = sorted(games_by_date.keys())

    team_last = {}   # abbr -> (lat, lon) of the arena they most recently played at
    travel = {}      # (date, matchup) -> {"home": miles, "away": miles or None}

    for d in dates:
        travel[d] = {}
        for g in games_by_date[d]:
            home = g["home"]; away = g["away"]
            matchup = f"{away}@{home}"
            ha = arenas.get(home)
            away_dist = None
            if ha:
                if away in team_last:
                    lat, lon = team_last[away]
                    away_dist = round(havelib_miles(lat, lon, ha["lat"], ha["lon"]), 1)
            travel[d][matchup] = {"home": 0.0, "away": away_dist}
            # After this game, both teams are at the home arena
            if ha:
                team_last[home] = (ha["lat"], ha["lon"])
                team_last[away] = (ha["lat"], ha["lon"])

    write_json(out_path, {
        "_meta": {
            "source": "data/arenas.json (approx arena coords) + official schedule",
            "method": "great-circle miles from previous game arena to current game arena (away team only); home team = 0.0",
            "note": "Away-team travel is None when the team has no previous game in the capture window (first game of season for that team). Coordinates are approximate and flagged for review.",
        },
        "travel": travel,
    })
    print(f"Wrote {out_path} with {len(dates)} dates")


if __name__ == "__main__":
    main()
