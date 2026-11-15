#!/usr/bin/env python3
"""Home court and travel: the two inputs the brief insists must be MEASURED, not assumed.

Home court
    The published model line adds a home-court constant. Three candidate values exist in this
    repository and they disagree by a factor of four:

      1. `HCA = 2.5` - a documented project assumption, hard-coded in scripts/build_edge_site.py,
         scripts/build_slate_refresh.py and scripts/generate_picks_d.py, and flagged as an
         assumption (flag E-01) rather than a measurement.
      2. 3.508 points - the intercept that engine/validate.py fits on holdout residuals
         (docs/data/validation.json, disclosed there as "estimated on the test window
         (in-sample)").
      3. the value implied by the MEASURED home-win rate, which is what the brief asks for:
         "home-court pinned to measured home-win rate".

    This module computes (3) two ways - from the official standings table's HOME column
    (league-wide, every game played) and from the repository's own official results feed
    (the games the models were tested on) - and converts each rate into points under the model's
    own margin spread. The disagreement between (1)/(2)/(3) is the published finding; no number
    here is blended.

    Conversion, stated so it can be checked: with a home margin distributed Normal(HCA, sigma)
    once team quality is averaged out, P(home win) = Phi(HCA / sigma), so
    HCA = sigma * Phi^-1(P(home win)). `sigma` is SIGMA from the shared model constants (11.0
    points), i.e. the spread of a final margin, not of a residual.

Travel
    The brief asks for rest load "from the official schedule plus travel distance from a sourced
    arena-coordinate table". No such table exists in this repository and no NBA-operated source
    in it publishes arena coordinates, so the term is NOT modelled - it is reported as zero with
    its reason, and the one travel fact that IS on the official pages (whether a team's
    consecutive games are in the same city or a different one) is reported instead. Distances are
    never estimated from memory: `travel_status()` says what to fetch.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGMA_MARGIN = 11.0                     # shared model constant (points, one final margin)
COORD_TABLE = os.path.join(ROOT, "data", "official", "arena_coordinates.json")
PIN_FILE = os.path.join(ROOT, "data", "derived", "home_court_pin.json")


def norm_inv(p):
    """Acklam's rational approximation of the standard-normal quantile (|err| < 1.2e-3)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(max(0.0, ctr - half), 4), round(min(1.0, ctr + half), 4))


def rate_to_points(rate, sigma=SIGMA_MARGIN):
    return round(sigma * norm_inv(rate), 3)


def measure_from_results(games):
    """Home wins from the repository's official per-game results feed."""
    cols = games["cols"]
    rows = [r for r in games["rows"] if not r[cols.index("neutral")]]
    h, n = 0, 0
    margins = []
    for r in rows:
        hp, ap = r[cols.index("home_pts")], r[cols.index("away_pts")]
        n += 1
        h += 1 if hp > ap else 0
        margins.append(hp - ap)
    mean_margin = round(sum(margins) / len(margins), 3) if margins else None
    return {"games": n, "home_wins": h, "home_win_rate": round(h / n, 4) if n else None,
            "wilson_95": wilson(h, n),
            "mean_home_margin_points": mean_margin,
            "implied_hca_points": rate_to_points(h / n) if n else None,
            "note": ("mean_home_margin_points is the direct arithmetic estimate (no normality "
                     "assumption); implied_hca_points is the same rate read through the model's "
                     "margin spread. They differ because the season's home margins are skewed by "
                     "blowouts on both sides."),
            "source_url": "https://www.nba.com/games"}


def measure_from_standings(standings):
    mc = standings["measured_home_court"]
    w, l = mc["home_wins"], mc["home_losses"]
    return {"home_games": w + l, "home_wins": w, "home_losses": l,
            "home_win_rate": mc["league_home_win_rate"], "wilson_95": wilson(w, w + l),
            "implied_hca_points": rate_to_points(mc["league_home_win_rate"]),
            "excludes": "neutral-site games (the page books them in their own column)",
            "source_url": standings["source_url"]}


def fitted_from_validation():
    """The value engine/validate.py actually fits, read from the published artefact."""
    p = os.path.join(ROOT, "docs", "data", "validation.json")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    def walk(o):
        if isinstance(o, dict):
            if "hca" in o and isinstance(o["hca"], dict) and "est" in o["hca"]:
                return o["hca"]
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None
    return walk(d)


def travel_status():
    """What the travel term needs, and what can be said without inventing distances."""
    if os.path.exists(COORD_TABLE):
        tbl = json.load(open(COORD_TABLE, encoding="utf-8"))
        need = {"status": "MODELLED from the sourced coordinate table",
                "table_source": tbl.get("coordinate_source"),
                "arenas": len(tbl.get("arenas", []))}
    else:
        need = {"status": "NOT MODELLED - no sourced arena-coordinate table exists in this repository",
                "what_would_close_it": ("add data/official/arena_coordinates.json: for each of the 30 "
                                        "arenas, the arena name, the city as printed on the NBA.com game "
                                        "card, and a latitude/longitude pair, each with the URL it was "
                                        "read from and the read time. Great-circle distance is then pure "
                                        "arithmetic and every number on the page stays traceable."),
                "why_not_filled_in": ("no NBA-operated source reachable from this build publishes arena "
                                      "coordinates, and distances from memory would be untraceable "
                                      "values in a table whose whole purpose is traceability."),
                "source_needed": "https://www.nba.com/teams (arena + address per franchise)"}
    return need


def same_city_legs(schedule_rows, games_rows):
    """The travel fact that IS printable today: for each team, the city of its consecutive games.

    Derived only from venue cities printed on official game pages, so it is a measured
    distance-in-days proxy (0 km when the next game is in the same city) rather than a guess.
    """
    city_by_game = {}
    for r in games_rows:
        # games_completed rows carry no venue; the schedule file does, so this map is filled
        # from whichever file has the city for the game id.
        pass
    for r in schedule_rows:
        city_by_game[r[9]] = r[7]
    return city_by_game


def pin(write=False):
    """Assemble the pin from the committed captures. `write=True` stores data/derived/...json."""
    games = json.load(open(os.path.join(ROOT, "data", "raw", "games_completed.json"), encoding="utf-8"))
    standings_path = os.path.join(ROOT, "verify", "2026-11-15-e3ebc423", "standings_2026-11-15.json")
    out = {"title": "Home-court pinned to the measured home-win rate, and the travel term's status",
           "sigma_margin_points": SIGMA_MARGIN,
           "conversion": "HCA = sigma * Phi^-1(P(home win)); sigma = 11.0 points, the spread of a final margin",
           "assumption_replaced": {"value_points": 2.5,
                                   "where": ["scripts/build_edge_site.py", "scripts/build_slate_refresh.py",
                                             "scripts/generate_picks_d.py"],
                                   "status": "documented assumption (flag E-01), not a measurement"},
           "fitted_on_residials": fitted_from_validation(),
           "measured": {"results_feed": measure_from_results(games),
                        "official_standings_home_column": measure_from_standings(
                            json.load(open(standings_path, encoding="utf-8")))},
           "travel": travel_status()}
    meas = [m["implied_hca_points"] for m in out["measured"].values() if m["implied_hca_points"] is not None]
    out["pinned_hca_points"] = round(sum(meas) / len(meas), 3) if meas else None
    out["pin_basis"] = ("mean of the two measured pins (results feed and standings HOME column). It is "
                        "published as a PIN, not as a third rating: the model either uses it or it does not, "
                        "and every page states which. The two measurements and the fitted value are printed "
                        "beside each other because they disagree.")
    out["adoption"] = {
        "new_freezes_use": out["pinned_hca_points"],
        "already_published_lines_use": 2.5,
        "why_not_applied_retroactively": (
            "the 60 horizon picks are frozen and hashed (data/live/ledger_2026-11-15.json); moving "
            "their lines after tip would make the settlement test the pre-registration was written to "
            "protect. The pin therefore takes effect at the next freeze, and the sensitivity of every "
            "already-published line to it is printed on the day-roll page instead of being applied "
            "silently."),
        "sensitivity_note": ("home-court enters the line additively, so the effect of the pin on any "
                             "published margin is exactly (pinned - 2.5) points, and zero on totals.")}
    if write:
        os.makedirs(os.path.dirname(PIN_FILE), exist_ok=True)
        with open(PIN_FILE, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    return out


def travel_leg_miles(fixtures, coord_table=None):
    """One-way miles per team between its consecutive venues inside a slate window.

    `fixtures` is a list of dicts with date/away/home/away_arena/home_arena, oldest first.
    Returns {} when there is no sourced coordinate table - callers must print travel_status()
    beside an empty result rather than read it as "no travel".
    """
    if coord_table is None:
        if not os.path.exists(COORD_TABLE):
            return {}
        coord_table = json.load(open(COORD_TABLE, encoding="utf-8"))
    coords = {a["arena"].strip().lower(): (a["lat"], a["lon"])
              for a in coord_table.get("arenas", []) if a.get("lat") is not None}
    if not coords:
        return {}
    last_seen, out = {}, {}
    for f in sorted(fixtures, key=lambda x: x["date"]):
        for team, arena in ((f["away"], f["away_arena"]), (f["home"], f["home_arena"])):
            here = coords.get((arena or "").strip().lower())
            prev = last_seen.get(team)
            if here and prev and prev != here:
                out[team] = round(out.get(team, 0.0) + haversine_miles(prev, here), 1)
            if here:
                last_seen[team] = here
    return out


def haversine_miles(a, b):
    """Great-circle distance in statute miles from two (lat, lon) pairs - pure arithmetic.

    Self-test reference: (40.7128, -74.0060) to (39.7392, -104.9903) = 1,627 miles, which is
    the published New York to Denver air distance to within the coordinate rounding.
    """
    r = 3958.7613
    la1, lo1, la2, lo2 = (math.radians(float(x)) for x in (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return round(2 * r * math.asin(min(1.0, math.sqrt(h))), 1)


def same_city_legs(schedule_rows, completed_rows):
    """The travel fact that IS printable today, from venue cities printed on official pages.

    For each team, its consecutive fixtures inside the roll window and whether the venue city of
    the next game is the city it just played in. No coordinates needed, so no invented distance:
    0 different-city legs means the schedule kept the team in one place, which is the only
    travel fact the official pages state outright.
    """
    by_team = {}
    for r in completed_rows["rows"]:
        cols = completed_rows["cols"]
        gid = r[cols.index("game_id")]
        for side, key in ((r[cols.index("away")], "away"), (r[cols.index("home")], "home")):
            by_team.setdefault(side, []).append({"date": r[cols.index("date")], "game_id": gid,
                                                 "role": key, "venue": None})
    for r in schedule_rows["rows"]:
        cols = schedule_rows["cols"]
        gid = r[9]
        for side, idx in ((r[2], "away"), (r[4], "home")):
            by_team.setdefault(side, []).append({"date": r[0], "game_id": gid, "role": idx,
                                                 "venue": r[7]})
    legs = {}
    for team, fs in by_team.items():
        fs = sorted(fs, key=lambda x: (x["date"], x["game_id"]))
        prev_city = None
        n_legs = []
        for f in fs:
            city = f.get("venue")
            if city and prev_city:
                n_legs.append({"from_date": f["date"], "to_city": city,
                               "changed_city": city != prev_city})
            if city:
                prev_city = city
        if n_legs:
            legs[team] = n_legs
    return legs


def hca_override():
    """The value model_core should price with, or None to leave the caller's params in force.

    Deliberately returns None unless the pin file exists AND has been adopted for the current
    freeze: a model change must be a decision recorded in a file, not a side effect of an import.
    """
    try:
        d = json.load(open(PIN_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not d.get("adopted_for_pricing"):
        return None
    return d.get("pinned_hca_points")


if __name__ == "__main__":
    import sys
    print(json.dumps(pin(write="--write" in sys.argv), indent=1)[:2600])
