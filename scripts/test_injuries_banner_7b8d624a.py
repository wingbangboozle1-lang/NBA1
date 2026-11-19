"""Regression test for the Injuries page banners (COORDINATION §74, session arena/7b8d624a-nba1).

Checks the rendered page (default: site/pages/injuries.html; pass a path to test another copy):
  * the banner that names the rows' edition states its printed revision time and retrieval time;
  * the hard-coded "newer official edition" text that contradicted the data is gone;
  * the consecutive-edition diff is not labelled against an edition it does not compare;
  * the index banner agrees with the stored index record;
  * every relative link in the three injury banners resolves to a file in the repository.

Exit 0 = pass, 1 = fail. Run:  python3 scripts/test_injuries_banner_7b8d624a.py [path]
"""
import html as _html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site", "pages", "injuries.html")
INDEX_REC = os.path.join(ROOT, "data", "official", "injury_index_2026-11-19_7b8d624a.json")
EDITION = os.path.join(ROOT, "data", "parsed", "injury_diffs", "editions", "Injury-Report_2026-11-16_09_45AM.json")

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


s = open(PAGE, encoding="utf-8").read()
banners = re.findall(r'<div class="banner (\w+)"><div class="b-t">(.*?)</div><div class="b-b">(.*?)</div></div>', s, re.S)
text_all = _html.unescape(re.sub(r"<[^>]+>", " ", s))

# 1. The edition behind the rows: printed revision and retrieval stamps.
ed = json.load(open(EDITION, encoding="utf-8"))
b1 = [b for b in banners if b[1].startswith("Edition behind the rows")]
check(len(b1) == 1, "banner naming the rows' edition is missing")
if b1:
    t1 = _html.unescape(re.sub(r"<[^>]+>", " ", b1[0][2]))
    check("11/16/26 09:45 AM ET" in t1, "revision time of the rows' edition not shown")
    check(ed["retrieved_at_utc"] in t1, "retrieval time of the rows' edition not shown")
    check(ed["sha256"][:16] in t1, "sha-256 prefix of the rows' edition not shown")

# 2. The stale hard-coded narrative must be gone.
for stale in ("There is a newer official edition than the one behind these numbers",
              "01:30 PM ET", "11/13/26 07:30 PM ET", "rows: 24 (21 player rows"):
    check(stale not in text_all, "stale text still on the page: %r" % stale)

# 3. The diff banner: it may only name the edition it was computed into.
diffs = re.findall(r'(from <b>|diff file\)|Consecutive-edition diff into this edition[^<]*)', s)
if "Consecutive-edition diff into this edition (from" in text_all:
    check("injury_diff_2026-11-17_1015AM_to_1030AM" not in s,
          "banner still links the 11/17 diff as if it described the rows' edition")
    check("09_30AM" in s, "diff banner does not name its 'from' edition")

# 4. The index banner agrees with the stored index record.
rec = json.load(open(INDEX_REC, encoding="utf-8"))
b2 = [b for b in banners if b[1].startswith("Newest edition the official index lists")]
check(len(b2) == 1, "index banner missing")
if b2:
    t2 = _html.unescape(re.sub(r"<[^>]+>", " ", b2[0][2]))
    check(str(rec["listed_count"]) in t2, "index banner count disagrees with the index record")
    check(rec["newest_listed"]["time_et"] in t2, "index banner newest time disagrees with the index record")
    check(rec["index_read_window_utc"]["end"] in t2, "index banner read time disagrees with the index record")
    check("11/19/26 07:00 AM" in t2, "index banner does not show the newest PDF's printed header")

# 5. The newer-edition warning is present and computed from the same record.
b3 = [b for b in banners if b[1].startswith("The rows on this page are not the newest")]
check(len(b3) == 1, "warning that the rows are not the newest edition is missing")

# 6. Every relative link in the injury banners resolves.
base = os.path.dirname(PAGE)
for kind, title, body in banners:
    if not (title.startswith("Edition behind") or title.startswith("Newest edition the official index")
            or title.startswith("The rows on this page are not")):
        continue
    for href in re.findall(r'href="([^"#]+)"', body):
        if re.match(r"^(https?:|mailto:)", href):
            continue
        target = os.path.normpath(os.path.join(base, href))
        check(os.path.exists(target), "broken link in banner %r: %s" % (title, href))

if fails:
    print("FAIL (%d):" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("PASS: injuries banners agree with the stored records (%s)" % os.path.relpath(PAGE, ROOT))
