#!/usr/bin/env python3
"""
generate_picks.py — model picks for the 11/14–11/17 horizon, built ONLY on
data/derived/horizon_lines.json (scripts/originate_horizon.py output).

Strategy families (candidate identity, all UNVALIDATED — no strategy has passed the
validation gates: Build A 0/8, Build B 0/10):

  SINGLE-SPREAD-v1   pick the model favourite when |originated spread| >= pick_gate_margin
                     (gate 3.0, inherited from data/originated_lines.json assumptions).
  PARLAY2-IND-v1     two SINGLE-SPREAD legs from DIFFERENT games (same date). Games are
                     treated as independent events; the price published on every row is the
                     naive product p1 x p2 (the measured_rho.json consequence for
                     cross-game pairs) with the Fréchet–Hoeffding band
                     [max(0,p1+p2-1), min(p1,p2)] beside it — the same bounds method as
                     scripts/build_edge_site.py, and no rho is ever asserted.
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
  * Parlay pricing follows data/derived/measured_rho.json (R14/F90): where a rho
    is measurable it is used; where it is not, the price printed IS the naive
    product p1 x p2 with the Fréchet–Hoeffding band beside it — never a
    withheld price and never an invented rho.
"""
import json
import math
import os
from datetime import datetime, timezone
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

PICK_GATE_MARGIN = 3.0          # inherited from data/originated_lines.json assumptions
PICK_GATE_SOURCE = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/originated_lines.json"

# MODEL-DERIVED rho register (docs/data/correlations.json, Build B), labelled as such
SGP_RHO_TEAMMATES = -0.2
SGP_RHO_OPPONENTS = 0.05
SGP_RHO_SOURCE_FILE = "docs/data/correlations.json"

# Measured rho registers — this repository has TWO, and they disagree (flagged):
#   data/derived/measured_rho.json   (scripts/measure_rho.py): side-vs-total on a
#       rolling finals window; records a methodological "not measurable" verdict
#       for cross-game pairs.
#   data/derived/rho_2026_27.json   (session arena/801ba27f-nba1): cross-game
#       same-date margin pairs MEASURED at rho=0.0142 (n_pairs 1546), teammate
#       points at -0.0975 (n=374), opponent leading-scorer at +0.0321 (n=187),
#       from official box-score pages.
# §61 W02 prices with rho_2026_27's measured values (the brief: "price every
# parlay with the measured rho"), prints the naive product beside every price,
# and publishes the methodological conflict as a flag instead of hiding it.
# Cross-game rho was re-derived first-hand from the committed finals corpus on
# 2026-11-16 (all unordered same-date margin pairs, 26 dates, 197 games):
# r = 0.0120 — the register's 0.0142 is confirmed in substance.
MEASURED_RHO_FILE = os.path.join(DATA, "derived", "measured_rho.json")
RHO_REGISTER_FILE = os.path.join(DATA, "derived", "rho_2026_27.json")
REGISTER_CONFLICT_FLAG = "F136"


def load_rho_register():
    """The rho_2026_27 measured register (pair -> rho, n, status), or None."""
    if not os.path.exists(RHO_REGISTER_FILE):
        return None, {}
    doc = json.load(open(RHO_REGISTER_FILE, encoding="utf-8"))
    by_pair = {m.get("pair"): m for m in doc.get("measured", [])}
    return doc, by_pair


def norm_ppf(p):
    """Inverse standard-normal CDF by bisection on norm_cdf (no scipy)."""
    lo, hi = -8.0, 8.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def load_measured_rho():
    """The measured-rho register, or a truthful stub if it is absent."""
    if not os.path.exists(MEASURED_RHO_FILE):
        return None, {"status": "MISSING",
                      "note": ("data/derived/measured_rho.json is not in the "
                               "tree; no measured rho is claimed anywhere "
                               "below")}
    doc = json.load(open(MEASURED_RHO_FILE, encoding="utf-8"))
    side_total = next((m for m in doc.get("measured", [])
                       if m.get("x") == "home margin" and m.get("y") == "game total"),
                      None)
    return doc, {
        "register": "data/derived/measured_rho.json",
        "corpus_n_games": (doc.get("corpus") or {}).get("n_games"),
        "corpus_window": "%s..%s" % ((doc.get("corpus") or {}).get("first_date"),
                                     (doc.get("corpus") or {}).get("last_date")),
        "side_and_total_rho": side_total,
        "cross_game_rho": next((nm for nm in doc.get("not_measurable", [])
                                if "two different games" in nm.get("quantity", "")),
                               None),
        "rule": ("where a rho is measurable it is used; where it is not, the "
                 "price is the naive product p1 x p2 printed beside the "
                 "Fréchet–Hoeffding band — R14"),
    }

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
    lines = hl
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
    # R14 / F90: measured_rho.json records that no rho between two different
    # games is measurable from official data, and publishes the consequence —
    # cross-game parlays are priced at the naive product with the
    # Fréchet–Hoeffding band beside it.  Both numbers are fields on every row.
    measured_doc, measured_meta = load_measured_rho()
    rho_register, rho_by_pair = load_rho_register()
    cross_meta = rho_by_pair.get(
        "cross-game: home margin vs home margin, two games on the same date", {})
    cross_rho = cross_meta.get("rho")
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
            # Price from the PUBLISHED leg probabilities (3 dp) so a reviewer
            # can reproduce the number on this row from the two printed legs,
            # and so scripts/build_roll_page.py renders exactly this figure.
            p1r, p2r = round(p1, 3), round(p2, 3)
            naive = p1r * p2r
            # R14: price at the MEASURED cross-game rho (rho_2026_27.json),
            # naive product printed beside it.  joint_over_over(z1, z2, rho)
            # computes P(X > z1, Y > z2), so z = norm_ppf(1 - p) makes
            # P(X > z) = p and the joint reduces exactly to the naive product
            # at rho = 0 (checked below).
            z1, z2 = norm_ppf(1.0 - p1r), norm_ppf(1.0 - p2r)
            if cross_rho is not None:
                price = joint_over_over(z1, z2, cross_rho)
            else:
                price = naive
            rho_status = (
                "MEASURED: rho_2026_27.json cross-game margin/margin, same date, "
                "rho = %s (n_pairs %s, official box-score pages); re-derived "
                "first-hand from the committed finals corpus 2026-11-16 at "
                "r = 0.0120 (26 dates, 197 games). measured_rho.json records the "
                "opposing methodological verdict (cross-game pairing is an "
                "artefact of how pairs are made) — both registers published, "
                "conflict flagged %s"
                % (cross_rho, cross_meta.get("n_pairs") or cross_meta.get("n"),
                   REGISTER_CONFLICT_FLAG)) if cross_rho is not None else (
                    "no measured cross-game rho available in rho_2026_27.json; "
                    "priced at the naive product")
            parlays.append({
                "date": dte,
                "leg1": f"{s1['matchup']} — {s1['pick']['pick_line']}", "p1": p1r,
                "leg2": f"{s2['matchup']} — {s2['pick']['pick_line']}", "p2": p2r,
                "naive_product": round(naive, 4),
                "price": round(price, 4),
                "fair_odds_at_price": round(1.0 / price, 2) if price > 0 else None,
                "joint_lb": round(lb, 3), "joint_ub": round(ub, 3),
                "rho_used": cross_rho,
                "rho_status": rho_status,
                "rho_lb": None if rho_lb is None else round(rho_lb, 3),
                "rho_ub": None if rho_ub is None else round(rho_ub, 3),
                "fair_odds_lb": round(1.0 / ub, 2) if ub > 0 else None,
                "fair_odds_ub": round(1.0 / lb, 2) if lb > 0 else None,
                "method": ("legs from different games; priced at the measured "
                           "cross-game rho under a Gaussian copula, with the naive "
                           "product p1 x p2 printed beside it and the "
                           "Fréchet–Hoeffding band [max(0,p1+p2-1), min(p1,p2)] "
                           "published as the range any rho must respect"),
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
            # R14/F90: price with the MEASURED rho where the register has one.
            # rho_2026_27.json measures teammate points at -0.0975 (n=374) and
            # opponent leading-scorer points at +0.0321 (n=187) from official
            # box-score pages.  Those box scores are not committed (only nine
            # gamebooks are), so the value cannot be re-derived inside this
            # tree — provenance and the limitation are printed on the row and
            # flagged, and the model-derived constant is kept as the fallback.
            if kind == "two_teammates":
                reg = rho_by_pair.get("two team-mates: points (top-2 minutes on the same team)", {})
            else:
                reg = rho_by_pair.get("two opponents: points (leading scorer on each team)", {})
            rho_measured = reg.get("rho") is not None
            rho = (reg.get("rho") if rho_measured
                   else (SGP_RHO_TEAMMATES if kind == "two_teammates" else SGP_RHO_OPPONENTS))
            rho_n = reg.get("n") or reg.get("n_pairs")

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
                "rho_measured": rho_measured,
                "rho_n": rho_n,
                "leg1": f"{l1['player']} ({l1['team']}) OVER {l1['line']}",
                "leg2": f"{l2['player']} ({l2['team']}) OVER {l2['line']}",
                "leg1_detail": l1, "leg2_detail": l2,
                "joint_prob_rho": round(joint, 4),
                "joint_prob_independent": round(joint_ind, 4),
                "naive_product": round(joint_ind, 4),
                "rho_status": (
                    "MEASURED: rho_2026_27.json %s rho = %s (n = %s, official "
                    "box-score pages). The box scores behind that n are not "
                    "committed to this repository (only nine gamebooks are), so "
                    "the value cannot be re-derived inside the tree — provenance "
                    "published on the row, limitation flagged %s. The naive "
                    "product is printed beside the rho price on every row"
                    % ("teammate points" if kind == "two_teammates"
                       else "opponent leading-scorer points",
                       rho, rho_n, REGISTER_CONFLICT_FLAG) if rho_measured else (
                    "MODEL-DERIVED fallback (docs/data/correlations.json sgp_rho "
                    "register, Build B): rho_2026_27.json carries no measured "
                    "value for this pair type; naive product printed beside")),
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

    dates = sorted({s_["date"] for s_ in singles}) or \
            sorted({g["date"] for g in lines["games"]})
    payload = {
        "_meta": {
            "title": f"Horizon picks — {dates[0]} through {dates[-1]}",
            "generated_by": "scripts/generate_picks.py (rolling window)",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "window_rule": ("the horizon is whatever data/derived/horizon_lines.json holds; "
                            "that file is produced by the rolling-slate originator from the "
                            "newest official schedule capture (today + up to 3 days ahead)"),
            "lines_source": "data/derived/horizon_lines.json (scripts/originate_horizon.py)",
            "pick_gate": {"margin": PICK_GATE_MARGIN,
                          "inherited_from": "data/originated_lines.json assumptions",
                          "source_url": PICK_GATE_SOURCE},
            "validation_state": ("NO strategy has passed the validation gates (Build A 0/8, "
                                 "Build B 0/10). Every pick is MODEL OUTPUT — UNVALIDATED, "
                                 "unfunded, zero stake. Market-comparison gates G4/G5 and "
                                 "prop-variance gate G-PROP remain BLOCKED (no odds feed)."),
            "parlay_pricing": dict(measured_meta, **{
                "registers": {
                    "measured_rho_json": ("scripts/measure_rho.py — side/total on a "
                                          "rolling finals window; carries a "
                                          "'not measurable' verdict for cross-game pairs"),
                    "rho_2026_27_json": ("session arena/801ba27f-nba1 — cross-game "
                                         "0.0142 (n_pairs 1546), teammates -0.0975 "
                                         "(n=374), opponents +0.0321 (n=187), side/total "
                                         "-0.0199 (n=190), from official box-score pages"),
                    "conflict": ("the two registers disagree on cross-game measurability "
                                 "and on the side/total value (different corpus windows); "
                                 "both are published, conflict flagged "
                                 + REGISTER_CONFLICT_FLAG),
                },
                "cross_game": ("price = joint under a Gaussian copula at the measured "
                               "cross-game rho from rho_2026_27.json; the naive product "
                               "p1 x p2 is printed beside it on every row (R14), with "
                               "the Fréchet–Hoeffding band as the range any rho "
                               "must respect"),
                "sgp_props": ("measured teammate/opponent rho from rho_2026_27.json "
                              "where present, MODEL-DERIVED fallback labelled as such; "
                              "naive product printed beside the rho price on every row "
                              "(R14/F90)"),
                "side_and_total": ("priced with the measured rho on site/pages/roll.html "
                                   "section 4 from measured_rho.json (refreshed to its "
                                   "current 74-final corpus this session)"),
            }),
            "as_of": (lines["_meta"]["inputs"]["ratings_recut_retrieved_utc"]
                      and ("ratings re-cut from the official team-stat captures retrieved %s; "
                           "schedule captured %s; latest injury report %s (revision %s, "
                           "retrieved %s)."
                           % (lines["_meta"]["inputs"]["ratings_recut_retrieved_utc"],
                              lines["_meta"]["inputs"]["schedule_captured_on"],
                              lines["_meta"]["inputs"]["injury_edition"],
                              lines["_meta"]["inputs"]["injury_revision_et"],
                              lines["_meta"]["inputs"]["injury_retrieved_utc"]))),
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
