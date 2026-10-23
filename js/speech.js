// Voice for every mode (word cards, games, later phrases).
//
//   Speech.play(item, opts)  item = {english, audio?}: plays the recorded
//                            `audio` file when present, else reads `english`
//                            with speechSynthesis in en-US.
//   Speech.zh(key, opts)     a Chinese instruction: plays audio/zh/<key>.mp3
//                            (recorded by tools/gen-voice.py); if the file
//                            fails, shows a visible error; Chinese never uses TTS.
//   Speech.setLines(map)     key -> Chinese text (data/voice-zh.json + theme
//                            names), used for that fallback.
//   Speech.say(text, opts)   reads any text with TTS (opts.lang, default en-US).
//   opts.queue = true        play after what is playing now instead of cutting it off
//   opts.onend = fn          called once when this item ends, fails or is cut off
//
// Everything goes through one queue, so a Chinese instruction followed by an
// English word always plays in that order, whatever each one is made of.
// iOS Safari only allows sound that starts inside a user gesture, so call
// Speech.unlock() from the first tap and play()/zh() directly from click handlers.
(function () {
  'use strict';

  var ZH_DIR = 'audio/zh/';
  var RATE = { 'en-US': 0.85, 'zh-TW': 0.95 };
  // Clear, natural voices seen on iOS/macOS, Android/Chrome and Windows.
  var PREFERRED = {
    'en-US': ['Samantha', 'Google US English', 'Microsoft Aria', 'Microsoft Jenny', 'Ava', 'Allison', 'Alex'],
    'zh-TW': ['Mei-Jia', '美佳', 'Google 國語', 'Microsoft HsiaoChen', 'Microsoft Hanhan', 'Microsoft Yating']
  };

  var synth = window.speechSynthesis || null;
  var ttsSupported = !!(synth && window.SpeechSynthesisUtterance);
  var voices = {};          // lang -> chosen SpeechSynthesisVoice
  var lines = {};           // zh key -> text
  var listeners = [];
  var player = null;        // one shared <audio>, unlocked by the first tap
  var queue = [];
  var current = null;
  var seq = 0;              // bumped by stop(); stale callbacks compare against it
  var SILENCE = 'data:audio/wav;base64,UklGRnQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YVAAAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==';

  function emit(type) {
    listeners.forEach(function (fn) { try { fn(type); } catch (e) { /* keep others running */ } });
  }

  function norm(lang) { return String(lang || '').replace('_', '-').toLowerCase(); }

  function pickFrom(all, lang) {
    var want = norm(lang), base = want.split('-')[0];
    var exact = all.filter(function (v) { return norm(v.lang) === want; });
    var near = all.filter(function (v) { return norm(v.lang).split('-')[0] === base; });
    var named = null;
    (PREFERRED[lang] || []).some(function (name) {
      named = exact.filter(function (v) { return v.name.indexOf(name) !== -1; })[0] || null;
      return named;
    });
    return named || exact.filter(function (v) { return v.localService; })[0] || exact[0] || near[0] || null;
  }

  function pickVoices() {
    if (!ttsSupported) return false;
    var all = [];
    try { all = synth.getVoices() || []; } catch (e) { /* not ready */ }
    if (!all.length) return false;
    Object.keys(RATE).forEach(function (lang) { voices[lang] = pickFrom(all, lang); });
    return true;
  }

  // Voices load asynchronously: listen for voiceschanged and also poll,
  // because some browsers (older Safari) never fire the event.
  function init() {
    if (!ttsSupported) return;
    pickVoices();
    if (synth.addEventListener) synth.addEventListener('voiceschanged', pickVoices);
    else synth.onvoiceschanged = pickVoices;
    var tries = 0;
    var timer = setInterval(function () {
      if (pickVoices() || ++tries >= 40) clearInterval(timer);
    }, 250);
  }

  // Call inside the first tap: playing silence once lets the shared <audio>
  // play later from timers (games move on without a new tap), and a silent
  // utterance does the same for speechSynthesis.
  function unlock() {
    try {
      if (!player) player = new Audio();
      player.src = SILENCE;
      var p = player.play();
      if (p && p.catch) p.catch(function () { /* fine: a real line may replace it */ });
    } catch (e) { /* ignore */ }
    if (!ttsSupported) return;
    try {
      var u = new SpeechSynthesisUtterance(' ');
      u.volume = 0;
      u.lang = 'en-US';
      synth.speak(u);
    } catch (e) { /* ignore */ }
  }

  function once(fn) {
    var done = false;
    return function () { if (!done && fn) { done = true; fn(); } };
  }

  // Cut off what is playing and drop the queue; their onend still runs.
  function stop() {
    seq++;
    var dropped = (current ? [current] : []).concat(queue);
    queue = [];
    current = null;
    if (player) { try { player.pause(); } catch (e) { /* ignore */ } }
    if (ttsSupported) { try { synth.cancel(); } catch (e) { /* ignore */ } }
    dropped.forEach(function (item) { item.onend(); });
  }

  function enqueue(item, opts) {
    opts = opts || {};
    item.onend = once(function () { if (item.cleanup) item.cleanup(); if (opts.onend) opts.onend(); });
    if (!opts.queue) stop();
    queue.push(item);
    if (!current) next();
  }

  function next() {
    if (current || !queue.length) return;
    var item = current = queue.shift();
    var id = seq;
    var done = function () {
      if (id !== seq || current !== item) return;
      current = null;
      item.onend();
      next();
    };
    if (item.src) playFile(item, done, id);
    else speakNow(item, done);
  }

  function speakNow(item, done) {
    if (!ttsSupported) { emit('unsupported'); done(); return; }
    var lang = item.lang || 'en-US';
    if (!voices[lang]) pickVoices();
    try {
      var u = new SpeechSynthesisUtterance(item.text);
      u.lang = lang;
      if (voices[lang]) u.voice = voices[lang];
      u.rate = item.rate || RATE[lang] || 0.9;
      var cues = [];
      item.cleanup = function () { cues.forEach(clearTimeout); cues = []; };
      if (item.boundary) u.onboundary = function (e) {
        // Real word boundaries take precedence over the approximate fallback.
        if (e.charIndex > 0) item.cleanup();
        item.boundary(e.charIndex);
      };
      u.pitch = 1.05;
      u.volume = 1;
      u.onstart = function () {
        emit('start');
        if (item.begin) item.begin();
        // Some mobile voices never emit word boundaries. Keep a gentle visual
        // cue moving; these timings are approximate, never used for scoring.
        if (item.boundary) {
          var re = /\S+/g, match;
          while ((match = re.exec(item.text))) {
            (function (index) {
              cues.push(setTimeout(function () { item.boundary(index); }, index * 62 / u.rate));
            })(match.index);
          }
        }
      };
      u.onend = function () { emit('end'); done(); };
      u.onerror = function (e) {
        // cancel() of a previous item reports interrupted/canceled: not a failure.
        emit(e && (e.error === 'interrupted' || e.error === 'canceled') ? 'end' : 'error');
        done();
      };
      synth.speak(u);
      if (synth.paused) synth.resume();
    } catch (e) {
      emit('error');
      done();
    }
  }

  function playFile(item, done, id) {
    if (!player) player = new Audio();
    var fellBack = false;
    // File missing or refused: read the same text with TTS instead.
    var fallback = function () {
      if (fellBack || id !== seq) return;
      fellBack = true;
      if (item.lang === 'zh-TW') { emit('error'); done(); }
      else if (item.text) speakNow(item, done);
      else done();
    };
    player.onerror = fallback;
    player.onplay = function () { if (id === seq && item.begin) item.begin(); };
    // Recordings lack word boundaries: use their playback position as a cue.
    player.ontimeupdate = function () {
      if (id === seq && item.boundary && isFinite(player.duration) && player.duration > 0) {
        item.boundary(Math.floor(item.text.length * player.currentTime / player.duration));
      }
    };
    player.onended = function () { if (id === seq) { emit('end'); done(); } };
    player.src = item.src;
    try {
      var p = player.play();
      if (p && p.catch) p.catch(fallback);
    } catch (e) {
      fallback();
      return;
    }
    emit('start');
  }

  // Returns 'audio', 'tts' or false (nothing could play).
  function play(item, opts) {
    var hasFile = !!item.audio;
    opts = opts || {};
    enqueue({ src: item.audio || null, text: item.english, lang: 'en-US', rate: item.category ? 0.72 : 0, boundary: opts.onboundary, begin: opts.onstart }, opts);
    return hasFile ? 'audio' : (ttsSupported ? 'tts' : false);
  }

  function zh(key, opts) {
    enqueue({ src: ZH_DIR + key + '.mp3', text: lines[key], lang: 'zh-TW' }, opts);
    return true;
  }

  function say(text, opts) {
    opts = opts || {};
    if (/^zh/i.test(opts.lang || '')) { emit('error'); if(opts.onend)opts.onend(); return false; }
    enqueue({ text: text, lang: opts.lang || 'en-US' }, opts);
    return ttsSupported;
  }

  window.Speech = {
    init: init,
    unlock: unlock,
    play: play,
    zh: zh,
    say: say,
    stop: stop,
    setLines: function (map) { lines = map || {}; },
    on: function (fn) { listeners.push(fn); },
    get supported() { return ttsSupported; },
    voice: function (lang) { return voices[lang || 'en-US'] || null; }
  };
})();
