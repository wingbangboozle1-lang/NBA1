#!/usr/bin/env python3
"""
check_links.py — prove the published site has no broken links before it is merged.

Two different questions, checked separately:

  1. INTERNAL links   — every relative href must resolve to a real file in docs/. A broken internal
                        link is a build failure and the merge must not happen.
  2. EXTERNAL links   — every absolute href must be present in the approved-host allowlist. Reachability
                        cannot be tested from this sandbox (outbound access to nba.com is blocked at the
                        network layer), so this checks the host, not the HTTP status, and says so.
  3. EVERY TABLE ROW  — the brief requires each row to carry a source link. A table row with no <a>
                        in it is flagged.
"""
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

APPROVED_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
    "stats.nba.com", "data.nba.com", "cdn.nba.com",
}

HREF = re.compile(r'href="([^"]+)"')


def main():
    pages = []
    for base, _, files in os.walk(DOCS):
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(base, f))
    pages.sort()

    broken_internal = []
    bad_hosts = []
    external_links = set()
    rows_without_source = []
    total_rows = 0
    total_links = 0

    for p in pages:
        rel = os.path.relpath(p, DOCS)
        with open(p, encoding="utf-8") as fh:
            html = fh.read()

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

        # table rows must carry a source link
        for tbl in re.findall(r"<tbody>(.*?)</tbody>", html, re.S):
            for row in re.findall(r"<tr>(.*?)</tr>", tbl, re.S):
                total_rows += 1
                if "<a " not in row:
                    rows_without_source.append((rel, re.sub(r"<[^>]+>", "", row)[:70].strip()))

    print("=" * 78)
    print("LINK AND SOURCING REPORT — docs/")
    print("=" * 78)
    print(f"  pages scanned        : {len(pages)}")
    print(f"  links found          : {total_links}")
    print(f"  distinct external    : {len(external_links)}")
    print(f"  table rows           : {total_rows}")
    print(f"  internal broken      : {len(broken_internal)}")
    print(f"  non-approved hosts   : {len(bad_hosts)}")
    print(f"  rows without a source: {len(rows_without_source)}")

    for r, h in broken_internal:
        print(f"  ERROR broken internal link in {r}: {h}")
    for r, h in bad_hosts:
        print(f"  ERROR non-approved host in {r}: {h}")
    for r, t in rows_without_source:
        print(f"  FLAG  table row without source link in {r}: {t}")

    print("-" * 78)
    print("note: external links are checked for approved host only. Outbound access to nba.com is")
    print("      blocked from this sandbox, so HTTP status cannot be verified here and is not claimed.")
    ok = not broken_internal and not bad_hosts
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
