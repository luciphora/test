(function () {
  var list = document.getElementById('txlist');
  if (!list) return;
  var items = Array.prototype.slice.call(list.querySelectorAll('.tx'));
  var q = document.getElementById('q'), fs = document.getElementById('fs'),
      ff = document.getElementById('ff'), fv = document.getElementById('fv'),
      count = document.getElementById('count');

  // Vertical options come from the rendered ads, so the filter can never offer
  // a vertical that has no transcripts behind it.
  var verts = {};
  items.forEach(function (el) { verts[el.dataset.v] = 1; });
  Object.keys(verts).sort().forEach(function (v) {
    var o = document.createElement('option'); o.value = v; o.textContent = v; fv.appendChild(o);
  });

  // Cache the original text once: re-reading textContent after highlighting
  // would fold previous <mark> tags into the search corpus.
  items.forEach(function (el) {
    var p = el.querySelector('p');
    el.__p = p; el.__raw = p.textContent; el.__low = p.textContent.toLowerCase();
  });

  function esc(s) { return s.replace(/[&<>]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }

  function apply() {
    var term = q.value.trim().toLowerCase(),
        s = fs.value, f = ff.value, v = fv.value, shown = 0;
    items.forEach(function (el) {
      var ok = (!s || el.dataset.s === s) && (!f || el.dataset.f === f) &&
               (!v || el.dataset.v === v) && (!term || el.__low.indexOf(term) !== -1);
      el.style.display = ok ? '' : 'none';
      if (!ok) return;
      shown++;
      if (term) {
        var re = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
        el.__p.innerHTML = esc(el.__raw).replace(re, '<mark>$1</mark>');
      } else if (el.__p.innerHTML !== el.__raw) {
        el.__p.textContent = el.__raw;
      }
    });
    count.textContent = shown + ' of ' + items.length;
  }

  [q, fs, ff, fv].forEach(function (el) {
    el.addEventListener('input', apply); el.addEventListener('change', apply);
  });
  apply();
})();
