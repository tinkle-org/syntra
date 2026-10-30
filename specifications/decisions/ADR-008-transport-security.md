# ADR-008: Transport Security Policy

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 7, 9; `SECURITY.md`

Amendment accepted 2026-10-29: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
and [ADR-011](ADR-011-noise-device-authorization.md) add
`SNTR-SC1-WSS-V1`, a transport-independent Noise channel with persistent shared
device authorization, as an additional secure profile. The amendment does not
remove TLS 1.3: SC1/WSS runs inside verified outer TLS. Existing profile
identifiers, wire formats and claims are unchanged.

## Context

Syntra carries opaque credentials and application bytes that may be
sensitive. It must be usable in restricted development environments
(without TLS) while forbidding insecure use in public production.

## Decision

1. **Production-capable (public use):** TLS 1.3 over TCP, HTTPS via
   HTTP/1.1, HTTPS via HTTP/2, Secure WebSocket over HTTP/1.1, and
   `SNTR-SC1-WSS-V1` (Noise SC1 inside verified TLS 1.3 WSS). These
   MUST use established TLS implementations; custom algorithms,
   ratchets, and ciphers are forbidden. SC1/WSS requires the separately
   provisioned Noise server pin in addition to TLS validation.
2. **Restricted development only:** plain TCP, plain HTTP/1.1, plain
   WebSocket over HTTP/1.1. These MUST NOT be used for public production
   traffic and MUST be clearly labeled in docs and configs.
3. `ClientHello.credential` is opaque sensitive bytes: transmitted only
   over secure transports in production; never logged, persisted, or
   interpreted by the core.
4. Hosts MUST authenticate before protected operations
   (`UNAUTHENTICATED`/`PERMISSION_DENIED` without leaking diagnostics).
   `RpcError.message` MUST NOT contain credentials or private backend
   details.
5. Implementations MUST enforce bounded buffers, concurrent-RPC caps,
   handshake and call timeouts, and deterministic cancellation. Panics
   on untrusted input and unbounded allocation are forbidden.
6. Transport receipt proves nothing about application processing.

## Alternatives considered

- **Allow insecure transports in production with a warning.** Rejected:
  warnings do not survive deployment automation; the standard must
  forbid it normatively.
- **Define application encryption in Syntra.** Rejected: violates the
  "no application-level encryption protocol" constraint; apps MAY
  encrypt above Syntra with vetted libraries.
- **Mandate mutual TLS for all hosts.** Rejected for v1: over-constrains
  generic use. Hosts MAY require mTLS per policy; the standard defines
  the opaque-credential interface, not the credential type.

## Consequences

- Conformance includes negative security tests (credential over
  insecure transport rejected/warned, unauthenticated access denied,
  oversized frames rejected).
- Development tooling defaults to secure profiles or prints explicit
  insecure-mode warnings.

## Compatibility implications

- Adding a new secure transport is a minor RFC if `Frame` is unchanged.
  SC1/WSS was added on that basis; it does not replace or weaken the
  existing TLS profiles. Downgrading a secure profile to insecure is a
  breaking change.
- Deferred profiles (Raw UDP, DTLS, QUIC, HTTP/3, QUIC DATAGRAM,
  WS-over-H2 Extended CONNECT) MUST NOT be claimed as supported.

## Status

Accepted.
