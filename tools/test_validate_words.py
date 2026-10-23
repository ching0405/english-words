#!/usr/bin/env python3
"""Proves tools/validate-words.py blocks bad data.

Each case copies data/ and images/ to a temp folder, breaks one thing and
expects the validator to fail (or only warn). Usage:
    python3 tools/test_validate_words.py
"""
import json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate-words.py"


def edit_words(fn):
    def apply(root):
        p = root / "data/words.json"
        words = json.loads(p.read_text())
        fn(words, root)
        p.write_text(json.dumps(words, ensure_ascii=False))
    return apply


def edit_json(rel, fn):
    def apply(root):
        p = root / rel
        data = json.loads(p.read_text())
        fn(data)
        p.write_text(json.dumps(data, ensure_ascii=False))
    return apply


def write(rel, content):
    def apply(root):
        (root / rel).write_bytes(content if isinstance(content, bytes) else content.encode())
    return apply


def both(*fns):
    def apply(root):
        for f in fns:
            f(root)
    return apply


def site(*fns):
    """Copy the rest of the site (page, code, sw.js) so the offline-cache check runs."""
    def apply(root):
        for rel in ("index.html", "manifest.webmanifest", "sw.js"):
            shutil.copy(ROOT / rel, root / rel)
        for rel in ("css", "js", "icons"):
            shutil.copytree(ROOT / rel, root / rel)
        for fn in fns:
            fn(root)
    return apply


def set_image(index, rel):
    return edit_words(lambda w, r: w[index].__setitem__("image", rel))


PNG_256 = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (256).to_bytes(4, "big") * 2 + b"\x08\x06\x00\x00\x00"

# (name, change, expected exit code, text that must appear in the output)
CASES = [
    ("real data passes", lambda r: None, 0, "OK:"),
    ("duplicate english, other case", edit_words(lambda w, r: w.append(dict(w[0], id="goat_two", english=w[0]["english"].upper()))), 1, "already used"),
    ("duplicate id", edit_words(lambda w, r: w.append(dict(w[0], english="billy goat"))), 1, "duplicate id"),
    ("missing chinese", edit_words(lambda w, r: w[0].pop("chinese")), 1, "missing or empty 'chinese'"),
    ("bad id", edit_words(lambda w, r: w[0].__setitem__("id", "Teddy Bear")), 1, "lowercase"),
    ("parent-only id prefix", edit_words(lambda w, r: w[0].__setitem__("id", "my_word_goat")), 1, "my_"),
    ("unknown theme", edit_words(lambda w, r: w[0].__setitem__("theme", "space")), 1, "not in themes.json"),
    ("image file missing", set_image(0, "images/words/nope.svg"), 1, "file not found"),
    ("svg without viewBox", both(write("images/words/novb.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"/>'),
                                 set_image(0, "images/words/novb.svg")), 1, "no viewBox"),
    ("svg not square", both(write("images/words/wide.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 512"/>'),
                            set_image(0, "images/words/wide.svg")), 1, "must be square"),
    ("png too small", both(write("images/words/tiny.png", PNG_256), set_image(0, "images/words/tiny.png")), 1, "at least 512"),
    ("fake png", both(write("images/words/fake.png", b"hello"), set_image(0, "images/words/fake.png")), 1, "not a PNG"),
    ("path escapes site", set_image(0, "../secret.svg"), 1, "relative path"),
    ("audio file missing", edit_words(lambda w, r: w[0].__setitem__("audio", "audio/words/goat.mp3")), 1, "file not found"),
    ("broken JSON", write("data/words.json", "[{"), 1, "invalid JSON"),
    ("voice line changed, not re-recorded", edit_json("data/voice-zh.json", lambda v: v.__setitem__("praise.1", "答對囉！")), 1, "text changed since it was recorded"),
    ("voice line added, no mp3", edit_json("data/voice-zh.json", lambda v: v.__setitem__("praise.5", "真厲害！")), 1, "mp3 missing"),
    ("theme renamed, voice not re-recorded", edit_json("data/themes.json", lambda t: t[0].__setitem__("chinese", "小動物")), 1, "theme.animals"),
    ("voice mp3 in the wrong format", write("audio/zh/praise.1.mp3", b"\xff\xfb\x90\x64" + bytes(2000)), 1, "expected 24 kHz"),
    ("whole site, offline list up to date", site(), 0, "OK"),
    ("new picture, offline list not rebuilt", site(write("images/words/panda.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"/>')), 1, "build-sw.py"),
    ("orphan image only warns", write("images/words/extra.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"/>'), 0, "orphan image"),
]


def main():
    failed = 0
    for name, change, want_code, want_text in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            shutil.copytree(ROOT / "data", root / "data")
            shutil.copytree(ROOT / "images", root / "images")
            shutil.copytree(ROOT / "audio", root / "audio")
            change(root)
            res = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root)], capture_output=True, text=True)
            ok = res.returncode == want_code and want_text in res.stdout
            failed += not ok
            print(("PASS" if ok else "FAIL"), name, "" if ok else f"\n  exit {res.returncode}, output:\n{res.stdout}")
    print(f"{len(CASES) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
