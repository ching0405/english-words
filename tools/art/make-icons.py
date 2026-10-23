#!/usr/bin/env python3
"""Home-screen icons: the lion on a sunny tile, rendered with headless Chrome.

Writes icons/icon.svg plus PNGs: icon-192, icon-512 (purpose "any"),
icon-maskable-512 (lion inside the 80% safe circle) and apple-touch-icon (180).
Usage: python3 tools/art/make-icons.py [--chrome /usr/bin/google-chrome]
"""
import argparse, base64, pathlib, re

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "icons"


def tile(art, scale):
    """512×512 tile: sun-yellow ground, soft dots, the lion centred at `scale`."""
    inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", art, flags=re.S)
    off = 256 * (1 - scale)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="7" fill="#ffe680"/>'
                   for y in range(32, 512, 64) for x in range(32 + (y // 64 % 2) * 32, 512, 64))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            f'<rect width="512" height="512" fill="#ffd43b"/>{dots}'
            f'<circle cx="256" cy="262" r="{200 * scale / .8:.0f}" fill="#fff6e5"/>'
            f'<g transform="translate({off:.1f} {off:.1f}) scale({scale})">{inner}</g></svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    lion = (ROOT / "images/words/lion.svg").read_text()
    full, safe = tile(lion, .86), tile(lion, .7)  # maskable: keep inside the 80% circle
    (OUT / "icon.svg").write_text(full)
    jobs = [("icon-192.png", full, 192), ("icon-512.png", full, 512),
            ("icon-maskable-512.png", safe, 512), ("apple-touch-icon.png", full, 180)]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome)
        for name, svg, size in jobs:
            page = browser.new_page(viewport={"width": size, "height": size})
            src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
            page.set_content(f'<body style="margin:0"><img src="{src}" width="{size}" height="{size}" style="display:block">')
            page.wait_for_function("() => document.images[0].complete")
            page.screenshot(path=str(OUT / name), omit_background=False)
            page.close()
        browser.close()
    print("wrote", ", ".join(n for n, _, _ in jobs), "and icon.svg in icons/")


if __name__ == "__main__":
    main()
