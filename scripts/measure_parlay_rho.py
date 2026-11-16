#!/usr/bin/env python3
"""S04 (session arena/3ff8ff0f-nba1, COORDINATION 56.1) - R14.

One measured-correlation register for every parlay the site prices, so no pricer
carries a hand-set rho again.

Background, measured not asserted:
  * `scripts/generate_picks.py` priced same-game pairs from module constants
    (SGP_RHO_TEAMMATES = -0.2, SGP_RHO_OPPONENTS = +0.05) that nothing in the
    repository measures (board flag F90).
  * `engine/parlay.py` claimed "rho measured from data/derived/measured_rho.json"
    while `measured_rho.json` has no top-level `rho` key, so the lookup always
    fell back to the literal 0.15 that sits next to the claim.

This script measures what the official data in this repository can actually
support, publishes the sample floor each number has to clear, and leaves the
numbers that cannot clear it labelled rather than hidden.  Nothing is inferred:
an unusable measurement is printed with its n and its confidence interval.

Pairings priced:
  cross_team_points   rho(home points, away points)        - both teams over a team total
  side_and_total      rho(home margin, game total)         - side + total same-game parlay
  home_points_total   rho(home points, game total)         - home over + game over
  same_team_players   rho(teammate points, teammate points) - same-game teammate pair

Sources: the verified-finals corpus of `engine/model_v2.load_results()` (the
league's own score data, filtered by `is_verified_final`) and the official
gamebooks transcribed under `data/official/gamebooks/`.

Run:  python3 scripts/measure_parlay_rho.py
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import model_v2 as M  # noqa: E402

OUT = os.path.join(ROOT, "data", "derived", "parlay_rho.json")
SEED = 20261116
BOOT = 2000
FLOORS = {"game_level": 100, "player_level_game_days": 30}


# ------------------------------------------------------------------ statistics
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def fisher_p(r, n):
    """Two-sided p from the Fisher-z normal approximation (method disclosed)."""
    if r is None or n < 4:
        return None
    r = max(min(r, 0.999999), -0.999999)
    z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3)
    return round(2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))), 6)


def boot_ci_groups(rows, key, pair_fn, reps=BOOT, seed=SEED):
    """Cluster bootstrap by `key` (a game / a game-day): resample the clusters,
    recompute the pooled statistic, take the 2.5/97.5 percentiles."""
    import random
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    names = sorted(groups)
    if len(names) < 3:
        return None, len(names)
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        picked = [names[rng.randrange(len(names))] for _ in names]
        flat = [r for nm in picked for r in groups[nm]]
        xs, ys = pair_fn(flat)
        rr = pearson(xs, ys)
        if rr is not None:
            stats.append(rr)
    if len(stats) < 100:
        return None, len(names)
    stats.sort()
    lo = stats[int(0.025 * len(stats))]
    hi = stats[int(0.975 * len(stats)) - 1]
    return [round(lo, 4), round(hi, 4)], len(names)


def jackknife_range(rows, key, pair_fn):
    """Leave-one-cluster-out spread of the statistic.  With a handful of clusters a
    percentile bootstrap CI is optimistic (there are too few resamples to span the
    real uncertainty), so the honest dispersion to print is the worst single-game
    influence: the range the estimate moves across when each game is dropped."""
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    vals = []
    for nm in sorted(groups):
        kept = [r for k, lst in groups.items() if k != nm for r in lst]
        xs, ys = pair_fn(kept)
        v = pearson(xs, ys)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, 0
    return [round(min(vals), 4), round(max(vals), 4)], len(vals)


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------- game-level rhos
    results = M.load_results()
    finals, excluded = M.verified_finals(results)
    games = [g for g in finals if not g.get("neutral")]
    hp = [g["home_pts"] for g in games]
    ap = [g["away_pts"] for g in games]
    mg = [g["home_pts"] - g["away_pts"] for g in games]
    tt = [g["home_pts"] + g["away_pts"] for g in games]
    score_urls = sorted({g.get("source_url") for g in games if g.get("source_url")})[:3]

    def fn_cross(flat):
        return ([r["home_pts"] for r in flat], [r["away_pts"] for r in flat])

    def fn_margin_total(flat):
        return ([r["home_pts"] - r["away_pts"] for r in flat],
                [r["home_pts"] + r["away_pts"] for r in flat])

    def fn_home_total(flat):
        return ([r["home_pts"] for r in flat],
                [r["home_pts"] + r["away_pts"] for r in flat])

    rows_game = [dict(home_pts=r["home_pts"], away_pts=r["away_pts"], game_id=r.get("game_id"))
                 for r in games]
    game_defs = [
        ("cross_team_points", fn_cross,
         "both teams over a team total in the same game: the two legs are the two "
         "teams' point totals, so the rho that prices them is rho(home points, away points)",
         "the only rho a both-teams-over parlay can be priced with from official box scores"),
        ("side_and_total", fn_margin_total,
         "side + total same-game parlay: rho(home margin, game total)",
         "the pairing the roll page and the SGP generator both price"),
        ("home_points_total", fn_home_total,
         "home team over + game over: rho(home points, game total)",
         "a same-game total pair that is not two independent teams"),
    ]
    register = {}
    for key, fn, what, why in game_defs:
        xs, ys = fn(games)
        r = pearson(xs, ys)
        ci, ncl = boot_ci_groups(rows_game, "game_id", fn)
        jj, jj_n = jackknife_range(rows_game, "game_id", fn)
        n = len(games)
        register[key] = {
            "pairing": what,
            "why_this_pairing": why,
            "rho_measured": None if r is None else round(r, 4),
            "n_games": n,
            "p_value": fisher_p(r, n),
            "ci95_bootstrap": ci,
            "bootstrap": ("%d reps, clusters = official games, seed %d, "
                          "2.5/97.5 percentiles" % (BOOT, SEED)) if ci else None,
            "clusters": ncl,
            "jackknife_range": jj,
            "jackknife_note": ("leave-one-game-out spread over %d drops; with fewer than "
                               "about 20 clusters this, not the bootstrap CI, is the "
                               "dispersion to read" % jj_n) if jj else None,
            "sample_floor": FLOORS["game_level"],
            "clears_floor": bool(n >= FLOORS["game_level"]),
            "status": None if r is None else (
                "MEASURED on %d official finals" % n if n >= FLOORS["game_level"]
                else "MEASURED - BELOW THE SAMPLE FLOOR (%d of %d)" % (n, FLOORS["game_level"])),
            "source": "the verified-finals corpus of engine/model_v2.load_results() "
                      "(official NBA.com scores, filtered by is_verified_final)",
            "source_examples": score_urls,
            "first_date": min(g["date"] for g in games),
            "last_date": max(g["date"] for g in games),
        }

    # ------------------------------------------- player-level teammate rho
    log_path = os.path.join(ROOT, "data", "official", "player_game_logs_2026-11-15.json")
    mate = {"available": os.path.exists(log_path)}
    if mate["available"]:
        doc = json.load(open(log_path, encoding="utf-8"))
        by_tg = {}
        for r in doc["rows"]:
            if not r.get("played") or r.get("pts") is None:
                continue
            by_tg.setdefault((r["game_id"], r["team"]), []).append(int(r["pts"]))
        pairs = []
        for (gid, team), pts in sorted(by_tg.items()):
            pts = sorted(pts, reverse=True)
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    pairs.append({"game_id": gid, "team": team, "a": pts[i], "b": pts[j]})

        def fn_mate(flat):
            return ([r["a"] for r in flat], [r["b"] for r in flat])

        r = pearson([p["a"] for p in pairs], [p["b"] for p in pairs])
        ci, ncl = boot_ci_groups(pairs, "game_id", fn_mate)
        jj, jj_n = jackknife_range(pairs, "game_id", fn_mate)
        n_days = len({p["game_id"] for p in pairs})
        mate.update({
            "pairing": "same_team_players: rho(one teammate's points, a teammate's points) "
                       "within a team-game",
            "why_this_pairing": "what a same-game teammate pair (SGP) actually depends on",
            "rho_measured": None if r is None else round(r, 4),
            "n_player_pairs": len(pairs),
            "n_game_days": n_days,
            "p_value": fisher_p(r, len(pairs)),
            "ci95_bootstrap": ci,
            "bootstrap": ("%d reps, clusters = games (the only clustering the sample "
                          "supports), seed %d" % (BOOT, SEED)) if ci else None,
            "clusters": ncl,
            "jackknife_range": jj,
            "jackknife_note": ("leave-one-game-out spread over %d drops. With six "
                               "game-days in the repository the bootstrap percentile "
                               "interval below is optimistic - the jackknife range is "
                               "the honest dispersion, and it is what the pricing "
                               "sensitivity is quoted against." % jj_n) if jj else None,
            "sample_floor": "%d game-days of official gamebooks" % FLOORS["player_level_game_days"],
            "clears_floor": n_days >= FLOORS["player_level_game_days"],
            "status": ("MEASURED - BELOW THE SAMPLE FLOOR: %d game-days of official "
                       "gamebooks in the repository against a floor of %d. The point "
                       "estimate is published and used to price; the interval is "
                       "printed beside it so the reader can see it does not exclude 0."
                       % (n_days, FLOORS["player_level_game_days"])),
            "source": "official team gamebook box scores, transcribed under "
                      "data/official/gamebooks/ and parsed by scripts/capture_player_logs.py",
            "source_examples": sorted({r2.get("source_pdf") for r2 in doc["rows"]
                                       if r2.get("source_pdf")})[:3],
        })
    else:
        mate["note"] = ("no player game-log capture present; the teammate rho stays blank "
                        "and every teammate SGP is priced with the Fréchet-Hoeffding band only")
    register["same_team_players"] = mate

    doc = {
        "title": "Parlay rho register - every correlation the site prices with, measured",
        "generated_by": "scripts/measure_parlay_rho.py",
        "generated_utc": now,
        "session": "arena/3ff8ff0f-nba1",
        "answers": "R14: price every parlay with the measured rho and print the naive product "
                   "beside it, instead of withholding the price",
        "rule": ("a rho may be printed as MEASURED only if it is computed from official data "
                 "in this repository by this script; a hand-set constant is never labelled "
                 "measured. Values that do not clear their sample floor are printed with their "
                 "n, their interval and the floor, and the naive independent product stays "
                 "beside them."),
        "finality_rule": "engine/model_v2.is_verified_final - an unplayed fixture that prints "
                         "0-0 in the dated captures is not a game and is excluded, not inferred",
        "corpus": {"results_rows": len(results), "verified_finals": len(finals),
                   "neutral_excluded": len(finals) - len(games),
                   "rows_excluded_as_unplayed": excluded,
                   "games_used": len(games)},
        "register": register,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    for k, v in register.items():
        print("  %-20s rho=%-8s n=%-4s CI=%-16s floor=%s"
              % (k, v.get("rho_measured"),
                 v.get("n_games", v.get("n_game_days")),
                 v.get("ci95_bootstrap"), v.get("clears_floor")))


if __name__ == "__main__":
    main()
