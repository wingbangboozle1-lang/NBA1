"""Inputs for the strategy lab.

Reads the repository's committed official captures and assembles one schedule layer.
Nothing in this file writes anywhere, and nothing here invents a value: a game whose
score the official page did not print stays scoreless and is used for scheduling only.
"""
from __future__ import annotations

import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")

MIN_HISTORY = 4      # games a team must have played before its rating is used
K_SHRINK = 3.0       # league-average games added to a team's mean margin as a prior
SESSION = "arena/a3e092a2-nba1"


def _head_commit():
    """The commit these numbers were built from, stamped into every page footer.

    Read from git rather than hard-coded, because a stale stamp is the kind of claim a
    reader cannot check and this repository's rule is that every number must be.
    """
    try:
        import subprocess
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        return (r.stdout or "").strip() or "unknown"
    except Exception:
        return "unknown"


COMMIT = os.environ.get("S28_COMMIT") or _head_commit()


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def d(s):
    return dt.date(*[int(p) for p in s.split("-")])


def build_schedule():
    """One row per NBA game this season, from official captures only.

    scored   = a final score is printed on an official page this repository read
    fixture  = the official day page prints FINAL with an empty score cell
    horizon  = an unplayed slate game, 2026-11-14 .. 2026-11-17
    """
    log = load("data", "official", "gamelog.json")
    fixtures_repo = log["known_unplayed_by_source"]["fixtures"]
    mine = load("verify", "2026-11-14-a3e092a2",
              "official_backfill_2026-10-24_2026-11-02.json")
    fin13 = load("verify", "2026-11-14", "official_finals_2026-11-13.json")["rows"]
    horizon = load("data", "derived", "horizon_lines.json")["games"]
    teams_official = {r["abbr"]: r for r in load("site", "data", "teams.json")["rows"]}

    games = []
    for g in log["games"]:
        games.append({
            "date": g["date"], "away": g["away"], "home": g["home"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "ot": 1 if g.get("ot") else 0, "neutral": 1 if g.get("neutral") else 0,
            "game_id": g["game_id"], "source_url": g["source_url"], "kind": "scored",
            "source": "data/official/gamelog.json (session arena/e32856d8-nba1, transcribed from nba.com/games)",
        })
    for r in fin13:
        games.append({
            "date": r["date"], "away": r["away"], "home": r["home"],
            "away_pts": r["away_score"], "home_pts": r["home_score"],
            "ot": 1 if "OT" in (r.get("status") or "") else 0, "neutral": 0,
            "game_id": r["game_id"], "source_url": r["source_url"], "kind": "scored",
            "source": "verify/2026-11-14/official_finals_2026-11-13.json, reproduced by this session from the official scoreboard block",
        })
    for g in fixtures_repo:
        games.append({
            "date": g["date"], "away": g["away"], "home": g["home"],
            "away_pts": None, "home_pts": None, "ot": 0, "neutral": 0,
            "game_id": g["game_id"], "source_url": g["source_url"], "kind": "fixture",
            "source": "official day page prints FINAL with an empty score cell - schedule only",
        })
    for h in horizon:
        games.append({
            "date": h["date"], "away": h["away"], "home": h["home"],
            "away_pts": None, "home_pts": None, "ot": 0, "neutral": 0,
            "game_id": h["game_id"], "kind": "horizon",
            "source_url": f"https://www.nba.com/game/{h['away'].lower()}-vs-{h['home'].lower()}-{h['game_id']}",
            "source": "unplayed slate game (data/derived/horizon_lines.json)",
        })
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    return {"games": games, "log": log, "mine": mine, "fixtures_repo": fixtures_repo,
            "fin13": fin13, "horizon": horizon, "teams_official": teams_official}


def rest_maps(games, use_fixtures=True):
    """team -> dates played, then a rest lookup for (team, date).

    use_fixtures=False reproduces what the shipped consumers do: they build rest history
    from games that carry a score, so the 23 fixture games never enter the history and
    every rest figure after 2026-10-23 and 2026-11-01 shifts.
    """
    played = {}
    for g in games:
        if not use_fixtures and g["kind"] == "fixture":
            continue
        played.setdefault(g["away"], set()).add(g["date"])
        played.setdefault(g["home"], set()).add(g["date"])
    played = {t: sorted(v) for t, v in played.items()}

    def lookup(team, date):
        prior = [x for x in played.get(team, []) if d(x) < d(date)]
        if not prior:
            return {"days_off": None, "gap": None, "b2b": None, "last": None,
                    "games_last_4": None}
        last = prior[-1]
        gap = (d(date) - d(last)).days
        recent = [x for x in prior if (d(date) - d(x)).days <= 3]
        return {"days_off": gap - 1, "gap": gap, "b2b": gap == 1, "last": last,
                "games_last_4": len(recent) + 1}
    return lookup, played
