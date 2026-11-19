#!/usr/bin/env python3
"""check_build_data.py - every build's pages must have the data they fetch.

WHY THIS EXISTS (COORDINATION.md §69.6, session `arena/89f7b601-nba1`)

`docs/b/` is build B, one of three entry points in this repository. Its pages
resolve their data from the script's own `src` (see `DATA_PREFIX` in
`docs/assets/site.js`), which means a page at `docs/b/pages/flagged.html` fetches
`docs/b/data/flagged.json`. `engine/build_site.py` wrote the 17 pages and never
wrote that directory.

The result: every build-B page loaded its chrome, ran its script, and failed its
fetch. `docs/b/pages/flagged.html` rendered an empty `<div id="items">` - on the
live site, for as long as build B has existed. It passed every existing gate,
because:

  * `check_site.py` checks that pages exist and that local links resolve; a
    page that exists and links correctly but fetches nothing is "fine";
  * `check_rendered.py` executes the Command Center pages, which is a different
    build with its own data;
  * `verify_all.py` audits rows and provenance in built tables, and an empty
    table has no rows to audit.

The defect is silent in exactly the way the board keeps flagging: the page looks
like a page. This check catches it structurally, without a browser: for every
build directory that has pages, resolve the data URL each page's script will
build, and require the file to exist and to be valid JSON.

Builds checked, and how each one's data prefix is derived:

  docs/b/    pages at docs/b/pages/*.html, script at ../../assets/site.js
             -> prefix "../../" -> docs/b/data/*.json
  site/      pages at site/pages/*.html,      script at ../assets/site.js
             -> prefix "../"     -> site/data/*.json
  docs/      top-level pages,                 script at assets/site.js
             -> prefix ""        -> docs/data/*.json
  command-center/  checked by check_rendered.py, skipped here

Exit 0 when every page in every build can load every data file its script names.
Exit 1 with the exact missing path otherwise.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every literal DATA("<name>.json") in a page's own inline script, plus the
# data files each build's JS references by name. Parsing the JS for every
# possible name would be guesswork; the pages that ship a script are the set
# that matters, and a page with no script has no fetch to fail.
DATA_CALL_RE = re.compile(r'DATA\(\s*"([A-Za-z0-9_\-]+\.json)"\s*\)')
SCRIPT_SRC_RE = re.compile(r'<script[^>]*src="([^"]*site\.js)"')

# Data files the shared site.js itself names, for pages whose script comes from
# SCRIPTS in engine/build_site.py rather than from the page's own inline block.
SHARED_FILES = [
    "meta.json", "sources.json", "teams.json", "lines.json", "picks.json",
    "props.json", "injuries.json", "gameflow.json", "backtest.json",
    "validation.json", "leaderboard.json", "correlations.json", "luck.json",
    "flagged.json", "questions.json", "suggestions.json", "executive.json",
]

# (label, directory holding the build's pages). The data directory is NOT
# assumed: it is derived from each page's own script src, because that is what
# the browser will do. Build B (`docs/b/pages/*.html`) resolves to `docs/data`,
# not to `docs/b/data` - the pages point at ../../assets/site.js, whose
# DATA_PREFIX keeps everything before "assets/site.js", i.e. "../../". Assuming
# a per-build data directory produced exactly the false alarm this check now
# prevents, so the resolution is computed rather than declared.
BUILDS = [
    ("docs/b", os.path.join(ROOT, "docs", "b", "pages")),
    ("site", os.path.join(ROOT, "site", "pages")),
    ("docs", os.path.join(ROOT, "docs")),
]


def build_data_prefix(page_path, script_src):
    """The data directory a page's script will actually fetch from.

    DATA_PREFIX in docs/assets/site.js slices the script's own src at the
    literal "assets/site.js" and keeps what precedes it, then appends "data/".
    So the base is the directory CONTAINING assets/, not assets/ itself:
    "../../assets/site.js" -> prefix "../../" -> <repo>/data at root depth.
    """
    page_dir = os.path.dirname(page_path)
    idx = script_src.find("assets/site.js")
    if idx < 0:
        return None
    prefix = script_src[:idx]
    base = os.path.normpath(os.path.join(page_dir, prefix)) if prefix else page_dir
    return os.path.join(base, "data")


def main():
    problems = []
    checked_pages = 0
    checked_files = 0
    resolved = set()
    for label, pages_dir in BUILDS:
        if not os.path.isdir(pages_dir):
            problems.append(f"{label}: pages directory missing: {pages_dir}")
            continue
        pages = sorted(f for f in os.listdir(pages_dir) if f.endswith(".html"))
        for name in pages:
            path = os.path.join(pages_dir, name)
            with open(path, encoding="utf-8") as fh:
                html = fh.read()
            checked_pages += 1
            m = SCRIPT_SRC_RE.search(html)
            if not m:
                continue        # page ships no script, so it fetches nothing
            # Where the page's script will look for data. This must exist and
            # hold JSON, or the page renders empty on the live site.
            target = build_data_prefix(path, m.group(1))
            if target is None:
                problems.append(f"{label}/{name}: script src {m.group(1)!r} "
                                f"has no assets/site.js component")
                continue
            if not os.path.isdir(target):
                problems.append(
                    f"{label}/{name}: script src {m.group(1)!r} resolves its "
                    f"data to {os.path.relpath(target, ROOT)}, which does not "
                    f"exist - the page would fetch nothing and render empty")
                continue
            resolved.add(os.path.relpath(target, ROOT))
            # Every file the page's own inline script names, plus the shared set.
            wanted = set(DATA_CALL_RE.findall(html))
            if not wanted:
                wanted = set(SHARED_FILES)
            for fn in sorted(wanted):
                fp = os.path.join(target, fn)
                checked_files += 1
                if not os.path.exists(fp):
                    problems.append(
                        f"{label}/{name}: fetches {fn} but "
                        f"{os.path.relpath(fp, ROOT)} does not exist")
                    continue
                try:
                    with open(fp, encoding="utf-8") as fh:
                        json.load(fh)
                except ValueError as exc:
                    problems.append(
                        f"{label}/{name}: {os.path.relpath(fp, ROOT)} is not "
                        f"valid JSON ({exc})")
    print(f"checked {checked_pages} page(s) across {len(BUILDS)} build(s); "
          f"{checked_files} page->data reference(s)")
    print("data directories resolved:", ", ".join(sorted(resolved)) or "none")
    for p in problems:
        print("BROKEN:", p)
    if problems:
        print(f"RESULT: FAIL — {len(problems)} problem(s)")
        return 1
    print("RESULT: PASS — every page can load every data file it fetches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
