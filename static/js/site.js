(function () {
  var mb = document.querySelector('.mb'), nav = document.getElementById('nav');
  if (mb) mb.onclick = function () { var o = nav.classList.toggle('open'); mb.setAttribute('aria-expanded', o); };
  var hero = document.getElementById('hero');
  if (hero) {
    var auto = true, still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    hero.addEventListener('pointermove', function (e) { auto = false; var r = hero.getBoundingClientRect(); hero.style.setProperty('--mx', (e.clientX - r.left) + 'px'); hero.style.setProperty('--my', (e.clientY - r.top) + 'px'); });
    hero.addEventListener('pointerleave', function () { auto = true; });
    (function loop(t) { if (auto && !still) { var r = hero.getBoundingClientRect(); hero.style.setProperty('--mx', r.width * (.5 + .32 * Math.sin(t / 1700)) + 'px'); hero.style.setProperty('--my', r.height * (.45 + .25 * Math.sin(t / 1130 + 1)) + 'px'); } requestAnimationFrame(loop); })(0);
  }
  function flip(f) { f.setAttribute('aria-pressed', f.getAttribute('aria-pressed') !== 'true'); }
  document.addEventListener('click', function (e) { var f = e.target.closest('.flip'); if (f) flip(f); });
  document.addEventListener('keydown', function (e) { var f = e.target.closest && e.target.closest('.flip'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); flip(f); } });
})();
