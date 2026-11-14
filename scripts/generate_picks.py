#!/usr/bin/env python3
"""
generate_picks.py — model picks for the 11/14–11/17 horizon, built ONLY on
data/derived/horizon_lines.json (scripts/originate_horizon.py output).

Strategy families (candidate identity, all UNVALIDATED — no strategy has passed the
validation gates: Build A 0/8, Build B 0/10):

  SINGLE-SPREAD-v1   pick the model favourite when |originated spread| >= pick_gate_margin
                     (gate 3.0, inherited from data/originated_lines.json assumptions).
  PARLAY2-IND-v1     two SINGLE-SPREAD legs from DIFFERENT games (same date). Games are
                     treated as independent events; the joint probability is published as
                     the Fréchet–Hoeffding band [max(0,p1+p2-1), min(p1,p2)] — the same
                     bounds method as scripts/build_edge_site.py — never a single number.
  SGP2-PROP-v1       same-game pair of player points OVER legs (originated prop lines =
                     floor(season avg)+0.5, sigma = sqrt(avg)*1.15, both documented
                     assumptions). Joint probability uses a Gaussian-copula bivariate
                     normal with the rho values recorded in docs/data/correlations.json
                     (MODEL-DERIVED: two_teammates -0.2, two_opponents +0.05) — labelled
                     as such, never as a measured statistic.

HONESTY RULES:
  * No market price is used or claimed; every probability is model-internal.
  * Every pick is stamped with the as-of date of its inputs and labelled
    MODEL OUTPUT — UNVALIDATED (zero stake until a strategy passes the gates).
  * G-PROP / G4 / G5 (market-comparison and variance-evidence gates) stay BLOCKED.
"""
import json
import math
import os
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

PICK_GATE_MARGIN = 3.0          # inherited from data/originated_lines.json assumptions
PICK_GATE_SOURCE = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/originated_lines.json"

# MODEL-DERIVED rho register (docs/data/correlations.json, Build B), labelled as such
SGP_RHO_TEAMMATES = -0.2
SGP_RHO_OPPONENTS = 0.05
SGP_RHO_SOURCE_FILE = "docs/data/correlations.json"

OVERDISPERSION = 1.15           # same documented assumption as scripts/originate_lines.py props

STATUS = "MODEL OUTPUT — UNVALIDATED (no strategy has passed the validation gates; zero stake)"


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def joint_over_over(z1, z2, rho, steps=400):
    """P(X>l1, Y>l2) for standardised thresholds z1,z2 under a Gaussian copula with
    correlation rho. Simpson integration of phi(t)*Phi((rho*t - z2)/sqrt(1-rho^2))
    from t=z1 upward. rho=0 reduces to the independent product."""
    if rho == 0:
        return (1 - norm_cdf(z1)) * (1 - norm_cdf(z2))
    s = math.sqrt(1.0 - rho * rho)
    a, b = z1, 8.0
    if b <= a:
        b = a + 1.0
    n = 2 * steps
    hstep = (b - a) / n
    total = 0.0
    for i in range(n + 1):
        t = a + i * hstep
        val = phi(t) * norm_cdf((rho * t - z2) / s)
        w = 1 if i in (0, n) else (4 if i % 2 == 1 else 2)
        total += w * val
    return max(0.0, min(1.0, total * hstep / 3.0))


def rho_bounds(p1, p2):
    denom = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    lb_joint = max(0.0, p1 + p2 - 1.0)
    ub_joint = min(p1, p2)
    rho_lb = (lb_joint - p1 * p2) / denom if denom else None
    rho_ub = (ub_joint - p1 * p2) / denom if denom else None
    return lb_joint, ub_joint, rho_lb, rho_ub


def main():
    hl = json.load(open(os.path.join(DATA, "derived", "horizon_lines.json"), encoding="utf-8"))
    games = hl["games"]
    players = [p for p in json.load(open(os.path.join(DATA, "players_2026_27.json"),
                                        encoding="utf-8"))["players"]
               if p.get("stat_source") == "players_traditional" and p.get("pts")]

    # ---------------- SINGLE-SPREAD-v1 ---------------------------------------
    singles = []
    for g in games:
        sp = g["line_spread_home"]
        p_home = g["model_home_win_prob"]
        if abs(sp) < PICK_GATE_MARGIN:
            pick = {"pick_side": "PASS", "pick_line": None,
                    "gate": f"G-CFG pass-through (|spread| {abs(sp):.1f} < {PICK_GATE_MARGIN}) — no bet",
                    "pick_prob": None}
        else:
            if sp > 0:
                side, prob = "HOME", p_home
                team, line_val = g["home"], sp
            else:
                side, prob = "AWAY", 1 - p_home
                team, line_val = g["away"], -sp
            pick = {"pick_side": side, "pick_line": f"{team} -{abs(round(line_val,1)):.1f}",
                    "gate": f"G-CFG pass (|spread| {abs(sp):.1f} >= {PICK_GATE_MARGIN})",
                    "pick_prob": round(prob, 4)}
        singles.append({
            "date": g["date"], "game_id": g["game_id"], "matchup": g["matchup"],
            "line_spread_home": g["line_spread_home"], "line_total": g["line_total"],
            "model_home_win_prob": p_home,
            "pick": pick, "status": STATUS,
            "sources": [g["schedule_source"], g["inputs_source"]],
            "as_of": g["inputs_as_of"],
        })
    n_single_picks = sum(1 for s in singles if s["pick"]["pick_side"] != "PASS")

    # ---------------- PARLAY2-IND-v1 ------------------------------------------
    parlays = []
    by_date = {}
    for s in singles:
        if s["pick"]["pick_side"] != "PASS":
            by_date.setdefault(s["date"], []).append(s)
    for dte in sorted(by_date):
        cands = sorted(by_date[dte], key=lambda x: -x["pick"]["pick_prob"])
        kept = 0
        for s1, s2 in combinations(cands, 2):
            if kept >= 3:
                break
            p1, p2 = s1["pick"]["pick_prob"], s2["pick"]["pick_prob"]
            lb, ub, rho_lb, rho_ub = rho_bounds(p1, p2)
            parlays.append({
                "date": dte,
                "leg1": f"{s1['matchup']} — {s1['pick']['pick_line']}", "p1": round(p1, 3),
                "leg2": f"{s2['matchup']} — {s2['pick']['pick_line']}", "p2": round(p2, 3),
                "joint_lb": round(lb, 3), "joint_ub": round(ub, 3),
                "rho_lb": None if rho_lb is None else round(rho_lb, 3),
                "rho_ub": None if rho_ub is None else round(rho_ub, 3),
                "fair_odds_lb": round(1.0 / ub, 2) if ub > 0 else None,
                "fair_odds_ub": round(1.0 / lb, 2) if lb > 0 else None,
                "method": ("legs from different games; joint published as the "
                           "Fréchet–Hoeffding band, never a single number"),
                "status": STATUS,
                "sources": [s1["sources"][0], s2["sources"][0]],
                "as_of": s1["as_of"],
            })
            kept += 1

    # ---------------- SGP2-PROP-v1 ---------------------------------------------
    sgp = []
    for g in games:
        game_players = [p for p in players if p["team"] in (g["home"], g["away"])]
        same_team_pairs, cross_pairs = [], []
        by_team = {}
        for p in game_players:
            by_team.setdefault(p["team"], []).append(p)
        for team, ps in by_team.items():
            top = sorted(ps, key=lambda x: -x["pts"])[:2]
            if len(top) == 2:
                same_team_pairs.append((top[0], top[1], team))
        if len(by_team) == 2:
            t1, t2 = sorted(by_team)
            if by_team[t1] and by_team[t2]:
                a = max(by_team[t1], key=lambda x: x["pts"])
                b = max(by_team[t2], key=lambda x: x["pts"])
                cross_pairs.append((a, b, None))
        for kind, pair in ([("two_teammates", p) for p in same_team_pairs] +
                           [("two_opponents", p) for p in cross_pairs]):
            rho = SGP_RHO_TEAMMATES if kind == "two_teammates" else SGP_RHO_OPPONENTS

            def leg(p):
                m, s = p["pts"], math.sqrt(max(p["pts"], 0.1)) * OVERDISPERSION
                line = math.floor(m) + 0.5
                z = (line - m) / s
                return {"player": p["player"], "team": p["team"], "line": line,
                        "season_avg": m, "sigma": round(s, 3), "prob_over": round(1 - norm_cdf(z), 4),
                        "z": z}

            l1, l2 = leg(pair[0]), leg(pair[1])
            joint = joint_over_over(l1["z"], l2["z"], rho)
            joint_ind = (1 - norm_cdf(l1["z"])) * (1 - norm_cdf(l2["z"]))
            sgp.append({
                "date": g["date"], "game": g["matchup"], "kind": kind, "rho": rho,
                "leg1": f"{l1['player']} ({l1['team']}) OVER {l1['line']}",
                "leg2": f"{l2['player']} ({l2['team']}) OVER {l2['line']}",
                "leg1_detail": l1, "leg2_detail": l2,
                "joint_prob_rho": round(joint, 4),
                "joint_prob_independent": round(joint_ind, 4),
                "rho_status": "MODEL-DERIVED (docs/data/correlations.json sgp_rho register, Build B)",
                "sigma_status": f"sqrt(season_avg) * {OVERDISPERSION} overdispersion (documented assumption)",
                "gates": "G-PROP BLOCKED (no market number, no game-log variance); no price claimed",
                "status": STATUS,
                "sources": [g["schedule_source"],
                            game_players[0]["source_url"] if game_players else g["inputs_source"]],
                "as_of": g["inputs_as_of"],
            })
    # keep the 2 highest joint-probability candidates per date
    sgp.sort(key=lambda x: (x["date"], -x["joint_prob_rho"]))
    kept, seen = [], {}
    for r in sgp:
        if seen.get(r["date"], 0) < 2:
            kept.append(r)
            seen[r["date"]] = seen.get(r["date"], 0) + 1

    payload = {
        "_meta": {
            "title": "Horizon picks — 2026-11-14 through 2026-11-17",
            "generated_by": "scripts/generate_picks.py",
            "generated_utc": "2026-11-14",
            "lines_source": "data/derived/horizon_lines.json (scripts/originate_horizon.py)",
            "pick_gate": {"margin": PICK_GATE_MARGIN,
                          "inherited_from": "data/originated_lines.json assumptions",
                          "source_url": PICK_GATE_SOURCE},
            "validation_state": ("NO strategy has passed the validation gates (Build A 0/8, "
                                 "Build B 0/10). Every pick is MODEL OUTPUT — UNVALIDATED, "
                                 "unfunded, zero stake. Market-comparison gates G4/G5 and "
                                 "prop-variance gate G-PROP remain BLOCKED (no odds feed)."),
            "as_of": ("ratings through 2026-11-12; records pre-11/13; latest injury report "
                      "11/13 05:15 PM ET. 11/13 finals were not yet final at build time."),
        },
        "singles": singles,
        "parlays": parlays,
        "sgp_candidates": kept,
        "n_model_picks": n_single_picks,
    }
    out = os.path.join(DATA, "derived", "horizon_picks.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    print(f"picks written -> {os.path.relpath(out, ROOT)}")
    print(f"  singles: {len(singles)} games, {n_single_picks} picks (gate {PICK_GATE_MARGIN})")
    print(f"  parlays: {len(parlays)}   sgp candidates: {len(kept)}")
    assert n_single_picks == payload["n_model_picks"]
    for s in singles:
        if s["pick"]["pick_side"] != "PASS":
            print(f"  {s['date']} {s['matchup']:8} {s['pick']['pick_line']:12} "
                  f"p={s['pick']['pick_prob']:.3f}")


if __name__ == "__main__":
    main()
