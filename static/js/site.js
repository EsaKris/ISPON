(function () {
  var mb = document.querySelector('.mb'), nav = document.getElementById('nav');
  if (mb) mb.onclick = function () { var o = nav.classList.toggle('open'); mb.setAttribute('aria-expanded', o); };
  function flip(f) { f.setAttribute('aria-pressed', f.getAttribute('aria-pressed') !== 'true'); }
  document.addEventListener('click', function (e) { var f = e.target.closest('.flip'); if (f) flip(f); });
  document.addEventListener('keydown', function (e) { var f = e.target.closest && e.target.closest('.flip'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); flip(f); } });
  var els = [].slice.call(document.querySelectorAll('[data-count]'));
  if (els.length && 'IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); count(e.target); } }); }, { threshold: .4 });
    els.forEach(function (el) { io.observe(el); });
  }
  function count(el) {
    var end = +el.dataset.count, pre = el.dataset.prefix || '', suf = el.dataset.suffix || '', t0 = null;
    el.textContent = pre + '0' + suf;
    requestAnimationFrame(function f(t) { if (!t0) t0 = t; var p = Math.min(1, (t - t0) / 1700); el.textContent = pre + Math.round(end * (1 - Math.pow(1 - p, 3))).toLocaleString('en-US') + suf; if (p < 1) requestAnimationFrame(f); });
  }
})();
