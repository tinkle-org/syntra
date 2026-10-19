# ADR-006: Generic RPC Design

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 4, 12; ADR-004

## Context

Syntra needs request/response semantics without standardizing any
application's methods. The design must support correlation, bounded
budgets, cancellation, and typed failures while staying agnostic to
payload schemas.

## Decision

Generic RPC over `Frame`:

1. `RpcRequest{method, payload, timeout_ms}` where `method` is a
   canonical `/package.Service/Method` path and `payload` is opaque
   bytes (arbitrary bytes are valid). `timeout_ms == 0` selects the
   host default; otherwise it bounds the call budget.
2. `RpcResult` carries exactly one `oneof outcome`: `payload` (empty
   bytes explicitly mean success) or `error{RpcError}` with a known
   nonzero `ErrorCode`.
3. Correlation by `request_id` (nonzero, initiator-chosen). At most one
   terminal `result` per `request_id`. Notifications MAY interleave
   before `result` but MUST NOT be mistaken for completion.
4. `Cancel{}` targets its envelope's `request_id`. It requests
   cancellation (best-effort); it does not roll back a committed
   mutation.
5. `method` paths and `ErrorCode` values are the only shared vocabularies;
   payload schemas belong to the application.

## Alternatives considered

- **Streaming RPC in the core.** Rejected for v1 core: adds flow-control
  and ordering complexity. Optional event streams (ADR-007) cover
  host-to-initiator push; bidirectional streaming needs an RFC.
- **Application-typed errors in the core.** Rejected: the core carries
  17 generic codes only; richer semantics belong in opaque payloads.
- **Implicit timeouts / unbounded calls.** Rejected: violates bounded-
  resource goals and makes conformance untestable.

## Consequences

- Hosts dispatch on `method` without core help; conformance tests use
  neutral `echo` and key/value fixtures.
- Clients implement per-call timers, idempotency keys (at the app layer
  if needed), and `cancel` handling.

## Compatibility implications

- `RpcRequest`/`RpcResult` field numbers and `ErrorCode` values are
  frozen. New codes or fields REQUIRE an RFC; unknown codes on the wire
  MUST be handled per the error specification (map to UNKNOWN, never
  crash).
- `Cancel` remains empty; adding fields would be a wire change.

## Status

Accepted.
