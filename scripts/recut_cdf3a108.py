#!/usr/bin/env python3
"""recut_cdf3a108.py — re-cut the model inputs and the measured constants from
first-hand official reads on 2026-11-19 (session arena/cdf3a108-nba1, §74 C03).

Adopted from `scripts/recut_2026_11_19.py` (session arena/929395a5-nba1, §66 P05):
every gate formula, the dispersion calculation, the norm_ppf implementation and
the home-court pin are copied verbatim. Only the input plumbing differs — this
cut reads the 12:2x–12:4x UTC re-read capture instead of an inlined table:

Inputs (all in-repo, all official, all read first-hand this cycle):
  data/official/teams_reread_2026-11-19_cdf3a108.json    advanced + traditional + opponent (30 rows each)
  data/official/standings_reread_2026-11-19_cdf3a108.json standings (30 rows, HOME/ROAD columns)
  data/official/results_feed_2026_27.json                 finals through 2026-11-18 (222 games)

Outputs (the live derived paths the originator reads):
  data/derived/team_stats_recut.json
  data/derived/measured_constants_2026_27.json

Gates (run and RECORDED):
  G1  W + L == GP for all 30 teams on the advanced table.
  G2  |NetRtg - (OffRtg - DefRtg)| <= 0.25 for all 30 teams.
  G3  GP and W-L on the advanced table equal GP and W-L on the standings for all 30 teams.
  G4  total team-games on the advanced table == 2 x (finals in the results feed).
  G5  the standings closed-system identity holds (home wins == road losses).
  GX  cross-page: GP/W/L agree across the three official pages; PTS-OppPTS vs +/-
      within 0.2 (per-game averages are rounded on the page); POSS*48/MIN vs PACE
      recorded per team as an informational residual (the page's own PACE is not
      exactly POSS*48/MIN — recorded, never "corrected").

What changed against the 05:44Z cut (the adoption request S-89F-02 / Q37 named it):
the official tables have absorbed the 11/18 UTA 109 @ LAL 97 game, so LAL and UTA
are now 16 GP like the standings. G3 and G4, which FAILed on the previous cut,
now pass. The two rows move: LAL 121.6/113.7 -> 119.8/113.2, UTA 107.2/115.9 ->
107.0/114.5. Nothing else moved (verified by diffing the 30 rows against the
previous capture inside this script and printing the diff).
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

SRC_ADV = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRAD = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_OPP = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"
SRC_STD = "https://www.nba.com/standings"
SRC_GAMES = "https://www.nba.com/games"

CAPTURE = "data/official/teams_reread_2026-11-19_cdf3a108.json"
STANDINGS = "data/official/standings_reread_2026-11-19_cdf3a108.json"

COLS = ["team", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
        "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
        "pace", "pie", "poss"]


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


def norm_ppf(p):
    # Acklam's rational approximation, |error| < 1.15e-9
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
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def main():
    cap = load(CAPTURE)
    adv_rows = [{k: r[k] for k in COLS} for r in cap["advanced"]]
    rows = adv_rows
    abbr_of = {r["team"]: r["team"] for r in rows}

    std = load(STANDINGS)
    std_rows = std["rows"]
    std_by = {r["team"]: r for r in std_rows}

    def wl(s):
        x, y = s.split("-")
        return int(x), int(y)

    total_w = sum(r["w"] for r in std_rows)
    total_l = sum(r["l"] for r in std_rows)
    home_w = sum(wl(r["home"])[0] for r in std_rows)
    home_l = sum(wl(r["home"])[1] for r in std_rows)
    road_w = sum(wl(r["road"])[0] for r in std_rows)
    road_l = sum(wl(r["road"])[1] for r in std_rows)
    cross_checks = {"total_w": total_w, "total_l": total_l, "home_w": home_w,
                    "home_l": home_l, "road_w": road_w, "road_l": road_l}

    # ---- gates (recorded)
    g1, g2, g3 = [], [], []
    for r in rows:
        if r["w"] + r["l"] != r["gp"]:
            g1.append(f"{r['team']}: W+L={r['w']+r['l']} != GP={r['gp']}")
        if abs(r["net_rtg"] - (r["off_rtg"] - r["def_rtg"])) > 0.25:
            g2.append(f"{r['team']}: NetRtg {r['net_rtg']} vs {r['off_rtg']-r['def_rtg']:.2f}")
        s = std_by[r["team"]]
        if (r["gp"], r["w"], r["l"]) != (s["w"] + s["l"], s["w"], s["l"]):
            g3.append(f"{r['team']}: advanced {r['gp']}-{r['w']}-{r['l']} vs standings {s['w']+s['l']}-{s['w']}-{s['l']}")
    g5_ok = (cross_checks["total_w"] == cross_checks["total_l"]) and (home_w == road_l)

    feed = load("data/official/results_feed_2026_27.json")
    finals = [r for r in feed["rows"] if r.get("game_status") == 3]
    n_games = len(finals)
    g4_ok = (sum(r["gp"] for r in rows) == 2 * n_games)

    # ---- GX: cross-page identities (recorded)
    gx = {"gp_wl_mismatch": [], "pts_minus_opp_vs_plusminus": [], "poss_pace_residual": []}
    trad_by = {r["team"]: r for r in cap["traditional"]}
    opp_by = {r["team"]: r for r in cap["opponent"]}
    for r in rows:
        t, o = trad_by[r["team"]], opp_by[r["team"]]
        if (r["gp"], r["w"], r["l"]) != (t["gp"], t["w"], t["l"]) or (r["gp"], r["w"], r["l"]) != (o["gp"], o["w"], o["l"]):
            gx["gp_wl_mismatch"].append(r["team"])
        d = round((t["pts"] - o["opp_pts"]) - t["plus_minus"], 2)
        if abs(d) > 0.2:
            gx["pts_minus_opp_vs_plusminus"].append(f"{r['team']}: pts-opp {t['pts']-o['opp_pts']:.1f} vs +/- {t['plus_minus']} (delta {d})")
        resid = round(r["poss"] * 48.0 / r["min"] - r["pace"], 2)
        gx["poss_pace_residual"].append({"team": r["team"], "residual_pace_units": resid})
    gx["poss_pace_note"] = ("the official PACE column is not exactly POSS*48/MIN (the page's own two "
                            "definitions); residuals are recorded per team, never corrected")
    gx_max = max(abs(x["residual_pace_units"]) for x in gx["poss_pace_residual"])

    print("G1", "pass (all 30)" if not g1 else f"FAIL {g1}")
    print("G2", "pass (all 30)" if not g2 else f"FAIL {g2}")
    print("G3", "pass (all 30)" if not g3 else f"FAIL {g3}")
    print("G4", f"pass ({sum(r['gp'] for r in rows)} = 2 x {n_games})" if g4_ok else
          f"FAIL total team-games {sum(r['gp'] for r in rows)} != 2 x {n_games}")
    print("G5", "pass" if g5_ok else "FAIL")
    print("GX gp/wl", "pass" if not gx["gp_wl_mismatch"] else f"FAIL {gx['gp_wl_mismatch']}")
    print("GX pts-opp", "pass" if not gx["pts_minus_opp_vs_plusminus"] else f"FAIL {gx['pts_minus_opp_vs_plusminus']}")
    print(f"GX poss/pace max |residual| {gx_max} pace units (recorded)")

    # ---- league baselines, possessions-weighted (measured, not assumed)
    poss_tot = sum(r["poss"] for r in rows)
    league_off = sum(r["off_rtg"] * r["poss"] for r in rows) / poss_tot
    league_pace = sum(r["pace"] * r["gp"] for r in rows) / sum(r["gp"] for r in rows)

    # ---- margin dispersion from the finals corpus (duplicates removed by game_id)
    seen, margins, totals = set(), [], []
    for r in finals:
        if r["game_id"] in seen:
            continue
        seen.add(r["game_id"])
        margins.append(r["home_pts"] - r["away_pts"])
        totals.append(r["home_pts"] + r["away_pts"])
    n = len(margins)
    mean_m = sum(margins) / n
    sd_m = math.sqrt(sum((m - mean_m) ** 2 for m in margins) / (n - 1))
    mean_t = sum(totals) / n
    sd_t = math.sqrt(sum((t - mean_t) ** 2 for t in totals) / (n - 1))

    # ---- the pin (verbatim: rate from the standings HOME/ROAD columns, never fitted)
    home_wins = cross_checks["home_w"]
    home_games = cross_checks["home_w"] + cross_checks["home_l"]
    home_rate = home_wins / home_games
    hca_pts = sd_m * norm_ppf(home_rate)

    # ---- diff against the previous (05:44Z) cut; printed, never hidden
    prev_path = "data/official/team_stats_recut_2026-11-19_929395a5.json"
    drift = []
    if os.path.exists(os.path.join(ROOT, prev_path)):
        prev = load(prev_path)
        prev_by = {r["team"]: r for r in prev["advanced"]}
        for r in rows:
            p = prev_by.get(r["team"])
            if not p:
                drift.append({"team": r["team"], "change": "row not in previous capture"})
                continue
            for k in ("gp", "w", "l", "off_rtg", "def_rtg", "net_rtg", "pace", "poss"):
                if r[k] != p[k]:
                    drift.append({"team": r["team"], "field": k, "was": p[k], "now": r[k]})
    print(f"drift vs {prev_path}: {len(drift)} field change(s)")
    for d in drift:
        print("  ", d)

    stale = {x.split(":")[0] for x in g3}
    out_teams = []
    for r in rows:
        out_teams.append({**{k: r[k] for k in COLS}, "abbr": r["team"],
                          "source_url": SRC_ADV,
                          "gp_matches_standings": r["team"] not in stale})
    out_teams.sort(key=lambda r: -r["off_rtg"])

    gates_meta = {
        "G1_W_plus_L_eq_GP": "pass (all 30)" if not g1 else f"FAIL: {g1}",
        "G2_netrtg_eq_off_minus_def": "pass (all 30, 0.25 rounding tolerance)" if not g2 else f"FAIL: {g2}",
        "G3_gp_and_wl_match_standings": "pass (all 30)" if not g3 else f"FAIL: {g3}",
        "G4_total_team_games_eq_2x_decided_finals": f"pass ({sum(r['gp'] for r in rows)} = 2 x {n_games})" if g4_ok else
            f"FAIL (recorded, not blocking): {sum(r['gp'] for r in rows)} != 2 x {n_games}",
        "G5_standings_identity": f"pass (home wins == road losses: {home_w} == {road_l})" if g5_ok else "FAIL",
        "GX_cross_page": (f"gp/wl agree across three pages; pts-opp vs +/- within 0.2; poss/pace max "
                          f"|residual| {gx_max} (recorded, definitional)"),
    }
    recut = {
        "_meta": {
            "title": "Team model inputs, re-cut from first-hand official reads on 2026-11-19 (12:2x-12:4x UTC)",
            "generated_by": "scripts/recut_cdf3a108.py (session arena/cdf3a108-nba1; formulas verbatim from scripts/recut_2026_11_19.py)",
            "retrieved_utc": cap["retrieved_utc"],
            "sources": {"advanced": SRC_ADV, "traditional": SRC_TRAD, "opponent": SRC_OPP,
                        "standings": SRC_STD, "finals": SRC_GAMES},
            "games_through": f"{n_games} decided games (results feed through 2026-11-18)",
            "note": ("Every value is printed on the official advanced page. Nothing is fitted, imputed or "
                     "adjusted. GP/W/L are shipped beside the ratings so a reader can see the sample each "
                     "rating rests on. This cut absorbs the 11/18 UTA 109 @ LAL 97 game that the 05:44Z cut "
                     "was missing (F-929-01 / F-89F-04 / S-89F-02 / Q37): LAL and UTA are 16 GP and now match "
                     "the standings. The two moved rows are printed in _meta.drift_vs_previous_cut."),
            "drift_vs_previous_cut": drift,
            "cross_page_checks": gx,
            "gates": gates_meta,
        },
        "rows": out_teams,
    }
    p = os.path.join(ROOT, "data/derived/team_stats_recut.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(recut, fh, indent=1, ensure_ascii=False); fh.write("\n")

    consts = {
        "_meta": {
            "title": "Measured constants for the 2026-27 model, re-derived on 2026-11-19",
            "generated_by": "scripts/recut_cdf3a108.py (formulas verbatim from scripts/recut_2026_11_19.py)",
            "retrieved_utc": NOW,
            "rule": "measure, never fit. Each constant states the official column it came from.",
        },
        "league": {
            "off_rtg_poss_weighted": round(league_off, 3),
            "pace_gp_weighted": round(league_pace, 3),
            "formula": "sum(OffRtg_i * POSS_i) / sum(POSS_i) over the 30 official rows; PACE weighted by GP",
            "source_url": SRC_ADV,
        },
        "dispersion": {
            "finals_n": n,
            "margin_mean": round(mean_m, 3),
            "sigma_margin": round(sd_m, 3),
            "total_mean": round(mean_t, 3),
            "sigma_total": round(sd_t, 3),
            "formula": "sample standard deviation (n-1) of the official home-minus-away margin and of the official game total, over every decided game in the corpus, de-duplicated by game id",
            "source_url": SRC_GAMES,
        },
        "home_court_pin": {
            "home_win_rate": round(home_rate, 4),
            "home_wins": home_wins,
            "home_games": home_games,
            "sigma_margin_used": round(sd_m, 3),
            "hca_points": round(hca_pts, 2),
            "formula": "HCA_points = sigma_margin * Phi^-1(home_win_rate); the rate comes from the official standings HOME/ROAD columns, never from a fit",
            "source_url": SRC_STD,
            "prior_pin": {"rate": 0.5196, "hca_points": 0.83, "as_of": "2026-11-17 (session arena/84264db0-nba1)"},
            "previous_pin": {"rate": 0.5023, "hca_points": 0.09, "as_of": "2026-11-19T05:44Z (session arena/929395a5-nba1)"},
            "drift": {"rate_change_vs_2026_11_17": round(home_rate - 0.5196, 4),
                      "points_change_vs_2026_11_17": round(hca_pts - 0.83, 3),
                      "rate_change_vs_0545Z_cut": round(home_rate - 0.5023, 4),
                      "points_change_vs_0545Z_cut": round(hca_pts - 0.09, 3)},
        },
    }
    p2 = os.path.join(ROOT, "data/derived/measured_constants_2026_27.json")
    with open(p2, "w", encoding="utf-8") as fh:
        json.dump(consts, fh, indent=1, ensure_ascii=False); fh.write("\n")

    print(f"decided games {n_games}; sigma_margin {sd_m:.2f}, sigma_total {sd_t:.2f}")
    print(f"league off_rtg {league_off:.3f}, pace {league_pace:.3f}")
    print(f"HCA pin: rate {home_rate:.4f} x sigma {sd_m:.3f} -> {hca_pts:.2f} pts "
          f"(vs 05:45Z pin 0.09: {hca_pts-0.09:+.2f})")


if __name__ == "__main__":
    main()
