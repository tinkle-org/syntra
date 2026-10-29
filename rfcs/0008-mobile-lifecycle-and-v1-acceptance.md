# RFC 0008: Mobile lifecycle and v1 acceptance contract

- RFC: 0008
- Title: Suspension, connection replacement, bounded execution and mobile release evidence
- Author(s): TBD — blocker (maintainer assignment)
- Status: Draft
- Date: 2026-10-28
- Target version: v1 pre-stable behavioral proposal; compatibility designation requires review
- Relates to: RFCs 0001–0007; core RPC/reliability/sessions; transport profiles; security threat model; GOVERNANCE.md §5
- Reviewers: TBD — blocker (protocol, security and mobile-runtime maintainers)

This is a selected proposal for review, not accepted normative behavior.
Clauses below use ordinary language deliberately; they introduce no active
requirement IDs, registered profiles or shipping authority. Accepted owner
edits and permanent requirement/test IDs follow the RFC process. The user
selected SC1 and standardized update recovery as required release deliverables;
that product/release scope is not a vote accepting the underlying RFCs.

## 1. Summary

Complete the mobile lifecycle contract around existing Syntra envelopes:
deadline accounting across queueing/suspension, half-open links, connection
replacement, bounded reconnect, surviving executions and shutdown. Select
raw-wire validation rules for RFC 0001 B4–B6. Require independent Rust/Go,
mobile integration, recovery-crash and security evidence before this release
target is complete. Specifications remain authoritative and implementations
remain in separate repositories.

## 2. Motivation

Closing RFCs 0003–0005 alone leaves idle blackholes, stale connections after
handover, delayed callbacks after wake, partial writes and cancellation-surviving
handlers underspecified. The current threat model's synchronized-clock assumption
also conflicts with relative local RPC budgets. Existing SC1 implementations use
different contexts/subprotocols (RFC 0007 §11). Recovery's fixed per-subscription
boundary needs a fresh-round rule (RFC 0006 §11). These are independent gaps,
not evidence that additional transports or application-specific features are
necessary.

## 3. Proposal

### D1. Raw-wire interpretation (RFC 0001 B4–B6)

Select bounded raw validation before generated Protobuf decoding can erase
multiplicity. `Frame.body` occupies field numbers 10..31 in v1: known bodies
10..15, permanently forbidden 16/17, future body space 18..31. Fields 3..9
and 32+ are ordinary unknown metadata; 1/2 retain their known header meanings.
Future extensions cannot assign metadata within the body space or bodies outside
it without a separately reviewed compatibility change. This is a proposed
behavioral partition, not a `.proto reserved` declaration for future fields.

Validation order for a complete bounded frame is:

1. Check all wire structure/length/varint/depth limits, including unknown fields;
   malformed structure or wrong wire types for any schema-known core field is
   `INVALID_ARGUMENT`. The parser completes structural validation before
   dispatch. This includes each occurrence in known nested messages such as
   `RpcRequest.timeout_ms`; a wrong-type occurrence followed by a valid one
   cannot be silently skipped by one decoder and rejected by another. Validate
   known core message boundaries recursively, never opaque payload/credential
   bytes as submessages. Profile payload validation follows its separate schema.
2. Reject Frame field 16 or 17 as `INVALID_ARGUMENT` irrespective of metadata.
3. Reject more than one occurrence in body space as `INVALID_ARGUMENT`, including
   repeated same-body or known-plus-future-body. Exactly one body is permitted.
4. A sole structurally valid body in 18..31 is `UNIMPLEMENTED`; no body is
   `INVALID_ARGUMENT`. Known bodies are length-delimited. Future bodies in the
   allocated space also use length-delimited encoding; other wire types fail
   structurally.
5. Decode the known body and apply field, version/state, correlation and
   authorization rules in their owning documents before effects. Unknown
   metadata is ignored within the same byte/depth limits, regardless of order.

`RpcResult.outcome` similarly has one raw occurrence: known fields 1/2,
future outcome space 3..15, unknown metadata 16+. Multiple outcomes (even the
same field) are `INVALID_ARGUMENT`, sole future outcome `UNIMPLEMENTED`, no
outcome `INVALID_ARGUMENT`. Empty selected success remains valid. The raw
policy applies to these two discriminated messages; ordinary singular fields
otherwise retain standard Protobuf merge/last-value semantics. Peers agree
on this validation before using decoded values, preserving non-canonical
field ordering and non-minimal valid varint acceptance within bounded widths.

Errors follow state/carrier rules, not permission to emit pre-ACTIVE results.
This selects a proposal for SNTR-SER-003/004/005/008 and SNTR-WIRE-002/003/004/008;
it needs explicit behavioral compatibility approval and raw positive/negative
fixtures before activation.

### D2. One elapsed operation budget

The initiator's local operation deadline starts when the call is admitted,
before readiness waiting or writer queueing. Admission rejection is local and
does not create a pending wire RPC. Queued expired calls are removed without
dispatch; no expired call is sent with `timeout_ms=0` because zero means host
default. Immediately before starting frame emission, compute a positive
remaining millisecond budget, rounding down fractional milliseconds. Less than
one millisecond expires locally rather than encoding zero. The writer's
queued-to-emitting handoff is atomic with checking the call's terminal/deadline
gate and just-in-time serialization; no already-terminal queued call starts
emission. The local absolute deadline is unchanged. Never rewrite bytes after
handoff/partial emission. The host timestamps complete bounded-frame receipt;
after validation establishes a legal request and effective timeout, calculate
its deadline from that receipt timestamp. Validation and host queue time consume
the budget; expired work is not dispatched. Assembly/decode also have independent
bounded admission/time/byte limits. Network transit is not measurable by the
host and is not subtracted using peer wall clocks.

An unset call budget uses the documented bounded initiator default; a host may
apply a stricter default/cap. Profile negotiation cannot silently extend an
existing local deadline. Reconnect/recovery operations get explicit budgets;
they never restart a failed mutation's budget or cause its automatic resend.

Durations count elapsed suspension time. Use an elapsed-time source that includes
suspend, or a platform lifecycle adapter supplying equivalent elapsed duration;
ordinary wall-clock adjustments do not extend deadlines. Where elapsed continuity
cannot be established after wake/process restart, fail affected live operations
and replace the connection instead of guessing remaining time. Durable checkpoint
recovery is separate. Never persist a traffic cipher or monotonic timestamp for
cross-process reuse.

On wake, account elapsed expiry and authorization/channel lifetime before
processing buffered results or scheduling sends. A result selected as terminal
before suspension remains terminal. Merely buffered bytes not validated and
selected before the deadline do not win retroactively. RFC 0004 owns the
single-terminal linearization rule; no synchronized peer wall clock is required.

### D3. Connectivity, liveness and replacement

Baseline TCP/TLS has no universal idle failure-detection bound. Per-call deadlines
still bound callers. A runtime advertising active blackhole detection documents
its idle probe, response and assembly budgets; WS uses carrier Ping/Pong and
never requires another core heartbeat. A probe is satisfied only by its matching
response, not unsolicited Pong, raw bytes or incomplete authenticated messages.
Slow trickles do not extend absolute handshake/probe/assembly deadlines. An
authenticated complete frame establishes channel progress, not authorization
renewal, RPC completion or checkpoint persistence.

The embedding application supplies pause/wake/network-change hints and chooses
foreground/background activity policy within platform execution limits. No
claim promises keepalives or reconnect while the OS suspends the process. A
connectivity hint does not prove endpoint reachability or create new trust.
False offline indications have a documented user/manual retry or bounded
re-evaluation path; background probes are policy, not a mandatory battery cost.

Each replacement connection has a new local generation and fresh core handshake,
SC1 keys and principal validation. Before retiring connection A, mark its
callbacks/events as belonging to A. Nothing from A can complete a B call,
confirm B's recovery negotiation or route a B subscription. Applications receive
exactly one terminal outcome for A's unfinished calls. Late A output is ignored
after retirement. A locally generated fence makes no claim that A's host-side
handler stopped or rolled back. No migration of traffic keys or request IDs.

### D4. Reconnect is distinct from retry

A runtime may own automatic connectivity restoration, but it never automatically
replays arbitrary RPCs. One logical client owns one cancelable reconnect loop;
if address racing is supported, total concurrent dials have a documented cap.
Backoff is capped, jittered and subject to an attempt or elapsed budget. Values,
reset conditions and foreground exceptions are documented downstream; successful
TCP establishment alone does not reset failure history. Pause cancels unwanted
dials/timers. Wake permits at most one newly eligible attempt, not accumulated
timer ticks. Credential rejection waits for explicit credential/policy recovery;
endpoint-validation failure does not trigger plaintext/legacy fallback.

After fresh readiness, independently negotiate recovery and re-subscribe from
the permitted durable checkpoint under RFC 0006. Failure to confirm recovery
is surfaced to a caller requiring it; do not silently report full mobile service
from mandatory-only fallback. Core-only peers remain valid for Core claims.

### D5. Resource ownership and shutdown

Document separate count/byte/time limits for accepted connections, handshakes,
pending RPCs, active executions (including after timeout/cancel), inbound and
outbound queues, subscription/replay/snapshot state, callbacks and aggregate
host/principal budgets. A handler's execution permit is released only when it
actually stops; ending RPC reporting cannot admit unlimited surviving handlers.
Reject excess valid work with `RESOURCE_EXHAUSTED` where a legal RPC response
exists; connection admission can reject/close without inventing a response.

One writer owns framed output. Before any bytes are emitted a queued call can
be removed. After partial emission, finish the unit in order within its write
budget or abort the connection; never retry the whole unit onto its remaining
prefix/body. Once SC1 encryption consumes a nonce, send the resulting record in
order or abort. Bound control/result progress capacity separately from event
production so a slow consumer cannot deadlock cancellation or confirmations.

Graceful shutdown is stop admission → drain eligible terminal output until a
drain cutoff → settle remaining callers once → close transport → join owned
I/O/timer tasks before the total absolute shutdown deadline. The documented
drain cutoff reserves a positive bounded teardown/join interval within that
total; if insufficient time remains, skip further drain and abort transport.
Preserve outcomes already selected terminal. Immediate close is explicit and
may skip drain. If owned tasks or uncooperative external work survive the total
deadline, report shutdown-incomplete, retain ownership and resource accounting,
and deny new admission rather than claiming termination. The protocol cannot
forcibly stop arbitrary application effects.

## 4. Detailed design and owner changes

No new envelope field, error code, core heartbeat or transport is proposed.
Existing requirement IDs remain owned and unchanged until acceptance:

| Decision | Owner edits on acceptance | Existing trace |
|---|---|---|
| D1 | serialization, framing, versioning; RFC 0001; raw fixtures | SNTR-SER-003/004/005/008, SNTR-WIRE-002/003/004/008 |
| D2 | RPC, reliability, sessions timeout table, threat-model clock assumption; RFC 0004 | SNTR-RPC-004/005, SNTR-REL-006/020 |
| D3/D4 | sessions, TCP/TLS/WS/WSS liveness, client guide | SNTR-SESS-003/008/010/011, SNTR-REL-003/009/020, SNTR-WS-070 |
| D5 | reliability, handshake close, transport write/close; server guide | SNTR-REL-007/008/030/031, SNTR-HS-006/013 |

Allocate additional permanent IDs and registry rows when translating accepted
clauses to their owners; this document does not hide pending coverage behind
invented active conformance rows. Numeric bounds already proposed in RFC 0005
and SC1/recovery retain their own owners.

```text
Initiator                                    Host
    |--- fresh WSS + SC1 ---------------------->|
    |--- encrypted hello ---------------------->| confirmation + current policy
    |<-- ready --------------------------------|
    |--- recovery negotiate / subscribe ------->|
    |<-- bounded replay / snapshot + boundary --|
    |    persist state + checkpoint             |
    |--- confirm ------------------------------>|
    |    sleep / network loss                    |
    |    expire budgets, retire old connection   |
    |--- fresh connection, repeat establishment >|
    |--- negotiate + fresh handle from progress >|
```

## 5. Alternatives considered

Do nothing leaves lifecycle behavior dependent on language scheduling and OS
clock semantics. Mandatory always-on heartbeat ignores mobile suspension and
battery policy. Transparent RPC replay imports delivery guarantees not present
in Syntra. Making SC1/recovery mandatory for every Core peer breaks optionality;
the release bundle can require them without redefining Core conformance.
Standard Protobuf oneof merge alone cannot enforce raw multiplicity or classify
future bodies; rejecting all unknown fields would break metadata evolution.

## 6. Compatibility

Raw-field partition/validation, request-ID policy, result timing and liveness
changes are observable. Maintainers need an explicit pre-stable version/freeze
decision, not a claim that unchanged field numbers prove compatibility. Stable
incompatible behavior follows the major-version process. Preserve all reserved
numbers/names and the immutable compatibility baselines. No generator output
is changed here. Downstream migration pins the accepted revision and records
the replaced experimental contracts; it does not negotiate by sniffing failures.

## 7. Security considerations

Bound unauthenticated work, lookups, callbacks and surviving executions. Preserve
TLS endpoint verification, fresh Noise confirmation, principal consistency and
fail-closed revocation. Redact credentials, handles, checkpoints and payloads
from diagnostics; telemetry uses bounded pseudonymous local labels. Network
names/addresses are not authorization. Remote input cannot supply clocks,
trust anchors, retry permissions or unlimited timer extensions.

## 8. Test plan and acceptance criteria

The [mobile acceptance plan](../conformance/plans/mobile-v1.md) defines positive,
negative and crash cases, with role and evidence requirements. It is not an
executable manifest or PASS record. On acceptance translate each case to
permanent requirement/case IDs and runner assertions before implementation.

- [ ] Owners/reviewers assigned; maintainer quorum and security review recorded.
- [ ] RFCs 0001–0007 and this proposal agree; owner/spec/schema/registry edits reviewed.
- [ ] Context fixtures lint; independently derived Noise vectors and socket results retained.
- [ ] Rust and pure Go pass both role assignments for every claimed profile.
- [ ] Recovery durability/crash gates and mobile iOS/Android lifecycle gates pass.
- [ ] No unexecuted/skipped mandatory cases in a claimed release profile.
- [ ] Structural/schema, runtime, security and operational evidence reported separately.

## 9. Drawbacks and risks

The body-tag partition limits future allocation choices. Suspend-aware time
requires platform adapters. Strict request emission ordering needs writer
coordination; draining cannot force user callbacks to stop. Real mobile energy
and scheduling measurements remain platform-specific and cannot be replaced
by simulated clocks or WASM compilation. Required recovery and SC1 enlarge
the release scope; a passing Core subset does not close that scope.

## 10. Unresolved questions and blockers

Formal reviewer assignment, security approval and explicit compatibility/freeze
designation remain blockers. Independent cryptographic vectors, executable
case registration, downstream alignment, host lifecycle/storage contracts and
mobile/security evidence are uncompleted gates. Numeric deployment acceptance
budgets (reconnect, latency, CPU/wakeups, memory, revocation) are declared before
measurement; changing a threshold after a failure requires a reviewed rationale.

No UDP/QUIC, logical-session resumption, reliable-session RPC reconciliation,
application E2EE or automatic mutation replay is included. Supporting them later
requires independent accepted contracts.

## Appendix: References

- [SDD delivery record](../docs/mobile-v1-delivery.md).
- [Protocol Buffers encoding](https://protobuf.dev/programming-guides/encoding/):
  ordinary scalar last-value/message-merge behavior and non-canonical ordering.
- [MTProto engine](https://github.com/TelegramMessenger/mtproto-engine/tree/da4b2170210aab0430c4ff18c032991f3030cf45):
  reference for test architecture and lifecycle questions, not Syntra authority.
