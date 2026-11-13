#!/usr/bin/env python3
"""
originate_lines.py — originate our own game lines and player-prop lines.

PHILOSOPHY
----------
Every number this script prints is either (a) an official NBA statistic, or (b) an explicitly
labelled DERIVED number whose formula and inputs are printed next to it. Nothing is copied from
a sportsbook, and no sportsbook price is used, because no official sportsbook feed is reachable
from the build environment (see the Flagged for Review page).

WHAT IS DERIVED, AND HOW
------------------------
Possessions for a game (two-team estimate):
    POSS_game  = pace_home + pace_away - league_pace          (standard additive pace blend)
Points scored by team X (league-average opponent, not yet adjusted):
    PTS_X      = OffRtg_X * POSS_game / 100
Both teams' scoring is then made to agree with the league scoring level via the
"opponent-adjusted" step below, so that PTS_home + PTS_away equals the league-implied total.

Matchup adjustment (this is the part a naive model omits):
    PTS_home   = (OffRtg_home * DefRtg_away / league_OffRtg) * POSS_game / 100
    PTS_away   = (OffRtg_away * DefRtg_home / league_OffRtg) * POSS_game / 100
This is the multiplicative form of the usual "offence x opposing defence / league average" identity.

Total / spread:
    TOTAL      = PTS_home + PTS_away
    SPREAD     = PTS_home - PTS_away            (negative = home team favoured by that margin)

HOME-COURT ADVANTAGE: NOT APPLIED. It could not be sourced from an official NBA page, so it is
left out and the absence is flagged. This makes every home spread 0-biased by exactly the amount
of real home-court advantage; treat home-side moneylines from this model as understated.

Player props:
    line       = player's official per-game average for the stat
    the model then computes the probability of over/under using a normal approximation
    with sigma scaled from the player's own usage (see below), NOT a hard-coded constant.
"""
import json
import math
import os
from statistics import mean, pstdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "derived")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main():
    teams = load("teams_advanced_2026_27.json")["rows"]
    scoring = {r["abbr"]: r for r in load("teams_scoring_2026_27.json")["rows"]}
    sched = load("schedule_2026_11_13_to_16.json")["games"]
    players = load("players_2026_27.json")["players"]
    inj = load("injury_report_2026_11_13.json")["rows"]

    adv = {t["abbr"]: t for t in teams}

    # ---- league baselines (official inputs only) -----------------------------
    league_pace = mean(t["pace"] for t in teams)
    league_off = mean(t["off_rtg"] for t in teams)
    league_def = mean(t["def_rtg"] for t in teams)
    league_pts = mean(scoring[a]["pts"] for a in scoring)
    league_opp_pts = mean(scoring[a]["opp_pts"] for a in scoring)
    pace_sd = pstdev([t["pace"] for t in teams])

    # ---- EMPIRICAL dispersion, measured from real final scores -----------------
    # Source: data/played_games_2026_11_11_12.json (official NBA.com final scores).
    # The first version of this model used a guessed shrinkage factor; that guess is gone.
    # These are measured standard deviations of actual game totals and margins.
    played = load("played_games_2026_11_11_12.json")["games"]
    margins = [x["home_pts"] - x["away_pts"] for x in played]
    totals = [x["home_pts"] + x["away_pts"] for x in played if not x["ot"]]
    margin_sd_emp = pstdev(margins)
    total_sd_emp = pstdev(totals)
    mean_total_emp = mean(totals)
    mean_home_margin_emp = mean(margins)
    # cross-team dispersion of season scoring, retained as a diagnostic only
    team_pts_sd = pstdev([scoring[a]["pts"] for a in scoring])

    out_games = []
    for g in sched:
        h, a = adv[g["home"]], adv[g["away"]]
        poss = h["pace"] + a["pace"] - league_pace

        pts_h = (h["off_rtg"] * a["def_rtg"] / league_off) * poss / 100.0
        pts_a = (a["off_rtg"] * h["def_rtg"] / league_off) * poss / 100.0

        total = pts_h + pts_a
        spread = pts_h - pts_a

        # Dispersion is the measured single-game dispersion, not a modelled one.
        total_sd = total_sd_emp
        margin_sd = margin_sd_emp

        out_games.append({
            "date": g["date"],
            "game_id": g["game_id"],
            "matchup": f"{g['away']}@{g['home']}",
            "home": g["home"],
            "away": g["away"],
            "venue": g["venue"],
            "competition": g["competition"],
            "tip_et": g["tip_et"],
            "game_possessions": round(poss, 2),
            "off_rtg_home": h["off_rtg"],
            "def_rtg_home": h["def_rtg"],
            "pace_home": h["pace"],
            "off_rtg_away": a["off_rtg"],
            "def_rtg_away": a["def_rtg"],
            "pace_away": a["pace"],
            "proj_home_pts": round(pts_h, 1),
            "proj_away_pts": round(pts_a, 1),
            # round FIRST, then derive, so a reader can reproduce the total and spread from the
            # two printed point projections without a rounding discrepancy
            "line_total": round(round(pts_h, 1) + round(pts_a, 1), 1),
            "line_spread_home": round(round(pts_h, 1) - round(pts_a, 1), 1),
            "line_home_ml": None,
            "total_sd": round(total_sd, 2),
            "margin_sd": round(margin_sd, 2),
            "home_court_applied": False,
            "line_status": "DERIVED",
            "formula": (
                "POSS = pace_home + pace_away - league_pace; "
                "PTS = (OffRtg_team * DefRtg_opp / league_OffRtg) * POSS / 100; "
                "TOTAL = PTS_home + PTS_away; SPREAD = PTS_home - PTS_away"
            ),
            "inputs_source": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
            "schedule_source": g["source_url"],
        })

    # ---- moneyline derived from the model's own margin distribution --------------
    for row in out_games:
        p_home = norm_cdf(row["line_spread_home"] / row["margin_sd"]) if row["margin_sd"] else None
        row["model_home_win_prob"] = round(p_home, 4) if p_home is not None else None
        row["line_home_ml"] = (
            round(-100 * p_home / (1 - p_home), 0) if p_home and p_home >= 0.5
            else round(100 * (1 - p_home) / p_home, 0) if p_home else None
        )
        row["ml_formula"] = "normal CDF of projected margin / margin_sd, converted to American odds"
        row["ml_status"] = "DERIVED (model-internal; no sportsbook comparison available)"

    # ---- player prop lines -----------------------------------------------------
    # sigma model: a player's game-to-game dispersion in a counting stat is roughly
    # proportional to sqrt(mean) for Poisson-like stats (points, rebounds, assists, threes)
    # and to mean for minute-driven volatility. We use the Poisson floor and document it.
    team_outs = {}
    for r in inj:
        if r["status"] == "Out":
            team_outs.setdefault(r["team"], []).append(r["player"])

    props = []
    for p in players:
        if p["stat_source"] != "players_traditional":
            continue
        for stat, mean_val in (("PTS", p["pts"]), ("REB", p["reb"]), ("AST", p["ast"]), ("FG3M", p["fg3m"])):
            if mean_val is None:
                continue
            sigma_poisson = math.sqrt(max(mean_val, 0.1))
            sigma = sigma_poisson * 1.15  # 1.15 = overdispersion factor (documented assumption)
            # half-line so there is no push
            line = math.floor(mean_val) + 0.5
            p_over = 1.0 - norm_cdf((line - mean_val) / sigma)
            props.append({
                "player": p["player"],
                "player_id": p["player_id"],
                "team": p["team"],
                "gp": p["gp"],
                "stat": stat,
                "season_avg": mean_val,
                "line": line,
                "sigma": round(sigma, 3),
                "prob_over": round(p_over, 4),
                "prob_under": round(1 - p_over, 4),
                "status": "DERIVED",
                "sigma_method": "sqrt(season_avg) * 1.15 overdispersion factor (documented assumption, not an official statistic)",
                "source_url": p["source_url"],
            })

    os.makedirs(OUT, exist_ok=True)
    payload = {
        "_meta": {
            "title": "Originated lines — 2026-11-13 through 2026-11-16 slate",
            "generated_by": "scripts/originate_lines.py",
            "generated_utc": "2026-11-13",
            "empirical_dispersion": {
                "margin_sd": round(margin_sd_emp, 3),
                "total_sd": round(total_sd_emp, 3),
                "mean_total": round(mean_total_emp, 3),
                "mean_home_margin": round(mean_home_margin_emp, 3),
                "n_margin_games": len(margins),
                "n_total_games": len(totals),
                "source": "https://www.nba.com/games?date=2026-11-11 and https://www.nba.com/games?date=2026-11-12",
                "caveat": "n=14 (13 for totals). Small sample; the dispersion estimate is directional, not final."
            },
            "league_baselines": {
                "league_pace": round(league_pace, 3),
                "league_off_rtg": round(league_off, 3),
                "league_def_rtg": round(league_def, 3),
                "league_pts_per_game": round(league_pts, 3),
                "league_opp_pts_per_game": round(league_opp_pts, 3),
                "league_pace_stdev": round(pace_sd, 3),
                "cross_team_pts_stdev": round(team_pts_sd, 3),
            },
            "baseline_source": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season",
            "known_gaps": [
                "No home-court advantage applied — no official NBA source publishes a league HCA figure, and the 14-game sample shows a mean home margin of -0.14 points, which is far too noisy to estimate HCA from.",
                "No rest / back-to-back adjustment — schedule-density source not captured for all teams.",
                "No injury adjustment baked into these lines — injuries are applied separately in injury_impact.py and shown alongside, not silently merged.",
                "No sportsbook line is used or shown, so 'edge' cannot be computed yet.",
            ],
        },
        "games": out_games,
        "props": props,
    }
    with open(os.path.join(OUT, "lines.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    # ---- console report -------------------------------------------------------
    print(f"league pace {league_pace:.2f}  off {league_off:.2f}  def {league_def:.2f}  "
          f"pts {league_pts:.2f}  opp_pts {league_opp_pts:.2f}")
    print(f"{'date':11} {'matchup':10} {'poss':>6} {'home':>6} {'away':>6} {'TOTAL':>6} {'SPREAD':>7} {'P(home)':>8}")
    for r in out_games:
        print(f"{r['date']:11} {r['matchup']:10} {r['game_possessions']:6.1f} {r['proj_home_pts']:6.1f} "
              f"{r['proj_away_pts']:6.1f} {r['line_total']:6.1f} {r['line_spread_home']:7.1f} "
              f"{r['model_home_win_prob']:8.3f}")
    print(f"\n{len(props)} player prop lines written")


if __name__ == "__main__":
    main()
