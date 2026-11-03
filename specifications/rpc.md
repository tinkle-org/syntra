# Syntra 1.0 — RPC

An RPC invokes a method with opaque input and returns one correlated success or
error. This page defines correlation, deadlines, cancellation and delivery
semantics. [Wire format](wire-format.md) defines envelopes and validation;
[connection](connection.md) defines readiness and lifetime; [security](security.md)
defines authorization; [transports](transports.md) defines byte carriage;
[recovery](recovery.md) defines notifications and explicit update recovery.
BCP 14 keywords are normative.

## 1. Requests, payloads, and concurrency

**SNTR-RPC-001** — `RpcRequest.method` MUST be a canonical
`/package.Service/Method`: leading slash, exactly two slashes, non-empty segments,
and printable ASCII excluding spaces and controls. Producers MUST validate before
sending; hosts MUST reject malformed paths with `INVALID_ARGUMENT` before
dispatch. Matching is byte-exact and case-sensitive, without normalization.
The frame bound is the only core method-length limit. Deployments MUST document
additional caps and their `INVALID_ARGUMENT`/`RESOURCE_EXHAUSTED` policy, and
application method/payload versioning. No prefix grants special treatment.

**SNTR-RPC-003** — Payloads MUST remain opaque, bit-exact bytes, including empty
and non-UTF-8 input. Syntra MUST NOT semantically validate, transform, compress
or decrypt them. The [total-frame bound](wire-format.md#1-envelope-and-opaque-bytes)
includes method and wrapper overhead. There is no core content-type field or
payload-format negotiation.

**SNTR-RPC-008** — Peers MUST support at least **16 concurrently outstanding
RPCs per connection**, MUST NOT negotiate below that floor, and MUST document
their maximum. Excess admission MUST return `RESOURCE_EXHAUSTED`. Calls progress
independently; results MAY arrive out of request order.

**SNTR-RPC-030** — Hosts MUST validate readiness, envelope bounds and method
shape before dispatch, dispatch only to the named method, and produce one
terminal result for each lawful call while the connection remains usable.

**SNTR-RPC-032** — Hosts MUST authorize the bound principal for the method
before effects. Missing/invalid authentication uses `UNAUTHENTICATED` and
withdraws the binding; insufficient permission uses `PERMISSION_DENIED` under
[connection authentication rules](connection.md#3-authentication-interface).

```text
Initiator → host: Frame{version=selected, request_id=N,
                       request{method,payload,timeout_ms}}
Host → initiator: Frame{version=selected, request_id=N,
                       result{payload}}
             or: Frame{version=selected, request_id=N,
                       result{error{code,message}}}
Initiator → host: Frame{version=selected, request_id=N, cancel{}} (optional)
```

The cancel may race with the result. Notifications use zero ID and never
complete a call.

## 2. Request identifiers and ordered admission

**SNTR-RPC-002**, **SNTR-RPC-010**, **SNTR-RPC-020** — `Frame.request_id`
MUST be a nonzero unsigned 64-bit, connection-scoped correlation label chosen
by the initiator. Request IDs MUST increase strictly in serialized request-frame
emission order. Gaps are allowed; a start at 1 is not required. Allocated,
skipped and retired IDs MUST NOT be reused, including after timeout, cancellation,
overload or idle time. Results echo the ID; cancels reference it. Neither consumes
a new ID nor advances request ordering. Before exhaustion, stop admission and
drain/close or open a fresh connection; never wrap or use zero. Skipped IDs can
also exhaust the space.

The host tracks a high-water mark H, initially zero. After bounded decode and
version/nonzero-ID/phase checks, but before method validation, authorization or
concurrency checks, requests are admitted in received-frame order:

| Received request ID N | Action |
|---|---|
| N ≤ H | Local `FAILED_PRECONDITION`; no dispatch, no result under N or zero ID; native connection termination |
| N > H | Set H = N as part of admission; later call rejection still consumes N |

The first rule includes completed, retired and skipped-below-H IDs. Other
unfinished calls follow the connection-loss rule. Ordinary method, authorization
or concurrency rejection may return one lawful result under an admitted ID.
Retiring correlation state never permits ID reuse.

Unknown/late results and unknown/completed cancels are ignored with bounded
diagnostics. They neither advance H, revive calls nor cause reply storms.
A new connection has an independent ID space. Equal numbers across connections
identify nothing in common. Application operation keys inside opaque payloads
are separate from request IDs.

## 3. One elapsed deadline and one terminal outcome

**SNTR-RPC-004**, **SNTR-REL-006** — Every RPC MUST have a bounded effective
deadline. `timeout_ms` is a relative millisecond budget, not a wall-clock timestamp;
zero selects the documented bounded host default. An unset local budget selects
the documented bounded initiator default. Deployments MUST document maxima and
whether above-cap budgets are clamped or rejected with `OUT_OF_RANGE` or
`INVALID_ARGUMENT`. Unbounded silent acceptance is forbidden.

1. The initiator's deadline starts at call admission, before readiness waiting
   or output delay. Local admission rejection creates no pending wire RPC.
   Negotiation cannot extend the deadline.
2. Immediately before emission, encode the remaining milliseconds rounded down.
   Less than one millisecond expires locally: never encode zero as an accidental
   host-default reset. An already-terminal call MUST NOT begin emission. Once
   emission begins, its bytes cannot be rewritten; partial output follows §4.
3. The host's deadline starts at complete bounded-frame receipt, before
   validation or execution delay. Once a legal request and its effective timeout
   are established, all time since that receipt counts. Expired work MUST NOT be
   dispatched. Assembly and decoding also have independent bounded limits.
   Neither peer subtracts transit time using synchronized clocks.
4. Suspension counts as elapsed time; wall-clock changes cannot extend budgets.
   On wake, expiry and authorization/channel lifetime are checked before buffered
   results or sends. Unknown elapsed continuity requires failing live operations
   and replacing the connection. Traffic cipher state and monotonic timestamps
   MUST NOT be persisted for cross-process reuse.
5. A terminal selected before suspension stays terminal. Buffered bytes cannot
   win retroactively. Reconnect and recovery use explicit bounded attempts and
   never restart a failed mutation's budget or automatically resend it.

**SNTR-RPC-005** — `Frame{request_id=N, cancel{}}` requests best-effort
interruption of the outstanding call on this connection. It MUST NOT imply
rollback. Cancelling a subscribe RPC cancels that call, not necessarily its
stream. Unknown/completed targets are ignored.

**SNTR-RPC-021** — Initiators SHOULD send cancel when abandoning work and MUST
await or explicitly discard the terminal result under their local timeout.
Abandonment alone does not cancel the host.

**SNTR-RPC-031** — Hosts SHOULD attempt to stop cancelled work and MUST produce
one terminal result while the connection remains usable: completion if it already
won, otherwise `CANCELLED`, subject to deadline precedence.

Each endpoint selects at most one terminal outcome for a call:

- If no outcome is selected and local elapsed time is at or beyond the deadline,
  `DEADLINE_EXCEEDED` wins over any candidate considered then, even if timeout
  processing has been delayed. A cancel/deadline tie therefore selects timeout.
- Before the deadline, competing candidates are resolved in one local order.
  Once selected, an outcome cannot be replaced by cancellation, timeout or loss.
- The host selects after computing the terminal result and before making it
  pending output, not at socket-write completion. The initiator selects after
  result validation and correlation, before application delivery. Delayed output
  or delivery does not change an already-selected outcome.
- Endpoints can observe different outcomes: host-selected success may reach the
  initiator after its deadline or loss. No result, cancellation or close promises
  rollback or exactly-once application effects.

After expiry, the host attempts to stop or disregards remaining work and reports
`DEADLINE_EXCEEDED` unless completion was already selected. Work that cannot be
interrupted may continue; its effects remain unknown to the caller.

## 4. Delivery, retries, and bounded execution

**SNTR-RPC-006** — Each lawful call MUST end with one `RpcResult` selecting
`payload` (including empty) or a defined nonzero error, except when a
connection-level failure prevents a result. An empty frame or carrier close is
not a result. The host MUST NOT send a second result for an ID.

**SNTR-REL-001** — Receipt, record authentication, request decode, execution,
result transmission and peer receipt are distinct observations. Only a correlated
`RpcResult{payload}` establishes application success. Error or loss MUST NOT be
treated as proof of absent effects.

**SNTR-REL-002** — Invocation MUST be at-most-once per connection. Syntra MUST
NOT automatically retry or deduplicate RPCs.

**SNTR-REL-003**, **SNTR-RPC-007** — A retry MUST be an explicit application
decision. Without a received terminal result, retry requires an idempotent
operation or application operation key. A received terminal result requires a
new application decision, never blind automatic replay; `CANCELLED` requires
re-evaluation. Each retry uses a fresh connection-local ID.

**SNTR-REL-004** — Applications needing retry safety MUST carry operation keys
inside opaque payloads and deduplicate above Syntra. Request IDs MUST NOT be
cross-connection operation keys. The application documents key scope, retention,
duplicate/conflict handling and expiry. After retention expires, a repeated key
is a new operation with possible duplicate effects. A retry retains the same
application key where applicable.

**SNTR-REL-009** — Abrupt loss MUST report `UNAVAILABLE` once to unfinished
calls and preserve already-selected outcomes. Execution effects remain unknown;
hosts MUST NOT assume a result sent near loss was observed.

**SNTR-REL-010** — Syntra MUST NOT claim exactly-once delivery or processing.
Any effectively-once behavior depends on the application's idempotency contract.

| Condition | Meaning for an explicit retry decision |
|---|---|
| Loss/no result, deadline, `INTERNAL` or `UNKNOWN` | Effects unknown; require idempotency or an application key |
| `RESOURCE_EXHAUSTED` or transient `UNAVAILABLE` | Conditional retry with bounded jittered backoff; no proof of non-execution |
| `UNAUTHENTICATED` | Recover credentials/authority and establish a fresh connection first |
| `PERMISSION_DENIED` | Authorization change required |
| `CANCELLED` | Re-evaluate before re-issuing |
| Other terminal errors | Correct the cause or make a new application decision |

**SNTR-REL-007** — Hosts MUST bound admitted work and buffered events, with
documented `RESOURCE_EXHAUSTED` admission or stream-specific overflow behavior.
Unbounded accumulation and indefinite blockage of terminal/control progress are
forbidden.

**SNTR-REL-008** — Hosts MUST isolate offending traffic before sacrificing
conformant traffic. Existing calls MUST NOT be terminated to admit new calls
except under documented priority. Bounds failures affect the call unless the
connection itself is exhausted or misbehaving.

**SNTR-REL-020** — Initiators MUST bound retry attempts and use jittered backoff.

**SNTR-REL-021** — Initiators MUST distinguish `UNAVAILABLE` from an application
outcome; overload and loss do not prove non-execution.

**SNTR-REL-030**, **SNTR-REL-031** — Hosts MUST document and enforce count,
byte and time limits for connections, handshakes, calls, execution, buffered
input/output, rates and subscription/recovery state, per principal and in
aggregate. Work surviving timeout, cancellation or connection loss still counts
against execution limits until it stops. Excess lawful work receives
`RESOURCE_EXHAUSTED`; connection-admission exhaustion may reject/close without
inventing a result. Security and carrier ceilings remain binding.

### FIFO output and shutdown

Framed output MUST preserve serialized byte order; independent calls can still
complete out of request order. A call may be removed before emission starts.
After partial emission, finish that unit within its write budget or abort the
connection. Never resend an entire unit onto its emitted prefix. Once a nonce
is consumed, emit that exact ciphertext in order or abort: no splicing,
re-encryption or traffic-key/nonce reuse. A slow event consumer MUST NOT
indefinitely block cancellation, terminal results or recovery confirmations.
[Transports](transports.md) defines carrier output bounds and exhaustion behavior.

Graceful shutdown stops new admission, drains eligible output only until an
absolute cutoff, settles remaining calls once and closes the carrier within
the total shutdown deadline. The cutoff leaves positive bounded time for teardown; if
insufficient time remains, abort rather than continue drain. Immediate close may
skip drain. Already-selected outcomes remain terminal. Close does not prove
delivery or that arbitrary application effects stopped. Security withdrawal
cuts off protected work without waiting for drain. See [connection shutdown](connection.md#5-shutdown-output-and-liveness).

## 5. Error vocabulary

**SNTR-ERR-001**, **SNTR-ERR-002** — [`errors.proto`](../proto/syntra/v1/errors.proto)
defines the error codes. Failure MUST use a defined nonzero code;
`UNSPECIFIED (0)` MUST be rejected as a failure outcome.

| Code | Meaning |
|---|---|
| `CANCELLED (1)` | Cancellation selected the terminal outcome |
| `UNKNOWN (2)` | Unclassified failure; prefer a specific code |
| `INVALID_ARGUMENT (3)` | Malformed envelope, method or input |
| `DEADLINE_EXCEEDED (4)` | Effective call or handshake deadline expired |
| `NOT_FOUND (5)` | Application target/resource missing |
| `ALREADY_EXISTS (6)` | Creation conflict |
| `PERMISSION_DENIED (7)` | Valid identity, insufficient access |
| `RESOURCE_EXHAUSTED (8)` | Size, concurrency, rate or buffering bound reached |
| `FAILED_PRECONDITION (9)` | Phase, binding or confirmation precondition failed |
| `ABORTED (10)` | Concurrency conflict or aborted sequence |
| `OUT_OF_RANGE (11)` | Value outside supported range |
| `UNIMPLEMENTED (12)` | Unknown method/body or unsupported behavior/version |
| `INTERNAL (13)` | Internal failure with generic public message |
| `UNAVAILABLE (14)` | Loss, shutdown or transient unavailability; effects unknown |
| `DATA_LOSS (15)` | Unrecoverable corruption/loss detected |
| `UNAUTHENTICATED (16)` | Required credential missing, invalid, expired or revoked |

**SNTR-ERR-003**, **SNTR-ERR-020**, **SNTR-ERR-021** — Hosts MUST choose the
most specific applicable code, document application mappings and sanitize the
public UTF-8 `message`. It MUST NOT contain credentials/tokens, secret identifiers,
principal enumerations, paths, SQL, stack traces, backend diagnostics or raw
untrusted bytes. The maximum is **4,096 UTF-8 encoded bytes**, within the total
frame bound. Producers MUST enforce it; local truncation respects UTF-8
boundaries. Receivers MUST reject oversize. Smaller carrier diagnostic limits
still apply. `RpcError` has only code/message: errors MUST NOT carry bulk data,
structured details or retry-after metadata. Private operational detail stays
local; authentication/authorization disclosure follows [security](security.md).

**SNTR-ERR-005**, **SNTR-ERR-010**, **SNTR-ERR-011** — Unknown numeric error
codes MUST map to `UNKNOWN` for application reporting, retaining the number in
diagnostics where possible. They MUST NOT cause a crash or success. Initiators
MUST branch on code, not message text, distinguish outcome-unknown loss from
application results and avoid displaying/logging unsafe peer text verbatim.

**SNTR-ERR-006** — An error code MUST NOT be treated as proof of idempotency.
Retry rules are in §4; message text is not a versioned interface.

**SNTR-ERR-004** — Each lawful RPC context MUST end once. Connection-fatal
failures produce a typed local cause and native close, with no invented
pre-active error frame, zero-ID result, error-bearing ready, second hello or error
notification. The peer reports only the evidence received. Malformed envelopes
follow [wire validation precedence](wire-format.md#2-bounded-raw-validation-and-first-error-precedence).
Malformed/unknown methods are call errors that leave the connection usable;
non-increasing request IDs close under §2. Binding withdrawal closes under
[connection](connection.md#3-authentication-interface). Missing result outcome,
zero failure code or invalid error-string UTF-8 is `INVALID_ARGUMENT` where a
lawful context exists, otherwise closure. Invalid input MUST NOT cause unbounded
error replies.

## 6. Optional capability negotiation

**SNTR-CAP-001** — The update-recovery capability MUST use the exact identifier
`syntra.update-recovery/1` and the methods/payloads in [recovery](recovery.md).
Capability identifiers are stable, versioned ASCII; ambiguous or unversioned
identifiers MUST be rejected.

**SNTR-CAP-002**, **SNTR-CAP-010**, **SNTR-CAP-011** — Capability negotiation MUST
be explicit through the capability's ordinary RPC after readiness. Only negotiation
is permitted before capability confirmation. Peers MUST NOT assume support, probe
with optional frames, invoke unconfirmed operations or require unnegotiated
options. Partial acceptance retains mandatory behavior and previously confirmed
options under the capability's rules. There is no generic capability enumeration,
hello list or advertisement. Negotiation MUST NOT lower a core floor or silently
escape a core limit.

**SNTR-CAP-003**, **SNTR-CAP-004** — Mandatory interoperability MUST NOT depend
on optional behavior. Hello/ready carries no capability terms, and optional state
MUST NOT cause handshake failure. Unknown capability operations, versions and fields
follow the capability's post-ready rules.

**SNTR-CAP-005** — Optional capability behavior MUST preserve mandatory connection
phases, envelope validation and error meanings.

**SNTR-CAP-020**, **SNTR-CAP-021** — Hosts MUST document supported capabilities and
confirm only supported behavior for this principal and connection, applying the
capability's operation/version/field rules. Confirmation MUST be integrity-protected
and MUST NOT transfer to another connection, resume a session, authorize another
principal or weaken authentication, bounds or security.
