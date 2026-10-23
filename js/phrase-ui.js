// Phrase games (listen, order) and phrase review; feedback, cancellation and
// stars belong to Games. Browsing the phrases is the #cards deck (js/app.js).
(function () {
  'use strict';
  var phrases = [];
  // Order-game tokens get these colours dealt afresh every question, so a
  // colour never tells which word comes first: only listening does.
  var colors = ['#4fb0ff', '#ff9f43', '#ff8fc0', '#9b6bff'];
  var REVIEW_SIZE = 4;

  function zhOn() { return document.body.classList.contains('show-zh'); }

  function definition(mode, targets) {
    return {
      id: 'phrase-' + mode,
      intro: 'phrases.' + mode,
      start: function (api) {
        // Review keeps its priority order (due, then missed); the rest is shuffled.
        var list = mode === 'review' ? targets : PhraseQuiz.round(targets || phrases, Math.random);
        var q = 0;
        api.dots(list.length);

        function end() {
          if (mode !== 'review') { api.finish(100, 100); return; }
          var over = false;
          var go = function () { if (!over && api.alive()) { over = true; api.finish(100, 100); } };
          api.zh('phrases.review_done', { onend: go });
          api.later(6000, go);
        }

        function ask() {
          if (!api.alive()) return;
          if (q === list.length) { end(); return; }
          var phrase = list[q], missed = false, locked = false;
          // True while the prompt (and, first time, the how-to before it) plays:
          // order tokens then only wiggle, so a tap never cuts the sentence off.
          var busy = false;
          api.setQ(q);
          api.stage.textContent = '';
          api.record(phrase, 'seen');
          var english = api.el('div', 'phrase-text aux-en');
          var chinese = api.el('div', 'word-zh');
          chinese.textContent = phrase.chinese;
          var words = PhraseQuiz.tokens(phrase);
          words.forEach(function (word) {
            var span = api.el('span');
            span.textContent = word;
            english.appendChild(span);
          });

          function light(index) {
            if (!api.alive()) return;
            english.querySelectorAll('span').forEach(function (span, i) {
              span.classList.toggle('lit', i === index);
            });
          }
          function listening(on) {
            busy = on;
            if (on) api.stage.dataset.listening = '1';
            else delete api.stage.dataset.listening;
          }
          function speak(queue) {
            light(-1);
            listening(true);
            var image = api.stage.querySelector('.scene img');
            if (image) { Fx.move(image, 'wiggle'); image.classList.add('phrase-speaking'); }
            api.word(phrase, {
              queue: !!queue,
              onstart: function () { light(0); },
              onboundary: function (charIndex) {
                var offset = 0;
                words.some(function (word, i) {
                  if (charIndex < offset + word.length) { light(i); return true; }
                  offset += word.length + 1;
                  return false;
                });
              },
              onend: function () {
                if (image) image.classList.remove('phrase-speaking');
                light(-1);
                listening(false);
              }
            });
          }
          api.onReplay(function () { if (!locked) speak(false); });

          function done(element) {
            locked = true;
            english.classList.add('shown'); // order: the sentence appears once it is built
            // A correction does not erase the first mistake's tomorrow schedule.
            api.record(phrase, missed ? 'seen' : 'right');
            api.dot(q);
            var next = function () {
              if (api.alive()) api.right(element, function () { q++; ask(); });
            };
            if (zhOn()) {
              api.word(phrase);
              api.zh('zh.' + phrase.id, { queue: true, onend: next });
            } else {
              api.word(phrase, { onend: next });
            }
          }
          function noteWrong() {
            if (!missed) api.record(phrase, 'wrong');
            missed = true;
          }

          if (mode === 'listen' || mode === 'review') {
            var grid = api.el('div', 'choices');
            api.stage.appendChild(grid);
            PhraseQuiz.choices(phrase, phrases, Math.random).forEach(function (option) {
              var button = api.picture(option);
              grid.appendChild(button);
              button.onclick = function () {
                if (locked || button.classList.contains('is-wrong')) return;
                if (option.id === phrase.id) {
                  button.classList.add('is-right');
                  done(button);
                } else {
                  button.classList.add('is-wrong');
                  noteWrong();
                  api.wrong(button, phrase);
                }
              };
            });
          } else {
            var scene = api.picture(phrase, 'scene');
            api.stage.append(scene, english, chinese);
            scene.onclick = function () { if (!locked) speak(false); };
            orderBoard(scene);
          }

          // Order: every token looks alike apart from a colour dealt at random,
          // and empty slots show nothing. Tap a token to hear its word, tap it
          // again (or the glowing slot) to put it in the next slot. Only after a
          // mistake does the right token glow.
          function orderBoard(scene) {
            var slots = api.el('div', 'phrase-slots');
            var bank = api.el('div', 'phrase-bank');
            api.stage.append(slots, bank);
            var position = 0, selected = null, hintAt = -1;
            var palette = PhraseQuiz.round(colors.slice(0, words.length), Math.random);
            var items = PhraseQuiz.round(words.map(function (word, i) {
              return { word: word, index: i };
            }), Math.random);

            function mark() {
              Array.from(slots.children).forEach(function (slot, i) {
                slot.classList.toggle('next', i === position);
              });
              items.forEach(function (item) {
                item.button.classList.toggle('hint', hintAt === position && item.index === position);
              });
            }
            function select(item) {
              selected = item;
              items.forEach(function (other) {
                other.button.classList.toggle('selected', other === item);
              });
            }
            function place(item) {
              select(null);
              if (!PhraseQuiz.accepts(phrase, position, item.index)) {
                noteWrong();
                api.wrong(item.button);          // shake and soft sound only
                hintAt = position;
                mark();
                api.zh('game.try_again');
                speak(true);
                return;
              }
              var slot = slots.children[position];
              item.button.disabled = true;
              item.button.classList.add('used');
              slot.disabled = true;
              slot.classList.add('filled');
              slot.style.background = item.button.style.background;
              slot.appendChild(item.button.querySelector('.aux-en').cloneNode(true));
              slot.setAttribute('aria-label', item.word);
              position++;
              mark();
              if (position === words.length) done(scene);
            }

            words.forEach(function (word, i) {
              var slot = api.el('button', 'btn slot', { 'aria-label': '放字卡的格子' });
              slots.appendChild(slot);
              slot.onclick = function () {
                if (!locked && !busy && i === position && selected) place(selected);
              };
            });
            items.forEach(function (item, j) {
              // The name includes the word the parent sees on it (screen readers, WCAG 2.5.3).
              var button = item.button = api.el('button', 'btn token', { 'aria-label': '聽這個字 ' + item.word });
              button.style.background = palette[j];
              button.appendChild(api.icon('#i-speaker'));
              var label = api.el('span', 'aux-en');
              label.textContent = item.word;
              button.appendChild(label);
              bank.appendChild(button);
              button.onclick = function () {
                if (locked || button.disabled) return;
                if (busy) { Fx.move(button, 'wiggle'); return; }
                if (selected === item) { place(item); return; }
                select(item);
                Speech.play({ english: item.word.replace(/[?.!]$/, '') });
              };
            });
            mark();
          }
          speak(q === 0); // First prompt waits for the recorded introduction.
        }
        ask();
      }
    };
  }

  // Today's review: due phrases first, then missed ones; back to the phrase area.
  function review() {
    var set = Progress.reviewSet(phrases, phrases.length);
    var targets = PhraseQuiz.reviewList(set, Progress.get, REVIEW_SIZE);
    Games.open(definition('review', targets), { back: 'phrases', targets: targets });
  }

  function menu() {
    var grid = document.querySelector('#phraseMenu');
    grid.textContent = '';
    [
      ['listen', '聽句子找圖', '#g-listen'],
      ['order', '排句子', '#g-order']
    ].forEach(function (row) {
      var button = document.createElement('button');
      button.className = 'game-card';
      button.dataset.phraseMode = row[0];
      button.style.setProperty('--theme', ['#ffe8a3', '#e0d0ff'][grid.children.length]);
      button.innerHTML = '<svg class="game-pic"><use href="' + row[2] + '"/></svg><span class="game-zh">' + row[1] + '</span>';
      button.onclick = function () {
        var only = row[0] === 'order' ? PhraseQuiz.orderable(phrases) : null;
        Games.open(definition(row[0], only), { back: 'phraseGames', targets: only });
      };
      grid.appendChild(button);
    });
  }
  window.Phrases = { build: function (list) { phrases = list; }, menu: menu, review: review };
})();
