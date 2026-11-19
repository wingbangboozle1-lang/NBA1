"""Byte-exact capture of the five official sources the scheduled refresh cannot parse.

    python3 scripts/capture_official_89f7b601.py

WHY THIS EXISTS (COORDINATION.md §69, session `arena/89f7b601-nba1`)

`data/raw/_last_refresh.json` at 2026-11-19T06:13:47Z records five parse
failures out of eight sources:

    S1_season            expected 30 team rows, parsed 0
    S2_train             expected 30 team rows, parsed 0
    S8_standings         East: parsed 0 teams, expected 15 / West: ... 0 ...
    S9_team_traditional  no header row with a Team column found
    S10_team_opponent    no header row with a Team column found

All five returned HTTP 200 with ~294 KB of body, so the *fetch* layer works and
the *parse* layer does not.  Fixing a parser by memory is not allowed in this
project (the standing rule is that a value is either measured from an official
artifact or left blank), so the parser must be developed against the real bytes.

The agent sandbox cannot reach nba.com (`curl` returns http_code 000 for both
www.nba.com and stats.nba.com - measured, not assumed), so the bytes are taken
on a GitHub Actions runner, which can.  This script is what that runner runs.

DESIGN RULES (same as engine/fetch_official.py, deliberately not relaxed)

1. Only the four official hosts are contacted.  Any other host raises.
2. The capture is content-addressed: the file name carries the SHA-256 of the
   exact bytes, and a sidecar record repeats the digest, the URL, the byte
   length and the retrieval clock.  A verifier can re-hash the file and compare.
3. Nothing under `data/raw/*.json` that a snapshot owner committed is touched.
   Everything this script writes lives under `data/raw/session-89f7b601/`.
4. Every endpoint is recorded, including the ones that fail.  A missing capture
   is recorded as missing with its error, never omitted.
5. No value is transcribed here.  The capture stores bytes and a structural
   diagnostic (which parsing strategies the document would support); it never
   states a team's record, rating or rank.

WHAT IT WRITES

    data/raw/session-89f7b601/<name>__<sha256>.bin          exact bytes
    data/raw/session-89f7b601/<name>__<sha256>.json.gz      same bytes, gzipped
                                                            (what the parser test
                                                            decompresses; .bin is
                                                            the re-hash authority)
    data/raw/session-89f7b601/<name>__<sha256>.sidecar.json provenance record
    data/raw/session-89f7b601/capture_manifest.json         one row per endpoint

Endpoints captured:

    S1_season            https://www.nba.com/stats/teams/advanced
    S2_train             https://www.nba.com/stats/teams/advanced?DateFrom=..&DateTo=..
    S8_standings         https://www.nba.com/standings
    S9_team_traditional  https://www.nba.com/stats/teams/traditional
    S10_team_opponent    https://www.nba.com/stats/teams/opponent
    A1_advanced_api      https://stats.nba.com/stats/leaguedashteamstats?MeasureType=Advanced
    A2_traditional_api   https://stats.nba.com/stats/leaguedashteamstats?MeasureType=Traditional
    A3_opponent_api      https://stats.nba.com/stats/leaguedashteamstats?MeasureType=Opponent
    A4_standings_api     https://stats.nba.com/stats/leaguestandings

The four `A*` endpoints are the NBA's own stats service - the data layer behind
the cited www.nba.com/stats pages.  They are captured because the page HTML has
historically been a client-rendered shell (the evidence files under
`data/raw/_capture_evidence_S*.json` show `<tr`: 0 and `/team/`: 0 in the
delivered body), and a documented official endpoint is a far better parse target
than a shell.  Whether the runner can reach it is *measured by this script* and
recorded per attempt; nothing is assumed either way.
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
OUTDIR = os.path.join(ROOT, "data", "raw", "session-89f7b601")

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com",
                 "stats.nba.com"}

# The web-client header set proven by data/raw/probe_official.json
# (`retried_with_browser_headers`).  Without these the stats pages answer 403.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}

STATS_API = ("https://stats.nba.com/stats/leaguedashteamstats"
             "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season"
             "&MeasureType={mt}&PerMode=PerGame&Scope=Season"
             "&LastNGames=0&Month=0&OpponentTeamID=0&TeamID=0"
             "&Period=0&DateFrom={df}&DateTo={dt}&GameSegment=&Location="
             "&Outcome=&SeasonSegment=&VsConference=&VsDivision="
             "&Conference=&Division=&GameScope=&PlayerExperience="
             "&PlayerPosition=&StarterBench=&PaceAdjust=N&PlusMinus=N&Rank=N")

ENDPOINTS = [
    ("S1_season", "https://www.nba.com/stats/teams/advanced"),
    ("S2_train", "https://www.nba.com/stats/teams/advanced"
                 "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season"),
    ("S8_standings", "https://www.nba.com/standings"),
    ("S9_team_traditional", "https://www.nba.com/stats/teams/traditional"),
    ("S10_team_opponent", "https://www.nba.com/stats/teams/opponent"),
    ("A1_advanced_api", STATS_API.format(mt="Advanced", df="", dt="")),
    ("A2_traditional_api", STATS_API.format(mt="Traditional", df="", dt="")),
    ("A3_opponent_api", STATS_API.format(mt="Opponent", df="", dt="")),
    ("A4_standings_api",
     "https://stats.nba.com/stats/leaguestandings?LeagueID=00&Season=2026-27"
     "&SeasonType=Regular+Season&SeasonYear=&IgnoreGB=N"),
]


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url, timeout=60):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError("refusing to fetch a non-official host: %r" % host)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read(), fh.status if hasattr(fh, "status") else 200


def structural_digest(raw):
    """What parsing strategies would this body support?  Counts only.

    This is the honesty check that stops a later session claiming the page
    "obviously" had a table in it: the counts are recorded before any parser
    is written, from the bytes that were actually delivered.
    """
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    return {
        "bytes_delivered": len(raw),
        "html_tr_elements": text.count("<tr"),
        "team_links": len(re.findall(r"/team/\d+", text)),
        "stats_team_links": len(re.findall(r"/stats/team/\d+", text)),
        "next_data_script": text.count('id="__NEXT_DATA__"'),
        "rowSet": text.count("rowSet"),
        "resultSets": text.count("resultSets"),
        "leaguedash": text.count("leaguedash"),
        "stats_nba_com": text.count("stats.nba.com"),
        "rule_34": text.count("rule 34"),
        "looks_like_json": (text.lstrip()[:1] in ("{", "[")),
    }


def already_captured(name):
    """Resume support: a finished endpoint is never re-fetched.

    The first run of this script (run 44476515526) sat on the stats.nba.com
    endpoints for nine minutes without finishing, because that host does not
    answer a runner the way www.nba.com does - which is a finding, and is why
    the API probe is bounded per endpoint and the page bytes are taken first.
    Re-running the job must not repeat work it already completed: every stored
    artifact is content-addressed and its digest is re-verified here, so a
    partial run resumes at the first endpoint still missing.
    """
    if not os.path.isdir(OUTDIR):
        return None
    for fn in sorted(os.listdir(OUTDIR)):
        if not fn.endswith(".sidecar.json") or not fn.startswith(name + "__"):
            continue
        try:
            with open(os.path.join(OUTDIR, fn), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        art = rec.get("artifact")
        path = os.path.join(ROOT, art) if art else None
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                disk = hashlib.sha256(fh.read()).hexdigest()
            if disk == rec.get("sha256"):
                rec["status"] = "stored"
                rec["resumed_from_disk"] = True
                return rec
    return None


def capture(name, url):
    prev = already_captured(name)
    if prev is not None:
        print("   already captured, digest re-verified:", prev.get("sha256"))
        return prev
    rec = {"name": name, "url": url, "retrieved_utc": now_utc()}
    attempts = []
    raw = None
    for attempt in (1, 2, 3):
        t0 = time.time()
        try:
            body, status = get(url, timeout=25)
            attempts.append({"attempt": attempt, "http_status": status,
                             "bytes": len(body),
                             "elapsed_s": round(time.time() - t0, 2)})
            if body and len(body) > 200:
                raw = body
                break
            attempts[-1]["note"] = "body implausibly short"
        except urllib.error.HTTPError as exc:
            attempts.append({"attempt": attempt, "http_status": exc.code,
                             "error": "HTTPError",
                             "elapsed_s": round(time.time() - t0, 2)})
        except Exception as exc:                                  # noqa: BLE001
            attempts.append({"attempt": attempt, "http_status": None,
                             "error": "%s: %s" % (type(exc).__name__, exc),
                             "elapsed_s": round(time.time() - t0, 2)})
        time.sleep(2.0)
    rec["attempts"] = attempts
    if raw is None:
        rec["status"] = "unavailable"
        return rec

    digest = hashlib.sha256(raw).hexdigest()
    stem = "%s__%s" % (name, digest)
    os.makedirs(OUTDIR, exist_ok=True)
    bin_path = os.path.join(OUTDIR, stem + ".bin")
    with open(bin_path, "wb") as fh:
        fh.write(raw)
    # Re-read and re-hash from disk: the digest a verifier will compute is the
    # digest this record must carry, not the digest of the in-memory buffer.
    with open(bin_path, "rb") as fh:
        on_disk = fh.read()
    rec["sha256"] = hashlib.sha256(on_disk).hexdigest()
    rec["sha256_matches_in_memory"] = rec["sha256"] == digest
    with gzip.open(os.path.join(OUTDIR, stem + ".json.gz"), "wb", compresslevel=9) as fh:
        fh.write(on_disk)
    rec["artifact"] = os.path.relpath(bin_path, ROOT)
    rec["gz_artifact"] = os.path.relpath(
        os.path.join(OUTDIR, stem + ".json.gz"), ROOT)
    rec["bytes"] = len(on_disk)
    rec["status"] = "stored"
    rec["structure"] = structural_digest(on_disk)
    rec["content_type_guess"] = (
        "json" if rec["structure"]["looks_like_json"] else
        "pdf" if on_disk[:4] == b"%PDF" else "html")
    side = os.path.join(OUTDIR, stem + ".sidecar.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.write("\n")
    return rec


def main():
    manifest = {"captured_by": "scripts/capture_official_89f7b601.py",
                "captured_at_utc": now_utc(),
                "purpose": "byte-exact bodies for the five official sources whose "
                           "parsers return 0 rows, so the parse repair is developed "
                           "against delivered bytes rather than recollection",
                "note": "Counts and digests only. No official value is transcribed "
                        "by this script.",
                "results": []}
    # Page endpoints first: they are the five the scheduled refresh actually
    # fails on. The API endpoints are a probe behind them, and are deliberately
    # tried last so a slow/absent stats.nba.com cannot cost the page bytes.
    order = [e for e in ENDPOINTS if not e[0].startswith("A")] + \
            [e for e in ENDPOINTS if e[0].startswith("A")]
    for name, url in order:
        print("capture %-22s <- %s" % (name, url), flush=True)
        rec = capture(name, url)
        print("   %s %s" % (rec["status"],
                            rec.get("sha256", rec.get("attempts", [{}])[-1].get("error", ""))),
              flush=True)
        manifest["results"].append(rec)
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, "capture_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    print("wrote", os.path.relpath(path, ROOT))
    stored = sum(1 for r in manifest["results"] if r["status"] == "stored")
    print("stored %d/%d endpoints" % (stored, len(ENDPOINTS)))
    # The five page sources are the contract; the four API probes are
    # evidence-gathering and their absence is recorded, not failed on.
    page_names = [n for n, _ in ENDPOINTS if not n.startswith("A")]
    pages_ok = all(r["status"] == "stored" for r in manifest["results"]
                   if r["name"] in page_names)
    api_ok = sum(1 for r in manifest["results"]
                 if r["name"].startswith("A") and r["status"] == "stored")
    print("page sources captured: %d/%d; API probes reachable: %d/4"
          % (sum(1 for r in manifest["results"]
                 if r["name"] in page_names and r["status"] == "stored"),
             len(page_names), api_ok))
    # Exit 0 only when all five page sources produced bytes: a partial page
    # capture is a finding, and the workflow must not report success on it.
    return 0 if pages_ok else 3


if __name__ == "__main__":
    sys.exit(main())
