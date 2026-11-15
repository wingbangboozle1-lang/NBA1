#!/usr/bin/env python3
"""capture_injury.py — store the 2026-11-15 06:15 AM ET injury report and diff it.

Source: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf
(retrieved live 2026-11-15T11:5xZ through the web-fetch channel; the edition name
comes from the official index page, which listed editions through 06:15 AM ET at
read time). Rows are transcribed verbatim, in report order.

Merged-cell caveat (honest): where the PDF's extraction dropped the Team column on
a continuation row, the row is stored with "team": null and "team_inherited" set to
the nearest preceding printed team in the same game block. Those rows are marked
and are diffed only within their inherited team.

Writes:
  data/official/injury_2026-11-15_0615AM.json
  data/official/injury_diff_2026-11-14_0130PM_to_2026-11-15_0615AM.json

Run:  python3 verify/2026-11-15-83d380ad/capture_injury.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf"
INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"
RETRIEVED = "2026-11-15T11:52Z"

# (game_date, tip, matchup, team_or_None, player, status, reason)
R = [
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Furphy, Johnny", "Out", "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Haliburton, Tyrese", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "McConnell, T.J.", "Probable", "Injury/Illness - Right Hamstring Strain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Nembhard, Andrew", "Questionable", "Injury/Illness - Left Hip Soreness / Tightness"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Nesmith, Aaron", "Questionable", "Injury/Illness - Left Hand Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Indiana Pacers", "Sheppard, Ben", "Out", "Injury/Illness - Left Meniscus Tear"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Barlow, Dominick", "Out", "Injury/Illness - Low Back Stress Reaction"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Bona, Adem", "Out", "Injury/Illness - Cervical Spine Sprain"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Embid, Joel", "Out", "Injury/Illness - Right Foot Plantar Fascia Injury Management"),
    ("11/15/2026", "01:00 (ET)", "IND@PHI", "Philadelphia 76ers", "Hukporti, Ariel", "Out", "Injury/Illness - Right Achilles Tendon Rupture / Tear"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Carr, Cameron", "Out", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Grimes, Quentin", "Available", "Injury/Illness - Right Finger Splint"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "James, Bronny", "Questionable", "Injury/Illness - Illness"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Los Angeles Lakers", "Reaves, Austin", "Out", "Injury/Illness - Left Heel Contusion / Bone Bruise"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Sexton, Collin", "Questionable", "Injury/Illness - Right Orbital Laceration"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", None, "Thiero, Adou", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "04:00 (ET)", "LAL@PHX", "Phoenix Suns", "Williams, Mark", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Ajayi, Michael", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Boswell, Kylan", "Out", "G League - Two-Way"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Knueppel, Kon", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Schroder, Dennis", "Out", "Injury/Illness - Left Hamstring Strain"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "Charlotte Hornets", "Steinbach, Hannes", "Out", "G League - On Assignment"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Beal, Bradley", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Ingram, Brandon", "Out", "Injury/Illness - Right Heel Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Miller, Jordan", "Out", "Injury/Illness - Left Rotator Cuff Surgery"),
    ("11/15/2026", "04:30 (ET)", "CHA@LAC", "LA Clippers", "Niederhauser, Yanic Konan", "Out", "Injury/Illness - Right Lisfranc Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Brown, Maliq", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Gillespie, Ja'Kobi", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Harris, Tobias", "Out", "Injury/Illness - Left Calf Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "San Antonio Spurs", "Quaintance, Jayden", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Alexander, Trey", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", "Utah Jazz", "Bufkin, Kobe", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "Hayes, Jaxson", "Out", "Injury/Illness - Left Knee Strain"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "Ingram, Harrison", "Out", "G League - Two-Way"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "Jackson Jr., Jaren", "Out", "Injury/Illness - Right MCL Tear"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "Markkanen, Lauri", "Out", "Injury/Illness - Right Hand Fracture"),
    ("11/15/2026", "05:00 (ET)", "SAS@UTA", None, "Nurkic, Jusuf", "Out", "Injury/Illness - Right 2nd Plantar Plate Tear"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Dallas Mavericks", None, "NOT YET SUBMITTED", None),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Carter, Devin", "Questionable", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Cenac Jr., Christopher", "Questionable", "G League - On Assignment"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Mitchell, Dillon", "Questionable", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "DAL@BOS", "Boston Celtics", "Williams, Amari", "Questionable", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Barnes, Scottie", "Questionable", "Injury/Illness - Left Groin Strain"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Bittle, Nate", "Out", "Injury/Illness - Right Foot Avulsion Fracture"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Leonard, Kawhi", "Out", "Injury/Illness - Left Knee Injury Management"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "McCullar Jr., Kevin", "Out", "G League - Two-Way"),
    ("11/15/2026", "06:00 (ET)", "NYK@TOR", "Toronto Raptors", "Smith, Malachi", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Adams, Steven", "Probable", "Injury/Illness - Right Soleus Strain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Capela, Clint", "Out", "Injury/Illness - Right Ankle Sprain"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Houston Rockets", "Copeland, Quadir", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Phillips, Julian", "Out", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "Smart, Marcus", "Out", "League Suspension"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", None, "VanVleet, Fred", "Out", "Injury/Illness - Right Knee Injury Management"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Beekman, Reece", "Out", "Injury/Illness - Right AC Joint Injury"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Carrington, Bub", "Questionable", "Injury/Illness - Chest / Sternum Contusion"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Champagne, Justin", "Out", "Injury/Illness - Right Foot Surgery"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Johnson, Tre", "Questionable", "Injury/Illness - Low Back Soreness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Okpara, Felix", "Questionable", "G League - Two-Way"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Sarr, Alex", "Questionable", "Injury/Illness - Illness"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Vukcevic, Tristan", "Out", "Injury/Illness - Left Hip Impingement"),
    ("11/15/2026", "07:00 (ET)", "HOU@WAS", "Washington Wizards", "Watkins, Jamir", "Out", "Injury/Illness - Left ACL Repair / Surgery"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Flemings, Kingston", "Out", "Injury/Illness - Lumbar Strain"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Gilbert, Keshon", "Out", "Injury/Illness - Left Knee Inflammation; Non-Surgical Procedure"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Gueye, Mouhamed", "Out", "Injury/Illness - Left Foot Fracture"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Landale, Jock", "Available", "Injury/Illness - Face Mask"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Atlanta Hawks", "Newell, Asa", "Out", "Injury/Illness - Left Great Toe Hyperextension"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", None, "Veesaar, Henri", "Out", "Injury/Illness - Right ACL Tear"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", None, "Wilson, Jalen", "Doubtful", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Dieng, Ousmane", "Out", "Injury/Illness - Left Finger Sprain"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Jones, Kam", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Markovic, Bogoljub", "Out", "G League - On Assignment"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Nance, Pete", "Out", "G League - Two-Way"),
    ("11/15/2026", "08:00 (ET)", "ATL@MIL", "Milwaukee Bucks", "Ryan, Cormac", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Holmgren, Chet", "Out", "Injury/Illness - Right Knee/ Injury Recovery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Mitchell, Ajay", "Questionable", "Injury/Illness - Left Ankle Sprain"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Sorber, Thomas", "Out", "Injury/Illness - Right Knee Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Wallace, Cason", "Out", "Injury/Illness - Left Shoulder Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jalen", "Out", "Injury/Illness - Left Ankle Surgery"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Oklahoma City Thunder", "Williams, Jaylin", "Out", "Injury/Illness - Low Back Spasms"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Achiuwa, Precious", "Questionable", "Injury/Illness - Left Ankle Soreness"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Mogbo, Jonathan", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Murray, Keegan", "Questionable", "Injury/Illness - Illness"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Pedulla, Sean", "Out", "G League - Two-Way"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", "Sacramento Kings", "Raynaud, Maxime", "Out", "Injury/Illness - Right Patella Subluxation"),
    ("11/15/2026", "09:00 (ET)", "OKC@SAC", None, "Simmons, Ben", "Out", "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
]
NYC = [("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls"), ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers"),
       ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies"), ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Washington Wizards"),
       ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic"), ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Boston Celtics"),
       ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Houston Rockets"), ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat"),
       ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Philadelphia 76ers"), ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets"),
       ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors"), ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans"),
       ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers"), ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves"),
       ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Phoenix Suns"), ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets")]

TEAM_INHERIT = {
    ("LAL@PHX", "Sexton, Collin"): "Los Angeles Lakers (inherited: PDF merged cells)",
    ("LAL@PHX", "Thiero, Adou"): "Los Angeles Lakers (inherited: PDF merged cells)",
    ("SAS@UTA", "Hayes, Jaxson"): "Utah Jazz (inherited: PDF merged cells)",
    ("SAS@UTA", "Ingram, Harrison"): "Utah Jazz (inherited: PDF merged cells)",
    ("SAS@UTA", "Jackson Jr., Jaren"): "Utah Jazz (inherited: PDF merged cells)",
    ("SAS@UTA", "Markkanen, Lauri"): "Utah Jazz (inherited: PDF merged cells)",
    ("SAS@UTA", "Nurkic, Jusuf"): "Utah Jazz (inherited: PDF merged cells)",
    ("HOU@WAS", "Phillips, Julian"): "Houston Rockets (inherited: PDF merged cells)",
    ("HOU@WAS", "Smart, Marcus"): "Houston Rockets (inherited: PDF merged cells)",
    ("HOU@WAS", "VanVleet, Fred"): "Houston Rockets (inherited: PDF merged cells)",
    ("ATL@MIL", "Veesaar, Henri"): "Atlanta Hawks (inherited: PDF merged cells)",
    ("ATL@MIL", "Wilson, Jalen"): "Atlanta Hawks (inherited: PDF merged cells)",
    ("OKC@SAC", "Simmons, Ben"): "Sacramento Kings (inherited: PDF merged cells)",
}

rows = []
for gd, tip, mu, team, player, status, reason in R:
    row = {
        "game_date": gd, "game_time_et": tip, "matchup": mu,
        "team_printed": team,
        "team_effective": team or TEAM_INHERIT.get((mu, player)),
        "team_inherited": team is None,
        "player": player, "status": status, "reason": reason,
        "source_url": PDF,
    }
    rows.append(row)
for gd, tip, mu, team in NYC:
    rows.append({"game_date": gd, "game_time_et": tip, "matchup": mu,
                 "team_printed": team, "team_effective": team, "team_inherited": False,
                 "player": None, "status": "NOT YET SUBMITTED", "reason": None,
                 "source_url": PDF})

doc = {
    "edition": "NBA Official Injury Report, 11/15/26 06:15 AM ET",
    "edition_file": "Injury-Report_2026-11-15_06_15AM.pdf",
    "revision_time_et": "2026-11-15 06:15 AM ET (edition stamp printed on every PDF page)",
    "retrieved_utc": RETRIEVED,
    "captured_by": "arena/83d380ad-nba1",
    "source_url": PDF,
    "index_url": INDEX,
    "index_note": ("Edition name listed on the official injury-report index page at retrieval time "
                   "(the index ended at the 06:15 AM ET edition for 2026-11-15). Later game-day "
                   "editions (11:00 AM-1:00 PM ET per league policy) had not yet published."),
    "submission_rule_quoted": ("By 5 p.m. local time the day before a game (other than the second day of a "
                               "back-to-back), teams must designate a participation status... For the second "
                               "game of a back-to-back, teams must report the above information by 1 p.m. local "
                               "time on the day of the game."),
    "submission_rule_url": INDEX,
    "merged_cell_caveat": ("13 rows lost their Team column in PDF extraction and are marked team_inherited; "
                           "their team_effective is the nearest preceding printed team in the same game block. "
                           "Flagged for review (F74)."),
    "rows_note": ("Verbatim report order. Rows cover the 2026-11-15 slate; the 2026-11-16 slate is printed "
                  "NOT YET SUBMITTED for all 16 team blocks. The report prints no rows for New York Knicks "
                  "(NYK@TOR): the edition prints NOT YET SUBMITTED rows for unsubmitted teams (Dallas, same "
                  "slate), so an absent block most likely means no reportable players - nothing inferred, "
                  "flagged for review (F74)."),
    "row_count": len(rows),
    "rows": rows,
}
p = os.path.join(ROOT, "data", "official", "injury_2026-11-15_0615AM.json")
json.dump(doc, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("wrote data/official/injury_2026-11-15_0615AM.json", len(rows), "rows")

# --- diff vs the previous stored edition (11/14 01:30 PM ET) ---------------
prev = json.load(open(os.path.join(ROOT, "data", "official", "injury_2026-11-14_0130PM.json"), encoding="utf-8"))
prev_rows = prev["rows"]


def prow_key(r):
    return (r.get("player") or "", r.get("team") or r.get("team_printed") or "")


prev_by_player = {}
for r in prev_rows:
    if r.get("player"):
        prev_by_player.setdefault(r["player"], []).append(r)

changed, new_only, gone = [], [], []
for r in rows:
    if not r["player"]:
        continue
    old = prev_by_player.get(r["player"])
    if not old:
        new_only.append({"player": r["player"], "team_effective": r["team_effective"],
                         "status_now": r["status"], "reason_now": r["reason"],
                         "note": "player absent from the 2026-11-14 01:30 PM edition"})
        continue
    for o in old:
        if o.get("status") != r["status"]:
            changed.append({"player": r["player"], "team_effective": r["team_effective"],
                            "status_before": o.get("status"), "status_now": r["status"],
                            "reason_now": r["reason"],
                            "before_edition": prev["edition"], "after_edition": doc["edition"]})

prev_players = {r.get("player") for r in prev_rows if r.get("player")}
now_players = {r["player"] for r in rows if r["player"]}
for name in sorted(prev_players - now_players):
    gone.append({"player": name, "note": "present in 11/14 01:30 PM edition (11/14 slate), absent from 11/15 06:15 AM edition (11/15 slate) - different slates, not a status change"})

diff = {
    "title": "Injury-report consecutive-edition diff (status-change detection)",
    "before": {"edition": prev["edition"], "source_url": prev["source_url"],
               "retrieved_utc": prev.get("captured_at_utc"), "rows": len(prev_rows)},
    "after": {"edition": doc["edition"], "source_url": PDF,
              "retrieved_utc": RETRIEVED, "rows": len(rows)},
    "comparability_note": ("The two editions cover different game slates (11/14 games vs 11/15 games). "
                           "Player-level status changes can only be detected for players listed in both; "
                           "the only team on both slates is Dallas (11/14 at CLE, 11/15 at BOS - a back-to-back), "
                           "whose 11/15 block is NOT YET SUBMITTED under the league's B2B game-day rule. "
                           "The team-block filing change below is the meaningful delta for this pair."),
    "team_blocks_11_15_before": "all 18 team blocks printed NOT YET SUBMITTED in the 01:30 PM edition",
    "team_blocks_filed_since": ["Indiana Pacers", "Philadelphia 76ers", "Los Angeles Lakers", "Phoenix Suns",
                                "Charlotte Hornets", "LA Clippers", "San Antonio Spurs", "Utah Jazz",
                                "Boston Celtics", "Toronto Raptors", "Houston Rockets", "Washington Wizards",
                                "Atlanta Hawks", "Milwaukee Bucks", "Oklahoma City Thunder", "Sacramento Kings"],
    "team_blocks_still_unsubmitted": ["Dallas Mavericks (second game of a back-to-back; league deadline 1 p.m. local game day)"],
    "team_blocks_no_rows_printed": ["New York Knicks (no rows and no NOT YET SUBMITTED row in either edition - flagged, not inferred)"],
    "player_status_changes": changed,
    "players_new_vs_before": new_only,
    "players_only_in_before": gone,
    "counts": {"status_changes": len(changed), "new_vs_before": len(new_only),
               "only_in_before": len(gone), "comparable_player_rows": len(prev_players & now_players)},
}
p = os.path.join(ROOT, "data", "official", "injury_diff_2026-11-14_0130PM_to_2026-11-15_0615AM.json")
json.dump(diff, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("wrote diff:", diff["counts"])
