/* NBA1 Command Center — shared render helpers. Vanilla JS, no network at runtime
   except same-origin JSON under data/. */

const CC = (() => {
  const PREFIX = (() => {
    // Works from /, /command-center/ and any deeper path: find this script's own src.
    const s = document.currentScript || [...document.scripts].find((x) => /cc\.js/.test(x.src));
    const src = s ? s.getAttribute("src") || "" : "";
    const i = src.indexOf("assets/cc.js");
    return i === -1 ? "" : src.slice(0, i);
  })();
  const DATA = (p) => PREFIX + "data/" + p;

  async function load(p) {
    const r = await fetch(DATA(p), { cache: "no-store" });
    if (!r.ok) throw new Error(p + " -> HTTP " + r.status);
    return r.json();
  }

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const isNum = (v) => v !== null && v !== undefined && v !== "" && !Number.isNaN(Number(v));

  /* A blank is rendered as a visible em dash with a tooltip. It is never zero. */
  const blank = '<span class="blankdash" title="Not available from an official source — left blank, never inferred">—</span>';

  function n(v, d = 1, signed = false) {
    if (!isNum(v)) return blank;
    const x = Number(v);
    const t = x.toFixed(d);
    if (!signed) return t;
    return (x > 0 ? "+" : "") + t;
  }
  function pct(v, d = 1) { return isNum(v) ? (Number(v) * 100).toFixed(d) + "%" : blank; }
  function num(v, d = 1, cls = "") {
    if (!isNum(v)) return blank;
    const x = Number(v);
    const c = cls || (x > 0 ? "pos" : x < 0 ? "neg" : "");
    return `<span class="${c}">${(x > 0 ? "+" : "") + x.toFixed(d)}</span>`;
  }
  const tag = (t, k = "n") => `<span class="tag ${k}">${esc(t)}</span>`;

  function table(cols, rows, opt = {}) {
    const head = cols.map((c) => `<th class="${c.n ? "n" : ""}">${esc(c.h)}</th>`).join("");
    const body = rows.map((r) => `<tr>${cols.map((c) => {
      let v = typeof c.v === "function" ? c.v(r) : r[c.k];
      if (v === null || v === undefined || v === "") v = blank;
      return `<td class="${c.n ? "n" : ""} ${c.c ? c.c : ""}">${v}</td>`;
    }).join("")}</tr>`).join("");
    return `<div class="tw"><table class="${opt.cls || ""}"><thead><tr>${head}</tr></thead>` +
      `<tbody>${body || `<tr><td colspan="${cols.length}" class="blank">No rows.</td></tr>`}</tbody></table></div>`;
  }

  function kpi(lab, val, note, cls = "") {
    return `<div class="kpi ${cls}"><div class="lab">${esc(lab)}</div><div class="val">${val}</div>` +
      `<div class="note">${note}</div></div>`;
  }

  function set(sel, html) {
    const e = document.querySelector(sel);
    if (e) e.innerHTML = html;
  }
  function fail(sel, e) {
    set(sel, `<div class="bn bad"><div class="ico">!</div><div><p><strong>Could not load the data file.</strong> ` +
      `${esc(e.message)}. The pages read same-origin JSON from <span class="mono">data/</span>; if you opened this ` +
      `file directly from disk the browser blocks that request. Serve the folder over HTTP.</p></div></div>`);
  }

  /* Provenance: one official link per row, per the project's verification rule. */
  const SRC = {
    S1: ["Team Advanced", "https://www.nba.com/stats/teams/advanced"],
    S2: ["Training window", "https://www.nba.com/stats/teams/advanced?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season"],
    S4: ["Schedule", "https://www.nba.com/schedule"],
    S6: ["Injury report 11/13 7:30 PM ET", "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-13_07_30PM.pdf"],
    S7: ["Player stats", "https://www.nba.com/stats/players/traditional"],
    S9: ["Standings", "https://www.nba.com/standings"],
  };
  function src(id, label) {
    if (!id) return blank;
    const s = SRC[id] || [id, null];
    if (!s[1]) return esc(label || id);
    return `<a href="${s[1]}" rel="noopener" target="_blank">${esc(label || s[0])} ↗</a>`;
  }
  function game(id, label) {
    return `<a href="https://www.nba.com/game/${id}" rel="noopener" target="_blank">${esc(label || id)} ↗</a>`;
  }
  function games(date) {
    return `<a href="https://www.nba.com/games?date=${date}" rel="noopener" target="_blank">${esc(date)} ↗</a>`;
  }

  return { PREFIX, DATA, load, esc, n, num, pct, tag, table, kpi, set, fail, src, game, games, blank, isNum };
})();
