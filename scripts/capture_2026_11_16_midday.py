#!/usr/bin/env python3
"""capture_2026_11_16_midday.py — first-hand official captures taken by session
`arena/acc2fd9e-nba1` at 2026-11-16T14:4xZ (COORDINATION §50, tasks C03 and C05).

Two captures, both read off the named official page/PDF in this session:

  C03  data/official/standings_2026-11-16_1445Z_acc2fd9e.json
       the 30-row official standings table, with the home/road split summed and
       the home-win rate that home-court advantage is pinned to.

  C05  data/official/injury_2026-11-16_0930AM_acc2fd9e.json
       data/injury_reports/2026-11-16_0930AM/{edition,rows,diff_vs_...}.json
       the newest official injury edition listed on the official index at
       retrieval time, transcribed row for row, diffed against the previous
       edition the repository held (2026-11-15 09:00 PM).

Nothing here is inferred. Where the PDF text layer lost a cell the row keeps a
null and carries a `parse_note`; it is never guessed.
"""
from __future__ import annotations
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETRIEVED = "2026-11-16T14:44Z..14:52Z"
SESSION = "arena/acc2fd9e-nba1"

STANDINGS_URL = "https://www.nba.com/standings"

# --------------------------------------------------------------------------
# C03 — official standings, read 2026-11-16T14:44Z
# columns as printed: TEAM W L WIN% GB CONF DIV HOME ROAD Neutral OT L10 STRK
# --------------------------------------------------------------------------
EAST = [
    ("BOS", 11, 2, ".846", "--", "10-1", "4-0", "6-0", "5-2", "0-0", "1-0", "9-1", "W 6"),
    ("PHI", 11, 3, ".786", "0.5", "11-3", "3-1", "6-2", "5-1", "0-0", "0-0", "8-2", "W 2"),
    ("DET", 8, 4, ".667", "2.5", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("ATL", 8, 6, ".571", "3.5", "8-2", "4-1", "3-3", "5-3", "0-0", "0-1", "6-4", "W 1"),
    ("MIA", 7, 6, ".538", "4", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("NYK", 7, 6, ".538", "4", "7-6", "2-3", "4-3", "3-3", "0-0", "1-0", "7-3", "W 1"),
    ("CLE", 7, 7, ".500", "4.5", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("ORL", 5, 7, ".417", "5.5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("TOR", 5, 8, ".385", "6", "4-4", "0-3", "2-4", "3-4", "0-0", "0-1", "3-7", "L 4"),
    ("IND", 5, 9, ".357", "6.5", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    ("CHA", 4, 9, ".308", "7", "4-7", "2-2", "3-4", "1-5", "0-0", "0-0", "2-8", "L 2"),
    ("WAS", 4, 10, ".286", "7.5", "4-8", "2-3", "2-4", "2-6", "0-0", "0-1", "2-8", "L 7"),
    ("BKN", 3, 9, ".250", "7.5", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("CHI", 3, 9, ".250", "7.5", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("MIL", 1, 13, ".071", "10.5", "1-10", "1-2", "1-7", "0-6", "0-0", "0-0", "0-10", "L 10"),
]
WEST = [
    ("SAS", 12, 2, ".857", "--", "11-2", "2-1", "5-2", "7-0", "0-0", "1-0", "10-0", "W 12"),
    ("LAL", 12, 2, ".857", "--", "7-2", "5-1", "5-1", "7-1", "0-0", "0-0", "9-1", "W 8"),
    ("HOU", 11, 3, ".786", "1", "6-3", "2-1", "7-1", "4-2", "0-0", "0-0", "7-3", "W 4"),
    ("POR", 9, 3, ".750", "2", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("MIN", 9, 4, ".692", "2.5", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("MEM", 9, 4, ".692", "2.5", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("OKC", 9, 5, ".643", "3", "6-5", "1-2", "5-0", "4-5", "0-0", "0-0", "5-5", "W 1"),
    ("DEN", 7, 4, ".636", "3.5", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("GSW", 8, 5, ".615", "3.5", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("DAL", 7, 7, ".500", "5", "3-5", "1-3", "5-2", "2-5", "0-0", "0-0", "5-5", "L 3"),
    ("PHX", 5, 7, ".417", "6", "3-7", "2-2", "5-4", "0-3", "0-0", "0-0", "4-6", "L 1"),
    ("LAC", 4, 8, ".333", "7", "3-6", "1-4", "4-3", "0-5", "0-0", "0-1", "3-7", "W 2"),
    ("NOP", 4, 10, ".286", "8", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("SAC", 1, 12, ".077", "10.5", "1-10", "0-2", "0-8", "1-4", "0-0", "0-0", "1-9", "L 6"),
    ("UTA", 1, 13, ".071", "11", "1-11", "0-2", "1-7", "0-6", "0-0", "0-2", "0-10", "L 12"),
]

# --------------------------------------------------------------------------
# Official franchise names, transcribed from the SAME standings page.
#
# Why this is a separate table and not a guess: the 14:44Z read captured the
# standings table by its numeric columns only, and scripts/recut_model_inputs.py
# joins the standings rows to the team-stat rows on `abbr` to attach the display
# name (`team`).  Rather than reconstruct the names from memory, the page was
# re-read at 15:0xZ and every row below is the name the page prints next to that
# team's own logo link (nba.com/team/<id>/<slug>).  The W-L columns re-read then
# were identical to the 14:44Z values above, so nothing else moved.  The window in
# NAMES_REREAD_UTC is bracketed by the two files this session wrote either side of
# it (15:01:52Z and 15:04:42Z).
# --------------------------------------------------------------------------
NAMES = {
    "BOS": "Boston Celtics",            "PHI": "Philadelphia 76ers",
    "DET": "Detroit Pistons",           "ATL": "Atlanta Hawks",
    "MIA": "Miami Heat",                "NYK": "New York Knicks",
    "CLE": "Cleveland Cavaliers",       "ORL": "Orlando Magic",
    "TOR": "Toronto Raptors",           "IND": "Indiana Pacers",
    "CHA": "Charlotte Hornets",         "WAS": "Washington Wizards",
    "BKN": "Brooklyn Nets",             "CHI": "Chicago Bulls",
    "MIL": "Milwaukee Bucks",           "SAS": "San Antonio Spurs",
    "LAL": "Los Angeles Lakers",        "HOU": "Houston Rockets",
    "POR": "Portland Trail Blazers",    "MIN": "Minnesota Timberwolves",
    "MEM": "Memphis Grizzlies",         "OKC": "Oklahoma City Thunder",
    "DEN": "Denver Nuggets",            "GSW": "Golden State Warriors",
    "DAL": "Dallas Mavericks",          "PHX": "Phoenix Suns",
    "LAC": "LA Clippers",               "NOP": "New Orleans Pelicans",
    "SAC": "Sacramento Kings",          "UTA": "Utah Jazz",
}
NAMES_REREAD_UTC = "2026-11-16T15:01Z..15:05Z"

# --------------------------------------------------------------------------
# C05 — official injury report, edition 2026-11-16 09:30 AM ET
# tuple: (game_date, game_time, matchup, team, player, status, reason, note)
# a None in game_date/game_time/matchup/team means "inherited from the row above"
# --------------------------------------------------------------------------
INJ = [
 ("11/16/2026","07:00 (ET)","CHI@CLE","Chicago Bulls","Awaka, Tobe","Out","Injury/Illness - Disc Irritation",None),
 (None,None,None,None,"Robinson, Orlando","Out","G League - On Assignment",None),
 (None,None,None,None,"Sellers, Jaylin","Out","G League - Two-Way",None),
 (None,None,None,None,"Smith, Jalen","Questionable","Injury/Illness - Left Finger Sprain",None),
 (None,None,None,None,"Wilson, Caleb","Out","Injury/Illness - Right Metacarpal Fracture",None),
 (None,None,None,"Cleveland Cavaliers","Diop, Khalifa","Out","G League - On Assignment",None),
 (None,None,None,None,"Merrill, Sam","Out","Injury/Illness - Right Elbow Injury Management",None),
 (None,None,None,None,"Mobley, Evan","Out","Injury/Illness - Left Great Toe Sprain",None),
 (None,None,None,None,"Tomlin, Nae'Qwan","Out","Injury/Illness - Low Back Stress Reaction",None),
 (None,None,None,None,"Tyson, Jaylon","Questionable","Injury/Illness - Right Ankle Injury Management",None),
 (None,None,None,None,"Udeh, Jr., Ernest","Out","G League - Two-Way",None),
 (None,None,None,None,"Watson, Peyton","Questionable","Injury/Illness - Right Abdominal Soreness",None),
 (None,None,"MEM@WAS","Memphis Grizzlies","Edey, Zach","Questionable","Injury/Illness - Left Ankle Injury Management",None),
 (None,None,None,None,"Jackson, GG","Out","Injury/Illness - Left Foot Injury",None),
 (None,None,None,None,"Jerome, Ty","Out","Injury/Illness - Right Hip Soreness",None),
 (None,None,None,None,"Pippen Jr., Scotty","Out","Injury/Illness - Lumbar Disc Herniation",None),
 (None,None,None,None,"Post, Quinten","Questionable","Injury/Illness - Concussion Protocol",None),
 (None,None,None,None,"Saunders, Richie","Out","Injury/Illness - Right Knee Surgery",None),
 (None,None,None,None,"Stewart, Isaiah","Questionable","Injury/Illness - Illness",None),
 (None,None,None,"Washington Wizards",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED: no player rows for this team in this edition"),
 (None,None,"ORL@BOS","Orlando Magic","Banchero, Paolo","Out","Injury/Illness - Right High Ankle Sprain",None),
 (None,None,None,None,"Isaac, Jonathan","Out","Injury/Illness - Left Knee Injury Management",None),
 (None,None,None,None,"Nelson, Izaiyah","Out","Injury/Illness - Left Ankle Injury Recovery",None),
 (None,None,None,None,"Penda, Noah","Out","Injury/Illness - Right Partially Torn Hamstring",None),
 (None,None,None,"Boston Celtics",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,"07:30 (ET)","HOU@MIA","Houston Rockets",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"Miami Heat","Goldin, Vladislav","Out","G League - Two-Way",None),
 (None,None,None,None,"Larsson, Pelle","Questionable","Injury/Illness - Illness",None),
 (None,None,None,None,"Thompson, Klay","Available","Injury/Illness - Left Ankle Sprain",None),
 (None,"07:30 (ET)","PHI@BKN","Philadelphia 76ers",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"Brooklyn Nets","Bilodeau, Tyler","Out","G League - Two-Way",None),
 (None,None,None,None,"Jefferson, Joshua","Out","G League - On Assignment",None),
 (None,None,None,None,"Nelson, Grant","Out","G League - Two-Way",None),
 (None,None,None,None,"Powell, Drake","Out","G League - On Assignment",None),
 (None,None,None,None,"Saraf, Ben","Out","G League - On Assignment",None),
 (None,"08:00 (ET)","GSW@NOP","Golden State Warriors","Butler III, Jimmy",None,None,
  "PDF text layer lost the status/reason column boundary for this row: the only trailing text printed was 'Injury/Illness - Right ACL Repair / Surgery', which is a reason, not a status. Status and reason are left null and the row is flagged rather than guessed."),
 (None,None,None,None,"Curry, Stephen","Out",None,"the PDF printed the status but not the reason for this row; reason left null rather than inferred"),
 (None,None,None,None,"Moody, Moses","Out",None,"the PDF printed the status but not the reason for this row; reason left null rather than inferred"),
 (None,None,None,None,"Porzingis, Kristaps","Out",None,"the PDF printed the status but not the reason for this row; reason left null rather than inferred"),
 (None,None,None,None,"Santos, Gui","Questionable",None,"the PDF printed the status but not the reason for this row; reason left null rather than inferred"),
 (None,None,None,None,"Williams, Brandon","Out",None,"the PDF printed the status but not the reason for this row; reason left null rather than inferred"),
 (None,None,None,"New Orleans Pelicans","Dia, Malik","Questionable","G League - Two-Way",None),
 (None,None,None,None,"Mathurin, Bennedict","Out","Injury/Illness - Left Plantar Fasciitis",None),
 (None,None,None,None,"McGowens, Bryce","Out","Injury/Illness - Left Elbow Infection",None),
 (None,None,None,None,"Murphy III, Trey","Out","Injury/Illness - Bilateral Patellar Tendinopathy",None),
 (None,None,None,None,"Murray, Dejounte","Out","Injury/Illness - Left Ankle Sprain",None),
 (None,None,None,None,"Pierre Jr., Jaron","Questionable","G League - Two-Way",None),
 (None,None,None,None,"Reese, Julian","Questionable","G League - Two-Way",None),
 (None,None,None,None,"Watford, Trendon","Out","Injury/Illness - Right Ankle Sprain",None),
 (None,None,"POR@MIN","Portland Trail Blazers","Krejci, Vit","Out","Injury/Illness - Left Ankle Fracture",None),
 (None,None,None,None,"Morant, Ja","Out","Injury/Illness - Left Hamstring Strain",None),
 (None,None,None,None,"Sharpe, Shaedon","Out","Injury/Illness - Right Knee Surgery",None),
 (None,None,None,None,"Youngblood, Chris","Out","Injury/Illness - Right Heel Contusion / Bone Bruise",None),
 (None,None,None,"Minnesota Timberwolves","Beringer, Joan","Available","Injury/Illness - Face Mask",None),
 (None,None,None,None,"Clark, Jaylen","Out","Injury/Illness - Right Hamstring Strain",None),
 (None,None,None,None,"DiVincenzo, Donte","Out","Injury/Illness - Right Achilles Tendon Repair / Surgery",None),
 (None,None,None,None,"Edwards, Anthony","Out","Injury/Illness - Right Knee Arthroscopy",None),
 (None,"09:00 (ET)","PHX@DEN","Phoenix Suns",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"Denver Nuggets","Holmes II, DaRon","Out","G League - On Assignment",None),
 (None,None,None,None,"Nembhard, Ryan","Out","G League - Two-Way",None),
 (None,None,None,None,"Strawther, Julian","Out","Injury/Illness - Left Knee Sprain",None),
 (None,None,None,None,"Whitmore, Cam","Out","G League - Two-Way",None),
 ("11/17/2026","07:30 (ET)","NYK@TOR","New York Knicks",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"Toronto Raptors",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,"08:00 (ET)","DET@SAS","Detroit Pistons",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"San Antonio Spurs",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,"POR@MIN","Portland Trail Blazers",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED (11/17 game)"),
 (None,None,None,"Minnesota Timberwolves",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED (11/17 game)"),
 (None,"10:30 (ET)","UTA@LAC","Utah Jazz",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"LA Clippers",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,"11:00 (ET)","CHA@LAL","Charlotte Hornets",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
 (None,None,None,"Los Angeles Lakers",None,"NOT YET SUBMITTED",None,"team-level NOT YET SUBMITTED"),
]

INJ_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-16_09_30AM.pdf"
INJ_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"
PREV_FILE = "data/official/injury_2026-11-15_0900PM_dfef26dc.json"


def w(rel, doc):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", rel)


def wl(rec):
    return int(rec.split("-")[0])


def ll(rec):
    return int(rec.split("-")[1])


def build_standings():
    rows = []
    for conf, tbl in (("East", EAST), ("West", WEST)):
        for i, (ab, W, L, pct, gb, confrec, div, home, road, neu, ot, l10, strk) in enumerate(tbl, 1):
            rows.append({"conference": conf, "rank": i, "abbr": ab, "team": NAMES[ab],
                         "w": W, "l": L,
                         "win_pct": pct, "gb": gb, "conf_rec": confrec, "div_rec": div,
                         "home": home, "road": road, "neutral": neu, "ot": ot,
                         "last10": l10, "streak": strk})
    missing = sorted({r["abbr"] for r in rows} - set(NAMES))
    if missing:
        problems.append("no official name transcribed for %s" % ", ".join(missing))
    hw = sum(wl(r["home"]) for r in rows)
    hg = sum(wl(r["home"]) + ll(r["home"]) for r in rows)
    rw = sum(wl(r["road"]) for r in rows)
    rg = sum(wl(r["road"]) + ll(r["road"]) for r in rows)
    nw = sum(wl(r["neutral"]) for r in rows)
    ng = sum(wl(r["neutral"]) + ll(r["neutral"]) for r in rows)
    tot_w = sum(r["w"] for r in rows)
    tot_l = sum(r["l"] for r in rows)
    problems = []
    if hg != rg:
        problems.append(f"home games {hg} != road games {rg}")
    if tot_w != tot_l:
        problems.append(f"league wins {tot_w} != league losses {tot_l}")
    if hw + rw + nw != tot_w:
        problems.append(f"home {hw} + road {rw} + neutral {nw} wins != {tot_w} total wins")
    if hg + ng + rg != tot_w + tot_l:
        problems.append("team-game counts do not reconcile")
    doc = {
        "title": "NBA 2026-27 regular-season standings, read 2026-11-16T14:44Z",
        "captured_by": SESSION,
        "retrieved_utc": RETRIEVED,
        "source_url": STANDINGS_URL,
        "team_names_reread_utc": NAMES_REREAD_UTC,
        "rule": ("Every cell is a cell of the official standings table, read "
                 "conference by conference. Nothing is computed from it except the "
                 "sums published in measured_home_court_anchor, which are arithmetic "
                 "on those cells and are reconciled three ways below."),
        "rows": rows,
        "measured_home_court_anchor": {
            "home_win_rate": round(hw / hg, 4) if hg else None,
            "road_win_rate": round(rw / rg, 4) if rg else None,
            "home_games": hg, "home_wins": hw,
            "road_games": rg, "road_wins": rw,
            "neutral_games": ng, "neutral_wins": nw,
            "total_wins": tot_w, "total_losses": tot_l,
            "reconciliation": [
                f"home games {hg} == road games {rg}",
                f"league wins {tot_w} == league losses {tot_l}",
                f"home {hw} + road {rw} + neutral {nw} wins == {tot_w} total wins",
                f"home win rate {hw}/{hg} + road win rate {rw}/{rg} = "
                f"{round(hw/hg + rw/rg, 6)} (must be 1.0 when neutral games are excluded)",
            ],
            "home_losses": hg - hw,
            "road_losses": rg - rw,
            "neutral_team_games": ng,
            "measured_from": ("the official standings HOME and ROAD columns, summed "
                              "across all 30 teams"),
            "cross_checks": [
                f"home_wins({hw}) must equal road_losses({rg - rw}): "
                f"{'OK' if hw == rg - rw else 'MISMATCH'}",
                f"road_wins({rw}) must equal home_losses({hg - hw}): "
                f"{'OK' if rw == hg - hw else 'MISMATCH'}",
            ],
            "source_url": STANDINGS_URL,
            "retrieved_utc": RETRIEVED,
            "caveat": ("every game completed at retrieval time is included. The 11/16 "
                       "slate had not tipped (first tip 7:00 PM ET = 2026-11-17T00:00Z), "
                       "so this is the complete standings through the games of "
                       "2026-11-15 - including the three 11/15 games that were still "
                       "in progress when the previous capture was taken at 02:13Z."),
            "note": ("this is the measurement home-court advantage is pinned to "
                     "(brief requirement: pin HCA to the measured home-win rate, "
                     "do not fit it)"),
        },
        "problems": problems,
    }
    return doc, (hw, hg, rw, rg, tot_w, tot_l)


def build_injury():
    rows, gd, gt, mu, tm = [], None, None, None, None
    inherited = 0
    for (d, t, m, team, player, status, reason, note) in INJ:
        gd = d or gd
        gt = t or gt
        mu = m or mu
        tm = team or tm
        inh = any(x is None for x in (d, t, m, team))
        if inh:
            inherited += 1
        rows.append({
            "game_date": gd, "game_time": gt, "matchup": mu, "team": tm,
            "team_effective": tm, "player": player, "status": status,
            "reason": reason,
            "inherited": inh,
            "parse_note": note,
            "source_url": INJ_URL,
            "edition_revision_et": "11/16/2026 09:30 AM ET (printed on the PDF as "
                                   "'Injury Report: 11/16/26 09:30 AM')",
        })
    player_rows = [r for r in rows if r["player"]]
    nys = [r for r in rows if r["status"] == "NOT YET SUBMITTED"]
    flagged = [r for r in rows if r["status"] is None or (r["player"] and r["reason"] is None)]
    txt = json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
    doc = {
        "edition": "2026-11-16 09:30 AM",
        "edition_file": "injury_2026-11-16_0930AM_acc2fd9e.json",
        "revision_time_et": "11/16/2026 09:30 AM ET (printed on the PDF as "
                            "'Injury Report: 11/16/26 09:30 AM')",
        "revision_time_utc": "2026-11-16T14:30Z",
        "retrieved_utc": RETRIEVED,
        "captured_by": SESSION,
        "source_url": INJ_URL,
        "index_url": INJ_INDEX,
        "index_note": ("newest edition listed on the official injury-report index at "
                       "retrieval time: the index for 16 November ran 12:00 AM through "
                       "09:30 AM ET, and 09:30 AM was the last entry"),
        "submission_rule_quoted": ("By 5 p.m. local time the day before a game (other "
                                   "than the second day of a back-to-back), teams must "
                                   "designate a participation status and identify a "
                                   "specific injury, illness, other medical condition, or "
                                   "other reason for any player whose participation in the "
                                   "game may be affected for any reason. For the second game "
                                   "of a back-to-back, teams must report by 1 p.m. local time "
                                   "on the day of the game. Teams are also required to submit "
                                   "a game-day injury report between 11 a.m. and 1 p.m. local "
                                   "time (and between 8 and 10 a.m. for tip-offs 5 p.m. or "
                                   "earlier) on game days."),
        "submission_rule_url": INJ_INDEX,
        "merged_cell_caveat": ("the PDF merges the Game Date, Game Time, Matchup and Team "
                               "cells across rows; for those rows the value is inherited "
                               "from the preceding printed value and the row is marked "
                               "inherited=true"),
        "rows_note": (f"{len(rows)} rows transcribed from the official PDF "
                      f"({len(player_rows)} player rows, {len(nys)} team-level "
                      f"NOT YET SUBMITTED blocks). Six Golden State rows and one more "
                      f"lost a status or reason cell in the PDF text layer; those cells "
                      f"are null and each row carries a parse_note."),
        "game_dates_present": sorted({r["game_date"] for r in rows}),
        "rows": rows,
    }
    ed = {
        "edition_id": "2026-11-16_0930AM",
        "revision": "2026-11-16 09:30 AM ET",
        "edition_published_utc": "2026-11-16T14:30Z",
        "retrieved_utc": RETRIEVED,
        "retrieval_window_utc": {
            "earliest_possible_utc": "2026-11-16T14:30Z",
            "latest_possible_utc": "2026-11-16T14:52Z",
            "basis": ("the edition is stamped 09:30 AM ET = 14:30Z; the session read it "
                      "at 14:44-14:52Z"),
        },
        "source_url": INJ_URL,
        "edition_index_url": INJ_INDEX,
        "captured_by": SESSION,
        "capture_method": ("Read live through the web-fetch channel. Rows transcribed "
                           "verbatim in report order."),
        "binary_pdf_stored": False,
        "binary_pdf_note": ("The PDF bytes could not be archived in this sandbox: the "
                            "only network route to ak-static.cms.nba.com is the "
                            "text-extraction fetch channel. The edition is archived as a "
                            "verbatim row transcription with the official URL and revision "
                            "stamp on every row; the SHA-256 below is of the transcribed "
                            "row text, not of the PDF bytes."),
        "rows_sha256": hashlib.sha256(txt).hexdigest(),
        "row_counts": {
            "rows_total": len(rows),
            "player_rows": len(player_rows),
            "not_yet_submitted_blocks": len(nys),
            "rows_with_inherited_team": inherited,
            "rows_with_a_null_cell_left_null_on_purpose": len(flagged),
        },
        "game_dates_in_edition": sorted({r["game_date"] for r in rows}),
    }
    return doc, ed, rows


def build_diff(rows):
    prev = json.load(open(os.path.join(ROOT, PREV_FILE), encoding="utf-8"))
    prow_all = prev["rows"]

    # The two editions cover different windows of game dates: the previous one
    # ran 11/15 + 11/16, this one runs 11/16 + 11/17. Comparing a player whose
    # 11/15 game is over against a report that no longer lists 11/15 would
    # manufacture "removals" that mean nothing. The comparison is therefore
    # restricted to the game dates BOTH editions cover, and the rest are counted
    # separately as window movement.
    cur_dates = {r["game_date"] for r in rows}
    prev_dates = {r.get("game_date") for r in prow_all}
    shared = sorted(cur_dates & prev_dates)
    only_prev = sorted(prev_dates - cur_dates)
    only_cur = sorted(cur_dates - prev_dates)

    prow = [r for r in prow_all if r.get("game_date") in shared]
    crows = [r for r in rows if r["game_date"] in shared]

    def key(r):
        # Normalise: the previous edition stores an empty player cell as "" and
        # this session stores it as null; both mean "no player row", and treating
        # them as different would manufacture five fake add/remove pairs.
        pl = r.get("player")
        pl = pl.strip() if isinstance(pl, str) else pl
        return (r.get("game_date"), r.get("matchup"),
                r.get("team_effective") or r.get("team"), pl or None)

    pmap = {}
    for r in prow:
        pmap.setdefault(key(r), []).append(r)
    cmap = {}
    for r in crows:
        cmap.setdefault(key(r), []).append(r)

    status_changes, added, removed = [], [], []
    unchanged, not_comparable = 0, []
    for k, crs in cmap.items():
        prs = pmap.get(k)
        if not prs:
            for r in crs:
                added.append({"game_date": k[0], "matchup": k[1], "team": k[2],
                              "player": k[3], "status": r["status"],
                              "reason": r["reason"]})
            continue
        for c, p in zip(crs, prs):
            cs, ps = c.get("status"), p.get("status")
            if cs is None:
                # The PDF text layer lost this row's status in the current
                # edition. Comparing it against the previous status would invent
                # a change that did not happen, so it is reported apart.
                not_comparable.append({
                    "matchup": k[1], "team": k[2], "player": k[3],
                    "previous_status": ps, "current_status": None,
                    "why": c.get("parse_note") or "current status not printed",
                })
                continue
            if ps != cs:
                status_changes.append({
                    "game_date": k[0], "matchup": k[1], "team": k[2], "player": k[3],
                    "previous_status": ps, "current_status": cs,
                    "previous_edition": prev["edition"],
                    "current_edition": "2026-11-16 09:30 AM",
                    "reason": c.get("reason") or p.get("reason"),
                    "source_previous": prev["source_url"], "source_current": INJ_URL,
                })
            else:
                unchanged += 1
    for k, prs in pmap.items():
        if k not in cmap:
            for r in prs:
                removed.append({"game_date": k[0], "matchup": k[1], "team": k[2],
                                "player": k[3], "status": r.get("status")})

    nys_now = sorted({(r["matchup"], r["team_effective"]) for r in rows
                      if r["status"] == "NOT YET SUBMITTED"})
    nys_prev = sorted({(r.get("matchup"), r.get("team_effective") or r.get("team"))
                       for r in prow_all if r.get("status") == "NOT YET SUBMITTED"})
    return {
        "title": "Injury-report status diff \u2014 2026-11-15 09:00 PM ET \u2192 2026-11-16 09:30 AM ET",
        "diffed_by": SESSION,
        "diffed_at_utc": RETRIEVED,
        "previous_edition": {"edition": prev["edition"], "source_url": prev["source_url"],
                             "file": PREV_FILE, "game_dates": sorted(prev_dates)},
        "current_edition": {"edition": "2026-11-16 09:30 AM", "source_url": INJ_URL,
                            "file": "data/official/injury_2026-11-16_0930AM_acc2fd9e.json",
                            "game_dates": sorted(cur_dates)},
        "rule": ("a status change is recorded only when the same (game date, matchup, "
                 "team, player) prints a different Current Status in the two editions. "
                 "A player who appears in one edition and not the other is listed as "
                 "added/removed, not as a status change. A row whose status the PDF "
                 "text layer lost in the current edition is reported under "
                 "not_comparable and is never counted as a change."),
        "comparison_window": {
            "game_dates_compared": shared,
            "game_dates_only_in_previous": only_prev,
            "game_dates_only_in_current": only_cur,
            "why": ("the report is a rolling document: it lists the next two game "
                    "dates. Comparing dates only one edition covers would report "
                    "every finished game as a removal."),
        },
        "status_changes": status_changes,
        "status_changes_count": len(status_changes),
        "not_comparable": not_comparable,
        "not_comparable_count": len(not_comparable),
        "added": added, "added_count": len(added),
        "removed": removed, "removed_count": len(removed),
        "unchanged_rows": unchanged,
        "not_yet_submitted_previous": [{"matchup": a, "team": b} for a, b in nys_prev],
        "not_yet_submitted_current": [{"matchup": a, "team": b} for a, b in nys_now],
        "not_yet_submitted_resolved": [{"matchup": a, "team": b} for a, b in nys_prev
                                       if (a, b) not in nys_now],
        "not_yet_submitted_new": [{"matchup": a, "team": b} for a, b in nys_now
                                  if (a, b) not in nys_prev],
    }


def main():
    std, sm = build_standings()
    w("data/official/standings_2026-11-16_1445Z_acc2fd9e.json", std)
    print(f"  standings: {len(std['rows'])} rows; home {sm[0]}/{sm[1]} = "
          f"{std['measured_home_court_anchor']['home_win_rate']}; "
          f"road {sm[2]}/{sm[3]}; W/L {sm[4]}/{sm[5]}")
    if std["problems"]:
        print("  PROBLEMS:", "; ".join(std["problems"]))
        return 1

    doc, ed, rows = build_injury()
    w("data/official/injury_2026-11-16_0930AM_acc2fd9e.json", doc)
    w("data/injury_reports/2026-11-16_0930AM/edition.json", ed)
    w("data/injury_reports/2026-11-16_0930AM/rows.json", rows)
    diff = build_diff(rows)
    w("data/injury_reports/2026-11-16_0930AM/diff_vs_2026-11-15_0900PM.json", diff)
    print(f"  injury: {len(rows)} rows, {ed['row_counts']['player_rows']} player rows, "
          f"{ed['row_counts']['not_yet_submitted_blocks']} NOT YET SUBMITTED")
    print(f"  diff: {diff['status_changes_count']} status changes, "
          f"{diff['added_count']} added, {diff['removed_count']} removed, "
          f"{diff['unchanged_rows']} unchanged")
    for c in diff["status_changes"]:
        print("    CHANGED", c["matchup"], c["team"], c["player"],
              c["previous_status"], "->", c["current_status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
