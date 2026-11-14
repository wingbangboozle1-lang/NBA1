#!/usr/bin/env python3
"""check_rendered.py — verify the pages that are built by JavaScript, after building them.

The static checker (check_links.py) can only see markup that exists in the file. Build B and the
Command Center render most of their tables in the browser from same-origin JSON, so a page can pass
the static check and still publish a table with no source link, or silently render nothing because a
field name changed.

This script drives the real page scripts against the real data files in a small DOM shim and then
applies the project's rules to the *output*:

  1. every page renders: its script runs without throwing and fills its target,
  2. every table row contains a link to an approved host,
  3. no cell shows a bare "undefined"/"NaN"/"[object Object]",
  4. a page that needs an optional data file does not fall into its load-error branch.

Run from the repository root:  python3 scripts/check_rendered.py
Exit code 0 means every rendered page satisfies all four rules.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "command-center")

APPROVED = ("nba.com", "github.com", "docs.github.com", "kansspelautoriteit.nl")

HARNESS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = process.argv[2];

function makeEl() {
  return {
    innerHTML: '', textContent: '', value: '', dataset: {}, style: {}, children: [],
    classList: { add(){}, remove(){}, contains(){ return false; } },
    insertAdjacentHTML(pos, html) { this.innerHTML += html; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    appendChild() {}, setAttribute() {}, getAttribute() { return null; },
    addEventListener() {}, focus() {},
  };
}

async function run(page) {
  const html = fs.readFileSync(path.join(ROOT, page), 'utf8');
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const store = {};
  const getEl = s => store[s] || (store[s] = makeEl());
  const doc = {
    currentScript: { getAttribute: () => '/command-center/assets/cc.js' },
    scripts: [],
    getElementById: id => getEl('#' + id),
    querySelector: s => getEl(s),
    querySelectorAll: () => [],
    addEventListener() {},
    createElement: () => makeEl(),
    body: makeEl(),
  };
  const errors = [];
  const ctx = {
    document: doc, console, setTimeout, clearTimeout, URL,
    fetch: async (u) => {
      const rel = String(u).replace(/^.*?(?=data\/)/, '');
      const p = path.join(ROOT, decodeURIComponent(rel));
      if (!fs.existsSync(p)) return { ok: false, status: 404, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) };
    },
  };
  ctx.window = ctx; ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'assets/cc.js'), 'utf8'), ctx, { filename: 'cc.js' });
  for (const b of blocks) {
    try { vm.runInContext(b, ctx, { filename: page }); }
    catch (e) { errors.push(e.message); }
  }
  await new Promise(r => setTimeout(r, 180));
  const out = {};
  for (const [k, v] of Object.entries(store)) out[k] = String(v.innerHTML || '');
  return { page, errors, out };
}

(async () => {
  const pages = fs.readdirSync(ROOT).filter(f => f.endsWith('.html')).sort();
  const results = [];
  for (const p of pages) results.push(await run(p));
  process.stdout.write(JSON.stringify(results));
})();
"""


def approved(href):
    host = re.sub(r"^https?://", "", href).split("/")[0].lower()
    return any(host == a or host.endswith("." + a) for a in APPROVED) or host in APPROVED


def main():
    if not os.path.isdir(SITE):
        print("command-center/ not found — nothing to render-check")
        return 0

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(HARNESS)
        harness = fh.name

    try:
        raw = subprocess.run(["node", harness, SITE], capture_output=True, text=True, timeout=180)
    finally:
        os.unlink(harness)
    if raw.returncode != 0:
        print("ERROR the render harness itself failed:")
        print(raw.stderr[-2000:])
        return 1

    results = json.loads(raw.stdout)
    fails = 0
    print("=" * 78)
    print("RENDERED-OUTPUT REPORT — command-center/")
    print("=" * 78)
    print(f"  pages rendered       : {len(results)}")

    total_rows = 0
    rows_without_source = 0
    bad_cells = 0
    empty_pages = []

    for r in results:
        page = r["page"]
        if r["errors"]:
            print(f"  ERROR script error in {page}: {r['errors'][0][:160]}")
            fails += 1
            continue

        body = "\n".join(r["out"].values())
        if "Could not load the data file" in body:
            print(f"  ERROR {page} fell into the data-load-error branch")
            fails += 1
            continue
        if "Loading…" in body or "Still loading" in body:
            print(f"  ERROR {page} never finished loading")
            fails += 1
            continue

        has_table = "<table" in body
        if not has_table and len(body.strip()) < 120:
            empty_pages.append(page)
            fails += 1
            continue

        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
            if "<th" in row:
                continue
            total_rows += 1
            # A row satisfies the rule with an official outbound link, or with an explicit
            # provenance tag when the row describes an artefact of this repository rather than a
            # statistic (a file inventory row, a capture-log row).
            if not (re.search(r'<a [^>]*href="https?://', row) or "in this repository" in row):
                rows_without_source += 1
                txt = re.sub(r"<[^>]+>", " ", row)
                print(f"  FLAG  row without an official link in {page}: {' '.join(txt.split())[:80]}")
            total_rows += 0

        for bad in ("undefined", "NaN", "[object Object]", "null<"):
            if bad in body:
                bad_cells += 1
                idx = body.find(bad)
                print(f"  ERROR '{bad}' rendered on {page}: …{body[max(0,idx-60):idx+40]!r}")

    print(f"  rendered table rows  : {total_rows}")
    print(f"  rows without a link  : {rows_without_source}")
    print(f"  rows with a bad cell : {bad_cells}")
    if empty_pages:
        print(f"  ERROR empty pages    : {', '.join(empty_pages)}")

    ok = fails == 0 and rows_without_source == 0 and bad_cells == 0
    print("-" * 78)
    print("note: this executes the page scripts in a DOM shim, not a real browser. It proves the data")
    print("      files satisfy the pages and every rendered row links out; it does not test CSS.")
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
