// Screens: home -> themes -> cards, and themes -> games -> play -> result
// (games live in js/games/); home -> phrases -> cards (phrase deck), and
// phrases -> phraseGames -> play (js/phrase-ui.js). All data comes from data/*.json.
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
  // base: the built-in lists from data/.
  // deck: 'words' or 'phrases', what #cards is showing.
  var state = { base: null, words: [], themes: [], phrases: [], list: [], i: 0, deck: 'words', settings: Data.settings.load(), told: {} };

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
    if (id === 'phrases') { buildPhrases(); Speech.zh('phrases.home'); }
    if (id === 'phraseGames') { Phrases.menu(); Speech.zh('games.pick'); }
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
  function reviewCard(dueWords, open) {
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
    b.addEventListener('click', open);
    return b;
  }

  function buildThemes() {
    var grid = $('#themeGrid');
    grid.textContent = '';
    grid.appendChild(reviewCard(Progress.due(state.words), function () { Games.review(); }));
    state.themes.forEach(function (th) {
      var list = Data.wordsInTheme(state.words, th.id);
      if (!list.length) return;
      grid.appendChild(themeCard(th, list.length, Progress.themeStars(state.words, th.id), function () { openTheme(th.id); }));
    });
  }

  // A deck card: picture, Chinese and English name, 0–3 stars (Progress.themeStars).
  function themeCard(th, n, got, open) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'theme-card';
    b.style.setProperty('--theme', th.color);
    b.dataset.theme = th.id;
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
    var stars = document.createElement('span');
    stars.className = 'theme-stars';
    stars.dataset.stars = String(got);
    b.setAttribute('aria-label', th.chinese + ' ' + th.english + ' · ' + n + ' cards · ' + got + '/3');
    for (var k = 0; k < 3; k++) stars.appendChild(icon('#i-star', 'theme-star' + (k < got ? ' on' : '')));
    b.append(img, zh, en, stars);
    b.addEventListener('click', open);
    return b;
  }

  // Phrases, like the word area: today's review, then one deck of every phrase.
  // Its stars use the theme rule over all phrases, kept as best.phrases.
  var PHRASE_DECK = { id: 'phrases', chinese: '句子卡', english: 'Phrase cards', color: '#c4e8ff', icon: 'images/phrases/hello.svg' };
  function buildPhrases() {
    var grid = $('#phraseGrid');
    grid.textContent = '';
    var list = state.phrases;
    if (!list.length) return;
    grid.appendChild(reviewCard(Progress.due(list), function () { Phrases.review(); }));
    var asTheme = list.map(function (p) { return { id: p.id, theme: 'phrases' }; });
    grid.appendChild(themeCard(PHRASE_DECK, list.length, Progress.themeStars(asTheme, 'phrases'), function () { openDeck(list, 'phrases'); }));
  }

  function openTheme(id) {
    openDeck(Data.wordsInTheme(state.words, id), 'words');
  }

  // Word or phrase cards on the same screen; the back button returns to their area.
  function setDeck(kind) {
    state.deck = kind;
    var phrases = kind === 'phrases';
    $('#cards').classList.toggle('phrase-deck', phrases);
    var back = $('#cards .bar [data-go]');
    back.dataset.go = phrases ? 'phrases' : 'themes';
    back.setAttribute('aria-label', phrases ? '回生活句子 Phrases' : '回主題 Themes');
  }

  function openDeck(list, kind) {
    state.list = list;
    state.i = 0;
    setDeck(kind);
    state.list.forEach(function (w) { new Image().src = w.image; });
    show('cards');
    renderCard(0);
    // First time: explain in Chinese, then say the word (queued after it).
    if (!state.told[kind]) {
      state.told[kind] = true;
      Speech.zh(kind === 'phrases' ? 'phrases.cards' : 'cards.howto');
      speakCurrent(true);
    } else {
      speakCurrent();
    }
  }

  // Today's review in card mode: look through the review words, then stars.
  function reviewCards(list, intro) {
    state.list = list;
    state.i = 0;
    setDeck('words');
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
    var en = $('#wordEn');
    en.textContent = '';
    // Phrases: one span per word, lit while it is spoken.
    if (state.deck === 'phrases') {
      w.english.split(' ').forEach(function (part) {
        var span = document.createElement('span');
        span.textContent = part;
        en.appendChild(span);
      });
    } else {
      en.textContent = w.english;
    }
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
      // Finished the deck (word, phrase or review cards): a cheer and praise,
      // then start again. No stars: Tim (phase 9) keeps them for games.
      next = 0;
      state.i = next;
      renderCard(delta);
      Fx.sound('star');
      Fx.move($('#picImg'), 'cheer');
      Speech.zh('cards.done');
      speakCurrent(true);
      return;
    }
    state.i = next;
    renderCard(delta);
    speakCurrent();
  }

  function speakCurrent(queue) {
    var w = state.list[state.i];
    if (!w) return;
    if (state.deck !== 'phrases') { Speech.play(w, { queue: queue === true }); return; }
    var spans = $('#wordEn').children;
    var light = function (i) { Array.prototype.forEach.call(spans, function (s, k) { s.classList.toggle('lit', k === i); }); };
    Speech.play(w, {
      queue: queue === true,
      onstart: function () { light(0); },
      onboundary: function (charIndex) {
        // Word i starts after i spaces: count the spaces before charIndex.
        light(w.english.slice(0, charIndex + 1).split(' ').length - 1);
      },
      onend: function () { light(-1); }
    });
    // Chinese switched on: the recorded meaning follows the sentence.
    if (document.body.classList.contains('show-zh')) Speech.zh('zh.' + w.id, { queue: true });
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
    var music = $('#musicBtn');
    music.setAttribute('aria-pressed', String(s.music));
    music.querySelector('use').setAttribute('href', s.music ? '#i-music' : '#i-music-off');
    Music.setOn(s.music);
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
    // Background music steps back while anything is spoken.
    if (type === 'busy') Music.duck(true);
    if (type === 'idle') Music.duck(false);
  });

  // ---------- background music (js/music.js)
  // Any tap may start it (iOS needs one) or wake it after the iPad paused it.
  document.addEventListener('click', function () { Music.start(); }, true);
  var sleepTimer = null;
  document.addEventListener('visibilitychange', function () {
    clearTimeout(sleepTimer);
    if (document.visibilityState !== 'hidden') return;
    Music.pause();
    // After the fade, let the sound sleep; the next tap wakes it.
    sleepTimer = setTimeout(function () {
      var c = Fx.context && Music.playing ? Fx.context() : null;
      if (c && document.visibilityState === 'hidden' && c.suspend) c.suspend();
    }, 300);
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
    $('#phraseGamesBtn').addEventListener('click', function () { firstTap('phraseGames'); });
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
    $('#musicBtn').addEventListener('click', function () {
      state.settings.music = !state.settings.music;
      applySettings();
    });
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

  // The built-in lists from data/ (phrases arrive a moment later).
  function applyData() {
    state.words = state.base.words;
    state.themes = state.base.themes;
    buildThemes();
    Games.build(state.words, state.themes);
    state.phrases = state.base.phrases || [];
    if (state.base.phrases) Phrases.build(state.base.phrases);
    Jar.renderAll();
  }

  function start() {
    Speech.init();
    applySettings();
    bind();
    Data.loadWords().then(function (d) {
      state.base = { words: d.words, themes: d.themes, phrases: null };
      // Which lines have an mp3: one not recorded yet is skipped, never read by TTS.
      Data.getJSON('audio/zh/manifest.json').then(function (m) { Speech.setRecorded(Object.keys(m)); }).catch(function () { /* play and report as before */ });
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
