// Parent corner (phase 6): add, edit and delete this device's own words and
// phrases, back them up and clear progress. Screens are for grown-ups, so
// they use text; children cannot get in by chance: the gear on the home screen
// needs a 2-second hold and then a sum (two-digit addition).
// Data and storage live in js/custom.js; App re-merges the lists on change.
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  var HOLD_MS = 2000;
  var SIZE = 512;                    // photos are cut to a 512×512 square
  var opts = null;                   // {builtIn(), changed(), toast(msg)}
  var form = { kind: 'word', id: null, image: null, picked: null };

  // ---------- gate
  var gate = { answer: null };
  function ask() {
    var a = 11 + Math.floor(Math.random() * 9), b = 6 + Math.floor(Math.random() * 4);
    gate.answer = a + b;
    $('#gateQ').textContent = a + ' + ' + b;
    $('#gateAnswer').value = '';
  }
  function openGate() {
    ask();
    $('#gateMsg').textContent = '';
    $('#gate').hidden = false;
    $('#gateAnswer').focus();
  }
  function closeGate() {
    var inside = $('#gate').contains(document.activeElement);
    $('#gate').hidden = true;
    if (inside) $('#parentDoor').focus({ preventScroll: true }); // keyboard and VoiceOver users go back to the gear
  }

  function bindDoor() {
    var door = $('#parentDoor'), timer = null, opened = false;
    function release() {
      if (timer === null) return;
      clearTimeout(timer);
      timer = null;
      door.classList.remove('holding');
      if (!opened) opts.toast('家長請長按齒輪 2 秒。');
    }
    door.addEventListener('pointerdown', function (e) {
      if (e.button) return;
      opened = false;
      door.classList.add('holding');
      clearTimeout(timer);
      timer = setTimeout(function () {
        timer = null;
        opened = true;
        door.classList.remove('holding');
        openGate();
      }, HOLD_MS);
    });
    ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (t) { door.addEventListener(t, release); });
    door.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    // Keyboard (no pointer): the sum alone guards the door.
    door.addEventListener('click', function (e) { if (e.detail === 0) openGate(); });
    $('#gateForm').addEventListener('submit', function (e) {
      e.preventDefault();
      if (parseInt($('#gateAnswer').value, 10) === gate.answer) {
        closeGate();
        App.show('parent');
      } else {
        ask();
        $('#gateMsg').textContent = '答案不對，換一題再試一次。';
        $('#gateAnswer').focus();
      }
    });
    $('#gateCancel').addEventListener('click', closeGate);
    $('#gate').addEventListener('keydown', function (e) { if (e.key === 'Escape') closeGate(); });
  }

  // ---------- pictures
  // Any picture (a file or a data URL) -> a 512×512 JPEG data URL, cut from
  // the middle like a photo app's square. Rejects when it cannot be decoded.
  function shrink(src) {
    return new Promise(function (ok, fail) {
      var img = new Image();
      img.onload = function () {
        try {
          var w = img.naturalWidth, h = img.naturalHeight, s = Math.min(w, h);
          if (!s) throw new Error('empty');
          var c = document.createElement('canvas');
          c.width = c.height = SIZE;
          var g = c.getContext('2d');
          g.fillStyle = '#fff';
          g.fillRect(0, 0, SIZE, SIZE);
          g.drawImage(img, (w - s) / 2, (h - s) / 2, s, s, 0, 0, SIZE, SIZE);
          ok(c.toDataURL('image/jpeg', 0.85));
        } catch (e) { fail(e); }
      };
      img.onerror = function () { fail(new Error('decode')); };
      img.src = src;
    });
  }

  function shrinkFile(file) {
    var url = URL.createObjectURL(file);
    return shrink(url).then(function (d) { URL.revokeObjectURL(url); return d; }, function (e) { URL.revokeObjectURL(url); throw e; });
  }

  // ---------- lists
  function themeName(id) {
    var all = opts.builtIn().themes.concat(Custom.list().themes);
    var t = all.filter(function (x) { return x.id === id; })[0];
    return t ? t.chinese : '';
  }

  function button(text, cls, label) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'pbtn ' + (cls || '');
    b.textContent = text;
    if (label) b.setAttribute('aria-label', label);
    return b;
  }

  function rows(kind) {
    var ul = $(kind === 'word' ? '#myWords' : '#myPhrases');
    var items = Custom.view()[kind === 'word' ? 'words' : 'phrases'];
    ul.textContent = '';
    if (!items.length) {
      var none = document.createElement('li');
      none.className = 'pempty';
      none.textContent = kind === 'word' ? '還沒有自己加的單字。' : '還沒有自己加的句子。';
      ul.appendChild(none);
    }
    items.forEach(function (w) {
      var li = document.createElement('li');
      li.className = 'prow';
      li.dataset.id = w.id;
      var img = document.createElement('img');
      img.src = w.image;
      img.alt = '';
      var text = document.createElement('div');
      text.className = 'prow-text';
      var en = document.createElement('b');
      en.lang = 'en';
      en.textContent = w.english;
      var zh = document.createElement('span');
      zh.textContent = w.chinese + (kind === 'word' ? '・' + themeName(w.theme) : '');
      text.append(en, zh);
      var say = button('聽', '', '聽 ' + w.english);
      say.addEventListener('click', function () { Speech.play(w); });
      var edit = button('編輯', '', '編輯 ' + w.english);
      edit.dataset.act = 'edit';
      edit.addEventListener('click', function () { openForm(kind, w); });
      var del = button('刪除', 'pbtn-warn', '刪除 ' + w.english);
      del.dataset.act = 'delete';
      del.addEventListener('click', function () {
        if (!confirm('要刪除「' + w.english + '」嗎？它的學習紀錄也會一起刪掉。')) return;
        Custom.remove(kind, w.id).then(function () {
          opts.changed();
          render();
          opts.toast('已刪除「' + w.english + '」。');
        }, function (err) {
          if (!err.removed) { opts.toast(err.message); return; }
          opts.changed();
          render();
          opts.toast('已刪除「' + w.english + '」，但' + err.message);
        });
      });
      li.append(img, text, say, edit, del);
      ul.appendChild(li);
    });
  }

  function render() {
    rows('word');
    rows('phrase');
    $('#myWordsTitle').textContent = '我加的單字（' + Custom.list().words.length + '）';
    $('#myPhrasesTitle').textContent = '我加的句子（' + Custom.list().phrases.length + '）';
  }

  // ---------- add / edit form
  function setPicture(src) {
    var img = $('#fImg');
    img.hidden = !src;
    if (src) img.src = src; else img.removeAttribute('src');
    $('#fImgNone').hidden = !!src;
  }

  function fillThemes(selected) {
    var sel = $('#fTheme');
    sel.textContent = '';
    opts.builtIn().themes.concat(Custom.list().themes).forEach(function (t) {
      var o = document.createElement('option');
      o.value = t.id;
      o.textContent = t.chinese + (t.english ? ' ' + t.english : '');
      sel.appendChild(o);
    });
    var add = document.createElement('option');
    add.value = '+new';
    add.textContent = '＋ 新主題…';
    sel.appendChild(add);
    sel.value = selected || sel.options[0].value;
    $('#fNewTheme').hidden = sel.value !== '+new';
  }

  function buildGallery() {
    var box = $('#fGallery');
    box.textContent = '';
    var b = opts.builtIn();
    var named = {};
    b.words.concat(b.phrases).forEach(function (w) { named[w.image] = w.english; });
    // A picture another word (or phrase) already shows is left out: two of
    // the same picture in one question cannot be told apart.
    var mine = form.kind === 'word' ? b.words : b.phrases;
    var used = Custom.lib.usedPictures(mine, form.id);
    Object.assign(used, Custom.shown(form.kind, form.id));
    b.gallery.filter(function (src) { return !used[src]; }).forEach(function (src) {
      var g = document.createElement('button');
      g.type = 'button';
      g.className = 'pgallery-pick';
      g.dataset.src = src;
      g.setAttribute('aria-label', '內建圖片 ' + (named[src] || src));
      g.setAttribute('aria-pressed', String(form.picked === src));
      var img = document.createElement('img');
      img.src = src;
      img.alt = '';
      g.appendChild(img);
      g.addEventListener('click', function () {
        form.image = form.picked = src;
        setPicture(src);
        box.querySelectorAll('.pgallery-pick').forEach(function (x) { x.setAttribute('aria-pressed', String(x === g)); });
      });
      box.appendChild(g);
    });
  }

  function openForm(kind, item) {
    form = { kind: kind, id: item ? item.id : null, image: null, picked: item && item.image.indexOf('data:') !== 0 ? item.image : null };
    var word = kind === 'word';
    $('#editTitle').textContent = (item ? '編輯' : '新增') + (word ? '單字' : '句子');
    $('#fEnLabel').textContent = word ? '英文（例如 cat、teddy bear）' : '英文句子（最多 ' + Custom.lib.MAX_TOKENS + ' 個字，例如 Good night.）';
    $('#fZhLabel').textContent = word ? '中文（只顯示，不會念出來）' : '中文意思（只顯示，不會念出來）';
    $('#fImgLegend').textContent = word ? '圖片' : '情境圖片';
    $('#fEn').value = item ? item.english : '';
    $('#fZh').value = item ? item.chinese : '';
    $('#fThemeRow').hidden = !word;
    if (word) fillThemes(item && item.theme);
    $('#fThemeZh').value = '';
    $('#fThemeEn').value = '';
    $('#fGallery').hidden = true;
    $('#fGalleryBtn').setAttribute('aria-expanded', 'false');
    $('#fMsg').textContent = '';
    $('#fFile').value = '';
    setPicture(item ? item.image : null);
    App.show('parentEdit');
    $('#fEn').focus();
  }

  function submit(e) {
    e.preventDefault();
    var word = form.kind === 'word';
    var item = { id: form.id, english: $('#fEn').value, chinese: $('#fZh').value };
    if (word) {
      if ($('#fTheme').value === '+new') item.newTheme = { chinese: $('#fThemeZh').value, english: $('#fThemeEn').value };
      else item.theme = $('#fTheme').value;
    }
    var save = $('#fSave');
    save.disabled = true;
    $('#fMsg').textContent = '';
    (word ? Custom.saveWord : Custom.savePhrase)(item, form.image, opts.builtIn()).then(function (saved) {
      save.disabled = false;
      opts.changed();
      App.show('parent');
      opts.toast('已存好「' + saved.english + '」。');
    }, function (err) {
      save.disabled = false;
      $('#fMsg').textContent = err.message;
    });
  }

  // ---------- backup
  function today() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  function exportFile() {
    var doc = Custom.backup();
    var name = 'picture-words-backup-' + today() + '.json';
    var blob = new Blob([JSON.stringify(doc, null, 1)], { type: 'application/json' });
    var n = doc.words.length + doc.phrases.length;
    var msg = '已匯出 ' + doc.words.length + ' 個單字、' + doc.phrases.length + ' 句句子。';
    if (!n) { $('#ioMsg').textContent = '還沒有自己加的單字或句子，沒有東西可以匯出。'; return; }
    // iPad: the share sheet (save to Files, AirDrop, mail…); elsewhere a download.
    var file = window.File ? new File([blob], name, { type: 'application/json' }) : null;
    if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
      navigator.share({ files: [file], title: name }).then(function () { $('#ioMsg').textContent = msg; }, function (err) {
        if (err && err.name === 'AbortError') return;
        download(blob, name);
        $('#ioMsg').textContent = msg;
      });
      return;
    }
    download(blob, name);
    $('#ioMsg').textContent = msg;
  }

  function download(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 10000);
  }

  function importFile() {
    var input = $('#importFile'), file = input.files && input.files[0];
    if (!file) return;
    var out = $('#ioMsg');
    out.textContent = '匯入中…';
    var text = file.size > 40 * 1024 * 1024 ? Promise.reject(new Error('這個檔案太大了。')) : file.text();
    text.then(function (t) { return Custom.restore(t, opts.builtIn(), shrink); }).then(function (res) {
      opts.changed();
      render();
      var msg = '匯入好了：新增 ' + res.added + ' 筆，更新 ' + res.updated + ' 筆。';
      if (res.skipped.length) msg += '略過 ' + res.skipped.length + ' 筆已經有的：' + res.skipped.join('、') + '。';
      out.textContent = msg;
    }, function (err) {
      out.textContent = '沒有匯入：' + err.message + ' 原本的資料都沒有改變。';
    }).then(function () { input.value = ''; });
  }

  // ---------- wiring
  function bind(o) {
    opts = o;
    bindDoor();
    $('#addWordBtn').addEventListener('click', function () { openForm('word'); });
    $('#addPhraseBtn').addEventListener('click', function () { openForm('phrase'); });
    $('#editForm').addEventListener('submit', submit);
    $('#fTheme').addEventListener('change', function () {
      $('#fNewTheme').hidden = $('#fTheme').value !== '+new';
      if (!$('#fNewTheme').hidden) $('#fThemeZh').focus();
    });
    $('#fSay').addEventListener('click', function () {
      var en = Custom.lib.tidy($('#fEn').value);
      if (en) Speech.play({ english: en, category: form.kind === 'phrase' ? 'custom' : undefined });
    });
    $('#fFile').addEventListener('change', function () {
      var file = this.files && this.files[0];
      if (!file) return;
      $('#fMsg').textContent = '';
      shrinkFile(file).then(function (data) {
        form.image = data;
        form.picked = null;
        setPicture(data);
        $('#fGallery').querySelectorAll('.pgallery-pick').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
      }, function () { $('#fMsg').textContent = '這張圖片打不開，請換一張。'; });
    });
    $('#fGalleryBtn').addEventListener('click', function () {
      var box = $('#fGallery');
      if (box.hidden) buildGallery();
      box.hidden = !box.hidden;
      this.setAttribute('aria-expanded', String(!box.hidden));
    });
    $('#exportBtn').addEventListener('click', exportFile);
    $('#importFile').addEventListener('change', importFile);
    $('#clearProgressBtn').addEventListener('click', function () {
      if (!confirm('確定要清除這台裝置上所有的學習紀錄、主題星星和星星罐嗎？自己加的單字和句子會留著。')) return;
      Progress.clear();
      opts.changed();
      opts.toast('學習進度已清除。');
    });
  }

  window.Parent = { bind: bind, render: render, shrink: shrink };
})();
