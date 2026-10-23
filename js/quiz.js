// Question engine shared by all games. Builds rounds straight from
// data/words.json, so new words join every game automatically.
// Pure functions (no DOM); runs in the browser (window.Quiz) and in Node for
// tests (tools/test_quiz.cjs). Pass `rand` (e.g. Quiz.rng(42)) for repeatable rounds.
(function (root) {
  'use strict';

  // Small seeded random generator (mulberry32).
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffle(list, rand) {
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function key(w) { return String(w.english).toLowerCase(); }

  // Words that sound the same or look the same (one picture) cannot share a
  // question or a board: a child could not tell them apart.
  function clash(seen, w) { return seen[key(w)] || (w.image && seen['pic:' + w.image]); }
  function mark(seen, w) { seen[key(w)] = true; if (w.image) seen['pic:' + w.image] = true; }

  // Words of a theme; unknown or empty theme means every word.
  function pool(words, themeId) {
    var p = words.filter(function (w) { return !themeId || w.theme === themeId; });
    return p.length ? p : words.slice();
  }

  // `n` question targets. No repeats while words last; with fewer words than
  // questions, words come round again but never twice in a row.
  function targets(words, n, rand) {
    var out = [];
    while (out.length < n && words.length) {
      var batch = shuffle(words, rand);
      if (out.length && batch.length > 1 && batch[0].id === out[out.length - 1].id) {
        batch.push(batch.shift());
      }
      out = out.concat(batch);
    }
    return out.slice(0, n);
  }

  // Up to `k` wrong choices for `target`: same theme first, then other themes.
  // Never the target itself and never a word that sounds or looks the same.
  function distractors(target, themeWords, allWords, k, rand) {
    var seen = {};
    mark(seen, target);
    var out = [];
    function add(list) {
      shuffle(list, rand).forEach(function (w) {
        if (out.length < k && !clash(seen, w)) { mark(seen, w); out.push(w); }
      });
    }
    add(themeWords.filter(function (w) { return w.theme === target.theme; }));
    add(themeWords);
    add(allWords);
    return out;
  }

  // Listen-and-pick style rounds: [{target, options}] with `choices` options
  // (fewer only when the whole word list is smaller).
  function questions(opts) {
    var rand = opts.rand || Math.random;
    var p = pool(opts.words, opts.themeId);
    return targets(p, opts.count, rand).map(function (t) {
      var wrong = distractors(t, p, opts.words, (opts.choices || 4) - 1, rand);
      return { target: t, options: shuffle([t].concat(wrong), rand) };
    });
  }

  // Questions for given target words (e.g. today's review), in that order,
  // with wrong choices from all words (same theme first).
  function questionsFor(targetWords, allWords, choices, rand) {
    rand = rand || Math.random;
    return targetWords.map(function (t) {
      var wrong = distractors(t, allWords, allWords, (choices || 4) - 1, rand);
      return { target: t, options: shuffle([t].concat(wrong), rand) };
    });
  }

  // `count` different words for one board (matching, memory). Theme words
  // not in `avoid` come first, then other theme words, then other themes.
  function pick(opts) {
    var rand = opts.rand || Math.random;
    var avoid = opts.avoid || {};
    var p = pool(opts.words, opts.themeId);
    var out = [], seen = {};
    function add(list) {
      shuffle(list, rand).forEach(function (w) {
        if (out.length < opts.count && !clash(seen, w)) { mark(seen, w); out.push(w); }
      });
    }
    add(p.filter(function (w) { return !avoid[w.id]; }));
    add(p);
    add(opts.words);
    return out;
  }

  // Several boards in a row, each with different words, spreading words
  // across boards before repeating any.
  function boards(opts) {
    var used = {}, out = [];
    for (var b = 0; b < opts.boards; b++) {
      var board = pick({ words: opts.words, themeId: opts.themeId, count: opts.perBoard, rand: opts.rand, avoid: used });
      board.forEach(function (w) { used[w.id] = true; });
      out.push(board);
    }
    return out;
  }

  // 1–3 stars from mistakes; finishing always earns at least one.
  function stars(mistakes, ok, fair) {
    if (mistakes <= ok) return 3;
    if (mistakes <= fair) return 2;
    return 1;
  }

  var Quiz = { rng: rng, shuffle: shuffle, pool: pool, targets: targets, distractors: distractors, questions: questions, questionsFor: questionsFor, pick: pick, boards: boards, stars: stars };
  if (typeof module !== 'undefined' && module.exports) module.exports = Quiz;
  else root.Quiz = Quiz;
})(this);
