#!/usr/bin/env python3
"""rolling_slate_build.py - assemble the 2026-11-15 rolling-slate build.

    python3 scripts/rolling_slate_build.py

Reads the official capture in `data/captures/2026-11-15/parsed/` and writes the
derived model outputs to `data/derived/rolling_slate_2026_11_15/`:

    horizon.json        one row per game in the horizon with BOTH estimators,
                        their disagreement, the pinned HCA, the possession-based
                        total, travel, rest and availability
    estimates.json      the estimator comparison and the measured out-of-sample
                        log-loss weights
    results.json        the official per-game result feed (final + quarters)
    settlement.json     the settlement of every published pick against the
                        official finals, with a settlement stamp
    injury_editions.json  every official injury edition and the consecutive diff
    minutes.json        per-team top-8 minutes shares and the replacement
                        allocation for every player the report says is out
    player_logs.json    per-player game logs (minutes, points, rebounds,
                        assists, opponent) for the players on the injury report
    preregistration.json  the frozen pre-registration file per strategy
    ledger.json         the tamper-evident pick ledger (hash published before
                        tip, verified after settlement)
    picks.json          the picks generated for the horizon by the registered
                        strategy rules
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import rolling_slate_model as M          # noqa: E402
import strategies as ST                  # noqa: E402  (engine/strategies.py)

CAP = os.path.join(ROOT, "data", "captures", "2026-11-15", "parsed")
DER = os.path.join(ROOT, "data", "derived", "rolling_slate_2026_11_15")
DOCS_DATA = os.path.join(ROOT, "docs", "data")

HORIZON_START = "2026-11-15"
HORIZON_END = "2026-11-18"
TRAIN_FROM, TRAIN_TO = "2026-10-20", "2026-11-05"
OOS_FROM, OOS_TO = "2026-11-06", "2026-11-14"


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


def log(msg):
    print("[%s] %s" % (now_utc(), msg), flush=True)


# --------------------------------------------------------------------- helpers
def reference_line(ti, g):
    """The naive reference the model has to beat - the same definition the rest
    of the repository uses (engine/model_core.reference_line): raw published net
    rating, a flat +2.0 home edge, and a total that is the two teams' published
    scoring averages added together."""
    th = ti["teams"].get(g["home"])
    ta = ti["teams"].get(g["away"])
    if not th or not ta:
        return None
    try:
        poss = (float(th["pace"]) + float(ta["pace"])) / 2.0
        h100 = float(th["ortg"]) + float(ta["drtg"]) - M.__dict__.get("_L", 0.0)
        a100 = float(ta["ortg"]) + float(th["drtg"]) - M.__dict__.get("_L", 0.0)
        margin = (h100 - a100) * poss / 100.0 + 2.0
        total = float(th["pts"]) / float(th["gp"]) + float(ta["pts"]) / float(ta["gp"])
    except (TypeError, ValueError, ZeroDivisionError, KeyError):
        return None
    return {"poss": poss, "margin": margin, "total": total, "hca": 2.0,
            "definition": "raw published net rating, flat +2.0 home edge, total = "
                          "the two teams' published scoring averages added"}


def league_avg_rating(ti):
    """The league-average offensive and defensive rating the efficiency model
    subtracts. Measured from the official advanced table."""
    teams = list(ti["teams"].values())
    if not teams:
        return 0.0
    return sum(float(t["ortg"]) for t in teams if t.get("ortg") is not None) / len(teams)


def base_margin_ratings(ti, g, L):
    th = ti["teams"].get(g["home"])
    ta = ti["teams"].get(g["away"])
    if not th or not ta:
        return None, None, None
    try:
        poss = (float(th["pace"]) + float(ta["pace"])) / 2.0
        h100 = float(th["ortg"]) + float(ta["drtg"]) - L
        a100 = float(ta["ortg"]) + float(th["drtg"]) - L
        h_pts = h100 * poss / 100.0
        a_pts = a100 * poss / 100.0
    except (TypeError, ValueError):
        return None, None, None
    return h_pts - a_pts, poss, h_pts + a_pts


def log_loss(pairs):
    """Mean negative log-likelihood of (probability, outcome) pairs."""
    if not pairs:
        return None
    total = 0.0
    for p, y in pairs:
        p = min(max(p, 1e-6), 1 - 1e-6)
        total += -(y * M.math.log(p) + (1 - y) * M.math.log(1 - p))
    return total / len(pairs)



def player_logs(boxes_doc, injury_rows, games, last_n=10):
    """Per-player game logs for the players that appear on the injury report."""
    wanted = {}
    for r in injury_rows:
        name = (r.get("player") or "").strip()
        if name:
            wanted.setdefault(name, {"team": r.get("team"), "status": r.get("status"),
                                     "source_url": r.get("source_url")})
    out = []
    for g in boxes_doc.get("games", []):
        for p in g.get("players", []):
            name = (p.get("player") or "").strip()
            if name not in wanted:
                continue
            out.append({
                "player": name,
                "team": p.get("team"),
                "date": g.get("date"),
                "game_id": g.get("game_id"),
                "opponent": p.get("opponent"),
                "minutes": p.get("minutes"),
                "points": p.get("points"),
                "rebounds": p.get("rebounds"),
                "assists": p.get("assists"),
                "source_url": "https://www.nba.com/game/%s/box-score" % g.get("game_id"),
            })
    players = []
    for name, meta in sorted(wanted.items()):
        gs = sorted([r for r in out if r["player"] == name],
                    key=lambda r: r["date"])[-last_n:]
        players.append({
            "player": name,
            "team": meta["team"],
            "injury_status": meta["status"],
            "injury_source_url": meta["source_url"],
            "games": gs,
            "games_counted": len(gs),
        })
    return {"players": players,
            "players_counted": len(players),
            "rows_counted": sum(p["games_counted"] for p in players),
            "rule": "One row per player per game, read from the official box scores: "
                    "minutes, points, rebounds, assists and the opponent.",
            "source": "official box scores"}


def lines_view(hz_rows, ev, minutes, sigma_margin):
    """The horizon rows in the exact field names the site's picks page reads."""
    from statistics import NormalDist
    out = []
    for r in hz_rows:
        ref = r.get("reference") or {}
        blend = r.get("blend_margin")
        p_home = None
        if blend is not None and sigma_margin:
            p_home = NormalDist().cdf(blend / sigma_margin)

        def american(p):
            if p is None or not (0 < p < 1):
                return None
            return -int(round(100 * (1 - p) / p)) if p >= 0.5 else int(round(100 * p / (1 - p)))
        out.append({
            "game_id": r.get("game_id"),
            "date": r["date"],
            "home": r.get("home"),
            "away": r.get("away"),
            "time_et": r.get("time_et"),
            "matchup": r["matchup"],
            "away_rec": r.get("away_record_printed"),
            "home_rec": r.get("home_record_printed"),
            "venue": r.get("arena_name"),
            "ref_spread_home": ref.get("margin"),
            "model_spread_home": blend,
            "spread_edge": (blend - ref["margin"]) if (blend is not None and ref.get("margin") is not None) else None,
            "ref_total": ref.get("total"),
            "model_total": r.get("total_possessions_x_ppp"),
            "total_edge": (r.get("total_possessions_x_ppp") - ref["total"])
                          if (r.get("total_possessions_x_ppp") is not None and ref.get("total") is not None) else None,
            "p_home_win": p_home,
            "ml_home_fair": american(p_home),
            "ml_away_fair": american(1 - p_home) if p_home is not None else None,
            "home_rest_days": r.get("home_rest_days"),
            "away_rest_days": r.get("away_rest_days"),
            "home_report_status": r.get("home_report_status"),
            "away_report_status": r.get("away_report_status"),
            "src": "S1",
            # new columns
            "estimator_a_margin": r["estimator_a"]["margin"],
            "estimator_b_margin": r["estimator_b"]["margin"],
            "disagreement_points": r.get("disagreement_points"),
            "away_travel_miles": r.get("away_travel_miles"),
            "home_travel_miles": r.get("home_travel_miles"),
            "away_back_to_back": r.get("away_back_to_back"),
            "home_back_to_back": r.get("home_back_to_back"),
            "home_rotation_availability": None,
            "away_rotation_availability": None,
        })
    return out

def main():
    os.makedirs(DER, exist_ok=True)
    games_doc = load(os.path.join(CAP, "games.json"), {"games": []})
    boxes_doc = load(os.path.join(CAP, "boxscores.json"), {"games": []})
    stats = load(os.path.join(CAP, "team_stats.json"), {})
    arenas = load(os.path.join(CAP, "arenas.json"), {})
    inj_doc = load(os.path.join(CAP, "injury_editions.json"), {"editions": []})

    ti = M.team_inputs(stats)
    L = league_avg_rating(ti)
    games = M.index_games(games_doc, boxes_doc)
    feats = M.schedule_features(games)
    form = M.box_form(boxes_doc)
    travel = M.travel_table(games, feats, arenas)
    shares = M.minutes_shares(boxes_doc)
    inj = M.injury_editions(inj_doc, os.path.join(ROOT, "data", "captures",
                                                 "2026-11-15", "raw"))
    log("teams %d | games %d | horizon candidates %d"
        % (len(ti["teams"]), len(games),
           sum(1 for g in games.values() if HORIZON_START <= g["date"] <= HORIZON_END)))

    horizon_games = [g for g in games.values()
                     if HORIZON_START <= g["date"] <= HORIZON_END and not g["is_final"]]
    horizon_games.sort(key=lambda g: (g["date"], g.get("tip_utc") or ""))

    # ---- the pinned home-court advantage -----------------------------------
    hca = M.pin_hca(ti, games, TRAIN_FROM, TRAIN_TO, horizon_games)
    if hca:
        log("HCA pinned to the measured home-win rate %.4f (%.1f points)"
            % (hca["measured_home_win_rate"], hca["hca_points_pinned"]))

    # ---- the newest injury edition ----------------------------------------
    newest_edition = None
    for e in sorted(inj["editions"], key=lambda r: r["edition_id"]):
        if e.get("http_status") == 200 and e.get("rows"):
            newest_edition = e
    injury_rows = (newest_edition or {}).get("rows", [])
    log("newest injury edition %s with %d rows"
        % ((newest_edition or {}).get("edition_id"), len(injury_rows)))

    # ---- per-game model ----------------------------------------------------
    rows = []
    for g in horizon_games:
        ref = reference_line(ti, g)
        baseA, poss, ptsA = base_margin_ratings(ti, g, L)
        baseB = M.base_margin_form(form, g, poss) if (poss and baseA is not None) else None
        total_ppp, ppp_home, ppp_away = (None, None, None)
        if poss and baseA is not None:
            total_ppp, ppp_home, ppp_away = M.total_ppp(ti, g, poss)
        form_total = None
        fh, fa = form.get(g["home"]), form.get(g["away"])
        if poss and fh and fa:
            try:
                form_total = poss * ((float(fh["offensive_ppp"]) + float(fa["defensive_ppp"])) / 2.0
                                     + (float(fa["offensive_ppp"]) + float(fh["defensive_ppp"])) / 2.0)
            except (TypeError, ValueError):
                form_total = None
        hca_pts = hca["hca_points_pinned"] if hca else None
        marginA = (baseA + hca_pts) if (baseA is not None and hca_pts is not None) else None
        marginB = (baseB + hca_pts) if (baseB is not None and hca_pts is not None) else None
        disagreement = (abs(marginA - marginB)
                        if (marginA is not None and marginB is not None) else None)
        f_home = feats.get((g["home"], g["game_id"]), {})
        f_away = feats.get((g["away"], g["game_id"]), {})
        tv = travel.get(g["game_id"], {})
        rows.append({
            "date": g["date"],
            "game_id": g["game_id"],
            "matchup": "%s@%s" % (g["away"], g["home"]),
            "away": g["away"], "home": g["home"],
            "away_record_printed": g.get("away_record_printed"),
            "home_record_printed": g.get("home_record_printed"),
            "time_et": g.get("tip_local"),
            "tip_utc": g.get("tip_utc"),
            "arena_name": g.get("arena_name"),
            "arena_city": g.get("arena_city"),
            "possessions": poss,
            "estimator_a": {
                "name": "Efficiency ratings (official team-stat pages)",
                "base_margin": baseA,
                "hca_points": hca_pts,
                "margin": marginA,
                "total": ptsA,
                "source": "https://www.nba.com/stats/teams/advanced",
            },
            "estimator_b": {
                "name": "Box-score form (raw official box scores, last 10 games)",
                "base_margin": baseB,
                "hca_points": hca_pts,
                "margin": marginB,
                "total": form_total,
                "source": "https://www.nba.com/games?date=%s" % g["date"],
            },
            "disagreement_points": disagreement,
            "disagreement_headline": (
                "A and B differ by %.1f points" % disagreement
                if disagreement is not None else None),
            "reference": ref,
            "total_possessions_x_ppp": total_ppp,
            "total_ppp_home": ppp_home,
            "total_ppp_away": ppp_away,
            "total_avg_of_scoring_averages": M.total_avg_of_averages(ti, g),
            "home_rest_days": f_home.get("rest_days"),
            "away_rest_days": f_away.get("rest_days"),
            "home_back_to_back": f_home.get("back_to_back"),
            "away_back_to_back": f_away.get("back_to_back"),
            "home_three_in_four": f_home.get("three_in_four"),
            "away_three_in_four": f_away.get("three_in_four"),
            "home_games_last_4_days": f_home.get("games_last_4_days"),
            "away_games_last_4_days": f_away.get("games_last_4_days"),
            "away_travel_miles": tv.get("away_travel_miles"),
            "home_travel_miles": tv.get("home_travel_miles"),
            "away_travel_from_city": tv.get("away_travel_from_city"),
            "home_travel_from_city": tv.get("home_travel_from_city"),
            "coordinate_source_url": tv.get("coordinate_source_url"),
            "slate_source_url": g.get("slate_source_url"),
            "box_score_url": g.get("box_score_url"),
        })

    # ---- out-of-sample evaluation of A, B and the reference ---------------
    oos = M.measure_window(games, OOS_FROM, OOS_TO)
    ev = {"window": {"from": OOS_FROM, "to": OOS_TO}, "games": len(oos)}
    pairs = {"A": [], "B": [], "reference": []}
    errs = {"A": [], "B": [], "reference": []}
    terrs = {"A": [], "B": [], "reference": []}
    for m in oos:
        g = games[m["game_id"]]
        ref = reference_line(ti, g)
        baseA, poss, ptsA = base_margin_ratings(ti, g, L)
        baseB = M.base_margin_form(form, g, poss) if (poss and baseA is not None) else None
        hca_pts = hca["hca_points_pinned"] if hca else None
        marginA = (baseA + hca_pts) if (baseA is not None and hca_pts is not None) else None
        marginB = (baseB + hca_pts) if (baseB is not None and hca_pts is not None) else None
        sigma = hca["margin_sigma_points"] if hca else None
        if not sigma:
            continue
        y = 1 if m["home_win"] else 0
        for key, mv in (("A", marginA), ("B", marginB),
                        ("reference", ref["margin"] if ref else None)):
            if mv is None:
                continue
            p = M.phi(mv / sigma)
            pairs[key].append((p, y))
            errs[key].append(abs(mv - m["margin"]))
        for key, tv in (("A", ptsA), ("B", None), ("reference", ref["total"] if ref else None)):
            if tv is None:
                continue
            t = M.total_ppp(ti, g, poss)[0] if key == "A" else None
            if key == "A" and t is not None:
                terrs["A"].append(abs(t - (m["home_pts"] + m["away_pts"])))
            elif key == "reference" and tv is not None:
                terrs["reference"].append(abs(tv - (m["home_pts"] + m["away_pts"])))
    for key in ("A", "B", "reference"):
        ev["log_loss_" + key] = log_loss(pairs[key])
        ev["brier_" + key] = (sum((p - y) ** 2 for p, y in pairs[key]) / len(pairs[key])
                                 if pairs[key] else None)
        ev["mae_margin_" + key] = (sum(errs[key]) / len(errs[key]) if errs[key] else None)
        ev["n_" + key] = len(pairs[key])
    ev["mae_total_A"] = (sum(terrs["A"]) / len(terrs["A"]) if terrs["A"] else None)
    ev["mae_total_reference"] = (sum(terrs["reference"]) / len(terrs["reference"])
                                  if terrs["reference"] else None)
    # blend weight from the measured out-of-sample log-loss
    la, lb = ev.get("log_loss_A"), ev.get("log_loss_B")
    if la is not None and lb is not None:
        w_a = 1.0 / (1.0 + M.math.exp(lb - la)) if abs(lb - la) < 50 else (1.0 if la < lb else 0.0)
    else:
        w_a = 0.5
    ev["blend_weight_A"] = w_a
    ev["blend_weight_B"] = 1.0 - w_a
    ev["blend_weight_rule"] = ("logistic weight on the measured out-of-sample "
                               "log-loss difference: w_A = 1 / (1 + exp(LL_B - LL_A))")
    # market-anchored weight: the anchor stands in for the market because no
    # NBA-operated source publishes a closing line
    lr = ev.get("log_loss_reference")
    ev["market_leg"] = {
        "status": "BLANK - no official closing line is published by any "
                  "NBA-operated source, so the market leg cannot be filled in",
        "source_url": None,
        "flag": "F3",
    }
    if la is not None and lr is not None:
        ev["anchor_weight_model"] = 1.0 / (1.0 + M.math.exp(lr - la))
    else:
        ev["anchor_weight_model"] = None
    ev["anchor_weight_rule"] = ("the anchor (the naive reference line) is weighted "
                                 "against the model by the same measured "
                                 "out-of-sample log-loss difference; the market "
                                 "leg stays blank until an official closing line "
                                 "exists")
    ev["note"] = ("Log-loss, Brier and MAE are measured on the %d official games "
                  "of the out-of-sample window. The ratings behind them are the "
                  "published season-to-date ratings, which include games played "
                  "after the training window; that is disclosed here rather than "
                  "hidden." % len(oos))

    # apply the blend weight and the anchor to each horizon row
    for r in rows:
        a, b = r["estimator_a"]["margin"], r["estimator_b"]["margin"]
        r["blend_margin"] = (w_a * a + (1 - w_a) * b) if (a is not None and b is not None) else None
        ref = r.get("reference") or {}
        r["anchor_margin"] = ref.get("margin")
        r["anchored_margin"] = (ev["anchor_weight_model"] * r["blend_margin"]
                                + (1 - ev["anchor_weight_model"]) * ref["margin"]
                                ) if (r["blend_margin"] is not None
                                     and ref.get("margin") is not None
                                     and ev["anchor_weight_model"] is not None) else None
        r["market_anchored_margin"] = None       # no official closing line exists
        r["market_anchored_status"] = "BLANK - no official closing line exists"

    write_json(os.path.join(DER, "horizon.json"), {
        "generated_at_utc": now_utc(),
        "horizon": {"start": HORIZON_START, "end": HORIZON_END,
                    "max_days_ahead": 3},
        "hca_pinning": hca,
        "headline": "The published headline for every game is the disagreement "
                    "between the two independent estimators. The blend is printed "
                    "underneath it.",
        "rows": rows,
    })
    write_json(os.path.join(DER, "estimates.json"), {
        "generated_at_utc": now_utc(),
        "estimator_a": "Efficiency ratings: the official advanced team table "
                       "(OFF_RTG/DEF_RTG/PACE) with the league-average rating "
                       "removed, scaled to the game's possessions.",
        "estimator_b": "Box-score form: offensive and defensive points-per-"
                       "possession rebuilt from the raw official box scores of each "
                       "team's last ten games (POSS = FGA + 0.44*FTA - OREB + TOV).",
        "hca_pinning": hca,
        "evaluation": ev,
        "market_anchored_prior": {
            "rule": "blended line = w_model * model line + (1 - w_model) * market "
                    "line, with w_model set from the measured out-of-sample "
                    "log-loss difference",
            "measured_weight_model": ev.get("anchor_weight_model"),
            "market_line": None,
            "market_line_status": ev["market_leg"]["status"],
            "flag": "F3",
        },
    })
    log("horizon rows %d | log-loss A %.4f B %s ref %s"
        % (len(rows), ev.get("log_loss_A") or 0, ev.get("log_loss_B"),
           ev.get("log_loss_reference")))

    # ---- the official result feed -----------------------------------------
    results = []
    for gid, g in sorted(games.items()):
        results.append({
            "date": g["date"], "game_id": gid,
            "away": g["away"], "home": g["home"],
            "away_team_name": g.get("away_name"), "home_team_name": g.get("home_name"),
            "status": g.get("status_text"),
            "is_final": g["is_final"],
            "ot": g.get("ot"),
            "final_away_score": g.get("final_away_score"),
            "final_home_score": g.get("final_home_score"),
            "away_quarter_scores": g.get("away_quarter_scores"),
            "home_quarter_scores": g.get("home_quarter_scores"),
            "away_quarter_sum": g.get("away_quarter_sum"),
            "home_quarter_sum": g.get("home_quarter_sum"),
            "quarters_reconcile": g.get("quarters_reconcile"),
            "tip_utc": g.get("tip_utc"), "tip_local": g.get("tip_local"),
            "arena_name": g.get("arena_name"), "arena_city": g.get("arena_city"),
            "source_url": g.get("box_score_url") or g.get("slate_source_url"),
            "slate_source_url": g.get("slate_source_url"),
        })
    write_json(os.path.join(DER, "results.json"), {
        "generated_at_utc": now_utc(),
        "rule": "One row per official game: date, both teams, the final score and "
                "the quarter-by-quarter scores. A game counts as settled only when "
                "the official page says Final AND the printed quarter lines add up "
                "to the printed final.",
        "rows": results,
        "counts": {"games": len(results),
                   "finals": sum(1 for r in results if r["is_final"]),
                   "finals_reconciling": sum(1 for r in results
                                             if r["is_final"] and r["quarters_reconcile"])},
    })
    log("result feed rows %d" % len(results))

    # ---- minutes redistribution and player logs ---------------------------
    redist = []
    for r in rows:
        red = M.redistribution(shares, injury_rows, r["date"])
        redist.append({"date": r["date"], "game_id": r["game_id"],
                       "matchup": r["matchup"], "rows": red})
    minutes = {
        "generated_at_utc": now_utc(),
        "injury_edition_used": (newest_edition or {}).get("edition_id"),
        "injury_edition_url": (newest_edition or {}).get("url"),
        "top8_minutes_shares": {t: shares[t]["top8"] for t in sorted(shares)},
        "status_weight_rule": M.STATUS_WEIGHT,
        "redistribution": redist,
        "source": "official box scores and the official injury report",
    }
    write_json(os.path.join(DER, "minutes.json"), minutes)

    # ---- per-player game logs --------------------------------------------
    logs = player_logs(boxes_doc, injury_rows, games)
    write_json(os.path.join(DER, "player_logs.json"), logs)
    log("player logs: %d players, %d rows"
        % (logs["players_counted"], logs["rows_counted"]))

    # ---- the lines view the site's picks page reads -----------------------
    import statistics as _st
    _m, _t = [], []
    for r in results:
        if not r.get("is_final"):
            continue
        fa, fh = r.get("final_away_score"), r.get("final_home_score")
        if fa is None or fh is None:
            continue
        _m.append(int(fh) - int(fa))
        _t.append(int(fh) + int(fa))
    _sigma = _st.pstdev(_m) if len(_m) > 2 else None
    _lv = lines_view(rows, ev, minutes, _sigma)
    # rotation availability per game, for the picks page column
    _av = {}
    for blk in minutes.get("redistribution", []):
        _lost = {}
        for rr in blk.get("rows", []):
            _lost[rr["team"]] = _lost.get(rr["team"], 0.0) + (rr.get("share_to_replace") or 0.0)
        _av[blk["game_id"]] = _lost
    for _row in _lv:
        _lost = _av.get(_row["game_id"], {})
        _row["home_rotation_availability"] = _lost.get(_row["home"])
        _row["away_rotation_availability"] = _lost.get(_row["away"])
        if _row["home"] in _lost:
            _row["home_report_status"] = "minutes at risk %.1f%%" % (100 * _lost[_row["home"]])
        if _row["away"] in _lost:
            _row["away_report_status"] = "minutes at risk %.1f%%" % (100 * _lost[_row["away"]])
    write_json(os.path.join(DER, "lines_view.json"),
               {"generated_at_utc": now_utc(), "rows": _lv,
                "sigma_margin": _sigma,
                "note": "The 2026-11-15 rolling-slate horizon, in the field names the "
                        "site's picks page reads."})

    log("model stage complete")
    return {
        "ti": ti, "games": games, "feats": feats, "form": form, "travel": travel,
        "shares": shares, "inj": inj, "injury_rows": injury_rows,
        "newest_edition": newest_edition, "rows": rows, "ev": ev, "hca": hca,
        "results": results, "L": L,
    }


if __name__ == "__main__":
    sys.exit(main())
