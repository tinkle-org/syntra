# Shared conformance runner

Executable runner driving four peer pairings with deterministic fault
injection, asserting wire payloads, durable state, bounds and terminal
outcomes — not just manifest validation (`scripts/validate-repo.py` checks
YAML; this runs the protocol).

## Pairings

| ID | Backend | Command |
|---|---|---|
| `rust-async` | async Rust tokio (`syntra-runtime::loopback_pair`) | `cargo test --locked -p syntra-runtime --test conformance_runner` |
| `go-pure` | pure-Go core (default build) | `go test -run TestRunner ./...` in `bindings/go` |
| `go-ffi` | Go+FFI native core (production Rust) | build `syntra-ffi --features production`, then `go test -tags syntranative -run TestRunner ./...` |
| `interop` | Rust↔Go wire interop | Go `TestRunnerWireInteropGolden` + Rust `sc_wire_vectors_decode` on the same logical frames |

## Scenarios

Runner scenarios live in `scenarios.yaml` (seed `0x5EED1234`, loaded at
startup by `runner.py:load_scenarios`). Currently verified by the
executable legs: echo, 16-concurrent, deadline-exactly-once,
oversize-handler-result, graceful-close drain, fault-injection
(drop/duplicate), wire interop cross-decode against the shared corpus,
plus reliable-session/checkpoint/recovery unit coverage (`TestReliable` /
`TestCheckpoint` / `TestRecovery` on the Go legs, `recovery_drivers` on
the Rust leg). Cancel-wins and duplicate-id are verified in the
`rust-async` leg only.

Defined in `scenarios.yaml` but not yet covered by all legs (do not claim):
oversize-payload, unknown/malformed method, notifications, abrupt transport
loss (only graceful close is exercised), truncate/delay faults.

Each scenario asserts:
- wire payloads (decoded `Frame` equality, opaque bytes bit-identical),
- durable state (recovery checkpoints only on validated complete batches),
- bounds actually tested here (16 concurrent, bounded oversize handler
  results with `RESOURCE_EXHAUSTED`),
- terminal outcomes (exactly one result per `request_id`, correct codes).

Not asserted by this runner (do not claim): 1 MiB envelope cap, 30 s max
budget, 5 s handshake deadline — no boundary test exercises them here.

## Run

```sh
python3 conformance/runner/runner.py --all
python3 conformance/runner/runner.py --pair go-pure
```

Results go to `conformance/runner/results.json` for declarations (CI-regenerated;
do not treat checked-in timings as normative).
Exit nonzero on any FAIL. All four legs must PASS for a runner claim. Runner
PASS covers only the scenarios above, not the full `conformance/manifest`
(CONF-*) matrix.
