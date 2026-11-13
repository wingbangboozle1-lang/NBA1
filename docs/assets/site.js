/* Shared helpers. No build step, no framework, no network calls at runtime. */

const DATA = (p) => DATA_PREFIX + "data/" + p;
/* Resolved from this script's own src so the same file works at docs/ and docs/b/ */
const DATA_PREFIX = (() => {
  const d = document.querySelector("script[src*='site.js']");
  if (!d) return "";
  const src = d.getAttribute("src") || "";
  const i = src.indexOf("assets/site.js");
  return i === -1 ? "" : src.slice(0, i);
})();

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(path + " -> HTTP " + res.status);
  return await res.json();
}

/* --------------------------------------------------------------- formatting */

function esc(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

const nf = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v))
  ? "" : Number(v).toFixed(d);

function num(v, d = 1, cls = "") {
  if (v === null || v === undefined || v === "" || Number.isNaN(v)) {
    return '<span class="blank" title="Not available - no official source value">n/a</span>';
  }
  const n = Number(v);
  let c = cls;
  if (!c) {
    if (n > 0) c = "pos";
    else if (n < 0) c = "neg";
    else c = "muted";
  }
  return `<span class="num ${c}">${n >= 0 && cls === "" ? "" : ""}${n.toFixed(d)}</span>`;
}

function signed(v, d = 1) {
  if (v === null || v === undefined || Number.isNaN(v)) {
    return '<span class="blank" title="Not available - no official source value">n/a</span>';
  }
  const n = Number(v);
  const c = n > 0 ? "pos" : n < 0 ? "neg" : "muted";
  return `<span class="num ${c}">${n > 0 ? "+" : ""}${n.toFixed(d)}</span>`;
}

function price(v) {
  if (v === null || v === undefined) return '<span class="blank">n/a</span>';
  return `<span class="num mono">${v > 0 ? "+" : ""}${v}</span>`;
}

/* ------------------------------------------------------------ source linking */

let SOURCES = {};
let SOURCE_IDX = {};   // id -> {url,title}

async function initSources() {
  SOURCES = await loadJSON(DATA("sources.json"));
  SOURCE_IDX = {};
  for (const [id, s] of Object.entries(SOURCES.sources || {})) {
    SOURCE_IDX[id] = s;
  }
  // game pages: S8_0022600034 -> url
  return SOURCES;
}

function srcLink(id, text) {
  const s = SOURCE_IDX[id];
  if (!s) return "";
  const label = text || id;
  return `<a class="srclink" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.title)}">${esc(label)}</a>`;
}

function srcCell(id) {
  const s = SOURCE_IDX[id];
  if (!s) return '<span class="blank" title="No source">—</span>';
  return `<a class="srclink" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.title)}">${esc(id)}</a>`;
}

/* provenance chips: official | derived | assumption | unverified */
function prov(kind, label) {
  return `<span class="prov ${kind}" title="${PROV_TITLE[kind] || ""}">${esc(label || kind)}</span>`;
}
const PROV_TITLE = {
  official: "Published directly by an official NBA source. Link attached.",
  derived: "Arithmetic or a statistical model applied to official values. Method shown on the Model page.",
  assumption: "A modelling choice, not an official measurement. Listed in the assumptions table.",
  unverified: "Could not be confirmed from an official source. Left blank on purpose - never inferred."
};

function badge(text, kind) {
  return `<span class="badge ${kind || ""}">${esc(text)}</span>`;
}

/* ------------------------------------------------------------------ tables */

/* Build a table from a column spec and rows.
   spec: [{key, label, num:true, fmt:fn, kind:'official'|'derived'|...}] */
function table(cols, rows, opts = {}) {
  if (!rows.length) {
    return `<div class="empty">${esc(opts.empty || "No rows match the current filter.")}</div>`;
  }
  const head = "<thead><tr>" + cols.map((c) => {
    const chip = c.prov ? " " + prov(c.prov, PROV_SHORT[c.prov]) : "";
    return `<th class="${c.num ? "num" : ""}" ${c.width ? `style="width:${c.width}"` : ""}>${esc(c.label)}${chip}</th>`;
  }).join("") + "</tr></thead>";
  const body = "<tbody>" + rows.map((r) => "<tr>" + cols.map((c) => {
    const v = r[c.key];
    let html;
    if (c.fmt) html = c.fmt(v, r);
    else if (c.num) html = c.signed ? signed(v, c.d === undefined ? 1 : c.d) : num(v, c.d === undefined ? 1 : c.d, c.cls);
    else if (c.src) html = srcCell(v);
    else html = esc(v === null || v === undefined ? "—" : v);
    return `<td class="${c.num ? "num" : (c.cls || "")}">${html}</td>`;
  }).join("") + "</tr>").join("") + "</tbody>";
  return `<div class="tablewrap"><table class="${opts.thin ? "thin" : ""}">${head}${body}</table></div>`;
}

/* ----------------------------------------------------------------- filters */

function chipbar(container, options, state, onChange, allLabel = "All") {
  const el = typeof container === "string" ? document.querySelector(container) : container;
  el.innerHTML = "";
  const mk = (val, label) => {
    const b = document.createElement("button");
    b.className = "chip" + (state.val === val ? " on" : "");
    b.textContent = label;
    b.onclick = () => { state.val = val; onChange(); };
    el.appendChild(b);
  };
  mk("", allLabel);
  for (const o of options) mk(o.v !== undefined ? o.v : o, o.l !== undefined ? o.l : o);
}

function setText(sel, txt) {
  const e = document.querySelector(sel);
  if (e) e.textContent = txt;
}

function setHTML(sel, html) {
  const e = document.querySelector(sel);
  if (e) e.innerHTML = html;
}

/* --------------------------------------------------------------- utilities */

function uniq(arr) { return [...new Set(arr.filter((x) => x !== null && x !== undefined))]; }
function sortBy(arr, key, dir = 1) {
  return [...arr].sort((a, b) => {
    const x = a[key], y = b[key];
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
    return String(x).localeCompare(String(y)) * dir;
  });
}

function el(html) {
  const d = document.createElement("div");
  d.innerHTML = html.trim();
  return d.firstElementChild;
}

const PROV_SHORT = { official: "OFF", derived: "DER", assumption: "ASSUM", unverified: "UNVER" };

function gateBadge(status) {
  const map = { PASS: "pass", FAIL: "fail", PROVISIONAL: "prov", "N/A": "na", "NOT RUN": "na" };
  return badge(status, map[status] || "na");
}

function bar(pct, cls) {
  const p = Math.max(0, Math.min(100, pct));
  return `<div class="bar"><i class="${cls || ""}" style="width:${p}%"></i></div>`;
}

/* ---- form + formatting helpers ---- */

function pct(v, d=1) {
  if (v === null || v === undefined || Number.isNaN(v)) return '<span class="blank">n/a</span>';
  return `<span class="num ${v>=0.5?"pos":"neg"}">${(v*100).toFixed(d)}%</span>`;
}
function fillSelect(sel, options) {
  const e = document.querySelector(sel);
  if (!e) return;
  const cur = e.value;
  for (const o of options) {
    if (o && typeof o === "object" && o.v !== undefined) {
      const op = document.createElement("option");
      op.value = o.v; op.textContent = o.l; e.appendChild(op);
    } else {
      const op = document.createElement("option");
      op.value = o; op.textContent = o; e.appendChild(op);
    }
  }
  if (cur) e.value = cur;
}
function fillChipbar(sel, options, onChange, allLabel) {
  const el = document.querySelector(sel);
  if (!el) return;
  el.innerHTML = "";
  const mk = (val, label) => {
    const b = document.createElement("button");
    b.className = "chip" + (val === "" ? " on" : "");
    b.textContent = label;
    b.onclick = () => {
      [...el.children].forEach(c => c.classList.remove("on"));
      b.classList.add("on");
      onChange(val);
    };
    el.appendChild(b);
  };
  mk("", allLabel || "All");
  for (const o of options) mk(o, o);
}
function bind(sel, fn) {
  const e = document.querySelector(sel);
  if (e) e.addEventListener("change", ev => fn(ev.target.value));
}
