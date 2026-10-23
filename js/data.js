// Data and settings shared by every mode. Word cards (phase 1) and the word
// games (phase 2) use data/words.json + data/themes.json; later modes (e.g.
// phase 4 phrases, data/phrases.json) load their own file with Data.getJSON
// and use Speech for pronunciation.
(function () {
  'use strict';

  var SETTINGS_KEY = 'ew.settings.v1';
  var DEFAULTS = { showEnglish: true, showChinese: false, music: true };

  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
  }

  function loadWords() {
    return Promise.all([getJSON('data/words.json'), getJSON('data/themes.json')]).then(function (res) {
      return { words: res[0], themes: res[1] };
    });
  }

  // Chinese voice lines: key -> text from data/voice-zh.json plus every
  // theme name as "theme.<id>" (the same keys tools/gen-voice.py records).
  // A missing file only loses the TTS fallback text, so it never blocks.
  function loadVoiceLines(themes) {
    return getJSON('data/voice-zh.json').catch(function () { return {}; }).then(function (lines) {
      (themes || []).forEach(function (t) { lines['theme.' + t.id] = t.chinese; });
      return lines;
    });
  }

  // Words of one theme in list order; no theme id means every word.
  function wordsInTheme(words, themeId) {
    return words.filter(function (w) { return !themeId || w.theme === themeId; });
  }

  // Parent settings on this device. Unknown or broken data falls back to defaults.
  var settings = {
    load: function () {
      var s = {};
      try { s = JSON.parse(localStorage.getItem(SETTINGS_KEY)) || {}; } catch (e) { /* private mode or bad JSON */ }
      var out = {};
      Object.keys(DEFAULTS).forEach(function (k) {
        out[k] = typeof s[k] === typeof DEFAULTS[k] ? s[k] : DEFAULTS[k];
      });
      return out;
    },
    save: function (s) {
      try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(s)); } catch (e) { /* ignore */ }
    }
  };

  window.Data = { getJSON: getJSON, loadWords: loadWords, loadVoiceLines: loadVoiceLines, wordsInTheme: wordsInTheme, settings: settings };
})();
