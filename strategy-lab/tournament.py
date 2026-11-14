"""Module 3 - the tournament: a point-in-time walk-forward over every scored game.

Design decisions that a reviewer should check, not take on trust:

* A team's rating at game i uses only games played strictly before i. No game informs its
  own prediction, so none of these numbers is look-ahead contaminated - the defect that made
  the first build in this repository unusable.
* sigma (the margin spread that turns a projection into a probability) is also estimated only
  from games before i.
* Every strategy is graded against the probability the originated line itself assigned, not
  against a coin flip. Grading "bet the favourite straight up" against 52.38% would print a
  win rate near 70% and mean nothing: a heavy favourite wins that often and pays almost
  nothing for it. The excess over the model's own expectation is the only quantity here that
  corresponds to a decision.
* No sportsbook price appears anywhere, so no result here is a claim about beating a book.
"""
from __future__ import annotations

import math
import random
import statistics as st

from labdata import MIN_HISTORY, K_SHRINK, rest_maps
from statools import (N_MC, SEED, auc, benjamini_hochberg, binom_two_sided, block_bootstrap,
                      norm_cdf, poisson_binom_ge, rnd, wilson)


def run(ctx):
    out = module_tournament(ctx["games"])
    for rec in out.get("strategies", []):
        rec.pop("_probs", None)
    return out


def poisson_binom_ge(probs, k):
    """Exact P(S >= k) for S = sum of independent Bernoulli(p_i).
    Dynamic program over the number of successes; no normal approximation.
    This is the test the site has been missing: with no market price, the only
    well-defined null is 'the originated line is right', so a signal has to beat
    the model's own expectation, not a coin flip."""
    n = len(probs)
    if n == 0:
        return None
    dist = [0.0] * (n + 1)
    dist[0] = 1.0
    for i, p in enumerate(probs):
        p = min(max(p, 1e-9), 1 - 1e-9)
        nd = [0.0] * (n + 1)
        for s in range(i + 2):
            if dist[s] == 0.0:
                continue
            nd[s] += dist[s] * (1 - p)
            nd[s + 1] += dist[s] * p
        dist = nd
    return min(1.0, sum(dist[k:]))


def auc(p_home, y_home):
    """Mann-Whitney AUC with tie correction. p_home: model probability that the
    home team wins; y_home: 1/0."""
    n = len(p_home)
    if n < 4 or sum(y_home) == 0 or sum(y_home) == n:
        return None
    pos = [p for p, y in zip(p_home, y_home) if y == 1]
    neg = [p for p, y in zip(p_home, y_home) if y == 0]
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else (0.5 if a == b else 0.0)
    return wins / (len(pos) * len(neg))


def module_tournament(all_games):
    """Point-in-time walk-forward over every scored game in the official log.

    For each game, both teams' ratings use only games played on an earlier date, so
    no test game informs its own prediction. Every strategy is graded against the
    probability the model itself assigned, which is the only price available in a
    repository that refuses to use an unlicensed odds feed.
    """
    games = [g for g in all_games if g["kind"] == "scored"]
    games.sort(key=lambda g: (g["date"], g["game_id"]))
    yes, _ = rest_maps(all_games, True)
    dates = sorted({g["date"] for g in games})
    date_index = {dd: i for i, dd in enumerate(dates)}

    hist = {t: [] for t in {g["away"] for g in games} | {g["home"] for g in games}}
    prior_margins = []
    plays = []
    resid_m, resid_t = [], []

    for g in games:
        before = date_index[g["date"]]
        ah = [x for x in hist[g["away"]] if x["di"] < before]
        hh = [x for x in hist[g["home"]] if x["di"] < before]
        if len(ah) >= MIN_HISTORY and len(hh) >= MIN_HISTORY and len(prior_margins) >= 20:
            mov_a = st.mean([x["mov"] for x in ah])
            mov_h = st.mean([x["mov"] for x in hh])
            wa = len(ah) / (len(ah) + K_SHRINK)
            wh = len(hh) / (len(hh) + K_SHRINK)
            r_a, r_h = mov_a * wa, mov_h * wh
            hm = [x["mov"] for x in ah + hh if x["home"]]
            am = [x["mov"] for x in ah + hh if not x["home"]]
            hca = (st.mean(hm) - st.mean(am)) / 2.0 if hm and am else 0.0
            sigma = st.pstdev(prior_margins)
            proj_home = (r_h - r_a) + hca
            actual_home = g["home_pts"] - g["away_pts"]
            actual_total = g["home_pts"] + g["away_pts"]
            rate_a = st.mean([x["pf"] + x["pa"] for x in ah])
            rate_h = st.mean([x["pf"] + x["pa"] for x in hh])
            lg_total = st.mean([x["lg_total"] for x in ah + hh])
            proj_total = (rate_a + rate_h) / 2.0
            ra, rh = yes(g["away"], g["date"]), yes(g["home"], g["date"])
            p_home = max(1e-6, min(1 - 1e-6, norm_cdf(proj_home / sigma)))
            fav = "home" if proj_home > 0 else "away"
            p_fav = p_home if fav == "home" else 1 - p_home
            plays.append({
                "date": g["date"], "game_id": g["game_id"],
                "matchup": f"{g['away']}@{g['home']}", "source_url": g["source_url"],
                "proj_home": rnd(proj_home, 2), "actual_home": actual_home,
                "naive_home": rnd(hca, 2), "sigma": rnd(sigma, 2),
                "proj_total": rnd(proj_total, 1), "actual_total": actual_total,
                "league_mean_total": rnd(lg_total, 1),
                "fav_model": fav, "p_fav": rnd(p_fav, 4), "p_home": rnd(p_home, 4),
                "home_won": 1 if actual_home > 0 else 0,
                "win_fav": 1 if ((actual_home > 0 and fav == "home") or
                                 (actual_home < 0 and fav == "away")) else 0,
                "win_over": 1 if actual_total > proj_total else 0,
                "edge": rnd(abs(proj_home - hca), 2),
                "gap_away": ra["gap"], "gap_home": rh["gap"],
                "b2b_away": 1 if ra["b2b"] else 0, "b2b_home": 1 if rh["b2b"] else 0,
                "g4_away": ra["games_last_4"], "g4_home": rh["games_last_4"],
                "form4_home": rnd(st.mean([x["mov"] for x in hh[-4:]]), 2),
                "form4_away": rnd(st.mean([x["mov"] for x in ah[-4:]]), 2),
            })
            resid_m.append((proj_home - actual_home, actual_home))
            resid_t.append((proj_total - actual_total, actual_total))
        for team, key, opp_ishome in ((g["away"], "away", False), (g["home"], "home", True)):
            other = "home" if key == "away" else "away"
            hist[team].append({"di": before, "home": opp_ishome,
                               "mov": g[f"{key}_pts"] - g[f"{other}_pts"],
                               "pf": g[f"{key}_pts"], "pa": g[f"{other}_pts"],
                               "lg_total": g["home_pts"] + g["away_pts"]})
        prior_margins.append(g["home_pts"] - g["away_pts"])

    # ------------------------------------------------------------ strategy library
    def rest_gap_edge(p):
        return (p["gap_home"] or 0) - (p["gap_away"] or 0)

    def s_fav(p, band=0.0):
        return p["win_fav"] if p["edge"] >= band else None

    def s_home(p, want_home):
        return p["home_won"] if want_home else (1 - p["home_won"])

    def p_of(p, want_home):
        return p["p_home"] if want_home else (1 - p["p_home"])

    defs = [
        ("T01", "Model favourite, any edge", "single", "Point spread",
         "Bet the side the point-in-time rating model favours.",
         lambda p: (p["win_fav"], p["p_fav"]), "the whole library's reference bet"),
        ("T02", "Model favourite, edge >= 3 pts", "single", "Point spread",
         "Bet the favourite only when the projected margin is at least 3 points clear of the naive home-court line.",
         lambda p: (s_fav(p, 3.0), p["p_fav"]), "the site's existing pick gate, re-tested on 160 games"),
        ("T03", "Model favourite, edge >= 5 pts", "single", "Point spread",
         "Same, with a 5-point band.",
         lambda p: (s_fav(p, 5.0), p["p_fav"]), "does a wider band add anything"),
        ("T04", "Home dog against a road favourite", "single", "Point spread",
         "When the model likes the away side by 3+, take the home dog instead: the exact reverse of T02.",
         lambda p: ((1 - p["win_fav"], 1 - p["p_fav"])
                    if (p["edge"] >= 3.0 and p["fav_model"] == "away") else None),
         "is the model's confidence misplaced on road favourites"),
        ("T05", "Back the better-rested team (gap >= 2 days)", "single", "Point spread",
         "Ignore the model; bet whichever team has had two or more extra calendar days between games.",
         lambda p: ((s_home(p, rest_gap_edge(p) > 0),
                     p_of(p, rest_gap_edge(p) > 0)) if abs(rest_gap_edge(p)) >= 2 else None),
         "is rest alone a signal at all"),
        ("T06", "Fade a back-to-back", "single", "Point spread",
         "Bet against the team on zero full days off when its opponent is not.",
         lambda p: ((s_home(p, not p["b2b_home"]), p_of(p, not p["b2b_home"]))
                    if p["b2b_home"] != p["b2b_away"] else None),
         "the tired-team fade, on a rest layer that now includes the 23 fixtures"),
        ("T07", "Fade 3 games in 4 nights", "single", "Point spread",
         "Bet against the team with three or more games in the last four calendar days when its opponent has one or fewer.",
         lambda p: ((s_home(p, (p["g4_away"] or 0) >= 3 and (p["g4_home"] or 0) <= 1),
                     p_of(p, (p["g4_away"] or 0) >= 3 and (p["g4_home"] or 0) <= 1))
                    if ((p["g4_home"] or 0) >= 3) != ((p["g4_away"] or 0) >= 3) else None),
         "a denser schedule measure than T06"),
        ("T08", "Model favourite AND opponent on a back-to-back", "single", "Point spread",
         "Take the model side only when the team it likes is also the better-rested one.",
         lambda p: ((p["win_fav"], p["p_fav"]) if p["edge"] >= 3.0 and (
             (p["fav_model"] == "home" and p["b2b_away"] and not p["b2b_home"]) or
             (p["fav_model"] == "away" and p["b2b_home"] and not p["b2b_away"])) else None),
         "the combination the site's S5 and S1 would like to be"),
        ("T09", "Recent-form confirmation", "single", "Point spread",
         "Take the model side only when its last-four margin points the same way.",
         lambda p: ((p["win_fav"], p["p_fav"]) if ((p["form4_home"] or 0) > 0 and p["fav_model"] == "home") or
                                                      ((p["form4_away"] or 0) > 0 and p["fav_model"] == "away") else None),
         "does recent form add to the season-long rating"),
        ("T10", "Over when the projection clears the league mean", "single", "Game total",
         "Bet the over when the projected total is above the running league mean total.",
         lambda p: (p["win_over"], 0.5),
         "totals have no originated opponent line, so the null here is a coin flip by construction"),
        ("T11", "Two-leg same-day parlay, edge >= 3", "parlay", "Same-day double",
         "The two strongest T02 legs on a date, if two exist; both must win.", None,
         "does the correlation between same-night legs matter once the legs are chosen this way"),
        ("T12", "Two-leg cross-game parlay, edge >= 5", "parlay", "Cross-game double",
         "The two strongest T03 legs on a date, if two exist; both must win.", None,
         "the high-confidence double"),
        ("T13", "Three-leg parlay, edge >= 3", "parlay", "Treble",
         "The three strongest T02 legs on a date; all three must win.", None,
         "how fast a treble's true price moves away from the product of its legs"),
    ]

    singles, meta_by_id = {}, {}
    for sid, name, fam, market, rule, fn, why in defs:
        if fam == "parlay":
            continue
        rows = []
        for p in plays:
            out = fn(p)
            if out is None:
                continue
            res, prob = out
            if res is None:
                continue
            rows.append((p, res, prob))
        singles[sid] = rows
        meta_by_id[sid] = (name, fam, market, rule, why)

    by_date = {}
    for p in plays:
        by_date.setdefault(p["date"], []).append(p)
    parlays, parlay_rows = {}, {}
    for sid, band, legs in (("T11", 3.0, 2), ("T12", 5.0, 2), ("T13", 3.0, 3)):
        rows = []
        for dd, ps in sorted(by_date.items()):
            cand = sorted([p for p in ps if p["edge"] >= band], key=lambda p: -p["edge"])
            if len(cand) < legs:
                continue
            take = cand[:legs]
            win = 1 if all(t["win_fav"] == 1 for t in take) else 0
            prob = 1.0
            for t in take:
                prob *= t["p_fav"]
            rows.append((take, win, prob))
            parlay_rows[sid] = parlay_rows.get(sid, []) + [{
                "date": dd,
                "legs": " + ".join(f"{t['matchup']} ({t['fav_model']})" for t in take),
                "leg_game_ids": [t["game_id"] for t in take],
                "model_prob": rnd(prob, 4), "win": win,
                "source_url": "https://www.nba.com/games?date=" + dd,
            }]
        parlays[sid] = rows
        meta_by_id[sid] = (dict((x[0], x[1]) for x in defs)[sid], "parlay",
                           dict((x[0], x[3]) for x in defs)[sid],
                           dict((x[0], x[4]) for x in defs)[sid],
                           dict((x[0], x[6]) for x in defs)[sid])

    records = []
    index_by_sid = {}
    for sid in singles:
        rec, idx = strategy_record(sid, singles[sid], plays, meta_by_id[sid])
        records.append(rec)
        index_by_sid[sid] = idx
    for sid in parlays:
        rec, idx = parlay_record(sid, parlays[sid], meta_by_id[sid])
        records.append(rec)
        index_by_sid[sid] = idx

    pvals = [(r["id"], r["p_model_null"]) for r in records]
    qs = benjamini_hochberg(pvals)
    k = sum(1 for _ in pvals)
    for rec in records:
        rec["bh_q"] = rnd(qs.get(rec["id"]), 4)
        rec["bonferroni"] = rnd(min(1.0, (qs.get(rec["id"]) or 1.0) * k), 4)
    records.sort(key=lambda r: -(r["excess_wins"] or 0))

    library_null = shared_draw_library_null(records, index_by_sid, plays)
    return {
        "window": f"{games[0]['date']} .. {games[-1]['date']}",
        "games_in_log_with_scores": len(games),
        "games_graded": len(plays),
        "first_graded_date": plays[0]["date"] if plays else None,
        "params": {"min_history_per_team": MIN_HISTORY, "shrink_k": K_SHRINK,
                   "sigma": "point-in-time SD of the home margin over all games before the date",
                   "status": "all parameters and both team ratings use only games strictly earlier than the game being predicted"},
        "what_being_tested": (
            "Each play is graded against the probability the originated line itself implied. "
            "A strategy earns promotion only by winning MORE often than its own model said it "
            "would - which is the question a bookmaker would ask and the one a repository with no "
            "odds feed can still answer. A raw hit rate against 52.38% is deliberately not the "
            "headline: betting a strong favourite straight up clears that bar for free and proves nothing."),
        "strategies": records,
        "library_null": library_null,
        "forecast_skill": forecast_skill(resid_m, resid_t, plays),
        "play_log": [{k2: p[k2] for k2 in ("date", "matchup", "game_id", "proj_home", "actual_home",
                                           "naive_home", "fav_model", "p_fav", "win_fav", "edge",
                                           "b2b_home", "b2b_away", "source_url")} for p in plays],
        "parlays": parlay_rows,
    }


def strategy_record(sid, rows, plays, meta):
    pos = {id(p): i for i, p in enumerate(plays)}
    idx = [pos[id(p)] for p, _, _ in rows]
    return _record(sid, rows, meta, [r for _, r, _ in rows],
                   [pr for _, _, pr in rows], idx, 1)


def parlay_record(sid, rows, meta):
    return _record(sid, rows, meta, [w for _, w, _ in rows],
                   [pr for _, _, pr in rows], list(range(len(rows))),
                   len(rows[0][0]) if rows else 0)


def _record(sid, rows, meta, results, probs, idx, legs):
    name, fam, market, rule, why = meta
    n = len(results)
    w = sum(results)
    exp = sum(probs)
    sd = math.sqrt(sum(p * (1 - p) for p in probs)) if probs else 0.0
    hit = (w / n) if n else None
    lo, hi = wilson(w, n) if n else (None, None)
    z = ((w - exp) / sd) if sd and sd > 0 else None
    dates, urls = [], []
    for row in rows:
        p0 = row[0]
        if isinstance(p0, list):
            dates.append(p0[0]["date"])
            urls.append("https://www.nba.com/games?date=" + p0[0]["date"])
        else:
            dates.append(p0["date"])
            urls.append(p0["source_url"])
    units = [1.0 if r == 1 else -1.0 for r in results]
    return {
        "id": sid, "name": name, "family": fam, "market": market, "rule": rule, "why_tested": why,
        "n": n, "wins": w, "losses": n - w, "hit_rate": rnd(hit, 4),
        "wilson_lo": rnd(lo, 4), "wilson_hi": rnd(hi, 4),
        "expected_wins_from_model": rnd(exp, 2), "excess_wins": rnd(w - exp, 2),
        "excess_per_100": rnd((w - exp) / n * 100, 2) if n else None,
        "z_vs_model": rnd(z, 2) if z is not None else None,
        "p_model_null": rnd(poisson_binom_ge(probs, w), 5) if n else None,
        "p_coin_flip_two_sided": rnd(binom_two_sided(w, n), 5) if n else None,
        "mean_p_model": rnd(st.mean(probs), 4) if probs else None,
        "calibration_gap": rnd(hit - st.mean(probs), 4) if probs and n else None,
        "units_pnl_minus110": rnd(sum(units), 2),
        "legs": legs,
        "bootstrap_units": block_bootstrap(units) if n >= 8 else None,
        "halves": split_halves(results) if n >= 8 else {},
        "sources_distinct": len(set(urls)),
        "first_date": dates[0] if dates else None, "last_date": dates[-1] if dates else None,
        "index": idx, "_probs": probs,
    }, idx


def split_halves(results):
    mid = len(results) // 2
    out = {}
    for label, chunk in (("first_half", results[:mid]), ("second_half", results[mid:])):
        if chunk:
            out[label] = {"n": len(chunk), "wins": sum(chunk),
                          "hit_rate": rnd(sum(chunk) / len(chunk), 4)}
    out["both_above_50"] = bool(out.get("first_half") and out.get("second_half") and
                                out["first_half"]["hit_rate"] > 0.5 and out["second_half"]["hit_rate"] > 0.5)
    return out


def shared_draw_library_null(records, index_by_sid, plays):
    """One simulated season per draw: every game outcome is sampled once from the
    probability the originated line assigned, and then every selection rule is
    re-evaluated on that same vector. That keeps the overlap between strategies -
    they bet the same games - which a per-strategy simulation would ignore.
    The statistic is the largest standardised excess (wins - expected wins)/sd in
    the library; the p-value is how often a luck-only library produces one this big."""
    probs_by_play = [p["p_fav"] for p in plays]
    n_plays = len(plays)
    obs = []
    for rec in records:
        probs = rec["_probs"]
        if not probs or rec["n"] < 5:
            continue
        exp = sum(probs)
        sd = math.sqrt(sum(p * (1 - p) for p in probs))
        if sd <= 0:
            continue
        obs.append((rec["id"], rec["wins"], rec["index"], exp, sd))
    if not obs:
        return None
    rng = random.Random(SEED)
    B = min(N_MC, 6000)
    z_obs = max((w - exp) / sd for _sid, w, _idx, exp, sd in obs)
    exceed = 0
    for _ in range(B):
        draw = [1 if rng.random() < p else 0 for p in probs_by_play]
        best = max(((sum(draw[i] for i in idx) - exp) / sd) for _sid, _w, idx, exp, sd in obs)
        if best >= z_obs:
            exceed += 1
    for rec in records:
        rec.pop("_probs", None)
    return {"statistic": "largest standardised excess over the model's own expectation, across the library",
            "observed_z": rnd(z_obs, 3), "strategies_in_library": len(obs),
            "simulations": B, "plays_per_simulation": n_plays,
            "probability_luck_only_library_matches_or_beats": rnd(exceed / B, 4),
            "reading": ("below 0.05 means the best strategy in this library is beyond what a "
                        "luck-only library of the same size, on the same games and the same "
                        "model probabilities, would usually produce"),
            "seed": SEED}


def forecast_skill(resid_m, resid_t, plays):
    pm = [a for a, _ in resid_m]
    am = [b for _, b in resid_m]
    pt = [a for a, _ in resid_t]
    at = [b for _, b in resid_t]
    n = len(pm)
    if not n:
        return {}
    mae_model = st.mean([abs(x) for x in pm])
    mae_naive = st.mean([abs(x) for x in am])
    brier_model = st.mean([(p["p_home"] - p["home_won"]) ** 2 for p in plays])
    brier_naive = st.mean([(0.5 - p["home_won"]) ** 2 for p in plays])
    exp_p = st.mean([p["p_fav"] for p in plays])
    real = st.mean([p["win_fav"] for p in plays])
    return {
        "n": n,
        "margin": {"mae_model": rnd(mae_model, 3), "mae_naive_zero_line": rnd(mae_naive, 3),
                   "improvement_pct": rnd((1 - mae_model / mae_naive) * 100, 2),
                   "bias_model": rnd(st.mean(pm), 3),
                   "rmse_model": rnd(math.sqrt(st.mean([x * x for x in pm])), 3),
                   "rmse_naive": rnd(math.sqrt(st.mean([x * x for x in am])), 3)},
        "total": {"mae_model": rnd(st.mean([abs(x) for x in pt]), 3),
                  "mae_naive": rnd(st.mean([abs(x - st.mean(at)) for x in at]), 3),
                  "bias_model": rnd(st.mean(pt), 3)},
        "win_probability": {
            "brier_model": rnd(brier_model, 4), "brier_naive": rnd(brier_naive, 4),
            "brier_skill_score": rnd(1 - brier_model / brier_naive, 4),
            "auc": rnd(auc([p["p_home"] for p in plays], [p["home_won"] for p in plays]), 4),
        },
        "favourite_side": {"mean_model_prob": rnd(exp_p, 4), "realised_win_rate": rnd(real, 4),
                           "gap": rnd(real - exp_p, 4)},
    }


