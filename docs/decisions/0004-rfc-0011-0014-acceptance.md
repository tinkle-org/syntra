# Decision 0004: Acceptance of RFCs 0011–0014

Status: approved design acceptance. Canonical adoption, implementation,
specification freeze and release authorization are separate dispositions below.

## Identity, scope and public evidence

| Field | Recorded value |
|---|---|
| Decision kind / state | RFC acceptance / approved |
| Date | 2026-11-06 |
| Decision owner | oscarlaw, the sole active maintainer in [the roster](../../MAINTAINERS.md) |
| Public decision | [Revision-bound acceptance comment on PR 25](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482) |
| Reviewed repository and commit | `tinkle-org/syntra` at `cfab7655c348f1d04f4e1d57e28cc1a634478854` |
| Reviewed documents | RFCs 0011, 0012, 0013 and 0014 at that commit, with the per-RFC dispositions in the public comment and below |
| Decision preparation branch | `feat/scoped-terminal-receipt`; [PR 25](https://github.com/tinkle-org/syntra/pull/25) |
| Authority | [Governance §3](../../GOVERNANCE.md#3-who-approves-normative-changes): one active maintainer, explicit public approval, disclosed self-approval and applicable security review |
| Supersedes | Decision 0003's pending acceptance/review disposition for RFC 0013; no earlier dated evidence is rewritten |

The maintainer explicitly instructed acceptance of all remaining pending RFCs,
authorized the specification commit/push and public acceptance PR, and confirmed
completion of human protocol/security self-review. The assistant published the
linked decision at that direction through the authenticated maintainer account.
The public comment pins the reviewed source independently of this record's
later status-propagation edits; there is no self-referential reviewed commit.

## Approval and review

| Field | Evidence / limit |
|---|---|
| Required maintainer quorum | One active maintainer; no additional maintainer exists in the current roster |
| Approval | oscarlaw, explicit decision in the linked public comment |
| Self-approval disclosure | oscarlaw is the requesting author and approver of the AI-assisted work; this is one person's approval, not two votes |
| Human protocol/security review | Completed self-review confirmed by oscarlaw and disclosed in the public decision |
| Independent human security review | NOT_EXECUTED; not supplied or claimed by this decision |
| Advisory analysis | AI-assisted proposal and consistency review; advisory only, not a maintainer vote or independent human review |
| Normative objections | None by the sole active maintainer recorded in the linked decision; this does not invent a second reviewer |
| Merge, freeze, tag and publication | Not authorized by this acceptance decision |

Self-review satisfies the acceptance disposition confirmed here. It does not
satisfy independent human security review required by the selected stable
release bundle. No runtime or conformance pass is inferred from acceptance,
repository validation, an SDK design document or a static fixture.

## Per-RFC dispositions

### RFC 0011: Specification release versioning and publication

**Accepted as a release-process design; publisher activation deferred.** The
two-component release identifiers, revision-bound authorization and publication
safeguards are accepted. This is a specification-process change, not a new
wire version or a change to SDK package versioning.

The existing publisher remains active. The prepared manual publisher remains
disabled by the qualified RFC status `Accepted (design only; activation deferred)`:
its exact bare-status guard is not satisfied. No workflow or administrative
protection is changed here. Activation needs the separately scoped publisher
migration, including retiring the old workflow/configuration atomically and
verifying the required protection and authorization controls.

The publisher-specific supersession of RFC 0009 D5 takes effect only at that
activation. Its independent implementation, recovery/mobile, operational and
security evidence gates remain intact. There is no release authorization.

### RFC 0012: Protocol reference scope

**Accepted.** Ratifies the six-page protocol reference and separation of
observable protocol obligations from implementation mechanisms. That reference
reorganization landed at `3f7e8ea037fefcc5c86101d23e7722c83e28a0d3`.

No additional wire declaration, cryptographic construction, carrier policy,
SDK behavior or runtime result is introduced. Observable ordering, expiry,
authorization and resource obligations are not removed by this ratification.

### RFC 0013: HTTP/TLS carriers and trusted streams

**Accepted as an optional additive pre-release design; canonical adoption
deferred.** The specified HTTP/HTTPS mappings and trusted in-process TLS-provider
boundary are approved. Its carrier 4/5 definitions, local requirement/case labels
and derived fixtures remain isolated, unregistered and unclaimable until
synchronized owner adoption. Existing canonical carrier, context, crypto and
authority inputs are unchanged.

The isolated bundle's `accepted-unadopted` state records completed public
acceptance and human self-review while keeping `active`, `freeze` and
`release_authorized` false and runtime/formal verdicts `NOT_EXECUTED`.
Local validation checks consistency with this record; it does not authenticate
a GitHub approval or execute a carrier/provider/proxy. `--require-adoption`
continues to fail closed until canonical adoption is completed.

Acceptance does not include automatic cross-carrier failover, additional
forward-proxy behavior, or another unreviewed extension. Activation needs
canonical owner/registry/fixture synchronization and separately identified
implementation evidence. This record supersedes only the pending review and
acceptance fields of [Decision 0003](0003-http-tls-consent.md), not its history.

### RFC 0014: Scoped terminal receipt and authorization retirement

**Accepted as an optional, default-disabled pre-release terminal-result design;
canonical and SDK adoption pending.** Application authority owns immediate
durable withdrawal. The reserved result is separately and narrowly authorized
by the exact owned transition; it is not continued ordinary session authority.

Accepted constraints include conditional operation/reservation ownership,
superseding-denial observations, pre-mutation full-frame fencing, immutable
first-terminal selection, one fixed non-sensitive result of at most 1,024
serialized frame bytes excluding the inner prefix, and the earlier of the
request deadline and five seconds after reservation. The final quarter of the
initial remaining budget, capped at 250 ms, is reserved for teardown.

The decision covers the documented last-observation/handoff race, sticky
failures, ignored cancellation after terminal selection, nonce/partial-frame
safety and retained cleanup/execution ownership. Unknown outcomes remain
possible; a successful local write is not peer receipt or joined closure.
No new required client exchange, capability allocation or wire field is approved.

Adapter signatures and concrete state/output plumbing are SDK implementation
work, not permission to weaken the accepted evidence or deadline contract.
Canonical owner and requirement/case adoption, matching runtime/driver support,
bidirectional interoperability and real application-authority integration remain
unfinished. Existing ordinary withdrawal remains the available behavior until
those integrations are enabled deliberately.

## Compatibility and remaining gates

RFCs 0011/0012 do not alter wire behavior. RFCs 0013/0014 are explicitly selected
additive pre-release designs with existing defaults preserved. The decision
considers security and failure semantics, not merely unchanged protobuf bytes.
An incompatible or security-weakening expansion beyond this scope requires a
separate normative disposition and any applicable major-version handling.

No current requirement registry, conformance case, active carrier or SDK input
pin is changed by this acceptance preparation. Canonical adoption and SDK
implementation must synchronize the accepted scope before claiming support.
This record permits implementation work; it does not claim it completed.

Freeze, independent interoperability/security review, required application and
mobile evidence, verified administrative controls and explicit release
authorization remain separate gates. This PR is not merged by recording the
decision, and no tag or release is created.
