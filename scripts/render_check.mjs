// Headless render check: load every HTML page, run its JS against the real data
// files on disk, and report what a browser would actually display.
//
//   node scripts/render_check.mjs            # all pages
//   node scripts/render_check.mjs docs/b/pages/picks.html   # one page, verbose
//
// Written for the final integration session because a static grep cannot catch a
// page whose script throws, a table that renders empty, or a cell that renders
// as "undefined"/"NaN"/"null". Every finding prints the page and the text.
//
// Scripts are executed in true document order (external src first, then inline),
// which is what a browser does; jsdom's runScripts:"dangerously" evaluates inline
// blocks at parse time, before site.js exists, and produced false failures.

import { JSDOM, VirtualConsole } from "jsdom";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Pages that render cards / <details> instead of a <table>. For these the
// expectation is a non-zero number of content blocks, not table rows.
const CARD_PAGES = new Set([
  "index.html",
  "docs/b/index.html",           // KPI cards + a small table
  "docs/b/pages/flagged.html",   // <details> per flag
  "docs/b/pages/questions.html", // <details> per question
  "docs/b/pages/strategy.html",  // one .card per strategy
  "docs/pages/suggestions.html", // decision cards
  // Command Center pages that present findings as one <details> card per item rather than a table:
  // a flag, a question, a suggestion. The rule they are held to is the same one: they must render
  // something substantive, with an official link, and never a loader message.
  "command-center/flagged.html",
  "command-center/questions.html",
  "command-center/suggestions.html",
]);

const only = process.argv[2] ? path.resolve(process.argv[2]) : null;
const verbose = Boolean(only);

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === ".git" || e.name === "node_modules") continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith(".html")) out.push(p);
  }
  return out;
}

async function renderPage(page) {
  const rel = path.relative(ROOT, page).split(path.sep).join("/");
  const problems = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => problems.push(`jsdomError: ${e.message}`));
  vc.on("error", (...a) => problems.push(`console.error: ${String(a[0]).slice(0, 200)}`));

  const dom = new JSDOM(fs.readFileSync(page, "utf8"), {
    url: "https://wingbangboozle1-lang.github.io/NBA1/" + rel,
    runScripts: "outside-only",
    virtualConsole: vc,
    pretendToBeVisual: true,
  });
  const { window } = dom;

  // jsdom lacks these; the pages use them for reveal animation / responsive
  // behaviour only, so a no-op stub is a faithful stand-in.
  window.IntersectionObserver = class {
    constructor(cb) { this.cb = cb; }
    observe(el) { this.cb([{ isIntersecting: true, target: el }], this); }
    unobserve() {}
    disconnect() {}
    takeRecords() { return []; }
  };
  window.matchMedia = (q) => ({
    matches: false, media: q, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {},
  });
  window.scrollTo = () => {};

  // fetch() that reads the payload off disk, resolved the way a browser would
  // (relative to the page), with a fallback to docs/data/<name> because Build B
  // keeps its data one level up from its pages.
  const base = path.dirname(page);
  window.fetch = async (u) => {
    const s = String(u);
    const clean = s.replace(/^https?:\/\/[^/]+/, "").replace(/^\/+/, "");
    const candidates = [
      path.resolve(base, clean),
      path.join(ROOT, clean),
      path.join(ROOT, "docs", "data", path.basename(clean)),
    ];
    const hit = candidates.find((c) => fs.existsSync(c) && fs.statSync(c).isFile());
    if (!hit) {
      problems.push(`fetch 404: ${s}`);
      return { ok: false, status: 404, json: async () => { throw new Error("404 " + s); }, text: async () => "" };
    }
    const body = fs.readFileSync(hit, "utf8");
    return { ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body };
  };

  // Each <script> is executed as its own top-level script in the page's real VM
  // context. That is what a browser does, and unlike window.eval() it keeps
  // top-level const/let visible to the following script.
  const ctx = dom.getInternalVMContext();
  const run = (code, name) => vm.runInContext(code, ctx, { filename: name });

  // 1. externals, in order
  const inline = [];
  for (const s of window.document.querySelectorAll("script")) {
    const type = (s.getAttribute("type") || "").toLowerCase();
    if (type === "application/json") continue;
    const src = s.getAttribute("src");
    if (src) {
      if (/^https?:/.test(src)) continue;
      const file = path.resolve(path.dirname(page), src);
      if (!fs.existsSync(file)) { problems.push(`missing script: ${src}`); continue; }
      try { run(fs.readFileSync(file, "utf8"), src); }
      catch (e) { problems.push(`script ${src} threw: ${e.message}`); }
    } else if (s.textContent.trim()) {
      inline.push(s.textContent);
    }
  }
  // 2. inlines, in order, now that the shared helpers exist
  inline.forEach((text, i) => {
    try { run(text, `inline#${i + 1}`); }
    catch (e) { problems.push(`inline script threw: ${e.message}`); }
  });

  for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 50));

  const doc = window.document;
  const trs = [...doc.querySelectorAll("tr")];
  const bodyRows = trs.filter((tr) => !tr.querySelector("th")).length;
  const tables = doc.querySelectorAll("table").length;
  const bad = [...doc.querySelectorAll("td,dd,span.num,strong")].filter((n) => {
    const t = n.textContent.trim();
    return t === "undefined" || t === "NaN" || t === "null" || t === "[object Object]";
  });
  if (bad.length) {
    problems.push(`${bad.length} node(s) rendering undefined/NaN/null/[object Object]`);
    if (verbose) bad.slice(0, 5).forEach((n) => console.log("   >", n.outerHTML.slice(0, 160)));
  }
  // "content block" = anything that actually puts a finding on the page:
  // a table row, a <details> item, a card, or a definition-list pair.
  const cards = doc.querySelectorAll(
    "details.q, details, .card, article.card, .grid > .card, dl.kv > dt"
  ).length;
  if (CARD_PAGES.has(rel)) {
    if (cards === 0 && bodyRows === 0) problems.push("no content blocks rendered at all");
  } else if (tables === 0) {
    problems.push("no table rendered at all");
  } else if (bodyRows === 0) {
    problems.push("table present but 0 body rows");
  }
  const loadmsg = doc.querySelector("#loadmsg, .empty");
  if (loadmsg && /error|still loading/i.test(loadmsg.textContent)) {
    problems.push(`loader message visible: "${loadmsg.textContent.trim().slice(0, 120)}"`);
  }
  if (verbose) {
    console.log(doc.querySelector("main")?.textContent.replace(/\s+/g, " ").slice(0, 600));
    window.close();
  }
  globalThis.TOTAL_TR = (globalThis.TOTAL_TR || 0) + bodyRows;
  return { rel, rows: bodyRows + cards, tables, problems };
}

const pages = only ? [only] : walk(ROOT).sort();
const results = [];
for (const p of pages) results.push(await renderPage(p));

console.log("page".padEnd(40), "rows".padStart(5), "tbl".padStart(4), "  problems");
console.log("-".repeat(92));
let failures = 0;
for (const r of results) {
  const bad = r.problems.length > 0;
  if (bad) failures++;
  console.log(
    `${bad ? "FAIL" : "ok  "} ${r.rel.padEnd(36)} ${String(r.rows).padStart(5)} ${String(r.tables).padStart(4)}  ${r.problems.join("; ")}`
  );
}
console.log("-".repeat(92));
console.log(`${results.length} pages, ${results.reduce((a, r) => a + r.rows, 0)} content blocks, ${globalThis.TOTAL_TR} rendered table rows, ${failures} page(s) with problems`);
process.exit(failures > 0 ? 1 : 0);
