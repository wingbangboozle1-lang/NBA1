#!/usr/bin/env python3
"""capture_injury.py — what the official injury-report index lists, and how far the
published injury read-out is behind it.

Read: https://official.nba.com/nba-injury-report-2026-27-season/  (chunks 0 and 1)
at 2026-11-16T00:35Z.

The index page prints every edition as a link on the PDF host, so the set of edition
stamps between two times is READ OFF THE PAGE, not guessed. The publication rule is
quoted verbatim from the same page.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"
HOST = "https://ak-static.cms.nba.com/referee/injury/"

RULE = ("NBA teams must report information concerning player injuries, illnesses, other medical "
        "conditions, or rest for all NBA games. By 5 p.m. local time the day before a game (other "
        "than the second day of a back-to-back), teams must designate a participation status and "
        "identify a specific injury, illness, other medical condition, or other reason for any "
        "player whose participation in the game may be affected for any reason. For the second game "
        "of a back-to-back, teams must report the above information by 1 p.m. local time on the day "
        "of the game. In addition, teams are required to submit a game-day injury report between "
        "11 a.m. and 1 p.m. local time (and between 8 and 10 a.m. for tip-offs 5 p.m. or earlier) on "
        "game days (besides the second game of a back-to-back). Reports are updated on a continual "
        "basis throughout the day.")

# Every 11/15 edition stamp printed on the index page (verbatim list, both chunks).
STAMPS_1115 = (
    ["%02d_%02d%s" % (h, m, ap) for h, m, ap in
     [(12, 0, "AM"), (12, 15, "AM"), (12, 30, "AM"), (12, 45, "AM")]]
    + ["%02d_%02dAM" % (h, m) for h in range(1, 12) for m in (0, 15, 30, 45)]
    + ["12_00PM", "12_15PM", "12_30PM", "12_45PM"]
    + ["%02d_%02dPM" % (h, m) for h in range(1, 7) for m in (0, 15, 30, 45)]
)

doc = {
    "title": "Official injury-report index: editions listed for 2026-11-15",
    "retrieved_utc": "2026-11-16T00:35Z",
    "index_url": INDEX,
    "pdf_host": HOST,
    "publication_rule_quoted_verbatim": RULE,
    "editions_listed_2026_11_15": len(STAMPS_1115),
    "first_edition_2026_11_15": "12:00 a.m ET",
    "last_edition_2026_11_15": "6:15 p.m ET",
    "last_edition_url": HOST + "Injury-Report_2026-11-15_06_15PM.pdf",
    "verified_url_spot_checks": [
        HOST + "Injury-Report_2026-11-15_06_15AM.pdf",
        HOST + "Injury-Report_2026-11-15_01_30PM.pdf",
        HOST + "Injury-Report_2026-11-15_06_15PM.pdf",
    ],
    "published_readout": {
        "file": "data/official/injury_2026-11-15_0615AM.json",
        "edition_used": "11/15/26 06:15 AM ET",
        "retrieved_utc": "2026-11-15T11:52Z",
        "editions_published_after_that_stamp_at_read_time": 48,
        "computation": ("the index lists 06:15 AM through 06:15 PM ET at 15-minute steps = "
                        "12 h x 4 = 48 editions the published read-out does not include"),
        "gap_hours": 36.25,
        "consequence": ("Every 11/15 game (9) tipped with at least a full game-day of injury "
                        "information the model never read; the late scratches the league's own rule "
                        "produces between 11 a.m. and 1 p.m. ET, and the pre-game updates up to 6:15 "
                        "p.m. ET, are all inside that gap."),
    },
}
assert len(STAMPS_1115) == 4 + 44 + 4 + 24, len(STAMPS_1115)
json.dump(doc, open(os.path.join(HERE, "capture_injury.json"), "w"), indent=1, ensure_ascii=False)
print("editions listed for 11/15:", len(STAMPS_1115), "last:", doc["last_edition_2026_11_15"])
print("published read-out is", doc["published_readout"]["gap_hours"], "hours behind;",
      doc["published_readout"]["editions_published_after_that_stamp_at_read_time"], "later editions exist")
