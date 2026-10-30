# Syntra Secure Channel v1 — Carrier bindings

- Status: Accepted (2026-10-29) — normative SC1/WSS profile `SNTR-SC1-WSS-V1`
- Date: 2026-10-29
- Owner: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Security owners: [shared channel](../security/secure-channel.md) and
  [device authorization](../security/device-authorization.md)
- Requirements: `SNTR-SCW-001`–`SNTR-SCW-012`

This document defines the accepted v1 byte mapping for the shared channel in
[secure-channel.md](../security/secure-channel.md). WSS is the permitted public
production carrier. TCP and plaintext WS are restricted development carriers.
UDP is deferred and is not part of this profile.

The accepted contract is RFC 0007 §11.4 and this document. The earlier
`syntra.sc1.draft1` bytes and local-revision-1 format are historical
experimental formats; they are not aliases and MUST be rejected. Baseline WSS
profiles (`SNTR-WSS-H1-V1`) retain their own frame-per-message mapping,
identifiers and claims. An SC1 pass does not certify a baseline profile.

## 1. Profile identity and selection

**SNTR-SCW-001** — SC1/WSS implementations MUST select the profile explicitly
by endpoint `/syntra/v1/sc1/ws` and the exact, case-sensitive WebSocket
subprotocol `syntra.sc1.v1`. They MUST NOT reuse the baseline WebSocket
endpoint `/syntra/v1/ws`, the baseline subprotocol `syntra.v1`, or a draft-1
identifier. Selection failures MUST fail closed; a failed SC1 attempt MUST NOT
trigger automatic retry over plaintext, bootstrap, another suite or a legacy
format.

**SNTR-SCW-002** — Both roles MUST encode and authenticate the canonical
context in §2 byte-for-byte as the Noise prologue. The context is public and
MUST be the exact prefix of M1. There is no additional domain separator,
revision field, hash, padding or terminator. Context mismatch MUST fail before
credential lookup, protected dispatch or application effects.

## 2. Canonical context

Let `S = len(scope)` in bytes. All offsets are zero-based and half-open.

| Offset | Bytes | Field | Encoding |
|---|---:|---|---|
| `[0,13)` | 13 | domain | ASCII `syntra.sc1.v1`, no terminator |
| `[13,14)` | 1 | mode | `u8`: bootstrap `1`, returning `2` |
| `[14,15)` | 1 | carrier | `u8`: TCP `1`, WS `2`, WSS `3` |
| `[15,19)` | 4 | `server_key_id` | `u32BE`; zero permitted |
| `[19,27)` | 8 | enrollment epoch | `u64BE` |
| `[27,35)` | 8 | enrollment handle | eight opaque bytes |
| `[35,37)` | 2 | scope length `S` | `u16BE` |
| `[37,37+S)` | `S` | scope | exact UTF-8, 1–255 bytes, no normalization |

The context is `37 + S` bytes: **38–292 bytes**. Bootstrap requires mode `1`,
epoch zero, an all-zero handle and no AK. Returning mode requires mode `2`, a
nonzero epoch, a nonzero independent handle and a separately provisioned
uniformly random 32-byte AK. The AK enters only the Noise PSK input, never the
prologue. `server_key_id`, carrier and scope MUST match the responder's
configuration; an input selector cannot create trust.

## 3. Handshake

**SNTR-SCW-003** — Both roles MUST use
`Noise_NK_25519_ChaChaPoly_SHA256` for bootstrap and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices, with standard PSK
placement `0` and fresh ephemeral key pairs per attempt. Both handshake
payloads MUST be empty. M1 is the context followed by exactly 48 Noise bytes
(**86–340 bytes**); M2 is exactly 48 Noise bytes (**134–388 bytes** total
before carrier framing). Unexpected lengths, payloads, modes, carriers,
contexts or trailing bytes are terminal.

**SNTR-SCW-004** — The initiator MUST verify the trusted server static key
through the Noise handshake and MUST verify the outer TLS 1.3 server
certificate and hostname for WSS. TLS verification MUST NOT be disabled to make
a deployment work. If either the TLS identity or the Noise pin fails, the
attempt fails closed with no credential release and no fallback. The initiator
MUST NOT send `hello` until M2 verifies.

## 4. WSS mapping

**SNTR-SCW-005** — SC1/WSS MUST run over verified TLS 1.3 or later. Each M1,
M2 and ciphertext record MUST occupy exactly one reassembled binary WebSocket
message. There is no `u16BE` SC1 prefix inside a WebSocket message. Text
messages, compressed messages, empty messages, truncated messages and invalid
tags MUST be rejected. WebSocket fragmentation is reassembled by the carrier;
SC1 record boundaries are not WebSocket frame boundaries. Ping, Pong and Close
are carrier control operations and are never authorization, channel
confirmation or RPC results.

**SNTR-SCW-006** — The Upgrade request MUST target `/syntra/v1/sc1/ws` with no
userinfo, query or fragment. The host MUST require the exact subprotocol
`syntra.sc1.v1`, MUST reject `Authorization` and `Cookie` request headers, and
MUST NOT treat `Origin` or forwarding headers as authentication. The client
MUST validate the 101 response and its `Upgrade` and `Connection` tokens,
`Sec-WebSocket-Accept` and selected subprotocol before sending any SC1 bytes;
if validation fails, it MUST close and send no M1. The client MUST NOT send a
Syntra credential in the request target or Upgrade headers.

**SNTR-SCW-007** — The host MUST terminate TLS itself for the initial permitted
topology in §8. A deployment that terminates TLS at a proxy MUST NOT claim
SC1/WSS or assert carrier `3` until a proxy topology is separately specified
and tested. A forwarded header is not evidence of the external carrier.

## 5. Restricted development carriers

**SNTR-SCW-008** — SC1/TCP and SC1/WS are restricted development carriers. They
MUST be disabled by default in any distribution claiming production readiness
and MUST be documented as providing no outer TLS. SC1/TCP MUST wrap every
handshake message and record in `u16BE(length) || bytes`, where the length
counts only the following bytes. SC1/WS MUST use one binary message per
handshake message or record, with carrier values TCP `1` and WS `2`
respectively. Plaintext WS MUST be restricted to loopback or an isolated test
network. Wrapping a development stream in TLS does not make it the WSS carrier
and does not permit carrier value `3`.

## 6. Records and the inner frame stream

**SNTR-SCW-009** — After Noise `Split()`, each direction MUST use independent
standard Noise transport state, implicit ordered nonces and empty associated
data. Record plaintext MUST be 1–65,519 bytes; ciphertext MUST be 17–65,535
bytes including the 16-byte tag. Empty plaintext records are not used as
heartbeats or close markers. Carrier headers are not authenticated AD; altering
a clear length or WebSocket boundary may cause bounded waiting or failure, never
unchecked allocation.

**SNTR-SCW-010** — Authenticated plaintext is the stream
`u32BE(F) || Frame || u32BE(F) || Frame ...`, where `F` is the serialized
`Frame` length. `F` MUST be 1–1,048,576 bytes. Prefixes, frames and record
boundaries are independent: a prefix or frame may span records, and one record
may contain multiple complete frames. The receiver MUST authenticate a complete
record before consuming plaintext, enforce `F` before frame allocation, and
dispatch only complete validated `Frame` messages. It MUST NOT resynchronize,
scan for a boundary or decode a partial frame.

## 7. First authenticated envelope and readiness

**SNTR-SCW-011** — The first authenticated plaintext MUST begin with exactly
one complete framed `ClientHello`. The envelope MAY span multiple records. The
record that completes it MUST end exactly at the hello boundary; no additional
complete envelope and no partial trailing envelope are permitted there. The
hello remains subject to the 1 MiB frame limit and to bounded frame-assembly
time and bytes. The host MUST validate the hello, apply current enrollment,
same-principal and method policy, and only then send `ready` and permit
protected dispatch. A replayed M1, an unauthenticated record or an
authenticated record without a valid hello supplies no fresh confirmation and
MUST NOT bind a principal or release sensitive output. A violation terminates
the channel natively and dispatches nothing.

## 8. Limits, cancellation and deployment

**SNTR-SCW-012** — Deployments MUST enforce finite, documented budgets and
MUST NOT retain unbounded work. The SC1/WSS profile defines these defaults;
implementations MAY choose shorter positive values and MUST NOT permit values
above the stated maxima:

| Operation | Default | Maximum |
|---|---:|---:|
| Total dial, TLS, Upgrade, SC1 and core readiness attempt | 15 s | 24 h |
| SC1 establishment and first-record confirmation | 5 s | 24 h |
| Next complete record, including idle wait | 30 s | 24 h |
| Frame assembly from first incomplete plaintext | 30 s | 24 h |
| One complete frame's encrypted output | 10 s | 24 h |
| Close/owner-task join after close | 1 s | 24 h |
| Channel lifetime, including idle and suspension | 24 h | 24 h |
| Protected records per direction | `2^32` | `2^32` |

Trickle input MUST NOT refresh an absolute deadline. Pending-operation
admission MUST be bounded (default 32 per direction, maximum 1,024) and excess
work MUST be rejected immediately. Writer queue capacity MUST be bounded
(default 256 frames, 1–1,024) and deployment memory budgets SHOULD use a
smaller value. One writer MUST serialize each record and retain the exact
ciphertext and partial-write offset; once a nonce is consumed, the ciphertext
MUST be emitted in order or the channel aborted. Cancellation MUST NOT splice
another frame into unfinished output or re-encrypt under a consumed nonce.

At 24 hours or `2^32` records in either direction, the channel MUST close
without wrapping counters. Renewal is a fresh handshake with fresh traffic
keys, followed by explicit recovery negotiation where the application supports
it; no in-place rekey, session resumption or RPC replay is implied.

The initial permitted production topology is direct verified TLS 1.3 WSS
termination by the host. Proxy termination is deferred. Hosts MUST bound
aggregate connections, unauthenticated handshakes, crypto workers, queued bytes
and reassembly memory. Operational budgets and their evidence belong to the
deployment record.

## 9. Failure, close and migration

Channel authentication, framing, context and policy failures MUST terminate the
carrier without an SC1 diagnostic payload or a promised WebSocket close code.
No carrier close is an authenticated SC1 close or a delivery acknowledgement.
EOF at a complete boundary is transport loss, not proof of orderly application
completion. Truncated records or frames MUST be discarded and never dispatched.
Callers MUST settle under the core loss/cancellation rules; unknown outcomes
remain unknown.

The v1 bytes are not backward compatible with `syntra.sc1.draft1` or the old
local-revision-1 format. A deployment that temporarily retains a legacy
endpoint MUST keep it explicitly configured and MUST NOT alias it to v1. A
failed v1 attempt MUST NOT fall back to a legacy or plaintext profile.

## 10. Verification and claims

Public context and prologue examples are frozen in
[`conformance/plans/sc1-context-v1.json`](../../conformance/plans/sc1-context-v1.json)
and registered through [`conformance/test-vectors/sc1/context-vectors.yaml`](../../conformance/test-vectors/sc1/context-vectors.yaml).
These are encoding fixtures, not independent Noise ciphertext vectors.

The Rust implementation at `tinkle-org/syntra-rs` main (`50ca849`) implements
the reviewed proposal and records local unit, race, transport, FFI/WASM and
security-check results in its `SC1.md`, `AUDIT.md` and
`docs/implementation-status.md`. That is implementation evidence for the
selected bytes, not independent interoperability, formal `CONF-SCW-*`
execution, mobile validation or an independent security review. Docker and
browser runs were not established, and host authorization, durable recovery,
production FFI and mobile integration remain implementation work.

The registered profile and cases are in
[`conformance/profiles.yaml`](../../conformance/profiles.yaml) and
[`conformance/manifest/sc1-wss.yaml`](../../conformance/manifest/sc1-wss.yaml).
A profile registration is not an execution result. Independent vectors,
pure-Go/Rust both-role and both-mode runs, direct-topology tests, recovery and
mobile evidence and independent human review remain release gates.

## References

- [Noise Protocol Framework](https://noiseprotocol.org/noise.html), revision 34:
  §§3, 5–7, 9, 11.2–11.4, 13–14.
- [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md) §11.
- [Secure channel](../security/secure-channel.md),
  [device authorization](../security/device-authorization.md),
  [ADR-011](../decisions/ADR-011-noise-device-authorization.md).
- Existing [TCP](tcp.md), [WebSocket](websocket.md) and
  [secure WebSocket](secure-websocket.md) mappings, which are not redefined
  here.
