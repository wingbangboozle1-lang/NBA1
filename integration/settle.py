"""Settlement ledger: grade what can be graded, and say plainly what cannot.

Settlement rule used throughout this desk, stated because it is the one place a lazy
implementation would cheat:

  * a game is gradeable ONLY if the official page printed FINAL for it, and
  * a pick is graded against the FINAL score, never against a projected or in-progress score,
  * nothing in the ratings used to make the pick may come from the game being graded.

Two of the three result buckets below are structurally ~50% and are labelled as such. The
model's own number is the line, so "covering" the model's own spread says nothing about
skill — only the error statistics in gates.py do. Publishing the cover rate without that
warning is exactly the kind of number that reads like an edge and is not one.
"""

import os

from common import OUT, binom_two_sided, block_bootstrap, dump, load, mean, sd, wilson


def grade_backtest(lines, final_ids=frozenset()):
    rows = []
    for g in lines["backtest"]:
        margin = g["actual_margin_home"]
        total = g["actual_total"]
        pm, pt = g["model_margin_home"], g["model_total"]
        pick_side = "HOME" if pm > 0 else ("AWAY" if pm < 0 else "PUSH")
        pick_won = (1 if (margin > 0 and pick_side == "HOME") or (margin < 0 and pick_side == "AWAY")
                    else (0 if pick_side in ("HOME", "AWAY") else None))
        t_dir = "OVER" if total > pt else ("UNDER" if total < pt else "PUSH")
        from_live_finals = g["game_id"] in final_ids
        rows.append({
            "date": g["date"], "matchup": g["matchup"], "game_id": g["game_id"],
            "source_url": g["source_url"],
            "final_score": f"{g['away']} {g['away_pts']} @ {g['home']} {g['home_pts']}"
                           + (" (OT)" if g["ot"] else "") + (" [neutral site]" if g["neutral"] else ""),
            "settled": True,
            "settled_reason": (
                "official FINAL score captured two-source by this session into "
                "data/live/results_2026_11_13_final.json (schedule card + the game's own page)"
                if from_live_finals else
                "official FINAL score transcribed to data/raw/games_completed.json"),
            "model_margin_home": pm, "actual_margin_home": margin, "abs_err_margin": g["abs_err_margin"],
            "model_total": pt, "actual_total": total, "abs_err_total": g["abs_err_total"],
            "side_pick": pick_side, "side_pick_correct": pick_won,
            "total_direction": t_dir,
            "total_direction_correct": 1 if t_dir in ("OVER", "UNDER") else 0,
            "trivial_by_construction": True,
            "note": "Graded against our own number. Correct here is ~50% by construction, "
                    "not evidence of edge.",
        })
    return rows


def main():
    lines = load("integration", "out", "lines.json")
    completed = load("data", "raw", "games_completed.json")
    inprog = load("data", "live", "results_2026_11_13_in_progress.json")
    slate = load("data", "live", "slate_2026_11_14_to_16.json")
    # D03 (COORDINATION §21): the 11/13 slate is now final. Games confirmed FINAL in the
    # two-source capture leave the "cannot settle" bucket and are graded with the backtest
    # rows; anything still not final there would stay blocked with its own source link.
    try:
        final13 = load("data", "live", "results_2026_11_13_final.json")
    except FileNotFoundError:
        final13 = {"games": []}
    final_ids = {g["game_id"] for g in final13["games"] if g.get("settled")}
    final_by_id = {g["game_id"]: g for g in final13["games"]}

    graded = grade_backtest(lines, final_ids)
    n_side = sum(1 for r in graded if r["side_pick_correct"] is not None)
    side_wins = sum(r["side_pick_correct"] or 0 for r in graded)
    errs_m = [r["abs_err_margin"] for r in graded]
    errs_t = [r["abs_err_total"] for r in graded]
    signed_m = [r["actual_margin_home"] - r["model_margin_home"] for r in graded]
    signed_t = [r["actual_total"] - r["model_total"] for r in graded]

    lo_m, hi_m = block_bootstrap([abs(e) for e in signed_m]) or (None, None)
    lo_t, hi_t = block_bootstrap([abs(e) for e in signed_t]) or (None, None)
    p_side = binom_two_sided(side_wins, n_side, 0.5)
    w_side = wilson(side_wins, n_side)

    # ---------------- what refuses to settle, and why (blank cells, never estimates)
    blocked = []
    for g in inprog["games"]:
        gid = g.get("game_id")
        if gid in final_ids:
            continue          # confirmed FINAL elsewhere — graded above, never double-listed
        fin = final_by_id.get(gid)
        blocked.append({
            "date": g.get("date", "2026-11-13"), "matchup": g.get("matchup"),
            "game_id": gid, "state": g.get("state"), "detail": g.get("detail"),
            "cup_group": g.get("cup_group"),
            "settled": False,
            "reason": ("still not FINAL in the two-source re-read either — non-FINAL rows are "
                       "unusable as results" if fin is None else
                       "the official card did not read FINAL when it was captured — non-FINAL "
                       "rows are unusable as results"),
            # Never fall back to the file-level URL: the earlier register pointed it at the
            # CHA@PHX box score of a different game (request R-X2). A blocked row gets its
            # own game page, or the date page, or nothing.
            "source_url": (fin.get("game_url") if fin else None)
                          or f"https://www.nba.com/games?date={g.get('date', '2026-11-13')}",
            "action": "re-fetch the same date page after the games end and re-run settle.py",
        })
    for g in slate["games"]:
        blocked.append({
            "date": g["date"], "matchup": f"{g['away']}@{g['home']}", "game_id": g["game_id"],
            "time_et": g.get("time_et"), "tip_status": "scheduled",
            "state": "SCHEDULED", "settled": False,
            "reason": "tip-off has not happened yet at capture time",
            "source_url": g["source_url"],
            "action": "this is a forward pick, not a result; it enters the ledger once FINAL",
        })

    out = {
        "graded_window": {"from": min(r["date"] for r in graded),
                          "to": max(r["date"] for r in graded),
                          "games": len(graded)},
        "side": {
            "record": f"{side_wins}-{n_side - side_wins}",
            "hit_rate": round(side_wins / n_side, 4) if n_side else None,
            "wilson_95": [round(w_side[0], 4), round(w_side[1], 4)] if w_side else None,
            "binom_two_sided_p_vs_coin": round(p_side, 4) if p_side is not None else None,
            "reading": "not a skill signal: the side pick is graded against our own number, so "
                       "coin-flip behaviour is expected. The p-value is shown to prove nothing "
                       "was hidden, not to claim an edge.",
        },
        "error_statistics": {
            "mae_margin": round(mean(errs_m), 3),
            "mae_margin_ci_95": [round(lo_m, 3), round(hi_m, 3)],
            "sd_margin": round(sd(signed_m), 3), "bias_margin": round(mean(signed_m), 3),
            "mae_total": round(mean(errs_t), 3),
            "mae_total_ci_95": [round(lo_t, 3), round(hi_t, 3)],
            "sd_total": round(sd(signed_t), 3), "bias_total": round(mean(signed_t), 3),
            "unit": "points per game; MAE is the number a bettor actually cares about because it "
                    "is what has to beat the spread to make money",
        },
        "rows": graded,
        "cannot_settle": blocked,
        "cannot_settle_count": len(blocked),
        "graded_count": len(graded),
        "provenance": {
            "results_file": "data/raw/games_completed.json",
            "finals_2026_11_13_file": "data/live/results_2026_11_13_final.json",
            "finals_2026_11_13_appended_at_load": len(final_ids),
            "in_progress_file": "data/live/results_2026_11_13_in_progress.json "
                                "(kept as provenance of the 00:47Z read; no longer the "
                                "settlement source for 11/13)",
            "note": "All are transcriptions of official NBA.com pages; see "
                    "data/live/capture_meta.json for the retrieval times. The 11/13 rows are "
                    "appended to the graded window by integration/model.py at load time — "
                    "data/raw/games_completed.json itself was not modified (request R-X1 "
                    "remains with the integration seat).",
        },
    }
    dump("settlement.json", out)
    print(f"settle · graded={len(graded)} blocked={len(blocked)} side={out['side']['record']} "
          f"MAE_m={out['error_statistics']['mae_margin']} MAE_t={out['error_statistics']['mae_total']}")
    return out


if __name__ == "__main__":
    main()
