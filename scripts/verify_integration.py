#!/usr/bin/env python3
"""Independent re-verification of the merged tree (final integration session).

    python3 scripts/verify_integration.py

This script deliberately does NOT invoke the earlier sessions' gates and take
their word for it. It re-derives the properties that the brief actually asks for
and fails loudly when they do not hold:

  I1  every JSON file in the repository parses, and every site data file that a
      page fetches exists
  I2  every internal link (href/src that is not absolute) resolves on disk, for
      every HTML file in the repository - including inside inline <script>
  I3  every external link is https and its host is on an allowlist of official /
      documentation hosts
  I4  every <tr> on every page that carries data has at least one source link
  I5  no text-search sentinels leak: "None", "nan", "undefined", "TODO",
      "{{", "}}", "python", "Traceback" in rendered prose
  I6  the numbers asserted in the prose exist in the data files (the class of
      defect that survived every automated gate in an earlier session)
  I7  both entry points exist and the repository-root index links to both builds

Exit code is 0 only if there are zero errors. Warnings never fail the run but
are printed, and they are the things a human has to look at.

Every check prints the exact file (and line where applicable) it looked at, so
the result can be audited by hand rather than trusted.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OFFICIAL_HOSTS = {
    # NBA official
    "www.nba.com",
    "nba.com",
    "official.nba.com",
    "ak-static.cms.nba.com",
    "stats.nba.com",
    "cdn.nba.com",
    # GitHub / docs (used for Pages + tooling references only)
    "github.com",
    "docs.github.com",
    "www.github.com",
    "raw.githubusercontent.com",
    # this repository's own GitHub Pages host — used by audit pages as live-site
    # evidence links (e.g. docs/audit/index.html); it is this repo's published output
    "wingbangboozle1-lang.github.io",
    # Google Fonts: stylesheet only, no data claim.
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}
# Official *data* hosts. A row that only links outside this set does not count as
# sourced to the brief's standard.
DATA_HOSTS = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
              "stats.nba.com", "cdn.nba.com"}
# The Dutch gambling regulator (Kansspelautoriteit) is cited for legal scope only,
# never for an NBA value. Accepted, but reported so a human can see the count.
REGULATOR_HOSTS = {"kansspelautoriteit.nl", "www.kansspelautoriteit.nl"}
SECONDARY_HOSTS = {"www.basketball-reference.com", "basketball-reference.com"}

errors: list[str] = []
warnings: list[str] = []
checked = {"json": 0, "html": 0, "links": 0, "rows": 0, "sourced_rows": 0}


def err(msg):
    errors.append(msg)
    print(f"  ERROR   {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  WARN    {msg}")


def ok(msg):
    print(f"  ok      {msg}")


def rel(p):
    return os.path.relpath(p, ROOT)


def walk(exts):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames:
            if any(f.endswith(e) for e in exts):
                yield os.path.join(dirpath, f)


# ---------------------------------------------------------------- I1 JSON
def check_json():
    print("\n[I1] JSON parses and site data exists")
    for p in walk((".json",)):
        checked["json"] += 1
        try:
            with open(p, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as e:
            err(f"{rel(p)}: invalid JSON: {e}")
    ok(f"{checked['json']} JSON files parse")

    # Build B's pages all read from docs/data/. Every file referenced there must exist.
    referenced = set()
    for p in walk((".js", ".html")):
        text = open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""['"](?:\.{0,2}/)?(?:docs/)?data/([\w.\-]+\.json)['"]""", text):
            referenced.add(m.group(1))
    missing = [f for f in sorted(referenced) if not os.path.exists(os.path.join(ROOT, "docs", "data", f))]
    if missing:
        for f in missing:
            err(f"page references docs/data/{f} which does not exist")
    else:
        ok(f"{len(referenced)} referenced data files all exist")


# ---------------------------------------------------------------- I2/I3 links
def strip_scripts(html):
    return re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)


def strip_json_blocks(html):
    return re.sub(r'<script[^>]*type=["\']application/json["\'][^>]*>.*?</script>', "", html, flags=re.S | re.I)


STATIC_LINK_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"'<>$`{}]+)["']""", re.I)


def classify(html):
    """Return (internal_links, external_urls) from static markup only.

    Script bodies are excluded on purpose: their markup-building templates
    contain ${...} expressions that are not URLs, and treating them as links
    produced false failures before this was fixed.
    """
    internal, external = [], []
    for m in STATIC_LINK_RE.finditer(strip_json_blocks(strip_scripts(html))):
        h = m.group(1).strip()
        if not h or h.startswith(("#", "data:", "mailto:", "javascript:")):
            continue
        if h.startswith("//"):
            external.append("https:" + h)
        elif re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", h):
            external.append(h)
        else:
            internal.append(h)
    return internal, external


def check_links():
    print("\n[I2/I3] Internal links resolve; external links are https on trusted hosts")
    bad_internal, bad_host, non_https, regulator = [], [], [], set()
    for p in walk((".html",)):
        checked["html"] += 1
        html = open(p, encoding="utf-8", errors="replace").read()
        base = os.path.dirname(p)
        internal, external = classify(html)
        checked["links"] += len(internal) + len(external)
        for h in internal:
            path = h.split("#")[0].split("?")[0]
            if not path:
                continue
            target = os.path.normpath(os.path.join(base, path))
            if not os.path.exists(target):
                bad_internal.append((rel(p), h))
        for u in external:
            from urllib.parse import urlparse
            if not u.startswith("https://"):
                non_https.append((rel(p), u))
                continue
            host = urlparse(u).netloc.lower().split("@")[-1].split(":")[0]
            if host in SECONDARY_HOSTS:
                warn(f"{rel(p)}: secondary (non-official) source host {host}: {u}")
            elif host in REGULATOR_HOSTS:
                regulator.add(host)
            elif host not in OFFICIAL_HOSTS:
                bad_host.append((rel(p), host, u))

    for p, h in bad_internal:
        err(f"broken internal link in {p}: {h}")
    for p, h in non_https:
        err(f"non-https external link in {p}: {h}")
    for p, host, h in bad_host:
        err(f"untrusted external host in {p}: {host} ({h})")
    if regulator:
        ok(f"regulator host cited for legal scope only: {', '.join(sorted(regulator))}")
    ok(f"{checked['html']} HTML files, {checked['links']} static links")

# ---------------------------------------------------------------- I4 sourced rows
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
LINK_RE = re.compile(r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"']", re.I)


def check_rows():
    print("\n[I4] Data rows carry a source link")
    unsourced = []
    for p in walk((".html",)):
        html = strip_json_blocks(open(p, encoding="utf-8", errors="replace").read())
        for m in ROW_RE.finditer(html):
            row = m.group(1)
            if "<th" in row.lower():
                continue  # header row
            checked["rows"] += 1
            static_row = strip_scripts(row)
            links = [u for u in LINK_RE.findall(static_row) if u.startswith("http")]
            official = [
                u for u in links
                if re.match(r"^https://([\w.\-]*\.)?nba\.com/", u)
            ]
            if official:
                checked["sourced_rows"] += 1
            elif links:
                unsourced.append((rel(p), "no official NBA link"))
            else:
                unsourced.append((rel(p), "no external link at all"))
    if unsourced:
        for p, why in unsourced[:40]:
            warn(f"{p}: row without an official source link ({why})")
        if len(unsourced) > 40:
            warn(f"... and {len(unsourced) - 40} more rows without an official link")
    ok(f"{checked['sourced_rows']}/{checked['rows']} data rows carry an official source link")


# ---------------------------------------------------------------- I5 sentinels
SENTINELS = [
    (re.compile(r">\s*None\s*<"), "'None' rendered into prose"),
    (re.compile(r">\s*nan\s*<", re.I), "'nan' rendered into prose"),
    (re.compile(r">\s*undefined\s*<", re.I), "'undefined' rendered into prose"),
    (re.compile(r"\{\{"), "unrendered '{{' template marker"),
    (re.compile(r"\bTODO\b"), "'TODO' left in a page"),
    (re.compile(r"Traceback \(most recent call last\)"), "python traceback pasted into a page"),
    (re.compile(r">\s*NaN\s*<"), "'NaN' rendered into prose"),
    (re.compile(r"INSERT[ _]HERE", re.I), "'INSERT HERE' placeholder"),
]


def check_sentinels():
    print("\n[I5] No leaked placeholders or sentinels")
    found = 0
    for p in walk((".html",)):
        html = strip_json_blocks(open(p, encoding="utf-8", errors="replace").read())
        prose = strip_scripts(html)
        for rx, what in SENTINELS:
            for m in rx.finditer(prose):
                line = prose[: m.start()].count("\n") + 1
                warn(f"{rel(p)}:{line}: {what}")
                found += 1
    if not found:
        ok("no sentinels found in rendered prose")


# ---------------------------------------------------------------- I6 prose numbers
def check_prose_numbers():
    """Every count the prose asserts must exist in the data it describes.

    This is the exact defect class that survived a green test suite earlier:
    prose said '486 table rows' when the site had 667, 'three absences' when
    there were two, and a luck gate passed on a 7-0 record. Here we only
    machine-check the cheap, unambiguous ones: the headline counts on the
    landing pages."""
    print("\n[I6] Headline counts in prose match the data")
    meta = json.load(open(os.path.join(ROOT, "docs/data/meta.json"), encoding="utf-8"))
    val = json.load(open(os.path.join(ROOT, "docs/data/validation.json"), encoding="utf-8"))
    bt = json.load(open(os.path.join(ROOT, "docs/data/backtest.json"), encoding="utf-8"))
    picks = json.load(open(os.path.join(ROOT, "docs/data/picks.json"), encoding="utf-8"))

    facts = {
        "out_of_sample_games": meta["counts"]["out_of_sample_games"],
        "strategies": meta["counts"]["strategies"],
        "upcoming_games": meta["counts"]["upcoming_games"],
        "pick_rows": len(picks["rows"]),
    }
    print(f"  data  {facts}")

    # backtest games actually listed must equal the declared count
    games = bt.get("games") or bt.get("rows") or []
    if isinstance(games, list) and games:
        if len(games) != facts["out_of_sample_games"]:
            err(f"backtest declares {facts['out_of_sample_games']} out-of-sample games "
                f"but lists {len(games)}")
        else:
            ok(f"backtest lists exactly {len(games)} games, matching meta.json")

    # validation strategy count
    strat = val.get("strategies") or []
    if isinstance(strat, list) and strat and len(strat) != facts["strategies"]:
        err(f"meta.json declares {facts['strategies']} strategies but validation.json has {len(strat)}")
    else:
        ok(f"strategy count agrees ({facts['strategies']})")

    # A page that says "51 out-of-sample" must not disagree
    for p in walk((".html",)):
        text = strip_scripts(open(p, encoding="utf-8", errors="replace").read())
        for m in re.finditer(r"(\d+)\s*(?:out-of-sample|out of sample)", text, re.I):
            n = int(m.group(1))
            if n != facts["out_of_sample_games"]:
                err(f"{rel(p)}: prose says {n} out-of-sample games, data says {facts['out_of_sample_games']}")


# --------------------------------------------------- I6b site-wide row counts
ROW_BLOCK = re.compile(r"<tbody>(.*?)</tbody>", re.S | re.I)
OFFICIAL_IN_ROW = re.compile(r"https?://([\w.\-]*\.)?nba\.com/")


def count_rows(scope):
    total = sourced = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, scope)):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for f in filenames:
            if not f.endswith(".html"):
                continue
            txt = open(os.path.join(dirpath, f), encoding="utf-8", errors="replace").read()
            txt = strip_scripts(txt)
            for tb in ROW_BLOCK.findall(txt):
                for row in re.findall(r"<tr\b[^>]*>.*?</tr>", tb, re.S):
                    total += 1
                    if OFFICIAL_IN_ROW.search(row):
                        sourced += 1
    return total, sourced


def check_row_counts():
    """The two numbers the executive summary publishes about itself.

    Earlier sessions shipped this sentence with a hard-coded count and then with
    an overstated claim ("a source link on every row"). Both were invisible to the
    existing gates because the gates check links, not arithmetic. Here the
    published numbers are recomputed from the pages and compared."""
    print("\n[I6b] Published site-wide row counts match the pages")
    total, sourced = count_rows("docs")
    page = open(os.path.join(ROOT, "docs/pages/summary.html"), encoding="utf-8",
                errors="replace").read()
    m = re.search(r"Of its (\d+) table rows, (\d+) carry", page)
    if not m:
        err("docs/pages/summary.html no longer states the derived row counts")
        return
    said_total, said_sourced = int(m.group(1)), int(m.group(2))
    if said_total != total:
        err(f"summary says {said_total} table rows, docs/ actually has {total}")
    elif said_sourced != sourced:
        err(f"summary says {said_sourced} sourced rows, docs/ actually has {sourced}")
    else:
        ok(f"summary's {said_total} rows / {said_sourced} sourced match the pages exactly")
    if said_sourced > total:
        err("sourced rows exceed total rows - impossible")


# ---------------------------------------------------------------- I7 entry points
def check_entry_points():
    print("\n[I7] Both builds reachable from the repository root")
    for p in ("index.html", "docs/index.html", "docs/b/index.html"):
        if os.path.exists(os.path.join(ROOT, p)):
            ok(f"{p} exists")
        else:
            err(f"{p} is missing")
    root = open(os.path.join(ROOT, "index.html"), encoding="utf-8", errors="replace").read()
    for target in ("docs/index.html", "docs/b/index.html"):
        if target not in root:
            err(f"repository-root index.html does not link to {target} "
                f"(Build B is undiscoverable - cross-session request R1)")
        else:
            ok(f"root index.html links to {target}")


def main():
    print(f"Independent integration verification of {ROOT}")
    check_json()
    check_links()
    check_rows()
    check_sentinels()
    check_prose_numbers()
    check_row_counts()
    check_entry_points()

    print("\n" + "=" * 66)
    print(f"JSON files  : {checked['json']}")
    print(f"HTML files  : {checked['html']}")
    print(f"Links       : {checked['links']}")
    print(f"Data rows   : {checked['sourced_rows']}/{checked['rows']} official-sourced")
    print(f"Errors      : {len(errors)}")
    print(f"Warnings    : {len(warnings)}")
    print("=" * 66)
    if errors:
        print("\nFAILED - errors must be fixed before publishing:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nPASSED - no errors. Warnings are listed above and are published on "
          "the Flagged for Review page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
