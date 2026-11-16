"""Parlay pricing with a MEASURED rho + the naive product printed side by side.

Parlay fair probability = product of single probabilities adjusted for correlation:
  P(both win) = p1*p2 + rho * sqrt(p1*(1-p1)*p2*(1-p2))   (Gaussian/Frechet linear form)
Naive product = p1 * p2 (assumes independence).

R14 fix (session arena/3ff8ff0f-nba1, COORDINATION 56.1).  This module used to open with

    RHO = 0.15  # measured parlay correlation from data/derived/measured_rho.json
    rho = read_json("data/derived/measured_rho.json").get("rho", RHO)

and `data/derived/measured_rho.json` has no top-level `rho` key, so the lookup always fell
back to the literal 0.15 while the output line still read "rho=0.15 measured from historical
same-game pairs".  A constant was being published as a measurement.  The rho now comes from
the measured register written by scripts/measure_parlay_rho.py, is labelled with its n, its
interval and its sample-floor status, and when no register exists the price is still printed -
at independence, labelled as such, never withheld.

The side + total pairing is the one this file prices (home win + over the reference total),
so it takes `side_and_total`, which measures -0.038 on 196 official finals, not +0.15.
The price is also printed at the ends of the leave-one-game-out (jackknife) range, so a
reader can see how much of the quote depends on a correlation the league data cannot pin down.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from common import read_json, write_json  # noqa: E402

REGISTER = "data/derived/parlay_rho.json"


def american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def load_rho(pairing="side_and_total"):
    """The measured rho for a pairing, with its provenance.  Never a silent constant."""
    try:
        doc = read_json(REGISTER)
    except (FileNotFoundError, OSError, ValueError):
        return {"rho": None, "status": "NO MEASURED REGISTER - priced at independence",
                "label": "not measured; run scripts/measure_parlay_rho.py",
                "n_games": None, "ci95": None, "jackknife": None,
                "source": REGISTER}
    row = (doc.get("register") or {}).get(pairing) or {}
    rho = row.get("rho_measured")
    return {
        "rho": rho,
        "status": row.get("status") or "no measurement for this pairing",
        "label": ("MEASURED (%s)" % row.get("n_games") if rho is not None
                  else "NOT MEASURED - priced at independence, labelled"),
        "n_games": row.get("n_games"),
        "ci95": row.get("ci95_bootstrap"),
        "jackknife": row.get("jackknife_range"),
        "sample_floor": row.get("sample_floor"),
        "clears_floor": row.get("clears_floor"),
        "pairing": row.get("pairing"),
        "source": REGISTER,
        "generated_utc": doc.get("generated_utc"),
    }


def joint(p1, p2, rho):
    """Linear Gaussian-correlation adjustment, clipped to the Frechet region."""
    p = p1 * p2 + rho * math.sqrt(max(p1 * (1 - p1) * p2 * (1 - p2), 0.0))
    return max(0.0, min(1.0, p))


def run():
    meta = load_rho("side_and_total")
    rho = 0.0 if meta["rho"] is None else meta["rho"]
    band = []
    if meta["jackknife"]:
        band = meta["jackknife"]

    lines = read_json("docs/data/lines.json")["rows"]
    out = []
    for r in lines:
        p_home = r["p_home_win"]
        # Two-leg parlay: home wins + over total (correlated legs)
        p_over = r.get("p_over_ref_total", 0.5)
        naive = p_home * p_over
        corr = joint(p_home, p_over, rho)
        row = {
            "date": r["date"], "matchup": r["matchup"], "away": r["away"], "home": r["home"],
            "leg1_p_home": round(p_home, 4),
            "leg2_p_over": round(p_over, 4),
            "naive_product": round(naive, 4),
            "naive_american": american(naive),
            "rho": rho,
            "rho_status": meta["status"],
            "rho_n_games": meta["n_games"],
            "rho_ci95": meta["ci95"],
            "rho_source": meta["source"],
            "rho_adjusted": round(corr, 4),
            "rho_american": american(corr),
            "edge_of_rho_over_naive_pct": round(100.0 * (corr / naive - 1.0), 2) if naive else None,
            "src": r.get("src"),
        }
        if band:
            lo, hi = min(band), max(band)
            row["rho_jackknife_range"] = [lo, hi]
            row["rho_adjusted_at_range"] = [round(joint(p_home, p_over, lo), 4),
                                            round(joint(p_home, p_over, hi), 4)]
            row["american_at_range"] = [american(joint(p_home, p_over, lo)),
                                        american(joint(p_home, p_over, hi))]
            row["price_spread_note"] = ("the whole quote, at the two ends of the measured "
                                        "rho's leave-one-game-out range - how much of this "
                                        "price is correlation and how much is the legs")
        row["method"] = ("Parlay price = naive product vs rho-adjusted, at the measured rho. "
                         "Both printed, never withheld.")
        out.append(row)
    write_json("data/parlay_pricing.json", {
        "_meta": {
            "method": ("P(parlay) = p1*p2 + rho*sqrt(p1(1-p1)p2(1-p2)); the naive product is "
                       "printed beside it on every row. rho is read from the measured register, "
                       "never set in code."),
            "rho": rho,
            "rho_status": meta["status"],
            "rho_n_games": meta["n_games"],
            "rho_ci95": meta["ci95"],
            "rho_jackknife_range": band or None,
            "rho_source": meta["source"],
            "rho_label": meta["label"],
            "correction": ("previous builds priced this page at a hardcoded 0.15 that was "
                           "labelled measured; the measured side+total rho on the official "
                           "finals is what is used now, with its interval"),
        },
        "rows": out,
    })
    print("Parlay pricing: %d games, rho=%s (%s, n=%s)"
          % (len(out), rho, meta["status"], meta["n_games"]))


if __name__ == "__main__":
    run()
