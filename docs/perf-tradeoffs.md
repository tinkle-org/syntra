# Batching / compression / idle-lease tradeoffs — evaluation 7 (no premature optimization)

Status: evaluated 2026-10-22 on main 9b8be21. Decision: **no changes** —
keep one-Frame-per-Send, compression default-off, idle lease supported
(capability-gated `syntra.reliable-session/1`) but not enabled by default.
Rationale and measurements below. Revisit only with production profiles and
an RFC; do not optimize the reference path prematurely.

## 1. Batching (envelope vs transport)

Normative: `SNTR-WIRE-001` — one `Frame` per Protobuf message; batching
multiple `Frame`s inside one message is forbidden. Transport batching
(multiple length-prefixed frames in one TCP segment) is framing, allowed.

Measurements (loopback, this checkout):
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

## 5. SC1 handshake size accounting (proposal only)

The historical evaluation above measures the existing runtime, not SC1.
New [Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
selects transport-independent SC1 but is not Accepted. No SC1
implementation, throughput/latency benchmark, or passing conformance
result is asserted here; baseline TLS requirements and executable
profiles remain unchanged.

For the selected [channel design](../specifications/security/secure-channel.md),
empty Noise M1/M2 payloads give these handshake-body sizes:

| Path | M1 body | M2 body | Lookup handle | Total counted bytes |
|---|---|---|---|---|
| Initial `Noise_NK_25519_ChaChaPoly_SHA256` | 48 | 48 | None | 96 |
| Returning `Noise_NKpsk0_25519_ChaChaPoly_SHA256` | 48 | 48 | 8-byte `auth_id` | 104 = 96 + 8 |

Each body includes a 32-byte ephemeral public key and a 16-byte tag for
the empty encrypted payload. The returning total adds only the opaque
lookup handle; the unique random shared 32-byte AK is not sent on
reconnect. Every channel still uses fresh ephemeral material and
directional traffic keys.

These totals exclude carrier/record framing and additional epoch/version
fields. They also exclude carrier establishment, the first authenticated
client transport record verified before protected actions, Syntra
hello/ready, and host enrollment/authorization work. They are not the byte
cost or RTT of full establishment, and empty M1/M2 does not permit 0-RTT
application data or credentials. Per-carrier costs belong to the proposed
[TCP/UDP/WS bindings](../specifications/transports/noise-bindings.md);
browser `wss://` still requires outer TLS. Reusing device authority does
not imply session resumption or automatic RPC retries.
