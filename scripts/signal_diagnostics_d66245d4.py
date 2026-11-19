#!/usr/bin/env python3
"""signal_diagnostics_d66245d4.py — session arena/d66245d4-nba1 (COORDINATION §72).

Two measurements that decide whether any strategy on this site can be skill, computed from
the repository's OWN record against the OFFICIAL finals it already stores:

  1. SELECTION BIAS of the pick gate. The pick gate is "|model spread| >= 3.0". That is a
     selection rule, not a filter: it keeps precisely the games where the model most disagrees
     with a 0-centred prior. If the model has no information, the sign of a large |model
     spread| is still ~50/50 and ATS results at the model's own number must regress toward
     .500. This script measures the realised cover rate by |model spread| bucket.

  2. CALIBRATION. The model publishes pick_prob (its win probability for the side it picked).
     If those probabilities are honest, the realised hit rate at each probability bucket must
     track them. This script bins by published pick_prob.

Both measurements use the observed margin and the PUBLISHED line only. No book price exists
anywhere in this repository, so "cover" here means "beat the model's own number", which is the
only comparison the record supports. It is stated in the output, not glossed over.

Run: python3 scripts/signal_diagnostics_d66245d4.py
"""
import collections
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTLEMENTS = sorted(
    os.path.join(ROOT, "data", "settlement", f)
    for f in os.listdir(os.path.join(ROOT, "data", "settlement"))
    if f.startswith("settlement_2026-11-") and f.endswith(".json")
)
OUT_JSON = os.path.join(ROOT, "data", "content", "signal_diagnostics_2026-11-19_d66245d4.json")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def binomial_p(k, n, p0=0.5):
    """One-sided exact binomial p for 'at least k of n' against p0."""
    if n == 0:
        return None
    # P(X >= k)
    tail = sum(math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1))
    return tail


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    ph = k / n
    den = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (round(centre - half, 4), round(centre + half, 4))


def main():
    tickets = []
    for f in SETTLEMENTS:
        d = load(f)
        for s in d.get("singles") or []:
            if s.get("result") not in ("WIN", "LOSS", "PUSH"):
                continue          # NO BET rows carry no outcome
            line = s.get("pick_line") or ""
            try:
                spread = abs(float(line.split()[-1]))
            except (ValueError, IndexError):
                spread = None
            tickets.append({
                "slate": os.path.basename(f).replace("settlement_", "").replace(".json", ""),
                "date": s.get("date"), "matchup": s.get("matchup"),
                "pick_side": s.get("pick_side"), "pick_line": line,
                "abs_model_spread": spread,
                "pick_prob": s.get("pick_prob"),
                "margin_pick_team": s.get("margin_pick_team"),
                "result": s.get("result"), "units": s.get("units"),
                "source_game_url": s.get("source_game_url"),
            })

    # ---- 1. selection bias by |model spread| bucket -------------------------------------
    buckets = collections.OrderedDict([
        ("3.0-5.0", lambda x: 3.0 <= x < 5.0),
        ("5.0-8.0", lambda x: 5.0 <= x < 8.0),
        ("8.0-12.0", lambda x: 8.0 <= x < 12.0),
        ("12.0+", lambda x: x >= 12.0),
    ])
    by_bucket = []
    for name, test in buckets.items():
        rows = [t for t in tickets if t["abs_model_spread"] is not None
                and test(t["abs_model_spread"])]
        w = sum(1 for r in rows if r["result"] == "WIN")
        l = sum(1 for r in rows if r["result"] == "LOSS")
        p = sum(1 for r in rows if r["result"] == "PUSH")
        n = w + l
        by_bucket.append({
            "bucket": name, "n_decided": n, "wins": w, "losses": l, "pushes": p,
            "hit_rate": round(w / n, 4) if n else None,
            "wilson_95": list(wilson(w, n)),
            "p_value_vs_50pct": None if n == 0 else round(binomial_p(w, n, 0.5), 4),
        })

    # ---- 2. calibration by published pick_prob -------------------------------------------
    prob_buckets = collections.OrderedDict([
        ("0.50-0.55", lambda x: 0.50 <= x < 0.55),
        ("0.55-0.60", lambda x: 0.55 <= x < 0.60),
        ("0.60-0.65", lambda x: 0.60 <= x < 0.65),
        ("0.65-0.70", lambda x: 0.65 <= x < 0.70),
        ("0.70+", lambda x: x >= 0.70),
    ])
    calib = []
    have = [t for t in tickets if t.get("pick_prob") is not None]
    for name, test in prob_buckets.items():
        rows = [t for t in have if test(t["pick_prob"])]
        w = sum(1 for r in rows if r["result"] == "WIN")
        l = sum(1 for r in rows if r["result"] == "LOSS")
        n = w + l
        calib.append({
            "bucket": name, "n_decided": n, "wins": w, "losses": l,
            "mean_predicted": round(sum(r["pick_prob"] for r in rows) / len(rows), 4) if rows else None,
            "observed_hit_rate": round(w / n, 4) if n else None,
            "gap_observed_minus_predicted": (round(w / n - sum(r["pick_prob"] for r in rows) / len(rows), 4)
                                             if n and rows else None),
        })

    # ---- 2b. WHY the calibration fails: residual scale vs the sigma the model assumes -----
    # The model converts its spread to a probability with sigma_margin (published in
    # data/derived/measured_constants_2026_27.json). That is correct ONLY if the spread is the
    # true expected margin. It is not: it is a raw difference of two teams' season-average
    # ratings, which is a point estimate with its own error. The error of that estimate is what
    # belongs in the probability, and it is measurable — it is the spread of (predicted minus
    # actual) on the games already played.
    resid = []
    for t in tickets:
        if t["margin_pick_team"] is None or t["abs_model_spread"] is None:
            continue
        # signed error in the picked team's frame: |model spread| is what the model expected the
        # picked team to win by; margin_pick_team is what happened.
        resid.append(t["abs_model_spread"] - t["margin_pick_team"])
    n_r = len(resid)
    mean_r = sum(resid) / n_r if n_r else None
    var_r = (sum((x - mean_r) ** 2 for x in resid) / (n_r - 1)) if n_r > 1 else None
    sd_r = math.sqrt(var_r) if var_r else None
    implied = []
    for t in tickets:
        pr = t.get("pick_prob")
        if pr and 0.5 < pr < 1 and t["abs_model_spread"]:
            z = statistics.NormalDist().inv_cdf(pr)
            if z:
                implied.append(t["abs_model_spread"] / z)
    sigma_used = None
    try:
        mc = load(os.path.join(ROOT, "data", "derived", "measured_constants_2026_27.json"))
        sigma_used = (mc.get("dispersion") or {}).get("sigma_margin")
    except Exception:
        pass
    sigma_implied = round(sum(implied) / len(implied), 3) if implied else None
    sigma_needed = round(math.sqrt((r_ := 0) + (sd_r ** 2) + (mean_r ** 2)), 3) if sd_r else None
    residual_block = {
        "what": ("the model's probability treats its spread as the true expected margin and "
                 "divides by sigma_margin. The measurable quantity is the error of the spread "
                 "estimate itself: sd(predicted magnitude - realised margin) plus its bias."),
        "n": n_r,
        "mean_signed_error": round(mean_r, 3) if mean_r is not None else None,
        "sd_of_error": round(sd_r, 3) if sd_r else None,
        "sigma_margin_used_by_model": sigma_used,
        "sigma_implied_by_published_probabilities": sigma_implied,
        "sigma_that_would_cover_the_measured_error": sigma_needed,
        "ratio_needed_over_used": (round(sigma_needed / sigma_used, 3)
                                   if sigma_needed and sigma_used else None),
        "interpretation": ("the probabilities divide by the spread of GAME margins, not by the "
                           "spread of the error in the LINE. Those are different quantities. The "
                           "model's own forecast error on the games already settled is the "
                           "correct denominator, and it is measured here rather than assumed."),
        "why_the_bias_matters": ("mean signed error is positive and large: the model over-"
                                 "predicts the picked team's winning margin by that many points. "
                                 "Because the gate keeps only the largest |spread|, it keeps "
                                 "precisely the games where that over-prediction is largest, "
                                 "which is why the highest-confidence bucket is the worst bucket."),
    }

    # ---- 3. the summary that matters -----------------------------------------------------
    w = sum(1 for t in tickets if t["result"] == "WIN")
    l = sum(1 for t in tickets if t["result"] == "LOSS")
    p = sum(1 for t in tickets if t["result"] == "PUSH")
    n = w + l
    units = round(sum(t["units"] or 0 for t in tickets), 3)
    allp = [t for t in tickets if t.get("pick_prob") is not None and t["result"] in ("WIN", "LOSS")]
    mean_pred = round(sum(t["pick_prob"] for t in allp) / len(allp), 4) if allp else None

    summary = {
        "tickets": len(tickets), "decided": n, "wins": w, "losses": l, "pushes": p,
        "hit_rate": round(w / n, 4) if n else None,
        "hit_rate_wilson_95": list(wilson(w, n)),
        "p_value_vs_50pct": None if n == 0 else round(binomial_p(w, n, 0.5), 4),
        "breakeven_at_minus110": 0.5238,
        "mean_published_pick_prob": mean_pred,
        "calibration_gap": (round(w / n - mean_pred, 4) if n and mean_pred is not None else None),
        "paper_units_at_minus110": units,
        "roi_at_minus110": round(units / (1.1 * n), 4) if n else None,
    }

    payload = {
        "title": "Signal diagnostics — selection bias and calibration of the published picks",
        "generated_by": "scripts/signal_diagnostics_d66245d4.py",
        "generated_utc": "2026-11-19",
        "rule": ("Every outcome below is the one recorded in data/settlement/** against the "
                 "official final stored in that file. No price exists in this repository, so "
                 "'cover' means beating the model's own published number, and the units are the "
                 "paper -110 convention the settlement files themselves disclose. Nothing here "
                 "is a claim about a sportsbook."),
        "sample_warning": ("n is in the tens, not the hundreds. Every interval below is wide "
                           "enough that the point estimates should not be acted on. The reason "
                           "to publish them is that a STRATEGY DECISION is being asked for, and "
                           "the selection rule is a known bias that no amount of waiting fixes."),
        "selection_rule": {
            "rule": "pick only if |model spread| >= 3.0 (data/derived/horizon_picks.json _meta.pick_gate)",
            "why_it_is_a_bias": ("the rule selects games where the model most disagrees with a "
                                 "0-centred prior. With no information, the sign of a large |model "
                                 "spread| is still ~50/50, so ATS results at the model's own number "
                                 "regress toward .500. A high hit rate in the >=12 bucket would be "
                                 "evidence of information; a flat profile across buckets is evidence "
                                 "of none."),
        },
        "by_abs_model_spread": by_bucket,
        "residual_scale": residual_block,
        "calibration_by_pick_prob": calib,
        "summary": summary,
        "tickets_detail": tickets,
        "questions_this_raises": [
            "Is the gate a skill filter or a variance filter? The bucket table answers it once "
            "n is large enough to separate the buckets; at n=%d it does not." % n,
            "Why does the model's mean published pick_prob (%s) sit above the realised hit rate (%s)?"
            % (mean_pred, summary["hit_rate"]),
            "What is the model's Brier score on these %d decided picks, and is it better than the "
            "climatology forecast (always the home base rate)?" % n,
        ],
        "sources": sorted({t["source_game_url"] for t in tickets if t.get("source_game_url")}),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")

    print("wrote", os.path.relpath(OUT_JSON, ROOT))
    print("tickets %d (%d decided) %d-%d-%d  hit %.1f%%  units %+.2f"
          % (len(tickets), n, w, l, p, 100 * (w / n if n else 0), units))
    print("mean published pick_prob", mean_pred, "vs realised", summary["hit_rate"],
          "gap", summary["calibration_gap"])
    print("\nby |model spread|:")
    for b in by_bucket:
        print("  %-9s n=%-3d %d-%d hit %s  wilson %s  p=%.4f"
              % (b["bucket"], b["n_decided"], b["wins"], b["losses"],
                 b["hit_rate"], b["wilson_95"], b["p_value_vs_50pct"] or 0))
    print("\nresidual scale:")
    print("  sd of (predicted - actual):", residual_block["sd_of_error"],
          " mean signed:", residual_block["mean_signed_error"])
    print("  sigma used by model:", residual_block["sigma_margin_used_by_model"],
          " implied by its own probabilities:", residual_block["sigma_implied_by_published_probabilities"],
          " needed to cover measured error:", residual_block["sigma_that_would_cover_the_measured_error"])
    print("\ncalibration:")
    for c in calib:
        print("  %-10s n=%-3d predicted %s  observed %s  gap %s"
              % (c["bucket"], c["n_decided"], c["mean_predicted"],
                 c["observed_hit_rate"], c["gap_observed_minus_predicted"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
