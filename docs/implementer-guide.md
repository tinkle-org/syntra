# Implementer Guide — Build Syntra v1 From Scratch

This guide explains how to build an independent Syntra implementation
using only this repository. It is informative: normative requirements
live in `specifications/` (see `specifications/README.md` for reading
order). Nothing here requires implementation code — only the specs, the
IDL, and the conformance suite.

The sequence below is ordered so each step is testable before the next
begins. After every step, run the corresponding conformance cases; do not
proceed on failing cases.

## 1. Obtain the schema from BSR

Fetch the versioned schema module, not a copy pasted from somewhere else:

- Module: `buf.build/tinklecorp/syntra`, package `syntra.v1`
  (approved module identity — see `docs/schema-registry.md` §1).
- Until publication, the Git tree (`proto/syntra/v1/*.proto`) is the
  distribution point. After publication, pin the exact BSR commit your
  release builds against and record it with your declaration (see
  `docs/schema-registry.md` §§11–12 on pinning and reproducibility).
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
the handshake with `UNIMPLEMENTED`/`FAILED_PRECONDITION` + close
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

The core hands you opaque credential bytes and a policy hook; everything
else is yours:

- Present credentials only in `ClientHello.credential` (frame-carrying
  profiles) or the profile-defined binding (`Authorization: Syntra
  <base64>` on HTTP/HTTPS). Never in URLs, IDs, methods, errors, or logs.
- Empty credential = anonymous attempt; acceptance is your policy, bound
  with least privilege.
- On success emit exactly one `ServerReady` with a fresh, unguessable
  `connection_id` (≥128-bit entropy) and bind the principal for the
  connection lifetime. On denial, fail the handshake with
  `UNAUTHENTICATED`/`PERMISSION_DENIED` and generic text.
- Enforce expiry/revocation; re-authentication on the same connection is
  forbidden by default (new handshake instead).

See `docs/server-implementation.md` for the host side and
`docs/client-implementation.md` for the initiator side. Test with
`CONF-SESS-001/002` and `CONF-SEC-004/005`.

## 7. Implement RPC correlation

- Initiator: nonzero `request_id`, unique among outstanding RPCs on the
  connection (`SNTR-RPC-002`). Correlate each terminal `result` by ID;
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

## 9. Implement optional events (only if claimed)

Events are never required for Core conformance. If claimed: subscriptions
are generic RPCs returning opaque handles; delivery is `notification`
frames (`request_id == 0`); tolerate duplicates; re-subscribe explicitly
after reconnect; replay/cursors only under a negotiated stream spec.
Mandatory-only hosts correctly refuse subscriptions with `UNIMPLEMENTED`.
Test with `CONF-EVT-*` (`UNSUPPORTED`/`SKIP` where unclaimed).

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
