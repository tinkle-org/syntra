# ADR-003: Transport-Independent Protocol Core

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 5, 9; ADR-004; ADR-008

## Accepted direction

[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
preserves this separation while preserving a carrier-independent Noise
secure channel below Syntra frames. TCP, UDP and WebSocket byte mappings
remain separate; protocol state does not dial sockets or require a carrier
library. This is not current UDP support or an accepted policy amendment.

## Context

Syntra must run over TCP, TLS 1.3/TCP, HTTP/1.1, HTTPS (HTTP/1.1 and
HTTP/2), and WebSocket (plain and secure) over HTTP/1.1, with future
transports (QUIC, HTTP/3, etc.) explicitly deferred. Coupling the core
to sockets would duplicate logic per transport and invite subtle
divergence.

## Decision

The protocol core is transport-independent:

1. The core defines `Frame`, handshake, RPC, cancellation, errors, and
   optional notifications without reference to sockets, TLS, or HTTP.
2. Each transport has a thin adapter specification mapping `Frame` to
   bytes (length prefixes, HTTP bindings, WebSocket messages) and
   mapping transport failures to `RpcError` codes.
3. Protobuf encoding and transport framing evolve independently
   (SYN-ARCH-012).

## Alternatives considered

- **Per-transport protocol variants.** Rejected: multiplies conformance
  surface and breaks the "one core, many adapters" guarantee.
- **TCP-only core with tunneling for the rest.** Rejected: hides HTTP
  and WebSocket constraints (proxies, intermediaries, message limits)
  and complicates deployment profiles.
- **Abstract transport API in core code.** Rejected as normative: APIs
  are language-specific; the standard defines behavior and byte
  mappings, not class hierarchies.

## Consequences

- Core specifications stay small and testable with in-memory fixtures.
- Transport specifications can be added (via RFC) without touching core
  state machines.
- Conformance needs both core tests and per-transport framing tests.

## Compatibility implications

- New transports are minor additions if they reuse `Frame` unchanged;
  any `Frame` change for a transport REQUIRES a major-version RFC.
- Adapters MUST NOT alter `Frame` semantics to fit a transport.

## Status

Accepted.
