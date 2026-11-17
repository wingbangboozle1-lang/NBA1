#!/usr/bin/env python3
"""Runner-side capture of official NBA evidence for session arena/ca442d3d-nba1.

COORDINATION §62 N05/N06/N07.

WHY A RUNNER
------------
This repository's sandbox reaches only github.com / npm / pypi, so nba.com
cannot be read from the agent itself. The GitHub Actions runner has normal
outbound access, and the scheduled job already proves the pattern
(``engine/fetch_official.py``, ``scripts/capture_injury_07920bdc.py``). This
script puts the fetch on the runner and commits the bytes back to the session
branch, so every value published afterwards is derived from a stored,
content-addressed official artifact - never from a memory of a page.

WHAT IT CAPTURES
----------------
1. ``https://www.nba.com/games?date=<d>`` for each requested date - the
   official per-day scoreboard (game ids, teams, printed score, game status).
2. The official **gamebook PDF** of every game on that date that the scoreboard
   page marks Final:
   ``https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf``
   - the league's own box-score document, which prints the **line score**
   (points by period) and every player's MIN/FG/3P/FT/OR/DR/TOT/A/PF/ST/TO/BS/+
   -PTS. This is the source for both the per-game result feed's quarter scores
   (R02) and the per-player game logs (R21).
3. ``https://www.nba.com/schedule`` - the official schedule page, whose month
   grid prints the game count for every date of the month: the independent
   cross-check for "how many games are on the rolling slate".
4. ``https://www.nba.com/standings`` and the three official team-stat pages
   (traditional / opponent / advanced), which the model re-cut reads (R20).

RULES (inherited from engine/fetch_official.py; do not weaken)
---------------------------------------------------------------
* Only the four official hosts above are contacted. Any other host raises.
* Every artifact is stored content-addressed with a sidecar that records the
  exact URL, the retrieval timestamp (UTC), the HTTP status, the byte count and
  the SHA-256 of the bytes as received. A digest is of the *uncompressed*
  response; HTML is stored gzipped only to keep the repository small.
* A failed fetch is recorded as a failure with its HTTP status. It is never
  dropped silently and never filled in from anywhere else. A PDF whose first
  KiB carries no ``%PDF-`` signature is recorded and not stored.
* Nothing a previous session committed is overwritten: this script writes only
  inside ``data/raw/session-ca442d3d/``.

Usage: ``python3 scripts/capture_official_ca442d3d.py --dates 2026-11-16,2026-11-17``
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, "data", "raw", "session-ca442d3d")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com",
                 "statsdmz.nba.com"}

# The web-client header set proven by data/raw/probe_official.json: HTTP 200 on
# www.nba.com and ak-static where a plain client is refused (flag F7).
WEB_CLIENT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
}

GAME_LINK_RE = re.compile(r"/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})")
# The scoreboard prints "Final", "Final/OT", "Live", a tip time, or a broadcast
# label. Only an explicit Final marker makes a game settleable (R02/R19).
FINAL_RE = re.compile(r"\bFinal(?:/OT\d*)?\b")
NEUTRAL_RE = re.compile(r"Neutral Site", re.I)


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


def store(rel: str, raw: bytes, meta: dict, compress: bool = False) -> dict:
    """Write one artifact content-addressed, with its provenance sidecar."""
    digest = hashlib.sha256(raw).hexdigest()
    dirn = os.path.join(OUT_ROOT, rel)
    os.makedirs(dirn, exist_ok=True)
    name = meta.get("name", os.path.basename(rel.rstrip("/")) or "artifact")
    ext = ".json.gz" if compress else ".bin"
    stem = f"{name}__{digest}{ext}"
    path = os.path.join(dirn, stem)
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(gzip.compress(raw, 6) if compress else raw)
    rec = dict(meta)
    rec.update({"stored": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                "sha256": digest, "bytes": len(raw),
                "retrieved_at_utc": now_utc()})
    with open(os.path.join(dirn, stem + ".sidecar.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
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
            raw = get(url, timeout=60)
            rec["http_status"] = 200
            if expect == "pdf" and b"%PDF-" not in raw[:1024]:
                rec["error"] = "HTTP 200 response carried no %PDF- signature"
                log(f"  {name}: {rec['error']} - not stored")
                return rec
            stored = store(rel, raw, rec, compress=compress)
            rec.update(stored)
            rec["_raw"] = raw
            log(f"  {name}: 200, {len(raw)} bytes")
            return rec
        except urllib.error.HTTPError as exc:
            rec["http_status"] = exc.code
            rec["error"] = f"HTTP {exc.code}"
            log(f"  {name}: HTTP {exc.code} (attempt {attempt})")
            if exc.code in (403, 429, 503) and attempt == 1:
                time.sleep(6)
                continue
        except Exception as exc:                            # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
            log(f"  {name}: {rec['error']} (attempt {attempt})")
            if attempt == 1:
                time.sleep(6)
                continue
    return rec


CARD_ANCHOR_RE = re.compile(
    r"<a[^>]*?/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})[^>]*>(.*?)</a>", re.S)


def parse_scoreboard(html: str, date: str) -> dict:
    """Extract the games the official per-day scoreboard prints, per card.

    Only what the page itself states is taken. Each game card is one anchor
    whose href carries the away team, the home team and the canonical game id,
    and whose own inner text carries the printed score and the status marker -
    so the Final marker is read from *inside that anchor* and cannot bleed in
    from the neighbouring card (an earlier ±4000-character window version of this
    parser bled, and a test now pins it).

    This function publishes no parsed score: the capture script stores the page
    bytes and the game list, and scores are extracted locally from the stored
    bytes so the extraction can be re-run and audited.
    """
    games, seen = [], set()
    for m in CARD_ANCHOR_RE.finditer(html):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if gid in seen:
            continue
        seen.add(gid)
        inner = m.group(4)
        plain = re.sub(r"<[^>]+>", " ", inner)
        plain = re.sub(r"\s+", " ", plain)
        games.append({"game_id": gid, "away": away, "home": home,
                      "date": date,
                      "marked_final_on_page": bool(FINAL_RE.search(plain)),
                      "marked_neutral_on_page": bool(NEUTRAL_RE.search(plain)),
                      "card_text": plain[:200],
                      "url": ("https://www.nba.com/game/"
                              f"{away.lower()}-vs-{home.lower()}-{gid}")})
    return {"date": date, "games": games,
            "final_count": sum(1 for g in games if g["marked_final_on_page"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dates", default="",
                    help="comma-separated YYYY-MM-DD result days to capture")
    ap.add_argument("--slate-dates", default="",
                    help="comma-separated YYYY-MM-DD future slate days")
    ap.add_argument("--skip-gamebooks", action="store_true")
    ap.add_argument("--skip-team-pages", action="store_true")
    args = ap.parse_args()

    run_at = now_utc()
    os.makedirs(OUT_ROOT, exist_ok=True)
    manifest = {"session": "arena/ca442d3d-nba1", "run_at_utc": run_at,
                "hosts_allowed": sorted(ALLOWED_HOSTS),
                "rule": ("Bytes as received, content-addressed. This script "
                         "publishes no parsed value: parsing happens locally on "
                         "the stored bytes so it can be re-run and audited."),
                "days": [], "pages": [], "gamebooks": [], "failures": []}

    # ---- 1. per-day scoreboard pages + gamebooks --------------------------
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        rec = fetch_recorded(url, "html", f"games_{d}", compress=True)
        html = (rec.pop("_raw", b"") or b"").decode("utf-8", "replace")
        day = parse_scoreboard(html, d)
        day["source_url"] = url
        day["page_sha256"] = rec.get("sha256")
        day["page_retrieved_at_utc"] = rec.get("retrieved_at_utc")
        day["http_status"] = rec.get("http_status")
        if rec.get("error"):
            manifest["failures"].append({"url": url, "error": rec["error"]})
        with open(os.path.join(OUT_ROOT, f"games_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(day, fh, indent=1)
            fh.write("\n")
        manifest["days"].append({"date": d, "games": len(day["games"]),
                                 "marked_final": day["final_count"],
                                 "http_status": rec.get("http_status"),
                                 "page_stored": rec.get("stored")})
        log(f"games?date={d}: {len(day['games'])} game links, "
            f"{day['final_count']} marked Final")

        if args.skip_gamebooks:
            continue
        ymd = d.replace("-", "")
        for g in day["games"]:
            if not g["marked_final_on_page"]:
                continue
            code = f"{g['away']}{g['home']}"
            gb_url = (f"https://statsdmz.nba.com/pdfs/{ymd}/"
                      f"{ymd}_{code}_book.pdf")
            grec = fetch_recorded(gb_url, f"gamebooks/{d}", f"{d}_{code}",
                                  expect="pdf")
            grec.pop("_raw", None)
            grec["game_id"] = g["game_id"]
            grec["away"] = g["away"]
            grec["home"] = g["home"]
            grec["source_page"] = g["url"]
            manifest["gamebooks"].append(grec)
            if grec.get("error"):
                manifest["failures"].append({"url": gb_url,
                                             "error": grec["error"],
                                             "game_id": g["game_id"]})
            with open(os.path.join(OUT_ROOT, f"gamebooks_{d}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"date": d, "gamebooks": manifest["gamebooks"]},
                          fh, indent=1)
            time.sleep(1.2)

    # ---- 2. slate pages for the rolling horizon --------------------------
    for d in [x.strip() for x in args.slate_dates.split(",") if x.strip()]:
        url = f"https://www.nba.com/games?date={d}"
        rec = fetch_recorded(url, "html", f"slate_{d}", compress=True)
        html = (rec.pop("_raw", b"") or b"").decode("utf-8", "replace")
        day = parse_scoreboard(html, d)
        with open(os.path.join(OUT_ROOT, f"slate_{d}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(day, fh, indent=1)
            fh.write("\n")
        manifest["pages"].append({"kind": "slate", "date": d,
                                  "games": len(day["games"]),
                                  "http_status": rec.get("http_status"),
                                  "stored": rec.get("stored"),
                                  "sha256": rec.get("sha256"),
                                  "retrieved_at_utc": rec.get("retrieved_at_utc")})

    # ---- 3. standings, the three team-stat pages, the injury index -------
    if not args.skip_team_pages:
        for name, url in (
                ("standings", "https://www.nba.com/standings"),
                ("teams_traditional", "https://www.nba.com/stats/teams/traditional"),
                ("teams_opponent", "https://www.nba.com/stats/teams/opponent"),
                ("teams_advanced", "https://www.nba.com/stats/teams/advanced"),
                ("schedule_page", "https://www.nba.com/schedule"),
                ("injury_index",
                 "https://official.nba.com/nba-injury-report-2026-27-season/")):
            prec = fetch_recorded(url, "pages", f"{name}_{run_at[:10]}",
                                  compress=True)
            prec.pop("_raw", None)
            prec["kind"] = name
            prec["url"] = url
            manifest["pages"].append(prec)
            if prec.get("error"):
                manifest["failures"].append({"url": url, "error": prec["error"]})

    with open(os.path.join(OUT_ROOT, "capture_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    log(f"manifest: {len(manifest['days'])} day(s), "
        f"{len(manifest['gamebooks'])} gamebook(s), "
        f"{len(manifest['pages'])} page(s), {len(manifest['failures'])} failure(s)")
    # A partial capture is still published: the failures are recorded in the
    # manifest and shown on the Flagged page rather than hidden by a red run.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
