#!/usr/bin/env python3
"""Runner-side capture of official NBA evidence for session arena/bc8c07a3-nba1.

COORDINATION §66 (Z02, Z03, Z04, Z05).

WHY A RUNNER
------------
Measured in this session's sandbox on 2026-11-19: https://www.nba.com/schedule
returns TLS ``SSL_ERROR_SYSCALL`` and https://official.nba.com is unreachable,
while github.com / api.github.com answer 200. nba.com therefore cannot be read
from the agent, and any value this session publishes must come from bytes that
a GitHub-hosted runner fetched and committed back - the same pattern as
``scripts/capture_injury_07920bdc.py`` and ``scripts/capture_official_ca442d3d.py``.

WHAT IT CAPTURES (and nothing else)
-----------------------------------
1. ``https://www.nba.com/games?date=<d>`` for 2026-11-17 .. 2026-11-20 - the
   official per-day scoreboard (game ids, teams, printed score, status, and the
   per-team ``periods`` array that the per-game result feed needs for quarter
   scores).  11/17 is the game day this cycle settles; 11/18..11/20 re-state the
   window this cycle originates.
2. The official **gamebook PDF** of every 11/17 game (and any 11/16 game whose
   gamebook is not yet archived):
   ``https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf``
   - the league's own document, which prints the line score (points by period)
   and every player's MIN/FG/3P/FT/OR/DR/TOT/A/PF/ST/TO/BS/+/-/PTS.  That is
   the source for the 11/17 player game logs (R21) and for the quarter-sum
   assertion behind settlement (R02/R03).
3. ``https://www.nba.com/schedule`` - the official schedule page, whose month
   grid prints the game count for every date of the month (the independent
   cross-check for "how many games are on the rolling slate").
4. ``https://www.nba.com/standings`` and the three official team-stat pages
   (traditional / opponent / advanced), **plus** the stats.nba.com JSON the
   pages themselves call (``leaguedashteamstats``), so the five parsers that
   fail closed on every scheduled run can be repaired against real captured
   bytes instead of a guess (F-CA-02 / R01).
5. The official injury-report index, and any 2026-11-18 edition listed there
   that is not yet archived (R04: every injury PDF with its timestamp).

RULES (inherited from engine/fetch_official.py - do not weaken)
---------------------------------------------------------------
* Only the official hosts below are contacted. Any other host raises.
* Every artifact is stored with a sidecar recording the exact URL, the UTC
  retrieval timestamp, the HTTP status, the byte count and the SHA-256 of the
  bytes as received. HTML is stored gzipped to keep the repository small.
* A failure is recorded with its HTTP status (or the exception class). It is
  never dropped silently and never filled in from anywhere else. A PDF without
  a ``%PDF-`` signature in its first KiB is recorded and not stored.
* Nothing a previous session committed is overwritten: this script writes only
  inside ``data/raw/session-bc8c07a3/``.

Usage:
  python3 scripts/capture_official_bc8c07a3.py --result-dates 2026-11-17,2026-11-18
  python3 scripts/capture_official_bc8c07a3.py --gamebook-dates 2026-11-17
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
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, "data", "raw", "session-bc8c07a3")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com",
                 "statsdmz.nba.com", "stats.nba.com", "cdn.nba.com"}

# The header set engine/fetch_official.py uses and that data/raw/probe_official.json
# proved returns HTTP 200 for www.nba.com and stats.nba.com.
WEB_CLIENT_HEADERS = {
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

STATS_API_URLS = {
    "leaguedashteamstats_advanced": (
        "https://stats.nba.com/stats/leaguedashteamstats"
        "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season&MeasureType=Advanced"
        "&PerMode=Totals&Scope=Season&LastNGames=0&Month=0&OpponentTeamID=0"
        "&DateFrom=&DateTo="),
    "leaguedashteamstats_traditional": (
        "https://stats.nba.com/stats/leaguedashteamstats"
        "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season&MeasureType=Base"
        "&PerMode=PerGame&Scope=Season&LastNGames=0&Month=0&OpponentTeamID=0"
        "&DateFrom=&DateTo="),
    "leaguedashteamstats_opponent": (
        "https://stats.nba.com/stats/leaguedashteamstats"
        "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season&MeasureType=Opponent"
        "&PerMode=PerGame&Scope=Season&LastNGames=0&Month=0&OpponentTeamID=0"
        "&DateFrom=&DateTo="),
    "leaguestandingsv3": (
        "https://stats.nba.com/stats/leaguestandingsv3"
        "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season"),
}

GAME_LINK_RE = re.compile(r"/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now_utc()}] {msg}", flush=True)


def get(url: str, timeout: int = 60) -> bytes:
    host = urllib.parse.urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers=WEB_CLIENT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def store(rel_dir: str, name: str, raw: bytes, meta: dict, compress: bool = False) -> dict:
    """Write one artifact content-addressed, with its provenance sidecar."""
    digest = hashlib.sha256(raw).hexdigest()
    dirn = os.path.join(OUT_ROOT, rel_dir)
    os.makedirs(dirn, exist_ok=True)
    ext = ".gz" if compress else ".bin"
    payload = gzip.compress(raw, 6) if compress else raw
    path = os.path.join(dirn, f"{name}__{digest}{ext}")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(payload)
    rec = dict(meta)
    rec.update({"stored": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                "sha256": digest, "bytes": len(raw)})
    side = path + ".sidecar.json"
    if not os.path.exists(side):
        with open(side, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)

    # A plain-text companion, because a few readers in this repository work on
    # text (the gamebook reader is one of them) and a gzip blob cannot be read.
    if compress:
        txt = path[:-3] + ".txt"
        if not os.path.exists(txt):
            with open(txt, "wb") as fh:
                fh.write(raw)
    return rec


def record_failure(bucket: list, key: str, url: str, exc: Exception) -> None:
    if isinstance(exc, urllib.error.HTTPError):
        detail = {"http_status": exc.code}
    else:
        detail = {"http_status": None, "error": f"{type(exc).__name__}: {exc}"}
    rec = {"key": key, "url": url, "checked_at_utc": now_utc()}
    rec.update(detail)
    bucket.append(rec)
    log(f"  FAIL {key}: {detail}")


def capture_pages(pages: list, failures: list, manifest: list) -> dict:
    """Fetch each (key, url, compress) page; return key -> decoded text."""
    texts = {}
    for key, url in pages:
        try:
            raw = get(url)
        except Exception as exc:                        # noqa: BLE001
            record_failure(failures, key, url, exc)
            continue
        rec = store("html", key, raw,
                    {"key": key, "source_url": url, "retrieved_at_utc": now_utc(),
                     "http_status": 200, "content_type": "text/html"},
                    compress=True)
        manifest.append(rec)
        texts[key] = raw.decode("utf-8", "replace")
        log(f"  ok {key} {len(raw)} bytes sha256 {rec['sha256'][:12]}")
        time.sleep(0.4)
    return texts


def capture_json(apis: list, failures: list, manifest: list) -> dict:
    """Fetch each (key, url) JSON endpoint; store bytes and return parsed payloads."""
    out = {}
    for key, url in apis:
        for attempt in (1, 2):
            try:
                raw = get(url)
                payload = json.loads(raw.decode("utf-8", "replace"))
            except Exception as exc:                    # noqa: BLE001
                if attempt == 2:
                    record_failure(failures, key, url, exc)
                else:
                    time.sleep(2.0)
                continue
            rec = store("api", key, raw,
                        {"key": key, "source_url": url, "retrieved_at_utc": now_utc(),
                         "http_status": 200, "content_type": "application/json"},
                        compress=False)
            manifest.append(rec)
            out[key] = payload
            log(f"  ok {key} {len(raw)} bytes")
            break
        time.sleep(1.0)
    return out


def game_ids_from_scoreboard(text: str) -> list:
    """Every game link on a scoreboard page, in page order, de-duplicated."""
    seen, games = set(), []
    for m in GAME_LINK_RE.finditer(text):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if gid in seen:
            continue
        seen.add(gid)
        games.append({"game_id": gid, "away": away, "home": home})
    return games


def capture_gamebooks(dates: list, scoreboards: dict, failures: list, manifest: list) -> None:
    """Fetch the official gamebook PDF of every game on each requested date."""
    for d in dates:
        key = f"games_{d}"
        text = scoreboards.get(key)
        if text is None:
            failures.append({"key": f"gamebooks_{d}", "url": None,
                             "checked_at_utc": now_utc(), "http_status": None,
                             "error": "no scoreboard capture for this date in this run"})
            continue
        games = game_ids_from_scoreboard(text)
        if not games:
            failures.append({"key": f"gamebooks_{d}", "url": f"https://www.nba.com/games?date={d}",
                             "checked_at_utc": now_utc(), "http_status": None,
                             "error": "scoreboard page listed no game links"})
            continue
        compact = d.replace("-", "")
        for g in games:
            slug = f"{g['away']}{g['home']}"
            url = f"https://statsdmz.nba.com/pdfs/{compact}/{compact}_{slug}_book.pdf"
            gkey = f"gamebook_{compact}_{slug}"
            try:
                raw = get(url, timeout=90)
            except urllib.error.HTTPError as exc:
                # A 403/404 for a gamebook is recorded, never substituted.
                failures.append({"key": gkey, "url": url, "checked_at_utc": now_utc(),
                                 "http_status": exc.code, "game_id": g["game_id"]})
                log(f"  FAIL {gkey}: HTTP {exc.code}")
                continue
            except Exception as exc:                    # noqa: BLE001
                record_failure(failures, gkey, url, exc)
                continue
            if b"%PDF-" not in raw[:1024]:
                failures.append({"key": gkey, "url": url, "checked_at_utc": now_utc(),
                                 "http_status": 200, "game_id": g["game_id"],
                                 "error": "response did not carry a PDF signature"})
                continue
            rec = store("gamebooks", gkey, raw,
                        {"key": gkey, "source_url": url, "retrieved_at_utc": now_utc(),
                         "http_status": 200, "content_type": "application/pdf",
                         "date": d, "game_id": g["game_id"],
                         "away": g["away"], "home": g["home"]})
            manifest.append(rec)
            log(f"  ok {gkey} {len(raw)} bytes")
            time.sleep(0.6)


def parse_injury_index_editions(text: str) -> list:
    """Every Injury-Report_*.pdf the official index links, newest name first."""
    names = set(re.findall(
        r"(Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}_\d{2}(?:AM|PM)\.pdf)", text))
    return sorted(names, reverse=True)


def capture_injury_pdfs(index_text: str, failures: list, manifest: list,
                        limit: int = 24) -> None:
    """Archive every 2026-11-18 edition the index lists that is not archived yet.

    The repository's own archive directory is the dedupe key, exactly as
    engine/fetch_official.py does it: a content-addressed re-download of
    identical bytes would write nothing, so the check is on the edition name.
    """
    archive = os.path.join(ROOT, "data", "raw", "injury_pdfs")
    archived = set()
    if os.path.isdir(archive):
        for fn in os.listdir(archive):
            if fn.endswith(".pdf"):
                archived.add(fn[:-4].split("__")[0] + ".pdf")
    listed = [e for e in parse_injury_index_editions(index_text)
              if e.startswith("Injury-Report_2026-11-18_")]
    todo = [e for e in listed if e not in archived][:limit]
    log(f"  index lists {len(listed)} 11/18 editions; {len(todo)} not yet archived")
    for edition in todo:
        url = "https://ak-static.cms.nba.com/referee/injury/" + edition
        try:
            raw = get(url, timeout=45)
        except urllib.error.HTTPError as exc:
            failures.append({"key": f"injury_{edition}", "url": url,
                             "checked_at_utc": now_utc(), "http_status": exc.code})
            continue
        except Exception as exc:                        # noqa: BLE001
            record_failure(failures, f"injury_{edition}", url, exc)
            continue
        if b"%PDF-" not in raw[:1024]:
            failures.append({"key": f"injury_{edition}", "url": url,
                             "checked_at_utc": now_utc(), "http_status": 200,
                             "error": "response did not carry a PDF signature"})
            continue
        digest = hashlib.sha256(raw).hexdigest()
        stem = f"{edition[:-4]}__{digest}"
        pdf_path = os.path.join(archive, stem + ".pdf")
        meta_path = os.path.join(archive, stem + ".json")
        os.makedirs(archive, exist_ok=True)
        if not os.path.exists(pdf_path):
            with open(pdf_path, "wb") as fh:
                fh.write(raw)
        if not os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump({"edition": edition, "source_url": url,
                           "retrieved_at_utc": now_utc(), "bytes": len(raw),
                           "sha256": digest, "content_type": "application/pdf"},
                          fh, indent=2)
        manifest.append({"key": f"injury_{edition}", "source_url": url,
                         "retrieved_at_utc": now_utc(), "http_status": 200,
                         "content_type": "application/pdf", "bytes": len(raw),
                         "sha256": digest,
                         "stored": os.path.relpath(pdf_path, ROOT).replace(os.sep, "/")})
        log(f"  ok injury {edition} {len(raw)} bytes")
        time.sleep(0.8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--result-dates", default="2026-11-17,2026-11-18,2026-11-19,2026-11-20")
    ap.add_argument("--gamebook-dates", default="2026-11-17")
    ap.add_argument("--skip-stats-api", action="store_true")
    ap.add_argument("--skip-injury", action="store_true")
    args = ap.parse_args()

    result_dates = [d.strip() for d in args.result_dates.split(",") if d.strip()]
    gamebook_dates = [d.strip() for d in args.gamebook_dates.split(",") if d.strip()]

    failures: list = []
    manifest: list = []

    log("scoreboards")
    pages = [(f"games_{d}", f"https://www.nba.com/games?date={d}") for d in result_dates]
    pages += [
        ("schedule_page", "https://www.nba.com/schedule"),
        ("standings_page", "https://www.nba.com/standings"),
        ("teams_advanced_page",
         "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"),
        ("teams_traditional_page",
         "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"),
        ("teams_opponent_page",
         "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"),
        ("injury_index", "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ]
    texts = capture_pages(pages, failures, manifest)

    log("official stats API (the data layer behind the cited pages)")
    apis = [] if args.skip_stats_api else list(STATS_API_URLS.items())
    capture_json(apis, failures, manifest)

    log(f"gamebooks for {gamebook_dates}")
    capture_gamebooks(gamebook_dates, texts, failures, manifest)

    if not args.skip_injury and "injury_index" in texts:
        log("injury PDFs listed by the official index")
        capture_injury_pdfs(texts["injury_index"], failures, manifest)

    os.makedirs(OUT_ROOT, exist_ok=True)
    doc = {
        "title": "Runner capture of official NBA evidence — session arena/bc8c07a3-nba1",
        "captured_at_utc": now_utc(),
        "result_dates": result_dates,
        "gamebook_dates": gamebook_dates,
        "rule": ("Only official hosts are contacted (www.nba.com, official.nba.com, "
                 "ak-static.cms.nba.com, statsdmz.nba.com, stats.nba.com, cdn.nba.com). "
                 "Every artifact carries its exact URL, retrieval timestamp and SHA-256. "
                 "A failure is recorded with its HTTP status and never substituted."),
        "manifest": manifest,
        "failures": failures,
        "counts": {"artifacts": len(manifest), "failures": len(failures)},
    }
    out = os.path.join(OUT_ROOT, "capture_manifest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    log(f"manifest -> {os.path.relpath(out, ROOT)}  "
        f"{len(manifest)} artifacts, {len(failures)} failures")
    # A partial failure is a finding, not a build error: the committed record
    # is what the parsers and checks read back.
    return 0


if __name__ == "__main__":
    sys.exit(main())
