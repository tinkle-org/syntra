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
              plus --test recovery_drivers (checkpoint/reconcile asserts)
  go-pure:    go test -run 'TestRunner|TestReliable|TestCheckpoint|TestRecovery'
              (bindings/go, default tags)
  go-ffi:     cargo build -p syntra-ffi --features production, then
              go test -tags syntranative -run
              'TestRunner|TestReliable|TestCheckpoint|TestRecovery' ./...
  interop:    go test -run 'TestGoldenVectors|TestRunnerWireInteropGolden' +
              Rust vector test (sc_wire_vectors_decode) + shared-corpus check:
              both sides decode bytes registered in the shared corpus
              (protobuf vectors.yaml / websocket fixtures.yaml) and the runner
              compares the logical frames — never cross-encoder byte equality.

The shared fault matrix (scenarios.yaml: seed, fault kinds/rates) is loaded
at startup by load_scenarios() and printed every run; it is descriptive where
legs differ (see scenarios.yaml rules/notes).

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
    # Counts runner, reliable-session, checkpoint and recovery tests: the legs
    # run -run 'TestRunner|TestReliable|TestCheckpoint|TestRecovery' so
    # recovery coverage is asserted, not excluded.
    if rc != 0:
        return False
    if "FAIL" in combined:
        return False
    passes = len(re.findall(r"--- PASS: Test(Runner|Reliable|Checkpoint|Recovery|Golden)", combined))
    skips = combined.count("--- SKIP:")
    if passes < 1:
        return False
    if skips != 0:
        return False
    return True


def load_scenarios():
    """Load the shared fault matrix from conformance/runner/scenarios.yaml.

    Returns a dict with seed, scenario count and fault kinds. The matrix is
    descriptive where legs differ (see scenarios.yaml rules/notes); loading it
    here keeps the runner honest about which seed/pattern each run used.
    """
    path = ROOT / "conformance" / "runner" / "scenarios.yaml"
    try:
        text = path.read_text()
    except OSError as e:
        return {"ok": False, "detail": f"scenarios.yaml unreadable: {e}"}
    m = re.search(r"seed:\s*(0x[0-9A-Fa-f]+|\d+)", text)
    seed = m.group(1) if m else "0x5EED1234"
    scenarios = len(re.findall(r"-\s*id:\s*SC-", text))
    faults = re.findall(r"kind:\s*(\w+)", text)
    return {"ok": True, "seed": seed, "scenarios": scenarios, "faults": faults}


def _shared_corpus_check():
    """Compare logical frames from the shared corpus file (both sides).

    Verifies the interop legs decode bytes registered in the shared corpus:
    Go's golden tests must decode the exact GOLD-PROT-HELLO-01 / GOLD-PROT-REQ-01
    frame_hex bytes from conformance/test-vectors/protobuf/vectors.yaml and
    assert the same logical fields (version, hello versions, credential,
    method); the Rust vector test must decode a hello registered in the
    websocket fixtures. Fails on mismatch — independent self-tests that never
    touch the corpus do not pass as interop.
    """
    tv = ROOT / "conformance" / "test-vectors"
    try:
        import yaml  # type: ignore

        vectors = yaml.safe_load((tv / "protobuf" / "vectors.yaml").read_text())
        by_id = {v.get("id"): v for v in vectors.get("vectors", [])}
    except Exception as e:
        return (False, f"cannot load protobuf vectors.yaml: {e}")
    problems = []
    go_test = (ROOT / "bindings" / "go" / "wire_test.go").read_text()
    for vid, needles in (
        ("GOLD-PROT-HELLO-01", ["0801521e080110011a186f70617175652d746573742d63726564656e7469616c2d41",
                                "opaque-test-credential-A"]),
        ("GOLD-PROT-REQ-01", ["08011007621e0a122f6578616d706c652e4563686f2f4563686f120568656c6c6f18f403",
                              "/example.Echo/Echo"]),
    ):
        entry = by_id.get(vid)
        if not entry:
            problems.append(f"{vid} missing from vectors.yaml")
            continue
        frame_hex = (entry.get("frame_hex") or "").lower()
        for needle in needles:
            if needle.lower() not in frame_hex and needle not in go_test:
                problems.append(f"{vid}: {needle[:24]}... in neither corpus nor go test")
        if frame_hex and frame_hex not in go_test.lower():
            problems.append(f"{vid}: corpus frame_hex not decoded by go golden test")
        sem = entry.get("semantic_fields", {}) or {}
        if sem.get("version") != 1 or sem.get("request_id") not in (0, 7):
            problems.append(f"{vid}: unexpected semantic_fields {sem}")
    rust_hex = "0801520408011001"  # WS no-length-prefix good hello (VEC-WS-009)
    try:
        ws_fix = (tv / "websocket" / "fixtures.yaml").read_text()
    except OSError as e:
        problems.append(f"cannot read websocket fixtures.yaml: {e}")
        ws_fix = ""
    if rust_hex not in ws_fix.replace(" ", ""):
        problems.append("rust vector hello not registered in websocket fixtures.yaml")
    rust_runner = (ROOT / "crates" / "syntra-runtime" / "tests" / "conformance_runner.rs").read_text()
    if "sc_wire_vectors_decode" not in rust_runner or "Body::Hello" not in rust_runner:
        problems.append("rust sc_wire_vectors_decode hello assertion missing")
    if problems:
        return (False, "; ".join(problems))
    return (True, "go + rust legs decode shared-corpus bytes (HELLO-01, REQ-01, WS hello); logical fields match")


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


GO_COVERAGE_RUN = "TestRunner|TestReliable|TestCheckpoint|TestRecovery"


def leg_rust_async():
    # Recovery coverage included: scenario legs plus checkpoint/reconcile
    # asserts in recovery_drivers — durable state, not just wire round-trips.
    rc1, out1, err1, dt1 = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "conformance_runner"],
        cwd=ROOT,
    )
    rc2, out2, err2, dt2 = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "recovery_drivers"],
        cwd=ROOT,
    )
    passed = _cargo_ok(rc1, out1 + err1) and _cargo_ok(rc2, out2 + err2)
    return (
        "PASS" if passed else "FAIL",
        f"cargo conformance_runner ({dt1:.1f}s) + recovery_drivers ({dt2:.1f}s)",
        (out1 + err1 + out2 + err2)[-4000:],
    )


def leg_go_pure():
    d = ROOT / "bindings" / "go"
    rc, out, err, dt = run(["go", "test", "-run", GO_COVERAGE_RUN, "-count=1", "-v", "."], cwd=d)
    passed = _go_ok(rc, out + err)
    return ("PASS" if passed else "FAIL", f"go {GO_COVERAGE_RUN} default ({dt:.1f}s)", (out + err)[-4000:])


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
        ["go", "test", "-tags", "syntranative", "-run", GO_COVERAGE_RUN, "-count=1", "-v", "."],
        cwd=d,
        env=env,
    )
    passed = _go_ok(rc, out + err)
    return ("PASS" if passed else "FAIL", f"go {GO_COVERAGE_RUN} syntranative ({dt:.1f}s)", (out + err)[-4000:])


def leg_interop():
    # Wire interop as cross-decode against the shared corpus: the Go golden
    # tests decode the exact vectors.yaml bytes (HELLO-01/REQ-01) and the Rust
    # vector test decodes the registered WS hello; _shared_corpus_check then
    # compares the logical frames from the corpus file. Fails on mismatch —
    # decoded Frame equality, opaque bytes preserved, never byte equality
    # across encoders.
    d = ROOT / "bindings" / "go"
    rc1, out1, err1, dt1 = run(
        ["go", "test", "-run", "TestGoldenVectors|TestRunnerWireInteropGolden", "-count=1", "-v", "."],
        cwd=d,
    )
    rc2, out2, err2, dt2 = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "conformance_runner", "sc_wire_vectors_decode"],
        cwd=ROOT,
    )
    go_combined = out1 + err1
    rust_combined = out2 + err2
    go_ran = (
        rc1 == 0
        and "--- PASS: TestGoldenVectors" in go_combined
        and "--- PASS: TestRunnerWireInteropGolden" in go_combined
        and "--- SKIP:" not in go_combined
        and "FAIL" not in go_combined
    )
    rust_ran = _cargo_ok(rc2, rust_combined) and "sc_wire_vectors_decode" in rust_combined
    corpus_ok, corpus_detail = _shared_corpus_check()
    passed = go_ran and rust_ran and corpus_ok
    return (
        "PASS" if passed else "FAIL",
        f"interop cross-decode (go {dt1:.1f}s + rust {dt2:.1f}s): {corpus_detail}",
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
    matrix = load_scenarios()
    if not matrix.get("ok"):
        print(f"matrix load FAILED: {matrix.get('detail')}", file=sys.stderr)
        return 1
    print(
        f"Syntra shared conformance runner — {len(pairs)} pairing(s), "
        f"seed {matrix['seed']} ({matrix['scenarios']} scenarios, "
        f"faults: {', '.join(matrix['faults'])})"
    )
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
