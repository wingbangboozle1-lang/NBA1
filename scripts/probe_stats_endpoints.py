#!/usr/bin/env python3
"""probe_stats_endpoints.py - which official endpoint actually returns the
published table?

    python3 scripts/probe_stats_endpoints.py

The 2026-11-15 capture could not read the official team-stat tables. The
stats.nba.com JSON API timed out on every request and the www.nba.com stats
and standings pages render their tables on the client, so a plain fetch
returns only the page shell.

This probe tries the official endpoints in order and records, for each one,
the URL, the HTTP status, the byte count and the SHA-256 of the bytes that
came back. A timeout is recorded as a timeout; it is never turned into a
value.

Nothing here is promoted into a published table. It is evidence.
"""

import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "captures", "2026-11-15", "probe")

SITE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

API_HEADERS = dict(SITE_HEADERS)
API_HEADERS.update({
    "Accept": ("application/json, text/plain, */*"),
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/stats/teams/advanced",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
})

API = ("https://stats.nba.com/stats/leaguedashteamstats"
       "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season"
       "&MeasureType={measure}&PerMode=Totals&DateFrom=&DateTo=&Conference="
       "&Division=&GameScope=&GameSegment=&LastNGames=0&Location=&Month=0"
       "&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&Period=0"
       "&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&SeasonSegment="
       "&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=")

TARGETS = []
for measure in ("Base", "Opponent", "Advanced"):
    TARGETS.append(("api_site_headers_" + measure, API.format(measure=measure),
                    API_HEADERS))
    TARGETS.append(("api_plain_headers_" + measure, API.format(measure=measure),
                    SITE_HEADERS))

TARGETS.append(("cdn_schedule",
                "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
                SITE_HEADERS))
TARGETS.append(("cdn_teams",
                "https://cdn.nba.com/static/json/staticData/teams.json",
                SITE_HEADERS))
TARGETS.append(("www_advanced_page",
                "https://www.nba.com/stats/teams/advanced"
                "?Season=2026-27&SeasonType=Regular+Season", SITE_HEADERS))
TARGETS.append(("www_standings_page",
                "https://www.nba.com/standings", SITE_HEADERS))


def fetch(url, headers, timeout=45):
    t0 = time.time()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            body = resp.read()
            return {"http_status": resp.status, "final_url": resp.geturl(),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "elapsed_ms": int((time.time() - t0) * 1000),
                    "error": None, "body": body,
                    "content_type": resp.headers.get("Content-Type")}
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read()
        except Exception:                                  # noqa: BLE001
            pass
        return {"http_status": exc.code, "final_url": url, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": "HTTP %s" % exc.code, "body": body,
                "content_type": exc.headers.get("Content-Type")
                if exc.headers else None}
    except Exception as exc:                              # noqa: BLE001
        return {"http_status": None, "final_url": url, "bytes": 0, "sha256": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": "%s: %s" % (type(exc).__name__, exc), "body": b"",
                "content_type": None}


def main():
    os.makedirs(OUT, exist_ok=True)
    results = []
    for label, url, headers in TARGETS:
        rec = fetch(url, headers)
        body = rec.pop("body", b"")
        store = None
        if body:
            ext = ".json" if "json" in (rec.get("content_type") or "") else ".html"
            path = os.path.join(OUT, f"{label}{ext}")
            with open(path, "wb") as fh:
                fh.write(body)
            store = os.path.relpath(path, ROOT)
        rec.update({"label": label, "url": url, "stored_path": store,
                    "probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   time.gmtime())})
        results.append(rec)
        print("%-28s %-5s %9sB %8sms %s" % (
            label, str(rec["http_status"]), rec["bytes"], rec["elapsed_ms"],
            rec["error"] or ""))
    with open(os.path.join(OUT, "probe_stats.json"), "w", encoding="utf-8") as fh:
        json.dump({"probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   time.gmtime()),
                   "note": "Evidence only. No value here is promoted into a "
                           "published table without a source link.",
                   "results": results}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
