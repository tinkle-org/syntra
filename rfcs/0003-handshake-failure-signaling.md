# RFC 0003: Handshake failure signaling (proposal)

- RFC: 0003
- Title: Local typed handshake causes, transport-native rejection, pre-ACTIVE handling, and timer binding
- Status: Draft (v1 consistency audit findings F-03, F-07, F-08, F-09, F-16, F-19)
- Date: 2026-10-28
- Target version: pre-stable v1 contract proposal; explicit freeze/version decision required (§6)
- Relates to: `specifications/core/handshake.md` (§1B, §2A, §5), `errors.md` (§§1C–1D), `events.md` (SNTR-EVENT-005/900), `framing.md`, `specifications/architecture.md` §12.1, ADR-007, transport profiles; RFC 0001 B1/B2; RFC 0002 §10 items 1–2
- Author(s): TBD — blocker (maintainer assignment)
- Reviewers: TBD — blocker (protocol + security maintainers)

> Draft proposal, not acceptance or shipping authority. The choices below
> are selected for review; they do not amend specifications, schemas, or
> conformance expectations. No new active requirement IDs are allocated.
> Approval remains subject to [governance](../GOVERNANCE.md) §3 and the
> [RFC process](README.md).

## 1. Summary

Select transport-native handshake rejection with typed causes at the detecting
endpoint, fail-close handling of pre-ACTIVE notifications, `UNIMPLEMENTED` for
version mismatch, and a core handshake timer beginning only after the profile's
transport establishment. No pre-ACTIVE error `Frame` is added. Initiators and
hosts report what they can actually observe; a generic peer close does not
reveal the host's precise rejection cause.

## 2. Motivation

SNTR-HS-020 and SNTR-ERR-004 appear to promise a typed handshake code to both
peers, although no legal pre-ACTIVE `Frame` carries an error: `ready` represents
success and `result` requires an RPC's nonzero ID. TCP closure cannot distinguish
version, authentication, and state failures. HTTP statuses and WS close codes
also collapse multiple causes. Requiring a reversible code mapping would invent
a wire channel that these profiles do not provide.

The pre-ACTIVE notification rules also conflict: events guidance permits
ignoring while handshake/framing require failure. Version mismatch currently
permits two codes. TLS/TCP has an unstated core-timer boundary, and the earlier
4-second/6-second TLS test confused transport setup time with the core budget.
The charter failure illustration and errors §1D need corresponding corrections
after acceptance.

## 3. Proposal

All obligations in §§3–4 are proposed acceptance text, not current authority.
Existing requirement references identify the clauses to revise after approval.

### D1 — Select local typed causes and transport-native peer signals

- The detecting endpoint records the applicable typed cause from handshake §5
  and terminates the attempt. Its local waiter receives that cause, subject to
  public diagnostic hygiene. It never serializes privileged rejection detail.
- The remote endpoint reports the profile signal it observed, marked as a
  transport/binding failure rather than a received `RpcResult`. If the signal
  cannot distinguish causes, the report stays generic; it does not claim the
  detecting endpoint's precise code.
- TCP/TLS closure without a lawful result maps to local `UNAVAILABLE` at the
  waiting peer. HTTP/HTTPS statuses follow their existing adapter-report table.
  WS/WSS reports retain the close code and a generic category; a many-to-one
  close code is not a lossless `ErrorCode` encoding.
- Neither endpoint sends a zero-ID `result`, error-bearing `ready`, second
  `hello`, invented handshake record, or error in a notification. Failure never
  establishes ACTIVE, authentication success, or a subscription.

Acceptance would revise SNTR-HS-020/030/040 and SNTR-ERR-004 to distinguish
detecting-side cause from peer-visible transport evidence, including all tables
and diagrams currently implying a typed error `Frame`.

### D2 — Select fail-close for pre-ACTIVE notifications

An endpoint receiving `notification` in CONNECTED, NEGOTIATING, or
AUTHENTICATING records `FAILED_PRECONDITION`, discards the notification without
application delivery, and enters CLOSING then CLOSED through D1. It neither
queues the event for later ACTIVE nor creates subscription state. A host also
rejects wrong-direction notifications; this does not relax direction checking.
Senders continue to prohibit application notifications before ACTIVE.

Acceptance would align SNTR-HS-012, handshake §2A rule 9, SNTR-WIRE-003/005,
SNTR-EVENT-005/900, and ADR-007. HTTP bodies remain request-only under their
profile: an illegal notification is a binding rejection, not a persistent
handshake exchange.

### D3 — Select `UNIMPLEMENTED` for version mismatch

After range shape and bounds validation, an empty version intersection has
local detecting-side cause `UNIMPLEMENTED`, followed by termination. Version
selection precedes credential semantics. Malformed ranges remain
`INVALID_ARGUMENT`; wrong-state frames remain `FAILED_PRECONDITION`.
No new enum value or automatic downgrade is proposed. The generic peer signal
need not disclose the mismatch (notably HTTP `400` remains `INVALID_ARGUMENT`
in the receiving adapter's table).

### D4 — Bind the core timer to transport establishment

The default core handshake budget is 5 seconds, starting at the local
CONNECTED boundary: established TCP for TCP; successfully completed and
verified TLS for TLS/TCP; validated Upgrade for WS; verified TLS plus validated
Upgrade for WSS. It runs continuously through negotiation and authentication,
without reset on partial input or state changes, until ACTIVE or failure.
Expiry locally reports `DEADLINE_EXCEEDED` and closes. Each endpoint measures
its own boundary; synchronized clocks are unnecessary.

TLS/Upgrade setup has a separate bounded, documented establishment budget.
A deployment may also enforce a documented total-attempt budget. Neither
budget changes the core start point. A setup timeout is reported as a setup
failure with its phase, not as expiry of a Syntra handshake that never began.
HTTP/HTTPS retain their per-exchange timing specialization rather than acquiring
a persistent hello/ready timer. Mobile queue/suspend timing is proposed in
RFC 0008 and needs joint review before acceptance; this RFC defines only the
phase boundary and does not change secure-channel establishment policy.

## 4. Detailed design

### Failure carriers and information available to each peer

| Detecting-side condition | Local cause | Native peer signal | What the peer can conclude |
|---|---|---|---|
| TCP/TLS Syntra handshake rejection | Applicable handshake §5 code | TCP close; TLS shutdown where possible | Attempt ended; `UNAVAILABLE` absent better local evidence, not the precise rejection cause |
| HTTP/HTTPS no version overlap or malformed binding | `UNIMPLEMENTED` for no overlap; `INVALID_ARGUMENT` for malformed binding | `400`, no Syntra envelope | Local binding failure `INVALID_ARGUMENT` per SNTR-HTTP-041; not proof of a particular host cause |
| HTTP/HTTPS authentication rejection | `UNAUTHENTICATED` or `PERMISSION_DENIED` | `401` or `403`, no Syntra envelope | The corresponding generic adapter report, without an authentication sub-reason |
| WS/WSS version/state/unknown-variant failure after Upgrade | `UNIMPLEMENTED` or `FAILED_PRECONDITION` | Close `1002` | Generic protocol rejection, not which cause/code occurred |
| WS/WSS authentication rejection | `UNAUTHENTICATED` or `PERMISSION_DENIED` | Close `1008` | Generic policy rejection, not credential validity or denial sub-reason |
| WS/WSS oversized message | `RESOURCE_EXHAUSTED` | Close `1009` | Message-size rejection, no echoed input |
| WS/WSS core handshake deadline | `DEADLINE_EXCEEDED` | Select Close `1001` | Going away/attempt ended; only the locally expired timer establishes deadline cause |
| Unexpected loss at any phase | `UNAVAILABLE` to affected local waiters | None if transport is gone | Failure with no inferred remote verdict |

The fixed `1001` handshake-timeout choice replaces the existing WS `1001/1008`
menu on acceptance. Other native framing/status mappings remain owned by their
profiles. In particular, HTTP size/status limits and WS control-frame limits
are not extended by this table. Native signaling is best effort with bounded
teardown; a failed close write cannot reopen the attempt or defer it forever.

```text
Initiator                                      Host
    |--- transport establishment ---------------->|
    |    each local core timer begins at CONNECTED |
    |--- hello{min,max,credential} ---------------->|
    |                                no overlap:  |
    |                       local UNIMPLEMENTED   |
    |<-- native close/status (no error Frame) ------|
    | local report of observed signal              |
    |    both terminate; new transport required     |
```

After acceptance, architecture §12.1 would depict this native failure path,
not `Frame{result}`. Errors §1D would reference HTTP/HTTPS's existing status
tables and retain the distinction between `200` plus an actual RPC result
and a non-`200` binding failure. Unknown fields keep serialization policy;
unknown body variants retain `UNIMPLEMENTED` at detection, never silent
success or an invented error envelope. Frame/depth/rate caps still precede
policy lookup and dispatch.

## 5. Alternatives considered

1. **New handshake error message.** Rejected for this proposal: it would need
   a separately reviewed binding, negotiation, bounds, and old-peer behavior.
   Post-ACTIVE negotiation cannot authorize a pre-ACTIVE record retroactively.
2. **Promise exact remote codes via native closes.** Rejected: TCP has no such
   carrier and HTTP/WS mappings are many-to-one. Close text is not a registry.
3. **Ignore pre-ACTIVE notifications.** Rejected: it conceals invalid ordering
   and permits inconsistent delivery/subscription behavior across receivers.
4. **Do nothing.** Rejected: preserves the carrier contradiction, dual mismatch
   codes, and timer tests that assert failure against the wrong phase.

## 6. Compatibility

No `.proto` fields, reserved values, or encodings change. That alone does not
make this behaviorally compatible: fail-close replaces ignore behavior;
`UNIMPLEMENTED` replaces an allowed alternative; local/remote error promises,
WS timeout close selection, and timer start semantics change observable results.

Maintainers need to record an explicit pre-stable contract freeze decision with
an inventory of affected peers and migration notes. If these behaviors are
already frozen or supported as an interoperable contract, the incompatible
changes require the major-version process in governance §4, including rollout
and any dual-support window. They are not inherently compatible clarifications
or capability-gated minor work. A post-ACTIVE capability cannot hide a baseline
handshake behavior change. Acceptance must state the version treatment and
the follow-up `MIGRATION.md`/`CHANGELOG.md` work.

## 7. Security considerations

Generic native rejection reduces credential/principal oracles. Local typed
reporting is not permission to log credentials, tokens, or authentication
sub-reasons publicly (SNTR-ASEC-001/011/024). Peer text is untrusted data and
cannot supply an authoritative code. Fail-close prevents pre-authentication
event delivery. Independent setup and core budgets prevent slow setup from
being unbounded while preserving the correct core deadline boundary. Neither
failure nor timeout permits plaintext fallback or credential transmission
before certificate/hostname verification.

## 8. Test plan and acceptance criteria

These are planned acceptance tests, not executed behavioral evidence or PASS
claims. Existing traces identify impacted coverage; acceptance must revise
owning cases and allocate any needed new requirements through normal review.

| Existing requirement trace | Planned positive/negative evidence |
|---|---|
| SNTR-HS-003/010/020/030/040, SNTR-HS-900/901, SNTR-ERR-004/901 | Highest-overlap success; low/high/disjoint mismatch yields detecting-side `UNIMPLEMENTED`; malformed range remains distinct; credential policy not called on mismatch; no error `Frame` |
| SNTR-HS-012, SNTR-WIRE-003/005, SNTR-EVENT-005/900 | Notification in each pre-ACTIVE state closes without dispatch, buffering, or subscription creation; lawful ACTIVE notification remains separate from RPC completion |
| SNTR-HS-002/011/021, SNTR-TLS-005/900, SNTR-WSS-041/900 | Separate setup/core timer cases below, plus no hello/credential before verified setup |
| SNTR-HTTP-040/041/042/900, SNTR-WS-080/081/900, SNTR-WSS-900, SNTR-ERR-900/901 | Observe native status/close and each endpoint's local report separately; many-to-one signals do not claim exact remote cause; HTTP non-200 never synthesizes `RpcResult` |
| SNTR-ASEC-011/024/900, SNTR-SER-006/007 | Generic/redacted failures, oversized and malformed inputs bounded before policy; close-write stall cannot retain the attempt indefinitely |

TLS timer fixtures use controlled time and explicit configuration:

- [ ] Setup budget 10 s, no tighter total-attempt cap: TLS taking either 4 s
  or 6 s followed by immediate successful hello/ready succeeds. The 6 s TLS
  duration does not consume the subsequently started 5 s core budget.
- [ ] Setup budget 5 s: stalled TLS expires in setup; no Syntra hello is sent
  and no core deadline expiry is claimed.
- [ ] Verified TLS completes; then ACTIVE at core +4 s succeeds, while a
  stalled handshake at core +5 s expires and is still failed at +6 s.
  Partial hello bytes or authentication activity do not reset that deadline.
- [ ] WSS repeats the phase tests with TLS plus Upgrade before CONNECTED;
  an explicit total-attempt cap is tested independently of the core timer.
- [ ] Two independent implementations (or governance's bootstrap fixture
  alternative) demonstrate detecting-side and peer-observed outcomes separately.
- [ ] After acceptance, align the owning specs, diagrams, ADR-007, and traces;
  schema checks remain a separate gate if a later revision adds schema work.

## 9. Drawbacks and risks

TCP peers cannot learn a precise remote rejection cause, and WS close categories
remain coarse. This is an explicit limitation of the selected carriers. Local
diagnostics improve troubleshooting without claiming nonexistent wire evidence.
Independent budgets add configuration that reviewers must check together.

## 10. Decision status and acceptance blockers

| Proposal choice | Selection for review | Approval status |
|---|---|---|
| D1 | Local typed cause plus native peer signal; no error Frame | Unapproved |
| D2 | Fail-close pre-ACTIVE notification | Unapproved |
| D3 | `UNIMPLEMENTED` for no version overlap | Unapproved |
| D4 | Core timer starts after profile establishment; setup budget separate | Unapproved |

1. **TBD — blocker:** assign actual author/owner and protocol/security reviewers.
2. **TBD — blocker:** record two maintainer approvals, security review, and
   resolution of normative objections; selected text is not acceptance.
3. **TBD — blocker:** record the pre-stable freeze/version and migration decision
   in §6, including the changed remote-reporting promise and WS timeout mapping.
4. **TBD — blocker:** reconcile the forthcoming RFC 0008 queue/suspend clock
   contract and related RFC 0007 setup budgets without combining timer phases.
5. **TBD — blocker:** accepted spec/diagram/case updates and independent evidence
   are still required; F-03/F-07/F-09/F-19 are not closed by this Draft.

## Appendix: References

- [Handshake](../specifications/core/handshake.md),
  [errors](../specifications/core/errors.md),
  [framing](../specifications/core/framing.md),
  [events](../specifications/core/events.md).
- [TLS/TCP](../specifications/transports/tls-tcp.md),
  [HTTP](../specifications/transports/http.md),
  [HTTPS](../specifications/transports/https.md),
  [WS](../specifications/transports/websocket.md),
  [WSS](../specifications/transports/secure-websocket.md).
- [Authentication security](../specifications/security/authentication-security.md),
  [RFC 0002](0002-auth-session-lifecycle.md),
  [RFC 0007](0007-secure-channel-device-authorization.md).
