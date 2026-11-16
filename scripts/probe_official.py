#!/usr/bin/env python3
"""Probe every official source the site cites, and record what actually happened.

    python3 scripts/probe_official.py

Why this exists
---------------
Both builds were produced in a sandbox whose outbound network was restricted to
github.com, npm and pypi. `engine/fetch_official.py` therefore has never been run
against nba.com, which is recorded as Flagged F7. That is an honest admission but
it leaves the most important question in the project unanswered: *does the
origination pipeline have a live, working feed of official data?*

This script answers it with evidence. It does not guess, and it does not promote
a probe result into a data value: a 200 here means "this URL was reachable at
this instant", not "the numbers in this repository are current". Reachability
and currency are different claims and the site keeps them separate.

Every URL it contacts is extracted from the repository's own source register, so
the probe can never wander outside the sources the site already cites.

Output: data/raw/probe_official.json  (machine-readable, committed)
Exit code: always 0 - a dead source is a finding, not a build failure.
"""

from __future__ import annotations

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
OUT = os.path.join(ROOT, "data", "raw", "probe_official.json")

# Only official NBA properties are probed. The regulator and documentation hosts
# are cited on the site for scope, not for NBA values, so they are recorded but
# reported separately.
PROBE_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com",
    "ak-static.cms.nba.com", "stats.nba.com", "cdn.nba.com",
}
USER_AGENT = "Mozilla/5.0 (compatible; NBA1-probe/1.0; +https://github.com/wingbangboozle1-lang/NBA1)"

# Runtime bounding (session arena/2823d556-nba1, 2026-11-16, COORDINATION §47.1).
#
# Measured, not guessed: the 2026-11-16T01:05Z probe run took **1h16m** for
# **1996 URLs**, and its own record shows 130 `stats.nba.com` URLs returning
# `http_status: null` - i.e. every one of them burned the full 30 s socket
# timeout. 130 x 30 s = 65 min, which is 85 % of the run. A probe that occupies
# a shared runner for over an hour is not a monitoring job, it is a denial of
# service on this repository's own publisher: while it runs, the
# `Publish static site to GitHub Pages` workflow waits behind it (observed
# 2026-11-16 02:0x UTC: production deploys `pending`/`cancelled` for 44-60 min
# while six probe runs held the queue).
#
# Two bounded, honest changes:
#
#   1. `TIMEOUT` 30 s -> 10 s. Every 2xx/403 URL in the 2026-11-16T01:05Z record
#      answered in under 2 s; only the unreachable ones ever approached 30 s.
#   2. A per-host circuit breaker. After `HOST_CIRCUIT_THRESHOLD` consecutive
#      transport failures on one host, the remaining URLs for that host are
#      recorded as NOT RETRIED THIS RUN with the reason printed in the record.
#      They are still listed (a cited source never disappears from the
#      register), still counted, and still flagged - the probe simply stops
#      paying the timeout for a host it has already proven is unreachable.
#
# Both are recorded in the output so a reader can see exactly which URLs were
# measured and which were skipped, and why. Nothing is inferred as reachable.
TIMEOUT = 10
HOST_CIRCUIT_THRESHOLD = 5


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] {msg}", flush=True)


def collect_urls():
    """Every https URL to an official host that appears anywhere in the repo."""
    found = {}
    exts = (".json", ".html", ".js", ".py", ".md")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".github"}]
        for f in filenames:
            if not f.endswith(exts):
                continue
            p = os.path.join(dirpath, f)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in re.finditer(r"https://([\w.\-]+)(/[^\s\"'<>)\\`]*)", text):
                host = m.group(1).lower()
                if host not in PROBE_HOSTS:
                    continue
                url = f"https://{host}{m.group(2)}"
                url = url.rstrip(".,;:)]}")
                found.setdefault(url, set()).add(os.path.relpath(p, ROOT))
    return found


def probe(url, timeout=TIMEOUT):
    started = time.time()
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    rec = {
        "url": url,
        "http_status": None,
        "ms": None,
        "bytes": 0,
        "content_type": None,
        "sha256": None,
        "error": None,
        "final_url": None,
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            body = fh.read()
            rec["http_status"] = fh.status
            rec["final_url"] = fh.geturl()
            rec["content_type"] = fh.headers.get("Content-Type")
            rec["bytes"] = len(body)
            rec["sha256"] = hashlib.sha256(body).hexdigest()
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["error"] = f"HTTP {e.code} {e.reason}"
    except Exception as e:  # noqa: BLE001 - any failure is a finding
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["ms"] = int((time.time() - started) * 1000)
    return rec


def probe_xhr(url, timeout=TIMEOUT):
    """Second attempt with nba.com's public web client headers.

    www.nba.com's stats front-end reads from the same endpoints with these
    headers. Probing both ways separates "the source is closed to scripts" from
    "the source needs specific headers", which are very different conclusions
    for anyone planning an automated pipeline."""
    started = time.time()
    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
        "Connection": "keep-alive",
    })
    rec = {"url": url, "http_status": None, "ms": None, "bytes": 0, "error": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            body = fh.read()
            rec["http_status"] = fh.status
            rec["bytes"] = len(body)
            rec["sha256"] = hashlib.sha256(body).hexdigest()
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["error"] = f"HTTP {e.code} {e.reason}"
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["ms"] = int((time.time() - started) * 1000)
    return rec


# The handful of URLs the whole project actually depends on. These are always
# retried with browser headers, because "can a script read the team advanced
# stats?" decides whether an automated origination pipeline is even possible.
PRIORITY_URLS = [
    "https://www.nba.com/stats/teams/advanced",
    "https://www.nba.com/stats/players/traditional",
    "https://www.nba.com/schedule",
    "https://www.nba.com/games?date=2026-11-13",
    "https://www.nba.com/game/atl-vs-chi-0022600037",
    "https://official.nba.com/nba-injury-report-2026-27-season/",
    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
]


def main():
    urls = collect_urls()
    log(f"{len(urls)} distinct official URLs cited in the repository")
    results = []
    # Per-host circuit breaker (see the TIMEOUT/HOST_CIRCUIT_THRESHOLD note at
    # the top of this file). A host that fails the transport layer N times in a
    # row is not going to answer on attempt N+1 within this run, and paying its
    # full socket timeout for every URL is what turned this job into an
    # hour-long occupant of the shared runner pool.
    host_consecutive_failures = {}
    host_circuit_open = set()
    for i, url in enumerate(sorted(urls), 1):
        host = url.split("/")[2]
        rec = {"url": url, "http_status": None, "ms": None, "bytes": 0,
               "content_type": None, "sha256": None, "error": None,
               "final_url": None}
        if host in host_circuit_open:
            # Recorded, counted and kept in the register - explicitly NOT
            # claimed to have been measured in this run.
            rec["error"] = (f"not retried this run: host '{host}' already failed "
                            f"{HOST_CIRCUIT_THRESHOLD} consecutive transport "
                            f"connections (per-host circuit breaker)")
            rec["retried_this_run"] = False
        else:
            rec = probe(url)
            rec["retried_this_run"] = True
        rec["cited_in"] = sorted(urls[url])
        results.append(rec)
        # Update the breaker only on a real transport failure (http_status None
        # with an error). An HTTP 403 is the host *answering*, so it resets the
        # counter: that host is reachable, it is just refusing this client.
        if rec.get("retried_this_run") and rec["http_status"] is None and rec["error"]:
            host_consecutive_failures[host] = host_consecutive_failures.get(host, 0) + 1
            if host_consecutive_failures[host] >= HOST_CIRCUIT_THRESHOLD:
                host_circuit_open.add(host)
                log(f"circuit open for host '{host}' after "
                    f"{HOST_CIRCUIT_THRESHOLD} consecutive transport failures - "
                    f"its remaining URLs are recorded as not retried this run")
        else:
            host_consecutive_failures[host] = 0
        status = rec["http_status"] if rec["http_status"] is not None else "ERR"
        # `ms` is None when the row was not contacted (circuit open) - print a
        # dash rather than a zero, so a skipped row never looks like a fast
        # measurement.
        ms = f"{rec['ms']:>6}ms" if rec["ms"] is not None else "      -"
        log(f"{i:>3}/{len(urls)}  {status:>4}  {ms}  {rec['bytes']:>9}B  {url}")
        time.sleep(0.4)  # be a polite client; nba.com is not ours

    # Second attempt only on the URLs the first attempt was refused, and only a
    # sample, so the probe stays a polite client.
    # Sample across every host, not just the first few: whether www.nba.com
    # answers a well-behaved client is the single most load-bearing fact for
    # anyone planning the automated pipeline, so it must be tested explicitly.
    by_host = {}
    for r in results:
        if r["http_status"] in (401, 403, 429):
            host = r["url"].split("/")[2]
            by_host.setdefault(host, []).append(r["url"])
    retry_targets = list(PRIORITY_URLS)
    for host, urls in sorted(by_host.items()):
        for u in urls[:2]:
            if u not in retry_targets:
                retry_targets.append(u)
    retried = []
    for u in retry_targets:
        rec = probe_xhr(u)
        retried.append(rec)
        log(f"retry-with-browser-headers  {rec['http_status']}  {u}")

    ok = [r for r in results if r["http_status"] and 200 <= r["http_status"] < 300]
    redirect = [r for r in results if r["http_status"] and 300 <= r["http_status"] < 400]
    gone = [r for r in results if r["http_status"] in (404, 410)]
    blocked = [r for r in results if r["http_status"] in (401, 403, 429)]
    # "failed" = measured this run and unreachable. "not_retried" = recorded in
    # the register but skipped by the per-host circuit breaker. They are
    # different claims and are reported as different numbers.
    failed = [r for r in results
              if r["error"] and r["http_status"] is None and r.get("retried_this_run", True)]
    not_retried = [r for r in results if r.get("retried_this_run") is False]

    findings = []
    if gone:
        findings.append({
            "id": "P1",
            "severity": "High",
            "detail": f"{len(gone)} cited official URL(s) return 404/410. A dead source link "
                      f"means the row it backs cannot be re-verified by a reader.",
            "urls": [r["url"] for r in gone],
        })
    if blocked:
        findings.append({
            "id": "P2",
            "severity": "Medium",
            "detail": f"{len(blocked)} cited URL(s) are refused to a non-browser client "
                      f"(401/403/429). Those values can only be checked by a human in a browser.",
            "urls": [r["url"] for r in blocked],
        })
    if failed:
        findings.append({
            "id": "P3",
            "severity": "High" if len(failed) > len(results) // 2 else "Medium",
            "detail": f"{len(failed)} cited URL(s) could not be reached at all from this runner.",
            "urls": [r["url"] for r in failed],
        })
    if redirect:
        findings.append({
            "id": "P4",
            "severity": "Low",
            "detail": f"{len(redirect)} cited URL(s) redirect. The destination is recorded in "
                      f"final_url so the register can be updated.",
            "urls": [r["url"] for r in redirect],
        })
    if not_retried:
        hosts = sorted({r["url"].split("/")[2] for r in not_retried})
        findings.append({
            "id": "P6",
            "severity": "Informational",
            "detail": (f"{len(not_retried)} cited URL(s) on {len(hosts)} host(s) "
                       f"({', '.join(hosts)}) were NOT retried in this run: each of those "
                       f"hosts had already failed {HOST_CIRCUIT_THRESHOLD} consecutive "
                       f"transport connections, so the per-host circuit breaker stopped "
                       f"spending the socket timeout on them. They are listed for a human "
                       f"check, not reported as reachable. Their status is UNKNOWN for this "
                       f"run - not 200, not 404."),
            "urls": [r["url"] for r in not_retried],
        })
    opened = [r for r in retried if r["http_status"] and 200 <= r["http_status"] < 300]
    if retried and opened:
        findings.append({
            "id": "P5",
            "severity": "Informational",
            "detail": f"{len(opened)}/{len(retried)} refused URL(s) answer when sent nba.com's own "
                      f"web-client headers. Those sources are script-readable with the right client, "
                      f"so an automated pipeline is possible for them.",
            "urls": [r["url"] for r in opened],
        })
    elif retried:
        findings.append({
            "id": "P5",
            "severity": "High",
            "detail": f"All {len(retried)} retried URL(s) stayed refused even with nba.com's own "
                      f"web-client headers. These sources are not machine-readable as-shipped; "
                      f"any pipeline must assume a human-in-the-loop or a licensed feed.",
            "urls": [r["url"] for r in retried],
        })
    if not findings:
        findings.append({
            "id": "P0",
            "severity": "Informational",
            "detail": "Every cited official URL answered with a 2xx at probe time.",
            "urls": [],
        })

    doc = {
        "probe": {
            "probed_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "runner": os.environ.get("RUNNER_OS", "unknown") + "/" + os.environ.get("ImageOS", "local"),
            "urls_probed": len(results),
            "ok": len(ok),
            "redirect": len(redirect),
            "gone": len(gone),
            "blocked": len(blocked),
            "unreachable": len(failed),
            "not_retried_circuit_open": len(not_retried),
            "socket_timeout_seconds": TIMEOUT,
            "host_circuit_threshold": HOST_CIRCUIT_THRESHOLD,
            "user_agent": USER_AGENT,
        },
        "what_this_proves": (
            "That these URLs answered at this instant from this runner. It does NOT prove "
            "that any number in this repository is current, that a value was parsed correctly, "
            "or that the source will still exist tomorrow. Reachability and currency are "
            "separate claims."
        ),
        "what_this_run_did_not_measure": (
            f"{len(not_retried)} URL(s) were recorded but not contacted in this run because "
            f"their host had already failed {HOST_CIRCUIT_THRESHOLD} consecutive transport "
            f"connections (finding P6). Their status is unknown for this run - it is not "
            f"reported as reachable, and it is not reported as dead."
        ),
        "retried_with_browser_headers": retried,
        "findings": findings,
        "results": results,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    log(f"wrote {os.path.relpath(OUT, ROOT)}")
    log(f"ok={len(ok)} redirect={len(redirect)} gone={len(gone)} "
        f"blocked={len(blocked)} unreachable={len(failed)} not_retried={len(not_retried)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
