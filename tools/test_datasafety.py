#!/usr/bin/env python3
"""Browser regression tests for the phase 6 data-safety review (F1–F5).

Each case injects the failure the review found, through the real parent page,
and checks that the parent's data really survives:
  F1  an import (or an edit) whose list write fails leaves the old photo as it was
  F3  a photo counts as saved only when its IndexedDB transaction completes;
      an aborted or failed transaction falls back, never a silent placeholder
  F2  a delete whose progress write fails says so, and the same word added
      again starts fresh (no old record)
  F4  two tabs adding words at the same time both keep their words
  F5  a built-in picture can belong to one word only

Runs at the three iPad sizes (820x1180, 1180x820, 1024x1366). Reuses the
helpers of tools/selftest.py (fake speech, parent gate, add form).
Screenshots go to /tmp/ew-datasafety-qa/; --qa writes them to qa/phase-6/datasafety/.

Usage: python3 tools/test_datasafety.py [--only F1,F3] [--qa] [--chrome /usr/bin/google-chrome]
Exit code 1 when any check fails.
"""
import argparse, base64, contextlib, json, pathlib, socket, subprocess, sys, time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import selftest as st  # noqa: E402

ROOT = st.ROOT
SIZES = ("ipad-portrait", "ipad-landscape", "ipad-pro")
OUT = pathlib.Path("/tmp/ew-datasafety-qa")
LIST = "ew.custom.v1"

# The stored photo of one list item, wherever the list says it is kept.
STORED_PHOTO = """id => new Promise(done => {
  const list = JSON.parse(localStorage.getItem('ew.custom.v1') || '{"words":[],"phrases":[]}');
  const item = list.words.concat(list.phrases).find(w => w.id === id);
  if (!item) return done(null);
  if (item.image !== 'idb') return done(item.image);
  const r = indexedDB.open('picture-words', 1);
  r.onsuccess = () => { const g = r.result.transaction('photos').objectStore('photos').get(item.photo || item.id);
    g.onsuccess = () => { done(g.result || null); r.result.close(); }; g.onerror = () => done(null); };
  r.onerror = () => done(null); })"""

PHOTO_KEYS = """() => new Promise(done => { const r = indexedDB.open('picture-words', 1);
  r.onsuccess = () => { const g = r.result.transaction('photos').objectStore('photos').getAllKeys();
    g.onsuccess = () => { done(g.result.map(String).sort()); r.result.close(); }; }; })"""

# A 512x512 blue JPEG made by the page itself.
BLUE = """() => { const c = document.createElement('canvas'); c.width = c.height = 512;
  const g = c.getContext('2d'); g.fillStyle = '#1040e0'; g.fillRect(0, 0, 512, 512); return c.toDataURL('image/jpeg', 0.85); }"""

# Only writes of `key` to localStorage fail (QuotaExceededError); everything else works.
FAIL_KEY = """key => { window.__realSet = window.__realSet || Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (k === key) throw new DOMException('full', 'QuotaExceededError');
    return window.__realSet.call(this, k, v); }; }"""
HEAL = "() => { if (window.__realSet) Storage.prototype.setItem = window.__realSet; }"


def open_page(browser, base, name, errors):
    return st.open_site(browser, base, st.VIEWPORTS[name], {"lateMs": 0, "event": True}, errors)


def reload_parent(page):
    page.reload()
    page.wait_for_selector("#phrasesBtn:not([disabled])")
    st.enter_parent(page)


def toast_has(page, text, timeout=5000):
    try:
        page.wait_for_function("t => !document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes(t)", arg=text, timeout=timeout)
        return True
    except Exception:
        return False


def f1(run, page, tag, snap):
    """Import (and edit) with the list write failing: the old photo stays."""
    st.enter_parent(page)
    run.check(st.add_item(page, "word", "cat", "貓", photo=st.test_photo(), theme="animals") == "", f"{tag} add cat with a photo")
    old = page.evaluate(STORED_PHOTO, "my_word_cat")
    keys = page.evaluate(PHOTO_KEYS)
    saved = page.evaluate(f"() => localStorage.getItem('{LIST}')")
    blue = page.evaluate(BLUE)
    doc = page.evaluate("() => Custom.backup()")
    doc["words"][0]["image"] = blue
    page.evaluate(FAIL_KEY, LIST)
    page.set_input_files("#importFile", files=[{"name": "blue.json", "mimeType": "application/json", "buffer": json.dumps(doc).encode()}])
    page.wait_for_function("() => document.querySelector('#ioMsg').textContent.startsWith('沒有匯入')", timeout=15000)
    snap("F1-import-failed")
    run.check("原本的資料都沒有改變" in page.inner_text("#ioMsg"), f"{tag} F1 import: the failure message is shown ({page.inner_text('#ioMsg')})")
    run.check(page.evaluate(STORED_PHOTO, "my_word_cat") == old, f"{tag} F1 import: the old photo is unchanged right after the failure")
    # Edit with a new photo, list write still failing.
    page.click('.prow[data-id="my_word_cat"] [data-act=edit]')
    page.wait_for_selector("#parentEdit:not([hidden])")
    page.set_input_files("#fFile", files=[{"name": "blue.jpg", "mimeType": "image/jpeg", "buffer": base64.b64decode(blue.split(",", 1)[1])}])
    page.wait_for_function("() => (document.querySelector('#fImg').getAttribute('src') || '').startsWith('data:image/jpeg')")
    page.click("#fSave")
    page.wait_for_function("() => document.querySelector('#fMsg').textContent", timeout=10000)
    run.check(page.evaluate(STORED_PHOTO, "my_word_cat") == old, f"{tag} F1 edit: a failed save leaves the old photo")
    page.click("#parentEdit [data-go=parent]")
    page.evaluate(HEAL)
    reload_parent(page)
    snap("F1-after-reload")
    run.check(page.evaluate(f"() => localStorage.getItem('{LIST}')") == saved, f"{tag} F1: the saved list is byte-for-byte the same")
    run.check(page.evaluate(STORED_PHOTO, "my_word_cat") == old, f"{tag} F1: after reload the photo is still the old one, not the imported one")
    run.check(page.evaluate(PHOTO_KEYS) == keys, f"{tag} F1: no half-written photo is left behind {page.evaluate(PHOTO_KEYS)} vs {keys}")


# The review's injection: the put request succeeds, then the transaction aborts.
ABORT_AFTER_SUCCESS = """() => { const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function () { const r = put.apply(this, arguments);
    r.addEventListener('success', () => { try { r.transaction.abort(); } catch (e) {} }); return r; }; }"""
# The request itself fails: the transaction is aborted before the put completes.
ABORT_BEFORE_SUCCESS = """() => { const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function () { const r = put.apply(this, arguments);
    try { this.transaction.abort(); } catch (e) {} return r; }; }"""


def f3(run, page, tag, snap):
    """A photo is saved only once its transaction completes."""
    for label, inject, english in (("abort after success", ABORT_AFTER_SUCCESS, "cat"), ("request error", ABORT_BEFORE_SUCCESS, "bird")):
        page.evaluate(inject)
        st.enter_parent(page)
        msg = st.add_item(page, "word", english, "動物", photo=st.test_photo(), theme="animals")
        if english == "cat":
            snap("F3-saved-after-abort")
        reload_parent(page)
        item = [w for w in page.evaluate("() => Custom.view().words") if w["english"] == english]
        if msg == "":
            ok = item and item[0]["image"].startswith("data:image/jpeg")
            run.check(ok, f"{tag} F3 {label}: shown as saved, so after reload the photo is really there ({item[0]['image'][:30] if item else 'missing'})")
        else:
            run.check(not item, f"{tag} F3 {label}: refused with a message ({msg}) and nothing half-saved")
        if english == "cat":
            snap("F3-after-reload")
        st.go_home(page)


def f2(run, page, tag, snap):
    """Delete with the progress write failing."""
    st.enter_parent(page)
    run.check(st.add_item(page, "word", "cat", "貓", gallery="images/phrases/ready.svg", theme="animals") == "", f"{tag} add cat")
    page.evaluate("() => { Progress.answer('my_word_cat', true); Progress.answer('goat', true); }")
    page.evaluate(FAIL_KEY, "ew.progress")
    page.click('.prow[data-id="my_word_cat"] [data-act=delete]')
    page.wait_for_function("() => !document.querySelector('.prow[data-id=\"my_word_cat\"]')")
    warned = toast_has(page, "學習紀錄")
    snap("F2-delete-progress-failed")
    run.check(warned, f"{tag} F2: the failed progress clean-up is reported ({page.inner_text('#toast')})")
    page.evaluate(HEAL)
    reload_parent(page)
    run.check(st.add_item(page, "word", "cat", "貓", gallery="images/phrases/ready.svg", theme="animals") == "", f"{tag} F2: add cat again")
    new = [w["id"] for w in page.evaluate("() => Custom.list().words") if w["english"] == "cat"]
    rec = page.evaluate("id => Progress.get(id)", new[0]) if new else "missing"
    run.check(rec is None, f"{tag} F2: the re-added word starts with no record ({new}: {rec})")
    stored = page.evaluate("() => JSON.parse(localStorage.getItem('ew.progress')).words")
    run.check(stored.get("goat", {}).get("right") == 1, f"{tag} F2: built-in progress (goat) is kept")
    page.reload()
    page.wait_for_selector("#phrasesBtn:not([disabled])")
    run.check(page.evaluate("id => Progress.get(id)", new[0] if new else "x") is None, f"{tag} F2: still no old record after another reload")


def f4(run, page, tag, snap, ctx):
    """Two tabs add words without reloading: neither wipes the other."""
    other = ctx.new_page()
    errors = []
    st.watch(other, errors)
    other.goto(page.url)
    other.wait_for_selector("#phrasesBtn:not([disabled])")
    st.enter_parent(page)
    st.enter_parent(other)
    run.check(st.add_item(page, "word", "cat", "貓", photo=st.test_photo(), theme="animals") == "", f"{tag} F4: tab A adds cat")
    run.check(st.add_item(other, "word", "dog", "狗", gallery="images/phrases/ready.svg", theme="animals") == "", f"{tag} F4: tab B adds dog without reloading")
    words = lambda p: sorted(w["english"] for w in p.evaluate(f"() => JSON.parse(localStorage.getItem('{LIST}')).words"))
    run.check(words(page) == ["cat", "dog"], f"{tag} F4: both words are saved {words(page)}")
    try:
        page.wait_for_function("() => document.querySelectorAll('#myWords .prow').length === 2", timeout=3000)
        live = True
    except Exception:
        live = page.locator("#myWords .prow").count()
    snap("F4-tabA-sees-tabB")
    run.check(live is True, f"{tag} F4: tab A's list shows tab B's word without reloading ({live})")
    run.check(st.add_item(page, "word", "fish", "魚", gallery="images/phrases/hello.svg", theme="animals") == "", f"{tag} F4: tab A adds another word")
    run.check(words(other) == ["cat", "dog", "fish"], f"{tag} F4: tab A's save keeps tab B's word {words(other)}")
    # Another tab's save whose storage event has not arrived yet (written here
    # directly, so this tab gets no event): the next save still keeps it.
    page.evaluate("""() => { const l = JSON.parse(localStorage.getItem('ew.custom.v1'));
      l.words.push({id: 'my_word_owl', english: 'owl', chinese: '貓頭鷹', theme: 'animals', image: 'images/phrases/sorry.svg'});
      localStorage.setItem('ew.custom.v1', JSON.stringify(l)); }""")
    run.check(st.add_item(page, "word", "frog", "青蛙", gallery="images/phrases/please.svg", theme="animals") == "", f"{tag} F4: tab A adds frog")
    run.check(words(page) == ["cat", "dog", "fish", "frog", "owl"], f"{tag} F4: a save made just before is kept, not overwritten {words(page)}")
    reload_parent(page)
    run.check(page.locator("#myWords .prow").count() == 5 and page.evaluate(STORED_PHOTO, "my_word_cat"), f"{tag} F4: after reload all five words and cat's photo are there")
    other.close()
    run.check(not errors, f"{tag} F4: no errors in tab B {errors}")


def f5(run, page, tag, snap):
    """A built-in picture is one word's picture only."""
    st.enter_parent(page)
    page.click("#addWordBtn")
    page.wait_for_selector("#parentEdit:not([hidden])")
    page.click("#fGalleryBtn")
    offered = page.eval_on_selector_all(".pgallery-pick", "e => e.map(x => x.dataset.src)")
    page.locator("#fGallery").scroll_into_view_if_needed()
    snap("F5-gallery")
    run.check("images/words/zebra.svg" not in offered and offered, f"{tag} F5: the gallery does not offer pictures other words use {offered}")
    page.click("#parentEdit [data-go=parent]")
    err = page.evaluate(BUILT_IN + """.then(b => Custom.saveWord({english: 'horse', chinese: '馬', theme: 'animals'}, 'images/words/zebra.svg', b))
      .then(() => '', e => e.message)""")
    run.check("zebra" in err, f"{tag} F5: saving a word with zebra's picture is refused ({err!r})")
    run.check(not any(w["english"] == "horse" for w in page.evaluate("() => Custom.list().words")), f"{tag} F5: nothing was saved")


# What the parent page checks against (App's builtIn()), rebuilt from data/.
BUILT_IN = """() => Promise.all(['data/words.json', 'data/phrases.json', 'data/themes.json'].map(f => fetch(f).then(r => r.json())))
  .then(([words, phrases, themes]) => ({words, phrases, themes, gallery: [...new Set(words.concat(phrases).map(w => w.image))]}))"""


CASES = {"F1": f1, "F3": f3, "F2": f2, "F4": f4, "F5": f5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    ap.add_argument("--only", default=",".join(CASES))
    ap.add_argument("--qa", action="store_true", help="acceptance run: screenshots to qa/phase-6/datasafety/")
    args = ap.parse_args()
    out = ROOT / "qa/phase-6/datasafety" if args.qa else OUT
    out.mkdir(parents=True, exist_ok=True)
    cases = [c.strip() for c in args.only.split(",") if c.strip()]
    port = st.free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/"
    run = st.Run()
    try:
        for _ in range(50):
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
                break
            time.sleep(0.1)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chrome)
            for case in cases:
                for name in SIZES:
                    tag = f"[{name}/{case}]"
                    errors = []
                    ctx, page = open_page(browser, base, name, errors)
                    page.on("dialog", lambda d: d.accept())
                    snap = lambda label, page=page, name=name: st.shot(page, f"{name}-{label}", out)
                    try:
                        if case == "F4":
                            f4(run, page, tag, snap, ctx)
                        else:
                            CASES[case](run, page, tag, snap)
                    except Exception as e:
                        import traceback
                        where = [f"{f.name}:{f.lineno}" for f in traceback.extract_tb(e.__traceback__) if f.filename == __file__][-2:]
                        run.check(False, f"{tag} stopped at {where}: {str(e).splitlines()[0]}")
                    real = [e for e in errors if "QuotaExceeded" not in e and "AbortError" not in e]
                    run.check(not real, f"{tag} no unexpected errors {real}")
                    ctx.close()
            browser.close()
    finally:
        server.terminate()
    print("\n".join(run.failures))
    print(f"{len(run.notes)} passed, {len(run.failures)} failed; screenshots in {out}/")
    sys.exit(1 if run.failures else 0)


if __name__ == "__main__":
    main()
