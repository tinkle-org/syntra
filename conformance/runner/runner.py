#!/usr/bin/env python3
"""Run implementation test legs and compare executed shared-corpus decodes.

Uses only the Python standard library. scenarios.yaml is JSON-compatible YAML;
its full descriptive fault matrix is validated, printed and saved, not used to
configure the hard-coded Rust/Go fault injectors. See README.md for coverage.
Verdicts are per leg, not per manifest case or scenario.
"""
import argparse
import base64
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
    passed = set(re.findall(r"--- PASS: (Test\w+)\s", combined))
    return (rc == 0 and "FAIL" not in combined and "--- SKIP:" not in combined
            and GO_REQUIRED_TESTS <= passed)


def load_scenarios():
    """Validate JSON-compatible YAML, failing closed on incomplete entries."""
    path = ROOT / "conformance" / "runner" / "scenarios.yaml"
    try:
        data = json.loads(path.read_text())
        if data["format_version"] != "1.0" or data["runner"] != "syntra-conformance-runner v1":
            raise ValueError("unsupported matrix format/runner")
        if [p["id"] for p in data["pairings"]] != PAIRINGS:
            raise ValueError("unexpected pairings")
        scenarios = data["scenarios"]
        ids = [s["id"] for s in scenarios]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("missing/duplicate scenario IDs")
        for scenario in scenarios:
            if (not re.fullmatch(r"SC-[A-Z0-9-]+", scenario["id"])
                    or not isinstance(scenario["name"], str) or not scenario["name"]):
                raise ValueError("invalid scenario")
            steps = scenario["steps"]
            if (not isinstance(steps, list) or not steps
                    or not all(isinstance(s, str) and s for s in steps)):
                raise ValueError("missing scenario steps")
        injection = data["fault_injection"]
        seed = injection["seed"]
        if not isinstance(seed, str) or not re.fullmatch(r"0x[0-9A-Fa-f]+|[0-9]+", seed):
            raise ValueError("missing/invalid seed")
        if not 0 < int(seed, 16 if seed.startswith("0x") else 10) < 2**64:
            raise ValueError("seed outside nonzero u64 range")
        faults = injection["faults"]
        if not isinstance(faults, list) or not faults:
            raise ValueError("missing faults")
        for fault in faults:
            kind = fault["kind"]
            if kind not in {"drop", "duplicate", "truncate", "delay"}:
                raise ValueError(f"unknown fault kind: {kind}")
            if fault["scope"] not in {"notifications", "results", "inbound-bytes", "send"}:
                raise ValueError("missing/unknown fault scope")
            keys = {"kind", "scope", "max_ms" if kind == "delay" else "rate"}
            if set(fault) != keys:
                raise ValueError("unexpected/missing fault fields")
            if kind == "delay":
                if type(fault["max_ms"]) is not int or fault["max_ms"] < 0:
                    raise ValueError("invalid max_ms")
            else:
                rate = re.fullmatch(r"([0-9]+)/([0-9]+)", fault["rate"])
                if not rate or not 0 < int(rate[1]) <= int(rate[2]):
                    raise ValueError("invalid fault rate")
        return {"ok": True, "seed": seed, "scenarios": len(ids), "faults": faults}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return {"ok": False, "detail": f"invalid scenarios.yaml: {e}"}


def _corpus_expected():
    """Read only the two selected flat fixture records, not general YAML.

    Unsupported/multiline syntax fails closed. This avoids a hidden PyYAML
    prerequisite while leaving the shared corpus format and files untouched.
    """
    text = (ROOT / "conformance/test-vectors/protobuf/vectors.yaml").read_text()
    expected = {}
    for vid in ("GOLD-PROT-HELLO-01", "GOLD-PROT-REQ-01"):
        blocks = re.findall(r"^  - id: " + vid + r"\n(.*?)(?=^  - id:|^verification:|\Z)", text, re.M | re.S)
        if len(blocks) != 1:
            raise ValueError(f"{vid}: missing/duplicate fixture")
        block = blocks[0]
        frame_hex = re.findall(r'^    frame_hex: "([0-9a-fA-F]+)"$', block, re.M)
        fields = re.findall(r"^    semantic_fields: \{ (.+) \}$", block, re.M)
        if len(frame_hex) != 1 or len(fields) != 1:
            raise ValueError(f"{vid}: expected single-line hex and flat semantic_fields")
        bytes.fromhex(frame_hex[0])
        sem = {}
        remaining = fields[0]
        while remaining:
            match = re.match(r'(\w+): ("(?:[^"\\]|\\.)*"|[\w.-]+)(?:, |$)', remaining)
            if not match or match[1] in sem:
                raise ValueError(f"{vid}: unsupported/duplicate semantic field")
            value = match[2]
            sem[match[1]] = json.loads(value) if value.startswith('"') or value.isdigit() else value
            remaining = remaining[match.end():]
        for key in ("credential_b64", "payload_b64"):
            if key in sem:
                sem[key[:-4]] = base64.b64decode(sem.pop(key), validate=True).decode("ascii")
        expected[vid] = {"id": vid, "frame_hex": frame_hex[0], "semantic_fields": sem}
    return expected


def _shared_corpus_check(go_output, rust_output):
    """Compare actual test-emitted bytes and decoded fields to the corpus."""
    try:
        expected = _corpus_expected()
        for language, output in (("go", go_output), ("rust", rust_output)):
            records = [json.loads(s) for s in re.findall(r"CORPUS (\{[^\n]+\})", output)]
            if len(records) != len(expected) or {r["id"] for r in records} != set(expected):
                raise ValueError(f"{language}: missing/duplicate executed corpus records")
            for record in records:
                exp = expected[record["id"]]
                rec_hex = record.get("frame_hex")
                exp_hex = exp.get("frame_hex")
                if not isinstance(rec_hex, str) or not isinstance(exp_hex, str):
                    raise ValueError(f"{language}: corpus bytes/decoded fields differ for {record.get('id')}")
                rec_norm = dict(record)
                exp_norm = dict(exp)
                rec_norm["frame_hex"] = rec_hex.lower()
                exp_norm["frame_hex"] = exp_hex.lower()
                if rec_norm != exp_norm:
                    raise ValueError(f"{language}: corpus bytes/decoded fields differ for {record['id']}")
    except (OSError, ValueError, KeyError, TypeError) as e:
        return False, str(e)
    return True, "Rust and Go executed HELLO-01/REQ-01 decodes; bytes and all corpus fields match"


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


GO_COVERAGE_RUN = (
    "^Test(Runner|Reliable|MemoryStore|NoteObserved|DuplicateCache|StagedSnapshot|"
    "DirectedDelivery|Checkpoint|Reconciler|LossTotals|WaitLossChange)"
)
GO_REQUIRED_TESTS = {
    "TestRunnerEcho", "TestRunnerEchoWithFaultInjection", "TestRunnerDuplicateResultDeduped",
    "TestRunnerDuplicateRequestThroughTransport", "TestRunnerDuplicateResultThroughTransport",
    "TestReliableReconciliation", "TestMemoryStoreAtomicFailure", "TestMemoryStoreDeepCopy",
    "TestNoteObservedDeepCopy", "TestDuplicateCacheBounded", "TestStagedSnapshotFailure",
    "TestDirectedDeliveryIsolation", "TestCheckpointReconciliationIdlePeers",
    "TestReconcilerBoundedTick", "TestLossTotalsCumulativeNoDoubleCount",
    "TestWaitLossChangeBroadcastsToAllWaiters",
}


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
    # Both tests emit evidence from actual decodes of the same corpus bytes.
    d = ROOT / "bindings" / "go"
    rc1, out1, err1, dt1 = run(
        ["go", "test", "-run", "TestGoldenVectors|TestRunnerWireInteropGolden", "-count=1", "-v", "."],
        cwd=d,
    )
    rc2, out2, err2, dt2 = run(
        ["cargo", "test", "--locked", "-p", "syntra-runtime", "--test", "conformance_runner", "sc_wire_vectors_decode", "--", "--nocapture"],
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
    corpus_ok, corpus_detail = _shared_corpus_check(go_combined, rust_combined)
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
        f"descriptive faults: {json.dumps(matrix['faults'], sort_keys=True)})"
    )
    for pid in pairs:
        verdict, detail, log = LEGS[pid]()
        ok = verdict == "PASS"
        overall &= ok
        print(f"[{verdict}] {pid}: {detail}")
        if verdict != "PASS":
            print(f"--- log {pid} ---\n{log}\n--- end log {pid} ---", file=sys.stderr)
        results.append({"pairing": pid, "verdict": verdict, "detail": detail})
    Path(args.json).write_text(json.dumps({"runner": "syntra-conformance-runner v1", "matrix": matrix, "results": results}, indent=2) + "\n")
    print(f"results -> {args.json}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
