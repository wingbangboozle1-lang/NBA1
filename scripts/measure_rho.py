#!/usr/bin/env python3
"""measure_rho.py — measure, from official finals only, the correlations the
parlay pricer needs, and refuse to publish a rho it cannot measure.

The brief asks for parlays to be priced with a *measured* rho and for the naive
product to be printed next to it. This script measures what official data can
support and leaves the rest blank rather than asserting a number:

  * rho(home margin, game total)   — MEASURABLE. Both legs come from the same
    official final score, so the correlation between the margin and the total of
    the same game is directly observable. This is the rho a same-game
    side-and-total parlay needs.
  * rho(two games on the same date) — NOT MEASURABLE from official data. Two
    different games have no natural pairing, so any number would be an artefact
    of how the pairs were made. The pricer therefore publishes the naive product
    with the Fréchet–Hoeffding band, and the gap is flagged.

Corpus: every official final in the repository. Each row keeps the file it came
from and the official URL behind it, and the corpus is printed on the page so a
reviewer can check the n.

Run:  python3 scripts/measure_rho.py
Writes: data/derived/measured_rho.json
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

CORPUS = [
    # (file, how to read it, official url for the rows)
    ("data/raw/games_completed.json", "cols_rows",
     "https://www.nba.com/games?date=2026-11-06"),
    ("data/verified/finals_2026-11-13.json", "dict_rows",
     "https://www.nba.com/games?date=2026-11-13"),
    ("data/official/results_2026-11-14.json", "dict_rows",
     "https://www.nba.com/games?date=2026-11-14"),
    ("data/official/results_2026-11-15.json", "dict_rows",
     "https://www.nba.com/games?date=2026-11-15"),
]


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None, None
    r = sxy / math.sqrt(sxx * syy)
    # two-sided t test on r with n-2 df, via the normal approximation of the
    # t distribution's tail (n >> 30 here); reported to 3 dp as a p-value.
    if abs(r) >= 1.0:
        return r, 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return r, p


def main():
    games, sources, files_used = [], [], []
    for rel, kind, url in CORPUS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        doc = json.load(open(path, encoding="utf-8"))
        if kind == "cols_rows":
            cols, rows = doc["cols"], doc["rows"]
            recs = [dict(zip(cols, r)) for r in rows]
        else:
            recs = doc["rows"]
        n_before = len(games)
        for r in recs:
            if r.get("away_pts") is None or r.get("home_pts") is None:
                continue                      # not final -> not used, never inferred
            if str(r.get("final_label") or r.get("status_label") or "Final") != "Final":
                continue
            games.append({
                "date": r["date"], "game_id": r.get("game_id"),
                "away": r["away"], "home": r["home"],
                "away_pts": r["away_pts"], "home_pts": r["home_pts"],
                "ot": r.get("ot", r.get("ot_periods", 0)) or 0,
                "source_file": rel, "source_url": url,
            })
        if len(games) > n_before:
            files_used.append({"file": rel, "games_added": len(games) - n_before,
                               "official_url": url})
            sources.append(url)

    # de-duplicate on game_id (the three corpora overlap on 11/13-11/14)
    seen, uniq = set(), []
    for g in sorted(games, key=lambda x: (x["date"], x["game_id"] or "")):
        if g["game_id"] and g["game_id"] in seen:
            continue
        seen.add(g["game_id"])
        uniq.append(g)
    games = uniq

    margins = [g["home_pts"] - g["away_pts"] for g in games]
    totals = [g["home_pts"] + g["away_pts"] for g in games]
    r_mt, p_mt = pearson(margins, totals)

    # regulation-only variant: overtime inflates the total without moving the
    # margin the same way, so it is reported separately, not mixed in.
    reg = [g for g in games if not g["ot"]]
    r_reg, p_reg = pearson([g["home_pts"] - g["away_pts"] for g in reg],
                           [g["home_pts"] + g["away_pts"] for g in reg])

    home_wins = sum(1 for m in margins if m > 0)
    out = {
        "title": "Measured correlations from official finals",
        "generated_by": "scripts/measure_rho.py",
        "corpus": {
            "n_games": len(games),
            "n_regulation": len(reg),
            "n_overtime": len(games) - len(reg),
            "first_date": games[0]["date"] if games else None,
            "last_date": games[-1]["date"] if games else None,
            "files": files_used,
            "rule": ("only games whose official label is Final are used; a game still "
                     "live at capture time is excluded, never filled in"),
        },
        "measured": [
            {"x": "home margin", "y": "game total", "r": None if r_mt is None else round(r_mt, 4),
             "p_value": None if p_mt is None else round(p_mt, 4), "n": len(games),
             "subset": "all finals",
             "status": "MEASURED from official final scores",
             "why": "the rho a same-game side-and-total parlay needs"},
            {"x": "home margin", "y": "game total", "r": None if r_reg is None else round(r_reg, 4),
             "p_value": None if p_reg is None else round(p_reg, 4), "n": len(reg),
             "subset": "regulation finals only (no overtime)",
             "status": "MEASURED from official final scores",
             "why": "overtime raises the total without moving the margin the same way, "
                    "so the regulation-only figure is the cleaner estimate"},
        ],
        "not_measurable": [
            {"quantity": "rho between two different games on the same date",
             "why_not": ("two games have no natural pairing, so a number would be an "
                         "artefact of how the pairs were made rather than a property of "
                         "the games"),
             "consequence": ("cross-game parlays are published as the naive product "
                             "p1 x p2 with the Frechet-Hoeffding band "
                             "[max(0, p1+p2-1), min(p1, p2)]; no rho is asserted")},
            {"quantity": "rho between a model pick and a market price",
             "why_not": "no NBA-operated source publishes a price, so there is no market leg to correlate",
             "consequence": "market-comparison gates remain blocked"},
        ],
        "home_win_rate": {
            "home_wins": home_wins, "n_decided": sum(1 for m in margins if m != 0),
            "n_games": len(games),
            "rate": round(home_wins / len(games), 4) if games else None,
            "status": "MEASURED from official final scores",
            "note": ("this is the measured home-win rate the brief asks to pin "
                     "home-court advantage to; it is published here and is NOT applied "
                     "to any originated line yet (flag F-W02 / F74)"),
        },
        "sources": sorted(set(sources)),
    }
    out_path = os.path.join(DATA, "derived", "measured_rho.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("measured rho written ->", os.path.relpath(out_path, ROOT))
    print("  corpus: %d finals (%s .. %s), %d regulation" %
          (len(games), out["corpus"]["first_date"], out["corpus"]["last_date"], len(reg)))
    print("  rho(margin, total) all      = %s (n=%d, p=%s)" %
          (out["measured"][0]["r"], out["measured"][0]["n"], out["measured"][0]["p_value"]))
    print("  rho(margin, total) regulation = %s (n=%d, p=%s)" %
          (out["measured"][1]["r"], out["measured"][1]["n"], out["measured"][1]["p_value"]))
    print("  measured home-win rate = %s (%d/%d)" %
          (out["home_win_rate"]["rate"], home_wins, len(games)))


if __name__ == "__main__":
    main()
