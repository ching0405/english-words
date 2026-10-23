#!/usr/bin/env python3
"""Make every Chinese voice line equally loud (phase 8), from the originals.

The recordings straight from edge-tts are kept unchanged in audio-src/zh/
(not downloaded by the iPad). This makes audio/zh/<key>.mp3 from them:
gain to TARGET LUFS (integrated, EBU R128), a limiter only when the gain
would push the true peak over PEAK_MAX, then 24 kHz / 48 kbps / mono mp3
like before. It always starts from the original, never from a file it made,
so re-running (or a new --target) never stacks losses. audio/zh/manifest.json
records for each line: src (sha256 of the original), gain_db, lufs, tp, target.

Usage: python3 tools/normalize-audio.py              only new or changed lines
       python3 tools/normalize-audio.py --force      every line again
       python3 tools/normalize-audio.py --target -14 every line to another level
       python3 tools/normalize-audio.py --check      measure only; exit 1 when off
       python3 tools/normalize-audio.py --table FILE also write a loudness table
Needs ffmpeg.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "audio-src" / "zh"
OUT = ROOT / "audio" / "zh"
MANIFEST = OUT / "manifest.json"
TARGET = -16.0      # LUFS: common for speech on phones and tablets (Apple, AES TD1004)
PEAK_MAX = -1.5     # dBTP after encoding
LIMIT = -2.5        # dBTP the limiter aims for; mp3 encoding can add up to ~1 dB
TOLERANCE = 1.0     # LU allowed around the target by --check


def measure(path):
    """(integrated LUFS, true peak dBTP, seconds) by ffmpeg ebur128."""
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True)
    out = res.stderr
    if res.returncode or "Summary:" not in out:
        raise RuntimeError(f"ffmpeg could not read {path}: {out.strip()[-200:]}")
    summary = out[out.rindex("Summary:"):]
    # Length from the decoded samples (gapless): ffprobe's header estimate counts encoder padding.
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "24000", "-"],
                         capture_output=True).stdout
    return (float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary)[1]),
            float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)[1]),
            len(pcm) / 2 / 24000)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def encode(src, dst, gain, limit):
    """src -> dst with gain (dB); a limiter at LIMIT dBTP when asked."""
    chain = f"volume={gain:.2f}dB"
    if limit:
        # 4x oversampled so the limiter catches peaks between samples (true peak).
        chain += f",aresample=96000,alimiter=limit={10 ** (LIMIT / 20):.4f}:level=disabled:attack=2:release=40,aresample=24000"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", chain,
                    "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k", "-id3v2_version", "0", str(dst)], check=True)


def normalize(key, target):
    """Make audio/zh/<key>.mp3 from the original; returns the manifest fields."""
    src = SRC / f"{key}.mp3"
    lufs, tp, _ = measure(src)
    gain = target - lufs
    limit = tp + gain > LIMIT
    dst = OUT / f"{key}.mp3"
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "out.mp3"
        encode(src, out, gain, limit)
        got, peak, _ = measure(out)
        if abs(got - target) > 0.3:  # the limiter took some loudness: once more, a little louder
            gain += target - got
            encode(src, out, gain, limit)
            got, peak, _ = measure(out)
        dst.write_bytes(out.read_bytes())
    return {"src": sha(src), "gain_db": round(gain, 2), "limited": limit, "lufs": got, "tp": peak, "target": target}


def check(manifest, keys, target):
    """Problems with audio/zh/ (measured now, not taken from the manifest)."""
    bad = []
    for key in keys:
        src, out, rec = SRC / f"{key}.mp3", OUT / f"{key}.mp3", manifest.get(key, {})
        if not src.is_file():
            bad.append(f"{key}: original audio-src/zh/{key}.mp3 missing")
            continue
        if not out.is_file():
            bad.append(f"{key}: audio/zh/{key}.mp3 missing")
            continue
        if rec.get("src") != sha(src):
            bad.append(f"{key}: the original changed since it was normalized; run tools/normalize-audio.py")
        if rec.get("target") != target:
            bad.append(f"{key}: made for {rec.get('target')} LUFS, not {target}; run tools/normalize-audio.py")
        lufs, tp, _ = measure(out)
        if abs(lufs - target) > TOLERANCE:
            bad.append(f"{key}: {lufs:.1f} LUFS (target {target:g} ±{TOLERANCE:g})")
        if tp > PEAK_MAX:
            bad.append(f"{key}: true peak {tp:.1f} dBTP (max {PEAK_MAX:g})")
    return bad


def table(manifest, keys, path):
    rows = ["key\toriginal LUFS\toriginal dBTP\toriginal s\tgain dB\tlimited\tLUFS\tdBTP\ts"]
    for key in keys:
        a, b = measure(SRC / f"{key}.mp3"), measure(OUT / f"{key}.mp3")
        rec = manifest.get(key, {})
        rows.append(f"{key}\t{a[0]:.1f}\t{a[1]:.1f}\t{a[2]:.3f}\t{rec.get('gain_db', 0):+.2f}\t{'yes' if rec.get('limited') else 'no'}\t{b[0]:.1f}\t{b[1]:.1f}\t{b[2]:.3f}")
    pathlib.Path(path).write_text("\n".join(rows) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--target", type=float)
    ap.add_argument("--table")
    ap.add_argument("keys", nargs="*", help="only these lines (default: every original in audio-src/zh/)")
    args = ap.parse_args(argv)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    keys = args.keys or sorted(p.stem for p in SRC.glob("*.mp3"))
    # Default target: what the files were made for (so --check and re-runs agree), else TARGET.
    targets = {r.get("target") for r in manifest.values() if r.get("target") is not None}
    target = args.target if args.target is not None else (targets.pop() if len(targets) == 1 else TARGET)
    if args.check:
        bad = check(manifest, sorted(manifest) if not args.keys else keys, target)
        if args.table:
            table(manifest, sorted(manifest), args.table)
        print("\n".join(bad) if bad else f"OK: {len(manifest)} Chinese lines at {target:g} ±{TOLERANCE:g} LUFS, true peak <= {PEAK_MAX:g} dBTP, made from audio-src/zh/")
        return 1 if bad else 0
    made = 0
    for key in keys:
        rec = manifest.get(key)
        if rec is None:
            print(f"skip {key}: not in audio/zh/manifest.json (run tools/gen-voice.py)")
            continue
        src = SRC / f"{key}.mp3"
        if not args.force and rec.get("src") == sha(src) and rec.get("target") == target and (OUT / f"{key}.mp3").is_file():
            continue
        rec.update(normalize(key, target))
        made += 1
        print(f"{key}: {rec['gain_db']:+.2f} dB{' (limited)' if rec['limited'] else ''} -> {rec['lufs']:.1f} LUFS, {rec['tp']:.1f} dBTP")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.table:
        table(manifest, sorted(manifest), args.table)
    print(f"OK: {made} normalized, {len(keys) - made} unchanged; target {target:g} LUFS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
