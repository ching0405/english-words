// The star jar: every finished round drops its stars into a glass jar the
// child can watch filling up. A full jar goes on the shelf beside it and a new
// empty jar starts. Pictures and voice only (no numbers or text).
//
//   Jar.render(box)         draw the current jar (+ shelf) into a container
//   Jar.drop(n, fromEls, box, delay)  add n stars: stars fly from fromEls
//                           into the jar in box, then it refills / celebrates;
//                           returns the Progress.addJarStars result
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var SHELF_MAX = 4;          // full jars drawn on the shelf; more show a "+"
  // Stars lie in a heap, not a grid (Tim, phase 9): layers of 5 and 4 from
  // the bottom up to the neck (30 stars, Tim 2026-10-24: "裝多一點"), each
  // star nudged, turned and sized a little differently, in one of a few golds.
  // A fixed seed: the same heap on every device and every redraw, so a star
  // never jumps when another one lands. PILE.length must equal
  // Progress.lib.JAR_SIZE (tools/test_progress.cjs checks it).
  var GOLDS = ['#ffd43b', '#ffc933', '#ffe066', '#ffbf3f'];
  var FIVE = [19, 34.5, 50, 65.5, 81], FOUR = [26.5, 42, 58, 73.5], THREE = [34.5, 50, 65.5];
  var PILE = (function () {
    var seed = 9, rand = function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    var layers = [[106, FIVE], [95.5, FOUR], [85, FIVE], [74.5, FOUR], [64, FIVE], [53.5, FOUR], [43, THREE]];
    var out = [];
    layers.forEach(function (layer) {
      // Within a layer stars land in a mixed order, not left to right.
      var xs = layer[1].slice().sort(function () { return rand() - 0.5; });
      xs.forEach(function (x) {
        out.push({ x: x + (rand() - 0.5) * 4, y: layer[0] + (rand() - 0.5) * 4, r: (rand() - 0.5) * 56,
                   s: 17 + rand() * 3, c: GOLDS[Math.floor(rand() * GOLDS.length)] });
      });
    });
    return out;
  })();

  function el(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  var SPARK = 'M0 -6Q1 -1 6 0Q1 1 0 6Q-1 1 -6 0Q-1 -1 0 -6Z';   // a 4-point glint

  // One jar picture with `stars` stars in the heap. Stars from index `fresh`
  // on are new: they drop onto the heap (CSS .jar-star-new).
  function jarSvg(stars, size, cls, fresh) {
    var svg = el('svg', { viewBox: '0 0 100 124', class: cls || 'jar-svg', 'aria-hidden': 'true' });
    svg.appendChild(el('rect', { x: 20, y: 4, width: 60, height: 16, rx: 6, fill: '#ff5a5f', stroke: '#2b3a55', 'stroke-width': 4 }));
    svg.appendChild(el('rect', { x: 26, y: 18, width: 48, height: 10, fill: '#ffd8d9', stroke: '#2b3a55', 'stroke-width': 4 }));
    svg.appendChild(el('path', { d: 'M18 28h64q12 0 12 12v68q0 12-12 12H18q-12 0-12-12V40q0-12 12-12z', fill: '#e8f6ff', stroke: '#2b3a55', 'stroke-width': 4, 'class': 'jar-glass' }));
    svg.appendChild(el('ellipse', { cx: 50, cy: 111, rx: 36, ry: 5, fill: '#c6e3f7' }));   // the jar's floor
    var n = Math.min(stars, size, PILE.length);
    for (var i = 0; i < n; i++) {
      var s = PILE[i];
      var drop = el('g', { 'class': 'jar-star-drop' + (fresh !== undefined && i >= fresh ? ' jar-star-new' : '') });
      if (fresh !== undefined && i >= fresh) drop.style.animationDelay = ((i - fresh) * 0.12) + 's';
      var g = el('g', { transform: 'translate(' + s.x.toFixed(1) + ' ' + s.y.toFixed(1) + ') rotate(' + s.r.toFixed(0) + ')' });
      g.appendChild(el('use', { href: '#i-star', x: -s.s / 2, y: -s.s / 2, width: s.s, height: s.s, 'class': 'jar-star', style: 'fill:' + s.c }));
      g.appendChild(el('circle', { cx: -2, cy: -2.4, r: 1.3, fill: '#fff', opacity: 0.85 }));   // a little shine
      drop.appendChild(g);
      svg.appendChild(drop);
    }
    // Two glints twinkle near the top of the heap (still with reduced motion).
    if (n && cls && cls.indexOf('jar-main') >= 0) {
      var top = PILE[n - 1], low = PILE[Math.max(0, n - 3)];
      [[top.x + 9, top.y - 10, 1], [Math.max(low.x, top.x) + 14, low.y - 4, 0.7]].forEach(function (p, k) {
        svg.appendChild(el('path', { d: SPARK, transform: 'translate(' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ') scale(' + p[2] + ')',
                                     fill: '#fff', stroke: '#ffd43b', 'stroke-width': 1, 'class': 'jar-glint jar-glint-' + k }));
      });
    }
    svg.appendChild(el('rect', { x: 14, y: 36, width: 6, height: 56, rx: 3, fill: '#fff', opacity: 0.8 }));
    return svg;
  }

  function render(box, state, fresh) {
    if (!box) return;
    var j = state || Progress.jar();
    box.textContent = '';
    box.dataset.stars = String(j.stars);
    box.dataset.full = String(j.full);
    box.appendChild(jarSvg(j.stars, j.size || Progress.lib.JAR_SIZE, 'jar-svg jar-main', fresh));
    if (j.full) {
      var shelf = document.createElement('span');
      shelf.className = 'jar-shelf';
      for (var i = 0; i < Math.min(j.full, SHELF_MAX); i++) shelf.appendChild(jarSvg(99, PILE.length, 'jar-svg jar-mini'));
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
        render(box, { stars: Progress.lib.JAR_SIZE, full: res.before.full, size: Progress.lib.JAR_SIZE }, res.before.stars);
        Fx.sound('star');
        Fx.move(box.querySelector('.jar-main'), 'cheer');
        box.classList.add('jar-celebrate');
        setTimeout(function () { box.classList.remove('jar-celebrate'); render(box); renderAll(); }, 1600);
      } else {
        render(box, null, res.before.stars);
        Fx.move(box.querySelector('.jar-main'), 'wiggle');
        renderAll();
      }
    }
    Speech.zh(res.filled ? 'jar.full' : 'jar.more', { queue: true });
    return res;
  }

  window.Jar = { render: render, renderAll: renderAll, drop: drop, PILE_SIZE: PILE.length };
})();
