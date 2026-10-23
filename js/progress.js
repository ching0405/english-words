// Learning progress per word, kept on this device (localStorage), with a
// simple spaced-review schedule (Leitner boxes on calendar days).
//
//   seen(id)          the child looked at / heard the word (cards, memory flips)
//   played(id)        the word was in a game round (theme stars need play, not just looking)
//   answer(id, ok)    a listen-and-pick answer: right moves a due word up a box,
//                     wrong sends it back to box 0, due tomorrow
//   due(words)        words waiting for review now, most urgent first
//   reviewSet(words, n)  n words for "today's review": due words first, then
//                     the least known; {due: [...], list: [...]}
//   themeStars(words, themeId)  0–3 stars for a theme from games only; never goes down
//   addJarStars(n)    put a round's stars in the star jar; {jar, filled}
//   nextReviewMode()  the play mode for today's review, taking turns
//   forget(ids, themeIds)  drop the records of deleted (parent-made) words;
//                     false when the save could not be written
//
// Due dates are local midnights ("tomorrow" = next calendar day at 0:00), so a
// word seen at 19:00 is ready first thing the next day. Clock changes are
// guarded: a date in the future beyond what its box allows is pulled back, so
// moving the device clock never hides a word for a year or breaks the save.
// Records are keyed by word id, so adding or removing words never touches the
// other words. The save carries a version; older saves are migrated, broken
// ones are kept aside (ew.progress.broken) and replaced by a fresh start.
// Works in the browser (window.Progress) and in Node (tools/test_progress.cjs):
// Progress.create(storage, now) takes any localStorage-like object and clock.
(function (root) {
  'use strict';

  var KEY = 'ew.progress';
  var BROKEN_KEY = 'ew.progress.broken';
  var VERSION = 3;
  var DAY = 24 * 60 * 60 * 1000;
  // Calendar days until the next review for each box. Box 0 = just met or just missed.
  var INTERVALS = [1, 1, 2, 4, 8, 16];
  var MAX_BOX = INTERVALS.length - 1;
  var KNOWN_BOX = 2;              // box 2+ counts as "known" for theme stars
  var JAR_SIZE = 12;              // stars that fill one star jar
  var REVIEW_MODES = ['listen', 'match', 'memory', 'cards'];

  // Older save formats -> next version.
  var MIGRATIONS = {
    // v1 kept plain counters per word.
    1: function (old) {
      var words = {};
      Object.keys(old.seen || {}).concat(Object.keys(old.right || {}), Object.keys(old.wrong || {})).forEach(function (id) {
        if (words[id]) return;
        var right = num(old.right && old.right[id]), wrong = num(old.wrong && old.wrong[id]);
        var last = num(old.last && old.last[id]);
        // No schedule was kept: start each word in the box its record earns.
        var box = Math.max(0, Math.min(MAX_BOX, right - wrong));
        words[id] = { seen: num(old.seen && old.seen[id]), right: right, wrong: wrong, last: last, box: box, due: dayAfter(last, INTERVALS[box]) };
      });
      return { version: 2, words: words };
    },
    // v3 adds best theme stars, the star jar and the review turn.
    2: function (old) {
      return { version: 3, words: old.words, best: {}, jar: { stars: 0, full: 0 }, reviewTurn: 0 };
    }
  };

  function num(v) { return typeof v === 'number' && isFinite(v) && v >= 0 ? v : 0; }

  // Local midnight `n` calendar days after time t (handles daylight saving).
  function dayAfter(t, n) {
    var d = new Date(t);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + n);
    return d.getTime();
  }

  function fresh() { return { version: VERSION, words: {}, best: {}, jar: { stars: 0, full: 0 }, reviewTurn: 0 }; }

  // Keep only well-formed data; drop anything else.
  function clean(data) {
    var out = fresh();
    var words = data && data.words;
    if (!words || typeof words !== 'object' || Array.isArray(words)) return null;
    Object.keys(words).forEach(function (id) {
      var r = words[id];
      if (!r || typeof r !== 'object') return;
      out.words[id] = {
        seen: num(r.seen), right: num(r.right), wrong: num(r.wrong), played: num(r.played), last: num(r.last),
        box: Math.min(MAX_BOX, Math.floor(num(r.box))), due: num(r.due)
      };
    });
    var best = data.best && typeof data.best === 'object' ? data.best : {};
    Object.keys(best).forEach(function (k) { out.best[k] = Math.min(3, Math.floor(num(best[k]))); });
    var jar = data.jar && typeof data.jar === 'object' ? data.jar : {};
    var stars = Math.floor(num(jar.stars));
    out.jar = { stars: stars % JAR_SIZE, full: Math.floor(num(jar.full)) + Math.floor(stars / JAR_SIZE) };
    out.reviewTurn = Math.floor(num(data.reviewTurn)) % REVIEW_MODES.length;
    return out;
  }

  // Parse, migrate and check a saved string. Returns {data, broken}.
  function parse(raw) {
    if (raw === null || raw === undefined) return { data: fresh(), broken: false };
    var data;
    try { data = JSON.parse(raw); } catch (e) { return { data: fresh(), broken: true }; }
    if (!data || typeof data !== 'object' || typeof data.version !== 'number') return { data: fresh(), broken: true };
    if (data.version > VERSION) return { data: fresh(), broken: true }; // from a newer app: do not guess
    while (data.version < VERSION) {
      var step = MIGRATIONS[data.version];
      if (!step) return { data: fresh(), broken: true };
      try { data = step(data); } catch (e) { return { data: fresh(), broken: true }; }
    }
    var ok = clean(data);
    return ok ? { data: ok, broken: false } : { data: fresh(), broken: true };
  }

  function create(storage, now) {
    now = now || function () { return Date.now(); };
    var store = storage;
    var data = null;

    // False when the save could not be written (full or blocked: kept in memory).
    function save() {
      try { store.setItem(KEY, JSON.stringify(data)); return true; } catch (e) { return false; }
    }

    // Clock guard: nothing may sit further in the future than its box allows
    // from today. Returns true when something was pulled back.
    function guard(t) {
      var changed = false;
      Object.keys(data.words).forEach(function (id) {
        var r = data.words[id];
        if (r.last > t) { r.last = t; changed = true; }
        if (r.due && r.due > dayAfter(t, INTERVALS[r.box] + 1)) { r.due = dayAfter(t, INTERVALS[r.box]); changed = true; }
      });
      return changed;
    }

    function load() {
      var raw = null;
      try { raw = store.getItem(KEY); } catch (e) { /* storage blocked: work in memory */ }
      var res = parse(raw);
      if (res.broken) {
        try { store.setItem(BROKEN_KEY, String(raw)); } catch (e) { /* ignore */ }
      }
      data = res.data;
      var migrated = !res.broken && raw && JSON.parse(raw).version !== VERSION;
      if (guard(now()) || res.broken || migrated) save();
      return data;
    }

    // Every use starts from a loaded, clock-checked save.
    function ready() {
      if (!data) load();
      else if (guard(now())) save();
      return data;
    }

    function rec(id) {
      ready();
      var r = data.words[id];
      if (!r) r = data.words[id] = { seen: 0, right: 0, wrong: 0, played: 0, last: 0, box: 0, due: 0 };
      return r;
    }

    function get(id) {
      ready();
      return data.words[id] || null;
    }

    function seen(id) {
      var r = rec(id), t = now();
      if (!r.due) r.due = dayAfter(t, 1); // first meeting: review tomorrow
      r.seen++;
      r.last = t;
      save();
    }

    // Tim (phase 9): stars come from playing games, not from looking at cards.
    function played(id) {
      rec(id).played++;
      save();
    }

    function answer(id, ok) {
      var r = rec(id), t = now();
      r.last = t;
      if (ok) {
        r.right++;
        // Only a word that is due (or brand new) moves up; extra right answers
        // before then do not skip boxes.
        if (!r.due || r.due <= t) {
          r.box = Math.min(MAX_BOX, r.box + 1);
          r.due = dayAfter(t, INTERVALS[r.box]);
        }
      } else {
        // Missed: back to the start, ready again tomorrow. (Games ask a missed
        // word once more at the end of the same round.)
        r.wrong++;
        r.box = 0;
        r.due = dayAfter(t, 1);
      }
      save();
    }

    function isDue(id, t) {
      var r = get(id);
      return !!(r && r.due && r.due <= (t || now()));
    }

    function due(words) {
      ready();
      var t = now();
      return words.filter(function (w) { return isDue(w.id, t); }).sort(function (a, b) {
        var ra = get(a.id), rb = get(b.id);
        return ra.box - rb.box || ra.due - rb.due;
      });
    }

    // How well a word is known, for picking practice words: unseen first.
    function strength(id) {
      var r = get(id);
      if (!r) return -1;
      return r.box * 10 + Math.min(9, r.right);
    }

    function reviewSet(words, n) {
      var d = due(words);
      var dueIds = {};
      d.forEach(function (w) { dueIds[w.id] = true; });
      var rest = words.filter(function (w) { return !dueIds[w.id]; })
        .sort(function (a, b) { return strength(a.id) - strength(b.id); });
      return { due: d, list: d.concat(rest).slice(0, n) };
    }

    // Stars a theme has earned now (0 untouched, 1 started, 2 half known, 3 all known).
    function themeLevel(words, themeId) {
      var list = words.filter(function (w) { return w.theme === themeId; });
      if (!list.length) return 0;
      var known = 0, met = 0;
      list.forEach(function (w) {
        var r = get(w.id);
        if (r && (r.played || r.right || r.wrong)) met++;
        if (r && r.box >= KNOWN_BOX) known++;
      });
      if (known === list.length) return 3;
      if (known * 2 >= list.length) return 2;
      return met ? 1 : 0;
    }

    // Only game play counts (played, right, wrong): looking at cards earns no
    // star. Older saves keep their best level (it is never taken back).
    function themeStars(words, themeId) {
      ready();
      var level = themeLevel(words, themeId);
      var best = data.best[themeId] || 0;
      if (level > best) { data.best[themeId] = level; save(); return level; }
      return best;
    }

    // Put a round's stars in the jar. A full jar is put on the shelf and a new
    // empty one starts. Returns {before, jar, filled} for the animation.
    function addJarStars(n) {
      ready();
      var before = { stars: data.jar.stars, full: data.jar.full };
      var total = data.jar.stars + Math.max(0, Math.floor(n || 0));
      data.jar = { stars: total % JAR_SIZE, full: data.jar.full + Math.floor(total / JAR_SIZE) };
      save();
      return { before: before, jar: { stars: data.jar.stars, full: data.jar.full }, filled: data.jar.full > before.full };
    }

    function jar() { ready(); return { stars: data.jar.stars, full: data.jar.full, size: JAR_SIZE }; }

    // Today's review takes turns between play modes.
    function nextReviewMode() {
      ready();
      var mode = REVIEW_MODES[data.reviewTurn % REVIEW_MODES.length];
      data.reviewTurn = (data.reviewTurn + 1) % REVIEW_MODES.length;
      save();
      return mode;
    }

    // A parent deleted their own words (or a whole theme of their own): drop
    // just those records. Every other word, the jar and other themes stay.
    // Returns false when that could not be written, so the caller can say so.
    function forget(ids, themeIds) {
      ready();
      (ids || []).forEach(function (id) { delete data.words[id]; });
      (themeIds || []).forEach(function (id) { delete data.best[id]; });
      return save();
    }

    function clear() {
      data = fresh();
      try { store.removeItem(KEY); } catch (e) { /* ignore */ }
    }

    return {
      load: load, get: get, seen: seen, played: played, answer: answer, isDue: function (id) { return isDue(id); },
      due: due, reviewSet: reviewSet, themeStars: themeStars, addJarStars: addJarStars, jar: jar,
      nextReviewMode: nextReviewMode, forget: forget, clear: clear,
      snapshot: function () { ready(); return JSON.parse(JSON.stringify(data)); }
    };
  }

  var Progress = {
    create: create, parse: parse, dayAfter: dayAfter, VERSION: VERSION, KEY: KEY, BROKEN_KEY: BROKEN_KEY,
    DAY: DAY, INTERVALS: INTERVALS, JAR_SIZE: JAR_SIZE, REVIEW_MODES: REVIEW_MODES
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = Progress;
  } else {
    // Browser: one shared tracker on this device's localStorage.
    var memory = {};
    var storage;
    try { storage = root.localStorage; storage.getItem(KEY); } catch (e) {
      storage = {
        getItem: function (k) { return k in memory ? memory[k] : null; },
        setItem: function (k, v) { memory[k] = String(v); },
        removeItem: function (k) { delete memory[k]; }
      };
    }
    root.Progress = Object.assign(create(storage), { lib: Progress });
  }
})(this);
