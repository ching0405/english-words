#!/usr/bin/env python3
"""Run every check in one go and print one table (phase 7).

Order: Node unit tests, data validators and their error cases, the offline
list (build-sw --check, includes the size cap), Chinese loudness
(normalize-audio --check), selftest.
Every step runs even after a failure, so one run shows everything that broke.
Screenshots go to /tmp as usual; nothing is written into the repo unless --qa.

Usage: python3 tools/check-all.py               everything (selftest takes about an hour)
       python3 tools/check-all.py --quick       no browser: unit tests, validators, build-sw (about a minute)
       python3 tools/check-all.py --twice       selftest twice in a row
       python3 tools/check-all.py --qa          selftest screenshots into qa/
       python3 tools/check-all.py --lighthouse  also tools/lighthouse.py (needs network once)
Exit 1 when any step fails.
"""
import argparse, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
NODE_TESTS = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tools").glob("test_*.cjs"))


def counts(out):
    """'N passed / M failed' from whichever summary the tool prints, or ''."""
    m = re.findall(r"(\d+) passed, (\d+) failed", out)
    if m:
        return f"{m[-1][0]} passed / {m[-1][1]} failed"
    p, f = re.search(r"^# pass (\d+)", out, re.M), re.search(r"^# fail (\d+)", out, re.M)
    if p and f:
        return f"{p[1]} passed / {f[1]} failed"
    m = re.search(r"^Ran (\d+) tests?", out, re.M)
    if m:
        return f"{m[1]} tests " + ("OK" if re.search(r"^OK", out, re.M) else "FAILED")
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return lines[-1][:90] if lines else ""


def run(name, argv):
    print(f"\n=== {name}: {' '.join(argv)}", flush=True)
    start = time.time()
    proc = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        out.append(line)
    code = proc.wait()
    return name, code, time.time() - start, counts("".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the browser tests (selftest)")
    ap.add_argument("--twice", action="store_true", help="run selftest twice in a row")
    ap.add_argument("--qa", action="store_true", help="pass --qa to selftest")
    ap.add_argument("--lighthouse", action="store_true", help="also run tools/lighthouse.py")
    args = ap.parse_args()
    qa = ["--qa"] if args.qa else []
    steps = [
        ("node unit tests", ["node", "--test", *NODE_TESTS]),
        ("validate-words", [PY, "tools/validate-words.py"]),
        ("test_validate_words", [PY, "tools/test_validate_words.py"]),
        ("validate-phrases", [PY, "tools/validate-phrases.py"]),
        ("test_validate_phrases", [PY, "tools/test_validate_phrases.py"]),
        ("build-sw --check", [PY, "tools/build-sw.py", "--check"]),
        ("normalize-audio --check", [PY, "tools/normalize-audio.py", "--check"]),
    ]
    if not args.quick:
        for i in range(2 if args.twice else 1):
            steps.append((f"selftest{' run ' + str(i + 1) if args.twice else ''}", [PY, "tools/selftest.py", *qa]))
        if args.lighthouse:
            steps.append(("lighthouse", [PY, "tools/lighthouse.py"]))
    results = [run(name, argv) for name, argv in steps]
    width = max(len(r[0]) for r in results)
    print("\n" + "=" * 72)
    for name, code, secs, summary in results:
        print(f"{'PASS' if code == 0 else 'FAIL'}  {name:<{width}}  {secs:7.1f}s  {summary}")
    failed = [r[0] for r in results if r[1] != 0]
    print("=" * 72)
    print(f"FAILED: {', '.join(failed)}" if failed else f"ALL {len(results)} STEPS PASSED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
