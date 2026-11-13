// Simple row filter for any table referenced by an input with data-target.
document.querySelectorAll('input.filter').forEach(function (input) {
  var table = document.getElementById(input.dataset.target);
  if (!table) return;
  input.addEventListener('input', function () {
    var q = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function (tr) {
      tr.style.display = tr.textContent.toLowerCase().indexOf(q) === -1 ? 'none' : '';
    });
  });
});
