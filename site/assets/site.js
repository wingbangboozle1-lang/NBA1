/* NBA1 site script: table filtering and gate-cell tooltips. No dependencies. */
(function () {
  "use strict";

  function addSearch(table) {
    var wrap = table.closest(".tablewrap");
    if (!wrap || wrap.dataset.searched === "1") return;
    wrap.dataset.searched = "1";

    var tools = document.createElement("div");
    tools.className = "tbl-tools";
    var input = document.createElement("input");
    input.type = "search";
    input.placeholder = "Filter rows…";
    input.setAttribute("aria-label", "Filter table rows");
    var count = document.createElement("span");
    count.className = "count";
    tools.appendChild(input);
    tools.appendChild(count);
    wrap.parentNode.insertBefore(tools, wrap);

    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    function apply() {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (r) {
        var hit = !q || r.textContent.toLowerCase().indexOf(q) !== -1;
        r.classList.toggle("hidden", !hit);
        if (hit) shown++;
      });
      count.textContent = q ? shown + " of " + rows.length + " rows" : rows.length + " rows";
    }
    input.addEventListener("input", apply);
    apply();
  }

  function addTooltips() {
    var cells = document.querySelectorAll(".g");
    Array.prototype.forEach.call(cells, function (c) {
      var row = c.closest("tr");
      if (!row) return;
      var id = row.querySelector("td");
      if (!id) return;
      var title = c.getAttribute("title");
      if (!title) {
        var headers = document.querySelectorAll("thead th");
        for (var i = 0; i < headers.length; i++) {
          var h = headers[i].textContent.trim();
          if (h === c.textContent.trim() || h.indexOf(c.textContent.trim()) === 0) { title = h; break; }
        }
      }
      if (title) c.setAttribute("title", title);
    });
  }

  function init() {
    var tables = document.querySelectorAll("table.tbl");
    Array.prototype.forEach.call(tables, function (t) {
      if (t.rows.length > 14) addSearch(t);
    });
    addTooltips();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
