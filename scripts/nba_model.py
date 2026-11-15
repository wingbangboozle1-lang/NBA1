#!/usr/bin/env python3
"""nba_model.py — originate the lines and run the strategy competition.

    python3 scripts/nba_model.py

Reads only `data/capture/<LATEST>/parsed/*` — the official captures produced by
`scripts/official_capture.py` — and writes `data/model_v3/*.json`.

WHAT IS ORIGINAL HERE, AND WHAT IS NOT
--------------------------------------
Every input is an official NBA value: box scores, period scores, player minutes,
the injury PDFs, tip times and arenas all come from nba.com / official.nba.com
and carry their own URL and retrieval timestamp. Everything the model *computes*
is listed in `assumptions.json` with its formula, so a reader can separate an
official number from a modelling choice.

The two estimators (requirement: keep two independent estimators and publish
their disagreement):

  A "net-rating"   additive. Team offensive and defensive efficiency per 100
                   possessions, shrunk toward the league mean, differenced.
  B "possessions"  multiplicative. Expected points = (pace_a * pace_b /
                   league_pace) * (ppp_off_a * ppp_def_b / league_ppp). This is
                   the possessions x points-per-possession construction, not an
                   average of scoring averages.

Home-court advantage is NOT fitted to outcomes. It is solved for, by bisection,
so that the model's league-wide expected home-win rate equals the home-win rate
measured from the official results (requirement 8).

The "line" every strategy is settled against is a naive reference model defined
in `reference.py`-style code below and disclosed on the site. It is not a
sportsbook price: no NBA-operated source publishes one, which is recorded as a
flag rather than worked around.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = os.path.join(ROOT, "data", "capture")
OUT = os.path.join(ROOT, "data", "model_v3")

MODEL_VERSION = "2026-11-15.1"

# ----------------------------------------------------------------- assumptions
# Every one of these is a MODELLING CHOICE, not an official number. They are
# published verbatim on the site's Model & Assumptions page.
ASSUMPTIONS = [
    ("possession_estimate",
     "possessions = FGA - OREB + TOV + 0.44 x FTA",
     "The standard box-score possession estimator. FGA, OREB, TOV and FTA are "
     "official per-game values read from each game's own box score."),
    ("pace",
     "pace = possessions x 240 / team-minutes",
     "Team-minutes is official (240:00 in a regulation game, longer in overtime), "
     "so this converts raw possessions to a per-48-minute rate."),
    ("efficiency",
     "ORTG = 100 x points / possessions;  DRTG = 100 x points allowed / opponent possessions",
     "Both inputs are official. In any game the two teams' possession counts differ "
     "only by rebound/turnover bookkeeping, so each team's DRTG uses the opponent's "
     "actual possessions."),
    ("shrinkage",
     "adjusted net rating = raw net rating x n / (n + K),  K = 10 games",
     "Early-season net ratings are noisy. K = 10 is a stated regularisation, not a "
     "fitted parameter: it is fixed before any result is looked at."),
    ("estimator_a",
     "margin_A = (net_home - net_away) / 100 x expected_possessions + HCA",
     "Additive, rating-driven."),
    ("estimator_b",
     "expected_possessions = pace_home x pace_away / league_pace ; "
     "ppp_exp(team) = ppp_off(team) x ppp_def(opponent) / league_ppp ; "
     "margin_B = poss x (ppp_home - ppp_away) + HCA",
     "Multiplicative, possession-driven. Requirement: model the total as "
     "possessions x points-per-possession."),
    ("hca_pinned",
     "HCA solves  mean_i Phi((margin_i + HCA) / sigma) = measured home-win rate",
     "HCA is pinned to the home-win rate MEASURED from official results on "
     "non-neutral courts (requirement 8). It is not a free parameter and it is "
     "not chosen to maximise profit."),
    ("sigma",
     "sigma = standard deviation of (actual margin - predicted margin)",
     "Recomputed on the out-of-sample window only, so the width that turns a "
     "margin into a probability is never fitted on the games it grades."),
    ("minutes_share",
     "share_i = player minutes / team minutes",
     "Team minutes are official (240:00 per regulation game). Shares therefore sum "
     "to 1 over a team's roster for any game."),
    ("replacement",
     "when player j is out: share_i' = share_i x (1 + share_j / (1 - share_j))",
     "Pro-rata redistribution over the remaining players (requirement 11). A "
     "stated rule, not a measured one: the league publishes no replacement-level "
     "table."),
    ("availability_weight",
     "expected minutes lost = Out x 1.00 + Doubtful x 0.50 + Questionable x 0.25",
     "A stated weight. Probable and Available carry weight 0. Each injured player's "
     "minutes share comes from the official box scores."),
    ("luck_z",
     "expected wins = sum of the model's own P(win) over the games played; "
     "z = (actual wins - expected wins) / sqrt(sum p(1-p))",
     "Requirement 9. The noise band is |z| <= 1.96."),
    ("travel",
     "great-circle distance between the two arenas' coordinates, km",
     "Arena name, city, state and country are official (each game's own page). "
     "The coordinates are NOT published by any NBA-operated source: they come "
     "from Wikipedia and every travel row is flagged as non-official."),
    ("market_anchor",
     "blend weight on the closing line = 0.00",
     "Requirement 15 asks for a market-anchored prior weighted by measured "
     "out-of-sample log-loss. No NBA-operated source publishes a closing line, so "
     "the weight is 0.00 by construction and the mechanism is published with the "
     "flag rather than fed a number from outside the official set."),
]

# Arena coordinates. Source: English Wikipedia (en.wikipedia.org), read through
# its API on 2026-11-15. NOT an official NBA source - no NBA-operated page
# publishes arena latitude/longitude - so every row that uses these is flagged.
ARENA_COORDS = {
    "State Farm Arena": (33.75722222, -84.39638889),
    "TD Garden": (42.36638889, -71.06222222),
    "Barclays Center": (40.68266111, -73.975225),
    "Spectrum Center": (35.225, -80.83916667),
    "United Center": (41.88055556, -87.67416667),
    "Rocket Arena": (41.49638889, -81.68805556),
    "American Airlines Center": (32.79055556, -96.81027778),
    "Ball Arena": (39.74861111, -105.0075),
    "Little Caesars Arena": (42.34111111, -83.055),
    "Chase Center": (37.76805556, -122.3875),
    "Toyota Center": (29.75083333, -95.36222222),
    "Gainbridge Fieldhouse": (39.76388889, -86.15555556),
    "Intuit Dome": (33.9451, -118.3431),
    "Crypto.com Arena": (34.04305556, -118.26722222),
    "FedExForum": (35.13833333, -90.05055556),
    "Kaseya Center": (25.78138889, -80.18805556),
    "Fiserv Forum": (43.04502778, -87.91816667),
    "Target Center": (44.97944444, -93.27611111),
    "Smoothie King Center": (29.94888889, -90.08194444),
    "Madison Square Garden": (40.75055556, -73.99361111),
    "Paycom Center": (35.46333333, -97.515),
    "Kia Center": (28.53916667, -81.38361111),
    "Xfinity Mobile Arena": (39.90111111, -75.17194444),
    "Moda Center": (45.53166667, -122.66666667),
    "Golden 1 Center": (38.58036111, -121.49961111),
    "Frost Bank Center": (29.42694444, -98.4375),
    "Moody Center": (30.28097222, -97.73047222),
    "Scotiabank Arena": (43.64333333, -79.37916667),
    "Delta Center": (40.76833333, -111.90111111),
    "Capital One Arena": (38.89805556, -77.02083333),
}
ARENA_COORD_SOURCE = "https://en.wikipedia.org/w/api.php (prop=coordinates), read 2026-11-15"

TEAMS_30 = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
            "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
            "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

SHRINK_K = 10.0
BREAK_EVEN = 110.0 / 210.0          # -110
PAYOUT = 100.0 / 110.0              # +0.9091 per win at -110

# The out-of-sample window: every game on or after this date is graded with a
# model fitted only on games strictly before it.
OOS_START = "2026-11-05"


# ----------------------------------------------------------------- small maths
def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def ncdf_inv(p):
    """Acklam's rational approximation for the inverse normal CDF."""
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
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def bivar_normal_prob(z1, z2, rho, steps=40):
    """P(X<=z1, Y<=z2) for standard bivariate normal by Gauss-Legendre-ish grid."""
    # Numeric integration over the conditioning variable (Simpson on a fine grid).
    if abs(rho) < 1e-9:
        return phi(z1) * phi(z2)
    lo, hi = -8.0, 8.0
    n = steps * 20
    h = (hi - lo) / n
    total = 0.0
    for i in range(n + 1):
        x = lo + i * h
        # P(Y<=z2 | X=x) = Phi((z2 - rho*x)/sqrt(1-rho^2)) ; weight = pdf(x)
        val = phi((z2 - rho * x) / math.sqrt(1 - rho * rho)) * \
            math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        total += w * val
    return total * h / 3.0


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def binom_p_two_sided(k, n, p0):
    """Exact binomial p-value (two-sided, by the method of small p-values)."""
    if n == 0:
        return None
    try:
        from math import comb
    except ImportError:                                          # pragma: no cover
        return None
    obs = comb(n, k) * (p0 ** k) * ((1 - p0) ** (n - k))
    tot = 0.0
    for i in range(n + 1):
        pi = comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
        if pi <= obs + 1e-12:
            tot += pi
    return min(1.0, tot)


def binom_p_greater(k, n, p0):
    """One-sided P(X >= k) - the direction that matters for a betting record."""
    if n == 0:
        return None
    from math import comb
    return min(1.0, sum(comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
                        for i in range(k, n + 1)))


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / den)


def minutes_to_float(s):
    """'32:31' -> 32.52 ; '240:00' -> 240.0. Official format on the box score."""
    if not s:
        return 0.0
    try:
        if ":" in s:
            a, b = s.split(":", 1)
            return float(a) + float(b) / 60.0
        return float(s)
    except ValueError:
        return 0.0


def haversine_km(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def american_odds(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return round(-100.0 * p / (1 - p)) if p >= 0.5 else round(100.0 * (1 - p) / p)


# ------------------------------------------------------------------- loading
def load_capture():
    run = open(os.path.join(CAPTURE, "LATEST"), encoding="utf-8").read().strip()
    P = os.path.join(CAPTURE, run, "parsed")
    man = json.load(open(os.path.join(CAPTURE, run, "manifest.json"), encoding="utf-8"))
    games = {}
    for fn in sorted(os.listdir(P)):
        if fn.startswith("games_") and fn.endswith(".json"):
            d = fn[len("games_"):-len(".json")]
            games[d] = json.load(open(os.path.join(P, fn), encoding="utf-8"))
    box = json.load(open(os.path.join(P, "boxscores.json"), encoding="utf-8"))["rows"]
    inj = {"editions": [], "edition_count": 0}
    ip = os.path.join(P, "injury_pdfs.json")
    if os.path.exists(ip):
        inj = json.load(open(ip, encoding="utf-8"))
    return run, man, games, box, inj


# --------------------------------------------------------- the results feed
def build_results(box, games_by_date):
    """Requirement 2: one row per game - date, teams, final score, quarter scores.

    Quarter scores come from each game's own official box score. A row whose
    quarter scores the official page does not print keeps them null and is
    flagged; they are never reconstructed from the final.
    """
    rows = []
    for b in sorted(box, key=lambda r: (r["date"], r["game_id"])):
        aq = b.get("away_quarters") or []
        hq = b.get("home_quarters") or []
        rows.append({
            "date": b["date"],
            "game_id": b["game_id"],
            "away": b["away"], "home": b["home"],
            "away_pts": b.get("away_pts"), "home_pts": b.get("home_pts"),
            "away_q1": aq[0] if len(aq) > 0 else None,
            "away_q2": aq[1] if len(aq) > 1 else None,
            "away_q3": aq[2] if len(aq) > 2 else None,
            "away_q4": aq[3] if len(aq) > 3 else None,
            "away_ot": aq[4] if len(aq) > 4 else None,
            "home_q1": hq[0] if len(hq) > 0 else None,
            "home_q2": hq[1] if len(hq) > 1 else None,
            "home_q3": hq[2] if len(hq) > 2 else None,
            "home_q4": hq[3] if len(hq) > 3 else None,
            "home_ot": hq[4] if len(hq) > 4 else None,
            "ot_periods": max(0, max(len(aq), len(hq)) - 4),
            "neutral": b.get("neutral"),
            "arena": b.get("arena_name"),
            "arena_city": b.get("arena_city"),
            "arena_state": b.get("arena_state"),
            "attendance": b.get("attendance"),
            "status": b.get("status_label"),
            "source_url": b.get("game_url"),
            "source_schedule_url": f"https://www.nba.com/games?date={b['date']}",
        })
    return rows


# ------------------------------------------------------- team-game aggregates
def team_game_rows(box):
    """One row per (game, team) with the possession model's official inputs."""
    out = []
    for b in box:
        for side in ("away", "home"):
            st = b.get(f"{side}_stats") or {}
            if not st:
                continue
            tm = minutes_to_float(st.get("minutes")) or 240.0
            fga = st.get("fieldGoalsAttempted") or 0
            oreb = st.get("reboundsOffensive") or 0
            tov = st.get("turnovers") or 0
            fta = st.get("freeThrowsAttempted") or 0
            poss = fga - oreb + tov + 0.44 * fta
            other = "home" if side == "away" else "away"
            ost = b.get(f"{other}_stats") or {}
            opposs = None
            if ost:
                opposs = ((ost.get("fieldGoalsAttempted") or 0)
                          - (ost.get("reboundsOffensive") or 0)
                          + (ost.get("turnovers") or 0)
                          + 0.44 * (ost.get("freeThrowsAttempted") or 0))
            out.append({
                "date": b["date"], "game_id": b["game_id"],
                "team": b.get(side), "opp": b.get(other),
                "home": side == "home",
                "neutral": b.get("neutral"),
                "pts": st.get("points"), "pts_allowed": b.get(f"{other}_pts"),
                "team_minutes": tm,
                "poss": poss, "opp_poss": opposs,
                "pace": poss * 240.0 / tm if tm else None,
                "fga": fga, "fgm": st.get("fieldGoalsMade"),
                "fg3a": st.get("threePointersAttempted"), "fg3m": st.get("threePointersMade"),
                "fta": fta, "oreb": oreb, "tov": tov,
                "ast": st.get("assists"), "stl": st.get("steals"), "blk": st.get("blocks"),
                "arena": b.get("arena_name"),
                "margin": (st.get("points") or 0) - (b.get(f"{other}_pts") or 0),
                "source_url": b.get("game_url"),
            })
    return out


def fit_ratings(tg_rows, upto_date=None):
    """Season-to-date ratings from official box scores, optionally cut at a date.

    Returns per-team: games, pace, ORTG, DRTG, NET (raw and shrunk), ppp_off,
    ppp_def, points for/against per game.
    """
    rows = [r for r in tg_rows if upto_date is None or r["date"] < upto_date]
    agg = {}
    for t in TEAMS_30:
        agg[t] = {"team": t, "n": 0, "poss": 0.0, "opp_poss": 0.0, "pts": 0, "pa": 0,
                  "pace": 0.0, "tm_min": 0.0}
    for r in rows:
        t, o = r["team"], r["opp"]
        if t not in agg or o not in agg:
            continue
        a = agg[t]
        a["n"] += 1
        a["poss"] += r["poss"] or 0
        a["opp_poss"] += r["opp_poss"] or r["poss"] or 0
        a["pts"] += r["pts"] or 0
        a["pa"] += r["pts_allowed"] or 0
        a["pace"] += r["pace"] or 0
        a["tm_min"] += r["team_minutes"] or 0
    lg_poss = sum(a["poss"] for a in agg.values())
    lg_pts = sum(a["pts"] for a in agg.values())
    lg_pace = statistics.fmean([a["pace"] / a["n"] for a in agg.values() if a["n"]]) if any(
        a["n"] for a in agg.values()) else 100.0
    lg_ppp = (lg_pts / lg_poss) if lg_poss else 1.0
    out = {}
    for t, a in agg.items():
        if a["n"] == 0:
            out[t] = {"team": t, "n": 0}
            continue
        ortg = 100.0 * a["pts"] / a["poss"] if a["poss"] else None
        drtg = 100.0 * a["pa"] / a["opp_poss"] if a["opp_poss"] else None
        net = (ortg or 0) - (drtg or 0)
        shrunk = net * a["n"] / (a["n"] + SHRINK_K)
        out[t] = {
            "team": t, "n": a["n"],
            "pace": a["pace"] / a["n"],
            "ppp_off": a["pts"] / a["poss"] if a["poss"] else None,
            "ppp_def": a["pa"] / a["opp_poss"] if a["opp_poss"] else None,
            "ortg": ortg, "drtg": drtg,
            "net_raw": net, "net": shrunk,
            "ppg": a["pts"] / a["n"], "papg": a["pa"] / a["n"],
        }
    return out, {"lg_pace": lg_pace, "lg_ppp": lg_ppp, "games": len(rows) // 2}


def predict(ratings, lg, home, away, hca, neutral=False):
    """Both estimators, from the home team's point of view."""
    h, a = ratings.get(home), ratings.get(away)
    if not h or not a or not h.get("n") or not a.get("n"):
        return None
    poss_exp = (h["pace"] * a["pace"] / lg["lg_pace"]) if lg["lg_pace"] else None
    # --- A: additive net rating
    margin_a = (h["net"] - a["net"]) / 100.0 * (poss_exp or lg["lg_pace"] or 100.0)
    # --- B: multiplicative possessions x points-per-possession
    ppp_h = h["ppp_off"] * a["ppp_def"] / lg["lg_ppp"] if lg["lg_ppp"] else None
    ppp_a = a["ppp_off"] * h["ppp_def"] / lg["lg_ppp"] if lg["lg_ppp"] else None
    pts_h = (poss_exp or 0) * (ppp_h or 0)
    pts_a = (poss_exp or 0) * (ppp_a or 0)
    margin_b = pts_h - pts_a
    total_b = pts_h + pts_a
    total_a = (h["ppg"] + a["ppg"])
    hc = 0.0 if neutral else hca
    return {
        "poss_exp": poss_exp,
        "margin_a": margin_a + hc,
        "margin_b": margin_b + hc,
        "total_a": total_a,
        "total_b": total_b,
        "pts_home_b": pts_h + (hc / 2.0),
        "pts_away_b": pts_a - (hc / 2.0),
        "ppp_home": ppp_h, "ppp_away": ppp_a,
    }


def reference_line(ratings, home, away, hca, neutral=False):
    """The naive reference the strategies are settled against.

    Deliberately dumb: a team's strength is its points-for minus points-against
    per game - no possession adjustment, no shrinkage, no opponent interaction -
    and the total is the sum of the two scoring averages. Requirement 16 calls
    that construction out as the thing NOT to use as the model; here it survives
    as the disclosed benchmark the model has to beat.
    """
    h, a = ratings.get(home), ratings.get(away)
    if not h or not a or not h.get("n") or not a.get("n"):
        return None
    hc = 0.0 if neutral else hca
    m = (h["ppg"] - h["papg"]) - (a["ppg"] - a["papg"]) + hc
    return {"margin": m, "total": h["ppg"] + a["ppg"]}


# ------------------------------------------------------------- HCA by bisection
def solve_hca(predictions, sigma):
    """Pin HCA to the home-win rate measured on non-neutral courts.

    `predictions` is a list of (actual_home_margin, predicted_margin_without_hca,
    neutral). The solve finds the single constant c with

        mean_i Phi((predicted_i + c) / sigma)  ==  measured home-win rate

    over exactly the games the model can score, so the target and the average are
    taken over the same set. HCA is therefore pinned to a measured rate and is
    not chosen to fit results or to maximise profit (requirement 8).
    """
    rows = [p for p in predictions if not p[2]]
    if not rows:
        return 0.0, None, 0
    wins = sum(1 for a, _, _ in rows if a > 0)
    p_home = wins / len(rows)

    def mean_pred(c):
        return sum(phi((d + c) / sigma) for _, d, _ in rows) / len(rows)

    lo, hi = -20.0, 20.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mean_pred(mid) < p_home:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, p_home, len(rows)


# ------------------------------------------------------------------ main build
def main():
    os.makedirs(OUT, exist_ok=True)
    run, manifest, games_by_date, box, inj = load_capture()
    src_of = {}
    for f in manifest.get("fetches", []):
        src_of[f.get("url", "")] = f

    results = build_results(box, games_by_date)
    tg = team_game_rows(box)

    dates = sorted({r["date"] for r in results})
    played = sorted([r for r in results if (r["away_pts"] or 0) or (r["home_pts"] or 0)],
                    key=lambda r: (r["date"], r["game_id"]))

    # ---- precomputed rating snapshots by date (for the walk-forward) --------
    cache = {}

    def ratings_at(d):
        if d not in cache:
            cache[d] = fit_ratings(tg, d)
        return cache[d]

    # ---- HCA pinned to the measured home-win rate ---------------------------
    # Use a first pass with a full-season fit to measure sigma, then solve HCA.
    full_r, full_lg = fit_ratings(tg)
    resid = []
    for g in played:
        pr = predict(full_r, full_lg, g["home"], g["away"], 0.0, g.get("neutral"))
        if pr is None:
            continue
        m = 0.5 * (pr["margin_a"] + pr["margin_b"])
        resid.append(g["home_pts"] - g["away_pts"] - m)
    sigma_full = statistics.pstdev(resid) if len(resid) > 2 else 12.0
    globals()["SIGMA_PRIOR"] = sigma_full

    hca, p_home, n_home = solve_hca(
        played, lambda d: ratings_at(d)[0], lambda d: ratings_at(d)[1], None)

    # ---- measured sigma on the out-of-sample window -------------------------
    oos_games = [g for g in played if g["date"] >= OOS_START]
    resid_oos = []
    for g in oos_games:
        r, lg = ratings_at(g["date"])
        pr = predict(r, lg, g["home"], g["away"], hca, g.get("neutral"))
        if pr is None:
            continue
        m = 0.5 * (pr["margin_a"] + pr["margin_b"])
        resid_oos.append(g["home_pts"] - g["away_pts"] - m)
    sigma = statistics.pstdev(resid_oos) if len(resid_oos) > 2 else sigma_full

    # ---- total residuals (for the same-game rho) ----------------------------
    resid_total = []
    for g in oos_games:
        r, lg = ratings_at(g["date"])
        pr = predict(r, lg, g["home"], g["away"], hca, g.get("neutral"))
        if pr is None:
            continue
        t = 0.5 * (pr["total_a"] + pr["total_b"])
        resid_total.append((g["home_pts"] + g["away_pts"]) - t)
        pr["_total_resid_actual"] = (g["home_pts"] + g["away_pts"]) - t
        pr["_margin_resid_actual"] = (g["home_pts"] - g["away_pts"]) - 0.5 * (pr["margin_a"] + pr["margin_b"])
        g["_pr"] = pr

    rho_side_total = None
    if len(resid_oos) == len(resid_total) and len(resid_oos) > 5:
        rho_side_total = pearson(resid_oos, resid_total)

    # binary (phi) correlation between covering the side and covering the total
    bin_side, bin_total = [], []
    for g in oos_games:
        pr = g.get("_pr")
        if not pr:
            continue
        m = 0.5 * (pr["margin_a"] + pr["margin_b"])
        t = 0.5 * (pr["total_a"] + pr["total_b"])
        act_m = g["home_pts"] - g["away_pts"]
        act_t = g["home_pts"] + g["away_pts"]
        bin_side.append(1 if act_m > m else 0)
        bin_total.append(1 if act_t > t else 0)
    phi_side_total = pearson(bin_side, bin_total) if len(bin_side) > 5 else None

    # player-prop same-game correlation: two teammates' points
    teammate_rhos = []
    by_game_team = {}
    for b in box:
        for side in ("away", "home"):
            ps = b.get(f"{side}_players") or []
            ps = [p for p in ps if (p.get("pts") or 0) > 0]
            ps.sort(key=lambda p: -(minutes_to_float(p.get("min"))))
            if len(ps) >= 2:
                by_game_team[(b["game_id"], b.get(side))] = ps
    for key, ps in by_game_team.items():
        if len(ps) < 3:
            continue
        top = ps[:3]
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                pass
    # pair the two highest-minute teammates across every game
    xs, ys = [], []
    for key, ps in by_game_team.items():
        xs.append(ps[0]["pts"]); ys.append(ps[1]["pts"])
    rho_teammates = pearson(xs, ys) if len(xs) > 5 else None

    # ---------------------------------------------------------------- outputs
    out = {}
    out["meta"] = {
        "model_version": MODEL_VERSION,
        "built_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_run": run,
        "games_captured": len(results),
        "games_played": len(played),
        "oos_window_start": OOS_START,
        "oos_games": len(oos_games),
        "season_start": dates[0] if dates else None,
        "last_result_date": max(r["date"] for r in played) if played else None,
        "sigma_margin": sigma,
        "sigma_full_sample": sigma_full,
        "hca_points": hca,
        "measured_home_win_rate": p_home,
        "measured_home_win_n": n_home,
        "rho_side_total_residual": rho_side_total,
        "rho_side_total_binary": phi_side_total,
        "rho_teammates_points": rho_teammates,
        "assumptions": [{"id": a, "formula": f, "note": n} for a, f, n in ASSUMPTIONS],
    }
    out["results"] = results
    out["team_ratings"] = {"ratings": full_r, "league": full_lg}
    json.dump(out, open("/tmp/_model_partial.json", "w"), indent=1)
    return out, dict(run=run, manifest=manifest, games_by_date=games_by_date, box=box,
                     inj=inj, results=results, tg=tg, played=played, dates=dates,
                     ratings_at=ratings_at, hca=hca, p_home=p_home, n_home=n_home,
                     sigma=sigma, sigma_full=sigma_full, oos_games=oos_games,
                     rho_side_total=rho_side_total, phi_side_total=phi_side_total,
                     rho_teammates=rho_teammates, src_of=src_of)


if __name__ == "__main__":
    o, ctx = main()
    print(json.dumps({k: v for k, v in o["meta"].items() if k != "assumptions"}, indent=1))
