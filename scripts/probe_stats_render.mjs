// probe_stats_render.mjs - render the official client-rendered pages and
// report what the DOM actually contained.
//
//   node scripts/probe_stats_render.mjs
//
// The NBA stats and standings pages paint their tables in the browser. This
// script opens each page in the runner's headless Chrome, waits for the page
// to settle, and records three things:
//
//   * the rendered HTML of the page (so the table can be parsed offline);
//   * every table it can find, with its header and rows;
//   * the XHR/fetch responses the page made, so the API the page itself uses
//     can be identified and fetched directly.
//
// Output: data/captures/2026-11-15/probe/render_<name>.json

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const OUT = path.join(ROOT, "data", "captures", "2026-11-15", "probe");

const PAGES = [
  ["advanced", "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"],
  ["traditional", "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"],
  ["opponent", "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"],
  ["standings", "https://www.nba.com/standings"],
];

const CHROME = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium", "/usr/bin/chromium-browser"];

function chromePath() {
  for (const p of CHROME) if (fs.existsSync(p)) return p;
  return null;
}

async function main() {
  const exe = chromePath();
  if (!exe) { console.log("no chrome binary found"); process.exit(2); }
  let puppeteer;
  try {
    puppeteer = require("puppeteer-core");
  } catch (e) {
    console.log("puppeteer-core is not installed: " + e.message);
    process.exit(3);
  }
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: exe,
    headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
           "--window-size=1600,1200"],
  });
  for (const [name, url] of PAGES) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1600, height: 1200 });
    await page.setUserAgent(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36");
    await page.setExtraHTTPHeaders({
      "Accept-Language": "en-US,en;q=0.9",
    });
    const xhr = [];
    page.on("response", async (resp) => {
      const u = resp.url();
      if (!/stats\.nba\.com|\/stats\/|api/.test(u)) return;
      if (resp.headers()["content-type"] &&
          !resp.headers()["content-type"].includes("json")) return;
      let body = null;
      try { body = await resp.text(); } catch (e) { body = null; }
      xhr.push({
        url: u,
        status: resp.status(),
        bytes: body ? body.length : 0,
        head: body ? body.slice(0, 400) : null,
      });
    });
    const record = { page_url: url, rendered_at_utc: new Date().toISOString() };
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
      // give the client-side table time to paint
      await new Promise((r) => setTimeout(r, 45000));
      record.title = await page.title();
      record.body_text_head = (await page.evaluate(() => document.body.innerText)).slice(0, 6000);
      record.html = await page.content();
      record.tables = await page.evaluate(() => {
        const out = [];
        for (const tbl of document.querySelectorAll("table")) {
          const head = Array.from(tbl.querySelectorAll("thead th")).map(
            (th) => th.innerText.replace(/\s+/g, " ").trim());
          const rows = Array.from(tbl.querySelectorAll("tbody tr")).map((tr) =>
            Array.from(tr.querySelectorAll("td")).map(
              (td) => td.innerText.replace(/\s+/g, " ").trim()));
          out.push({ header: head, rows, row_count: rows.length });
        }
        return out;
      });
      // the stats site paints rows into divs, not into <table>, so also grab
      // any element whose text looks like a stats row
      record.div_rows = await page.evaluate(() => {
        const sel = "div,li,tr";
        const out = [];
        for (const el of document.querySelectorAll(sel)) {
          const t = (el.innerText || "").trim();
          if (!t || t.length > 400) continue;
          const cells = t.split("\t").map((s) => s.trim()).filter(Boolean);
          if (cells.length >= 8 && /\d/.test(cells[cells.length - 1])) {
            out.push(cells);
          }
        }
        return out.slice(0, 200);
      });
      record.xhr = xhr;
      fs.writeFileSync(path.join(OUT, `render_${name}.json`), JSON.stringify(record, null, 1));
      console.log(`${name}: tables=${(record.tables || []).length} ` +
                  `div_rows=${(record.div_rows || []).length} xhr=${xhr.length}`);
    } catch (err) {
      record.error = String(err && err.message);
      fs.writeFileSync(path.join(OUT, `render_${name}.json`), JSON.stringify(record, null, 1));
      console.log(`${name}: FAILED ${record.error}`);
    } finally {
      await page.close();
    }
  }
  await browser.close();
}

main().catch((e) => { console.log("fatal " + (e && e.message)); process.exit(1); });
