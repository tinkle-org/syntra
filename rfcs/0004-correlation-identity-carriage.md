# RFC 0004: Correlation identity, races, and authentication carriage (accepted)

- RFC: 0004
- Title: Monotonic connection-scoped request IDs, single-terminal races, HTTP independence, and credential carriage
- Status: Accepted (closes audit findings F-02, F-04, F-10, F-13, F-14, F-15 at the specification level)
- Date: 2026-10-28
- Target version: pre-stable v1 contract proposal; explicit freeze/version decision required (§6)
- Relates to: `specifications/core/rpc.md` (§§1B/1F–1I, §4), `framing.md`, `security/replay-protection.md` (SNTR-RPL-012/020/030), `reliability.md` (SNTR-REL-001/003/009), `errors.md` (SNTR-ERR-002/004), `authentication.md` (SNTR-AUTH-010), `sessions.md` (§1B/§1E), `security/authentication-security.md` (SNTR-ASEC-003), HTTP/HTTPS; RFC 0001 B3/B10; RFC 0002 §10 items 3, 6; RFC 0008 queue/suspend proposal
- Author(s): oscarlaw
- Reviewers: oscarlaw (self-review disclosed; sole active maintainer)

> Accepted (2026-10-30, [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md);
> disclosed self-approval per [governance](../GOVERNANCE.md) §3). D1–D5 are
> normative and the owner edits are applied: strictly increasing request IDs
> in emission order with permanent connection-local non-reuse (no reuse after
> completion either), native-close recording of a locally typed cause on
> violation, per-exchange independence for HTTP/HTTPS, the serialized
> deadline-checked terminal gate with `DEADLINE_EXCEEDED` on tie, and
> credentials per profile. Intra-section wording that reads as proposal-only
> is superseded by §10 and the applied owner files; the obligations above are
> not merely proposed. Executed conformance evidence remains a separate
> release gate.

## 1. Summary

Select strictly increasing, nonzero request IDs in persistent-connection
request emission order, with no reuse during the connection lifetime and
constant-size retired-ID tracking. Invalid repeated or non-increasing requests
terminate the connection without ambiguous same-ID errors or duplicate dispatch.
Define one local terminal outcome through a serialized race gate, preserve
HTTP per-exchange independence, and make credential carriage profile-specific.
Queue/suspend integration is proposed here for review with RFC 0008.

## 2. Motivation

The core permits ID reuse after completion while replay security rejects stale
IDs. A time-window cache cannot reject reuse forever, and random-ID tombstones
grow with connection age. An error for a duplicate outstanding ID is itself
ambiguous: the caller cannot distinguish rejection of the duplicate from a
terminal error for the original call.

Cancellation, deadline, completion, output queues, and loss can each attempt to
complete a call. A delayed callback or suspended executor must not publish a
second outcome or dispatch expired queued work. Finally, ASEC-003's current
carrier wording excludes the specified HTTP Authorization binding, and the
sessions table implies a `ServerReady`/`connection_id` absent from HTTP.

## 3. Proposal

All obligations below are proposed acceptance text. The current conflicting
clauses remain unchanged until this RFC is accepted and the owning edits land.

### D1 — Monotonic IDs on persistent connections

For each persistent Syntra connection, the initiator emits `request` frames
with unsigned 64-bit IDs in strictly increasing order, all nonzero. Gaps are
allowed; consecutive numbering and a start at 1 are not required. The ordering
is the actual serialized request-frame emission order, not API-call order,
goroutine/task scheduling, or the order concurrent producers obtained tickets.

- The connection's single logical writer assigns IDs when serializing requests,
  or serializes preassigned IDs so actual request emission is increasing. It
  never lets a producer with a smaller ID emit after a larger one. Results may
  complete in any order.
- `result` and `cancel` echo/reference the original request ID; they do not
  consume a new ID or advance the request high-water mark. A late cancel for
  ID 7 after request 10 is not a non-increasing request violation.
- Allocated/skipped/retired IDs are never reused on that connection, including
  after timeout, cancellation, overload rejection, successful completion, or
  arbitrarily long idle. There is no aging window that makes an old ID fresh.
- There is no wrap at `2^64 - 1`. Before exhaustion the initiator stops
  admitting new requests and drains/closes or opens a fresh connection; zero
  is never a fallback ID. A skipped reservation can exhaust the space too.
- Each new connection has a fresh correlation namespace. The same numeric value
  on another connection does not identify or deduplicate an earlier attempt.
  Retry creates a fresh attempt; application operation keys remain separate.

### D2 — Connection violation for duplicate/reused/non-increasing requests

The host holds a `uint64` high-water mark H, initially zero. After bounded
decode, version/nonzero-ID/state checks and before method authorization or
handler dispatch, request admission is serialized in received-frame order, not
validation-worker completion or mutex-acquisition order. Parallel validation may
prepare results, but cannot admit N=10 before an earlier received valid N=7.
Authorization and handler execution after ordered admission remain concurrent:

1. If N ≤ H, record local `FAILED_PRECONDITION`, dispatch nothing for the
   offending frame, and terminate the connection through the native profile.
2. Otherwise set H = N atomically with request admission. The number is consumed
   even if later method validation, authorization, or concurrency checks reject
   the request. Such ordinary rejections can return one lawful result for N.

This applies whether N names an active, completed, skipped-below-H, or otherwise
retired ID. Zero remains the existing envelope violation, not an RPC context.
Existing raw-wire/size validation still precedes admission; this proposal does
not bypass validation precedence for malformed input.

For N ≤ H the host sends no `RpcResult` under N to explain the violation and no
zero-ID error. It cannot promise that the original RPC continues on a now-failed
connection. Already committed outcomes stay committed; remaining local pending
calls fail under D4's connection-loss rule. The original handler may already
have effects; closure is not rollback. Native peer signals remain generic as
proposed by [RFC 0003](0003-handshake-failure-signaling.md).

Retired-ID rejection requires O(1) state (H), plus the bounded active-call map
and existing bounded output queues: O(maximum active calls + queued bytes), not
O(connection age) or an ever-growing seen-ID set. Terminal entries leave the
active map when committed; a selected response waiting to write occupies only
bounded output resources. No cached outcome or tombstone is needed to reject
an old request. Unknown/completed cancels and unknown/late results are ignored
with bounded diagnostics and no reply storm; neither changes H nor dispatches
work. A result with no active local call cannot resurrect one.

Retiring correlation does not free execution or queued-output capacity while
those resources still exist. Non-interruptible handlers remain charged against
bounded execution capacity after local timeout/cancel; otherwise repeated
abandonment could bypass the active-call cap. RFC 0008 coordinates those
independent queue/execution budgets with this correlation model.

### D3 — HTTP/HTTPS remain per exchange

HTTP, HTTPS/H1, and HTTPS/H2 request-response exchanges are exempt from D1/D2's
persistent high-water rule. Each exchange is an independent logical connection
with one nonzero request ID echoed by its result (SNTR-HTTP-070–073). TCP
keep-alive, pooling, and HTTP/2 multiplexing create no cross-exchange ID memory.
Reusing a number in a different exchange is not a host replay violation;
clients still correlate outstanding exchanges unambiguously and use a fresh
attempt identity for retries. Authentication is evaluated on every exchange.

Acceptance would correct sessions §1B/§1E: headers synthesize the HTTP logical
handshake; no `ServerReady` or `connection_id` is sent on this binding. This
exemption does not authorize recovery/session continuity across HTTP exchanges.

### D4 — Exactly one local terminal outcome and an explicit race gate

Each endpoint owns a per-call Pending → Terminal transition under one serialized
gate. Terminal is irreversible and releases the active entry exactly once.
Handler effects, wire-result emission, and local application notification are
distinct: local timeout/cancel/loss can finish a call without a received result,
and a host result can be selected before it reaches the caller.

At every terminal-candidate gate entry:

1. If Terminal, discard the new completion candidate; never publish a second
   callback, future resolution, result, or replacement code.
2. If Pending and the local absolute effective deadline has been reached
   (`now >= deadline`), commit `DEADLINE_EXCEEDED` before any candidate being
   considered now, even if the timer callback has not run.
3. Otherwise commit the first eligible observed candidate in gate order:
   validated result at the initiator; handler success/error at the host;
   explicit local cancellation or accepted incoming cancel → `CANCELLED`;
   connection loss/shutdown without an already selected outcome → `UNAVAILABLE`.

Thus completion committed before the deadline beats a later cancel/loss/expiry;
completion not yet committed at expiry does not win merely because the handler
finished on another executor. A cancel committed before the deadline wins over
later expiry. A cancel/deadline tie while Pending selects `DEADLINE_EXCEEDED`.
Simultaneous pre-deadline completion/cancel/loss is ordered by gate acquisition,
not callback delivery or wall-clock guesses. The host's completion gate is
before enqueueing its terminal output, not at socket-write completion. The
initiator's result gate is after validation/correlation, before application
callback delivery. Endpoints can therefore legitimately observe different
outcomes (host selected success; initiator deadline/loss won before receipt).

An emitted request gets at most one host terminal result where transport
remains available. The host never sends a second result when its already
selected output stalls or transport fails. The initiator gets exactly one
local terminal outcome even when no result arrives. Neither property promises
exactly-once execution, rollback, or delivery of every selected host result.

### D5 — Profile-specific credentials and re-authentication

Select the following replacement intent for SNTR-ASEC-003:

- Persistent frame-carrying profiles: initial credential bytes only in
  `ClientHello.credential`. WS/WSS Upgrade `Authorization`/`Cookie`, when used
  for documented transport admission, do not establish or merge Syntra identity.
- HTTP/HTTPS request-response profiles: initial credential bytes only through
  `Authorization: Syntra <base64>` for that exchange, or deliberate omission
  for an anonymous attempt. Base64 is a byte-preserving binding, not a second
  credential format or confidentiality mechanism.
- Explicitly documented follow-up authentication RPC payloads after ACTIVE
  remain subject to the owning authentication policy; they do not implicitly
  authorize changing the connection principal or invent mechanism negotiation.
- No credential carriage in URLs, IDs, methods, error text, logs, or event
  metadata. Public deployments still require a permitted secure profile.

A valid post-ACTIVE RPC requesting forbidden same-connection principal change
returns `FAILED_PRECONDITION` under its valid nonzero ID, leaving the binding
intact and the connection usable by default. This does not reserve a new auth
method. A second `hello` is instead a connection state violation: local
`FAILED_PRECONDITION` plus native close, without any zero-ID result. Credential
expiry/revocation and binding withdrawal keep their separate owning policy.

## 4. Detailed design

### Queueing and suspension proposal for coordination with RFC 0008

The selected proposal is an absolute, elapsed-time budget, not a timer that
restarts on dequeue, writer wakeup, or foregrounding. Initiator queue waiting
counts from local call admission; if admission fails there is no accepted call
to dispatch. A bounded client default is needed when `timeout_ms=0` delegates
the host budget. At the writer's atomic queued-to-emitting handoff, check the
same call's terminal/deadline gate and serialize using the remaining positive
millisecond budget (round down); less than one remaining millisecond expires
locally, never encoding zero as an accidental host-default reset. An already
terminal queued call cannot start emission. Serialization occurs at this handoff,
not earlier in an unbounded ready queue. Before handoff, cancel/expiry removes
the item; afterward the partial-write rule applies, without rewriting encoded
bytes. Any reserved ID remains skipped forever on that connection.

The host timestamps complete bounded-frame receipt before worker-queue waiting;
that waiting and validation consume its effective budget. Expired work is not
dispatched. The request's relative `timeout_ms` does not synchronize endpoint
clocks or let the host account for unobserved network transit. This changes the
current send/post-validation timer wording and needs compatibility review.

Suspension counts toward elapsed budgets. On resume, the endpoint checks
elapsed expiry at the gate before processing buffered results, dispatching
queued work, or replaying queued cancels. A result committed before suspension
remains Terminal even if its application callback is delivered after resume.
A result merely buffered/queued before suspension is not a committed terminal
outcome and loses if validated only after expiry. Cancel for an already
emitted request may be sent best effort, but never extends its deadline or
changes a committed local outcome.

RFC 0008 owns the complete queue/suspend contract, queue capacities, clock
semantics, overload admission, write-stall budgets and platform verification.
The text above is synchronized proposed text, not a claim of RFC acceptance.
No unspecified queue may be
treated as an unbounded exception, and no Draft authorizes runtime behavior.

```text
Initiator writer                               Host admission
    |--- request id=7 -------------------------->| H=7; dispatch once
    |--- request id=10 ------------------------->| H=10 (8/9 skipped)
    |<-- result id=10 ---------------------------| completion out of order
    |--- cancel id=7 --------------------------->| reference, H unchanged
    |<-- result id=7 ----------------------------| one host terminal
    |--- request id=7 (invalid reuse) ---------->| no duplicate dispatch
    |<-- native close; no result for violation ---| local FAILED_PRECONDITION
    | pending local calls settle once            |
```

Acceptance would revise SNTR-RPC-002/010/020/021/030/031, SNTR-WIRE-010,
SNTR-RPL-012/020/030 and RPC §4 together, alongside sessions §1B/§1E for D3's
per-exchange semantics, authentication-security SNTR-ASEC-003 and core
authentication SNTR-AUTH-010 for D5's credential carriage and reauthentication
changes. The correlation edits replace both reuse permission and duplicate
same-ID error behavior. Cross-connection numeric equality is harmless;
continuity/idempotency never derives from correlation IDs. Errors §1C would
name the connection-fatal ID violation explicitly. Errors §1D and handshake
examples would continue to prohibit synthetic or zero-ID results.

Errors SNTR-ERR-002 already states that `UNAVAILABLE` is not the only
unknown-execution report. Preserve that correction: timeout, cancellation,
`INTERNAL`, and `UNKNOWN` also do not establish non-execution or rollback.
There is no proposed core operation-ID field or retained-outcome protocol.

## 5. Alternatives considered

1. **Retired-ID window with aged reuse.** Rejected: old late traffic becomes
   ambiguous again after eviction; clocks/windows add state without permanent
   stale rejection. Monotonic requests need only H and active-call state.
2. **Random IDs plus permanent tombstones.** Rejected: retired state grows with
   connection age. A bounded cache cannot prove permanent non-reuse.
3. **Error under the duplicate ID while the original continues.** Rejected:
   the caller cannot correlate that error to a distinct attempt. Connection
   termination is unambiguous and prevents duplicate dispatch.
4. **Require HTTP cross-exchange tracking.** Rejected: contradicts the binding's
   independent exchange semantics and creates ambient session state.
5. **Do nothing / executor callback order alone.** Rejected: leaves reuse
   contradictory and lets overdue completion win merely because a timer was
   delayed by queueing or suspension.

## 6. Compatibility

Unchanged field encodings do not make this a clarification. Existing peers may
reuse completed IDs, emit concurrent IDs out of numeric order, expect a
duplicate-ID RPC error, or measure deadlines from later queue boundaries.
Those behaviors would break under D1/D2/D4 and §4. No post-ACTIVE capability
can retroactively make the baseline correlation model interoperable.

Before acceptance, maintainers must explicitly decide whether this is the
pre-stable v1 contract freeze, inventory downstream behavior, and record
migration/rollout expectations. If an existing frozen contract must remain
supported, incompatible changes need governance §4's major-version designation
and migration plan, including any feasible dual-support window. Do not label
these baseline changes minor-additive merely because schemas are unchanged.

HTTP independence and carrier reconciliation preserve the intended profile
specialization but still need review against deployed behavior. No schema,
reserved number/name, spec requirement, manifest ownership, or generated code
changes occur in this Draft. Accepted follow-ups would update `MIGRATION.md`,
`CHANGELOG.md`, specs, and traces together.

## 7. Security considerations

One high-water mark rejects arbitrarily old connection-local replay without
unbounded memory. It is neither a random authenticator nor cross-connection
deduplication; secure transport, fresh credential evaluation, and application
operation keys remain necessary. Connection-fatal ID violations can terminate
other work, so diagnostics and replay bursts are rate-limited and isolated per
principal/source. Closing cannot undo original handler effects.

Serialized admission prevents duplicate dispatch; one terminal gate prevents
double callbacks from races.
Bounded queues and elapsed deadlines prevent suspension or slow writers from
silently extending work indefinitely. Credentials remain opaque sensitive
bytes under each profile, never a URL or diagnostic channel. A lawful error
requires lawful correlation; ID misuse never licenses a zero-ID error.

## 8. Test plan and acceptance criteria

These are planned tests for accepted follow-ups, not current conformance PASS
claims. No new active requirement or case IDs are introduced by this Draft.

| Existing requirement trace | Planned positive/negative evidence |
|---|---|
| SNTR-RPC-002/010/020/030/900/901, SNTR-WIRE-010, SNTR-RPL-012/030/900 | Increasing nonzero requests with gaps; concurrent producers forced into opposite scheduling order still emit increasing IDs; reversed host validation completion still admits in received order; out-of-order results correlate correctly |
| SNTR-RPC-002/030/901, SNTR-RPL-012/031/900 | Duplicate outstanding, reuse after result/timeout/cancel/long idle, lower skipped ID, and decreasing ID each close with no same-ID rejection result and no duplicate dispatch; original effects are not claimed rolled back |
| SNTR-WIRE-003/005, SNTR-RPC-005/900 | Zero request rejected without zero-ID error; late/duplicate/unknown cancel ignored; cancel/result IDs never advance H; unknown/late result cannot resurrect a retired call |
| SNTR-RPC-002/008/900, SNTR-ASEC-020 | Near-maximum uint64 IDs, no wrap or reuse; long-connection stress verifies constant retired-ID storage plus capped active map/output bytes |
| SNTR-RPC-004/005/021/031/901, SNTR-ERR-002/004, SNTR-REL-003/009 | Gate permutations of completion/cancel/deadline/loss; exact-deadline tie; already-committed result survives delayed callback; host-success/client-timeout divergence; exactly one local outcome and at most one lawful wire result |
| SNTR-RPC-004/008, SNTR-REL-007/008, SNTR-ASEC-021 | Planned RFC 0008 integration: enqueue expiry, writer stall, queued result, suspend/resume, sub-millisecond remaining budget, default budget, overflow; no expired dispatch or timeout reset |
| SNTR-HTTP-070/071/072/073/900, SNTR-RPL-020 | Repeated numeric ID on separate sequential/concurrent HTTP exchanges allowed; no shared high-water state over keep-alive/H2; changed/missing credentials independently evaluated |
| SNTR-ASEC-003/011/900, SNTR-HTTP-060/061/062/900, SNTR-WS-013/050/051, SNTR-WSS-012 | Exact credential-byte carriage per profile, anonymous attempt, no URL/header leakage into WS identity, no secret diagnostics |
| SNTR-AUTH-007/010, SNTR-HS-012/040/900 | Forbidden principal-change RPC gets one nonzero-ID `FAILED_PRECONDITION`; binding intact; second hello closes with no zero-ID result |

- [ ] Align the exact queue/suspend boundaries and fixtures with RFC 0008.
- [ ] Update accepted owning clauses/cases together; do not run old duplicate-ID
  expectations and call them evidence for the proposed connection violation.
- [ ] Record independent interop/packet-fixture evidence per governance §5.
- [ ] Keep schema validation separate; no schema edit is proposed here.

## 9. Drawbacks and risks

A single logical writer adds serialization to request admission, and numeric
IDs reveal request-order information. They already convey correlation and are
not secrets. Connection-fatal misuse interrupts unrelated calls but avoids
ambiguous completion. Strict elapsed budgets can expire buffered results after
suspension; RFC 0008 must make this visible and testable without implying
non-execution or automatic retry safety.

## 10. Decision status and acceptance blockers

| Proposal choice | Selection for review | Approval status |
|---|---|---|
| D1/D2 | Increasing request emission IDs; permanent connection-local non-reuse; native close on violation | Accepted 2026-10-30 |
| D3 | HTTP/HTTPS per-exchange exemption | Accepted 2026-10-30 |
| D4 | Serialized, deadline-checked local terminal gate | Accepted 2026-10-30; clock wording synchronized with RFC 0008 D2 via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md) |
| D5 | Credentials per profile; no implicit principal replacement | Accepted 2026-10-30 |

Acceptance was recorded 2026-10-30 via
[Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)
(disclosed self-approval; sole active maintainer per `GOVERNANCE.md` Sec. 3):
1. Owner/reviewers: oscarlaw (self-review disclosed).
2. Approvals: recorded in Decision 0002; security scope acknowledged
   (RPC/errors/auth carriage); independent security review remains a gate.
3. Freeze: the specification-freeze decision records the version and
   migration disposition for correlation/duplicate/race semantics.
4. Clocks: §4 and RFC 0008 D2 were reconciled into the one controlling
   wording recorded in Decision 0002 (initiator admission start; host
   receipt timestamp; validation/queue time consume the budget; RFC 0004
   owns the terminal gate, RFC 0008 owns queue/suspend; pending calls on a
   violating or lost connection fail `UNAVAILABLE` while the violation
   itself is recorded as a local cause).
5. Owner edits: `rpc.md`, `errors.md`, `sessions.md`, `authentication.md`,
   `replay-protection.md`, `authentication-security.md`, `framing.md`
   applied in the acceptance PR. Executed conformance evidence remains a
   release gate.

## Appendix: References

- [RPC](../specifications/core/rpc.md),
  [framing](../specifications/core/framing.md),
  [errors](../specifications/core/errors.md),
  [reliability](../specifications/core/reliability.md),
  [sessions](../specifications/core/sessions.md).
- [Replay protection](../specifications/security/replay-protection.md),
  [authentication security](../specifications/security/authentication-security.md),
  [HTTP](../specifications/transports/http.md),
  [HTTPS](../specifications/transports/https.md).
- [RFC 0002](0002-auth-session-lifecycle.md),
  [RFC 0003](0003-handshake-failure-signaling.md),
  [RFC 0005](0005-negotiation-bounds-identifiers.md).
