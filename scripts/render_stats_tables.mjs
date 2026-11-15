// render_stats_tables.mjs - render the three official NBA team-stat pages and
// extract the published tables.
//
// The three pages (traditional, opponent, advanced) are rendered client-side
// from the NBA's own stats service, so a plain HTTP fetch returns only the
// page shell. This script drives the headless Chrome that the GitHub runner
// already has, waits for the table to be painted, and writes the header and
// the rows as JSON.
//
//   node scripts/render_stats_tables.mjs
//
// Output: data/captures/2026-11-15/raw/stats_tables/<name>.json
//
// Every value written here is a value the official page printed. Nothing is
// computed and nothing is inferred: the script reads the cells and copies them.

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const OUT = path.join(ROOT, "data", "captures", "2026-11-15", "raw", "stats_tables");

const PAGES = [
  ["traditional", "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"],
  ["opponent", "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"],
  ["advanced", "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"],
];

const CHROME = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium", "/usr/bin/chromium-browser"];

function chromePath() {
  for (const p of CHROME) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

async function main() {
  const exe = chromePath();
  if (!exe) {
    console.log("no chrome binary found");
    process.exit(2);
  }
  const puppeteer = require("puppeteer-core");
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: exe,
    headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  });
  for (const [name, url] of PAGES) {
    const page = await browser.newPage();
    await page.setUserAgent(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36");
    try {
      await page.goto(url, { waitUntil: "networkidle2", timeout: 120000 });
      await page.waitForFunction(() => {
        const t = document.querySelectorAll("table");
        if (!t.length) return false;
        for (const tbl of t) {
          const rows = tbl.querySelectorAll("tbody tr");
          if (rows.length >= 20) return true;
        }
        return false;
      }, { timeout: 120000 });
      const table = await page.evaluate(() => {
        let best = null;
        for (const tbl of document.querySelectorAll("table")) {
          const rows = tbl.querySelectorAll("tbody tr");
          if (!best || rows.length > best.rows.length) {
            const head = Array.from(tbl.querySelectorAll("thead th")).map(
              (th) => th.innerText.replace(/\s+/g, " ").trim());
            const body = Array.from(rows).map((tr) =>
              Array.from(tr.querySelectorAll("td")).map(
                (td) => td.innerText.replace(/\s+/g, " ").trim()));
            best = { head, body, rows };
          }
        }
        return best;
      });
      const payload = {
        page_url: url,
        rendered_at_utc: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
        method: "headless Chrome render of the official NBA stats page; the "
                + "cells are copied as printed",
        header: table ? table.head : [],
        rows: table ? table.body : [],
      };
      fs.writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify(payload, null, 1));
      console.log(`${name}: ${payload.rows.length} rows, ${payload.header.length} columns`);
    } catch (err) {
      console.log(`${name}: FAILED ${err && err.message}`);
      fs.writeFileSync(path.join(OUT, `${name}.error.json`),
        JSON.stringify({ page_url: url, error: String(err && err.message) }, null, 1));
    } finally {
      await page.close();
    }
  }
  await browser.close();
}

main().catch((e) => {
  console.log("fatal " + (e && e.message));
  process.exit(1);
});
