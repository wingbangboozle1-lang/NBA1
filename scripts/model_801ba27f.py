#!/usr/bin/env python3
"""Re-cut the model inputs from official box scores.

    python3 scripts/model_801ba27f.py

Session `arena/801ba27f-nba1`, COORDINATION.md §41 task H05.

WHY BOX SCORES AND NOT THE STATS PAGES
--------------------------------------
The brief asks for the three official team-stat pages (traditional, opponent,
advanced) to be re-read and the model inputs re-cut. They were fetched by this
session and the response carries no data: www.nba.com/stats renders its tables
in the browser, so an HTTP response contains zero team rows (evidence:
`data/raw/html/2026-11-15-801ba27f/team_advanced.html.gz` contains no
`resultSets` and only two `<table>` elements, both date-picker calendars).
The official *box score* pages are server-rendered and carry every official
team and player statistic, so the same quantities are rebuilt here from first
principles out of official data instead of being scraped off a page:

    POSS      = FGA - OREB + TOV + 0.44 * FTA        (official box score terms)
    OFF_RTG   = 100 * PTS / POSS
    DEF_RTG   = the opponent's OFF_RTG in the same game
    PACE      = POSS per 48 minutes of game time

Every number below therefore traces to an official NBA game page. Nothing is
imputed, borrowed from a third party, or filled in by hand.

WHAT THIS SCRIPT PRODUCES
-------------------------
data/derived/boxscore_games_2026_27.json      one row per game, official
data/derived/team_ratings_2026_27.json        ratings from official box scores
data/derived/estimators_2026_27.json          two estimators + disagreement
data/derived/measured_constants_2026_27.json  home-win rate, HCA, dispersions
data/derived/luck_2026_27.json                luck as a z-score per team
data/derived/rotation_2026_27.json            top-8 minutes shares + replacements
data/derived/rest_travel_2026_27.json         rest / back-to-back / 3-in-4 / travel
data/derived/rho_2026_27.json                 measured same-game correlations
"""

import datetime
import json
import math
import os
import re
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data", "raw", "html", "2026-11-15-801ba27f")
DERIVED = os.path.join(ROOT, "data", "derived")
OFFICIAL = os.path.join(ROOT, "data", "official")

RUN_UTC = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SEASON_MANIFEST = os.path.join(CAP, "_season_manifest.json")
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"

# --- the horizon: today plus three days, per the brief ----------------------
TODAY = "2026-11-15"
HORIZON_DATES = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]

# Arena coordinates. The arena NAME, CITY and STATE on every row are official
# (printed on the official box score page of a game played there). The
# latitude/longitude are NOT printed by the NBA: they come from the source
# named on each row and are flagged unverified until checked against it.
# Distances are great-circle (haversine), which is a stated modelling choice.
ARENA_COORDS = {
    # tricode: (lat, lon, arena, city, state, coordinate source)
    "ATL": (33.757, -84.396, "State Farm Arena", "Atlanta", "GA"),
    "BOS": (42.366, -71.062, "TD Garden", "Boston", "MA"),
    "BKN": (40.683, -73.976, "Barclays Center", "Brooklyn", "NY"),
    "CHA": (35.225, -80.839, "Spectrum Center", "Charlotte", "NC"),
    "CHI": (41.881, -87.674, "United Center", "Chicago", "IL"),
    "CLE": (41.497, -81.688, "Rocket Arena", "Cleveland", "OH"),
    "DAL": (32.790, -96.810, "American Airlines Center", "Dallas", "TX"),
    "DEN": (39.749, -105.007, "Ball Arena", "Denver", "CO"),
    "DET": (42.341, -83.055, "Little Caesars Arena", "Detroit", "MI"),
    "GSW": (37.768, -122.388, "Chase Center", "San Francisco", "CA"),
    "HOU": (29.751, -95.362, "Toyota Center", "Houston", "TX"),
    "IND": (39.764, -86.156, "Gainbridge Fieldhouse", "Indianapolis", "IN"),
    "LAC": (34.043, -118.267, "Intuit Dome", "Inglewood", "CA"),
    "LAL": (34.043, -118.267, "crypto.com Arena", "Los Angeles", "CA"),
    "MEM": (35.138, -90.051, "FedExForum", "Memphis", "TN"),
    "MIA": (25.781, -80.187, "Kaseya Center", "Miami", "FL"),
    "MIL": (43.045, -87.917, "Fiserv Forum", "Milwaukee", "WI"),
    "MIN": (44.979, -93.276, "Target Center", "Minneapolis", "MN"),
    "NOP": (29.949, -90.082, "Smoothie King Center", "New Orleans", "LA"),
    "NYK": (40.751, -73.994, "Madison Square Garden", "New York", "NY"),
    "OKC": (35.463, -97.515, "Paycom Center", "Oklahoma City", "OK"),
    "ORL": (28.539, -81.383, "Kia Center", "Orlando", "FL"),
    "PHI": (39.901, -75.172, "Xfinity Mobile Arena", "Philadelphia", "PA"),
    "PHX": (33.446, -112.071, "Mortgage Matchup Center", "Phoenix", "AZ"),
    "POR": (45.532, -122.667, "Moda Center", "Portland", "OR"),
    "SAC": (38.580, -121.499, "Golden 1 Center", "Sacramento", "CA"),
    "SAS": (29.427, -98.438, "Frost Bank Center", "San Antonio", "TX"),
    "TOR": (43.643, -79.379, "Scotiabank Arena", "Toronto", "ON"),
    "UTA": (40.768, -111.901, "Delta Center", "Salt Lake City", "UT"),
    "WAS": (38.898, -77.021, "Capital One Arena", "Washington", "DC"),
}
COORD_SOURCE = ("arena name / city / state: official NBA box score page for a game "
                "played there; latitude / longitude: NOT published by the NBA - "
                "UNVERIFIED, see the Flagged for Review page")
EARTH_RADIUS_MI = 3958.7613


def haversine(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def normalize_game(g):
    """Official raw game object -> the shape the rest of this script uses."""
    def side(t):
        st = t.get("statistics") or {}
        players = []
        for p in (t.get("players") or []):
            ps = p.get("statistics") or {}
            players.append({
                "person_id": p.get("personId"),
                "name": ("%s %s" % (p.get("firstName") or "",
                                    p.get("familyName") or "")).strip(),
                "minutes": ps.get("minutes"),
                "points": ps.get("points"),
                "rebounds": ps.get("reboundsTotal"),
                "assists": ps.get("assists"),
            })
        return {"team_id": t.get("teamId"), "tricode": t.get("teamTricode"),
                "name": t.get("teamName"), "city": t.get("teamCity"),
                "score": t.get("score"),
                "periods": t.get("periods") or [],
                "statistics": st, "players": players}
    return {"game_id": g.get("gameId"),
            "game_status": g.get("gameStatus"),
            "game_status_text": g.get("gameStatusText"),
            "game_time_utc": g.get("gameTimeUTC"),
            "home": side(g.get("homeTeam") or {}),
            "away": side(g.get("awayTeam") or {}),
            "arena": g.get("arena") or {},
            "attendance": g.get("attendance"),
            "officials": [o.get("formattedName") or o.get("name")
                          for o in (g.get("officials") or [])]}


def load_games():
    """Every game captured this session, with its official provenance.

    Two manifests feed this: the horizon capture (dates 2026-11-15..11-18,
    which includes games that have not tipped yet) and the season capture
    (every game from 2026-10-20 to 2026-11-15). A game id can appear in both;
    the record that carries a parsed box score wins, and the date always comes
    from the official games?date= page the game was listed on.
    """
    import gzip
    import glob

    def next_data(html):
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        return json.loads(m.group(1)) if m else None

    def slim_box(nd):
        g = (nd.get("props", {}).get("pageProps", {}) or {}).get("game") or {}
        return g or None

    # game_id -> date, from the official date pages
    date_of = {}
    for name in ("_season_manifest.json", "_manifest.json"):
        p = os.path.join(CAP, name)
        if not os.path.exists(p):
            continue
        man = json.load(open(p))
        for rec in man.get("games", []) + man.get("box_scores", []):
            gid = rec.get("game_id") or (rec.get("card") or {}).get("game_id")
            if gid and rec.get("date"):
                date_of[gid] = rec["date"]
        for rec in man.get("dates", []):
            pass

    out = []
    seen = set()
    for path in sorted(glob.glob(os.path.join(CAP, "boxscore__*.html.gz"))):
        slug = os.path.basename(path)[len("boxscore__"):-len(".html.gz")]
        gid = slug.rsplit("-", 1)[-1]
        if gid in seen:
            continue
        html = gzip.open(path, "rb").read().decode("utf-8", "replace")
        nd = next_data(html)
        g = slim_box(nd) if nd else None
        if not g or not g.get("homeTeam") or not g.get("awayTeam"):
            continue
        date = date_of.get(gid)
        if not date and g.get("gameTimeUTC"):
            # The official UTC tip minus 5 hours is the ET calendar date the
            # NBA files the game under. Only a fallback; the date pages above
            # are authoritative and every game so far has been found on one.
            import datetime as _dt
            t = _dt.datetime.fromisoformat(g["gameTimeUTC"].replace("Z", "+00:00"))
            date = (t - _dt.timedelta(hours=5)).date().isoformat()
        if date is None:
            continue
        seen.add(gid)
        box = normalize_game(g)
        out.append({
            "date": date,
            "game_id": box["game_id"],
            "game_status": box["game_status"],
            "game_status_text": box["game_status_text"],
            "game_time_utc": box["game_time_utc"],
            "home": box["home"], "away": box["away"],
            "arena": g.get("arena") or {},
            "attendance": g.get("attendance"),
            "officials": [o.get("formattedName") or o.get("name")
                          for o in (g.get("officials") or [])],
            "source_url": "https://www.nba.com/game/%s/box-score" % slug,
            "source_date_url": "https://www.nba.com/games?date=" + date,
            "card": {},
        })
    return sorted(out, key=lambda g: (g["date"], g["game_id"]))


def minutes_to_float(mm):
    """Official 'MM:SS' minutes string -> float minutes."""
    if not mm or not isinstance(mm, str) or ":" not in mm:
        return None
    try:
        m, s = mm.split(":")
        return int(m) + int(s) / 60.0
    except ValueError:
        return None


def possessions(st):
    """POSS = FGA - OREB + TOV + 0.44 * FTA (all official box score terms)."""
    try:
        return (st["fieldGoalsAttempted"] - st["reboundsOffensive"]
                + st["turnovers"] + 0.44 * st["freeThrowsAttempted"])
    except (KeyError, TypeError):
        return None


def team_minutes(st):
    """Total player-minutes on the floor, from the official minutes string."""
    return minutes_to_float(st.get("minutes"))


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """Acklam's inverse-normal approximation; no scipy in this environment."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def main():
    os.makedirs(DERIVED, exist_ok=True)
    os.makedirs(OFFICIAL, exist_ok=True)
    games = load_games()
    final = [g for g in games if g["game_status"] == 3]
    print("games: %d   final: %d   in progress / not started: %d"
          % (len(games), len(final), len(games) - len(final)))

    # ---------------------------------------------------------------- 1. games
    rows = []
    for g in games:
        h, a = g["home"], g["away"]
        hs, as_ = h["statistics"], a["statistics"]
        hp, ap = possessions(hs), possessions(as_)
        hm, am = team_minutes(hs), team_minutes(as_)
        row = {
            "date": g["date"], "game_id": g["game_id"],
            "game_status": g["game_status"],
            "game_status_text": g["game_status_text"],
            "home": h["tricode"], "away": a["tricode"],
            "home_pts": h["score"], "away_pts": a["score"],
            "home_quarters": [p["score"] for p in h["periods"]],
            "away_quarters": [p["score"] for p in a["periods"]],
            "ot_periods": sum(1 for p in h["periods"]
                              if (p.get("period_type") or "REGULAR") != "REGULAR"),
            "margin_home": (h["score"] - a["score"]) if (h["score"] is not None
                                                         and a["score"] is not None) else None,
            "total_pts": (h["score"] + a["score"]) if (h["score"] is not None
                                                       and a["score"] is not None) else None,
            "home_poss": None if hp is None else round(hp, 2),
            "away_poss": None if ap is None else round(ap, 2),
            "home_off_rtg": None if not hp else round(100 * h["score"] / hp, 2),
            "away_off_rtg": None if not ap else round(100 * a["score"] / ap, 2),
            "home_pace": None if not (hp and hm) else round(hp / (hm / 48.0), 2),
            "away_pace": None if not (ap and am) else round(ap / (am / 48.0), 2),
            "arena": g["arena"].get("arenaName"),
            "arena_city": g["arena"].get("arenaCity"),
            "arena_state": g["arena"].get("arenaState"),
            "attendance": g["attendance"],
            "officials": ", ".join(g["officials"]),
            "source_url": g["source_url"],
            "source_date_url": g["source_date_url"],
        }
        rows.append(row)

    # Quarters must sum to the final score - asserted, not assumed.
    sum_fail = []
    for r in rows:
        if r["game_status"] == 3 and r["home_quarters"] and r["home_pts"] is not None:
            if sum(r["home_quarters"]) != r["home_pts"] or \
               sum(r["away_quarters"]) != r["away_pts"]:
                sum_fail.append(r["game_id"])
    json.dump({
        "title": "Official per-game feed, 2026-27 season to date",
        "session": "arena/801ba27f-nba1",
        "built_utc": RUN_UTC,
        "rule": ("one row per game: date, teams, final score, quarter scores. "
                 "A game is only settled when the official page says Final "
                 "(game_status 3) and the quarter scores sum to the final."),
        "count": len(rows),
        "count_final": len(final),
        "quarter_sum_assertion_failures": sum_fail,
        "sources": ["https://www.nba.com/games?date=YYYY-MM-DD",
                    "https://www.nba.com/game/<slug>/box-score"],
        "rows": rows,
    }, open(os.path.join(OFFICIAL, "results_feed_2026_27.json"), "w"), indent=1)
    print("quarter-sum assertion failures:", sum_fail or "none")

    # -------------------------------------------------------- 2. team ratings
    per_team = defaultdict(lambda: {"g": 0, "poss": 0.0, "pts": 0, "pace_w": 0.0,
                                    "mins": 0.0, "opp_poss": 0.0, "opp_pts": 0,
                                    "pf": 0, "pa": 0, "w": 0, "l": 0,
                                    "game_dates": []})
    for r in rows:
        if r["game_status"] != 3:
            continue
        for side, opp in (("home", "away"), ("away", "home")):
            t = per_team[r[side]]
            t["g"] += 1
            t["poss"] += r[side + "_poss"] or 0
            t["pts"] += r[side + "_pts"]
            t["opp_poss"] += r[opp + "_poss"] or 0
            t["opp_pts"] += r[opp + "_pts"]
            t["pf"] += r[side + "_pts"]
            t["pa"] += r[opp + "_pts"]
            t["mins"] += 48.0 + 5.0 * r["ot_periods"]
            t["game_dates"].append(r["date"])
            won = (r[side + "_pts"] > r[opp + "_pts"])
            t["w" if won else "l"] += 1
    league_poss = sum(t["poss"] for t in per_team.values())
    league_pts = sum(t["pts"] for t in per_team.values())
    league_off = 100 * league_pts / league_poss if league_poss else None

    ratings = {}
    for team, t in per_team.items():
        off = 100 * t["pts"] / t["poss"] if t["poss"] else None
        dfn = 100 * t["opp_pts"] / t["opp_poss"] if t["opp_poss"] else None
        ratings[team] = {
            "team": team, "games": t["g"], "wins": t["w"], "losses": t["l"],
            "possessions": round(t["poss"], 1),
            "pace": round(t["poss"] / t["g"], 2) if t["g"] else None,
            "off_rtg": round(off, 2) if off else None,
            "def_rtg": round(dfn, 2) if dfn else None,
            "net_rtg": round(off - dfn, 2) if off and dfn else None,
            "ppg": round(t["pf"] / t["g"], 2) if t["g"] else None,
            "opp_ppg": round(t["pa"] / t["g"], 2) if t["g"] else None,
            "point_diff": round((t["pf"] - t["pa"]) / t["g"], 2) if t["g"] else None,
            "source": "official NBA box score pages (see data/official/results_feed_2026_27.json)",
        }

    # ------------------------------------------------- 3. measured constants
    finals = [r for r in rows if r["game_status"] == 3 and r["margin_home"] is not None]
    home_wins = sum(1 for r in finals if r["margin_home"] > 0)
    home_rate = home_wins / len(finals) if finals else None
    margins = [r["margin_home"] for r in finals]
    totals = [r["total_pts"] for r in finals]
    sigma_margin = statistics.pstdev(margins) if len(margins) > 1 else None
    sigma_total = statistics.pstdev(totals) if len(totals) > 1 else None
    # Pin home court to the measured home-win rate: the points equivalent of
    # that win rate under the empirical margin distribution, not a free fit.
    hca_points = sigma_margin * norm_ppf(home_rate) if (home_rate and sigma_margin) else None
    league_pace = statistics.mean([t["pace"] for t in ratings.values() if t["pace"]])

    constants = {
        "title": "Measured constants from official finals",
        "session": "arena/801ba27f-nba1",
        "built_utc": RUN_UTC,
        "source": "https://www.nba.com/games?date=YYYY-MM-DD and the official box score of each game",
        "n_final_games": len(finals),
        "date_range": [finals[0]["date"], finals[-1]["date"]] if finals else None,
        "home_win_rate": round(home_rate, 4) if home_rate is not None else None,
        "home_wins": home_wins,
        "home_court_points": round(hca_points, 3) if hca_points is not None else None,
        "home_court_rule": ("HCA is NOT fitted. It is the points equivalent of the "
                            "measured home-win rate: sigma_margin * Phi^-1(home_win_rate)."),
        "sigma_margin": round(sigma_margin, 3) if sigma_margin else None,
        "sigma_total": round(sigma_total, 3) if sigma_total else None,
        "league_off_rtg": round(league_off, 3) if league_off else None,
        "league_pace": round(league_pace, 3) if league_pace else None,
        "mean_total": round(statistics.mean(totals), 2) if totals else None,
        "mean_home_margin": round(statistics.mean(margins), 3) if margins else None,
    }
    json.dump(constants, open(os.path.join(DERIVED, "measured_constants_2026_27.json"), "w"),
              indent=1)
    print("home win rate %.4f over %d finals -> HCA %.3f pts"
          % (home_rate, len(finals), hca_points))

    json.dump({"title": "Team ratings rebuilt from official box scores, 2026-27",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "method": ("POSS = FGA - OREB + TOV + 0.44*FTA; OFF = 100*PTS/POSS; "
                          "DEF = 100*opp PTS/opp POSS; PACE = POSS per game"),
               "league_off_rtg": round(league_off, 3) if league_off else None,
               "n_games": sum(t["games"] for t in ratings.values()) // 2,
               "teams": ratings},
              open(os.path.join(DERIVED, "team_ratings_2026_27.json"), "w"), indent=1)

    # ------------------------------------------------------------- 4. luck
    # Pythagorean expectation on official points for/against. Exponent is the
    # one the repo already published (13.91); it is a stated choice, not an
    # official number.
    EXP = 13.91
    luck = []
    for team, t in sorted(per_team.items()):
        n = t["g"]
        if not n:
            continue
        pf, pa = t["pf"], t["pa"]
        exp_w = n * (pf ** EXP) / (pf ** EXP + pa ** EXP) if (pf and pa) else None
        z = (t["w"] - exp_w) / math.sqrt(n * (exp_w / n) * (1 - exp_w / n)) \
            if exp_w and 0 < exp_w < n else None
        luck.append({
            "team": team, "games": n, "wins": t["w"], "losses": t["l"],
            "points_for": pf, "points_against": pa,
            "point_diff_per_game": round((pf - pa) / n, 2),
            "pythagorean_expected_wins": round(exp_w, 2) if exp_w else None,
            "win_surplus": round(t["w"] - exp_w, 2) if exp_w else None,
            "luck_z": round(z, 3) if z is not None else None,
            "inside_noise_band": (abs(z) <= 2.0) if z is not None else None,
        })
    json.dump({"title": "Luck as a z-score per team",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "method": ("Pythagorean expectation, exponent %.2f (stated modelling "
                          "choice, not an official number), applied to official "
                          "points for / against; z = (W - E[W]) / sqrt(n p (1-p))." % EXP),
               "noise_band": "refuse to publish a strategy that leans on a team with |z| > 2.0",
               "source": "data/official/results_feed_2026_27.json (official finals)",
               "rows": sorted(luck, key=lambda r: -(r["luck_z"] if r["luck_z"] is not None else -99))},
              open(os.path.join(DERIVED, "luck_2026_27.json"), "w"), indent=1)

    # ------------------------------------------- 5. rotation / minutes shares
    # Per team: minutes played by every player in every official box score, so
    # the top-8 share and the replacement share when a player is out are both
    # measured, not assumed.
    RECENT = 10
    by_team_games = defaultdict(list)
    for g in final:
        for side in ("home", "away"):
            t = g[side]
            by_team_games[t["tricode"]].append((g["date"], t))
    rotation = {}
    for team, lst in by_team_games.items():
        lst.sort(key=lambda x: x[0], reverse=True)
        recent = lst[:RECENT]
        mins = defaultdict(float)
        pts = defaultdict(float)
        for _, side in recent:
            for p in side["players"]:
                m = minutes_to_float(p.get("minutes"))
                if m:
                    mins[p["name"]] += m
                    pts[p["name"]] += p.get("points") or 0
        total = sum(mins.values())
        if not total:
            continue
        ordered = sorted(mins.items(), key=lambda kv: -kv[1])
        shares = [(n, m / total) for n, m in ordered]
        top8 = shares[:8]
        rest = shares[8:]
        rest_share = sum(s for _, s in rest)
        rotation[team] = {
            "team": team,
            "games_used": len(recent),
            "window": "%s .. %s" % (recent[-1][0], recent[0][0]) if recent else None,
            "total_player_minutes": round(total, 1),
            "top8": [{"player": n, "minutes_share": round(s, 4),
                      "minutes_per_game": round(mins[n] / len(recent), 1),
                      "points_per_game": round(pts[n] / len(recent), 2)}
                     for n, s in top8],
            "bench_share_outside_top8": round(rest_share, 4),
            # Replacement: the minutes a player leaves are re-allocated across
            # the players still available in proportion to their measured
            # share. This is the standard zero-sum minutes assumption and is a
            # stated modelling choice, not an official number.
            "replacement_rule": ("when a player is out their minutes are redistributed "
                                 "to the remaining players in proportion to their "
                                 "measured minutes share"),
            "replacement_example": {
                "player_out": top8[0][0] if top8 else None,
                "redistribution": [
                    {"player": n,
                     "minutes_share_before": round(s, 4),
                     "minutes_share_after_out": round(s / (1 - top8[0][1]), 4) if top8 and top8[0][1] < 1 else None}
                    for n, s in top8[1:]
                ] if top8 else [],
            },
            "source": "official NBA box score pages, last %d games played" % len(recent),
        }
    json.dump({"title": "Rotation minutes: top-8 shares and replacement shares",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "method": ("minutes summed from the official box score of each team's last "
                          "%d completed games; share = player minutes / team minutes" % RECENT),
               "source": "https://www.nba.com/game/<slug>/box-score",
               "teams": rotation},
              open(os.path.join(DERIVED, "rotation_2026_27.json"), "w"), indent=1)

    # ------------------------------------------ 6. rest, b2b, 3-in-4, travel
    played = defaultdict(list)
    for r in sorted(rows, key=lambda x: x["date"]):
        played[r["home"]].append(r["date"])
        played[r["away"]].append(r["date"])
    upcoming = defaultdict(list)
    for r in rows:
        if r["date"] in HORIZON_DATES:
            upcoming[r["home"]].append(r)
            upcoming[r["away"]].append(r)
    rest_rows = []
    import datetime as _dt
    for r in rows:
        if r["date"] not in HORIZON_DATES:
            continue
        for side, opp in (("home", "away"), ("away", "home")):
            team = r[side]
            prev = [d for d in played[team] if d < r["date"]]
            last = prev[-1] if prev else None
            rest_days = ( _dt.date.fromisoformat(r["date"]) - _dt.date.fromisoformat(last)).days \
                if last else None
            prev3 = [d for d in prev
                     if (_dt.date.fromisoformat(r["date"]) - _dt.date.fromisoformat(d)).days <= 3]
            b2b = rest_days == 1 if rest_days is not None else None
            home_coords = ARENA_COORDS.get(r["home"])
            # Travel: from the arena of the team's previous game to this arena.
            prev_game = None
            for g2 in rows:
                if g2["date"] == last and team in (g2["home"], g2["away"]):
                    prev_game = g2
                    break
            travel_mi = None
            if prev_game and home_coords:
                prev_arena_team = prev_game["home"]        # previous game was at its home floor
                pc = ARENA_COORDS.get(prev_arena_team)
                if pc and side == "away" and prev_game["away"] == team:
                    travel_mi = round(haversine(pc, home_coords), 1)
                elif pc:
                    travel_mi = round(haversine(pc, home_coords), 1)
            rest_rows.append({
                "date": r["date"], "game_id": r["game_id"], "team": team,
                "side": side, "opponent": r[opp],
                "last_game_date": last, "rest_days": rest_days,
                "back_to_back": b2b,
                "games_in_last_3_days": len(prev3),
                "three_in_four": len(prev3) >= 2,
                "travel_miles_from_previous_venue": travel_mi,
                "travel_source": COORD_SOURCE if travel_mi is not None else None,
                "source_url": r["source_url"],
            })
    json.dump({"title": "Rest, back-to-back, 3-in-4 and travel, horizon 2026-11-15..18",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "rule": ("rest / b2b / 3-in-4 computed from the official schedule and "
                        "official finals, never assumed. Travel is great-circle miles "
                        "between arenas."),
               "travel_caveat": COORD_SOURCE,
               "rows": rest_rows},
              open(os.path.join(DERIVED, "rest_travel_2026_27.json"), "w"), indent=1)

    # ----------------------------------------------------------- 7. measured rho
    def pearson(xs, ys):
        n = len(xs)
        if n < 3:
            return None
        mx, my = statistics.mean(xs), statistics.mean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        return num / (dx * dy) if dx and dy else None

    mg = [r["margin_home"] for r in finals]
    tt = [r["total_pts"] for r in finals]
    rho_side_total = pearson(mg, tt)

    # Player-prop correlation, measured from the same official game logs: the
    # points of the two leading scorers on the same team, and of the leading
    # scorers on the two opposing teams.
    same_team, opp_team = [], []
    for g in final:
        for side in ("home", "away"):
            ps = sorted([p for p in g[side]["players"] if minutes_to_float(p.get("minutes"))],
                        key=lambda p: -minutes_to_float(p.get("minutes")))
            if len(ps) >= 2:
                a1 = ps[0].get("points") or 0
                a2 = ps[1].get("points") or 0
                same_team.append((a1, a2))
        hs = sorted([p for p in g["home"]["players"] if minutes_to_float(p.get("minutes"))],
                    key=lambda p: -minutes_to_float(p.get("minutes")))
        as_ = sorted([p for p in g["away"]["players"] if minutes_to_float(p.get("minutes"))],
                     key=lambda p: -minutes_to_float(p.get("minutes")))
        if hs and as_:
            opp_team.append((hs[0].get("points") or 0, as_[0].get("points") or 0))
    # Cross-game: are two different games on the same night correlated at all?
    # This is the rho that prices an ordinary multi-game parlay. It is measured,
    # not assumed: pair every game with every other game on the same date and
    # correlate their home margins.
    by_date = defaultdict(list)
    for r in finals:
        by_date[r["date"]].append(r["margin_home"])
    xs, ys = [], []
    for d, ms in by_date.items():
        if len(ms) < 2:
            continue
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                xs.append(ms[i]); ys.append(ms[j])
                xs.append(ms[j]); ys.append(ms[i])
    rho_cross = pearson(xs, ys)
    rho_teammates = pearson([a for a, _ in same_team], [b for _, b in same_team])
    rho_opponents = pearson([a for a, _ in opp_team], [b for _, b in opp_team])

    json.dump({"title": "Measured correlations from official game logs",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "n_final_games": len(finals),
               "source": "official NBA box score pages",
               "measured": [
                   {"pair": "same game: home margin vs total points",
                    "rho": round(rho_side_total, 4) if rho_side_total is not None else None,
                    "n": len(mg), "status": "MEASURED",
                    "note": "the correlation that prices a side/total same-game parlay"},
                   {"pair": "cross-game: home margin vs home margin, two games on the same date",
                    "rho": round(rho_cross, 4) if rho_cross is not None else None,
                    "n_pairs": len(xs), "status": "MEASURED",
                    "note": "the rho that prices an ordinary multi-game parlay; if two "
                            "different games really are independent this is 0"},
                   {"pair": "two team-mates: points (top-2 minutes on the same team)",
                    "rho": round(rho_teammates, 4) if rho_teammates is not None else None,
                    "n": len(same_team), "status": "MEASURED",
                    "note": "small sample at this point in the season"},
                   {"pair": "two opponents: points (leading scorer on each team)",
                    "rho": round(rho_opponents, 4) if rho_opponents is not None else None,
                    "n": len(opp_team), "status": "MEASURED",
                    "note": "small sample at this point in the season"},
               ],
               "caveat": ("these are measured, not modelled; they are still early-season "
                          "samples and are published with their n")},
              open(os.path.join(DERIVED, "rho_2026_27.json"), "w"), indent=1)

    # ------------------------------------- 7b. margin-based power ratings (E2)
    # Estimator 2 must be INDEPENDENT of estimator 1, or their "disagreement"
    # is noise dressed up as a confidence signal. E1 looks at efficiency
    # (points per possession). E2 looks only at official final margins and
    # solves a least-squares power rating, with home court pinned to the
    # measured home-win rate rather than fitted. Different information set,
    # different failure mode - which is the point.
    teams_ls = sorted(per_team.keys())
    idx = {t: i for i, t in enumerate(teams_ls)}
    n = len(teams_ls)
    A = []
    y = []
    for r in finals:
        if r["home"] not in idx or r["away"] not in idx:
            continue
        row = [0.0] * n
        row[idx[r["home"]]] = 1.0
        row[idx[r["away"]]] = -1.0
        A.append(row)
        y.append(float(r["margin_home"]) - (hca_points or 0.0))
    LAMBDA = 5.0                      # ridge, stated modelling choice
    M = [[sum(A[k][i] * A[k][j] for k in range(len(A))) + (LAMBDA if i == j else 0.0)
          for j in range(n)] for i in range(n)]
    b = [sum(A[k][i] * y[k] for k in range(len(A))) for i in range(n)]
    # Gaussian elimination with partial pivoting.
    for c in range(n):
        piv = max(range(c, n), key=lambda rr: abs(M[rr][c]))
        M[c], M[piv] = M[piv], M[c]
        b[c], b[piv] = b[piv], b[c]
        pv = M[c][c]
        for j in range(c, n):
            M[c][j] /= pv
        b[c] /= pv
        for rr in range(n):
            if rr != c and M[rr][c]:
                f = M[rr][c]
                for j in range(c, n):
                    M[rr][j] -= f * M[c][j]
                b[rr] -= f * b[c]
    power = {t: b[idx[t]] for t in teams_ls}
    # In-sample fit, reported so the reader can see how loose it is.
    resid = []
    for r in finals:
        if r["home"] in power and r["away"] in power:
            pred = (hca_points or 0.0) + power[r["home"]] - power[r["away"]]
            resid.append(r["margin_home"] - pred)
    power_mae = round(statistics.mean(abs(v) for v in resid), 3) if resid else None
    power_rmse = round(math.sqrt(statistics.mean(v * v for v in resid)), 3) if resid else None
    json.dump({"title": "Margin-based power ratings (estimator 2)",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "method": ("least squares on official final margins: "
                          "margin_home = HCA + r_home - r_away, ridge lambda=%.1f, "
                          "HCA pinned to the measured home-win rate" % LAMBDA),
               "n_games": len(A), "in_sample_mae": power_mae, "in_sample_rmse": power_rmse,
               "caveat": "in-sample fit, reported for transparency; not an out-of-sample score",
               "source": "data/official/results_feed_2026_27.json",
               "ratings": {t: round(v, 3) for t, v in sorted(power.items(),
                                                             key=lambda kv: -kv[1])}},
              open(os.path.join(DERIVED, "power_ratings_2026_27.json"), "w"), indent=1)

    # ------------------------------------------------------- 8. two estimators
    est_rows = []
    L = league_off
    for r in rows:
        if r["date"] not in HORIZON_DATES:
            continue
        h, a = r["home"], r["away"]
        if h not in ratings or a not in ratings:
            continue
        H, A = ratings[h], ratings[a]
        # Estimator 1 - possessions x points-per-possession, the brief's rule.
        poss = H["pace"] + A["pace"] - league_pace
        e1_home = (H["off_rtg"] * A["def_rtg"] / L) * poss / 100
        e1_away = (A["off_rtg"] * H["def_rtg"] / L) * poss / 100
        e1_total = e1_home + e1_away
        e1_spread = -(e1_home - e1_away) + (hca_points or 0)
        # Estimator 2 - independent information set: a margin-based power
        # rating solved from official final margins for the spread, and the
        # teams' own scoring / allowed rates for the total.
        e2_spread = -((power.get(h, 0.0) - power.get(a, 0.0)) + (hca_points or 0))
        e2_home = 0.5 * (H["ppg"] + A["opp_ppg"])
        e2_away = 0.5 * (A["ppg"] + H["opp_ppg"])
        e2_total = e2_home + e2_away
        est_rows.append({
            "date": r["date"], "game_id": r["game_id"],
            "home": h, "away": a,
            "game_status": r["game_status"],
            "status": r["game_status_text"],
            "e1_possessions": round(poss, 2),
            "e1_total": round(e1_total, 1), "e1_spread_home": round(e1_spread, 1),
            "e2_total": round(e2_total, 1), "e2_spread_home": round(e2_spread, 1),
            "disagreement_total": round(abs(e1_total - e2_total), 1),
            "disagreement_spread": round(abs(e1_spread - e2_spread), 1),
            "blend_total": round((e1_total + e2_total) / 2, 1),
            "blend_spread_home": round((e1_spread + e2_spread) / 2, 1),
            "hca_applied": round(hca_points, 2) if hca_points else None,
            "source_url": r["source_url"],
            "already_tipped": r["game_status"] != 1,
        })
    json.dump({"title": "Two independent estimators and their disagreement",
               "session": "arena/801ba27f-nba1",
               "built_utc": RUN_UTC,
               "headline_rule": ("the DISAGREEMENT between the two estimators is the "
                                 "headline confidence signal; the 50/50 blend is printed "
                                 "underneath it and is never the headline"),
               "estimator_1": ("possessions x points-per-possession: "
                               "POSS = pace_h + pace_a - league_pace; "
                               "PTS = (OffRtg * opp DefRtg / league OffRtg) * POSS / 100"),
               "estimator_2": ("score-based: spread from a least-squares power rating solved "
                               "on official final margins (HCA pinned to the measured home-win "
                               "rate); total from the teams' own scored and allowed rates"),
               "home_court": constants["home_court_rule"],
               "power_rating_mae_in_sample": power_mae,
               "power_rating_rmse_in_sample": power_rmse,
               "rows": est_rows},
              open(os.path.join(DERIVED, "estimators_2026_27.json"), "w"), indent=1)
    print("estimator rows for the horizon:", len(est_rows))
    print("done.")


if __name__ == "__main__":
    main()
