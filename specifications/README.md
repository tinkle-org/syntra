# Syntra v1 Specification Index

This is the entry point to the normative specifications. The project
charter (`architecture.md`) defines what Syntra is and is not; the
documents below define how it behaves. Each normative `MUST`/`MUST NOT`
carries a requirement ID (`SNTR-*`, `SYN-ARCH-*`) and links to a
conformance test. In case of conflict, the ownership matrix
(`architecture.md` Sec. 8) decides which document prevails.

All core, transport, and security specifications are **drafts pending
maintainer approval via RFC**. Release-blocking open questions are tracked
in `SESSION-OPEN-QUESTIONS.md` and the RFC set.

## Selected secure-channel proposal

[Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md) proposes
Syntra Secure Channel v1 (SC1): `Noise_NK_25519_ChaChaPoly_SHA256` for
authorized bootstrap enrollment and `Noise_NKpsk0_25519_ChaChaPoly_SHA256`
for returning devices sharing a persistent random 32-byte AK. Every new
channel derives fresh traffic keys. This selected direction is not accepted
production policy, shipping implementation or a conformance claim; current
TLS requirements and existing profile identifiers remain unchanged.

Read the [shared channel](security/secure-channel.md),
[device authorization](security/device-authorization.md),
[carrier mappings](transports/noise-bindings.md),
[proposed ADR-011](decisions/ADR-011-noise-device-authorization.md), and
[acceptance plan](../conformance/plans/secure-channel.md) together. The core
remains independent of sockets and carrier libraries; TCP/UDP/WebSocket are
separate bindings, with UDP still deferred until its complete binding is
accepted. Persistent device authorization does not resume logical sessions.

## Reading order

Read in this order. Each layer assumes the previous one; do not start
with a transport profile or the conformance suite.

1. **Core protocol** — `core/protocol.md`
   Roles, abstractions, and lifecycle: initiator/host, connections,
   sessions, principals, requests, responses, opaque payloads, events,
   capabilities, errors. Defines every term once; all other documents
   reference these definitions.
2. **Serialization** — `core/serialization.md`
   Protobuf binary encoding, unknown-field tolerance, malformed-input
   handling, size and recursion limits. Non-canonical encoding: compare
   decoded fields, never serialized bytes.
3. **Handshake** — `core/handshake.md`
   Six-state machine (`CONNECTED → NEGOTIATING → AUTHENTICATING → ACTIVE →
   CLOSING → CLOSED`), version negotiation, timeouts, close and loss
   handling. Includes the full transition table and ordering rules.
4. **Authentication** — `core/authentication.md`
   Opaque credential carriage, anonymous attempts, success/rejection
   semantics, principal binding, expiry/revocation, re-authentication
   policy. Mechanisms are application-defined; the core defines only
   carriage and result semantics.
5. **Sessions** — `core/sessions.md`
   Connection-bound sessions by default, close/loss/expiry behavior,
   deferred optional resumption, cross-transport rules, HTTP principles,
   termination and timeout tables.
6. **RPC** — `core/rpc.md`
   Method identifiers, `request_id` correlation, opaque payloads,
   deadlines, best-effort cancellation, error propagation, idempotency
   (request ID vs operation key), retry guidance, concurrency.
7. **Events** — `core/events.md`
   Optional host→initiator push: subscription lifecycle via generic RPC,
   ordering scope, delivery guarantees, replay and cursors (all
   capability-gated), backpressure, session-loss behavior.
8. **Reliability** — `core/reliability.md`
   At-most-once default, retry conditions, backpressure, exhaustion,
   connection-loss mapping (`UNAVAILABLE`, outcome unknown), no
   exactly-once claims.
9. **Errors** — `core/errors.md`
   The 17-value `ErrorCode` registry (0–16, including 16 nonzero failure
   codes), code meanings, message hygiene, protocol-error vs RPC-error
   distinction, unknown-code mapping, layering rules.
10. **Transport profile** — `transports/*.md`
    Pick the profile(s) you implement: `tcp.md`, `tls-tcp.md`, `http.md`,
    `https.md`, `websocket.md`, `secure-websocket.md`. Each binds the same
    core to bytes (framing, handshake binding, auth carriage, status/close
    mapping, limits). Transport specs MUST NOT restate core state machines.
11. **Security** — `security/*.md`
    Read alongside everything: `threat-model.md`, `transport-security.md`,
    `authentication-security.md`, `replay-protection.md`,
    `opaque-payloads.md`, plus `test-plan.md`, `review-checklist.md`, and
    `requirements.md`. Security specifications own security requirements
    (`SYN-ARCH-043`); no other document may weaken them.

Then: `core/requirements.md` (requirement index), `core/conformance.md`
(fixture mapping), `core/open-questions.md` (deferred decisions), and the
executable [`conformance/`](../conformance/README.md) suite. Schema
mechanics live in [`schema/`](schema/README.md); design rationale in
[`decisions/`](decisions/README.md); change proposals in [`rfcs/`](../rfcs/README.md).

## Document map

| Area | Documents | Requirement IDs |
|---|---|---|
| Charter + ownership | `architecture.md` | `SYN-ARCH-*` |
| Core behavior | `core/protocol.md`, `serialization.md`, `framing.md`, `handshake.md`, `authentication.md`, `sessions.md`, `rpc.md`, `events.md`, `reliability.md`, `capabilities.md`, `errors.md`, `versioning.md` | `SNTR-CORE/SER/WIRE/HS/AUTH/SESS/RPC/EVENT/REL/CAP/ERR/VER-*` |
| Transports | `transports/tcp.md`, `tls-tcp.md`, `http.md`, `https.md`, `websocket.md`, `secure-websocket.md` | `SNTR-TCP/TLS/HTTP/HTTPS/WS/WSS-*` |
| Security | `security/threat-model.md`, `transport-security.md`, `authentication-security.md`, `replay-protection.md`, `opaque-payloads.md`, `test-plan.md` | `SNTR-TMOD/TSEC/ASEC/RPL/OPQ/STEST-*` |
| Schema | `schema/reference.md`, `generation.md`, `compatibility.md`, `validation.md` + `proto/syntra/v1/*.proto` | references `SNTR-*` |
| Decisions | `decisions/ADR-001`–`ADR-010` | rationale, no new normative force |
| Proposed SC1 security | `security/secure-channel.md`, `device-authorization.md` | `SNTR-SC-*`, `SNTR-DAUTH-*` (Draft RFC 0007 only) |
| Proposed SC1 mappings | `transports/noise-bindings.md` | informative candidates; not registered profiles |
| Proposed decision | `decisions/ADR-011-noise-device-authorization.md` | Proposed, not a supersession of ADR-008 yet |

All specification examples use neutral applications: `echo`, generic
key/value, generic event subscription. No domain-specific concepts appear.
