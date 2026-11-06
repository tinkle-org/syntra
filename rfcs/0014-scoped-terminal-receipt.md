# RFC 0014: Scoped terminal receipt and authorization retirement

- RFC: 0014
- Title: Scoped terminal receipt and authorization retirement
- Author(s): Syntra contributors
- Status: Draft
- Date: 2026-11-05
- Target version: Optional pre-release behavior; compatibility disposition pending review
- Relates to: [connection](../specifications/connection.md), [RPC](../specifications/rpc.md), [security](../specifications/security.md), [transports](../specifications/transports.md), [RFC process](README.md), [Go issue 17](https://github.com/tinkle-org/syntra-go/issues/17)
- Reviewers: Protocol maintainer and human security reviewer unassigned
- Acceptance: Not requested or recorded; implementation and publication remain gated

## 1. Summary

This proposal separates application authorization withdrawal from the final
retirement of an established encrypted connection. An explicitly authorized,
already-admitted request may reserve one bounded, non-sensitive success result
before its application-owned durable transition. The connection stops ordinary
admission and output before that transition. Only authoritative evidence that
this exact operation owns the committed transition can permit its reserved
result; the connection then closes and its cryptographic state is retired.

The application owns session policy, account state, durable transactions and
receipt meaning. Syntra owns request correlation, output fencing, encryption,
deadlines, and shutdown. This proposal does not define an account service,
logout method, database, persistence format or new key-destruction wire method.

This document is a proposal, not protocol authority. BCP 14 keywords describe
proposed obligations only. Labels beginning `R14-` and `R14-T` are local to
this draft, not registered requirements or conformance cases. The draft changes
no current specifications, schemas, compatibility inputs or SDK behavior. Public
acceptance and security review under the [RFC lifecycle](README.md#lifecycle)
are prerequisites to activating the proposed exception. Passing document
validation or model tests cannot establish acceptance or implementation support.

## 2. Motivation

An application operation may durably withdraw the authority supporting its own
request. Returning a successful handler result does not prove result delivery:
the host's writer, receive path or authority supervisor may observe withdrawal
first and close. A caller may therefore observe an unknown outcome even though
the operation committed. Current fail-closed behavior is correct under the
existing connection and security rules.

Ordinary external revocation is different. When one authorized connection
revokes another, the requester can receive its result on its unaffected
connection. The revoked peer's acknowledgement is not a prerequisite to
withdrawal. Account-wide withdrawal that includes the requesting connection
has the same terminal-result problem as any other self-withdrawing operation.

An ordinary graceful drain does not solve this problem. It permits unrelated
eligible output and cannot override current-authority checks. Conversely, a
blanket post-withdrawal grace period could leak queued protected results or
permit new effects. The exception needs narrower ownership than the principal,
method name or connection alone.

The motivating [Go issue](https://github.com/tinkle-org/syntra-go/issues/17)
records a Go responder and Rust caller. It is not evidence of a Rust server
implementation, durable application storage or guaranteed delivery. The
reference at `729bc87` and both existing SDK withdrawal paths remain the baseline
for this proposal; no production defect or security vulnerability is asserted.

## 3. Proposal

### 3.1 Layered terminal transition

The preferred design is a layered terminal transition: the application denies
ordinary use through a durable authority transition, while the SDK retains
only enough connection-local cryptographic state to attempt one predeclared
result. Retaining that state does not keep the application session active.
Fresh connections and other affected connections cannot inherit the exception.

This supports applications that withdraw application authority and retire key
material separately, and applications that atomically revoke their enrollment
and application session. Both require the same explicit terminal-only authority;
leaving a key available alone cannot override application withdrawal.

There is no client-driven second phase that must complete to make revocation
effective. A client disappearing, refusing an acknowledgement or failing to
clear its storage cannot postpone the durable authority transition. The SDK
does not acquire permission to restore authority or generate replacement keys.

### 3.2 Scope and defaults

**R14-01 (explicit opt-in; host).** The terminal-result operation MUST be
disabled by default. A host enabling it MUST provide compatible runtime,
driver and authoritative-transition adapters and explicit method policy.
Unsupported configurations MUST fail reservation before starting the mutation.
Missing support MUST NOT fall back to ordinary sending or graceful draining.

**R14-02 (request ownership; host).** Reservation MUST be available only to an
authenticated, method-authorized, still-pending request. The SDK MUST privately
bind it to the actual connection generation, call ownership, request ID,
principal, scope, enrollment binding and application operation. Diagnostic
connection IDs, peer-supplied values and public request IDs alone MUST NOT
construct or transfer this permission. A connection permits at most one
reservation; repeated attempts MUST NOT renew its deadline.

Bootstrap participation alone is insufficient. An application may independently
authorize receipt reconciliation over a separate connection, but that is an
application contract outside this proposal.

### 3.3 Connection sequence

```text
Initiator                     Host runtime/driver              Application authority
    | request -------------------->| authorize method and current binding |
    |                              | reserve exact result; fence         |
    |                              | reach full outbound-frame boundary  |
    |                              | conditional durable transition ---->|
    |                              |<----- exact ownership evidence ------|
    |                              | select once; final authority gate    |
    |<----- one correlated result -|                                     |
    |                              | close; retire state; retain cleanup |
    | outcome unknown on loss      |                                     |
```

The authority transition is not atomic with carrier I/O. A response can be
lost after commit. A new connection authenticates afresh and cannot replay the
reserved result or carry the old reservation.

### 3.4 Proposed owner edits after acceptance

| Owner | Proposed change |
|---|---|
| `specifications/connection.md` | Define the opt-in terminal-only substate and narrow exception to unfinished-call withdrawal; preserve ordinary withdrawal |
| `specifications/rpc.md` | Define reservation, first-terminal selection, exact-result delivery eligibility and unknown outcomes |
| `specifications/security.md` | Define owned-transition evidence, competing denial, freshness, connection isolation and retention limits |
| `specifications/transports.md` | Define writer barriers, terminal-only handoff, output budgets and abort behavior |
| Conformance requirements and manifests | Register accepted IDs and role-specific positive/negative cases only after acceptance |
| `MIGRATION.md` and `CHANGELOG.md` | Record reviewed compatibility disposition and behavior actually activated |
| SDK design and input records | Reconcile APIs and reviewed input provenance with the accepted revision |

No `.proto` diff is proposed. Existing envelope version, fields, reservations,
RPC result correlation, carrier identifiers and cryptographic context remain
unchanged. No capability name or new error code is allocated by this draft.

## 4. Detailed design

### 4.1 Authority evidence and causality

**R14-03 (durable ownership; application adapter and host).** The adapter MUST
provide evidence that the reserved operation conditionally committed the exact
terminal transition from the expected active authority revision. It MUST bind
the transition to the SDK-created reservation, operation and authorization
binding, and to all application conditions represented by the fixed receipt.
An unconditional revoke, a callback returning success, or an already-withdrawn
row MUST NOT grant ownership to a later operation.

The authority abstraction does not prescribe a database. A conditional durable
transaction recording an operation owner and authority revision is one possible
implementation. The SDK trusts a correctly configured in-process adapter; it
cannot prove persistence guarantees from a callback's return value. A toy
authority fixture establishes only the behavior of that fixture.

**R14-04 (classified observation; host and adapter).** Writer, receive and
supervision gates MUST share one terminal-operation coordinator and distinguish
the following authoritative observations without exposing their private details
on the wire:

| Observation | Behavior after reservation |
|---|---|
| Expected binding still active | Keep ordinary traffic fenced; do not emit success |
| Exact owned transition committed, receipt conditions met, no superseding denial | Eligible for one reserved result within its original budget |
| External withdrawal, owner/revision mismatch, expiry or superseding hard denial | Abort; no terminal-result exception |
| Store error, timeout, stale evidence or unresolved cause | Fail closed; no terminal-result exception |

The durable ownership record MUST bridge the interval between commit and
callback completion: a supervisor observing the transition first must be able
to classify that same committed operation. A generic lookup error MUST NOT be
converted to an owned transition. Prior sticky failures MUST NOT be cleared by
late callback success or delayed validity reads.

**R14-05 (competing denial; adapter and host).** External hard withdrawal visible
to the required authoritative observation, or already observed locally before
the serialized carrier handoff, MUST invalidate receipt eligibility. An otherwise
idempotent external revoke must advance a denial revision or provide equivalent
evidence when it supersedes an owned transition. A permanent first-owner
tombstone alone MUST NOT imply the absence of a later denial. Changes after
the last authoritative observation may race the first handoff as well as later
bytes, under R14-11; later observed denial MUST abort remaining I/O. Every other
affected connection MUST use ordinary withdrawal without inheriting permission.

This explicitly rejects an impossible inference: a local mutex cannot determine
which independent database writer caused an invalidity result. Deployments
unable to provide operation-aware evidence cannot enable this operation safely.

### 4.2 Reservation and writer barrier

**R14-06 (pre-mutation fence; host and driver).** Before allowing the application
transition to start, reservation MUST stop new protected admission and ordinary
egress on that connection, suppress unstarted ordinary output, reserve bounded
writer/result capacity and establish a complete outbound-frame boundary.
Sibling calls and subscriptions MUST lose delivery eligibility; cancellation
does not imply their effects stopped. Failure to establish the boundary within
budget MUST close without starting the terminal mutation.

The fence covers runtime queues, notifications, recovery, selected replies and
driver-buffered output. Any independent ingress checks or authority supervisors
owned by an embedder must coordinate through the same contract. Driver support
alone cannot stop an embedder from closing the socket independently.

**R14-07 (irreversible stream; driver).** A partially emitted ordinary frame
MUST finish within the pre-mutation budget or force abort. It MUST NOT be
dropped and followed by a receipt. Once encryption consumes a nonce, the exact
ciphertext MUST finish in order or the connection MUST abort; implementations
MUST NOT splice frames, skip nonces, re-encrypt replacements or restart an
entire partially emitted unit. These rules also apply to a partial receipt.

Quiescence is pre-mutation. It is not permission to finish unrelated protected
output after withdrawal merely to reach a receipt in the FIFO. A hard denial
during quiescence aborts instead of completing ordinary output under the
exception. Inbound protected requests are never dispatched after the fence;
malformed/authentication failures and carrier loss retain terminal precedence.

### 4.3 Fixed result and resource bounds

**R14-08 (one fixed result; host).** The reservation MUST copy and validate a
predeclared non-sensitive success payload before mutation. Only its existing
correlated `RpcResult` may become eligible after the exact owned commit.
The complete serialized `Frame` MUST be at most 1,024 bytes, excluding the
four-byte inner length prefix. The limit cannot be raised by configuration.
The result MUST NOT carry credentials, key material, recovered protected data,
unrelated state, notifications or another call's output.

**R14-09 (absolute budget; host and driver).** The final deadline MUST be the
earlier of the initiating request deadline and five seconds after reservation
begins. The final quarter of that initial remaining budget, capped at 250 ms,
MUST be reserved for teardown. Quiescence, authority I/O, application completion,
selection and result writing MUST finish before that teardown tail. Insufficient
clock resolution or remaining budget MUST reject reservation before mutation.
Deadlines MUST NOT be extended by retries, progress, repeated callers or adapter
callbacks. Earlier security, channel-age and record limits remain binding.

The same budgets apply if the receipt spans multiple records. Carrier packet
fragmentation is not an additional permission. Applications may configure
stricter limits. Clocks must preserve conservative elapsed/deadline semantics;
detected discontinuity closes instead of buying more time. The SDK must account
for application work surviving its budget without postponing carrier closure.

### 4.4 State, selection and handoff

| State | Allowed work | Exit |
|---|---|---|
| `ACTIVE` | Ordinary current-authority policy | Valid reserve or ordinary withdrawal |
| `RESERVED/FENCED` | Bounded barrier and exact operation; no ordinary admission/egress | Exact owned commit or abort |
| `OWNED_COMMIT` | Validate durable receipt conditions and terminal selection | Select once or abort |
| `RECEIPT_ONLY` | Only the selected result's ordered record sequence | Completion, deadline or hard failure |
| `CLOSED` | Retained cleanup/accounting only | No reopen or transfer |

These labels are proposed host-local substates, not new wire connection-state
values. Any failure after reservation follows an irreversible terminal path;
failed operations do not resume ordinary service on that connection.

**R14-10 (first terminal; runtime).** Reservation MUST NOT select success.
Existing first-terminal and deadline precedence MUST remain intact. A prior
cancellation, timeout, withdrawal or selected result MUST NOT be replaced by
the reserved success, even if the durable operation subsequently commits.
Suppressing output eligibility does not rewrite an already-selected outcome.
Cancellation of an already-selected or completed call MUST follow the existing
ignore rule; it does not become a new terminal outcome or abort trigger.
Hard denial, output deadline and carrier failure still defeat delivery
independently of request-cancellation selection.

**R14-11 (one-use handoff; driver and authority adapter).** Receipt eligibility
MUST be consumed once, at the final validated handoff to the sole carrier writer,
bound to the exact result and original connection. The handoff MUST use a fresh,
operation-aware authority observation; cached generic validity alone is
insufficient. Checks and blocked-I/O repolls MUST keep external denial, unknown
authority, deadline and hard transport failures fail-closed. A local lock MUST
NOT be held across an application transaction or unbounded authority I/O.

The observation-to-I/O interval is not a distributed atomic transaction. The
adapter must declare its freshness/read/close bounds within existing security
limits. A superseding event after the last observation may race bytes already
handed to the carrier; those bytes cannot be recalled. This proposal promises
neither instantaneous distributed cutoff nor rollback of already-emitted bytes.
If atomic remote permission consumption is required, an application adapter
needs a stronger coordinated authority contract, not a longer cached allow.

### 4.5 Cancellation, retained ownership and observation

**R14-12 (retained owner; runtime).** Reservation MUST install one SDK-owned
cleanup continuation before starting application work that may outlive the
initiating handler. Dropping a waiter MUST NOT abandon close responsibility,
restart its budget, or permit late output. An initiating handler MUST NOT wait
for an output action that depends on that handler returning. Surviving effects
MUST retain their actual execution accounting until they stop.

**R14-13 (outcomes; both roles).** A selected result, queue admission, completed
local write, client receipt, durable client storage and joined closure MUST be
reported as different facts. Loss or timeout MUST NOT imply operation rollback,
authorize automatic replay, or be synthesized into success. Receipt delivery
does not prove that the same connection's cleanup already joined. Clients MUST
continue to correlate and validate the ordinary result and treat loss as an
unknown outcome unless independently authorized reconciliation resolves it.

An optional local completion observer may report result write completion and
cleanup status separately. It does not add a peer acknowledgement. A durable
operation-status service, protected-store clearing and application-specific
reconciliation remain application responsibilities.

### 4.6 Language adapters

The Go runtime can supply a private request handle through the handler context,
with optional transport coordination forwarded through ownership wrappers.
The Rust runtime can supply an additive handler-context hook and carry trusted
output metadata through the native pump. Names and signatures require SDK API
review; none is defined by this RFC or available in the current SDKs.

The core remains portable. Record adapters may inherit support only when they
participate in the entire fence/observation/handoff contract. Raw frame drivers,
foreign-function embedders and custom byte pumps must explicitly implement it
or fail reservation before mutation. Carrier support never activates an
otherwise unaccepted carrier or weakens encryption and trust policy.

## 5. Alternatives considered

### 5.1 Keep current withdrawal behavior

Preserves the smallest security surface. Local sign-out can still complete,
while remote effects remain unknown on lost responses. This remains the
default and is the only available behavior until this proposal is accepted
and implemented. Its drawback is the healthy-path terminal receipt conflict.

### 5.2 Application withdrawal followed by a new key-retirement wire exchange

Separates application policy from key disposal, but requires a new service
operation, client behavior and authority model. Merely retaining a key leaves
application-authority checks unsatisfied. We prefer a host-local terminal-only
transition using the existing result, without adding a required client phase.
An independently useful key-retirement service needs a separate proposal.

### 5.3 Separate application receipt capability

A capability scoped to one durable operation could allow encrypted receipt
reconciliation after the original connection closes. It requires protected
capability distribution, expiry, rate limits and public application methods.
It is a valid application alternative, not a feature implicitly supplied by
Bootstrap or this RFC. It can coexist with the proposed terminal attempt.

### 5.4 Unrestricted grace or acknowledgement before commit

A general drain can deliver protected output to withdrawn authority. Waiting
for the peer's acknowledgement can let it postpone revocation. Sending success
before durable commit can lie across a crash. None satisfies the proposed
contract. A durable command may report acceptance/pending, but that is a
different application result, not confirmed terminal completion.

## 6. Compatibility

The proposal retains the existing wire representation and ordinary client
result handling. Disabled hosts behave as before; mixed-version peers can
still observe ordinary success or an unknown outcome. Clients cannot infer
support from the endpoint, a connection error or a diagnostic identifier.

Wire-byte compatibility is not sufficient to approve changed withdrawal
semantics. Review must decide whether the opt-in exception is compatible under
[governance](../GOVERNANCE.md#4-how-breaking-changes-are-handled), including
security and failure behavior. If classified as breaking, the major-version
and migration requirements apply. This draft assigns no release version,
changes no dependency pins and grants no publication authorization.

## 7. Security considerations

The exception is an independently justified terminal-only permission, not
continued application authority. Its attack surface is the authority adapter,
private call ownership, output metadata and deadline/cleanup coordinator.
Peer-controlled fields cannot create a permit. Wrong ownership or an external
denial must defeat it. Failure details stay local and must not expose key,
credential, payload or authority-store diagnostics.

The 1,024-byte ceiling, one reservation per connection, existing execution
limits and five-second ceiling bound resource use. A malicious or stalled
peer cannot keep the application authority active or extend the deadline.
No notification, unrelated selected result, recovery event or sibling channel
gains permission. Closed/suspended cipher state cannot be restored for a receipt.

Already-running external effects can survive cancellation and channel loss.
Applications must use their own transactional preconditions and effect fences;
this RFC cannot make distributed work stop or roll back. Likewise, revocation
cannot force a remote peer to delete information it already retained.

## 8. Test plan and acceptance criteria

All rows are proposed cases, currently **NOT_EXECUTED**. They are not registered
conformance cases and do not imply production application durability.

| Draft case | Coverage | Requirement labels |
|---|---|---|
| R14-T01 | Disabled/unsupported preflight rejects before effects | R14-01, R14-02 |
| R14-T02 | Wrong call, generation, principal, scope or binding cannot reserve/use | R14-02, R14-03 |
| R14-T03 | Exact owned commit permits one correlated result; fresh Returning denied | R14-03, R14-08, R14-11 |
| R14-T04 | Commit visible before callback return is recognized only by its owner | R14-03, R14-04 |
| R14-T05 | Denial visible to final validation or already observed before handoff aborts; post-observation changes follow the declared race bound | R14-04, R14-05, R14-11 |
| R14-T06 | Unknown/store error, stale evidence and delayed success cannot clear abort | R14-04, R14-05 |
| R14-T07 | Queued replies, notifications, recovery and sibling delivery are suppressed | R14-05, R14-06 |
| R14-T08 | Partial ordinary frame finishes precommit or aborts without mutation | R14-06, R14-07 |
| R14-T09 | Partial receipt preserves ciphertext/order and never replays | R14-07, R14-11 |
| R14-T10 | Oversized result, budget exhaustion and clock loss reject/close boundedly | R14-08, R14-09 |
| R14-T11 | Cancel selected first beats success; cancel after selected success is ignored; deadline and duplicate completion rules preserved | R14-10, R14-12 |
| R14-T12 | Dropped waiter, stalled I/O and surviving effects retain accounting/close owner | R14-09, R14-12 |
| R14-T13 | Loss never becomes success/replay; write and client observation stay distinct | R14-11, R14-13 |
| R14-T14 | Both cross-language TCP directions, including fragmentation and forced loss | R14-01 through R14-13 |

Use deterministic barriers around authority commit, callback completion,
supervisor observation, terminal selection and carrier handoff. Include
default-disabled regressions and the existing generic withdrawal suites.
Exercise custom drivers and portable builds separately from native TCP.
Other supported carriers need their own composition tests; they inherit no
verification from sharing an internal driver.

### Review and acceptance gate

- [ ] Protocol and human security review completed; no unresolved objections.
- [ ] Public acceptance and compatibility/version decision recorded.

### Post-acceptance implementation gate

- [ ] Accepted owner edits and registered requirement/case mappings synchronized.
- [ ] Both SDK implementations pass their isolated runtime and transport suites.
- [ ] Go server with Rust client and Rust server with Go client observe the result.
- [ ] Forced loss remains unknown without replay or revived authority.

### Consuming-application gate

- [ ] The application proves its real durable transition and integration separately.

The latter gates are future evidence obligations, not work completed by drafting
this proposal or a substitute for its review and public acceptance.

## 9. Drawbacks and risks

This adds a security-sensitive cross-layer coordinator and an authority adapter
more expressive than boolean validity. Applications without atomic ownership
evidence cannot use it. Conservative aborts will still lose some receipts.
Output barriers may cancel unrelated calls and sacrifice availability even
when an attempted mutation fails. A short budget may be too small for an
application dependency; that application must keep the default or use separate
receipt reconciliation, not stretch the security limits silently.

## 10. Unresolved questions and blockers

1. **TBD — blocker:** public protocol acceptance, human security review and
   compatibility/version disposition have not occurred.
2. **TBD — blocker:** review the 1,024-byte ceiling, five-second absolute cap
   and quarter-budget/250-ms teardown tail against platform clock resolution,
   native carrier cancellation and application authority latency.
3. **TBD — blocker:** specify concrete SDK adapter contracts for owned commit
   evidence and superseding denial, including data lifetime and monotonically
   ordered revisions. A callback boolean is not an acceptable implementation.
4. **TBD — blocker:** prove writer-barrier and final-handoff linearization in
   each SDK, including independent embedder monitors, custom drivers and
   carrier-buffered output. The remote-observation race must remain explicit.
5. **TBD — blocker:** establish whether any explicit peer negotiation is
   required by compatibility review. No new capability or message is allocated.

## Appendix: References

- [Current connection contract](../specifications/connection.md)
- [RPC output, terminal selection and shutdown](../specifications/rpc.md)
- [Authorization lifecycle and security](../specifications/security.md)
- [Carrier output and failure rules](../specifications/transports.md)
- [Go implementation issue 17](https://github.com/tinkle-org/syntra-go/issues/17)
- [Go implementation repository](https://github.com/tinkle-org/syntra-go)
- [Rust implementation repository](https://github.com/tinkle-org/syntra-rs)
- [Governance and acceptance](../GOVERNANCE.md)
