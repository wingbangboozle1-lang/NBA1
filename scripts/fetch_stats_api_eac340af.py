#!/usr/bin/env python3
"""Probe the official NBA stats endpoints behind the client-rendered pages.

WHY THIS EXISTS (flag F-CA-02, requirement R01)

The scheduled refresh (`engine/fetch_official.py`) fetches five official sources that the
published model inputs depend on:

    S1_season            https://www.nba.com/stats/teams/advanced
    S2_train             https://www.nba.com/stats/teams/advanced?DateFrom=...&DateTo=...
    S8_standings         https://www.nba.com/standings
    S9_team_traditional  https://www.nba.com/stats/teams/traditional
    S10_team_opponent    https://www.nba.com/stats/teams/opponent

On 2026-11-19T06:13:47Z the scheduled run stored all five pages at HTTP 200 and then parsed
**0 rows** from each, because those pages are client-rendered shells: the team tables are
built in the browser from an XHR against the official stats API, so the fetched HTML contains
no team records. `engine/refresh_gate.py` therefore BLOCKS the rebuild (it fails closed, which
is correct) and the gated "bet" surface stays closed.

This script does not guess. It asks the question on a machine that has the network: are the
official stats endpoints reachable, and do they return the team rows the parsers need? Every
answer is written with its HTTP status, byte count, SHA-256 and - for JSON - the number of
rows in the first result set, so the answer is a measurement and not an opinion.

Rules
-----
* Only the official hosts `stats.nba.com` and `www.nba.com` may be fetched. Any other host in
  the candidate list aborts the run.
* The browser-like header set is the one the repository's own reachability probe
  (`data/raw/probe_official.json`) measured as returning HTTP 200.
* Nothing is overwritten: raw bytes are written under a new directory keyed by the capture
  stamp, and a manifest records what was asked and what came back.

Usage
-----
    python3 scripts/fetch_stats_api_eac340af.py --out data/raw/session-eac340af
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ALLOWED_HOSTS = {"stats.nba.com", "www.nba.com", "official.nba.com"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Accept-Encoding": "identity",
}

# The five pages the scheduled refresh cannot parse, mapped to the official stats API
# endpoint that renders each one.  Every URL below is an official nba.com address.
SEASON = "2026-27"
SEASON_TYPE = "Regular+Season"
LEAGUE = "00"

CANDIDATES = [
    {
        "key": "S8_standings_leaguestandingsv3",
        "page": "https://www.nba.com/standings",
        "url": (
            "https://stats.nba.com/stats/leaguestandingsv3"
            f"?LeagueID={LEAGUE}&Season={SEASON}&SeasonType={SEASON_TYPE}"
        ),
        "expect": "30 team rows (15 East + 15 West)",
    },
    {
        "key": "S9_team_traditional_leaguedashteamstats_base",
        "page": "https://www.nba.com/stats/teams/traditional",
        "url": (
            "https://stats.nba.com/stats/leaguedashteamstats"
            "?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=0"
            f"&LeagueID={LEAGUE}&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome="
            f"&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition="
            f"&PlusMinus=N&Rank=N&Season={SEASON}&SeasonSegment=&SeasonType={SEASON_TYPE}"
            "&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight=N"
        ),
        "expect": "30 team rows (per-game traditional team stats)",
    },
    {
        "key": "S10_team_opponent_leaguedashoppstats_base",
        "page": "https://www.nba.com/stats/teams/opponent",
        "url": (
            "https://stats.nba.com/stats/leaguedashoppstats"
            "?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=0"
            f"&LeagueID={LEAGUE}&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome="
            f"&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition="
            f"&PlusMinus=N&Rank=N&Season={SEASON}&SeasonSegment=&SeasonType={SEASON_TYPE}"
            "&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight=N"
        ),
        "expect": "30 team rows (opponent-side per-game team stats)",
    },
    {
        "key": "S1_season_leaguedashteamstats_advanced",
        "page": "https://www.nba.com/stats/teams/advanced",
        "url": (
            "https://stats.nba.com/stats/leaguedashteamstats"
            "?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=0"
            f"&LeagueID={LEAGUE}&Location=&MeasureType=Advanced&Month=0&OpponentTeamID=0&Outcome="
            f"&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition="
            f"&PlusMinus=N&Rank=N&Season={SEASON}&SeasonSegment=&SeasonType={SEASON_TYPE}"
            "&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight=N"
        ),
        "expect": "30 team rows (per-game advanced team stats)",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_of(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc


def fetch(url: str, timeout: int = 45) -> dict:
    """Fetch one official URL and describe exactly what came back."""
    host = host_of(url)
    if host not in ALLOWED_HOSTS:
        raise RuntimeError(f"refusing non-official host: {host}")
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl.create_default_context()
    started = time.time()
    out = {
        "url": url,
        "requested_at_utc": now_utc(),
        "http_status": None,
        "bytes": 0,
        "sha256": None,
        "content_type": None,
        "elapsed_s": None,
        "error": None,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            out["http_status"] = int(resp.status)
            out["bytes"] = len(body)
            out["sha256"] = hashlib.sha256(body).hexdigest()
            out["content_type"] = resp.headers.get("Content-Type")
            out["_body"] = body
    except urllib.error.HTTPError as exc:  # an HTTP error is a measurement, not a crash
        out["http_status"] = int(exc.code)
        out["error"] = f"HTTPError {exc.code}: {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - the error text is the measurement
        out["error"] = f"{type(exc).__name__}: {exc}"
    out["elapsed_s"] = round(time.time() - started, 2)
    return out


def describe_json(body: bytes) -> dict:
    """Describe a JSON payload the way a parser would need it."""
    info: dict = {"json_ok": False, "row_count": None, "result_sets": None,
                  "team_ids": None, "sample_headers": None, "parse_error": None}
    try:
        doc = json.loads(body.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        info["parse_error"] = f"{type(exc).__name__}: {exc}"
        return info
    info["json_ok"] = True
    sets = doc.get("resultSets") if isinstance(doc, dict) else None
    if sets is None and isinstance(doc, dict) and "resultSet" in doc:
        sets = [doc]
    if isinstance(sets, list) and sets:
        info["result_sets"] = len(sets)
        first = sets[0]
        rows = first.get("rowSet") or []
        info["row_count"] = len(rows)
        headers = first.get("headers") or []
        info["sample_headers"] = headers[:12]
        ids = set()
        for row in rows:
            if isinstance(row, (list, tuple)):
                for cell in row:
                    if isinstance(cell, str) and cell.isdigit() and len(cell) == 3:
                        ids.add(cell)
        info["team_ids"] = sorted(ids)[:35]
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/raw/session-eac340af")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = os.path.join(args.out, "stats_api", stamp)
    os.makedirs(raw_dir, exist_ok=True)

    manifest = {
        "title": "Official stats-API reachability probe (F-CA-02 / R01)",
        "generated_at_utc": now_utc(),
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "headers": {k: v for k, v in HEADERS.items() if k != "Cookie"},
        "results": [],
    }

    for cand in CANDIDATES:
        print(f"[probe] {cand['key']} -> {cand['url'][:110]}...", flush=True)
        res = fetch(cand["url"])
        body = res.pop("_body", None)
        record = {
            "key": cand["key"],
            "official_page": cand["page"],
            "expects": cand["expect"],
            **res,
        }
        if body:
            name = f"{cand['key']}.json"
            path = os.path.join(raw_dir, name)
            with open(path, "wb") as fh:
                fh.write(body)
            record["stored_bytes_at"] = path
            record["stored_bytes"] = os.path.getsize(path)
            record["stored_sha256"] = hashlib.sha256(body).hexdigest()
            record["json"] = describe_json(body)
        manifest["results"].append(record)
        print(
            f"[probe]   status={record['http_status']} bytes={record['bytes']} "
            f"error={record.get('error')}",
            flush=True,
        )

    manifest["summary"] = {
        "attempted": len(manifest["results"]),
        "http_200": sum(1 for r in manifest["results"] if r.get("http_status") == 200),
        "with_rows": sum(
            1
            for r in manifest["results"]
            if (r.get("json") or {}).get("row_count")
        ),
        "endpoints_that_could_close_fca_02": [
            r["key"]
            for r in manifest["results"]
            if r.get("http_status") == 200
            and (r.get("json") or {}).get("row_count")
            and (r.get("json") or {}).get("row_count", 0) >= 30
        ],
    }
    out_path = os.path.join(args.out, "stats_api_probe_manifest.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps(manifest["summary"], indent=1))
    print(f"[probe] manifest -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
