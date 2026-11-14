#!/usr/bin/env python3
"""gameday_read_2026_11_14.py — game-day injury refresh: verify, diff, re-price.

Session `arena/95c1cb23-nba1` (COORDINATION.md §30, tasks G02/G03).

Three jobs, in this order:

  1. VERIFY. Every published horizon row in docs/data/lines.json (27 games) is compared
     field by field against a fresh official read of NBA.com (slate capture of 2026-11-14
     ~19:10Z) and against the official standings page. Every published 11/14 injury row
     in docs/data/injuries.json is compared against an independent re-transcription of the
     same official PDF the row cites. Agreement and disagreement are both reported;
     nothing is silently corrected.

  2. DIFF. The injury report moved between the edition the lines were built from
     (11/14 04:15 AM ET) and the league's game-day edition (11/14 01:30 PM ET): four clubs
     filed, one still has not, and four statuses changed. This is computed row by row.

  3. RE-PRICE. The engine's own Availability class and its own availability adjustment
     (engine/model_core.py: margin += (loss_away - loss_home) * poss/100, total adjusted by
     -(1 - 2*alpha) * (loss_home + loss_away) * poss/100) are re-run on the game-day edition
     for tonight's five games, and the result is published NEXT TO the line that is already
     on the record.

THE ONE RULE THAT SHAPES THIS FILE: the published line is NOT edited. Lines and picks are
pre-registered before tip-off; overwriting them with a post-capture number would destroy the
out-of-sample property the whole leaderboard depends on and is exactly the look-ahead error
§1 of this repository is full of. So the re-price is additive: "what the same model, on the
same ratings, would say if it were cut now". Anything you can still act on is the new number;
anything already graded is the old one.

Run:  python3 scripts/gameday_read_2026_11_14.py
Writes: data/derived/gameday_read.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from injuries import Availability, _norm          # noqa: E402  (the repo's own engine)
from common import ABBR                           # noqa: E402

CAP = os.path.join(ROOT, "data", "captures", "2026-11-14-pm")
DOCS = os.path.join(ROOT, "docs", "data")
OUT = os.path.join(ROOT, "data", "derived", "gameday_read.json")

PDF_1330 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"
PDF_0415 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_04_15AM.pdf"
HUB = "https://official.nba.com/nba-injury-report-2026-27-season/"


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def rnd(v, dp=2):
    return None if v is None else round(v + 0.0, dp)


def norm_cdf(z):
    # erf-based, identical to the engine's implementation
    import math
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# --------------------------------------------------------------------- inputs
inj_new = load(os.path.join(CAP, "injury_2026-11-14_1330PM.json"))
inj_old = load(os.path.join(CAP, "injury_2026-11-14_0415AM.json"))
slate = load(os.path.join(CAP, "slate_2026-11-14_to_17.json"))["games"]
standings = load(os.path.join(CAP, "standings_2026-11-14.json"))["rows"]
lines = load(os.path.join(DOCS, "lines.json"))["rows"]
pub_inj = load(os.path.join(DOCS, "injuries.json"))
picks = load(os.path.join(DOCS, "picks.json"))["rows"]
params = load(os.path.join(DOCS, "backtest.json"))["params"]
meta = load(os.path.join(DOCS, "meta.json"))
players_raw = load(os.path.join(ROOT, "data", "raw", "players_traditional.json"))
players = [dict(zip(players_raw["cols"], r)) for r in players_raw["rows"]]

SIGMA_M = params["sigma_margin"]
ALPHA = meta["assumptions"]["alpha_offense_share"]["value"]
COEF = meta["assumptions"]["injury_impact_coef"]["value"]

HORIZON_GAMES = {g["game_id"]: g for g in slate}


def as_rows(doc):
    return doc["rows"]


avail_new = Availability(as_rows(inj_new), players)
avail_old = Availability(as_rows(inj_old), players)


# ------------------------------------------------------- 1. slate verification
slate_check = []
std_by_team = {r["team"]: r for r in standings}
for r in lines:
    gid = r["game_id"]
    obs = HORIZON_GAMES.get(gid)
    if obs is None:
        slate_check.append({"game_id": gid, "matchup": r["matchup"], "verdict": "NO-OFFICIAL-COUNTERPART",
                            "detail": "this game id was not present in the 2026-11-14 live read of NBA.com",
                            "source_url": "https://www.nba.com/games?date=" + r["date"]})
        continue
    fields = {}
    fields["matchup"] = {"published": r["matchup"], "official": "%s@%s" % (obs["away"], obs["home"]),
                         "agree": r["matchup"] == "%s@%s" % (obs["away"], obs["home"])}
    fields["time_et"] = {"published": r["time_et"], "official": obs["time_et"], "agree": r["time_et"] == obs["time_et"]}
    fields["date"] = {"published": r["date"], "official": obs["date"], "agree": r["date"] == obs["date"]}
    for side in ("away", "home"):
        pub = r.get(side + "_rec")
        off = obs[side + "_record"]
        std = std_by_team.get(obs[side], {}).get("w"), std_by_team.get(obs[side], {}).get("l")
        std_str = "%d-%d" % std if std[0] is not None else None
        fields[side + "_rec"] = {"published": pub, "official": off, "agree": pub == off,
                                 "standings_page": std_str,
                                 "agree_standings": (off == std_str)}
    ok = all(f["agree"] for f in fields.values())
    slate_check.append({
        "game_id": gid, "date": r["date"], "matchup": r["matchup"],
        "verdict": "AGREE" if ok else "CHECK",
        "fields": fields,
        "source_url": obs["source_url"],
        "game_url": obs["game_url"],
        "official_read_at": obs["read_at_utc"],
    })

# ---------------------------------------------- 1b. published injury-row check
old_rows = [r for r in pub_inj["rows"] if r.get("date") == "2026-11-14"]
mine_old = [r for r in inj_old["rows"] if r["game_date"] == "11/14/2026"]


def ab(v):
    """The site stores club abbreviations, the report stores club names: one namespace."""
    return v if v in set(ABBR.values()) else ABBR.get(v, v)


def key(r):
    return (ab(r.get("team")), _norm(r.get("player") or ""))


mine_idx = {key(r): r for r in mine_old}
inj_check = []
for r in old_rows:
    k = key(r)
    m = mine_idx.get(k)
    if m is None:
        inj_check.append({"team": r.get("team"), "player": r.get("player"), "verdict": "NOT-IN-FRESH-READ",
                          "source_url": PDF_0415})
        continue
    agree_status = r.get("status") == m["status"]
    agree_reason = (r.get("reason") or "").replace(" EDITION", "").strip() in (m["reason"] or "") or \
                   (m["reason"] is None and r.get("player") is None)
    inj_check.append({
        "team": r.get("team"), "player": r.get("player"),
        "published_status": r.get("status"), "fresh_status": m["status"],
        "published_reason": r.get("reason"), "fresh_reason": m["reason"],
        "verdict": "AGREE" if (agree_status and agree_reason) else "CHECK",
        "attribution_in_pdf": m["attribution"],
        "source_url": PDF_0415,
    })
extra = [m for k, m in mine_idx.items() if k not in {key(r) for r in old_rows}]
for m in extra:
    inj_check.append({"team": m["team"], "player": m["player"], "verdict": "MISSING-FROM-SITE",
                      "fresh_status": m["status"], "fresh_reason": m["reason"],
                      "attribution_in_pdf": m["attribution"], "source_url": PDF_0415})

# ------------------------------------------------------------- 2. edition diff
def team_index(rows):
    out = {}
    for r in rows:
        ab = ABBR.get(r["team"])
        out.setdefault((r["game_date"], ab), []).append(r)
    return out


ix_new, ix_old = team_index(inj_new["rows"]), team_index(inj_old["rows"])
delta_rows = []
for (date, ab), old_list in sorted(ix_old.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    if date != "11/14/2026":
        continue
    new_list = ix_new.get((date, ab), [])
    old_p = {(_norm(r["player"] or "")): r for r in old_list}
    new_p = {(_norm(r["player"] or "")): r for r in new_list}
    old_ns = any(r["status"] == "NOT YET SUBMITTED" for r in old_list)
    new_ns = any(r["status"] == "NOT YET SUBMITTED" for r in new_list)
    added = [new_p[k] for k in new_p if k and k not in old_p]
    removed = [old_p[k] for k in old_p if k and k not in new_p]
    changed = [
        {"player": new_p[k]["player"], "from": old_p[k]["status"], "to": new_p[k]["status"],
         "reason": new_p[k]["reason"]}
        for k in new_p if k in old_p and old_p[k]["status"] != new_p[k]["status"]
    ]
    if not (added or removed or changed or old_ns != new_ns):
        continue
    delta_rows.append({
        "date": "2026-11-14", "team": ab,
        "matchup": (old_list[0]["matchup"] if old_list else None),
        "was_not_yet_submitted": old_ns, "now_not_yet_submitted": new_ns,
        "filed_since": old_ns and not new_ns,
        "n_added": len(added), "n_removed": len(removed), "n_status_changes": len(changed),
        "added": [{"player": a["player"], "status": a["status"], "reason": a["reason"],
                   "attribution": a["attribution"]} for a in added],
        "removed": [{"player": a["player"], "status": a["status"], "reason": a["reason"]} for a in removed],
        "status_changes": changed,
        "source_old": PDF_0415, "source_new": PDF_1330,
    })

# --------------------------------------------------- 3. impact + re-price table
def rep_for(avail, date, ab, matchup):
    return avail.team_report(date, ab)


readout = []
for r in [x for x in lines if x["date"] == "2026-11-14"]:
    away, home = r["away"], r["home"]
    date = "11/14/2026"
    o_h, o_a = rep_for(avail_old, date, home, r["matchup"]), rep_for(avail_old, date, away, r["matchup"])
    n_h, n_a = rep_for(avail_new, date, home, r["matchup"]), rep_for(avail_new, date, away, r["matchup"])
    poss = r["model_possessions"]
    scale = poss / 100.0
    loss_h_old, loss_a_old = r["home_availability_loss"], r["away_availability_loss"]
    loss_h_new, loss_a_new = n_h["impact_net_rating"], n_a["impact_net_rating"]
    margin_old = r["model_spread_home"]
    # re-apply the engine's adjustment rule with the new losses, starting from the
    # published (already-adjusted) margin: undo the old, add the new.
    margin_new = (margin_old - (loss_a_old - loss_h_old) * scale + (loss_a_new - loss_h_new) * scale)
    total_old = r["model_total"]
    total_new = (total_old + (1.0 - 2.0 * ALPHA) * (loss_h_old + loss_a_old) * scale
                 - (1.0 - 2.0 * ALPHA) * (loss_h_new + loss_a_new) * scale)
    p_old = r["p_home_win"]
    p_new = norm_cdf(margin_new / SIGMA_M)
    game_picks = [p for p in picks if p.get("game_id") == r["game_id"] and p.get("date") == r["date"]]
    affected = []
    for p in game_picks:
        fav = "home" if margin_new > 0 else "away"
        affected.append({
            "strategy": p.get("strategy"), "market": p.get("market"), "side": p.get("side"),
            "team": p.get("team"), "line_display": p.get("line_display"),
            "model_side_still_agrees": (p.get("side") == fav),
            "edge_old": p.get("edge"),
            "edge_new": rnd(margin_new - p.get("ref_line"), 2) if p.get("market") == "Point spread" else None,
        })
    readout.append({
        "date": r["date"], "time_et": r["time_et"], "matchup": r["matchup"], "game_id": r["game_id"],
        "away": away, "home": home,
        "published": {
            "model_spread_home": margin_old, "model_total": total_old, "p_home_win": p_old,
            "loss_home": loss_h_old, "loss_away": loss_a_old,
            "home_report_status": r["home_report_status"], "away_report_status": r["away_report_status"],
            "home_confidence": r["home_injury_confidence"], "away_confidence": r["away_injury_confidence"],
            "src": r["src"],
        },
        "gameday": {
            "loss_home": loss_h_new, "loss_away": loss_a_new,
            "model_spread_home": rnd(margin_new, 1), "model_total": rnd(total_new, 1),
            "p_home_win": rnd(p_new, 3),
            "home_listed": n_h["listed"], "away_listed": n_a["listed"],
            "home_minutes_known": n_h["listed"] - len(n_h["unknown_minutes_players"]),
            "away_minutes_known": n_a["listed"] - len(n_a["unknown_minutes_players"]),
            "home_coverage": n_h["minutes_coverage"], "away_coverage": n_a["minutes_coverage"],
            "home_confidence": n_h["confidence"], "away_confidence": n_a["confidence"],
            "home_not_submitted": n_h["not_submitted"], "away_not_submitted": n_a["not_submitted"],
            "home_weighted_share": n_h["weighted_lost_share"], "away_weighted_share": n_a["weighted_lost_share"],
            "home_sensitivity": n_h["impact_sensitivity"], "away_sensitivity": n_a["impact_sensitivity"],
            "home_unknown_players": n_h["unknown_minutes_players"],
            "away_unknown_players": n_a["unknown_minutes_players"],
        },
        "delta": {
            "spread_move": rnd(margin_new - margin_old, 2),
            "total_move": rnd(total_new - total_old, 2),
            "p_home_move": rnd(p_new - p_old, 3),
            "favourite_flips": (margin_old > 0) != (margin_new > 0),
            "changed": abs(margin_new - margin_old) >= 0.05 or abs(total_new - total_old) >= 0.05,
        },
        "picks": affected,
        "sources": {"slate": r["src"], "report_old": PDF_0415, "report_new": PDF_1330,
                    "game_url": HORIZON_GAMES[r["game_id"]]["game_url"],
                    "slate_page": HORIZON_GAMES[r["game_id"]]["source_url"]},
    })

# 11/15-11/17: what the game-day edition does and does not say about them
later = []
for r in [x for x in lines if x["date"] != "2026-11-14"]:
    keydate = {"2026-11-15": "11/15/2026"}.get(r["date"])
    rows_new = [q for q in inj_new["rows"] if q["game_date"] == keydate] if keydate else []
    listed_new = [q for q in rows_new if q["status"] != "NOT YET SUBMITTED"]
    later.append({
        "date": r["date"], "matchup": r["matchup"], "game_id": r["game_id"],
        "in_gameday_edition": bool(keydate),
        "player_rows_for_this_date": len(listed_new),
        "teams_not_yet_submitted": len([q for q in rows_new if q["status"] == "NOT YET SUBMITTED"]),
        "verdict": ("LISTED, ALL UNFILED" if keydate and not listed_new else
                    ("NOT COVERED BY THE REPORT" if not keydate else "MIXED")),
        "source_url": PDF_1330 if keydate else HUB,
        "note": ("the report covers 11/14 and 11/15 only; a game on this date has no line in it"
                 if not keydate else
                 "every club in this game is listed NOT YET SUBMITTED at the 01:30 PM ET edition"),
    })

# --------------------------------------------------------------- minutes cross-check
# For every row whose team came from a re-flowed PDF block, check the club the
# official top-50 minutes table assigns to that player, where the table knows him.
player_team = {p["player"]: p["team"] for p in players}
# the report writes "Holmes, DaRon", NBA.com writes "DaRon Holmes"; the engine's own
# token-sorting normaliser is what makes the two comparable, so it is what is used here.
player_team_by_norm = {_norm(k): v for k, v in player_team.items()}
attr_check = []
for r in inj_new["rows"]:
    if r["attribution"] != "block" or not r["player"]:
        continue
    disp = r["player"]
    t = player_team_by_norm.get(_norm(disp))
    attr_check.append({
        "player": disp, "team_in_pdf_block": ABBR.get(r["team"]), "team_in_minutes_table": t,
        "verdict": "AGREE" if t == ABBR.get(r["team"]) else ("NO-CROSS-CHECK" if t is None else "CONFLICT"),
        "source_url_pdf": PDF_1330,
        "source_url_table": "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season",
    })

# exact counts, so no sentence on the site has to estimate
tonight_listed = sum(g["gameday"]["home_listed"] + g["gameday"]["away_listed"] for g in readout)
tonight_blind = sum(len(g["gameday"]["home_unknown_players"]) + len(g["gameday"]["away_unknown_players"])
                    for g in readout)
newly_filed = sum(d["n_added"] for d in delta_rows)
newly_known = 0
for _d in delta_rows:
    for _a in _d["added"]:
        if _norm(_a["player"]) in avail_new.players_by_key:
            newly_known += 1

summary = {
    "generated_utc": "2026-11-14T19:20Z",
    "counts": {"tonight_listed_rows": tonight_listed, "tonight_rows_without_minutes": tonight_blind,
               "rows_added_by_the_game_day_edition": newly_filed,
               "added_rows_with_a_minutes_value": newly_known,
               "added_rows_without_a_minutes_value": newly_filed - newly_known},
    "session": "arena/95c1cb23-nba1",
    "edition_published_by_site": pub_inj["report"],
    "edition_gameday": inj_new["report"],
    "slate_rows_checked": len(slate_check),
    "slate_rows_agree": sum(1 for x in slate_check if x["verdict"] == "AGREE"),
    "slate_rows_check": [x["game_id"] for x in slate_check if x["verdict"] != "AGREE"],
    "injury_rows_checked": len([x for x in inj_check if x["verdict"] != "NOT-IN-FRESH-READ"]),
    "injury_rows_agree": sum(1 for x in inj_check if x["verdict"] == "AGREE"),
    "injury_rows_disagree": [x for x in inj_check if x["verdict"] not in ("AGREE",)],
    "teams_that_filed_since": [d["team"] for d in delta_rows if d["filed_since"]],
    "teams_still_unfiled": sorted({r["team"] for r in inj_new["rows"]
                                   if r["game_date"] == "11/14/2026" and r["status"] == "NOT YET SUBMITTED"}),
    "teams_unfiled_last_edition": sorted({ABBR.get(r["team"]) for r in inj_old["rows"]
                                          if r["game_date"] == "11/14/2026"
                                          and r["status"] == "NOT YET SUBMITTED"}),
    "games_repriced": sum(1 for x in readout if x["delta"]["changed"]),
    "favourite_flips": [x["matchup"] for x in readout if x["delta"]["favourite_flips"]],
    "attribution_checks": {"total": len(attr_check),
                           "agree": sum(1 for x in attr_check if x["verdict"] == "AGREE"),
                           "no_cross_check": sum(1 for x in attr_check if x["verdict"] == "NO-CROSS-CHECK"),
                           "conflict": [x for x in attr_check if x["verdict"] == "CONFLICT"]},
    "mechanism": {
        "impact_coef_net_pts_per_100poss": COEF,
        "alpha_offense_share": ALPHA,
        "sigma_margin": rnd(SIGMA_M, 4),
        "rule": "margin += (loss_away - loss_home) * possessions/100 ; "
                "total += -(1 - 2*alpha) * (loss_home + loss_away) * possessions/100",
        "rule_source": "engine/model_core.py apply_availability()",
        "minutes_source": "https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season",
    },
    "honest_limits": [
        "Impact is a LOWER BOUND: a listed player outside the captured top-50 minutes table "
        "contributes 0.00 net-rating points, so a team can be missing real rotation and still "
        "show 0.0. The count of such players is published per game below.",
        "The 01:30 PM ET edition is the newest published when this was captured. Memphis had "
        "not filed; its game-day window (11 a.m. to 1 p.m. local, Central time, for an 8:00 PM "
        "ET tip) was still open at capture time, so 'not yet submitted' is not a missed deadline.",
        "Status labels are the league's own words. The probability attached to each label "
        "(Out 1.00 / Doubtful 0.70 / Questionable 0.35 / Probable 0.10 / Available 0.00) is a "
        "modelling choice of this project, not an official figure, and is flagged as such (F4).",
        "No market price exists anywhere in this file. 'Re-priced' means the model against its "
        "own naive reference, never the model against a book.",
    ],
}

doc = {"summary": summary, "slate_verification": slate_check, "injury_verification": inj_check,
       "edition_delta": delta_rows, "gameday_readout": readout, "later_dates": later,
       "attribution_cross_check": attr_check}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False)
    fh.write("\n")

print("slate rows: %d/%d AGREE   disagreement: %s" % (summary["slate_rows_agree"],
      summary["slate_rows_checked"], summary["slate_rows_check"] or "none"))
print("published 11/14 injury rows: %d/%d AGREE   issues: %d" % (
    summary["injury_rows_agree"], summary["injury_rows_checked"], len(summary["injury_rows_disagree"])))
print("teams that filed between editions:", summary["teams_that_filed_since"],
      "| still unfiled:", sorted(set(summary["teams_still_unfiled"])))
print("games whose line moves:", summary["games_repriced"], " flips:", summary["favourite_flips"] or "none")
print("block-attribution cross-check:", summary["attribution_checks"]["agree"], "agree,",
      summary["attribution_checks"]["no_cross_check"], "no cross-check,",
      len(summary["attribution_checks"]["conflict"]), "conflict")
for x in readout:
    g = x["gameday"]
    print("  %-9s spread %6.1f -> %6.1f  total %6.1f -> %6.1f  p_home %.3f -> %.3f  %-8s "
          "listing H%d/A%d  minutes-known H%d/A%d" % (
              x["matchup"], x["published"]["model_spread_home"], x["gameday"]["model_spread_home"],
              x["published"]["model_total"], x["gameday"]["model_total"],
              x["published"]["p_home_win"], x["gameday"]["p_home_win"],
              "CHANGED" if x["delta"]["changed"] else "no change",
              g["home_listed"], g["away_listed"], g["home_minutes_known"], g["away_minutes_known"]))
    for who in ("home", "away"):
        unk = g[who + "_unknown_players"]
        if unk:
            print("             %s players listed but OUTSIDE the minutes table (impact forced to 0.00): %s"
                  % (who, ", ".join(unk)))
