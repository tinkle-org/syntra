# ADR-011: Shared secure channel and persistent device authorization

- Status: Proposed — pending acceptance of RFC 0007 and security review
- Date: 2026-10-27
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md), ADR-003, ADR-004, ADR-008

## Context

Syntra needs a lightweight secure-channel design that is independent of its
carrier and allows an enrolled device to reconnect without repeating
interactive authorization. Persistent authorization does not require
persistent traffic keys or logical-session resumption.

## Proposed decision

Use `Noise_NK_25519_ChaChaPoly_SHA256` for authenticated bootstrap enrollment
and `Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices. Provision a
unique random 32-byte shared AK per enrollment, plus an opaque lookup handle.
Use fresh ephemeral and directional traffic keys for each new channel.

Keep the core independent of carrier/socket libraries and credential stores.
Define TCP, UDP and WebSocket byte mappings separately. Application policy
owns enrollment, storage, generic principal binding, permissions, expiration,
rotation and revocation. No first-flight application requests or automatic
security fallback are part of v1. No new cipher, custom key schedule or
application E2EE is introduced.

## Alternatives considered

- Current TLS-only policy: remains the production baseline until approval.
- Plain NK plus device signatures: not selected; a distinct credential model.
- Reusing traffic keys or symmetric-only reconnect: not selected because it
  increases cross-channel nonce/replay and compromise-recovery responsibilities.
- Supporting multiple alternative suites at launch: not selected; expands
  negotiation, implementation and audit scope without measured need.

## Consequences

The host must protect usable shared authorization secrets. Fresh channel keys
do not prevent stolen-AK device impersonation. Server-key provisioning,
context binding, replay/DoS controls and credential transitions require review.
The [carrier contract](../transports/noise-bindings.md) now specifies implemented
experimental draft-1 context and TCP/WS/WSS bytes, including exact
`syntra.sc1.draft1` selection. Their acceptance is pending; encoding and adapter
defaults are no longer design TBDs. HTTP/HTTPS request-response is excluded
from SC1 draft-1, with existing profiles unchanged. UDP remains deferred pending
its complete accepted binding.

The [implementation evidence ledger](../../docs/sc1-implementation.md) records
channel, trusted host-policy integration and async-writer delivery, operational
defaults, local unit/race/native-core tests and six same-implementation Docker
groups (TCP/WS/WSS × NK/NKpsk0). In-memory benchmarks are not TLS comparisons
or evidence of binary-size/CPU superiority. No formal SC1 conformance cases or
profiles are registered. Only out-of-band preprovisioning is delivered;
enrollment issuance/storage transactions and rotation flows remain absent.
Independent vectors, cross-implementation interoperability and independent
security review remain open. Host policy owns principal agreement, trusted root
identity and synchronous enrollment checks before readiness; channel
authentication does not perform those checks automatically.

## Compatibility implications

This proposal would amend ADR-008's exclusive TLS production policy only
after acceptance and security review. It does not mark ADR-008 superseded
now. Existing TLS/TCP, HTTPS and WSS profiles remain valid and retain their
wire formats/identifiers. New Noise-in-WebSocket framing is a separate binding;
browser outer TLS remains necessary. Mandatory replacement/removal requires
an explicit version/deprecation decision and migration window.

## Status

Proposed. Scoped implementation and execution evidence is recorded separately;
it does not imply acceptance, an independent audit or full conformance.
See the RFC blockers and [acceptance plan](../../conformance/plans/secure-channel.md).
