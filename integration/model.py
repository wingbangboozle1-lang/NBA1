"""Line origination for the integration desk.

Every number this module publishes comes from one of two places:
  * a transcribed official NBA.com / official.nba.com file under data/, or
  * an entry in ASSUMPTIONS, which is printed on the site as a choice, never as a fact.

The out-of-sample test uses the FIT window (2026-10-20 .. 2026-11-05) to predict the
60 finished games of 2026-11-06 .. 2026-11-13. Nothing from those 60 games is allowed to
touch the ratings, the shrinkage constant, home court or the availability weights. Where a
component could not be estimated without looking forward, it is declared as an assumption
and the look-ahead risk is printed on the page instead of being hidden.

The 2026-11-13 finals enter through data/live/results_2026_11_13_final.json (two-source
capture, session arena/df3fed12-nba1, COORDINATION §21 D03): they are appended to the
graded rows and to the rest-day index at load time. data/raw/games_completed.json is NOT
modified here — it is shared with builds outside this session's claim (request R-X1).
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
        "status": "ASSUMPTION, not measured here. Estimating it from the out-of-sample "
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
        "used_for": "the win probabilities on the graded games. The live slate's "
                    "probabilities instead divide by the measured out-of-sample error σ, "
                    "because once the error is known it is the honest scale. The two are not "
                    "interchangeable and the difference is quantified in "
                    "integration/out/transform_test.json: on this window a normal link near "
                    "σ=11–12 out-scores the measured error-σ, so what costs accuracy here is "
                    "the link function in scripts/build_edge_site.py, not the size of σ.",
        "unit": "points, single-game scoring noise used to set the shrinkage constant",
        "status": "ROUND NUMBER, deliberately conservative. A larger noise term shrinks team "
                  "ratings harder, so this choice makes the model less bold, not more. The "
                  "realised out-of-sample spread is measured below and printed beside it.",
    },
    "sigma_margin": {
        "value": None, "unit": "points",
        "status": "MEASURED from the official final scores in the out-of-sample window "
                  "(60 games, 2026-11-06 .. 2026-11-13). Small sample; the number moves "
                  "whenever the window grows.",
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
def _stamp_key(inj):
    """Sort key from an edition's own printed stamp, e.g. 'Injury Report: 11/14/26 05:00 AM'."""
    import re
    s = str(inj.get("report_stamp") or "")
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{1,2}):(\d{2})\s*(AM|PM)", s)
    if not m:
        return (0, 0, 0, 0, 0, "")
    mo, dy, yr, hh, mm, ap = m.groups()
    hh = int(hh) % 12 + (12 if ap.upper() == "PM" else 0)
    return (2000 + int(yr), int(mo), int(dy), hh, int(mm), s)


def load_injury():
    """The newest official edition present in data/live, chosen by its printed stamp.

    Never overwrites: each edition is its own file. Returns (dict, path) for the file whose
    report_stamp is latest, so pricing always uses the most recent league statement that
    actually exists in the repository.
    """
    import glob
    best = None
    for path in sorted(glob.glob(os.path.join("data", "live", "injury_report_*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                inj = json.load(fh)
        except (OSError, ValueError):
            continue
        if "report_stamp" not in inj or "rows" not in inj:
            continue
        key = _stamp_key(inj)
        if best is None or key > best[0]:
            best = (key, path, inj)
    if best is None:
        raise FileNotFoundError("no injury_report_*.json edition in data/live")
    return best[2], best[1]


def load_inputs():
    windows = load("data", "live", "team_windows.json")
    slate = load("data", "live", "slate_2026_11_14_to_16.json")
    injury, injury_path = load_injury()
    logs = load("data", "live", "player_game_logs.json")
    completed = load("data", "raw", "games_completed.json")
    meta = load("data", "live", "capture_meta.json")
    trad = load("data", "raw", "players_traditional.json")
    sched = load("data", "schedule_2026_11_13_to_16.json")

    # ---- D03 (COORDINATION §21): append the verified 11/13 finals to the graded rows and to
    # the rest-day index. data/raw/games_completed.json stays untouched (shared with builds
    # outside this claim; promotion is request R-X1 for the integration seat). FIT untouched.
    final13 = None
    try:
        final13 = load("data", "live", "results_2026_11_13_final.json")
    except FileNotFoundError:
        final13 = None
    appended = []
    if final13:
        have = {r[7] for r in completed["rows"]}          # game_id column
        for g in final13["games"]:
            if g["game_id"] in have or not g.get("settled"):
                continue
            appended.append([g["date"], g["away"], g["away_pts"], g["home"], g["home_pts"],
                             int(g.get("ot") or 0), int(g.get("neutral") or 0), g["game_id"],
                             "L15_2026-11-13"])
        if appended:
            completed = dict(completed)
            completed["rows"] = list(completed["rows"]) + appended
            completed["note"] = (
                (completed.get("note") or "")
                + f" | +{len(appended)} rows (2026-11-13) appended at load time from "
                  "data/live/results_2026_11_13_final.json by integration/model.py; the raw "
                  "file on disk is unmodified.")

    # ---- D04: prefer the refreshed LIVE window (through 11/13) when that capture exists.
    try:
        windows = dict(windows)
        windows["window_live"] = load("data", "live",
                                      "team_windows_live_2026_11_13.json")["window_live"]
    except (FileNotFoundError, KeyError):
        pass
    # ---- D04: post-finals record reread overlaid on the slate cards (IR-05 closure).
    try:
        records_reread = load("data", "live", "slate_records_reread_2026_11_14.json")["records"]
    except (FileNotFoundError, KeyError):
        records_reread = {}
    for g in slate.get("games", []):
        rr = (records_reread.get(g.get("date"), {}) or {}).get(str(g.get("game_id")))
        if rr:
            g["away_record_as_displayed"] = rr.get("away") or g.get("away_record")
            g["home_record_as_displayed"] = rr.get("home") or g.get("home_record")
            g["record_source_url"] = "https://www.nba.com/schedule"
            g["record_read_at_utc"] = "2026-11-14T09:50Z"
            g["record_lags_one_day"] = False
        else:
            g["away_record_as_displayed"] = g.get("away_record")
            g["home_record_as_displayed"] = g.get("home_record")
            g["record_source_url"] = g.get("source_url")
            g["record_read_at_utc"] = slate.get("retrieved_utc")
            g["record_lags_one_day"] = True

    venue_by_id = {}
    try:
        cap = load("data", "raw", "official_schedule_capture_2026-11-14.json")
        for row in cap["rows"]:
            v = dict(zip(cap["cols"], row))
            venue_by_id[str(v["game_id"])] = v
    except (OSError, ValueError, KeyError):
        pass                          # the venue layer is optional; its absence shows as a blank

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

    return dict(venue_by_id=venue_by_id,
                windows=windows, slate=slate, injury=injury, injury_path=injury_path,
                logs=logs, completed=completed, final13=final13, appended_rows=appended,
                meta=meta, player_season=player_season, played=played)


def neutral_site(venue_row):
    """False when the matched venue sits in a US city, None when we cannot tell.

    The test is on the shape of the published city field (`, ST` suffix), which is what the
    league's own schedule prints for domestic games; international venues (Paris, Mexico City,
    Manila) do not carry a state suffix. Nothing is looked up in a table of known arenas, so
    the rule cannot silently mis-classify a venue this repo has never seen.
    """
    import re as _re
    city = (venue_row or {}).get("city")
    if not city:
        return None
    return False if _re.search(r", [A-Z]{2}$", city) else True


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

    # ---- out of sample: the 60 finished games (11/06..11/13), predicted from FIT and nothing else
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
        sub_by_date = src["injury"].get("submission_state") or {
            "2026-11-14": src["injury"].get("submission_state_2026_11_14", [])}
        sub = {r["team"]: r["state"] for r in sub_by_date.get(g["date"], [])}
        has_report = g["date"] in sub_by_date
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
            "matchup": matchup,
            "away_record": g["away_record_as_displayed"],
            "home_record": g["home_record_as_displayed"],
            "record_source_url": g.get("record_source_url"),
            "record_read_at_utc": g.get("record_read_at_utc"),
            "record_lags_one_day": g.get("record_lags_one_day"),
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
            "venue": (src["venue_by_id"].get(str(g["game_id"])) or {}).get("venue"),
            "city": (src["venue_by_id"].get(str(g["game_id"])) or {}).get("city"),
            "venue_source_url": (src["venue_by_id"].get(str(g["game_id"])) or {}).get(
                "_source", "https://www.nba.com/schedule"),
            "venue_captured_by": "arena/afbb836e-nba1 — an independent capture of the same "
                                 "official pages, not this session's read",
            "neutral_site": neutral_site(src["venue_by_id"].get(str(g["game_id"])) or {}),
            "neutral_site_reason": ("city carries a US state suffix, so the venue is the home "
                                    "team's own building" if neutral_site(
                                        src["venue_by_id"].get(str(g["game_id"])) or {}) is False
                                    else "no venue row matched this game id in the independent "
                                         "capture — neutrality is unknown, not absent"),
            "report_state_away": (sub.get(away, "no row printed for this team") if has_report
                                 else "no edition covers this date yet"),
            "report_state_home": (sub.get(home, "no row printed for this team") if has_report
                                  else "no edition covers this date yet"),
            "report_edition": src.get("injury_path"),
            "report_stamp": src["injury"].get("report_stamp"),
        })

    os.makedirs(OUT, exist_ok=True)
    # Stamp discipline (gate V12): never read the wall clock. The register's latest recorded
    # activity — the original capture time or the newest amendment — is the honest timestamp
    # for a rebuild, and it stays diffable.
    register_latest = max(
        [str(src["meta"].get("captured_at_utc") or "")]
        + [str(a.get("at") or "") for a in src["meta"].get("amendments", [])])
    out = {
        "generated_utc": register_latest or src["meta"]["captured_at_utc"],
        "rebuild_note": ("recomputed by integration/model.py after the 2026-11-13 settlement "
                         "and the 11/14 05:00 AM injury edition; stamp = latest activity in "
                         "data/live/capture_meta.json"),
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
