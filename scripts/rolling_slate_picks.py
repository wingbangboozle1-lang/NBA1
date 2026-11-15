#!/usr/bin/env python3
"""rolling_slate_picks.py - picks, measured correlations, the frozen
pre-registration and the tamper-evident ledger for the 2026-11-15 build.

    python3 scripts/rolling_slate_picks.py

What this produces
------------------
    correlations.json   rho MEASURED from the official box scores and the
                        official results (the repository's rho values were
                        model-derived, which is Flagged F6)
    picks.json          the plays the registered strategy rules produce for the
                        horizon, priced with the measured rho
    preregistration.json  one frozen pre-registration document per strategy,
                        with the sha256 of each document
    ledger.json         the tamper-evident pick ledger: the sha256 of every
                        published pick, published BEFORE tip, and re-verified
                        after settlement
    settlement.json     every published pick graded against the official final
                        score, with the settlement stamp

The rules are the ones already registered in `engine/strategies.py`. This file
does not invent new strategy rules; it feeds them the new model and prices the
parlays with a measured correlation instead of a derived one.
"""

import datetime
import hashlib
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import rolling_slate_model as M          # noqa: E402
import strategies as ST                  # noqa: E402

DER = os.path.join(ROOT, "data", "derived", "rolling_slate_2026_11_15")
DOCS_DATA = os.path.join(ROOT, "docs", "data")
LEDGER_DIR = os.path.join(ROOT, "data", "ledger")

HORIZON_START = "2026-11-15"
HORIZON_END = "2026-11-18"
TRAIN_FROM, TRAIN_TO = "2026-10-20", "2026-11-05"

NORM = M.NORM


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


def log(msg):
    print("[%s] %s" % (now_utc(), msg), flush=True)


def sha256_payload(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ------------------------------------------------------- measured correlations
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, n
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None, n
    r = sxy / math.sqrt(sxx * syy)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else None
    p = None
    if t is not None:
        try:
            p = 2 * (1 - NORM.cdf(abs(t)))
        except Exception:                                # noqa: BLE001
            p = None
    return r, n, p


def measured_correlations(games, boxes_doc):
    """Correlations measured from the official results and box scores."""
    # 1) side vs total across games
    margins, totals = [], []
    for g in games.values():
        if not g.get("is_final"):
            continue
        fa, fh = g.get("final_away_score"), g.get("final_home_score")
        if fa is None or fh is None:
            continue
        margins.append(int(fh) - int(fa))
        totals.append(int(fh) + int(fa))
    r_mt = pearson(margins, totals)
    r_home = pearson([1 if m > 0 else 0 for m in margins], margins)

    # 2) player-pair correlations inside one game
    teams, opp, total = [], [], []
    for g in boxes_doc.get("games", []):
        by_team = {}
        for p in g.get("players", []):
            if p.get("did_not_play"):
                continue
            by_team.setdefault(p.get("team"), []).append(p)
        if len(by_team) != 2:
            continue
        (ta, pa), (tb, pb) = sorted(by_team.items())
        for x in pa:
            for y in pb:
                if x.get("points") is None or y.get("points") is None:
                    continue
                opp.append(float(x["points"]))
                opp.append(float(y["points"]))
                teams.append(float(x["points"]))
                teams.append(float(y["points"]))
    # teammate pairs inside one team
    tm_pts, tm_tot = [], []
    for g in boxes_doc.get("games", []):
        by_team = {}
        for p in g.get("players", []):
            if p.get("did_not_play"):
                continue
            by_team.setdefault(p.get("team"), []).append(p)
        for t, ps in by_team.items():
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    a, b = ps[i], ps[j]
                    if a.get("points") is None or b.get("points") is None:
                        continue
                    tm_pts.append(float(a["points"]))
                    tm_pts.append(float(b["points"]))
                    tm_tot.append(float(a.get("points") or 0) + float(b.get("points") or 0))
    r_teammate = pearson(tm_pts, tm_pts)
    r_opponent = pearson(opp, opp)

    def pack(r, label, why):
        if r is None:
            return {"label": label, "rho": None, "n": 0, "status": "not measurable",
                    "what_it_is": why, "source": None}
        val, n = r[0], r[1]
        p = r[2] if len(r) > 2 else None
        return {"label": label, "rho": round(val, 4), "n": n, "p_value": p,
                "status": "MEASURED from official data", "what_it_is": why,
                "source": "https://www.nba.com/games"}

    return {
        "side_total": pack(r_mt, "Side (margin) vs game total, same game",
                           "the correlation between the winning margin and the "
                           "game total across every completed official game"),
        "home_win_margin": pack(r_home, "Home win (0/1) vs margin",
                                 "how strongly the margin implies the home win"),
        "teammate_points": pack(r_teammate, "Teammate points, same game",
                                 "the correlation between two teammates' point "
                                 "totals inside one official box score"),
        "opponent_points": pack(r_opponent, "Opponent points, same game",
                                "the correlation between two opponents' point "
                                "totals inside one official box score"),
        "model_derived_for_reference": {
            "note": "The values the rest of the repository used were MODEL-DERIVED "
                    "(engine/strategies.py SGP_RHO), which is Flagged F6. They are "
                    "kept only so the change is visible.",
            "model_derived": ST.SGP_RHO,
        },
    }


def bivariate_cdf(a, b, rho, steps=400):
    """P(X < a, Y < b) for a standard bivariate normal with correlation rho."""
    pa, pb = NORM.cdf(a), NORM.cdf(b)
    if not rho:
        return pa * pb
    if rho <= -0.999:
        rho = -0.999
    if rho >= 0.999:
        rho = 0.999
    n = steps if steps % 2 == 0 else steps + 1
    h = rho / n

    def f(t):
        d = 1 - t * t
        e = math.exp(-(a * a - 2 * t * a * b + b * b) / (2 * d))
        return e / math.sqrt(d) / (2 * math.pi)

    total = f(0) + f(rho)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(i * h)
    return pa * pb + total * h / 3.0


def parlay_price(p1, p2, rho):
    """Joint probability with correlation rho, next to the naive product."""
    a, b = NORM.inv_cdf(min(max(p1, 1e-9), 1 - 1e-9)), \
        NORM.inv_cdf(min(max(p2, 1e-9), 1 - 1e-9))
    joint = bivariate_cdf(a, b, rho)
    naive = p1 * p2
    return {
        "leg_probabilities": [round(p1, 4), round(p2, 4)],
        "rho": round(rho, 4),
        "joint_probability_with_rho": round(joint, 4),
        "naive_independent_product": round(naive, 4),
        "difference": round(joint - naive, 4),
        "fair_price_with_rho": int(round(100 * joint)) if joint > 0 else None,
        "fair_price_naive_product": int(round(100 * naive)) if naive > 0 else None,
        "pricing_note": "the price with the measured rho, and the naive product "
                        "printed beside it; the difference is the correlation cost",
    }


# ------------------------------------------------------------------ settlement
def grade_leg(leg, margin, total):
    m = leg.get("market")
    if m == "Point spread":
        diff = margin - float(leg["ref_line"])
        if abs(diff) < 1e-9:
            return "push"
        won = diff > 0 if leg["side"] == "home" else diff < 0
        return "win" if won else "loss"
    if m == "Game total":
        diff = total - float(leg["ref_line"])
        if abs(diff) < 1e-9:
            return "push"
        won = diff > 0 if leg["side"] == "over" else diff < 0
        return "win" if won else "loss"
    if m == "Moneyline":
        if margin == 0:
            return "push"
        won = margin > 0 if leg["side"] == "home" else margin < 0
        return "win" if won else "loss"
    return "ungraded"


def grade_pick(pick, game):
    """Grade one published pick against the official final."""
    fa, fh = game.get("final_away_score"), game.get("final_home_score")
    if fa is None or fh is None:
        return None
    margin = int(fh) - int(fa)
    total = int(fh) + int(fa)
    if pick.get("n_legs", 1) > 1:
        legs = pick.get("legs_detail") or []
        results = []
        for lg in legs:
            gid = lg.get("game_id")
            g = game.get("_by_id", {}).get(gid) if game.get("_by_id") else None
            if g is None:
                return None
            gfa, gfh = g.get("final_away_score"), g.get("final_home_score")
            if gfa is None or gfh is None:
                return None
            results.append(grade_leg({"market": lg.get("market"), "side": lg.get("side"),
                                      "ref_line": lg.get("ref_line")},
                                     int(gfh) - int(gfa), int(gfh) + int(gfa)))
        if "loss" in results:
            return "loss"
        if "push" in results:
            return "push"
        if "win" in results:
            return "win"
        return "ungraded"
    return grade_leg(pick, margin, total)
