// 連連看 Match: speakers on the left say a word; join each to its picture on
// the right, by dragging a line or by tapping the speaker and then the picture.
(function () {
  'use strict';

  var BOARDS = 2, PER_BOARD = 3;
  var COLORS = ['#ff5a5f', '#4fb0ff', '#5ccf6a', '#9b6bff'];
  var SVGNS = 'http://www.w3.org/2000/svg';

  Games.register({
    id: 'match',
    zh: '連連看',
    en: 'Match',
    icon: '#g-match',
    color: '#c9f0c1',
    intro: 'intro.match',
    start: function (api) {
      // Review rounds bring their own words: boards of three in order.
      var boards = api.targets
        ? [api.targets.slice(0, PER_BOARD), api.targets.slice(PER_BOARD, 2 * PER_BOARD)].filter(function (x) { return x.length >= 2; })
        : Quiz.boards({ words: api.words, themeId: api.themeId, boards: BOARDS, perBoard: PER_BOARD, rand: api.rand });
      var total = boards.reduce(function (n, x) { return n + x.length; }, 0);
      api.dots(total);
      // Words missed in the round are asked once more at the end, one
      // listen-and-pick question each (see api.askAgain).
      var missedWords = [];
      var box = api.el('div', 'match');
      api.stage.appendChild(box);
      var b = 0, done = 0, picked = null, lines = [], drag = null, temp = null, svg, missed = {};

      function center(node) {
        var r = node.getBoundingClientRect(), o = box.getBoundingClientRect();
        return { x: r.left - o.left + r.width / 2, y: r.top - o.top + r.height / 2 };
      }

      function path(from, to, color, cls) {
        var g = document.createElementNS(SVGNS, 'g');
        if (cls) g.setAttribute('class', cls);
        var d = 'M' + from.x + ' ' + from.y + ' L' + to.x + ' ' + to.y;
        [['#2b3a55', 18], [color, 10]].forEach(function (s) {
          var p = document.createElementNS(SVGNS, 'path');
          p.setAttribute('d', d);
          p.setAttribute('stroke', s[0]);
          p.setAttribute('stroke-width', s[1]);
          p.setAttribute('stroke-linecap', 'round');
          p.setAttribute('fill', 'none');
          g.appendChild(p);
        });
        svg.appendChild(g);
        return g;
      }

      function redraw() {
        svg.textContent = '';
        lines.forEach(function (l) { path(center(l.a), center(l.b), l.color); });
      }

      function board() {
        missed = {};
        box.textContent = '';
        lines = [];
        picked = null;
        svg = document.createElementNS(SVGNS, 'svg');
        svg.setAttribute('class', 'match-lines');
        svg.setAttribute('aria-hidden', 'true');
        var left = api.el('div', 'match-col'), right = api.el('div', 'match-col');
        boards[b].forEach(function (w) {
          var s = api.el('button', 'btn btn-sun match-say', { type: 'button', 'aria-label': '聽 ' + w.english });
          s.dataset.word = w.id;
          s.appendChild(api.icon('#i-speaker'));
          s.addEventListener('pointerdown', function (e) { startDrag(e, s, w); });
          s.addEventListener('click', function () { if (!s.disabled) choose(s, w); });
          left.appendChild(s);
        });
        Quiz.shuffle(boards[b], api.rand).forEach(function (w) {
          var p = api.picture(w, 'match-pic');
          p.addEventListener('click', function () { join(p, w); });
          right.appendChild(p);
        });
        box.append(left, svg, right);
        api.setQ(done);
        api.onReplay(function () { if (picked) api.word(picked.w); else api.zh('intro.match'); });
      }

      function choose(s, w) {
        if (picked) picked.s.classList.remove('is-picked');
        picked = { s: s, w: w };
        s.classList.add('is-picked');
        api.word(w);
      }

      function join(p, w) {
        if (p.classList.contains('is-done')) return;
        if (!picked) {
          // Picture first: point back to the speakers.
          Fx.move(p, 'shake');
          api.zh('match.speaker_first');
          return;
        }
        if (w.id !== picked.w.id) {
          if (!missed[picked.w.id]) {
            api.record(picked.w, 'wrong');
            if (missedWords.indexOf(picked.w) < 0) missedWords.push(picked.w);
          }
          missed[picked.w.id] = true;
          api.wrong(p, picked.w);
          return;
        }
        api.record(w, missed[w.id] ? 'seen' : 'right');
        var s = picked.s, color = COLORS[lines.length % COLORS.length];
        picked = null;
        s.classList.remove('is-picked');
        s.classList.add('is-done');
        s.disabled = true;
        p.classList.add('is-done');
        p.style.setProperty('--line', color);
        lines.push({ a: s, b: p, color: color });
        redraw();
        api.dot(done);
        done++;
        api.setQ(done);
        Fx.tap(p.querySelector('img'), w);
        api.right(null, function () {
          if (lines.length < boards[b].length) return;
          b++;
          if (b < boards.length) { board(); api.zh('match.next_board'); return; }
          api.askAgain(missedWords, done, function () { api.finish(1, 3); });
        });
      }

      // Drag from a speaker: a line follows the finger; letting go on a picture joins them.
      function startDrag(e, s, w) {
        if (s.disabled) return;
        drag = { s: s, w: w, x: e.clientX, y: e.clientY, moved: false };
        try { s.releasePointerCapture(e.pointerId); } catch (err) { /* touch keeps capture otherwise */ }
      }
      function onMove(e) {
        if (!drag) return;
        if (!drag.moved && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < 12) return;
        if (!drag.moved) { drag.moved = true; choose(drag.s, drag.w); }
        var o = box.getBoundingClientRect();
        if (temp) temp.remove();
        temp = path(center(drag.s), { x: e.clientX - o.left, y: e.clientY - o.top }, '#ffd43b', 'match-temp');
      }
      function onUp(e) {
        if (!drag) return;
        var d = drag;
        drag = null;
        if (temp) { temp.remove(); temp = null; }
        if (!d.moved) return; // a plain tap is handled by click
        var hit = document.elementFromPoint(e.clientX, e.clientY);
        var p = hit && hit.closest('.match-pic');
        if (p) join(p, boards[b].filter(function (w) { return w.id === p.dataset.word; })[0]);
      }
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
      window.addEventListener('resize', redraw);
      api.onStop(function () {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
        window.removeEventListener('resize', redraw);
      });

      board();
    }
  });
})();
