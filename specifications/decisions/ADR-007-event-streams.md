# ADR-007: Optional Generic Event Streams

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 4, 12; ADR-004; ADR-006

## Context

Some hosts need to push data (e.g., generic topic updates) after the
handshake. Making streams mandatory would burden simple request/response
hosts; leaving them undefined would fragment push mechanisms per
application.

## Decision

A single OPTIONAL push primitive:

1. `Notification{payload}` carries opaque host-authorized bytes with no
   delivery or durable-state semantics. No acknowledgment, ordering, or
   persistence is implied.
2. Notifications are valid only after `ServerReady` on an authenticated
   connection. Hosts MUST NOT send them before readiness; initiators
   MUST ignore-or-reject (per the forthcoming stream spec) pre-ready
   notifications without affecting the handshake.
3. `request_id == 0` marks notifications as uncorrelated. They MUST NOT
   complete an RPC.
4. Streams are negotiated as an optional capability. Hosts that do not
   implement them MUST reject stream-setup attempts with
   `UNIMPLEMENTED`; initiators MUST NOT assume subscription success.
5. At-most-once is the default. Any stronger guarantee (replay, resume,
   ordering) REQUIRES a future specification and explicit negotiation.

## Alternatives considered

- **Mandatory streams.** Rejected: overkill for echo/key-value hosts and
  complicates minimal conformance.
- **General pub/sub with topics/QoS in the core.** Rejected for v1:
  bakes broker semantics into every implementation. Applications MAY
  build topics/QoS above `Notification`.
- **Reusing `RpcResult` for pushes.** Rejected: breaks the "exactly one
  terminal result per request" invariant and confuses correlation.

## Consequences

- Minimal hosts can pass conformance without streams.
- Stream tests use generic subscriptions, never domain topics.

## Compatibility implications

- `Notification` field layout is frozen. Stream extensions (sequence
  numbers, resume tokens) MUST use new fields/methods via RFC and MUST
  remain optional.
- Former `event` (field 16/17) stays `reserved` and MUST NOT be revived.

## Status

Accepted. Detailed stream lifecycle and recovery will be specified in a
forthcoming `specifications/streams.md` via RFC.
