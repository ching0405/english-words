#!/usr/bin/env python3
"""Record every Chinese voice line as an mp3 with Microsoft Edge neural TTS.

Lines come from data/voice-zh.json (key -> text) plus each theme name in
data/themes.json (key "theme.<id>"). The recordings as edge-tts makes them
(24 kHz, 48 kbps, mono) go to audio-src/zh/<key>.mp3 (originals, kept as they
are); then tools/normalize-audio.py makes the played files audio/zh/<key>.mp3,
all equally loud. audio/zh/manifest.json: key -> text and hash (+ loudness).
Only new or changed lines are recorded (hash of voice + rate + text); mp3s
for keys that no longer exist are removed from both folders. Safe to re-run.

Usage: python3 tools/gen-voice.py [--force] [--edge-tts PATH]
Needs network access (edge-tts calls Microsoft's online voice service).
"""
import argparse, hashlib, json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "audio" / "zh"
SRC = ROOT / "audio-src" / "zh"
MANIFEST = OUT / "manifest.json"
VOICE = "zh-TW-HsiaoChenNeural"
RATE = "-8%"
KEY_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")


def line_hash(text):
    return hashlib.sha1(f"{VOICE}|{RATE}|{text}".encode("utf-8")).hexdigest()[:16]


def load_lines(root=ROOT):
    """All Chinese lines: key -> text. Raises ValueError on bad data."""
    lines = json.loads((root / "data/voice-zh.json").read_text(encoding="utf-8"))
    if not isinstance(lines, dict):
        raise ValueError("data/voice-zh.json must be an object of key -> text")
    for th in json.loads((root / "data/themes.json").read_text(encoding="utf-8")):
        key = f"theme.{th['id']}"
        if key in lines:
            raise ValueError(f"{key} comes from themes.json; do not repeat it in voice-zh.json")
        lines[key] = th["chinese"]
    for key, text in lines.items():
        if not KEY_RE.match(key):
            raise ValueError(f"bad key '{key}' (lowercase letters, digits, _ and dots)")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"'{key}' has no text")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="re-record every line")
    ap.add_argument("--edge-tts", default=shutil.which("edge-tts") or str(pathlib.Path.home() / ".local/bin/edge-tts"))
    args = ap.parse_args()
    try:
        lines = load_lines()
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        sys.exit(f"ERROR: {e}")
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    manifest, made, kept = {}, 0, 0
    for key, text in lines.items():
        h = line_hash(text)
        mp3 = SRC / f"{key}.mp3"
        if not args.force and mp3.exists() and old.get(key, {}).get("hash") == h:
            manifest[key] = old[key]
            kept += 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmp_mp3 = pathlib.Path(tmp) / "out.mp3"
            res = subprocess.run([args.edge_tts, "--voice", VOICE, f"--rate={RATE}", "--text", text, "--write-media", str(tmp_mp3)],
                                 capture_output=True, text=True, timeout=120)
            if res.returncode or not tmp_mp3.exists() or tmp_mp3.stat().st_size < 1000:
                sys.exit(f"ERROR: edge-tts failed for '{key}': {res.stderr.strip()[-300:]}")
            shutil.move(str(tmp_mp3), mp3)
        manifest[key] = {"text": text, "hash": h}
        made += 1
        print(f"recorded {key}: {text}")
    removed = 0
    for folder in (SRC, OUT):
        for f in folder.glob("*.mp3"):
            if f.stem not in lines:
                f.unlink()
                removed += folder == SRC
                print(f"removed {f.relative_to(ROOT)} (line no longer used)")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Same loudness for every line: new or changed originals -> audio/zh/.
    if subprocess.run([sys.executable, str(ROOT / "tools/normalize-audio.py")]).returncode:
        sys.exit("ERROR: tools/normalize-audio.py failed")
    print(f"OK: {len(lines)} lines ({made} recorded, {kept} unchanged, {removed} removed); voice {VOICE} rate {RATE}")


if __name__ == "__main__":
    main()
