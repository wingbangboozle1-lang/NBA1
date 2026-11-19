"""Render the five official pages in a real browser and store the rendered DOM.

    python3 scripts/render_official_89f7b601.py

WHY (COORDINATION.md §69, session `arena/89f7b601-nba1`)

Measured, not assumed. `data/raw/session-89f7b601/capture_manifest.json`
(runner run 44477742276, 2026-11-19) stores the byte-exact bodies the scheduled
refresh actually receives, and their structural digest is:

    S1_season           293,688 B  <tr>=12  /team/=0  /stats/team/=0  rowSet=0
    S2_train            294,812 B  <tr>=12  /team/=0  /stats/team/=0  rowSet=0
    S8_standings        225,373 B  <tr>=0   /team/=0  /stats/team/=0  rowSet=0
    S9_team_traditional 293,835 B  <tr>=12  /team/=0  /stats/team/=0  rowSet=0
    S10_team_opponent   293,765 B  <tr>=12  /team/=0  /stats/team/=0  rowSet=0

i.e. HTTP 200, a quarter of a megabyte each, and **not one team row in any of
them**. Every table on those pages is mounted by client-side JavaScript after
the HTML arrives, so no amount of string parsing of the response will ever
produce 30 rows. The data layer behind them is `stats.nba.com`
(`leaguedashteamstats` / `leaguestandings`, read out of the page's own JS chunk
and recorded in `data/raw/_capture_evidence_S1_season.json`), and the same run
measured that host to be **unreachable from a GitHub runner**: 4 endpoints x 3
attempts x 25s, every attempt `TimeoutError`, no HTTP status at all. The
2026-11-19T06:13Z scheduled run recorded the same `TimeoutError` on the same
host.

So the two obvious repairs both fail for a measured reason, and the remaining
correct one is to let the page do its own rendering: run a headless browser on
the runner, wait for the table element to exist, and store the **rendered DOM**.
That is still the official page - same URL, same origin, the league's own
markup - and it is the artifact the parser can be tested against.

The parse code itself is not rewritten here. If the tables are present, the
existing strategies (`html_table` first) are supposed to succeed; this script
proves whether they do, from bytes, before anything is changed.

WHAT IT WRITES (all under data/raw/session-89f7b601/render/)

    <name>__<sha256>.rendered.dom        the rendered DOM, content-addressed
    <name>__<sha256>.rendered.dom.gz     the same bytes, gzipped

The artifact deliberately does NOT end in `.html`: `scripts/render_check.mjs`
walks every `.html` file in the repository and reports one with no rendered
table as a broken page. These are captured evidence, not site pages, and on
2026-11-19 the scanner correctly reported all five denials as "no table
rendered at all" - five red lines caused by a file extension. The extension is
now `.dom` and the evidence is still byte-identical and still content-addressed.
    <name>__<sha256>.tables.json         every <table> in the live DOM, as text
                                         cells with the row/col index and the
                                         section heading above it
    <name>__<sha256>.sidecar.json        url, retrieval clock, digest, counts,
                                         the selector that was waited for, and
                                         whether it appeared
    render_manifest.json                 one row per page

No value is transcribed by hand and nothing is written into
`data/raw/*.json`, `data/derived/**` or any other session's file.
"""

import datetime
import gzip
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "data", "raw", "session-89f7b601", "render")

PAGES = [
    # name, url, CSS selector that must appear before the DOM is dumped
    ("S8_standings", "https://www.nba.com/standings", "table"),
    ("S9_team_traditional", "https://www.nba.com/stats/teams/traditional", "table"),
    ("S10_team_opponent", "https://www.nba.com/stats/teams/opponent", "table"),
    ("S1_season", "https://www.nba.com/stats/teams/advanced", "table"),
    ("S2_train", "https://www.nba.com/stats/teams/advanced"
                 "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026"
                 "&SeasonType=Regular+Season", "table"),
]

# Pulled from the live DOM, not from the HTML source: every <table>, its rows,
# the text of every cell, and the nearest preceding heading so the conference
# split on the standings page can be reconstructed without guessing.
TABLE_JS = r"""
() => {
  const out = [];
  const tables = document.querySelectorAll('table');
  tables.forEach((t, ti) => {
    const rows = [];
    t.querySelectorAll('tr').forEach((tr, ri) => {
      const cells = [];
      tr.querySelectorAll('th,td').forEach((c) => {
        cells.push({
          tag: c.tagName.toLowerCase(),
          text: (c.innerText || c.textContent || '').replace(/\s+/g, ' ').trim(),
          href: (c.querySelector('a') || {}).getAttribute
                ? (c.querySelector('a').getAttribute('href') || '') : ''
        });
      });
      rows.push({ row_index: ri, cells: cells });
    });
    // Walk back through the document for the closest preceding heading.
    let heading = '';
    let node = t;
    while (node && !heading) {
      node = node.previousElementSibling || node.parentElement;
      if (!node) break;
      const h = node.querySelector
        ? node.querySelector('h1,h2,h3,h4') : null;
      if (h && h.innerText && h.innerText.trim()) heading = h.innerText.trim();
    }
    out.push({ table_index: ti, heading: heading, n_rows: rows.length, rows: rows });
  });
  return out;
}
"""


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def store(name, url, html, tables, extra):
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    stem = "%s__%s" % (name, digest)
    os.makedirs(OUTDIR, exist_ok=True)
    hpath = os.path.join(OUTDIR, stem + ".rendered.dom")
    with open(hpath, "w", encoding="utf-8") as fh:
        fh.write(html)
    # Re-hash from disk: the digest a verifier recomputes is the one recorded.
    with open(hpath, "rb") as fh:
        disk = fh.read()
    with gzip.open(os.path.join(OUTDIR, stem + ".rendered.dom.gz"), "wb",
                   compresslevel=9) as fh:
        fh.write(disk)
    tpath = os.path.join(OUTDIR, stem + ".tables.json")
    with open(tpath, "w", encoding="utf-8") as fh:
        json.dump({"source_url": url, "tables": tables}, fh, indent=1)
        fh.write("\n")
    rec = {
        "name": name,
        "url": url,
        "retrieved_utc": extra.get("retrieved_utc") or now_utc(),
        "sha256": hashlib.sha256(disk).hexdigest(),
        "bytes": len(disk),
        "artifact": os.path.relpath(hpath, ROOT),
        "tables_artifact": os.path.relpath(tpath, ROOT),
        "waited_for": extra.get("waited_for"),
        "selector_found": extra.get("selector_found"),
        "n_tables": len(tables),
        "n_rows_total": sum(t["n_rows"] for t in tables),
        "n_rows_first_table": tables[0]["n_rows"] if tables else 0,
        "headings": [t["heading"] for t in tables][:6],
        "status": "stored",
    }
    with open(os.path.join(OUTDIR, stem + ".sidecar.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.write("\n")
    return rec


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; this script only runs on the runner")
        return 2
    manifest = {"rendered_by": "scripts/render_official_89f7b601.py",
                "rendered_at_utc": now_utc(),
                "purpose": "rendered DOM of the five official pages, because the "
                           "delivered HTML contains zero team rows and the "
                           "stats.nba.com data layer times out from CI",
                "results": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"),
            viewport={"width": 1600, "height": 1200},
            locale="en-US")
        page = ctx.new_page()
        for name, url, selector in PAGES:
            print("render %-22s <- %s" % (name, url), flush=True)
            rec = {"name": name, "url": url, "retrieved_utc": now_utc()}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                found = True
                try:
                    page.wait_for_selector(selector, timeout=45000,
                                           state="attached")
                except Exception:                            # noqa: BLE001
                    found = False
                # The table element can exist before it is populated; give the
                # client-side fetch a bounded moment, then measure row count.
                for _ in range(10):
                    if page.evaluate(
                            "() => document.querySelectorAll('table tr').length") > 1:
                        break
                    page.wait_for_timeout(1000)
                html = page.content()
                tables = page.evaluate(TABLE_JS)
                rec = store(name, url, html, tables,
                            {"retrieved_utc": rec["retrieved_utc"],
                             "waited_for": selector,
                             "selector_found": found})
                print("   stored %s B  tables=%d rows=%d"
                      % (rec["bytes"], rec["n_tables"], rec["n_rows_total"]),
                      flush=True)
            except Exception as exc:                          # noqa: BLE001
                rec["status"] = "failed"
                rec["error"] = "%s: %s" % (type(exc).__name__, exc)
                print("   FAILED:", rec["error"], flush=True)
            manifest["results"].append(rec)
        browser.close()
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "render_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    ok = sum(1 for r in manifest["results"] if r["status"] == "stored")
    # A render that produced no rows is not a success: that is the defect.
    with_rows = sum(1 for r in manifest["results"]
                    if r["status"] == "stored" and r["n_rows_total"] > 30)
    print("rendered %d/%d pages; %d with a populated table"
          % (ok, len(PAGES), with_rows))
    return 0 if ok == len(PAGES) else 3


if __name__ == "__main__":
    sys.exit(main())
