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
context binding, replay/DoS controls, credential transitions and complete
carrier mappings require review. Binary-size/CPU benefits need measurement.
UDP remains deferred pending its complete accepted binding.

## Compatibility implications

This proposal would amend ADR-008's exclusive TLS production policy only
after acceptance and security review. It does not mark ADR-008 superseded
now. Existing TLS/TCP, HTTPS and WSS profiles remain valid and retain their
wire formats/identifiers. New Noise-in-WebSocket framing is a separate binding;
browser outer TLS remains necessary. Mandatory replacement/removal requires
an explicit version/deprecation decision and migration window.

## Status

Proposed. No acceptance, implementation, audit or conformance is implied.
See the RFC blockers and [acceptance plan](../../conformance/plans/secure-channel.md).
