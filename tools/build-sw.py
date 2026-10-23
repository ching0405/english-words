#!/usr/bin/env python3
"""Write the offline file list and version into sw.js.

The list is every file the game loads: the page, manifest, icons, css, js,
data/*.json, images and audio (mp3). VERSION is a hash of all of them, so any
change (a new word, a fixed picture, a re-recorded line) makes a new version
and the home-screen app refreshes its cache.

The first open downloads the whole list, so --check also keeps it small:
at most MAX_TOTAL bytes in all and MAX_FILE bytes for any one file.

Usage: python3 tools/build-sw.py          rewrite sw.js
       python3 tools/build-sw.py --check  exit 1 if sw.js is out of date or the list is too big
"""
import hashlib, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATTERNS = ["index.html", "manifest.webmanifest", "icons/*.png", "icons/*.svg", "css/*.css",
            "js/*.js", "js/games/*.js", "data/*.json", "images/**/*.svg", "images/**/*.png",
            "images/**/*.webp", "audio/**/*.mp3"]
MAX_TOTAL = 2_500_000   # 2.5 MB; 1.27 MB at phase 7
MAX_FILE = 300_000      # 300 KB; the biggest at phase 7 is icons/icon-512.png, 51 KB
BLOCK = re.compile(r"(// <build-sw>[^\n]*\n).*?(// </build-sw>)", re.S)


def files(root=ROOT):
    return sorted({p.relative_to(root).as_posix() for pat in PATTERNS for p in root.glob(pat) if p.is_file()})


def block(root=ROOT):
    names = files(root)
    h = hashlib.sha256()
    for name in names:
        h.update(name.encode() + b"\0" + (root / name).read_bytes())
    version = h.hexdigest()[:12]
    listing = ",\n  ".join(json.dumps(n) for n in ["./"] + names)
    return f"var VERSION = '{version}';\nvar FILES = [\n  {listing}\n];\n", version, len(names)


def size(root=ROOT):
    """(total bytes of the offline list, problems): what the first open downloads."""
    sizes = {name: (root / name).stat().st_size for name in files(root)}
    total = sum(sizes.values())
    problems = [f"{name} is {n / 1000:.0f} KB (max {MAX_FILE / 1000:.0f} KB per file)"
                for name, n in sorted(sizes.items()) if n > MAX_FILE]
    if total > MAX_TOTAL:
        problems.append(f"the offline list is {total / 1e6:.2f} MB (max {MAX_TOTAL / 1e6:.1f} MB)")
    return total, problems


def render(root=ROOT):
    """(new sw.js text, version, file count); ValueError when the block is missing."""
    body, version, n = block(root)
    text = (root / "sw.js").read_text()
    if not BLOCK.search(text):
        raise ValueError("sw.js: missing the // <build-sw> ... // </build-sw> block")
    return BLOCK.sub(lambda m: m.group(1) + body + m.group(2), text), version, n


def main():
    root = pathlib.Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else ROOT
    sw = root / "sw.js"
    new, version, n = render(root)
    if "--check" in sys.argv:
        total, problems = size(root)
        if new != sw.read_text():
            problems.insert(0, "sw.js is out of date: run python3 tools/build-sw.py")
        for problem in problems:
            print(problem)
        if problems:
            sys.exit(1)
        print(f"sw.js OK, version {version}, {n} files, first open downloads {total / 1e6:.2f} MB")
        return
    sw.write_text(new)
    print(f"sw.js version {version}, {n} files")


if __name__ == "__main__":
    main()
