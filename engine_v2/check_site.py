"""Structural checks for the rendered site. Run before any merge.

Four questions, each a hard failure:

  1. INTERNAL LINKS  - every relative href/src resolves to a real file.
  2. EXTERNAL HOSTS  - every absolute href points at an approved host. A link to
                       anything else is a provenance failure.
  3. ROW PROVENANCE  - every row of every data table carries at least one link to
                       an approved host. Tables marked `class="definitions"` are
                       exempt and say so in their caption.
  4. NO PLACEHOLDERS - no unrendered `{...}`, `None`, `nan` or template literal
                       leaked into the output.
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APPROVED_HOSTS = {
    # official NBA properties - the only acceptable source for a statistic
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
    "stats.nba.com", "data.nba.com", "cdn.nba.com",
    # the repository and platform documentation, for provenance of the build
    "github.com", "docs.github.com", "raw.githubusercontent.com",
}

SITE = os.path.join(ROOT, "origination")
PAGES = ["origination/index.html"] + [
    "origination/pages/" + f
    for f in sorted(os.listdir(os.path.join(SITE, "pages"))) if f.endswith(".html")]

BAD_TEXT = [
    (re.compile(r"\{[a-z_]+[\[\"']"), "unrendered f-string placeholder"),
    (re.compile(r"\bnan\b"), "NaN leaked into output"),
    (re.compile(r">None<"), "None leaked into output"),
]


class RowLinkAudit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []          # (definitions: bool, rows: [has_official_link])
        self.cur = None
        self.in_tbody = False
        self.in_row = False
        self.row_links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.cur = {"defs": "definitions" in (a.get("class") or ""), "rows": []}
            self.tables.append(self.cur)
        elif tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.cur is not None and self.in_tbody:
            self.in_row = True
            self.row_links = []
        elif tag == "a" and self.in_row and a.get("href"):
            host = (urlparse(a["href"]).hostname or "").lower()
            if host in APPROVED_HOSTS:
                self.row_links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_tbody = False
        if tag == "tr" and self.in_row and self.cur is not None:
            self.cur["rows"].append(bool(self.row_links))
            self.in_row = False
        elif tag == "table":
            self.cur = None


def main():
    errors, notes = [], []
    for rel in PAGES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            errors.append(f"{rel}: MISSING")
            continue
        raw = open(path, encoding="utf-8").read()

        # 1. internal links (script blocks stripped: their strings are not links)
        html = re.sub(r"<script\b.*?</script>", "", raw, flags=re.S | re.I)
        base = os.path.dirname(path)
        for m in re.finditer(r'(?:href|src)="([^"#][^"]*)"', html):
            h = m.group(1)
            if re.match(r"^(https?:|mailto:|//)", h) or "${" in h:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, h.split("#")[0]))):
                errors.append(f"{rel}: broken internal link -> {h}")

        # 2. external hosts
        for m in re.finditer(r'href="(https?://[^"]+)"', raw):
            host = (urlparse(m.group(1)).hostname or "").lower()
            if host and host not in APPROVED_HOSTS:
                errors.append(f"{rel}: unapproved host {host} -> {m.group(1)}")

        # 3. row provenance
        audit = RowLinkAudit()
        audit.feed(raw)
        for i, t in enumerate(audit.tables):
            if t["defs"]:
                continue
            bad = [j for j, ok in enumerate(t["rows"]) if not ok]
            if bad:
                errors.append(f"{rel}: table {i} has {len(bad)} row(s) with no official source link "
                              f"(first at row {bad[0] + 1} of {len(t['rows'])})")
            else:
                notes.append(f"{rel}: table {i} - {len(t['rows'])} rows, all source-linked")

        # 4. placeholders
        text = re.sub(r"<script\b.*?</script>", "", raw, flags=re.S | re.I)
        for rx, why in BAD_TEXT:
            m = rx.search(text)
            if m:
                errors.append(f"{rel}: {why} near {text[max(0, m.start()-40):m.end()+20]!r}")

    if errors:
        print("FAIL")
        for e in errors:
            print("  -", e)
        return 1
    print(f"OK - {len(PAGES)} pages")
    for n in notes:
        print("   ", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
