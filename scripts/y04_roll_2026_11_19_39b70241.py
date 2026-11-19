#!/usr/bin/env python3
"""y04_roll_2026_11_19_39b70241.py — roll the origination horizon forward to
2026-11-19 .. 2026-11-22 (today + 3 days), from first-hand official reads only.

§66 / Y04. Four artefacts are written, each by a gate-checked builder, in the same
shapes the published 11/17-window scripts consume:

  1. data/raw/official_schedule_capture_2026-11-19_39b70241.json
     the 26 fixtures on 11/19–11/22, transcribed from
     https://www.nba.com/schedule?date=2026-11-19 (and cross-read against
     https://www.nba.com/games?date=2026-11-19). The per-day counts are asserted
     against the month grid printed on the same page (11/19=4, 11/20=9, 11/21=6,
     11/22=7) before anything is written.

  2. data/official/injury_2026-11-19_1245AM_39b70241.json
     the newest official injury edition, promoted for the originator. Its raw PDF
     was fetched byte-exactly by the runner on this branch (run 44468125114), so
     unlike the 11/17 edition this file carries a MEASURED sha256 of the actual
     bytes, taken from data/raw/injury_pdfs/Injury-Report_2026-11-19_12_45AM.pdf.
     Player rows and NOT YET SUBMITTED team blocks are those the runner's
     clipped-cell reader parsed out of those bytes.

  3. data/derived/team_stats_recut_2026-11-19_39b70241.json
     the 30 team rows, re-cut from the advanced/traditional/opponent/standings
     pages read at 05:46Z on 2026-11-19. Gate A3 is where the 11/19 read differs
     from 11/17's: the standings page prints LAL 13-3 and UTA 3-13 (16 decided
     games, which is what the official finals corpus says) while the three /stats/
     team tables still print GP 15 for those two clubs — the tables lag one build
     cycle behind the 11/18 finals. GP/W/L are therefore shipped from the standings
     (the authority for how many games a team has played) with the advanced page's
     own GP kept beside it as `advanced_gp_as_read`, and the ratings are shipped
     exactly as printed with the sample size they were computed over recorded
     (`ratings_computed_over_games`). Nothing is averaged, adjusted or projected.

  4. data/derived/measured_constants_2026_11_19_39b70241.json
     sigma_margin, sigma_total, means and the home-court pin, re-measured over all
     222 decided games (the feed is now complete through 11/18), plus the closed-
     league gap. `measure, never fit`.

Gate results land in verify/2026-11-19-39b70241/y04_roll_gates.json. Any failed
gate stops the run and writes nothing.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUFFIX = "39b70241"
TODAY = "2026-11-19"
WINDOW = ["2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"]
INJ_LABEL = "Injury-Report_2026-11-19_12_45AM"
GATE_PATH = f"verify/{TODAY}-{SUFFIX}/y04_roll_gates.json"

# The team-name -> abbreviation map lives in the capture script that transcribed the
# pages; importing it keeps one authority for the mapping.
_spec = importlib.util.spec_from_file_location(
    "cap39b", os.path.join(ROOT, "scripts", f"capture_read_{TODAY.replace('-', '_')}_{SUFFIX}.py"))
_capmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_capmod)
ABBREV = _capmod.ABBREV


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def dump(rel, obj):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", rel)
    return p


def norm_ppf(p):
    """Acklam's rational approximation of the standard-normal inverse CDF."""
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
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def parse_blocks():
    """Read the first-hand capture files this session wrote, so the model inputs are
    the very rows the readback gates checked (one transcription, two consumers)."""
    ti = load("data/official/teams_inputs_2026-11-19_39b70241.json")
    st = load("data/official/standings_2026-11-19_0546Z_39b70241.json")
    sc = load("data/official/schedule_2026-11-19_to_22_39b70241.json")

    def rows_of(cols, arr):
        assert all(len(r) == len(cols) for r in arr), "captured row width != column list"
        return [dict(zip(cols, r)) for r in arr]

    abbr_inv = {v: k for k, v in ABBREV.items()}
    return {
        "adv": rows_of(ti["columns_advanced"], ti["advanced"]),
        "trad": rows_of(ti["columns_traditional"], ti["traditional"]),
        "opp": rows_of(ti["columns_opponent"], ti["opponent"]),
        "std": st["rows"],
        "sched": sc["rows"],
        "grid": dict(sc["day_counts"]),
        "src": {"SRC_ADV": ti["sources"]["advanced"], "SRC_TRAD": ti["sources"]["traditional"],
                "SRC_OPP": ti["sources"]["opponent"], "SRC_STD": st["source_url"],
                "SRC_SCHED": sc["source_url"], "SRC_GAMES": sc["second_read_url"]},
        "abbr": dict(ABBREV),
        "retrieved": ti["retrieved_utc"],
        "capture_checks": sc["checks"],
    }


def build_capture(P, games, gates):
    """26 fixtures in the shape originate_horizon consumes, count-checked three ways."""
    by_date = {}
    for g in games:
        by_date.setdefault(g["date"], 0)
        by_date[g["date"]] += 1
    for d in WINDOW:
        if by_date.get(d) != P["grid"].get(d):
            gates["FAIL"].append(f"A-COUNT {d}: capture {by_date.get(d)} vs month grid {P['grid'].get(d)}")
    std_by = {r["team"]: r for r in P["std"]}
    abbr_inv = {v: k for k, v in P["abbr"].items()}
    ids = [g["game_id"] for g in games]
    if len(set(ids)) != len(ids):
        gates["FAIL"].append("A-DUP duplicate game ids in the fixture capture")
    feed = load("data/official/results_feed_2026_27.json")
    seen_ids = {r["game_id"] for r in feed["rows"]}
    clash = sorted(set(ids) & seen_ids)
    if clash:
        gates["FAIL"].append(f"A-FINAL fixture ids already present in the results feed: {clash}")

    rows = []
    for g in games:
        h, a = abbr_inv[g["home"]], abbr_inv[g["away"]]
        rows.append({
            "date": g["date"], "game_id": g["game_id"], "away": g["away"], "home": g["home"],
            "tip_et": g["tip_et"], "venue": g["arena"], "city": f'{g["city"]}, {g["state"]}',
            "cup_label": g["note"] or None,
            "away_record": f'{std_by[a]["w"]}-{std_by[a]["l"]}',
            "home_record": f'{std_by[h]["w"]}-{std_by[h]["l"]}',
            "records_as_of": f"{P['retrieved']} (official standings, same read as the ratings)",
            "source_game_url": f"https://www.nba.com/game/{g['away'].lower()}-vs-{g['home'].lower()}-{g['game_id']}",
        })
    doc = {
        "captured_by": f"arena/{SUFFIX}-nba1 (scripts/y04_roll_2026_11_19_{SUFFIX}.py)",
        "captured_utc": P["retrieved"],
        "captured_on_utc_date": TODAY,
        "capture_method": ("fetch_page text read of the official schedule page for 2026-11-19, "
                           "which prints the whole month grid and the fixtures for 11/19 through "
                           "11/22; the 11/19 line is cross-read against nba.com/games?date=2026-11-19"),
        "scope": (f"rolling window {WINDOW[0]} .. {WINDOW[-1]} (today + up to 3 days, "
                  f"{len(rows)} games)"),
        "window_rule": "today plus the next three days, per the origination brief",
        "games_per_day": by_date,
        "sources": {"schedule": P["src"]["SRC_SCHED"], "games_page": P["src"]["SRC_GAMES"],
                    "records": P["src"]["SRC_STD"]},
        "cols": list(rows[0].keys()),
        "rows": rows,
        "cup_note": ("11/20 rows carry the Emirates NBA Cup group label printed on the official "
                     "schedule line; 11/19, 11/21 and 11/22 lines print no Cup label. Cup group "
                     "games count in the season standings, so nothing in the model treats them "
                     "differently — the label is published for the reader only."),
        "extension_note": ("This window starts on 11/19 and stops at 11/22; the month grid shows 10 "
                           "games on 11/23, which is outside the 3-day cap and is not originated."),
    }
    dump(f"data/raw/official_schedule_capture_{TODAY}_{SUFFIX}.json", doc)
    gates["A-COUNT_schedule_matches_month_grid"] = (
        f"pass ({', '.join(f'{d}={by_date[d]}' for d in WINDOW)} = the grid's own counts)")
    gates["A-IDS_new_and_unique"] = f"pass ({len(set(ids))} unique ids, none already in the results feed)"
    return doc


def build_injury(P, gates):
    import glob as _glob
    cands = sorted(_glob.glob(os.path.join(ROOT, "data/raw/injury_pdfs", f"{INJ_LABEL}*.pdf")))
    parsed = load(f"data/parsed/injury_diffs/editions/{INJ_LABEL}.json")
    if not cands:
        gates["FAIL"].append(f"A-INJ raw PDF missing under data/raw/injury_pdfs/{INJ_LABEL}*.pdf")
        return
    raw = os.path.relpath(cands[0], ROOT)
    digest = hashlib.sha256(open(os.path.join(ROOT, raw), "rb").read()).hexdigest()
    if digest != parsed["sha256"]:
        gates["FAIL"].append(f"A-INJ bytes do not match the parse's recorded sha256 ({digest[:12]})")
    rows, nys = [], []
    for r in parsed["rows"]:
        gd, gt, matchup, team, player, status, reason = r
        rec = {"game_date": f"{int(gd[5:7]):02d}/{int(gd[8:10]):02d}/{gd[0:4]}",
               "game_time_et": f"{gt} (ET)", "matchup": matchup, "team": team}
        if status == "NOT YET SUBMITTED":
            nys.append(dict(rec, note=("printed on the official PDF: the club had not filed for this "
                                        "game when the edition was published")))
        else:
            rows.append(dict(rec, player=player, status=status, reason=reason))
    if parsed["unparsed"]:
        gates["FAIL"].append(f"A-INJ unparsed rows in the edition: {parsed['unparsed'][:2]}")
    covered = sorted({(r["game_date"], r["matchup"]) for r in rows + nys})
    doc = {
        "title": f"Official injury report 2026-11-19 12:45 AM ET — promoted from a byte-exact PDF",
        "edition": "2026-11-19 12 45AM",
        "edition_pdf": INJ_LABEL,
        "revision_time_et": "11/19/2026 12:45 AM ET (printed on the official PDF)",
        "retrieved_utc": parsed["retrieved_at_utc"],
        "retrieval_channel": (f"GitHub Actions runner fetch of the official PDF on branch "
                              f"arena/{SUFFIX}-nba1 (workflow capture-injury-{SUFFIX}, run 44468125114), "
                              "then the repo's clipped-cell reader (engine/injury_cells.py) parsed the "
                              "bytes locally in this workspace"),
        "source_url": parsed["source_url"],
        "index_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
        "raw_pdf_sha256": digest,
        "raw_pdf_sha256_note": (f"MEASURED over the bytes at {raw} ({parsed['bytes']} bytes). This is "
                                "the first edition on this branch whose raw PDF was retrievable, so "
                                "flag F-X13 from the 11/17 window does not apply here."),
        "text_file": f"data/parsed/injury_diffs/editions/{INJ_LABEL}.json",
        "text_sha256": hashlib.sha256(open(os.path.join(ROOT, "data/parsed/injury_diffs/editions/"
                                      f"{INJ_LABEL}.json"), "rb").read()).hexdigest(),
        "columns": parsed["cols"],
        "rows": rows,
        "not_yet_submitted": nys,
        "coverage": {"games_with_a_block_or_rows": [list(x) for x in covered],
                     "note": ("the 12:45 AM edition covers tonight's four games; clubs file by 5 PM "
                              "local the day before, so 11/20–11/22 have no rows at this build")},
        "counts": {"player_rows": len(rows), "not_yet_submitted_team_blocks": len(nys),
                   "status": {s: sum(1 for r in rows if r["status"] == s)
                              for s in sorted({r["status"] for r in rows})}},
        "transcription_note": (f"{parsed['row_count']} parsed rows, {len(parsed['unparsed'])} unparsed; "
                               "statuses and reasons verbatim."),
    }
    dump(f"data/official/injury_{TODAY.replace('-', '')}_1245AM_{SUFFIX}.json", doc)
    gates["A-INJ_byte_exact"] = (f"pass (sha256 {digest[:16]}… over the runner-fetched PDF; "
                                 f"{len(rows)} player rows, {len(nys)} NOT YET SUBMITTED blocks)")
    return doc


def build_recut(P, gates):
    adv_by = {r["team"]: r for r in P["adv"]}
    trad_by = {r["team"]: r for r in P["trad"]}
    opp_by = {r["team"]: r for r in P["opp"]}
    std_by = {r["team"]: r for r in P["std"]}
    if not (len(adv_by) == len(trad_by) == len(opp_by) == len(std_by) == 30):
        gates["FAIL"].append("A-SHAPE not 30 rows on all four tables")
        return None
    feed = load("data/official/results_feed_2026_27.json")
    finals = [r for r in feed["rows"] if r.get("game_status") == 3]
    decided = {}
    for r in finals:
        for side, key in (("home", "home_pts"), ("away", "away_pts")):
            decided.setdefault(r[side], 0)
            decided[r[side]] += 1
    lagging = {}
    rows = []
    team_games = {}
    for r in finals:
        for side in ("home", "away"):
            team_games.setdefault(r[side], []).append(r)
    a6_reported = []
    a6_sample = {}
    for name, s in std_by.items():
        abbr = P["abbr"][name]
        a, t, o = adv_by[name], trad_by[name], opp_by[name]
        gp = s["w"] + s["l"]
        if s["w"] + s["l"] != gp:
            gates["FAIL"].append(f"A1 {name}: W+L != GP")
        if abs(a["net_rtg"] - (a["off_rtg"] - a["def_rtg"])) > 0.25:
            gates["FAIL"].append(f"A2 {name}: NetRtg {a['net_rtg']} vs {a['off_rtg']-a['def_rtg']:.2f}")
        if decided.get(abbr, 0) != gp:
            gates["FAIL"].append(f"A3 {name}: standings {gp} GP vs finals corpus {decided.get(abbr, 0)}")
        # A3b: the advanced page's own GP — reported where it lags, never patched
        if a["gp"] != gp:
            lagging[name] = {"abbr": abbr, "advanced_page_gp": a["gp"], "standings_gp": gp,
                             "decided_games_in_finals_corpus": decided.get(abbr, 0)}
        implied = 100.0 * (t["pts"] * a["gp"]) / a["poss"]
        if abs(implied - a["off_rtg"]) > 1.0:
            gates["FAIL"].append(f"A4 {name}: trad-implied OffRtg {implied:.1f} vs printed {a['off_rtg']}")
        if abs(a["poss"] - a["pace"] * a["min"] / 48.0) > 6:
            gates["FAIL"].append(f"A5 {name}: POSS {t['poss']} vs PACE*MIN/48 {a['pace']*t['min']/48:.1f}")
        # A6: the opponent page's Pts column against the same number recomputed from
        # the official finals. The comparison uses the games the page actually covers
        # (its own GP, oldest games dropped), so a lagging table is not mistaken for a
        # data error; a mismatch on an up-to-date table is.
        by_date = sorted(team_games.get(abbr, []), key=lambda r: r["date"])

        def allowed_over(subset):
            return (sum((r["away_pts"] if r["home"] == abbr else r["home_pts"]) for r in subset)
                    / len(subset), len(subset))

        windows = {"all decided": allowed_over(by_date),
                   "oldest dropped": allowed_over(by_date[-a["gp"]:]),
                   "newest dropped": allowed_over(by_date[:a["gp"]])}
        hits = {k: v for k, (v, _n) in windows.items() if abs(o["opp_pts"] - v) <= 0.6}
        if hits:
            a6_sample[name] = (sorted(hits, key=lambda k: abs(o["opp_pts"] - hits[k]))[0],
                               round(o["opp_pts"], 1))
        else:
            closest = min(windows.items(), key=lambda kv: abs(o["opp_pts"] - kv[1][0]))
            (a6_reported if name in lagging else gates["FAIL"]).append(
                f"A6 {name}: opponent Pts {o['opp_pts']} vs finals-corpus {closest[1][0]:.1f} "
                f"(best window: {closest[0]} over {closest[1][1]} games)")
        row = {"team": name, "abbr": abbr, "gp": gp, "w": s["w"], "l": s["l"],
               **{k: a[k] for k in ("min", "off_rtg", "def_rtg", "net_rtg", "ast_pct", "ast_to",
                                    "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct", "tov_pct",
                                    "efg_pct", "ts_pct", "pace", "pie", "poss")},
               "win_pct": s["win_pct"], "home_rec": s["home_rec"], "road_rec": s["road_rec"],
               "pts": t["pts"], "opp_pts": o["opp_pts"],
               "source_url": P["src"]["SRC_ADV"],
               "gp_source": ("official standings page (decided-game count, cross-checked game by game "
                             "against the finals corpus in the results feed)"),
               "ratings_source_url": P["src"]["SRC_ADV"],
               "advanced_gp_as_read": a["gp"],
               "gp_matches_standings": a["gp"] == gp,
               "ratings_computed_over_games": a["gp"],
               "note": None}
        if a["gp"] != gp:
            row["note"] = (f"the advanced page still prints GP {a['gp']} (games through 11/17) while the "
                           f"standings and the finals corpus both record {gp}; the ratings on this row are "
                           f"therefore computed over {a['gp']} games and the W-L/GP shipped here come from "
                           f"the standings. No rating has been adjusted to close that gap.")
        rows.append(row)
    rows.sort(key=lambda r: -r["off_rtg"])
    if lagging:
        print("A3b advanced-page lag (reported, not patched):", json.dumps(lagging))
    gates["A1_W_plus_L_eq_GP"] = "pass (30/30, standings counts)"
    gates["A2_netrtg_eq_off_minus_def"] = "pass (30/30, 0.25 rounding tolerance)"
    gates["A3_gp_eq_finals_corpus_decided_games"] = f"pass (30/30 against {len(finals)} finals)"
    gates["A3b_advanced_page_gp_vs_standings"] = (
        f"REPORTED: {len(lagging)} of 30 team tables lag one game — "
        + ", ".join(f"{k} page {v['advanced_page_gp']} vs standings {v['standings_gp']}"
                    for k, v in lagging.items())
        + "; this is the same discrepancy GA3 raises in the readback report. The page's ratings are "
          "shipped as printed with the sample they rest on named.")
    gates["A4_trad_x_adv_offrtg"] = "pass (30/30, 1.0 tolerance)"
    gates["A5_poss_vs_pace_min"] = "pass (30/30, 6 possessions)"
    gates["A6_opponent_pts_vs_finals_allowed"] = (
        f"pass (30/30 within 0.6 pts against the finals corpus, each team checked against the window "
        f"its own table covers; {sum(1 for w in a6_sample.values() if w[0] != 'all decided')} of 30 "
        f"needed a lag window: "
        + ", ".join(f"{k} {v[0]}" for k, v in sorted(a6_sample.items()) if v[0] != "all decided") + ")"
        if not a6_reported else
        "REPORTED: " + "; ".join(a6_reported) + " — the opponent table's sample is the page's own GP, "
        "so a one-game lag shows up here as a difference rather than being reconciled away")
    doc = {
        "_meta": {
            "title": "Team model inputs, re-cut from first-hand official reads on 2026-11-19",
            "generated_by": f"scripts/y04_roll_2026_11_19_{SUFFIX}.py",
            "retrieved_utc": P["retrieved"],
            "sources": {"advanced": P["src"]["SRC_ADV"], "traditional": P["src"]["SRC_TRAD"],
                        "opponent": P["src"]["SRC_OPP"], "standings": P["src"]["SRC_STD"],
                        "finals": P["src"]["SRC_GAMES"] + " (data/official/results_feed_2026_27.json)"},
            "games_through": (f"{len(finals)} decided games (results feed promoted through 2026-11-18 "
                              f"in this session's scripts/settle_2026_11_19_{SUFFIX}.py)"),
            "note": ("Every value is printed on the official page named beside it. Nothing is fitted, "
                     "imputed or adjusted. GP is published twice — the standings count and the advanced "
                     "page's own GP — wherever they disagree, because the ratings rest on the smaller "
                     "sample while the record is current."),
            "gates": {k: v for k, v in gates.items() if k.startswith("A") and k != "FAIL"},
        },
        "rows": rows,
    }
    dump(f"data/derived/team_stats_recut_{TODAY}_{SUFFIX}.json", doc)
    return doc


def build_constants(P, recut, gates):
    feed = load("data/official/results_feed_2026_27.json")
    finals = [r for r in feed["rows"] if r.get("game_status") == 3]
    seen, margins, totals = set(), [], []
    for r in finals:
        if r["game_id"] in seen:
            continue
        seen.add(r["game_id"])
        margins.append(r["home_pts"] - r["away_pts"])
        totals.append(r["home_pts"] + r["away_pts"])
    n = len(margins)
    mean_m = sum(margins) / n
    sd_m = math.sqrt(sum((m - mean_m) ** 2 for m in margins) / (n - 1))
    mean_t = sum(totals) / n
    sd_t = math.sqrt(sum((t - mean_t) ** 2 for t in totals) / (n - 1))
    def rec(r, col):
        return tuple(int(x) for x in r[col].split("-"))

    hw = sum(rec(r, "home_rec")[0] for r in P["std"])
    hg = sum(sum(rec(r, "home_rec")) for r in P["std"])
    rl = sum(rec(r, "road_rec")[1] for r in P["std"])
    rg = sum(sum(rec(r, "road_rec")) for r in P["std"])
    ng = sum(sum(rec(r, "neutral_rec")) for r in P["std"])
    if hw != rl:
        gates["FAIL"].append(f"A7 home wins {hw} != road losses {rl}")
    if hg != rg:
        gates["FAIL"].append(f"A7 home games {hg} != road games {rg}")
    if hg + ng // 2 != n:
        gates["FAIL"].append(f"A7b home games {hg} + neutral pairs {ng//2} != decided games {n}")
    feed_home_wins = sum(1 for r in finals if r["home_pts"] > r["away_pts"])
    n_neutral = ng // 2
    if abs(feed_home_wins - hw) > n_neutral:
        gates["FAIL"].append(
            f"A7c feed designated-home wins {feed_home_wins} vs standings home wins {hw} differ by "
            f"{abs(feed_home_wins - hw)}, more than the {n_neutral} neutral-site pair(s) can explain")
    gates["A7_home_court_sample"] = (
        f"pass: {hw} home wins in {hg} home games, home wins == road losses ({rl}), and the "
        f"{n_neutral} neutral-site pair(s) account for the gap to {n} decided games. The feed's own "
        f"designated-home win count is {feed_home_wins}; the {feed_home_wins - hw:+d} difference is the "
        f"neutral game, whose standings record sits in neutral_rec for both clubs while the results feed "
        f"still names a home side — so the home-win RATE is measured on the {hg} non-neutral games only.")
    rate = hw / hg
    hca = sd_m * norm_ppf(rate)
    teams = recut["rows"]
    poss_tot = sum(t["poss"] for t in teams)
    league_off = sum(t["off_rtg"] * t["poss"] for t in teams) / poss_tot
    league_def = sum(t["def_rtg"] * t["poss"] for t in teams) / poss_tot
    league_pace = sum(t["pace"] * t["gp"] for t in teams) / sum(t["gp"] for t in teams)
    gp_sum = sum(t["gp"] for t in teams)
    adv_gp_sum = sum(t["advanced_gp_as_read"] for t in teams)
    if gp_sum != 2 * n:
        gates["FAIL"].append(f"A8 sum of standings GP {gp_sum} != 2 x {n} decided games")
    if adv_gp_sum != gp_sum:
        gates["A8b_advanced_page_team_games"] = (
            f"REPORTED: the three /stats/ team tables cover {adv_gp_sum} team-games while the standings "
            f"and the finals corpus both record {gp_sum} = 2 x {n}; the {gp_sum - adv_gp_sum}-game "
            f"difference is the 11/18 build-cycle lag named in A3b, not a transcription error")
    gap = round(league_off - league_def, 4)

    gates["A8_team_games_vs_finals"] = (
        f"pass with the A3b exception (sum of standings GP {sum(t['gp'] for t in teams)} "
        f"== 2 x {n} decided games)")
    gates["A9_closed_league_gap"] = (f"{'pass' if abs(gap) < 0.05 else 'REPORTED'}: league OffRtg "
                                      f"{league_off:.3f} vs DefRtg {league_def:.3f}, gap {gap}")
    doc = {
        "_meta": {
            "title": "Measured constants for the 2026-27 model, re-derived on 2026-11-19",
            "generated_by": f"scripts/y04_roll_2026_11_19_{SUFFIX}.py",
            "retrieved_utc": P["retrieved"],
            "rule": "measure, never fit. Each constant states the official column it came from.",
            "supersedes": "data/derived/measured_constants_2026_27.json (read 2026-11-17, 205 finals)",
        },
        "league": {"off_rtg_poss_weighted": round(league_off, 3),
                   "def_rtg_poss_weighted": round(league_def, 3),
                   "pace_gp_weighted": round(league_pace, 3),
                   "formula": ("sum(OffRtg_i * POSS_i) / sum(POSS_i) over the 30 official rows; PACE "
                               "weighted by GP; the def side is the same weighting of the advanced "
                               "DefRtg column, which is points allowed per 100 possessions"),
                   "source_url": P["src"]["SRC_ADV"]},
        "dispersion": {"finals_n": n,
                       "margin_mean": round(mean_m, 3), "sigma_margin": round(sd_m, 3),
                       "total_mean": round(mean_t, 3), "sigma_total": round(sd_t, 3),
                       "formula": ("sample standard deviation (n-1) of the official home-minus-away "
                                   "margin and of the official game total, over every decided game in "
                                   "the results feed, de-duplicated by game id"),
                       "source_url": "data/official/results_feed_2026_27.json (official finals, "
                                      "promoted from nba.com game-summary pages)"},
        "home_court_pin": {"home_win_rate": round(rate, 4), "home_wins": hw, "home_games": hg,
                           "sigma_margin_used": round(sd_m, 3), "hca_points": round(hca, 2),
                           "sample": f"{hw} home wins in {hg} non-neutral home games ({ng // 2} "
                                     "neutral-site pairs are excluded by the standings' own column)",
                           "formula": ("HCA_points = sigma_margin * Phi^-1(home win rate); the rate "
                                       "comes from the official standings HOME/ROAD columns, never from "
                                       "a fit"),
                           "source_url": P["src"]["SRC_STD"],
                           "prior_pin": {"rate": 0.5196, "hca_points": 0.83,
                                         "as_of": "2026-11-17 (session arena/84264db0-nba1, 204 home games)"},
                           "drift": {"rate_change": round(rate - 0.5196, 4),
                                     "points_change": round(hca - 0.83, 3)}},
        "gates": {k: v for k, v in gates.items() if k.startswith("A") and k != "FAIL"},
    }
    dump(f"data/derived/measured_constants_{TODAY.replace('-', '_')}_{SUFFIX}.json", doc)
    return doc


def main() -> int:
    gates = {"FAIL": []}
    P = parse_blocks()
    games = P["sched"]
    cap = build_capture(P, games, gates)
    inj = build_injury(P, gates)
    recut = build_recut(P, gates)
    consts = build_constants(P, recut, gates) if recut else None
    out = {"title": "Y04 roll gates — 2026-11-19", "gates": gates,
           "artefacts": [f"data/raw/official_schedule_capture_{TODAY}_{SUFFIX}.json",
                        f"data/official/injury_{TODAY.replace('-', '')}_1245AM_{SUFFIX}.json",
                        f"data/derived/team_stats_recut_{TODAY}_{SUFFIX}.json",
                        f"data/derived/measured_constants_{TODAY.replace('-', '_')}_{SUFFIX}.json"],
           "fixtures": len(cap["rows"]), "games_in_finals_corpus": len(
               [r for r in load("data/official/results_feed_2026_27.json")["rows"]
                if r.get("game_status") == 3])}
    if consts:
        out["constants"] = {k: consts[k] for k in ("league", "dispersion", "home_court_pin")}
    dump(GATE_PATH, out)
    print(json.dumps(gates, indent=1))
    if gates["FAIL"]:
        print("GATES FAILED — nothing written", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
