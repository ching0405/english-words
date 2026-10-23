// The star jar: every finished round drops its stars into a glass jar the
// child can watch filling up. A full jar goes on the shelf beside it and a new
// empty jar starts. Pictures and voice only (no numbers or text).
//
//   Jar.render(box)         draw the current jar (+ shelf) into a container
//   Jar.drop(n, fromEls, box, delay)  add n stars: stars fly from fromEls
//                           into the jar in box, then it refills / celebrates;
//                           returns the Progress.addJarStars result
//   Jar.pop(n, fromEl)      the same in a small overlay (end of a card deck)
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var SHELF_MAX = 4;          // full jars drawn on the shelf; more show a "+"
  // Star slots inside the jar, filled bottom row first, left to right.
  var SLOTS = [];
  [96, 76, 56, 36].forEach(function (y) { [18, 40, 62].forEach(function (x) { SLOTS.push([x, y]); }); });

  function el(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  // One jar picture with `stars` of `size` slots filled.
  function jarSvg(stars, size, cls) {
    var svg = el('svg', { viewBox: '0 0 100 124', class: cls || 'jar-svg', 'aria-hidden': 'true' });
    svg.appendChild(el('rect', { x: 20, y: 4, width: 60, height: 16, rx: 6, fill: '#ff5a5f', stroke: '#2b3a55', 'stroke-width': 4 }));
    svg.appendChild(el('rect', { x: 26, y: 18, width: 48, height: 10, fill: '#ffd8d9', stroke: '#2b3a55', 'stroke-width': 4 }));
    svg.appendChild(el('path', { d: 'M18 28h64q12 0 12 12v68q0 12-12 12H18q-12 0-12-12V40q0-12 12-12z', fill: '#e8f6ff', stroke: '#2b3a55', 'stroke-width': 4, 'class': 'jar-glass' }));
    for (var i = 0; i < Math.min(stars, size); i++) {
      var s = SLOTS[i];
      svg.appendChild(el('use', { href: '#i-star', x: s[0], y: s[1], width: 20, height: 20, 'class': 'jar-star' }));
    }
    svg.appendChild(el('rect', { x: 14, y: 36, width: 6, height: 56, rx: 3, fill: '#fff', opacity: 0.8 }));
    return svg;
  }

  function render(box, state) {
    if (!box) return;
    var j = state || Progress.jar();
    box.textContent = '';
    box.dataset.stars = String(j.stars);
    box.dataset.full = String(j.full);
    box.appendChild(jarSvg(j.stars, j.size || Progress.lib.JAR_SIZE, 'jar-svg jar-main'));
    if (j.full) {
      var shelf = document.createElement('span');
      shelf.className = 'jar-shelf';
      for (var i = 0; i < Math.min(j.full, SHELF_MAX); i++) shelf.appendChild(jarSvg(99, SLOTS.length, 'jar-svg jar-mini'));
      if (j.full > SHELF_MAX) {
        var plus = el('svg', { viewBox: '0 0 48 48', class: 'jar-plus', 'aria-hidden': 'true' });
        plus.appendChild(el('use', { href: '#i-plus' }));
        shelf.appendChild(plus);
      }
      box.appendChild(shelf);
    }
  }

  function renderAll() {
    document.querySelectorAll('.jar-box').forEach(function (b) { render(b); });
  }

  // Stars fly from each source element to the jar inside `box`.
  function fly(box, fromEls, done) {
    var target = box.querySelector('.jar-main');
    if (!target || !fromEls.length || !target.animate) { done(); return; }
    var to = target.getBoundingClientRect();
    var left = fromEls.length;
    fromEls.forEach(function (from, i) {
      var r = from.getBoundingClientRect();
      var s = el('svg', { viewBox: '0 0 48 48', class: 'flying-star' });
      s.appendChild(el('use', { href: '#i-star' }));
      var size = 48;
      s.style.left = (r.left + r.width / 2 - size / 2) + 'px';
      s.style.top = (r.top + r.height / 2 - size / 2) + 'px';
      document.body.appendChild(s);
      var dx = to.left + to.width / 2 - (r.left + r.width / 2);
      var dy = to.top + to.height * 0.6 - (r.top + r.height / 2);
      var a = s.animate([
        { transform: 'translate(0,0) scale(1)', opacity: 1 },
        { transform: 'translate(' + dx * 0.5 + 'px,' + (dy * 0.5 - 60) + 'px) scale(1.2)', opacity: 1, offset: 0.5 },
        { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.4)', opacity: 0.3 }
      ], { duration: 700, delay: i * 180, easing: 'ease-in', fill: 'forwards' });
      a.onfinish = function () {
        s.remove();
        Fx.sound('flip');
        if (--left === 0) done();
      };
    });
  }

  // Add n stars and show them landing in the jar in `box`, then say (queued
  // after what is playing) that the jar grew or is full. A full jar cheers
  // before the new empty one appears.
  // `delay` ms lets other animations (stars popping in) finish first; the
  // stars are saved straight away, whatever happens on screen.
  function drop(n, fromEls, box, delay) {
    box = box || document.querySelector('#result .jar-box');
    var res = Progress.addJarStars(n);
    render(box, { stars: res.before.stars, full: res.before.full, size: Progress.lib.JAR_SIZE });
    setTimeout(function () { fly(box, fromEls || [], landed); }, delay || 0);
    function landed() {
      if (res.filled) {
        // Show it full for a moment, celebrate, then the new jar.
        render(box, { stars: Progress.lib.JAR_SIZE, full: res.before.full, size: Progress.lib.JAR_SIZE });
        Fx.sound('star');
        Fx.move(box.querySelector('.jar-main'), 'cheer');
        box.classList.add('jar-celebrate');
        setTimeout(function () { box.classList.remove('jar-celebrate'); render(box); renderAll(); }, 1600);
      } else {
        render(box);
        Fx.move(box.querySelector('.jar-main'), 'wiggle');
        renderAll();
      }
    }
    Speech.zh(res.filled ? 'jar.full' : 'jar.more', { queue: true });
    return res;
  }

  // Small overlay jar for rounds without a result screen (card deck done).
  var popTimer;
  function pop(n, fromEl) {
    var o = document.getElementById('jarPop');
    o.hidden = false;
    clearTimeout(popTimer);
    var box = o.querySelector('.jar-box');
    var res = drop(n, fromEl ? [fromEl] : [], box);
    popTimer = setTimeout(function () { o.hidden = true; }, res.filled ? 3400 : 2400);
    return res;
  }

  window.Jar = { render: render, renderAll: renderAll, drop: drop, pop: pop };
})();
