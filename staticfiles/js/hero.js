(function () {
  var root = document.getElementById('hero'); if (!root) return;
  var slides = [].slice.call(root.querySelectorAll('.hc-slide')), n = slides.length, i = 0, timer = null, userPaused = false, hovering = false,
    still = matchMedia('(prefers-reduced-motion: reduce)').matches, auto = root.dataset.autoplay === '1', ms = (+root.dataset.interval || 7) * 1000,
    dots = [].slice.call(root.querySelectorAll('.hc-dot')), live = root.querySelector('.hc-live'), pb = root.querySelector('.hc-pause');
  function media(s, on) { var v = s.querySelector('video'); if (!v) return; if (on && !still) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause(); }
  function stop() { clearTimeout(timer); timer = null; }
  function restart() { stop(); if (auto && !still && !userPaused && !hovering && n > 1) timer = setTimeout(function () { show(i + 1); }, ms); }
  function show(k, user) {
    i = (k + n) % n;
    slides.forEach(function (s, j) { var on = j === i; s.classList.toggle('is-active', on); s.setAttribute('aria-hidden', on ? 'false' : 'true'); media(s, on); });
    dots.forEach(function (d, j) { d.setAttribute('aria-current', j === i ? 'true' : 'false'); });
    if (user && live) live.textContent = 'Slide ' + (i + 1) + ' of ' + n;
    restart();
  }
  function on(sel, fn) { var el = root.querySelector(sel); if (el) el.addEventListener('click', fn); }
  on('.hc-prev', function () { show(i - 1, true); }); on('.hc-next', function () { show(i + 1, true); });
  dots.forEach(function (d, j) { d.addEventListener('click', function () { show(j, true); }); });
  if (pb) pb.addEventListener('click', function () { userPaused = !userPaused; pb.setAttribute('aria-pressed', userPaused); pb.textContent = userPaused ? '\u25B6' : 'II'; pb.setAttribute('aria-label', userPaused ? 'Play slides' : 'Pause slides'); restart(); });
  root.addEventListener('mouseenter', function () { hovering = true; stop(); }); root.addEventListener('mouseleave', function () { hovering = false; restart(); });
  root.addEventListener('focusin', function () { hovering = true; stop(); }); root.addEventListener('focusout', function () { hovering = false; restart(); });
  root.addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') show(i + 1, true); if (e.key === 'ArrowLeft') show(i - 1, true); });
  var x0 = null;
  root.addEventListener('pointerdown', function (e) { if (!e.target.closest('button,a')) x0 = e.clientX; });
  root.addEventListener('pointerup', function (e) { if (x0 === null) return; var dx = e.clientX - x0; x0 = null; if (Math.abs(dx) > 60) show(dx < 0 ? i + 1 : i - 1, true); });
  slides.forEach(function (s) {
    if (!s.classList.contains('flashlight')) return;
    s._auto = true;
    s.addEventListener('pointermove', function (e) { s._auto = false; var r = s.getBoundingClientRect(); s.style.setProperty('--mx', (e.clientX - r.left) + 'px'); s.style.setProperty('--my', (e.clientY - r.top) + 'px'); });
    s.addEventListener('pointerleave', function () { s._auto = true; });
  });
  (function loop(t) {
    var s = slides[i];
    if (s && s.classList.contains('flashlight') && s._auto && !still) { var r = s.getBoundingClientRect(); s.style.setProperty('--mx', r.width * (.5 + .32 * Math.sin(t / 1700)) + 'px'); s.style.setProperty('--my', r.height * (.45 + .25 * Math.sin(t / 1130 + 1)) + 'px'); }
    requestAnimationFrame(loop);
  })(0);
  media(slides[0], true); restart();
})();
