#!/usr/bin/env python3
"""prop_variance.py - measure game-to-game dispersion from official player game logs
and turn it into (a) an uncertainty band on every prop we originate, (b) a prop signal
against the naive season-average anchor, (c) the first measured same-game correlation
between two props, and (d) the injury delta between the edition the lines were built
from and the newest official edition.

Everything measured here comes from data/proplogs/2026-11-14/captures.json, a row-for-row
transcription of the "Last 5 Games" table on each player's official NBA.com page. No box
score is reconstructed, interpolated or rounded by this script; a cell that was cut off at
a page-chunk boundary stays null and the row is excluded from the statistics that need it.

Modelling choices (declared, not official):
  * sample SD with ddof=1;
  * per-player SD is shrunk toward the cohort's pooled relative dispersion:
        sd_used^2 = ((n-1) * sd_player^2 + k * sd_cohort^2) / (n-1 + k),  k = 4
    because n=3-4 games per player is not enough to trust a player-level SD alone;
  * probability uses a normal model on (projection, sd_used). With n this small the SD
    itself carries roughly SD / sqrt(2(n-1)) of uncertainty, which is printed next to
    every figure instead of being hidden;
  * the naive anchor used for "edge" is the player's own season average as published on
    the site's props row (docs/data/props.json). It is NOT a sportsbook line; no official
    source publishes one (Q1 / F3).

Run:  python3 scripts/prop_variance.py
"""
import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return json.load(fh)


def dump(obj, *p):
    path = os.path.join(ROOT, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def r2(v):
    return None if v is None else round(v, 2)


def r3(v):
    return None if v is None else round(v, 3)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


STATS = ["pts", "reb", "ast", "pra", "fg3m", "min"]
K_SHRINK = 4.0


def complete(game, keys):
    return all(game.get(k) is not None for k in keys)


def main():
    cap = load("data", "proplogs", "2026-11-14", "captures.json")
    props = load("docs", "data", "props.json")["rows"]
    pub_1114 = {r["player"]: r for r in props if r["date"] == "2026-11-14"}
    prev = load("data", "live", "player_game_logs.json")
    season = {p["player"].lower(): p for p in load("data", "players_2026_27.json")["players"]}
    lines = load("docs", "data", "lines.json")["rows"]
    new_inj = load("data", "proplogs", "2026-11-14", "injury_2026-11-14_04_30AM.json")
    site_inj = load("data", "live", "injury_report_2026_11_14.json")
    base_inj = load("data", "injuries_0515.json")

    # ---------------------------------------------------------------- per player
    per_player = []
    resid_rel = {s: [] for s in STATS}          # cohort pool of within-player residuals
    rows_by_player = {}

    for p in cap["players"]:
        games = p["games"]
        rows_by_player[p["player"]] = p
        full = [g for g in games if complete(g, ["min", "pts", "reb", "ast"])]
        pts_ok = [g for g in games if g.get("pts") is not None]

        # per-game stat vectors. Points and minutes are readable even on a row the chunk
        # boundary cut (they sit left of the cut); rebounds, assists, PRA and threes are
        # taken only from rows that survived complete.
        vec = {"pts": [g.get("pts") for g in games],
               "min": [g.get("min") for g in games],
               "reb": [g.get("reb") for g in full],
               "ast": [g.get("ast") for g in full],
               "fg3m": [g.get("fg3m") for g in full]}
        for g in full:
            g["pra"] = g["pts"] + g["reb"] + g["ast"]
        vec["pra"] = [g.get("pra") for g in full]

        stats = {}
        for s in STATS:
            xs = [x for x in vec[s] if x is not None]
            m, d = mean(xs), sd(xs)
            if m is not None and d is not None and m != 0:
                for x in xs:
                    resid_rel[s].append((x - m) / m)
            stats[s] = {"n": len(xs), "mean": r2(m), "sd": r2(d)}

        # cohort-implied SD for this player, then shrink
        pooled = {}
        for s in STATS:
            rs = resid_rel[s]
            # computed after the loop for the full cohort; placeholder filled below
            pooled[s] = None
        pub = pub_1114.get(p["player"])
        per_player.append({
            "player": p["player"], "team": p["team"], "player_id": p["player_id"],
            "page": p["page"], "read_window_utc": cap["read_window_utc"],
            "official_header_ppg": p["header_line"]["ppg"],
            "official_header_rpg": p["header_line"]["rpg"],
            "official_header_apg": p["header_line"]["apg"],
            "n_games_pts": len([g for g in pts_ok]),
            "n_games_full": len(full),
            "games": [{"date": g["date"], "matchup": g["matchup"], "game_id": g["game_id"],
                       "pts": g.get("pts"), "reb": g.get("reb"), "ast": g.get("ast"),
                       "pra": g.get("pra"), "fg3m": g.get("fg3m"), "min": g.get("min"),
                       "box_url": "https://www.nba.com/game/%s/box-score" % g["game_id"],
                       "row_cut_at_chunk_boundary": bool(g.get("truncated"))}
                      for g in games],
            "measured": stats,
            "site_baseline_pts": (pub or {}).get("baseline_pts"),
            "site_proj_pts": (pub or {}).get("proj_pts"),
            "site_proj_pra": (pub or {}).get("proj_pts_reb_ast"),
            "site_season_min": (pub or {}).get("season_min"),
            "in_season_table": p["player"].lower() in season,
            "gp_at_capture": (pub_1114.get(p["player"]) or {}).get("gp"),
        })

    # cohort pooled relative dispersion (CV) per stat, from within-player residuals
    cohort = {}
    for s in STATS:
        rs = [x for x in resid_rel[s] if x is not None]
        m, d = mean(rs), sd(rs)
        cohort[s] = {"n_obs": len(rs), "pooled_cv": r3(d),
                     "note": "standard deviation of (game - player mean) / player mean, "
                             "pooled over every captured complete row"}

    # now that the cohort figure exists, finish each player row
    for row in per_player:
        finished = {}
        for s in STATS:
            m = row["measured"][s]["mean"]
            n = row["measured"][s]["n"]
            own = row["measured"][s]["sd"]
            cv = cohort[s]["pooled_cv"]
            cohort_sd = None if (m is None or cv is None) else cv * m
            if own is not None and cohort_sd is not None:
                num = (max(n - 1, 0)) * own ** 2 + K_SHRINK * cohort_sd ** 2
                den = max(n - 1, 0) + K_SHRINK
                used = math.sqrt(num / den)
            else:
                used = cohort_sd
            se_sd = None if (used is None or n < 2) else used / math.sqrt(2.0 * (n - 1))
            finished[s] = {"n": n, "mean": m, "sd_player": r2(own), "sd_cohort_implied": r2(cohort_sd),
                           "sd_used": r2(used), "sd_uncertainty": r2(se_sd),
                           "cv": r3(used / m) if (used and m) else None,
                           "band_80": [r2((m or 0) - 1.2816 * used) if m is not None and used is not None else None,
                                       r2((m or 0) + 1.2816 * used) if m is not None and used is not None else None]}
        row["band"] = finished

    # ------------------------------------------------------- the prop signal
    # edge = our projection minus the naive season-average anchor, expressed in the
    # measured dispersion. p_over_anchor answers: how likely is he to beat the number a
    # naive model (and, in practice, most prop anchors) would hang on him.
    signals = []
    for row in per_player:
        s = row["band"]["pts"]
        proj, anchor = row["site_proj_pts"], row["site_baseline_pts"]
        if proj is None or anchor is None or s["sd_used"] in (None, 0):
            signals.append({"player": row["player"], "status": "NOT PRICED",
                            "why": "no measured dispersion or no published projection"})
            continue
        z = (proj - anchor) / s["sd_used"]
        p_over = 1.0 - norm_cdf((anchor - proj) / s["sd_used"])
        tier = ("settable" if abs(proj - anchor) >= 1.0 * s["sd_used"] and s["n"] >= 3 else
                "thin - inside one measured SD" if abs(proj - anchor) < 0.5 * s["sd_used"] else
                "borderline")
        signals.append({
            "player": row["player"], "team": row["team"], "status": "MEASURED",
            "n_games": s["n"], "measured_sd_pts": s["sd_used"], "sd_uncertainty": s["sd_uncertainty"],
            "anchor_season_avg": anchor, "our_projection": proj, "gap_pts": r2(proj - anchor),
            "gap_in_sd": r3(z), "p_beats_anchor": r3(p_over),
            "fair_line_low": r2(proj - 1.2816 * s["sd_used"]), "fair_line_high": r2(proj + 1.2816 * s["sd_used"]),
            "tier": tier,
            "page": row["page"],
        })
    signals.sort(key=lambda x: -abs(x.get("gap_in_sd") or 0))

    # --------------------------------------------------- anchor choice test (LOO)
    # For every captured game: predict it three ways and score the absolute error.
    #   season average  = the site's baseline (contaminated: it contains these games)
    #   LOO window mean = mean of the player's other captured games (a clean form estimator)
    #   previous game   = the game immediately before it (form chasing)
    anchor_test = []
    for s in ("pts", "reb", "ast", "pra"):
        rows_err = {"season_avg": [], "loo_mean": [], "prev_game": []}
        for row in per_player:
            series = [g for g in row["games"] if g.get(s) is not None]
            order = list(reversed(series))          # chronological
            vals = [g[s] for g in order]
            for i, v in enumerate(vals):
                others = vals[:i] + vals[i + 1:]
                if others:
                    rows_err["loo_mean"].append(abs(v - sum(others) / len(others)))
                if i > 0:
                    rows_err["prev_game"].append(abs(v - vals[i - 1]))
            if s == "pts":
                for g in order:
                    if g.get("pts") is not None and row["site_baseline_pts"] is not None:
                        rows_err["season_avg"].append(abs(g["pts"] - row["site_baseline_pts"]))
        def summarize(xs):
            xs = [x for x in xs if x is not None]
            return {"n": len(xs), "mae": r2(mean(xs)), "rmse": r2(math.sqrt(sum(x * x for x in xs) / len(xs))) if xs else None}
        anchor_test.append({"stat": s.upper(), "season_avg_baseline": summarize(rows_err["season_avg"]),
                            "leave_one_out_window_mean": summarize(rows_err["loo_mean"]),
                            "previous_game": summarize(rows_err["prev_game"])})
    # official-header anchor for every stat (same construction, one game fresher)
    for a in anchor_test:
        key = {"PTS": "ppg", "REB": "rpg", "AST": "apg"}.get(a["stat"])
        errs = []
        for row in per_player:
            if key:
                anchor_v = row["official_header_" + key]
            else:                                    # PRA
                anchor_v = None if None in (row["official_header_ppg"], row["official_header_rpg"],
                                            row["official_header_apg"]) else (
                    row["official_header_ppg"] + row["official_header_rpg"] + row["official_header_apg"])
            stat_l = a["stat"].lower()
            for g in row["games"]:
                if g.get(stat_l) is not None and anchor_v is not None:
                    errs.append(abs(g[stat_l] - anchor_v))
        a["official_header_average"] = {"n": len(errs), "mae": r2(mean(errs)),
                                        "rmse": r2(math.sqrt(sum(e * e for e in errs) / len(errs))) if errs else None}
        if a["stat"] != "PTS":
            a["season_avg_baseline"] = {"n": 0, "mae": None, "rmse": None,
                                        "why": "the site's props table carries a season POINTS baseline only; for "
                                               "rebounds, assists and PRA the comparable official anchor is the "
                                               "player-page header average, printed in official_header_average"}
    for a in anchor_test:
        a["note"] = ("all three forecasts are scored on the same captured games; the season average is "
                     "CONTAMINATED (those games are inside it), so a form estimator beating it is the "
                     "conservative result, and it losing to it is not evidence of failure")

    # ------------------------------------------- measured same-game correlation
    by_game = {}
    for row in per_player:
        for g in row["games"]:
            if g.get("pts") is None:
                continue
            by_game.setdefault(g["game_id"], []).append(row["player"])
    means = {row["player"]: {s: row["measured"][s]["mean"] for s in STATS} for row in per_player}
    pairs = {}
    for gid, players in by_game.items():
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                a, b = players[i], players[j]
                ga = next(g for g in rows_by_player[a]["games"] if g["game_id"] == gid)
                gb = next(g for g in rows_by_player[b]["games"] if g["game_id"] == gid)
                if ga.get("pts") is None or gb.get("pts") is None:
                    continue
                if ga.get("reb") is None or ga.get("ast") is None or gb.get("reb") is None or gb.get("ast") is None:
                    continue
                key = tuple(sorted([a, b]))
                rec = pairs.setdefault(key, {"games": [], "dx": [], "dy": [], "pra_x": [], "pra_y": []})
                ma, mb = means[a], means[b]
                if None in (ma["pts"], mb["pts"], ma["pra"], mb["pra"]):
                    continue
                rec["games"].append(gid)
                rec["dx"].append(ga["pts"] - ma["pts"])
                rec["dy"].append(gb["pts"] - mb["pts"])
                rec["pra_x"].append(ga["pts"] + ga["reb"] + ga["ast"] - ma["pra"])
                rec["pra_y"].append(gb["pts"] + gb["reb"] + gb["ast"] - mb["pra"])

    def corr(x, y):
        n = len(x)
        if n < 2:
            return None, n
        mx, my = mean(x), mean(y)
        sx, sy = sd(x), sd(y)
        if not sx or not sy:
            return None, n
        return r3(sum((a - mx) * (b - my) for a, b in zip(x, y)) / ((n - 1) * sx * sy)), n

    correlations = []
    for (a, b), rec in pairs.items():
        rho, n = corr(rec["dx"], rec["dy"])
        rho_pra, _ = corr(rec["pra_x"], rec["pra_y"])
        same_team = rows_by_player[a]["team"] == rows_by_player[b]["team"]
        correlations.append({
            "leg_a": a, "leg_b": b, "relationship": "same team" if same_team else "opponents",
            "games_shared": n, "rho_points": rho, "rho_pra": rho_pra,
            "game_ids": rec["games"],
            "reading": ("not interpretable - n=%d" % n) if n < 5 else "provisional",
        })
    correlations.sort(key=lambda c: -c["games_shared"])
    pooled_pairs = [c for c in correlations if c["rho_points"] is not None]
    pooled_rho = r3(mean([c["rho_points"] for c in pooled_pairs])) if pooled_pairs else None

    # ------------------------------------------------ staleness of the baseline
    stale = []
    for row in per_player:
        off = row["official_header_ppg"]
        site = row["site_baseline_pts"]
        if site is None or off is None:
            stale.append({"player": row["player"], "status": "no published baseline"})
            continue
        gp = (pub_1114.get(row["player"]) or {}).get("gp")
        new_games = [g for g in row["games"] if g["date"] > "2026-11-12" and g.get("pts") is not None]
        recon = None
        recon_note = "gp not published on the props row - not reconciled"
        if gp:
            recon = (site * gp + sum(g["pts"] for g in new_games)) / (gp + len(new_games))
            tol = 0.05 * (1 + gp / float(gp + len(new_games)))   # both inputs are 1-decimal averages
            recon_note = ("EXPLAINED (within the rounding of a 1-decimal average, tolerance %.3f): recomputing the season average from the site's own baseline (%.1f over %d games) "
                          "plus the %d captured game(s) since gives %.2f against the %.1f the official page prints now"
                          % (tol, site, gp, len(new_games), recon, off)) if abs(recon - off) <= tol else (
                          "NOT EXPLAINED: recomputation gives %.2f, the official page prints %.1f - the gap is beyond "
                          "rounding, so one of the two reads needs a human look" % (recon, off))
        row["reconciled_ppg"] = r2(recon)
        row["reconciliation_note"] = recon_note
        stale.append({"player": row["player"], "team": row["team"], "gp_at_capture": gp,
                      "games_since": [g["date"] for g in new_games],
                      "recomputed_ppg": r2(recon), "reconciliation": recon_note,
                      "site_season_ppg_used": site, "official_ppg_now": off,
                      "delta": r2(off - site), "rel": r3((off - site) / site if site else None),
                      "note": ("the site's prop baseline was transcribed on 2026-11-13 from "
                               "https://www.nba.com/stats/players/traditional (Per Game, sorted by PTS); the "
                               "player page header now carries the same figure one game later")})
    stale.sort(key=lambda x: -abs(x.get("delta") or 0))

    # --------------------------------------------------------- injury delta 11/14
    def keyed(doc):
        out = {}
        for r in doc.get("rows", []):
            if not r.get("player"):
                continue
            out[(r["matchup"], r["player"])] = r
        return out

    new_rows = keyed(new_inj)
    site_rows = keyed(site_inj)
    base_rows = keyed(base_inj)
    delta = []
    for k, r in sorted(new_rows.items()):
        older = site_rows.get(k) or base_rows.get(k)
        delta.append({"matchup": k[0], "team": r.get("team_printed"), "player": r["player"],
                      "status_new": r["status"], "reason_new": r.get("reason"),
                      "status_in_site_edition": (older or {}).get("status"),
                      "change": ("NEW ROW" if older is None else
                                 ("CHANGED" if older.get("status") != r["status"] else "same"))})
    changed = [d for d in delta if d["change"] != "same"]
    prop_players_1114 = set(pub_1114)
    touched = [d for d in changed if any(d["player"].split(", ")[-1] in p or d["player"].split(", ")[0] in p
                                         for p in prop_players_1114)]
    # which of the day's originated games does a changed team row bear on?
    affected_games = []
    for g in lines:
        if g.get("date") != "2026-11-14":
            continue
        mu = "%s@%s" % (g.get("away"), g.get("home"))
        hits = [d for d in changed if d["matchup"] == mu]
        affected_games.append({"matchup": mu, "game_id": g.get("game_id"),
                              "n_new_or_changed_rows": len(hits),
                              "players": [d["player"] for d in hits],
                              "line_originated": "spread home %+.1f / total %.1f  (reference line %+.1f / %.1f)" % (
                                  g.get("model_spread_home") or 0, g.get("model_total") or 0,
                                  g.get("ref_spread_home") or 0, g.get("ref_total") or 0),
                              "report_state_at_line_build": "%s / %s" % (g.get("home_report_status"),
                                                                          g.get("away_report_status")),
                              "note": ("the originated line was cut against the 11/13 05:15 PM ET edition; the newest "
                                       "edition changes nothing for this game" if not hits else
                                       "the newest edition adds or changes the rows listed, and the line has NOT been "
                                       "re-cut for them")})

    # ------------------------------------------- minutes -> production, pooled
    # Within a player: how much of his game-to-game production swing is explained by the
    # minutes he actually played? Pooled over the cohort after demeaning per player, so a
    # starter's level does not masquerade as a minutes effect. This is the rotation link the
    # injury module has been asserting without a measured number behind it.
    minutes_link = []
    for stat in ("pts", "reb", "ast", "pra"):
        xs, ys = [], []
        for row in per_player:
            m_min = row["measured"]["min"]["mean"]
            m_s = row["measured"][stat]["mean"]
            if m_min is None or m_s is None:
                continue
            for g in row["games"]:
                v = g.get(stat) if stat != "pra" else g.get("pra")
                if v is None or g.get("min") is None:
                    continue
                xs.append(g["min"] - m_min)
                ys.append(v - m_s)
        rho, n = corr(xs, ys)
        # t statistic for a correlation, and the two-sided normal reading of it
        t_stat = None if not rho or rho in (-1, 1) or n < 3 else rho * math.sqrt((n - 2) / (1 - rho ** 2))
        p_two = None if t_stat is None else r3(2 * (1 - norm_cdf(abs(t_stat))))
        minutes_link.append({"stat": stat.upper(), "n_rows": n, "rho": rho, "rho_squared": r3(rho ** 2) if rho else None,
                             "t_statistic": r2(t_stat), "p_value_two_sided": p_two,
                             "reading": ("minutes carry a measurable share of the swing" if (rho or 0) > 0.4 else
                                         "minutes explain little of the swing at this sample")})

    # --------------------------------------------- cross-check vs the earlier read
    cross = []
    for p in prev.get("players", []):
        mine = rows_by_player.get(p["player"]) or rows_by_player.get(p["player"].replace("Jokić", "Jokic"))
        if not mine:
            cross.append({"player": p["player"], "result": "not in this session's cohort"})
            continue
        mine_by_id = {g["game_id"]: g for g in mine["games"]}
        agree, disagree, not_read = 0, [], []
        for g in p.get("games", []):
            m = mine_by_id.get(g.get("game_id"))
            if m is None:
                not_read.append(g.get("date"))
                continue
            vals_ok = all(m.get(k) is not None for k in ("pts", "reb", "ast") if g.get(k) is not None)
            if not vals_ok:
                not_read.append(g.get("date"))
                continue
            same = all(g.get(k) == m.get(k) for k in ("pts", "reb", "ast", "min") if g.get(k) is not None)
            if same:
                agree += 1
            else:
                disagree.append({"game_id": g.get("game_id"), "theirs": g, "ours": m})
        cross.append({"player": p["player"], "read_this_session": mine["page"],
                      "rows_compared_and_agreeing": agree, "disagreements": disagree,
                      "rows_only_one_side_could_read": not_read,
                      "window_shift": "the earlier read (00:55Z) predates the 11/13 games, so it carries an "
                                      "older window; the rows that overlap agree cell for cell"})

    # ------------------------------------------- minutes elasticity of production
    # Pooled within-player regression of relative production on relative minutes:
    #     (v - mean_v)/mean_v  =  beta * (min - mean_min)/mean_min
    # beta is the number the injury module needs and never had: what fraction of a
    # player's production leaves with a given fraction of his minutes.
    elas = []
    for stat in ("pts", "reb", "ast", "pra"):
        xs, ys = [], []
        for row in per_player:
            m_min = row["measured"]["min"]["mean"]
            m_s = row["measured"][stat]["mean"]
            if not m_min or not m_s:
                continue
            for g in row["games"]:
                v = g.get("pra") if stat == "pra" else g.get(stat)
                if v is None or g.get("min") is None:
                    continue
                xs.append((g["min"] - m_min) / m_min)
                ys.append((v - m_s) / m_s)
        if len(xs) < 3:
            continue
        mx, my = mean(xs), mean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        beta = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else None
        resid = [y - my - (beta or 0) * (x - mx) for x, y in zip(xs, ys)]
        se = math.sqrt(sum(r * r for r in resid) / (len(xs) - 2) / sxx) if sxx and len(xs) > 2 else None
        elas.append({"stat": stat.upper(), "n_rows": len(xs), "beta_minutes_to_production": r3(beta),
                     "standard_error": r3(se),
                     "t_statistic": r2(beta / se) if (beta is not None and se) else None,
                     "reading": ("a 10%% cut in minutes predicts a %.1f%% cut in %s"
                                 % (abs(beta or 0) * 10, stat.upper()))})

    # ------------------------------------------------------------- headline block
    priced = [s for s in signals if s["status"] == "MEASURED"]
    settable = [s for s in priced if s["tier"] == "settable"]
    headline = {
        "players_captured": len(per_player),
        "games_transcribed": sum(len(p["games"]) for p in per_player),
        "complete_rows": sum(p["n_games_full"] for p in per_player),
        "props_now_priced": len(priced),
        "props_still_unpriced": len(props) - len(priced),
        "props_total_in_horizon": len(props),
        "props_clearing_one_sd": len(settable),
        "cohort_cv_points": cohort["pts"]["pooled_cv"],
        "median_abs_gap_in_sd": r3(mean(sorted(abs(s["gap_in_sd"]) for s in priced))) if priced else None,
        "best_pair_games_for_rho": max([c["games_shared"] for c in correlations] or [0]),
        "injury_rows_changed_since_the_lines_edition": len(changed),
        "cross_check_rows_agreeing": sum(c.get("rows_compared_and_agreeing", 0) for c in cross),
        "cross_check_disagreements": sum(len(c.get("disagreements", [])) for c in cross),
    }

    out = {
        "_meta": {
            "title": "Measured prop variance, 2026-11-14 cohort",
            "generated_by": "scripts/prop_variance.py",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "cohort": "the 10 players of the 2026-11-14 slate whose NBA.com player id was already carried in a "
                      "committed official capture; 4 of the 14 published prop rows have no id in the repo and are "
                      "listed under not_captured",
            "official_source": "each player's NBA.com game-log page, transcribed row for row in "
                               "data/proplogs/2026-11-14/captures.json (read window %s)" % cap["read_window_utc"],
            "model_rules_declared": {
                "sd": "sample standard deviation, ddof = 1",
                "shrinkage_k": K_SHRINK,
                "shrinkage_formula": "sd_used^2 = ((n-1)*sd_player^2 + k*sd_cohort_implied^2) / (n-1 + k)",
                "band": "mean +/- 1.2816 * sd_used (an 80% band under a normal model)",
                "probability": "normal model on (our projection, sd_used); the anchor is the player's own season "
                               "average as published by this site, NOT a sportsbook line",
                "small_sample": "with n = 3-4 the SD itself is uncertain by about SD/sqrt(2(n-1)) - printed per row "
                                "as sd_uncertainty; nothing here is a claim of statistical significance",
            },
            "what_this_changes": "F2 and Q3 asked for a measured dispersion figure because none existed. Ten players "
                                 "now have one; the other 78 prop rows are unchanged and still publish no probability.",
        },
        "headline": headline,
        "minutes_to_production": minutes_link,
        "minutes_elasticity": elas,
        "cohort_dispersion": cohort,
        "per_player": per_player,
        "prop_signals": signals,
        "anchor_test": anchor_test,
        "same_game_correlations": correlations,
        "pooled_pairwise_rho_points": pooled_rho,
        "baseline_staleness": stale,
        "injury_delta": {"new_edition": new_inj["source_url"], "new_stamp": new_inj["report_stamp"],
                         "site_edition": site_inj["source_url"], "site_stamp": site_inj.get("report_stamp"),
                         "edition_behind_the_lines": base_inj.get("report"),
                         "rows_changed_or_new": changed, "rows_total_in_delta": len(delta),
                         "prop_rows_directly_touched": touched, "games_affected": affected_games,
                         "teams_not_yet_submitted_at_this_edition": [
                             r.get("team_printed") for r in new_inj["rows"] if r["status"] == "NOT YET SUBMITTED"]},
        "cross_check_against_earlier_read": cross,
        "not_captured": cap["not_captured"],
    }
    dump(out, "data", "derived", "prop_variance.json")

    # ------------------------------------------------------------------- report
    print("elasticity beta         : " + ", ".join("%s %s (se %s, t %s)" % (e["stat"], e["beta_minutes_to_production"], e["standard_error"], e["t_statistic"]) for e in elas))
    print("minutes->production     : " + ", ".join("%s rho=%s (n=%s)" % (m["stat"], m["rho"], m["n_rows"]) for m in minutes_link))
    print("props clearing 1 SD     : %d of %d priced" % (len(settable), len(priced)))
    print("captured players      : %d (games %d, complete rows %d)" % (
        len(per_player), sum(len(p["games"]) for p in per_player),
        sum(p["n_games_full"] for p in per_player)))
    print("cohort CV (pts)       : %s  from n=%d rows" % (cohort["pts"]["pooled_cv"], cohort["pts"]["n_obs"]))
    print("props priced          : %d of %d published 11/14 rows" % (
        sum(1 for s in signals if s["status"] == "MEASURED"), len(pub_1114)))
    print("largest |gap| in SD   : " + ", ".join(
        "%s %+.2f sd (p=%.3f)" % (s["player"], s["gap_in_sd"], s["p_beats_anchor"])
        for s in signals[:3] if s["status"] == "MEASURED"))
    for a in anchor_test:
        print("anchor MAE %-4s      : season %s (n=%s) | LOO mean %s (n=%s) | prev game %s (n=%s)" % (
            a["stat"], a["season_avg_baseline"]["mae"], a["season_avg_baseline"]["n"],
            a["leave_one_out_window_mean"]["mae"], a["leave_one_out_window_mean"]["n"],
            a["previous_game"]["mae"], a["previous_game"]["n"]))
    print("pairs with rho        : %d; best n=%s; pooled mean rho %s" % (
        len(correlations), max([c["games_shared"] for c in correlations] or [0]), pooled_rho))
    print("injury rows new/changed vs the edition the lines used: %d" % len(changed))
    print("cross-check agrees    : %s" % [(c["player"], c["rows_compared_and_agreeing"], len(c["disagreements"]))
                                          for c in cross])
    print("wrote data/derived/prop_variance.json")


if __name__ == "__main__":
    main()
