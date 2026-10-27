(function () {
  var lb = document.getElementById('lb'); if (!lb) return;
  var bi = lb.querySelector('.big-im'), cur = null, last = null; window.ISPON = window.ISPON || { moved: 0 };
  function items(g) { return [].filter.call(document.querySelectorAll('[data-lb][data-group="' + g + '"]'), function (e) { return !e.classList.contains('off'); }); }
  function show(el) {
    cur = el; var v = items(el.dataset.group); bi.textContent = ''; bi.style.setProperty('--h', el.dataset.h || 150);
    if (el.dataset.full) { var im = new Image(); im.src = el.dataset.full; im.alt = el.dataset.alt || ''; bi.appendChild(im); } else bi.textContent = 'PHOTO';
    var t = el.dataset.title || el.dataset.cap || '', d = el.dataset.desc; document.getElementById('cap').textContent = t + (d ? ' \u2014 ' + d : ''); document.getElementById('ct').textContent = (v.indexOf(el) + 1) + ' / ' + v.length;
  }
  function step(d) { var v = items(cur.dataset.group); show(v[(v.indexOf(cur) + d + v.length) % v.length]); }
  function close() { lb.classList.remove('on'); if (last) last.focus(); }
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-lb]'); if (!el || ISPON.moved > 6) return;
    last = el; show(el); lb.classList.add('on'); document.getElementById('cl').focus();
  });
  document.getElementById('cl').onclick = close; document.getElementById('pv').onclick = function () { step(-1); }; document.getElementById('nx').onclick = function () { step(1); };
  lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
  addEventListener('keydown', function (e) {
    if (!lb.classList.contains('on')) return;
    if (e.key === 'Escape') close(); if (e.key === 'ArrowRight') step(1); if (e.key === 'ArrowLeft') step(-1);
    if (e.key === 'Tab') { var f = lb.querySelectorAll('button'), a = f[0], z = f[f.length - 1]; if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); } }
  });
})();
