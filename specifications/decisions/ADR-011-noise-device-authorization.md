# ADR-011: Shared secure channel and persistent device authorization

- Status: Accepted (2026-10-29) — accepted with RFC 0007
- Date: 2026-10-27
- Owner: Syntra maintainers (see `GOVERNANCE.md` and `MAINTAINERS.md`)
- Relates to: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md), ADR-003, ADR-004, ADR-008

## Context

Syntra needs a lightweight secure-channel design that is independent of its
carrier and allows an enrolled device to reconnect without repeating
interactive authorization. Persistent authorization does not require
persistent traffic keys or logical-session resumption.

## Decision

Use `Noise_NK_25519_ChaChaPoly_SHA256` for authenticated bootstrap enrollment
and `Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices. Provision a
unique uniformly random 32-byte shared AK per enrollment, plus an opaque
eight-byte lookup handle and a nonzero epoch. Use fresh ephemeral and
directional traffic keys for every new channel.

The accepted v1 carrier profile is `SNTR-SC1-WSS-V1`: canonical
`syntra.sc1.v1` context over verified TLS 1.3 WSS at `/syntra/v1/sc1/ws` with
subprotocol `syntra.sc1.v1`. TCP and plaintext WS mappings remain restricted
development carriers. UDP is deferred. The exact bytes, limits and admission
rules are owned by [RFC 0007 §11](../../rfcs/0007-secure-channel-device-authorization.md#114-accepted-decisions-2026-10-29)
and [noise-bindings.md](../transports/noise-bindings.md).

Keep the core independent of carrier/socket libraries and credential stores.
Application policy owns enrollment, protected storage, generic principal
binding, permissions, expiration, rotation and revocation. No first-flight
application requests or automatic security fallback are part of v1. No new
cipher, custom key schedule or application E2EE is introduced.

## Alternatives considered

- TLS-only policy: remains the baseline for existing profiles; SC1/WSS is an
  additional secure profile, not a replacement.
- Plain NK plus device signatures: not selected; a distinct credential model.
- Reusing traffic keys or symmetric-only reconnect: not selected because it
  increases cross-channel nonce/replay and compromise-recovery responsibilities.
- Supporting multiple alternative suites at launch: not selected; expands
  negotiation, implementation and audit scope without measured need.

## Consequences

The host must protect usable shared authorization secrets. Fresh channel keys
do not prevent stolen-AK device impersonation. Server-key provisioning,
context binding, replay/DoS controls, current-enrollment checks and credential
transitions are required host obligations.

The canonical v1 context is 38–292 bytes; M1 is 86–340 bytes and M2 is 48
bytes, with empty handshake payloads. The inner stream is
`u32BE(F) || Frame`, frames are 1–1,048,576 bytes, record plaintext is
1–65,519 bytes and ciphertext is 17–65,535 bytes with empty AD. A channel is
limited to 24 hours and `2^32` records per direction; renewal is a fresh
handshake followed by explicit recovery negotiation, never an in-place rekey.

The implementation evidence at `tinkle-org/syntra-rs` main (`50ca849`)
implements the reviewed contract at `94404d7` and is recorded in its `SC1.md`,
`AUDIT.md` and `docs/implementation-status.md`. Local unit, race and transport
tests are implementation evidence, not independent vectors, cross-language
interoperability, a formal profile pass or an independent security review.
Host authorization, durable recovery, production FFI and mobile integration
remain implementation work.

## Compatibility implications

Accepted as an additive secure profile. ADR-008's TLS 1.3 requirement remains
for SC1/WSS: the Noise channel is inside verified outer TLS, not a replacement
for it. Existing TLS/TCP, HTTPS and WSS profiles retain their wire formats,
identifiers and claims. Raw SC1 TCP/WS do not become public production
profiles. Mandatory replacement/removal requires an explicit major-version and
deprecation decision.

## Status

Accepted. Independent production security review and the RFC 0009 D5 release
evidence remain separate gates. See
[the acceptance plan](../../conformance/plans/secure-channel.md) and
[RFC 0007 §11.4](../../rfcs/0007-secure-channel-device-authorization.md#114-accepted-decisions-2026-10-29).
