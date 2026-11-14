#!/usr/bin/env python3
"""verify_dashboard.py — audit the unified site (index.html + site/pages/**).

Checks, and fails on the first problem found:
  1. every table row on every generated page has a source link in its last cell,
     or that cell explicitly marks the value as unavailable with a non-empty reason;
  2. every internal link and asset reference resolves to a file that exists;
  3. every external link is https and on an allowed official host;
  4. no unresolved merge markers and no empty page.

This is a structural/provenance check. It does not fetch sources or verify that
published values agree with the linked pages.

Exit 0 = pass.
"""
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
           "cdn.nba.com", "docs.github.com", "github.com", "kansspelautoriteit.nl",
           "www.kansspelautoriteit.nl", "www.monumentalsportsnetwork.com",
           "nbatickets.nba.com", "a.data.nba.com", "www.peacocktv.com",
           "www.amazon.com", "nbatv.com"}

errors = []
PAGES = [os.path.join(ROOT, "index.html")]
for name in sorted(os.listdir(os.path.join(ROOT, "site", "pages"))):
    if name.endswith(".html"):
        PAGES.append(os.path.join(ROOT, "site", "pages", name))


class TableScan(HTMLParser):
    """Collect every table row's cells, plus every link, per page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []          # list of list-of-cell dicts
        self.tables = []        # per table: {"header": [...], "rows": [...]}
        self.links = []         # (href, text)
        self._cell = None
        self._row = None
        self._in_table = False
        self._in_head = False
        self._row_is_header = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "table":
            self._in_table = True
            self._tbl = {"header": [], "rows": []}
        elif tag == "thead":
            self._in_head = True
        elif tag == "tr" and self._in_table:
            self._row = []
            self._row_is_header = self._in_head
        elif tag in ("td", "th") and self._row is not None:
            classes = (d.get("class", "") or "").split()
            self._cell = {
                "text": "",
                "links": [],
                "cls": d.get("class", ""),
                "na": "na" in classes,
                "na_reason": d.get("title", "").strip(),
            }
        elif tag == "a" and self._cell is not None:
            href = d.get("href", "")
            self._cell["links"].append(href)
        elif tag == "span" and self._cell is not None:
            if "na" in (d.get("class", "") or "").split():
                self._cell["na"] = True
                self._cell["na_reason"] = d.get("title", "").strip() or self._cell["na_reason"]

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row_is_header:
                self._tbl["header"] = self._row
            else:
                self.rows.append(self._row)
                self._tbl["rows"].append(self._row)
            self._row = None
        elif tag == "thead":
            self._in_head = False
        elif tag == "table":
            self._in_table = False
            self.tables.append(self._tbl)


def is_official(url):
    p = urlparse(url)
    return p.scheme == "https" and p.netloc in ALLOWED


def main():
    total_rows = 0
    sourced_rows = 0
    explicit_no_source_rows = 0
    unexplained_markers = 0
    unmarked_missing_rows = 0
    for path in PAGES:
        rel = os.path.relpath(path, ROOT)
        text = open(path, encoding="utf-8").read()
        if len(text) < 400:
            errors.append("%s: page looks empty" % rel)
        if "<<<<<<<" in text or ">>>>>>>" in text:
            errors.append("%s: unresolved merge markers" % rel)

        scan = TableScan()
        try:
            scan.feed(text)
        except Exception as exc:
            errors.append("%s: HTML parse error: %s" % (rel, exc))
            continue

        # every table row must have exactly as many cells as its header row
        for ti, tbl in enumerate(scan.tables):
            if not tbl["header"]:
                errors.append("%s: table %d has no header row" % (rel, ti + 1))
                continue
            ncol = len(tbl["header"])
            for ri, row in enumerate(tbl["rows"]):
                if len(row) != ncol:
                    errors.append("%s: table %d row %d has %d cells, the header has %d"
                                  % (rel, ti + 1, ri + 1, len(row), ncol))

        for i, row in enumerate(scan.rows):
            total_rows += 1
            last = row[-1]
            off = [h for h in last["links"] if is_official(h)]
            marked = last.get("na") or ("na" in (last.get("cls") or "").split())
            if off:
                sourced_rows += 1
            elif marked:
                reason = (last.get("na_reason") or "").strip()
                if reason:
                    explicit_no_source_rows += 1
                else:
                    unexplained_markers += 1
                    errors.append("%s: table row %d marks its source as unavailable without an explanation"
                                  % (rel, i + 1))
            else:
                unmarked_missing_rows += 1
                errors.append("%s: table row %d has no official source link in its last cell: %r"
                              % (rel, i + 1, last["text"][:60]))

        # links
        for href in re.findall(r'(?:href|src)="([^"]+)"', re.sub(r"<script\b.*?</script>", "", text, flags=re.S | re.I)):
            if href.startswith(("http://", "https://", "#", "mailto:", "//")):
                if href.startswith("http://"):
                    errors.append("%s: insecure external link %s" % (rel, href))
                if href.startswith("https://") and not is_official(href):
                    errors.append("%s: external link off an allowed official host: %s" % (rel, href))
                continue
            target = href.split("#")[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(resolved):
                errors.append("%s: broken internal link -> %s" % (rel, href))

    print("pages checked                         : %d" % len(PAGES))
    print("table rows checked                    : %d" % total_rows)
    print("rows with an allowed official source  : %d / %d" % (sourced_rows, total_rows))
    print("rows marked no-source with a reason   : %d / %d" % (explicit_no_source_rows, total_rows))
    print("unmarked rows without an official link: %d" % unmarked_missing_rows)
    print("no-source markers without a reason   : %d" % unexplained_markers)
    if errors:
        print("\nVERIFY FAILED")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("\nVERIFY OK - every row has an allowed official source link or an explicit, reasoned no-source mark; all internal links resolve.")
    print("NOTE - this checks provenance/link structure only; it does not fetch sources or compare their values to the published rows.")


if __name__ == "__main__":
    main()
