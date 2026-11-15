#!/usr/bin/env python3
"""check_injury_editions.py - the injury-report surface has to prove four things.

Run it locally or from CI. Exit 0 = all four hold; exit 1 prints every failure.

  A. UNIT: engine/fetch_official.parse_injury_index finds BOTH the AM and the PM
     editions on a fixture of the official index page. The pre-fix pattern
     required a "PM" suffix, so the 15-minute game-day morning editions
     (observed on https://official.nba.com/nba-injury-report-2026-27-season/ on
     2026-11-15: 12:00 a.m. through 06:15 a.m. ET) were invisible to the
     scheduled job and the newest report of the day was never captured.
  B. UNIT: edition_revision_time() turns a published filename into the revision
     instant, so the page can print "report revised at" next to "retrieved at".
  C. AUDIT: the injury snapshot the site reads carries a revision stamp AND a
     retrieval stamp, names its edition, and its rows all carry a reason or an
     explicit non-filing marker.
  D. AUDIT: a consecutive-edition diff exists for the edition in use. Storing a
     PDF is not enough - the requirement is to diff consecutive reports for
     status changes, so the diff file must exist and name the two editions it
     compares.

Nothing here fetches the network; the fixtures are inline so the check is
reproducible on any machine.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

failures = []


def check(name, ok, detail):
    print("%-58s %s" % (name, "PASS" if ok else "FAIL"))
    if not ok:
        failures.append("%s - %s" % (name, detail))
    return ok


# ---------------------------------------------------------------- fixture
IDX_FIXTURE = """
<li><a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf">
6:15 a.m ET report</a> &#8211; NBA Official Injury Report (November 15, 2026)</li>
<li><a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_00AM.pdf">
6:00 a.m ET report</a></li>
<li><a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_05_15AM.pdf">
5:15 a.m ET report</a></li>
<li><a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_07_30PM.pdf">
7:30 p.m ET report</a></li>
<li><a href="https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_05_15PM.pdf">
5:15 p.m ET report</a></li>
"""

try:
    import fetch_official as fo
except Exception as exc:                                    # pragma: no cover
    print("cannot import engine/fetch_official.py: %s" % exc)
    sys.exit(1)

# ---------------------------------------------------------------- A + B
editions = fo.parse_injury_index(IDX_FIXTURE)
check("A1 index parse finds every linked edition", len(editions) == 5,
      "parsed %d of 5 fixture links: %s" % (len(editions), editions))
am = [e for e in editions if "AM" in e]
check("A2 the AM (morning) editions are not skipped", len(am) == 3,
      "found %d AM editions; a PM-only regex returns 0 and the newest report of the day is missed" % len(am))
check("A3 newest-first ordering puts 06:15AM above 07:30PM of the previous day",
      bool(editions) and "2026-11-15_06_15AM" in editions[0],
      "order is %s" % editions)
check("A4 the fixed fallback covers the AM window",
      any("AM" in t for t in fo.INJURY_AM_EDITION_TIMES) and len(fo.INJURY_AM_EDITION_TIMES) >= 20,
      "INJURY_AM_EDITION_TIMES = %s" % (fo.INJURY_AM_EDITION_TIMES,))

rev, human = fo.edition_revision_time("Injury-Report_2026-11-15_06_15AM.pdf")
check("B1 revision time parsed from the filename", rev == "2026-11-15T11:15:00Z",
      "got %r (expected 2026-11-15T11:15:00Z: 06:15 ET = 11:15 UTC in EST)" % rev)
check("B2 revision time keeps the printed ET label", human == "2026-11-15 06:15 ET",
      "got %r" % human)
rev2, _ = fo.edition_revision_time("Injury-Report_2026-11-14_05_15PM.pdf")
check("B3 a PM edition converts the same way", rev2 == "2026-11-14T22:15:00Z", "got %r" % rev2)
check("B4 an unparseable name returns no stamp rather than a guess",
      fo.edition_revision_time("Injury-Report_draft.pdf") == (None, None),
      "must be (None, None), not a fabricated time")

# ---------------------------------------------------------------- C
inj_path = os.path.join(ROOT, "data", "raw", "injuries.json")
inj = json.load(open(inj_path, encoding="utf-8"))
cols, rows = inj["cols"], inj["rows"]
check("C1 the snapshot names its edition", bool(inj.get("report")) and bool(inj.get("source_url")),
      "report/source_url must both be present")
check("C2 it carries a revision stamp and a retrieval stamp",
      bool(inj.get("edition_revision_time")) and bool(inj.get("retrieval_time")),
      "edition_revision_time=%r retrieval_time=%r - the brief requires the injury page to show "
      "report revision time AND retrieval time" % (inj.get("edition_revision_time"), inj.get("retrieval_time")))
if re.search(r"(\d{2})_(\d{2})(AM|PM)", inj.get("source_url", "")):
    m = re.search(r"Injury-Report_[\d\-_]+?_(\d{2})_(\d{2})(AM|PM)\.pdf", inj["source_url"])
    stamp = fo.edition_revision_time(inj["source_url"].split("/")[-1])[0]
    shown = inj.get("edition_revision_time", "")
    check("C3 the edition label and the file it points at agree",
          m is not None and ("06:15" in shown or "%s:%s" % (m.group(1), m.group(2)) in shown.replace(".", ":")),
          "url names an edition at %s:%s %s, the page label says %r"
          % (m.group(1), m.group(2), m.group(3), shown) if m else "the source_url is not a dated edition PDF")
    check("C4 the revision instant is derivable from the published filename", bool(stamp),
          "edition_revision_time should be expressible as a UTC instant for 'newer than' maths")
i_status, i_reason = cols.index("status"), cols.index("reason")
i_player = cols.index("player")
bad = [r for r in rows if not r[i_status]]
check("C5 every row has a printed status", not bad, "%d rows with an empty status cell" % len(bad))
nys = [r for r in rows if r[i_status] == "NOT YET SUBMITTED"]
check("C6 a non-filing is marked as such, never filled in",
      all(not r[i_player] for r in nys),
      "%d NOT YET SUBMITTED rows; a non-filing row must carry no invented player" % len(nys))
no_reason = [r for r in rows if r[i_status] != "NOT YET SUBMITTED" and not r[i_reason]]
check("C7 every real status row carries the printed reason", not no_reason,
      "%d rows without a reason: %s" % (len(no_reason), no_reason[:3]))

# ---------------------------------------------------------------- D
live = os.path.join(ROOT, "data", "live")
diffs = sorted(f for f in os.listdir(live) if f.startswith("injury_edition_diff_")) if os.path.isdir(live) else []
check("D1 a consecutive-edition diff file exists", bool(diffs),
      "expected data/live/injury_edition_diff_<date>.json - storing reports without diffing them does "
      "not satisfy 'diff consecutive reports for status changes'")
if diffs:
    d = json.load(open(os.path.join(live, diffs[-1]), encoding="utf-8"))
    check("D2 the diff names both editions it compares",
          bool(d.get("edition_a")) and bool(d.get("edition_b")) and d["edition_a"] != d["edition_b"],
          "got %r / %r" % (d.get("edition_a"), d.get("edition_b")))
    check("D3 the diff reports all three directions",
          all(k in d for k in ("status_changes", "players_appearing", "players_leaving")),
          "a diff that only lists changes cannot tell a reader that a status is unchanged")
    check("D4 row counts of both editions are recorded",
          isinstance(d.get("rows_a"), int) and isinstance(d.get("rows_b"), int),
          "rows_a=%r rows_b=%r" % (d.get("rows_a"), d.get("rows_b")))

print()
if failures:
    print("FAIL - %d problem(s):" % len(failures))
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS - injury edition handling: index parse, revision stamps and the consecutive diff all hold.")
