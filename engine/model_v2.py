"""model_v2.py — the second-generation line origination model.

Every input is an official capture.  Nothing here is fitted freely:

  measured home-court anchor  data/official/standings_*.json  and the official
                               results corpus (data/official/gamelog.json)
  team efficiency/traditional  data/official/teams_advanced|traditional|opponent_*.json
  schedule, venues            data/official/official_schedule_2026-11-15_to_19.json
  arena coordinates           data/official/arena_coordinates_2026-11-15.json
  injury statuses             data/official/injury_*.json
  per-player minutes          data/official/players_minutes_*.json (optional)

Feature map (the brief, and where each one lives in this file):

  possession x PPP total          ppp_construction()
  measured home-court advantage   hca_from_measured_home_win_rate()
  two independent estimators      estimator_a() / estimator_b() / blend_estimators()
  disagreement as headline signal blend_estimators() -> disagreement
  minutes redistribution         minutes_redistribution()
  rest / back-to-back / 3-in-4    rest_profile()
  travel distance                 travel_distance()
  luck z-score per team           luck_table()
  market prior by OOS log-loss    market_blend()  (market leg flagged when absent)
  parlay rho pricing              measured_rho() / price_parlay()

Modelling choices (not official facts) are listed in ASSUMPTIONS and are
surfaced on the site as assumptions, never as sourced values.
"""

import datetime
import json
import math
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.path.join(ROOT, "data", "official")
DERIVED = os.path.join(ROOT, "data", "derived")

TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

# share of a listed player's captured minutes the redistribution removes
# (1 - the play probability the repo publishes by status)
ABSENCE_SHARE = {"Out": 1.00, "Doubtful": 0.75, "Questionable": 0.50,
                 "Probable": 0.20, "Available": 0.00}

ASSUMPTIONS = {
    "league_pace_formula": {
        "value": "POSS_game = pace_home + pace_away - league_pace",
        "status": "ARITHMETIC identity used by the published NBA efficiency "
                  "construction; the model also publishes the possession "
                  "estimate taken straight from the official POSS column.",
    },
    "opponent_ppp_scaling": {
        "value": "PPP_proj(team) = PPP_off(team) * PPP_def(opponent) / league_PPP_def",
        "status": "DERIVED from the official points-per-possession fields; the "
                  "scaling exponent is a modelling choice fixed at 1.0.",
    },
    "estimator_blend_weights": {
        "value": 0.5,
        "status": "MODELLING CHOICE - the two estimators are blended with equal "
                  "weight. The headline confidence signal is their DISAGREEMENT, "
                  "not the blend, so the blend weight does not drive the "
                  "confidence gate.",
    },
    "bench_efficiency_ratio": {
        "value": 0.85,
        "status": "MODELLING CHOICE - replacement players are assumed to "
                  "produce at 0.85 points per minute of the absent player's rate. "
                  "Sensitivity 0.75 / 0.85 / 0.95 is published. Flagged F4.",
    },
    "replacement_pool_size": {
        "value": 5,
        "status": "MODELLING CHOICE - the replacement pool is the five rotation "
                  "players behind the top eight by minutes.",
    },
    "absence_minutes_share_by_status": {
        "value": {"Out": 1.00, "Doubtful": 0.75, "Questionable": 0.50,
                  "Probable": 0.20, "Available": 0.00},
        "status": "MODELLING CHOICE - the share of a listed player's captured "
                  "season minutes that the redistribution removes is one minus "
                  "the repo's published play probability by status "
                  "(STATUS_PLAY_PROB). Available players lose nothing; "
                  "Questionable players lose an expected half. The removed "
                  "minutes are re-spread at the bench-efficiency ratio.",
    },
    "team_name_to_abbr": {
        "value": "canonical mapping of the official full team names to the "
                 "three-letter abbreviations used by every official surface",
    },
    "rest_penalty_points": {
        "value": {"b2b": 1.1, "three_in_four": 0.6},
        "status": "MODELLING CHOICE - net-rating points per 100 possessions "
                  "conceded to a team on a back-to-back or that has played three "
                  "games in four. Flagged F4.",
    },
    "travel_penalty_points": {
        "value": "0.0012 points per mile of great-circle distance",
        "status": "MODELLING CHOICE - calibrated so that a 3,000-mile "
                  "cross-country trip is worth about 3.6 net-rating points per "
                  "100 possessions. Flagged F4.",
    },
    "luck_noise_band_z": {
        "value": 1.5,
        "status": "MODELLING CHOICE - a strategy that leans on a team whose "
                  "luck z-score is outside +/-1.5 is refused. Flagged F4.",
    },
    "market_leg_weight": {
        "value": 0.0,
        "status": "BLOCKED BY SOURCE, not chosen: no official closing line is "
                  "reachable from this sandbox, so the market leg of the blend "
                  "carries zero weight and the blend is model-only. The "
                  "machinery and the measured out-of-sample log loss that would "
                  "set the weight are implemented and published.",
    },
}


# ----------------------------------------------------------------- small maths

def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    """Acklam's inverse normal CDF (|error| < 1.15e-9)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    # one Halley refinement
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    x = x - u / (1 + x * u / 2)
    return x


def bivariate_normal_cdf(a, b, rho):
    """P(X <= a, Y <= b) for a standard bivariate normal with correlation rho.

    Plackett's identity:
        P = Phi(a)Phi(b) + integral_0^rho phi2(a,b;phi) dphi
    integrated with Simpson's rule (4000 intervals -> |error| < 1e-10).
    """
    if rho == 0:
        return norm_cdf(a) * norm_cdf(b)
    if rho <= -0.9999:
        return max(0.0, norm_cdf(a) + norm_cdf(b) - 1.0)
    if rho >= 0.9999:
        return min(norm_cdf(a), norm_cdf(b))
    n = 4000
    h = rho / n
    total = 0.0

    def f(phi):
        if abs(phi) >= 1.0:
            phi = math.copysign(0.999999999, phi)
        denom = 1.0 - phi * phi
        expo = -(a * a - 2.0 * phi * a * b + b * b) / (2.0 * denom)
        return math.exp(expo) / (2.0 * math.pi * math.sqrt(denom))

    total += f(0.0)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(i * h)
    total += f(rho)
    integral = total * h / 3.0
    return min(1.0, max(0.0, norm_cdf(a) * norm_cdf(b) + integral))


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8  # mean earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pstdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None, None, n
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    dx = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs))
    dy = math.sqrt(sum((p[1] - my) ** 2 for p in pairs))
    if dx == 0 or dy == 0:
        return None, None, n
    r = num / (dx * dy)
    # two-tailed p-value from the t approximation
    t = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    p = 2 * (1 - student_t_cdf(abs(t), n - 2))
    return r, p, n


def student_t_cdf(t, df):
    x = df / (df + t * t)
    ib = 0.5 * _betainc(df / 2.0, 0.5, x)
    return 1 - ib if t > 0 else ib


def _betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = (math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-10:
            break
    return front * (f - 1.0)


def log_loss(probs, outcomes):
    """Mean binary log loss (lower is better)."""
    vals = []
    for p, y in zip(probs, outcomes):
        p = min(max(p, 1e-6), 1 - 1e-6)
        vals.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
    return sum(vals) / len(vals) if vals else None


# ------------------------------------------------------------------ official IO

def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def latest(prefix):
    """Newest file in data/official whose name starts with prefix."""
    files = sorted(f for f in os.listdir(OFF) if f.startswith(prefix) and f.endswith(".json"))
    if not files:
        return None
    return os.path.join(OFF, files[-1])


def load_team_tables():
    """The three official team-stat tables, newest capture of each."""
    out = {}
    for key, prefix in (("advanced", "teams_advanced_"),
                        ("traditional", "teams_traditional_"),
                        ("opponent", "teams_opponent_")):
        path = latest(prefix)
        doc = _load(path)
        out[key] = {r["abbr"]: r for r in doc["rows"]}
        out[key + "_source"] = doc.get("source_url")
        out[key + "_file"] = os.path.basename(path)
    return out


def load_standings():
    path = latest("standings_2026-")
    doc = _load(path)
    return doc, os.path.basename(path)


def load_schedule():
    """Union of every official schedule capture, newest capture winning per
    game id.

    Why a union and not "the newest file": a later capture is usually a
    narrower window (this session re-read only the 3-day pick window), while an
    earlier capture carries fields the narrower read does not print - the
    venue and city, which the travel-distance context needs.  Merging per game
    id keeps both: the newest read supplies the fields it re-read (tip time,
    date, teams), and the earlier read supplies the fields it did not (venue).

    A field the newer row leaves empty is filled from the older row; a field
    both carry is taken from the newer row and any disagreement is recorded by
    the capture itself in its `conflicts` list.
    """
    files = sorted(f for f in os.listdir(OFF)
                   if f.startswith("official_schedule_") and f.endswith(".json"))
    merged, order = {}, []
    for name in files:
        doc = _load(os.path.join(OFF, name))
        for r in doc.get("rows", []):
            gid = r.get("game_id")
            if not gid:
                order.append(r)
                continue
            if gid not in merged:
                merged[gid] = {}
                order.append(merged[gid])
            base = merged[gid]
            for k, v in r.items():
                if v not in (None, "", []):
                    base[k] = v
    rows = [r for r in order if r]
    rows.sort(key=lambda r: (r.get("date") or "", r.get("game_id") or ""))
    return {"title": "official schedule, merged from %d captures" % len(files),
            "sources": files, "rows": rows}


def load_arenas():
    return _load(os.path.join(OFF, "arena_coordinates_2026-11-15.json"))


def _more_complete(a, b):
    """True when row a carries strictly more settled information than row b.

    A row is more complete when it has final scores and the other does not;
    ties are broken in favour of the row that reports a status of FINAL.
    """
    def done(r):
        return r.get("home_pts") is not None and r.get("away_pts") is not None
    if done(a) != done(b):
        return done(a)
    return str(r_get(a, "status") or "").upper().startswith("FINAL") and not \
        str(r_get(b, "status") or "").upper().startswith("FINAL")


def r_get(row, key):
    return row.get(key)


def _played(g):
    """True only for a game that has actually finished.

    Three ways an unplayed row gets into a results file, all measured in
    data/official/results_feed_2026_27.json on 2026-11-16 (session
    arena/23ec1e32-nba1, COORDINATION §55 W01):

      * `game_status: 1` (scheduled) with tied placeholder scores 0-0 — 25 such
        rows (11/16-11/18) were being counted as road wins and as 25 zero
        margins, which deflated sigma_margin and broke the home-win anchor
        (finding F113's mechanical cause);
      * `game_status: 2` (live) with partial scores — must not be read as final;
      * a null score in a mid-game capture.

    A finished row has game_status == 3 where the field exists, and otherwise
    two present, unequal scores: an NBA game never ends tied.
    """
    st = g.get("game_status")
    if st is not None:
        try:
            return int(st) == 3
        except (TypeError, ValueError):
            return False
    hp, ap = g.get("home_pts"), g.get("away_pts")
    if hp is None or ap is None:
        return False
    return hp != ap


def load_results():
    """Official completed-game corpus: the season game log plus the dated
    results files, filtered to games that have finished (`_played`).
    Each row: date, away, home, away_pts, home_pts, neutral."""
    games = []
    path = os.path.join(OFF, "gamelog.json")
    if os.path.exists(path):
        for g in _load(path)["games"]:
            games.append(dict(g))
    for name in sorted(os.listdir(OFF)):
        if name.startswith("results_") and name.endswith(".json"):
            doc = _load(os.path.join(OFF, name))
            for g in doc.get("games", doc.get("rows", [])):
                if isinstance(g, dict) and "home_pts" in g and _played(g):
                    games.append(dict(g))
    games = [g for g in games if _played(g)]
    # De-duplicate on game id.  A later capture wins over an earlier one when
    # the later one is more complete: the 2026-11-15 slate was captured
    # mid-game, so the first capture of those ids carries null scores while a
    # later capture carries finals.  Keeping "the first row" would freeze the
    # nulls in and the finals out, so completeness decides, not file order.
    by_id = {}
    for g in games:
        gid = g.get("game_id")
        if not gid:
            continue
        cur = by_id.get(gid)
        if cur is None or _more_complete(g, cur):
            by_id[gid] = g
    seen, uniq = set(), []
    for g in games:
        gid = g.get("game_id")
        if gid and gid in by_id:
            if gid not in seen:
                seen.add(gid)
                uniq.append(by_id[gid])
        else:
            uniq.append(g)
    return uniq


# --------------------------------------------------------------- league tables

def league_inputs():
    """League baselines and per-team efficiency fields from the official tables."""
    tabs = load_team_tables()
    adv, tra, opp = tabs["advanced"], tabs["traditional"], tabs["opponent"]
    teams = {}
    for ab in adv:
        a, t, o = adv[ab], tra.get(ab, {}), opp.get(ab, {})
        gp = float(a["gp"])
        poss_game = float(a["poss"]) / gp if gp else None
        ppg = float(t.get("pts") or 0)
        opp_ppg = float(o.get("opp_pts") or 0)
        ppp_off = ppg / poss_game if poss_game else None
        ppp_def = opp_ppg / poss_game if poss_game else None
        teams[ab] = {
            "abbr": ab, "name": t.get("team") or a.get("team"),
            "gp": int(gp), "w": a["w"], "l": a["l"],
            "off_rtg": a["off_rtg"], "def_rtg": a["def_rtg"], "net_rtg": a["net_rtg"],
            "pace": a["pace"], "poss_total": a["poss"], "poss_game": poss_game,
            "pts_per_game": ppg, "opp_pts_per_game": opp_ppg,
            "ppp_off": ppp_off, "ppp_def": ppp_def,
            "efg_pct": a.get("efg_pct"), "ts_pct": a.get("ts_pct"),
            "tov_pct": a.get("tov_pct"), "oreb_pct": a.get("oreb_pct"),
            "dreb_pct": a.get("dreb_pct"), "pie": a.get("pie"),
            "source_url": tabs["advanced_source"],
        }
    league = {
        "league_off_rtg": mean([t["off_rtg"] for t in teams.values()]),
        "league_def_rtg": mean([t["def_rtg"] for t in teams.values()]),
        "league_pace": mean([t["pace"] for t in teams.values()]),
        "league_pts_per_game": mean([t["pts_per_game"] for t in teams.values()]),
        "league_opp_pts_per_game": mean([t["opp_pts_per_game"] for t in teams.values()]),
        "league_ppp_off": mean([t["ppp_off"] for t in teams.values()]),
        "league_ppp_def": mean([t["ppp_def"] for t in teams.values()]),
        "n_teams": len(teams),
    }
    return teams, league, tabs


# --------------------------------------------------- measured home-court edge

def hca_from_measured_home_win_rate(home_win_rate, sigma_margin):
    """Pin the home-court advantage to the MEASURED home win rate.

    The model with no home advantage is fair: its expected margin is 0 and its
    home win rate is 0.5.  The smallest margin shift that reproduces the
    measured home win rate at the fitted dispersion is

        HCA_points = sigma_margin * Phi^-1(measured_home_win_rate)

    so the number of points is not fitted - it is read off the measurement.
    """
    if home_win_rate is None or not sigma_margin:
        return None, None
    z = norm_ppf(home_win_rate)
    return z * sigma_margin, z


def measured_home_win_rate(results, standings_doc=None):
    """Home win rate measured on official final scores (neutral games removed)."""
    hw = hg = rw = rg = 0
    for g in results:
        if g.get("neutral"):
            continue
        if g.get("home_pts") is None or g.get("away_pts") is None:
            continue
        hg += 1
        rg += 1
        if g["home_pts"] > g["away_pts"]:
            hw += 1
        else:
            rw += 1
    out = {"source": "official final scores (data/official/gamelog.json + results_*.json)",
           "home_games": hg, "home_wins": hw,
           "road_games": rg, "road_wins": rw,
           "home_win_rate": (hw / hg) if hg else None,
           "road_win_rate": (rw / rg) if rg else None,
           "n_games": hg}
    if standings_doc:
        a = standings_doc["measured_home_court_anchor"]
        out["standings_anchor"] = {
            "home_win_rate": a["home_win_rate"],
            "road_win_rate": a["road_win_rate"],
            "home_games": a["home_games"], "road_games": a["road_games"],
            "source_url": a["source_url"]}
    return out


# ------------------------------------------------------------------ estimators

def game_possessions(home, away, league):
    """Possessions in one game, from the official PACE fields.

    POSS = pace_home + pace_away - league_pace is the published identity; the
    possession count implied by the official POSS column is published next to
    it so a reviewer can see both.
    """
    ident = home["pace"] + away["pace"] - league["league_pace"]
    from_poss = None
    if home.get("poss_game") and away.get("poss_game"):
        from_poss = (home["poss_game"] + away["poss_game"]) / 2.0
    return ident, from_poss


def estimator_a(home, away, league, hca_points=0.0, alpha=0.60):
    """Estimator A - the possession x points-per-possession estimator.

    PPP_proj(team)   = PPP_off(team) * PPP_def(opponent) / league_PPP_def
    TOTAL            = game_possessions * (PPP_proj_home + PPP_proj_away)
    SPREAD           = game_possessions * (PPP_proj_home - PPP_proj_away)
    """
    poss, poss_from_column = game_possessions(home, away, league)
    ldef = league["league_ppp_def"] or 1.0
    ppp_h = home["ppp_off"] * (away["ppp_def"] / ldef)
    ppp_a = away["ppp_off"] * (home["ppp_def"] / ldef)
    scale = poss / 100.0
    pts_h = ppp_h * poss
    pts_a = ppp_a * poss
    margin = pts_h - pts_a + hca_points
    total = pts_h + pts_a
    return {
        "estimator": "A: possession x points-per-possession (official efficiency, "
                     "traditional and opponent tables)",
        "game_possessions": round(poss, 2),
        "game_possessions_from_official_poss_column": round(poss_from_column, 2) if poss_from_column else None,
        "ppp_proj_home": round(ppp_h, 4), "ppp_proj_away": round(ppp_a, 4),
        "pts_home": round(pts_h, 1), "pts_away": round(pts_a, 1),
        "margin": round(margin, 1), "total": round(total, 1),
    }


def estimator_b(home, away, league, hca_points=0.0):
    """Estimator B - the points-based estimator, built from a different set of
    official fields so that its errors are not the same as estimator A's.

    It uses only points scored and points allowed (official traditional and
    opponent tables) plus the pace adjustment; it never touches the
    offensive/defensive efficiency ratings that estimator A uses.

    PTS_home = PTS_home_per_game * (OPP_PTS_away / league_OPP_PTS) * pace_factor
    pace_factor = game_possessions / league_pace
    """
    poss, _ = game_possessions(home, away, league)
    lopp = league["league_opp_pts_per_game"] or 1.0
    pace_factor = poss / league["league_pace"] if league["league_pace"] else 1.0
    adj_h = (away["opp_pts_per_game"] / lopp) * pace_factor
    adj_a = (home["opp_pts_per_game"] / lopp) * pace_factor
    pts_h = home["pts_per_game"] * adj_h
    pts_a = away["pts_per_game"] * adj_a
    margin = pts_h - pts_a + hca_points
    total = pts_h + pts_a
    return {
        "estimator": "B: points-scored / points-allowed with an opponent and pace "
                     "adjustment (official traditional and opponent tables only)",
        "game_possessions": round(poss, 2),
        "pace_factor": round(pace_factor, 4),
        "pts_home": round(pts_h, 1), "pts_away": round(pts_a, 1),
        "margin": round(margin, 1), "total": round(total, 1),
    }


def blend_estimators(a, b, sigma_margin):
    """Blend the two estimators UNDERNEATH and publish their disagreement as
    the headline confidence signal."""
    pa = norm_cdf(a["margin"] / sigma_margin)
    pb = norm_cdf(b["margin"] / sigma_margin)
    w = ASSUMPTIONS["estimator_blend_weights"]["value"]
    p_blend = w * pa + (1 - w) * pb
    disagreement = abs(pa - pb)
    return {
        "p_home_win_estimator_a": round(pa, 4),
        "p_home_win_estimator_b": round(pb, 4),
        "p_home_win_blend": round(p_blend, 4),
        "disagreement": round(disagreement, 4),
        "disagreement_pp": round(disagreement * 100, 2),
        "confidence_signal": (
            "HEADLINE: |P(A) - P(B)| = %.2f percentage points. A small "
            "disagreement means two independent official-input constructions "
            "agree, so the number is trustworthy; a large one means the line "
            "is not safe to publish." % (disagreement * 100)),
        "blend_weight_a": w, "blend_weight_b": 1 - w,
        "margin_blend": round(w * a["margin"] + (1 - w) * b["margin"], 1),
        "total_blend": round(w * a["total"] + (1 - w) * b["total"], 1),
    }


# ------------------------------------------------------------- minutes / injury

def norm_name(s):
    """Normalize a player name for cross-surface matching.

    The official injury-report PDF prints names as 'Last, First' while the
    official stats leaderboard prints 'First Last'; diacritics and initials
    also differ between the two surfaces.  Returns a canonical form:
    'Last, First' reordered, diacritics stripped, punctuation removed,
    casefolded.  Official PDF misspellings (e.g. 'Embid') remain unmatched
    on purpose — nothing is fuzzy-fitted.
    """
    if not s:
        return ""
    s0 = s
    if "," in s0:
        last, first = s0.split(",", 1)
        s0 = first.strip() + " " + last.strip()
    s0 = unicodedata.normalize("NFKD", s0)
    s0 = "".join(c for c in s0 if not unicodedata.combining(c))
    s0 = s0.replace(".", "").replace("'", "")
    return re.sub(r"\s+", " ", s0).strip().lower()


def load_minutes():
    """Per-player season minutes, if a capture exists.  Returns
    {abbr: [player rows]} with team, player, gp, min, pts, ... .

    Preference order:
      1. player_minutes_top50_2026-11-15.json  (official leaderboard, page 1
         of 10 = top 50 league-wide by MIN; pages 2-10 were not reachable —
         the URL Page parameter was not honored by the rendered slice)
      2. players_minutes_2026-11-15.json       (earlier per-team capture, if any)
    """
    candidates = ["player_minutes_top50_2026-11-15.json",
                  "players_minutes_2026-11-15.json"]
    for name in candidates:
        path = os.path.join(OFF, name)
        if not os.path.exists(path):
            continue
        doc = _load(path)
        meta = doc.get("_meta") or {}
        teams = {}
        for r in doc["rows"]:
            teams.setdefault(r["team"], []).append(r)
        for ab in teams:
            teams[ab].sort(key=lambda r: -(r.get("min") or 0))
        return teams, {"available": True, "file": name,
                       "captured_utc": meta.get("captured_utc") or doc.get("captured_utc"),
                       "source_url": meta.get("source_url") or doc.get("source_url"),
                       "rows_captured": meta.get("rows_captured") or len(doc["rows"]),
                       "rows_total_official": meta.get("rows_total_official"),
                       "capture_limitation": meta.get("capture_limitation"),
                       "teams_captured": sorted(teams)}
    return {}, {"available": False,
                "note": "no official per-player minutes capture in this repo yet"}


def minutes_redistribution(team, absent, roster, bench_ratio=None):
    """Explicit minutes redistribution.

    `absent` is a list of dicts: {player, status, min, pts, reb, ast}.
    `roster` is the full team roster sorted by minutes.

    The absent player's minutes leave the rotation.  They are redistributed
    across the remaining rotation in proportion to the minutes those players
    already have, but at the bench-efficiency ratio, because a replacement
    minute is worth less than the minute it replaces.

    Returns the new shares plus the production the team loses.
    """
    if bench_ratio is None:
        bench_ratio = ASSUMPTIONS["bench_efficiency_ratio"]["value"]
    if not roster:
        return None
    total_min = sum(r.get("min") or 0 for r in roster) or 1.0
    absent_names = {norm_name(a["player"]) for a in absent}
    remaining = [r for r in roster if norm_name(r["player"]) not in absent_names]
    if not remaining:
        return None
    gone_minutes = sum(a.get("min") or 0 for a in absent)
    gone_points = sum(a.get("pts") or 0 for a in absent)
    # production per minute of the absent players
    ppm = (gone_points / gone_minutes) if gone_minutes else 0.0
    remaining_minutes = sum(r.get("min") or 0 for r in remaining) or 1.0
    redistributed = []
    for r in remaining:
        share = (r.get("min") or 0) / remaining_minutes
        add = gone_minutes * share
        redistributed.append({
            "player": r["player"],
            "minutes_before": r.get("min"),
            "minutes_added": round(add, 2),
            "share_before": round((r.get("min") or 0) / total_min, 4),
            "share_after": round(((r.get("min") or 0) + add) / (total_min + gone_minutes), 4),
            "expected_points_added": round(add * ppm * bench_ratio, 2),
        })
    lost_points = gone_points
    gained_points = sum(x["expected_points_added"] for x in redistributed)
    return {
        "team": team,
        "minutes_removed": round(gone_minutes, 1),
        "absent_players": absent,
        "production_per_minute_removed": round(ppm, 4),
        "bench_efficiency_ratio": bench_ratio,
        "redistribution": redistributed,
        "team_points_lost": round(lost_points, 2),
        "team_points_gained_by_replacement": round(gained_points, 2),
        "net_points_lost": round(lost_points - gained_points, 2),
        "note": ("minutes that leave the rotation are re-spread across the "
                 "remaining rotation in proportion to existing minutes and "
                 "valued at the bench-efficiency ratio"),
    }


def _mdy_to_iso(d):
    """'11/16/2026' (the injury PDF's Game Date format) -> '2026-11-16'."""
    if not d:
        return None
    parts = str(d).split("/")
    if len(parts) != 3:
        return None
    m, day, y = parts
    return "%s-%s-%s" % (y, m.zfill(2), day.zfill(2))


def rotation_availability(team, injury_rows, roster, game_date=None,
                          covered_dates=None, not_submitted=None):
    """The rotation-availability read-out used on the picks page.

    Provenance is part of the value, so the status string is decided by what
    the official sources actually cover:

    * no per-player minutes capture for the team            -> "not captured"
    * no official injury edition covers this game date yet  -> the percentage
      is left blank and flagged.  Teams file by 5 p.m. local the day before a
      game, so an edition that stops at 11/16 says nothing about 11/17 or
      11/18; an empty injury list is NOT evidence that nobody is injured.
    * the edition covers the date but this team's entry prints
      NOT YET SUBMITTED                                     -> flagged as such
    * otherwise                                             -> "MEASURED"
    """
    if roster is None:
        return {"team": team, "status": "not captured",
                "rotation_players": None, "out": None, "questionable": None,
                "note": "official per-player minutes not captured for this team"}
    covered_dates = covered_dates or set()
    not_submitted = not_submitted or set()
    top = roster[:8]
    names = {norm_name(r["player"]) for r in top}
    out, quest, listed = [], [], []
    for r in injury_rows:
        if r.get("team") != team or not r.get("player"):
            continue
        listed.append(r["player"])
        if r.get("status") == "Out":
            out.append(r["player"])
        elif r.get("status") in ("Questionable", "Doubtful"):
            quest.append(r["player"])
    rotation_out = [p for p in out if norm_name(p) in names]
    rotation_quest = [p for p in quest if norm_name(p) in names]
    res = {
        "team": team,
        "rotation_players": len(top),
        "rotation_players_named": sorted(names),
        "listed_on_injury_report": len(listed),
        "out": sorted(out),
        "questionable": sorted(quest),
        "rotation_out": sorted(rotation_out),
        "rotation_questionable": sorted(rotation_quest),
        "rotation_out_count": len(rotation_out),
        "rotation_questionable_count": len(rotation_quest),
    }
    # ---- provenance, in order of what the official sources actually cover
    if game_date and game_date not in covered_dates:
        res["availability_pct"] = None
        res["status"] = ("NOT YET PUBLISHED - no official injury edition covers "
                         "%s; the newest edition stops at %s. An empty injury "
                         "list is not evidence that nobody is injured, so the "
                         "cell is blank rather than 100%%."
                         % (game_date, ", ".join(sorted(covered_dates)) or "no date"))
    elif (game_date, team) in not_submitted:
        res["availability_pct"] = None
        res["status"] = ("NOT YET SUBMITTED - the official injury edition for "
                         "%s prints NOT YET SUBMITTED for this team, so its "
                         "availability is unknown and the cell is blank."
                         % game_date)
    else:
        res["availability_pct"] = (round(100.0 * (len(top) - len(rotation_out)) / len(top), 1)
                                   if top else None)
        res["status"] = ("MEASURED from the official injury-report edition and the "
                         "official per-player minutes capture")
    return res


# ------------------------------------------------------------- rest and travel

def team_game_dates(results, schedule_rows):
    """date -> list of (home, away) for every team, from official results and
    the official schedule."""
    hist = {}
    for g in results:
        d = g.get("date")
        if not d:
            continue
        hist.setdefault(g["home"], {}).setdefault(d, []).append(g)
        hist.setdefault(g["away"], {}).setdefault(d, []).append(g)
    fut = {}
    for r in schedule_rows:
        d = r["date"]
        fut.setdefault(r["home"], {}).setdefault(d, []).append(r)
        fut.setdefault(r["away"], {}).setdefault(d, []).append(r)
    return hist, fut


def rest_profile(team, game_date, hist, fut, team_arena):
    """Rest days, back-to-back and 3-in-4 for one team, from official dates.

    The 3-in-4 count is the number of games in the four days that END on the
    game date, which is the standard on the wire.
    """
    days = sorted(set(hist.get(team, {})) | set(fut.get(team, {})))
    prior = [d for d in days if d < game_date]
    if not prior:
        return {"rest_days": None, "back_to_back": None, "three_in_four": None,
                "last_date": None, "source": "official results + official schedule",
                "note": "no prior game on the official record"}
    last = prior[-1]
    from datetime import date as _d

    def dd(s):
        y, m, day = (int(x) for x in s.split("-"))
        return _d(y, m, day)

    rest = (dd(game_date) - dd(last)).days - 1
    window = [d for d in days if 0 <= (dd(game_date) - dd(d)).days <= 3]
    return {
        "rest_days": rest,
        "back_to_back": rest == 0,
        "three_in_four": len(window) >= 3,
        "games_in_last_4_days": len(window),
        "last_date": last,
        "last_game_was_home": bool(hist.get(team, {}).get(last)) and
                                  hist[team][last][0].get("home") == team,
        "source": "official results (data/official/gamelog.json) + official schedule",
    }


def travel_distance(away_team, home_team, prev_venue, arenas_by_team, arena_by_name):
    """Great-circle distance from the away team's previous venue to the home
    team's arena, using the sourced arena coordinate table."""
    if not prev_venue:
        return None
    b = arenas_by_team.get(home_team)
    if not b:
        return None
    src = arena_by_name.get(prev_venue)
    if not src:
        return None
    miles = haversine_miles(src["lat"], src["lon"], b["lat"], b["lon"])
    return {
        "from_venue": prev_venue, "from_city": src["city"],
        "to_venue": b["arena"], "to_city": b["city"],
        "miles": round(miles, 0),
        "coordinate_source": b["coordinate_source_url"],
        "venue_source": b["venue_source_url"],
    }


def arenas_by_name(arenas):
    out = {}
    for row in arenas["rows"]:
        out[row["arena"]] = row
    return out


def previous_venue(team, game_date, hist, fut, team_arena, venues_by_home_team):
    """The venue of the team's most recent previous game.

    The official schedule prints the venue of every game, and the venue of a
    home game is the home team's arena; the neutral-site games are listed
    explicitly.  Where the previous game is inside the captured official
    schedule window the venue is taken verbatim from it; otherwise the rule
    (home team's arena) is applied and labelled DERIVED.
    """
    from datetime import date as _d

    def dd(s):
        y, m, day = (int(x) for x in s.split("-"))
        return _d(y, m, day)

    days = sorted(set(hist.get(team, {})) | set(fut.get(team, {})))
    prior = [d for d in days if d < game_date]
    if not prior:
        return None, None
    last = prior[-1]
    for g in hist.get(team, {}).get(last, []):
        if g.get("venue"):
            return g["venue"], "official schedule"
        if g.get("neutral"):
            return None, "neutral site - no distance measured"
        host = g.get("home")
        if host in venues_by_home_team:
            return venues_by_home_team[host], "DERIVED: the official schedule prints the venue of the home team's home games as that team's arena"
    for r in fut.get(team, {}).get(last, []):
        if r.get("venue"):
            return r["venue"], "official schedule"
        host = r.get("home")
        if host in venues_by_home_team:
            return venues_by_home_team[host], "DERIVED: the official schedule prints the venue of the home team's home games as that team's arena"
    return None, None


# --------------------------------------------------------------------- luck

def luck_table(teams, league, results, sigma_margin):
    """Per-team luck z-score.

    For every completed official game the model's current ratings give an
    expected margin; the actual margin minus that expectation is the team's
    residual, and the residual divided by the residual dispersion is the luck
    z-score.  A positive z-score means the team has been luckier than its
    rating says.

    The rating used is the CURRENT official rating, so the measure is a
    current-rating residual rather than a strictly point-in-time one; that
    limitation is published with the table.
    """
    rows = []
    for g in results:
        h, a = g.get("home"), g.get("away")
        if h not in teams or a not in teams:
            continue
        if g.get("home_pts") is None or g.get("away_pts") is None:
            continue
        th, ta = teams[h], teams[a]
        poss, _ = game_possessions(th, ta, league)
        ldef = league["league_ppp_def"] or 1.0
        ppp_h = th["ppp_off"] * (ta["ppp_def"] / ldef)
        ppp_a = ta["ppp_off"] * (th["ppp_def"] / ldef)
        exp_margin = ppp_h * poss - ppp_a * poss
        actual = g["home_pts"] - g["away_pts"]
        rows.append({"date": g.get("date"), "game_id": g.get("game_id"),
                     "home": h, "away": a, "expected_margin": exp_margin,
                     "actual_margin": actual, "residual": actual - exp_margin,
                     "source_url": g.get("source_url")})
    if not rows:
        return [], None
    sd = pstdev([r["residual"] for r in rows]) or 1.0
    per = {}
    for r in rows:
        for t, sign in ((r["home"], 1.0), (r["away"], -1.0)):
            d = per.setdefault(t, {"team": t, "residual_sum": 0.0, "games": 0,
                                    "expected_sum": 0.0, "actual_sum": 0.0})
            d["residual_sum"] += sign * r["residual"]
            d["games"] += 1
            d["expected_sum"] += sign * r["expected_margin"]
            d["actual_sum"] += sign * (r["actual_margin"] if sign > 0 else -r["actual_margin"])
    out = []
    for t, d in sorted(per.items()):
        z = d["residual_sum"] / (sd * math.sqrt(d["games"]))
        out.append({
            "team": t,
            "games": d["games"],
            "expected_points_total": round(d["expected_sum"], 1),
            "actual_points_total": round(d["actual_sum"], 1),
            "luck_points": round(d["residual_sum"], 1),
            "luck_z": round(z, 2),
            "in_noise_band": abs(z) <= ASSUMPTIONS["luck_noise_band_z"]["value"],
            "source": "official final scores; expected margin from the official "
                      "team-stat tables",
        })
    out.sort(key=lambda r: -abs(r["luck_z"]))
    return out, sd


def refuse_outside_noise_band(strategies, luck):
    """A strategy that leans on a team outside the luck noise band is refused."""
    band = ASSUMPTIONS["luck_noise_band_z"]["value"]
    zmap = {r["team"]: r for r in luck}
    verdicts = []
    for s in strategies:
        teams = set(s.get("teams", []))
        outside = {t: zmap[t]["luck_z"] for t in teams if t in zmap and not zmap[t]["in_noise_band"]}
        verdicts.append({
            "strategy": s.get("id") or s.get("name"),
            "teams": sorted(teams),
            "teams_outside_noise_band": outside,
            "verdict": "REFUSED - leans on team(s) outside the +/-%.1f luck band" % band
                       if outside else "allowed",
            "band_z": band,
        })
    return verdicts


# --------------------------------------------------------------- market prior

def market_blend(p_model, market_prob, oos_log_loss_model, oos_log_loss_market):
    """Blend a model probability with a market probability, weighted by the
    measured out-of-sample log loss of each.

    w_market = (LL_model - LL_market) / (LL_model + LL_market)  clipped to
    [0, 1]; a market that is no better than the model gets zero weight.

    When no official closing line exists the market leg is unavailable, its
    weight is 0 and the blend is the model probability.  That is recorded, not
    hidden.
    """
    if market_prob is None or oos_log_loss_market is None:
        return {"p_model": p_model, "p_market": None, "p_blend": p_model,
                "w_model": 1.0, "w_market": 0.0,
                "market_leg": "UNAVAILABLE - no official closing line is reachable "
                              "from this sandbox, so the market leg carries zero "
                              "weight",
                "oos_log_loss_model": oos_log_loss_model}
    denom = (oos_log_loss_model + oos_log_loss_market) or 1.0
    w_market = max(0.0, min(1.0, (oos_log_loss_model - oos_log_loss_market) / denom))
    w_model = 1.0 - w_market
    return {"p_model": p_model, "p_market": market_prob,
            "p_blend": w_model * p_model + w_market * market_prob,
            "w_model": round(w_model, 4), "w_market": round(w_market, 4),
            "market_leg": "available",
            "oos_log_loss_model": oos_log_loss_model,
            "oos_log_loss_market": oos_log_loss_market}


def model_out_of_sample_log_loss(teams, league, results, hca_points):
    """Measured out-of-sample log loss of the model's home-win probability."""
    probs, outcomes = [], []
    for g in results:
        h, a = g.get("home"), g.get("away")
        if h not in teams or a not in teams:
            continue
        if g.get("home_pts") is None or g.get("away_pts") is None:
            continue
        if g.get("neutral"):
            continue
        est = estimator_a(teams[h], teams[a], league, hca_points)
        p = norm_cdf(est["margin"] / 12.0)
        probs.append(p)
        outcomes.append(1 if g["home_pts"] > g["away_pts"] else 0)
    return log_loss(probs, outcomes), len(probs)


# ------------------------------------------------------------------ parlay rho

def measured_rho(results):
    """Correlations MEASURED on the official finals corpus.

    rho(home points, away points) is the correlation that matters for a
    two-team total parlay; rho(margin, total) is the one that matters for a
    side + total same-game parlay.
    """
    hp, ap, mg, tt = [], [], [], []
    for g in results:
        if g.get("home_pts") is None or g.get("away_pts") is None:
            continue
        hp.append(g["home_pts"])
        ap.append(g["away_pts"])
        mg.append(g["home_pts"] - g["away_pts"])
        tt.append(g["home_pts"] + g["away_pts"])
    out = []
    for name, xs, ys, why in (
            ("home points / away points", hp, ap,
             "the correlation between the two teams' scores in the same game - "
             "the rho a both-teams-over parlay has to be priced with"),
            ("margin / total", mg, tt,
             "the correlation between the margin and the total - the rho a side "
             "plus total same-game parlay has to be priced with"),
            ("home points / total", hp, tt,
             "the correlation between a team's own score and the game total")):
        r, p, n = pearson(xs, ys)
        out.append({"pair": name, "rho_measured": round(r, 4) if r is not None else None,
                    "p_value": round(p, 5) if p is not None else None, "n": n,
                    "why": why,
                    "status": "MEASURED on official final scores "
                              "(data/official/gamelog.json)"})
    return out


def price_parlay(p_leg1, p_leg2, rho):
    """Price a two-leg parlay with the measured rho and print the naive
    independent product beside it."""
    joint_naive = p_leg1 * p_leg2
    if rho is None:
        joint = joint_naive
    else:
        z1, z2 = norm_ppf(p_leg1), norm_ppf(p_leg2)
        joint = bivariate_normal_cdf(z1, z2, rho)
    return {
        "p_leg1": p_leg1, "p_leg2": p_leg2, "rho_used": rho,
        "p_joint_with_rho": round(joint, 5),
        "p_naive_independent_product": round(joint_naive, 5),
        "difference": round(joint - joint_naive, 5),
        "bettor_edge_pct": round(100.0 * (joint / joint_naive - 1.0), 2) if joint_naive else None,
        "pricing_note": "the joint probability is computed from the bivariate "
                        "normal with the measured rho; the naive independent "
                        "product is printed beside it so the correlation cost is "
                        "visible",
    }


def american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))
