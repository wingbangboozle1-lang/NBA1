#!/usr/bin/env python3
"""
check_links.py — prove the published site has no broken links before it is merged.

Two different questions, checked separately:

  1. INTERNAL links   — every relative href must resolve to a real file in docs/. A broken internal
                        link is a build failure and the merge must not happen.
  2. EXTERNAL links   — every absolute href must be present in the approved-host allowlist. The allowlist is
                        split by purpose: NBA hosts for statistics, the Dutch regulator for licensing questions,
                        and GitHub for build provenance. Reachability
                        cannot be tested from this sandbox (outbound access to nba.com is blocked at the
                        network layer), so this checks the host, not the HTTP status, and says so.
  3. EVERY TABLE ROW  — the brief requires each row to carry a source link. A table row with no <a>
                        in it is flagged.

Build B and the Command Center are rendered in the browser from same-origin JSON, so their pages
contain almost no static <tr> markup — the rows are built by JavaScript. Template literals inside a
<script> block look like markup to a regex and were being read as broken links and ragged rows. Those
blocks are therefore stripped before any structural check. The rendered output is checked separately
by scripts/check_rendered.py, which actually executes the page scripts.
"""
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SITE_ROOTS = [os.path.join(ROOT, "docs"), os.path.join(ROOT, "command-center")]

SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)

APPROVED_HOSTS = {
    # official NBA properties — the only acceptable source for a statistic
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
    "stats.nba.com", "data.nba.com", "cdn.nba.com",
    # regulatory: the Dutch gambling authority. Used for licensing questions only, never for a statistic.
    "kansspelautoriteit.nl",
    # the repository and platform documentation, for provenance of the build itself
    "github.com", "docs.github.com",
}

HREF = re.compile(r'href="([^"]+)"')


def main():
    pages = []
    for root in SITE_ROOTS:
        if not os.path.isdir(root):
            continue
        for base, _, files in os.walk(root):
            for f in files:
                if f.endswith(".html"):
                    pages.append(os.path.join(base, f))
    pages.sort()

    broken_internal = []
    bad_hosts = []
    external_links = set()
    rows_without_source = []
    rows_explicitly_unverified = []
    ragged = []
    total_rows = 0
    total_links = 0
    script_blocks = 0

    for p in pages:
        rel = os.path.relpath(p, DOCS)
        with open(p, encoding="utf-8") as fh:
            html = fh.read()

        # <script> bodies are client-side templates rendered from JSON at load time. Their href and
        # row markup is not static HTML, so it is not scanned here. They are counted and reported.
        script_blocks += len(re.findall(r"<script\b[^>]*>.*?</script>", html, re.S))
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
        markup = SCRIPT_OR_STYLE.sub("", html)

        for href in HREF.findall(html):
            total_links += 1
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            if href.startswith("http://") or href.startswith("https://"):
                host = urlparse(href).netloc
                external_links.add(href)
                if host not in APPROVED_HOSTS:
                    bad_hosts.append((rel, href))
                continue
            # internal: resolve relative to the page
            target = os.path.normpath(os.path.join(os.path.dirname(p), href.split("#")[0]))
            if not os.path.exists(target):
                broken_internal.append((rel, href))

        # every table must be rectangular: a row with the wrong number of cells means the header
        # and body disagree, which is what a botched in-place patch looks like
        for thead, tbody in re.findall(r"<thead>(.*?)</thead>\s*<tbody>(.*?)</tbody>", markup, re.S):
            ncol = len(re.findall(r"<th[^>]*>", thead))
            for row in re.findall(r"<tr>(.*?)</tr>", tbody, re.S):
                ncells = len(re.findall(r"<td[^>]*>", row))
                if ncells and ncells != ncol:
                    ragged.append((rel, ncol, ncells))

        # table rows must carry a source link
        for tbl in re.findall(r"<tbody>(.*?)</tbody>", markup, re.S):
            for row in re.findall(r"<tr>(.*?)</tr>", tbl, re.S):
                total_rows += 1
                if "<a " not in row:
                    # A design-register row (a validation gate, a proposal, a legal-scope item) states
                    # no NBA value, so it has no official source to cite. The build marks those rows
                    # explicitly as unverified with a reason, which is the honest alternative to a
                    # fabricated link. They are counted separately and never as a pass.
                    flat = re.sub(r"<[^>]+>", " ", row)
                    if "unverified" in flat.lower() or "no official source" in flat.lower():
                        rows_explicitly_unverified.append(
                            (rel, " ".join(flat.split())[:90]))
                    else:
                        rows_without_source.append((rel, re.sub(r"<[^>]+>", "", row)[:70].strip()))

    print("=" * 78)
    print("LINK AND SOURCING REPORT — docs/ and command-center/")
    print("=" * 78)
    print(f"  pages scanned        : {len(pages)}")
    print(f"  links found          : {total_links}")
    print(f"  distinct external    : {len(external_links)}")
    print(f"  table rows           : {total_rows}")
    print(f"  internal broken      : {len(broken_internal)}")
    print(f"  non-approved hosts   : {len(bad_hosts)}")
    print(f"  rows without a source: {len(rows_without_source)}")
    print(f"  rows marked unverified: {len(rows_explicitly_unverified)} (no NBA value; reason stated)")
    print(f"  ragged table rows    : {len(ragged)}")
    print(f"  client-side scripts  : {script_blocks} (rendered from JSON; not statically scanned)")

    for r, h in broken_internal:
        print(f"  ERROR broken internal link in {r}: {h}")
    for r, h in bad_hosts:
        print(f"  ERROR non-approved host in {r}: {h}")
    for r, ncol, ncells in ragged[:10]:
        print(f"  ERROR ragged row in {r}: header has {ncol} columns, row has {ncells}")
    for r, t in rows_without_source:
        print(f"  FLAG  table row without source link in {r}: {t}")
    for r, t in rows_explicitly_unverified:
        print(f"  see   explicitly unverified in {r}: {t}")

    print("-" * 78)
    print("note: external links are checked for approved host only. Outbound access to nba.com is")
    print("      blocked from this sandbox, so HTTP status cannot be verified here and is not claimed.")
    print("note: rows inside client-side scripts are rendered from JSON and are not counted here.")
    ok = not broken_internal and not bad_hosts and not ragged
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
