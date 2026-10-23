// 翻牌記憶 Memory: flip cards (each says its word) and find matching pairs.
(function () {
  'use strict';

  var PAIRS = 6;

  Games.register({
    id: 'memory',
    zh: '翻牌記憶',
    en: 'Memory',
    icon: '#g-memory',
    color: '#ffc9de',
    intro: 'intro.memory',
    start: function (api) {
      var words = api.targets ? api.targets.slice(0, PAIRS)
        : Quiz.pick({ words: api.words, themeId: api.themeId, count: PAIRS, rand: api.rand });
      var deck = Quiz.shuffle(words.concat(words), api.rand);
      var board = api.el('div', 'memory');
      board.dataset.cards = String(deck.length);
      api.stage.appendChild(board);
      api.dots(words.length);
      api.setQ(0);
      api.onReplay(function () { api.zh('intro.memory'); });
      var open = [], found = 0, busy = false;
      // Only a wrong pair blocks taps (while it turns back); data-busy is for tests.
      function setBusy(on) { busy = on; board.dataset.busy = on ? '1' : '0'; }
      setBusy(false);

      deck.forEach(function (w) {
        var c = api.el('button', 'mcard', { type: 'button', 'aria-label': '卡片 card' });
        c.dataset.word = w.id;
        var face = api.el('span', 'mcard-face');
        face.appendChild(api.el('img', '', { src: w.image, alt: '', draggable: 'false' }));
        var back = api.el('span', 'mcard-back');
        back.appendChild(api.icon('#i-star', 'mcard-star'));
        c.append(back, face);
        c.addEventListener('click', function () { flip(c, w); });
        board.appendChild(c);
      });

      function flip(c, w) {
        // While a wrong pair turns back, a tapped card rocks a little (no flip)
        // so the child sees the tap was noticed.
        if (busy) { if (!c.classList.contains('is-done')) Fx.move(c, 'wiggle'); return; }
        if (c.classList.contains('is-open')) return;
        c.classList.add('is-open');
        c.setAttribute('aria-label', w.english);
        Fx.sound('flip');
        api.word(w);
        // Memory is about places, not knowing the word: flips count as practice only.
        api.record(w, 'seen');
        open.push({ c: c, w: w });
        if (open.length < 2) return;
        var a = open[0], b = open[1];
        open = [];
        if (a.w.id === b.w.id) {
          a.c.classList.add('is-done');
          b.c.classList.add('is-done');
          api.dot(found);
          found++;
          api.setQ(found);
          var all = found === words.length;
          // Let the word finish, then praise. Play can go on meanwhile.
          api.later(700, function () {
            Fx.move(a.c, 'cheer');
            api.right(b.c, function () { if (all) api.finish(4, 9); });
          });
        } else {
          setBusy(true);
          api.miss();
          api.later(1300, function () {
            [a.c, b.c].forEach(function (x) { x.classList.remove('is-open'); x.setAttribute('aria-label', '卡片 card'); });
            setBusy(false);
          });
        }
      }
    }
  });
})();
