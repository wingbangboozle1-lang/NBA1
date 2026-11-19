#!/usr/bin/env python3
"""capture_official_e3d25abc.py — runner-side, byte-exact official capture for
session arena/e3d25abc-nba1 (COORDINATION §67 Q02).

WHAT THIS FETCHES (and nothing else)
------------------------------------
1. The official injury-report **index**
   (https://official.nba.com/nba-injury-report-2026-27-season/) — stored, then
   enumerated.  Every edition the league lists for the requested days is fetched
   from https://ak-static.cms.nba.com/referee/injury/<edition> as **PDF bytes**,
   unless that exact edition name is already archived in `data/raw/injury_pdfs/`.
   Requirement line: "Store every injury PDF with its timestamp".
2. The official **gamebook PDF** of every game the per-day scoreboard marks Final
   on the requested result days:
   https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf
   The gamebook is the league's own box-score document: it prints SCORE BY PERIOD
   (the line score) and every player's MIN/FG/3P/FT/OR/DR/TOT/A/PF/ST/TO/BS/+/-PTS,
   plus DNP/DND and the Inactive line.  Requirement line: "Capture per-player game
   logs (minutes, points, rebounds, assists, and the opponent)".
3. The per-day scoreboard page HTML for the result days AND for the rolling
   slate days, gzipped, so the parse can be re-run locally on stored bytes.

WHY A RUNNER
------------
This sandbox reaches only github.com / api.github.com / npm / pypi, so nba.com
cannot be read from the agent (fetch_page renders a page, it does not give
bytes).  The GitHub Actions runner has normal outbound access, and the pattern is
already proven twice in this repo (engine/fetch_official.py, and
scripts/capture_official_ca442d3d.py which this script extends).  Putting the
fetch on the runner means every published value traces to a stored,
content-addressed official artifact rather than to a memory of a page.

RULES (inherited; do not weaken)
--------------------------------
* Only the four official hosts are contacted; any other host raises ValueError.
* Every artifact is stored content-addressed with a sidecar carrying the exact
  URL, the retrieval timestamp (UTC), the HTTP status, the byte count and the
  SHA-256 of the bytes as received.  A response whose first KiB carries no
  `%PDF-` signature is recorded as a failure and NOT stored.
* A failed fetch is recorded, never dropped silently and never filled in from
  anywhere else.
* Nothing is overwritten: everything lands inside `data/raw/session-e3d25abc/`.
* This script publishes **no parsed number**.  Parsing happens locally on the
  stored bytes (scripts/e3d25abc_injury_chain.py,
  scripts/e3d25abc_game_logs.py) so extraction can be re-run and audited.

Usage:
  python3 scripts/capture_official_e3d25abc.py \
      --injury-days 2026-11-17,2026-11-18,2026-11-19 \
      --result-days 2026-11-17,2026-11-18 \
      --slate-days 2026-11-19,2026-11-20
"""

from __future__ import annotations

import argparse
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
OUT_ROOT = os.path.join(ROOT, "data", "raw", "session-e3d25abc")
ARCHIVE_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com",
                 "statsdmz.nba.com"}

INJURY_HOST = "https://ak-static.cms.nba.com/referee/injury/"
INJURY_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"

# The web-client header set proven by data/raw/probe_official.json to return
# HTTP 200 on www.nba.com and ak-static, where a plain client is refused
# (flag F7).  Copied verbatim from scripts/capture_official_ca442d3d.py.
WEB_CLIENT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 "
                   "Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
}

CARD_ANCHOR_RE = re.compile(
    r"<a[^>]*?/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})[^>]*>(.*?)</a>", re.S)
FINAL_RE = re.compile(r"\bFinal\b")
EDITION_RE = re.compile(r"Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM)\.pdf")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def get(url: str, timeout: int = 60) -> bytes:
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers=WEB_CLIENT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def store(rel: str, raw: bytes, meta: dict, compress: bool = False) -> dict:
    """Write one artifact content-addressed, with its provenance sidecar."""
    digest = hashlib.sha256(raw).hexdigest()
    dirn = os.path.join(OUT_ROOT, rel)
    os.makedirs(dirn, exist_ok=True)
    name = meta.get("name", "artifact")
    ext = ".json.gz" if compress else ".pdf"
    stem = f"{name}__{digest}{ext}"
    path = os.path.join(dirn, stem)
    existed = os.path.exists(path)
    if not existed:
        with open(path, "wb") as fh:
            fh.write(gzip.compress(raw, 6) if compress else raw)
    rec = dict(meta)
    rec.update({"stored": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                "sha256": digest, "bytes": len(raw),
                "new_artifact": not existed,
                "retrieved_at_utc": now_utc()})
    side = path + ".sidecar.json"
    if not os.path.exists(side):
        with open(side, "w", encoding="utf-8") as fh:
            json.dump({k: v for k, v in rec.items() if k != "_raw"}, fh, indent=1)
            fh.write("\n")
    return rec


def fetch_recorded(url: str, rel: str, name: str, compress: bool = False,
                   expect: str = "html") -> dict:
    """Fetch one URL and record the outcome - including a failed outcome."""
    rec = {"url": url, "name": name, "http_status": None, "error": None,
           "attempts": 0}
    for attempt in (1, 2):
        rec["attempts"] = attempt
        try:
            raw = get(url)
            rec["http_status"] = 200
            if expect == "pdf" and b"%PDF-" not in raw[:1024]:
                rec["error"] = "HTTP 200 response carried no %PDF- signature"
                log(f"  {name}: {rec['error']} - not stored")
                return rec
            stored = store(rel, raw, rec, compress=compress)
            rec.update(stored)
            rec["_raw"] = raw
            log(f"  {name}: 200, {len(raw)} bytes"
                + ("" if rec.get("new_artifact") else " (already stored)"))
            return rec
        except urllib.error.HTTPError as exc:
            rec["http_status"] = exc.code
            rec["error"] = f"HTTP {exc.code}"
            log(f"  {name}: HTTP {exc.code} (attempt {attempt})")
            if exc.code in (403, 429, 500, 502, 503) and attempt == 1:
                time.sleep(7)
                continue
        except Exception as exc:                            # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
            log(f"  {name}: {rec['error']} (attempt {attempt})")
            if attempt == 1:
                time.sleep(7)
                continue
    return rec


def edition_key(name: str):
    """Sort key: (iso date, HHMM in 24h) so newest-first ordering is exact."""
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0)
    y, mo, d, hh, mm, ampm = m.groups()
    return (f"{y}-{mo}-{d}",
            (int(hh) % 12 + (12 if ampm == "PM" else 0)) * 100 + int(mm))


def parse_scoreboard(html: str, date: str) -> dict:
    """Games printed by the official per-day scoreboard, read per card.

    Each game is one anchor whose href carries away team, home team and the
    canonical game id; the Final marker is read from inside that same anchor so
    it cannot bleed in from a neighbouring card.  No score is published here -
    only which game ids exist, who plays, and whether the card is marked Final.
    """
    games, seen = [], set()
    for m in CARD_ANCHOR_RE.finditer(html):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if gid in seen:
            continue
        seen.add(gid)
        plain = re.sub(r"<[^>]+>", " ", m.group(4))
        plain = re.sub(r"\s+", " ", plain)
        games.append({"game_id": gid, "away": away, "home": home, "date": date,
                      "marked_final_on_page": bool(FINAL_RE.search(plain)),
                      "card_text": plain[:180],
                      "url": (f"https://www.nba.com/game/"
                              f"{away.lower()}-vs-{home.lower()}-{gid}")})
    return {"date": date, "games": games,
            "final_count": sum(1 for g in games if g["marked_final_on_page"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--injury-days", default="",
                    help="comma-separated YYYY-MM-DD whose injury editions to archive")
    ap.add_argument("--result-days", default="",
                    help="comma-separated YYYY-MM-DD game days to capture scoreboards + gamebooks")
    ap.add_argument("--slate-days", default="",
                    help="comma-separated future YYYY-MM-DD scoreboard pages")
    ap.add_argument("--max-injury-editions", type=int, default=120)
    args = ap.parse_args()

    run_at = now_utc()
    os.makedirs(OUT_ROOT, exist_ok=True)
    manifest = {"session": "arena/e3d25abc-nba1", "coordination": "§67 Q02",
                "run_at_utc": run_at,
                "hosts_allowed": sorted(ALLOWED_HOSTS),
                "rule": ("Bytes as received, content-addressed, one sidecar each. "
                         "This script publishes no parsed value: parsing happens "
                         "locally on the stored bytes so it can be re-run and audited."),
                "injury_index": {}, "injury_editions": [], "days": [],
                "gamebooks": [], "slate": [], "failures": []}

    # ---- 1. injury index + every listed edition for the requested days ----
    irec = fetch_recorded(INJURY_INDEX, "injury", f"injury_index_{run_at[:10]}",
                          compress=True)
    index_html = (irec.pop("_raw", b"") or b"").decode("utf-8", "replace")
    listed = sorted({m.group(0) for m in EDITION_RE.finditer(index_html)},
                    key=edition_key, reverse=True)
    manifest["injury_index"] = {
        "url": INJURY_INDEX, "http_status": irec.get("http_status"),
        "error": irec.get("error"), "retrieved_at_utc": irec.get("retrieved_at_utc"),
        "page_sha256": irec.get("sha256"), "page_bytes": irec.get("bytes"),
        "stored": irec.get("stored"), "editions_listed": len(listed),
        "newest_listed": listed[0] if listed else None,
        "per_day_counts": {d: sum(1 for e in listed if f"_{d.replace('-', '_')}_" in e)
                           for d in sorted({edition_key(e)[0] for e in listed})[-8:]}}
    log(f"injury index: HTTP {irec.get('http_status')}, "
        f"{len(listed)} editions listed, newest {manifest['injury_index']['newest_listed']}")
    if irec.get("error"):
        manifest["failures"].append({"url": INJURY_INDEX, "error": irec["error"]})

    want_days = [d.strip() for d in args.injury_days.split(",") if d.strip()]
    archived_names = set()
    if os.path.isdir(ARCHIVE_DIR):
        for fn in os.listdir(ARCHIVE_DIR):
            if fn.endswith(".pdf"):
                archived_names.add(fn[:-4].split("__")[0] + ".pdf")
    todo = [e for e in listed
            if any(f"_{d.replace('-', '_')}_" in e for d in want_days)
            and e not in archived_names][: args.max_injury_editions]
    log(f"injury: {len(todo)} not-yet-archived edition(s) for {want_days}")
    for edition in todo:
        url = INJURY_HOST + edition
        rec = fetch_recorded(url, "injury_pdfs", edition[:-4])
        rec.pop("_raw", None)
        rec["edition"] = edition
        rec["listed_on_official_index"] = True
        rec["archived_in_repo_before_this_run"] = False
        manifest["injury_editions"].append(rec)
        if rec.get("error"):
            manifest["failures"].append({"url": url, "error": rec["error"],
                                         "edition": edition})
        time.sleep(1.0)

    # ---- 2. per-day scoreboard pages + official gamebook PDFs ------------
    for d in [x.strip() for x in args.result_days.split(",") if x.strip()]:
        url = f"https://www.nba.com/games?date={d}"
        rec = fetch_recorded(url, "html", f"games_{d}", compress=True)
        html = (rec.pop("_raw", b"") or b"").decode("utf-8", "replace")
        day = parse_scoreboard(html, d)
        day.update({"source_url": url, "page_sha256": rec.get("sha256"),
                    "page_retrieved_at_utc": rec.get("retrieved_at_utc"),
                    "http_status": rec.get("http_status")})
        with open(os.path.join(OUT_ROOT, f"games_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(day, fh, indent=1)
            fh.write("\n")
        manifest["days"].append({"date": d, "games": len(day["games"]),
                                 "marked_final": day["final_count"],
                                 "http_status": rec.get("http_status"),
                                 "page_stored": rec.get("stored"),
                                 "page_sha256": rec.get("sha256")})
        log(f"games?date={d}: {len(day['games'])} game link(s), "
            f"{day['final_count']} marked Final")
        if rec.get("error"):
            manifest["failures"].append({"url": url, "error": rec["error"]})

        ymd = d.replace("-", "")
        booked = []
        for g in day["games"]:
            if not g["marked_final_on_page"]:
                continue
            code = f"{g['away']}{g['home']}"
            gb_url = f"https://statsdmz.nba.com/pdfs/{ymd}/{ymd}_{code}_book.pdf"
            grec = fetch_recorded(gb_url, f"gamebooks/{d}",
                                  f"{d}_{code}", expect="pdf")
            grec.pop("_raw", None)
            grec.update({"game_id": g["game_id"], "away": g["away"],
                         "home": g["home"], "date": d,
                         "game_page": g["url"]})
            manifest["gamebooks"].append(grec)
            booked.append(grec)
            if grec.get("error"):
                manifest["failures"].append({"url": gb_url, "game_id": g["game_id"],
                                             "error": grec["error"]})
            time.sleep(1.2)
        with open(os.path.join(OUT_ROOT, f"gamebooks_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"date": d, "gamebooks": booked}, fh, indent=1)
            fh.write("\n")

    # ---- 3. slate pages for the rolling horizon (cross-check evidence) ----
    for d in [x.strip() for x in args.slate_days.split(",") if x.strip()]:
        url = f"https://www.nba.com/games?date={d}"
        rec = fetch_recorded(url, "html", f"slate_{d}", compress=True)
        html = (rec.pop("_raw", b"") or b"").decode("utf-8", "replace")
        day = parse_scoreboard(html, d)
        with open(os.path.join(OUT_ROOT, f"slate_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(day, fh, indent=1)
            fh.write("\n")
        manifest["slate"].append({"date": d, "games": len(day["games"]),
                                  "http_status": rec.get("http_status"),
                                  "stored": rec.get("stored"),
                                  "sha256": rec.get("sha256"),
                                  "retrieved_at_utc": rec.get("retrieved_at_utc"),
                                  "game_ids": [g["game_id"] for g in day["games"]]})
        if rec.get("error"):
            manifest["failures"].append({"url": url, "error": rec["error"]})

    with open(os.path.join(OUT_ROOT, "capture_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"manifest: {len(manifest['injury_editions'])} injury edition(s), "
        f"{len(manifest['gamebooks'])} gamebook(s), {len(manifest['slate'])} slate "
        f"page(s), {len(manifest['failures'])} failure(s)")
    # A partial capture is still published: every failure is recorded in the
    # manifest and shown on the Flagged page rather than hidden by a red run.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
