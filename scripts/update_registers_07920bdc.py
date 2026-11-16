#!/usr/bin/env python3
"""Append this session's flags and retire the stale ones (§56 / X05-X06).

The flag register is append-only: nothing is deleted and no other session's
wording is rewritten. A flag this session resolved keeps its own text and gains
a ``status`` field plus a visible ``RESOLVED``/``RETIRED`` prefix, because the
Flagged page renders title, detail and suggested action - not ``status`` - so a
retirement that lived only in a field would be invisible to a reviewer.

Standard library only. Re-runnable: an id already present is updated in place
rather than appended twice.
"""

from __future__ import annotations

import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGGED = os.path.join(ROOT, "data", "content", "flagged.json")
QUESTIONS = os.path.join(ROOT, "data", "content", "questions.json")

SESSION = "arena/07920bdc-nba1"
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

IDX = "https://official.nba.com/nba-injury-report-2026-27-season/"
PDF_NEW = ("https://ak-static.cms.nba.com/referee/injury/"
           "Injury-Report_2026-11-16_01_15PM.pdf")
PDF_PREV = ("https://ak-static.cms.nba.com/referee/injury/"
            "Injury-Report_2026-11-16_01_00PM.pdf")
GH_BLOB = "https://github.com/wingbangboozle1-lang/NBA1/blob/main/"

NEW_FLAGS = [
    {
        "id": "F-X03",
        "severity": "High",
        "status": "open",
        "title": ("An edition transcribed from the text render of an official PDF "
                  "loses the Reason column on wrapped GSW rows and one Status"),
        "detail": (
            "The 2026-11-16 01:30 PM edition in data/official/ was transcribed by "
            "session arena/7ec9e7a3-nba1 from the fetch_page text render of the "
            "official PDF rather than from its bytes. Diffing it against the "
            "byte-verified 01:15 PM edition (87 rows each, 85 comparable) shows 9 "
            "differences, and checking each against a fresh read of the official "
            "01:30 PM PDF separates them: 3 are real league status changes (Dia, "
            "Malik; Pierre Jr., Jaron; Reese, Julian - all New Orleans, Questionable "
            "to Probable between 01:15 and 01:30 PM), and 6 are reading losses in the "
            "render (the Reason column is empty for Butler III, Curry, Moody, "
            "Porzingis, Santos and Williams - every Golden State row, whose table "
            "block is the one the render splits across pages - and Butler's Status is "
            "empty). The render also prints 'Champagne, Justin' and 'Mathurin, "
            "Benedict' where the official bytes print 'Champagnie' and 'Bennedict'. "
            "The 3 real upgrades are published as status changes; the 6 losses are "
            "reported as unverified and the blank values are left blank, never copied "
            "forward from the earlier edition."),
        "affected": ("data/official/injury_2026-11-16_0130PM_7ec9e7a3.json and any "
                     "availability figure derived from it; the Injuries banner's "
                     "'Report revision' row counts"),
        "source": "S5",
        "source_url": ("https://ak-static.cms.nba.com/referee/injury/"
                       "Injury-Report_2026-11-16_01_30PM.pdf"),
        "suggested_action": ("Prefer byte-exact capture (the workflow added in §56 "
                             "does this) and re-transcribe 01:30 PM from the archived "
                             "PDF once it is captured, before any availability input "
                             "is re-cut from that edition."),
    },
    {
        "id": "F-X01",
        "severity": "High",
        "status": "open",
        "title": ("The injury-PDF parser drops player rows that the official PDF "
                  "contains, and reports zero unparsed cells"),
        "detail": (
            "engine/injury_diff.py recovers report text by grouping words into visual "
            "lines. Read against the 2026-11-16 01:15 PM edition it returns 80 rows and "
            "reports 0 unparsed cells, while the same PDF's content stream contains 87 "
            "report rows. Seven player rows are silently missing: Jerome (Ty), Pippen Jr. "
            "(Scotty), Post (Quinten), Saunders (Richie) and Stewart (Isaiah) for "
            "Memphis in MEM@WAS, and Reese (Julian) and Watford (Trendon) for New "
            "Orleans in GSW@NOP. The bytes were re-read independently, per clipped "
            "rectangle rather than per visual line, by "
            "scripts/verify_injury_edition_07920bdc.py, which recovers all 87 with 0 "
            "status disagreements and 0 rows the line parser finds that it does not. "
            "A parser that drops rows while reporting a clean parse is the worst "
            "failure mode for an archive whose purpose is detecting a status change, so "
            "this session's published edition and its consecutive diff are built from "
            "the verified rows, and each recovered row carries recovered_by."),
        "affected": ("data/parsed/injury_diffs/** (every edition parsed so far), any "
                     "consecutive-edition diff computed from it, and any availability "
                     "strategy graded from parsed editions"),
        "source": "S5",
        "source_url": PDF_NEW,
        "suggested_action": (
            "Port the per-clipped-rectangle reader in "
            "scripts/verify_injury_edition_07920bdc.py into engine/injury_diff.py, or "
            "make it fail loudly when a row's cells do not assemble. Until then, no "
            "parsed edition's row count should be treated as complete. Logged as a "
            "cross-session request in COORDINATION §56.7 - the file is outside this "
            "session's claim."),
    },
    {
        "id": "F-X02",
        "severity": "Low",
        "status": "open",
        "title": ("Both PDF readers split a hyphenated word into two kerned strings and "
                  "print it with a spurious space"),
        "detail": (
            "The reports draw 'Two-Way' as two kerned strings, so a reader that joins "
            "drawn strings with a space prints 'G League - Two- Way'. Both "
            "engine/injury_diff.py and this session's cell reader do it. It is a "
            "rendering artifact, not a content disagreement: the independent 11/15 "
            "06:15 AM transcription prints 'Two-Way'. The cell reader now suppresses "
            "the space when the preceding string ends in a hyphen and is not itself a "
            "standalone dash, and the regression test normalises it before comparing, "
            "so no value on the site is affected - but any future diff of reason text "
            "should normalise it too."),
        "affected": "Reason text in parsed editions, and reason comparison in tests",
        "source": "S5",
        "source_url": PDF_NEW,
        "suggested_action": ("Normalise kerned hyphens at the point of extraction in "
                             "engine/injury_diff.py so reason strings are comparable "
                             "across editions without post-processing."),
    },
    {
        "id": "F-DFA-01",
        "severity": "High",
        "status": "resolved",
        "resolved_utc": STAMP,
        "resolved_by": SESSION,
        "title": ("RESOLVED - three pages named three different 'newest official "
                  "injury editions'"),
        "detail": (
            "Found by session arena/dfa3057f-nba1 (§55) on 2026-11-16: the Injuries "
            "banner named the 11/15 09:00 PM edition, the picks page's availability "
            "columns cited 11/16 09:45 AM, and the Injuries body text said the window "
            "was priced from 11/15 06:15 AM, while the official index listed 11/16 "
            "editions through 1:00 PM ET. Resolved in §56: twelve further 11/16 editions "
            "(09:15 AM through 01:15 PM ET) were captured byte-exactly from "
            "ak-static.cms.nba.com by a runner with network access and archived with "
            "their SHA-256 and retrieval timestamps; the 01:15 PM edition was "
            "transcribed twice by two independent readers and promoted; the two "
            "hard-coded 'newest' sentences on the Injuries page now read the same value "
            "as the banner. The banner shows report revision 11/16/2026 01:15 PM ET and "
            "retrieval 2026-11-16T18:25:44Z. The page still also shows a separate "
            "'Report edition in use' banner (11/16 09:45 AM) - deliberately, because "
            "that is the edition the published availability numbers were cut from, and "
            "a line re-priced after the cut cannot be graded."),
        "affected": "site/pages/injuries.html, site/pages/picks.html availability columns",
        "source": "S5",
        "source_url": PDF_NEW,
        "suggested_action": ("Re-point the 'Report edition in use' at a newer edition "
                             "only alongside a deliberate re-cut of the availability "
                             "inputs, never silently (§56.7 request 2)."),
    },
    {
        "id": "F-DFA-02",
        "severity": "Medium",
        "status": "resolved",
        "resolved_utc": STAMP,
        "resolved_by": SESSION,
        "title": ("RESOLVED - test_injury_diff.py pinned a player from an older edition "
                  "against the newest archived PDF"),
        "detail": (
            "The test asserted that 'Furphy, Johnny' appears in the newest archived "
            "injury PDF. He appears in the 11/15 slate's reports, so the test failed as "
            "soon as the archive rolled to an 11/16 edition that does not list him - a "
            "stale fixture, not a parser fault. It was not wired into any workflow, so "
            "no gate was affected. Fixed: the test now loads the edition the independent "
            "transcription was made from (11/15 06:15 AM) and compares every shared "
            "player row instead of one hand-picked name, skipping cleanly when those "
            "bytes are absent. scripts/test_injury_edition_crosscheck_07920bdc.py adds "
            "the regression this exposed: the independent cell reader must never recover "
            "fewer player rows than the line parser, and the seven rows the line parser "
            "dropped (F-X01) must be present in the bytes."),
        "affected": "scripts/test_injury_diff.py, the unit-test suite",
        "source": "S5",
        "source_url": ("https://ak-static.cms.nba.com/referee/injury/"
                       "Injury-Report_2026-11-15_06_15AM.pdf"),
        "suggested_action": ("Wire both test files into the validate job so a parser "
                             "regression fails CI rather than a reviewer's read."),
    },
    {
        "id": "F-DFA-03",
        "severity": "Low",
        "status": "resolved",
        "resolved_utc": STAMP,
        "resolved_by": SESSION,
        "title": ("RESOLVED - answered question A12 read as current while quoting a "
                  "stale count"),
        "detail": (
            "A12 ('Does the site now produce a line for every game in the next three "
            "days?') answered 'Yes. 27 games from 2026-11-14 to 2026-11-17' under the "
            "Answered heading, while the live horizon is 29 games, 16-19 Nov. The "
            "answer was correct when written and was not re-opened, but under "
            "'Answered' the wording read as current. The answer now opens with the date "
            "it was recorded and states the live count separately; the underlying "
            "record is unchanged."),
        "affected": "site/pages/questions.html answer A12",
        "source": "S4",
        "source_url": "https://www.nba.com/schedule",
        "suggested_action": ("Give every answered question a recorded-on date and have "
                             "the page render it, so a dated answer can never silently "
                             "read as a live one."),
    },
    {
        "id": "F-DFA-04",
        "severity": "Low",
        "status": "resolved",
        "resolved_utc": STAMP,
        "resolved_by": SESSION,
        "title": "RESOLVED - flag F5 ('No archived injury reports') was out of date",
        "detail": (
            "F5 said only the 2026-11-13 05:15 PM edition had been captured. The "
            "archive now holds 29 editions (11/15 12:45 PM through 11/16 01:15 PM ET), "
            "each content-addressed with its retrieval timestamp. F5 is retired below: "
            "its premise is false, and the grading consequence it described no longer "
            "follows from an empty archive but from F-X01 (parsed editions that are "
            "silently incomplete), which is the live item."),
        "affected": "Flagged page item F5",
        "source": "S5",
        "source_url": IDX,
        "suggested_action": "None. Retired, kept in the register for the record.",
    },
    {
        "id": "F-DFA-05",
        "severity": "Info",
        "status": "open",
        "title": ("scripts/test_refresh_gate.py cannot import engine when run as a "
                  "script from the repository root"),
        "detail": (
            "It needs PYTHONPATH=. because it imports the engine package. Harmless in "
            "CI, which does not run it, but a reviewer running the suite by hand sees a "
            "failure that is not a defect."),
        "affected": "scripts/test_refresh_gate.py",
        "source": "",
        "source_url": GH_BLOB + "scripts/test_refresh_gate.py",
        "suggested_action": ("Add the repository root to sys.path in the test module, "
                             "as scripts/test_injury_diff.py already does."),
    },
]

# Questions this session must re-date (F-DFA-03). Nothing else changes.
QUESTION_DATELINE = {
    "A12": ("Recorded 2026-11-14 and left as written - a dated answer, not a live "
            "count: "),
}


def main() -> int:
    with open(FLAGGED, encoding="utf-8") as fh:
        flagged = json.load(fh)
    items = flagged["items"]
    by_id = {f["id"]: f for f in items}

    # Additive only. The register is append-only and another session may have
    # landed the same id in the meantime: theirs stands, mine is not re-written
    # over it. A flag id this session already owns is left untouched.
    added = []
    for new in NEW_FLAGS:
        if new["id"] in by_id:
            print("  keep existing %s (another session's text is not "
                  "overwritten)" % new["id"])
            continue
        items.append(new)
        by_id[new["id"]] = new
        added.append(new["id"])

    # Retire F5 in place (append-only: the original text is kept, the retirement
    # is recorded on top of it and made visible in the title).
    f5 = by_id.get("F5")
    if f5 and f5.get("status") != "retired":
        f5["status"] = "retired"
        f5["retired_utc"] = STAMP
        f5["retired_by"] = SESSION
        f5["retired_note"] = (
            "RETIRED 2026-11-16 (COORDINATION §56, flag F-DFA-04): the premise is no "
            "longer true - data/raw/injury_pdfs/ now holds 29 content-addressed "
            "editions, 11/15 12:45 PM through 11/16 01:15 PM ET, each with its "
            "retrieval timestamp and SHA-256. The grading gap this flag described is "
            "now carried by F-X01 instead (parsed editions that are silently "
            "incomplete), not by an empty archive.")
        f5["title"] = "RETIRED - " + f5["title"]
        f5["detail"] = ("RETIRED 2026-11-16 (§56). " + f5["retired_note"]
                        + " Original finding, kept verbatim: " + f5["detail"])

    flagged["items"] = items
    with open(FLAGGED, "w", encoding="utf-8") as fh:
        json.dump(flagged, fh, indent=1)
        fh.write("\n")
    print("flagged.json: %d items, %d added by this session: %s"
          % (len(items), len(added), ", ".join(added) or "none"))

    with open(QUESTIONS, encoding="utf-8") as fh:
        qs = json.load(fh)
    changed = 0
    for q in qs["answered"]:
        lead = QUESTION_DATELINE.get(q["id"])
        if lead and not q["answer"].startswith(lead):
            q["answer"] = lead + q["answer"]
            q["recorded_on"] = "2026-11-14"
            q["live_note"] = ("The live rolling horizon is 29 games, 2026-11-16 to "
                              "2026-11-19, and every game in it carries an originated "
                              "line - see the Horizon and Projection pages. This answer "
                              "is the 2026-11-14 record, kept because an answered "
                              "question is not re-opened.")
            changed += 1
    with open(QUESTIONS, "w", encoding="utf-8") as fh:
        json.dump(qs, fh, indent=1)
        fh.write("\n")
    print("questions.json: %d answer(s) re-dated" % changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
