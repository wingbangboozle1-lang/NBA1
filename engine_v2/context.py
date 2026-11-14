"""Injury / rotation / game-flow layer.

Everything published here is either (a) a verbatim row from the official injury
report, or (b) counted from the official game log.  What is NOT available is
stated as unavailable.  In particular this module never estimates how many
minutes an absent player's replacement will play.
"""
from __future__ import annotations

import json
import os
import unicodedata
from collections import Counter, defaultdict

from .common import NAMES, ROOT, TEAMS, d, load, mean

PLAYERS_TRAD = os.path.join(ROOT, "data", "raw", "players_traditional.json")
PLAYERS_MIN = os.path.join(ROOT, "data", "players_minutes_2026_27.json")


def _norm(name: str) -> str:
    """'Antetokounmpo, Giannis' -> 'giannis antetokounmpo'.

    Accents are stripped and the two orderings are unified, because the injury
    report prints surname-first with diacritics while the stats leaderboard
    prints given-name-first without them.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\u2019", "'").lower().strip()
    if "," in s:
        last, first = s.split(",", 1)
        s = first.strip() + " " + last.strip()
    return " ".join(s.split())


def load_player_refs():
    """Two PARTIAL official leaderboards. Neither is a game log."""
    out = {}
    try:
        pt = json.load(open(PLAYERS_TRAD, encoding="utf-8"))
        cols = pt["cols"]
        for row in pt["rows"]:
            r = dict(zip(cols, row))
            out[_norm(r["player"])] = {
                "player": r["player"], "team": r["team"], "gp": r["gp"],
                "min": r["min"], "pts": r["pts"], "reb": r.get("reb"),
                "ast": r.get("ast"),
                "source_url": pt["source_url"], "leaderboard": "Top 50 scorers",
            }
    except Exception:
        pass
    try:
        pm = json.load(open(PLAYERS_MIN, encoding="utf-8"))
        rows = pm.get("rows") or pm.get("players") or []
        cols = pm.get("cols") or pm.get("fields_captured")
        for r in rows:
            if isinstance(r, dict):
                rec = r
            else:
                rec = dict(zip(cols, r))
            key = _norm(rec.get("player", ""))
            if not key:
                continue
            out.setdefault(key, {"player": rec.get("player"), "team": rec.get("team"),
                                 "gp": rec.get("gp"), "min": rec.get("min"),
                                 "pts": rec.get("pts"), "reb": None, "ast": None,
                                 "source_url": pm["_meta"]["source_url"],
                                 "leaderboard": "Top 24 by minutes"})
            out[key]["min"] = rec.get("min", out[key].get("min"))
            out[key]["leaderboard"] = "Top 24 by minutes and top 50 scorers"
    except Exception:
        pass
    return out


def build(slate, gamelog, injuries, played):
    refs = load_player_refs()

    # ---------------- injury report ---------------------------------------
    inj_rows = injuries["rows"]
    by_game = defaultdict(list)
    for r in inj_rows:
        by_game[(r["game_date"], r["matchup"])].append(r)

    injury_games = []
    for (dt, mu), rows in sorted(by_game.items()):
        teams = {}
        for r in rows:
            t = r["team"]
            teams.setdefault(t, {"team": t, "players": [], "not_submitted": False})
            if r["status"] == "NOT YET SUBMITTED":
                teams[t]["not_submitted"] = True
            else:
                p = refs.get(_norm(r["player"]))
                teams[t]["players"].append({
                    "player": r["player"], "status": r["status"], "reason": r["reason"],
                    "verified_min": p["min"] if p else None,
                    "verified_pts": p["pts"] if p else None,
                    "verified_gp": p["gp"] if p else None,
                    "verified_team": p["team"] if p else None,
                    "leaderboard": p["leaderboard"] if p else None,
                    "leaderboard_url": p["source_url"] if p else None,
                    "production_known": bool(p),
                })
        counts = Counter()
        for t in teams.values():
            for p in t["players"]:
                counts[p["status"]] += 1
        known = sum(1 for t in teams.values() for p in t["players"] if p["production_known"])
        total = sum(1 for t in teams.values() for p in t["players"])
        injury_games.append({
            "date": dt, "matchup": mu, "game_time_et": rows[0]["game_time_et"],
            "teams": [teams[k] for k in sorted(teams)],
            "counts": dict(counts),
            "players_listed": total,
            "players_with_verified_production": known,
            "coverage_pct": (known / total * 100.0) if total else None,
            "source_url": injuries["source_url"],
        })

    # ---------------- team form / game flow --------------------------------
    games = gamelog["games"]
    form = {t: dict(gp=0, w=0, l=0, pts_for=0, pts_ag=0, home_w=0, home_l=0,
                    away_w=0, away_l=0, ot=0, margins=[], rest=[], b2b=0, blowout=0)
            for t in TEAMS}
    for g in games:
        h, a = g["home"], g["away"]
        hp, ap = g["home_pts"], g["away_pts"]
        for t, pf, pa, won, ishome in ((h, hp, ap, hp > ap, True), (a, ap, hp, ap > hp, False)):
            f = form[t]
            f["gp"] += 1
            f["w" if won else "l"] += 1
            f["pts_for"] += pf
            f["pts_ag"] += pa
            f["home_w" if (won and ishome) else "home_l" if ishome else
              "away_w" if won else "away_l"] += 1
            f["ot"] += 1 if g["ot"] else 0
            f["margins"].append(pf - pa)
            if abs(pf - pa) >= 20:
                f["blowout"] += 1
    rows_form = []
    for t in TEAMS:
        f = form[t]
        if not f["gp"]:
            continue
        rows_form.append({
            "team": t, "name": NAMES[t], "gp": f["gp"], "w": f["w"], "l": f["l"],
            "ppg": f["pts_for"] / f["gp"], "papg": f["pts_ag"] / f["gp"],
            "mov": mean(f["margins"]),
            "home": f"{f['home_w']}-{f['home_l']}",
            "away": f"{f['away_w']}-{f['away_l']}",
            "ot_games": f["ot"],
            "ot_pct": f["ot"] / f["gp"] * 100.0,
            "blowout_20": f["blowout"],
            "blowout_pct": f["blowout"] / f["gp"] * 100.0,
            "source_url": "https://www.nba.com/games?date=2026-<date>",
        })
    rows_form.sort(key=lambda r: -r["mov"])

    # ---------------- per-slate-game flow -----------------------------------
    def last4(team, date_str):
        dd = d(date_str)
        return sum(1 for x in played.get(team, [])
                   if (dd - d(x)).days <= 4 and x < date_str)

    def rest(team, date_str):
        prior = [x for x in played.get(team, []) if x < date_str]
        return (d(date_str) - d(prior[-1])).days if prior else None

    flow = []
    inj_by_matchup = {}
    for ig in injury_games:
        inj_by_matchup.setdefault(ig["date"], {})[ig["matchup"]] = ig
    for g in slate:
        rh, ra = rest(g["home"], g["date"]), rest(g["away"], g["date"])
        mu = f"{g['away']}@{g['home']}"
        ig = inj_by_matchup.get(g["date"], {}).get(mu)
        flow.append({
            "date": g["date"], "time_et": g["time_et"], "matchup": mu,
            "away": g["away"], "home": g["home"],
            "rest_home": rh, "rest_away": ra,
            "b2b_home": 1 if rh == 1 else 0, "b2b_away": 1 if ra == 1 else 0,
            "rest_edge": (rh - ra) if (rh is not None and ra is not None) else None,
            "games_last4_home": last4(g["home"], g["date"]),
            "games_last4_away": last4(g["away"], g["date"]),
            "home_ppg": form[g["home"]]["pts_for"] / max(1, form[g["home"]]["gp"]),
            "away_ppg": form[g["away"]]["pts_for"] / max(1, form[g["away"]]["gp"]),
            "home_papg": form[g["home"]]["pts_ag"] / max(1, form[g["home"]]["gp"]),
            "away_papg": form[g["away"]]["pts_ag"] / max(1, form[g["away"]]["gp"]),
            "injury_rows": ig["players_listed"] if ig else 0,
            "injury_out": ig["counts"].get("Out", 0) if ig else 0,
            "injury_questionable": ig["counts"].get("Questionable", 0) if ig else 0,
            "injury_not_submitted": (sum(1 for t in ig["teams"] if t["not_submitted"])
                                     if ig else None),
            "injury_source_url": ig["source_url"] if ig else None,
            "injury_note": (None if ig else
                            "No official injury report published for this game date at capture time."),
            "source_url": g["source_url"],
        })

    coverage = {
        "players_in_latest_report": sum(1 for r in inj_rows if r["status"] != "NOT YET SUBMITTED"),
        "players_with_verified_season_average": sum(
            1 for r in inj_rows
            if r["status"] != "NOT YET SUBMITTED" and _norm(r["player"]) in refs),
        "minutes_leaderboard_size": sum(1 for v in refs.values() if v["leaderboard"].startswith("Top 24")),
        "scoring_leaderboard_size": 50,
        "limit": ("A season average is not a game log. Originating a player-prop line needs the "
                  "game-by-game distribution behind the average, which no official page reachable "
                  "here publishes. Rotation minutes for a replacement player are therefore not "
                  "estimated anywhere on this site."),
    }
    return {
        "injury_games": injury_games,
        "team_form": rows_form,
        "slate_flow": flow,
        "player_reference": sorted(
            [{"player": v["player"], "team": v["team"], "gp": v["gp"], "min": v["min"],
              "pts": v["pts"], "reb": v.get("reb"), "ast": v.get("ast"),
              "leaderboard": v["leaderboard"], "source_url": v["source_url"]}
             for v in refs.values()], key=lambda x: -(x["min"] or 0)),
        "coverage": coverage,
    }
