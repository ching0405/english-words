// Short cute sounds (synthesised with Web Audio, no files) and picture
// actions (Web Animations), shared by word cards and games.
//
//   Fx.unlock()           call inside the first tap (iOS starts audio muted)
//   Fx.sound(name)        tap, boing, whoosh, sparkle, oops, flip, star,
//                         pop (button press), ding1–ding3 (result stars, rising)
//   Fx.move(el, name)     wiggle, swing, sway (word pictures), shake, cheer
//   Fx.burst(el)          little stars fly out of el (a right answer)
//   Fx.actFor(word)       the word's own sway, e.g. {move: 'swing', sound: 'whoosh'}
//   Fx.tap(el, word)      sway + sound for tapping a word picture
//
// Pictures only rock side to side: no spins, never more than 15 degrees.
// A new move cancels the running one on the same element, and a new sound
// stops the previous one, so fast repeated taps never pile up.
(function () {
  'use strict';

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  var ctx = null;
  var bus = null;           // every sound goes through a soft limiter, so none is harsh
  var playing = [];

  function audio() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      try { ctx = new AC(); } catch (e) { return null; }
      bus = ctx.destination;
      try {
        var limit = ctx.createDynamicsCompressor();
        limit.threshold.value = -14;
        limit.ratio.value = 6;
        limit.connect(ctx.destination);
        bus = limit;
      } catch (e) { /* plain output */ }
    }
    if (ctx.state === 'suspended' && ctx.resume) ctx.resume();
    return ctx;
  }

  function unlock() {
    var c = audio();
    if (!c) return;
    // A silent one-sample buffer started inside the tap unmutes iOS.
    try {
      var src = c.createBufferSource();
      src.buffer = c.createBuffer(1, 1, 22050);
      src.connect(bus);
      src.start(0);
    } catch (e) { /* ignore */ }
  }

  // notes: [startSec, durSec, freqFrom, freqTo, type, volume]
  var SOUNDS = {
    tap: [[0, .14, 520, 880, 'sine', .35]],
    boing: [[0, .22, 620, 220, 'triangle', .35], [.12, .16, 300, 520, 'sine', .2]],
    whoosh: [[0, .3, 300, 1200, 'sine', .22]],
    sparkle: [[0, .14, 1047, 1047, 'sine', .28], [.08, .14, 1319, 1319, 'sine', .28], [.16, .3, 1568, 1568, 'sine', .28], [.16, .3, 784, 784, 'triangle', .12]],
    oops: [[0, .16, 392, 370, 'sine', .22], [.14, .24, 330, 294, 'sine', .22]],
    flip: [[0, .06, 900, 1400, 'triangle', .25]],
    star: [[0, .14, 523, 523, 'triangle', .3], [.12, .14, 659, 659, 'triangle', .3], [.24, .14, 784, 784, 'triangle', .3], [.36, .4, 1047, 1047, 'triangle', .3]],
    pop: [[0, .07, 660, 990, 'sine', .14]],
    ding1: [[0, .32, 784, 784, 'triangle', .3], [0, .32, 1568, 1568, 'sine', .08]],
    ding2: [[0, .32, 988, 988, 'triangle', .3], [0, .32, 1976, 1976, 'sine', .08]],
    ding3: [[0, .5, 1175, 1175, 'triangle', .3], [0, .5, 2349, 2349, 'sine', .08], [.12, .5, 1568, 1568, 'sine', .12]]
  };

  function sound(name) {
    var notes = SOUNDS[name];
    var c = notes && audio();
    if (!c) return;
    playing.forEach(function (o) { try { o.stop(); } catch (e) { /* already stopped */ } });
    playing = [];
    var t0 = c.currentTime + 0.01;
    notes.forEach(function (n) {
      var o = c.createOscillator(), g = c.createGain();
      var s = t0 + n[0], e = s + n[1];
      o.type = n[4];
      o.frequency.setValueAtTime(n[2], s);
      o.frequency.exponentialRampToValueAtTime(n[3], e);
      g.gain.setValueAtTime(0.0001, s);
      g.gain.exponentialRampToValueAtTime(n[5], s + 0.015);
      g.gain.exponentialRampToValueAtTime(0.0001, e);
      o.connect(g);
      g.connect(bus);
      o.start(s);
      o.stop(e + 0.02);
      playing.push(o);
    });
  }

  // Keyframes for Element.animate(); each lasts 500–800ms and tilts at most 12°.
  var MOVES = {
    // quick rock on the spot
    wiggle: [[{ transform: 'none' }, { transform: 'rotate(-9deg)', offset: .2 }, { transform: 'rotate(8deg)', offset: .45 }, { transform: 'rotate(-4deg)', offset: .7 }, { transform: 'none' }], 600],
    // pendulum from the top edge
    swing: [[{ transform: 'none', transformOrigin: '50% 0' }, { transform: 'rotate(12deg)', transformOrigin: '50% 0', offset: .3 }, { transform: 'rotate(-9deg)', transformOrigin: '50% 0', offset: .65 }, { transform: 'none', transformOrigin: '50% 0' }], 750],
    // slow lean from the feet, two small rocks
    sway: [[{ transform: 'none', transformOrigin: '50% 100%' }, { transform: 'rotate(-7deg)', transformOrigin: '50% 100%', offset: .25 }, { transform: 'rotate(6deg)', transformOrigin: '50% 100%', offset: .55 }, { transform: 'rotate(-3deg)', transformOrigin: '50% 100%', offset: .8 }, { transform: 'none', transformOrigin: '50% 100%' }], 800],
    shake: [[{ transform: 'none' }, { transform: 'translateX(-6%)', offset: .2 }, { transform: 'translateX(6%)', offset: .45 }, { transform: 'translateX(-3%)', offset: .7 }, { transform: 'none' }], 500],
    cheer: [[{ transform: 'none' }, { transform: 'scale(1.1) rotate(-5deg)', offset: .3 }, { transform: 'scale(1.08) rotate(5deg)', offset: .6 }, { transform: 'none' }], 700]
  };
  var MOVE_SOUND = { wiggle: 'tap', swing: 'whoosh', sway: 'boing' };
  var WORD_MOVES = ['wiggle', 'swing', 'sway'];

  function move(el, name) {
    var m = MOVES[name];
    if (!el || !m || !el.animate) return null;
    if (el.getAnimations) el.getAnimations().forEach(function (a) { a.cancel(); });
    if (reduced && reduced.matches) {
      // Reduced motion: a gentle glow instead of movement.
      return el.animate([{ filter: 'brightness(1)' }, { filter: 'brightness(1.15)' }, { filter: 'brightness(1)' }], { duration: 400 });
    }
    return el.animate(m[0], { duration: m[1], easing: 'ease-in-out' });
  }

  // Same word, same action every time; different words feel different.
  function actFor(word) {
    var id = String(word.id || word.english || ''), h = 0;
    for (var i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
    var name = WORD_MOVES[h % WORD_MOVES.length];
    return { move: name, sound: MOVE_SOUND[name] };
  }

  function tap(el, word) {
    var a = actFor(word);
    move(el, a.move);
    sound(a.sound);
    return a;
  }

  // Eight little stars fly out of el and fade (no movement when reduced motion is on).
  function burst(el) {
    if (!el || !el.getBoundingClientRect || !document.body.animate || (reduced && reduced.matches)) return;
    var r = el.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    var reach = Math.max(70, Math.min(r.width, r.height) * 0.75);
    for (var i = 0; i < 8; i++) {
      var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      s.setAttribute('viewBox', '0 0 48 48');
      s.setAttribute('class', 'burst-star');
      s.setAttribute('aria-hidden', 'true');
      var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', '#i-star');
      s.appendChild(use);
      s.style.left = (cx - 18) + 'px';
      s.style.top = (cy - 18) + 'px';
      document.body.appendChild(s);
      var a = (i / 8) * Math.PI * 2 + 0.3;
      var dx = Math.cos(a) * reach, dy = Math.sin(a) * reach;
      s.animate([
        { transform: 'translate(0,0) scale(.3)', opacity: 0 },
        { transform: 'translate(' + dx * 0.7 + 'px,' + dy * 0.7 + 'px) scale(1)', opacity: 1, offset: 0.45 },
        { transform: 'translate(' + dx + 'px,' + (dy + 24) + 'px) scale(.6)', opacity: 0 }
      ], { duration: 750, easing: 'ease-out', fill: 'forwards' }).onfinish = (function (node) {
        return function () { node.remove(); };
      })(s);
    }
  }

  window.Fx = { unlock: unlock, sound: sound, move: move, actFor: actFor, tap: tap, burst: burst, moves: Object.keys(MOVES), sounds: Object.keys(SOUNDS) };
})();
