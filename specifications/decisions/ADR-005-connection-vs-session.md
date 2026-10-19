# ADR-005: Connection vs. Logical Session

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 4, 12; `schema/syntra/v1/session.proto`

## Context

Early designs conflated a transport connection with an authenticated
session, implying that `connection_id` could resume state or prove
identity. That conflation risks replay confusion and encourages hosts to
treat a disposable connection token as a credential.

## Decision

Connection and logical session are distinct:

1. A **connection** is a single transport instance that has completed
   `ClientHello` → `ServerReady` (or failed with a typed error). It is
   disposable.
2. `ServerReady.connection_id` is opaque, host-scoped, and diagnostic
   only. It MUST NOT be treated as an authentication session ID and
   MUST NOT grant resumption by itself.
3. A **logical session** (identity, authorization, resumption) belongs to
   the application above Syntra. If a future specification defines
   resumption, it MUST define explicit tokens, lifetimes, replay rules,
   and failure semantics — none are implied by `connection_id`.
4. `request_id == 0` is reserved for notifications not tied to an RPC;
   nonzero IDs correlate exactly one `request`/`cancel` with at most one
   terminal `result`.

## Alternatives considered

- **Connection ID as resumable session.** Rejected: binds transport
  lifetime to auth lifetime, invites fixation/replay, and contradicts
  opaque-credential handling.
- **Implicit resumption on reconnect.** Rejected: hides state-machine
  complexity and makes "at-most-once vs. at-least-once" untestable.
- **No connection identifier at all.** Rejected: operators need a
  correlation handle for logs and conformance traces; opaque ID without
  auth semantics is the minimal safe option.

## Consequences

- Hosts must re-authenticate each connection per policy; clients must
  not cache `connection_id` as a credential.
- Future session/resumption work needs a dedicated RFC with normative
  state machines and negative tests (expired, forked, replayed tokens).

## Compatibility implications

- `connection_id` semantics are frozen: opaque and non-authenticating.
  Giving it auth power would be a breaking change requiring a major
  version.
- Reserved names `resume`/`ack` remain retired so a future resumption
  design cannot silently collide with old bytes.

## Status

Accepted.
