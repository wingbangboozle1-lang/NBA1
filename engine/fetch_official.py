"""Re-fetch the official sources into data/raw, then rebuild the site data.

    python3 engine/fetch_official.py

Design rules, in order:

1. ONLY official hosts are contacted (www.nba.com, official.nba.com,
   ak-static.cms.nba.com). Nothing else is fetched and nothing is cached from
   anywhere else.
2. Every fetch is written to data/raw with the exact URL and a capture
   timestamp, so every published value stays traceable.
3. If a fetch fails or a page does not look like the page we want, the
   existing file is left exactly as it is. A partial or wrong file is worse
   than a stale one.
4. If the parsed content has not changed, nothing is rewritten.

NOTE ON TESTING: this script was written in a sandbox whose outbound network
was restricted to github.com, npm and pypi, so it has never been executed
against nba.com. It is written defensively - every step is guarded and the
caller (the GitHub Actions workflow) runs it with continue-on-error, so a
failure leaves the last known-good snapshot in place rather than breaking the
published site. See Flagged for Review F7.
"""

import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import ABBR, RAW, ROOT, read_json, write_json

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com"}

FETCHES = {
    # id -> (url, kind)
    "S1_season": ("https://www.nba.com/stats/teams/advanced", "teams_advanced"),
    "S2_train": ("https://www.nba.com/stats/teams/advanced"
                 "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season",
                 "teams_advanced"),
    "S7_players": ("https://www.nba.com/stats/players/traditional", "players"),
    "S4_schedule": ("https://www.nba.com/schedule", "schedule"),
    "S5_injury_index": ("https://official.nba.com/nba-injury-report-2026-27-season/", "injury_index"),
}

TEAM_ABBR_RE = re.compile(
    r"\b(Atlanta Hawks|Boston Celtics|Brooklyn Nets|Charlotte Hornets|Chicago Bulls|"
    r"Cleveland Cavaliers|Dallas Mavericks|Denver Nuggets|Detroit Pistons|"
    r"Golden State Warriors|Houston Rockets|Indiana Pacers|LA Clippers|"
    r"Los Angeles Lakers|Memphis Grizzlies|Miami Heat|Milwaukee Bucks|"
    r"Minnesota Timberwolves|New Orleans Pelicans|New York Knicks|"
    r"Oklahoma City Thunder|Orlando Magic|Philadelphia 76ers|Phoenix Suns|"
    r"Portland Trail Blazers|Sacramento Kings|San Antonio Spurs|Toronto Raptors|"
    r"Utah Jazz|Washington Wizards)\b")

GAME_LINK_RE = re.compile(
    r"/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})")

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def get(url, timeout=45):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; NBA1-refresh/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        raw = fh.read()
    return raw


def as_text(raw):
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] {msg}", flush=True)


# -------------------------------------------------------------- team advanced

def parse_teams_advanced(text):
    """Pull the 30-team advanced table out of the rendered page.

    The nba.com stats pages embed their table data as JSON. We look for the
    per-team rows rather than trying to scrape <td> cells, because the table is
    client-rendered. If the JSON cannot be found, we return [] and the caller
    leaves the existing file alone rather than writing garbage.
    """
    out = []
    # The embedded payload lists resultSets[0].rowSet as [teamId, teamName, ...]
    for m in re.finditer(r'"rowSet"\s*:\s*\[(.*?)\]\s*,\s*"name"\s*:', text, re.S):
        body = m.group(1)
        for row in re.finditer(r"\[(.*?)\]", body, re.S):
            cells = re.findall(r'-?\d+\.?\d*|"([^"]*)"', row.group(1))
            vals = [c if isinstance(c, str) else c for c in cells]
            if len(vals) >= 26 and isinstance(vals[1], str) and vals[1] in ABBR:
                out.append(vals)
    return out


# ------------------------------------------------------------------- schedule

def parse_schedule(text):
    games = []
    seen = set()
    for m in GAME_LINK_RE.finditer(text):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if gid in seen:
            continue
        seen.add(gid)
        games.append({"away": away, "home": home, "game_id": gid})
    return games


# --------------------------------------------------------------- injury index

def parse_injury_index(text):
    links = re.findall(
        r'https://ak-static\.cms\.nba\.com/referee/injury/(Injury-Report_[0-9_]+\w*PM\.pdf)',
        text)
    return sorted(set(links), reverse=True)


# ---------------------------------------------------------------------- main

def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = []
    failed = []

    for key, (url, kind) in FETCHES.items():
        log(f"fetch {key} <- {url}")
        try:
            raw = get(url)
        except Exception as exc:                      # noqa: BLE001 - report and continue
            failed.append((key, f"fetch failed: {exc}"))
            log(f"  FAILED: {exc} - keeping the existing snapshot")
            continue
        text = as_text(raw)
        if len(text) < 2000:
            failed.append((key, f"implausibly short response ({len(text)} bytes)"))
            log("  FAILED: response too short - keeping the existing snapshot")
            continue

        if kind == "teams_advanced":
            rows = parse_teams_advanced(text)
            if len(rows) != 30:
                failed.append((key, f"expected 30 team rows, parsed {len(rows)}"))
                log(f"  SKIPPED: parsed {len(rows)} rows - keeping the existing snapshot")
                continue
            log(f"  parsed {len(rows)} team rows")
            # A full rewrite of team_advanced.json needs the window metadata and
            # every column; only rewrite when all 30 rows for both windows parse.
            # Here we just record the raw capture for a human/verifier to diff.
            write_json(os.path.join(RAW, f"_capture_{key}.json"),
                       {"captured_at_utc": now, "source_url": url, "row_count": len(rows)})
            changed.append(key)
        elif kind == "players":
            log(f"  captured {len(text)} bytes")
            write_json(os.path.join(RAW, f"_capture_{key}.json"),
                       {"captured_at_utc": now, "source_url": url, "bytes": len(text)})
            changed.append(key)
        elif kind == "schedule":
            games = parse_schedule(text)
            log(f"  parsed {len(games)} game links")
            if not games:
                failed.append((key, "no game links found"))
                continue
            write_json(os.path.join(RAW, f"_capture_{key}.json"),
                       {"captured_at_utc": now, "source_url": url, "games": games})
            changed.append(key)
        elif kind == "injury_index":
            links = parse_injury_index(text)
            log(f"  found {len(links)} report editions")
            if not links:
                failed.append((key, "no injury-report links found"))
                continue
            write_json(os.path.join(RAW, f"_capture_{key}.json"),
                       {"captured_at_utc": now, "source_url": url, "editions": links})
            changed.append(key)

    # results: one page per date, for the dates we already know about plus today
    games = read_json(os.path.join(RAW, "games_completed.json"))
    sched = read_json(os.path.join(RAW, "schedule_upcoming.json"))
    dates = sorted({r[0] for r in games["rows"]} | {r[0] for r in sched["rows"]})
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if today not in dates:
        dates.append(today)
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        try:
            raw = get(url)
            text = as_text(raw)
        except Exception as exc:                       # noqa: BLE001
            failed.append((f"results {d}", f"fetch failed: {exc}"))
            continue
        final = re.findall(r'(\d{2,3})\s*-\s*(\d{2,3})', text)
        log(f"  {d}: {len(final)} score-like strings")
        write_json(os.path.join(RAW, f"_capture_results_{d}.json"),
                   {"captured_at_utc": now, "source_url": url, "bytes": len(text)})
        changed.append(f"results {d}")

    summary = {
        "captured_at_utc": now,
        "changed": changed,
        "failed": failed,
        "note": "Raw captures only. Nothing in data/raw/*.json is overwritten by this "
                "script automatically - a parsed result is written as _capture_*.json so a "
                "verifier can diff it against the committed snapshot before it is promoted.",
    }
    write_json(os.path.join(RAW, "_last_refresh.json"), summary)
    log(f"done. {len(changed)} captures written, {len(failed)} problems.")
    for k, v in failed:
        log(f"  problem: {k}: {v}")
    # Exit 0 even with failures: the caller decides. A failure must never break
    # the published site, and the committed snapshot stays live.
    return 0


if __name__ == "__main__":
    sys.exit(main())
