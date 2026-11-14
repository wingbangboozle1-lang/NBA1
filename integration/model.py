"""Line origination for the integration desk.

Every number this module publishes comes from one of two places:
  * a transcribed official NBA.com / official.nba.com file under data/, or
  * an entry in ASSUMPTIONS, which is printed on the site as a choice, never as a fact.

The out-of-sample test uses the FIT window (2026-10-20 .. 2026-11-05) to predict the
51 finished games of 2026-11-06 .. 2026-11-12. Nothing from those 51 games is allowed to
touch the ratings, the shrinkage constant, home court or the availability weights. Where a
component could not be estimated without looking forward, it is declared as an assumption
and the look-ahead risk is printed on the page instead of being hidden.
"""

import json
import os

from common import OUT, assert_official, load, mean, sd, norm_cdf

TEAM_FULL = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}


def rnd(x, n=2):
    return None if x is None else round(x, n)


ASSUMPTIONS = {
    "hca_points": {
        "value": 2.5, "unit": "points added to the home margin",
        "status": "ASSUMPTION, not measured here. Estimating it from the 51 out-of-sample "
                  "games would be fitting on the test window, so it is held fixed and swept "
                  "at 0.0 / 2.5 / 5.0 on the Gates page instead.",
        "sensitivity": [0.0, 2.5, 5.0],
    },
    "b2b_penalty": {
        "value": 2.0, "unit": "points taken off a team on the second night of a back-to-back",
        "status": "ASSUMPTION. The back-to-back flag is official (it is read off the schedule); "
                  "the size of the penalty is not measured. Swept at 0.0 / 2.0 / 4.0.",
        "sensitivity": [0.0, 2.0, 4.0],
    },
    "absence_points_per_minute_share": {
        "value": 0.35,
        "unit": "margin points surrendered per 1.0 of team-minute share vacated by a NEW absence",
        "status": "ASSUMPTION. The minute share is built from official season minutes and games "
                  "played; the conversion to points is not measured — no lineup or on/off data is "
                  "reachable from this sandbox. Swept at 0.0 / 0.35 / 0.70.",
        "sensitivity": [0.0, 0.35, 0.70],
    },
    "sigma_game_points": {
        "value": 12.0,
        "unit": "points, single-game scoring noise used to set the shrinkage constant",
        "status": "ROUND NUMBER, deliberately conservative. A larger noise term shrinks team "
                  "ratings harder, so this choice makes the model less bold, not more. The "
                  "realised out-of-sample spread is measured below and printed beside it.",
    },
    "sigma_margin": {
        "value": None, "unit": "points",
        "status": "MEASURED from the 51 official final scores in the out-of-sample window. Small "
                  "sample; the number moves whenever the window grows.",
    },
    "price": {
        "value": None, "unit": "odds / juice",
        "status": "ABSENT. No sportsbook price is reachable from this sandbox. Therefore there is "
                  "no break-even price, no closing-line value, no ROI, no Kelly stake and no "
                  "market-consensus gate. Every 'pick' on this desk is a paper forecast graded "
                  "against the final score, not against a price.",
    },
}


# --------------------------------------------------------------------- loading
def load_inputs():
    windows = load("data", "live", "team_windows.json")
    slate = load("data", "live", "slate_2026_11_14_to_16.json")
    injury = load("data", "live", "injury_report_2026_11_14.json")
    logs = load("data", "live", "player_game_logs.json")
    completed = load("data", "raw", "games_completed.json")
    meta = load("data", "live", "capture_meta.json")
    trad = load("data", "raw", "players_traditional.json")
    sched = load("data", "schedule_2026_11_13_to_16.json")

    cols = trad["cols"]
    ip, it, igp, imin, ipts = (cols.index(k) for k in ("player", "team", "gp", "min", "pts"))
    player_season = {}
    for r in trad["rows"]:
        player_season[(str(r[ip]).lower().replace(" ", ""), r[it])] = {
            "gp": r[igp], "min": r[imin], "pts": r[ipts],
            "source_url": trad["source_url"], "listed_as": r[ip], "team": r[it]}

    played = {}
    ccols = completed["cols"]
    for row in completed["rows"]:
        g = dict(zip(ccols, row))
        played.setdefault(g["away"], set()).add(g["date"])
        played.setdefault(g["home"], set()).add(g["date"])
    for g in sched["games"]:
        played.setdefault(g["away"], set()).add(g["date"])
        played.setdefault(g["home"], set()).add(g["date"])

    return dict(windows=windows, slate=slate, injury=injury, logs=logs, completed=completed,
                meta=meta, player_season=player_season, played=played)


def day_index(dstr):
    y, m, d = (int(x) for x in dstr.split("-"))
    from datetime import date as _d
    return _d(y, m, d).toordinal()


def rest_state(played_by_team, team, date):
    """Days between this game and the team's previous captured game, minus one.

    None is returned when nothing earlier exists in the captured window. That is not the
    same as 'rested' — it means unknowable from what was captured — so the caller must
    render a blank, never a zero.
    """
    prior = [d for d in played_by_team.get(team, set()) if d < date]
    if not prior:
        return None, "no earlier game inside the captured schedule window"
    gap = day_index(date) - day_index(max(prior))
    return gap - 1, None


# ---------------------------------------------------------------- ratings
def build_ratings(window):
    """Shrink each team's net rating toward the league mean; k derived from this window only."""
    teams = {ab: dict(v) for ab, v in window["teams"].items()}
    nets = [t["netrtg"] for t in teams.values()]
    mu = mean(nets)
    var_obs = sum((n - mu) ** 2 for n in nets) / (len(nets) - 1)
    gp_mean = mean([t["gp"] for t in teams.values()])
    poss = mean([t["pace"] for t in teams.values()])
    sigma_game_net = ASSUMPTIONS["sigma_game_points"]["value"] / poss * 100.0
    mean_noise = sigma_game_net ** 2 / gp_mean
    var_true = max(1.0, var_obs - mean_noise)
    k = sigma_game_net ** 2 / var_true
    L = mean([t["ortg"] for t in teams.values()])

    out = {}
    for ab, t in teams.items():
        f = t["gp"] / (t["gp"] + k)
        t["shrink"] = round(f, 4)
        t["net_shrunk"] = round(t["netrtg"] * f, 3)
        t["or_shrunk"] = round(L + (t["ortg"] - L) * f, 3)
        t["dr_shrunk"] = round(L + (t["drtg"] - L) * f, 3)
        out[ab] = t
    out["_L"] = round(L, 3)
    diag = {"k": round(k, 3), "L": round(L, 3), "var_obs": round(var_obs, 3),
            "var_true": round(var_true, 3), "gp_mean": rnd(gp_mean, 2),
            "pace_mean": round(poss, 3), "sigma_game_net": round(sigma_game_net, 3),
            "mean_noise": round(mean_noise, 3), "n_teams": len(teams) - 1,
            "source_url": window["source_url"], "label": window["label"]}
    return out, diag


# ---------------------------------------------------------------- projection
def project(rat, away, home, hca=0.0, b2b_pen=0.0, avail_adj=0.0,
            away_rest=None, home_rest=None, neutral=False):
    a, h = rat[away], rat[home]
    L = rat["_L"]
    poss = (a["pace"] + h["pace"]) / 2.0
    pp100_h = h["or_shrunk"] + a["dr_shrunk"] - L
    pp100_a = a["or_shrunk"] + h["dr_shrunk"] - L
    total = (pp100_h + pp100_a) * poss / 100.0
    raw_margin = (h["net_shrunk"] - a["net_shrunk"]) * poss / 100.0
    rest_adj = 0.0
    if home_rest == 0:
        rest_adj -= b2b_pen
    if away_rest == 0:
        rest_adj += b2b_pen
    margin = raw_margin + (0.0 if neutral else hca) + rest_adj + avail_adj
    return {"poss": round(poss, 2), "total": round(total, 2),
            "margin_home": round(margin, 2), "raw_margin_home": round(raw_margin, 2),
            "rest_adj": round(rest_adj, 2), "avail_adj": round(avail_adj, 2),
            "pp100_home": round(pp100_h, 2), "pp100_away": round(pp100_a, 2)}


# ---------------------------------------------------------------- availability
def availability_for(injury, player_season, rat, matchup, team_abbr):
    """Return (rows, minute_share_vacated, n_new_absences).

    Two filters decide whether a listed absence moves the line:
      1. the PDF row must have carried its own Team cell (pagination-dropped rows are shown
         but never used), and
      2. the player must have played every one of his team's games. A season-long absence is
         already inside the season rating, so deducting it again double-counts.
    """
    full = TEAM_FULL[team_abbr]
    team_gp = rat[team_abbr]["gp"]
    rows = [r for r in injury["rows"]
            if r["matchup"] == matchup and r["printed_team"] and r["team_printed"] == full]
    detail, share, new_abs = [], 0.0, 0
    for r in rows:
        d = {"player": r["player"], "status": r["status"], "reason": r["reason"],
             "printed_whole_row": bool(r["printed_team"]), "team_abbr": team_abbr,
             "team_gp": team_gp, "player_gp": None, "minutes_per_game": None,
             "minute_share": None, "classification": "SEASON DATA NOT CAPTURED",
             "moves_the_line": False, "source_url": injury["source_url"]}
        last, _, first = r["player"].partition(",")
        key = ((first + last).strip().lower().replace(".", "").replace(" ", ""))
        prof = player_season.get((key, team_abbr))
        if prof:
            d["player_gp"], d["minutes_per_game"] = prof["gp"], prof["min"]
            d["season_source_url"] = prof["source_url"]
            if r["status"] in ("Out", "Doubtful"):
                if prof["gp"] == team_gp:
                    d["classification"] = "NEW_ABSENCE"
                else:
                    d["classification"] = f"ALREADY_IN_SAMPLE ({prof['gp']} of {team_gp} games played)"
            else:
                d["classification"] = "Cleared/Available — no deduction"
        if d["classification"] == "NEW_ABSENCE" and d["minutes_per_game"] and r["printed_team"]:
            s = d["minutes_per_game"] * d["player_gp"] / (240.0 * team_gp)
            d["minute_share"] = round(s, 4)
            d["moves_the_line"] = True
            share += s
            new_abs += 1
        detail.append(d)
    return detail, round(share, 4), new_abs


# ---------------------------------------------------------------- main
def main():
    src = load_inputs()
    fit_w, live_w = src["windows"]["window_fit"], src["windows"]["window_live"]
    assert_official(fit_w["source_url"], "fit window")
    assert_official(live_w["source_url"], "live window")

    rat_fit, diag_fit = build_ratings(fit_w)
    rat_live, diag_live = build_ratings(live_w)

    # ---- out of sample: the 51 finished games, predicted from the FIT window and nothing else
    cols = src["completed"]["cols"]
    oos, margin_errs, total_errs = [], [], []
    for row in src["completed"]["rows"]:
        g = dict(zip(cols, row))
        if g["away"] not in rat_fit or g["home"] not in rat_fit:
            continue
        hr, hn = rest_state(src["played"], g["home"], g["date"])
        ar, an = rest_state(src["played"], g["away"], g["date"])
        p = project(rat_fit, g["away"], g["home"],
                    hca=ASSUMPTIONS["hca_points"]["value"],
                    b2b_pen=ASSUMPTIONS["b2b_penalty"]["value"],
                    away_rest=ar, home_rest=hr, neutral=bool(g.get("neutral")))
        actual_margin = g["home_pts"] - g["away_pts"]
        actual_total = g["home_pts"] + g["away_pts"]
        em, et = p["margin_home"] - actual_margin, p["total"] - actual_total
        margin_errs.append(em)
        total_errs.append(et)
        sigma = ASSUMPTIONS["sigma_game_points"]["value"]
        oos.append({
            "date": g["date"], "away": g["away"], "home": g["home"],
            "matchup": f"{g['away']}@{g['home']}", "game_id": g["game_id"],
            "source_id": g["source_id"],
            "source_url": f"https://www.nba.com/games?date={g['date']}",
            "away_pts": g["away_pts"], "home_pts": g["home_pts"],
            "ot": g["ot"], "neutral": g["neutral"],
            "actual_margin_home": actual_margin, "actual_total": actual_total,
            "model_margin_home": p["margin_home"], "model_total": p["total"],
            "model_poss": p["poss"], "rest_adj": p["rest_adj"],
            "err_margin": rnd(em, 2), "abs_err_margin": rnd(abs(em), 2),
            "err_total": rnd(et, 2), "abs_err_total": rnd(abs(et), 2),
            "p_home_model": rnd(norm_cdf(p["margin_home"] / (sigma or 12.0)), 4),
            "home_won": 1 if actual_margin > 0 else 0,
            "home_rest_days": hr, "away_rest_days": ar,
            "home_b2b": 1 if hr == 0 else 0, "away_b2b": 1 if ar == 0 else 0,
            "rest_known": (hr is not None and ar is not None),
            "rest_note": None if (hr is not None and ar is not None) else (hn or an),
        })

    ASSUMPTIONS["sigma_margin"]["value"] = rnd(sd(margin_errs), 2)
    ASSUMPTIONS["sigma_margin"]["measured_from"] = f"{len(oos)} out-of-sample games"

    # ---- live: the Nov 14-16 slate from the LIVE window
    games = []
    for g in src["slate"]["games"]:
        away, home = g["away"], g["home"]
        hr, hn = rest_state(src["played"], home, g["date"])
        ar, an = rest_state(src["played"], away, g["date"])
        matchup = f"{away}@{home}"
        sub = {r["team"]: r["state"] for r in src["injury"]["submission_state_2026_11_14"]}
        has_report = g["date"] == "2026-11-14"
        det_a, sh_a, new_a = availability_for(src["injury"], src["player_season"], rat_live,
                                               matchup, away) if has_report else ([], 0.0, 0)
        det_h, sh_h, new_h = availability_for(src["injury"], src["player_season"], rat_live,
                                               matchup, home) if has_report else ([], 0.0, 0)
        coef = ASSUMPTIONS["absence_points_per_minute_share"]["value"]
        avail_adj = round(-coef * sh_h + coef * sh_a, 2)
        p = project(rat_live, away, home,
                    hca=ASSUMPTIONS["hca_points"]["value"],
                    b2b_pen=ASSUMPTIONS["b2b_penalty"]["value"],
                    avail_adj=avail_adj, away_rest=ar, home_rest=hr)
        sigma = ASSUMPTIONS["sigma_margin"]["value"] or ASSUMPTIONS["sigma_game_points"]["value"]
        games.append({
            "date": g["date"], "time_et": g["time_et"], "away": away, "home": home,
            "matchup": matchup, "away_record": g["away_record"], "home_record": g["home_record"],
            "game_id": g["game_id"], "game_url": g["game_url"], "source_url": g["source_url"],
            "leaders_away": g["leaders_away"], "leaders_home": g["leaders_home"],
            "ratings_window": live_w["label"],
            "away_net_shrunk": rat_live[away]["net_shrunk"], "home_net_shrunk": rat_live[home]["net_shrunk"],
            "away_pace": rat_live[away]["pace"], "home_pace": rat_live[home]["pace"],
            "away_gp": rat_live[away]["gp"], "home_gp": rat_live[home]["gp"],
            "projection": p,
            "spread_home": rnd(-p["margin_home"], 1),
            "p_home_win": rnd(norm_cdf(p["margin_home"] / sigma), 4),
            "rest_days_away": ar, "rest_days_home": hr,
            "rest_note": None if (ar is not None and hr is not None) else (an or hn),
            "b2b_away": 1 if ar == 0 else 0, "b2b_home": 1 if hr == 0 else 0,
            "availability_away": det_a, "availability_home": det_h,
            "new_absences_away": new_a, "new_absences_home": new_h,
            "minute_share_vacated_away": sh_a, "minute_share_vacated_home": sh_h,
            "neutral_site": None,
            "neutral_site_reason": "the slate page capture carries no venue field, so neutrality "
                                    "is unknown for these dates and is left blank, not defaulted "
                                    "to a home game",
            "report_state_away": sub.get(away) if has_report else "no 11/15 or 11/16 edition exists yet",
            "report_state_home": sub.get(home) if has_report else "no 11/15 or 11/16 edition exists yet",
        })

    os.makedirs(OUT, exist_ok=True)
    out = {
        "generated_utc": src["meta"]["captured_at_utc"],
        "capture_session": src["meta"]["captured_by_session"],
        "assumptions": ASSUMPTIONS,
        "diagnostics": {"fit": diag_fit, "live": diag_live,
                        "sigma_margin_measured": rnd(sd(margin_errs), 3),
                        "sigma_total_measured": rnd(sd(total_errs), 3),
                        "bias_margin": rnd(mean(margin_errs), 3),
                        "bias_total": rnd(mean(total_errs), 3),
                        "oos_games": len(oos), "live_games": len(games)},
        "backtest": oos, "live_lines": games,
    }
    with open(os.path.join(OUT, "lines.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"originate · oos={len(oos)} live={len(games)} "
          f"sigma_margin={out['diagnostics']['sigma_margin_measured']} "
          f"k_fit={diag_fit['k']} k_live={diag_live['k']} "
          f"MAE_margin={rnd(mean([r['abs_err_margin'] for r in oos]),2)}")
    return out


if __name__ == "__main__":
    main()
