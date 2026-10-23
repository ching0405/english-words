// Screens: home -> themes -> cards, and home -> games -> play -> result
// (games live in js/games/). All word data comes from data/*.json.
// Children may not read yet: every step is spoken (Chinese instructions,
// English words) and text on cards is only an optional helper for parents.
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  // Spoken Chinese lines are keys of data/voice-zh.json (recorded mp3s, see
  // tools/gen-voice.py). The toasts below are text for parents, not spoken.
  var TEXT = {
    noVoice: '這台裝置不能朗讀英文，請改用 Safari 或 Chrome。',
    failed: '聲音沒有播出來，再點一次試試看。'
  };
  // base: the built-in lists from data/; words/themes: those plus this device's own (js/custom.js).
  var state = { base: null, words: [], themes: [], list: [], i: 0, settings: Data.settings.load(), toldCards: false };

  // Keyboard and VoiceOver users: focus that was on a button of the old
  // screen would stay on a hidden element, so it moves to the new screen.
  // Only then: a tap that left no focus behind never draws a focus ring.
  var FOCUSABLE = 'button:not([disabled]), [href], input:not([type=hidden]), select, textarea, [tabindex]:not([tabindex="-1"])';
  function keepFocus(screen) {
    var was = document.activeElement;
    if (!was || was === document.body || !was.closest('[hidden]')) return;
    var to = screen && Array.prototype.find.call(screen.querySelectorAll(FOCUSABLE), function (el) { return !el.closest('[hidden]'); });
    if (to) to.focus({ preventScroll: true });
  }

  function show(id) {
    document.querySelectorAll('.screen').forEach(function (s) { s.hidden = s.id !== id; });
    if (id !== 'play') Games.stop();
    if (id !== 'cards') Speech.stop();
    if (id === 'themes') {
      buildThemes(); // progress may have changed
      Speech.zh('themes.pick');
    }
    if (id === 'games') Games.menu();
    if (id === 'phrases') { Phrases.menu(); Speech.zh('phrases.pick'); }
    if (id === 'parent') Parent.render();
    Jar.renderAll();
    if (id === 'home' && window.Pwa) Pwa.atHome(); // a new version waits for the home screen
    keepFocus(document.getElementById(id));
  }
  window.App = { show: show, reviewCards: reviewCards, toast: toast };

  var toastTimer;
  function toast(msg) {
    var t = $('#toast');
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, 3500);
  }

  // ---------- themes
  function icon(href, cls) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', cls);
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', href);
    svg.appendChild(use);
    return svg;
  }

  // Today's review card: small pictures of the words waiting (up to 5, then
  // a "+"), or a check mark when nothing is waiting. No numbers or text.
  var REVIEW_PICS = 5;
  function reviewCard() {
    var dueWords = Progress.due(state.words);
    var due = dueWords.length;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'theme-card review-card';
    b.dataset.theme = 'review';
    b.dataset.due = String(due);
    b.setAttribute('aria-label', '今日複習 Review: ' + due);
    b.appendChild(icon('#g-review', 'review-pic'));
    var zh = document.createElement('span');
    zh.className = 'theme-zh';
    zh.textContent = '今日複習';
    var en = document.createElement('span');
    en.className = 'theme-en aux-en';
    en.lang = 'en';
    en.textContent = 'Review';
    var dots = document.createElement('span');
    dots.className = 'due-pics';
    if (due) {
      dueWords.slice(0, REVIEW_PICS).forEach(function (w) {
        var pic = document.createElement('img');
        pic.src = w.image;
        pic.alt = '';
        pic.dataset.word = w.id;
        dots.appendChild(pic);
      });
      if (due > REVIEW_PICS) dots.appendChild(icon('#i-plus', 'due-more'));
    } else {
      dots.appendChild(icon('#i-check', 'due-done'));
    }
    var label = document.createElement('span');
    label.className = 'review-text';
    label.append(zh, en, dots);
    b.append(label);
    b.addEventListener('click', function () { Games.review(); });
    return b;
  }

  function buildThemes() {
    var grid = $('#themeGrid');
    grid.textContent = '';
    grid.appendChild(reviewCard());
    state.themes.forEach(function (th) {
      var n = Data.wordsInTheme(state.words, th.id).length;
      if (!n) return;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'theme-card';
      b.style.setProperty('--theme', th.color);
      b.dataset.theme = th.id;
      b.setAttribute('aria-label', th.chinese + ' ' + th.english);
      var img = document.createElement('img');
      img.src = th.icon;
      img.alt = '';
      var zh = document.createElement('span');
      zh.className = 'theme-zh';
      zh.textContent = th.chinese;
      var en = document.createElement('span');
      en.className = 'theme-en aux-en';
      en.lang = 'en';
      en.textContent = th.english;
      // Progress: 0–3 filled stars (see Progress.themeStars).
      var stars = document.createElement('span');
      var got = Progress.themeStars(state.words, th.id);
      stars.className = 'theme-stars';
      stars.dataset.stars = String(got);
      b.setAttribute('aria-label', th.chinese + ' ' + th.english + ' · ' + n + ' cards · ' + got + '/3');
      for (var k = 0; k < 3; k++) stars.appendChild(icon('#i-star', 'theme-star' + (k < got ? ' on' : '')));
      b.append(img, zh, en, stars);
      b.addEventListener('click', function () { openTheme(th.id); });
      grid.appendChild(b);
    });
  }

  function openTheme(id) {
    state.reviewing = false;
    state.list = Data.wordsInTheme(state.words, id);
    state.i = 0;
    state.list.forEach(function (w) { new Image().src = w.image; });
    show('cards');
    renderCard(0);
    // First time: explain in Chinese, then say the word (queued after it).
    if (!state.toldCards) {
      state.toldCards = true;
      Speech.zh('cards.howto');
      speakCurrent(true);
    } else {
      speakCurrent();
    }
  }

  // Today's review in card mode: look through the review words, then stars.
  function reviewCards(list, intro) {
    state.list = list;
    state.i = 0;
    state.reviewing = true;
    show('cards');
    renderCard(0);
    Speech.zh(intro);
    Speech.zh('cards.howto', { queue: true });
    speakCurrent(true);
  }

  // ---------- cards
  function renderCard(dir) {
    var w = state.list[state.i];
    var last = state.i === state.list.length - 1;
    Progress.seen(w.id);
    var img = $('#picImg');
    img.src = w.image;
    img.alt = w.english;
    $('#wordEn').textContent = w.english;
    $('#wordZh').textContent = w.chinese;
    $('#progress').textContent = (state.i + 1) + ' / ' + state.list.length;
    $('#prevBtn').disabled = state.i === 0;
    $('#nextIcon').setAttribute('href', last ? '#i-again' : '#i-next');
    $('#nextBtn').setAttribute('aria-label', last ? '再看一次 Again' : '下一張 Next');
    var pic = $('#pic');
    pic.classList.remove('in-left', 'in-right');
    if (dir) {
      void pic.offsetWidth; // restart the slide-in animation
      pic.classList.add(dir > 0 ? 'in-right' : 'in-left');
    }
  }

  function move(delta) {
    var n = state.list.length;
    var next = state.i + delta;
    if (next < 0) return;
    if (next >= n) {
      if (state.reviewing) {
        // Looked through today's review words: stars and the jar.
        state.reviewing = false;
        Games.cardsDone(state.list.slice());
        return;
      }
      // Finished the deck: fanfare, praise, a star for the jar, then start again.
      next = 0;
      state.i = next;
      renderCard(delta);
      Fx.sound('star');
      Fx.move($('#picImg'), 'cheer');
      Speech.zh('cards.done');
      Jar.pop(1, $('#picImg'));
      speakCurrent(true);
      return;
    }
    state.i = next;
    renderCard(delta);
    speakCurrent();
  }

  function speakCurrent(queue) {
    var w = state.list[state.i];
    if (w) Speech.play(w, { queue: queue === true });
  }

  // Tapping the picture: the word's own little action and sound, then the word.
  function tapPicture() {
    var w = state.list[state.i];
    if (!w) return;
    Fx.tap($('#picImg'), w);
    speakCurrent();
  }

  // Text helpers for parents: English (default on) and Chinese (default off).
  function applySettings() {
    var s = state.settings;
    document.body.classList.toggle('hide-en', !s.showEnglish);
    document.body.classList.toggle('show-zh', s.showChinese);
    $('#enBtn').setAttribute('aria-pressed', String(s.showEnglish));
    $('#zhBtn').setAttribute('aria-pressed', String(s.showChinese));
    Data.settings.save(s);
  }

  // Horizontal swipe on the picture area changes card; vertical is ignored.
  // A mouse swipe still fires click on the picture, so skip that one click.
  var swipedAt = 0;
  function bindSwipe(el) {
    var x0 = null, y0 = 0;
    el.addEventListener('pointerdown', function (e) { x0 = e.clientX; y0 = e.clientY; });
    el.addEventListener('pointercancel', function () { x0 = null; });
    el.addEventListener('pointerup', function (e) {
      if (x0 === null) return;
      var dx = e.clientX - x0, dy = e.clientY - y0;
      x0 = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.2) {
        swipedAt = Date.now();
        move(dx < 0 ? 1 : -1);
      }
    });
  }

  // ---------- speech feedback
  Speech.on(function (type) {
    document.querySelectorAll('#sayBtn, #replayBtn').forEach(function (say) {
      if (type === 'start') say.classList.add('talking');
      if (type === 'end' || type === 'error' || type === 'unsupported') say.classList.remove('talking');
    });
    if (type === 'unsupported') toast(TEXT.noVoice);
    if (type === 'error') toast(TEXT.failed);
  });

  // ---------- wiring
  function bind() {
    // Either home button is the first tap: unlock speech and sound inside it (iOS).
    function firstTap(screen) {
      Speech.unlock();
      Fx.unlock();
      show(screen);
      if (!Speech.supported) toast(TEXT.noVoice);
    }
    $('#startBtn').addEventListener('click', function () { firstTap('themes'); });
    $('#phrasesBtn').addEventListener('click', function () { firstTap('phrases'); });
    $('#gamesBtn').addEventListener('click', function () { firstTap('games'); });
    Games.bind();
    // A soft pop on menu and navigation buttons. Capture phase, so a button's
    // own sound (if any) starts after it and replaces it.
    document.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-go], .btn-nav, .theme-card, .game-card, .chip, .btn-wide');
      if (b && !b.disabled) Fx.sound('pop');
    }, true);
    document.querySelectorAll('.jar-btn').forEach(function (b) {
      b.addEventListener('click', function () {
        Fx.move(b.querySelector('.jar-main'), 'wiggle');
        Speech.zh('jar.look');
      });
    });
    document.querySelectorAll('[data-go]').forEach(function (b) {
      b.addEventListener('click', function () { show(b.dataset.go); });
    });
    $('#pic').addEventListener('click', function () {
      if (Date.now() - swipedAt < 400) return;
      tapPicture();
    });
    $('#sayBtn').addEventListener('click', function () { speakCurrent(); });
    $('#prevBtn').addEventListener('click', function () { move(-1); });
    $('#nextBtn').addEventListener('click', function () { move(1); });
    $('#enBtn').addEventListener('click', function () {
      state.settings.showEnglish = !state.settings.showEnglish;
      applySettings();
    });
    $('#zhBtn').addEventListener('click', function () {
      state.settings.showChinese = !state.settings.showChinese;
      applySettings();
    });
    bindSwipe($('#stage'));
    document.addEventListener('keydown', function (e) {
      if ($('#cards').hidden) return;
      if (e.key === 'ArrowRight') move(1);
      else if (e.key === 'ArrowLeft') move(-1);
    });
  }

  // Built-in lists plus the parent's own words, phrases and themes.
  function applyData() {
    var mine = Custom.view();
    state.words = state.base.words.concat(mine.words);
    state.themes = state.base.themes.concat(mine.themes);
    buildThemes();
    Games.build(state.words, state.themes);
    if (state.base.phrases) Phrases.build(state.base.phrases.concat(mine.phrases));
    Jar.renderAll();
  }

  // What the parent page checks against: built-in items and their pictures.
  function builtIn() {
    var b = state.base, phrases = b.phrases || [];
    var gallery = [];
    b.words.concat(phrases).forEach(function (w) { if (gallery.indexOf(w.image) < 0) gallery.push(w.image); });
    return { words: b.words, phrases: phrases, themes: b.themes, gallery: gallery };
  }

  function start() {
    Speech.init();
    applySettings();
    bind();
    Parent.bind({ builtIn: builtIn, changed: applyData, toast: toast });
    // Words added or deleted in another tab show up here too.
    Custom.onChange(function () {
      if (!state.base) return;
      applyData();
      if (!$('#parent').hidden) Parent.render();
    });
    Promise.all([Data.loadWords(), Custom.load()]).then(function (res) {
      var d = res[0];
      state.base = { words: d.words, themes: d.themes, phrases: null };
      return Data.loadVoiceLines(d.themes).then(function (lines) { Speech.setLines(lines); return d; });
    }).then(function () {
      applyData();
      $('#startBtn').disabled = false;
      $('#gamesBtn').disabled = false;
      Data.getJSON('data/phrases.json').then(function (list) {
        state.base.phrases = list;
        applyData();
        $('#phrasesBtn').disabled = false;
      }).catch(function () { toast('讀不到生活句子資料，請重新整理。'); });
      $('#loadMsg').textContent = '';
    }).catch(function (err) {
      $('#loadMsg').textContent = '讀不到單字資料。請用網址開啟（本機請執行 python3 -m http.server）。';
      if (window.console) console.warn(err);
    });
  }

  start();
})();
