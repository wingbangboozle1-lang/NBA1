"""Build every artefact in this directory.

    python3 strategy-lab/run.py            # writes strategy-lab/data/*.json

Deterministic: one fixed seed, no network, no clock inside the numbers other than the
generation stamp. Re-running it on the same commit must reproduce every table.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backfill
import gates
import labdata
import restaudit
import tournament
import correlations
import content
import impact
from labdata import COMMIT, OUT, SESSION


def main():
    os.makedirs(OUT, exist_ok=True)
    content.write_out()
    ctx = labdata.build_schedule()
    bf = backfill.run(ctx)
    rest = restaudit.run(ctx)
    tour = tournament.run(ctx)
    corr = correlations.run(ctx)
    gate = gates.module_gates(tour)
    prob = gates.module_probability_audit(ctx)
    corr["probability_audit"] = prob
    measured = next((r["measured"] for r in corr["regressions"]
                     if r.get("measured") and r["measured"]["term"].startswith("back-to-back differential on the home")),
                    None)
    imp = impact.run(ctx, measured)
    meta = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": SESSION,
        "commit": COMMIT,
        "inputs": {
            "data/official/gamelog.json": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/official/gamelog.json",
            "verify/2026-11-14/official_finals_2026-11-13.json": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/2026-11-14/official_finals_2026-11-13.json",
            "verify/2026-11-14-a3e092a2/official_backfill_2026-10-24_2026-11-02.json": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/verify/2026-11-14-a3e092a2/official_backfill_2026-10-24_2026-11-02.json",
            "data/derived/horizon_lines.json": "https://www.nba.com/games?date=2026-11-14",
            "site/data/teams.json": "https://www.nba.com/stats/teams/advanced",
            "site/data/gameflow.json": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/gameflow.json",
            "site/data/backtest.json": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/site/data/backtest.json",
        },
        "official_pages_read_by_this_session": [
            "https://www.nba.com/games?date=2026-10-24",
            "https://www.nba.com/games?date=2026-11-02",
            "https://www.nba.com/games?date=2026-11-14",
            "https://www.nba.com/stats/teams/advanced",
        ],
        "not_used_anywhere_in_this_directory": [
            "a sportsbook or exchange price: none exists in this repository and no NBA-operated source publishes one",
            "a score for the 23 fixture games, because the official page does not print one",
            "any third-party stats site",
        ],
        "determinism": {"seed": 20261114, "python": sys.version.split()[0]},
    }
    for name, payload in (("backfill", bf), ("rest-audit", rest), ("tournament", tour),
                          ("correlations", corr), ("impact", imp), ("gates", gate),
                          ("probability-audit", prob),
                          ("meta", meta)):
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, ensure_ascii=False)
    report(bf, rest, tour, corr, gate, prob, imp)


def report(bf, rest, tour, corr, gate, prob, imp):
    s = bf["summary"]
    print(f"games: {s['scored_games']} scored + {s['fixtures_without_published_scores']} fixtures "
          f"+ {s['unplayed_horizon_games']} unplayed")
    print(f"backfill: {s['fixture_rows_matching_repo']}/{s['fixture_rows_compared']} fixture rows agree, "
          f"{s['fixture_rows_disagreeing']} disagree | dates {s['dates_mismatched']}/{s['dates_checked']} bad "
          f"| teams {s['teams_mismatched']}/{s['teams_checked']} bad | 11/13 finals {s['finals_11_13_agreeing']}/9")
    r = rest["summary"]
    print(f"rest: {r['team_slots_affected_by_the_missing_fixtures']} of {r['team_slots_checked']} team-slots "
          f"differ, {r['back_to_back_flags_that_flip']} b2b flips, {r['affected_inside_the_published_51_game_window']} "
          f"inside the graded window | horizon agree {rest['horizon_rest_check']['agree']} "
          f"mismatch {rest['horizon_rest_check']['mismatch']}")
    print(f"tournament: {tour['games_graded']} graded of {tour['games_in_log_with_scores']} scored "
          f"({tour['window']})")
    print(f"  {'id':4} {'n':>4} {'W':>3} {'hit':>7} {'E':>7} {'excess':>7} {'z':>6} {'p':>8} {'q':>7}  tier")
    for rec in tour["strategies"]:
        print(f"  {rec['id']:4} {rec['n']:>4} {rec['wins']:>3} {rec['hit_rate']:>7} "
              f"{rec['expected_wins_from_model']:>7} {rec['excess_wins']:>7} "
              f"{(rec['z_vs_model'] or 0):>6} {rec['p_model_null']:>8} {rec['bh_q']:>7}  "
              f"{gate['rows'][0]['tier'][:0]}")
    print(f"library null: z={tour['library_null']['observed_z']} "
          f"p={tour['library_null']['probability_luck_only_library_matches_or_beats']} "
          f"({tour['library_null']['strategies_in_library']} strategies, "
          f"{tour['library_null']['simulations']} draws)")
    fs = tour["forecast_skill"]
    print(f"forecast skill: margin MAE {fs['margin']['mae_model']} vs naive {fs['margin']['mae_naive_zero_line']} "
          f"({fs['margin']['improvement_pct']}% better); Brier skill {fs['win_probability']['brier_skill_score']}; "
          f"AUC {fs['win_probability']['auc']}")
    print(f"favourites: model said {fs['favourite_side']['mean_model_prob']}, "
          f"reality {fs['favourite_side']['realised_win_rate']} (gap {fs['favourite_side']['gap']:+})")
    print("tiers:")
    for row in gate["rows"]:
        print(f"  {row['id']:4} gates {row['gates_passed']}/6  {row['tier']}")
    print("correlations:")
    for reg in corr["regressions"]:
        m = reg["measured"]
        if m:
            print(f"  {m['term']}: {m['coef']} +- {m['se']} (t={m['t']}, p={m['p_two_sided']}, n={m['n']})"
                  f"  | site value: {reg['site_value']}")
    for c in corr["correlations"]:
        print(f"  corr({c['x']}, {c['y']}) = {c['r']}  p={c['p']}  n={c['n']}  | site assumes: {c['site_assumption']}")
    lc = corr["leg_correlation"]
    print(f"  same-night legs: joint {lc['measured_joint']} vs product {lc['independent_product']} "
          f"(diff {lc['difference']}, n={lc['date_pairs']})")
    sm = imp["summary"]
    print(f"b2b impact: {sm['games_where_the_two_positions_differ_by_3_points_or_more']} of "
          f"{sm['horizon_games']} horizon games move 3+ points; mean "
          f"{sm['mean_abs_disagreement_points']} pts, max {sm['max_abs_disagreement_points']} pts; "
          f"rest flags reproduced on {sm['rest_flags_reproduced_from_the_official_schedule']}/{sm['horizon_games']}")
    print("probability audit (site game-flow page vs the season):")
    for row in prob["rows"]:
        print(f"  {row['quantity']:22} model {row['mean_model_probability_published']} vs realised "
              f"{row['realised_rate_on_completed_games']}  gap {row['gap_points']}pp  p={row['p_exact_vs_model']}")


if __name__ == "__main__":
    main()
