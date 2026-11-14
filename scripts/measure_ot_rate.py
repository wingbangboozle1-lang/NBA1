#!/usr/bin/env python3
"""measure_ot_rate.py — the measured season overtime rate, reproducible from committed data.

Writes data/derived/ot_rate.json, which the site's Game Flow page reads at build time
(no quoted constant: the builder never hard-codes a measured number — defect class I6).

Measurement basis: the same completed-game schedule the strategy lab measures on
(strategy-lab/labdata.py build_schedule: official gamelog + the verified 11/13 finals),
so the denominator matches the published probability audit exactly (n = 160 scored
games, window 2026-10-20 .. 2026-11-13, 8 overtime games -> rate 0.0500).

Official provenance of the underlying rows: each game is transcribed from
https://www.nba.com/games?date=... (see data/raw/sources.json and data/official/gamelog.json
row sources). This script computes a statistic over those captured rows; it performs no
network access and infers no values.

Usage: python3 scripts/measure_ot_rate.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "strategy-lab"))

import labdata  # noqa: E402  (in-repo; same schedule build the lab publishes against)


def main():
    ctx = labdata.build_schedule()
    games = [g for g in ctx["games"] if g.get("kind") == "scored"]
    n = len(games)
    ot = sum(1 for g in games if g.get("ot"))
    if n == 0:
        raise SystemExit("no scored games in the captured log; refusing to write a rate")
    dates = sorted(g["date"] for g in games)
    out = {
        "quantity": "season overtime rate (share of completed games decided in overtime)",
        "rate": round(ot / n, 4),
        "ot_games": ot,
        "n": n,
        "window": dates[0] + ".." + dates[-1],
        "method": "count of games with a recorded overtime in the captured official game log, "
                  "divided by completed games; Wilson 95% CI is reported by the strategy-lab "
                  "probability audit alongside this value",
        "why_not_the_model_approximation": (
            "the model's per-game normal approximation (p_overtime_approx) averages ~0.019 on this "
            "season against a realised 0.050; the strategy-lab probability audit rejects equality "
            "at p = 0.012 (exact), so the measured rate is the honest price for the column"),
        "computed_by": "scripts/measure_ot_rate.py",
        "data_sources": [
            "data/official/gamelog.json (rows transcribed from https://www.nba.com/games?date=...)",
            "verify/2026-11-14/official_finals_2026-11-13.json",
        ],
        "note": "This is a measurement over committed official transcriptions, not a live fetch. "
                "Re-run the script to reproduce; re-transcribe the game pages to re-verify.",
    }
    dest = os.path.join(ROOT, "data", "derived", "ot_rate.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("wrote %s: %s/%s = %.4f (%s)" % (dest, ot, n, out["rate"], out["window"]))


if __name__ == "__main__":
    main()
