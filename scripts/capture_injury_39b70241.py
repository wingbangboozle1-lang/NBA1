#!/usr/bin/env python3
"""Capture the newest official NBA injury-report PDFs byte-exactly (§66 / Y02).

Why this script exists
----------------------
Requirement R03: *store every injury PDF with its timestamp and diff consecutive
reports to detect status changes*.  The archive under ``data/raw/injury_pdfs/``
stops at 2026-11-17 11:30 AM ET, so the 11/17 evening, 11/18 and 11/19 editions
- the ones that actually gate the 11/19-11/22 slate - are not stored.  A session
runs behind a sandbox whose only outbound path is the GitHub API plus the agent's
own fetch channel, and that channel can read a page but cannot write PDF *bytes*
to disk.  So the fetch is moved to a runner that has the network, on this
session's own branch, in one file this session owns.  It downloads only from
``official.nba.com`` and ``ak-static.cms.nba.com`` (the two hosts the league
itself serves the injury report from), with the browser header set recorded in
``engine/fetch_official.py``.

Lineage: this is a copy of ``scripts/capture_injury_07920bdc.py`` (board §56/§60)
with three changes and nothing else:
  * ``--since YYYY-MM-DD`` so a run can be scoped to the days this slate needs;
  * the manifest and sidecars name this session, so provenance is unambiguous;
  * it reports the newest edition per calendar day, which is what the Injuries
    banner needs (revision time) rather than only a flat newest-first list.

Rules this script holds to (inherited unchanged)
------------------------------------------------
* Nothing is inferred.  An edition that cannot be fetched is recorded with its
  HTTP status; a 403 is recorded as "unavailable to this client at this time",
  never as "does not exist".
* Every stored PDF is content-addressed: the file name carries its own SHA-256
  and a sidecar records source URL, retrieval timestamp, byte count and hash.
  A re-download of identical bytes writes nothing new.
* The official index page is transcribed first and its SHA-256 recorded, so the
  list of editions the league publishes is evidence, not an assumption.
* Already-archived editions are never re-fetched unless ``--force`` is given.

Usage: ``python3 scripts/capture_injury_39b70241.py [--max N] [--since DATE] [--force]``
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")
OUT_DIR = os.path.join(ROOT, "verify", "2026-11-19-39b70241")

INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
PDF_HOST = "https://ak-static.cms.nba.com/referee/injury/"
ALLOWED_HOSTS = {"official.nba.com", "ak-static.cms.nba.com"}
SESSION = "arena/39b70241-nba1"

WEB_CLIENT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
}

EDITION_RE = re.compile(
    r"https://ak-static\.cms\.nba\.com/referee/injury/"
    r"(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM)\.pdf)")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def get(url: str, timeout: int = 45) -> bytes:
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers=WEB_CLIENT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def edition_key(name: str) -> tuple:
    """Sort key: (date, minutes past midnight). Newest last."""
    m = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)", name)
    if not m:
        return (name, 0)
    year, mo, day, hh, mm, ampm = m.groups()
    hour24 = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return (f"{year}-{mo}-{day}", hour24 * 100 + int(mm))


def edition_date(name: str) -> str:
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_", name)
    return m.group(1) if m else ""


def archived_editions() -> dict:
    out: dict = {}
    if not os.path.isdir(PDF_DIR):
        return out
    for name in os.listdir(PDF_DIR):
        if not name.endswith(".pdf"):
            continue
        stem = name[:-4]
        edition = stem.split("__")[0] + ".pdf"
        side = os.path.join(PDF_DIR, stem + ".json")
        rec = {}
        if os.path.exists(side):
            try:
                with open(side, encoding="utf-8") as fh:
                    rec = json.load(fh)
            except (OSError, ValueError):
                rec = {}
        out.setdefault(edition, []).append({
            "file": "data/raw/injury_pdfs/" + name,
            "sha256": rec.get("sha256"),
            "retrieved_at_utc": rec.get("retrieved_at_utc") or rec.get("retrieved_utc"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max", type=int, default=24,
                    help="maximum number of editions to download in one run")
    ap.add_argument("--since", default="",
                    help="only consider editions dated on/after YYYY-MM-DD")
    ap.add_argument("--force", action="store_true",
                    help="re-download editions even if already archived")
    args = ap.parse_args()

    run_at = now_utc()
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    log(f"reading official index {INDEX_URL}")
    index_raw = get(INDEX_URL, timeout=60)
    index_text = index_raw.decode("utf-8", "replace")
    listed = sorted(set(EDITION_RE.findall(index_text)), key=edition_key, reverse=True)
    log(f"index lists {len(listed)} editions; newest = {listed[0] if listed else 'NONE'}")

    editions = [e for e in listed if not args.since or edition_date(e) >= args.since]
    newest_per_day: dict = {}
    for e in editions:
        newest_per_day.setdefault(edition_date(e), e)

    archived = archived_editions()
    todo = []
    for ed in editions:
        if not args.force and ed in archived:
            continue
        todo.append(ed)
        if len(todo) >= args.max:
            break

    log(f"{len(todo)} edition(s) to fetch of {len(editions)} in range "
        f"(since={args.since or 'any'}, max {args.max}, force={args.force})")

    results = []
    for ed in todo:
        url = PDF_HOST + ed
        rec = {"edition": ed, "url": url, "attempts": 0, "http_status": None,
               "bytes": 0, "sha256": None, "stored": False, "artifact": None,
               "error": None}
        for attempt in (1, 2):
            rec["attempts"] = attempt
            try:
                raw = get(url, timeout=45)
                rec["http_status"] = 200
                rec["bytes"] = len(raw)
                digest = hashlib.sha256(raw).hexdigest()
                rec["sha256"] = digest
                if b"%PDF-" not in raw[:1024]:
                    rec["error"] = "HTTP 200 response carried no PDF signature"
                    log(f"  {ed}: {rec['error']} - not stored")
                    break
                stem = f"{ed[:-4]}__{digest}"
                pdf_path = os.path.join(PDF_DIR, stem + ".pdf")
                meta_path = os.path.join(PDF_DIR, stem + ".json")
                if not os.path.exists(pdf_path):
                    with open(pdf_path, "wb") as fh:
                        fh.write(raw)
                with open(meta_path, "w", encoding="utf-8") as fh:
                    json.dump({"edition": ed, "source_url": url,
                               "retrieved_at_utc": run_at, "bytes": len(raw),
                               "sha256": digest, "content_type": "application/pdf",
                               "captured_by": SESSION, "capture_run_utc": run_at},
                              fh, indent=2)
                    fh.write("\n")
                rec["stored"] = True
                rec["artifact"] = "data/raw/injury_pdfs/" + stem + ".pdf"
                log(f"  {ed}: 200, {len(raw)} bytes, sha256 {digest[:12]}")
                break
            except urllib.error.HTTPError as exc:
                rec["http_status"] = exc.code
                log(f"  {ed}: HTTP {exc.code} (attempt {attempt})")
                if exc.code in (403, 429, 503) and attempt == 1:
                    time.sleep(8)
                    continue
                break
            except Exception as exc:                     # noqa: BLE001
                rec["error"] = f"{type(exc).__name__}: {exc}"
                log(f"  {ed}: {rec['error']}")
                break
        results.append(rec)
        time.sleep(1.5)

    manifest = {
        "session": SESSION,
        "purpose": ("COORDINATION §66 / Y02 - byte-exact capture of the official "
                    "injury-report editions covering the 2026-11-19 - 2026-11-22 "
                    "slate, so the Injuries banner cites an edition this session "
                    "retrieved and hashed, and so consecutive-edition diffs can "
                    "detect status changes on the slate's own day rolls (R03, R23)."),
        "run_at_utc": run_at,
        "index_url": INDEX_URL,
        "index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "editions_listed_on_index": len(listed),
        "newest_listed_on_index": listed[0] if listed else None,
        "newest_edition_per_day_in_range": dict(sorted(newest_per_day.items(), reverse=True)),
        "editions_archived_before_run": len(archived),
        "editions_fetched_this_run": [r["edition"] for r in results if r["stored"]],
        "results": results,
        "note": ("A non-200 status is recorded as unavailable to this client at "
                 "this time.  ak-static.cms.nba.com answers 403 both for editions "
                 "that are not published yet and, intermittently, for editions a "
                 "browser opens, so no status here is treated as proof of absence."),
    }
    out = os.path.join(OUT_DIR, "injury_capture_manifest_2026-11-19.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"manifest -> {os.path.relpath(out, ROOT)}")
    log(f"done. {sum(1 for r in results if r['stored'])} of {len(results)} stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
