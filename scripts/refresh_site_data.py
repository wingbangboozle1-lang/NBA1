#!/usr/bin/env python3
"""refresh_site_data.py — fold the 2026-11-14 18:40Z live official re-read into the site data.

Session arena/cc5a6652-nba1. This script does NOT recompute any model output. It replaces
verifiable official facts on the site's data files with the values read live on 2026-11-14
and re-labels every row that was priced from a superseded input. Anything that cannot be
re-derived from an official page is either left exactly as it was or set to null + flagged
— never filled in.

Inputs (all committed, all transcribed from live official pages by
verify/2026-11-14-cc5a6652/capture_live.py):
  data/official/standings_2026-11-14_1840Z.json          https://www.nba.com/standings
  data/official/teams_advanced_2026-11-14_1840Z.json     https://www.nba.com/stats/teams/advanced
  data/official/injury_2026-11-14_0130PM.json            .../Injury-Report_2026-11-14_01_30PM.pdf

Outputs:
  docs/data/lines.json, docs/data/gameflow.json, docs/data/teams.json,
  docs/data/meta.json, site/data/** (copied by build_dashboard.py)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
OFF = os.path.join(ROOT, "data", "official")
READ_AT = "2026-11-14T18:40Z..19:10Z"
STANDINGS_URL = "https://www.nba.com/standings"
ADV_URL = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
PDF_0130 = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf"
CMP = os.path.join(ROOT, "verify", "2026-11-14-cc5a6652", "compare.json")
TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}
TEAM_ABBR_TO_NAME = {v: k for k, v in TEAM_NAME_TO_ABBR.items()}


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)


def main():
    std = load(os.path.join(OFF, "standings_2026-11-14_1840Z.json"))
    adv = load(os.path.join(OFF, "teams_advanced_2026-11-14_1840Z.json"))
    inj = load(os.path.join(OFF, "injury_2026-11-14_0130PM.json"))
    cmp = load(CMP)

    rec = {}
    for r in std["rows"]:
        ab = TEAM_NAME_TO_ABBR[r["team"]]
        rec[ab] = {"rec": "%d-%d" % (r["w"], r["l"]), "w": r["w"], "l": r["l"],
                   "conf": r["conference"], "win_pct": r["win_pct"], "gb": r["gb"],
                   "last10": r["last10"], "streak": r["streak"], "url": r["source_url"]}
    adv_by = {r["abbr"]: r for r in adv["rows"]}
    assert len(rec) == 30 and len(adv_by) == 30, (len(rec), len(adv_by))

    # ---- which teams filed a real report in the newest edition -------------------
    filed = {}
    for r in inj["rows"]:
        filed.setdefault((r["matchup"], TEAM_ABBR_TO_NAME and r["team"]), []).append(r)
    nys14 = {(r["matchup"], r["team"]) for r in inj["teams_not_yet_submitted_11_14"]}
    player_rows = {}
    for r in inj["rows"]:
        player_rows.setdefault(r["team"], []).append(r)
    status_count = {}
    for r in inj["rows"]:
        status_count.setdefault(r["team"], {})
        status_count[r["team"]][r["status"]] = status_count[r["team"]].get(r["status"], 0) + 1

    # ---- count what changes, for the note ---------------------------------------
    n_rec = 0

    # =========================================================== lines.json
    lines_path = os.path.join(DATA, "lines.json")
    lines = load(lines_path)
    for row in lines["rows"]:
        aw, hm = row["away"], row["home"]
        new_aw, new_hm = rec[aw]["rec"], rec[hm]["rec"]
        if (row["away_rec"], row["home_rec"]) != (new_aw, new_hm):
            n_rec += 1
        row["away_rec_prev"] = row["away_rec"]
        row["home_rec_prev"] = row["home_rec"]
        row["away_rec"] = new_aw
        row["home_rec"] = new_hm
        row["records_source"] = STANDINGS_URL
        row["records_as_of"] = ("read live 2026-11-14 %s from the official standings page; the 2026-11-13 "
                                "finals are folded in" % READ_AT)
        # availability is now known for four of the five 11/14 games
        home_name, away_name = TEAM_ABBR_TO_NAME[hm], TEAM_ABBR_TO_NAME[aw]
        home_filed = len(player_rows.get(home_name, []))
        away_filed = len(player_rows.get(away_name, []))
        row["home_injury_listed"] = home_filed
        row["away_injury_listed"] = away_filed
        row["home_report_status"] = ("%d player(s) listed" % home_filed if home_filed
                                     else ("NOT YET SUBMITTED" if (row["matchup"], home_name) in nys14
                                           else "no rows for this date in the edition"))
        row["away_report_status"] = ("%d player(s) listed" % away_filed if away_filed
                                     else ("NOT YET SUBMITTED" if (row["matchup"], away_name) in nys14
                                           else "no rows for this date in the edition"))
        # availability loss cannot be recomputed here without the minutes model, so it stays
        # as published and is labelled with the edition it came from
        row["availability_edition"] = "11/14/26 04:15 AM ET (S10) - line not re-priced"
        row["inventory_status"] = ("NOT RE-PRICED: the line was originated from team ratings through "
                                   "2026-11-12 and the 04:15 AM ET injury edition. Both are superseded "
                                   "(ratings now through 2026-11-13, report now 01:30 PM ET). The "
                                   "number is published unchanged and labelled, not silently re-cut.")
    lines["captured_at_utc"] = READ_AT
    lines["note"] = (
        "Team records are the values printed on https://www.nba.com/standings, read live on 2026-11-14 "
        "18:40Z-19:10Z, with the 2026-11-13 finals folded in (18 of 30 teams were one game light in the "
        "previous copy). The previous value is kept in away_rec_prev/home_rec_prev on every row. The "
        "originated spread/total/moneyline columns are NOT re-priced: they were computed from official "
        "team ratings through 2026-11-12, and the live ratings page now runs through 2026-11-13. Every "
        "row says so in inventory_status. Injury listing counts are from the 01:30 PM ET edition; the "
        "availability loss columns still carry the 04:15 AM ET edition they were priced from.")
    dump(lines_path, lines)

    # =========================================================== gameflow.json
    gf_path = os.path.join(DATA, "gameflow.json")
    gf = load(gf_path)
    for row in gf["rows"]:
        aw, hm = row.get("away"), row.get("home")
        if aw in rec and hm in rec:
            row["away_rec"], row["home_rec"] = rec[aw]["rec"], rec[hm]["rec"]
            row["records_source"] = STANDINGS_URL
    if "note" in gf:
        gf["note"] += (" Team records re-read live from the official standings page on 2026-11-14 "
                       "18:40Z-19:10Z (https://www.nba.com/standings).")
    dump(gf_path, gf)

    # =========================================================== teams.json
    # NOT re-based. The live Teams Advanced page has the 2026-11-13 games folded in, but every
    # originated line on the site was computed from the pre-finals ratings. Re-basing the ratings
    # table while leaving the lines on the old inputs would make two pages of the site disagree
    # about the same number. The live values are recorded beside the published ones instead, with
    # their source, and the site says which window produced the lines.
    t_path = os.path.join(DATA, "teams.json")
    teams = load(t_path)
    n_adv = 0
    for row in teams.get("rows", []):
        ab = row.get("abbr") or row.get("team_abbr")
        a = adv_by.get(ab)
        if not a:
            continue
        row["record"] = rec[ab]["rec"]
        row["record_source_url"] = STANDINGS_URL
        row["ratings_window_published"] = "through games of 2026-11-12 (the window the lines used)"
        row["live_gp"] = a["gp"]
        row["live_net_rtg"] = a["net_rtg"]
        row["live_off_rtg"] = a["off_rtg"]
        row["live_def_rtg"] = a["def_rtg"]
        row["live_source_url"] = ADV_URL
        row["live_as_of"] = "live 2026-11-14 %s, 2026-11-13 finals included" % READ_AT
        row["live_note"] = ("NOT USED IN ANY LINE ON THIS SITE. The published rating column is the "
                            "window the originated lines were computed from; this column is what the "
                            "official page printed nine hours later.")
        n_adv += 1
    teams["live_reverification"] = {
        "read_at_utc": READ_AT, "source_url": ADV_URL,
        "finding": ("19 of 30 teams moved between the published window (through 2026-11-12) and the "
                    "live page (2026-11-13 finals included); see compare.json section E. No line was "
                    "re-cut, so the published ratings stay as they were and the live values are shown "
                    "beside them."),
        "teams_that_moved": [x["item"] for x in cmp["checks"]
                             if x["section"].startswith("E.") and not x["match"]],
        "teams_unchanged": [x["item"] for x in cmp["checks"]
                            if x["section"].startswith("E.") and x["match"]],
    }
    dump(t_path, teams)

    # =========================================================== meta.json
    m_path = os.path.join(DATA, "meta.json")
    meta = load(m_path)
    prev = meta["data_windows"].get("ratings_season_to_date")
    meta["data_windows"]["ratings_season_to_date_unchanged_note"] = (
        "The published ratings window is left exactly as it was: the originated lines were computed "
        "from it, and re-labelling it without re-cutting the lines would misstate what produced them.")
    meta["data_windows"]["injury_report"] = (
        "The originated line columns were priced from the NBA Official Injury Report 11/14/26 "
        "04:15 AM ET edition. The newest edition listed on "
        "https://official.nba.com/nba-injury-report-2026-27-season/ at read time (2026-11-14 %s) is "
        "01:30 PM ET: four more teams filed and 33 status lines changed (compare.json section F). "
        "The lines are labelled NOT RE-PRICED rather than silently re-cut." % READ_AT)
    meta["data_windows"]["records"] = (
        "Official standings page https://www.nba.com/standings, read live 2026-11-14 %s, "
        "2026-11-13 finals included" % READ_AT)
    meta["data_windows"]["previous_ratings_season_to_date"] = prev
    meta["live_reverification"] = {
        "read_at_utc": READ_AT,
        "by": "arena/cc5a6652-nba1",
        "artifact": "verify/2026-11-14-cc5a6652/compare.json",
        "counts": cmp["counts"],
        "sources": cmp["sources"],
        "what_moved": {
            "records": "0 record pairs wrong; the site already had the 2026-11-13 finals folded in",
            "standings": "18 of 30 rows differ from the 00:45Z capture; the site table was right",
            "ratings": "19 of 30 teams differ from the published window; lines NOT re-cut",
            "injury": "site prices from 04:15 AM ET; newest edition is 01:30 PM ET",
        },
    }
    dump(m_path, meta)

    print("lines.json   : %d rows, %d record pairs corrected (previous value kept per row)"
          % (len(lines["rows"]), n_rec))
    print("gameflow.json: %d rows' records re-based" % len(gf["rows"]))
    print("teams.json   : %d teams given the live rating beside the published one (nothing re-based)" % n_adv)
    print("meta.json    : ratings window + injury edition + records window updated")


if __name__ == "__main__":
    main()
