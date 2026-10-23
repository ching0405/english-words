#!/usr/bin/env python3
"""PWA and accessibility audit (phase 5 acceptance).

1. Lighthouse 11.7.1 (the last version with the PWA category) on the home
   page: PWA and accessibility scores, reports saved as JSON + HTML.
2. Lighthouse only sees the first screen, so axe-core (the engine behind its
   accessibility score) also runs on every screen and game: WCAG 2 A/AA rules.

Needs network the first time (npx downloads Lighthouse) and /usr/bin/google-chrome.
Usage: python3 tools/lighthouse.py [--out DIR]   (default /tmp/ew-lighthouse)
       python3 tools/lighthouse.py --url https://<user>.github.io/<repo>/   the live site instead of a local server
Exit 1 when a score is below 1.0 (PWA: every audit that applies passes) or axe finds a violation.
"""
import argparse, contextlib, glob, json, os, pathlib, socket, subprocess, sys, time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIGHTHOUSE = "lighthouse@11.7.1"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lighthouse(url, out):
    env = dict(os.environ, CHROME_PATH="/usr/bin/google-chrome")
    subprocess.run(["npx", "-y", LIGHTHOUSE, url, "--only-categories=pwa,accessibility", "--output=json", "--output=html",
                    f"--output-path={out / 'lighthouse'}", "--chrome-flags=--headless=new --no-sandbox", "--quiet"],
                   check=True, env=env, timeout=600)
    report = json.loads((out / "lighthouse.report.json").read_text())
    lines, ok = [], True
    for key, cat in report["categories"].items():
        lines.append(f"Lighthouse {key}: {cat['score']:.2f}")
        ok &= cat["score"] == 1
        for ref in cat["auditRefs"]:
            audit = report["audits"][ref["id"]]
            if audit["score"] is not None and audit["score"] < 1:
                lines.append(f"  FAIL {ref['id']}: {audit['title']}")
    return ok, lines


def axe_screens(base, axe_js):
    """Visit every screen like a child would and run axe on each."""
    found, lines = 0, []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        for size in ({"width": 820, "height": 1180}, {"width": 1180, "height": 820}):
            ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True, service_workers="block")
            page = ctx.new_page()
            page.goto(base)
            page.wait_for_selector("#phrasesBtn:not([disabled])")

            def check(label):
                nonlocal found
                page.wait_for_timeout(700)
                page.add_script_tag(content=axe_js) if not page.evaluate("() => !!window.axe") else None
                res = page.evaluate("""() => axe.run(document.querySelector('#gate:not([hidden])') || document.querySelector('.screen:not([hidden])') || document,
                  {runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']})""")
                bad = res["violations"]
                found += len(bad)
                where = f"{size['width']}x{size['height']} {label}"
                lines.append(f"axe {where}: {len(bad)} violations" + "".join(
                    f"\n  {v['id']}: {v['help']} ({len(v['nodes'])}: {v['nodes'][0]['target']})" for v in bad))

            check("home")
            page.click("#startBtn", force=True); check("themes")
            page.click('.theme-card[data-theme="animals"]'); check("word card")
            page.click("#cards [data-go=themes]"); page.click("#gamesBtn", force=True); check("game menu")
            for game in ("listen", "match", "memory"):
                page.click(f'.game-card[data-game="{game}"]'); check(f"game {game}")
                page.click("#play [data-go]")
            page.evaluate("() => Games.cardsDone([])"); check("result")
            page.click("#result [data-go=home]")
            page.click("#phrasesBtn", force=True); check("phrase menu")
            for mode in ("cards", "listen", "order"):
                page.click(f'[data-phrase-mode="{mode}"]'); check(f"phrase {mode}")
                page.click("#play [data-go]")
            # Parent corner (phase 6): hold the gear 2 s, answer the sum.
            page.click("#phrases [data-go=home]")
            box = page.locator("#parentDoor").bounding_box()
            page.mouse.move(box["x"] + 20, box["y"] + 20); page.mouse.down(); page.wait_for_timeout(2300); page.mouse.up()
            check("parent gate")
            a, b = map(int, page.inner_text("#gateQ").split(" + "))
            page.fill("#gateAnswer", str(a + b)); page.click("#gateForm [type=submit]"); check("parent page")
            page.click("#addWordBtn"); page.click("#fGalleryBtn"); check("parent add form")
            ctx.close()
        browser.close()
    return found == 0, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/ew-lighthouse", type=pathlib.Path)
    ap.add_argument("--url", help="audit this address (e.g. the GitHub Pages site) instead of a local server")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    server = None
    if not args.url:
        port = free_port()
        server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=ROOT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(0 if args.url else 50):
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), 0.2):
                break
            time.sleep(0.1)
        base = args.url or f"http://127.0.0.1:{port}/"
        lh_ok, lines = lighthouse(base, args.out)
        axe = sorted(glob.glob(os.path.expanduser("~/.npm/_npx/*/node_modules/axe-core/axe.min.js")))
        if not axe:
            sys.exit("axe-core not found next to Lighthouse in ~/.npm/_npx")
        axe_ok, more = axe_screens(base, pathlib.Path(axe[0]).read_text())
    finally:
        if server:
            server.terminate()
    text = "\n".join(lines + more)
    (args.out / "summary.txt").write_text(text + "\n")
    print(text)
    print(f"reports in {args.out}")
    sys.exit(0 if lh_ok and axe_ok else 1)


if __name__ == "__main__":
    main()
