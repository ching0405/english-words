#!/usr/bin/env python3
"""Check data/words.json and data/themes.json before committing.

Errors (exit 1): bad JSON, missing/empty fields, bad id, duplicate id or
english (case-insensitive), unknown theme, missing or invalid image (SVG needs
a square viewBox; PNG/WebP must be square and at least 512px), missing audio.
Chinese voice lines (data/voice-zh.json + theme names): every line must have
audio/zh/<key>.mp3 recorded from its current text (manifest hash matches).
Warnings (exit 0): images in images/words that no word uses, empty themes,
unknown fields, mp3s in audio/zh that no line uses.
Offline cache: when the folder has sw.js, its file list and version must match
the files now (python3 tools/build-sw.py), so the home-screen app refreshes.

Usage: python3 tools/validate-words.py [--root DIR]
Standard library only.
"""
import argparse, importlib.util, json, pathlib, re, struct, sys
import xml.etree.ElementTree as ET

# Same line list and hash as the recorder.
_spec = importlib.util.spec_from_file_location("gen_voice", pathlib.Path(__file__).with_name("gen-voice.py"))
gen_voice = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_voice)
_spec = importlib.util.spec_from_file_location("build_sw", pathlib.Path(__file__).with_name("build-sw.py"))
build_sw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_sw)

WORD_FIELDS = ("id", "english", "chinese", "image", "theme")
WORD_OPTIONAL = ("audio",)
THEME_FIELDS = ("id", "english", "chinese", "color", "icon")
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
IMAGE_EXT = {".svg", ".png", ".webp"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}
MIN_PX = 512


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_json(path, rep):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.error(f"{path.name}: file not found")
        return None
    except json.JSONDecodeError as e:
        rep.error(f"{path.name}: invalid JSON ({e})")
        return None
    if not isinstance(data, list):
        rep.error(f"{path.name}: must be a JSON array")
        return None
    return data


def local_file(root, rel, where, rep):
    """Resolve a relative path inside the site; report problems."""
    if not isinstance(rel, str) or not rel.strip():
        rep.error(f"{where}: path is empty")
        return None
    if rel.startswith("/") or "://" in rel or ".." in pathlib.PurePosixPath(rel).parts:
        rep.error(f"{where}: '{rel}' must be a relative path inside the site (no leading /, no ..)")
        return None
    path = root / rel
    if not path.is_file():
        rep.error(f"{where}: file not found: {rel}")
        return None
    return path


def image_size(path):
    """(width, height) for SVG viewBox / PNG / WebP, or raise ValueError."""
    ext = path.suffix.lower()
    if ext == ".svg":
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            raise ValueError(f"not valid SVG/XML ({e})")
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("root element is not <svg>")
        vb = root.get("viewBox")
        if not vb:
            raise ValueError("SVG has no viewBox")
        try:
            nums = [float(n) for n in re.split(r"[\s,]+", vb.strip())]
        except ValueError:
            nums = []
        if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
            raise ValueError(f"bad viewBox '{vb}'")
        return nums[2], nums[3]
    head = path.read_bytes()[:64]
    if ext == ".png":
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            raise ValueError("not a PNG file")
        return struct.unpack(">II", head[16:24])
    if ext == ".webp":
        if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
            raise ValueError("not a WebP file")
        kind = head[12:16]
        if kind == b"VP8X":
            return 1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little")
        if kind == b"VP8L":
            b = int.from_bytes(head[21:25], "little")
            return 1 + (b & 0x3FFF), 1 + ((b >> 14) & 0x3FFF)
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return w & 0x3FFF, h & 0x3FFF
        raise ValueError("unknown WebP format")
    raise ValueError(f"unsupported image type {ext}")


def check_image(root, rel, where, rep):
    path = local_file(root, rel, where, rep)
    if not path:
        return
    if path.suffix.lower() not in IMAGE_EXT:
        rep.error(f"{where}: {rel} must be .svg, .png or .webp")
        return
    try:
        w, h = image_size(path)
    except ValueError as e:
        rep.error(f"{where}: {rel}: {e}")
        return
    if abs(w - h) > 0.5:
        rep.error(f"{where}: {rel} must be square (is {w:g}x{h:g})")
    if path.suffix.lower() != ".svg" and min(w, h) < MIN_PX:
        rep.error(f"{where}: {rel} is {w}x{h}; bitmaps need at least {MIN_PX}x{MIN_PX}")


def check_text_fields(item, fields, where, rep):
    ok = True
    for f in fields:
        v = item.get(f)
        if not isinstance(v, str) or not v.strip():
            rep.error(f"{where}: missing or empty '{f}'")
            ok = False
        elif v != v.strip():
            rep.error(f"{where}: '{f}' has leading/trailing spaces")
    return ok


def validate(root):
    rep = Report()
    themes = load_json(root / "data/themes.json", rep)
    words = load_json(root / "data/words.json", rep)
    if themes is None or words is None:
        return rep

    theme_ids = set()
    for n, th in enumerate(themes):
        where = f"themes.json[{n}]"
        if not isinstance(th, dict):
            rep.error(f"{where}: must be an object")
            continue
        where = f"theme '{th.get('id', n)}'"
        check_text_fields(th, THEME_FIELDS, where, rep)
        tid = th.get("id")
        if isinstance(tid, str):
            if not ID_RE.match(tid):
                rep.error(f"{where}: id must be lowercase letters, digits, underscore")
            if tid.startswith("my_"):
                rep.error(f"{where}: id must not start with my_ (kept for themes a parent adds on the device)")
            if tid in theme_ids:
                rep.error(f"{where}: duplicate theme id")
            theme_ids.add(tid)
        if isinstance(th.get("color"), str) and not COLOR_RE.match(th["color"]):
            rep.error(f"{where}: color must look like #a1b2c3")
        if isinstance(th.get("icon"), str):
            check_image(root, th["icon"], where, rep)

    ids, englishes, used_images, theme_count = set(), {}, set(), {}
    for n, w in enumerate(words):
        where = f"words.json[{n}]"
        if not isinstance(w, dict):
            rep.error(f"{where}: must be an object")
            continue
        where = f"word '{w.get('id', n)}'"
        check_text_fields(w, WORD_FIELDS, where, rep)
        extra = set(w) - set(WORD_FIELDS) - set(WORD_OPTIONAL)
        if extra:
            rep.warn(f"{where}: unknown field(s) {sorted(extra)}")
        wid = w.get("id")
        if isinstance(wid, str):
            if not ID_RE.match(wid):
                rep.error(f"{where}: id must be lowercase letters, digits, underscore (e.g. teddy_bear)")
            if wid.startswith("my_"):
                rep.error(f"{where}: id must not start with my_ (kept for words a parent adds on the device; a word from a parent backup gets a new id, see ADDING_WORDS.md)")
            if wid in ids:
                rep.error(f"{where}: duplicate id")
            ids.add(wid)
        en = w.get("english")
        if isinstance(en, str) and en.strip():
            key = " ".join(en.lower().split())
            if key in englishes:
                rep.error(f"{where}: english '{en}' already used by '{englishes[key]}'")
            englishes.setdefault(key, wid)
        th = w.get("theme")
        if isinstance(th, str):
            if th not in theme_ids:
                rep.error(f"{where}: theme '{th}' is not in themes.json")
            theme_count[th] = theme_count.get(th, 0) + 1
        if isinstance(w.get("image"), str):
            check_image(root, w["image"], where, rep)
            used_images.add(pathlib.PurePosixPath(w["image"]).as_posix())
        if "audio" in w:
            path = local_file(root, w["audio"], f"{where} audio", rep)
            if path and path.suffix.lower() not in AUDIO_EXT:
                rep.error(f"{where}: audio must be one of {sorted(AUDIO_EXT)}")

    for tid in sorted(theme_ids - set(theme_count)):
        rep.warn(f"theme '{tid}' has no words (it is hidden in the app)")
    used_images |= {th.get("icon") for th in themes if isinstance(th, dict)}
    img_dir = root / "images/words"
    if img_dir.is_dir():
        for f in sorted(img_dir.iterdir()):
            rel = f.relative_to(root).as_posix()
            if f.is_file() and not f.name.startswith(".") and rel not in used_images:
                rep.warn(f"orphan image not used by any word: {rel}")
    voice_count = check_voice(root, rep)
    if (root / "sw.js").is_file():
        try:
            if build_sw.render(root)[0] != (root / "sw.js").read_text():
                rep.error("sw.js offline file list is out of date; run python3 tools/build-sw.py")
        except ValueError as e:
            rep.error(str(e))
    if not rep.errors:
        rep.ok = f"{len(words)} words in {len(theme_count)} themes, {voice_count} Chinese voice lines"
    return rep


def mp3_format(path):
    """(sample rate, kbps, 'mono'|'stereo') from the first MPEG audio frame, or None."""
    d = path.read_bytes()[:64 * 1024]
    i = 0
    if d[:3] == b"ID3" and len(d) >= 10:
        i = 10 + ((d[6] & 0x7F) << 21 | (d[7] & 0x7F) << 14 | (d[8] & 0x7F) << 7 | (d[9] & 0x7F))
    if len(d) < i + 4 or d[i] != 0xFF or d[i + 1] & 0xE0 != 0xE0:
        return None
    version, layer = (d[i + 1] >> 3) & 3, (d[i + 1] >> 1) & 3
    if layer != 1:  # Layer III only
        return None
    rates = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}.get(version)
    kbps = ((0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320) if version == 3 else
            (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160))
    b, r = d[i + 2] >> 4, (d[i + 2] >> 2) & 3
    if not rates or r == 3 or b in (0, 15):
        return None
    return rates[r], kbps[b], "mono" if d[i + 3] >> 6 == 3 else "stereo"


def check_voice(root, rep):
    """Every Chinese line has an mp3 recorded from its current text."""
    try:
        lines = gen_voice.load_lines(root)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        rep.error(f"voice-zh.json: {e}")
        return 0
    out = root / "audio/zh"
    try:
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    for key, text in lines.items():
        mp3 = out / f"{key}.mp3"
        if not mp3.is_file():
            rep.error(f"voice '{key}': audio/zh/{key}.mp3 missing; run python3 tools/gen-voice.py")
            continue
        fmt = mp3_format(mp3)
        if fmt is None:
            rep.error(f"voice '{key}': audio/zh/{key}.mp3 is not an mp3 file")
        elif fmt != (24000, 48, "mono"):
            rep.error(f"voice '{key}': audio/zh/{key}.mp3 is {fmt}; expected 24 kHz, 48 kbps, mono (re-run gen-voice.py)")
        if manifest.get(key, {}).get("hash") != gen_voice.line_hash(text):
            rep.error(f"voice '{key}': text changed since it was recorded; run python3 tools/gen-voice.py")
    if out.is_dir():
        for f in sorted(out.glob("*.mp3")):
            if f.stem not in lines:
                rep.warn(f"audio/zh/{f.name} is not used by any voice line")
    return len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=pathlib.Path(__file__).resolve().parents[1], type=pathlib.Path)
    rep = validate(ap.parse_args().root)
    for w in rep.warnings:
        print(f"WARNING: {w}")
    for e in rep.errors:
        print(f"ERROR: {e}")
    if rep.errors:
        print(f"FAILED: {len(rep.errors)} error(s)")
        sys.exit(1)
    print(f"OK: {rep.ok}" + (f", {len(rep.warnings)} warning(s)" if rep.warnings else ""))


if __name__ == "__main__":
    main()
