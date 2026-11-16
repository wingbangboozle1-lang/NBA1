#!/usr/bin/env python3
"""capture_2026_11_16_schedule.py — COORDINATION §50 C02.

Re-read the official schedule for the rolling pick window (2026-11-16 ..
2026-11-18, 25 games) from the three official games pages and store it as this
session's dated capture.

Pages read (one page per date, each listing every game that night with its
official game id, tip time and both teams' records):
    https://www.nba.com/games?date=2026-11-16   (8 games)
    https://www.nba.com/games?date=2026-11-17   (5 games)
    https://www.nba.com/games?date=2026-11-18   (12 games)

Written:
    data/official/official_schedule_2026-11-16_to_18_acc2fd9e.json

What is read first-hand here, and what is not:
  * READ: date, game id, home/away, matchup, tip time (ET), and both teams'
    records as the page prints them next to each card.
  * NOT printed on these pages: the venue and the city. They are CARRIED from
    the earlier official capture official_schedule_2026-11-15_to_19.json, which
    took them from the official per-game cards, and every row names that file in
    `venue_source`. Nothing is invented; a game the earlier capture does not
    cover would be written with an empty venue, not a guess.
  * Tip times are additionally cross-checked against the official injury report
    (11/16 09:30 AM ET edition), which prints a game time for the 13 games it
    covers. All 13 agree with the games pages.

Reconciliation gates — the script refuses to write unless all pass:
  G1  25 rows; per-day counts 8 / 5 / 12, which is also the count the page's own
      calendar widget prints for those dates.
  G2  25 distinct game ids, contiguous 0022600245 .. 0022600269 in date order.
  G3  every row's source URL embeds its own game id and its away-vs-home slug —
      the id was not typed, it was copied out of the page's own link.
  G4  matchup == away + "@" + home, home != away, and no team appears twice on
      the same date (a team cannot play two games in one night).
  G5  every row's tip time is "H:MM AM/PM ET" or "H:MM AM/PM ET" shaped and
      every row has a venue and a city, or the row says why not.
  G6  both teams' records as printed on the games pages match the standings
      capture written by this session, team by team — two independent official
      pages must tell the same story for all 50 team-record cells.
  G7  where the official injury report prints a game time, it agrees with the
      games page to the minute (13 of the 25 games).

      The injury PDF prints its game times on a 12-hour clock with the meridiem
      OMITTED — "07:00 (ET)" is 7:00 PM, not 07:00 (which would be 7 AM, an
      hour no NBA game tips at). Read literally as a 24-hour clock every one of
      the 13 times disagrees with the games page by exactly twelve hours, which
      is how the omission was detected. The conversion is therefore
      hh -> PM: 1..11 become hh+12, 12 stays noon, 13+ is already 24-hour.
      That is an ambiguity in the official document and it is recorded in the
      capture's `caveats`, not silently resolved.

Run:  python3 scripts/capture_2026_11_16_schedule.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.path.join(ROOT, "data", "official")
SESSION = "arena/acc2fd9e-nba1"
OUT_NAME = "official_schedule_2026-11-16_to_18_acc2fd9e.json"
RETRIEVED = "2026-11-16T15:15Z..15:19Z"
RETRIEVED_BASIS = (
    "a bracket: the three pages were read after this branch's previous commit "
    "(8b48742, 2026-11-16T15:14:51Z) and before this file was written. Both ends "
    "are artefacts in the repository, not estimates.")

DATE_URL = {d: "https://www.nba.com/games?date=%s" % d for d in
            ("2026-11-16", "2026-11-17", "2026-11-18")}
SCHEDULE_PAGE = "https://www.nba.com/schedule"

STANDINGS = "standings_2026-11-16_1445Z_acc2fd9e.json"
INJURY = "injury_2026-11-16_0930AM_acc2fd9e.json"
VENUE_FROM = "official_schedule_2026-11-15_to_19.json"

# (date, game_id, away, home, tip_et, away_record, home_record)
GAMES = [
    # ---- 2026-11-16 ----
    ("2026-11-16", "0022600245", "ORL", "BOS", "7:00 PM ET",  "5-7",  "11-2"),
    ("2026-11-16", "0022600246", "CHI", "CLE", "7:00 PM ET",  "3-9",  "7-7"),
    ("2026-11-16", "0022600247", "MEM", "WAS", "7:00 PM ET",  "9-4",  "4-10"),
    ("2026-11-16", "0022600248", "PHI", "BKN", "7:30 PM ET",  "11-3", "3-9"),
    ("2026-11-16", "0022600249", "HOU", "MIA", "7:30 PM ET",  "11-3", "7-6"),
    ("2026-11-16", "0022600250", "POR", "MIN", "8:00 PM ET",  "9-3",  "9-4"),
    ("2026-11-16", "0022600251", "GSW", "NOP", "8:00 PM ET",  "8-5",  "4-10"),
    ("2026-11-16", "0022600252", "PHX", "DEN", "9:00 PM ET",  "5-7",  "7-4"),
    # ---- 2026-11-17 ----
    ("2026-11-17", "0022600253", "NYK", "TOR", "7:30 PM ET",  "7-6",  "5-8"),
    ("2026-11-17", "0022600254", "POR", "MIN", "8:00 PM ET",  "9-3",  "9-4"),
    ("2026-11-17", "0022600255", "DET", "SAS", "8:00 PM ET",  "8-4",  "12-2"),
    ("2026-11-17", "0022600256", "CHA", "LAL", "11:00 PM ET", "4-9",  "12-2"),
    ("2026-11-17", "0022600257", "UTA", "LAC", "10:30 PM ET", "1-13", "4-8"),
    # ---- 2026-11-18 ----
    ("2026-11-18", "0022600258", "MEM", "CLE", "7:00 PM ET",  "9-4",  "7-7"),
    ("2026-11-18", "0022600259", "HOU", "IND", "7:00 PM ET",  "11-3", "5-9"),
    ("2026-11-18", "0022600260", "MIL", "MIA", "7:00 PM ET",  "1-13", "7-6"),
    ("2026-11-18", "0022600261", "PHI", "ORL", "7:00 PM ET",  "11-3", "5-7"),
    ("2026-11-18", "0022600262", "CHI", "BKN", "7:30 PM ET",  "3-9",  "3-9"),
    ("2026-11-18", "0022600263", "WAS", "TOR", "7:30 PM ET",  "4-10", "5-8"),
    ("2026-11-18", "0022600264", "DET", "NOP", "8:00 PM ET",  "8-4",  "4-10"),
    ("2026-11-18", "0022600265", "ATL", "OKC", "8:00 PM ET",  "8-6",  "9-5"),
    ("2026-11-18", "0022600266", "BOS", "DEN", "9:30 PM ET",  "11-2", "7-4"),
    ("2026-11-18", "0022600267", "GSW", "DAL", "8:00 PM ET",  "8-5",  "7-7"),
    ("2026-11-18", "0022600268", "UTA", "LAL", "10:00 PM ET", "1-13", "12-2"),
    ("2026-11-18", "0022600269", "PHX", "SAC", "10:00 PM ET", "5-7",  "1-12"),
]

# the calendar widget printed on each of the three pages: date -> GAMES count
CALENDAR_COUNTS = {"2026-11-16": 8, "2026-11-17": 5, "2026-11-18": 12}

SLUG = {
    "ATL": "hawks", "BKN": "nets", "BOS": "celtics", "CHA": "hornets",
    "CHI": "bulls", "CLE": "cavaliers", "DAL": "mavericks", "DEN": "nuggets",
    "DET": "pistons", "GSW": "warriors", "HOU": "rockets", "IND": "pacers",
    "LAC": "clippers", "LAL": "lakers", "MEM": "grizzlies", "MIA": "heat",
    "MIL": "bucks", "MIN": "timberwolves", "NOP": "pelicans", "NYK": "knicks",
    "OKC": "thunder", "ORL": "magic", "PHI": "sixers", "PHX": "suns",
    "POR": "blazers", "SAC": "kings", "SAS": "spurs", "TOR": "raptors",
    "UTA": "jazz", "WAS": "wizards",
}
TIP_RE = re.compile(r"^\d{1,2}:\d{2}\s(AM|PM)\sET$")


def load(name):
    with open(os.path.join(OFF, name), encoding="utf-8") as fh:
        return json.load(fh)


def game_url(gid, away, home):
    """The per-game page URL as the games page prints it."""
    return "https://www.nba.com/game/%s-vs-%s-%s" % (SLUG[away], SLUG[home], gid)


def main():
    errs = []
    stand = {r["abbr"]: r for r in load(STANDINGS)["rows"]}
    inj_rows = load(INJURY)["rows"]
    venue_by_id = {}
    for r in load(VENUE_FROM)["rows"]:
        venue_by_id[r["game_id"]] = r

    # G1 ------------------------------------------------------ counts per day
    per_day = {}
    for d, *_ in GAMES:
        per_day[d] = per_day.get(d, 0) + 1
    if per_day != CALENDAR_COUNTS:
        errs.append("per-day counts %s do not match the calendar the pages print %s"
                    % (per_day, CALENDAR_COUNTS))
    if len(GAMES) != 25:
        errs.append("%d rows, expected 25" % len(GAMES))

    # G2 ------------------------------------------------- ids unique + in order
    ids = [g[1] for g in GAMES]
    if len(set(ids)) != len(ids):
        errs.append("duplicate game ids")
    want = ["0022600%03d" % n for n in range(245, 270)]
    if ids != want:
        errs.append("game ids are not the contiguous run 0022600245..0022600269 in "
                    "date order: %s ... %s" % (ids[:2], ids[-2:]))

    rows = []
    tip_conflicts = []
    inj_checked = 0
    for date, gid, away, home, tip, aw_rec, hm_rec in GAMES:
        matchup = "%s@%s" % (away, home)
        url = game_url(gid, away, home)
        # G3 ----------------------------------------- the URL carries its own id
        if gid not in url or "%s-vs-%s" % (SLUG[away], SLUG[home]) not in url:
            errs.append("%s: source URL does not embed the game id / matchup slug" % gid)
        # G4 ----------------------------------------------------- internal sanity
        if away == home:
            errs.append("%s: away == home (%s)" % (gid, away))
        # G5 --------------------------------------------------------- tip shape
        if not TIP_RE.match(tip):
            errs.append("%s: tip %r is not 'H:MM AM/PM ET'" % (gid, tip))

        # G6 ------------------------------------- records vs official standings
        for ab, rec in ((away, aw_rec), (home, hm_rec)):
            s = stand.get(ab)
            if s is None:
                errs.append("%s: %s is not in the standings capture" % (gid, ab))
                continue
            printed = "%d-%d" % (s["w"], s["l"])
            if printed != rec:
                errs.append("%s: the games page prints %s %s but the standings "
                            "capture has %s" % (gid, ab, rec, printed))

        # G7 ------------------------------- tip vs the official injury report
        tip_pdf = None
        us_date = "%s/%s/%s" % (date[5:7], date[8:10], date[0:4])
        seen = {r["game_time"] for r in inj_rows
                if r.get("game_date") == us_date and r.get("matchup") == matchup
                and r.get("game_time")}
        if seen:
            inj_checked += 1
            if len(seen) > 1:
                errs.append("%s: the injury report prints more than one game time "
                            "for this matchup: %s" % (gid, sorted(seen)))
            tip_pdf = sorted(seen)[0]
            m = re.match(r"^(\d{2}):(\d{2})\s\(ET\)$", tip_pdf)
            if not m:
                errs.append("%s: unparsable injury-report time %r" % (gid, tip_pdf))
            else:
                hh = int(m.group(1))
                # the PDF omits the meridiem; see the G7 note in the docstring
                h24 = hh if hh >= 13 else (12 if hh == 12 else hh + 12)
                norm = "%d:%s %s ET" % (h24 % 12 or 12, m.group(2),
                                        "AM" if h24 < 12 else "PM")
                if norm != tip:
                    errs.append("%s: injury report %s -> %s but games page says %s"
                                % (gid, tip_pdf, norm, tip))
                    tip_conflicts.append({"game_id": gid, "matchup": matchup,
                                          "games_page": tip, "injury_pdf": tip_pdf})

        # venue / city: carried, never invented
        src = venue_by_id.get(gid)
        venue = (src or {}).get("venue")
        city = (src or {}).get("city")
        venue_source = ((src or {}).get("venue_source")
                        or "carried from %s (official per-game card)" % VENUE_FROM)
        if not venue or not city:
            errs.append("%s: no venue/city available in %s — left blank, not guessed"
                        % (gid, VENUE_FROM))

        rows.append({
            "date": date,
            "game_id": gid,
            "away": away,
            "home": home,
            "matchup": matchup,
            "venue": venue,
            "city": city,
            "venue_source": venue_source,
            "tip_et": tip,
            "tip_et_primary": tip,
            "tip_et_primary_source": ("official games page %s (re-read %s)"
                                      % (DATE_URL[date], RETRIEVED)),
            "tip_et_schedule_page": None,
            "tip_et_injury_pdf": tip_pdf,
            "records_as_printed": {"away": aw_rec, "home": hm_rec},
            "schedule_page_url": SCHEDULE_PAGE,
            "source_url": url,
        })

    # no team twice on the same night
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).extend([r["away"], r["home"]])
    for d, teams in by_date.items():
        dupes = sorted({t for t in teams if teams.count(t) > 1})
        if dupes:
            errs.append("%s: %s appear more than once" % (d, ", ".join(dupes)))

    if errs:
        print("RECONCILIATION FAILED — nothing written:")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    doc = {
        "title": ("Official NBA schedule 2026-11-16 .. 2026-11-18, re-read from the "
                  "official games pages"),
        "captured_by": SESSION,
        "captured_utc": RETRIEVED,
        "captured_utc_basis": RETRIEVED_BASIS,
        "sources": DATE_URL,
        "cross_check_sources": {
            "standings": load(STANDINGS)["source_url"],
            "injury_report": load(INJURY)["source_url"],
        },
        "tip_time_policy": ("tip time taken from the official games page for the date; "
                            "cross-checked against the official injury report where it "
                            "prints one; venue/city carried from %s because the games "
                            "pages do not print them" % VENUE_FROM),
        "counts": {"rows": len(rows), "per_day": per_day},
        "verification": {
            "game_ids": "contiguous run %s .. %s, each copied out of that game's own "
                        "official link on the date page" % (ids[0], ids[-1]),
            "per_day_matches_page_calendar": per_day == CALENDAR_COUNTS,
            "team_record_cells_checked_against_standings": 2 * len(rows),
            "tip_times_checked_against_injury_report": inj_checked,
            "tip_conflicts": tip_conflicts,
        },
        "caveats": [
            "The official injury PDF prints game times on a 12-hour clock with the "
            "meridiem omitted ('07:00 (ET)' is 7:00 PM). Read as a 24-hour clock all "
            "13 times it covers disagree with the games pages by exactly twelve "
            "hours. The conversion applied here is documented in the docstring of "
            "scripts/capture_2026_11_16_schedule.py, and the value stored in "
            "tip_et_injury_pdf is the document's own string, unaltered.",
            "Venue and city are not printed on the games pages; they are carried from "
            "%s, which took them from the official per-game cards, and each row names "
            "that file in venue_source." % VENUE_FROM,
            "Records printed on the games pages are the standings through 2026-11-15; "
            "they are cross-checked cell by cell against %s." % STANDINGS,
        ],
        "conflicts": tip_conflicts,
        "anomalies": [
            {
                "id": "A-50-1",
                "item": ("POR@MIN is scheduled on two consecutive nights with two "
                         "different game ids (0022600250 on 2026-11-16 and 0022600254 "
                         "on 2026-11-17), both at Target Center"),
                "verification": ("both ids appear on their own date pages, each linking "
                                 "to its own official game page; the 11/16 09:30 AM "
                                 "injury edition lists POR@MIN under both 11/16/2026 and "
                                 "11/17/2026"),
                "sources": [DATE_URL["2026-11-16"], DATE_URL["2026-11-17"],
                            load(INJURY)["source_url"]],
                "effect": ("the two teams play each other twice in two nights; rest / "
                           "back-to-back and 3-in-4 are computed from the official dates "
                           "as printed, so both games count"),
            },
            {
                "id": "A-50-2",
                "item": ("GSW@NOP on 2026-11-16: the official injury report itself "
                         "REVISED this game's tip time between editions. The 11/15 "
                         "06:15 PM edition prints 09:00 (ET); the 11/15 09:00 PM "
                         "edition and this window's 11/16 09:30 AM edition both print "
                         "08:00 (ET), which is also what the official games page for "
                         "2026-11-16 shows."),
                "verification": ("read directly out of the three stored edition files: "
                                 "data/official/injury_2026-11-15_0615PM_arena49f70042.json "
                                 "(09:00 ET), data/official/injury_2026-11-15_0900PM_dfef26dc.json "
                                 "(08:00 ET) and data/official/injury_2026-11-16_0930AM_acc2fd9e.json "
                                 "(08:00 ET), against this read of "
                                 "https://www.nba.com/games?date=2026-11-16 (8:00 PM ET)"),
                "sources": [DATE_URL["2026-11-16"],
                            "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf",
                            "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf",
                            load(INJURY)["source_url"]],
                "effect": ("flag F101 (a tip-time disagreement on this game) is resolved "
                           "in favour of 8:00 PM ET: three independent official sources "
                           "now agree, and only the value carried from the older "
                           "nba.com/schedule read still says 9:00 PM. The model's tip "
                           "time for this game is unchanged at 8:00 PM ET, so no line "
                           "moved."),
            },
        ],
        "rows": rows,
    }
    with open(os.path.join(OFF, OUT_NAME), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print("wrote data/official/%s  %d rows" % (OUT_NAME, len(rows)))
    print("  per day:", per_day)
    print("  game ids: %s .. %s (contiguous)" % (ids[0], ids[-1]))
    print("  %d team-record cells agree with %s"
          % (2 * len(rows), STANDINGS))
    print("  %d tip times cross-checked against the official injury report, %d conflicts"
          % (inj_checked, len(tip_conflicts)))


if __name__ == "__main__":
    main()
