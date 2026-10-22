#!/usr/bin/env python3
"""Shared conformance runner (executable, not just manifest validation).

Drives four peer pairings with deterministic fault injection, asserting wire
payloads, durable state, bounds and terminal outcomes:
  1. rust-async  — async Rust tokio runtime (syntra-runtime loopback)
  2. go-pure     — pure-Go core (default build)
  3. go-ffi      — Go+FFI native core (production Rust via syntranative)
  4. interop — Rust<->Go wire interop (golden vectors + cross-decode, alias rust-go-interop)

Usage:
  python3 conformance/runner/runner.py [--pair rust-async|go-pure|go-ffi|interop|rust-go-interop|all]
  python3 conformance/runner/runner.py --all  # CI entrypoint, exits nonzero on FAIL

Each leg runs the executable harness (not the YAML validator):
  rust-async: cargo test --locked -p syntra-runtime --test conformance_runner
  go-pure:    go test -run TestRunner ./... (bindings/go, default tags)
  go-ffi:     cargo build -p syntra-ffi --features production, then
              go test -tags syntranative -run TestRunner ./...
  interop:    go test -run TestRunnerWireInteropGolden + Rust vector test
              (sc_wire_vectors_decode) — same logical frames both sides.

Verdicts per scenario: PASS/FAIL/SKIP with logs. Results also written to
conformance/runner/results.json for declarations.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "conformance" / "runner" / "results.json"

PAIRINGS = ["rust-async", "go-pure", "go-ffi", "interop"]


def _cargo_ok(rc, combined):
    # Require exit 0, "test result: ok", at least 1 passed, 0 failed,
    # and no skipped (ignored) required tests — not just exit code.
    if rc != 0:
        return False
    if "test result: ok" not in combined:
        return False
    m_pass = re.search(r"(\d+) passed", combined)
    if not m_pass or int(m_pass.group(1)) < 1:
        return False
    m_fail = re.search(r"(\d+) failed", combined)
    if m_fail and int(m_fail.group(1)) != 0:
        return False
    m_ign = re.search(r"(\d+) ignored", combined)
    if m_ign and int(m_ign.group(1)) != 0:
        return False
    return True


def _go_ok(rc, combined):
    # Require exit 0, no FAIL, at least one passing required test,
    # and no skipped required tests — not just exit code/absence of FAIL.
    # Caller must run go test with -v so --- PASS:/--- SKIP: lines exist.
    if rc != 0:
        return False
    if "FAIL" in combined:
        return False
    passes = combined.count("--- PASS: TestRunner")
    skips = combined.count("--- SKIP:")
    if passes < 1:
        return False
    if skips != 0:
        return False
    return True


def run(cmd, cwd, env=None, timeout=300):
    start = time.time()
    try:
        p = subprocess.run(
            cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout
        )
        # Retain complete output so pass/skip verdicts see every
        # "--- PASS:"/"--- SKIP:" line regardless of position;
        # callers truncate only the displayed log.
        return p.returncode, p.stdout, p.stderr, time.time() - start
    except subprocess.TimeoutExpired as e:
        if isinstance(e.stdout, bytes):
            out = (e.stdout or b"").decode(errors="replace")
        else:
            out = str(e.stdout or "")
        if isinstance(e.stderr, bytes):
            err = (e.stderr or b"").decode(errors="replace")
        else:
            err = str(e.stderr or "")
        return 124, out, err, time.time() - start


def leg_rust_async():
    rc, out, err, dt = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "conformance_runner"],
        cwd=ROOT,
    )
    passed = _cargo_ok(rc, out + err)
    return ("PASS" if passed else "FAIL", f"cargo conformance_runner ({dt:.1f}s)", (out + err)[-4000:])


def leg_go_pure():
    d = ROOT / "bindings" / "go"
    rc, out, err, dt = run(["go", "test", "-run", "TestRunner", "-count=1", "-v", "."], cwd=d)
    passed = _go_ok(rc, out + err)
    return ("PASS" if passed else "FAIL", f"go TestRunner default ({dt:.1f}s)", (out + err)[-4000:])


def leg_go_ffi():
    rc1, out1, err1, dt1 = run(
        ["cargo", "build", "--locked", "-p", "syntra-ffi", "--features", "production"],
        cwd=ROOT,
    )
    if rc1 != 0:
        return ("FAIL", "ffi build", (out1 + err1)[-4000:])
    import os

    libdir = str(ROOT / "target" / "debug")
    env = dict(os.environ)
    env["CGO_LDFLAGS"] = f"-L{libdir} -lsyntra_ffi"
    env["LD_LIBRARY_PATH"] = libdir + ":" + env.get("LD_LIBRARY_PATH", "")
    env["DYLD_LIBRARY_PATH"] = libdir + ":" + env.get("DYLD_LIBRARY_PATH", "")
    d = ROOT / "bindings" / "go"
    rc, out, err, dt = run(
        ["go", "test", "-tags", "syntranative", "-run", "TestRunner", "-count=1", "-v", "."],
        cwd=d,
        env=env,
    )
    passed = _go_ok(rc, out + err)
    return ("PASS" if passed else "FAIL", f"go TestRunner syntranative ({dt:.1f}s)", (out + err)[-4000:])


def leg_interop():
    # Wire interop: Go golden test + Rust vector test must both pass on the
    # same logical frames (decoded equality, opaque bytes preserved).
    d = ROOT / "bindings" / "go"
    rc1, out1, err1, dt1 = run(
        ["go", "test", "-run", "TestRunnerWireInteropGolden", "-count=1", "-v", "."],
        cwd=d,
    )
    rc2, out2, err2, dt2 = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "conformance_runner", "sc_wire_vectors_decode"],
        cwd=ROOT,
    )
    go_combined = out1 + err1
    rust_combined = out2 + err2
    go_ran = rc1 == 0 and "--- PASS: TestRunnerWireInteropGolden" in go_combined and "--- SKIP:" not in go_combined and "FAIL" not in go_combined
    rust_ran = _cargo_ok(rc2, rust_combined) and "sc_wire_vectors_decode" in rust_combined
    passed = go_ran and rust_ran
    return (
        "PASS" if passed else "FAIL",
        f"interop wire vectors (go {dt1:.1f}s + rust {dt2:.1f}s)",
        (out1 + err1 + out2 + err2)[-4000:],
    )


LEGS = {
    "rust-async": leg_rust_async,
    "go-pure": leg_go_pure,
    "go-ffi": leg_go_ffi,
    "interop": leg_interop,
}


def main():
    ap = argparse.ArgumentParser(description="Shared Syntra conformance runner")
    ap.add_argument("--pair", choices=PAIRINGS + ["all", "rust-go-interop"], default="all")
    ap.add_argument("--all", action="store_true", help="run every pairing (same as --pair all)")
    ap.add_argument("--json", default=str(RESULTS))
    args = ap.parse_args()
    if args.all or args.pair == "all":
        pairs = PAIRINGS
    elif args.pair == "rust-go-interop":
        pairs = ["interop"]
    else:
        pairs = [args.pair]
    results = []
    overall = True
    print(f"Syntra shared conformance runner — {len(pairs)} pairing(s), seed 0x5EED1234")
    for pid in pairs:
        verdict, detail, log = LEGS[pid]()
        ok = verdict == "PASS"
        overall &= ok
        print(f"[{verdict}] {pid}: {detail}")
        if verdict != "PASS":
            print(f"--- log {pid} ---\n{log}\n--- end log {pid} ---", file=sys.stderr)
        results.append({"pairing": pid, "verdict": verdict, "detail": detail})
    Path(args.json).write_text(json.dumps({"runner": "syntra-conformance-runner v1", "results": results}, indent=2))
    print(f"results -> {args.json}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
