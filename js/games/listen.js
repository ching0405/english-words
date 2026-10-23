// 聽音找圖 Listen & find: hear a word, tap its picture among four.
(function () {
  'use strict';

  Games.register({
    id: 'listen',
    zh: '聽音找圖',
    en: 'Listen & find',
    icon: '#g-listen',
    color: '#ffe08a',
    intro: 'intro.listen',
    start: function (api) {
      var qs = api.targets ? Quiz.questionsFor(api.targets, api.words, 4, api.rand)
        : Quiz.questions({ words: api.words, themeId: api.themeId, count: 6, choices: 4, rand: api.rand });
      var grid = api.el('div', 'choices');
      api.stage.appendChild(grid);
      api.dots(qs.length);
      var i = 0, locked = false, missed = false;
      // Words missed in this round are asked once more at the end (only once).
      // missedAt: question index of the first miss; askedAfter: the word came
      // back later in the round anyway (small themes repeat words), which
      // already was its second try.
      var missedWords = [], missedAt = {}, askedAfter = {}, rightFirst = [];

      function ask(first) {
        var q = qs[i];
        if (q.target.id in missedAt && missedAt[q.target.id] < i) askedAfter[q.target.id] = true;
        api.setQ(i);
        grid.textContent = '';
        q.options.forEach(function (w) {
          var b = api.picture(w);
          b.addEventListener('click', function () { pick(b, w); });
          grid.appendChild(b);
        });
        api.onReplay(function () { api.word(q.target); });
        locked = false;
        missed = false;
        api.word(q.target, { queue: first === true });
      }

      function pick(b, w) {
        var q = qs[i];
        if (locked || b.classList.contains('is-wrong')) return;
        if (w.id === q.target.id) {
          locked = true;
          // Right first time counts as known; after a miss it only counts as practice.
          api.record(q.target, missed ? 'seen' : 'right');
          if (!missed) rightFirst.push(q.target);
          b.classList.add('is-right');
          api.dot(i);
          api.right(b, function () {
            i++;
            if (i < qs.length) { ask(); return; }
            var last = qs[qs.length - 1].target;
            var again = missedWords.filter(function (mw) { return !askedAfter[mw.id]; });
            // Never the same word twice in a row: the last question's word goes last.
            if (again.length > 1 && again[0] === last) again.push(again.shift());
            // Only word to ask again was just missed in the last question: put an
            // easy word the child got right in between (a quick success, and not
            // the same question twice in a row). It is not recorded.
            var bridge = null;
            if (again.length === 1 && again[0] === last) {
              bridge = rightFirst.filter(function (w) { return w !== last; }).pop() || null;
            }
            api.askAgain(again, qs.length, function () { api.finish(1, 3); }, { bridge: bridge });
          });
        } else {
          b.classList.add('is-wrong'); // fades so the child can try the others
          if (!missed) {
            api.record(q.target, 'wrong');
            if (missedWords.indexOf(q.target) < 0) { missedWords.push(q.target); missedAt[q.target.id] = i; }
          }
          missed = true;
          api.wrong(b, q.target);
        }
      }

      ask(true);
    }
  });
})();
