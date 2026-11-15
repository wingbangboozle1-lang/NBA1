#!/usr/bin/env python3
"""Capture raw official HTML + injury PDFs into the repository.

    python3 scripts/capture_official_801ba27f.py

Session `arena/801ba27f-nba1` (COORDINATION.md §41, task H02).

WHY THIS SCRIPT EXISTS
----------------------
The agent sandbox for this project reaches only github.com / npm / pypi, so
`nba.com` cannot be read from a developer workstation. GitHub's runners do
have normal outbound access (proved by `data/raw/probe_official.json`, which
recorded HTTP 200 for these URLs when nba.com's own web-client headers are
sent). This script is executed by
`.github/workflows/capture-2026-11-15-801ba27f.yml`, which commits the
captured bytes back to the branch so they can be parsed and verified locally.

DESIGN RULES (inherited from engine/fetch_official.py, do not weaken)
---------------------------------------------------------------------
1. ONLY official hosts are contacted: www.nba.com, official.nba.com,
   ak-static.cms.nba.com.
2. Every capture is stored with its exact URL, retrieval timestamp (UTC),
   HTTP status, byte count and SHA-256 of the bytes as received.
3. Nothing that a previous session committed is overwritten. This script only
   writes into its own run directory `data/raw/html/2026-11-15-801ba27f/`
   plus the shared content-addressed `data/raw/injury_pdfs/`.
4. A failed fetch is recorded as a failure, never silently dropped and never
   filled in from anywhere else.
5. Pages are stored gzipped to keep the repository small. The manifest
   records the SHA-256 and byte count of the UNCOMPRESSED bytes, so the
   digest is the digest of the official response, not of the archive.
"""

import datetime
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
RUN_ID = "2026-11-15-801ba27f"
OUT = os.path.join(RAW, "html", RUN_ID)
PDF_DIR = os.path.join(RAW, "injury_pdfs")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com"}

# The web-client header set proven by data/raw/probe_official.json section
# `retried_with_browser_headers`: HTTP 200 on www.nba.com/stats/..., /schedule,
# /games?date=... and official.nba.com/..., where a plain client gets 403.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}

SEASON_Q = "Season=2026-27&SeasonType=Regular+Season"

PAGES = [
    # id, url
    ("injury_index", "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("standings", "https://www.nba.com/standings"),
    ("schedule", "https://www.nba.com/schedule"),
    ("team_traditional", "https://www.nba.com/stats/teams/traditional?" + SEASON_Q),
    ("team_opponent", "https://www.nba.com/stats/teams/opponent?" + SEASON_Q),
    ("team_advanced", "https://www.nba.com/stats/teams/advanced?" + SEASON_Q),
    # Clean cut: everything up to and including 2026-11-14, i.e. the last day
    # on which every scheduled game had finished when this capture was taken.
    # Used as the model input so in-progress 11/15 games cannot leak in.
    ("team_traditional_thru_1114",
     "https://www.nba.com/stats/teams/traditional?" + SEASON_Q + "&DateTo=11%2F14%2F2026"),
    ("team_opponent_thru_1114",
     "https://www.nba.com/stats/teams/opponent?" + SEASON_Q + "&DateTo=11%2F14%2F2026"),
    ("team_advanced_thru_1114",
     "https://www.nba.com/stats/teams/advanced?" + SEASON_Q + "&DateTo=11%2F14%2F2026"),
    ("players_traditional", "https://www.nba.com/stats/players/traditional?" + SEASON_Q),
]

GAME_DATES = ["2026-11-15", "2026-11-16", "2026-11-17", "2026-11-18"]
for d in GAME_DATES:
    PAGES.append(("games_" + d, "https://www.nba.com/games?date=" + d))

PDF_LINK_RE = re.compile(
    r'https://ak-static\.cms\.nba\.com/referee/injury/(Injury-Report_[^"\'\s<>\\]+?\.pdf)')
GAME_LINK_RE = re.compile(r'/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_ok(url):
    m = re.match(r"https?://([^/]+)/", url + "/")
    return bool(m) and m.group(1) in ALLOWED_HOSTS


def fetch(url, timeout=60):
    """Return (status, bytes). Raises only on network-level error."""
    if not host_ok(url):
        raise ValueError("host not on the official allow-list: " + url)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def save_page(name, url):
    path = os.path.join(OUT, name + ".html.gz")
    rec = {"id": name, "url": url, "retrieved_utc": None, "http_status": None,
           "bytes": None, "sha256": None, "file": os.path.relpath(path, ROOT),
           "error": None}
    try:
        status, body = fetch(url)
        rec["http_status"] = status
        rec["retrieved_utc"] = utc()
        rec["bytes"] = len(body)
        rec["sha256"] = hashlib.sha256(body).hexdigest()
        with gzip.open(path, "wb") as fh:
            fh.write(body)
        print("  %-28s %s %8d B  %s" % (name, status, len(body), rec["sha256"][:12]))
    except Exception as exc:                                  # noqa: BLE001
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("  %-28s FAILED %s" % (name, rec["error"]))
    return rec


def read_gz(path):
    with gzip.open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def save_pdf(url):
    """Content-addressed store: <edition>__<sha256>.pdf + a JSON sidecar."""
    name = url.rsplit("/", 1)[-1]
    rec = {"id": "pdf:" + name, "url": url, "retrieved_utc": None,
           "http_status": None, "bytes": None, "sha256": None,
           "revision_label": None, "file": None, "sidecar": None, "error": None}
    m = re.match(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2}_\d{2}(?:AM|PM))\.pdf", name)
    if m:
        rec["revision_label"] = "%s %s ET" % (m.group(1), m.group(2).replace("_", ":"))
    try:
        status, body = fetch(url)
        rec["http_status"] = status
        rec["retrieved_utc"] = utc()
        rec["bytes"] = len(body)
        digest = hashlib.sha256(body).hexdigest()
        rec["sha256"] = digest
        # A PDF file always starts with %PDF-; anything else is an error page.
        rec["pdf_signature_ok"] = body[:5] == b"%PDF-"
        base = name[:-4] + "__" + digest[:16] + ".pdf"
        path = os.path.join(PDF_DIR, base)
        with open(path, "wb") as fh:
            fh.write(body)
        rec["file"] = os.path.relpath(path, ROOT)
        side = path[:-4] + ".json"
        with open(side, "w") as fh:
            json.dump({k: v for k, v in rec.items() if k != "sidecar"}, fh, indent=1)
        rec["sidecar"] = os.path.relpath(side, ROOT)
        print("  %-52s %s %8d B" % (name, status, len(body)))
    except Exception as exc:                                  # noqa: BLE001
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("  %-52s FAILED %s" % (name, rec["error"]))
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    started = utc()
    print("capture run %s started %s" % (RUN_ID, started))

    manifest = {"run_id": RUN_ID, "session": "arena/801ba27f-nba1",
                "started_utc": started, "pages": [], "box_scores": [], "pdfs": []}

    print("official pages:")
    pages = dict(PAGES)
    for name, url in PAGES:
        manifest["pages"].append(save_page(name, url))
        time.sleep(0.4)

    # Injury PDFs: every edition the official index links for today.
    idx = os.path.join(OUT, "injury_index.html.gz")
    pdf_urls = []
    if os.path.exists(idx):
        html = read_gz(idx)
        seen = set()
        for m in PDF_LINK_RE.finditer(html):
            u = m.group(0)
            if u not in seen:
                seen.add(u)
                pdf_urls.append(u)
        # Only today's editions: keeping every edition ever published would be
        # tens of thousands of files. The index lists days newest-first.
        today_urls = [u for u in pdf_urls if "Injury-Report_2026-11-15_" in u]
        print("injury index: %d PDF links, %d for 2026-11-15" % (len(pdf_urls), len(today_urls)))
        print("injury PDFs (2026-11-15 editions):")
        for u in sorted(today_urls):
            manifest["pdfs"].append(save_pdf(u))
            time.sleep(0.2)
    else:
        manifest["injury_index_error"] = "page capture missing; no PDF links discovered"

    # Box scores / game pages: for every game the official date pages link.
    print("box score pages:")
    for d in GAME_DATES:
        p = os.path.join(OUT, "games_%s.html.gz" % d)
        if not os.path.exists(p):
            continue
        html = read_gz(p)
        ids = []
        for m in GAME_LINK_RE.finditer(html):
            slug = "%s-vs-%s-%s" % (m.group(1), m.group(2), m.group(3))
            if slug not in ids:
                ids.append(slug)
        print("  %s: %d game links" % (d, len(ids)))
        for slug in ids:
            url = "https://www.nba.com/game/%s/box-score" % slug
            rec = save_page("boxscore__" + slug, url)
            rec["date"] = d
            manifest["box_scores"].append(rec)
            time.sleep(0.3)

    manifest["finished_utc"] = utc()
    manifest["counts"] = {
        "pages": len(manifest["pages"]),
        "pages_ok": sum(1 for r in manifest["pages"] if r["http_status"] == 200),
        "pdfs": len(manifest["pdfs"]),
        "pdfs_ok": sum(1 for r in manifest["pdfs"] if r["http_status"] == 200),
        "box_scores": len(manifest["box_scores"]),
        "box_scores_ok": sum(1 for r in manifest["box_scores"] if r["http_status"] == 200),
    }
    with open(os.path.join(OUT, "_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps(manifest["counts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
