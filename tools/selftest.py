#!/usr/bin/env python3
"""Headless browser self-test for Picture Words (phase 1 cards, phase 2 games).

Starts `python3 -m http.server` on a free port, drives the site in Chrome at
iPad (main device) and phone sizes and checks:
  - no console errors, page errors or 4xx/5xx responses
  - every card image loads (naturalWidth > 0), no text overflow, buttons >= 56px
  - tapping the picture / speaker calls speechSynthesis.speak with the right
    text, lang en-US and a slow rate; voices that load late are still picked
  - a word with `audio` plays the file; a broken audio file falls back to TTS
  - a browser without speechSynthesis shows a friendly message, no errors
  - tapping a card picture runs a short action + sound; fast taps never pile up
  - card taps only rock side to side (no spin, tilt <= 15 degrees)
  - every game plays a full round (wrong answer, right answers, stars) using
    only what is spoken, never on-screen text; boards contain no text
  - progress (phase 3): kept after reload, review of due words a day later,
    clearing and a broken save start over safely
  - offline (phase 5): the service worker caches every game file; with the
    server stopped the app reloads and plays (pictures, recorded mp3s, Range
    requests); a new version refreshes the cache and reloads only on the home screen
Screenshots go to /tmp/ew-selftest-qa/phase-N/ so a normal run leaves the
committed qa/ pictures alone; pass --qa (acceptance runs only) to write them to
qa/phase-1/ (cards), qa/phase-2/ (games), qa/phase-3/ (progress), qa/phase-4/ (phrases).

Usage: python3 tools/selftest.py [--only cards|games|progress|phrases|pwa|look|a11y|music] [--qa] [--chrome /usr/bin/google-chrome]
Exit code 1 when any check fails.
"""
import argparse, contextlib, importlib.util, io, json, pathlib, re, shutil, socket, subprocess, sys, tempfile, time, wave

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP_QA = pathlib.Path("/tmp/ew-selftest-qa")
QA = QA2 = QA3 = QA4 = QA5 = QA6 = QA7 = QA8 = None  # set by use_qa_root() in main()


def use_qa_root(root):
    global QA, QA2, QA3, QA4, QA5, QA6, QA7, QA8
    QA, QA2, QA3, QA4, QA5, QA6, QA7, QA8 = (root / f"phase-{n}" for n in (1, 2, 3, 4, 5, 6, 7, 8))

# iPad is the main device (every theme, big buttons); phones only must not break.
# The offline worker is blocked here so ctx.route() (short test clips, broken
# files) still sees every request; pwa_flow() runs the real worker.
TABLET = dict(is_mobile=True, has_touch=True, device_scale_factor=1, service_workers="block")
PHONE = dict(is_mobile=True, has_touch=True, device_scale_factor=2, service_workers="block")
VIEWPORTS = {
    "ipad-portrait": dict(viewport={"width": 820, "height": 1180}, **TABLET),
    "ipad-landscape": dict(viewport={"width": 1180, "height": 820}, **TABLET),
    "ipad-pro": dict(viewport={"width": 1024, "height": 1366}, **TABLET),
    "phone-portrait": dict(viewport={"width": 390, "height": 844}, **PHONE),
    "phone-landscape": dict(viewport={"width": 844, "height": 390}, **PHONE),
}
FULL_RUN = ("ipad-portrait", "ipad-landscape")
MIN_TAP = {"ipad": 80, "phone": 56}

# Replaces speechSynthesis with a recorder. Voices arrive late (after `lateMs`)
# and, when `event` is false, without a voiceschanged event (polling fallback).
FAKE_SPEECH = r"""
(cfg => {
  const rec = window.__speech = { calls: [], cancels: 0 };
  window.__audio = [];
  window.__osc = 0;  // oscillators started = sound effects played
  const AC = window.AudioContext || window.webkitAudioContext;
  if (AC) {
    const osc = AC.prototype.createOscillator;
    AC.prototype.createOscillator = function () { window.__osc++; return osc.call(this); };
  }
  const origPlay = HTMLMediaElement.prototype.play;
  window.__audioEls = [];
  window.__mediaEvents = [];
  HTMLMediaElement.prototype.play = function () {
    if (!this.__watched) {
      this.__watched = true;
      ['play', 'playing', 'pause', 'ended', 'error', 'waiting', 'stalled', 'abort', 'emptied', 'loadeddata'].forEach(type => {
        this.addEventListener(type, () => {
          window.__mediaEvents.push({type, src: this.src, t: performance.now(), time: this.currentTime});
          if (window.__mediaEvents.length > 100) window.__mediaEvents.shift();
        });
      });
    }
    window.__audio.push(this.src); window.__audioEls.push(this); return origPlay.call(this);
  };
  if (cfg.unsupported) {
    Object.defineProperty(window, 'speechSynthesis', { value: undefined, configurable: true });
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: undefined, configurable: true });
    return;
  }
  const voices = [
    { name: 'Daniel', lang: 'en-GB', localService: true, default: false, voiceURI: 'daniel' },
    { name: 'Mei-Jia', lang: 'zh-TW', localService: true, default: true, voiceURI: 'meijia' },
    { name: 'Samantha', lang: 'en_US', localService: true, default: false, voiceURI: 'samantha' },
  ];
  let ready = false;
  const synth = new EventTarget();
  synth.getVoices = () => ready ? voices.slice() : [];
  // Utterances play one after another for ~90ms each, like a real queue.
  let queue = [];
  const next = () => {
    const u = queue[0];
    if (!u) { synth.speaking = false; return; }
    synth.speaking = true;
    setTimeout(() => {
      if (queue[0] !== u) return;
      u.onstart && u.onstart({});
      if (u.onboundary) {
        Array.from(u.text.matchAll(/\S+/g)).forEach((m,i) => setTimeout(() => {
          if(queue[0] === u) u.onboundary({charIndex:m.index});
        }, i*15));
      }
      setTimeout(() => { if (queue[0] !== u) return; queue.shift(); u.onend && u.onend({}); next(); }, 80);
    }, 10);
  };
  synth.speak = u => {
    rec.calls.push({ text: u.text, lang: u.lang, voice: u.voice && u.voice.name, rate: u.rate, volume: u.volume, q: document.querySelector('#play')?.dataset.q, game: document.querySelector('#play')?.dataset.game, t: performance.now() });
    queue.push(u);
    if (queue.length === 1) next();
  };
  synth.cancel = () => {
    rec.cancels++;
    const old = queue; queue = []; synth.speaking = false;
    old.forEach(u => u.onerror && u.onerror({ error: 'interrupted' }));
  };
  synth.pause = synth.resume = () => {};
  synth.paused = false; synth.speaking = false; synth.pending = false;
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
  window.SpeechSynthesisUtterance = function (text) {
    this.text = text; this.lang = ''; this.voice = null; this.rate = 1; this.pitch = 1; this.volume = 1;
  };
  setTimeout(() => { ready = true; if (cfg.event) synth.dispatchEvent(new Event('voiceschanged')); }, cfg.lateMs);
})
"""

# Text that must stay inside its box and inside the viewport horizontally.
LAYOUT_CHECK = """
(minTap) => {
  const bad = [];
  const vw = innerWidth, vh = innerHeight;
  const screen = [...document.querySelectorAll('.screen')].find(s => !s.hidden);
  screen.querySelectorAll('h1 span, h2, .pill, .word-en, .word-zh, .theme-zh, .theme-en, .theme-count, .btn, .pic, .chip, .game-card, .pick, .mcard, .big-star').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width) return;
    // .pic clips its picture (overflow: hidden), so only its position matters.
    if (!el.matches('.pic, .pick, .mcard') && el.scrollWidth > el.clientWidth + 1) bad.push(`overflow ${el.className || el.tagName}: ${el.textContent.trim()}`);
    if (r.left < -1 || r.right > vw + 1) bad.push(`offscreen-x ${el.className || el.tagName}: ${el.textContent.trim()}`);
    if (!el.closest('.theme-grid, .game-grid') && (r.top < -1 || r.bottom > vh + 1)) bad.push(`offscreen-y ${el.className || el.tagName}: ${el.textContent.trim()}`);
  });
  screen.querySelectorAll('button').forEach(b => {
    const r = b.getBoundingClientRect();
    if (r.width && (r.width < minTap || r.height < minTap)) bad.push(`small button ${b.id || b.className} ${Math.round(r.width)}x${Math.round(r.height)}`);
  });
  return bad;
}
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def beep_wav():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"".join(int(8000 * ((i // 10) % 2 * 2 - 1)).to_bytes(2, "little", signed=True) for i in range(2400)))
    return buf.getvalue()


class Run:
    def __init__(self):
        self.failures = []
        self.notes = []

    def check(self, ok, msg):
        (self.notes if ok else self.failures).append(("PASS " if ok else "FAIL ") + msg)
        return ok


def watch(page, errors, allow=()):
    page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("response", lambda r: r.status >= 400 and not any(a in r.url for a in allow) and errors.append(f"{r.status} {r.url}"))


def short_wav(seconds=0.15):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(8000)
        w.writeframes(b"\x80" * int(8000 * seconds))
    return buf.getvalue()


SHORT_WAV = short_wav()


def fast_voice(ctx):
    """Serve every recorded Chinese line as a 0.15s clip so rounds run fast.
    The real mp3 files are checked separately in special_cases()."""
    ctx.route("**/audio/zh/*.mp3", lambda r: r.fulfill(status=200, content_type="audio/wav", body=SHORT_WAV))


def open_site(browser, base, opts, cfg, errors, allow=(), real_voice=False):
    ctx = browser.new_context(**opts)
    if not real_voice:
        fast_voice(ctx)
    ctx.add_init_script(FAKE_SPEECH + f"({json.dumps(cfg)})")
    page = ctx.new_page()
    watch(page, errors, allow)
    page.goto(base)
    page.wait_for_selector("#startBtn:not([disabled])")
    return ctx, page


def last_call(page):
    return page.evaluate("() => window.__speech && window.__speech.calls.at(-1)")


def calls(page):
    return page.evaluate("() => window.__speech ? window.__speech.calls.length : 0")


def audios(page):
    return page.evaluate("() => window.__audio.length")


def zh_said(page, since, key):
    """A recorded Chinese line (key, or key prefix such as 'praise.') played since audio mark `since`."""
    return any(f"/audio/zh/{key}" in u for u in page.evaluate("() => window.__audio")[since:])


def zh_tts(page):
    """Chinese read by speechSynthesis instead of the recordings (should be none)."""
    return [c["text"] for c in page.evaluate("() => window.__speech ? window.__speech.calls : []") if c["lang"] == "zh-TW"]


def wait_word(page, since, english, timeout=5000):
    """Wait until `english` is spoken (en-US) after speech mark `since`; True if it was."""
    try:
        page.wait_for_function("([n, w]) => window.__speech.calls.slice(n).some(c => c.lang === 'en-US' && c.text === w)",
                               arg=[since, english], timeout=timeout)
        return True
    except Exception:
        return False


def image_ok(page):
    page.wait_for_function("() => document.querySelector('#picImg').complete")
    return page.evaluate("() => document.querySelector('#picImg').naturalWidth") > 0


def shot(page, name, folder=None):
    folder = folder or QA
    page.wait_for_timeout(350)  # let slide-in animations settle
    # Headless Chrome now and then stalls on a capture while animations run:
    # freeze them for the picture and retry once.
    for attempt in (1, 2):
        try:
            page.screenshot(path=str(folder / f"{name}.png"), animations="disabled", timeout=15000)
            return
        except Exception:
            if attempt == 2:
                raise


def flow(run, browser, base, name, opts, words, themes):
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 800, "event": True}, errors)
    min_tap = MIN_TAP["ipad" if name.startswith("ipad") else "phone"]
    lay = lambda where: run.check(not (bad := page.evaluate(LAYOUT_CHECK, min_tap)), f"[{name}] layout {where} {bad if bad else ''}".rstrip())
    lay("home")
    shot(page, f"{name}-home")
    page.click("#startBtn", force=True)
    spoken = page.evaluate("() => window.__speech.calls")
    run.check(len(spoken) >= 1 and spoken[0]["volume"] == 0, f"[{name}] Start speaks a silent unlock utterance")
    run.check(zh_said(page, 0, "themes.pick"), f"[{name}] theme screen instruction plays the recorded Chinese line")
    page.wait_for_selector("#themes:not([hidden])")
    run.check(page.locator(".theme-card:not(.review-card)").count() == len(themes) and page.locator(".review-card").count() == 1, f"[{name}] {len(themes)} theme cards plus today's review")
    lay("themes")
    shot(page, f"{name}-themes")
    page.wait_for_timeout(600)  # voices arrive at 800ms

    for t_index, th in enumerate(themes):
        if name not in FULL_RUN and t_index > 0:
            break
        tw = [w for w in words if w["theme"] == th["id"]]
        n, a = calls(page), audios(page)
        page.click(f'.theme-card[data-theme="{th["id"]}"]')
        page.wait_for_selector("#cards:not([hidden])")
        if t_index == 0:
            heard_first = page.evaluate("(n) => window.__speech.calls.slice(n).filter(c => c.text.trim()).length", n)
            # The word waits for the how-to to finish (heard_first == 0 right after the tap).
            run.check(zh_said(page, a, "cards.howto") and heard_first == 0 and wait_word(page, n, tw[0]["english"]),
                      f"[{name}] first card: recorded Chinese how-to, then the word, spoken automatically")
        else:
            opened = page.evaluate("() => window.__speech.calls")[n:]
            run.check([c["text"] for c in opened] == [tw[0]["english"]], f"[{name}] opening a theme speaks the first word")
        for i, w in enumerate(tw):
            run.check(page.inner_text("#wordEn") == w["english"], f"[{name}] card {w['id']} shows '{w['english']}'")
            run.check(page.inner_text("#progress").replace(" ", "") == f"{i + 1}/{len(tw)}", f"[{name}] progress {i + 1}/{len(tw)}")
            run.check(image_ok(page), f"[{name}] image loads: {w['image']}")
            page.wait_for_timeout(300)  # slide-in animation moves the card sideways
            lay(f"card {w['id']}")
            n = calls(page)
            page.click("#pic")
            tilt = page.evaluate(TILT, "#picImg")
            run.check(0 < tilt <= 15, f"[{name}] tapping {w['id']}: side-to-side sway, no spin (max tilt {tilt:g}°)")
            c = last_call(page)
            run.check(calls(page) == n + 1 and c["text"] == w["english"] and c["lang"] == "en-US" and 0.8 <= c["rate"] <= 0.9,
                      f"[{name}] tap picture speaks '{w['english']}' en-US {c and c['rate']}")
            if i == 0:
                run.check(c["voice"] == "Samantha", f"[{name}] late-loaded en-US voice chosen ({c['voice']})")
                fx = page.evaluate("() => ({anims: document.querySelector('#picImg').getAnimations().length, osc: window.__osc})")
                run.check(fx["anims"] == 1 and fx["osc"] > 0, f"[{name}] tapping the picture plays an action and a sound {fx}")
                if t_index == 0:
                    for _ in range(6):
                        page.click("#pic", delay=0)
                    fx = page.evaluate("() => document.querySelector('#picImg').getAnimations().length")
                    run.check(fx <= 1, f"[{name}] fast repeated taps do not stack actions ({fx})")
                    page.wait_for_timeout(900)
                    run.check(page.evaluate("() => document.querySelector('#picImg').getAnimations().length") == 0,
                              f"[{name}] picture action finishes within 0.9s")
                shot(page, f"{name}-card-{w['id']}")
            if i < len(tw) - 1:
                page.click("#nextBtn")
                run.check(last_call(page)["text"] == tw[i + 1]["english"], f"[{name}] Next speaks the new word")
        n = calls(page)
        page.click("#sayBtn")
        run.check(calls(page) == n + 1 and last_call(page)["text"] == tw[-1]["english"], f"[{name}] speaker button speaks")
        n, a = calls(page), audios(page)
        page.click("#nextBtn")  # last card wraps to the first
        run.check(page.inner_text("#progress").replace(" ", "") == f"1/{len(tw)}", f"[{name}] after last card starts again")
        run.check(wait_word(page, n, tw[0]["english"]) and zh_said(page, a, "cards.done"),
                  f"[{name}] finishing the deck gives recorded praise, then the first word")
        if t_index == 0:
            # Tim 2026-10-23: right after the jump back the card must not wait for the praise.
            for _ in tw[1:]:
                page.click("#nextBtn")
            n, a = calls(page), audios(page)
            page.click("#nextBtn")  # wrap again
            page.wait_for_timeout(100)
            page.click("#nextBtn")  # the child taps on at once
            run.check(page.inner_text("#progress").replace(" ", "") == f"2/{len(tw)}" and last_call(page)["text"] == tw[1]["english"],
                      f"[{name}] tapping Next right after the jump back moves on and speaks '{tw[1]['english']}' at once")
            page.wait_for_timeout(900)
            run.check(not zh_said(page, a, "cards.done") and last_call(page)["text"] == tw[1]["english"],
                      f"[{name}] ...and the cut-off praise does not play afterwards")
            page.click("#prevBtn")
        a = audios(page)
        page.click('#cards [data-go="themes"]')
        page.wait_for_selector("#themes:not([hidden])")
        run.check(zh_said(page, a, "themes.pick"), f"[{name}] back on themes: recorded Chinese instruction again")

    # Chinese toggle and swipe on the first theme.
    page.click(".theme-card:not(.review-card) >> nth=0")
    run.check(not page.is_visible("#wordZh") or page.evaluate("getComputedStyle(document.querySelector('#wordZh')).visibility") == "hidden",
              f"[{name}] Chinese hidden by default")
    page.click("#zhBtn")
    vis = page.evaluate("getComputedStyle(document.querySelector('#wordZh')).visibility")
    run.check(vis == "visible" and page.inner_text("#wordZh") == words[0]["chinese"], f"[{name}] Chinese toggle shows '{words[0]['chinese']}'")
    lay("card with Chinese")
    shot(page, f"{name}-card-chinese")
    page.click("#zhBtn")
    run.check(page.is_visible("#wordEn"), f"[{name}] English word shown by default")
    page.click("#enBtn")
    run.check(not page.is_visible("#wordEn"), f"[{name}] English text can be turned off")
    lay("card without text")
    shot(page, f"{name}-card-no-text")
    page.click("#enBtn")
    box = page.locator("#stage").bounding_box()
    y = box["y"] + box["height"] / 2
    for x0, x1, want in ((0.8, 0.2, 2), (0.2, 0.8, 1)):
        page.mouse.move(box["x"] + box["width"] * x0, y)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * x1, y, steps=6)
        page.mouse.up()
        run.check(page.inner_text("#progress").startswith(f"{want} "), f"[{name}] swipe goes to card {want}")
    run.check(not zh_tts(page), f"[{name}] every Chinese line came from a recording, none from TTS {zh_tts(page)}")
    run.check(not errors, f"[{name}] no console/page errors or 4xx/5xx {errors if errors else ''}".rstrip())
    ctx.close()


def special_cases(run, browser, base, words):
    opts = VIEWPORTS["ipad-portrait"]
    first = words[0]

    # Every action and every word's tap move: rocking only, at most 15 degrees.
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    moves = page.evaluate("""(words) => {
      const box = document.body.appendChild(document.createElement('div'));
      const out = {};
      Fx.moves.forEach(m => { Fx.move(box, m); out[m] = box.getAnimations()[0].effect.getKeyframes().map(k => k.transform); });
      box.remove();
      return { frames: out, wordMoves: [...new Set(words.map(w => Fx.actFor(w).move))] };
    }""", words)
    run.check(not {"spin", "hop", "jelly", "pop"} & set(moves["frames"]), f"[fx] no spin/hop/jelly/pop moves remain {sorted(moves['frames'])}")
    run.check(set(moves["wordMoves"]) <= {"wiggle", "swing", "sway"}, f"[fx] word taps use only sways {moves['wordMoves']}")
    worst = max(abs(float(d)) for fr in moves["frames"].values() for t in fr for d in re.findall(r"rotate\((-?[\d.]+)deg", t or "") or [0])
    run.check(worst <= 15 and not any("turn" in (t or "") for fr in moves["frames"].values() for t in fr),
              f"[fx] no move tilts more than 15 degrees (max {worst:g})")
    run.check(not errors, f"[fx] no errors {errors if errors else ''}".rstrip())
    ctx.close()

    # Voices without a voiceschanged event: the polling fallback must find them.
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 1200, "event": False}, errors)
    page.click("#startBtn", force=True)
    page.click(".theme-card:not(.review-card) >> nth=0")
    page.wait_for_timeout(1700)
    page.click("#sayBtn")
    page.wait_for_timeout(50)
    run.check(last_call(page)["voice"] == "Samantha", "[polling] voices found without voiceschanged event")
    run.check(not errors, f"[polling] no errors {errors if errors else ''}".rstrip())
    ctx.close()

    # Real recorded Chinese lines: every mp3 decodes in the browser, and one
    # plays end to end on the Start tap without any zh-TW TTS.
    voice = json.loads((ROOT / "data/voice-zh.json").read_text())
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors, real_voice=True)
    decoded = page.evaluate("""async () => {
      const keys = Object.keys(await (await fetch('audio/zh/manifest.json')).json());
      const ac = new OfflineAudioContext(1, 1, 24000);
      const out = {};
      for (const k of keys) {
        try { out[k] = (await ac.decodeAudioData(await (await fetch('audio/zh/' + k + '.mp3')).arrayBuffer())).duration; }
        catch (e) { out[k] = -1; }
      }
      return out;
    }""")
    bad = {k: d for k, d in decoded.items() if not 0.3 < d < 15}
    run.check(len(decoded) == len(voice) + len(json.loads((ROOT / "data/themes.json").read_text())) and not bad,
              f"[voice] all {len(decoded)} recorded lines decode, 0.3–15s each {bad if bad else ''}".rstrip())
    page.click("#startBtn", force=True)
    page.wait_for_timeout(3500)
    played = page.evaluate("""() => window.__audioEls.filter(e => e.src.includes('/audio/zh/themes.pick.mp3'))
                                      .map(e => ({ended: e.ended, t: e.currentTime, err: e.error && e.error.code}))""")
    run.check(played and (played[-1]["ended"] or played[-1]["t"] > 0.5) and not played[-1]["err"] and not zh_tts(page),
              f"[voice] real mp3 plays on the first tap, no zh-TW TTS {played}")
    run.check(not errors, f"[voice] no errors {errors if errors else ''}".rstrip())
    ctx.close()

    # A missing recording falls back to reading the same line with zh-TW TTS.
    errors = []
    ctx = browser.new_context(**opts)
    fast_voice(ctx)
    # Registered last, so it wins over fast_voice for this one file.
    ctx.route("**/audio/zh/themes.pick.mp3", lambda r: r.fulfill(status=404, body="not found"))
    ctx.add_init_script(FAKE_SPEECH + '({"lateMs": 0, "event": true})')
    page = ctx.new_page()
    watch(page, errors, allow=("themes.pick.mp3",))
    page.goto(base)
    page.wait_for_selector("#startBtn:not([disabled])")
    page.click("#startBtn", force=True)
    page.wait_for_timeout(800)
    run.check(not zh_tts(page) and page.locator("#toast").is_visible(), "[voice] missing Chinese mp3 shows visible error without TTS")
    errors = [e for e in errors if "404" not in e]
    run.check(not errors, f"[voice-missing] no other errors {errors if errors else ''}".rstrip())
    ctx.close()

    # A word with an audio file plays it instead of TTS; a broken one falls back.
    wav = beep_wav()
    for label, audio, expect_tts in (("audio-ok", "audio/words/test-beep.wav", False), ("audio-missing", "audio/words/missing.wav", True)):
        errors = []
        ctx = browser.new_context(**opts)
        fast_voice(ctx)
        ctx.add_init_script(FAKE_SPEECH + '({"lateMs": 0, "event": true})')
        patched = [dict(w, audio=audio) if w["id"] == first["id"] else w for w in words]
        ctx.route("**/data/words.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(patched)))
        ctx.route("**/audio/words/test-beep.wav", lambda r: r.fulfill(status=200, content_type="audio/wav", body=wav))
        ctx.route("**/audio/words/missing.wav", lambda r: r.fulfill(status=404, body="not found"))
        page = ctx.new_page()
        watch(page, errors, allow=("missing.wav",))
        page.goto(base)
        page.wait_for_selector("#startBtn:not([disabled])")
        page.click("#startBtn", force=True)
        page.click(f'.theme-card[data-theme="{first["theme"]}"]')
        page.wait_for_timeout(600)
        played = page.evaluate("() => window.__audio")
        spoke = [c["text"] for c in page.evaluate("() => window.__speech.calls")]
        run.check(any(audio in u for u in played), f"[{label}] <audio> played {audio}")
        if expect_tts:
            run.check(first["english"] in spoke, f"[{label}] fell back to TTS '{first['english']}'")
        else:
            run.check(first["english"] not in spoke, f"[{label}] TTS not used when audio plays")
        # The 404 is the point of this case; the browser also logs it without a URL.
        errors = [e for e in errors if "missing.wav" not in e and not (expect_tts and "404" in e)]
        run.check(not errors, f"[{label}] no other errors {errors if errors else ''}".rstrip())
        ctx.close()

    # No speechSynthesis at all: friendly message, nothing breaks.
    errors = []
    ctx, page = open_site(browser, base, opts, {"unsupported": True}, errors)
    page.click("#startBtn", force=True)
    run.check(page.is_visible("#toast") and "不能朗讀" in page.inner_text("#toast"), "[unsupported] friendly message shown")
    page.click(".theme-card:not(.review-card) >> nth=0")
    page.click("#sayBtn")
    run.check(image_ok(page), "[unsupported] cards still work")
    shot(page, "unsupported-message")
    run.check(not errors, f"[unsupported] no errors {errors if errors else ''}".rstrip())
    ctx.close()


def contact_sheet(browser, base, words, themes):
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    page.goto(base)
    names = {t["id"]: t["chinese"] for t in themes}
    cells = "".join(
        f'<figure><img src="{w["image"]}"><figcaption><b>{w["english"]}</b> {w["chinese"]}<small>{names[w["theme"]]} · {w["id"]}</small></figcaption></figure>'
        for w in words)
    page.set_content(
        "<style>body{margin:0;padding:16px;background:#fff6e5;font-family:system-ui,sans-serif;color:#2b3a55;"
        "display:grid;grid-template-columns:repeat(5,1fr);gap:14px}figure{margin:0;background:#fff;border:3px solid #2b3a55;"
        "border-radius:20px;padding:10px;text-align:center}img{width:100%;aspect-ratio:1}figcaption{font-size:20px}"
        "small{display:block;font-size:13px;color:#5d6b85}</style>" + cells)
    page.wait_for_function("() => [...document.images].every(i => i.complete && i.naturalWidth > 0)")
    page.screenshot(path=str(QA / "contact-sheet.png"), full_page=True)
    page.close()


# ---------------------------------------------------------------- games (phase 2)

# Largest tilt (degrees) in the running animations of an element; spins count as 360.
TILT = """(sel) => {
  const deg = t => {
    let m = 0;
    for (const r of String(t || '').matchAll(/rotate[Z]?\\(\\s*(-?[\\d.]+)(deg|turn|rad)?/g)) {
      const v = Math.abs(parseFloat(r[1]));
      m = Math.max(m, r[2] === 'turn' ? v * 360 : r[2] === 'rad' ? v * 57.3 : v);
    }
    return m;
  };
  const el = document.querySelector(sel);
  return Math.max(0, ...el.getAnimations().flatMap(a => a.effect.getKeyframes().map(k => deg(k.transform) + deg(k.rotate))));
}"""

# The answer is found the way a child would: from the English word that
# was spoken, never from text on screen.
NO_TEXT = """(sel) => [...document.querySelectorAll(sel)].filter(e => e.innerText.trim()).map(e => e.innerText.trim())"""


def speech_diagnostic(page, since):
    print("speech wait diagnostic: " + json.dumps(page.evaluate("""n => ({
      since: n, calls: window.__speech.calls.slice(-8), audio: window.__audio.slice(-8),
      events: window.__mediaEvents.slice(-20),
      media: window.__audioEls.slice(-1).map(a => ({src: a.src, paused: a.paused,
        ended: a.ended, currentTime: a.currentTime, duration: a.duration,
        readyState: a.readyState, error: a.error && a.error.code})),
      visibility: document.visibilityState, game: document.querySelector('#play').dataset.game,
      screen: document.querySelector('.screen:not([hidden])').id
    })""", since)), flush=True)


def heard_after(page, since, timeout=8000):
    """The first English word spoken after speech mark `since`, waiting for it.
    Words can be queued behind a Chinese line (round intro, ask-again line),
    so a fixed wait may still read the previous word."""
    try:
        text = page.wait_for_function("""(n) => {
          const c = window.__speech.calls.slice(n).find(c => c.lang === 'en-US' && c.text.trim());
          return c ? c.text : false;
        }""", arg=since, timeout=timeout).json_value()
    except Exception:
        speech_diagnostic(page, since)
        raise
    return BY_EN.get(text)


# Speech mark taken just before a round is opened (open_game / start_review),
# so its first, queued word is found reliably.
SPEECH_MARK = {"n": 0}


def to_games(page, base):
    """Back to the games menu; if no back button is visible (a stuck round),
    reload the page and enter the games again so later checks still run."""
    try:
        page.click('[data-go="games"] >> visible=true', timeout=3000)
    except Exception:
        page.goto(base)
        page.wait_for_selector("#startBtn:not([disabled])")
        page.click("#startBtn", force=True)
        page.wait_for_selector("#themes:not([hidden])")
        page.click("#gamesBtn", force=True)
    page.wait_for_selector("#games:not([hidden])")


def wait_q(page, q):
    page.wait_for_function("(q) => document.querySelector('#play').dataset.q === String(q) || !document.querySelector('#result').hidden", arg=q, timeout=15000)


def wait_result(page):
    page.wait_for_selector("#result:not([hidden])", timeout=20000)
    page.wait_for_timeout(700)  # stars pop in
    return int(page.get_attribute("#resultStars", "data-stars"))


def open_game(page, game):
    a = audios(page)
    SPEECH_MARK["n"] = calls(page)
    page.click(f'.game-card[data-game="{game}"]')
    page.wait_for_selector("#play:not([hidden])")
    return a


def pick_game(run, page, name, game, by_english, shots, selector, tap):
    """listen: one wrong answer, then every question right."""
    a = open_game(page, game)
    page.wait_for_timeout(400)
    run.check(zh_said(page, a, f"intro.{game}"), f"[{name}/{game}] how-to plays the recorded Chinese line first")
    run.check(not page.evaluate(NO_TEXT, selector), f"[{name}/{game}] answer buttons have no text")
    play_listen(run, page, name, game, shots, QA2, selector, tap)


def play_listen(run, page, name, label, shots, folder, selector=".choices .pick", tap=None):
    """Play a listen round from its first question: miss Q1 once, then all right.
    The missed word must come back once at the end (7 questions). Returns asked ids."""
    tap = tap or (lambda sel: page.click(sel))
    asked = []
    q = 0
    a0 = audios(page)
    since = SPEECH_MARK["n"]
    while page.is_hidden("#result"):
        target = heard_after(page, since)
        opts = page.eval_on_selector_all(selector, "els => els.map(e => e.dataset.word)")
        if not run.check(target in opts, f"[{name}/{label}] Q{q + 1}: heard word '{target}' is one of the pictures"):
            return asked
        asked.append(target)
        if q == 0:
            wrong = next(o for o in opts if o != target)
            n, a = calls(page), audios(page)
            tap(f'{selector}[data-word="{wrong}"]')
            page.wait_for_timeout(250)
            run.check(page.get_attribute(f'{selector}[data-word="{wrong}"]', "class").find("is-wrong") >= 0, f"[{name}/{label}] wrong picture is softly marked")
            run.check(zh_said(page, a, "game.try_again") and wait_word(page, n, by_english_rev(BY_EN)[target]),
                      f"[{name}/{label}] wrong answer: recorded gentle hint, then the word again")
            if shots:
                shot(page, f"{name}-{label}-wrong", folder)
        a = audios(page)
        since = calls(page)  # the next question's word is the next English word
        tap(f'{selector}[data-word="{target}"]')
        page.wait_for_timeout(150)
        if q == 0:
            run.check(zh_said(page, a, "praise.") and page.evaluate("() => window.__osc") > 0, f"[{name}/{label}] right answer: recorded praise and sound")
            if shots:
                shot(page, f"{name}-{label}-right", folder)
        # Fixed file name every run: the ask-again question, or (when the missed
        # word already came back as Q6) that second try.
        if shots and (q == 6 or (q == 5 and asked[5] == asked[0])):
            shot(page, f"{name}-{label}-asked-again", folder)
        q += 1
        wait_q(page, q)
    stars = wait_result(page)
    # Q1 was missed. It comes back once at the end, unless it already came back
    # as question 6 (small themes repeat words) — then that was its second try.
    came_back_as_q6 = len(asked) >= 6 and asked[5] == asked[0]
    want = 6 if came_back_as_q6 else 7
    run.check(len(asked) == want and (came_back_as_q6 or asked[6] == asked[0]) and page.locator("#dots .dot").count() == want,
              f"[{name}/{label}] the missed word gets one more try at the end: {asked}")
    run.check(all(asked[i] != asked[i - 1] for i in range(1, len(asked))), f"[{name}/{label}] never the same word twice in a row {asked}")
    told = ask_again_count(page, a0)
    run.check(told == (want - 6), f"[{name}/{label}] recorded 'that word again' line before the ask-again question: played {told}x")
    run.check(stars == 3, f"[{name}/{label}] one mistake -> {stars} stars")
    return asked


def ask_again_count(page, since):
    """How many times the recorded ask-again line played since audio mark `since`."""
    return sum("/audio/zh/game.ask_again.mp3" in u for u in page.evaluate("() => window.__audio")[since:])


def by_english_rev(by_english):
    return {v: k for k, v in by_english.items()}


def memory_game(run, page, name, shots):
    open_game(page, "memory")
    play_memory(run, page, name, "memory", shots, QA2)


def play_memory(run, page, name, label, shots, folder):
    """Play a memory round: one wrong pair, then every pair. Returns the words on the board."""
    page.wait_for_timeout(300)
    cards = page.eval_on_selector_all(".mcard", "els => els.map(e => e.dataset.word)")
    run.check(len(cards) == 12 and all(cards.count(c) == 2 for c in cards), f"[{name}/{label}] 12 cards in 6 pairs")
    run.check(not page.evaluate(NO_TEXT, ".mcard"), f"[{name}/{label}] cards have no text")
    pos = {}
    for i, c in enumerate(cards):
        pos.setdefault(c, []).append(i)
    a, b = list(pos)[:2]
    n = calls(page)
    page.click(f".mcard >> nth={pos[a][0]}")
    page.click(f".mcard >> nth={pos[b][0]}")
    run.check([c["text"] for c in page.evaluate("() => window.__speech.calls")[n:] if c["lang"] == "en-US"][-1:] == [by_english_rev(BY_EN)[b]],
              f"[{name}/{label}] flipping a card says its word")
    # P5-a: a tap while the wrong pair waits to turn back rocks that card, no flip.
    other = next(i for i, c in enumerate(cards) if c not in (a, b))
    page.click(f".mcard >> nth={other}")
    rocked = page.evaluate("""i => { const c = document.querySelectorAll('.mcard')[i];
      const anims = c.getAnimations();
      const turns = anims.flatMap(a => a.effect.getKeyframes()).map(k => k.transform || '').filter(t => /rotate/.test(t))
        .map(t => Math.abs(parseFloat(t.match(/rotate\\((-?[\\d.]+)deg/)[1])));
      return {anims: anims.length, open: c.classList.contains('is-open'), tilt: Math.max(0, ...turns), flip: anims.some(a => JSON.stringify(a.effect.getKeyframes()).includes('rotateY'))}; }""", other)
    run.check(rocked["anims"] > 0 and not rocked["open"] and rocked["tilt"] <= 15 and not rocked["flip"],
              f"[{name}/{label}] a tap while the wrong pair waits rocks that card, no flip {rocked}")
    if shots:
        shot(page, f"{name}-{label}-wrong", folder)
    try:
        page.wait_for_function("() => document.querySelector('.memory').dataset.busy === '0'", timeout=5000)
    except Exception as exc:
        state = page.evaluate("""() => ({screen: [...document.querySelectorAll('.screen')].filter(s => !s.hidden).map(s => s.id),
          play: {...document.querySelector('#play').dataset}, busy: document.querySelector('.memory') && document.querySelector('.memory').dataset.busy,
          open: document.querySelectorAll('.mcard.is-open').length, audio: window.__audio.slice(-4)})""")
        raise RuntimeError(f"[{name}/{label}] wrong pair never turned back: {state}") from exc
    run.check(page.locator(".mcard.is-open").count() == 0, f"[{name}/{label}] a wrong pair turns back over")
    for k, (word, (i, j)) in enumerate(pos.items()):
        page.click(f".mcard >> nth={i}")
        page.click(f".mcard >> nth={j}")
        run.check(page.locator(".mcard.is-done").count() == 2 * (k + 1), f"[{name}/{label}] pair {k + 1} found")
        if k == 0 and shots:
            page.wait_for_timeout(900)
            shot(page, f"{name}-{label}-right", folder)
        page.wait_for_timeout(300)
    stars = wait_result(page)
    run.check(stars == 3, f"[{name}/{label}] one wrong pair -> {stars} stars")
    return list(pos)


def match_game(run, page, name, shots):
    open_game(page, "match")
    play_match(run, page, name, "match", shots, QA2)


def play_match(run, page, name, label, shots, folder):
    """Play a match round: one wrong join on the first board, the rest right.
    The missed word is asked once more at the end as one listen-and-pick
    question. Returns the boards (word ids)."""
    page.wait_for_timeout(300)
    run.check(not page.evaluate(NO_TEXT, ".match-say, .match-pic"), f"[{name}/{label}] board has no text")
    boards, missed, done, again = [], None, 0, []
    a0 = audios(page)
    since = calls(page)
    while page.is_hidden("#result"):
        page.wait_for_function("(d) => !document.querySelector('#result').hidden || document.querySelector('.choices .pick[data-again]') || (document.querySelector('#play').dataset.q === String(d) && document.querySelectorAll('.match-say').length && !document.querySelector('.match-say.is-done'))",
                               arg=done, timeout=15000)
        if not page.is_hidden("#result"):
            break
        if page.locator(".choices .pick[data-again]").count():
            # Ask-again question: hear the missed word (queued after the
            # spoken ask-again line), pick its picture.
            target = heard_after(page, since)
            again.append(target)
            opts = page.eval_on_selector_all(".choices .pick", "els => els.map(e => e.dataset.word)")
            run.check(target in opts and len(opts) == 4 and not page.evaluate(NO_TEXT, ".choices .pick"),
                      f"[{name}/{label}] ask-again question: heard '{target}', 4 pictures, no text")
            if shots:
                shot(page, f"{name}-{label}-asked-again", folder)
            since = calls(page)
            page.click(f'.choices .pick[data-word="{target}"]')
            page.wait_for_function("(q) => !document.querySelector('#result').hidden || document.querySelector('#play').dataset.q !== q",
                                   arg=page.get_attribute("#play", "data-q"), timeout=15000)
            continue
        says = page.eval_on_selector_all(".match-say", "els => els.map(e => e.dataset.word)")
        boards.append(says)
        if len(boards) == 1:
            a = audios(page)
            n = calls(page)
            page.click(".match-say >> nth=0")
            heard = heard_after(page, n)
            run.check(heard == says[0], f"[{name}/{label}] speaker says its word ({heard})")
            missed = says[0]
            wrong = next(w for w in says if w != says[0])
            page.click(f'.match-pic[data-word="{wrong}"]')
            page.wait_for_timeout(200)
            run.check(zh_said(page, a, "game.try_again"), f"[{name}/{label}] wrong picture: recorded gentle hint, word again")
            if shots:
                shot(page, f"{name}-{label}-wrong", folder)
        for k, w in enumerate(says):
            if len(boards) == 1 and k == 0:
                # Drag a line from the speaker to the picture.
                a = page.locator(f'.match-say[data-word="{w}"]').bounding_box()
                b = page.locator(f'.match-pic[data-word="{w}"]').bounding_box()
                page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
                page.mouse.down()
                page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=8)
                page.mouse.up()
                page.wait_for_timeout(200)
                run.check(page.locator(".match-lines g").count() == 1, f"[{name}/{label}] dragging a line joins a pair")
                if shots:
                    shot(page, f"{name}-{label}-right", folder)
            else:
                page.click(f'.match-say[data-word="{w}"]')
                page.click(f'.match-pic[data-word="{w}"]')
            since = calls(page)  # anything English after the last join is the next question
            done += 1
            if k < len(says) - 1:  # after the last, the next board replaces this one
                run.check(page.locator(".match-pic.is-done").count() == k + 1 and page.locator(".match-lines g").count() == k + 1,
                          f"[{name}/{label}] board {len(boards)}: {k + 1} line(s) drawn")
            page.wait_for_timeout(250)
    stars = wait_result(page)
    run.check(len(boards) == 2 and again == [missed] and page.locator("#dots .dot").count() == done + 1,
              f"[{name}/{label}] no extra board; the missed word ({missed}) asked once more as one question {again}")
    told = ask_again_count(page, a0)
    run.check(told == 1, f"[{name}/{label}] recorded 'that word again' line before the ask-again question: played {told}x")
    run.check(stars == 3, f"[{name}/{label}] {done} pairs, one mistake -> {stars} stars")
    return boards


BY_EN = {}


def fixed_order(page, order):
    """The next listen round asks exactly these words, in this order."""
    page.evaluate("""(order) => {
      const orig = Quiz.questions;
      Quiz.questions = function (opts) {
        Quiz.questions = orig;
        const byId = Object.fromEntries(opts.words.map(w => [w.id, w]));
        return Quiz.questionsFor(order.map(id => byId[id]), opts.words, 4, Math.random);
      };
    }""", order)


def last_miss_case(run, page, name):
    """8-word theme, Q1–Q5 right, only Q6 missed: the word must still be asked
    again, but not straight after itself — an easy word from the round comes
    first (not recorded), then the missed word."""
    order = ["goat", "cow", "koala", "lion", "zebra", "wolf"]
    fixed_order(page, order)
    open_game(page, "listen")
    page.wait_for_timeout(300)
    a0 = audios(page)
    asked, q, bridge_before = [], 0, None
    since = SPEECH_MARK["n"]
    while page.is_hidden("#result"):
        target = heard_after(page, since)
        asked.append(target)
        if q == 6:
            bridge_before = page.evaluate("(id) => Progress.get(id)", target)
        if q == 5:
            opts = page.eval_on_selector_all(".choices .pick", "els => els.map(e => e.dataset.word)")
            n = calls(page)
            page.click(f'.choices .pick[data-word="{next(o for o in opts if o != target)}"]')
            wait_word(page, n, by_english_rev(BY_EN)[target])  # the word is said again first
        since = calls(page)
        page.click(f'.choices .pick[data-word="{target}"]')
        if q == 7:
            shot(page, f"{name}-listen-last-miss-asked-again", QA2)
        q += 1
        wait_q(page, q)
    wait_result(page)
    run.check(len(asked) == 8 and asked[:6] == order and asked[7] == "wolf" and asked[6] in order[:5],
              f"[{name}/listen-last-miss] missed in the last question: an easy word, then asked again {asked}")
    run.check(all(asked[i] != asked[i - 1] for i in range(1, len(asked))), f"[{name}/listen-last-miss] never the same word twice in a row")
    after = page.evaluate("(id) => Progress.get(id)", asked[6])
    run.check(after == bridge_before, f"[{name}/listen-last-miss] the in-between word is not recorded ({asked[6]})")
    run.check(ask_again_count(page, a0) == 1, f"[{name}/listen-last-miss] recorded 'that word again' line played once")


def repeat_case(run, page, name):
    """The case seen in review: a 5-word theme, Q1 missed and the same word back
    as Q6. Its second try is Q6, so no extra question follows (no 'witch, witch')."""
    order = ["witch", "vampire", "zombie", "monster", "pumpkin", "witch"]
    fixed_order(page, order)
    open_game(page, "listen")
    page.wait_for_timeout(300)
    asked = play_listen(run, page, name, "listen-repeat", False, QA2)
    run.check(asked == order, f"[{name}/listen-repeat] Q1 missed and back as Q6: 6 questions, no repeat {asked}")


def games_flow(run, browser, base, name, opts, words):
    BY_EN.update({w["english"]: w["id"] for w in words})
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    min_tap = MIN_TAP["ipad" if name.startswith("ipad") else "phone"]
    lay = lambda where: run.check(not (bad := page.evaluate(LAYOUT_CHECK, min_tap)), f"[{name}] layout {where} {bad if bad else ''}".rstrip())
    full = name in FULL_RUN or name == "phone-portrait"
    if not page.locator("#gamesBtn").is_visible(): page.click("#startBtn", force=True)
    page.click("#gamesBtn", force=True)
    page.wait_for_selector("#games:not([hidden])")
    run.check(zh_said(page, 0, "games.pick"), f"[{name}] game menu is introduced by the recorded voice")
    run.check(page.eval_on_selector_all(".game-card", "els => els.map(e => e.dataset.game)") == ["listen", "match", "memory"],
              f"[{name}] 3 games in the menu: listen, match, memory")
    lay("game menu")
    shot(page, f"{name}-menu", QA2)
    # Theme chip: Halloween only (5 words, so some rounds borrow other words).
    a = audios(page)
    page.click('.chip[data-theme="halloween"]')
    run.check(zh_said(page, a, "theme.halloween"), f"[{name}] theme chip says its recorded name")
    tap = lambda sel: page.click(sel)

    def guarded(label, fn):
        # A stuck round is reported as a failure with where it stopped, then the run goes on.
        try:
            fn()
        except Exception as e:
            import traceback
            print(traceback.format_exc(), flush=True)
            print("game wait diagnostic: " + json.dumps(page.evaluate("""() => ({
              screen: document.querySelector('.screen:not([hidden])').id,
              buttons: [...document.querySelectorAll('#againBtn, #play [data-go], #themeChips .chip')]
                .map(b => ({id: b.id, go: b.dataset.go, theme: b.dataset.theme,
                  visible: !!b.getClientRects().length, disabled: b.disabled}))
            })""")), flush=True)
            q = page.evaluate("() => [document.querySelector('#play').dataset.game, document.querySelector('#play').dataset.q]")
            run.check(False, f"[{name}/{label}] stopped at game/question {q}: {str(e).splitlines()[0]}")
            to_games(page, base)

    def listen():
        pick_game(run, page, name, "listen", BY_EN, full, ".choices .pick", tap)
        lay("listen result")
        shot(page, f"{name}-listen-result", QA2)
        page.click("#againBtn")
        page.wait_for_selector("#play:not([hidden])")
        run.check(page.locator(".choices .pick").count() == 4, f"[{name}] play again restarts the game")
        page.click("#play [data-go=games]")
        if full:
            page.click('.chip[data-theme=""]')

    def memory():
        memory_game(run, page, name, full)
        lay("memory result")
        shot(page, f"{name}-memory-result", QA2)
        page.click("#result [data-go=games]")

    def match():
        match_game(run, page, name, full)
        shot(page, f"{name}-match-result", QA2)

    for label, fn in (("listen", listen), ("memory", memory), ("match", match)):
        guarded(label, fn)
    if name == "ipad-portrait":
        to_games(page, base)
        guarded("listen-repeat", lambda: repeat_case(run, page, name))
    if name in ("ipad-portrait", "ipad-pro"):
        to_games(page, base)
        guarded("listen-last-miss", lambda: last_miss_case(run, page, name))
    if full:
        # In-game layouts at this size.
        for game in ("listen", "memory", "match"):
            to_games(page, base)
            open_game(page, game)
            page.wait_for_timeout(600)
            lay(f"{game} board")
            shot(page, f"{name}-{game}-board", QA2)
    run.check(not zh_tts(page), f"[{name}] games: every Chinese line came from a recording, none from TTS {zh_tts(page)}")
    run.check(not errors, f"[{name}] games: no console/page errors or 4xx/5xx {errors if errors else ''}".rstrip())
    ctx.close()


# ---------------------------------------------------------------- progress (phase 3)

PROGRESS_SIZES = ("ipad-portrait", "ipad-landscape", "ipad-pro", "phone-portrait")
TZ = "Asia/Taipei"


def taipei(y, mo, d, h=0, mi=0):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return int(datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(TZ)).timestamp() * 1000)


STATE = """() => ({
  stars: Object.fromEntries([...document.querySelectorAll('.theme-card[data-theme]:not(.review-card)')].map(c => [c.dataset.theme, +c.querySelector('.theme-stars').dataset.stars])),
  due: +document.querySelector('.review-card').dataset.due,
  pics: [...document.querySelectorAll('.review-card .due-pics img')].map(i => i.dataset.word),
  more: !!document.querySelector('.review-card .due-more'),
  check: !!document.querySelector('.review-card .due-done'),
  picText: document.querySelector('.review-card .due-pics').innerText.trim(),
  jar: Progress.jar(),
  jarShown: [...document.querySelectorAll('#themes .jar-box')].map(b => [+b.dataset.stars, +b.dataset.full]),
  saved: localStorage.getItem('ew.progress')
})"""


def open_at(browser, base, opts, errors, when, seed=None, allow=()):
    """A device in Taipei whose clock reads `when` (ms), optionally starting from saved progress `seed`."""
    ctx = browser.new_context(timezone_id=TZ, **opts)
    fast_voice(ctx)
    ctx.add_init_script(FAKE_SPEECH + '({"lateMs": 0, "event": true})')
    # The clock keeps running across reloads (start time kept in sessionStorage).
    ctx.add_init_script("""(when => { const real = Date.now.bind(Date);
      let start = +sessionStorage.getItem('clockStart');
      if (!start) { start = real(); sessionStorage.setItem('clockStart', String(start)); }
      Date.now = () => when + (real() - start); })(%d)""" % when)
    if seed is not None:
        # Only on the first load of this "device", so reloads keep what the app saved.
        ctx.add_init_script("""(s => { if (!sessionStorage.getItem('seeded')) {
          localStorage.setItem('ew.progress', s); sessionStorage.setItem('seeded', '1'); } })(%s)""" % json.dumps(seed))
    page = ctx.new_page()
    watch(page, errors, allow)
    page.goto(base)
    page.wait_for_selector("#startBtn:not([disabled])")
    return ctx, page


def to_themes(page):
    page.click("#startBtn", force=True)
    page.wait_for_selector("#themes:not([hidden])")
    page.wait_for_timeout(200)
    return page.evaluate(STATE)


def back_to_themes(page):
    page.click('#result [data-go="themes"]')
    page.wait_for_selector("#themes:not([hidden])")
    page.wait_for_timeout(200)
    return page.evaluate(STATE)


def start_review(run, page, name, mode, want_intro):
    """Tap today's review; check the mode and its spoken opening. Returns the review word ids."""
    expected = page.evaluate("(words) => Progress.reviewSet(words, 6).list.map(w => w.id)", WORDS)
    a = audios(page)
    SPEECH_MARK["n"] = calls(page)
    page.click(".review-card")
    if mode == "cards":
        page.wait_for_selector("#cards:not([hidden])")
    else:
        page.wait_for_selector("#play:not([hidden])")
        run.check(page.get_attribute("#play", "data-game") == mode and page.get_attribute("#play", "data-mode") == "review",
                  f"[{name}] today's review plays {mode}")
    how = {"listen": "intro.listen", "match": "intro.match", "memory": "intro.memory", "cards": "cards.howto"}[mode]
    try:
        page.wait_for_function("""args => args.keys.every(key => window.__audio.slice(args.since).some(url => url.endsWith('/'+key+'.mp3')))""", arg={"since":a,"keys":[want_intro,how]},timeout=8000)
    except Exception:
        speech_diagnostic(page, SPEECH_MARK["n"])
        raise
    run.check(zh_said(page, a, want_intro) and zh_said(page, a, how), f"[{name}] {mode} review opens with '{want_intro}' then its how-to")
    return expected


def play_review_cards(run, page, name, shots):
    """Look through the review words in card mode. Like any deck (phase 9): praise,
    back to the first card, no stars and no result screen."""
    seen = []
    n = int(page.inner_text("#progress").split("/")[1])
    jar = page.evaluate("() => Progress.jar()")
    for i in range(n):
        seen.append(BY_EN[page.inner_text("#wordEn")])
        if i == 0 and shots:
            shot(page, f"{name}-review-cards", QA3)
        a = audios(page)
        page.click("#nextBtn")
        page.wait_for_timeout(150)
    page.wait_for_timeout(1200)
    run.check(zh_said(page, a, "cards.done") and not zh_said(page, a, "jar.more") and page.is_hidden("#result")
              and page.inner_text("#progress") == f"1 / {n}" and page.evaluate("() => Progress.jar()") == jar,
              f"[{name}/review-cards] looked through {len(seen)} cards: praise, start again, no stars")
    return seen


WORDS = []


def progress_flow(run, browser, base, name, opts, words):
    BY_EN.update({w["english"]: w["id"] for w in words})
    WORDS[:] = words
    big = name == "ipad-portrait"
    errors = []
    animals = [w["id"] for w in words if w["theme"] == "animals"]
    day0 = taipei(2026, 10, 22, 19, 0)

    # Day 0, 19:00, new device: nothing learned, empty jar.
    ctx, page = open_at(browser, base, opts, errors, day0)
    run.check(page.evaluate("() => document.querySelector('.home-jar').dataset.stars") == "0", f"[{name}] home shows the star jar (empty)")
    st = to_themes(page)
    run.check(set(st["stars"].values()) == {0} and st["due"] == 0 and st["check"] and st["jar"]["stars"] == 0,
              f"[{name}] new device: 0 stars, nothing to review, empty jar")
    shot(page, f"{name}-themes-new", QA3)

    # Look at every animal card: praise, but stars are only for games (Tim, phase 9).
    page.click('.theme-card[data-theme="animals"]')
    for _ in animals[1:]:
        page.click("#nextBtn")
    a = audios(page)
    page.click("#nextBtn")
    page.wait_for_timeout(1400)
    run.check(zh_said(page, a, "cards.done") and not zh_said(page, a, "jar.more") and not page.locator(".flying-star").count(),
              f"[{name}] finishing the deck: praise, no star flies to the jar")
    run.check(page.evaluate("() => Progress.jar().stars") == 0, f"[{name}] the jar is still empty")
    page.click('#cards [data-go="themes"]')
    page.wait_for_timeout(200)
    st = page.evaluate(STATE)
    saved = json.loads(st["saved"])
    run.check(st["stars"]["animals"] == 0 and st["stars"]["halloween"] == 0, f"[{name}] after the animal cards: no theme star yet {st['stars']}")
    run.check(all(saved["words"].get(i, {}).get("seen", 0) >= 1 for i in animals) and saved["version"] == 3,
              f"[{name}] every animal card recorded as seen (save version {saved['version']})")
    run.check(st["due"] == 0, f"[{name}] cards just seen are not due today")

    # Reload: progress and jar are kept.
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    st = to_themes(page)
    run.check(st["stars"]["animals"] == 0 and json.loads(st["saved"]) == saved and st["jarShown"] == [[0, 0]],
              f"[{name}] progress and star jar kept after reloading the page")

    # Nothing due: kind message, a listen practice round of the words never met.
    start_review(run, page, name, "listen", "review.none")
    asked = play_listen(run, page, name, "practice", big, QA3)
    halloween = {w["id"] for w in words if w["theme"] == "halloween"}
    run.check(halloween <= set(asked), f"[{name}] practice picks the words never met first {asked}")
    st = back_to_themes(page)
    rec = json.loads(st["saved"])["words"]
    run.check(st["jar"]["stars"] == 3, f"[{name}] the jar got the round's 3 stars ({st['jar']})")
    run.check(st["stars"]["halloween"] >= 1, f"[{name}] playing the words in a game gives the theme its first star {st['stars']}")
    missed = asked[0]
    run.check(rec[missed]["wrong"] == 1 and rec[missed]["box"] == 0 and rec[missed]["due"] == taipei(2026, 10, 23),
              f"[{name}] missed word ({missed}): asked again, then due tomorrow 0:00 — not 5 minutes later")
    run.check(st["due"] == 0 and st["check"], f"[{name}] right after the review nothing pops up to review again today")
    if big:
        shot(page, f"{name}-themes-jar-half", QA3)
    day0_save = st["saved"]
    stars_day0 = st["stars"]
    ctx.close()

    # Same evening 23:59: still nothing due. Next day 0:01: yesterday's words are due.
    errors_late = []
    ctx, page = open_at(browser, base, opts, errors_late, taipei(2026, 10, 22, 23, 59), seed=day0_save)
    st = to_themes(page)
    run.check(st["due"] == 0, f"[{name}] 23:59 the same day: nothing due yet")
    ctx.close()
    errors1 = []
    ctx, page = open_at(browser, base, opts, errors1, taipei(2026, 10, 23, 0, 1), seed=day0_save)
    st = to_themes(page)
    due_ids = page.evaluate("(words) => Progress.due(words).map(w => w.id)", words)
    want = min(5, len(due_ids))
    run.check(st["due"] == len(due_ids) and set(animals) <= set(due_ids) and len(st["pics"]) == want and st["pics"] == due_ids[:want]
              and st["more"] == (len(due_ids) > 5) and not st["check"] and st["picText"] == "",
              f"[{name}] 0:01 next day: {len(due_ids)} words due, shown as {len(st['pics'])} pictures{' + plus' if st['more'] else ''}, no text")
    run.check(all(st["stars"][k] >= v for k, v in stars_day0.items()), f"[{name}] theme stars never went down {stars_day0} -> {st['stars']}")
    shot(page, f"{name}-themes-due", QA3)

    # The review takes turns: match, memory, cards, listen — each on the review words.
    expected = start_review(run, page, name, "match", "review.intro")
    boards = play_match(run, page, name, "review-match", big or name == "ipad-landscape", QA3)
    run.check(set(boards[0] + boards[1]) == set(expected), f"[{name}] match review uses the review words")
    if name != "phone-portrait":
        shot(page, f"{name}-review-match-result", QA3)
    st = back_to_themes(page)
    expected = start_review(run, page, name, "memory", "review.intro")
    run.check(set(page.eval_on_selector_all(".mcard", "els => els.map(e => e.dataset.word)")) == set(expected),
              f"[{name}] memory review uses the review words")
    if big or name == "ipad-pro":
        shot(page, f"{name}-review-memory", QA3)
    play_memory(run, page, name, "review-memory", False, QA3)
    st = back_to_themes(page)
    expected = start_review(run, page, name, "cards", "review.intro")
    seen = play_review_cards(run, page, name, big or name == "ipad-landscape")
    run.check(seen == expected or set(seen) == set(expected), f"[{name}] card review shows every review word once {seen}")
    page.click('#cards [data-go="themes"]')
    page.wait_for_selector("#themes:not([hidden])")
    expected = start_review(run, page, name, "listen", "review.intro")
    run.check(True, f"[{name}] after cards the turn comes back to listen")
    page.click('#play [data-go="themes"]')
    page.wait_for_selector("#themes:not([hidden])")
    after = page.evaluate(STATE)
    run.check(after["due"] < len(due_ids), f"[{name}] after reviewing, fewer words wait ({len(due_ids)} -> {after['due']})")
    shot(page, f"{name}-themes-after-review", QA3)

    # A nearly full jar: the next round fills it, it celebrates and a new jar starts.
    snap = json.loads(after["saved"])
    snap["jar"] = {"stars": 11, "full": 0}
    page.evaluate("(s) => localStorage.setItem('ew.progress', s)", json.dumps(snap))
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    st = to_themes(page)
    run.check(st["jarShown"] == [[11, 0]], f"[{name}] nearly full jar shown {st['jarShown']}")
    if big:
        shot(page, f"{name}-themes-jar-nearly-full", QA3)
    a = audios(page)
    page.click("#gamesBtn", force=True)
    page.wait_for_selector("#games:not([hidden])")
    open_game(page, "listen")
    play_listen(run, page, name, "jar-fill", False, QA3)   # a game round: its stars fill the jar
    page.wait_for_timeout(1200)
    jar = page.evaluate("() => Progress.jar()")
    run.check(zh_said(page, a, "jar.full") and jar["full"] == 1 and jar["stars"] < 3,
              f"[{name}] the jar fills, celebrates and a new one starts {jar}")
    if big or name == "ipad-landscape":
        shot(page, f"{name}-jar-full", QA3)
    page.wait_for_timeout(2600)
    page.click('#result [data-go="home"]')
    st = to_themes(page)
    run.check(st["jarShown"] == [[jar["stars"], 1]], f"[{name}] themes show the new jar next to the full one {st['jarShown']}")
    if big:
        shot(page, f"{name}-themes-jar-shelf", QA3)

    # Clear: everything starts over.
    page.evaluate("() => localStorage.removeItem('ew.progress')")
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    st = to_themes(page)
    run.check(set(st["stars"].values()) == {0} and st["due"] == 0 and st["jar"]["stars"] == 0 and st["jar"]["full"] == 0,
              f"[{name}] cleared progress resets stars, review and jar")

    # Broken save: safe fresh start, old data kept aside, no errors.
    page.evaluate("() => localStorage.setItem('ew.progress', '{broken json')")
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    st = to_themes(page)
    backup = page.evaluate("() => localStorage.getItem('ew.progress.broken')")
    run.check(set(st["stars"].values()) == {0} and backup == "{broken json" and json.loads(st["saved"])["version"] == 3,
              f"[{name}] broken save: fresh start, old data kept in ew.progress.broken")
    page.click('.theme-card[data-theme="halloween"]')
    page.click('#cards [data-go="themes"]')
    st = page.evaluate(STATE)
    hw = [w["id"] for w in words if w["theme"] == "halloween"][0]
    run.check(json.loads(st["saved"])["words"].get(hw, {}).get("seen") == 1, f"[{name}] after the reset, progress saves again")
    lay_errors = page.evaluate(LAYOUT_CHECK, MIN_TAP["ipad" if name.startswith("ipad") else "phone"])
    run.check(not lay_errors, f"[{name}] themes screen layout {lay_errors if lay_errors else ''}".rstrip())
    run.check(not zh_tts(page), f"[{name}] progress: every Chinese line came from a recording {zh_tts(page)}")
    all_errors = errors + errors_late + errors1
    run.check(not all_errors, f"[{name}] progress: no console/page errors or 4xx/5xx {all_errors if all_errors else ''}".rstrip())
    ctx.close()



# Phase 4: solve from spoken sentences and shape hints, with all helper text off.

# Saved on a device by the phase 6/7 site (parent corner): progress with the
# parent's own words, their list and a photo. Phase 8 removed the parent corner.
LEGACY_SEED = """() => new Promise(done => {
  const day = 86400000, now = Date.now(), r = (box) => ({seen: 3, right: 2, wrong: 1, last: now - 2 * day, box, due: now - day});
  localStorage.setItem('ew.progress', JSON.stringify({version: 3,
    words: {goat: r(2), phrase_hello: r(1), my_word_cat: r(1), my_phrase_good_night: r(0)},
    best: {animals: 1, my_theme_pets: 2}, jar: {stars: 7, full: 1}, reviewTurn: 0}));
  localStorage.setItem('ew.custom.v1', JSON.stringify({version: 1,
    themes: [{id: 'my_theme_pets', english: 'Pets', chinese: '寵物', color: '#ffd6a5'}],
    words: [{id: 'my_word_cat', english: 'cat', chinese: '貓', theme: 'my_theme_pets', image: 'idb'}],
    phrases: [{id: 'my_phrase_good_night', english: 'Good night.', chinese: '晚安', category: 'custom', image: 'images/phrases/hello.svg'}]}));
  localStorage.setItem('ew.settings.v1', JSON.stringify({showEnglish: false, showChinese: true}));
  const open = indexedDB.open('picture-words', 1);
  open.onupgradeneeded = () => open.result.createObjectStore('photos');
  open.onsuccess = () => { const tx = open.result.transaction('photos', 'readwrite');
    tx.objectStore('photos').put('data:image/jpeg;base64,AAAA', 'my_word_cat');
    tx.oncomplete = () => { open.result.close(); done(true); }; };
})"""
LEGACY_READ = """() => new Promise(done => {
  const open = indexedDB.open('picture-words');
  open.onsuccess = () => { const db = open.result;
    if (!db.objectStoreNames.contains('photos')) { db.close(); done(null); return; }
    const get = db.transaction('photos').objectStore('photos').get('my_word_cat');
    get.onsuccess = () => { db.close(); done(get.result || null); }; };
})"""


def legacy_case(run, browser, base, name, opts):
    """An iPad that used the parent corner updates to phase 8: nothing breaks,
    built-in progress, jar and settings stay, the parent's data is left alone."""
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    tag = f"[{name}/legacy]"
    page.evaluate(LEGACY_SEED)
    custom_before = page.evaluate("() => localStorage.getItem('ew.custom.v1')")
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    goat = page.evaluate("() => Progress.get('goat')")
    run.check(goat and goat["box"] == 2 and goat["seen"] == 3 and goat["right"] == 2, f"{tag} built-in word progress kept {goat}")
    run.check(page.evaluate("() => Progress.get('phrase_hello').box") == 1, f"{tag} built-in phrase progress kept")
    jar = page.evaluate("() => JSON.parse(localStorage.getItem('ew.progress')).jar")
    run.check(jar == {"stars": 7, "full": 1}, f"{tag} star jar kept {jar}")
    run.check(page.evaluate("() => document.body.classList.contains('hide-en') && document.body.classList.contains('show-zh')"), f"{tag} Aa / 中 settings kept")
    page.click("#startBtn", force=True)
    page.wait_for_selector("#themes:not([hidden])")
    themes = page.evaluate("() => [...document.querySelectorAll('#themeGrid .theme-card')].map(b => b.dataset.theme)")
    run.check(themes == ["review", "animals", "halloween"], f"{tag} only built-in themes {themes}")
    due = page.evaluate("() => [...document.querySelectorAll('.review-card .due-pics img')].map(i => i.dataset.word)")
    run.check(due == ["goat"], f"{tag} review shows only built-in due words {due}")
    page.click('.theme-card[data-theme="animals"]')
    page.wait_for_selector("#cards:not([hidden])")
    animals = sum(w["theme"] == "animals" for w in json.loads((ROOT / "data/words.json").read_text()))
    run.check(page.evaluate("() => document.querySelector('#progress').textContent") == f"1 / {animals}", f"{tag} animal cards: the {animals} built-in words")
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('ew.progress')).words")
    run.check("my_word_cat" in saved and "my_phrase_good_night" in saved, f"{tag} old records of the parent's words are not deleted")
    run.check(page.evaluate("() => localStorage.getItem('ew.custom.v1')") == custom_before, f"{tag} ew.custom.v1 untouched")
    run.check(page.evaluate(LEGACY_READ) == "data:image/jpeg;base64,AAAA", f"{tag} IndexedDB photo untouched")
    run.check(not errors, f"{tag} no errors {errors}")
    ctx.close()


def jar_case(run, browser, base, name, opts):
    """Phase 9 jar: stars lie in a heap (not a grid) inside the glass, the same
    heap on every draw, and only the new stars of a round drop in."""
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    tag = f"[{name}/jar]"
    info = page.evaluate(r"""() => {
      const box = document.createElement('div'); box.className = 'jar-box result-jar'; document.body.appendChild(box);
      const read = () => [...box.querySelectorAll('.jar-main .jar-star-drop > g')].map(g => g.getAttribute('transform'));
      Jar.render(box, {stars: 11, full: 0, size: 12}); const a = read();
      Jar.render(box, {stars: 11, full: 0, size: 12}); const b = read();
      const glass = box.querySelector('.jar-glass').getBoundingClientRect();
      const inside = [...box.querySelectorAll('.jar-main .jar-star')].every(u => { const r = u.getBoundingClientRect();
        return r.left >= glass.left - 1 && r.right <= glass.right + 1 && r.top >= glass.top - 1 && r.bottom <= glass.bottom + 1; });
      const xy = a.map(t => t.match(/translate\(([-\d.]+) ([-\d.]+)\)/).slice(1).map(Number));
      const rot = new Set(a.map(t => t.match(/rotate\(([-\d.]+)\)/)[1])).size;
      const ys = xy.map(p => p[1]), rows = new Set(ys.map(y => Math.round(y))).size;
      Jar.render(box, {stars: 11, full: 0, size: 12}, 8);
      const fresh = box.querySelectorAll('.jar-main .jar-star-new').length;
      box.remove();
      return {n: a.length, same: JSON.stringify(a) === JSON.stringify(b), inside, rot, rows, fresh, lowFirst: ys[0] > ys[ys.length - 1]};
    }""")
    run.check(info["n"] == 11 and info["inside"], f"{tag} 11 stars, all inside the glass {info}")
    run.check(info["same"], f"{tag} the heap is the same on every draw (a star never jumps)")
    run.check(info["rot"] >= 8 and info["rows"] >= 8 and info["lowFirst"], f"{tag} a heap from the bottom up, turned and placed unevenly, not a grid {info}")
    run.check(info["fresh"] == 3, f"{tag} only the round's new stars drop in ({info['fresh']} of 3)")
    reduced = page.evaluate("""() => matchMedia('(prefers-reduced-motion: reduce)').matches""")
    if not reduced:
        page.emulate_media(reduced_motion="reduce")
    still = page.evaluate("""() => { const box = document.createElement('div'); box.className = 'jar-box'; document.body.appendChild(box);
      Jar.render(box, {stars: 5, full: 0, size: 12}, 3); const n = box.querySelector('svg').getAnimations({subtree: true}).length; box.remove(); return n; }""")
    run.check(still == 0, f"{tag} reduced motion: no dropping or twinkling ({still} animations)")
    run.check(not errors, f"{tag} no errors {errors}")
    ctx.close()


def phrase_deck(run, page, name, phrases):
    """Phrase cards (phase 8): the #cards screen, like word cards. Every phrase in
    data order, slow en-US, arrows; the end of the deck praises but gives no star (phase 9)."""
    tag = f"[{name}/phrase cards]"
    jar0 = page.evaluate("() => Progress.snapshot().jar")
    since = calls(page)
    page.click('#phraseGrid .theme-card[data-theme="phrases"]')
    page.wait_for_selector("#cards:not([hidden])")
    run.check(page.evaluate("() => document.querySelector('#cards').classList.contains('phrase-deck')"), f"{tag} phrases open in the card screen")
    run.check(page.get_attribute("#cards .bar [data-go]", "data-go") == "phrases", f"{tag} back button leads to the phrase area")
    run.check(page.locator("#enBtn").is_visible() and page.locator("#zhBtn").is_visible(), f"{tag} Aa / 中 switches are there")
    n = len(phrases)
    for i, p in enumerate(phrases):
        page.wait_for_function("(t) => window.__speech.calls.some(c => c.text === t)", arg=p["english"])
        said = [c for c in page.evaluate("(n) => window.__speech.calls.slice(n)", since) if c["text"] == p["english"]][-1]
        run.check(said["rate"] == .72 and said["lang"] == "en-US", f"{tag} card {i + 1}: '{p['english']}' read slowly in en-US")
        run.check(page.inner_text("#progress") == f"{i + 1} / {n}", f"{tag} card {i + 1}: counter {page.inner_text('#progress')}")
        if i == 0:
            layout = page.evaluate(LAYOUT_CHECK, MIN_TAP["ipad" if name.startswith("ipad") else "phone"])
            run.check(not layout, f"{tag} layout {layout}")
            shot(page, name + "-phrase-card", QA4)
            # Back and forth with the arrows.
            page.click("#nextBtn")
            page.wait_for_function("(t) => document.querySelector('#progress').textContent === t", arg=f"2 / {n}")
            page.click("#prevBtn")
            page.wait_for_function("(t) => document.querySelector('#progress').textContent === t", arg=f"1 / {n}")
            run.check(page.evaluate("() => window.__speech.calls.at(-1).text") == p["english"], f"{tag} back arrow reads the first phrase again")
        since = calls(page)
        page.click("#nextBtn")
    page.wait_for_function("(t) => document.querySelector('#progress').textContent === t", arg=f"1 / {n}")
    page.wait_for_timeout(1200)
    jar = page.evaluate("() => Progress.snapshot().jar")
    run.check(jar == jar0, f"{tag} whole deck seen: no star in the jar (stars are for games) {jar0} -> {jar}")
    run.check(zh_said(page, 0, "cards.done") and not zh_said(page, 0, "jar.more"), f"{tag} whole deck seen: recorded praise, no jar line")
    page.click("#cards .bar [data-go]")
    page.wait_for_selector("#phrases:not([hidden])")
    stars = page.get_attribute('#phraseGrid .theme-card[data-theme="phrases"] .theme-stars', "data-stars")
    run.check(stars == "0", f"{tag} looking through gives the phrase card no star ({stars})")


def phrases_flow(run, browser, base, name, opts):
    errors=[]
    ctx,page=open_site(browser,base,{**opts,"reduced_motion":"reduce"},{"lateMs":0,"event":True},errors)
    page.evaluate("() => { document.body.classList.add('hide-en'); document.body.classList.remove('show-zh'); }")
    page.wait_for_selector('#phrasesBtn:not([disabled])')
    page.click('#phrasesBtn',force=True)
    page.wait_for_selector('#phrases:not([hidden])')
    page.wait_for_timeout(300)
    # Laid out like the word area: games button, then review and the phrase cards.
    cards=page.evaluate("() => [...document.querySelectorAll('#phraseGrid > button')].map(b => b.dataset.theme)")
    run.check(cards==['review','phrases'] and page.locator('#phraseGamesBtn').is_visible(),f'[{name}] phrase area: games button, review and phrase cards {cards}')
    run.check(page.locator('#phrases p').count()==0,f'[{name}] phrase area: no written instructions')
    run.check(zh_said(page,0,'phrases.home'),f'[{name}] phrase area: recorded how-to')
    layout=page.evaluate(LAYOUT_CHECK, MIN_TAP['ipad' if name.startswith('ipad') else 'phone'])
    run.check(not layout,f'[{name}] phrase area layout {layout}')
    shot(page,name+'-menu',QA4)
    phrases=json.loads((ROOT/'data/phrases.json').read_text())
    phrase_deck(run,page,name,phrases)
    page.click('#phraseGamesBtn',force=True)
    page.wait_for_selector('#phraseGames:not([hidden])')
    modes=page.evaluate("() => [...document.querySelectorAll('#phraseMenu button')].map(b => b.dataset.phraseMode)")
    run.check(modes==['listen','order'],f'[{name}] phrase games: listen and order {modes}')
    run.check(zh_said(page,0,'games.pick'),f'[{name}] phrase games: recorded how-to')
    shot(page,name+'-games',QA4)
    lookup={p['english']:p for p in phrases}
    multi=[p for p in phrases if len(p['english'].split())>1]
    rounds={'listen':len(phrases),'order':len(multi),'review':4}
    missed=[]
    for mode in ('listen','order','review'):
        if mode=='review':
            # Today's review sits in the phrase area, like the word review card.
            page.click('#phraseGames [data-go="home"]')
            page.click('#phrasesBtn',force=True)
            page.click('#phraseGrid .review-card')
        else:
            page.click('[data-phrase-mode="'+mode+'"]')
        asked=[]
        order_wrong=False
        busy_tap=None
        if mode=='order':
            # A tap while the how-to and the sentence play must not cut them off.
            page.wait_for_selector('.phrase-bank button')
            busy_tap=page.evaluate("""() => { const busy=!!document.querySelector('#playStage').dataset.listening;
              const n=window.__speech.calls.length; document.querySelector('.phrase-bank button').click(); return {busy,n}; }""")
        page.wait_for_function('(n) => document.querySelectorAll("#dots .dot").length===n',arg=rounds[mode])
        for q in range(rounds[mode]):
            try:
                page.wait_for_function('(q) => document.querySelector("#play").dataset.q===String(q)',arg=q)
            except Exception as exc:
                shot(page,name+'-'+mode+'-stuck',QA4)
                raise RuntimeError(f'{name} {mode} Q{q}: '+str(page.evaluate('() => ({q:document.querySelector("#play").dataset.q,calls:window.__speech.calls.slice(-6)})'))) from exc
            # Intro then the queued English prompt; never read on-screen text.
            prompt_key={'q':str(q),'game':'phrase-'+mode}
            page.wait_for_function('(key) => window.__speech.calls.some(c => c.rate===.72 && c.q===key.q && c.game===key.game)',arg=prompt_key)
            page.wait_for_timeout(150)
            calls=page.evaluate('(key) => window.__speech.calls.filter(c=>c.rate===.72 && c.q===key.q && c.game===key.game)',prompt_key)
            prompt=calls[-1]['text'];p=lookup[prompt];asked.append(p['id'])
            run.check(calls[-1]['lang']=='en-US',f'[{name}] {mode} prompt en-US')
            layout=page.evaluate(LAYOUT_CHECK, MIN_TAP['ipad' if name.startswith('ipad') else 'phone'])
            run.check(not layout,f'[{name}] {mode} Q{q} layout {layout}')
            if mode in ('listen','review'):
                buttons=page.locator('#playStage .pick')
                run.check(buttons.count()==4,f'[{name}] at most four unique scenario options')
                run.check(page.locator('#playStage').inner_text().strip()=='',f'[{name}] picture choices need no reading')
                if q==0 and mode=='listen':
                    bad=page.locator('#playStage .pick:not([data-word="'+p['id']+'"])').first
                    bad.click()
                    missed.append(p['id'])
                    page.wait_for_timeout(500)
                    since=audios(page)
                    bad.click()  # the same wrong picture again: no repeated feedback
                    page.wait_for_timeout(300)
                    run.check(not zh_said(page,since,'game.try_again') and 'is-wrong' in bad.get_attribute('class'),f'[{name}] listen: a wrong picture is greyed out and not repeated')
                    shot(page,name+'-'+mode+'-wrong',QA4)
                page.locator('#playStage .pick[data-word="'+p['id']+'"]').click()
            else:
                tokens=[t.rstrip('?.!') for t in p['english'].split()]
                run.check(len(tokens)>1,f'[{name}] order only uses multi-word phrases')
                if busy_tap and q==0:
                    run.check(busy_tap['busy'],f'[{name}] order: tokens wait while the prompt plays')
                    early=page.evaluate('(n) => window.__speech.calls.slice(n)',busy_tap['n'])
                    run.check(any(c['text']==p['english'] for c in early) and all(c['rate']==.72 for c in early),f'[{name}] order: a tap during the how-to keeps the queued sentence {early}')
                page.wait_for_function("() => !document.querySelector('#playStage').dataset.listening")
                # Nothing on the board tells the order before listening.
                run.check(page.evaluate("() => getComputedStyle(document.querySelector('.game-phrase-order .phrase-text')).visibility")=='hidden',f'[{name}] order: the written sentence is hidden until it is built')
                run.check(page.locator('.phrase-bank .hint, .phrase-slots .next.lit').count()==0 and not page.locator('.phrase-bank').inner_text().strip() and not page.locator('.phrase-slots').inner_text().strip(),f'[{name}] order: no hint, shape or text before a mistake')
                if q==0:shot(page,name+'-order-start',QA4)
                def hear(button):
                    n=page.evaluate('() => window.__speech.calls.length')
                    button.click()
                    page.wait_for_function('(n) => window.__speech.calls.length>n',arg=n)
                    return page.evaluate('() => window.__speech.calls.at(-1).text')
                for i,target in enumerate(tokens):
                    bank=page.locator('.phrase-bank button:not([disabled])')
                    if not order_wrong:
                        # Pick a token that sounds wrong and put it in: gentle miss, then a hint.
                        order_wrong=True
                        missed.append(p['id'])
                        for j in range(bank.count()):
                            if hear(bank.nth(j))!=target: bank.nth(j).click();break
                        page.wait_for_timeout(300)
                        hint=page.locator('.phrase-bank .hint')
                        run.check(hint.count()==1,f'[{name}] order: the right token glows only after a mistake')
                        shot(page,name+'-order-wrong',QA4)
                        page.wait_for_function("() => !document.querySelector('#playStage').dataset.listening")
                        run.check(hear(hint)==target,f'[{name}] order: the glowing token is the next word')
                        hint.click()
                        continue
                    for j in range(bank.count()):
                        # Solve by listening only: tap to hear, tap again to place.
                        if hear(bank.nth(j))==target:
                            bank.nth(j).click();break
                    page.wait_for_timeout(60)
                run.check(page.locator('.phrase-slots .filled').count()==len(tokens),f'[{name}] order: all words placed')
                run.check(page.evaluate("() => getComputedStyle(document.querySelector('.game-phrase-order .phrase-text')).visibility")=='visible',f'[{name}] order: the sentence shows once built')
                if q==0:shot(page,name+'-order-right',QA4)
            if q==0:
                rows=page.evaluate("() => new Set([...document.querySelectorAll('#dots .dot')].map(d => Math.round(d.getBoundingClientRect().top))).size")
                run.check(rows==1,f'[{name}] {mode} progress stars on one row ({rows})')
                run.check(page.evaluate("""() => document.documentElement.scrollWidth<=innerWidth && Array.from(document.querySelectorAll('#playStage img')).every(i=>i.complete&&i.naturalWidth>0)"""),f'[{name}] {mode} no overflow or broken images')
        page.wait_for_selector('#result:not([hidden])',timeout=15000)
        page.wait_for_timeout(1800)
        if mode=='review':
            run.check(zh_said(page,0,'phrases.review_done'),f'[{name}] review ends with its own done line')
            run.check(set(asked[:len(set(missed))])==set(missed),f'[{name}] review asks missed phrases first {asked} {missed}')
        run.check(len(set(asked))==rounds[mode],f'[{name}] {mode} every phrase once per round')
        shot(page,name+'-'+mode+'-result',QA4)
        if mode!='review':
            # Back to the phrase games menu (grid icon), not the word games.
            page.click('#result [data-go="phraseGames"]')
            page.wait_for_selector('#phraseGames:not([hidden])')
    snapshot=page.evaluate('() => Progress.snapshot()')
    run.check(all(snapshot['words'].get(p['id'],{}).get('seen',0)>0 for p in phrases),f'[{name}] phrase progress saved separately')
    run.check(any(r.get('wrong',0) for id,r in snapshot['words'].items() if id.startswith('phrase_')),f'[{name}] wrong phrases recorded')
    run.check(snapshot['jar']['full']*12+snapshot['jar']['stars']==9,f'[{name}] three game rounds give three stars each in the shared jar; the card deck none')
    page.reload()
    page.wait_for_selector('#phrasesBtn:not([disabled])')
    run.check(page.evaluate('() => Progress.snapshot()')==snapshot,f'[{name}] phrase records and stars persist after reload')
    page.click('#phrasesBtn',force=True)
    page.wait_for_selector('#phrases:not([hidden])')
    stars=page.get_attribute('#phraseGrid .theme-card[data-theme="phrases"] .theme-stars','data-stars')
    run.check(stars=='1',f'[{name}] after playing phrase games the phrase card shows its first star ({stars})')
    run.check(not zh_tts(page),f'[{name}] phrases Chinese mp3 only')
    run.check(not errors,f'[{name}] phrases no console errors/404 {errors}')
    ctx.close()


def phrase_sheet(browser, base):
    """All seven scene pictures side by side, to check they tell apart at a glance."""
    page = browser.new_page(viewport={"width": 1200, "height": 700})
    page.goto(base)
    cells = "".join(f'<figure><img src="{p["image"]}"><figcaption>{p["english"]} {p["chinese"]}</figcaption></figure>'
                    for p in json.loads((ROOT / "data/phrases.json").read_text()))
    page.set_content("<style>body{margin:0;padding:12px;background:#fff6e5;font-family:system-ui,sans-serif;color:#2b3a55;"
                     "display:grid;grid-template-columns:repeat(4,1fr);gap:12px}figure{margin:0;background:#fff;border:3px solid #2b3a55;"
                     "border-radius:18px;padding:6px;text-align:center}img{width:100%;aspect-ratio:1}figcaption{font-size:20px}</style>" + cells)
    page.wait_for_function("() => [...document.images].every(i => i.complete && i.naturalWidth > 0)")
    page.screenshot(path=str(QA4 / "phrase-contact-sheet.png"), full_page=True)
    page.close()


def phrase_voice_cases(run, browser, base):
    errors=[]
    ctx,page=open_site(browser,base,VIEWPORTS['ipad-portrait'],{'lateMs':0,'event':True},errors)
    page.wait_for_selector('#phrasesBtn:not([disabled])')
    page.click('#phrasesBtn',force=True)
    # Use a fixed sentence to check boundary callbacks independently of random rounds.
    result=page.evaluate("""async () => {
      const phrase={english:'What is your name?',category:'introductions'};
      const cues=[];
      await new Promise(resolve => Speech.play(phrase,{onboundary:i=>cues.push(i),onend:resolve}));
      return {cues,calls:window.__speech.calls};
    }""")
    run.check(set([0,5,8,13]).issubset(set(result['cues'])),'[phrases voice] sequential word-boundary cues')
    run.check(result['calls'][-1]['rate']==.72 and result['calls'][-1]['lang']=='en-US','[phrases voice] slower en-US phrase speech')
    # The UI uses these boundary callbacks to highlight the displayed word.
    page.evaluate("""() => {
      window.__lit=[];
      new MutationObserver(() => document.querySelectorAll('#wordEn span.lit').forEach(s=>window.__lit.push(s.textContent))).observe(document.querySelector('#wordEn'),{subtree:true,attributes:true,attributeFilter:['class']});
    }""")
    page.evaluate("() => document.body.classList.remove('hide-en')")
    page.click('#phraseGrid .theme-card[data-theme="phrases"]')
    page.wait_for_timeout(500)
    page.click('#pic')
    page.wait_for_timeout(180)
    run.check(bool(page.evaluate('() => window.__lit.length')),'[phrases voice] visible word highlight during card playback')
    shot(page,'ipad-phrase-text',QA4)
    ctx.route('**/audio/phrases/test.wav',lambda r:r.fulfill(status=200,content_type='audio/wav',body=beep_wav()))
    before=calls(page)
    page.evaluate("""() => Speech.play({english:'Thank you.',category:'manners',audio:'audio/phrases/test.wav'})""")
    page.wait_for_timeout(500)
    run.check(calls(page)==before and any('/audio/phrases/test.wav' in u for u in page.evaluate('() => window.__audio')),'[phrases voice] optional recording takes priority')
    ctx.route('**/audio/phrases/broken.wav',lambda r:r.fulfill(status=404,body='missing'))
    page.evaluate("""() => Speech.play({english:'Thank you.',category:'manners',audio:'audio/phrases/broken.wav'})""")
    page.wait_for_timeout(350)
    latest=page.evaluate('() => window.__speech.calls.at(-1)')
    run.check(latest['text']=='Thank you.' and latest['rate']==.72 and latest['lang']=='en-US','[phrases voice] failed recording falls back to slow English TTS')
    run.check(not [e for e in errors if '404' not in e and 'broken.wav' not in e],'[phrases voice] no unexpected errors')
    ctx.close()
    # Chinese switched on: the recorded meaning (zh.phrase_*) follows the English sentence.
    errors=[]
    ctx,page=open_site(browser,base,VIEWPORTS['ipad-portrait'],{'lateMs':0,'event':True},errors)
    page.evaluate("() => { window.__order=[]; const o=Speech.play, z=Speech.zh; Speech.play=(i,p)=>{window.__order.push('en:'+i.english);return o(i,p);}; Speech.zh=(k,p)=>{window.__order.push('zh:'+k);return z(k,p);}; }")
    page.click('#phrasesBtn',force=True)
    page.click('#phraseGrid .theme-card[data-theme="phrases"]')
    page.wait_for_selector('#cards:not([hidden])')
    page.click('#zhBtn')  # the 中 switch on the card screen
    page.wait_for_timeout(300)
    since=audios(page)
    page.click('#pic')
    pid=json.loads((ROOT/'data/phrases.json').read_text())[0]['id']
    page.wait_for_timeout(800)
    order=page.evaluate('() => window.__order')
    run.check(order[-2:]==['en:'+[p for p in json.loads((ROOT/'data/phrases.json').read_text()) if p['id']==pid][0]['english'],'zh:zh.'+pid] and zh_said(page,since,'zh.'+pid),f'[phrases voice] Chinese on: recorded meaning after the English sentence {order[-3:]}')
    run.check(not zh_tts(page) and not errors,f'[phrases voice] Chinese meaning is an mp3, no errors {errors}')
    ctx.close()
    # A line added to voice-zh.json but not recorded yet: skipped in silence, never TTS.
    errors=[]
    ctx,page=open_site(browser,base,VIEWPORTS['ipad-portrait'],{'lateMs':0,'event':True},errors)
    page.wait_for_load_state('networkidle')  # audio/zh/manifest.json is read; set our own list after it
    page.evaluate("() => Speech.setRecorded(['cards.howto'])")
    before=(audios(page),calls(page))
    res=page.evaluate("""() => new Promise(done => { let ended=false;
      const r=Speech.zh('phrases.not_recorded_yet',{onend:()=>{ended=true;}});
      Speech.play({english:'goat'},{queue:true,onend:()=>done({r,ended})}); })""")
    page.wait_for_timeout(300)
    run.check(res=={'r':False,'ended':True},f'[phrases voice] an unrecorded line is skipped and its onend still runs {res}')
    run.check(audios(page)==before[0] and not zh_tts(page),'[phrases voice] an unrecorded line fetches no mp3 and uses no TTS')
    run.check(page.evaluate("() => window.__speech.calls.at(-1).text")=='goat','[phrases voice] what was queued after it still plays')
    run.check(page.is_hidden('#toast') and not errors,f'[phrases voice] no error message for an unrecorded line {errors}')
    ctx.close()
    # Short how-to lines (real recordings) so the first English comes quickly.
    errors=[]
    ctx,page=open_site(browser,base,VIEWPORTS['ipad-portrait'],{'lateMs':0,'event':True},errors,real_voice=True)
    lengths=page.evaluate("""async () => { const ac=new (window.AudioContext||window.webkitAudioContext)(); const out={};
      for (const k of ['phrases.cards','phrases.listen','phrases.order','phrases.review','phrases.review_done']) {
        const b=await (await fetch('audio/zh/'+k+'.mp3')).arrayBuffer(); out[k]=(await ac.decodeAudioData(b)).duration; }
      return out; }""")
    run.check(all(v<=4.0 for v in lengths.values()),f'[phrases voice] every phrase how-to line is 4 s or shorter {lengths}')
    ctx.close()


def overview_sheet(browser, base):
    """Every word card and every phrase scene on one sheet (phase 5 acceptance)."""
    words = json.loads((ROOT / "data/words.json").read_text())
    phrases = json.loads((ROOT / "data/phrases.json").read_text())
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(base)
    cell = lambda img, en, zh: f'<figure><img src="{img}"><figcaption><b>{en}</b> {zh}</figcaption></figure>'
    page.set_content(
        "<style>body{margin:0;padding:16px;background:#fff6e5;font-family:system-ui,sans-serif;color:#2b3a55}"
        "h2{margin:8px 4px}section{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-bottom:12px}"
        "figure{margin:0;background:#fff;border:3px solid #2b3a55;border-radius:18px;padding:8px;text-align:center}"
        "img{width:100%;aspect-ratio:1}figcaption{font-size:17px}</style>"
        f"<h2>單字 Words ({len(words)})</h2><section>" + "".join(cell(w["image"], w["english"], w["chinese"]) for w in words) +
        f"</section><h2>句子 Phrases ({len(phrases)})</h2><section>" + "".join(cell(p["image"], p["english"], p["chinese"]) for p in phrases) + "</section>")
    page.wait_for_function("() => [...document.images].every(i => i.complete && i.naturalWidth > 0)")
    page.screenshot(path=str(QA5 / "overview-words-phrases.png"), full_page=True)
    page.close()


# Text colour contrast of everything visible (WCAG: 4.5:1, or 3:1 for big text).
CONTRAST = r"""() => {
  const lum = c => { const v = c.match(/[\d.]+/g).slice(0, 3).map(x => { x /= 255; return x <= .03928 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4; });
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  const bg = el => { for (; el; el = el.parentElement) { const b = getComputedStyle(el).backgroundColor;
    const a = b.match(/[\d.]+/g); if (a && (a.length < 4 || +a[3] > .9)) return b; } return 'rgb(255,246,229)'; };
  const bad = [];
  document.querySelectorAll('.screen:not([hidden]) *').forEach(el => {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || !el.getClientRects().length || getComputedStyle(el).visibility !== 'visible') return;
    if (el.closest('button:disabled')) return;
    const cs = getComputedStyle(el), size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
    const L1 = lum(cs.color), L2 = lum(bg(el)), r = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
    const need = size >= 24 || (bold && size >= 18.66) ? 3 : 4.5;
    if (r < need) bad.push(`${el.textContent.trim().slice(0, 20)} ${r.toFixed(2)}`);
  });
  return bad;
}"""


def look_flow(run, browser, base, name, opts):
    """Phase 5 look: big targets, contrast, transitions, star bursts, order
    sentence hidden until built; screenshots of each iPad size in qa/phase-5/."""
    BY_EN.update({w["english"]: w["id"] for w in json.loads((ROOT / "data/words.json").read_text())})
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    # Praise lasts 2 s here, so a finished board stays on screen to be checked.
    ctx.route("**/audio/zh/praise.*.mp3", lambda r: r.fulfill(status=200, content_type="audio/wav", body=short_wav(2)))
    shot5 = lambda label: shot(page, f"{name}-{label}", QA5)
    contrast = lambda where: run.check(not (bad := page.evaluate(CONTRAST)), f"[{name}/look] text contrast on {where} {bad}")
    lay = lambda where: run.check(not (bad := page.evaluate(LAYOUT_CHECK, MIN_TAP["ipad"])), f"[{name}/look] layout {where} {bad}")
    sizes = page.evaluate("() => [...document.querySelectorAll('#home .btn-wide')].map(b => b.getBoundingClientRect().height)")
    run.check(min(sizes) >= 120, f"[{name}/look] home buttons are big ({sizes})")
    contrast("home"); lay("home"); shot5("home")
    page.click("#startBtn", force=True)
    page.wait_for_selector("#themes:not([hidden])")
    run.check(page.evaluate("() => document.querySelector('#themes').getAnimations().length > 0"), f"[{name}/look] the new screen animates in")
    page.wait_for_timeout(500)
    contrast("themes"); lay("themes"); shot5("themes")
    page.click('.theme-card[data-theme="animals"]')
    page.wait_for_timeout(500)
    contrast("word card"); lay("word card"); shot5("card")
    page.click("#zhBtn")
    contrast("word card with Chinese"); shot5("card-chinese")
    page.click("#zhBtn")
    # Listen game: a right answer sends out little stars and plays a sound.
    page.click("#cards [data-go=themes]")
    page.click("#gamesBtn", force=True)
    page.wait_for_selector("#games:not([hidden])")
    page.wait_for_timeout(500)
    contrast("game menu"); shot5("games")
    SPEECH_MARK["n"] = calls(page)
    page.click('.game-card[data-game="listen"]')
    target = heard_after(page, SPEECH_MARK["n"])
    page.wait_for_timeout(500)
    lay("listen"); shot5("listen")
    osc = page.evaluate("() => window.__osc")
    page.click(f'.choices .pick[data-word="{target}"]')
    page.wait_for_timeout(220)
    run.check(page.locator(".burst-star").count() == 8 and page.evaluate("() => window.__osc") > osc, f"[{name}/look] right answer: star burst and sound")
    page.screenshot(path=str(QA5 / f"{name}-listen-right.png"))
    page.wait_for_timeout(900)
    run.check(page.locator(".burst-star").count() == 0, f"[{name}/look] burst stars clean up")
    page.goto(base)
    page.wait_for_selector("#startBtn:not([disabled])")
    page.click("#phrasesBtn", force=True)
    page.wait_for_selector("#phrases:not([hidden])")
    page.wait_for_timeout(500)
    contrast("phrase area"); lay("phrase area"); shot5("phrases")
    page.click('#phraseGrid .theme-card[data-theme="phrases"]')
    page.wait_for_selector("#cards:not([hidden])")
    page.wait_for_timeout(500)
    contrast("phrase card"); lay("phrase card"); shot5("phrase-card")
    page.click("#cards .bar [data-go]")
    page.click("#phraseGamesBtn", force=True)
    page.wait_for_selector("#phraseGames:not([hidden])")
    page.wait_for_timeout(500)
    contrast("phrase games"); lay("phrase games"); shot5("phrase-games")
    # Order: English helper on (default), the sentence stays hidden until built.
    page.click('[data-phrase-mode="order"]')
    page.wait_for_function("() => document.querySelector('#play').dataset.q === '0'")
    page.wait_for_function("() => !document.querySelector('#playStage').dataset.listening", timeout=15000)
    hidden = page.evaluate("() => getComputedStyle(document.querySelector('.game-phrase-order .phrase-text')).visibility")
    run.check(hidden == "hidden" and not page.evaluate("() => document.body.classList.contains('hide-en')"), f"[{name}/look] order: English on, sentence still hidden ({hidden})")
    tok = page.evaluate("() => [...document.querySelectorAll('.phrase-bank .token')].map(b => b.getBoundingClientRect().width)")
    run.check(min(tok) >= 120, f"[{name}/look] order tokens are big ({tok})")
    lay("order"); shot5("order-start")
    pid = page.locator("#playStage .scene").get_attribute("data-word")
    english = next(p["english"] for p in json.loads((ROOT / "data/phrases.json").read_text()) if p["id"] == pid)
    # Tap a token to hear it; tap the same one again to place it.
    for want in re.findall(r"[A-Za-z']+", english):
        bank = page.locator(".phrase-bank button:not([disabled])")
        for j in range(bank.count()):
            n = calls(page)
            bank.nth(j).click()
            page.wait_for_function("(n) => window.__speech.calls.length > n", arg=n)
            if page.evaluate("() => window.__speech.calls.at(-1).text") == want:
                bank.nth(j).click()
                break
    page.wait_for_timeout(250)
    shown = page.evaluate("() => getComputedStyle(document.querySelector('.game-phrase-order .phrase-text')).visibility")
    run.check(shown == "visible", f"[{name}/look] order: the sentence shows once built ({shown})")
    shot5("order-done")
    run.check(not errors, f"[{name}/look] no errors {errors}")
    ctx.close()


# ---------- phase 7: keyboard focus and reduced motion (VoiceOver, Switch Control and keyboard users)

# What has focus now: does it show a ring, have a name, sit on the visible screen?
FOCUS_INFO = """() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const cs = getComputedStyle(el), img = el.querySelector('img[alt]');
  const name = (el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].innerText) || el.innerText
    || el.getAttribute('title') || (img && img.alt) || '').trim();
  const where = el.closest('.screen');
  window.__focusKeys = window.__focusKeys || new WeakMap();
  if (!window.__focusKeys.has(el)) window.__focusKeys.set(el, window.__focusKeys.size || Math.random());
  return {key: String(window.__focusKeys.get(el)), id: el.id || String(el.className || el.tagName), name,
    ring: cs.outlineStyle !== 'none' && cs.outlineStyle !== 'auto' && parseFloat(cs.outlineWidth) >= 3,  // the app's own ring, not the thin browser default
    outline: cs.outlineStyle + ' ' + cs.outlineWidth, visible: el.matches(':focus-visible'),
    where: where ? where.id : '', shown: !el.closest('[hidden]') && el.getClientRects().length > 0};
}"""


def tab_walk(page, limit=60):
    """Press Tab until focus comes back round; the controls reached, in order."""
    seen, out = set(), []
    for _ in range(limit):
        page.keyboard.press("Tab")
        info = page.evaluate(FOCUS_INFO)
        if not info:
            continue
        if info["key"] in seen:
            break
        seen.add(info["key"])
        out.append(info)
    return out


def tab_to(page, selector, limit=60):
    """Tab until `selector` has focus; False if Tab never got there."""
    for _ in range(limit):
        if page.evaluate("(s) => !!document.activeElement && document.activeElement.matches(s)", selector):
            return True
        page.keyboard.press("Tab")
    return False


def kb_go(page, selector, limit=60):
    """Tab to `selector` like a keyboard user and press Enter; False if Tab never got there."""
    if not tab_to(page, selector, limit):
        return False
    page.keyboard.press("Enter")
    return True


def a11y_flow(run, browser, base, name, opts):
    """Keyboard only: every control shows a focus ring and has a name, and on each
    new screen focus moves onto it (not left on a hidden button). Taps draw no ring."""
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    tag = f"[{name}/a11y]"

    def walk(where):
        page.wait_for_timeout(500)  # screens fade in
        found = tab_walk(page)
        bad = [f"{i['id']} ({i['outline']}, name '{i['name']}', {'' if i['shown'] else 'hidden'})"
               for i in found if not (i["ring"] and i["visible"] and i["name"] and i["shown"])]
        run.check(found and not bad, f"{tag} {where}: all {len(found)} controls Tab reaches show a focus ring and have a name {bad if bad else ''}".rstrip())

    def go(selector, screen, where):
        ok = kb_go(page, selector)
        page.wait_for_selector(f"#{screen}:not([hidden])")
        info = page.evaluate(FOCUS_INFO)
        run.check(ok and info and info["where"] == screen and info["visible"] and info["shown"],
                  f"{tag} keyboard {where}: focus moves onto the new screen ({info and info['id']} on {info and info['where']})")

    walk("home")
    page.evaluate("() => document.activeElement.blur()")
    go("#startBtn", "themes", "home -> themes")
    walk("themes")
    axe_check(run, page, f"{tag} themes after keyboard")
    go('.theme-card[data-theme="animals"]', "cards", "themes -> word card")
    walk("word card")
    shot(page, f"{name}-focus-word-card", QA7)
    go("#cards [data-go=themes]", "themes", "word card -> themes")
    go("#gamesBtn", "games", "themes -> game menu")
    walk("game menu")
    for game in ("listen", "match", "memory"):
        go(f'.game-card[data-game="{game}"]', "play", f"menu -> {game}")
        walk(f"game {game}")
        if game == "listen":
            tab_to(page, ".choices .pick")  # focus a picture without answering
            shot(page, f"{name}-focus-listen", QA7)
        go("#play [data-go]", "games", f"{game} -> menu")
    page.evaluate("() => Games.showResult(3, [])")  # the result screen opens by itself after a round
    page.wait_for_selector("#result:not([hidden])")
    info = page.evaluate(FOCUS_INFO)
    run.check(info and info["where"] == "result", f"{tag} a round ends: focus moves onto the result screen ({info and info['id']})")
    walk("result")
    axe_check(run, page, f"{tag} result after keyboard")
    go("#result [data-go=home]", "home", "result -> home")
    go("#phrasesBtn", "phrases", "home -> phrases")
    walk("phrase area")
    axe_check(run, page, f"{tag} phrase area")
    go('#phraseGrid .theme-card[data-theme="phrases"]', "cards", "phrases -> phrase cards")
    walk("phrase cards")
    axe_check(run, page, f"{tag} phrase cards")
    go("#cards .bar [data-go]", "phrases", "phrase cards -> phrases")
    go("#phraseGamesBtn", "phraseGames", "phrases -> phrase games")
    walk("phrase games")
    axe_check(run, page, f"{tag} phrase games")
    for mode in ("listen", "order"):
        go(f'[data-phrase-mode="{mode}"]', "play", f"phrase games -> {mode}")
        walk(f"phrase {mode}")
        go("#play [data-go]", "phraseGames", f"phrase {mode} -> phrase games")
    go("#phraseGames [data-go=home]", "home", "phrase games -> home")
    run.check(not errors, f"{tag} keyboard: no errors {errors}")
    ctx.close()

    # Taps, as a child plays: no focus ring appears anywhere.
    errors = []
    ctx, page = open_site(browser, base, opts, {"lateMs": 0, "event": True}, errors)
    rings = []
    for sel, screen in (("#startBtn", "themes"), ('.theme-card[data-theme="animals"]', "cards"), ("#cards [data-go=themes]", "themes"),
                        ("#gamesBtn", "games"), ('.game-card[data-game="listen"]', "play"), ("#play [data-go]", "games")):
        page.tap(sel, force=True)  # the big buttons breathe, so they are never "stable"
        page.wait_for_selector(f"#{screen}:not([hidden])")
        info = page.evaluate(FOCUS_INFO)
        if info and info["visible"]:
            rings.append(f"{screen}: {info['id']}")
    run.check(not rings, f"{tag} taps: no focus ring on any screen {rings if rings else ''}".rstrip())
    run.check(not errors, f"{tag} taps: no errors {errors}")
    ctx.close()


# Animations that move (transform) on an element or the whole page.
MOVING = """(sel) => (sel ? document.querySelector(sel).getAnimations() : document.getAnimations())
  .filter(a => a.effect && a.effect.getKeyframes().some(k => k.transform && k.transform !== 'none')).length"""


def motion_case(run, browser, base, name, opts, reduce):
    """With 'Reduce Motion' on nothing moves, yet every step still works. The same
    measures with it off must see movement, so the checks are not empty."""
    BY_EN.update({w["english"]: w["id"] for w in json.loads((ROOT / "data/words.json").read_text())})
    errors = []
    ctx, page = open_site(browser, base, {**opts, "reduced_motion": "reduce" if reduce else "no-preference"}, {"lateMs": 0, "event": True}, errors)
    tag = f"[{name}/motion {'reduced' if reduce else 'normal'}]"
    want = (lambda n: n == 0) if reduce else (lambda n: n > 0)
    page.click("#startBtn", force=True)
    page.wait_for_selector("#themes:not([hidden])")
    n = page.evaluate("() => document.querySelector('#themes').getAnimations().length")
    run.check(want(n), f"{tag} new screen: {n} animations")
    page.click('.theme-card[data-theme="animals"]')
    page.wait_for_selector("#cards:not([hidden])")
    page.wait_for_timeout(600)
    page.click("#pic")
    page.wait_for_timeout(60)
    n = page.evaluate(MOVING, "#picImg")
    glow = page.evaluate("() => document.querySelector('#picImg').getAnimations().length")
    run.check(want(n) and glow > 0, f"{tag} tapped picture: {n} moving of {glow} animations")
    page.click("#cards [data-go=themes]")
    page.click("#gamesBtn", force=True)
    page.wait_for_selector("#games:not([hidden])")
    SPEECH_MARK["n"] = calls(page)
    page.click('.game-card[data-game="listen"]')
    target = heard_after(page, SPEECH_MARK["n"])
    page.wait_for_timeout(500)
    page.click(f'.choices .pick[data-word="{target}"]')
    page.wait_for_timeout(220)
    stars, n = page.locator(".burst-star").count(), page.evaluate(MOVING, None)
    run.check(want(stars) and want(n), f"{tag} right answer: {stars} burst stars, {n} moving animations")
    page.evaluate("() => Games.showResult(3, [])")
    page.wait_for_selector("#result:not([hidden])")
    page.wait_for_timeout(300)
    run.check(page.locator("#resultStars > *").count() > 0, f"{tag} result: the stars are still shown")
    run.check(not errors, f"{tag} no errors {errors}")
    ctx.close()


AXE = sorted(pathlib.Path.home().glob(".npm/_npx/*/node_modules/axe-core/axe.min.js"))


def axe_check(run, page, label):
    """axe-core (WCAG 2 A/AA) on the visible screen, when axe is installed (tools/lighthouse.py fetches it)."""
    if not AXE:
        print(f"note: axe-core not found, skipped axe on {label}")
        return
    if not page.evaluate("() => !!window.axe"):
        page.add_script_tag(content=AXE[0].read_text())
    res = page.evaluate("""() => axe.run(document.querySelector('.screen:not([hidden])'), {runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']})
      .then(r => r.violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).slice(0, 3).join(', ')))""")
    run.check(not res, f"{label}: axe 0 violations {res}")


# ---------- phase 8: background music (js/music.js)

def load_render_bgm():
    spec = importlib.util.spec_from_file_location("render_bgm", ROOT / "tools/render-bgm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def music_level(page, duck):
    """Integrated loudness (LUFS) of one loop at the game's gain, measured by ffmpeg."""
    rb = load_render_bgm()
    res = page.evaluate(rb.RENDER, duck)
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "loop.wav"
        rb.write_wav(wav, res["rate"], __import__("base64").b64decode(res["pcm"]), repeat=2)
        return rb.loudness(wav)[0]


def music_flow(run, browser, base, name, opts):
    """Quiet music after the first tap, ducked under every voice line, a
    picture-only switch on the home screen that is remembered, asleep in the
    background, the iPad mute switch does not silence it ('playback')."""
    errors = []
    ctx = browser.new_context(**opts)
    fast_voice(ctx)
    # Chrome has no navigator.audioSession: a stand-in shows what Safari gets.
    ctx.add_init_script("navigator.audioSession = {type: 'auto'}; window.__ctxs = 0; const AC0 = window.AudioContext;"
                        "window.AudioContext = function (...a) { window.__ctxs++; return new AC0(...a); }; window.AudioContext.prototype = AC0.prototype;")
    ctx.add_init_script(FAKE_SPEECH + '({"lateMs": 0, "event": true})')
    page = ctx.new_page()
    watch(page, errors)
    page.goto(base)
    page.wait_for_selector("#startBtn:not([disabled])")
    tag = f"[{name}/music]"
    page.wait_for_timeout(500)
    run.check(page.evaluate("() => window.__ctxs") == 0 and not page.evaluate("() => Music.playing"), f"{tag} silent before the first tap (no audio started)")
    btn = page.locator("#musicBtn")
    run.check(btn.get_attribute("aria-pressed") == "true" and btn.get_attribute("aria-label") and not btn.inner_text().strip(), f"{tag} switch: on by default, a picture with a name, no text")
    box = btn.bounding_box()
    run.check(box["width"] >= MIN_TAP["ipad"] and box["height"] >= MIN_TAP["ipad"], f"{tag} switch is a big target {box['width']:.0f}x{box['height']:.0f}")
    page.click("#startBtn", force=True)
    page.wait_for_function("() => Music.playing", timeout=5000)
    run.check(page.evaluate("() => navigator.audioSession.type") == "playback", f"{tag} audio session 'playback': the mute switch does not silence the game")
    # The how-to is speaking: the music waits under it, then comes up to its level.
    page.wait_for_function("() => Math.abs(Music.gain() - Music.LEVEL) < 0.02", timeout=8000)
    run.check(True, f"{tag} after the first tap the music comes up to its level")
    normal, ducked = music_level(page, False), music_level(page, True)
    run.check(abs(normal + 32) <= 1.5, f"{tag} loudness {normal:.1f} LUFS (about -32, voice is -16)")
    run.check(abs(ducked + 44) <= 1.5, f"{tag} under a voice line {ducked:.1f} LUFS (about -44)")
    # Ducking: Chinese how-to then an English word, sampled every 50 ms.
    trace = page.evaluate("""() => new Promise(done => {
      const out = [], t0 = performance.now();
      const id = setInterval(() => out.push([Math.round(performance.now() - t0), Music.gain()]), 50);
      Speech.zh('cards.howto');
      Speech.play({english: 'goat'}, {queue: true, onend: () => { out.push(['end', Music.gain()]);
        setTimeout(() => { out.push(['hold', Music.gain()]);
          setTimeout(() => { clearInterval(id); out.push(['back', Music.gain()]); done(out); }, 1500); }, 400); }});
    })""")
    level, low = page.evaluate("() => Music.LEVEL"), page.evaluate("() => Music.LEVEL * Music.DUCK")
    during = [g for t, g in trace if isinstance(t, int) and t >= 250 and t < next(i for i, (k, _) in enumerate(trace) if k == "end") * 50]
    marks = {k: g for k, g in trace if isinstance(k, str)}
    run.check(during and max(during) <= low * 1.15, f"{tag} while speaking (both lines) the music stays ducked (max {max(during or [0]):.3f}, ducked {low:.3f})")
    run.check(marks["hold"] <= low * 1.15, f"{tag} 0.4 s after the last line it is still ducked ({marks['hold']:.3f})")
    run.check(abs(marks["back"] - level) < 0.03, f"{tag} then it comes back ({marks['back']:.3f} of {level:.3f})")
    # The switch: off fades out, remembered after reload, on again.
    page.click("#themes [data-go=home]")
    page.wait_for_selector("#home:not([hidden])")
    page.click("#musicBtn")
    page.wait_for_function("() => Music.gain() < 0.01", timeout=3000)
    off = page.evaluate("() => [document.querySelector('#musicBtn').getAttribute('aria-pressed'), document.querySelector('#musicBtn use').getAttribute('href'), JSON.parse(localStorage.getItem('ew.settings.v1')).music]")
    run.check(off == ["false", "#i-music-off", False], f"{tag} switch off: music fades out, crossed-out picture, saved {off}")
    shot(page, f"{name}-music-off", QA8)
    page.reload()
    page.wait_for_selector("#startBtn:not([disabled])")
    page.click("#startBtn", force=True)
    page.wait_for_timeout(800)
    run.check(page.evaluate("() => document.querySelector('#musicBtn').getAttribute('aria-pressed')") == "false" and page.evaluate("() => Music.gain()") < 0.01, f"{tag} still off after reload")
    page.click("#themes [data-go=home]")
    page.click("#musicBtn")
    page.wait_for_function("() => Music.playing && Music.gain() > 0.1", timeout=8000)
    run.check(page.evaluate("() => document.querySelector('#musicBtn').getAttribute('aria-pressed')") == "true", f"{tag} switch on again: music comes back")
    shot(page, f"{name}-music-on", QA8)
    # Background: fade out and sleep; the next tap wakes it.
    page.evaluate("() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange')); }")
    page.wait_for_timeout(700)
    faded = page.evaluate("() => Music.gain()")
    run.check(faded < 0.05, f"{tag} in the background the music fades out ({faded:.3f})")
    page.evaluate("() => { Object.defineProperty(document, 'visibilityState', {value: 'visible', configurable: true}); document.dispatchEvent(new Event('visibilitychange')); }")
    page.click("#startBtn", force=True)
    page.wait_for_function("() => Music.gain() > 0.05", timeout=8000)
    run.check(True, f"{tag} back in front, the next tap brings the music back")
    run.check(not errors, f"{tag} no errors {errors}")
    ctx.close()


def load_build_sw():
    spec = importlib.util.spec_from_file_location("build_sw", ROOT / "tools/build-sw.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def serve(folder, port):
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=folder,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
            return proc
        time.sleep(0.1)
    return proc


def pwa_flow(run, browser):
    """Home-screen app offline: cache everything, stop the server, reload and play;
    then publish a new version and check the cache refreshes."""
    build_sw = load_build_sw()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ew-pwa-"))
    site = tmp / "site"
    shutil.copytree(ROOT, site, ignore=shutil.ignore_patterns(".git", ".codex-status", "qa", "tools", "docs", "__pycache__"))
    files = build_sw.files(site)
    port = free_port()
    base = f"http://127.0.0.1:{port}/"
    server = serve(site, port)
    errors = []
    ctx = browser.new_context(viewport={"width": 820, "height": 1180}, is_mobile=True, has_touch=True)
    ctx.add_init_script(FAKE_SPEECH + '({"lateMs": 0, "event": true})')
    page = ctx.new_page()
    try:
        page.goto(base)
        page.wait_for_selector("#startBtn:not([disabled])")
        run.check(page.evaluate("() => fetch('manifest.webmanifest').then(r => r.json()).then(m => m.display === 'standalone' && m.icons.some(i => i.purpose === 'maskable'))"),
                  "[pwa] manifest: standalone, has a maskable icon")
        page.wait_for_function("() => navigator.serviceWorker.controller", timeout=30000)
        version = re.search(r"VERSION = '(\w+)'", (site / "sw.js").read_text()).group(1)
        cached = page.evaluate("v => caches.open('picture-words-' + v).then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname.slice(1)))", version)
        run.check(set(files) <= set(cached) and "" in cached, f"[pwa] every game file is cached ({len(cached)} of {len(files) + 1})")
        mp3s = [f for f in files if f.endswith(".mp3")]
        run.check(len(mp3s) >= 40 and all(f in cached for f in mp3s), f"[pwa] all {len(mp3s)} recorded mp3s are cached")

        # Offline: stop the server and open the app again.
        server.terminate(); server.wait()
        run.check(page.evaluate("() => fetch('/no-such-file.txt').then(() => false, () => true)"), "[pwa] server really stopped (uncached fetch fails)")
        watch(page, errors)
        page.reload()
        page.wait_for_selector("#startBtn:not([disabled])", timeout=15000)
        page.wait_for_selector("#phrasesBtn:not([disabled])", timeout=15000)
        run.check(page.locator("#loadMsg").inner_text() == "", "[pwa] offline reload: words load, no error message")
        page.click("#startBtn", force=True)
        page.click('.theme-card[data-theme="animals"]')
        page.wait_for_function("() => document.querySelector('#picImg').complete && document.querySelector('#picImg').naturalWidth > 0")
        run.check(True, "[pwa] offline: word card picture shows")
        broken = page.evaluate("""async files => { const bad = [];
          for (const f of files) { const r = await fetch(f).catch(() => null); if (!r || !r.ok) bad.push(f); }
          return bad; }""", files)
        run.check(not broken, f"[pwa] offline: every cached file answers 200 {broken[:5]}")
        played = page.evaluate("""() => new Promise(done => { const a = new Audio('audio/zh/praise.1.mp3');
          a.onended = () => done(a.duration); a.onerror = () => done(-1); a.play().catch(() => done(-2)); })""")
        run.check(played > 0.3, f"[pwa] offline: a recorded Chinese line plays to the end ({played:.2f}s)")
        part = page.evaluate("""() => fetch('audio/zh/praise.1.mp3', {headers: {Range: 'bytes=0-99'}}).then(r => [r.status, r.headers.get('Content-Range'), r.headers.get('Content-Type')])""")
        run.check(part[0] == 206 and part[1].startswith("bytes 0-99/") and part[2] == "audio/mpeg", f"[pwa] offline: audio Range request gets 206 for Safari {part}")
        page.click("#cards [data-go=themes]")
        page.click("#themes [data-go=home]")
        page.click("#phrasesBtn", force=True)
        page.click('#phraseGrid .theme-card[data-theme="phrases"]')
        page.wait_for_function("() => document.querySelector('#picImg').complete && document.querySelector('#picImg').naturalWidth > 0")
        run.check(True, "[pwa] offline: phrase card picture shows")
        page.click("#cards .bar [data-go]")
        page.click("#phraseGamesBtn", force=True)
        page.click('[data-phrase-mode="listen"]')
        page.wait_for_function("() => [...document.querySelectorAll('#playStage img')].length === 4 && [...document.querySelectorAll('#playStage img')].every(i => i.complete && i.naturalWidth > 0)")
        run.check(True, "[pwa] offline: phrase pictures show in a game")
        # A cold start (new tab, like opening the home-screen icon) while offline.
        cold = ctx.new_page()
        watch(cold, errors)
        cold.goto(base)
        cold.wait_for_selector("#startBtn:not([disabled])", timeout=15000)
        run.check(True, "[pwa] offline: opening the app fresh works")
        cold.click("#startBtn", force=True)
        cold.click('.theme-card[data-theme="animals"]')
        animals = sum(w["theme"] == "animals" for w in json.loads((ROOT / "data/words.json").read_text()))
        run.check(cold.evaluate("() => document.querySelector('#progress').textContent") == f"1 / {animals}", "[pwa] offline: word cards open after a cold start")
        cold.close()
        run.check(not errors, f"[pwa] offline: no errors {errors}")

        # New version published: the cache refreshes, the page waits for the home screen.
        css = site / "css/app.css"
        css.write_text(css.read_text() + "\n/* pwa-test-version */\n")
        (site / "sw.js").write_text(build_sw.render(site)[0])
        new_version = re.search(r"VERSION = '(\w+)'", (site / "sw.js").read_text()).group(1)
        server = serve(site, port)
        page.click("#play [data-go]")  # back to the phrase menu, not home
        page.evaluate("() => { window.__same = 1; }")
        page.evaluate("() => navigator.serviceWorker.getRegistration().then(r => r.update())")
        page.wait_for_function("v => caches.keys().then(k => k.includes('picture-words-' + v))", arg=new_version, timeout=30000)
        page.wait_for_function("v => caches.keys().then(k => !k.includes('picture-words-' + v))", arg=version, timeout=30000)
        page.wait_for_timeout(500)
        run.check(page.evaluate("() => window.__same === 1"), "[pwa] update: no reload in the middle of play")
        page.click("#phraseGames [data-go=home]")
        page.wait_for_function("() => !window.__same", timeout=15000)
        page.wait_for_selector("#startBtn:not([disabled])")
        run.check(page.evaluate("() => fetch('css/app.css').then(r => r.text()).then(t => t.includes('pwa-test-version'))"),
                  "[pwa] update: new version cached, old cache deleted, page reloaded on the home screen")
        server.terminate(); server.wait()
        page.reload()
        page.wait_for_selector("#startBtn:not([disabled])", timeout=15000)
        run.check(True, "[pwa] update: the new version also works offline")
    except Exception as e:
        run.check(False, f"[pwa] stopped: {str(e).splitlines()[0]}")
    finally:
        ctx.close()
        server.terminate()
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    ap.add_argument("--only", choices=("cards", "games", "progress", "phrases", "pwa", "look", "a11y", "music"), help="run only the word cards (phase 1), games (phase 2), progress (phase 3), phrases (phase 4/8), offline app or look (phase 5), keyboard focus and reduced motion (phase 7), background music (phase 8)")
    ap.add_argument("--show-pass", action="store_true", help="also list every passed check")
    ap.add_argument("--qa", action="store_true", help="acceptance run: write screenshots to qa/ instead of /tmp/ew-selftest-qa/")
    args = ap.parse_args()
    qa_root = ROOT / "qa" if args.qa else TMP_QA
    use_qa_root(qa_root)
    parts = [args.only] if args.only else ["cards", "games", "progress", "phrases", "pwa", "look", "a11y", "music"]
    for folder, part in ((QA, "cards"), (QA2, "games"), (QA3, "progress"), (QA4, "phrases"), (QA5, "look"), (QA7, "a11y"), (QA8, "music")):
        if part in parts:
            folder.mkdir(parents=True, exist_ok=True)
            for old in folder.glob("*.png"):
                old.unlink()
    words = json.loads((ROOT / "data/words.json").read_text())
    themes = json.loads((ROOT / "data/themes.json").read_text())
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/"
    run = Run()
    try:
        for _ in range(50):
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
                break
            time.sleep(0.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chrome)
            if "cards" in parts:
                for name, opts in VIEWPORTS.items():
                    flow(run, browser, base, name, opts, words, themes)
                special_cases(run, browser, base, words)
                contact_sheet(browser, base, words, themes)
            if "games" in parts:
                for name, opts in VIEWPORTS.items():
                    games_flow(run, browser, base, name, opts, words)
            if "progress" in parts:
                for name in PROGRESS_SIZES:
                    progress_flow(run, browser, base, name, VIEWPORTS[name], words)
                for name in ("ipad-portrait", "ipad-landscape", "ipad-pro"):
                    legacy_case(run, browser, base, name, VIEWPORTS[name])
                    jar_case(run, browser, base, name, VIEWPORTS[name])
            if "phrases" in parts:
                phrase_sheet(browser, base)
                phrase_voice_cases(run, browser, base)
                for name, opts in VIEWPORTS.items():
                    phrases_flow(run, browser, base, name, opts)
            if "pwa" in parts:
                pwa_flow(run, browser)
            if "look" in parts:
                overview_sheet(browser, base)
                for name in ("ipad-portrait", "ipad-landscape", "ipad-pro"):
                    look_flow(run, browser, base, name, VIEWPORTS[name])
            if "music" in parts:
                for name in ("ipad-portrait", "ipad-landscape", "ipad-pro"):
                    try:
                        music_flow(run, browser, base, name, VIEWPORTS[name])
                    except Exception as e:
                        import traceback
                        print(traceback.format_exc(), flush=True)
                        run.check(False, f"[{name}/music] stopped: {str(e).splitlines()[0]}")
            if "a11y" in parts:
                cases = [(a11y_flow, name, ()) for name in ("ipad-portrait", "ipad-landscape", "ipad-pro")]
                cases += [(motion_case, "ipad-portrait", (reduce,)) for reduce in (False, True)]
                for fn, name, more in cases:
                    try:
                        fn(run, browser, base, name, VIEWPORTS[name], *more)
                    except Exception as e:
                        import traceback
                        print(traceback.format_exc(), flush=True)
                        run.check(False, f"[{name}/{fn.__name__}] stopped: {str(e).splitlines()[0]}")
            browser.close()
    finally:
        server.terminate()
        if sys.exc_info()[0]:  # crashed: still show what failed before it
            print("\n".join(run.failures))
    if args.show_pass:
        print("\n".join(run.notes))
    print("\n".join(run.failures) if run.failures else "")
    print(f"{len(run.notes)} passed, {len(run.failures)} failed; screenshots in {qa_root}/phase-1..8/")
    sys.exit(1 if run.failures else 0)


if __name__ == "__main__":
    main()
