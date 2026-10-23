#!/usr/bin/env python3
"""Render the background music (js/music.js) in headless Chrome to a file and
measure it, so it can be heard and checked without an iPad.

Usage: python3 tools/render-bgm.py OUT.mp3 [--seconds 30] [--lufs -18]
       python3 tools/render-bgm.py --measure     print the loop's loudness in the game
--lufs sets the preview's loudness for listening (the game plays it at about
-32 LUFS, see js/music.js LEVEL). Needs ffmpeg and Chrome (/usr/bin/google-chrome).
"""
import argparse, base64, json, pathlib, re, subprocess, sys, tempfile, wave

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
RENDER = """async (duck) => {
  const buf = await Music.render(22050);
  const x = buf.getChannelData(0), gain = duck ? Music.LEVEL * Music.DUCK : Music.LEVEL;
  const out = new Int16Array(x.length);
  let peak = 0;
  for (let i = 0; i < x.length; i++) { const v = x[i] * gain; peak = Math.max(peak, Math.abs(v)); out[i] = Math.max(-32768, Math.min(32767, Math.round(v * 32767))); }
  let s = ''; const b = new Uint8Array(out.buffer);
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return {rate: buf.sampleRate, peak, pcm: btoa(s)};
}"""


def render(duck=False, chrome="/usr/bin/google-chrome"):
    """(rate, pcm16 bytes, peak) of one loop at the game's level."""
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome)
        page = browser.new_page()
        page.set_content("<!doctype html><title>bgm</title>")
        page.add_script_tag(content=(ROOT / "js/music.js").read_text())
        res = page.evaluate(RENDER, duck)
        browser.close()
    return res["rate"], base64.b64decode(res["pcm"]), res["peak"]


def write_wav(path, rate, pcm, repeat=1):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(pcm * repeat)


def loudness(path):
    """(integrated LUFS, true peak dBTP) by ffmpeg ebur128."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = out[out.rindex("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary)[1]), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", type=pathlib.Path)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--lufs", type=float, default=-18)
    ap.add_argument("--measure", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        if args.measure:
            res = {}
            for duck in (False, True):
                rate, pcm, peak = render(duck)
                wav = pathlib.Path(tmp) / f"loop{int(duck)}.wav"
                write_wav(wav, rate, pcm, repeat=2)   # twice: the seam is measured too
                res["ducked" if duck else "normal"] = loudness(wav)
            print(json.dumps(res))
            return
        if not args.out:
            sys.exit("give an output file, or --measure")
        rate, pcm, _ = render()
        wav = pathlib.Path(tmp) / "loop.wav"
        write_wav(wav, rate, pcm, repeat=2)
        lufs, _ = loudness(wav)
        gain = args.lufs - lufs
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-t", str(args.seconds),
                        "-af", f"volume={gain:.2f}dB,afade=t=out:st={args.seconds - 2}:d=2", "-ac", "1", "-ar", "24000",
                        "-b:a", "64k", str(args.out)], check=True)
        print(f"{args.out}: {args.seconds:g} s, game level {lufs:.1f} LUFS, preview {args.lufs:g} LUFS ({gain:+.1f} dB)")


if __name__ == "__main__":
    main()
