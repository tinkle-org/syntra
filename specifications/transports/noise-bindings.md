# Syntra Secure Channel v1 — Carrier binding proposals

- Status: Proposal only — Draft RFC 0007; no registered conformance profiles
- Date: 2026-10-27
- Parent: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Security owners: [shared channel](../security/secure-channel.md) and
  [device authorization](../security/device-authorization.md)

These are concrete experimental draft-1 mappings for one transport-independent
channel over TCP, WS and WSS, pending RFC acceptance. The core does not initiate
networking; applications supply I/O through adapters. Executed implementation
tests and integration evidence are recorded in the
[implementation evidence ledger](../../docs/sc1-implementation.md).
Existing profile identifiers and plaintext/TLS-backed mappings are unchanged.
The draft-1 domain and WS subprotocol below identify experimental bytes, not
accepted conformance profiles. Raw UDP remains deferred. HTTP/HTTPS
request-response is excluded from SC1 draft-1; existing HTTP/HTTPS profiles
remain unchanged.

## 1. Common handshake mapping

The binding selects `Noise_NK_25519_ChaChaPoly_SHA256` for bootstrap or
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices, with standard PSK
placement 0. There is no negotiation menu or fallback. The exact canonical
context is the following concatenation, with no padding or terminator:

| Field | Exact draft-1 encoding |
|---|---|
| Domain | ASCII `syntra.sc1.draft1` (17 bytes) |
| Mode | `u8`: bootstrap = 1, returning = 2 |
| Carrier | `u8`: TCP = 1, WS = 2, WSS = 3 |
| ServerKeyID | `u32BE`; zero is allowed |
| Epoch | `u64BE` |
| Handle | Eight opaque bytes |
| Scope length | `u16BE`, counting scope bytes |
| Scope | Exact UTF-8, 1–255 bytes, without normalization |

Context length is `41 + S` bytes, hence 42–296 bytes. Bootstrap requires epoch
zero, an all-zero handle and no AK. Returning mode requires nonzero epoch,
a handle other than all zero, and a 32-byte AK other than all zero. High-entropy
AK generation remains a separate provisioning obligation; nonzero validation
does not prove entropy. The AK enters only the standard PSK input.

M1 is `canonical_context || NoiseMessage1[48]`: 90–344 bytes. The context is
cleartext and is also supplied byte-for-byte as the Noise prologue. M2 is
exactly `NoiseMessage2[48]`. Both handshake payloads are empty. Total handshake
bytes before carrier framing are 138–392, for either mode. The raw Noise bodies
alone total 96 bytes; 104 = 96 + 8 counts only those bodies and a handle, not
this complete draft-1 exchange. Wrappers are bounded before Noise processing.
No client may send Syntra credentials until M2 is verified. The host gates
protected work on fresh client transport confirmation and subsequent Syntra
handshake/authorization; replayed M1 does not provide that confirmation.

## 2. TCP stream candidate

Every M1, M2 and transport record is wrapped in `u16BE(length) || message`.
The prefix counts only the following message bytes. TCP handshake totals are
142–396 bytes, including the two prefixes. After establishment:

```text
TCP bytes:                 u16BE(C) || NoiseCiphertext[C] || ...
Authenticated plaintext:   u32BE(F) || ProtobufFrame[F] || ...
```

`C` counts ciphertext including its tag and excludes the two-byte prefix.
The experimental binding permits nonempty plaintext records, so `17 <= C <=
65,535`; a standard Noise empty plaintext is not used as a heartbeat or close
marker. `F` counts serialized `Frame` bytes, excluding its four-byte prefix:
`1 <= F <= 1,048,576`, subject to a documented lower deployment limit.

The encrypted inner stream retains a simple envelope length and can span
records. Records may contain pieces of one envelope or several complete
envelopes. Prefixes may themselves span records. This deliberately avoids
frame IDs, fragment numbers and fragment counts on an already ordered stream.
It has no record-type byte; overhead figures for a different grammar do not
describe this binding.

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

Exactly one reassembled binary WebSocket message contains one M1, M2 or
transport ciphertext. There is no TCP `u16BE` prefix. Selection uses the exact,
case-sensitive subprotocol `syntra.sc1.draft1`; compression is off and text
messages are rejected. Bounds apply to reassembled messages, not merely their
individual fragments. WSS uses the distinct carrier value 3 and verified TLS
1.3 or later; TLS policy for a custom `RoundTripper` is host-owned and must not
be inferred to have been verified by the default adapter path.

The binding uses the same authenticated inner `u32BE(F) || Frame` stream as
TCP to handle envelopes above the Noise record limit without introducing a
second fragmentation grammar. An envelope may span multiple binary messages,
and the parser preserves state across them. A single-envelope/single-record
message adds 20 bytes above its envelope, excluding WebSocket framing.

Carrier Ping/Pong/Close remain carrier operations, not authorization, Syntra
RPC results or cryptographic record acknowledgments. Malformed wrappers,
invalid lengths/tags and incomplete records/frames fail closed; there is no
resynchronization. Operational deadlines and tested failure/close behavior are
recorded in the evidence ledger. A browser may impose assembly limitations that
prevent a full bounded-allocation claim; those limitations require disclosure.

This is **not** the existing WS/WSS mapping, where a binary message is a
serialized `Frame`. Existing clients must not be silently upgraded or given
the same profile/subprotocol identifier for different bytes. A separate
explicit endpoint/subprotocol selection is required; draft-1 uses the token
above, never `syntra.v1`.
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

The implemented ordered record construction uses empty associated data and
implicit ordered per-direction nonces; plaintext is 1–65,519 bytes and
ciphertext is 17–65,535 bytes. Records are authenticated before allocating a
declared inner frame. Both the inner prefix and frame can span records, and
coalesced frames are accepted. The ordered adapters default to 5 seconds each
for channel handshake, write, frame assembly and record assembly, configurable
only to shorter positive durations. Pending-operation admission defaults to
32 per direction including active work, permits at most 1,024, and rejects
excess work immediately as busy. Lifetime defaults to 24 hours with shorter
values permitted; usage is capped at `2^32` records per direction. The entry
clock includes establishment and expires idle channels too. These are implemented experimental
defaults, not accepted core requirements. The evidence ledger owns the total
dial, server, async-writer and shutdown budgets and their cancellation limits.

The [acceptance plan](../../conformance/plans/secure-channel.md) includes
every split point of short TCP records, coalescing and large-frame assembly,
message/carrier boundaries, malformed lengths/tags, bounded cancellation and
shutdown, and the UDP-specific failure/DoS cases above. The
[implementation evidence ledger](../../docs/sc1-implementation.md) separately
records executed unit/race/native-core tests and same-implementation Docker
integration across TCP/WS/WSS × NK/NKpsk0. No formal SC1 `CONF-*` cases or
profiles are registered. Independent vectors, cross-implementation exchange
and independent security review remain open; same-implementation success does
not supply those results.

## References

- [Noise Protocol Framework](https://noiseprotocol.org/noise.html), §§3, 5,
  11.4, 13–14.
- Existing [TCP](tcp.md), [WebSocket](websocket.md), and
  [secure WebSocket](secure-websocket.md) mappings, which are not redefined here.
