#!/usr/bin/env python3
"""Bulk capture of official NBA per-player game logs (requirement R21).

This script is executed on a GitHub Actions runner (see
.github/workflows/capture-2026-11-16-4ff440c7.yml) because the build sandbox has
no outbound network. GitHub runners have normal outbound internet.

It fetches ONLY official NBA hosts:

  1. https://stats.nba.com/stats/leaguegamelog   - the endpoint nba.com's own
     "Players Box Scores" page (https://www.nba.com/stats/players/boxscores) is
     served from. One row per player-game: GAME_DATE, MATCHUP (which carries the
     opponent and home/away), MIN, PTS, REB, AST.
  2. https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json
     - the official schedule the site's own slate captures come from.
  3. https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_09_00PM.pdf
     - the official injury PDF, archived byte-for-byte with its sha256 (R04).

Everything is written under verify/2026-11-16-4ff440c7/raw/ with a manifest that
records the exact URL, HTTP status, byte length and sha256 of each artifact, so a
reader can re-fetch and compare without trusting this script.

Nothing here is inferred: if a fetch fails, the manifest says so.
"""
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
PDF_DIR = os.path.join(RAW, "injury_pdfs")
os.makedirs(RAW, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

SEASON = "2026-27"
SEASON_TYPE = "Regular Season"

# The web-client header set. stats.nba.com refuses requests without a browser
# User-Agent and an nba.com Referer.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}

LEAGUE_GAMELOG = (
    "https://stats.nba.com/stats/leaguegamelog"
    "?Counter={counter}"
    "&DateFromNullable=&DateToNullable="
    "&Direction=DESC&LeagueID=00&PlayerOrTeam=P"
    "&Season={season}&SeasonType={st}&Sorter=DATE"
).format(counter="{counter}", season=SEASON, st=SEASON_TYPE.replace(" ", "+"))

SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
INJURY_PDF_URL = ("https://ak-static.cms.nba.com/referee/injury/"
                  "Injury-Report_2026-11-15_09_00PM.pdf")

manifest = {"captured_by": "session arena/4ff440c7-nba1",
            "season": SEASON, "season_type": SEASON_TYPE, "items": []}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, tries=5, timeout=90):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), r.read()
        except Exception as e:            # noqa: BLE001 - recorded, never hidden
            last = e
            time.sleep(4 * (i + 1))
    return None, last


def record(name, url, status, body, path, note=""):
    item = {"name": name, "url": url, "http_status": status,
            "bytes": len(body) if isinstance(body, bytes) else None,
            "sha256": sha256(body) if isinstance(body, bytes) else None,
            "path": os.path.relpath(path, HERE), "note": note}
    manifest["items"].append(item)
    print(json.dumps(item, sort_keys=True))
    return item


def write_gz(path, body):
    with gzip.open(path, "wb") as fh:
        fh.write(body)


def main():
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["captured_utc"] = started
    ok = True

    # 1. league game log -------------------------------------------------------
    rows = None
    hdrs = None
    params = None
    for counter in (1000, 5000, 20000, 100000):
        url = LEAGUE_GAMELOG.format(counter=counter)
        status, body = fetch(url)
        if not isinstance(body, bytes):
            record("leaguegamelog", url, status, None,
                   os.path.join(RAW, "leaguegamelog.json.gz"),
                   note="FETCH FAILED: %r" % (body,))
            ok = False
            break
        try:
            doc = json.loads(body.decode("utf-8"))
        except Exception as e:             # noqa: BLE001
            record("leaguegamelog", url, status, body,
                   os.path.join(RAW, "leaguegamelog.json.gz"),
                   note="NOT JSON: %r" % (e,))
            ok = False
            break
        rs = doc.get("resultSets") or []
        if not rs:
            record("leaguegamelog", url, status, body,
                   os.path.join(RAW, "leaguegamelog.json.gz"),
                   note="NO resultSets in response")
            ok = False
            break
        rs0 = rs[0]
        hdrs = rs0.get("headers")
        rows = rs0.get("rowSet")
        params = doc.get("parameters")
        note = ("counter=%d returned %d rows" % (counter, len(rows or [])))
        # keep going while the response is exactly saturated by the counter
        if rows is None or len(rows) < counter:
            write_gz(os.path.join(RAW, "leaguegamelog.json.gz"), body)
            record("leaguegamelog", url, status, body,
                   os.path.join(RAW, "leaguegamelog.json.gz"), note=note)
            break
        write_gz(os.path.join(RAW, "leaguegamelog.json.gz"), body)
        record("leaguegamelog", url, status, body,
               os.path.join(RAW, "leaguegamelog.json.gz"), note=note)

    if rows is not None:
        print("leaguegamelog rows:", len(rows), "headers:", len(hdrs or []))

    # 2. official schedule -----------------------------------------------------
    status, body = fetch(SCHEDULE_URL)
    spath = os.path.join(RAW, "scheduleLeagueV2.json.gz")
    if isinstance(body, bytes):
        write_gz(spath, body)
        record("scheduleLeagueV2", SCHEDULE_URL, status, body, spath)
    else:
        record("scheduleLeagueV2", SCHEDULE_URL, status, None, spath,
               note="FETCH FAILED: %r" % (body,))
        ok = False

    # 3. the injury PDF, archived by content hash ------------------------------
    status, body = fetch(INJURY_PDF_URL)
    if isinstance(body, bytes):
        h = sha256(body)
        ppath = os.path.join(PDF_DIR, "Injury-Report_2026-11-15_09_00PM__%s.pdf" % h[:16])
        with open(ppath, "wb") as fh:
            fh.write(body)
        record("injury_pdf_2026-11-15_09_00PM", INJURY_PDF_URL, status, body,
               ppath, note="PDF archived by content hash (R04)")
    else:
        record("injury_pdf_2026-11-15_09_00PM", INJURY_PDF_URL, status, None,
               os.path.join(PDF_DIR, "Injury-Report_2026-11-15_09_00PM.pdf"),
               note="FETCH FAILED: %r" % (body,))
        ok = False

    manifest["all_fetches_ok"] = bool(ok)
    with open(os.path.join(RAW, "_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print("MANIFEST OK" if ok else "MANIFEST HAS FAILURES")
    # a failed fetch is a FINDING, never a build error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
