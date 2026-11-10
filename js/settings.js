// Settings for grown-ups (Tim 2026-11-06): the word range (which themes
// the games, today's review, theme cards and sticker book use) and 幼幼模式
// (short, easier rounds for about 3-year-olds). Not the old
// parent corner: no own words, import/export or clearing progress.
// Children cannot get in by chance: the gear on the home screen needs a
// 2-second hold, then a sum (11–19 + 6–9). The screen itself uses Chinese
// labels for the grown-up; the child never needs to read anything.
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  var HOLD_MS = 2000;
  var TEXT = {
    hold: '大人請長按齒輪 2 秒。',
    wrong: '答案不對，換一題再試一次。',
    last: '至少要留 2 個字，遊戲才有圖可以選。',
    few: '開啟的字很少：遊戲的選項和牌會變少（例如只開點心就是 2 選 1），不會出現關掉的字。'
  };
  var opts = null;   // {themes(), words(), changed(), toast(msg)}

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
    if (inside) $('#settingsDoor').focus({ preventScroll: true });
  }

  function bindDoor() {
    var door = $('#settingsDoor'), timer = null, opened = false;
    function release() {
      if (timer === null) return;
      clearTimeout(timer);
      timer = null;
      door.classList.remove('holding');
      if (!opened) opts.toast(TEXT.hold);
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
        App.show('settings');
      } else {
        ask();
        $('#gateMsg').textContent = TEXT.wrong;
        $('#gateAnswer').focus();
      }
    });
    $('#gateCancel').addEventListener('click', closeGate);
    $('#gate').addEventListener('keydown', function (e) { if (e.key === 'Escape') closeGate(); });
  }

  // ---------- the word range
  function storage() { try { return window.localStorage; } catch (e) { return null; } }
  var memory = { off: [] };
  function current() { var st = storage(); return st ? Scope.load(st) : memory; }
  function store(s) {
    memory = Scope.clean(s);
    var st = storage();
    if (st) Scope.save(st, s);
  }

  function render() {
    renderEasy();
    var list = $('#scopeList');
    list.textContent = '';
    var s = current(), themes = opts.themes(), words = opts.words();
    themes.forEach(function (th) {
      var n = words.filter(function (w) { return w.theme === th.id; }).length;
      if (!n) return;
      var on = Scope.isOn(s, th.id);
      var row = document.createElement('li');
      row.className = 'scope-row';
      row.style.setProperty('--theme', th.color);
      var img = document.createElement('img');
      img.src = th.icon;
      img.alt = '';
      var name = document.createElement('span');
      name.className = 'scope-name';
      name.textContent = th.chinese + '（' + n + ' 個字）';
      var sw = document.createElement('button');
      sw.type = 'button';
      sw.className = 'scope-switch';
      sw.setAttribute('role', 'switch');
      sw.setAttribute('aria-checked', String(on));
      sw.setAttribute('aria-label', th.chinese);
      sw.dataset.theme = th.id;
      var knob = document.createElement('span');
      knob.className = 'scope-knob';
      sw.appendChild(knob);
      sw.addEventListener('click', function () {
        var now = current();
        if (!Scope.canTurnOff(themes, words, now, th.id)) { opts.toast(TEXT.last); return; }
        store(Scope.toggle(now, th.id));
        render();
        opts.changed();
      });
      row.append(img, name, sw);
      list.appendChild(row);
    });
    var count = Scope.words(words, current()).length;
    $('#scopeCount').textContent = '目前開啟 ' + count + ' 個字。';
    $('#scopeFew').hidden = count >= 4;
    $('#scopeFew').textContent = TEXT.few;
  }

  // ---------- 幼幼模式 (little ones' mode): short, easier rounds (Quiz.EASY).
  // Off by default; kept on this device like the word range.
  var EASY_KEY = 'ew.easy.v1';
  var easyMemory = false;
  function easy() {
    var st = storage();
    try { return st ? st.getItem(EASY_KEY) === '1' : easyMemory; } catch (e) { return easyMemory; }
  }
  function setEasy(on) {
    easyMemory = !!on;
    var st = storage();
    try { if (st) st.setItem(EASY_KEY, on ? '1' : '0'); } catch (e) { /* kept for this visit only */ }
  }
  function renderEasy() { $('#easySwitch').setAttribute('aria-checked', String(easy())); }

  function init(o) {
    opts = o;
    bindDoor();
    $('#easySwitch').addEventListener('click', function () {
      setEasy(!easy());
      renderEasy();
    });
  }

  window.Settings = { init: init, render: render, scope: current, easy: easy };
})();
