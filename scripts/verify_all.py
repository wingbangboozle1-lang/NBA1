#!/usr/bin/env python3
"""End-to-end verification for the NBA1 repository (integration gate).

Runs, in order, and fails on the first error:
  1. scripts/build_site.py        — docs/ snapshot build (source/link validation)
  2. scripts/build_edge_site.py   — Edge Lab pages + originated-lines audit record
  3. scripts/check_site.py        — root pages: local links + official source per table row
  4. Data audits (this file):
       - every slate/game row has an allowed official source URL
       - every injury row carries the official PDF source; team/matchup blanking rules hold
       - every leader row has an allowed official source URL
       - originated_lines.json covers every slate game and reproduces the pick count
       - no rendered HTML page contains unresolved merge markers
       - every root HTML page parses and every internal href target exists
Exit 0 = pass. Any failure prints a list and exits 1.
"""
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = {"www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com",
           "cdn.nba.com", "docs.github.com", "github.com", "kansspelautoriteit.nl",
           "www.kansspelautoriteit.nl"}
errors = []


def run(script):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        errors.append(f"{script} failed:\n{r.stdout}\n{r.stderr}")
    return r.returncode == 0


def load(name):
    with open(os.path.join(ROOT, "data", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def ok_url(u):
    if not u:
        return False
    p = urlparse(u)
    return p.scheme == "https" and p.netloc in ALLOWED


# 1–3: builders + checker
run("build_site.py")
run("build_edge_site.py")
run("check_site.py")

# 4a: slate sources
slate = load("slate_full")
n_games = 0
for s in slate["slates"]:
    if not ok_url(s["slate_url"]):
        errors.append(f"slate {s['date']}: bad slate_url")
    for g in s["games"]:
        n_games += 1
        if not ok_url(g["preview_url"]):
            errors.append(f"game {s['date']} {g['away']}@{g['home']}: bad preview_url")
        if not (g["away_record"] and g["home_record"]):
            errors.append(f"game {s['date']} {g['away']}@{g['home']}: blank record")
if n_games != 36:
    errors.append(f"expected 36 window games (11/13-11/17), found {n_games}")

# prior games (rest inputs) must all carry official slate URLs
for p in slate["prior_games"]:
    if not ok_url(p["slate_url"]):
        errors.append(f"prior {p['date']}: bad slate_url")

# 4b: injuries source + blanking rules
inj = load("injuries_0515")
if not ok_url(inj["source_url"]):
    errors.append("injuries_0515: bad source_url")
for r in inj["rows"]:
    if not r.get("team"):
        errors.append(f"injury row without team in main table: {r.get('player')}")
for r in inj["unattributed_rows"]:
    if r.get("team"):
        errors.append(f"unattributed row unexpectedly has team: {r.get('player')}")

# archived dataset: no implied matchups may remain filled
arch = load("injuries")
for r in arch["rows"]:
    if r.get("matchup") and str(r.get("matchup_basis", "")).startswith("implied"):
        errors.append(f"archived injury row still has implied matchup: {r.get('player')}")
    if not ok_url(r.get("source_url")):
        errors.append(f"archived injury row bad source: {r.get('player')}")

# 4c: leaders
leaders = load("leaders")
for l in leaders["leaders"]:
    if not ok_url(l.get("source_url")):
        errors.append(f"leader {l.get('team')}: bad source_url")
    if l.get("player") is None and not l.get("blank_reason"):
        errors.append(f"leader {l.get('team')}: blank without blank_reason")

# 4d: originated lines audit coverage
audit = load("originated_lines")
if len(audit["games"]) != n_games:
    errors.append("originated_lines.json does not cover every slate game")
picks = sum(1 for g in audit["games"] if g["model"] and g["model"]["pick_side"] != "PASS")
if picks != audit["n_model_picks"]:
    errors.append("pick count mismatch in originated_lines.json")
for g in audit["games"]:
    for u in g["sources"]:
        if not ok_url(u):
            errors.append(f"audit game {g['matchup']}: bad source {u}")

# 4e: pages — parse, no merge markers, internal hrefs exist
ROOT_PAGES = [f for f in os.listdir(ROOT) if f.endswith(".html")]
DOCS_PAGES = ["docs/" + f for f in os.listdir(os.path.join(ROOT, "docs")) if f.endswith(".html")]

class LinkScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            if d.get("href"):
                self.hrefs.append(d["href"])


for rel in sorted(ROOT_PAGES + DOCS_PAGES):
    path = os.path.join(ROOT, rel)
    text = open(path, encoding="utf-8").read()
    if "<<<<<<<" in text or ">>>>>>>" in text:
        errors.append(f"{rel}: unresolved merge markers")
    scan = LinkScan()
    try:
        scan.feed(text)
    except Exception as exc:
        errors.append(f"{rel}: HTML parse error: {exc}")
        continue
    base = os.path.dirname(path)
    for href in scan.hrefs:
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = href.split("#")[0]
        if not target:
            continue
        resolved = os.path.normpath(os.path.join(base, target))
        if not os.path.isfile(resolved):
            errors.append(f"{rel}: broken internal link -> {href}")

# 4f: no stray conflict markers anywhere in tracked text files
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
    for fn in filenames:
        if fn.endswith((".html", ".json", ".md", ".py", ".css", ".js")):
            p = os.path.join(dirpath, fn)
            try:
                t = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            if t.startswith("<<<<<<<") or "\n<<<<<<<" in t:
                errors.append(f"{os.path.relpath(p, ROOT)}: merge conflict markers")

if errors:
    print("\nVERIFY FAILED")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\nVERIFY OK — builders, checker, and data audits all passed.")
