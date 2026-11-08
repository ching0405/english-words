// Word range (Tim 2026-11-06): which themes the games, today's review and the
// sticker book use. The theme cards (word-card browsing) always show every
// theme (Tim 2026-11-07). Chosen by a grown-up on the settings screen
// (js/settings.js); the child's screens never change it.
//
// Saved as the themes that are OFF, so a theme added later (docs/ADD_CONTENT.md)
// is on by default, and a new device has every theme on ("全部").
//
//   Scope.load(storage)              {off: [themeIds]} (bad data -> nothing off)
//   Scope.save(storage, s)           false when it could not be written
//   Scope.words(words, s)            the words in range; never empty: when the
//                                    setting would leave nothing, every word
//   Scope.themes(themes, words, s)   themes in range that have words
//   Scope.canTurnOff(themes, words, s, id)  false when fewer than 2 words would stay on
// Works in the browser (window.Scope) and in Node (tools/test_scope.cjs).
(function (root) {
  'use strict';

  var KEY = 'ew.scope.v1';

  function clean(s) {
    var off = s && Array.isArray(s.off) ? s.off.filter(function (id) { return typeof id === 'string' && id; }) : [];
    return { off: off.filter(function (id, i) { return off.indexOf(id) === i; }) };
  }

  function load(storage) {
    try { return clean(JSON.parse(storage.getItem(KEY))); } catch (e) { return clean(null); }
  }

  function save(storage, s) {
    try { storage.setItem(KEY, JSON.stringify(clean(s))); return true; } catch (e) { return false; }
  }

  function isOn(s, themeId) { return clean(s).off.indexOf(themeId) < 0; }

  function words(all, s) {
    var on = all.filter(function (w) { return isOn(s, w.theme); });
    return on.length ? on : all.slice();
  }

  function themes(allThemes, all, s) {
    var inRange = words(all, s);
    return allThemes.filter(function (t) { return inRange.some(function (w) { return w.theme === t.id; }); });
  }

  // A grown-up may not switch off the last themes: at least MIN_WORDS words
  // stay on, so every game still has a choice to make (two pictures).
  var MIN_WORDS = 2;
  function canTurnOff(allThemes, all, s, themeId) {
    if (!isOn(s, themeId)) return true;
    var c = clean(s);
    var left = all.filter(function (w) { return w.theme !== themeId && c.off.indexOf(w.theme) < 0; });
    return left.length >= MIN_WORDS;
  }

  function toggle(s, themeId) {
    var c = clean(s);
    var i = c.off.indexOf(themeId);
    if (i >= 0) c.off.splice(i, 1); else c.off.push(themeId);
    return c;
  }

  var Scope = { KEY: KEY, load: load, save: save, isOn: isOn, words: words, themes: themes, canTurnOff: canTurnOff, MIN_WORDS: MIN_WORDS, toggle: toggle, clean: clean };
  if (typeof module !== 'undefined' && module.exports) module.exports = Scope;
  else root.Scope = Scope;
})(this);
