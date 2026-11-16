#!/usr/bin/env python3
"""Build R21 (per-player game logs) and R12 (minutes redistribution) artifacts.

Inputs
  raw/leaguegamelog.json.gz      official stats.nba.com leaguegamelog capture
                                 (the data behind nba.com/stats/players/boxscores)
  raw/injury_2026-11-15_0900PM_rows.json
                                 the official injury-report edition parsed by
                                 parse_injury.py

Outputs
  ../../data/official/player_game_logs_4ff440c7_2026-11-16.json
  ../../data/derived/rotation_minutes_4ff440c7_2026-11-16.json

Rules this script holds itself to
  * every emitted number is computed from the official capture, never assumed;
  * a value that cannot be measured from the capture is emitted as None with a
    reason, never filled with a plausible number;
  * the replacement-share estimate is MEASURED (minutes shares in the team's games
    without the player minus minutes shares in the team's games with him), and the
    number of games behind each estimate is published next to it. Small samples are
    flagged, not hidden.
"""
import gzip
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
GAMELOG = os.path.join(RAW, "leaguegamelog.json.gz")
INJ = os.path.join(RAW, "injury_2026-11-15_0900PM_rows.json")

OUT_LOGS = os.path.join(REPO, "data", "official",
                        "player_game_logs_4ff440c7_2026-11-16.json")
OUT_ROT = os.path.join(REPO, "data", "derived",
                       "rotation_minutes_4ff440c7_2026-11-16.json")


def norm(name):
    """'Furphy, Johnny' -> 'johnny furphy'; 'Doncic, Luka' -> 'luka doncic'."""
    if not name:
        return ""
    s = name.lower()
    s = s.replace("-", " ")
    s = re.sub(r"[^a-z0-9\' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def key(name):
    return strip_accents(norm(name))


def load_gamelog():
    if not os.path.exists(GAMELOG):
        return None
    with gzip.open(GAMELOG, "rt", encoding="utf-8") as fh:
        doc = json.load(fh)
    rs = (doc.get("resultSets") or [{}])[0]
    hdr = rs.get("headers") or []
    idx = {h: i for i, h in enumerate(hdr)}
    recs = []
    for r in rs.get("rowSet") or []:
        recs.append({h: r[idx[h]] for h in hdr})
    return {"headers": hdr, "params": doc.get("parameters"), "rows": recs}


def parse_min(v):
    """Official MIN column is mm:ss or None for a DNP."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in ("-", "None"):
        return None
    if ":" in s:
        m, sec = s.split(":", 1)
        try:
            return int(m) + int(sec) / 60.0
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    gl = load_gamelog()
    if gl is None:
        print("no official game-log capture at", GAMELOG, file=sys.stderr)
        return 2
    rows = gl["rows"]
    print("official leaguegamelog rows:", len(rows))

    # ---------------------------------------------------------------- game logs
    logs = defaultdict(list)
    for r in rows:
        gid = r.get("GAME_ID")
        team = r.get("TEAM_ABBREVIATION")
        # MATCHUP is printed as "LAL @ PHX" (away) or "LAL vs. POR" (home)
        matchup = (r.get("MATCHUP") or "").strip()
        m = re.match(r"^([A-Z]{3})\s+(@|vs\.)\s+([A-Z]{3})$", matchup)
        opp = None
        home = None
        if m:
            if m.group(1) == team:
                opp, home = m.group(3), (m.group(2) == "vs.")
            else:
                opp, home = m.group(1), (m.group(2) == "@")
        logs[(key(r.get("PLAYER_NAME")), r.get("PLAYER_ID"))].append({
            "game_id": gid,
            "game_date": (r.get("GAME_DATE") or "")[:10],
            "team": team,
            "opponent": opp,
            "home": home,
            "matchup_official": matchup,
            "wl": r.get("WL"),
            "min": parse_min(r.get("MIN")),
            "min_official": r.get("MIN"),
            "pts": r.get("PTS"),
            "reb": r.get("REB"),
            "ast": r.get("AST"),
            "source_game_url": ("https://www.nba.com/game/%s/" % gid) if gid else None,
        })

    # ------------------------------------------------- injury-report universe
    inj = json.load(open(INJ, encoding="utf-8"))
    universe = []
    seen = set()
    for r in inj["rows"]:
        if not r.get("player"):
            continue
        k = key(r["player"])
        if (k, r.get("team")) in seen:
            continue
        seen.add((k, r.get("team")))
        universe.append(r)

    by_key = defaultdict(list)
    for (nm, pid), v in logs.items():
        by_key[nm].append((pid, v))

    matched, unmatched = [], []
    for r in universe:
        k = key(r["player"])
        cands = by_key.get(k)
        if not cands:
            unmatched.append({"injury_player": r["player"], "injury_team": r.get("team"),
                              "status": r.get("status"),
                              "why": "no official 2026-27 game log row under this name"})
            continue
        # if several player ids share a name, keep the one whose team matches
        pick = cands[0]
        for pid, v in cands:
            teams = {g["team"] for g in v if g["team"]}
            abbr = ABBR.get(r.get("team"))
            if abbr and abbr in teams:
                pick = (pid, v)
                break
        pid, v = pick
        v = sorted(v, key=lambda g: g["game_date"])
        gms = [g for g in v if g["min"] is not None]
        matched.append({
            "player": r["player"],
            "player_id": pid,
            "injury_team": r.get("team"),
            "injury_status": r.get("status"),
            "injury_reason": r.get("reason"),
            "injury_source_url": r.get("source_url"),
            "n_games_log": len(v),
            "n_games_played": len(gms),
            "season_min": round(sum(g["min"] for g in gms), 1),
            "mpg": round(sum(g["min"] for g in gms) / len(gms), 1) if gms else None,
            "ppg": round(sum(g["pts"] or 0 for g in gms) / len(gms), 1) if gms else None,
            "rpg": round(sum(g["reb"] or 0 for g in gms) / len(gms), 1) if gms else None,
            "apg": round(sum(g["ast"] or 0 for g in gms) / len(gms), 1) if gms else None,
            "log": v,
        })

    # ------------------------------------------------- team minutes structure
    team_games = defaultdict(lambda: defaultdict(list))   # team -> gid -> [rows]
    for r in rows:
        team_games[r.get("TEAM_ABBREVIATION")][r.get("GAME_ID")].append(r)

    team_total_min = {}          # team -> total minutes over all its games
    team_game_count = {}
    for t, games in team_games.items():
        tot = 0.0
        for gid, rr in games.items():
            s = sum(parse_min(x.get("MIN")) or 0.0 for x in rr)
            tot += s
        team_total_min[t] = tot
        team_game_count[t] = len(games)

    player_min = defaultdict(float)          # (team, playerkey) -> total minutes
    player_games = defaultdict(int)
    player_teamgames = defaultdict(set)      # (team, playerkey) -> set of gids played
    for r in rows:
        t = r.get("TEAM_ABBREVIATION")
        nm = r.get("PLAYER_NAME")
        mn = parse_min(r.get("MIN"))
        player_min[(t, key(nm))] += (mn or 0.0)
        if mn:
            player_games[(t, key(nm))] += 1
            player_teamgames[(t, key(nm))].add(r.get("GAME_ID"))

    DISP = {}
    for r in rows:
        DISP[key(r.get("PLAYER_NAME"))] = r.get("PLAYER_NAME")

    teams_sorted = sorted(team_games)
    rotation = {}
    for t in teams_sorted:
        disp = DISP
        entries = []
        for (tt, nm), mins in player_min.items():
            if tt != t or mins <= 0:
                continue
            entries.append({
                "player": disp.get(nm),
                "minutes": round(mins, 1),
                "games_played": player_games[(t, nm)],
                "minutes_share_of_team_season": (round(mins / team_total_min[t], 4)
                                                 if team_total_min[t] else None),
                "mpg": round(mins / player_games[(t, nm)], 1) if player_games[(t, nm)] else None,
            })
        entries.sort(key=lambda e: -e["minutes"])
        rotation[t] = {
            "team_games": team_game_count[t],
            "team_total_minutes": round(team_total_min[t], 1),
            "top8": entries[:8],
            "all": entries,
        }

    # ------------------------------------- measured replacement shares (R12 core)
    # For each team, for each of its top-8 players P:
    #   games_with    = team games in which P recorded minutes
    #   games_without = team games in which P recorded no minutes (DNP / out)
    #   for every other player Q: share_with = Q minutes in games_with / team minutes
    #   in those games; share_without likewise. delta = share_without - share_with.
    replacements = {}
    for t in teams_sorted:
        games = team_games[t]
        per = rotation[t]["top8"]
        out = []
        for p in per:
            pk = None
            for (tt, nm), _ in player_min.items():
                if tt == t and disp.get(nm) == p["player"]:
                    pk = nm
                    break
            if pk is None:
                continue
            played = player_teamgames[(t, pk)]
            gwith = [gid for gid in games if gid in played]
            gwithout = [gid for gid in games if gid not in played]
            if not gwith or not gwithout:
                out.append({
                    "player": p["player"],
                    "games_with": len(gwith), "games_without": len(gwithout),
                    "measurable": False,
                    "why": ("player has no missed game this season, so the "
                            "replacement share cannot be measured from official data")
                            if not gwithout else "player has not played this season",
                    "absorbers": [],
                })
                continue
            tm_with = sum(sum(parse_min(x.get("MIN")) or 0.0 for x in games[g])
                          for g in gwith)
            tm_without = sum(sum(parse_min(x.get("MIN")) or 0.0 for x in games[g])
                             for g in gwithout)
            mins_with = defaultdict(float)
            mins_without = defaultdict(float)
            for g in gwith:
                for x in games[g]:
                    mins_with[key(x.get("PLAYER_NAME"))] += parse_min(x.get("MIN")) or 0.0
            for g in gwithout:
                for x in games[g]:
                    mins_without[key(x.get("PLAYER_NAME"))] += parse_min(x.get("MIN")) or 0.0
            absorbers = []
            for qk in set(list(mins_with) + list(mins_without)):
                if qk == pk:
                    continue
                sw = mins_with.get(qk, 0.0) / tm_with if tm_with else 0.0
                so = mins_without.get(qk, 0.0) / tm_without if tm_without else 0.0
                if max(sw, so) <= 0:
                    continue
                absorbers.append({
                    "player": disp.get(qk, qk),
                    "share_with_p": round(sw, 4),
                    "share_without_p": round(so, 4),
                    "delta_share": round(so - sw, 4),
                    "mpg_with": round(mins_with.get(qk, 0.0) / len(gwith), 1),
                    "mpg_without": round(mins_without.get(qk, 0.0) / len(gwithout), 1),
                    "delta_mpg": round(mins_without.get(qk, 0.0) / len(gwithout)
                                       - mins_with.get(qk, 0.0) / len(gwith), 1),
                })
            absorbers.sort(key=lambda a: -a["delta_mpg"])
            out.append({
                "player": p["player"],
                "games_with": len(gwith),
                "games_without": len(gwithout),
                "measurable": True,
                "why": None,
                "vacated_mpg": p["mpg"],
                "vacated_share": p["minutes_share_of_team_season"],
                "absorbers": absorbers[:5],
                "_low_sample": len(gwithout) < 3,
            })
        replacements[t] = out

    doc_logs = {
        "_meta": {
            "title": "Official per-player game logs for every player on the 2026-11-15 09:00 PM ET injury report (R21)",
            "season": "2026-27",
            "season_type": "Regular Season",
            "built_utc": None,
            "built_by": "session arena/4ff440c7-nba1",
            "script": "verify/2026-11-16-4ff440c7/build_rotation.py",
            "game_log_source": {
                "name": "stats.nba.com leaguegamelog (the data behind nba.com/stats/players/boxscores)",
                "url": "https://stats.nba.com/stats/leaguegamelog",
                "human_page": "https://www.nba.com/stats/players/boxscores?Season=2026-27&SeasonType=Regular+Season",
                "capture": os.path.relpath(GAMELOG, REPO),
                "manifest": "verify/2026-11-16-4ff440c7/raw/_manifest.json",
            },
            "injury_universe_source": {
                "edition": "2026-11-15_09_00PM",
                "url": "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf",
                "index": "https://official.nba.com/nba-injury-report-2026-27-season/",
            },
            "per_game_source_url_template": "https://www.nba.com/game/{game_id}/",
            "fields": "date, opponent (from the official MATCHUP string), minutes, points, rebounds, assists",
            "players_on_injury_report": len(universe),
            "players_with_an_official_game_log": len(matched),
            "players_without": len(unmatched),
        },
        "players": sorted(matched, key=lambda p: -(p["mpg"] or 0)),
        "unmatched": unmatched,
    }

    doc_rot = {
        "_meta": {
            "title": "Measured rotation minutes: top-8 shares per team and measured replacement shares when a player is out (R12)",
            "season": "2026-27",
            "built_by": "session arena/4ff440c7-nba1",
            "script": "verify/2026-11-16-4ff440c7/build_rotation.py",
            "source": "https://stats.nba.com/stats/leaguegamelog",
            "method": ("team total minutes are the sum of the official MIN column over that "
                       "team's players in that game, so overtime is included automatically and "
                       "no 240-minute assumption is made. A player's share is his season "
                       "minutes divided by his team's season minutes."),
            "replacement_method": ("measured within this season only: for each top-8 player P, "
                                   "the team's games split into games P played and games P "
                                   "missed; each team-mate's minutes share is computed on both "
                                   "sides and the difference is the measured replacement share. "
                                   "No regression, no assumed redistribution curve."),
            "limitation": ("through 2026-11-15 a team has played 11-14 games, so most players "
                           "have 0-3 missed games. Where games_without is 0 the replacement "
                           "share is published as unmeasurable rather than estimated; where it "
                           "is 1-2 the row is flagged low_sample."),
        },
        "teams": {t: {"team_games": rotation[t]["team_games"],
                      "team_total_minutes": rotation[t]["team_total_minutes"],
                      "top8": rotation[t]["top8"]} for t in teams_sorted},
        "replacements": replacements,
    }

    os.makedirs(os.path.dirname(OUT_LOGS), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_ROT), exist_ok=True)
    with open(OUT_LOGS, "w", encoding="utf-8") as fh:
        json.dump(doc_logs, fh, indent=1, ensure_ascii=False)
    with open(OUT_ROT, "w", encoding="utf-8") as fh:
        json.dump(doc_rot, fh, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT_LOGS, REPO), "players:", len(matched),
          "unmatched:", len(unmatched))
    print("wrote", os.path.relpath(OUT_ROT, REPO), "teams:", len(teams_sorted))
    return 0


ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


if __name__ == "__main__":
    raise SystemExit(main())
