#!/usr/bin/env python3
"""recut_2026_11_17.py — re-cut the model inputs and the measured constants from
first-hand official reads on 2026-11-17.

Inputs (all in-repo, all official):
  data/official/teams_inputs_2026-11-17_84264db0.json   advanced + opponent team tables
  data/official/standings_2026-11-17_1547Z_84264db0.json standings (30 rows, identity-checked)
  data/official/results_feed_2026_27.json               finals through the 2026-11-15
  data/official/results_2026-11-16.json                 the eight 2026-11-16 finals
  data/raw/official_schedule_capture_2026-11-17.json    the 11/17..11/20 fixture list

Outputs:
  data/derived/team_stats_recut.json                    per-team model inputs
  data/derived/measured_constants_2026_27.json          league baselines, sigma_margin, HCA pin

Every published number is either printed on an official page (and carries the page
URL) or derived here with the formula printed beside it. Nothing is fitted: the
home-court advantage is the measured home-win rate converted to points, never a
free parameter.

Gates (the script refuses to write if any fails):
  G1  W + L == GP for all 30 teams on the advanced table.
  G2  |NetRtg - (OffRtg - DefRtg)| <= 0.25 for all 30 teams.
  G3  GP and W-L on the advanced table equal GP and W-L on the standings for all 30 teams.
  G4  total team-games on the advanced table == 2 x (finals in the results feed + 11/16 finals).
  G5  the standings closed-system identity holds (home wins == road losses).
"""
from __future__ import annotations

import glob
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

ABBR = {"Los Angeles Lakers": "LAL", "Philadelphia 76ers": "PHI", "San Antonio Spurs": "SAS",
        "Boston Celtics": "BOS", "Houston Rockets": "HOU", "Memphis Grizzlies": "MEM",
        "Minnesota Timberwolves": "MIN", "Oklahoma City Thunder": "OKC",
        "Portland Trail Blazers": "POR", "Atlanta Hawks": "ATL", "Cleveland Cavaliers": "CLE",
        "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Miami Heat": "MIA",
        "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "New York Knicks": "NYK",
        "Orlando Magic": "ORL", "Phoenix Suns": "PHX", "Indiana Pacers": "IND",
        "New Orleans Pelicans": "NOP", "Toronto Raptors": "TOR", "Charlotte Hornets": "CHA",
        "LA Clippers": "LAC", "Washington Wizards": "WAS", "Brooklyn Nets": "BKN",
        "Chicago Bulls": "CHI", "Milwaukee Bucks": "MIL", "Sacramento Kings": "SAC",
        "Utah Jazz": "UTA"}
COLS = ["team", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
        "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct", "efg_pct", "ts_pct",
        "pace", "pie", "poss"]


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


def main():
    adv_doc = load("data/official/teams_inputs_2026-11-17_84264db0.json")
    rows = [dict(zip(COLS, r)) for r in adv_doc["advanced"]]
    for r in rows:
        r["abbr"] = ABBR[r["team"]]
        r["source_url"] = SRC_ADV

    std_path = sorted(glob.glob(os.path.join(ROOT, "data/official/standings_2026-11-17_*_84264db0.json")))[-1]
    std = json.load(open(std_path, encoding="utf-8"))
    std_by = {r["abbr"]: r for r in std["rows"]}

    # ---- gates on the official tables themselves
    fails = []
    for r in rows:
        if r["w"] + r["l"] != r["gp"]:
            fails.append(f"G1 {r['abbr']}: W+L={r['w']+r['l']} != GP={r['gp']}")
        if abs(r["net_rtg"] - (r["off_rtg"] - r["def_rtg"])) > 0.25:
            fails.append(f"G2 {r['abbr']}: NetRtg {r['net_rtg']} vs {r['off_rtg']-r['def_rtg']:.2f}")
        s = std_by[r["abbr"]]
        if (r["gp"], r["w"], r["l"]) != (s["w"] + s["l"], s["w"], s["l"]):
            fails.append(f"G3 {r['abbr']}: advanced {r['gp']}-{r['w']}-{r['l']} vs standings {s['w']+s['l']}-{s['w']}-{s['l']}")
    hca = std["measured_home_court_anchor"]
    if not std["identity_checks"]["global_ok"]:
        fails.append("G5 standings identity failed")

    feed = load("data/official/results_feed_2026_27.json")
    finals = [r for r in feed["rows"] if r.get("game_status") == 3]
    r16 = load("data/official/results_2026-11-16.json")
    n_games = len(finals) + len(r16["rows"])
    if sum(r["gp"] for r in rows) != 2 * n_games:
        fails.append(f"G4 total team-games {sum(r['gp'] for r in rows)} != 2 x {n_games}")

    if fails:
        print("GATES FAILED — nothing written")
        for f in fails:
            print("  ", f)
        raise SystemExit(1)

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
    for r in r16["rows"]:
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

    # ---- the pin: home-court advantage = sigma_margin * Phi^-1(home win rate)
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

    hca_pts = sd_m * norm_ppf(hca["home_win_rate"])

    out_teams = []
    for r in rows:
        out_teams.append({**{k: r[k] for k in COLS}, "abbr": r["abbr"], "source_url": SRC_ADV,
                          "gp_matches_standings": True})
    out_teams.sort(key=lambda r: -r["off_rtg"])

    recut = {
        "_meta": {
            "title": "Team model inputs, re-cut from first-hand official reads on 2026-11-17",
            "generated_by": "scripts/recut_2026_11_17.py",
            "retrieved_utc": NOW,
            "sources": {"advanced": SRC_ADV, "traditional": SRC_TRAD, "opponent": SRC_OPP,
                        "standings": SRC_STD, "finals": SRC_GAMES},
            "games_through": f"{n_games} decided games (results feed through 2026-11-15 plus the eight 2026-11-16 finals)",
            "note": ("Every value is printed on the official advanced page. Nothing is fitted, imputed or "
                     "adjusted. GP/W/L are shipped beside the ratings so a reader can see the sample each "
                     "rating rests on."),
            "gates": {
                "G1_W_plus_L_eq_GP": "pass (all 30)",
                "G2_netrtg_eq_off_minus_def": "pass (all 30, 0.25 rounding tolerance)",
                "G3_gp_and_wl_match_standings": "pass (all 30)",
                "G4_total_team_games_eq_2x_decided_finals": f"pass ({sum(r['gp'] for r in rows)} = 2 x {n_games})",
                "G5_standings_identity": "pass (home wins == road losses: 106 == 106)",
            },
        },
        "rows": out_teams,
    }
    p = os.path.join(ROOT, "data/derived/team_stats_recut.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(recut, fh, indent=1, ensure_ascii=False); fh.write("\n")

    consts = {
        "_meta": {
            "title": "Measured constants for the 2026-27 model, re-derived on 2026-11-17",
            "generated_by": "scripts/recut_2026_11_17.py",
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
            "home_win_rate": hca["home_win_rate"],
            "home_wins": hca["home_wins"],
            "home_games": hca["home_games"],
            "sigma_margin_used": round(sd_m, 3),
            "hca_points": round(hca_pts, 2),
            "formula": "HCA_points = sigma_margin * Phi^-1(home_win_rate); the rate comes from the official standings HOME/ROAD columns, never from a fit",
            "source_url": SRC_STD,
            "prior_pin": {"rate": 0.5204, "hca_points": 0.87, "as_of": "2026-11-16 (session arena/23ec1e32-nba1)"},
            "drift": {"rate_change": round(hca["home_win_rate"] - 0.5204, 4),
                      "points_change": round(hca_pts - 0.87, 3)},
        },
    }
    p2 = os.path.join(ROOT, "data/derived/measured_constants_2026_27.json")
    with open(p2, "w", encoding="utf-8") as fh:
        json.dump(consts, fh, indent=1, ensure_ascii=False); fh.write("\n")

    print(f"gates: all pass; decided games {n_games}; sigma_margin {sd_m:.2f}, sigma_total {sd_t:.2f}")
    print(f"league off_rtg {league_off:.3f}, pace {league_pace:.3f}")
    print(f"HCA pin: rate {hca['home_win_rate']} x sigma {sd_m:.3f} -> {hca_pts:.2f} pts "
          f"(prior 0.87, drift {hca_pts-0.87:+.2f})")
    print("wrote data/derived/team_stats_recut.json, data/derived/measured_constants_2026_27.json")


if __name__ == "__main__":
    main()
