#!/usr/bin/env python3
"""capture_gamebooks_a374ec9f.py — byte-exact capture of official NBA gamebooks.

Why this script exists
----------------------
Requirement R21 (*per-player game logs: minutes, points, rebounds, assists and
the opponent*) and R02 (*one row per game: date, teams, final score, quarter
scores*) both need the league's own box-score document.  The NBA publishes one
PDF per game at a deterministic URL:

    https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf

The repository already holds the *page-1 text* of the 2026-11-15 gamebooks,
transcribed by hand from a text render of that PDF.  A text render is a lossy
second-hand copy; the PDF bytes are the document.  So this script stores the
bytes, content-addressed, with a sidecar that carries the source URL, the
retrieval timestamp, the byte count and the SHA-256 — the same discipline the
injury-PDF archive already uses.

A session's sandbox has no outbound path to `statsdmz.nba.com` (its only
outbound route is the GitHub API), so this script is designed to run on a
runner; see `.github/workflows/capture-a374ec9f.yml`.

Rules this script holds to
--------------------------
* Only `statsdmz.nba.com` is fetched.  The host list is a hard refusal, not a
  default.
* Nothing is inferred.  A gamebook that cannot be fetched is recorded with its
  HTTP status and is *not* written to the archive; a 403 is recorded as
  "unavailable to this client at this time", never as "does not exist".
* Every stored file is content-addressed and re-downloading identical bytes
  writes nothing new.
* The game list comes from the official games listing for that date, not from a
  hand-typed guess.  The list is passed in on the command line *and* recorded
  in the manifest so a reader can check it.

Usage
-----
    python3 scripts/capture_gamebooks_a374ec9f.py --date 2026-11-16 \
        --game 0022600245:ORL:BOS --game 0022600246:CHI:CLE ...
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = {"statsdmz.nba.com"}

# The browser header set already proven to reach NBA hosts (see
# data/raw/probe_official.json and scripts/capture_injury_07920bdc.py).
WEB_CLIENT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Connection": "keep-alive",
}

OUT_DIR = os.path.join(ROOT, "verify", "2026-11-17-a374ec9f")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def get(url: str, timeout: int = 60) -> bytes:
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers=WEB_CLIENT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def gamebook_url(date: str, away: str, home: str) -> str:
    ymd = date.replace("-", "")
    return f"https://statsdmz.nba.com/pdfs/{ymd}/{ymd}_{away}{home}_book.pdf"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="game date, YYYY-MM-DD")
    ap.add_argument("--game", action="append", default=[],
                    metavar="GAMEID:AWAY:HOME",
                    help="repeatable; away/home are the official 3-letter codes")
    ap.add_argument("--out-root", default=os.path.join(ROOT, "data", "raw", "gamebooks"))
    args = ap.parse_args()

    run_at = now_utc()
    ymd = args.date.replace("-", "")
    out_dir = os.path.join(args.out_root, ymd)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    results = []
    for spec in args.game:
        parts = spec.split(":")
        if len(parts) != 3:
            log(f"skipping malformed --game {spec!r}")
            continue
        gid, away, home = (p.strip().upper() for p in parts)
        url = gamebook_url(args.date, away, home)
        rec = {"game_id": gid, "away": away, "home": home, "url": url,
               "http_status": None, "bytes": 0, "sha256": None,
               "stored": False, "artifact": None, "sidecar": None,
               "error": None}
        for attempt in (1, 2):
            try:
                raw = get(url, timeout=60)
                rec["http_status"] = 200
                rec["bytes"] = len(raw)
                if b"%PDF-" not in raw[:1024]:
                    rec["error"] = "HTTP 200 response carried no PDF signature"
                    log(f"  {away}@{home}: {rec['error']}")
                    break
                digest = hashlib.sha256(raw).hexdigest()
                rec["sha256"] = digest
                stem = f"{ymd}_{away}{home}_book__{digest[:16]}"
                pdf_path = os.path.join(out_dir, stem + ".pdf")
                meta_path = os.path.join(out_dir, stem + ".json")
                if not os.path.exists(pdf_path):
                    with open(pdf_path, "wb") as fh:
                        fh.write(raw)
                with open(meta_path, "w", encoding="utf-8") as fh:
                    json.dump({
                        "date": args.date, "game_id": gid, "away": away, "home": home,
                        "source_url": url, "retrieved_at_utc": run_at,
                        "bytes": len(raw), "sha256": digest,
                        "content_type": "application/pdf",
                        "captured_by": "arena/a374ec9f-nba1",
                        "capture_run_utc": run_at,
                        "official_game_page": (
                            f"https://www.nba.com/game/{away.lower()}-vs-"
                            f"{home.lower()}-{gid}"),
                    }, fh, indent=2)
                    fh.write("\n")
                rec["stored"] = True
                rec["artifact"] = os.path.relpath(pdf_path, ROOT)
                rec["sidecar"] = os.path.relpath(meta_path, ROOT)
                log(f"  {away}@{home}: 200, {len(raw)} bytes, sha256 {digest[:12]}")
                break
            except urllib.error.HTTPError as exc:
                rec["http_status"] = exc.code
                log(f"  {away}@{home}: HTTP {exc.code} (attempt {attempt})")
                if exc.code in (403, 429, 503) and attempt == 1:
                    time.sleep(6)
                    continue
                break
            except Exception as exc:                     # noqa: BLE001
                rec["error"] = f"{type(exc).__name__}: {exc}"
                log(f"  {away}@{home}: {rec['error']}")
                break
        results.append(rec)
        time.sleep(1.0)

    manifest = {
        "session": "arena/a374ec9f-nba1",
        "purpose": ("COORDINATION §62 / A03 - byte-exact capture of the official "
                    "NBA gamebook PDFs for the 2026-11-16 slate, so the results "
                    "feed, the per-player game logs and the minutes-share "
                    "measurements all rest on the league's own box-score "
                    "document rather than on a hand transcription."),
        "run_at_utc": run_at,
        "date": args.date,
        "host": "statsdmz.nba.com",
        "results": results,
        "note": ("A non-200 status is recorded as unavailable to this client at "
                 "this time; it is never treated as proof that the document does "
                 "not exist."),
    }
    out = os.path.join(OUT_DIR, f"gamebook_capture_{ymd}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"manifest -> {os.path.relpath(out, ROOT)}")
    stored = sum(1 for r in results if r["stored"])
    log(f"done. {stored} of {len(results)} gamebooks stored.")
    return 0 if stored == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
