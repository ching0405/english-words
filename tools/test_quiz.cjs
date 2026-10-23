// Unit tests for the question engine (js/quiz.js).
// Usage: node --test tools/test_quiz.cjs tools/test_progress.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Quiz = require('../js/quiz.js');

const ROOT = path.join(__dirname, '..');
const WORDS = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/words.json'), 'utf8'));
const theme = id => WORDS.filter(w => w.theme === id);
const ids = list => list.map(w => w.id);
const fake = (n, t = 'x') => Array.from({ length: n }, (_, i) => ({ id: `${t}${i}`, english: `${t}${i}`, theme: t }));

test('same seed gives the same round; different seeds differ', () => {
  const a = Quiz.questions({ words: WORDS, count: 6, choices: 4, rand: Quiz.rng(7) });
  const b = Quiz.questions({ words: WORDS, count: 6, choices: 4, rand: Quiz.rng(7) });
  const c = Quiz.questions({ words: WORDS, count: 6, choices: 4, rand: Quiz.rng(8) });
  assert.deepEqual(a.map(q => q.target.id), b.map(q => q.target.id));
  assert.notDeepEqual(a.map(q => ids(q.options)), c.map(q => ids(q.options)));
});

test('targets do not repeat while words last', () => {
  for (let seed = 0; seed < 200; seed++) {
    const t = Quiz.targets(theme('animals'), 8, Quiz.rng(seed));
    assert.equal(new Set(ids(t)).size, 8);
  }
});

test('with fewer words than questions, no word comes twice in a row', () => {
  for (let seed = 0; seed < 300; seed++) {
    const t = Quiz.targets(theme('halloween'), 8, Quiz.rng(seed));
    assert.equal(t.length, 8);
    for (let i = 1; i < t.length; i++) assert.notEqual(t[i].id, t[i - 1].id, `seed ${seed} at ${i}`);
    assert.equal(new Set(ids(t.slice(0, 5))).size, 5, 'first pass uses every word once');
  }
});

test('every question has the target once plus distinct wrong choices', () => {
  for (const themeId of [null, 'animals', 'halloween']) {
    for (let seed = 0; seed < 200; seed++) {
      for (const q of Quiz.questions({ words: WORDS, themeId, count: 6, choices: 4, rand: Quiz.rng(seed) })) {
        assert.equal(q.options.length, 4);
        assert.equal(q.options.filter(o => o.id === q.target.id).length, 1);
        assert.equal(new Set(q.options.map(o => o.english.toLowerCase())).size, 4);
      }
    }
  }
});

test('wrong choices come from the same theme when it has enough words', () => {
  for (let seed = 0; seed < 200; seed++) {
    for (const q of Quiz.questions({ words: WORDS, themeId: 'animals', count: 6, choices: 4, rand: Quiz.rng(seed) })) {
      assert.ok(q.options.every(o => o.theme === 'animals'));
    }
  }
});

test('small theme borrows wrong choices from other themes only when needed', () => {
  // Halloween has 5 words: 3 wrong choices always fit inside the theme.
  for (let seed = 0; seed < 200; seed++) {
    for (const q of Quiz.questions({ words: WORDS, themeId: 'halloween', count: 6, choices: 4, rand: Quiz.rng(seed) })) {
      assert.ok(q.options.every(o => o.theme === 'halloween'));
    }
  }
  // A 2-word theme needs 2 borrowed words, and same-theme words come first.
  const words = fake(2, 'tiny').concat(fake(5, 'big'));
  for (let seed = 0; seed < 100; seed++) {
    for (const q of Quiz.questions({ words, themeId: 'tiny', count: 5, choices: 4, rand: Quiz.rng(seed) })) {
      assert.equal(q.options.length, 4);
      assert.equal(q.options.filter(o => o.theme === 'tiny').length, 2);
      assert.equal(new Set(ids(q.options)).size, 4);
    }
  }
});

test('tiny word lists still work', () => {
  const one = fake(1);
  const q1 = Quiz.questions({ words: one, count: 5, choices: 4, rand: Quiz.rng(1) });
  assert.equal(q1.length, 5);
  assert.ok(q1.every(q => q.options.length === 1 && q.target.id === 'x0'));
  const three = fake(3);
  const q3 = Quiz.questions({ words: three, count: 6, choices: 4, rand: Quiz.rng(1) });
  assert.ok(q3.every(q => q.options.length === 3));
  assert.deepEqual(Quiz.questions({ words: [], count: 5, choices: 4 }), []);
});

test('questionsFor keeps the given targets in order, wrong choices same theme first', () => {
  const targets = [WORDS.find(w => w.id === 'zebra'), WORDS.find(w => w.id === 'witch')];
  for (let seed = 0; seed < 100; seed++) {
    const qs = Quiz.questionsFor(targets, WORDS, 4, Quiz.rng(seed));
    assert.deepEqual(qs.map(q => q.target.id), ['zebra', 'witch']);
    qs.forEach(q => {
      assert.equal(q.options.length, 4);
      assert.equal(new Set(ids(q.options)).size, 4);
      assert.ok(q.options.every(o => o.theme === q.target.theme));
    });
  }
});

test('unknown theme falls back to every word', () => {
  assert.equal(Quiz.pool(WORDS, 'space').length, WORDS.length);
});

test('boards: distinct words on each board, spread before repeating', () => {
  for (let seed = 0; seed < 200; seed++) {
    const b = Quiz.boards({ words: WORDS, themeId: 'halloween', boards: 2, perBoard: 3, rand: Quiz.rng(seed) });
    b.forEach(board => assert.equal(new Set(ids(board)).size, 3));
    // 5 halloween words over 6 slots: exactly one word shows up twice.
    const all = ids(b.flat());
    assert.equal(new Set(all).size, 5);
    assert.ok(b.flat().every(w => w.theme === 'halloween'));
  }
});

test('pick fills a memory board from other themes when the theme is small', () => {
  for (let seed = 0; seed < 100; seed++) {
    const p = Quiz.pick({ words: WORDS, themeId: 'halloween', count: 6, rand: Quiz.rng(seed) });
    assert.equal(p.length, 6);
    assert.equal(new Set(ids(p)).size, 6);
    assert.equal(p.filter(w => w.theme === 'halloween').length, 5);
  }
  assert.equal(Quiz.pick({ words: fake(2), count: 6, rand: Quiz.rng(1) }).length, 2);
});

test('stars: finishing always gives at least one', () => {
  assert.equal(Quiz.stars(0, 1, 3), 3);
  assert.equal(Quiz.stars(2, 1, 3), 2);
  assert.equal(Quiz.stars(50, 1, 3), 1);
});

// F5: two words with the same picture must never be on screen together.
test('words sharing one picture never meet in a question or on a board', () => {
  const twin = { id: 'my_word_horse', english: 'horse', theme: 'animals', image: 'images/words/zebra.svg' };
  const words = WORDS.concat([twin]);
  const pictures = list => list.map(w => w.image);
  for (let seed = 0; seed < 300; seed++) {
    const rand = Quiz.rng(seed);
    Quiz.questions({ words, themeId: 'animals', count: 6, choices: 4, rand }).forEach(q => {
      assert.equal(new Set(pictures(q.options)).size, q.options.length, `seed ${seed}: ${ids(q.options)}`);
    });
    Quiz.questionsFor([twin], words, 4, rand).forEach(q => assert.equal(new Set(pictures(q.options)).size, 4));
    const board = Quiz.pick({ words, themeId: 'animals', count: 6, rand });
    assert.equal(new Set(pictures(board)).size, board.length, `seed ${seed}: ${ids(board)}`);
  }
});
