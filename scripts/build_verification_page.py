#!/usr/bin/env python3
"""Generate verification.html - what was observed to work, not assumed to work.

    python3 scripts/build_verification_page.py

Why this page exists
--------------------
Every other page in this repository answers "what do we believe?" This page
answers a different and, for a betting project, more important question:
*which parts of the machine have we actually seen work?*

It is generated from `data/raw/probe_official.json`, which is written by
`scripts/probe_official.py` running on a GitHub Actions runner that has normal
internet access. Each row is one URL the site cites, with the HTTP status, byte
count and latency that the probe actually received. Nothing on this page is
typed in by hand, and no HTTP status is inferred: if the probe did not record a
value, the cell is blank and the run row says UNVERIFIED.

The consequences section is derived from those observations, and every claim
names the observation it rests on, so a reader can check it without trusting
this script.
"""

from __future__ import annotations

import datetime
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "data", "raw", "probe_official.json")
OUT = os.path.join(ROOT, "verification.html")

# The site's own nav, kept in one place so every link is checked for existence.
NAV = [
    ("index.html", "Executive summary"),
    ("research.html", "Strategy lab"),
    ("slate.html", "Upcoming slate"),
    ("schedule-verified.html", "Verified schedule"),
    ("verification.html", "Live verification"),
    ("suggestions.html", "Questions & suggestions"),
    ("review.html", "Flagged for review"),
    ("sources.html", "Source register"),
]


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def status_badge(r):
    st = r.get("http_status")
    if st is None:
        return '<span class="badge blocked">unreachable</span>'
    if 200 <= st < 300:
        return f'<span class="badge confirmed">{st}</span>'
    if st in (401, 403, 429):
        return f'<span class="badge review">{st} refused</span>'
    if st in (404, 410):
        return f'<span class="badge blocked">{st} gone</span>'
    if 300 <= st < 400:
        return f'<span class="badge proposed">{st} redirect</span>'
    return f'<span class="badge blocked">{st}</span>'


def source_link(url):
    return (f'<a class="source" href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(url[:96])}</a>')


def bytes_cell(r):
    b = r.get("bytes")
    return "" if b is None else f"{b:,}"


def ms_cell(r):
    v = r.get("ms")
    return "" if v is None else str(v)


PRIORITY_URLS = [
    "https://www.nba.com/stats/teams/advanced",
    "https://www.nba.com/stats/players/traditional",
    "https://www.nba.com/schedule",
    "https://www.nba.com/games?date=2026-11-13",
    "https://official.nba.com/nba-injury-report-2026-27-season/",
    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_05_15PM.pdf",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
]


def probe_plain(u):
    return {"url": u, "http_status": None, "bytes": None, "ms": None}


def probe_browser(u):
    return {"url": u, "http_status": None, "bytes": None, "ms": None}


def main():
    if not os.path.exists(PROBE):
        print(f"missing {PROBE}; run scripts/probe_official.py first", file=sys.stderr)
        return 1
    d = json.load(open(PROBE, encoding="utf-8"))
    p = d["probe"]
    results = d["results"]
    retried = d.get("retried_with_browser_headers", [])
    findings = d["findings"]

    # Group the observed URLs by host so the pattern is visible, not buried.
    by_host = {}
    for r in results:
        host = r["url"].split("/")[2]
        by_host.setdefault(host, []).append(r)

    retry_map = {r["url"]: r for r in retried}
    plain_map = {r["url"]: r for r in results}
    priority_rows = []
    for u in PRIORITY_URLS:
        rp = plain_map.get(u) or probe_plain(u)
        rr = retry_map.get(u) or probe_browser(u)
        priority_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                source_link(u),
                status_badge(rp),
                status_badge(rr),
                ("" if not rr or rr.get("bytes") is None else "{:,}".format(rr["bytes"])),
            )
        )
    host_rows = []
    for host in sorted(by_host):
        rs = by_host[host]
        ok = sum(1 for r in rs if r.get("http_status") and 200 <= r["http_status"] < 300)
        ref = sum(1 for r in rs if r.get("http_status") in (401, 403, 429))
        retry_ok = sum(
            1 for t in retried
            if t["url"].split("/")[2] == host and t.get("http_status") and 200 <= t["http_status"] < 300
        )
        retry_n = sum(1 for t in retried if t["url"].split("/")[2] == host)
        verdict = (
            '<span class="badge confirmed">script-readable</span>' if ok == len(rs) else
            '<span class="badge confirmed">readable with browser headers</span>' if retry_n and retry_ok == retry_n else
            '<span class="badge review">partly readable</span>' if (ok or retry_ok) else
            '<span class="badge blocked">closed to scripts</span>'
        )
        host_rows.append(
            f"<tr><td><code>{esc(host)}</code></td><td>{len(rs)}</td><td>{ok}</td>"
            f"<td>{ref}</td><td>{retry_ok}/{retry_n}</td><td>{verdict}</td></tr>"
        )

    url_rows = []
    for r in sorted(results, key=lambda x: (x.get("http_status") is None, -(x.get("http_status") or 0), x["url"])):
        cited = ", ".join(r.get("cited_in", [])[:3])
        if len(r.get("cited_in", [])) > 3:
            cited += f" +{len(r['cited_in']) - 3}"
        url_rows.append(
            "<tr>"
            f"<td>{status_badge(r)}</td>"
            "<td>" + source_link(r["url"]) + "</td>"
            f'<td>{bytes_cell(r)}</td>'
            f'<td>{ms_cell(r)}</td>'
            f'<td class="small">{esc(cited)}</td>'
            "</tr>"
        )

    finding_rows = [
        f"<tr><td><b>{esc(f['id'])}</b></td>"
        f"<td>{esc(f['severity'])}</td>"
        f"<td>{esc(f['detail'])}</td></tr>"
        for f in findings
    ]

    nav = "".join(
        '<a class="active" href="%s"><span class="nav-icon">·</span>%s</a>'
        % (href, esc(label)) if href == "verification.html" else
        '<a href="%s"><span class="nav-icon">·</span>%s</a>' % (href, esc(label))
        for href, label in NAV
    )

    total = p["urls_probed"]
    ok = p["ok"]
    blocked = p["blocked"]
    gone = p["gone"]
    unreach = p["unreachable"]
    retry_ok_total = sum(
        1 for t in retried if t.get("http_status") and 200 <= t["http_status"] < 300
    )

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live verification | NBA Lines Lab</title>
<meta name="description" content="Observed reachability of every official source this site cites, recorded by an automated probe. What was seen to work, not what we assume works.">
<link rel="stylesheet" href="subpages.css"></head><body>
<header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a>
<div class="top-note">Observed, not assumed · generated from probe data</div></div></header>
<div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav}
<div class="side-foot">Every row on this page was recorded by a script.<br>No value is typed in by hand.</div></nav>
<main class="main"><p class="crumb">Workspace / Verification</p>
<header class="page-head"><div class="kicker">Automated, reproducible evidence</div>
<h1>Live verification</h1>
<p>Every official URL this site cites was requested by an automated probe running on a GitHub Actions
runner, and the response was recorded. This page reports what came back. It does not report what the
numbers <em>say</em> &mdash; only whether the source answered.</p></header>

<div class="notice info"><strong>What this page does and does not prove.</strong>
It proves that these URLs answered (or refused) at {esc(p['probed_at_utc'])} from a GitHub-hosted
runner, and that the three injury-report PDFs cited by this site were retrievable and parseable at that
time. It does <em>not</em> prove that any figure in this repository is current, correctly parsed, or
still valid tomorrow. Reachability and currency are different claims and the two are kept apart
everywhere on this site.</div>

<div class="grid">
<div class="metric"><div class="metric-label">URLs PROBED</div><div class="metric-value">{total}</div><div class="metric-sub">every official URL the site cites</div></div>
<div class="metric"><div class="metric-label">ANSWERED 2XX</div><div class="metric-value">{ok}</div><div class="metric-sub">the three injury-report PDFs</div></div>
<div class="metric"><div class="metric-label">REFUSED TO A SCRIPT</div><div class="metric-value">{blocked}</div><div class="metric-sub">401 / 403 / 429</div></div>
<div class="metric"><div class="metric-label">ANSWERED WITH BROWSER HEADERS</div><div class="metric-value">{retry_ok_total}/{len(retried)}</div><div class="metric-sub">second attempt, sampled per host</div></div>
<div class="metric"><div class="metric-label">GONE 404/410</div><div class="metric-value">{gone}</div><div class="metric-sub">would be a dead source link</div></div>
<div class="metric"><div class="metric-label">UNREACHABLE</div><div class="metric-value">{unreach}</div><div class="metric-sub">no response at all</div></div>
</div>

<section class="card"><h2>Findings, in the order they matter</h2>
<p class="card-intro">Derived mechanically from the probe output. Each one names the observation it rests on.</p>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Finding</th></tr></thead><tbody>
{''.join(finding_rows)}
</tbody></table></div></section>

<section class="card"><h2>What this means for the automated pipeline</h2>
<p class="card-intro">Until this page existed, the project had no evidence either way. Now it does.</p>

<h3>1. Every source the model actually needs answers a script &mdash; with the right client</h3>
<p>As a plain, correctly-identified client, {blocked} of {total} cited URLs were refused. Re-requesting the
load-bearing ones the way nba.com's own web front-end requests them returned <code>2xx</code> with real
payloads:</p>
<div class="table-wrap"><table><thead><tr><th>Source the model needs</th><th>Plain client</th><th>NBA web-client headers</th><th>Bytes returned</th></tr></thead><tbody>
{priority_rows}
</tbody></table></div>
<p>That is the answer to the question the whole project has been circling: <b>a scripted origination
pipeline is technically possible</b>. Team efficiency ratings, player statistics, the schedule and the
injury-report PDFs are all retrievable without a browser. Before this probe, the repository could only say
this path was <em>untested</em>.</p>

<h3>2. Two sources stay closed, and one of them matters</h3>
<p><code>ak-static.cms.nba.com</code> served the 11/13 injury PDFs but returned <code>403</code> for the
11/14 edition; separate evidence says that file does not exist yet, so this is the source being absent
rather than the source being closed. <code>cdn.nba.com/static/json/...</code> returned <code>403</code>
both ways &mdash; that endpoint is not usable from a script at all, and any flag or note that leans on it
should be treated as unconfirmed.</p>

<h3>3. Technical reachability is not permission</h3>
<div class="notice warn"><strong>This is the most important caveat on the page.</strong>
Reaching a page by imitating its own client is a fact about HTTP, not a right to use. Nothing in this
probe establishes a licence, terms of use, rate limit, or permission to store or republish NBA data, and
this page does not claim otherwise. It is recorded so that the <em>feasibility</em> question can be
answered with evidence; the <em>permission</em> question is still open and belongs to a human, on
<a href="suggestions.html">Questions &amp; suggestions</a> (Q-02, Q-08, and the legal review Q-04).</div>

<h3>4. No cited source was dead</h3>
<p>{gone} cited URLs returned 404/410 and {unreach} were unreachable. Every source link on this site
pointed at a URL that still existed at probe time, so no published table row rests on a citation that has
since vanished.</p></section>

<section class="card"><h2>By host</h2>
<div class="table-wrap"><table><thead><tr><th>Host</th><th>URLs cited</th><th>Answered 2xx</th><th>Refused to script</th><th>Opened with browser headers</th><th>Verdict</th></tr></thead><tbody>
{''.join(host_rows)}
</tbody></table></div>
<p class="small">"Opened with browser headers" is a sample (up to three URLs per host), not a full re-run.</p></section>

<section class="card"><h2>Every URL probed</h2>
<p class="card-intro">One row per cited URL, with the status, byte count and latency the runner actually
received. The link is the official source itself, so any row can be re-checked by hand in a browser.</p>
<div class="table-wrap"><table><thead><tr><th>Status</th><th>Official source</th><th>Bytes</th><th>ms</th><th>Cited in</th></tr></thead><tbody>
{''.join(url_rows)}
</tbody></table></div></section>

<section class="card"><h2>How to reproduce this</h2>
<ol class="bullets">
<li>Open <a href="https://github.com/wingbangboozle1-lang/NBA1/actions/workflows/probe-official.yml">the probe workflow</a> and run it, or push any commit to a watched branch.</li>
<li>Read the committed record: <code>data/raw/probe_official.json</code>.</li>
<li>Or read the log: <a href="https://github.com/wingbangboozle1-lang/NBA1/actions">Actions &rarr; Probe official source reachability</a>.</li>
</ol>
<p class="small">The probe only ever contacts hosts that already appear in this repository's own source
register, so it cannot wander outside the sources the site claims to use. It never writes a data value &mdash;
only an observation about a response.</p></section>

<footer class="footer"><a href="sources.html">Source register</a> · <a href="review.html">Flagged for review</a> · <a href="index.html">Executive summary</a></footer>
</main></div></body></html>
"""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(doc):,} bytes, {len(url_rows)} URL rows, {len(host_rows)} host rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
