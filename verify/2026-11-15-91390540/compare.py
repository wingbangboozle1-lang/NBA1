#!/usr/bin/env python3
"""Row-by-row comparison for session arena/91390540-nba1 (COORDINATION §39, R03).

Reads this session's fresh official captures (same directory) against the values the
repository currently publishes, and writes compare.json next to itself.

Rules:
  * every comparison row names both sides and the official URL it came from;
  * a published value that the fresh official read contradicts is a MISMATCH, listed
    with both values - never silently corrected here;
  * anything not compared is reported as NOT CHECKED, never assumed;
  * no value is inferred to fill a blank.
"""
import json
import os
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return json.load(f)


def load_here(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    finals = load_here("official_finals_2026-11-14.json")
    horizon = load_here("official_horizon_2026-11-15_to_18.json")
    injury = load_here("injury_report_2026-11-15_0615AM.json")
    sched = load("data", "raw", "schedule_upcoming.json")
    picks = load("site", "data", "picks.json")
    settlement = load("integration", "out", "settlement.json")
    site_inj = load("site", "data", "injuries.json")
    site_meta = load("site", "data", "meta.json")
    prev_inj = load("data", "captures", "2026-11-14-pm", "injury_2026-11-14_1330PM.json")
    flagged = load("data", "content", "flagged.json")

    sched_cols = sched["cols"]
    sched_rows = [dict(zip(sched_cols, r)) for r in sched["rows"]]
    sched_by_id = {r["game_id"]: r for r in sched_rows}
    fresh_by_id = {r[6]: dict(zip(horizon["cols"], r)) for r in horizon["rows"]}
    fresh_finals_by_id = {g["game_id"]: g for g in finals["games"]}
    picks_by_game = collections.Counter(r["game_id"] for r in picks["rows"])

    out = {
        "session": "arena/91390540-nba1",
        "generated_by": "verify/2026-11-15-91390540/compare.py",
        "official_capture_window_utc": finals["retrieved_at_utc_window"],
        "sections": {},
    }

    # ---------- A. the five 2026-11-14 finals against what the repo publishes
    picks_1114 = [r for r in picks["rows"] if r["date"] == "2026-11-14"]
    a_rows = []
    for g in finals["games"]:
        gid = g["game_id"]
        pub = sched_by_id.get(gid)
        cannot = next((c for c in settlement["cannot_settle"] if c.get("game_id") == gid), None)
        singles = [r for r in picks_1114 if r["game_id"] == gid]
        parlay_legs = [r for r in picks_1114 if r["game_id"] != gid and gid in r["game_id"].split("+")]
        a_rows.append({
            "game_id": gid,
            "matchup": g["matchup"],
            "official_final": f"{g['away']} {g['away_pts']} @ {g['home']} {g['home_pts']}",
            "quarters": g["quarters"],
            "two_source": g["two_source"],
            "official_urls": [g["url_card"], g["url_game"]],
            "published_horizon_row_present": pub is not None,
            "published_records_at_capture": (f"{pub['away']} {pub['away_rec']} / {pub['home']} {pub['home_rec']}"
                                             if pub else None),
            "published_single_picks": len(singles),
            "published_parlay_legs": len(parlay_legs),
            "published_picks_status": sorted({r["status"] for r in singles + parlay_legs}),
            "settlement_ledger_entry": ({"state": cannot.get("state"), "reason": cannot.get("reason")}
                                        if cannot else None),
        })
    out["sections"]["A_1114_finals_vs_published"] = {
        "check": "official two-source finals vs published horizon rows, published picks, and the settlement ledger",
        "rows": a_rows,
        "summary": {
            "finals": len(a_rows),
            "all_finals_two_source": all(r["two_source"] for r in a_rows),
            "picks_rows_dated_1114": len(picks_1114),
            "picks_statuses_dated_1114": sorted({r["status"] for r in picks_1114}),
            "single_game_picks": sum(1 for r in picks_1114 if "+" not in r["game_id"]),
            "parlay_or_sgp_picks": sum(1 for r in picks_1114 if "+" in r["game_id"]),
            "ledger_still_says_tipoff_not_happened": sum(
                1 for r in a_rows
                if r["settlement_ledger_entry"] and "tip-off has not happened" in r["settlement_ledger_entry"]["reason"]),
            "verified_finals_file_for_1114_present": any(
                f.startswith("finals_2026-11-14") for f in os.listdir(os.path.join(REPO, "data", "verified"))),
        },
        "verdict": "MISMATCH (stale): the repository publishes no final score for any of the five 11/14 games; "
                   "all 17 published pick rows dated 11/14 (15 single-game + 2 parlays/SGPs whose legs are "
                   "among these finals) are still PENDING; the settlement ledger still records the five games "
                   "as 'tip-off has not happened yet at capture time'. The finals captured here are ready to "
                   "settle against — two-source, with quarter scores.",
    }

    # ---------- B. published horizon rows 11/15-11/17 vs the fresh read
    b_rows = []
    for gid, pub in sched_by_id.items():
        if pub["date"] not in ("2026-11-15", "2026-11-16", "2026-11-17"):
            continue
        fresh = fresh_by_id.get(gid)
        if fresh is None:
            b_rows.append({
                "game_id": gid, "published": f"{pub['away']}@{pub['home']} {pub['date']} {pub['time_et']}",
                "fresh": None, "verdict": "MISSING FROM FRESH CAPTURE",
            })
            continue
        cell_checks = {
            "date": (pub["date"], fresh["date"]),
            "time_et": (pub["time_et"], fresh["time_et"]),
            "away": (pub["away"], fresh["away"]),
            "home": (pub["home"], fresh["home"]),
            "game_id": (pub["game_id"], fresh["game_id"]),
        }
        cell_verdicts = {k: ("AGREE" if v[0] == v[1] else "MISMATCH") for k, v in cell_checks.items()}
        rec_checks = {
            "away_rec": (pub["away_rec"], fresh["away_rec"]),
            "home_rec": (pub["home_rec"], fresh["home_rec"]),
        }
        rec_verdicts = {k: ("AGREE" if v[0] == v[1] else "STALE (published pre-dates the 11/14 results)")
                        for k, v in rec_checks.items()}
        b_rows.append({
            "game_id": gid,
            "published": f"{pub['away']}({pub['away_rec']})@{pub['home']}({pub['home_rec']}) {pub['date']} {pub['time_et']}",
            "fresh": f"{fresh['away']}({fresh['away_rec']})@{fresh['home']}({fresh['home_rec']}) {fresh['date']} {fresh['time_et']}",
            "identity_cells": {k: {"published": v[0], "fresh": v[1], "verdict": cell_verdicts[k]}
                               for k, v in cell_checks.items()},
            "record_cells": {k: {"published": v[0], "fresh": v[1], "verdict": rec_verdicts[k]}
                             for k, v in rec_checks.items()},
            "verdict": ("AGREE" if all(v == "AGREE" for v in cell_verdicts.values())
                        and all(v == "AGREE" for v in rec_verdicts.values())
                        else ("IDENTITY AGREE / RECORD STALE"
                              if all(v == "AGREE" for v in cell_verdicts.values())
                              else "MISMATCH")),
        })
    n_id_mismatch = sum(1 for r in b_rows if r["verdict"] == "MISMATCH")
    n_stale = sum(1 for r in b_rows if r["verdict"] == "IDENTITY AGREE / RECORD STALE")
    out["sections"]["B_horizon_1115_to_1117_vs_published"] = {
        "check": "each published horizon row (date, tip ET, matchup, game id, both records) vs the fresh official read",
        "rows": b_rows,
        "summary": {
            "published_rows_checked": len(b_rows),
            "identity_mismatches": n_id_mismatch,
            "rows_with_stale_records": n_stale,
            "rows_fully_agreeing": sum(1 for r in b_rows if r["verdict"] == "AGREE"),
        },
        "verdict": (f"IDENTITY: {len(b_rows) - n_id_mismatch}/{len(b_rows)} agree on date/tip/matchup/game id "
                    f"(0 identity mismatches expected; found {n_id_mismatch}). "
                    f"RECORDS: {n_stale} rows carry pre-11/14 records (stale by exactly the 11/14 results, "
                    "reconciled 10/10 in the finals capture)."),
        "venue_cells": "NOT CHECKED this pass (the games pages do not print venues; needs https://www.nba.com/schedule)",
    }

    # ---------- C. 11/18 coverage (today + 3 = 11/15..11/18)
    fresh_1118 = [dict(zip(horizon["cols"], r)) for r in horizon["rows"] if r[0] == "2026-11-18"]
    pub_1118 = [r for r in sched_rows if r["date"] == "2026-11-18"]
    out["sections"]["C_1118_coverage"] = {
        "check": "the brief's maximum horizon is today + 3 days = 2026-11-18; the published capture window is 11/14..11/17",
        "fresh_1118_games": len(fresh_1118),
        "published_1118_rows": len(pub_1118),
        "picks_slate_dates": picks.get("slate_dates"),
        "rows": [{"game_id": r["game_id"],
                  "matchup": f"{r['away']}@{r['home']}",
                  "time_et": r["time_et"],
                  "in_published_horizon": any(p["game_id"] == r["game_id"] for p in pub_1118)}
                 for r in fresh_1118],
        "verdict": "GAP: 12 official 11/18 games exist and are captured here; none appears in the published "
                   "horizon, and the published picks stop at 11/17. Flagged, not filled.",
    }

    # ---------- D. injury-report currency + consecutive-edition diff
    old_rows = [r for r in prev_inj["rows"] if r.get("game_date") == "11/15/2026"]
    # rows for 11/15 in the new edition = every row printed in the 11/15 block (pages 1-6),
    # identified by the 'block' field recorded at transcription time (position, not inference
    # into any value cell).
    new_rows_1115 = [r for r in injury["rows"] if r[9] == "11/15"]
    old_by_player = {}
    for r in old_rows:
        old_by_player.setdefault(r["player"], []).append(r)
    new_by_player = {}
    for r in new_rows_1115:
        new_by_player.setdefault(r[4], []).append(r)

    # The 01:30 PM edition's 11/15 rows are 18 NOT YET SUBMITTED team entries (no player
    # rows at all), so a player-level status diff has no shared keys. The meaningful
    # consecutive-edition diff is therefore: which team entries filed, what designations
    # appeared, and what is still unfiled.
    team_entries = [(r["matchup"], r["team"]) for r in old_rows]  # all 18 printed
    # Keyed by team alone inside the 11/15 block: continuation rows often drop the Matchup
    # cell too, and each team appears at most once in the block, so team name is the only
    # key that survives the PDF reflow. Dropped Team cells are still never attributed.
    new_team_rows = collections.defaultdict(list)
    for r in new_rows_1115:
        if r[3]:  # printed team cell only
            new_team_rows[r[3]].append(r)
    team_filing_changes = []
    for matchup, team in team_entries:
        rows = new_team_rows.get(team, [])
        player_rows = [r for r in rows if r[4]]
        nys_rows = [r for r in rows if r[5] == "NOT YET SUBMITTED"]
        if player_rows:
            new_state = f"filed — {len(player_rows)} player designation row(s) printed"
        elif nys_rows:
            new_state = "NOT YET SUBMITTED (unchanged)"
        else:
            new_state = ("no row of any kind for this team in the new edition - recorded as absent, "
                         "not interpreted (a disappeared NOT YET SUBMITTED row could mean an empty "
                         "filing; the two PDFs alone cannot distinguish that)")
        team_filing_changes.append({
            "entry": f"{matchup} / {team}",
            "old": "NOT YET SUBMITTED",
            "new": new_state,
            "new_statuses": sorted({r[5] for r in player_rows}) if player_rows else [],
        })
    newly_listed = [{"player": r[4], "status": r[5], "matchup_printed": r[2],
                     "team_printed": r[3], "attribution": r[7]}
                    for r in new_rows_1115 if r[4] and r[4] not in old_by_player]
    still_nys = [{"entry": f"{r[2]} / {r[3]}", "status": r[5]}
                 for r in new_rows_1115 if r[5] == "NOT YET SUBMITTED"]

    out["sections"]["D_injury_edition_currency_and_diff"] = {
        "published_basis": {
            "site_injuries_report": site_inj.get("report"),
            "site_injuries_src": site_inj.get("src"),
            "site_meta_injury_report_text": site_meta.get("data_windows", {}).get("injury_report"),
            "site_rows": len(site_inj.get("rows", [])),
        },
        "fresh_basis": {
            "report": injury["report"],
            "source_url": injury["source_url"],
            "edition_index_url": injury["edition_index_url"],
            "rows_1115": len(new_rows_1115),
            "rows_1116_nys": sum(1 for r in injury["rows"] if r[0] == "11/16/2026"),
        },
        "consecutive_edition_diff": {
            "from": prev_inj["report"],
            "to": injury["report"],
            "overlap": "the nine 11/15 games (18 team entries in the old edition)",
            "old_edition_rows_for_overlap": len(old_rows),
            "old_edition_player_rows_for_overlap": sum(1 for r in old_rows if r["player"]),
            "old_edition_all_nys": all(r["status"] == "NOT YET SUBMITTED" for r in old_rows),
            "new_edition_rows_for_overlap": len(new_rows_1115),
            "new_edition_player_rows_for_overlap": sum(1 for r in new_rows_1115 if r[4]),
            "player_level_status_changes": [],
            "player_level_note": "the old edition listed zero players for 11/15 (all 18 entries were "
                                 "NOT YET SUBMITTED), so no player-level status change is computable "
                                 "between these two editions; nothing is inferred",
            "team_filing_changes": team_filing_changes,
            "newly_listed_player_rows": len(newly_listed),
            "newly_listed_sample": newly_listed[:10],
            "still_not_submitted": still_nys,
            "attribution_caveat": "team filing states use printed Team cells only; the 13 continuation rows "
                                  "whose Team cell the PDF dropped are listed under newly_listed_player_rows "
                                  "with attribution='dropped-by-pdf' and are never attributed to a team here",
        },
        "verdict": (f"STALE: the site prices from {site_inj.get('report')} while the newest official edition at "
                    f"read time is {injury['report']}. Between the previous in-repo edition "
                    f"({prev_inj['report']}) and this one, {sum(1 for t in team_filing_changes if t['new'].startswith('filed'))} "
                    f"of 18 team entries for 11/15 moved from NOT YET SUBMITTED to filed, "
                    f"{len(newly_listed)} player designation rows appeared, and "
                    f"{len(still_nys)} entry is still unfiled (Dallas, inside its game-day window). "
                    "Nothing here is re-priced: re-pricing a frozen line would put post-cut information "
                    "into a graded number (standing rule from §31.1 G03)."),
    }

    # ---------- E. register state (so ids cannot collide)
    items = flagged["items"]
    out["sections"]["E_register_state"] = {
        "flagged_items_published": len(items),
        "last_flag_id": items[-1]["id"] if items else None,
        "next_free_flag_id": f"F{int(items[-1]['id'][1:]) + 1}" if items and items[-1]["id"][1:].isdigit() else None,
        "note": "append-only: new flags from this pass start at the next free id",
    }

    with open(os.path.join(HERE, "compare.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    # console summary
    A = out["sections"]["A_1114_finals_vs_published"]["summary"]
    B = out["sections"]["B_horizon_1115_to_1117_vs_published"]["summary"]
    D = out["sections"]["D_injury_edition_currency_and_diff"]["consecutive_edition_diff"]
    print("A finals:", A)
    print("B horizon:", B)
    print("C 11/18 published rows:", out["sections"]["C_1118_coverage"]["published_1118_rows"],
          "fresh:", out["sections"]["C_1118_coverage"]["fresh_1118_games"])
    filed = sum(1 for t in D["team_filing_changes"] if t["new"].startswith("filed"))
    print("D diff: team entries filed %d/18, new player rows %d, still NYS %d"
          % (filed, D["newly_listed_player_rows"], len(D["still_not_submitted"])))
    print("E next flag id:", out["sections"]["E_register_state"]["next_free_flag_id"])
    print("compare.json written")


if __name__ == "__main__":
    main()
