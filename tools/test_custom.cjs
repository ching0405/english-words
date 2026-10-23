// Unit tests for parent-added words and phrases (js/custom.js): ids, checks,
// reading a backup (good and broken files) and merging it into a device's list.
// Usage: node --test tools/test_custom.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const C = require('../js/custom.js');

const read = f => JSON.parse(fs.readFileSync(path.join(__dirname, '..', f), 'utf8'));
const WORDS = read('data/words.json');
const PHRASES = read('data/phrases.json');
const THEMES = read('data/themes.json');
const GALLERY = WORDS.concat(PHRASES).map(w => w.image);
const BUILTIN = { words: WORDS, phrases: PHRASES, themes: THEMES, gallery: GALLERY };
const PHOTO = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ==';
const ctx = extra => Object.assign({ themes: THEMES.map(t => t.id), gallery: GALLERY, taken: WORDS.map(w => w.english) }, extra);

function backup(extra) {
  return JSON.stringify(Object.assign({
    format: C.FORMAT, version: 1,
    themes: [{ id: 'my_theme_pets', english: 'Pets', chinese: '寵物', color: '#ffd6a5' }],
    words: [
      { id: 'my_word_cat', english: 'cat', chinese: '貓', theme: 'my_theme_pets', image: PHOTO },
      { id: 'my_word_horse', english: 'horse', chinese: '馬', theme: 'animals', image: 'images/words/zebra.svg' }
    ],
    phrases: [{ id: 'my_phrase_good_night', english: 'Good night.', chinese: '晚安', category: 'custom', image: PHOTO }]
  }, extra));
}

test('built-in ids never use the parent prefix', () => {
  WORDS.concat(PHRASES, THEMES).forEach(w => assert.ok(!/^my_/.test(w.id), w.id));
});

test('ids: prefix, readable slug, never taken', () => {
  assert.equal(C.makeId('word', 'Teddy Bear', []), 'my_word_teddy_bear');
  assert.equal(C.makeId('phrase', 'What is it?', []), 'my_phrase_what_is_it');
  assert.equal(C.makeId('word', 'cat', ['my_word_cat', 'my_word_cat_2']), 'my_word_cat_3');
  assert.equal(C.makeId('theme', '', []), 'my_theme_item');
  WORDS.forEach(w => assert.notEqual(C.makeId('word', w.english, []), w.id));
});

test('word checks give a friendly message', () => {
  const ok = { english: 'cat', chinese: '貓', theme: 'animals', image: PHOTO };
  assert.equal(C.checkWord(ok, ctx()), null);
  assert.equal(C.checkWord(Object.assign({}, ok, { image: 'images/words/lion.svg' }), ctx()), null);
  assert.match(C.checkWord(Object.assign({}, ok, { english: '' }), ctx()), /英文/);
  assert.match(C.checkWord(Object.assign({}, ok, { english: 'cat2' }), ctx()), /字母/);
  assert.match(C.checkWord(Object.assign({}, ok, { chinese: ' ' }), ctx()), /中文/);
  assert.match(C.checkWord(Object.assign({}, ok, { theme: 'nope' }), ctx()), /主題/);
  assert.match(C.checkWord(Object.assign({}, ok, { english: 'lion' }), ctx()), /已經有/);
  assert.match(C.checkWord(Object.assign({}, ok, { image: 'https://example.com/x.png' }), ctx()), /照片/);
  assert.match(C.checkWord(Object.assign({}, ok, { image: 'data:image/svg+xml;base64,AAAA' }), ctx()), /照片/);
  assert.equal(C.checkWord(Object.assign({}, ok, { image: '' }), ctx({ needImage: false })), null);
});

test('phrase checks: up to four words so the order game fits', () => {
  const ok = { english: 'Good night.', chinese: '晚安', image: PHOTO };
  const c = ctx({ taken: PHRASES.map(p => p.english.toLowerCase()) });
  assert.equal(C.checkPhrase(ok, c), null);
  assert.equal(C.checkPhrase(Object.assign({}, ok, { english: 'Can I have it?' }), c), null);
  assert.match(C.checkPhrase(Object.assign({}, ok, { english: 'Can I have some water?' }), c), /最多 4/);
  assert.match(C.checkPhrase(Object.assign({}, ok, { english: 'Hello.' }), c), /已經有/);
  assert.match(C.checkPhrase(Object.assign({}, ok, { english: '你好' }), c), /英文/);
  assert.deepEqual(C.tokens('Good night.'), ['Good', 'night.']);
});

test('a good backup is read in full', () => {
  const res = C.readBackup(backup(), BUILTIN, C.empty());
  assert.equal(res.ok, true, res.error);
  assert.equal(res.doc.words.length, 2);
  assert.equal(res.doc.phrases.length, 1);
  assert.equal(res.doc.themes[0].id, 'my_theme_pets');
});

test('broken backups are refused with a gentle message', () => {
  const bad = [
    ['not json {', /JSON/],
    [JSON.stringify([1, 2]), /不是/],
    [JSON.stringify({ format: 'other' }), /不是/],
    [backup({ version: 99 }), /新的版本/],
    [JSON.stringify({ format: C.FORMAT, version: 1 }), /沒有單字/],
    [backup({ words: [{ id: 'goat', english: 'goaty', chinese: '羊', theme: 'animals', image: PHOTO }] }), /my_word_/],
    [backup({ words: [{ id: 'my_word_x', english: 'x', chinese: '', theme: 'animals', image: PHOTO }] }), /中文/],
    [backup({ words: [{ id: 'my_word_x', english: 'x', chinese: '叉', theme: 'space', image: PHOTO }] }), /主題/],
    [backup({ words: [{ id: 'my_word_x', english: 'x', chinese: '叉', theme: 'animals', image: 'javascript:alert(1)' }] }), /照片/],
    [backup({ words: [{ id: 'my_word_x', english: 'x', chinese: '叉', theme: 'animals', image: PHOTO }, { id: 'my_word_x', english: 'y', chinese: '叉', theme: 'animals', image: PHOTO }] }), /重複/],
    [backup({ words: [null] }), /格式/],
    [backup({ phrases: [{ id: 'my_phrase_long', english: 'one two three four five', chinese: '五', image: PHOTO }] }), /最多 4/]
  ];
  bad.forEach(([text, why]) => {
    const res = C.readBackup(text, BUILTIN, C.empty());
    assert.equal(res.ok, false, text.slice(0, 60));
    assert.match(res.error, why, res.error);
  });
});

test('merging: new items added, same id replaced, built-in duplicates skipped', () => {
  const current = C.empty();
  current.words.push({ id: 'my_word_cat', english: 'cat', chinese: '小貓', theme: 'animals', image: 'idb' });
  current.words.push({ id: 'my_word_dog', english: 'dog', chinese: '狗', theme: 'animals', image: 'idb' });
  const doc = C.readBackup(backup({
    words: [
      { id: 'my_word_cat', english: 'cat', chinese: '貓', theme: 'my_theme_pets', image: PHOTO },
      { id: 'my_word_lion', english: 'Lion', chinese: '獅子', theme: 'animals', image: PHOTO },
      { id: 'my_word_doggy', english: 'dog', chinese: '狗狗', theme: 'animals', image: PHOTO },
      { id: 'my_word_bus', english: 'bus', chinese: '公車', theme: 'animals', image: PHOTO }
    ]
  }), BUILTIN, current).doc;
  const res = C.mergeBackup(current, doc, BUILTIN);
  assert.equal(res.updated, 1);
  assert.equal(res.added, 2); // bus + the phrase
  assert.deepEqual(res.skipped.sort(), ['Lion', 'dog']);
  assert.equal(res.next.words.find(w => w.id === 'my_word_cat').chinese, '貓');
  assert.equal(res.next.themes.length, 1);
  assert.equal(current.words[0].chinese, '小貓', 'the current list is not changed in place');
  assert.deepEqual(C.unusedThemes(res.next), []);
});

test('the saved list survives junk and keeps only well-formed items', () => {
  assert.equal(C.parseList('{').broken, true);
  assert.equal(C.parseList(null).broken, false);
  const res = C.parseList(JSON.stringify({ version: 1, words: [{ id: 'goat', english: 'goat', image: 'x' }, { id: 'my_word_cat', english: 'cat', chinese: '貓', theme: 'animals', image: 'idb' }], phrases: 'oops' }));
  assert.equal(res.broken, false);
  assert.deepEqual(res.data.words.map(w => w.id), ['my_word_cat']);
  assert.deepEqual(res.data.phrases, []);
});

// F5: one built-in picture belongs to one word (and one phrase).
test('a built-in picture already used by another word is refused', () => {
  const used = {};
  WORDS.forEach(w => { used[w.image] = w.english; });
  const horse = { english: 'horse', chinese: '馬', theme: 'animals', image: 'images/words/zebra.svg' };
  assert.match(C.checkWord(horse, ctx({ used })) || '', /zebra/);
  assert.equal(C.checkWord(Object.assign({}, horse, { image: 'images/phrases/ready.svg' }), ctx({ used })), null);
  // Importing a backup whose word reuses a picture is refused as a whole.
  const doc = C.readBackup(backup(), BUILTIN, C.empty()).doc;
  const res = C.mergeBackup(C.empty(), doc, BUILTIN);
  assert.match(res.clash || '', /horse.*zebra/);
});
