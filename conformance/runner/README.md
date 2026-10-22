# Shared conformance runner

Runs selected Rust and Go implementation tests, deterministic transport faults,
and shared-corpus decode comparisons. Verdicts are **per leg**, not per scenario
or `conformance/manifest` case. A PASS covers only the checks described below.

## Run

From the repository root:

```sh
python3 conformance/runner/runner.py --all
python3 conformance/runner/runner.py --pair go-pure
python3 -S -m unittest discover -s tests -p test_conformance_runner.py -v
```

The runner uses the Python standard library only (including with `python3 -S`).
Rust/Cargo and Go are needed for executable legs; `go-ffi` also needs a working
native C toolchain. Dependencies come from the existing Cargo lockfile and Go
module. The runner builds the production Rust library and configures the native
loader paths for the FFI leg.

`scenarios.yaml` is **JSON-compatible YAML**, parsed with `json.loads`; keep it in
that form. The runner validates its seed, scenario IDs/steps, and complete fault
entries (kind, rate or maximum delay, scope). It prints those entries and saves
them alongside results. The target fault matrix is descriptive: it does not
configure the injectors compiled into the language tests. Actual schedules and
differences are documented in the matrix's `rules`.

By default results go to `conformance/runner/results.json`; use `--json PATH` for
a separate report. Exit status is nonzero on a failed leg or invalid matrix.
Saved reports are execution snapshots, not conformance declarations; an old
checked-in report does not prove the current code passed. The runner is not
currently invoked by `repo-validation.yml` as a four-leg job.

## Legs and exact selection

| ID | Execution |
|---|---|
| `rust-async` | `cargo test --locked -p syntra-runtime --test conformance_runner`, then `--test recovery_drivers` |
| `go-pure` | `go test -run REGEX -count=1 -v .` in `bindings/go` |
| `go-ffi` | `cargo build --locked -p syntra-ffi --features production`, then the Go command with `-tags syntranative` |
| `interop` | Go `TestGoldenVectors` and `TestRunnerWireInteropGolden`, then Rust `sc_wire_vectors_decode -- --nocapture`, with executed decode records compared to the corpus |

`REGEX` is:

```text
^Test(Runner|Reliable|MemoryStore|NoteObserved|DuplicateCache|StagedSnapshot|DirectedDelivery|Checkpoint|Reconciler|LossTotals|WaitLossChange)
```

These prefixes include all tests currently in `recovery_test.go`. The runner
requires named runner/reliable/recovery tests to pass, rejects skipped tests,
and requires nonzero test execution. Zero selected tests cannot produce a PASS.
`rust-go-interop` remains an alias for `interop`.

## Executed checks

- **Echo/concurrency:** empty, `hello` and 64KiB echo payloads; 16 concurrent
  calls with distinct payloads correlated to their callers. Out-of-order
  completion is not deliberately forced.
- **Cancellation (Rust):** handler entry is synchronized before cancellation;
  the caller reports `CANCELLED` and a follow-up echo succeeds. This does not
  check the completion-wins race or count wire terminal frames.
- **Deadlines:** Rust caller deadline reports `DEADLINE_EXCEEDED` with unknown
  outcome. Go checks a stalled send respects its budget and, separately, core
  expiry queues one deadline result and rejects a late answer without another
  outbound result. These checks are not an end-to-end host-expiry race.
- **Oversize handler output:** a 2MiB result becomes `RESOURCE_EXHAUSTED` and a
  follow-up call works, on both languages' legs.
- **Duplicate requests:** Rust feeds duplicate bytes to a host with an original
  handler outstanding. Go sends an actual seeded duplicate request through
  loopback into `Host.Serve`, observes `FAILED_PRECONDITION`, checks one handler
  dispatch, releases the original result, then checks a follow-up call. The
  rejection and original success are two wire results for one request ID; this
  is not an exactly-once wire-result guarantee.
- **Rust response faults:** seeded copies of a real host result feed
  `Initiator::ingest` while a real call is pending. Drops and truncations leave
  the caller pending until the held intact response is redelivered. Duplicate
  copies settle it once, release pending state, and cannot settle another call.
  A dedicated seeded-position test guarantees drop, truncate and duplicate
  branches all run even if the short mixed stream misses a branch. This is
  test-controlled redelivery, not reliable-session reconciliation or proof
  that re-executing a request is safe.
- **Go faults:** seeded notification loss is counted and the delivered count
  checked; real request/result frames can duplicate through the transport.
  Separate seeded-position cases guarantee both RPC duplicate branches execute.
  A real `Client.Run` receives duplicate results; a notification barrier confirms
  their processing, one outcome is consumed, and a late duplicate cannot settle
  a new pending call. Fault transport counters and PRNG access are synchronized;
  duplicate send errors are propagated. No handshake/notification duplication,
  truncation or delay is implemented in the Go injector.
- **Close:** an echo completes before the host is closed. Rust checks zero
  sessions afterward; Go checks repeated Close/Serve-after-Close rejection and
  that the original Serve exits. Neither runner test holds a queued result
  across close or proves in-flight draining/CLOSING transitions.
- **Recovery:** Rust `recovery_drivers` and the selected Go reliable/checkpoint/
  recovery tests assert their own state/store/cache/reconciliation behavior.
  They execute separately from the transport fault tests.

## What interop proves

Both language tests read `GOLD-PROT-HELLO-01` and `GOLD-PROT-REQ-01` from
`conformance/test-vectors/protobuf/vectors.yaml`, decode those bytes, assert
envelope and body fields, and emit records containing the consumed fixture hex
and decoded values. Python compares both executed records to the corpus's full
selected semantic fields (versions, IDs, body, credential, method, payload and
timeout). Missing/duplicate records or differing bytes/fields fail the leg.

The fixture readers intentionally support only the existing selected records'
single-line hex and flat semantic-field syntax; unsupported syntax fails closed.
No Python YAML package is needed and no test source scan supplies execution
evidence. Chosen fixture bytes are compared to consumed bytes; arbitrary encoder
outputs are not required to be byte-identical. This proves shared-fixture decode
agreement, not a live Rust-to-Go exchange or cross-encoder round trip.

## Remaining gaps

The runner does not cover oversize request rejection, unknown/malformed methods,
notification overflow/order semantics, abrupt transport loss/reconnect, the
completion-wins cancellation race, or queued-result graceful drain. Some have
tests elsewhere, but those are not implied by the runner's filters. Delay faults
are unimplemented; Rust truncation runs, Go truncation does not. There are no
runner boundary checks for the 1MiB envelope cap, 30s maximum budget or 5s
handshake deadline. All four legs passing still does not certify the full
`conformance/manifest` matrix or every step of a profile.
