#!/usr/bin/env python3
"""Injury-report edition capture + consecutive-report diff (session arena/c348e6c7).

    python3 verify/2026-11-16-c348e6c7/capture_injury.py

WHAT IT CAPTURES
----------------
The newest official injury edition at the time of this pass:
    Injury-Report_2026-11-15_09_00PM.pdf          revision stamp "11/15/26 09:00 PM"
    https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf
    index: https://official.nba.com/nba-injury-report-2026-27-season/

The index was read first and 09:00 PM was the LAST edition it listed for 11/15,
so this is the newest report the league had published.

WHAT IT CANNOT DO, STATED PLAINLY
---------------------------------
The brief asks for "every injury PDF with its timestamp". This session's sandbox
cannot fetch binary files: outbound network is restricted to github.com, pypi and
npm, and `curl` to ak-static.cms.nba.com fails at the TLS handshake (measured:
"OpenSSL SSL_connect: SSL_ERROR_SYSCALL", HTTP 000, 0 bytes). The agent-side
fetcher reaches the PDF but returns parsed text, so **no SHA-256 of the original
bytes can be recorded and no byte-identical copy can be archived**. What is
archived instead is the full row transcription with:
    * the edition stamp the PDF prints,
    * the exact source URL,
    * the UTC retrieval time,
    * the row count the PDF printed.
That is recorded as flag F-c348-1 rather than papered over.

SCOPE OF THE DIFF
-----------------
Rows are transcribed for the games in the live horizon window (11/16) because
those are the rows the picks page consumes. The 11/15 rows in the same edition
belong to games that have already tipped and are not re-transcribed here.
"""

from __future__ import annotations

import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

EDITION = "2026-11-15_09_00PM"
REVISION_TIME_ET = "11/15/2026 09:00 PM"
PDF_URL = ("https://ak-static.cms.nba.com/referee/injury/"
           "Injury-Report_2026-11-15_09_00PM.pdf")
INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
RETRIEVED_UTC = "2026-11-16T02:31Z..02:36Z"
RETRIEVED_ET = "2026-11-15 21:31..21:36 ET"
CAPTURED_BY = "arena/c348e6c7-nba1"

# ---------------------------------------------------------------------------
# Rows for the 11/16 games, transcribed verbatim from the PDF.
# The PDF prints one row per player; a team that has not filed yet prints a
# single row with an empty player cell and status "NOT YET SUBMITTED".
# Merged cells in the PDF mean game_date / game_time / matchup are printed only
# on the first row of a block - the same caveat the repository already records
# for every other edition.
# ---------------------------------------------------------------------------
# (game_date, game_time_et, matchup, team_printed, player, status, reason)
ROWS_11_16 = [
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls",       "Awaka, Tobe",        "Out",          "Injury/Illness - Disc Irritation"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls",       "Robinson, Orlando",  "Out",          "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls",       "Sellers, Jaylin",    "Out",          "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls",       "Smith, Jalen",       "Questionable", "Injury/Illness - Left Finger Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Chicago Bulls",       "Wilson, Caleb",      "Out",          "Injury/Illness - Right Metacarpal Fracture"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Diop, Khalifa",      "Out",          "G League - On Assignment"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Merrill, Sam",       "Out",          "Injury/Illness - Right Elbow Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Mobley, Evan",       "Out",          "Injury/Illness - Left Great Toe Sprain"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Tomlin, Nae'Qwan",   "Out",          "Injury/Illness - Low Back Stress Reaction"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Tyson, Jaylon",      "Questionable", "Injury/Illness - Right Ankle Injury Management"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Udeh, Jr., Ernest",  "Out",          "G League - Two-Way"),
    ("11/16/2026", "07:00 (ET)", "CHI@CLE", "Cleveland Cavaliers", "Watson, Peyton",     "Questionable", "Injury/Illness - Right Abdominal Soreness"),

    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Edey, Zach",         "Questionable", "Injury/Illness - Left Ankle Injury Management"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Jackson, GG",        "Out",          "Injury/Illness - Left Foot Injury"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Jerome, Ty",         "Out",          "Injury/Illness - Right Hip Soreness"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Pippen Jr., Scotty", "Out",          "Injury/Illness - Lumbar Disc Herniation"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Post, Quinten",      "Questionable", "Injury/Illness - Concussion Protocol"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Saunders, Richie",   "Out",          "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Memphis Grizzlies",   "Stewart, Isaiah",    "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", "07:00 (ET)", "MEM@WAS", "Washington Wizards",  None,                 "NOT YET SUBMITTED", None),

    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic",       "Banchero, Paolo",    "Out",          "Injury/Illness - Right High Ankle Sprain"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic",       "Isaac, Jonathan",    "Out",          "Injury/Illness - Left Knee Injury Management"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic",       "Nelson, Izaiyah",    "Out",          "Injury/Illness - Left Ankle Injury Recovery"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Orlando Magic",       "Penda, Noah",        "Out",          "Injury/Illness - Right Partially Torn Hamstring"),
    ("11/16/2026", "07:00 (ET)", "ORL@BOS", "Boston Celtics",      None,                 "NOT YET SUBMITTED", None),

    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Houston Rockets",     None,                 "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat",          "Goldin, Vladislav",  "Out",          "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat",          "Larsson, Pelle",     "Questionable", "Injury/Illness - Illness"),
    ("11/16/2026", "07:30 (ET)", "HOU@MIA", "Miami Heat",          "Thompson, Klay",     "Available",    "Injury/Illness - Left Ankle Sprain"),

    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Philadelphia 76ers",  None,                 "NOT YET SUBMITTED", None),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets",       "Bilodeau, Tyler",    "Out",          "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets",       "Jefferson, Joshua",  "Out",          "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets",       "Nelson, Grant",      "Out",          "G League - Two-Way"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets",       "Powell, Drake",      "Out",          "G League - On Assignment"),
    ("11/16/2026", "07:30 (ET)", "PHI@BKN", "Brooklyn Nets",       "Saraf, Ben",         "Out",          "G League - On Assignment"),

    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Butler III, Jimmy", "Out",          "Injury/Illness - Right ACL Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Curry, Stephen",   "Out",          "Injury/Illness - Right Oblique Tear"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Moody, Moses",     "Out",          "Injury/Illness - Left Patellar Tendon Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Porzingis, Kristaps", "Out",       "Not With Team"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Santos, Gui",      "Questionable", "Injury/Illness - Right Ankle Inflammation"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "Golden State Warriors", "Williams, Brandon","Out",          "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Dia, Malik",        "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Mathurin, Bennedict", "Out",        "Injury/Illness - Left Plantar Fasciitis"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "McGowens, Bryce",   "Out",          "Injury/Illness - Left Elbow Infection"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Murphy III, Trey",  "Out",          "Injury/Illness - Bilateral Patellar Tendinopathy"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Murray, Dejounte",  "Out",          "Injury/Illness - Left Ankle Sprain"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Pierre Jr., Jaron", "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Reese, Julian",     "Questionable", "G League - Two-Way"),
    ("11/16/2026", "08:00 (ET)", "GSW@NOP", "New Orleans Pelicans", "Watford, Trendon",  "Out",          "Injury/Illness - Right Ankle Sprain"),

    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Krejci, Vit",     "Out",          "Injury/Illness - Left Ankle Fracture"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Morant, Ja",      "Out",          "Injury/Illness - Left Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Sharpe, Shaedon", "Out",          "Injury/Illness - Right Knee Surgery"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Portland Trail Blazers", "Youngblood, Chris", "Out",        "Injury/Illness - Right Heel Contusion / Bone Bruise"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Beringer, Joan",  "Available",    "Injury/Illness - Face Mask"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Clark, Jaylen",   "Out",          "Injury/Illness - Right Hamstring Strain"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "DiVincenzo, Donte", "Out",        "Injury/Illness - Right Achilles Tendon Repair / Surgery"),
    ("11/16/2026", "08:00 (ET)", "POR@MIN", "Minnesota Timberwolves", "Edwards, Anthony","Out",          "Injury/Illness - Right Knee Arthroscopy"),

    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Phoenix Suns",        None,                 "NOT YET SUBMITTED", None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets",      "Holmes II, DaRon",   "Out",          None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets",      "Nembhard, Ryan",     "Out",          None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets",      "Strawther, Julian",  "Out",          None),
    ("11/16/2026", "09:00 (ET)", "PHX@DEN", "Denver Nuggets",      "Whitmore, Cam",      "Out",          None),
]

# Denver's four rows print a status but no reason: the PDF's trailing block had
# the reason column empty. Recorded as printed, not filled in.
DENVER_REASON_NOTE = (
    "The four DEN rows in the 09:00 PM edition print a status ('Out') with an "
    "empty reason cell - the PDF's final block is truncated at the page break. "
    "The reason is recorded as null, not guessed."
)


def build_rows():
    out = []
    for (gd, gt, mu, team, player, status, reason) in ROWS_11_16:
        out.append({
            "game_date": gd,
            "game_time_et": gt,
            "matchup": mu,
            "team_printed": team,
            "team_effective": team,
            "team_inherited": False,
            "player": player,
            "status": status,
            "reason": reason,
            "source_url": PDF_URL,
        })
    return out


def norm(s):
    return (s or "").strip().lower()


def diff(prev_rows, cur_rows):
    """Status changes between two consecutive editions, keyed (matchup, player)."""
    def key(r):
        return (norm(r.get("matchup")), norm(r.get("player")))
    prev = {}
    for r in prev_rows:
        k = key(r)
        prev.setdefault(k, r)
    cur = {}
    for r in cur_rows:
        k = key(r)
        cur.setdefault(k, r)

    changes, added, removed, same = [], [], [], 0
    for k, r in cur.items():
        p = prev.get(k)
        if p is None:
            # A player row with no name is a team-level NOT YET SUBMITTED marker;
            # it is only "new" if that team filed nothing at all before.
            if not r.get("player"):
                continue
            added.append({"matchup": r.get("matchup"), "player": r.get("player"),
                          "team": r.get("team_printed"), "status": r.get("status"),
                          "reason": r.get("reason")})
        elif norm(p.get("status")) != norm(r.get("status")):
            changes.append({
                "matchup": r.get("matchup"),
                "team": r.get("team_printed"),
                "player": r.get("player"),
                "from_status": p.get("status"),
                "to_status": r.get("status"),
                "reason": r.get("reason"),
                "prev_edition": PREV_EDITION,
                "cur_edition": EDITION,
            })
        else:
            same += 1

    for k, r in prev.items():
        if k not in cur:
            removed.append({"matchup": r.get("matchup"), "player": r.get("player"),
                            "team": r.get("team_printed"), "status": r.get("status")})

    # Team-level submission tracking. A player-keyed diff misses the single most
    # consequential kind of change: a team that had filed NOTHING ("NOT YET
    # SUBMITTED") filing a real report. That is exactly the gap §42 flagged - the
    # model was cut from an edition in which a whole team's participation status
    # did not exist. Compare (matchup, team) submission state explicitly.
    def team_state(rows_):
        st = {}
        for r in rows_:
            k = (norm(r.get("matchup")), norm(r.get("team_printed")))
            is_marker = ("NOT YET SUBMITTED" in (r.get("status") or "").upper()
                         or "NOT YET SUBMITTED" in (r.get("reason") or "").upper())
            if r.get("player") and not is_marker:
                st.setdefault(k, {"filed": True, "players": []})
                st[k]["players"].append((r.get("player"), r.get("status")))
            else:
                st.setdefault(k, {"filed": False, "players": []})
        return st

    tp, tc = team_state(prev_rows), team_state(cur_rows)
    submission_changes = []
    # Ignore inherited-name artefacts when deciding whether a team filed: a
    # NOT YET SUBMITTED row with a player name is NOT a filing.
    for k in sorted(set(tp) | set(tc)):
        a, b = tp.get(k), tc.get(k)
        if a is None or b is None:
            continue
        if a["filed"] != b["filed"]:
            submission_changes.append({
                "matchup": k[0].upper(),
                "team": k[1],
                "from": "filed" if a["filed"] else "NOT YET SUBMITTED",
                "to": "filed" if b["filed"] else "NOT YET SUBMITTED",
                "players_now_listed": len(b["players"]),
                "outright_outs_now": sum(1 for _, s in b["players"]
                                         if norm(s) == "out"),
            })
    still_not_submitted = [
        {"matchup": k[0].upper(), "team": k[1]}
        for k, v in tc.items() if not v["filed"]
    ]

    return {
        "prev_edition": PREV_EDITION,
        "prev_source_url": PREV_PDF,
        "cur_edition": EDITION,
        "cur_source_url": PDF_URL,
        "diff_generated_utc": datetime.datetime.now(datetime.timezone.utc)
                                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_prev_11_16": len(prev_rows),
        "rows_cur_11_16": len(cur_rows),
        "players_unchanged": same,
        "status_changes": changes,
        "team_submission_changes": submission_changes,
        "teams_still_not_submitted_in_current": still_not_submitted,
        "rows_only_in_current": added,
        "rows_only_in_previous": removed,
        "inherited_name_rows_in_prev": find_inherited_name_rows(prev_rows, PREV_EDITION),
        "inherited_name_rows_in_cur": find_inherited_name_rows(cur_rows, EDITION),
        "verdict": (
            f"{len(changes)} player status change(s), "
            f"{len(submission_changes)} team submission change(s), "
            f"{len(added)} row(s) only in the newer edition, "
            f"{len(removed)} row(s) only in the older one"
        ),
    }


def find_inherited_name_rows(rows_, edition):
    """A 'NOT YET SUBMITTED' row is a TEAM-level marker: the league prints no
    player on it. If such a row carries a player name, that name was inherited
    from the previous row during transcription and the row must not be counted
    as a filed player. This is the merged-cell hazard the repository already
    documents; here it is detected rather than assumed away."""
    bad = []
    for r in rows_:
        status = (r.get("status") or "")
        reason = (r.get("reason") or "")
        marker = ("NOT YET SUBMITTED" in status.upper()
                  or "NOT YET SUBMITTED" in reason.upper())
        if marker and r.get("player"):
            enc = ("status" if "NOT YET SUBMITTED" in status.upper() else "reason")
            bad.append({
                "edition": edition,
                "matchup": r.get("matchup"),
                "team": r.get("team_printed"),
                "inherited_player": r.get("player"),
                "status_field": status,
                "reason_field": reason,
                "marker_in_field": enc,
                "why_suspect": (
                    "NOT YET SUBMITTED is a TEAM-level marker and the league "
                    "prints no player on that row; a player name here was "
                    "inherited from the previous row during transcription."
                ),
                "consumer_hazard": (
                    "This row is encoded status='Out'. A consumer that reads the "
                    "status column alone will count a player who was never named "
                    "as ruled out for a team that had filed nothing."
                ) if status.strip().lower() == "out" else None,
            })
    return bad


PREV_EDITION = "2026-11-15_0615PM"
PREV_PDF = ("https://ak-static.cms.nba.com/referee/injury/"
            "Injury-Report_2026-11-15_06_15PM.pdf")


def main():
    rows = build_rows()

    edition = {
        "title": "Official NBA injury report edition (LIVE READ)",
        "edition": EDITION,
        "edition_file": f"Injury-Report_{EDITION[:10]}_{EDITION[11:]}.pdf",
        "revision_time_et": REVISION_TIME_ET,
        "retrieved_utc": RETRIEVED_UTC,
        "retrieved_et": RETRIEVED_ET,
        "captured_by": CAPTURED_BY,
        "source_url": PDF_URL,
        "index_url": INDEX_URL,
        "index_note": (
            "The index was read first and 09:00 PM was the last edition it listed "
            "for 11/15, so this is the newest report the league had published at "
            "retrieval time."
        ),
        "submission_rule_quoted": (
            "Teams must report by 5 p.m. local time the day before a game (other "
            "than the second day of a back-to-back); for the second game of a "
            "back-to-back, by 1 p.m. local time on the day of the game."
        ),
        "submission_rule_url": INDEX_URL,
        "merged_cell_caveat": (
            "The PDF prints game_date / game_time / matchup / team only on the "
            "first row of each block; continuation rows carry blanks. Rows are "
            "transcribed as printed."
        ),
        "not_read_notes": [
            DENVER_REASON_NOTE,
            "Rows for 11/15 games in this same edition were NOT transcribed: they "
            "belong to games that have already tipped and are outside the live "
            "horizon window.",
        ],
        "binary_archive_gap": (
            "FLAG F-c348-1: the original PDF bytes could not be archived. The "
            "sandbox has no outbound network (curl to ak-static.cms.nba.com fails "
            "at TLS handshake, HTTP 000) and the agent-side fetcher returns parsed "
            "text only, so no SHA-256 of the PDF and no byte-identical copy exist. "
            "The edition stamp, exact URL, retrieval time and full row "
            "transcription are recorded instead."
        ),
        "rows": rows,
    }
    json.dump(edition, open(os.path.join(HERE, "injury_2026-11-15_0900PM.json"), "w"), indent=1)

    prev_path = os.path.join(ROOT, "data", "official", f"injury_{PREV_EDITION}.json")
    if os.path.exists(prev_path):
        prev = json.load(open(prev_path))
        prev_rows = [r for r in prev.get("rows", []) if r.get("game_date") == "11/16/2026"]
        d = diff(prev_rows, rows)
    else:
        d = {"status": "previous edition not found", "path": prev_path}
    json.dump(d, open(os.path.join(HERE, "injury_diff_0615PM_to_0900PM.json"), "w"), indent=1)

    print(f"edition rows (11/16 games): {len(rows)}")
    print("diff:", d.get("verdict", d.get("status")))
    for c in d.get("status_changes", []):
        print(f"  CHANGE {c['matchup']} {c['player']}: {c['from_status']} -> {c['to_status']}")
    for a in d.get("rows_only_in_current", []):
        print(f"  NEW    {a['matchup']} {a['player']}: {a['status']}")
    for a in d.get("rows_only_in_previous", []):
        print(f"  GONE   {a['matchup']} {a['player']}: {a['status']}")


if __name__ == "__main__":
    main()
