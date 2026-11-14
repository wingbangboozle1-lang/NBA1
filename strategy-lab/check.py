"""Gate check for strategy-lab/**, using the repository's own rules.

The published checkers (scripts/check_links.py, scripts/verify_integration.py) scan
docs/ and command-center/, not this directory, so this file applies their rules here
instead of waiting for the integration seat to fold these pages into site/. Same allowlist,
same 'every tbody row carries a source link', same rectangular-table test, same sentinels.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

APPROVED = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
            "stats.nba.com", "data.nba.com", "cdn.nba.com", "kansspelautoriteit.nl",
            "github.com", "docs.github.com", "wingbangboozle1-lang.github.io"}
SENTINELS = [
    (re.compile(r">\s*None\s*<"), "'None' rendered into prose"),
    (re.compile(r">\s*nan\s*<", re.I), "'nan' rendered into prose"),
    (re.compile(r">\s*undefined\s*<", re.I), "'undefined' rendered into prose"),
    (re.compile(r">\s*NaN\s*<"), "'NaN' rendered into prose"),
    (re.compile(r"\{\{"), "unrendered '{{' template marker"),
    (re.compile(r"\bTODO\b"), "'TODO' left in a page"),
    (re.compile(r"INSERT[ _]HERE", re.I), "'INSERT HERE' placeholder"),
    (re.compile(r"Traceback \(most recent call last\)"), "python traceback pasted into a page"),
]
SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
HREF = re.compile(r'href="([^"]+)"')


def main():
    errors = 0
    files = sorted(os.path.join(b, f) for b, _d, fs in os.walk(HERE) for f in fs if f.endswith(".html"))
    for p in files:
        rel = os.path.relpath(p, ROOT)
        raw = open(p, encoding="utf-8").read()
        markup = SCRIPT_OR_STYLE.sub("", raw)
        prose = re.sub(r"<script\b[^>]*>.*?</script>", "", raw, flags=re.S | re.I)
        for rx, what in SENTINELS:
            for m in rx.finditer(prose):
                print(f"  ERROR {rel}: {what}")
                errors += 1
        for href in HREF.findall(raw):
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            if href.startswith(("http://", "https://")):
                host = urllib.parse.urlparse(href).netloc
                if host not in APPROVED:
                    print(f"  ERROR {rel}: non-approved host {host}")
                    errors += 1
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), href.split("#")[0]))
            if not os.path.exists(target):
                print(f"  ERROR {rel}: broken internal link {href}")
                errors += 1
        for thead, tbody in re.findall(r"<thead>(.*?)</thead>\s*<tbody>(.*?)</tbody>", markup, re.S):
            ncol = len(re.findall(r"<th[^>]*>", thead))
            for row in re.findall(r"<tr>(.*?)</tr>", tbody, re.S):
                ncells = len(re.findall(r"<td[^>]*>", row))
                if ncells and ncells != ncol:
                    print(f"  ERROR {rel}: ragged row, header {ncol} columns, row {ncells}")
                    errors += 1
        n_rows = n_src = 0
        for tbody in re.findall(r"<tbody>(.*?)</tbody>", markup, re.S):
            for row in re.findall(r"<tr>(.*?)</tr>", tbody, re.S):
                n_rows += 1
                if 'href="http' in row:
                    n_src += 1
                else:
                    print(f"  FLAG  {rel}: table row without a source link: "
                          f"{re.sub(r'<[^>]+>', ' ', row)[:80].strip()}")
                    errors += 1
        print(f"{rel:36} rows {n_rows:4}  rows with an official link {n_src:4}")
    for name in sorted(os.listdir(os.path.join(HERE, "data"))):
        if name.endswith(".json"):
            import json
            try:
                json.load(open(os.path.join(HERE, "data", name), encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR data/{name} does not parse: {e}")
                errors += 1
    print("-" * 78)
    print(f"RESULT: {'PASS' if not errors else 'FAIL'} ({errors} problem(s) in {len(files)} pages)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
