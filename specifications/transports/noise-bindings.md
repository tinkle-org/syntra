# Syntra Secure Channel v1 — Carrier binding proposals

- Status: Proposal only — Draft RFC 0007; no registered conformance profiles
- Date: 2026-10-27
- Parent: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Security owners: [shared channel](../security/secure-channel.md) and
  [device authorization](../security/device-authorization.md)

These are proposed mappings for one transport-independent channel, not three
different cryptographic protocols. The core does not initiate networking.
Applications supply stream/datagram/message I/O through optional adapters.
Existing profile identifiers and plaintext/TLS-backed mappings are unchanged.
New binding identifiers and frozen byte schemas require RFC acceptance.
Raw UDP remains deferred, not supported by virtue of this document.

## 1. Common handshake mapping

The binding selects bootstrap NK or returning NKpsk0 explicitly. A wrapper
carries bounded mode/context information and, for returning devices, the
authorization lookup handle. Both sides feed the identical canonical context
into the Noise prologue. Context includes version, carrier, endpoint scope,
handle and epoch where relevant. The exact wrapper and encoding are freeze
blockers; the eight-byte handle alone is not a complete protocol preface.

Each empty-payload Noise message is 48 bytes. Bootstrap uses 96 Noise bytes;
returning channels use those 96 plus the proposed eight-byte handle before
additional context/framing. Wrappers are parsed and bounded before Noise
processing. No client may send Syntra credentials until the second Noise
message has been verified. The host gates protected work on fresh client
transport confirmation and the subsequent Syntra handshake/authorization.

## 2. TCP stream candidate

Proposed transport record format after establishment:

```text
TCP bytes:                 u16BE(C) || NoiseCiphertext[C] || ...
Authenticated plaintext:   u32BE(F) || ProtobufFrame[F] || ...
```

`C` counts ciphertext including its tag and excludes the two-byte prefix.
The proposed profile permits nonempty plaintext records, so `17 <= C <=
65,535`; a standard Noise empty plaintext is not used as a heartbeat or close
marker. `F` counts serialized `Frame` bytes, excluding its four-byte prefix:
`1 <= F <= 1,048,576`, subject to a documented lower deployment limit.

The encrypted inner stream retains a simple envelope length and can span
records. Records may contain pieces of one envelope or several complete
envelopes. Prefixes may themselves span records. This deliberately avoids
frame IDs, fragment numbers and fragment counts on an already ordered stream.
It differs from proposals using a record-type byte; their overhead figures
do not describe this candidate.

The receiver first bounds the outer length, authenticates the complete record,
then incrementally reconstructs the inner stream. It bounds `F` before
allocating frame storage and dispatches only complete validated envelopes.
It never infers boundaries from reads or Protobuf parsing or scans to recover
after corruption. The clear outer prefix is not authenticated AD: alteration
can cause bounded waiting, truncation or tag failure, not unchecked allocation.

One writer serializes ciphertexts and retains partial-write offsets. Once a
nonce is consumed, the resulting ciphertext is sent in order or the channel
is aborted. Cancellation cannot remove an unfinished envelope from the inner
stream or insert another frame into it. A blocked writer has a separate
deadline; RPC cancellation does not stop all remote processing by itself.

For an independently packed envelope of `F` bytes in `N` records, overhead is
`4 + 18*N` bytes. For `N=1` it is 22 bytes above the serialized envelope.
With maximal records, a 1 MiB envelope needs 17 records and 310 overhead bytes.
These are framing calculations, not full-RPC or TCP/IP costs, worst-case
tiny-record bounds, or measured performance.

TCP establishment, channel establishment and Syntra `hello`/`ready` have
separate bounded phases and a total-attempt budget. FIN/EOF and half-close do
not prove application completion. Truncated outer/inner prefixes or bodies
are failures; complete-boundary EOF is still not authenticated close. Drain
within a close budget or abort, settle callers, and discard channel state.

## 3. WebSocket message candidate

One complete binary WebSocket message would contain one bounded channel
handshake wrapper/message during establishment or one Noise ciphertext after
establishment. No TCP outer length prefix is necessary because the carrier
preserves message boundaries. Limits apply to reassembled messages, not only
individual WebSocket fragments; underlying library allocation also needs
bounds.

The candidate uses the same authenticated inner `u32BE(F) || Frame` stream as
TCP to handle envelopes above the Noise record limit without introducing a
second fragmentation grammar. An envelope may span multiple binary messages,
and the parser preserves state across them. A single-envelope/single-record
message adds 20 bytes above its envelope, excluding WebSocket framing.

Carrier Ping/Pong/Close remain carrier operations, not authorization, Syntra
RPC results or cryptographic record acknowledgments. The frozen profile must
specify text rejection, handshake-wrapper errors, message bounds, close
mapping and exact deadlines. A browser may impose assembly limitations that
prevent a full bounded-allocation claim; those limitations require disclosure.

This is **not** the existing WS/WSS mapping, where a binary message is a
serialized `Frame`. Existing clients must not be silently upgraded or given
the same profile/subprotocol identifier for different bytes. A separate
explicit endpoint/subprotocol selection and migration contract is required.
Browser `wss://` retains TLS outside WebSocket even when SC1 protects its
binary messages. Existing HTTPS/WSS compatibility profiles remain available.

## 4. UDP datagram work required

The same channel construction can have a datagram binding, but neither
Noise nor an authenticated datagram supplies reliable ordered delivery.
The following are blockers for a UDP specification and implementation:

| Area | Required design/verification |
|---|---|
| Handshake | Attempt demultiplexing, bounded retransmission, duplicate flights, cached exact responses, fresh ephemerals per new attempt, replay/DoS budgets and absolute expiry |
| Routing | Channel-handle assignment, collision scope, authenticated communication, retirement and unknown-handle behavior |
| Records | Explicit per-direction nonce/counter, key limits, duplicate rejection and a bounded sliding receive window |
| State updates | Authenticate and check replay before changing replay/peer/application state; invalid tags cannot advance the receive window |
| Path changes | Return-path validation and anti-amplification; a valid tag alone does not establish source-address reachability |
| Payload sizing | MTU/path behavior, bounded record sizes without relying on IP fragmentation, aggregate reconstruction caps and timeout |
| Reliability | Congestion control, loss/retransmission and ordering semantics, delivery ambiguity and cancellation |
| Fragmentation | Exact encoded frame length, identity/offset/count rules, overlap/duplicate handling, bounded concurrent assemblies and expiry |
| Headers | Bind routing/type/context through an explicitly reviewed representation; do not silently add outer-header AD to standard Noise transport |

The standard Noise out-of-order mechanism permits carrying a nonce and
rejecting successfully authenticated duplicate nonces. That alone does not
define the entire UDP binding above. If ciphertext is retransmitted, the
binding must distinguish retransmitting identical bytes from encrypting a
new message under an already used nonce. It must also prevent invalid input
from poisoning counters, paths or assemblies.

No 14-byte header, 31-byte overhead, roaming guarantee, reliability feature,
or UDP production claim is standardized here. Those need frozen schemas,
failure rules, threat review, deterministic fixtures and independent interop.

## 5. Selection, compatibility, and verification

Endpoints select carrier/mode explicitly and bind them to the handshake.
They never sniff a secure failure and automatically retry over another mode
or plaintext. An AK can authorize another permitted carrier within its scope,
but that carrier establishes new traffic keys and a new Syntra binding.
Logical-session resumption, RPC idempotency and event recovery are separate.

The [acceptance plan](../../conformance/plans/secure-channel.md) includes
every split point of short TCP records, coalescing and large-frame assembly,
message/carrier boundaries, malformed lengths/tags, bounded cancellation and
shutdown, and the UDP-specific failure/DoS cases above. No conformance profile
or vector is registered before the mapping and evidence exist.

## References

- [Noise Protocol Framework](https://noiseprotocol.org/noise.html), §§3, 5,
  11.4, 13–14.
- Existing [TCP](tcp.md), [WebSocket](websocket.md), and
  [secure WebSocket](secure-websocket.md) mappings, which are not redefined here.
