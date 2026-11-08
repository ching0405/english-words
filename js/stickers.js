// The sticker book (S2, 2026-11-06): every word picture (and phrase scene) is
// a sticker. Not yet collected = the same picture as a grey shape (CSS only);
// collected = in colour, tap to hear it; gold frame = the word reached
// Progress KNOWN_BOX (right again on a later day). Opened from the star jar.
// Each finished round turns over one covered card on the result screen: a
// sticker for a word answered right in that round. New words in
// data/words.json show up here by themselves, as grey shapes.
//
//   Stickers.choose(right, ctx, rand)  pure: which sticker a round gives
//   Stickers.book(words, phrases)      the pages: [{id, items}] (theme order, phrases last)
//   Stickers.grant(right, all)         choose + save; {id, kind, word, pageDone} or null
//   Stickers.open() / render(page)     the book screen
//   Stickers.card(gift, where)         the covered card on the result screen
// The pure parts run in Node (tools/test_stickers.cjs).
(function (root) {
  'use strict';

  // ---------- pure rules
  // right: ids answered right in this round (in order, may repeat)
  // ctx: {has(id), gold(id), complete} — complete: every sticker in range collected
  // Returns {id, kind: 'new' | 'again' | 'gold'} or null (nothing answered right).
  function choose(right, ctx, rand) {
    rand = rand || Math.random;
    var ids = right.filter(function (id, i) { return right.indexOf(id) === i; });
    if (!ids.length) return null;
    var pick = function (list) { return list[Math.floor(rand() * list.length)]; };
    var fresh = ids.filter(function (id) { return !ctx.has(id); });
    if (fresh.length) return { id: pick(fresh), kind: 'new' };
    if (ctx.complete) {
      var gold = ids.filter(function (id) { return ctx.gold(id); });
      if (gold.length) return { id: pick(gold), kind: 'gold' };
    }
    return { id: pick(ids), kind: 'again' };
  }

  // Pages of the book: themes in data order (only themes with words), then phrases.
  function book(words, themes, phrases) {
    var pages = [];
    themes.forEach(function (t) {
      var items = words.filter(function (w) { return w.theme === t.id; });
      if (items.length) pages.push({ id: t.id, theme: t, items: items });
    });
    if (phrases && phrases.length) pages.push({ id: 'phrases', theme: null, items: phrases });
    return pages;
  }

  // The page an id is on, and whether every sticker there is collected.
  function pageOf(pages, id) {
    return pages.filter(function (p) { return p.items.some(function (w) { return w.id === id; }); })[0] || null;
  }
  function pageDone(page, has) {
    return !!page && page.items.every(function (w) { return has(w.id); });
  }

  // Columns for n square stickers in a w×h box, the biggest size that fits
  // without scrolling (iPad: animals 17 -> 4 columns upright, 6 sideways).
  function layout(n, w, h, gap) {
    var best = { cols: 1, size: 0 };
    for (var cols = 1; cols <= Math.max(1, n); cols++) {
      var rows = Math.ceil(n / cols);
      var size = Math.min((w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows);
      if (size > best.size) best = { cols: cols, size: size };
    }
    return best;
  }

  var lib = { choose: choose, book: book, pageOf: pageOf, pageDone: pageDone, layout: layout };
  if (typeof module !== 'undefined' && module.exports) { module.exports = lib; return; }

  // ---------- browser
  var $ = function (s) { return document.querySelector(s); };
  var MIN_CELL = 96;   // smaller than this: the page scrolls instead (more words later)
  var state = { words: [], themes: [], phrases: [], page: null, flash: null, back: 'home' };

  function setData(words, themes, phrases) {
    state.words = words || state.words;
    state.themes = themes || state.themes;
    if (phrases) state.phrases = phrases;
  }

  function pages() { return book(state.words, state.themes, state.phrases); }
  function has(id) { return !!Progress.stickers()[id]; }
  function all() { return state.words.concat(state.phrases); }

  // A round ended: pick and save its sticker (saved now, so skipping the
  // card loses nothing). `right` are the word / phrase objects answered right.
  function grant(right) {
    var ids = (right || []).map(function (w) { return w.id; })
      .filter(function (id) { return all().some(function (w) { return w.id === id; }); });
    var collected = Progress.stickers();
    var complete = all().every(function (w) { return collected[w.id]; });
    var got = choose(ids, { has: function (id) { return !!collected[id]; }, gold: Progress.isGold, complete: complete });
    if (!got) return null;
    var item = all().filter(function (w) { return w.id === got.id; })[0];
    if (got.kind === 'new') Progress.collect(got.id);
    var page = pageOf(pages(), got.id);
    state.flash = got.id;   // it twinkles once the next time the book opens
    return { id: got.id, kind: got.kind, word: item, gold: Progress.isGold(got.id),
             page: page && page.id, pageDone: got.kind === 'new' && pageDone(page, has) };
  }

  function icon(href, cls) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', cls);
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', href);
    svg.appendChild(use);
    return svg;
  }

  // ---------- the book screen
  function open(from) {
    state.back = from || 'home';
    var back = $('#stickers .bar [data-go]');
    back.dataset.go = state.back;
    var list = pages();
    // Open on the page of the newest sticker, else the first page.
    var flashPage = state.flash && pageOf(list, state.flash);
    if (flashPage) state.page = flashPage.id;
    if (!list.some(function (p) { return p.id === state.page; })) state.page = list.length ? list[0].id : null;
    App.show('stickers');
    tabs(list);
    render();
    Speech.zh('sticker.book');
  }

  function tabs(list) {
    var box = $('#stickerTabs');
    box.textContent = '';
    list.forEach(function (p) {
      var t = p.theme || { chinese: '句子', english: 'Phrases', color: '#c4e8ff', icon: 'images/phrases/hello.svg' };
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip sticker-tab';
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-label', t.chinese + ' ' + t.english);
      b.dataset.page = p.id;
      var img = document.createElement('img');
      img.src = t.icon;
      img.alt = '';
      b.appendChild(img);
      b.style.setProperty('--theme', t.color);
      // A finished page shows a star on its tab.
      if (pageDone(p, has)) b.appendChild(icon('#i-star', 'chip-star tab-done'));
      b.addEventListener('click', function () {
        state.page = p.id;
        render();
        Speech.zh(p.theme ? 'theme.' + p.id : 'sticker.phrases');
      });
      box.appendChild(b);
    });
  }

  function render() {
    var list = pages();
    var page = list.filter(function (p) { return p.id === state.page; })[0];
    document.querySelectorAll('#stickerTabs .sticker-tab').forEach(function (b) {
      b.setAttribute('aria-selected', String(b.dataset.page === state.page));
    });
    var grid = $('#stickerGrid');
    grid.textContent = '';
    if (!page) return;
    grid.dataset.page = page.id;
    var got = Progress.stickers();
    page.items.forEach(function (w) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'sticker';
      b.dataset.word = w.id;
      var img = document.createElement('img');
      img.src = w.image;
      img.alt = '';
      img.draggable = false;
      b.appendChild(img);
      if (got[w.id]) {
        b.classList.add('is-got');
        if (Progress.isGold(w.id)) b.classList.add('is-gold');
        b.setAttribute('aria-label', w.english);
        b.addEventListener('click', function () { Fx.tap(img, w); Speech.play(w); });
      } else {
        // Grey shape: still a button (a little wobble), but no word yet.
        b.classList.add('is-missing');
        b.setAttribute('aria-label', '?');
        b.addEventListener('click', function () { Fx.move(img, 'wiggle'); });
      }
      if (state.flash === w.id) b.classList.add('is-flash');
      grid.appendChild(b);
    });
    state.flash = null;
    fit();
  }

  // Size the stickers to fill the page without scrolling.
  function fit() {
    var grid = $('#stickerGrid');
    if (!grid || $('#stickers').hidden) return;
    var n = grid.children.length;
    if (!n) return;
    var gap = parseFloat(getComputedStyle(grid).columnGap) || 12;
    var box = grid.getBoundingClientRect();
    var l = layout(n, box.width - 26, box.height - 26, gap);   // 12px padding each side for the gold ring
    var size = Math.max(MIN_CELL, Math.min(l.size, 260));
    var cols = Math.max(1, Math.min(n, Math.floor((box.width + gap) / (size + gap))));
    grid.style.setProperty('--cols', String(cols));
    grid.style.setProperty('--cell', Math.floor(size) + 'px');
  }
  window.addEventListener('resize', fit);

  // ---------- the covered card on the result screen
  // Appears after the stars flew in; tap it to turn it over. Skipping is fine.
  function card(gift, delay) {
    var slot = $('#resultGift');
    slot.textContent = '';
    slot.hidden = true;
    if (!gift) return null;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'mcard gift-card';
    b.setAttribute('aria-label', '翻開貼紙 Sticker');
    b.dataset.word = gift.id;
    b.dataset.kind = gift.kind;
    var back = document.createElement('span');
    back.className = 'mcard-back';
    back.appendChild(icon('#i-star', 'mcard-star'));
    var face = document.createElement('span');
    face.className = 'mcard-face' + (gift.gold ? ' is-gold' : '');
    var img = document.createElement('img');
    img.src = gift.word.image;
    img.alt = '';
    img.draggable = false;
    face.appendChild(img);
    b.append(back, face);
    var timer = setTimeout(function () {
      if ($('#result').hidden) return;
      $('#resultFriend').hidden = true;
      slot.hidden = false;
      Speech.zh('sticker.tap', { queue: true });
    }, delay || 0);
    b.addEventListener('click', function () {
      if (b.classList.contains('is-open')) { Fx.tap(img, gift.word); Speech.play(gift.word); return; }
      b.classList.add('is-open');
      b.setAttribute('aria-label', gift.word.english);
      Fx.sound('flip');
      Speech.stop();
      Speech.zh(gift.kind === 'new' ? 'sticker.new' : gift.kind === 'gold' ? 'sticker.gold' : 'sticker.again');
      Speech.play(gift.word, { queue: true });
      if (gift.kind === 'new') Fx.burst(b);
      if (gift.pageDone) {
        // The whole page is collected: one cheer.
        setTimeout(function () {
          if ($('#result').hidden) return;
          Fx.move(b, 'cheer');
          Fx.sound('star');
          Speech.zh('sticker.page_done', { queue: true });
        }, 700);
      }
      // Into the book (the jar opens it), like the stars into the jar.
      setTimeout(function () { if (!$('#result').hidden) fly(img, $('#result .jar-box')); }, 1200);
    });
    slot.appendChild(b);
    return { el: b, timer: timer };
  }

  function fly(img, to) {
    if (!img || !to || !document.body.animate) return;
    if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var a = img.getBoundingClientRect(), b = to.getBoundingClientRect();
    var c = img.cloneNode();
    c.className = 'flying-sticker';
    c.style.left = a.left + 'px';
    c.style.top = a.top + 'px';
    c.style.width = a.width + 'px';
    c.style.height = a.height + 'px';
    document.body.appendChild(c);
    var dx = b.left + b.width / 2 - (a.left + a.width / 2), dy = b.top + b.height / 2 - (a.top + a.height / 2);
    c.animate([
      { transform: 'translate(0,0) scale(1)', opacity: 1 },
      { transform: 'translate(' + dx * 0.5 + 'px,' + (dy * 0.5 - 60) + 'px) scale(.7)', opacity: 1, offset: 0.5 },
      { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.2)', opacity: 0.2 }
    ], { duration: 800, easing: 'ease-in', fill: 'forwards' }).onfinish = function () {
      c.remove();
      Fx.move(to.querySelector('.jar-main'), 'wiggle');
    };
  }

  root.Stickers = Object.assign({ setData: setData, grant: grant, open: open, render: render, card: card, fit: fit }, lib);
})(this);
