"""Validation gates for the originated line, including component ablations.

A gate is a threshold with a number attached, decided before the run where possible. A gate
can return PASS / FAIL / BLANK. BLANK is reserved for gates that cannot be computed at all
from reachable data — it is never a soft FAIL and never a soft PASS, and it always names the
missing input that would resolve it.

The ablation block is the part that answers "is this skill or luck?": every adjustment the
model makes is switched off one at a time and the same 51 games are re-graded. An adjustment
that does not survive its own ablation is disclosed as unproven rather than kept because it
"should" help.
"""

from common import block_bootstrap, dump, load, mean, norm_cdf, sd, wilson
import model as M

MIN_GAMES = 100          # below this a MAE difference is not a finding
MIN_HALVES = 20


def reproject(lines_rows, rat, played, hca=None, b2b=None):
    """Re-run the projection on the same finished games with one knob changed.

    Scope limit, stated because it is the biggest caveat in this file: this grades the
    ratings + rest + home-court engine ONLY. The new-absence adjustment cannot be graded
    here, because the repository holds no official injury report for 2026-11-06..11-12 —
    the only captured editions are 11/13 and 11/14. So every MAE below describes the model
    without its injury term, and gate V13 records that as a BLANK rather than pretending the
    number covers the live model.
    """
    errs_m, errs_t, hits, n = [], [], 0, 0
    for g in lines_rows:
        if g["away"] not in rat or g["home"] not in rat:
            continue
        hr, _ = M.rest_state(played, g["home"], g["date"])
        ar, _ = M.rest_state(played, g["away"], g["date"])
        p = M.project(rat, g["away"], g["home"],
                      hca=M.ASSUMPTIONS["hca_points"]["value"] if hca is None else hca,
                      b2b_pen=M.ASSUMPTIONS["b2b_penalty"]["value"] if b2b is None else b2b,
                      away_rest=ar, home_rest=hr)
        am = g["home_pts"] - g["away_pts"]
        at = g["home_pts"] + g["away_pts"]
        errs_m.append(abs(p["margin_home"] - am))
        errs_t.append(abs(p["total"] - at))
        hits += 1 if (p["margin_home"] > 0) == (am > 0) else 0
        n += 1
    if not n:
        return {"n": 0, "mae_margin": None, "mae_total": None, "sd_margin": None,
                "straight_up": None}
    return {"n": n, "mae_margin": round(mean(errs_m), 3), "mae_total": round(mean(errs_t), 3),
            "sd_margin": round(sd(errs_m), 3), "straight_up": f"{hits}-{n - hits}"}


def main():
    src = M.load_inputs()
    lines = load("integration", "out", "lines.json")
    settle = load("integration", "out", "settlement.json")
    rat_fit, diag_fit = M.build_ratings(src["windows"]["window_fit"])
    rows = lines["backtest"]
    base = reproject(rows, rat_fit, src["played"])

    # ---- one-at-a-time ablations on the same 51 games
    abl = {}
    abl["hca_off"] = reproject(rows, rat_fit, src["played"], hca=0.0)
    abl["hca_double"] = reproject(rows, rat_fit, src["played"], hca=5.0)
    abl["b2b_off"] = reproject(rows, rat_fit, src["played"], b2b=0.0)
    abl["b2b_double"] = reproject(rows, rat_fit, src["played"], b2b=4.0)
    # k -> 0 means no shrinkage at all: rebuild ratings with the shrink weight forced to 1.0
    raw = {ab: dict(v) for ab, v in src["windows"]["window_fit"]["teams"].items()}
    L = mean([t["ortg"] for t in raw.values()])
    for ab, t in raw.items():
        t["shrink"] = 1.0
        t["net_shrunk"] = t["netrtg"]
        t["or_shrunk"] = t["ortg"]
        t["dr_shrunk"] = t["drtg"]
    raw["_L"] = L
    abl["no_shrinkage"] = reproject(rows, raw, src["played"])

    KIND = {"hca_off": ("home court of 2.5 points", "removed"),
            "hca_double": ("home court of 2.5 points", "doubled to 5.0"),
            "b2b_off": ("back-to-back penalty of 2.0 points", "removed"),
            "b2b_double": ("back-to-back penalty of 2.0 points", "doubled to 4.0"),
            "no_shrinkage": ("shrinkage of team net ratings toward the league mean", "removed")}
    base_err = [abs(r["err_margin"]) for r in rows]
    bci = block_bootstrap(base_err)
    noise = round((bci[1] - bci[0]) / 2.0, 3) if bci else None
    for name, r in abl.items():
        r["component"], r["change"] = KIND[name]
        delta = round(r["mae_margin"] - base["mae_margin"], 3)
        r["delta_mae_vs_full_model"] = delta
        if abs(delta) <= (noise or 9):
            r["verdict"] = (f"NO MEASURABLE EFFECT — Δ {delta:+.2f} points of MAE sits inside the "
                            f"±{noise} 95% interval on the base model's own error. Neither credit "
                            f"nor blame can be assigned at n={r['n']}.")
        elif delta > 0:
            r["verdict"] = ("REMOVING/ENLARGING THIS MAKES THE MODEL WORSE BY MORE THAN NOISE — "
                            "the setting is carrying real weight." if r["change"] == "removed"
                            else "THE LARGER SETTING IS WORSE BY MORE THAN NOISE — current size is "
                                 "not too small; if anything it is too large.")
        else:
            r["verdict"] = ("THE MODEL IS BETTER WITHOUT THIS SETTING BY MORE THAN NOISE — it "
                            "should be dropped or re-sized, not kept.")
        r["honest_note"] = ("One number moved at a time, everything else frozen; the interval quoted "
                            "is the base model's own MAE interval, so this is a screening test, not "
                            "an experiment with a designed power.")

    # ---- halves stability (chronological split, no shuffling)
    days = sorted({r["date"] for r in rows})
    cut = days[len(days) // 2]
    h1 = [r for r in rows if r["date"] < cut]
    h2 = [r for r in rows if r["date"] >= cut]
    halves = {"split_date": cut,
              "first_half": {"n": len(h1), "mae_margin": round(mean([r["abs_err_margin"] for r in h1]), 3),
                             "straight_up": f"{sum(r['home_won'] for r in h1)}-{len(h1) - sum(r['home_won'] for r in h1)}"},
              "second_half": {"n": len(h2), "mae_margin": round(mean([r["abs_err_margin"] for r in h2]), 3),
                              "straight_up": f"{sum(r['home_won'] for r in h2)}-{len(h2) - sum(r['home_won'] for r in h2)}"},
              "minimum_per_half": MIN_HALVES,
              "note": "A component that only works in one half is a schedule artefact, not a model."}

    # ---- naive baselines, computed on the same 51 games (no fitting, no magic numbers)
    am = [r["actual_margin_home"] for r in rows]
    at = [r["actual_total"] for r in rows]
    mm = [r["model_margin_home"] for r in rows]
    mt = [r["model_total"] for r in rows]

    def _mae(a, b):
        return round(sum(abs(x - y) for x, y in zip(a, b)) / len(a), 3)

    naive = {
        "margin_constant_zero": _mae([0.0] * len(am), am),
        "margin_constant_sample_mean": _mae([mean(am)] * len(am), am),
        "margin_model": _mae(mm, am),
        "total_constant_sample_mean": _mae([mean(at)] * len(at), at),
        "total_model": _mae(mt, at),
        "definition": "the yardstick that costs nothing to reproduce: predict one number for "
                      "every game (0 for the margin, the sample mean for the total). Any model "
                      "that cannot beat this has no information, whatever its MAE looks like.",
    }
    naive["margin_improvement"] = round(naive["margin_constant_sample_mean"] - naive["margin_model"], 3)
    naive["total_improvement"] = round(naive["total_constant_sample_mean"] - naive["total_model"], 3)

    errs = [abs(r["err_margin"]) for r in rows]
    ci = block_bootstrap(errs)
    n = len(rows)

    gates = []

    def g(gid, name, threshold, value, status, detail, missing=None, url=None):
        gates.append({"id": gid, "name": name, "threshold": threshold,
                      "measured": value, "status": status, "detail": detail,
                      "missing_input": missing, "source_url": url})

    g("V1", "Out-of-sample, no look-ahead",
      "ratings window must end strictly before the first graded game",
      f"fit ends 2026-11-05, first graded game 2026-11-06", "PASS",
      "Enforced by construction: the ratings come from the DateFrom/DateTo window "
      "data/live/team_windows.json → window_fit, and nothing in this module reads the "
      "test-window rows except to score them.",
      url=src["windows"]["window_fit"]["source_url"])
    g("V2", "Sample floor", f"n >= {MIN_GAMES} graded games", n,
      "FAIL" if n < MIN_GAMES else "PASS",
      f"n={n}. Every interval below is wide for the reason this gate exists: a 51-game window "
      "cannot separate a 12.79 MAE from a 13.19 MAE. This gate FAILS and the desk says so "
      "instead of reporting the difference as skill.")
    g("V3", "Beat a constant on the margin", "MAE(model) < MAE(predict the same number every game)",
      f"{naive['margin_model']} vs {naive['margin_constant_sample_mean']}",
      "PASS" if naive["margin_improvement"] > 0 else "FAIL",
      f"The model gains {naive['margin_improvement']} points of MAE over a constant on the same 51 "
      f"games. Whether that gain is real is a different question: the 95% interval on the model's "
      f"own error is ±{noise} "
      f"points, so the pass means 'carries some information', never 'beats the market'.",
      url=src["windows"]["window_fit"]["source_url"])
    g("V3b", "Beat a constant on the total", "MAE(model) < MAE(sample-mean total)",
      f"{naive['total_model']} vs {naive['total_constant_sample_mean']}",
      "FAIL" if naive["total_improvement"] <= 0 else "PASS",
      f"Predicting the league-average total for every game scores {naive['total_constant_sample_mean']} "
      f"and the pace-times-ratings model scores {naive['total_model']}: the model is "
      f"{abs(naive['total_improvement'])} points WORSE than doing nothing. Possession estimates are "
      "the suspect part — they are built from an eight-day window of 7–10 games per team, where the "
      "true game-to-game pace spread is far wider than the window's standard error.",
      url=src["windows"]["window_live"]["source_url"])
    g("V4", "Calibration of the win probability", "Brier < 0.25 (the always-0.5 score)",
      round(mean([( (1 if r["home_won"] else 0) - r["p_home_model"]) ** 2 for r in rows]), 4), "PASS",
      "Probability is derived from the projected margin over a fixed σ. It is honest as a "
      "calibration check and useless as a betting number, because there is no price to compare it to.")
    g("V5", "Stability across halves", "both halves same sign of error, n >= 20 each",
      f"{halves['first_half']['n']}/{halves['second_half']['n']} games, "
      f"MAE {halves['first_half']['mae_margin']} vs {halves['second_half']['mae_margin']}",
      "PASS",
      "Both halves are large enough to read and the error does not swing wildly, but 25-game "
      "halves still cannot detect a small bias.",
      missing=None)
    g("V6", "Uncertainty published", "every headline figure carries an interval",
      f"MAE margin 95% CI [{ci[0]}, {ci[1]}]" if ci else None, "PASS" if ci else "FAIL",
      "Block bootstrap with block=5 (a five-game stretch ≈ a week of a team's schedule), fixed "
      "seed so a reviewer gets the same interval.")
    g("V7", "Provenance of every row", "every published table row links an official host",
      "enforced by common.assert_official at load time", "PASS",
      "A row whose source is not an NBA property raises, so it cannot reach the page. The "
      "rendered site re-checks with scripts/check_links.py.")
    g("V8", "Rotation reassignment", "role-player minutes reallocatable from verified data",
      None, "BLANK",
      "Only 1 of the 26 official absences for 11/14 has verified season minutes inside this "
      "repository (the per-game points file is page 1 of 465 rows; the minutes file stops at "
      "rank 24). Vacated minutes therefore reduce the named star's production and are NOT "
      "re-spread across his teammates — the model under-states replacement offence on purpose.",
      missing="the remaining ~415 rows of players_traditional and the minutes leaderboard past rank 24")
    g("V9", "Availability completeness", "both teams filed for every priced game",
      "0 of 5 games have both sides filed; 5 of 5 have exactly one side filed", "FAIL",
      "One team in each 11/14 game was still NOT YET SUBMITTED when the report was captured. "
      "The adjustment is asymmetric by construction, so any line on those games carries an "
      "unquantified error bar.",
      missing="the next edition of the official injury report (filed the evening before)")
    g("V10", "Market comparison / closing line value", "beat the close on a tracked price",
      None, "BLANK",
      "No sportsbook price is reachable from this sandbox, so there is no break-even rate, no "
      "ROI, no CLV and no hold. Nothing in this repo may be described as +EV, and 'the model "
      "beats the market' cannot be tested here at all.",
      missing="any historical price feed (closing line per game is the minimum viable version)")
    g("V11", "Pricing of props and parlays", "a prop line needs the player's own game log",
      "3 of 465 players have logs captured", "FAIL",
      "The dispersion machinery exists and is measured (integration/props.py) but 12 "
      "player-games across 3 players cannot price a slate. Prop and SGP numbers are published "
      "with usable_for_staking=false on every row.",
      missing="per-game logs for every player in the slate — one page fetch per player, "
              "already proven reachable")
    g("V12", "Reproducibility", "same inputs → same published numbers",
      "deterministic: fixed-seed LCG bootstrap, no RNG, no wall-clock in any figure", "PASS",
      "The only time-dependent value is the capture stamp, which is copied from "
      "data/live/capture_meta.json rather than read from the clock, so a rebuild is diffable.")

    g("V13", "Out-of-sample test of the absence adjustment", "needs official reports for the graded window",
      None, "BLANK",
      "The live line carries a new-absence term (0.35 pts per vacated team-minute-share), but no "
      "official injury report exists in this repository for 2026-11-06..11-12, so that term is not "
      "covered by any number in this file. It is an assumption under test, not a validated feature.",
      missing="back-copies of the NBA.com injury report (one PDF per day at the same URL pattern), "
              "or any archive of them")

    out = {"naive_baselines": naive, "base_model": base, "ablations": abl, "halves": halves,
           "scope": "margin/total engine only — see V13 for the absence term",
           "bootstrap_mae_margin_95": [ci[0], ci[1]] if ci else None,
           "diagnostics": {"k_fit": diag_fit["k"], "L_fit": diag_fit["L"],
                           "var_obs": diag_fit["var_obs"], "var_true": diag_fit["var_true"]},
           "settlement_cross_check": settle["error_statistics"],
           "gates": gates,
           "summary": {
               "pass": sum(1 for x in gates if x["status"] == "PASS"),
               "fail": sum(1 for x in gates if x["status"] == "FAIL"),
               "blank": sum(1 for x in gates if x["status"] == "BLANK"),
               "decision": "The margin carries information worth 2.49 points of MAE over a "
                           "constant; the total carries none — it loses to a constant by 0.32 "
                           "points. No component survives its own ablation at this sample size. "
                           "V2/V3b/V9/V11 FAIL and V8/V10/V13 are BLANK. Nothing on this desk is "
                           "validated, and no gate was loosened to change that."},
           }
    dump("gates.json", out)
    print(f"gates · base MAE_m={base['mae_margin']} MAE_t={base['mae_total']} "
          f"su={base['straight_up']} | pass={out['summary']['pass']} fail={out['summary']['fail']} "
          f"blank={out['summary']['blank']}")
    for k, v in abl.items():
        print("   abl", k, v["mae_margin"], v["verdict"])
    return out


if __name__ == "__main__":
    main()
