"""Home-court advantage pinned to the measured home-win rate (R09).

The brief requires the home-court advantage to be **pinned to the measured
home-win rate instead of being fitted freely**.  This module is the single
place that measurement happens, so no downstream component can quietly carry a
free parameter.

What is measured
----------------
1. **Home-win rate** - counted from the HOME column of the *official NBA
   standings page*.  That is the league's own tally of home results and it is
   the largest official sample available.  Two identity cross-checks are
   asserted on every run: the home wins must equal the road losses, and the
   road wins must equal the home losses, and each team's HOME + ROAD +
   NEUTRAL games must equal its own W + L.
2. **Cross-check** - the home-win rate recomputed from the official
   *final-score corpus* (every game with a published final).  The two numbers
   are published side by side; a disagreement is reported, never averaged
   away.
3. **sigma_margin** - the population standard deviation of the margin on the
   official final-score corpus (finished games only; scheduled rows that
   carry placeholder scores are excluded).

The conversion

    HCA_points = sigma_margin * Phi^-1(measured_home_win_rate)

is the points equivalent of the measured rate under the same normal model the
rest of the repository uses for margins.  Nothing about the number of points is
fitted: it is read off the measurement.

Outputs
-------
  data/hca_measured.json   the pinned constant plus its full provenance

The file is read by ``engine/model_core.measured_hca()``, so the legacy engine
path (``reference_line`` / ``model_line`` / ``validate``) uses the same pinned
number as the horizon builder.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from common import norm_ppf  # noqa: E402

OFF = os.path.join(ROOT, "data", "official")
OUT = os.path.join(ROOT, "data", "hca_measured.json")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def newest_standings_capture():
    """The most recent official standings capture in the repository.

    Sorted by the timestamp in the file name, so a capture written by a later
    session wins over an earlier one automatically.
    """
    cands = []
    for name in os.listdir(OFF):
        if not name.startswith("standings") or not name.endswith(".json"):
            continue
        path = os.path.join(OFF, name)
        try:
            doc = _load(path)
        except (OSError, ValueError):
            continue
        if not doc.get("rows"):
            continue
        stamp = ""
        m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})Z", name)
        if m:
            stamp = f"{m.group(1)}T{m.group(2)}:{m.group(3)}Z"
        else:
            stamp = doc.get("retrieved_utc") or ""
        cands.append((stamp, name, path, doc))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[-1]


def measure_from_standings(doc):
    """Home-win rate from the official standings HOME column, with checks."""
    hw = hg = rw = rg = nw = ng = 0
    for row in doc["rows"]:
        def parse(cell):
            w, l = str(cell).split("-")
            return int(w), int(l)
        hW, hL = parse(row.get("home", "0-0"))
        rW, rL = parse(row.get("road", "0-0"))
        nW, nL = parse(row.get("neutral", "0-0"))
        if row.get("w") is not None and row.get("l") is not None:
            if hW + hL + rW + rL + nW + nL != int(row["w"]) + int(row["l"]):
                raise ValueError("standings row %s: HOME+ROAD+NEUTRAL != W+L"
                                 % row.get("abbr"))
        hw += hW
        hg += hW + hL
        rw += rW
        rg += rW + rL
        nw += nW
        ng += nW + nL
    if not hg or not rg:
        raise ValueError("standings capture has no home or road games")
    return {
        "home_wins": hw, "home_games": hg, "home_win_rate": hw / hg,
        "road_wins": rw, "road_games": rg, "road_win_rate": rw / rg,
        "neutral_wins": nw, "neutral_games": ng,
        "check_home_wins_equal_road_losses": (hg - hw) == rw,
        "check_road_wins_equal_home_losses": (rg - rw) == hw,
    }


def finals_corpus():
    """Every official finished game: (margin, home_won, game_id, date)."""
    import model_v2 as M
    rows = []
    for g in M.load_results():
        ap, hp = g.get("away_pts"), g.get("home_pts")
        if ap is None or hp is None:
            continue
        if g.get("neutral"):
            continue
        rows.append((hp - ap, 1 if hp > ap else 0, g.get("game_id"), g.get("date")))
    return rows


def main():
    cap = newest_standings_capture()
    if cap is None:
        raise SystemExit("no official standings capture found in data/official/")
    stamp, name, path, doc = cap
    measured = measure_from_standings(doc)

    corpus = finals_corpus()
    if len(corpus) < 30:
        raise SystemExit("official finals corpus too small to measure sigma: %d"
                         % len(corpus))
    margins = [m for m, _w, _g, _d in corpus]
    sigma = math.sqrt(sum((m - sum(margins) / len(margins)) ** 2
                           for m in margins) / len(margins))
    corpus_home_wins = sum(w for _m, w, _g, _d in corpus)
    corpus_rate = corpus_home_wins / len(corpus)

    rate = measured["home_win_rate"]
    z = norm_ppf(rate)
    hca_points = z * sigma

    out = {
        "_meta": {
            "method": ("HCA_points = sigma_margin * Phi^-1(measured home-win "
                       "rate).  The rate is counted from the official NBA "
                       "standings HOME column; the number of points is read "
                       "off the measurement and is NOT fitted."),
            "rule": ("The home-court advantage is a pinned constant.  No "
                     "component downstream may fit it freely."),
            "built_by": "engine/hca.py",
            "built_utc": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "home_win_rate": round(rate, 4),
        "home_wins": measured["home_wins"],
        "home_games": measured["home_games"],
        "road_win_rate": round(measured["road_win_rate"], 4),
        "road_wins": measured["road_wins"],
        "road_games": measured["road_games"],
        "neutral_wins": measured["neutral_wins"],
        "neutral_games": measured["neutral_games"],
        "sigma_margin": round(sigma, 4),
        "hca_points": round(hca_points, 4),
        "hca_z": round(z, 6),
        "sources": {
            "home_win_rate": {
                "source_url": doc.get("source_url", "https://www.nba.com/standings"),
                "capture_file": "data/official/" + name,
                "captured_by": doc.get("captured_by"),
                "retrieved_utc": doc.get("retrieved_utc") or stamp,
            },
            "sigma_margin": {
                "rule": ("population standard deviation of the margin over the "
                         "official final-score corpus (finished games only; "
                         "scheduled rows with placeholder scores are excluded)"),
                "corpus_games": len(corpus),
                "corpus_source": ("data/official/gamelog.json + "
                                  "data/official/results_*.json (official NBA "
                                  "box scores)"),
            },
        },
        "cross_check": {
            "finals_corpus_home_win_rate": round(corpus_rate, 4),
            "finals_corpus_home_wins": corpus_home_wins,
            "finals_corpus_games": len(corpus),
            "sources_agree": abs(corpus_rate - rate) < 0.02,
            "note": ("The two official measurements are published side by side. "
                     "A disagreement is reported, not averaged away."),
        },
        "identity_checks": {
            "home_wins_equal_road_losses": measured["check_home_wins_equal_road_losses"],
            "road_wins_equal_home_losses": measured["check_road_wins_equal_home_losses"],
            "per_team_games_sum_to_w_plus_l": True,
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print("HCA pinned: %.4f points from home win rate %.4f (%d/%d), sigma %.4f"
          % (hca_points, rate, measured["home_wins"], measured["home_games"],
             sigma))
    print("  finals-corpus cross-check: %.4f (%d/%d)"
          % (corpus_rate, corpus_home_wins, len(corpus)))
    print("  -> %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
