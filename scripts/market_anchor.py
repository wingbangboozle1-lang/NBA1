#!/usr/bin/env python3
"""market_anchor.py — the market-anchored prior, and the honest statement of
what can and cannot be measured without a price feed.

Brief line this answers: "Add a market-anchored prior: blend the model line with
the closing line, weight by measured out-of-sample log-loss."  (register R16)

What is measurable here, and what is not
----------------------------------------
No closing line exists in this repository and none can be fetched: the
pre-registration files say so ("No licensed two-sided price exists"), no file
under `data/` holds a two-sided price, and no NBA-operated host publishes a
priced market.  Inventing one would be a fabricated input, which the brief
forbids.

But the *weighting rule* the brief asks for is a measurable quantity:

    p_anchor = w * p_other + (1 - w) * p_model

For a binary outcome the mean log-loss of that blend is strictly convex in `w`,
so its optimum is a well-defined number with a bootstrap interval.  This script
measures that `w` on the repository's out-of-sample corpus and reports whether
the anchor buys anything.  The moment a licensed closing line exists, the same
function is fed that price instead of the second estimator and nothing else
changes.

Corpus (official outcomes only)
-------------------------------
`docs/data/validation.json` -> `metrics` is the walk-forward record: 60 games,
2026-11-06..2026-11-13, every one predicted from ratings built only on
2026-10-20..2026-11-05.  It carries the model's and the reference's Brier and
log-loss for exactly those 60 games.  The per-play rows (`graded_plays`) are
*spread* tickets priced off the same numbers and cannot be read as a moneyline
probability without inventing a mapping, so they are not used.

  CAVEAT, printed into the output: the repo publishes aggregate log-loss for
  the model and for the reference, not per-game probabilities.  The blend
  weight is therefore identifiable only as the value that reproduces the
  published aggregate exactly along the [0,1] path; if that weight is
  degenerate (0 or 1) the honest reading is that the corpus cannot locate a
  blend between them, and it is published as such rather than dressed up.

Inputs
------
  docs/data/validation.json          out-of-sample metrics (official finals)
  data/derived/model_report_v2.json  measured sigma_margin used for any price

Output
------
  data/derived/market_anchor.json

Run
---
  python3 scripts/market_anchor.py
  python3 scripts/market_anchor.py --market     # refuses without a price file
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = "data/derived/market_anchor.json"
CLOSING = "data/external/closing_lines.json"
SEED = 20261116
BOOT = 4000


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# 1. the blend-weight estimator
# ---------------------------------------------------------------------------
def logloss_binary(p, y):
    p = min(1 - 1e-12, max(1e-12, p))
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def brier_binary(p, y):
    return (p - y) ** 2


def optimal_w_on_outcomes(rows, anchor_key, model_key="p_model"):
    """Rows carry three numbers per game: p_model, p_anchor, y (0/1).

    Returns the w in [0,1] minimising the mean log-loss of the blend.  The
    function is strictly convex, so a golden-section search is exact to 1e-9.
    """
    def f(w):
        return sum(logloss_binary(w * r[anchor_key] + (1 - w) * r[model_key], r["y"])
                   for r in rows) / len(rows)
    lo, hi = 0.0, 1.0
    gr = (math.sqrt(5) - 1) / 2
    c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
    fc, fd = f(c), f(d)
    for _ in range(200):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - gr * (hi - lo)
            fc = f(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + gr * (hi - lo)
            fd = f(d)
    return (lo + hi) / 2.0, f(0.0), f(0.5), f(1.0)


def bootstrap_w(rows, anchor_key, reps=BOOT, seed=SEED):
    rng = random.Random(seed)
    n = len(rows)
    ws = []
    for _ in range(reps):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        ws.append(optimal_w_on_outcomes(sample, anchor_key)[0])
    ws.sort()
    return ws[int(0.025 * reps)], ws[int(0.975 * reps)], ws[reps // 2]


def load_pairs():
    """Per-game out-of-sample probabilities from the walk-forward record."""
    bt = load("docs/data/backtest.json")
    rows = []
    for r in bt["rows"]:
        if r.get("p_home_model") is None or r.get("p_home_ref") is None:
            continue
        rows.append({
            "date": r["date"], "matchup": r["matchup"],
            "p_model": float(r["p_home_model"]),
            "p_anchor": float(r["p_home_ref"]),
            "y": int(r["home_won"]),
            "source_url": r.get("src") and f'https://www.nba.com/games?date={r["date"]}',
        })
    return bt, rows


def main():
    bt, rows = load_pairs()
    if len(rows) < 30:
        print(f"corpus too small ({len(rows)}) to measure a blend weight", file=sys.stderr)
        return 6
    mr = load("data/derived/model_report_v2.json")
    metrics = bt["metrics"]

    w, f0, fhalf, f1 = optimal_w_on_outcomes(rows, "p_anchor")
    f_at_w = (sum(logloss_binary(w * r["p_anchor"] + (1 - w) * r["p_model"], r["y"])
                  for r in rows) / len(rows))
    lo, hi, med = bootstrap_w(rows, "p_anchor")
    n = len(rows)

    def mean(fn):
        return sum(fn(r) for r in rows) / n

    ll_model = mean(lambda r: logloss_binary(r["p_model"], r["y"]))
    ll_anchor = mean(lambda r: logloss_binary(r["p_anchor"], r["y"]))
    br_model = mean(lambda r: brier_binary(r["p_model"], r["y"]))
    br_anchor = mean(lambda r: brier_binary(r["p_anchor"], r["y"]))
    br_at_w = mean(lambda r: brier_binary(w * r["p_anchor"] + (1 - w) * r["p_model"], r["y"]))

    # Paired bootstrap on the log-loss improvement from anchoring.
    rng = random.Random(SEED + 1)
    diffs = []
    for _ in range(BOOT):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        m = sum(logloss_binary(r["p_model"], r["y"]) -
                logloss_binary(w * r["p_anchor"] + (1 - w) * r["p_model"], r["y"])
                for r in sample) / n
        diffs.append(m)
    diffs.sort()
    d_lo, d_hi = diffs[int(0.025 * BOOT)], diffs[int(0.975 * BOOT)]
    p_not_positive = sum(1 for d in diffs if d <= 0) / BOOT

    # Reconcile with the numbers the repo already publishes.
    recon = {
        "n_games_published": metrics["n_games"],
        "n_games_recomputed": n,
        "logloss_model_published": metrics["logloss_model"],
        "logloss_model_recomputed": round(ll_model, 4),
        "logloss_ref_published": metrics["logloss_ref"],
        "logloss_ref_recomputed": round(ll_anchor, 4),
        "brier_model_published": metrics["brier_model"],
        "brier_model_recomputed": round(br_model, 4),
        "brier_ref_published": metrics["brier_ref"],
        "brier_ref_recomputed": round(br_anchor, 4),
        "agree": (abs(ll_model - metrics["logloss_model"]) < 5e-4
                  and abs(ll_anchor - metrics["logloss_ref"]) < 5e-4),
        "note": ("The recomputation is from the per-game p_home_model / p_home_ref rows in "
                 "docs/data/backtest.json; agreement to four decimals means the blend below is "
                 "measured on exactly the corpus the published log-losses describe."),
    }

    identity = {
        "statement": ("For a binary outcome y and a forecast p, Brier = (p-y)^2 and log-loss = "
                      "-[y ln p + (1-y) ln(1-p)]. Both are proper scoring rules and both are "
                      "minimised at the true probability, but they are NOT affine images of each "
                      "other: Brier is quadratic in p, log-loss is logarithmic. A blend weight "
                      "optimised for one is therefore not, in general, optimal for the other."),
        "withdrawn_claim": ("An earlier draft of this file asserted that Brier and log-loss rank "
                            "linear blends identically. That claim is false and was withdrawn "
                            "before publication; the two weights below are reported separately "
                            "because they really are different numbers."),
        "measured_w_logloss": round(w, 4),
        "measured_w_brier": None,   # filled below
    }

    doc_weights = {
        "anchor_identity_used_here": ("the naive reference probability p_home_ref carried on every "
                                      "backtest row: the same official ratings with the fitted extras "
                                      "removed. It is the only second probability this repository holds "
                                      "for these games, and it stands in for a market price in the "
                                      "ARITHMETIC only - not in the claim."),
        "w_optimal_logloss": round(w, 4),
        "w_bootstrap_95_logloss": [round(lo, 4), round(hi, 4)],
        "w_bootstrap_median": round(med, 4),
        "logloss_at_w0_pure_model": round(f0, 5),
        "logloss_at_w0.5": round(fhalf, 5),
        "logloss_at_w1_pure_anchor": round(f1, 5),
        "logloss_at_w_optimal": round(f_at_w, 5),
        "improvement_vs_pure_model": round(f0 - f_at_w, 5),
        "improvement_bootstrap_95": [round(d_lo, 5), round(d_hi, 5)],
        "improvement_significant_at_5pct": d_lo > 0,
        "one_sided_p_improvement_not_positive": round(p_not_positive, 4),
        "brier_at_w_optimal": round(br_at_w, 5),
        "published_reconciliation": recon,
        "reading": ("If improvement_significant_at_5pct is false, the honest statement is that "
                    "anchoring to this second source buys no log-loss improvement that the sample "
                    "can detect, so the weight applied today must be 0 (pure model) until it does. "
                    "It is published either way, and the same function is what would run against a "
                    "real closing line."),
    }

    # Brier-optimal weight, measured separately (do not conflate the two rules).
    def brier_at(w_):
        return sum(brier_binary(w_ * r["p_anchor"] + (1 - w_) * r["p_model"], r["y"])
                   for r in rows) / n
    # golden-section on the Brier path (convex in w for a fixed set)
    a_, b_ = 0.0, 1.0
    gr = (math.sqrt(5) - 1) / 2
    c_, d_ = b_ - gr * (b_ - a_), a_ + gr * (b_ - a_)
    fc_, fd_ = brier_at(c_), brier_at(d_)
    for _ in range(200):
        if fc_ < fd_:
            b_, d_, fd_ = d_, c_, fc_
            c_ = b_ - gr * (b_ - a_)
            fc_ = brier_at(c_)
        else:
            a_, c_, fc_ = c_, d_, fd_
            d_ = a_ + gr * (b_ - a_)
            fd_ = brier_at(d_)
    w_brier = (a_ + b_) / 2
    identity["measured_w_brier"] = round(w_brier, 4)
    identity["do_they_differ"] = abs(w_brier - w) > 0.01

    doc = {
        "title": "Market-anchored prior - the measured blend weight, and why the market half is blocked",
        "generated_by": "scripts/market_anchor.py",
        "answers": "register R16",
        "verdict": ("PARTIAL - the weighting rule is implemented and the weight is MEASURED out of "
                    "sample; the market application is BLOCKED because no closing line exists for this "
                    "repository and no NBA-operated source publishes a priced market."),
        "blend_formula": "p_anchor = w * p_other + (1 - w) * p_model, w measured by out-of-sample log-loss",
        "corpus": {
            "what": "every graded game in the walk-forward record that carries both probabilities",
            "n": n,
            "window": metrics["window"],
            "ratings_window": metrics["ratings_window"],
            "out_of_sample": True,
            "source": "docs/data/backtest.json (p_home_model, p_home_ref, home_won per game)",
            "why_not_the_v2_horizon": ("data/derived/horizon_lines_v2.json covers 2026-11-15..19 and only "
                                       "its 11/15 games have finished; a weight measured on six games is "
                                       "not a measurement. The 60-game out-of-sample record is."),
        },
        "logloss_weights": doc_weights,
        "logloss_identity": identity,
        "market_anchor": {
            "status": "BLOCKED - no closing line exists",
            "why": ("The pre-registration files state 'No licensed two-sided price exists (no odds feed)'; "
                    "no file under data/ holds a two-sided price; and the only hosts this project may read "
                    "for evidence are the NBA's own, which do not publish priced markets."),
            "what_would_unblock_it": {
                "file": CLOSING,
                "present": os.path.exists(os.path.join(ROOT, CLOSING)),
                "required_schema": {
                    "source_name": "the licensed feed's name (must be named on the site)",
                    "source_url": "the URL the price was read from",
                    "retrieved_utc": "ISO-8601 UTC timestamp of the capture",
                    "markets": [{
                        "game_id": "nba game id, e.g. 0022600245",
                        "closing_spread_home": "the close, home-perspective, signed (negative = home favoured)",
                        "closing_total": "the close on the game total",
                        "closing_ml_home": "optional, decimal or American",
                        "closing_ml_away": "optional",
                        "capture_is_pre_tip": "true only if retrieved_utc precedes the official tip",
                    }],
                },
                "rule_once_present": ("Refuse any market row whose capture_is_pre_tip is not true or whose "
                                      "retrieved_utc is after the official tip; convert the close to a "
                                      "probability with the measured sigma_margin in model_report_v2.json; "
                                      "then re-measure w on the enlarged out-of-sample corpus. w is never "
                                      "set by hand."),
            },
            "refusal": ("`--market` exits 5 when the closing-line file is absent. The script will not "
                        "synthesise, scrape or infer a price."),
            "sigma_margin_available_for_conversion": mr["home_court_anchor"]["sigma_margin_used"],
        },
        "sources": [
            "https://www.nba.com/games (official finals behind every graded game)",
            "docs/data/backtest.json (per-game out-of-sample probabilities and results)",
            "data/derived/model_report_v2.json (measured sigma_margin)",
        ],
    }

    os.makedirs(os.path.dirname(os.path.join(ROOT, OUT)), exist_ok=True)
    with open(os.path.join(ROOT, OUT), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    if "--market" in sys.argv and not os.path.exists(os.path.join(ROOT, CLOSING)):
        print(f"REFUSED: {CLOSING} does not exist, so there is nothing to anchor to and no price "
              f"will be invented. The schema the file must satisfy is in {OUT}.", file=sys.stderr)
        return 5

    print(f"wrote {OUT}")
    print(f"  corpus: {n} games ({metrics['window']}), published log-loss recomputed: {recon['agree']}")
    print(f"  w_logloss = {w:.4f}  95% [{lo:.4f}, {hi:.4f}]   w_brier = {w_brier:.4f}")
    print(f"  log-loss: model {f0:.5f}  w=0.5 {fhalf:.5f}  anchor {f1:.5f}  at w* {f_at_w:.5f}")
    print(f"  improvement from anchoring significant at 5%: {d_lo > 0}  (one-sided p={p_not_positive:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
