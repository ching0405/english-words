// Words and phrases a parent adds on this device (phase 6). They join the
// built-in lists from data/ at load time and show up in cards, every game,
// today's review and the phrase games; progress is kept like any other word.
//
//   Custom.load()                  read this device's list (Promise)
//   Custom.view(builtInThemes)     {words, phrases, themes} ready to merge
//   Custom.saveWord(item, image)   add (no id) or edit; image is a data URL
//                                  (a new photo) or a built-in picture path
//   Custom.savePhrase(item, image) the same for phrases
//   Custom.remove(kind, id)        delete a word or phrase and its progress
//   Custom.backup()                the whole list as a backup file (Promise)
//   Custom.restore(text, builtIn)  read a backup file; nothing changes unless
//                                  the whole file is fine
//
//   Custom.onChange(fn)            fn() runs when another tab changed the list
//
// Ids start with my_word_, my_phrase_ or my_theme_, so they never meet a
// built-in id. The list lives in localStorage (ew.custom.v1); photos live in
// IndexedDB (the list says "idb" and the photo's key), or inline in the list
// when IndexedDB is not available.
// Safe saving: a new photo is written under a new key and counts only once its
// IndexedDB transaction completes; the list is switched to it in one
// localStorage write, and only then is the old photo dropped. A failed save
// therefore leaves the old list and old photos exactly as they were. Every
// change is made on the list as it is in storage at that moment (another tab
// may have saved since), and other tabs are told through the storage event. Chinese is shown as text only: there is no
// recording for a parent's words and Chinese is never read by TTS.
// The checks below are pure functions and also run in Node (tools/test_custom.cjs).
(function (root) {
  'use strict';

  var KEY = 'ew.custom.v1';
  var BROKEN_KEY = 'ew.custom.broken';
  var FORMAT = 'picture-words-custom';
  var VERSION = 1;
  var PREFIX = { word: 'my_word_', phrase: 'my_phrase_', theme: 'my_theme_' };
  var ID = /^my_(word|phrase|theme)_[a-z0-9_]{1,40}$/;
  var PHOTO_KEY = /^photo_[a-z0-9]{1,30}$/;   // where a photo is kept in IndexedDB
  var PHOTO = /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/;
  var MAX_PHOTO = 3 * 1024 * 1024;   // characters of one data URL in a backup
  var MAX_ITEMS = 500;
  var MAX_TOKENS = 4;                // the order game has room for four word cards
  var COLORS = ['#ffd6a5', '#a0e7e5', '#ffc6c7', '#caffbf', '#d7c8ff', '#fdf3a8'];

  function tidy(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
  function lower(s) { return tidy(s).toLowerCase(); }
  function tokens(english) { return tidy(english).match(/[A-Za-z']+[?.!]?/g) || []; }

  function slug(english) {
    var s = lower(english).replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 30);
    return s || 'item';
  }

  // A new id for `kind` that is not in `taken` (array of ids).
  function makeId(kind, english, taken) {
    var base = PREFIX[kind] + slug(english), id = base, n = 2;
    while (taken.indexOf(id) >= 0) id = base + '_' + n++;
    return id;
  }

  function isPicture(image, gallery) {
    if (typeof image !== 'string') return false;
    if (PHOTO.test(image)) return image.length <= MAX_PHOTO;
    return (gallery || []).indexOf(image) >= 0;
  }

  // Problems with one item, as Chinese text for the parent; null when fine.
  // ctx: {themes: [ids], gallery: [built-in picture paths], taken: [english
  // already used by other items, lower case], used: {picture: english of the
  // other item of this kind that shows it}, needImage}
  function checkWord(w, ctx) {
    var en = tidy(w.english);
    if (!en) return '請輸入英文。';
    if (en.length > 24) return '英文最多 24 個字母。';
    if (!/^[A-Za-z][A-Za-z' -]*$/.test(en)) return '單字的英文只能有英文字母、空格、- 和 \'。';
    if (!tidy(w.chinese)) return '請輸入中文。';
    if (tidy(w.chinese).length > 12) return '中文最多 12 個字。';
    if ((ctx.themes || []).indexOf(w.theme) < 0) return '請選一個主題。';
    if ((ctx.taken || []).indexOf(en.toLowerCase()) >= 0) return '已經有「' + en + '」這個字了。';
    if (ctx.needImage !== false && !isPicture(w.image, ctx.gallery)) return '請拍照、選一張照片，或從內建圖片選一張。';
    return sharedPicture(w, ctx);
  }

  // Two words (or two phrases) with one picture would put two identical
  // pictures in one question, and a child cannot tell which one is meant.
  function sharedPicture(w, ctx) {
    var other = w.image && (ctx.used || {})[w.image];
    return other ? '這張圖片已經是「' + other + '」的圖了，同一張圖不能給兩個，請換一張。' : null;
  }

  function checkPhrase(p, ctx) {
    var en = tidy(p.english);
    if (!en) return '請輸入英文句子。';
    if (en.length > 40) return '英文句子最多 40 個字母。';
    if (!/^[A-Za-z][A-Za-z' ,]*[.?!]?$/.test(en)) return '句子只能有英文字母、空格、逗號、\' ，最後可以加 . ? !';
    if (tokens(en).length > MAX_TOKENS) return '句子最多 ' + MAX_TOKENS + ' 個英文字（排句子遊戲放得下）。';
    if (!tidy(p.chinese)) return '請輸入中文意思。';
    if (tidy(p.chinese).length > 20) return '中文最多 20 個字。';
    if ((ctx.taken || []).indexOf(en.toLowerCase()) >= 0) return '已經有「' + en + '」這句了。';
    if (ctx.needImage !== false && !isPicture(p.image, ctx.gallery)) return '請拍照、選一張照片，或從內建圖片選一張。';
    return sharedPicture(p, ctx);
  }

  // {picture: english} for the items of one kind, leaving out the item `id`.
  function usedPictures(items, id) {
    var used = {};
    items.forEach(function (x) { if (x.id !== id && x.image && x.image !== 'idb') used[x.image] = x.english; });
    return used;
  }

  function checkTheme(t) {
    if (!tidy(t.chinese)) return '請輸入新主題的中文名稱。';
    if (tidy(t.chinese).length > 8) return '主題名稱最多 8 個字。';
    if (tidy(t.english) && !/^[A-Za-z][A-Za-z ]{0,19}$/.test(tidy(t.english))) return '主題的英文名稱只能有英文字母和空格（最多 20 個）。';
    return null;
  }

  function empty() { return { version: VERSION, themes: [], words: [], phrases: [] }; }

  // The saved list; anything malformed is dropped (and the raw text kept aside by the caller).
  function parseList(raw) {
    if (raw === null || raw === undefined) return { data: empty(), broken: false };
    var d;
    try { d = JSON.parse(raw); } catch (e) { return { data: empty(), broken: true }; }
    if (!d || typeof d !== 'object' || d.version !== VERSION) return { data: empty(), broken: true };
    var out = empty();
    var str = function (v) { return typeof v === 'string' ? v : ''; };
    (Array.isArray(d.themes) ? d.themes : []).forEach(function (t) {
      if (t && ID.test(t.id) && t.id.indexOf(PREFIX.theme) === 0) out.themes.push({ id: t.id, english: str(t.english), chinese: str(t.chinese), color: str(t.color) || COLORS[0] });
    });
    ['words', 'phrases'].forEach(function (kind) {
      var prefix = PREFIX[kind === 'words' ? 'word' : 'phrase'];
      (Array.isArray(d[kind]) ? d[kind] : []).forEach(function (w) {
        if (!w || !ID.test(w.id) || w.id.indexOf(prefix) !== 0 || typeof w.image !== 'string') return;
        var item = { id: w.id, english: str(w.english), chinese: str(w.chinese), image: w.image };
        if (w.image === 'idb' && PHOTO_KEY.test(w.photo)) item.photo = w.photo;
        if (kind === 'words') item.theme = str(w.theme);
        out[kind].push(item);
      });
    });
    return { data: out, broken: false };
  }

  // Read a backup file. builtIn: {words, phrases, themes, gallery}; current:
  // this device's list. Returns {ok:false, error} or {ok:true, doc} where doc
  // holds the checked themes, words and phrases (photos still to be decoded).
  function readBackup(text, builtIn, current) {
    var bad = function (why) { return { ok: false, error: why }; };
    var d;
    try { d = JSON.parse(text); } catch (e) { return bad('這個檔案打不開（不是 JSON 格式）。'); }
    if (!d || typeof d !== 'object' || d.format !== FORMAT) return bad('這不是「看圖學英文」的備份檔。');
    if (typeof d.version !== 'number' || d.version > VERSION) return bad('這個備份檔是比較新的版本，請先更新遊戲再匯入。');
    var themes = Array.isArray(d.themes) ? d.themes : [], words = Array.isArray(d.words) ? d.words : [], phrases = Array.isArray(d.phrases) ? d.phrases : [];
    if (!Array.isArray(d.words) && !Array.isArray(d.phrases)) return bad('備份檔裡沒有單字或句子。');
    if (themes.length + words.length + phrases.length > MAX_ITEMS * 3) return bad('備份檔太大了。');
    var gallery = builtIn.gallery || [];
    var themeIds = (builtIn.themes || []).map(function (t) { return t.id; }).concat((current.themes || []).map(function (t) { return t.id; }));
    var doc = { themes: [], words: [], phrases: [] }, seen = {};
    var label = function (kind, i, item) { return kind + ' 第 ' + (i + 1) + ' 筆' + (item && item.english ? '（' + tidy(item.english) + '）' : '') + '：'; };
    var problem = null;
    themes.some(function (t, i) {
      var why = !t || typeof t !== 'object' ? '格式不對。'
        : !ID.test(t.id) || t.id.indexOf(PREFIX.theme) !== 0 ? 'id 要以 my_theme_ 開頭。'
        : seen[t.id] ? 'id 重複了。' : checkTheme(t);
      if (why) { problem = label('主題', i, t) + why; return true; }
      seen[t.id] = true;
      themeIds.push(t.id);
      doc.themes.push({ id: t.id, english: tidy(t.english), chinese: tidy(t.chinese), color: /^#[0-9a-fA-F]{6}$/.test(t.color) ? t.color : COLORS[i % COLORS.length] });
      return false;
    });
    if (problem) return bad(problem);
    [['words', '單字', 'word', checkWord], ['phrases', '句子', 'phrase', checkPhrase]].some(function (row) {
      var list = row[0] === 'words' ? words : phrases;
      var english = {};
      return list.some(function (w, i) {
        var why = !w || typeof w !== 'object' ? '格式不對。'
          : !ID.test(w.id) || w.id.indexOf(PREFIX[row[2]]) !== 0 ? 'id 要以 ' + PREFIX[row[2]] + ' 開頭。'
          : seen[w.id] ? 'id 重複了。'
          : english[lower(w.english)] ? '英文和同一個檔案裡的另一筆重複了。'
          : row[3](w, { themes: themeIds, gallery: gallery, needImage: true });
        if (why) { problem = label(row[1], i, w) + why; return true; }
        seen[w.id] = true;
        english[lower(w.english)] = true;
        var item = { id: w.id, english: tidy(w.english), chinese: tidy(w.chinese), image: w.image };
        if (row[0] === 'words') item.theme = w.theme;
        doc[row[0]].push(item);
        return false;
      });
    });
    if (problem) return bad(problem);
    return { ok: true, doc: doc };
  }

  // Put a checked backup into the current list. Same id: replaced. Same
  // English as a built-in item, or as another of this device's items:
  // skipped (it is already here). Returns {next, added, updated, skipped,
  // clash}; clash is a message when an item would share a picture with
  // another one (the import is then refused as a whole).
  function mergeBackup(current, doc, builtIn) {
    var next = JSON.parse(JSON.stringify(current));
    var res = { next: next, added: 0, updated: 0, skipped: [], clash: null };
    var usedThemes = {};
    ['words', 'phrases'].forEach(function (kind) {
      var taken = {};
      (builtIn[kind] || []).forEach(function (w) { taken[lower(w.english)] = 'builtin'; });
      next[kind].forEach(function (w) { taken[lower(w.english)] = w.id; });
      doc[kind].forEach(function (w) {
        var owner = taken[lower(w.english)];
        if (owner && owner !== w.id) { res.skipped.push(w.english); return; }
        var at = -1;
        next[kind].forEach(function (x, i) { if (x.id === w.id) at = i; });
        var item = JSON.parse(JSON.stringify(w));
        if (at >= 0) {
          delete taken[lower(next[kind][at].english)];
          next[kind][at] = item;
          res.updated++;
        } else {
          next[kind].push(item);
          res.added++;
        }
        taken[lower(w.english)] = w.id;
        if (item.theme) usedThemes[item.theme] = true;
      });
      if (res.clash) return;
      var all = (builtIn[kind] || []).concat(next[kind]);
      doc[kind].forEach(function (w) {
        if (res.clash || !next[kind].some(function (x) { return x.id === w.id && x.image === w.image; })) return;
        res.clash = sharedPicture(w, { used: usedPictures(all, w.id) });
        if (res.clash) res.clash = '「' + w.english + '」：' + res.clash;
      });
    });
    doc.themes.forEach(function (t) {
      if (!usedThemes[t.id]) return;
      var at = -1;
      next.themes.forEach(function (x, i) { if (x.id === t.id) at = i; });
      if (at >= 0) next.themes[at] = JSON.parse(JSON.stringify(t));
      else next.themes.push(JSON.parse(JSON.stringify(t)));
    });
    return res;
  }

  // Custom themes nobody uses any more.
  function unusedThemes(list) {
    return list.themes.filter(function (t) {
      return !list.words.some(function (w) { return w.theme === t.id; });
    }).map(function (t) { return t.id; });
  }

  var lib = {
    KEY: KEY, FORMAT: FORMAT, VERSION: VERSION, PREFIX: PREFIX, COLORS: COLORS, MAX_TOKENS: MAX_TOKENS,
    tidy: tidy, tokens: tokens, slug: slug, makeId: makeId, isPicture: isPicture, checkWord: checkWord,
    checkPhrase: checkPhrase, checkTheme: checkTheme, parseList: parseList, readBackup: readBackup,
    mergeBackup: mergeBackup, unusedThemes: unusedThemes, usedPictures: usedPictures, empty: empty
  };
  if (typeof module !== 'undefined' && module.exports) { module.exports = lib; return; }

  // ---------- browser: this device's storage
  var list = empty();     // what is saved (images: path, "idb" or inline data URL)
  var raw = null;         // the saved text `list` was read from
  var photos = {};        // photo key -> data URL of a photo kept in IndexedDB
  var db = null;          // IndexedDB, or null when not available
  var stale = {};         // ids whose old progress could not be dropped yet: not reused
  var listeners = [];     // Custom.onChange()

  function clone(x) { return JSON.parse(JSON.stringify(x)); }

  function openDb() {
    return new Promise(function (ok) {
      try {
        var r = indexedDB.open('picture-words', 1);
        r.onupgradeneeded = function () { r.result.createObjectStore('photos'); };
        r.onsuccess = function () { ok(r.result); };
        r.onerror = r.onblocked = function () { ok(null); };
      } catch (e) { ok(null); }
    });
  }

  // One IndexedDB transaction. A request's success is not enough: the data is
  // stored only when the transaction completes; an error or abort rejects.
  function tx(mode, work) {
    return new Promise(function (ok, fail) {
      if (!db) { fail(new Error('no IndexedDB')); return; }
      var t;
      try { t = db.transaction('photos', mode); work(t.objectStore('photos')); } catch (e) { fail(e); return; }
      t.oncomplete = function () { ok(); };
      t.onerror = function () { fail(t.error || new Error('IndexedDB error')); };
      t.onabort = function () { fail(t.error || new Error('IndexedDB aborted')); };
    });
  }

  // Photos written before the list said where they are use the item's id.
  function keyOf(item) { return item.photo || item.id; }
  function photoKeys(l) {
    return l.words.concat(l.phrases).filter(function (w) { return w.image === 'idb'; }).map(keyOf);
  }

  function dropPhotos(keys) {
    keys.forEach(function (k) { delete photos[k]; });
    if (!db || !keys.length) return Promise.resolve();
    // One that cannot be dropped only takes space: no list points to it.
    return tx('readwrite', function (s) { keys.forEach(function (k) { s.delete(k); }); }).catch(function () {});
  }

  // Read the photos the list uses that are not in memory yet.
  function loadPhotos() {
    var wanted = photoKeys(list).filter(function (k) { return !photos[k]; });
    if (!db || !wanted.length) return Promise.resolve();
    var got = {};
    return tx('readonly', function (s) {
      wanted.forEach(function (k) { var r = s.get(k); r.onsuccess = function () { if (r.result) got[k] = r.result; }; });
    }).then(function () { Object.assign(photos, got); }, function () { /* missing: placeholders */ });
  }

  function readRaw() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; } /* blocked: start empty */
  }

  function adopt(text, keepBroken) {
    var res = parseList(text);
    if (res.broken && keepBroken) { try { localStorage.setItem(BROKEN_KEY, String(text)); } catch (e) { /* ignore */ } }
    list = res.data;
    raw = text;
  }

  function idsOf(l) {
    return l.themes.concat(l.words, l.phrases).map(function (x) { return x.id; });
  }

  // Ids a new item must not take: in the list, or still holding old progress.
  function takenIds(l) {
    var ids = idsOf(l).concat(Object.keys(stale));
    if (root.Progress) {
      var p = Progress.snapshot();
      ids = ids.concat(Object.keys(p.words), Object.keys(p.best));
    }
    return ids;
  }

  // Progress of parent items that are gone (a delete whose progress write
  // failed, or one made in another tab) is dropped when the game opens.
  function tidyProgress() {
    if (!root.Progress) return;
    var saved = parseList(readRaw());
    if (saved.broken) return;   // the list may yet be recovered from ew.custom.broken
    var have = {};
    idsOf(saved.data).forEach(function (id) { have[id] = true; });
    var p = Progress.snapshot();
    var gone = function (id) { return ID.test(id) && !have[id]; };
    var ids = Object.keys(p.words).filter(gone), themes = Object.keys(p.best).filter(gone);
    if (!ids.length && !themes.length) return;
    if (Progress.forget(ids, themes)) stale = {};
    else ids.forEach(function (id) { stale[id] = true; });
  }

  function load() {
    adopt(readRaw(), true);
    return openDb().then(function (d) {
      db = d;
      return loadPhotos();
    }).catch(function () { /* no photos: placeholders */ }).then(function () {
      tidyProgress();
      return list;
    });
  }

  // Another tab saved: take its list and photos, then let the page redraw.
  if (root.addEventListener) {
    root.addEventListener('storage', function (e) {
      if (e.key !== KEY && e.key !== null) return;
      var text = readRaw();
      if (text === raw) return;
      adopt(text);
      loadPhotos().then(function () { listeners.forEach(function (fn) { fn(); }); });
    });
  }

  var PLACEHOLDER = 'icons/icon.svg';
  function picture(item) {
    if (item.image === 'idb') return photos[keyOf(item)] || PLACEHOLDER;
    return item.image || PLACEHOLDER;
  }

  // Lists in the shape of data/*.json, with pictures ready to show.
  function view() {
    var words = list.words.map(function (w) {
      return { id: w.id, english: w.english, chinese: w.chinese, theme: w.theme, image: picture(w), custom: true };
    });
    var phrases = list.phrases.map(function (p) {
      return { id: p.id, english: p.english, chinese: p.chinese, category: 'custom', image: picture(p), custom: true };
    });
    var themes = list.themes.map(function (t) {
      var first = words.filter(function (w) { return w.theme === t.id; })[0];
      return { id: t.id, english: t.english, chinese: t.chinese, color: t.color, icon: first ? first.image : PLACEHOLDER, custom: true };
    });
    return { words: words, phrases: phrases, themes: themes };
  }

  // Make one change to the saved list. build(list) changes the copy it is
  // given and returns it, or throws an Error with a message for the parent.
  // pictures: new photos (data URLs) that build may put in items' image.
  // Each photo is stored under a new key first; then build runs again on the
  // list as saved right now if another tab saved meanwhile, and the list is
  // written in one go. Only after that are photos nobody uses dropped, so a
  // failure anywhere leaves the old list and old photos as they were.
  function change(build, pictures) {
    var text = readRaw();
    if (text !== raw) adopt(text);
    var next;
    try { next = build(clone(list)); } catch (e) { return Promise.reject(e); }
    var keys = {};
    pictures = pictures.filter(function (d, i) { return pictures.indexOf(d) === i; });   // one key per photo
    return Promise.all(pictures.map(function (data, i) {
      var key = 'photo_' + Date.now().toString(36) + i + Math.random().toString(36).slice(2, 8);
      // Not stored: the photo stays inline in the list.
      return tx('readwrite', function (s) { s.put(data, key); }).then(function () { keys[data] = key; }, function () {});
    })).then(function () {
      var fresh = Object.keys(keys).map(function (d) { return keys[d]; });
      var fail = function (err) { dropPhotos(fresh); throw err; };
      text = readRaw();
      if (text !== raw) {
        adopt(text);
        try { next = build(clone(list)); } catch (e) { return fail(e); }
      }
      next.words.concat(next.phrases).forEach(function (w) {
        if (keys[w.image]) { w.photo = keys[w.image]; w.image = 'idb'; }
      });
      var out = JSON.stringify(next);
      try { localStorage.setItem(KEY, out); } catch (e) { return fail(new Error('這台裝置的儲存空間不夠，沒有存起來。')); }
      Object.keys(keys).forEach(function (d) { photos[keys[d]] = d; });
      var used = photoKeys(next);
      var unused = photoKeys(list).concat(fresh).filter(function (k) { return used.indexOf(k) < 0; });
      list = next;
      raw = out;
      return dropPhotos(unused);
    });
  }

  // Pictures other items of one kind show: {picture: english}; photos too.
  function shown(items) {
    return usedPictures(items.map(function (x) {
      return { id: x.id, english: x.english, image: x.image === 'idb' ? photos[keyOf(x)] : x.image };
    }));
  }

  // item: {id?, english, chinese, theme | newTheme: {chinese, english}}.
  // image: a data URL (new photo), a built-in path, or null to keep the old one.
  function save(kind, item, image, builtIn) {
    var key = kind === 'word' ? 'words' : 'phrases';
    var w, unused;
    return change(function (next) {
      var old = item.id ? next[key].filter(function (x) { return x.id === item.id; })[0] : null;
      w = { id: old ? old.id : '', english: tidy(item.english), chinese: tidy(item.chinese), image: image || (old && old.image) || '' };
      if (!image && old && old.photo) w.photo = old.photo;
      var problem;
      if (kind === 'word') {
        w.theme = item.theme;
        if (item.newTheme) {
          problem = checkTheme(item.newTheme);
          if (problem) throw new Error(problem);
          var t = { id: makeId('theme', item.newTheme.english || 'theme', takenIds(next)), english: tidy(item.newTheme.english), chinese: tidy(item.newTheme.chinese), color: COLORS[next.themes.length % COLORS.length] };
          next.themes.push(t);
          w.theme = t.id;
        }
      }
      var others = (builtIn[key] || []).concat(next[key]).filter(function (x) { return x.id !== w.id; });
      var ctx = {
        themes: (builtIn.themes || []).concat(next.themes).map(function (t) { return t.id; }),
        gallery: builtIn.gallery, taken: others.map(function (x) { return lower(x.english); }), used: shown(others),
        // An edit keeping its photo (stored as "idb") needs no new picture.
        needImage: !(old && !image)
      };
      problem = (kind === 'word' ? checkWord : checkPhrase)(w, ctx);
      if (problem) throw new Error(problem);
      if (!old) w.id = makeId(kind, w.english, takenIds(next));
      if (old) next[key] = next[key].map(function (x) { return x.id === w.id ? w : x; });
      else next[key].push(w);
      unused = unusedThemes(next);
      next.themes = next.themes.filter(function (t) { return unused.indexOf(t.id) < 0; });
      return next;
    }, image && PHOTO.test(image) ? [image] : []).then(function () {
      if (unused.length && root.Progress) Progress.forget([], unused);
      return w;
    });
  }

  // Rejects with err.removed = true when the item is gone but its progress
  // could not be written; it is dropped again the next time the game opens.
  function remove(kind, id) {
    var key = kind === 'word' ? 'words' : 'phrases';
    var unused;
    return change(function (next) {
      next[key] = next[key].filter(function (w) { return w.id !== id; });
      unused = unusedThemes(next);
      next.themes = next.themes.filter(function (t) { return unused.indexOf(t.id) < 0; });
      return next;
    }, []).then(function () {
      if (!root.Progress || Progress.forget([id], unused)) return;
      stale[id] = true;
      var err = new Error('學習紀錄沒有清掉（這台裝置的儲存空間不夠），下次打開遊戲時會再清一次。');
      err.removed = true;
      throw err;
    });
  }

  // The backup: like data/words.json and data/phrases.json, photos inline.
  function backup() {
    var full = function (w) { var x = clone(w); x.image = picture(w); delete x.photo; return x; };
    return {
      format: FORMAT, version: VERSION, exported: new Date().toISOString(),
      note: 'Picture Words: words and phrases a parent added on one device. See ADDING_WORDS.md (section "From a parent backup").',
      themes: list.themes.map(clone),
      words: list.words.map(full),
      phrases: list.phrases.map(full).map(function (p) { p.category = 'custom'; return p; })
    };
  }

  // Import: check everything, decode and shrink every photo, then save in one go.
  // shrink(dataUrl) -> Promise<dataUrl> (js/parent.js, canvas). Resolves
  // {added, updated, skipped}; rejects with a Chinese message, nothing changed.
  function restore(text, builtIn, shrink) {
    var now = readRaw();
    if (now !== raw) adopt(now);
    var res = readBackup(text, builtIn, list);
    if (!res.ok) return Promise.reject(new Error(res.error));
    var doc = res.doc;
    var items = doc.words.concat(doc.phrases).filter(function (w) { return PHOTO.test(w.image); });
    var counts, unused;
    return Promise.all(items.map(function (w) {
      return shrink(w.image).then(function (small) { w.image = small; }, function () {
        throw new Error('「' + w.english + '」的圖片壞掉了，打不開。');
      });
    })).then(function () {
      return change(function (next) {
        var merged = mergeBackup(next, doc, builtIn);
        if (merged.clash) throw new Error(merged.clash);
        unused = unusedThemes(merged.next);
        merged.next.themes = merged.next.themes.filter(function (t) { return unused.indexOf(t.id) < 0; });
        counts = { added: merged.added, updated: merged.updated, skipped: merged.skipped };
        return merged.next;
      }, items.map(function (w) { return w.image; }));
    }).then(function () {
      if (unused.length && root.Progress) Progress.forget([], unused);
      return counts;
    });
  }

  root.Custom = Object.assign({
    load: load, view: view, list: function () { return clone(list); },
    saveWord: function (item, image, builtIn) { return save('word', item, image, builtIn); },
    savePhrase: function (item, image, builtIn) { return save('phrase', item, image, builtIn); },
    remove: remove, backup: backup, restore: restore,
    // Pictures items of one kind already show (the gallery leaves them out).
    shown: function (kind, exceptId) {
      return shown(list[kind === 'word' ? 'words' : 'phrases'].filter(function (x) { return x.id !== exceptId; }));
    },
    onChange: function (fn) { listeners.push(fn); },
    hasDb: function () { return !!db; }
  }, { lib: lib });
})(this);
