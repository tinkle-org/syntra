# ADR-004: Core vs. Transport vs. Application Boundaries

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 2, 5; ADR-006; ADR-007

## Context

Without sharp boundaries, application concepts (e.g., domain methods,
payload schemas, credential formats) leak into the core, and transport
details leak into application logic. Past iterations reserved generic
names (`event`, `resume`, `ack`) that could be confused with
application replay; those are now permanently retired.

## Decision

Three strict layers:

1. **Core** — owns `Frame`, `ClientHello`/`ServerReady`, `RpcRequest`/
   `RpcResult`, `Cancel`, `Notification`, `RpcError`, version and
   capability logic, correlation, timeouts, and resource bounds. The core
   treats credentials, methods, payloads, and notification bytes as
   opaque. It MUST NOT parse or decrypt application ciphertext.
2. **Transport adapters** — own byte framing, TLS/HTTP/WS bindings, and
   failure mapping. They MUST NOT interpret RPC semantics or application
   state.
3. **Application** — owns method names, payload schemas, credential
   issuance/validation, authorization, and event meaning. It is out of
   scope except for neutral examples (echo, generic key/value,
   generic event subscription).

The core keeps no application business-logic types or methods. Generic
principals, endpoints, identities, opaque payloads, requests, responses,
streams, and events are the only acceptable abstractions.

## Alternatives considered

- **Rich core with typed methods.** Rejected: bakes one application's
  model into every implementation; violates independence requirements
  SYN-ARCH-001/002.
- **Thin core that delegates framing to applications.** Rejected: pushes
  transport complexity to every app and breaks interop.
- **Middleware hooks in the core specification.** Rejected as normative:
  hooks are API design, not wire behavior. Non-normative SDKs MAY offer
  them.

## Consequences

- Core reviews reject domain-specific fields on sight.
- Applications can evolve payload schemas without a Syntra version bump.
- Security review is simpler: the core never sees plaintext application
  semantics.

## Compatibility implications

- Adding a generic core mechanism (e.g., a new `Frame.body` variant)
  is a wire change governed by ADR-009. Adding an application method is
  not a Syntra change at all.
- `reserved 16, 17` and `reserved "event", "resume", "ack"` MUST be
  preserved to avoid resurrecting retired semantics.

## Status

Accepted.
