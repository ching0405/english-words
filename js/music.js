// Light, upbeat background music, made in the browser (no audio file): a
// 32-second loop in C major pentatonic (bright triangle melody, bouncy bass,
// soft shaker and wood-block clicks), rendered once with OfflineAudioContext
// and then looped. Quiet (about -32 LUFS), and quieter still (-12 dB) while
// a voice line plays, so it never covers the words.
//
//   Music.render(rate)   Promise<AudioBuffer> of one loop (tests, preview tool)
//   Music.start()        call inside a tap: starts (or resumes) the loop if on
//   Music.on / setOn(b)  the home-screen switch (saved in ew.settings.v1.music)
//   Music.duck(b)        true while a voice line plays (Speech busy/idle)
//   Music.pause()        the page went to the background
//   Music.level()        the gain the loop is heading for; Music.gain() now (tests)
(function () {
  'use strict';

  // v2 (Tim: "太輕柔了，可以活潑一點"): 120 BPM instead of 90, melody an octave
  // up, bass bouncing in eighths, light percussion.
  var BPM = 120, BARS = 16;
  var BEAT = 60 / BPM;
  var LOOP = BARS * 4 * BEAT;           // 32 s
  var TAIL = 1.5;                        // ring-out folded back onto the start
  var LEVEL = 1.2;                       // loop gain when nothing is speaking: about -32 LUFS
  var DUCK = Math.pow(10, -12 / 20);     // -12 dB under a voice line
  var C4 = 261.63;
  // Bars as chords in semitones from C: C G Am F | C G F G | Am F C G | F G C G.
  var C = [0, 4, 7], G = [7, 11, 14], AM = [9, 12, 16], F = [5, 9, 12];
  var CHORDS = [C, G, AM, F, C, G, F, G, AM, F, C, G, F, G, C, G];
  var PENTA = [0, 2, 4, 7, 9, 12, 14, 16];
  // Melody: eighth-note slots per bar, 1 = play. A 4-bar phrase, repeated.
  var RHYTHM = [[1, 0, 1, 1, 0, 1, 1, 0], [1, 1, 0, 1, 1, 0, 1, 0], [1, 0, 1, 1, 0, 1, 0, 1], [1, 0, 1, 0, 1, 0, 0, 0]];
  // Bass per bar in eighths: root, -, fifth, root+8va, root, -, fifth, - (a bounce).
  var BASS = [[0, 0], [2, 7], [3, 12], [4, 0], [6, 7]];

  function hz(semi) { return C4 * Math.pow(2, semi / 12); }

  // Small fixed random source: the tune is the same on every device.
  function seeded(seed) {
    return function () { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  }

  function note(c, out, t, f, dur, vol, type) {
    var o = c.createOscillator(), g = c.createGain();
    o.type = type || 'sine';
    o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(out);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  // Shaker: a short burst of high noise. Wood block: a tiny falling "tok".
  function shaker(c, out, noise, t, vol) {
    var src = c.createBufferSource(), g = c.createGain();
    src.buffer = noise;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.07);
    src.connect(g);
    g.connect(out);
    src.start(t);
    src.stop(t + 0.1);
  }
  function block(c, out, t, vol) {
    var o = c.createOscillator(), g = c.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(1100, t);
    o.frequency.exponentialRampToValueAtTime(700, t + 0.05);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
    o.connect(g);
    g.connect(out);
    o.start(t);
    o.stop(t + 0.08);
  }

  function score(c, out, perc) {
    var rand = seeded(20261024), last = 4;
    var noise = c.createBuffer(1, Math.round(0.1 * c.sampleRate), c.sampleRate);
    var data = noise.getChannelData(0);
    for (var n = 0; n < data.length; n++) data[n] = rand() * 2 - 1;
    var EIGHTH = BEAT / 2;
    CHORDS.forEach(function (chord, bar) {
      var t0 = bar * 4 * BEAT;
      // Bouncy bass: short plucks an octave down.
      BASS.forEach(function (b) {
        note(c, out, t0 + b[0] * EIGHTH, hz(chord[0] % 12 - 12 + b[1]), EIGHTH * 0.9, b[0] ? 0.10 : 0.14, 'triangle');
      });
      // Pad: the chord, soft, the whole bar.
      chord.forEach(function (s) { note(c, out, t0, hz(s), BEAT * 4.1, 0.018, 'sine'); });
      // Percussion: shaker on the off-beats, wood block on beats 2 and 4.
      for (var k = 0; k < 8; k++) {
        if (k % 2) shaker(c, perc, noise, t0 + k * EIGHTH, 0.05);
        if (k === 2 || k === 6) block(c, out, t0 + k * EIGHTH, 0.07);
      }
      // Melody: chord tones on strong slots, nearby pentatonic steps between,
      // around C5–E6; the last bar of each phrase leaps up for a lift.
      RHYTHM[bar % 4].forEach(function (on, k) {
        if (!on) return;
        var pick;
        if (k % 4 === 0) {
          pick = chord[Math.floor(rand() * 3)] % 12 + 12;
        } else {
          var i = PENTA.indexOf(last), step = rand() < 0.5 ? -1 : 1;
          pick = PENTA[Math.max(0, Math.min(PENTA.length - 1, (i < 0 ? 3 : i) + step))] + 12;
        }
        last = pick - 12;
        var t = t0 + k * EIGHTH, f = hz(pick + 12);
        note(c, out, t, f, 0.45, 0.07, 'triangle');
        note(c, out, t, f * 2, 0.2, 0.015, 'sine');   // a little sparkle on top
      });
    });
  }

  // One seamless loop: render a ring-out tail and fold it onto the start.
  function render(rate) {
    rate = rate || 22050;
    var OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!OAC) return Promise.reject(new Error('no OfflineAudioContext'));
    var c = new OAC(1, Math.ceil((LOOP + TAIL) * rate), rate);
    var soft = c.createBiquadFilter();
    soft.type = 'lowpass';
    soft.frequency.value = 3600;   // bright, still gentle on the ear
    soft.connect(c.destination);
    // The shaker lives above the voice range only: a thin high band, very quiet.
    var air = c.createBiquadFilter();
    air.type = 'highpass';
    air.frequency.value = 6000;
    air.connect(c.destination);
    score(c, soft, air);
    var done = function (full) {
      var n = Math.round(LOOP * rate), tail = full.length - n;
      var loop = c.createBuffer ? c.createBuffer(1, n, rate) : null;
      if (!loop) loop = new AudioBuffer({ length: n, numberOfChannels: 1, sampleRate: rate });
      var src = full.getChannelData(0), dst = loop.getChannelData(0);
      dst.set(src.subarray(0, n));
      for (var i = 0; i < tail; i++) dst[i] += src[n + i];
      return loop;
    };
    // Old Safari: startRendering() has no promise, only oncomplete.
    return new Promise(function (resolve, reject) {
      c.oncomplete = function (e) { resolve(done(e.renderedBuffer)); };
      var p = c.startRendering();
      if (p && p.then) p.then(function (b) { resolve(done(b)); }, reject);
    });
  }

  var ctx = null, gain = null, source = null, loading = null;
  var on = true, ducked = false, hidden = false;
  var armed = false;          // a tap has happened: iOS lets audio start now

  function target() { return on && !hidden ? (ducked ? LEVEL * DUCK : LEVEL) : 0; }

  // Glide to the right level: fast down (a voice is starting), slow up.
  function apply(down, up) {
    if (!gain) return;
    var t = ctx.currentTime, want = target();
    var from = gain.gain.value;
    gain.gain.cancelScheduledValues(t);
    gain.gain.setValueAtTime(from, t);
    gain.gain.linearRampToValueAtTime(want, t + (want < from ? down : up));
  }

  // Call inside a tap (every tap is fine): starts the loop the first time,
  // and wakes the sound up again after the iPad paused it.
  function start() {
    armed = true;
    hidden = false;
    if (!on || !window.Fx || !Fx.context) return;
    ctx = Fx.context();
    if (!ctx) return;
    if (!gain) {
      gain = ctx.createGain();
      gain.gain.value = 0;
      gain.connect(ctx.destination);
    }
    if (!source && !loading) {
      // 22.05 kHz is plenty for soft music and keeps the buffer small.
      loading = render(22050).then(function (buffer) {
        source = ctx.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        source.connect(gain);
        source.start();
        apply(0.15, 0.5);
      }).catch(function () { loading = null; /* no music; everything else still works */ });
      return;
    }
    apply(0.15, 0.5);
  }

  function setOn(value) {
    on = !!value;
    if (on && armed) start();
    else apply(0.5, 0.5);
  }

  var release = null;
  function duck(value) {
    clearTimeout(release);
    if (value) { ducked = true; apply(0.15, 0.15); return; }
    // Wait a moment: the next line of a queue usually follows right away.
    release = setTimeout(function () { ducked = false; apply(0.15, 0.8); }, 600);
  }

  // The page went to the background: fade out; the next tap brings it back.
  function pause() { hidden = true; apply(0.2, 0.2); }

  window.Music = {
    render: render,
    start: start,
    setOn: setOn,
    duck: duck,
    pause: pause,
    get on() { return on; },
    get playing() { return !!source; },
    gain: function () { return gain ? gain.gain.value : 0; },
    level: target,
    LEVEL: LEVEL,
    DUCK: DUCK,
    LOOP: LOOP
  };
})();
