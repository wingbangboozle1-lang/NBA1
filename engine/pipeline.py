"""Build every JSON file the site reads.

Run:  python3 engine/pipeline.py        (from the repo root)
Reads: data/raw/*.json  (official snapshots) + data/content/*.json (authored pages)
Writes: docs/data/*.json

No network access is used here - every number comes from a captured snapshot.
"""

import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (ABBR, OUT, RAW, TEAM_NAME, american_from_prob, mean,
                    norm_cdf, read_json, rnd, write_json)
from correlate import (measured_correlations, model_derived_correlations,
                       parlay_pricing_grid)
from injuries import Availability
from leaderboard import build as build_leaderboard
from model_core import (ASSUMPTIONS, RatingTable, game_flow, model_line,
                        project_player, reference_line)
from strategies import (SGP_RHO, STRATEGIES, build_plays, grade_play,
                        roi_units, summarise)
from validate import luck_table, run as run_backtest

CONTENT = os.path.join(os.path.dirname(RAW), "content")
GENERATED_AT = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_private(obj):
    """Drop helper keys that start with an underscore before serialising."""
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


def main():
    # ---------------------------------------------------------------- load
    adv = read_json(os.path.join(RAW, "team_advanced.json"))
    games_raw = read_json(os.path.join(RAW, "games_completed.json"))
    sched_raw = read_json(os.path.join(RAW, "schedule_upcoming.json"))
    inj_raw = read_json(os.path.join(RAW, "injuries.json"))
    pl_raw = read_json(os.path.join(RAW, "players_traditional.json"))
    sources = read_json(os.path.join(RAW, "sources.json"))

    train_block = [w for w in adv["windows"] if w["window_id"] == "train_2026-10-20_2026-11-05"][0]
    season_block = [w for w in adv["windows"] if w["window_id"] == "season_to_date"][0]
    train_rows = [dict(zip(adv["cols"], r)) for r in train_block["rows"]]
    season_rows = [dict(zip(adv["cols"], r)) for r in season_block["rows"]]
    completed = [dict(zip(games_raw["cols"], r)) for r in games_raw["rows"]]
    scheduled = [dict(zip(sched_raw["cols"], r)) for r in sched_raw["rows"]]
    injuries = [dict(zip(inj_raw["cols"], r)) for r in inj_raw["rows"]]
    players = [dict(zip(pl_raw["cols"], r)) for r in pl_raw["rows"]]

    # ------------------------------------------------------- backtest + params
    bt = run_backtest(train_rows, season_rows, completed,
                      train_block["source_id"], season_block["source_id"])
    season = bt["season"]
    params = bt["params"]
    sigma_m = params["sigma_margin"]
    sigma_t = params["sigma_total"]

    avail = Availability(injuries, players)

    # player status lookup: (date, team) -> normalised name -> status
    from injuries import _norm
    status_map = {}
    for r in injuries:
        ab = ABBR.get(r["team"])
        if not ab or not r["player"]:
            continue
        status_map.setdefault((r["game_date"], ab), {})[_norm(r["player"])] = r["status"]

    # ------------------------------------------------- rest / B2B for all games
    all_games = [{"date": g["date"], "home": g["home"], "away": g["away"]} for g in completed]
    all_games += [{"date": g["date"], "home": g["home"], "away": g["away"]} for g in scheduled]
    dates = sorted({g["date"] for g in all_games})
    last_by_date = {}
    for d in dates:
        prev = [x for x in dates if x < d]
        if not prev:
            last_by_date[d] = {}
            continue
        last = max(prev)
        last_by_date[d] = {g["home"]: last for g in all_games if g["date"] == last}
        last_by_date[d].update({g["away"]: last for g in all_games if g["date"] == last})

    def days_between(a, b):
        da = datetime.date(*[int(x) for x in a.split("-")])
        db = datetime.date(*[int(x) for x in b.split("-")])
        return (db - da).days

    def rest_for(date, team):
        last = last_by_date.get(date, {}).get(team)
        if not last:
            return 0, None, False
        dd = days_between(last, date)
        return (1 if dd == 1 else 0), dd, True

    league = {
        "L": season.L, "L_off": season.L_off, "L_def": season.L_def,
        "L_pace": season.L_pace,
        "L_dreb": mean([t["dreb_pct"] for t in season.teams.values()]),
    }

    # ------------------------------------------------------------ game contexts
    def build_ctx(date, away, home, time_et=None, venue=None, game_id=None,
                  actual_margin=None, actual_total=None, extra=None):
        hb, hrest, hk = rest_for(date, home)
        ab_, arest, ak = rest_for(date, away)
        matchup = f"{away}@{home}"
        rep_home, rep_away = {}, {}
        loss_home = loss_away = 0.0
        if date in {r["game_date"] for r in injuries}:
            loss_home, loss_away, rep_home, rep_away = avail.game_loss(date, matchup)
        ref = reference_line(season, home, away, flat_hca=2.0)
        ml = model_line(season, home, away, params,
                        loss_home=loss_home, loss_away=loss_away,
                        home_b2b=hb, away_b2b=ab_, shrink_k=params["shrink_k"])
        ml["total"] += params["total_bias"] + params["total_b2b_coef"] * (hb + ab_)
        ctx = {
            "date": date, "away": away, "home": home, "matchup": matchup,
            "time_et": time_et, "venue": venue, "game_id": game_id,
            "home_b2b": hb, "away_b2b": ab_,
            "home_rest_days": hrest, "away_rest_days": arest,
            "rest_known": (hk, ak),
            "ref": ref, "model": ml,
            "model_margin_final": ml["margin"], "model_total_final": ml["total"],
            "game_pace": ml["poss"], "L_pace": season.L_pace,
            "sigma_margin": sigma_m, "sigma_total": sigma_t,
            "p_home_model": norm_cdf(ml["margin"] / sigma_m),
            "p_home_ref": norm_cdf(ref["margin"] / sigma_m),
            "loss_home": loss_home, "loss_away": loss_away,
            "inj_home": rep_home, "inj_away": rep_away,
            "actual_margin": actual_margin, "actual_total": actual_total,
            "props": [],
        }
        if extra:
            ctx.update(extra)
        return ctx

    def add_props(ctx):
        date = ctx["date"]
        for side_key, opp_key in (("home", "away"), ("away", "home")):
            team = ctx[side_key]
            opp = ctx[opp_key]
            opp_rating = season.rating(opp, shrink_k=None)
            team_pace = season.teams[team]["pace"]
            st = status_map.get((date, team), {})
            for p in players:
                if p["team"] != team:
                    continue
                status = st.get(_norm(p["player"]))
                if status in ("Out", "Doubtful"):
                    continue
                lost = avail.teammate_lost_share(date, team, p["player"]) \
                    if (date, team) in avail.by_team_game else 0.0
                ctx["props"].append(project_player(
                    p, team_pace, ctx["game_pace"], opp_rating, league,
                    teammate_lost_share=lost))

    holdout_ctx = []
    for r in bt["rows"]:
        g = r["game"]
        ctx = build_ctx(g["date"], g["away"], g["home"], game_id=g["game_id"],
                        actual_margin=r["actual_margin"], actual_total=r["actual_total"])
        # keep the out-of-sample ratings: rebuild with the TRAINING table
        tr = bt["train"]
        ctx["ref"] = reference_line(tr, g["home"], g["away"], flat_hca=2.0)
        mlt = model_line(tr, g["home"], g["away"], params,
                         home_b2b=r["home_b2b"], away_b2b=r["away_b2b"],
                         shrink_k=params["shrink_k"])
        mlt["total"] += params["total_bias"] + params["total_b2b_coef"] * \
            (r["home_b2b"] + r["away_b2b"])
        ctx["model"] = mlt
        ctx["model_margin_final"] = mlt["margin"]
        ctx["model_total_final"] = mlt["total"]
        ctx["game_pace"] = mlt["poss"]
        ctx["L_pace"] = tr.L_pace
        ctx["p_home_model"] = norm_cdf(mlt["margin"] / sigma_m)
        ctx["p_home_ref"] = norm_cdf(ctx["ref"]["margin"] / sigma_m)
        ctx["sigma_margin"] = sigma_m
        ctx["sigma_total"] = sigma_t
        holdout_ctx.append(ctx)

    future_ctx = []
    for g in scheduled:
        src = g["source_id"]
        ctx = build_ctx(g["date"], g["away"], g["home"], time_et=g["time_et"],
                        venue=f'{g["venue"]}, {g["city"]}', game_id=g["game_id"],
                        extra={
                            "away_rec": g["away_rec"], "home_rec": g["home_rec"],
                            "cup_group": g["cup_group"], "src": src,
                        })
        add_props(ctx)
        future_ctx.append(ctx)

    # ------------------------------------------------------------- plays/grading
    holdout_plays = build_plays(holdout_ctx)
    for p in holdout_plays:
        p["result"] = grade_play(p)
        p["units"] = roi_units(p, p["result"])

    future_plays = build_plays(future_ctx)

    summaries = []
    for s in STRATEGIES:
        ps = [p for p in holdout_plays if p["strategy"] == s["id"]]
        summaries.append(summarise(s, ps, bt["metrics"], params))
    leaderboard = build_leaderboard(summaries)

    # ------------------------------------------------------------------ outputs
    os.makedirs(OUT, exist_ok=True)

    meta = {
        "generated_at_utc": GENERATED_AT,
        "season": "2026-27",
        "as_of": "2026-11-13",
        "data_windows": {
            "ratings_season_to_date": season_block["label"],
            "ratings_training_window": train_block["label"],
            "results_captured": "2026-11-06 .. 2026-11-12 (51 games, all of them out-of-sample)",
            "out_of_sample_window": "2026-11-06 .. 2026-11-12 (51 games)",
            "upcoming_slates": "2026-11-13, 2026-11-14, 2026-11-15 (23 games)",
            "injury_report": inj_raw["report"],
        },
        "counts": {
            "teams": len(season.teams),
            "completed_games_captured": len(completed),
            "out_of_sample_games": len(holdout_ctx),
            "upcoming_games": len(future_ctx),
            "players_captured": len(players),
            "injury_rows": len(injuries),
            "strategies": len(STRATEGIES),
        },
        "league_averages": {
            "off_rtg": rnd(season.L_off, 2), "def_rtg": rnd(season.L_def, 2),
            "L_used_in_model": rnd(season.L, 2), "pace": rnd(season.L_pace, 2),
            "dreb_pct": rnd(league["L_dreb"], 2),
        },
        "assumptions": ASSUMPTIONS,
        "verification_rule": "Every published table row carries a source id. Anything that "
                             "could not be traced to an official URL is left blank and "
                             "appears on the Flagged for Review page.",
    }
    write_json(os.path.join(OUT, "meta.json"), meta)
    write_json(os.path.join(OUT, "sources.json"), sources)

    # teams
    teams_out = []
    for ab, t in sorted(season.teams.items()):
        ppg = t["ortg"] * t["pace"] / 100.0
        opp_ppg = t["drtg"] * t["pace"] / 100.0
        teams_out.append({
            "abbr": ab, "team": t["team"], "gp": t["gp"], "w": t["w"], "l": t["l"],
            "win_pct": rnd(t["w"] / t["gp"], 3),
            "ortg": t["ortg"], "drtg": t["drtg"], "netr": t["netr"], "pace": t["pace"],
            "efg_pct": t["efg_pct"], "ts_pct": t["ts_pct"], "tov_pct": t["tov_pct"],
            "oreb_pct": t["oreb_pct"], "dreb_pct": t["dreb_pct"], "reb_pct": t["reb_pct"],
            "ast_pct": t["ast_pct"], "pie": t["pie"],
            "ppg_implied": rnd(ppg, 1), "opp_ppg_implied": rnd(opp_ppg, 1),
            "src": "S1",
        })
    write_json(os.path.join(OUT, "teams.json"), {
        "cols": ["abbr", "team", "gp", "w", "l", "win_pct", "ortg", "drtg", "netr", "pace",
                 "efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct", "reb_pct",
                 "ast_pct", "pie", "ppg_implied", "opp_ppg_implied"],
        "rows": teams_out, "src": "S1",
        "note": "ppg_implied and opp_ppg_implied are arithmetic (OffRtg x Pace / 100) on "
                "official inputs; every other column is published verbatim by NBA.com.",
    })

    # lines for the upcoming slates
    lines = []
    for c in future_ctx:
        spread_edge = c["model_margin_final"] - c["ref"]["margin"]
        total_edge = c["model_total_final"] - c["ref"]["total"]
        p_over = 1.0 - norm_cdf((c["ref"]["total"] - c["model_total_final"]) / sigma_t)
        p_cover_home = 1.0 - norm_cdf((c["ref"]["margin"] - c["model_margin_final"]) / sigma_m)
        lines.append({
            "date": c["date"], "time_et": c["time_et"], "matchup": c["matchup"],
            "away": c["away"], "home": c["home"],
            "away_rec": c.get("away_rec"), "home_rec": c.get("home_rec"),
            "venue": c["venue"], "cup_group": c.get("cup_group"),
            "game_id": c["game_id"],
            "ref_spread_home": rnd(c["ref"]["margin"], 1),
            "model_spread_home": rnd(c["model_margin_final"], 1),
            "spread_edge": rnd(spread_edge, 2),
            "ref_total": rnd(c["ref"]["total"], 1),
            "model_total": rnd(c["model_total_final"], 1),
            "total_edge": rnd(total_edge, 2),
            "model_possessions": rnd(c["game_pace"], 1),
            "p_home_win": rnd(c["p_home_model"], 3),
            "p_home_cover_ref": rnd(p_cover_home, 3),
            "p_over_ref_total": rnd(p_over, 3),
            "ml_home_fair": american_from_prob(c["p_home_model"]),
            "ml_away_fair": american_from_prob(1 - c["p_home_model"]),
            "home_b2b": c["home_b2b"], "away_b2b": c["away_b2b"],
            "home_rest_days": c["home_rest_days"], "away_rest_days": c["away_rest_days"],
            "home_availability_loss": rnd(c["loss_home"], 2),
            "away_availability_loss": rnd(c["loss_away"], 2),
            "home_injury_listed": (c["inj_home"] or {}).get("listed"),
            "away_injury_listed": (c["inj_away"] or {}).get("listed"),
            "home_injury_confidence": (c["inj_home"] or {}).get("confidence", "NONE - no entry in this edition of the report"),
            "away_injury_confidence": (c["inj_away"] or {}).get("confidence", "NONE - no entry in this edition of the report"),
            "home_minutes_coverage": (c["inj_home"] or {}).get("minutes_coverage"),
            "away_minutes_coverage": (c["inj_away"] or {}).get("minutes_coverage"),
            "home_report_status": _report_status(c["inj_home"]),
            "away_report_status": _report_status(c["inj_away"]),
            "src": c.get("src"),
            "src_ratings": "S1",
        })
    write_json(os.path.join(OUT, "lines.json"), {"rows": lines, "src": "S1"})

    # player props
    props = []
    for c in future_ctx:
        for p in c["props"]:
            props.append({
                "date": c["date"], "matchup": c["matchup"], "game_id": c["game_id"],
                "player": p["player"], "team": p["team"],
                "opponent": c["home"] if p["team"] == c["away"] else c["away"],
                "gp": p["gp"], "season_min": p["season_min"],
                "baseline_pts": p["baseline_pts"], "proj_pts": p["proj_pts"],
                "delta_pts": p["delta_pts"],
                "baseline_reb": p["baseline_reb"], "proj_reb": p["proj_reb"],
                "delta_reb": p["delta_reb"],
                "baseline_ast": p["baseline_ast"], "proj_ast": p["proj_ast"],
                "delta_ast": p["delta_ast"],
                "baseline_pts_reb_ast": p["baseline_pts_reb_ast"],
                "proj_pts_reb_ast": p["proj_pts_reb_ast"],
                "delta_pts_reb_ast": p["delta_pts_reb_ast"],
                "baseline_fg3m": p["baseline_fg3m"], "proj_fg3m": p["proj_fg3m"],
                "delta_fg3m": p["delta_fg3m"],
                "poss_factor": p["poss_factor"], "def_factor": p["def_factor"],
                "reb_factor": p["reb_factor"], "usage_factor": p["usage_factor"],
                "src_baseline": "S7", "src_context": "S1",
                "probability": None,
                "probability_note": "Not published: game-to-game variance was not measured "
                                    "from official player game logs (F2 / Q3).",
            })
    write_json(os.path.join(OUT, "props.json"), {"rows": props, "src": "S7"})

    # injuries + rotation
    inj_rows = []
    for c in future_ctx:
        for side, rep in (("home", c["inj_home"]), ("away", c["inj_away"])):
            if not rep:
                inj_rows.append({
                    "date": c["date"], "matchup": c["matchup"], "game_id": c["game_id"],
                    "team": c[side], "side": side, "listed": None,
                    "status": "NO ENTRY IN THE 2026-11-13 05:15 PM ET EDITION",
                    "weighted_lost_share": None, "impact_net_rating": None,
                    "minutes_coverage": None,
                    "confidence": "NONE - no entry in this edition of the report",
                    "src": "S6",
                })
                continue
            for d in rep["detail"]:
                inj_rows.append({
                    "date": c["date"], "matchup": c["matchup"], "game_id": c["game_id"],
                    "team": c[side], "side": side,
                    "player": d["player"], "status": d["status"], "reason": d["reason"],
                    "status_weight": d["status_weight"],
                    "minutes_known": d["minutes_known"],
                    "season_min": d["season_min"],
                    "minutes_share": d["minutes_share"],
                    "weighted_share": d["weighted_share"],
                    "team_listed": rep["listed"],
                    "team_weighted_lost_share": rep["weighted_lost_share"],
                    "team_impact_net_rating": rep["impact_net_rating"],
                    "impact_sensitivity": rep["impact_sensitivity"],
                    "minutes_coverage": rep["minutes_coverage"],
                    "confidence": rep["confidence"],
                    "src": "S6",
                })
            if rep["not_submitted"]:
                inj_rows.append({
                    "date": c["date"], "matchup": c["matchup"], "game_id": c["game_id"],
                    "team": c[side], "side": side, "player": None,
                    "status": "NOT YET SUBMITTED", "reason": "Team had not filed at the "
                    "05:15 PM ET edition", "src": "S6",
                })
    write_json(os.path.join(OUT, "injuries.json"), {
        "rows": inj_rows, "src": "S6",
        "report": inj_raw["report"],
        "method": ASSUMPTIONS["injury_impact_coef"],
        "lower_bound_note": "Minutes are only known for players in the captured official "
                            "top-50 minutes table (S7). Everyone else contributes 0.00, so "
                            "the impact column is a lower bound.",
    })

    # game flow
    gf = []
    for c in sorted(future_ctx, key=lambda x: (x["date"], x["matchup"])):
        g = game_flow({"margin": c["model_margin_final"], "total": c["model_total_final"],
                       "poss": c["game_pace"],
                       "pace_delta": c["game_pace"] - c["L_pace"]},
                      sigma_m, sigma_t)
        g.update({
            "date": c["date"], "time_et": c["time_et"], "matchup": c["matchup"],
            "away": c["away"], "home": c["home"], "game_id": c["game_id"],
            "away_rec": c.get("away_rec"), "home_rec": c.get("home_rec"),
            "pace_rank_note": f'{rnd(c["game_pace"] - c["L_pace"], 1)} possessions per 48 '
                              f'minutes vs the league average of {rnd(c["L_pace"], 2)}',
            "home_b2b": c["home_b2b"], "away_b2b": c["away_b2b"],
            "home_rest_days": c["home_rest_days"], "away_rest_days": c["away_rest_days"],
            "rest_known": c["rest_known"],
            "src": c.get("src"), "src_ratings": "S1",
        })
        gf.append(g)
    write_json(os.path.join(OUT, "gameflow.json"), {"rows": gf, "src": "S1"})

    # backtest
    bt_rows = []
    for r, c in zip(bt["rows"], holdout_ctx):
        g = r["game"]
        bt_rows.append({
            "date": g["date"], "matchup": f'{g["away"]}@{g["home"]}',
            "away": g["away"], "home": g["home"], "game_id": g["game_id"],
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "ot": g["ot"], "neutral": g.get("neutral", 0),
            "actual_margin_home": r["actual_margin"], "actual_total": r["actual_total"],
            "ref_spread_home": rnd(r["ref"]["margin"], 1),
            "model_spread_home": rnd(r["model_margin_final"], 1),
            "err_model_margin": rnd(r["err_margin_model"], 2),
            "err_ref_margin": rnd(r["err_margin_ref"], 2),
            "ref_total": rnd(r["ref"]["total"], 1),
            "model_total": rnd(r["model_total_final"], 1),
            "err_model_total": rnd(r["err_total_model"], 2),
            "err_ref_total": rnd(r["err_total_ref"], 2),
            "home_b2b": r["home_b2b"], "away_b2b": r["away_b2b"],
            "home_rest_days": r["home_rest_days"], "away_rest_days": r["away_rest_days"],
            "p_home_model": rnd(r["p_home_model"], 3),
            "p_home_ref": rnd(r["p_home_ref"], 3),
            "home_won": r["home_won"],
            "src": f'S3_{g["date"]}',
        })
    write_json(os.path.join(OUT, "backtest.json"), {
        "rows": bt_rows, "metrics": bt["metrics"], "params": params, "fit": bt["fit"],
    })

    # validation + leaderboard
    write_json(os.path.join(OUT, "validation.json"), {
        "metrics": bt["metrics"], "fit": bt["fit"],
        "strategies": summaries,
        "gate_definitions": [
            {"id": i, "name": n, "definition": d} for i, n, d in
            [("G1", "Sample size", "At least 30 graded plays; 10-29 is provisional."),
             ("G2", "Calibration", "Observed hit rate within 8 pp of the mean predicted probability."),
             ("G3", "Edge over break-even", "Mean modelled probability at or above 52.38% "
                                            "(break-even at -110)."),
             ("G4", "Skill, not luck", "Wilson 95% lower bound on the hit rate above 52.38%; "
                                       "exact binomial p reported."),
             ("G5", "Stability", "Bootstrap 95% CI of the model's margin MAE sits entirely "
                                 "below the reference model's MAE."),
             ("G6", "Correlation limit", "Parlay leg pairs limited to |rho| <= 0.30."),
             ("G7", "Availability robustness", "A play must survive flipping every Questionable "
                                               "player to Out (needs the official report for the "
                                               "graded window).")]
        ],
        "graded_plays": strip_private(holdout_plays),
    })
    write_json(os.path.join(OUT, "leaderboard.json"), {
        "weights": {"sample": 0.20, "edge": 0.25, "calibration": 0.15,
                    "result": 0.25, "gates": 0.15},
        "formula": "LBS = 100 x (0.20*sample + 0.25*edge + 0.15*calibration + 0.25*result + 0.15*gates)",
        "rows": leaderboard,
        "tiers": [
            {"floor": 70, "name": "Tier 1 - Funded", "note": "Full unit."},
            {"floor": 50, "name": "Tier 2 - Half unit", "note": "Half unit."},
            {"floor": 30, "name": "Tier 3 - Quarter unit", "note": "Quarter unit."},
            {"floor": 0, "name": "Not funded - research only", "note": "Paper only."},
        ],
    })

    # correlations
    write_json(os.path.join(OUT, "correlations.json"), {
        "measured": measured_correlations(season),
        "model_derived": model_derived_correlations(),
        "sgp_rho": SGP_RHO,
        "parlay_pricing_grid": parlay_pricing_grid(),
        "src": "S1",
    })

    # luck
    write_json(os.path.join(OUT, "luck.json"), {
        "rows": luck_table(season), "src": "S1",
        "method": "Pythagorean expectation with exponent 13.91 applied to the official "
                  "OffRtg and DefRtg. Expected wins = GP x pythag. Luck = actual wins - "
                  "expected wins; z divides that by the binomial SD over games played.",
    })

    # picks (upcoming)
    picks = []
    for p in future_plays:
        row = dict(p)
        row["result"] = None
        row["status"] = "PENDING"
        picks.append(strip_private(row))
    write_json(os.path.join(OUT, "picks.json"), {
        "generated_at_utc": GENERATED_AT,
        "slate_dates": sorted({c["date"] for c in future_ctx}),
        "rows": picks,
        "note": "Picks are produced from the originated lines only. No play has been graded "
                "yet; grading happens automatically once the official final score is "
                "published on nba.com.",
    })

    # authored content -> docs/data
    for name in ("flagged.json", "questions.json", "suggestions.json", "executive.json"):
        src = os.path.join(CONTENT, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUT, name))

    print(f"Wrote site data to {OUT}")
    print(json.dumps(meta["counts"], indent=1))
    print("metrics:", json.dumps(bt["metrics"], indent=1))
    print("fit:", json.dumps({k: v for k, v in bt["fit"].items() if k != "b2b_caveat"}, indent=1))
    for s in summaries:
        print(f'{s["id"]:>3} {s["name"][:38]:<38} n={s["n_graded"]:>3} '
              f'record={s["wins"]}-{s["losses"]} units={s["units_at_minus110"]:+.2f} '
              f'gates={[g["status"] for g in s["gates"]]}')
    for r in leaderboard:
        print(f'{r["rank"]:>2} {r["id"]} {r["lbs"]:>5} {r["tier"]}')


def _report_status(rep):
    if not rep:
        return "NO ENTRY IN THE 2026-11-13 05:15 PM ET EDITION"
    if rep.get("not_submitted"):
        return "NOT YET SUBMITTED"
    if rep.get("no_entry_in_report"):
        return "NO ENTRY IN THE 2026-11-13 05:15 PM ET EDITION"
    return f'{rep["listed"]} player(s) listed'


if __name__ == "__main__":
    main()
