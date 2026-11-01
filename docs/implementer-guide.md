# Implementer Guide — Build Syntra v1 From Scratch

This guide explains how to build an independent Syntra implementation
using only this repository. It is informative: normative requirements
live in `specifications/` (see `specifications/README.md` for reading
order). Nothing here requires implementation code — only the specs, the
IDL, and the conformance suite.

The sequence below is ordered so each step is testable before the next
begins. After every step, run the corresponding conformance cases; do not
proceed on failing cases.

## Baseline and accepted SC1 work

The numbered steps implement the current baseline: its TLS requirements
and all existing executable conformance profiles remain unchanged.
[RFC 0007](../rfcs/0007-secure-channel-device-authorization.md) is accepted
and adds the `SNTR-SC1-WSS-V1` profile: canonical `syntra.sc1.v1` context
inside verified TLS 1.3 WSS at `/syntra/v1/sc1/ws`, with TCP/WS retained for
restricted development. The exact bytes and limits are in
[noise-bindings.md](../specifications/transports/noise-bindings.md). The Rust
implementation records local evidence, but registered `CONF-SCW-*` cases are
not executed by that evidence. Read the
[SC1 contract](../specifications/transports/noise-bindings.md) and the
[historical implementation record](sc1-implementation.md#implementation-status).

For SC1 integration, keep three separate gates: carrier establishment,
secure-channel authentication/confirmation, then Syntra hello/ready and
host authorization. Bootstrap `Noise_NK_25519_ChaChaPoly_SHA256`
and returning `Noise_NKpsk0_25519_ChaChaPoly_SHA256` use empty M1/M2
payloads, never 0-RTT application data or credentials. Protected actions
wait for verification of the first authenticated client transport record;
Noise completion does not replace Syntra `ACTIVE` or host policy.

The proposed [device model](../specifications/security/device-authorization.md)
uses a unique random shared 32-byte AK and opaque 8-byte `auth_id` per
device, not a signing keypair. The AK is not sent on reconnect; the handle
is a lookup hint, not authentication proof or `connection_id`. Enrollment,
storage, authorization, and revocation remain host-owned without mandatory
human accounts. Every channel has fresh ephemeral material and directional
traffic keys; returning-device authentication adds no session resumption
or automatic RPC retry.

Canonical v1 binds TCP messages with u16BE lengths, and WS/WSS binary messages
without that prefix. Both protect an inner u32BE-length-prefixed frame stream.
The exact domain/subprotocol is `syntra.sc1.v1`; ciphertext is at most 65,535
bytes and serialized frames at most 1 MiB. The first authenticated envelope is
exactly one complete framed `ClientHello`. UDP remains deferred and HTTP/HTTPS
request-response is excluded from SC1.
The core remains independent of socket dialing and carrier libraries. WSS
keeps verified outer TLS ≥1.3 and an independent Noise pin, without automatic
downgrade. These bytes do not redefine baseline WS/WSS profiles or production
TLS policy. [ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md)
is accepted; the [SC1 conformance plan](../conformance/plans/secure-channel.md)
distinguishes registered cases from implementation tests.

Authenticated out-of-band provisioning is the enrollment function delivered
in this guide; authorized bootstrap enrollment also stays permitted as a
designated authority path under the lifecycle contract. Accepted RFC 0007
owns the SC1 credential levels; accepted RFC 0010 fixes the host operational
contract for
enrollment authority, issuance, staged durable provisioning with
idempotent retries, principal binding, revocation propagation (at most a
300-second hard profile maximum with a 60-second operational target,
fail-closed), rotation, and compromise recovery. The contract is
registered, not yet executed; conformance runs and independent review
remain open gate work. Independent review, independent vectors/wire interoperability
and native ABI completion-time/credential-release gaps remain
[unresolved](sc1-implementation.md#remaining-work).

## 1. Obtain the schema from Git

Fetch the versioned schema from the Git tree, not a copy pasted from
somewhere else:

- Source: `proto/syntra/v1/*.proto` at a specification tag
  (`vX.Y` or `vX.Y-rcN`, proposed by Draft RFC 0011) or, before the first release, a commit SHA
  on `main`, package `syntra.v1`. There is no registry
  module — see `docs/schema-registry.md` §1.
- Pin the exact tag or commit your release builds against and record it
  with your declaration (see `docs/schema-registry.md` §§11–12 on
  pinning and reproducibility).
- Verify what you fetched: `buf build` and `buf lint` MUST pass clean
  (`STANDARD`, `FILE`, no exceptions). Any failure here means your input
  is wrong, not the protocol.

## 2. Generate or use language bindings

Generate message types with a pinned generator (see
`specifications/schema/generation.md` for the tested pins):

- Generate `Frame`, `ClientHello`, `ServerReady`, `RpcRequest`,
  `RpcResult`, `Cancel`, `Notification`, `RpcError`, and `ErrorCode` in
  your language. `session.proto` and `capabilities.proto` are
  documentation-only and intentionally define no types.
- Bindings are **data structures only**. They do not implement the
  handshake, sessions, RPC runtime, transport, or authentication. If a
  generated helper appears to decide protocol behavior, the specification
  wins (ADR-010).
- Language notes: generated unknown-field retention differs by runtime
  (e.g., Go preserves, Prost drops). Both satisfy tolerance rules because
  conformance compares decoded fields — but do not build re-emitting
  proxies that depend on retention. Generated debug/string output can leak
  credential bytes; never log it.

## 3. Implement envelope validation

Before any state machine, implement the per-`Frame` validator
(`SNTR-WIRE-003/005`, `SNTR-SER-005/006`):

1. Protobuf well-formedness + size/depth bounds (default envelope ceiling
   1 MiB / 1,048,576 serialized bytes; bound **before** full allocation).
2. `version` check (pre-handshake: within your proposed range;
   post-handshake: equals the selected version).
3. `request_id` discipline: `0` only for `hello`/`ready`/`notification`;
   nonzero for `request`/`result`/`cancel`.
4. Exactly one `body` variant set; reject reserved numbers 16/17.
5. Variant-state legality (no application frames before `ACTIVE`).

First failure determines the error; validation MUST complete before any
dispatch. Test with `CONF-CORE-*` and the `test-vectors/protobuf/` golden
vectors (logical equality, never byte equality).

## 4. Implement version negotiation

Propose your supported range as `[min_version, max_version]` (both nonzero,
`min ≤ max`) in `ClientHello`; select, as host, the highest overlap or fail
the handshake with `UNIMPLEMENTED` + close on version mismatch
(`SNTR-HS-003/010`, `SNTR-VER-002`). Record the selected version and stamp
it on every post-handshake `Frame`. Never negotiate below the highest
mutual version without explicit application consent (`SNTR-VER-007`).
Test with `CONF-SESS-004/010` and `CONF-CORE-005`.

## 5. Implement the session state machine

Implement exactly the six states `CONNECTED → NEGOTIATING →
AUTHENTICATING → ACTIVE → CLOSING → CLOSED` with the transition table in
`core/handshake.md` §1B — no shortcuts, no extra wire states, no
re-handshake on one transport (`SNTR-HS-001/040`). Default session
lifetime equals connection lifetime; connection close ends the session and
all per-connection state is discarded except diagnostics. There is no
session identifier in v1 and no resumption without a negotiated
capability: any resumption attempt without one MUST be rejected
(`SNTR-SESS-006`). Test with `CONF-SESS-*`.

## 6. Implement the authentication adapter

The ordinary authentication boundary hands you opaque credential bytes and
a policy hook. The experimental SC1 boundary additionally provides confirmed
channel evidence through `ChannelIdentityProvider` and `ChannelPolicy`:

- Present credentials only in `ClientHello.credential` (frame-carrying
  profiles) or the profile-defined binding (`Authorization: Syntra
  <base64>` on HTTP/HTTPS). Never in URLs, IDs, methods, errors, or logs.
- Empty credential = anonymous attempt; acceptance is your policy, bound
  with least privilege.
- On success emit exactly one `ServerReady` with a fresh, unguessable
  `connection_id` (≥128-bit entropy) and bind the principal for the
  connection lifetime. On denial, record the detecting-side typed cause
  (`UNAUTHENTICATED`/`PERMISSION_DENIED`) with generic text. Before `ACTIVE`
  send no error `Frame`: the peer observes only the transport-native close
  signal (RFC 0003 D1/D2).
- Enforce expiry/revocation; re-authentication on the same connection is
  forbidden by default (new handshake instead).

In the delivered SC1 host, `ChannelPolicy` replaces ordinary credential policy
and must independently verify the root credential, current enrollment and
admission before ready. For returning mode it must enforce the intended
same-principal binding; the library does not automatically compare the callback's principal with the
channel principal. An empty credential is passed explicitly, never implicitly
authorized. Nil method `Authorize` denies every method. The asynchronous
confirmed-peer check (1s ticker, 1s lookup context) does not replace admission
checking. See [authentication boundary](sc1-implementation.md#authentication-boundary).

See `docs/server-implementation.md` for the host side and
`docs/client-implementation.md` for the initiator side. Test with
`CONF-SESS-001/002` and `CONF-SEC-004/005`.

## 7. Implement RPC correlation

- Initiator: nonzero `request_id`, strictly increasing in the actual
  serialized request-frame emission order, unique for the whole connection
  and never reused — not even after a terminal `result` (`SNTR-RPC-002`,
  accepted RFC 0004; reusing or reissuing an already-seen ID is an
  ordered-admission violation: the detecting host records local
  `FAILED_PRECONDITION`, sends no result, and closes the connection).
  Correlate each terminal `result` by ID;
  tolerate interleaved `notification`s and out-of-order completion.
  Enforce your timer (≤ requested budget); abandonment without `cancel`
  does not cancel the host.
- Host: validate (method shape, size, `ACTIVE`, authorization) before
  dispatch; return exactly one terminal `result` per request; honor
  best-effort `cancel` (completion wins races); ignore `cancel` for
  unknown/completed IDs.
- Retry only when no terminal `result` arrived AND the operation is
  idempotent or carries an application operation key in the payload — with
  a fresh `request_id` per attempt (`SNTR-REL-003`, `SNTR-RPL-020`).
  Never use `request_id` for cross-connection deduplication.
- Test with `CONF-RPC-*`.

## 8. Implement the chosen transport profile

Implement at least one profile (secure if you claim production use).
Each profile is a thin adapter over the core from step 3–7:

- TCP/TLS-TCP: 4-byte big-endian length prefix + serialized `Frame`;
  strict stream loop; no magic bytes.
- HTTP/HTTPS: `POST /syntra/v1/rpc`, one `Frame` per body, version
  headers, status layering (`200` + envelope = RPC outcome; anything else
  = transport outcome, never a synthesized `result`).
- WS/WSS: `/syntra/v1/ws` Upgrade with `syntra.v1` subprotocol; one
  binary message = one `Frame` (never `[length][protobuf]`); binary only;
  Ping/Pong liveness; close-code mapping.

See `docs/transport-selection.md` for choosing, and the profile spec for
binding details. Test with the matching `CONF-TCP/TLS/HTTP/HTTPS/WS/WSS-*`
manifests plus the shared `test-vectors/` fixtures.

For experimental SC1, high-level `DialTCP`/`DialWebSocket` return after validated
core ready within a 10s total establishment budget, shortened by the caller.
Successful client lifetime is independent of the dial context. `Connect` owns
an established transport even on failure; core `Run`/`Serve` own terminal
transport closure. The server owns raw half-handshake sockets and listeners;
the application also closes its HTTP server and the connection server for WS.

Document separate resource budgets: adapter handshake/write/frame/record
timeouts default/max at 5s; lifetime at most 24h and 2^32 records/direction;
32 pending operations/direction (maximum 1,024). Server admission defaults to
128 connections/16 handshakes (maxima 4,096/256), retaining handshake slots
through ready write. These are concurrent admission limits, not rate limits.

Post-ready host output has one owned FIFO snapshot writer, with queued-plus-active
limits of 256 frames/8 MiB and a 5s default per-send timeout. Saturation is
terminal; dispatch/cancel/deadline work continues during socket stalls.
Method authorization returning `UNAUTHENTICATED` attempts actual-send denial
drain for up to 200ms, with no delivery guarantee. Enrollment-watchdog failure
and principal disconnect close directly. The core's shared 1s callback grace,
the writer's 1s join **after
transport Close**, and the high-level default/max 5s server shutdown budget
are distinct. Uncooperative callbacks cannot be killed; `Lookup`, I/O and
`Close` must honor cancellation, and low-level close may otherwise remain
blocked. See [operational limits](sc1-implementation.md#operational-limits).

## 9. Implement optional events (only if claimed)

Events are never required for Core conformance. If claimed: subscriptions
are generic RPCs returning opaque handles; delivery is `notification`
frames (`request_id == 0`); tolerate duplicates; re-subscribe explicitly
after reconnect; replay/cursors only under a negotiated stream spec.
Mandatory-only hosts correctly refuse subscriptions with `UNIMPLEMENTED`.
Test with `CONF-EVT-*` (`UNSUPPORTED`/`SKIP` where unclaimed). The
recovery boundary is specified in the defining drafts and owned by your
implementation.

## 10. Run the conformance suite

Build a runner over `conformance/manifest/*.yaml` (any language — YAML
parsing is the only requirement): connect, send each case's input, assert
`expected`, and emit one verdict per case (`PASS`, `FAIL`, `SKIP`,
`UNSUPPORTED`, `NOT_EXECUTED`; the last three NEVER count as passes).
Publish an implementation declaration (`conformance/declaration.example.yaml`)
and claim wording per `conformance/claims.md` (e.g., "Conforms to Syntra
Core v1 and WSS/H1 v1"). `PASS` MUST NOT be reported unless executed with
logs. Green on your implementation plus interop proof against a second
implementation (or fixture verification during bootstrap) is the
`GOVERNANCE.md` Sec. 5 stability bar.

The delivered SC1 [verification record](sc1-implementation.md#verification-evidence)
covers local connection orchestration tests and same-implementation Docker
adapter/core RPC tests across TCP/WS/WSS × bootstrap/returning. Containers do
not exercise the high-level connection helpers. Native-core tests still use
the same Go SC1 carriers; neither level establishes independent wire
interoperability or a formal `CONF-*` verdict. In-memory benchmark execution
is report-only, full RPCs are not zero-allocation, and measurements do not
establish deployment performance; see [performance evidence](perf-tradeoffs.md).
