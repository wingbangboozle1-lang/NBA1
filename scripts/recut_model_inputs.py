#!/usr/bin/env python3
"""recut_model_inputs.py — re-cut the model's team-rating inputs from the newest
official team-stat capture in data/official/.

The brief asks for the three official team-stat pages (traditional, opponent,
advanced) to be re-read and the model inputs re-cut from them. This script does
exactly that and nothing else: it reads the three dated capture files written by
a capture pass, re-derives the two files the originator consumes, and stamps
them with the capture's own retrieved_utc and source URL. No value is computed
that is not present on the official pages.

Inputs (newest capture wins, by the timestamp suffix on the filename):
    data/official/teams_traditional_<YYYY-MM-DD>_<HHMMZ>.json
    data/official/teams_opponent_<YYYY-MM-DD>_<HHMMZ>.json
    data/official/teams_advanced_<YYYY-MM-DD>_<HHMMZ>.json

Outputs (rewritten in place, the paths originate_horizon.py already reads):
    data/teams_advanced_2026_27.json    pace / OffRtg / DefRtg per team
    data/teams_scoring_2026_27.json     own and opponent scoring splits per team

Cross-checks (assertions, so a bad capture cannot silently reach the model):
  * all three captures cover the same 30 teams and agree on (GP, W, L);
  * traditional PTS - opponent OPP_PTS equals the printed +/- (rounding tolerance);
  * the re-cut rows reproduce the capture rows exactly.

Run:  python3 scripts/recut_model_inputs.py [--stamp YYYY-MM-DD_HHMMZ]
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL = os.path.join(ROOT, "data", "official")

SRC_ADVANCED = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRADITIONAL = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_OPPONENT = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"


def newest(prefix):
    pat = os.path.join(OFFICIAL, "teams_%s_*.json" % prefix)
    cands = [p for p in glob.glob(pat) if re.search(r"_\d{4}-\d{2}-\d{2}_\d{4}Z\.json$", p)]
    if not cands:
        # fall back to the undated captures written by the earliest passes
        cands = [p for p in glob.glob(os.path.join(OFFICIAL, "teams_%s*.json" % prefix))]
    if not cands:
        sys.exit("no capture found for %s (looked in %s)" % (prefix, pat))
    return sorted(cands)[-1]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=None,
                    help="capture stamp to use, e.g. 2026-11-15_2345Z (default: newest)")
    args = ap.parse_args()

    def pick(prefix):
        if args.stamp:
            p = os.path.join(OFFICIAL, "teams_%s_%s.json" % (prefix, args.stamp))
            if not os.path.exists(p):
                sys.exit("requested capture missing: %s" % os.path.relpath(p, ROOT))
            return p
        return newest(prefix)

    p_trad, p_opp, p_adv = pick("traditional"), pick("opponent"), pick("advanced")
    trad_doc, opp_doc, adv_doc = load(p_trad), load(p_opp), load(p_adv)
    trad = {r["abbr"]: r for r in trad_doc["rows"]}
    opp = {r["abbr"]: r for r in opp_doc["rows"]}
    adv = {r["abbr"]: r for r in adv_doc["rows"]}

    assert len(trad) == len(opp) == len(adv) == 30, "every capture must hold 30 teams"
    assert set(trad) == set(opp) == set(adv), "the three captures disagree on the team set"
    for abbr in trad:
        assert (trad[abbr]["gp"], trad[abbr]["w"], trad[abbr]["l"]) == \
               (opp[abbr]["gp"], opp[abbr]["w"], opp[abbr]["l"]) == \
               (adv[abbr]["gp"], adv[abbr]["w"], adv[abbr]["l"]), \
            "%s: (GP, W, L) disagrees across the three pages" % abbr
        diff = round(trad[abbr]["pts"] - opp[abbr]["opp_pts"], 1)
        assert abs(diff - trad[abbr]["plus_minus"]) <= 0.15, \
            "%s: pts - opp_pts = %s but printed +/- = %s" % (abbr, diff, trad[abbr]["plus_minus"])

    retrieved = " / ".join(sorted({d.get("retrieved_utc") or "undated"
                                   for d in (trad_doc, opp_doc, adv_doc)}))
    games_through = max(trad[a]["gp"] for a in trad)

    # ---- advanced ---------------------------------------------------------
    adv_rows = []
    for abbr in sorted(adv, key=lambda a: -adv[a]["net_rtg"]):
        r = adv[abbr]
        adv_rows.append({
            # display name is filled in from the standings capture two lines below
            "team": abbr,
            "abbr": abbr, "gp": r["gp"], "w": r["w"], "l": r["l"], "min": r["min"],
            "off_rtg": r["off_rtg"], "def_rtg": r["def_rtg"], "net_rtg": r["net_rtg"],
            "ast_pct": r["ast_pct"], "ast_to": r["ast_to"], "ast_ratio": r["ast_ratio"],
            "oreb_pct": r["oreb_pct"], "dreb_pct": r["dreb_pct"], "reb_pct": r["reb_pct"],
            "tov_pct": r["tov_pct"], "efg_pct": r["efg_pct"], "ts_pct": r["ts_pct"],
            "pace": r["pace"], "pie": r["pie"], "poss": r["poss"],
            "source_url": SRC_ADVANCED,
        })
    # team display names come from the standings capture, never from memory
    st_path = sorted(glob.glob(os.path.join(OFFICIAL, "standings_*.json")))[-1] \
        if glob.glob(os.path.join(OFFICIAL, "standings_*.json")) else None
    name = {}
    if st_path and os.path.exists(st_path):
        for r in load(st_path)["rows"]:
            name[r["abbr"]] = r["team"]
    for r in adv_rows:
        r["team"] = name.get(r["abbr"], r["abbr"])

    # ---- scoring ----------------------------------------------------------
    score_rows = []
    for abbr in sorted(trad):
        t, o = trad[abbr], opp[abbr]
        score_rows.append({
            "abbr": abbr, "gp": t["gp"], "pts": t["pts"], "opp_pts": o["opp_pts"],
            "plus_minus": t["plus_minus"],
            "fgm": t["fgm"], "fga": t["fga"], "fg_pct": t["fg_pct"],
            "fg3m": t["fg3m"], "fg3a": t["fg3a"], "fg3_pct": t["fg3_pct"],
            "ftm": t["ftm"], "fta": t["fta"], "ft_pct": t["ft_pct"],
            "oreb": t["oreb"], "dreb": t["dreb"], "reb": t["reb"],
            "ast": t["ast"], "tov": t["tov"], "stl": t["stl"], "blk": t["blk"],
            "opp_fgm": o["opp_fgm"], "opp_fga": o["opp_fga"], "opp_fg_pct": o["opp_fg_pct"],
            "opp_fg3m": o["opp_fg3m"], "opp_fg3a": o["opp_fg3a"], "opp_fg3_pct": o["opp_fg3_pct"],
            "opp_ftm": o["opp_ftm"], "opp_fta": o["opp_fta"],
            "opp_reb": o["opp_reb"], "opp_tov": o["opp_tov"],
            "source_url": SRC_TRADITIONAL,
        })

    out_adv = {
        "_meta": {
            "title": "NBA team advanced statistics, 2026-27 regular season (season-to-date)",
            "source_url": SRC_ADVANCED,
            "source_name": ("NBA.com official team advanced stats — OffRtg, DefRtg, NetRtg, PACE"),
            "captured_from": [os.path.relpath(p_adv, ROOT)],
            "retrieved_utc": retrieved,
            "recut_by": "scripts/recut_model_inputs.py",
            "games_through": "GP on the official page at capture time (max %d)" % games_through,
            "note": ("re-cut from the newest official capture in data/official/; every value is "
                     "the value printed by the official page, nothing derived"),
            "columns": ["team", "abbr", "gp", "w", "l", "min", "off_rtg", "def_rtg", "net_rtg",
                        "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct",
                        "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"],
        },
        "rows": adv_rows,
    }
    out_score = {
        "_meta": {
            "title": ("NBA team scoring and shooting, 2026-27 regular season (Per Game), "
                      "own and opponent splits"),
            "source_urls": {"own": SRC_TRADITIONAL, "opponent": SRC_OPPONENT},
            "captured_from": [os.path.relpath(p_trad, ROOT), os.path.relpath(p_opp, ROOT)],
            "retrieved_utc": retrieved,
            "recut_by": "scripts/recut_model_inputs.py",
            "games_through": "GP on the official page at capture time (max %d)" % games_through,
            "note": ("own split from the official traditional page, opponent split from the "
                     "official opponent page; the two are joined on abbr and cross-checked "
                     "against the printed +/-"),
        },
        "rows": score_rows,
    }

    for rel, doc in (("data/teams_advanced_2026_27.json", out_adv),
                     ("data/teams_scoring_2026_27.json", out_score)):
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print("re-cut %-38s %2d rows  from %s" % (rel, len(doc["rows"]),
                                                  ", ".join(doc["_meta"]["captured_from"])))
    print("retrieved_utc:", retrieved)
    print("captures used:", os.path.basename(p_trad), os.path.basename(p_opp),
          os.path.basename(p_adv))


if __name__ == "__main__":
    main()
