
// Sortable tables. Click a header to sort; click again to reverse.
// Blanks (a dash rendered as "unavailable") always sort last.
(function () {
  function cellValue(tr, i) {
    var td = tr.children[i];
    if (!td) return "";
    if (td.querySelector(".blank")) return "";
    var t = (td.textContent || "").trim();
    var m = t.match(/^([+-]?\d[\d,]*(\.\d+)?)/);
    if (m) return parseFloat(m[1].replace(/,/g, ""));
    return t.toLowerCase();
  }
  document.querySelectorAll("table[data-sortable]").forEach(function (table) {
    var ths = table.querySelectorAll("thead th");
    ths.forEach(function (th, i) {
      th.title = "Sort by this column";
      th.addEventListener("click", function () {
        var body = table.tBodies[0];
        var rows = Array.prototype.slice.call(body.rows);
        var dir = th.dataset.dir === "asc" ? "desc" : "asc";
        var prev = table.querySelector("th[data-dir]");
        if (prev && prev !== th) delete prev.dataset.dir;
        th.dataset.dir = dir;
        rows.sort(function (a, b) {
          var x = cellValue(a, i), y = cellValue(b, i);
          var xn = typeof x === "number", yn = typeof y === "number";
          if (xn && yn) return dir === "asc" ? x - y : y - x;
          if (xn) return -1;
          if (yn) return 1;
          if (x === "") return 1;
          if (y === "") return -1;
          return dir === "asc" ? (x < y ? -1 : x > y ? 1 : 0) : (x < y ? 1 : x > y ? -1 : 0);
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });
})();
