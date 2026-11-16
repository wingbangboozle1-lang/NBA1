#!/usr/bin/env python3
"""build_horizon_v2.py — build the second-generation horizon lines, picks and
model report for the rolling slate window.

Outputs
  data/derived/horizon_lines_v2.json    one row per game in the window
  data/derived/horizon_picks_v2.json    the picks the gates allow
  data/derived/model_report_v2.json     the measured inputs the model is pinned
                                         to (HCA anchor, rho, luck, log loss,
                                         assumptions, every gap that is blank)

Everything it prints is either an official value with its source URL, a
DERIVED value with its formula, or blank and flagged.  Nothing is inferred.

Run: python3 scripts/build_horizon_v2.py
"""
import datetime
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import model_v2 as M  # noqa: E402

DERIVED = os.path.join(ROOT, "data", "derived")
OFF = os.path.join(ROOT, "data", "official")

# The pick window is "up to 3 days ahead" from the current slate date.
TODAY = "2026-11-15"
# The 2026-11-15 slate was already in progress when the official pages were
# read (18:45 ET: five games live, three not yet tipped), so the pick window
# starts on the next slate and runs three days ahead.
PICK_WINDOW_START = "2026-11-16"
PICK_WINDOW_END = "2026-11-18"
LINE_WINDOW_END = "2026-11-19"

STATUS_PLAY_PROB = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
                    "Probable": 0.80, "Available": 1.00}

GATES = {
    "max_disagreement_pp": 4.0,
    "min_model_prob": 0.55,
    "luck_band_z": M.ASSUMPTIONS["luck_noise_band_z"]["value"],
    "note": ("a pick must survive every gate to be published as a stakeable "
             "pick. No strategy has passed the strategy validation gates in "
             "this repository, so every pick below is published as MODEL "
             "OUTPUT - UNVALIDATED with zero stake, which is the honest state "
             "of the evidence."),
}


def load_injury_edition():
    """The newest official injury-report edition in the repo."""
    files = sorted(f for f in os.listdir(OFF)
                   if f.startswith("injury_2026") and f.endswith(".json"))
    path = os.path.join(OFF, files[-1])
    doc = M._load(path)
    rows = []
    for r in doc["rows"]:
        if not r.get("player"):
            continue
        rows.append({
            "matchup": r.get("matchup"),
            # the PDF cells carry full team names (and merged-cell rows inherit
            # a neighbour's team) — normalize to the official abbr the rest of
            # the model keys on; anything unmapped keeps the printed name
            "team": (M.TEAM_NAME_TO_ABBR.get(
                        (r.get("team_effective") or "").split(" (inherited")[0].strip())
                     or r.get("team_effective")),
            "player": r.get("player"),
            "status": r.get("status"),
            "reason": r.get("reason"),
            "game_date": r.get("game_date"),
            "game_time": r.get("game_time"),
            "source_url": r.get("source_url"),
        })
    return doc, rows, os.path.basename(path)


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    teams, league, tabs = M.league_inputs()
    standings, standings_file = M.load_standings()
    sched = M.load_schedule()
    arenas = M.load_arenas()
    arenas_by_team = {r["abbr"]: r for r in arenas["rows"]}
    arena_by_name = M.arenas_by_name(arenas)
    results = M.load_results()
    inj_doc, inj_rows, inj_file = load_injury_edition()
    minutes, minutes_meta = M.load_minutes()

    # ---------------------------------------------------------------- HCA
    sigma_margin = 12.0  # league margin dispersion; replaced by the measured
                         # value below when it is computable
    margins = [g["home_pts"] - g["away_pts"] for g in results
               if g.get("home_pts") is not None and g.get("away_pts") is not None]
    measured_sd = M.pstdev(margins)
    if measured_sd:
        sigma_margin = measured_sd
    anchor = M.measured_home_win_rate(results, standings)
    hwr_gl = anchor["home_win_rate"]
    hwr_std = (standings["measured_home_court_anchor"]["home_win_rate"]
               if standings else None)
    # PRIMARY measurement: the official standings HOME/ROAD columns, which
    # cover every game completed at read time (the largest official sample).
    # The final-score corpus is published next to it as a cross-check.
    hwr = hwr_std if hwr_std else hwr_gl
    hca_points, hca_z = M.hca_from_measured_home_win_rate(hwr, sigma_margin)
    hca_points_gl, hca_z_gl = M.hca_from_measured_home_win_rate(hwr_gl, sigma_margin)

    hca_block = {
        "measured_home_win_rate": hwr,
        "measured_home_win_rate_from_final_scores": hwr_gl,
        "hca_points_from_final_scores_crosscheck": round(hca_points_gl, 2) if hca_points_gl else None,
        "primary_measurement": ("the official standings HOME/ROAD columns (the "
                                "largest official sample); the final-score corpus "
                                "measurement is published beside it as a "
                                "cross-check"),
        "measured_road_win_rate": anchor["road_win_rate"],
        "games_measured": anchor["n_games"],
        "home_wins": anchor["home_wins"], "home_games": anchor["home_games"],
        "standings_cross_check": anchor.get("standings_anchor"),
        "sigma_margin_used": round(sigma_margin, 2),
        "sigma_margin_source": "population standard deviation of the margin on "
                               "the official final-score corpus",
        "hca_points": round(hca_points, 2),
        "hca_z": round(hca_z, 4),
        "formula": ("HCA_points = sigma_margin * Phi^-1(measured home win rate). "
                    "The number of points is read off the measurement; nothing "
                    "about it is fitted."),
        "status": "MEASURED - the home-court advantage is pinned to the official "
                  "home win rate",
    }

    # ------------------------------------------------- rest / travel context
    hist, fut = M.team_game_dates(results, sched["rows"])
    venues_by_home_team = {r["abbr"]: r["arena"] for r in arenas["rows"]}

    # ------------------------------------------------------------ luck table
    luck, luck_sd = M.luck_table(teams, league, results, sigma_margin)
    zmap = {r["team"]: r for r in luck}

    # ------------------------------------------------------- OOS log loss
    oos_ll, oos_n = M.model_out_of_sample_log_loss(teams, league, results, hca_points)
    market_block = M.market_blend(0.5, None, oos_ll, None)

    rho_rows = M.measured_rho(results)
    rho_map = {r["pair"]: r["rho_measured"] for r in rho_rows}

    # ------------------------------------------------------- per-game lines
    out_games = []
    for r in sched["rows"]:
        if r["date"] < TODAY or r["date"] > LINE_WINDOW_END:
            continue
        h, a = r["home"], r["away"]
        th, ta = teams.get(h), teams.get(a)
        if not th or not ta:
            continue
        in_pick_window = (PICK_WINDOW_START <= r["date"] <= PICK_WINDOW_END)

        est_a = M.estimator_a(th, ta, league, hca_points)
        est_b = M.estimator_b(th, ta, league, hca_points)
        blend = M.blend_estimators(est_a, est_b, sigma_margin)

        # rest and travel
        rest_h = M.rest_profile(h, r["date"], hist, fut, arenas_by_team.get(h))
        rest_a = M.rest_profile(a, r["date"], hist, fut, arenas_by_team.get(a))
        prev_venue, prev_src = M.previous_venue(a, r["date"], hist, fut,
                                                arenas_by_team.get(a),
                                                venues_by_home_team)
        travel = M.travel_distance(a, h, prev_venue, arenas_by_team, arena_by_name)

        # availability -> minutes redistribution
        def team_absent(team):
            res = []
            for row in inj_rows:
                if row["team"] != team:
                    continue
                if row["matchup"] and row["matchup"] != "%s@%s" % (a, h):
                    continue
                res.append(row)
            return res

        abs_h = team_absent(h)
        abs_a = team_absent(a)
        minutes_meta_team = minutes.get(h), minutes.get(a)

        def redistribution(team, absent_rows, roster):
            if roster is None:
                return None
            absent = []
            for row in absent_rows:
                # injury PDF prints 'Last, First'; the leaderboard prints
                # 'First Last' — match through model_v2.norm_name, never fuzzily
                m = next((p for p in roster
                          if M.norm_name(p["player"]) == M.norm_name(row["player"])), None)
                if m is None:
                    absent.append({"player": row["player"], "status": row["status"],
                                   "min": None, "pts": None,
                                   "note": "no official minutes capture for this "
                                           "player -> his minutes are NOT "
                                           "estimated; the effect is left blank"})
                    continue
                share = M.ABSENCE_SHARE.get(row["status"], 0.0)
                absent.append({"player": row["player"], "status": row["status"],
                               "minutes_removed_share": share,
                               "min": round((m.get("min") or 0.0) * share, 2),
                               "pts": round((m.get("pts") or 0.0) * share, 2),
                               "min_captured": m.get("min"), "pts_captured": m.get("pts"),
                               "source_url": m.get("source_url"),
                               "note": ("minutes removed at the status share "
                                        "(%s -> %.0f%% of his captured minutes)"
                                        % (row["status"], 100.0 * share))
                                       if share else
                                       "status %s -> no minutes removed"
                                       % (row["status"] or "?")})
            usable = [x for x in absent if (x.get("min") or 0.0) > 0.0]
            if not usable:
                return {"team": team, "minutes_removed": 0.0,
                        "net_points_lost": 0.0,
                        "absent_players": absent,
                        "note": "no absent player has an official minutes "
                                "capture -> no redistribution is computed"}
            return M.minutes_redistribution(team, usable, roster)

        red_h = redistribution(h, abs_h, minutes.get(h))
        red_a = redistribution(a, abs_a, minutes.get(a))
        net_h = (red_h or {}).get("net_points_lost") or 0.0
        net_a = (red_a or {}).get("net_points_lost") or 0.0

        # rest / travel adjustments (modelling choices, published as such)
        adj = M.ASSUMPTIONS["rest_penalty_points"]["value"]
        travel_coef = 0.0012
        rest_loss_h = 0.0
        rest_loss_a = 0.0
        if rest_h.get("back_to_back"):
            rest_loss_h += adj["b2b"]
        if rest_h.get("three_in_four"):
            rest_loss_h += adj["three_in_four"]
        if rest_a.get("back_to_back"):
            rest_loss_a += adj["b2b"]
        if rest_a.get("three_in_four"):
            rest_loss_a += adj["three_in_four"]
        travel_loss_a = (travel["miles"] * travel_coef) if travel else 0.0

        # apply the availability / rest / travel losses to the blended line
        scale = blend["margin_blend"] and (est_a["game_possessions"] / 100.0) or 1.0
        margin = blend["margin_blend"] + (net_a - net_h) * scale + \
            (rest_loss_a - rest_loss_h) * scale + travel_loss_a * scale
        total = blend["total_blend"] - (net_a + net_h) * scale * 0.4
        p_home = M.norm_cdf(margin / sigma_margin)

        rot_h = M.rotation_availability(h, inj_rows, minutes.get(h))
        rot_a = M.rotation_availability(a, inj_rows, minutes.get(a))

        luck_h = zmap.get(h, {})
        luck_a = zmap.get(a, {})

        out_games.append({
            "date": r["date"],
            "game_id": r["game_id"],
            "matchup": r["matchup"],
            "away": a, "home": h,
            "venue": r["venue"], "city": r["city"],
            "tip_et": r["tip_et_primary"],
            "tip_et_sources": {"per_game_card": r["tip_et_primary"],
                               "schedule_page": r.get("tip_et_schedule_page"),
                               "injury_pdf": r.get("tip_et_injury_pdf"),
                               "conflict": r.get("tip_conflict")},
            "in_pick_window": in_pick_window,
            "estimator_a": est_a,
            "estimator_b": est_b,
            "blend": blend,
            "line_total": round(total, 1),
            "line_spread_home": round(margin, 1),
            "model_home_win_prob": round(p_home, 4),
            "model_home_ml": M.american(p_home),
            "confidence_signal_pp": blend["disagreement_pp"],
            "rest_home": rest_h,
            "rest_away": rest_a,
            "travel_away": travel,
            "travel_source": prev_src,
            "availability_redistribution_home": red_h,
            "availability_redistribution_away": red_a,
            "net_points_lost_home": net_h,
            "net_points_lost_away": net_a,
            "rest_adjustment_home": rest_loss_h,
            "rest_adjustment_away": rest_loss_a,
            "travel_adjustment_away": round(travel_loss_a, 3),
            "rotation_availability_home": rot_h,
            "rotation_availability_away": rot_a,
            "luck_home": {"luck_z": luck_h.get("luck_z"),
                          "in_noise_band": luck_h.get("in_noise_band"),
                          "luck_points": luck_h.get("luck_points")},
            "luck_away": {"luck_z": luck_a.get("luck_z"),
                          "in_noise_band": luck_a.get("in_noise_band"),
                          "luck_points": luck_a.get("luck_points")},
            "source_url": r["source_url"],
            "schedule_source_url": "https://www.nba.com/schedule",
        })

    # ------------------------------------------------------------- the picks
    picks = []
    for g in out_games:
        if not g["in_pick_window"]:
            continue
        p = g["model_home_win_prob"]
        side = "home" if p >= 0.5 else "away"
        prob = p if side == "home" else 1 - p
        gates_pass = []
        gates_fail = []
        if g["confidence_signal_pp"] <= GATES["max_disagreement_pp"]:
            gates_pass.append("disagreement <= %.1f pp" % GATES["max_disagreement_pp"])
        else:
            gates_fail.append("disagreement %.2f pp > %.1f pp"
                              % (g["confidence_signal_pp"], GATES["max_disagreement_pp"]))
        if prob >= GATES["min_model_prob"]:
            gates_pass.append("model probability >= %.2f" % GATES["min_model_prob"])
        else:
            gates_fail.append("model probability %.3f < %.2f"
                              % (prob, GATES["min_model_prob"]))
        for ab, lk in ((g["home"], g["luck_home"]), (g["away"], g["luck_away"])):
            if lk.get("in_noise_band") is False:
                gates_fail.append("%s luck z %.2f outside the +/-%.1f band"
                                  % (ab, lk.get("luck_z"), GATES["luck_band_z"]))
            else:
                gates_pass.append("%s inside the luck band" % ab)
        if g["availability_redistribution_home"] is None or \
                g["availability_redistribution_away"] is None:
            gates_fail.append("minutes redistribution not computable for one of "
                              "the teams (per-player minutes not captured)")
        else:
            gates_pass.append("minutes redistribution computed")
        picks.append({
            "date": g["date"], "game_id": g["game_id"], "matchup": g["matchup"],
            "pick": "%s %s" % (g["home"] if side == "home" else g["away"],
                               "wins" if side == "home" else "wins"),
            "side": side,
            "team": g["home"] if side == "home" else g["away"],
            "opponent": g["away"] if side == "home" else g["home"],
            "model_probability": round(prob, 4),
            "model_ml": M.american(prob),
            "line_total": g["line_total"],
            "line_spread_home": g["line_spread_home"],
            "confidence_signal_pp": g["confidence_signal_pp"],
            "rotation_availability_pick_team": (g["rotation_availability_home"]
                                               if side == "home"
                                               else g["rotation_availability_away"]),
            "rotation_availability_opponent": (g["rotation_availability_away"]
                                               if side == "home"
                                               else g["rotation_availability_home"]),
            "rest_days_pick_team": (g["rest_home"]["rest_days"] if side == "home"
                                    else g["rest_away"]["rest_days"]),
            "rest_days_opponent": (g["rest_away"]["rest_days"] if side == "home"
                                   else g["rest_home"]["rest_days"]),
            "back_to_back_pick_team": (g["rest_home"]["back_to_back"] if side == "home"
                                       else g["rest_away"]["back_to_back"]),
            "travel_miles_opponent": (g["travel_away"] or {}).get("miles"),
            "luck_z_pick_team": (g["luck_home"] if side == "home"
                                 else g["luck_away"]).get("luck_z"),
            "gates_passed": gates_pass,
            "gates_failed": gates_fail,
            "gate_verdict": "PASS" if not gates_fail else "FAIL",
            "stake_units": 0,
            "status": ("MODEL OUTPUT - UNVALIDATED - NO STRATEGY HAS PASSED THE "
                       "VALIDATION GATES; zero stake"),
            "source_url": g["source_url"],
        })

    # ------------------------------------------------------------- outputs
    lines_doc = {
        "_meta": {
            "title": "Originated horizon lines v2 - 2026-11-15 through 2026-11-19",
            "generated_by": "scripts/build_horizon_v2.py",
            "generated_utc": now,
            "method": ("two independent estimators built on the official team "
                       "tables, blended underneath; their disagreement is the "
                       "headline confidence signal; the home-court advantage is "
                       "pinned to the measured official home win rate"),
            "pick_window": "%s .. %s (up to 3 days ahead)" % (TODAY, PICK_WINDOW_END),
            "line_window": "%s .. %s" % (TODAY, LINE_WINDOW_END),
            "inputs": {
                "team_tables": {"advanced": tabs["advanced_file"],
                                "traditional": tabs["traditional_file"],
                                "opponent": tabs["opponent_file"]},
                "team_table_source_url": tabs["advanced_source"],
                "standings_file": standings_file,
                "schedule_file": "official_schedule_2026-11-15_to_19.json",
                "arena_file": "arena_coordinates_2026-11-15.json",
                "injury_edition_file": inj_file,
                "injury_edition_revision": inj_doc.get("revision"),
                "minutes_file": minutes_meta.get("file"),
            },
            "league_baselines": {k: (round(v, 4) if isinstance(v, float) else v)
                                 for k, v in league.items()},
            "home_court_anchor": hca_block,
            "assumptions": M.ASSUMPTIONS,
            "gates": GATES,
        },
        "games": out_games,
    }
    p1 = os.path.join(DERIVED, "horizon_lines_v2.json")
    with open(p1, "w", encoding="utf-8") as fh:
        json.dump(lines_doc, fh, indent=1, ensure_ascii=False)
    print("wrote", p1, len(out_games), "games")

    picks_doc = {
        "_meta": {
            "title": "Horizon picks v2 - every game in the 3-day pick window",
            "generated_by": "scripts/build_horizon_v2.py",
            "generated_utc": now,
            "status_note": ("no strategy has passed the validation gates in this "
                            "repository, so every pick below is MODEL OUTPUT - "
                            "UNVALIDATED with zero stake. The gate results are "
                            "published so a reviewer can see exactly what each "
                            "pick cleared and what it did not."),
            "gates": GATES,
            "home_court_anchor": hca_block,
        },
        "picks": picks,
    }
    p2 = os.path.join(DERIVED, "horizon_picks_v2.json")
    with open(p2, "w", encoding="utf-8") as fh:
        json.dump(picks_doc, fh, indent=1, ensure_ascii=False)
    print("wrote", p2, len(picks), "picks;",
          sum(1 for p in picks if p["gate_verdict"] == "PASS"), "passed the per-pick gates")

    # --------------------------------------------------------- model report
    parlay_grid = []
    for p1v in (0.55, 0.60, 0.65):
        for rho_key in ("home points / away points", "margin / total"):
            rho = rho_map.get(rho_key)
            if rho is None:
                continue
            parlay_grid.append(M.price_parlay(p1v, p1v, rho))
    report = {
        "title": "Model report v2 - every measured input the line model is pinned to",
        "generated_by": "scripts/build_horizon_v2.py",
        "generated_utc": now,
        "home_court_anchor": hca_block,
        "league_baselines": {k: (round(v, 4) if isinstance(v, float) else v)
                             for k, v in league.items()},
        "measured_correlations": rho_rows,
        "parlay_pricing_with_measured_rho": parlay_grid,
        "luck_table": luck,
        "luck_noise_band_z": M.ASSUMPTIONS["luck_noise_band_z"]["value"],
        "market_prior": market_block,
        "model_out_of_sample_log_loss": {"value": round(oos_ll, 5) if oos_ll else None,
                                         "n_games": oos_n,
                                         "definition": "binary log loss of the "
                                                       "model's home-win "
                                                       "probability on the "
                                                       "official final-score "
                                                       "corpus"},
        "per_player_minutes": minutes_meta,
        "assumptions": M.ASSUMPTIONS,
        "gaps": [],
    }
    gaps = report["gaps"]
    if not minutes_meta.get("available"):
        gaps.append({"id": "G-MIN", "severity": "high",
                     "item": "no official per-player minutes capture is stored",
                     "detail": "minutes redistribution cannot be computed, so the "
                               "availability adjustment to every line is 0 and "
                               "every pick fails the 'minutes redistribution "
                               "computed' gate",
                     "source": "https://www.nba.com/stats/players/traditional"})
    else:
        missing = sorted(({r["home"] for r in sched["rows"]
                           if r["date"] >= TODAY} |
                          {r["away"] for r in sched["rows"]
                           if r["date"] >= TODAY}) -
                         set(minutes_meta.get("teams_captured", [])))
        if missing:
            gaps.append({"id": "G-MIN-2", "severity": "medium",
                         "item": "per-player minutes captured for %d of the teams in the window; missing: %s"
                                  % (len(minutes_meta.get("teams_captured", [])), ", ".join(missing)),
                         "detail": "for those teams the rotation-availability column "
                                   "and the redistribution effect are blank and flagged",
                         "source": "https://www.nba.com/stats/players/traditional"})
    gaps.append({"id": "G-MKT", "severity": "high",
                 "item": "no official closing line is reachable, so the market leg of "
                         "the blend carries zero weight",
                 "detail": "the blend machinery and the measured out-of-sample log "
                           "loss that would set the weight are implemented and "
                           "published; the weight is 0 because the market leg is "
                           "unavailable, not because it was chosen",
                 "source": "https://www.nba.com/games"})
    p3 = os.path.join(DERIVED, "model_report_v2.json")
    with open(p3, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    print("wrote", p3)
    print("HCA points:", hca_block["hca_points"], "| measured home win rate:",
          hca_block["measured_home_win_rate"], "| sigma:", hca_block["sigma_margin_used"])
    print("measured rho:", {k: v for k, v in rho_map.items()})
    print("OOS log loss:", report["model_out_of_sample_log_loss"]["value"], "n =", oos_n)


if __name__ == "__main__":
    main()
