(function () {
  document.documentElement.classList.add('js');
  var navbar = document.getElementById('navbar');
  function onScroll() { if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 60); }
  onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
  /* fade-up reveal for content below the fold */
  var still0 = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if ('IntersectionObserver' in window && !still0) {
    var ro = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('visible'); ro.unobserve(e.target); } }); }, { threshold: .12, rootMargin: '0px 0px -40px 0px' });
    [].forEach.call(document.querySelectorAll('.hm-about .ab-in,.pillars>div,.svc-card,.tcard,.news>a,.reasons article,.branch,.pin,.split a,.ab-facts,.tl li,.hm-counts>div,.svc article,details'), function (el) {
      if (el.getBoundingClientRect().top > window.innerHeight) { el.classList.add('reveal'); ro.observe(el); }
    });
  }
  /* countdown to the event banner */
  var cd = document.querySelector('.cd[data-target]');
  if (cd) {
    var target = new Date(cd.dataset.target);
    (function tick() {
      var d = target - new Date(); if (d <= 0) { cd.style.display = 'none'; return; }
      var v = { d: Math.floor(d / 864e5), h: Math.floor(d % 864e5 / 36e5), m: Math.floor(d % 36e5 / 6e4), s: Math.floor(d % 6e4 / 1e3) };
      Object.keys(v).forEach(function (k) { var el = cd.querySelector('[data-u=' + k + ']'); if (el) el.textContent = String(v[k]).padStart(2, '0'); });
      setTimeout(tick, 1000);
    })();
  }
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
