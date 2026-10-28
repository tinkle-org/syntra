# Batching / compression / idle-lease tradeoffs — evaluation 7 (no premature optimization)

Historical evaluation: 2026-10-22. Decision at that time: **no changes** —
keep one-Frame-per-Send, compression default-off, idle lease supported
(capability-gated `syntra.reliable-session/1`) but not enabled by default.
Sections 1–4 preserve that evaluation and its decisions; their measurements
are historical observations, not current reproduction results for this checkout.
Sections 5–6 add experimental SC1 accounting and current measurement evidence.
Revisit the historical optimization decisions only with production profiles and
an RFC; do not optimize the reference path prematurely.

## 1. Batching (envelope vs transport)

Normative: `SNTR-WIRE-001` — one `Frame` per Protobuf message; batching
multiple `Frame`s inside one message is forbidden. Transport batching
(multiple length-prefixed frames in one TCP segment) is framing, allowed.

Historical measurements (loopback, 2026-10-22):
- `cargo test -p syntra-runtime --test conformance_runner`: 9 scenarios in ~0.11 s.
- `go test -run TestRunner`: 8 scenarios in ~0.20 s.
- 16-concurrent echo (`SC-CONCURRENT-16`): all correlate by id, out-of-order legal, no head-of-line blocking.
- Envelope overhead for `/example.Echo/Echo`: ~32 B (version + request_id + method + timeout tags).
  - 0 B payload → ~32 B wire; 64 KiB payload → ~65,568 B wire.
  - 16×64 KiB as 16 separate frames: ~1,049,600 B total; as one batched Protobuf: same bytes but **undecodable as one Frame** (violates exactly-one-body, breaks correlation).

Tradeoff: envelope batching would save ~16 syscalls per batch but destroys
per-RPC correlation, deadline, cancel and terminal-outcome semantics (one
`result` per `request_id` becomes ambiguous). Transport batching already
coalesces small frames in the OS without any protocol change (Nagle/TSO/GRO).

Decision: keep one-Frame-per-`Transport.Send`. Adapters MAY coalesce at the
transport layer (TCP segments, WS message flushes). No envelope batching.

## 2. Compression (permessage-deflate / HTTP content-encoding)

Normative: `SNTR-WS-090…092`, `SNTR-HTTP-120/121`, `SNTR-WSS-090` — default
off; opt-in only with documented settings and decompressed-size bound
(= max envelope) enforced during inflation; exceedance → WS/WSS close 1009
or HTTP 413, both with local `RESOURCE_EXHAUSTED` per
`SNTR-WS-092`/`SNTR-HTTP-121`.

Measurements / analysis:
- Opaque payloads are often ciphertext or already-compressed bytes
  (application decision): incompressible inputs gain ~0% while paying CPU.
- Compressible fixture (64 KiB zeros): deflate saves ~99% bytes but costs
  ~ms CPU per message on loopback and opens CRIME/BREACH side channels over
  mixed secret/attacker-controlled envelopes plus decompression-bomb DoS
  (must bound inflation to 1 MiB anyway).
- Reference harness runs with compression off; enabling it for one pairing
  would fork interop (compressed vs identity legs diverge on the wire).

Tradeoff: bandwidth saving is deployment-specific and small on the
restricted-development transports (loopback/isolated net); cost is CPU,
negotiation complexity, side-channel and bomb surface.

Decision: keep default-off everywhere. Deployments that opt in MUST document
window/context settings and enforce the decompressed-size bound. No change
to the reference runtime.

## 3. Idle lease / heartbeat / keepalive

Normative: transport liveness stays at the transport layer (`SNTR-TLS-011` /
WS `SNTR-WS-072` Ping/Pong with bounded documented timeouts). Syntra adds a
capability-gated client-negotiated idle/keepalive lease under
`syntra.reliable-session/1` (`SNTR-SESS-030..034`, `SNTR-REL-011..015`):
client proposes, host confirms/clamps effective lease, renewal is
application traffic or explicit keepalive with acknowledgement, expiry detaches
the attachment while disconnected-session retention remains separate from
authentication validity and RPC deadlines.

Measurements:
- Loopback handshake completes in ms (5 s budget is a bound, not a cost).
- Idle connection cost: pending table + buffers + handler slots (~KB per
  connection); handshake cost: one hello/ready exchange + policy check.
- `SC-GRACEFUL-CLOSE` and `SC-TRANSPORT-LOSS` prove both paths: graceful
  drains queued results then discards state; abrupt maps in-flight to
  `UNAVAILABLE` unknown-outcome.

Tradeoff: keepalive masks NAT/proxy idle drops but adds timer/wheel and
versioning surface. WS Ping/Pong alone cannot renew a Syntra attachment;
without the lease, idle drops are abrupt loss requiring fresh handshake.

Decision: implement the negotiated lease as correctness work (task 12), tune
intervals with production profiles under task 7. Batching stays
one-Frame-per-Send with transport coalescing; compression stays default-off.

## 4. Conclusion

No premature optimization. The reference path stays: one Frame per Send,
identity encoding, no heartbeat. All three options remain deployment opt-ins
behind documented bounds and capability negotiation, never silent defaults.

## 5. Experimental SC1 handshake size accounting

[Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
selects transport-independent SC1 and remains Draft. Experimental draft-1
implementations and benchmarks now exist. The
[implementation status](sc1-implementation.md#implementation-status) and
[verification evidence](sc1-implementation.md#verification-evidence) ledger
owns implementation coverage and conformance status; the measurements below
do not establish RFC acceptance or a production security profile.

The [shared channel contract](../specifications/security/secure-channel.md)
owns authentication ordering. The exact context and carrier bytes belong to
the [draft-1 carrier contract](../specifications/transports/noise-bindings.md).
For scope length `S` in exact UTF-8 bytes, `1 <= S <= 255`, the canonical
context contains:

| Field | Bytes |
|---|---:|
| Domain `syntra.sc1.draft1` | 17 |
| Mode + carrier | 2 |
| Server-key selector | 4 |
| Epoch | 8 |
| Opaque handle | 8 |
| Scope-length prefix | 2 |
| Scope | S |
| **Context total** | **41 + S** |

The context prefixes M1 in clear and is also the exact Noise prologue.
Bootstrap includes the zero epoch and zero handle; returning mode includes
its epoch and handle. The 32-byte AK enters the standard PSK input and is
not transmitted. Each raw Noise message contains a 32-byte ephemeral public
key and a 16-byte tag for its empty encrypted payload.

| Path | M1 including context | M2 | Total before carrier framing | TCP total, including two u16 length prefixes |
|---|---:|---:|---:|---:|
| Bootstrap `Noise_NK_25519_ChaChaPoly_SHA256` | 89 + S | 48 | 137 + S = 138–392 | 141 + S = 142–396 |
| Returning `Noise_NKpsk0_25519_ChaChaPoly_SHA256` | 89 + S | 48 | 137 + S = 138–392 | 141 + S = 142–396 |

Raw Noise bodies alone total 96 bytes. The shorthand `104 = 96 + 8` counts
only those bodies and a handle, not a complete draft-1 handshake. These
analytical totals exclude carrier establishment, WS framing, outer TLS,
client transport confirmation, Syntra `hello`/`ready`, enrollment and policy
work, and failed/new attempts. They are neither measured latency nor the
full establishment byte/RTT cost. Empty handshake payloads permit no 0-RTT
application data or credentials; reusing device authority does not imply
session resumption or automatic RPC retries. See the ledger's
[authentication boundary](sc1-implementation.md#authentication-boundary).

Draft-1 covers TCP/WS/WSS; HTTP/HTTPS request-response is excluded and UDP
is deferred. WSS retains verified outer TLS 1.3 or later under the carrier
contract; the measurements below do not measure that TLS layer.

## 6. SC1 draft-1 measured results

### Capture and scope

The 2026-10-28 full benchmark capture completed successfully: every package
result passed or reported no test files, with no `FAIL` samples. Its command
was:

```sh
go test -mod=readonly -run '^$' -bench . -benchmem -count=3 -benchtime=100ms -cpu=1,4 -timeout=10m ./...
```

This records benchmark execution, not a full test-suite or conformance run:
`-run '^$'` skips ordinary tests. Benchmark identifiers below are
language-specific labels for the measured operations, not protocol names or
commands reproducible in this specification checkout.

- The recorded execution used Go 1.26.10 on `darwin/arm64`, Apple M4. The raw
  benchmark stream identifies OS, architecture and CPU but omits `go version`
  and a source revision; it is not a self-contained immutable build attestation.
- The documented default session-core backend is pure Go. No explicit build
  tags appear in the command, but backend selection and `CGO_ENABLED` were
  not recorded in this capture. CGO being disabled in the benchmark workflow
  does not establish that it was disabled for this local run.
- There are three repetitions per CPU lane with a 100 ms target per sample.
  All table entries use **GOMAXPROCS=1**, the unsuffixed benchmark lane;
  `-4` samples are excluded. GOMAXPROCS is execution parallelism, not CPU
  affinity, and 16 workers do not mean 16 CPU cores.
- This is in-memory microbenchmark evidence. It does not measure deployed
  network latency, socket throughput, TLS-relative performance, energy or
  binary size. Timing is report-only, not a fixed CI performance gate;
  execution errors still fail the benchmark job.

### Representative observed ranges

Ranges are the minimum and maximum reported values across the three
GOMAXPROCS=1 samples, not confidence intervals. A single allocation figure
means all three samples reported it. B/op and allocs/op are per benchmark
operation as defined below, not retained memory or whole-RPC guarantees.

| Benchmark / operation | ns/op | B/op | allocs/op |
|---|---:|---:|---:|
| `BenchmarkWire/ScanFrameTags/request/1KiB` | 26.88–27.34 | 0 | 0 |
| `BenchmarkWire/MarshalFrame/request/1KiB` | 346.8–351.4 | 1,184 | 2 |
| `BenchmarkWire/UnmarshalFrame/request/1KiB` | 295.9–362.8 | 1,232 | 5 |
| `BenchmarkWire/RoundTrip/request/1KiB` | 644.5–728.4 | 2,416 | 7 |
| `BenchmarkSessionHeaderValidation` | 35.82–37.08 | 0 | 0 |
| `BenchmarkSessionLoopback/1KiB/Serial` | 6,305–6,353 | 12,664 | 57 |
| `BenchmarkSessionLoopback/1KiB/Workers16` | 6,060–6,072 | 12,663–12,664 | 56–57 |
| `BenchmarkSessionCoreHandshake` | 1,536–1,568 | 1,496 | 29 |
| `BenchmarkSessionHandshake` | 12,987–13,130 | 20,831–20,832 | 150–151 |
| `BenchmarkAppendContext/bootstrap` (preallocated) | 8.744–8.876 | 0 | 0 |
| `BenchmarkAppendContext/returning` (preallocated) | 8.801–8.880 | 0 | 0 |
| `BenchmarkHandshakeAndConfirm/NK` | 288,406–292,197 | 15,968 | 225 |
| `BenchmarkHandshakeAndConfirm/NKpsk0` | 294,607–295,819 | 26,561 | 367 |
| `BenchmarkRecordWarm/returning/1024/client-to-server` | 2,077–2,472 | 32 | 2 |
| `BenchmarkNetPipeReassembly` (encrypted TCP, 128 KiB) | 209,556–215,910 | 136,129 | 90 |
| `BenchmarkWebSocketAdapterPipeEcho/1KiB` (encrypted WS) | 12,220–12,363 | 5,920 | 68 |

### Measurement boundaries

- **Wire and headers:** fixtures and logical round-trip validation are
  prepared before timing. Wire round trip means marshal plus unmarshal of
  one request, not request/response I/O. Wire byte accounting uses serialized
  envelope size, doubled for round trip. Scans skip opaque payload contents,
  so their logical MB/s is not memory bandwidth. Phase-header checking avoids
  a second Protobuf object; full decode and semantic validation still precede
  admitted effects. Neither zero-allocation row describes full RPC dispatch.
- **Session loopback:** one operation is a payload-verified echo RPC through
  client and host over an in-memory loopback pair, with explicit allow-all
  method authorization. Configuration, activation, fixture allocation and
  worker creation are outside timing; worker release, calls, comparisons and
  completion collection are timed; teardown is excluded. Workers16 means
  exactly 16 workers, each with at most one outstanding call. Byte throughput
  counts request plus echo application bytes, excluding envelopes. These rows
  do not include SC1 carrier encryption and retain real session/writer
  allocations; they are not allocation-free RPCs.
- **Session handshakes:** CoreHandshake includes core construction, hello
  encoding/acceptance, authentication completion, ready encoding/activation
  and both closes; configuration resolution is excluded. SessionHandshake
  includes the full loopback construction/activation/cancellation/join/close
  lifecycle, excluding configuration construction. Neither sends an
  application RPC or measures the Noise handshake.
- **SC1 context and handshake:** AppendContext writes canonical bytes into
  preallocated storage; setup and final byte comparison are excluded.
  HandshakeAndConfirm includes both Noise roles with real `crypto/rand`
  ephemerals, one verified 64-byte record in each direction and channel close;
  static provisioning is outside timing. Its byte metric counts context,
  both 48-byte Noise messages and two 80-byte ciphertext records, excluding
  carrier headers. It includes duplex confirmation, not carrier setup,
  enrollment storage/policy or Syntra readiness.
- **Warm records:** one operation encrypts and decrypts one 1,024-byte
  returning-mode client-to-server plaintext. Cipher setup and one warmup pair
  are excluded; buffers are reused and nonces advance without reset. Final
  payload/nonce checks are outside timing. Byte throughput counts one
  plaintext length per pair. The measured dependency path still allocates
  32 bytes in two allocations per pair.
- **Encrypted TCP:** one operation sends and reassembles a 128 KiB frame
  through the production adapter over `net.Pipe`, including worker
  synchronization. Handshake and fixture allocation are excluded. Byte
  throughput counts one frame, excluding headers and tags; no OS socket or
  network stack is measured.
- **Encrypted WS:** one operation is a serial, verified adapter Send/Recv
  echo over `net.Pipe`, with two owned frames. Provisioning, a real in-memory
  HTTP/WebSocket upgrade, SC1 handshakes and cleanup are outside timing.
  Active assembly timers, encryption, framing, masking and I/O are included.
  Byte throughput counts twice the application-frame length; `frames/s`
  counts both directions. This is neither a high-level RPC nor a WSS/TLS
  deployment measurement.

### Interpretation and follow-up

The older build-graph baseline used Go 1.26.4 and default GOMAXPROCS=10,
before runtime hardening and its additional ownership/writer work. It is not
a like-for-like baseline for this capture. These three short repetitions
support reporting observed costs only, not a statistically sound comparison,
regression attribution or a performance-win claim, including against TLS.

A comparative run needs the same toolchain, backend/build tags, CGO setting,
CPU lanes, fixture sizes and timing boundaries on both revisions, with source
revision and environment recorded. Collect at least ten samples per revision,
preferably interleaved on an otherwise idle host, before drawing comparative
conclusions. Dedicated socket/network measurements are needed for deployment
claims. Allocation work must preserve buffer ownership, authentication and
nonce safety. Operational bounds and unresolved production work remain owned
by the ledger's [operational limits](sc1-implementation.md#operational-limits)
and [remaining work](sc1-implementation.md#remaining-work).
