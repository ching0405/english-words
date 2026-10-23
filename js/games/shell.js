// Game menu, game screen and results, shared by every game module.
// A game registers itself with Games.register({...start(api)}) and only
// deals with its own board; the shell handles voice, feedback, stars and
// navigation. Questions come from Quiz (js/quiz.js) and data/words.json.
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  // Chinese lines are keys of data/voice-zh.json (recorded mp3s).
  var PRAISE = ['praise.1', 'praise.2', 'praise.3', 'praise.4'];
  var defs = [];
  var state = { words: [], themes: [], themeId: null, game: null, run: 0, timers: [], stops: [], mistakes: 0, replay: null };

  function el(tag, cls, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  function icon(href, cls) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', cls || 'ic');
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', href);
    svg.appendChild(use);
    return svg;
  }

  // A square picture button for a word (used by several games).
  function picture(word, cls) {
    var b = el('button', 'pick ' + (cls || ''), { type: 'button', 'aria-label': word.english });
    b.dataset.word = word.id;
    var img = el('img', '', { src: word.image, alt: '', draggable: 'false' });
    b.appendChild(img);
    return b;
  }

  function register(def) { defs.push(def); }

  // ---------- menu
  function build(words, themes) {
    state.words = words;
    state.themes = themes.filter(function (t) { return Data.wordsInTheme(words, t.id).length; });
    // The chosen theme may no longer exist.
    if (state.themeId && !state.themes.some(function (t) { return t.id === state.themeId; })) state.themeId = null;
    var chips = $('#themeChips');
    chips.textContent = '';
    [{ id: null, chinese: '全部', english: 'All' }].concat(state.themes).forEach(function (t) {
      var b = el('button', 'chip', { type: 'button', role: 'radio', 'aria-label': t.chinese + ' ' + t.english });
      b.dataset.theme = t.id || '';
      if (t.icon) b.appendChild(el('img', '', { src: t.icon, alt: '' }));
      else b.appendChild(icon('#i-star', 'chip-star'));
      var label = el('span', 'chip-label');
      label.textContent = t.chinese;
      b.appendChild(label);
      if (t.color) b.style.setProperty('--theme', t.color);
      b.addEventListener('click', function () {
        state.themeId = t.id;
        markChips();
        Speech.zh(t.id ? 'theme.' + t.id : 'games.all');
      });
      chips.appendChild(b);
    });
    markChips();
    var grid = $('#gameGrid');
    grid.textContent = '';
    defs.forEach(function (def) {
      var b = el('button', 'game-card', { type: 'button', 'aria-label': def.zh + ' ' + def.en });
      b.dataset.game = def.id;
      b.style.setProperty('--theme', def.color);
      b.appendChild(icon(def.icon, 'game-pic'));
      var zh = el('span', 'game-zh');
      zh.textContent = def.zh;
      var en = el('span', 'game-en aux-en', { lang: 'en' });
      en.textContent = def.en;
      b.append(zh, en);
      b.addEventListener('click', function () { open(def); });
      grid.appendChild(b);
    });
  }

  function markChips() {
    document.querySelectorAll('#themeChips .chip').forEach(function (c) {
      c.setAttribute('aria-checked', String((c.dataset.theme || null) === state.themeId));
    });
  }

  function menu() { Speech.zh('games.pick'); }

  // ---------- running a game
  function stop() {
    state.run++;
    state.timers.forEach(clearTimeout);
    state.timers = [];
    state.stops.forEach(function (fn) { try { fn(); } catch (e) { /* ignore */ } });
    state.stops = [];
    state.replay = null;
  }

  // Where the grid/back buttons on the game and result screens lead.
  function setBack(screen) {
    document.querySelectorAll('#play .bar [data-go], #result [data-go]:not([data-go="home"])').forEach(function (b) {
      b.dataset.go = screen;
      var use = b.querySelector('use');
      if (use) use.setAttribute('href', screen === 'games' || screen === 'phraseGames' ? '#i-grid' : '#i-back');
    });
  }

  // opts (optional): {targets: words to ask about, intro: voice key,
  // back: screen to return to, mode: 'review'}.
  function open(def, opts) {
    opts = opts || {};
    stop();
    state.game = def;
    state.opts = opts;
    state.mistakes = 0;
    state.roundWords = [];
    var run = state.run;
    App.show('play');
    setBack(opts.back || 'games');
    var stage = $('#playStage');
    stage.textContent = '';
    stage.className = 'play-stage game-' + def.id;
    $('#play').dataset.game = def.id;
    $('#play').dataset.mode = opts.mode || 'game';
    // Review rounds open with their own line, then the game's how-to.
    if (opts.intro) {
      Speech.zh(opts.intro);
      Speech.zh(def.intro, { queue: true });
    } else {
      Speech.zh(def.intro);
    }
    var note = function (w) { if (w && state.roundWords.indexOf(w) < 0) state.roundWords.push(w); };

    var alive = function () { return run === state.run; };
    var later = function (ms, fn) {
      state.timers.push(setTimeout(function () { if (alive()) fn(); }, ms));
    };
    // Run fn after a Chinese line ends (or after maxMs if the end never comes).
    var afterSay = function (key, fn, maxMs) {
      var done = false;
      var go = function () { if (!done && alive()) { done = true; fn(); } };
      Speech.zh(key, { onend: go });
      later(maxMs || 5000, go);
    };

    var api = {
      stage: stage,
      words: state.words,
      themeId: state.themeId,
      targets: opts.targets || null,
      rand: Math.random,
      el: el,
      icon: icon,
      picture: function (w, cls) { note(w); return picture(w, cls); },
      later: later,
      alive: alive,
      onStop: function (fn) { state.stops.push(fn); },
      onReplay: function (fn) { state.replay = fn; },
      // English word; queue:true waits for the spoken instruction first.
      word: function (w, opts) { note(w); return Speech.play(w, opts); },
      zh: function (key, opts) { return Speech.zh(key, opts); },
      dots: function (n) {
        var d = $('#dots');
        d.textContent = '';
        for (var i = 0; i < n; i++) d.appendChild(icon('#i-star', 'dot'));
      },
      // One more progress star (a missed word asked again at the end).
      addDot: function () { $('#dots').appendChild(icon('#i-star', 'dot')); },
      dot: function (i) {
        var d = $('#dots').children[i];
        if (d) { d.classList.add('on'); Fx.move(d, 'wiggle'); }
      },
      // Question number, for tests and screen readers.
      setQ: function (i) { $('#play').dataset.q = String(i); },
      // Correct: cheer, sparkle and praise, then next().
      right: function (target, next) {
        if (target) { Fx.move(target, 'cheer'); Fx.burst(target); }
        Fx.sound('sparkle');
        afterSay(PRAISE[Math.floor(Math.random() * PRAISE.length)], next);
      },
      // Wrong: gentle shake and soft sound, then hear the word again. No penalty shown.
      wrong: function (target, word) {
        state.mistakes++;
        if (target) Fx.move(target, 'shake');
        Fx.sound('oops');
        if (word) {
          Speech.zh('game.try_again');
          Speech.play(word, { queue: true });
        }
      },
      miss: function () { state.mistakes++; },
      // Learning progress for a word: 'seen', 'right' or 'wrong' (js/progress.js).
      record: function (word, outcome) {
        if (!word) return;
        Progress.played(word.id);
        if (outcome === 'seen') Progress.seen(word.id);
        else Progress.answer(word.id, outcome === 'right');
      },
      // Words missed in this round, asked once more at the end: one
      // listen-and-pick question each (hear the word, pick from 4 pictures),
      // after a spoken "that word again" so the child knows the game changed.
      // `q` is the question number to continue from; done() runs after the last.
      // opts.bridge: an easy word from the round asked first and not recorded,
      // so a word missed in the very last question is not asked twice in a row.
      askAgain: function (list, q, done, opts) {
        if (!list.length) { done(); return; }
        var items = list.map(function (w) { return { w: w, record: true }; });
        if (opts && opts.bridge) items.unshift({ w: opts.bridge, record: false });
        var grid = el('div', 'choices');
        stage.textContent = '';
        stage.appendChild(grid);
        var base = $('#dots').children.length;
        items.forEach(function () { api.addDot(); });
        var k = 0;
        function ask() {
          if (k >= items.length) { done(); return; }
          var w = items[k].w, rec = items[k].record, missed = false, locked = false;
          api.setQ(q + k);
          grid.textContent = '';
          Quiz.questionsFor([w], state.words, 4, Math.random)[0].options.forEach(function (o) {
            var b = api.picture(o);
            b.dataset.again = '1';
            b.addEventListener('click', function () {
              if (locked || b.classList.contains('is-wrong')) return;
              if (o.id === w.id) {
                locked = true;
                if (rec) api.record(w, missed ? 'seen' : 'right');
                b.classList.add('is-right');
                api.dot(base + k);
                api.right(b, function () { k++; ask(); });
              } else {
                b.classList.add('is-wrong');
                if (!missed && rec) api.record(w, 'wrong');
                missed = true;
                api.wrong(b, w);
              }
            });
            grid.appendChild(b);
          });
          api.onReplay(function () { api.word(w); });
          if (k === 0) {
            // Once, before the first ask-again question; the word waits for it.
            Speech.zh('game.ask_again');
            api.word(w, { queue: true });
          } else {
            api.word(w);
          }
        }
        ask();
      },
      // End of round: stars from mistakes (`ok` or fewer = 3, `fair` or fewer = 2).
      finish: function (ok, fair) {
        later(300, function () { result(Quiz.stars(state.mistakes, ok, fair)); });
      }
    };
    def.start(api);
  }

  // Result screen: stars, then they fly into the star jar. `words` are the
  // words of this round; one of them jumps above the stars.
  function result(n, words) {
    var round = words || state.roundWords || [];
    stop();
    App.show('result');
    var friend = $('#resultFriend');
    var pool = round.length ? round : state.words;
    var w = pool[Math.floor(Math.random() * pool.length)];
    if (w) { friend.src = w.image; friend.dataset.word = w.id; }
    var box = $('#resultStars');
    box.textContent = '';
    box.dataset.stars = String(n);
    box.setAttribute('aria-label', n + ' / 3');
    for (var i = 0; i < 3; i++) {
      var s = icon('#i-star', 'big-star' + (i < n ? ' on' : ''));
      s.style.animationDelay = (i * 0.25) + 's';
      box.appendChild(s);
    }
    // One rising ding per star as it pops in (stars are 0.25 s apart).
    Fx.sound('ding1');
    [2, 3].slice(0, Math.max(0, n - 1)).forEach(function (k) {
      var t = setTimeout(function () { if (!$('#result').hidden) Fx.sound('ding' + k); }, (k - 1) * 250);
      state.timers.push(t);
    });
    Speech.zh('stars.' + n);
    Jar.drop(n, [].slice.call(box.querySelectorAll('.big-star.on')), $('#result .jar-box'), 1100);
  }

  function bind() {
    $('#replayBtn').addEventListener('click', function () {
      if (state.replay) state.replay();
    });
    $('#againBtn').addEventListener('click', function () {
      if (state.opts && state.opts.mode === 'review') review();
      else if (state.game) open(state.game, state.opts);
    });
  }

  // Today's review: due words first (then the least known), so missed words
  // come back. Nothing due: say so kindly and practise the words that need it
  // most. The play mode takes turns: listen, match, memory, cards.
  var REVIEW_SIZE = 6;
  function review() {
    var set = Progress.reviewSet(state.words, REVIEW_SIZE);
    var intro = set.due.length ? 'review.intro' : 'review.none';
    var list = Quiz.shuffle(set.list, Math.random);
    var mode = Progress.nextReviewMode();
    var def = defs.filter(function (d) { return d.id === mode; })[0];
    if (!def) {
      // Cards: look through the review words (counts as seen only).
      stop();
      state.game = null;
      state.opts = { mode: 'review' };
      App.reviewCards(list, intro);
      return;
    }
    open(def, { targets: list, intro: intro, back: 'themes', mode: 'review' });
  }

  // The result screen with n stars (tests and audits use it to reach the screen).
  function showResult(n, words) {
    setBack('games');
    result(n, words || []);
  }

  window.Games = { open: open, register: register, build: build, menu: menu, stop: stop, bind: bind, review: review, showResult: showResult, list: function () { return defs.slice(); } };
})();
