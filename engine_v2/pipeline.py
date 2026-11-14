"""Walk-forward backtest, strategy library, validation gates, correlations and
the originated-line slate.  Writes site/data/*.json.

The skill question this answers
-------------------------------
We originate our own lines.  A bettor who uses exactly the same information as
the line-generating model cannot beat it, by construction.  Skill can therefore
only be measured as: *does this strategy's extra input move the probability
estimate in a direction that reality confirms?*

  baseline line  = ORIG-BASE, the model in model.py, which uses ONLY season
                   ratings and home court.  This is the "market" we originate.
  strategy       = ORIG-BASE + one extra official input the baseline ignores
                   (rest days, back-to-back, scoring environment).
  settlement     = every bet is struck at the baseline's fair price, 1/p_base.
  skill          = the strategy's realised hit rate beats p_base more often than
                   a no-skill bettor taking the same number of the same bets.

That last step is the luck removal: each strategy's ROI is compared with a
Monte-Carlo null of 5,000 no-skill bettors placing the identical bet list.
"""
from __future__ import annotations

import json
import math
import os
import random
from collections import Counter, defaultdict

from . import context as context_mod
from .content import FLAGGED, QUESTIONS, SOURCES, SUGGESTIONS
from .common import (NAMES, OFFICIAL, ROOT, TEAMS, _student_t_cdf, brier, d, load,
                     mean, norm_cdf, pearson, sd)
from .model import Ratings

SITE_DATA = os.path.join(ROOT, "data", "derived")
SEED = 20261114
NULL_REPS = 5000
MIN_BETS = 25          # gate G1
# The trigger is the smallest probability edge a strategy must show before it bets.
# It is NOT tuned: the whole grid is run, every cell is published, and the multiple-
# comparisons gate (G7) is applied across every cell in the grid.
EDGE_TRIGGERS = [0.02, 0.03, 0.04]
ALPHA = 0.05

# ---------------------------------------------------------------------------
# data assembly
# ---------------------------------------------------------------------------

def build_universe():
    gl = load("gamelog.json")
    games = gl["games"]
    fixtures = gl["known_unplayed_by_source"]["fixtures"]
    inprog = load("slate_2026_11_13_inprogress.json")["matchups"]
    slate = load("slate.json")["rows"]

    # every date on which a team is known (from an official page) to have played
    played = defaultdict(list)          # team -> [dates]
    for g in games:
        played[g["away"]].append(g["date"])
        played[g["home"]].append(g["date"])
    for f in fixtures:
        played[f["away"]].append(f["date"])
        played[f["home"]].append(f["date"])
    for m in inprog:
        played[m["away"]].append("2026-11-13")
        played[m["home"]].append("2026-11-13")
    for t in played:
        played[t].sort()
    return games, fixtures, inprog, slate, played


def rest_days(played, team, date_str):
    """Whole days between the team's previous game and this one. 1 = back-to-back."""
    prior = [x for x in played.get(team, []) if x < date_str]
    if not prior:
        return None
    return (d(date_str) - d(prior[-1])).days


def b2b(played, team, date_str):
    return rest_days(played, team, date_str) == 1


def _minus4(date_str):
    return (d(date_str) - __import__("datetime").timedelta(days=4)).isoformat()


# ---------------------------------------------------------------------------
# walk-forward
# ---------------------------------------------------------------------------

def walk_forward(games, played, sigma_m, sigma_t, start_after_dates=5,
                 k_margin=None, k_total=None):
    """Fit on everything strictly before each date; predict that date's games.

    Returns one record per game with baseline and signal inputs.
    """
    dates = sorted({g["date"] for g in games})
    out = []
    for i, dt in enumerate(dates):
        if i < start_after_dates:
            continue
        train = [g for g in games if g["date"] < dt]
        test = [g for g in games if g["date"] == dt]
        if len(train) < 40:
            continue
        R = (Ratings(train) if k_margin is None
             else Ratings(train, k_margin=k_margin, k_total=k_total))
        for g in test:
            p = R.predict(g["home"], g["away"], g.get("neutral", 0))
            if p["home_gp"] < 3 or p["away_gp"] < 3:
                continue
            r_h = rest_days(played, g["home"], dt)
            r_a = rest_days(played, g["away"], dt)
            dens_h = sum(1 for x in played[g["home"]] if dt > x >= _minus4(dt))
            dens_a = sum(1 for x in played[g["away"]] if dt > x >= _minus4(dt))
            rec = {
                "date": dt, "game_id": g["game_id"], "home": g["home"], "away": g["away"],
                "neutral": g.get("neutral", 0),
                "home_pts": g["home_pts"], "away_pts": g["away_pts"],
                "actual_margin_home": g["home_pts"] - g["away_pts"],
                "actual_total": g["home_pts"] + g["away_pts"],
                "pred_margin_home": p["pred_margin_home"],
                "pred_total": p["pred_total"],
                "rest_home": r_h, "rest_away": r_a,
                "density_home": dens_h, "density_away": dens_a,
                "b2b_home": 1 if r_h == 1 else 0,
                "b2b_away": 1 if r_a == 1 else 0,
                "train_games": len(train),
                "source_url": g["source_url"],
            }
            rec["p_home_win"] = norm_cdf(rec["pred_margin_home"] / sigma_m)
            rec["p_over"] = 0.5  # the originated total is our median: fair at even money
            rec["resid_margin"] = rec["actual_margin_home"] - rec["pred_margin_home"]
            rec["resid_total"] = rec["actual_total"] - rec["pred_total"]
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# strategies
# ---------------------------------------------------------------------------
# Each strategy returns a list of bets:
#   {date, game_id, market, side, p_base, p_strat, odds, win, profit, note}
# side is always described from the HOME team's point of view in `home_side`.

REST_PER_DAY = 0.55
DENSITY_POINTS = 0.90    # margin penalty per extra game played in the last four days
XGAME_MIN_SHIFT = 1.00   # minimum margin shift for a leg to enter the cross-game parlay     # points of margin per day of rest advantage
B2B_POINTS = 1.60       # margin penalty for the second night of a back-to-back
B2B_TOTAL = 1.70        # points removed from a total per team on a back-to-back


def _spread_bet(rec, delta, sigma_m, tag, trig):
    """Home covers the originated spread if actual margin > predicted margin.
    A strategy that shifts the expected margin by `delta` believes
    P(home covers) = Phi(delta / sigma_m)."""
    p_base, p_strat = 0.5, norm_cdf(delta / sigma_m)
    if p_strat - p_base < trig:
        return None
    home_covers = rec["actual_margin_home"] > rec["pred_margin_home"]
    win = 1 if home_covers else 0
    return _mk(rec, "Spread (home vs originated number)", "HOME", p_base, p_strat,
               win, f"margin shift {delta:+.2f} - {tag}")


def _total_bet(rec, delta, sigma_t, tag, trig):
    p_strat = norm_cdf(delta / sigma_t)
    if p_strat - 0.5 < trig:
        return None
    win = 1 if rec["actual_total"] > rec["pred_total"] else 0
    return _mk(rec, "Total (over originated number)", "OVER", 0.5, p_strat,
               win, f"total shift {delta:+.2f} - {tag}")


def _ml_bet(rec, p_strat_home, tag, trig):
    p_base = rec["p_home_win"]
    for side, ps, pb in (("HOME", p_strat_home, p_base),
                         ("AWAY", 1 - p_strat_home, 1 - p_base)):
        if ps - pb >= trig:
            win = 1 if ((rec["actual_margin_home"] > 0) == (side == "HOME")) else 0
            return _mk(rec, "Moneyline", side, pb, ps, win, tag)
    return None


def _mk(rec, market, side, p_base, p_strat, win, note):
    odds = 1.0 / p_base
    return {
        "date": rec["date"], "game_id": rec["game_id"], "home": rec["home"],
        "away": rec["away"], "market": market, "side": side,
        "p_base": p_base, "p_strat": p_strat, "odds": odds,
        "win": win, "profit": (odds - 1.0) if win else -1.0,
        "note": note, "source_url": rec["source_url"],
    }


def strategies(recs, sigma_m, sigma_t, trig):
    S = {}

    # ---- S1 rest differential, spread -------------------------------------
    def s1(rec):
        rh, ra = rec["rest_home"], rec["rest_away"]
        if rh is None or ra is None:
            return None
        delta = REST_PER_DAY * (rh - ra)
        if rec["b2b_home"] or rec["b2b_away"]:
            delta += B2B_POINTS * (rec["b2b_away"] - rec["b2b_home"])
        return _spread_bet(rec, delta, sigma_m, "rest / B2B differential", trig)

    # ---- S2 back-to-back fade, spread -------------------------------------
    def s2(rec):
        if not (rec["b2b_home"] or rec["b2b_away"]):
            return None
        delta = B2B_POINTS * (rec["b2b_away"] - rec["b2b_home"])
        return _spread_bet(rec, delta, sigma_m, "fade the team on the second night", trig)

    # ---- S3 rest, totals ---------------------------------------------------
    def s3(rec):
        delta = -B2B_TOTAL * (rec["b2b_home"] + rec["b2b_away"])
        if delta == 0:
            return None
        return _total_bet(rec, delta, sigma_t, "back-to-back scoring environment", trig)

    # ---- S4 rest advantage, moneyline --------------------------------------
    def s4(rec):
        rh, ra = rec["rest_home"], rec["rest_away"]
        if rh is None or ra is None:
            return None
        delta = REST_PER_DAY * (rh - ra) + B2B_POINTS * (rec["b2b_away"] - rec["b2b_home"])
        p = norm_cdf((rec["pred_margin_home"] + delta) / sigma_m)
        return _ml_bet(rec, p, "rest advantage, moneyline", trig)

    # ---- S5 rested underdog, moneyline -------------------------------------
    def s5(rec):
        rh, ra = rec["rest_home"], rec["rest_away"]
        if rh is None or ra is None:
            return None
        dog_home = rec["pred_margin_home"] < 0
        if dog_home and rh > ra and rec["b2b_away"]:
            delta = REST_PER_DAY * (rh - ra) + B2B_POINTS
        elif (not dog_home) and ra > rh and rec["b2b_home"]:
            delta = -(REST_PER_DAY * (ra - rh) + B2B_POINTS)
        else:
            return None
        p = norm_cdf((rec["pred_margin_home"] + delta) / sigma_m)
        return _ml_bet(rec, p, "rested underdog, moneyline", trig)

    # ---- S6 scoring environment, totals ------------------------------------
    def s6(rec):
        delta = 0.0
        rh, ra = rec["rest_home"], rec["rest_away"]
        if rh is not None and ra is not None:
            delta += 0.30 * ((3 - min(rh, 3)) + (3 - min(ra, 3)))
        return _total_bet(rec, delta, sigma_t, "short-rest scoring environment", trig)

    # ---- S7 same-game parlay, correlation priced ---------------------------
    def s7(rec, rho):
        rh, ra = rec["rest_home"], rec["rest_away"]
        if rh is None or ra is None:
            return None
        d_m = REST_PER_DAY * (rh - ra) + B2B_POINTS * (rec["b2b_away"] - rec["b2b_home"])
        d_t = -B2B_TOTAL * (rec["b2b_home"] + rec["b2b_away"])
        if abs(d_m) < 1.0 and abs(d_t) < 1.0:
            return None
        a = 1 if d_m >= 0 else -1           # home covers / away covers
        u = 1 if d_t >= 0 else -1           # over / under
        zh = d_m / sigma_m if a == 1 else -d_m / sigma_m
        zt = d_t / sigma_t if u == 1 else -d_t / sigma_t
        # bivariate normal with the MEASURED correlation of margin and total
        p1 = norm_cdf(zh)
        p2 = norm_cdf(zt)
        pj = bivariate_normal_cdf(zh, zt, rho)
        side = ("HOME + OVER" if a == 1 else "AWAY + OVER") if u == 1 else \
               ("HOME + UNDER" if a == 1 else "AWAY + UNDER")
        home_covers = rec["actual_margin_home"] > rec["pred_margin_home"]
        over = rec["actual_total"] > rec["pred_total"]
        leg1 = home_covers if a == 1 else not home_covers
        leg2 = over if u == 1 else not over
        p_base = 0.25                        # two independent even-money legs
        if pj - p_base < trig:
            return None
        return _mk(rec, "Same-game parlay (spread + total)", side, p_base, pj,
                   1 if (leg1 and leg2) else 0,
                   f"correlation-priced, rho={rho:+.3f}; legs {p1:.3f} x {p2:.3f}")

    S["S1"] = dict(name="Rest Edge (spread)", kind="Single bet", fn=s1,
                   signal="Rest days and back-to-back status from the official schedule.",
                   desc="Shifts the originated spread by 0.55 points per day of rest advantage plus 1.60 points against any team on the second night of a back-to-back. Bets the side when the shift is worth at least the trigger probability edge.")
    S["S2"] = dict(name="Back-to-Back Fade (spread)", kind="Single bet", fn=s2,
                   signal="Back-to-back flag derived from consecutive official schedule dates.",
                   desc="Fades the team playing the second game in two nights by 1.60 points against the originated spread. Bets only when a back-to-back is present.")
    S["S3"] = dict(name="Fatigue Unders (total)", kind="Single bet", fn=s3,
                   signal="Back-to-back flag derived from consecutive official schedule dates.",
                   desc="Removes 1.70 points from the originated total for each team on the second night of a back-to-back. Bets the under when the shift is worth at least the trigger probability edge.")
    S["S4"] = dict(name="Rest Advantage (moneyline)", kind="Single bet", fn=s4,
                   signal="Rest days and back-to-back status from the official schedule.",
                   desc="Re-prices the moneyline after the rest adjustment and bets when the new price is at least 4 percentage points better than the originated price.")
    S["S5"] = dict(name="Rested Underdog (moneyline)", kind="Single bet", fn=s5,
                   signal="Rest days, back-to-back flag and the originated spread.",
                   desc="Backs the underdog by the originated spread only when that underdog also holds a rest advantage and the favourite is on the second night of a back-to-back.")
    S["S6T"] = dict(name="Short-Rest Overs (total)", kind="Single bet", fn=s6,
                   signal="Rest days from the official schedule.",
                   desc="Adds 0.30 points to the originated total for each day of rest a team is short of three, capped at three days. Bets the over when that is worth at least the trigger.")
    # ---- S6b schedule density, spread -------------------------------------
    def s6b(rec):
        delta = DENSITY_POINTS * (rec["density_away"] - rec["density_home"])
        return _spread_bet(rec, delta, sigma_m, "four-day schedule density", trig)

    S["S6"] = dict(name="Schedule Density (spread)", kind="Single bet", fn=s6b,
                   signal="Games played in the previous four days, counted from consecutive official schedule dates.",
                   desc="Penalises a team by 0.90 points of spread for every extra game it has played in the previous four days relative to its opponent. A schedule-density signal the baseline rating ignores entirely.")
    S["S7"] = dict(name="Correlation SGP (spread + total)", kind="Same-game parlay",
                   fn=lambda r: s7(r, RHO), signal="Rest and back-to-back flags, priced with the measured margin/total correlation.",
                   desc="Combines the rest spread leg and the fatigue total leg in one same-game parlay. Pricing uses the bivariate normal with the correlation MEASURED on the out-of-sample window, not an assumed independence.")
    return S


def cross_game_parlay(recs, sigma_m, trig):
    """Two-game parlay: the two largest rest-signal spread edges on the same slate.
    Legs come from different games, so independence is the natural assumption -
    and it is the assumption the correlation page tests."""
    by_date = defaultdict(list)
    for r in recs:
        by_date[r["date"]].append(r)
    bets = []
    for dt, group in sorted(by_date.items()):
        cand = []
        for r in group:
            rh, ra = r["rest_home"], r["rest_away"]
            if rh is None or ra is None:
                continue
            d_m = (REST_PER_DAY * (rh - ra)
                   + B2B_POINTS * (r["b2b_away"] - r["b2b_home"]))
            if abs(d_m) < XGAME_MIN_SHIFT:
                continue
            cand.append((abs(d_m), d_m, r))
        cand.sort(key=lambda x: -x[0])
        if len(cand) < 2:
            continue
        legs = cand[:2]
        pj = 1.0
        win = 1
        desc, sides = [], []
        for _, d_m, r in legs:
            home_side = d_m > 0
            p = norm_cdf(abs(d_m) / sigma_m)
            pj *= p
            covers = r["actual_margin_home"] > r["pred_margin_home"]
            ok = covers if home_side else not covers
            win = win * (1 if ok else 0)
            sides.append(f"{r['away']}@{r['home']} {'HOME' if home_side else 'AWAY'}")
            desc.append(f"{abs(d_m):.2f}pt")
        p_base = 0.25
        if pj - p_base < trig:
            continue
        r0 = legs[0][2]
        bets.append({
            "date": dt, "game_id": "PARLAY-" + dt, "home": sides[0], "away": sides[1],
            "market": "Cross-game parlay (two spreads)", "side": " + ".join(sides),
            "p_base": p_base, "p_strat": pj, "odds": 1.0 / p_base,
            "win": win, "profit": (1.0 / p_base - 1.0) if win else -1.0,
            "note": "legs " + " / ".join(desc) + "; independence assumed across games",
            "source_url": "https://www.nba.com/games?date=" + dt,
        })
    return {"spec": dict(name="Cross-Game Parlay (two spreads)", kind="Cross-game parlay",
                         signal="Rest days and back-to-back status from the official schedule.",
                         desc="Takes the two largest rest-signal spread edges available on one slate and parlays them across two different games. Priced at independence; the correlation page tests whether that assumption holds."),
            "bets": bets, "trig": trig, "blocked": False, "block_reason": None}


def bivariate_normal_cdf(a, b, rho):
    """P(Z1 <= a, Z2 <= b) for standard bivariate normal, by Gauss-Legendre
    quadrature on the conditional.  rho is clipped for numerical safety."""
    if abs(rho) < 1e-9:
        return norm_cdf(a) * norm_cdf(b)
    rho = max(-0.999, min(0.999, rho))
    # 20-point Gauss-Legendre on [0,1] via the standard nodes (Newton-free table)
    xs = [0.9931285991850949, 0.9639719272779138, 0.9122344282513259, 0.8391169718222188,
          0.7463319064601508, 0.6360536807265150, 0.5108670019508271, 0.3737060887154195,
          0.2277858511416451, 0.0765265211334973]
    ws = [0.0176140071391521, 0.0406014298003869, 0.0626720483341091, 0.0832767415767048,
          0.1019301198172404, 0.1181945319615184, 0.1316886384491766, 0.1420961093183820,
          0.1491729864726037, 0.1527533871307259]
    s = 0.0
    for x, w in zip(xs, ws):
        s += w * (norm_cdf((b - rho * x) / math.sqrt(1 - rho * rho))
                  * math.exp(-x * x / 2.0))
    for x, w in zip([-v for v in xs], ws):
        s += w * (norm_cdf((b - rho * x) / math.sqrt(1 - rho * rho))
                  * math.exp(-x * x / 2.0))
    return norm_cdf(a) - (s / math.sqrt(2 * math.pi))


# ---------------------------------------------------------------------------
# gates + luck removal
# ---------------------------------------------------------------------------

def evaluate(bets, rng):
    n = len(bets)
    if n == 0:
        return None
    wins = sum(b["win"] for b in bets)
    profit = sum(b["profit"] for b in bets)
    roi = profit / n
    # probability-points edge: did the outcome beat the baseline forecast
    edge = mean([b["win"] - b["p_base"] for b in bets])
    # Monte-Carlo null: identical bet list, no-skill outcomes
    p_base_list = [b["p_base"] for b in bets]
    null_rois = []
    for _ in range(NULL_REPS):
        tot = 0.0
        for pb in p_base_list:
            if rng.random() < pb:
                tot += (1.0 / pb - 1.0)
            else:
                tot -= 1.0
        null_rois.append(tot / n)
    null_rois.sort()
    p_null = sum(1 for x in null_rois if x >= roi) / NULL_REPS
    luck_line = null_rois[int(0.95 * NULL_REPS)]
    # split-half stability
    half = n // 2
    r1 = sum(b["profit"] for b in bets[:half]) / half if half else None
    r2 = sum(b["profit"] for b in bets[half:]) / (n - half) if n - half else None
    return {
        "bets": n, "wins": wins, "losses": n - wins, "hit_rate": wins / n,
        "roi": roi, "edge_pp": edge * 100.0,
        "p_null": p_null,
        "null_median_roi": null_rois[NULL_REPS // 2],
        "luck_line_roi": luck_line,
        "skill_est_roi": roi - null_rois[NULL_REPS // 2],
        "excess_over_luck_pp": (roi - luck_line) * 100.0,
        "half1_roi": r1, "half2_roi": r2,
        "stake_returned": 1.0 + roi,
    }


def ols(xs, ys, label, note, expected=1.0):
    """Ordinary least squares y = a + b x, with t test and 95% interval on b."""
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if n < 10 or sxx <= 0:
        return None
    b = sxy / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in resid)
    se = math.sqrt((sse / (n - 2)) / sxx)
    t = b / se if se > 0 else 0.0
    p = 2 * (1 - _student_t_cdf(abs(t), n - 2))
    lo, hi = b - 1.96 * se, b + 1.96 * se
    sst = sum((y - my) ** 2 for y in ys)
    return {"label": label, "n": n, "slope": b, "se": se, "t": t, "p": p,
            "lo": lo, "hi": hi, "r2": (1 - sse / sst) if sst > 0 else None,
            "expected": expected, "note": note}


def signal_study(recs):
    """Does a signal contain information the baseline line missed?

    A bet-level test can only use the handful of games that clear a trigger,
    which on a 100-game window is far too few to conclude anything.  This tests
    the SIGNAL on every evaluated game instead: regress the model's out-of-sample
    error on the signal.  A slope that is reliably away from zero means the
    signal carries information; a slope near zero means it does not.
    """
    out = []
    xs = [r["rest_home"] - r["rest_away"] for r in recs if r["rest_home"] is not None]
    sub = [r for r in recs if r["rest_home"] is not None]
    out.append(ols([r["rest_home"] - r["rest_away"] for r in sub],
                   [r["resid_margin"] for r in sub],
                   "Rest-day differential  ->  margin error",
                   "Points of home margin per extra day of rest the home team holds."))
    out.append(ols([r["b2b_away"] - r["b2b_home"] for r in recs],
                   [r["resid_margin"] for r in recs],
                   "Back-to-back differential  ->  margin error",
                   "Points of home margin when only the away team is on the second night of a back-to-back."))
    out.append(ols([r["density_away"] - r["density_home"] for r in recs],
                   [r["resid_margin"] for r in recs],
                   "Four-day density differential  ->  margin error",
                   "Points of home margin per extra game the away team played in the previous four days."))
    out.append(ols([REST_PER_DAY * (r["rest_home"] - r["rest_away"])
                    + B2B_POINTS * (r["b2b_away"] - r["b2b_home"]) for r in sub],
                   [r["resid_margin"] for r in sub],
                   "S1 shift  ->  margin error (slope 1 = correctly sized)",
                   "If the rest signal is real AND correctly sized this slope is 1.0. "
                   "Slope 0 means the shift adds nothing; slope 2 means it should be doubled."))
    out.append(ols([r["b2b_home"] + r["b2b_away"] for r in recs],
                   [r["resid_total"] for r in recs],
                   "Back-to-back count  ->  total error",
                   "Points of total scoring per team playing the second night of a back-to-back."))
    out.append(ols([-B2B_TOTAL * (r["b2b_home"] + r["b2b_away"]) for r in recs],
                   [r["resid_total"] for r in recs],
                   "S3 shift  ->  total error (slope 1 = correctly sized)",
                   "Same test for the totals signal."))
    for o in out:
        if o["se"] and abs(o["slope"]) > 0:
            se_needed = abs(o["slope"]) / 2.802     # 80% power, 5% two-sided
            o["n_required"] = int(math.ceil(o["n"] * (o["se"] / se_needed) ** 2))
            o["games_short"] = max(0, o["n_required"] - o["n"])
        else:
            o["n_required"] = None
            o["games_short"] = None
    return [o for o in out if o]


def power_mde(bets):
    """Smallest true ROI this many bets could have detected at 80% power, 5% size."""
    n = len(bets)
    if n < 5:
        return None
    profits = [b["profit"] for b in bets]
    sdp = sd(profits)
    if not sdp:
        return None
    return (0.8416 + 1.96) * sdp / math.sqrt(n)   # z_0.80 + z_0.975


def ols_multi(X, y):
    """Least squares with intercept.  X is a list of rows of predictors."""
    n = len(y)
    k = len(X[0]) if X else 0
    if n < k + 5:
        return None
    A = [[1.0] + list(row) for row in X]
    p = k + 1
    # normal equations
    M = [[sum(A[i][a] * A[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    v = [sum(A[i][a] * y[i] for i in range(n)) for a in range(p)]
    # Gauss-Jordan
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        v[c], v[piv] = v[piv], v[c]
        pv = M[c][c]
        M[c] = [x / pv for x in M[c]]
        v[c] /= pv
        for r in range(p):
            if r == c:
                continue
            f = M[r][c]
            if f:
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
                v[r] -= f * v[c]
    resid = [y[i] - sum(A[i][a] * v[a] for a in range(p)) for i in range(n)]
    sse = sum(r * r for r in resid)
    dof = n - p
    s2 = sse / dof if dof > 0 else 0.0
    # standard errors: diagonal of s2 * (M^-1); M is now identity-augmented so
    # recompute the inverse of the original matrix by re-solving
    Minv = []
    for e in range(p):
        rhs = [1.0 if i == e else 0.0 for i in range(p)]
        Mc = [row[:] for row in M]
        vc = rhs[:]
        for c in range(p):
            for r in range(c + 1, p):
                f = Mc[r][c]
                if f:
                    Mc[r] = [a - f * b for a, b in zip(Mc[r], Mc[c])]
                    vc[r] -= f * vc[c]
        x = [0.0] * p
        for c in range(p - 1, -1, -1):
            x[c] = vc[c] - sum(Mc[c][b] * x[b] for b in range(c + 1, p))
        Minv.append(x)
    ses = [math.sqrt(max(0.0, s2 * Minv[a][a])) for a in range(p)]
    return {"coef": v, "se": ses, "n": n, "dof": dof, "sse": sse}


def adaptive_bets(recs, sigma_m, sigma_t, trig, target, min_hist=25):
    """Signal weights are FITTED on the out-of-sample errors of earlier games
    only, then applied forward.  Nothing from the game being bet, or from any
    later game, can enter the fit.  This is the difference between a strategy
    and a curve fit."""
    bets = []
    hist_X, hist_y = [], []
    for r in recs:
        rh, ra = r["rest_home"], r["rest_away"]
        if rh is None or ra is None:
            continue
        rd = rh - ra
        bd = r["b2b_away"] - r["b2b_home"]
        bc = r["b2b_home"] + r["b2b_away"]
        if len(hist_y) >= min_hist:
            fit = ols_multi(hist_X, hist_y)
            if fit:
                if target == "margin":
                    b0, b1, b2 = fit["coef"]
                    delta = b1 * rd + b2 * bd
                    b = _spread_bet(r, delta, sigma_m,
                                    f"walk-forward fitted weights "
                                    f"(rest {b1:+.2f}, b2b {b2:+.2f}; n_fit={fit['n']})", trig)
                    if b:
                        bets.append(b)
                else:
                    b0, b1 = fit["coef"][0], fit["coef"][1]
                    delta = b1 * bc
                    b = _total_bet(r, delta, sigma_t,
                                   f"walk-forward fitted weight (b2b count {b1:+.2f}; "
                                   f"n_fit={fit['n']})", trig)
                    if b:
                        bets.append(b)
        hist_X.append([rd, bd] if target == "margin" else [bc])
        hist_y.append(r["resid_margin"] if target == "margin" else r["resid_total"])
    return bets


def shrinkage_sensitivity(games, played):
    """How much does the shrinkage choice matter?

    K is declared before any run (K_MARGIN = 4, K_TOTAL = 6).  This table shows
    what the walk-forward would have produced at other values, so the reader can
    see whether the declared value sits on a cliff edge or on a plateau.  It is
    reported, not used to re-tune the model.
    """
    rows = []
    for km in (1, 2, 4, 8, 16, 32):
        for kt in (6,):
            recs = walk_forward(games, played, 13.0, 20.0, k_margin=km, k_total=kt)
            if not recs:
                continue
            sm = sd([r["resid_margin"] for r in recs])
            for r in recs:
                r["p_home_win"] = norm_cdf(r["pred_margin_home"] / sm)
            rows.append({
                "k_margin": km, "k_total": kt, "games": len(recs),
                "mae_margin": mean([abs(r["resid_margin"]) for r in recs]),
                "mae_total": mean([abs(r["resid_total"]) for r in recs]),
                "brier": brier([(r["p_home_win"], 1 if r["actual_margin_home"] > 0 else 0)
                                for r in recs]),
                "su": sum(1 for r in recs
                          if (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0)),
                "declared": km == 4 and kt == 6,
            })
    return rows


def american(p):
    if p is None:
        return None
    if p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return int(round(-100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
RHO = 0.0


def main():
    os.makedirs(SITE_DATA, exist_ok=True)
    rng = random.Random(SEED)
    games, fixtures, inprog, slate, played = build_universe()

    # --- pass 1: provisional sigmas, measure out-of-sample residual spread ---
    recs = walk_forward(games, played, 13.0, 20.0)
    sigma_m = sd([r["resid_margin"] for r in recs])
    sigma_t = sd([r["resid_total"] for r in recs])
    # --- pass 2: recompute probabilities with the measured sigmas ----------
    for r in recs:
        r["p_home_win"] = norm_cdf(r["pred_margin_home"] / sigma_m)
    global RHO
    rho_c = pearson([r["resid_margin"] for r in recs], [r["resid_total"] for r in recs])
    RHO = rho_c["r"] if rho_c else 0.0

    # ------------------------------------------------------------------
    # The trigger grid.  Every strategy is run at every trigger and every
    # cell is published.  Nothing is tuned: the multiple-comparisons gate
    # (G7) is applied across the whole grid.
    # ------------------------------------------------------------------
    cells = {}
    for trig in EDGE_TRIGGERS:
        S = strategies(recs, sigma_m, sigma_t, trig)
        for k, spec in S.items():
            bets = [b for b in (spec["fn"](r) for r in recs) if b]
            cells[(k, trig)] = {"spec": spec, "bets": bets, "trig": trig,
                                "blocked": False, "block_reason": None}
        # ---- S10 / S11 adaptive: weights fitted on past out-of-sample errors --
        cells[("S10", trig)] = {
            "spec": dict(name="Adaptive Rest Model (spread)", kind="Single bet",
                         signal="Rest days and back-to-back flags, with the WEIGHTS fitted on past out-of-sample errors.",
                         desc=("Instead of fixed 0.55 / 1.60 weights, this refits the rest and "
                               "back-to-back coefficients every slate using only the forecast "
                               "errors of games already played, then applies them forward. It "
                               "answers the question the fixed-weight strategies cannot: is the "
                               "signal real but mis-sized, or is it simply not there?")),
            "bets": adaptive_bets(recs, sigma_m, sigma_t, trig, "margin"),
            "trig": trig, "blocked": False, "block_reason": None}
        cells[("S11", trig)] = {
            "spec": dict(name="Adaptive Fatigue Model (total)", kind="Single bet",
                         signal="Back-to-back count, weight fitted on past out-of-sample errors.",
                         desc="Same adaptive method applied to the totals market."),
            "bets": adaptive_bets(recs, sigma_m, sigma_t, trig, "total"),
            "trig": trig, "blocked": False, "block_reason": None}
        # ---- S8 cross-game parlay (two legs, different games, same slate) ----
        cells[("S8", trig)] = cross_game_parlay(recs, sigma_m, trig)
        # ---- S9 player-prop combos -----------------------------------------
        cells[("S9", trig)] = {
            "spec": dict(name="Player-Prop Combos (points + rebounds + assists)",
                         kind="Player prop combo",
                         signal="Would require a verified per-game player box-score log.",
                         desc=("Combines two or three player props from the same game. "
                               "NOT BUILT: originating a player-prop line requires each "
                               "player's game-by-game box score, and no official page "
                               "available in this environment publishes a full season of "
                               "them. Only two partial official leaderboards exist - the "
                               "top 50 scorers and the top 24 by minutes - and neither is "
                               "a game log. Nothing is estimated in their place.")),
            "bets": [], "trig": trig, "blocked": True,
            "block_reason": ("No verified per-game player log. The official Players > "
                             "Traditional table is rendered client-side and only page 1 "
                             "(50 players, season averages) is reachable; a prop line "
                             "needs the game-by-game distribution behind those averages."),
        }

    # ---- null control: the same number of bets, no signal ------------------
    total_bets = sum(len(v["bets"]) for v in cells.values())
    for trig in EDGE_TRIGGERS:
        ctrl = []
        pool = list(recs)
        rng.shuffle(pool)
        take = max(1, total_bets // len(EDGE_TRIGGERS))
        for r in pool[:take]:
            p = norm_cdf(rng.uniform(-2.0, 2.0))
            side = "HOME" if p >= 0.5 else "AWAY"
            pb = r["p_home_win"] if side == "HOME" else 1 - r["p_home_win"]
            win = 1 if ((r["actual_margin_home"] > 0) == (side == "HOME")) else 0
            ctrl.append(_mk(r, "Moneyline (random)", side, pb, p, win, "null control"))
        cells[("S0", trig)] = {
            "spec": dict(name="Null Control (random moneyline)", kind="Control",
                         signal="None - a uniform random probability.",
                         desc=("Takes the same number of moneyline bets at random, with no "
                               "signal at all. Any gate this control passes is a gate too "
                               "weak to detect skill.")),
            "bets": ctrl, "trig": trig, "blocked": False, "block_reason": None}

    for key, v in cells.items():
        v["stats"] = evaluate(v["bets"], rng) if v["bets"] else None

    # ---- system-level gate G6: is the baseline line any good? --------------
    pairs = [(r["p_home_win"], 1 if r["actual_margin_home"] > 0 else 0) for r in recs]
    br = brier(pairs)
    mae_m = mean([abs(r["resid_margin"]) for r in recs])
    mae_t = mean([abs(r["resid_total"]) for r in recs])
    naive_home = mean([1.0 if r["actual_margin_home"] > 0 else 0.0 for r in recs])
    naive_mae = mean([abs(r["actual_margin_home"] - mean([x["actual_margin_home"] for x in recs]))
                      for r in recs])
    brier_naive = brier([(naive_home, 1 if r["actual_margin_home"] > 0 else 0) for r in recs])
    su = sum(1 for r in recs if (r["pred_margin_home"] > 0) == (r["actual_margin_home"] > 0))
    g6 = {
        "games": len(recs), "brier": br, "brier_naive": brier_naive,
        "mae_margin": mae_m, "mae_margin_naive": naive_mae,
        "mae_total": mae_t, "straight_up": f"{su}-{len(recs)-su}",
        "straight_up_pct": su / len(recs),
        "home_win_rate": naive_home,
        "sigma_margin": sigma_m, "sigma_total": sigma_t,
        "pass": bool(br is not None and br <= 0.25 and mae_m < naive_mae),
    }

    # ---- gates ------------------------------------------------------------
    n_cells = sum(1 for v in cells.values() if v["stats"] and v["stats"]["bets"] >= MIN_BETS)
    sidak = 1 - (1 - ALPHA) ** (1 / max(1, n_cells))
    for key, v in cells.items():
        st = v["stats"]
        if not st:
            v["gates"] = {"G1_sample": False, "G2_positive": False, "G3_significance": False,
                          "G4_stability": False, "G5_no_lookahead": True, "G7_sidak": False,
                          "G6_baseline": g6["pass"], "all_pass": False,
                          "verdict": "NO BETS GENERATED"}
            continue
        g1 = st["bets"] >= MIN_BETS
        g2 = st["roi"] > 0
        g3 = st["p_null"] <= ALPHA
        g4 = (st["half1_roi"] or -9) > 0 and (st["half2_roi"] or -9) > 0
        g5 = True  # walk-forward: every forecast uses only games strictly before it
        g7 = st["p_null"] <= sidak
        v["gates"] = {"G1_sample": g1, "G2_positive": g2, "G3_significance": g3,
                      "G4_stability": g4, "G5_no_lookahead": g5, "G7_sidak": g7,
                      "G6_baseline": g6["pass"]}
        v["gates"]["all_pass"] = all([g1, g2, g3, g4, g5, g7, g6["pass"]])

    # ---- leaderboard + reward tiers ---------------------------------------
    def tier(v):
        st, g = v["stats"], v["gates"]
        if v["blocked"]:
            return 0, "Blocked - missing data", 0.0
        if not st or not g.get("G1_sample"):
            return 0, "Unranked - below sample floor", 0.0
        if not g.get("G6_baseline"):
            return 0, "System gate failed", 0.0
        if g.get("all_pass"):
            return (4, "Funded - full unit", 1.0) if st["roi"] >= 0.10 else (3, "Funded - half unit", 0.5)
        if g.get("G3_significance"):
            return 2, "Promising - paper only", 0.0
        if st["roi"] > 0:
            return 1, "Paper", 0.0
        return 1, "Paper (negative)", 0.0

    for key, v in cells.items():
        v["tier"], v["tier_name"], v["stake"] = tier(v)
        st = v["stats"]
        v["score"] = (st["roi"] * math.sqrt(min(st["bets"], 100) / 100.0) * (1 - st["p_null"])
                      if st else None)

    results = {}
    for (sid, trig), v in cells.items():
        v["id"] = sid
        results[f"{sid}@{trig:.2f}"] = v
    order = sorted(results.items(),
                   key=lambda kv: (kv[1]["score"] is None, -(kv[1]["score"] or 0)))

    # ---- shrinkage sensitivity --------------------------------------------
    sens = shrinkage_sensitivity(games, played)

    # ---- signal study + power ---------------------------------------------
    sig = signal_study(recs)
    for k, v in cells.items():
        v["mde"] = power_mde(v["bets"]) if v["bets"] else None
        st = v["stats"]
        if st and v["mde"]:
            st["mde_roi"] = v["mde"]
            st["underpowered"] = st["roi"] < v["mde"]

    # ---- correlations ------------------------------------------------------
    corr = correlation_block(games, recs, results, sigma_m, sigma_t)

    # ---- the slate: originated lines for the next three days ---------------
    R_full = Ratings(games)
    slate_out = []
    for row in slate:
        rh = rest_days(played, row["home"], row["date"])
        ra = rest_days(played, row["away"], row["date"])
        p = R_full.predict(row["home"], row["away"])
        ph = norm_cdf(p["pred_margin_home"] / sigma_m)
        # signal adjustment the strategies would apply
        d_m = 0.0
        if rh is not None and ra is not None:
            d_m = REST_PER_DAY * (rh - ra) + B2B_POINTS * ((1 if ra == 1 else 0) - (1 if rh == 1 else 0))
        d_t = -B2B_TOTAL * ((1 if rh == 1 else 0) + (1 if ra == 1 else 0))
        slate_out.append({
            "date": row["date"], "time_et": row["time_et"], "away": row["away"],
            "home": row["home"], "away_rec": row["away_rec"], "home_rec": row["home_rec"],
            "game_id": row["game_id"], "source_url": row["source_url"],
            "spread_home": -p["pred_margin_home"],
            "total": p["pred_total"],
            "pred_home_pts": p["pred_home_pts"], "pred_away_pts": p["pred_away_pts"],
            "p_home_win": ph,
            "ml_home": american(ph), "ml_away": american(1 - ph),
            "signal_margin_shift": d_m, "signal_total_shift": d_t,
            "rest_home": rh, "rest_away": ra,
            "b2b_home": 1 if rh == 1 else 0, "b2b_away": 1 if ra == 1 else 0,
            "rating_home": p["rating_home"], "rating_away": p["rating_away"],
            "hca": p["hca"],
        })

    # ---- distribution ------------------------------------------------------
    out = {
        "meta": meta_block(games, fixtures, recs, sigma_m, sigma_t, RHO),
        "g6": g6,
        "sidak_alpha": sidak,
        "min_bets": MIN_BETS,
        "edge_triggers": EDGE_TRIGGERS,
        "null_reps": NULL_REPS,
        "strategies": [
            {
                "id": k, "sid": v["id"], "trigger": v["trig"],
                "name": v["spec"]["name"], "kind": v["spec"]["kind"],
                "signal": v["spec"]["signal"], "description": v["spec"]["desc"],
                "stats": v["stats"], "gates": v["gates"], "tier": v["tier"],
                "tier_name": v["tier_name"], "stake": v["stake"], "score": v["score"],
                "blocked": v["blocked"], "block_reason": v["block_reason"],
                "bets": v["bets"],
            } for k, v in order
        ],
        "correlations": corr,
        "signal_study": sig,
        "shrinkage_sensitivity": sens,
        "slate": slate_out,
        "eval_games": recs,
        "ratings": [{"team": t, "abbr": t, "name": NAMES[t], "rating": R_full.rating[t],
                     "off": R_full.off[t], "def": R_full.def_[t], "gp": R_full.gp[t],
                     "hca": R_full.hca, "league_pts": R_full.league_pts} for t in TEAMS],
    }
    out["ratings"].sort(key=lambda x: -x["rating"])

    # ---- injuries, rotation and game flow (official rows only) ------------
    out["context"] = context_mod.build(slate, load("gamelog.json"), load("injuries.json"), played)

    # ---- governance content ------------------------------------------------
    out["sources"] = SOURCES
    out["flagged"] = FLAGGED
    out["questions"] = QUESTIONS
    out["suggestions"] = SUGGESTIONS
    return out


def meta_block(games, fixtures, recs, sigma_m, sigma_t, rho):
    gl = load("gamelog.json")
    return {
        "generated_at_utc": "2026-11-14T01:20:00Z",
        "session": "arena/e32856d8-nba1",
        "captured_games": len(games),
        "unpublished_fixtures": len(fixtures),
        "total_games_in_window": len(games) + len(fixtures),
        "window": "2026-10-20 to 2026-11-12",
        "train_start": "2026-10-20",
        "eval_games": len(recs),
        "eval_window": f"{recs[0]['date']} to {recs[-1]['date']}",
        "sigma_margin": sigma_m, "sigma_total": sigma_t, "rho_margin_total": rho,
        "edge_triggers": EDGE_TRIGGERS,
        "start_after_dates": 5,
        "gamelog_source_url": "https://www.nba.com/games?date=2026-<date>",
        "standings_source_url": "https://www.nba.com/standings",
        "shrine": gl["verification"],
    }


def correlation_block(games, recs, results, sigma_m, sigma_t):
    out = []
    am = [g["home_pts"] - g["away_pts"] for g in games]
    at = [g["home_pts"] + g["away_pts"] for g in games]
    hp = [g["home_pts"] for g in games]
    ap = [g["away_pts"] for g in games]
    rm = [r["resid_margin"] for r in recs]
    rt = [r["resid_total"] for r in recs]

    def add(label, xs, ys, note, basis):
        c = pearson(xs, ys)
        if not c:
            return
        out.append({"label": label, "n": c["n"], "r": c["r"], "p": c["p"],
                    "lo": c["lo"], "hi": c["hi"], "note": note, "basis": basis})

    add("Home margin vs total points", am, at,
        "The correlation that decides whether a same-game parlay of a side and a total is worth more or less than the product of its legs.",
        "All 151 captured games")
    add("Home points vs away points", hp, ap,
        "Negative values mean a blowout for one side suppresses the other team's scoring - the mechanism behind the margin/total link.",
        "All 151 captured games")
    add("Absolute margin vs total points", [abs(x) for x in am], at,
        "Do close games and blowouts produce different scoring environments?",
        "All 151 captured games")
    add("OUT-OF-SAMPLE margin residual vs total residual", rm, rt,
        "The number actually used to price same-game parlays: the correlation left over after both models have made their forecast.",
        f"Walk-forward window, {len(recs)} games")

    # joint table for the SGP-relevant pair
    j = Counter()
    for r in recs:
        cover = r["actual_margin_home"] > r["pred_margin_home"]
        over = r["actual_total"] > r["pred_total"]
        j[(cover, over)] += 1
    n = len(recs)
    both = j[(True, True)] / n
    out.append({
        "label": "P(home covers AND over), measured", "n": n, "r": None, "p": None,
        "lo": None, "hi": None,
        "joint": both, "independent": 0.25,
        "delta_pp": (both - 0.25) * 100.0,
        "frechet_lo": 0.0, "frechet_hi": 0.5,
        "note": ("Measured on the walk-forward window against the originated number. "
                 "Independence would give 0.250. The gap is the correlation edge a "
                 "same-game parlay price must account for."),
        "basis": f"Walk-forward window, {n} games",
    })

    # same-slate correlation: are outcomes of different games on one date linked?
    # This is the assumption a cross-game parlay rests on.
    bydate = defaultdict(list)
    for r in recs:
        bydate[r["date"]].append(r)
    xs1, xs2 = [], []
    for dt, grp in sorted(bydate.items()):
        cov = [1.0 if r["actual_margin_home"] > r["pred_margin_home"] else 0.0 for r in grp]
        for i in range(len(cov)):
            for j in range(len(cov)):
                if i == j:
                    continue
                xs1.append(cov[i]); xs2.append(cov[j])
    if len(xs1) > 8:
        c = pearson(xs1, xs2)
        if c:
            out.append({"label": "Same-slate cover indicator, game A vs game B",
                        "n": len(xs1), "r": c["r"], "p": c["p"], "lo": c["lo"], "hi": c["hi"],
                        "note": ("Every ordered pair of different games played on the same date. "
                                 "A value near zero is what makes pricing a cross-game parlay at "
                                 "independence defensible; a positive value would make parlays "
                                 "cheaper to the house than independence implies."),
                        "basis": f"{len(bydate)} slates, {len(xs1)} ordered pairs"})

    # strategy overlap - how correlated are the strategy bet sets themselves
    ids = [k for k, v in results.items() if v["bets"]]
    ov = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A = {(x["game_id"], x["market"]) for x in results[a]["bets"]}
            B = {(x["game_id"], x["market"]) for x in results[b]["bets"]}
            if not A or not B:
                continue
            ov.append({"a": a, "b": b, "jaccard": len(A & B) / len(A | B),
                       "shared": len(A & B), "a_bets": len(A), "b_bets": len(B)})
    return {"pairs": out, "strategy_overlap": ov}


if __name__ == "__main__":
    data = main()
    with open(os.path.join(SITE_DATA, "engine_v2.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    print(json.dumps(data["meta"], indent=1))
    print(json.dumps(data["g6"], indent=1))
    for s in data["strategies"]:
        st = s["stats"]
        if st:
            print(f"{s['id']:3} {s['name'][:34]:34} n={st['bets']:3} "
                  f"w={st['wins']:3} roi={st['roi']*100:+7.2f}% "
                  f"p={st['p_null']:.3f} luckline={st['luck_line_roi']*100:+6.2f}% "
                  f"tier={s['tier']} {s['tier_name']}")
        else:
            print(f"{s['id']:3} {s['name'][:34]:34} NO BETS")
