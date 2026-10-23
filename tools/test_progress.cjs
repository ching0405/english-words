// Unit tests for learning progress and spaced review (js/progress.js).
// Usage: node --test tools/test_quiz.cjs tools/test_progress.cjs
// Runs in Asia/Taipei time, like the family's iPad.
process.env.TZ = 'Asia/Taipei';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const P = require('../js/progress.js');

const WORDS = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/words.json'), 'utf8'));
const DAY = P.DAY;
const HOUR = 60 * 60 * 1000;
// Local Taipei time.
const at = (y, mo, d, h = 0, mi = 0) => new Date(y, mo - 1, d, h, mi).getTime();
const T0 = at(2026, 10, 22, 19, 0); // Thursday 19:00

function memoryStorage(init) {
  const m = Object.assign({}, init);
  return {
    getItem: k => (k in m ? m[k] : null),
    setItem: (k, v) => { m[k] = String(v); },
    removeItem: k => { delete m[k]; },
    dump: () => m
  };
}

function setup(init, start = T0) {
  const clock = { t: start };
  const store = memoryStorage(init);
  const p = P.create(store, () => clock.t);
  p.load();
  return { p, store, clock };
}

test('test clock really runs in Taipei time', () => {
  assert.equal(new Date(T0).getHours(), 19);
  assert.equal(P.dayAfter(T0, 1), at(2026, 10, 23));
});

test('seen at 19:00: due at 0:00 the next calendar day, not 24 hours later', () => {
  const { p, clock } = setup();
  p.seen('goat');
  clock.t = at(2026, 10, 22, 23, 59);
  assert.equal(p.isDue('goat'), false);
  clock.t = at(2026, 10, 23, 0, 0);
  assert.equal(p.isDue('goat'), true);
  clock.t = at(2026, 10, 23, 7, 30);  // breakfast, well before 19:00
  assert.deepEqual(p.due(WORDS).map(w => w.id), ['goat']);
});

test('seen just after midnight is also due the next midnight', () => {
  const { p, clock } = setup(undefined, at(2026, 10, 22, 0, 5));
  p.seen('cow');
  assert.equal(p.get('cow').due, at(2026, 10, 23));
  clock.t = at(2026, 10, 23, 0, 0);
  assert.equal(p.isDue('cow'), true);
});

test('right answers on due days stretch the interval: 1, 2, 4, 8, 16 calendar days', () => {
  const { p, clock } = setup();
  const gaps = [];
  p.answer('cow', true); // brand new word answered right: box 1
  for (let i = 0; i < 6; i++) {
    const r = p.get('cow');
    gaps.push(Math.round((r.due - P.dayAfter(clock.t, 0)) / DAY));
    clock.t = r.due + 9 * HOUR; // play at 9:00 on the due day
    p.answer('cow', true);
  }
  assert.deepEqual(gaps, [1, 2, 4, 8, 16, 16]);
  assert.equal(p.get('cow').box, 5);
  assert.equal(new Date(p.get('cow').due).getHours(), 0);
});

test('extra right answers before the word is due do not skip boxes', () => {
  const { p, clock } = setup();
  p.answer('lion', true);
  const due = p.get('lion').due;
  for (let i = 0; i < 5; i++) { clock.t += 60 * 1000; p.answer('lion', true); }
  assert.equal(p.get('lion').box, 1);
  assert.equal(p.get('lion').due, due);
  assert.equal(p.get('lion').right, 6);
});

test('a missed word goes back to box 0 and waits until tomorrow (not 5 minutes)', () => {
  const { p, clock } = setup();
  p.answer('wolf', true);
  clock.t = p.get('wolf').due + HOUR;
  p.answer('wolf', true);
  assert.equal(p.get('wolf').box, 2);
  p.answer('wolf', false);
  assert.equal(p.get('wolf').box, 0);
  assert.equal(p.get('wolf').due, P.dayAfter(clock.t, 1));
  clock.t += 2 * HOUR;
  assert.equal(p.isDue('wolf'), false, 'not back on the review card the same day');
});

test('asked again at the end of the round: right or wrong, it is due tomorrow', () => {
  for (const second of [true, false]) {
    const { p, clock } = setup();
    p.answer('zebra', true);
    clock.t = p.get('zebra').due + HOUR;
    p.answer('zebra', false);          // missed in the round
    clock.t += 3 * 60 * 1000;
    p.answer('zebra', second);         // asked once more at the end
    const r = p.get('zebra');
    assert.ok(r.box <= 1, `box ${r.box}`);
    assert.equal(r.due, P.dayAfter(clock.t, 1), `second answer ${second}`);
  }
});

test('two weeks of daily play: missed words come back more than known ones', () => {
  const { p, clock } = setup();
  const easy = 'koala', hard = 'zebra';
  const reviews = { [easy]: 0, [hard]: 0 };
  p.seen(easy); p.seen(hard);
  for (let day = 1; day <= 14; day++) {
    clock.t = at(2026, 10, 22 + day, 8 + (day % 12)); // a different hour every day
    for (const w of p.due(WORDS)) {
      reviews[w.id]++;
      p.answer(w.id, w.id === easy || reviews[w.id] % 2 === 0);
    }
  }
  assert.ok(reviews[hard] > reviews[easy], JSON.stringify(reviews));
  assert.ok(p.get(easy).box > p.get(hard).box);
});

test('clock jumps a year ahead and back: no word gets stuck, save stays valid', () => {
  const { p, store, clock } = setup();
  for (const w of WORDS.slice(0, 5)) p.seen(w.id);
  clock.t = T0 + 365 * DAY;                 // clock set a year ahead
  for (const w of p.due(WORDS)) p.answer(w.id, true);
  clock.t = T0 + HOUR;                      // and back to now
  const later = P.dayAfter(clock.t, 3);
  for (const w of WORDS.slice(0, 5)) {
    const r = p.get(w.id);
    assert.ok(r.due <= later, `${w.id} due ${new Date(r.due)}`);
    assert.ok(r.last <= clock.t, `${w.id} last in the future`);
  }
  clock.t = P.dayAfter(T0, 3);
  assert.equal(p.due(WORDS).length, 5, 'all come back within the normal interval');
  assert.equal(JSON.parse(store.getItem(P.KEY)).version, P.VERSION);
});

test('a save from the future (dates far ahead) is repaired when loaded', () => {
  const far = T0 + 400 * DAY;
  const raw = JSON.stringify({ version: 3, words: { goat: { seen: 1, right: 1, wrong: 0, last: far, box: 1, due: far + DAY } }, best: {}, jar: { stars: 0, full: 0 }, reviewTurn: 0 });
  const { p } = setup({ [P.KEY]: raw });
  assert.equal(p.get('goat').last, T0);
  assert.equal(p.get('goat').due, P.dayAfter(T0, 1));
});

test('many clock jumps back and forth: format stays valid, nothing unreachable', () => {
  const { p, store, clock } = setup();
  const jumps = [30, -30, 200, -199, 5, -400, 3, 0, 90, -91];
  let base = T0;
  for (const j of jumps) {
    base += j * DAY;
    clock.t = base;
    for (const w of WORDS) {
      if (p.isDue(w.id) || !p.get(w.id)) p.answer(w.id, (w.id.length + j) % 3 !== 0);
    }
    const saved = JSON.parse(store.getItem(P.KEY));
    assert.equal(saved.version, P.VERSION);
    for (const [id, r] of Object.entries(saved.words)) {
      for (const k of ['seen', 'right', 'wrong', 'last', 'box', 'due']) assert.ok(Number.isFinite(r[k]) && r[k] >= 0, `${id}.${k}`);
      assert.ok(r.due <= P.dayAfter(clock.t, P.INTERVALS[r.box] + 1), `${id} due too far`);
      assert.ok(r.last <= clock.t, `${id} last in the future`);
    }
  }
  clock.t = P.dayAfter(base, 17);
  assert.equal(p.due(WORDS).length, WORDS.length, 'every word comes back within the longest interval');
});

test('due list: weakest and most overdue first', () => {
  const { p, clock } = setup();
  p.answer('goat', true);                          // box 1, due tomorrow
  p.seen('cow');                                   // box 0, due tomorrow
  clock.t += 3 * DAY;
  assert.deepEqual(p.due(WORDS).map(w => w.id), ['cow', 'goat']);
});

test('review set: due words first, then the least known; never more than asked', () => {
  const { p, clock } = setup();
  for (const w of WORDS) { p.answer(w.id, true); }  // all box 1
  clock.t = P.dayAfter(T0, 1) + HOUR;
  p.answer('goat', true); p.answer('cow', true);    // now box 2, not due
  const set = p.reviewSet(WORDS, 6);
  assert.equal(set.list.length, 6);
  assert.equal(set.due.length, WORDS.length - 2);
  assert.ok(!set.list.some(w => w.id === 'goat' || w.id === 'cow'));
  const fresh = setup();
  fresh.p.answer('goat', true);
  const s2 = fresh.p.reviewSet(WORDS, 6);
  assert.equal(s2.due.length, 0);
  assert.equal(s2.list.length, 6);
  assert.ok(!s2.list.some(w => w.id === 'goat'));
});

test('theme stars only go up, even when a known word is missed', () => {
  const { p, clock } = setup();
  const hw = WORDS.filter(w => w.theme === 'halloween');
  assert.equal(p.themeStars(WORDS, 'halloween'), 0);
  p.seen(hw[0].id);
  assert.equal(p.themeStars(WORDS, 'halloween'), 1);
  // Answer right on due days until the word reaches box 2 ("known").
  const learn = id => { p.answer(id, true); while (p.get(id).box < 2) { clock.t = Math.max(clock.t, p.get(id).due) + HOUR; p.answer(id, true); } };
  hw.forEach(w => learn(w.id));
  assert.equal(p.themeStars(WORDS, 'halloween'), 3);
  hw.forEach(w => p.answer(w.id, false));        // a bad day: every word missed
  assert.equal(p.get(hw[0].id).box, 0, 'schedule still resets');
  assert.equal(p.themeStars(WORDS, 'halloween'), 3, 'stars are not taken back');
  assert.equal(p.themeStars(WORDS, 'nope'), 0);
});

test('star jar: counts stars, fills at JAR_SIZE, starts a new jar, survives reload', () => {
  const { p, store, clock } = setup();
  assert.deepEqual(p.jar(), { stars: 0, full: 0, size: P.JAR_SIZE });
  let res = p.addJarStars(3);
  assert.deepEqual(res.jar, { stars: 3, full: 0 });
  assert.equal(res.filled, false);
  for (let i = 0; i < 3; i++) p.addJarStars(3);  // 12
  res = p.jar();
  assert.deepEqual([res.stars, res.full], [0, 1]);
  res = p.addJarStars(2);
  assert.equal(res.filled, false);
  res = p.addJarStars(P.JAR_SIZE - 1);           // 2 + 11 = 13: second jar full, 1 left over
  assert.equal(res.filled, true);
  assert.deepEqual(res.jar, { stars: 1, full: 2 });
  const again = P.create(store, () => clock.t);
  again.load();
  assert.deepEqual(again.jar(), { stars: 1, full: 2, size: P.JAR_SIZE });
});

test('star jar: broken jar fields are repaired, the rest of the save kept', () => {
  for (const jar of ['x', null, { stars: 'many', full: -2 }, { stars: 30, full: 1 }]) {
    const raw = JSON.stringify({ version: 3, words: { goat: { seen: 2, right: 0, wrong: 0, last: T0, box: 0, due: P.dayAfter(T0, 1) } }, best: { animals: 1 }, jar, reviewTurn: 1 });
    const { p, store } = setup({ [P.KEY]: raw });
    const j = p.jar();
    assert.ok(Number.isInteger(j.stars) && j.stars >= 0 && j.stars < P.JAR_SIZE, JSON.stringify(jar));
    assert.ok(Number.isInteger(j.full) && j.full >= 0, JSON.stringify(jar));
    assert.equal(p.get('goat').seen, 2);
    assert.equal(store.getItem(P.BROKEN_KEY), null);
  }
  const { p } = setup({ [P.KEY]: JSON.stringify({ version: 3, words: {}, jar: { stars: 30, full: 1 } }) });
  assert.deepEqual(p.jar(), { stars: 6, full: 3, size: P.JAR_SIZE }, 'overflowing stars become full jars');
});

test('review mode takes turns: listen, match, memory, cards, listen…', () => {
  const { p, store, clock } = setup();
  const modes = [];
  for (let i = 0; i < 5; i++) modes.push(p.nextReviewMode());
  assert.deepEqual(modes, ['listen', 'match', 'memory', 'cards', 'listen']);
  const again = P.create(store, () => clock.t);
  again.load();
  assert.equal(again.nextReviewMode(), 'match', 'the turn is saved');
});

test('progress survives a reload', () => {
  const { p, store, clock } = setup();
  p.seen('goat'); p.answer('cow', false);
  const again = P.create(store, () => clock.t);
  again.load();
  assert.equal(again.get('goat').seen, 1);
  assert.equal(again.get('cow').wrong, 1);
});

test('version-1 saves are migrated to the current format', () => {
  const last = at(2026, 10, 21, 10);
  const v1 = { version: 1, seen: { goat: 3 }, right: { goat: 2, cow: 1 }, wrong: { cow: 1 }, last: { goat: last } };
  const { p, store } = setup({ [P.KEY]: JSON.stringify(v1) });
  const saved = JSON.parse(store.getItem(P.KEY));
  assert.equal(saved.version, P.VERSION);
  assert.deepEqual(p.get('goat'), { seen: 3, right: 2, wrong: 0, last, box: 2, due: P.dayAfter(last, 2) });
  assert.equal(p.get('cow').box, 0);
  assert.deepEqual(p.jar(), { stars: 0, full: 0, size: P.JAR_SIZE });
  assert.equal(store.getItem(P.BROKEN_KEY), null);
});

test('version-2 saves (phase 3 first build) gain the jar and keep every word', () => {
  const v2 = { version: 2, words: { lion: { seen: 1, right: 1, wrong: 0, last: T0, box: 1, due: P.dayAfter(T0, 1) } } };
  const { p, store } = setup({ [P.KEY]: JSON.stringify(v2) });
  assert.equal(JSON.parse(store.getItem(P.KEY)).version, 3);
  assert.equal(p.get('lion').box, 1);
  assert.equal(p.nextReviewMode(), 'listen');
});

test('broken saves are set aside and replaced by a fresh start', () => {
  for (const raw of ['{not json', '42', '"text"', 'null', '[]', '{"version":"2"}', '{"version":99,"words":{}}', '{"version":3,"words":[]}', '{"version":0}']) {
    const { p, store } = setup({ [P.KEY]: raw });
    const snap = p.snapshot();
    assert.deepEqual(snap.words, {}, raw);
    assert.deepEqual(snap.jar, { stars: 0, full: 0 }, raw);
    assert.equal(store.getItem(P.BROKEN_KEY), raw, raw);
    p.seen('goat');
    assert.equal(JSON.parse(store.getItem(P.KEY)).words.goat.seen, 1, raw);
  }
});

test('bad fields inside a good save are repaired, good words kept', () => {
  const raw = JSON.stringify({ version: 3, words: { goat: { seen: 2, right: 'x', wrong: -3, box: 99, due: null }, cow: 'oops', lion: { seen: 1, right: 1, wrong: 0, last: T0, box: 1, due: P.dayAfter(T0, 1) } } });
  const { p } = setup({ [P.KEY]: raw });
  assert.deepEqual(p.get('goat'), { seen: 2, right: 0, wrong: 0, last: 0, box: 5, due: 0 });
  assert.equal(p.get('cow'), null);
  assert.equal(p.get('lion').box, 1);
});

test('adding or removing words leaves the other words alone', () => {
  const { p } = setup();
  p.answer('goat', true); p.seen('cow');
  const before = p.snapshot();
  const fewer = WORDS.filter(w => w.id !== 'cow');
  const more = WORDS.concat([{ id: 'panda', english: 'panda', chinese: '熊貓', theme: 'animals', image: 'x' }]);
  assert.deepEqual(p.due(fewer), []);
  assert.equal(p.get('panda'), null);
  assert.deepEqual(p.snapshot().words, before.words);
  assert.equal(p.themeStars(more, 'animals'), 1);
  p.answer('panda', true);
  assert.deepEqual(p.get('goat'), before.words.goat);
});

test('clear starts over', () => {
  const { p, store } = setup();
  p.seen('goat');
  p.addJarStars(3);
  p.clear();
  assert.equal(p.get('goat'), null);
  assert.equal(p.jar().stars, 0);
  assert.equal(store.getItem(P.KEY), null);
});

test('blocked storage still works in memory', () => {
  const broken = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
  const p = P.create(broken, () => T0);
  p.load();
  p.seen('goat');
  p.addJarStars(2);
  assert.equal(p.get('goat').seen, 1);
  assert.equal(p.jar().stars, 2);
});

test('forget drops only the deleted parent-made words and themes', () => {
  const { p, store } = setup();
  p.seen('goat');
  p.answer('lion', true);
  p.seen('my_word_cat');
  p.answer('my_word_cat', false);
  p.themeStars([{ id: 'my_word_cat', theme: 'my_theme_pets' }], 'my_theme_pets');
  p.themeStars(WORDS, 'animals');
  p.addJarStars(5);
  const before = JSON.parse(store.getItem(P.KEY));
  p.forget(['my_word_cat'], ['my_theme_pets']);
  const after = JSON.parse(store.getItem(P.KEY));
  assert.equal(p.get('my_word_cat'), null);
  assert.equal(after.best.my_theme_pets, undefined);
  assert.deepEqual(after.words.goat, before.words.goat);
  assert.deepEqual(after.words.lion, before.words.lion);
  assert.equal(after.best.animals, before.best.animals);
  assert.deepEqual(after.jar, before.jar);
  p.forget(['no_such_word']);
  assert.deepEqual(JSON.parse(store.getItem(P.KEY)).words, after.words);
});

test('forget reports whether the deletion was saved (F2)', () => {
  const { p, store } = setup();
  p.answer('my_word_cat', true);
  p.answer('goat', true);
  assert.equal(p.forget(['my_word_cat'], []), true);
  p.answer('my_word_dog', true);
  const real = store.setItem;
  store.setItem = () => { throw new Error('QuotaExceededError'); };
  assert.equal(p.forget(['my_word_dog'], []), false, 'a failed save is reported, not swallowed');
  store.setItem = real;
  assert.ok(JSON.parse(store.dump()[P.KEY]).words.my_word_dog, 'the record is still on disk, so the caller must know');
});
