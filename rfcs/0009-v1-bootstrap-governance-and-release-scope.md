# RFC 0009: Bootstrap governance and the first stable release scope

- RFC: 0009
- Title: Explicit sole-maintainer ratification, specification acceptance, and WSS-first release gates
- Author(s): oscarlaw
- Status: Accepted
- Date: 2026-10-29
- Target version: pre-stable governance transition and v1 release-scope decision; no wire activation by this RFC
- Relates to: GOVERNANCE.md §§2–6/8; CONTRIBUTING.md §4; RFC process; RFCs 0001–0008; RELEASE.md; docs/mobile-v1-delivery.md; conformance/claims.md
- Reviewers: oscarlaw (self-review disclosed; sole active maintainer)

This document records the accepted governance amendment. The public bootstrap
ratification is [Decision 0001](../docs/decisions/0001-bootstrap-ratification.md);
the active roster is [MAINTAINERS.md](../MAINTAINERS.md). The prior
two-maintainer quorum was not met; the transition is a one-time owner-ratified
bootstrap act, not a second approval. Acceptance of this RFC does not accept
RFCs 0001–0008, activate wire behavior, register a profile or authorize a
release.

## 1. Summary

Propose an explicit bootstrap transition for a project with one active
maintainer, followed by a published, count-based approval rule. Separate
acceptance of a specification from activation in its owning documents and
from authorization of a stable production release. Select canonical SC1 over
verified TLS 1.3 WSS, standardized update recovery, and applicable mobile
lifecycle evidence for the first stable bundle. Other transport claims remain
independent. This RFC changes no peer behavior, schema, profile registry,
or current production policy.

## 2. Motivation

The current two-maintainer quorum cannot be satisfied by one person. Repeating
an approval, counting an automated reviewer, or silently reducing the quorum
would misrepresent the review. Governance §8 also applies that quorum to its
own amendment, so the transition cannot be described as an ordinary compliant
amendment without either a second maintainer or a disclosed bootstrap action.

The selected RFC package is not yet the accepted specification. RFCs 0006/0007
contain later amendments that disagree with earlier text and their owners.
Some acceptance lists also combine contract review with downstream release
execution, obscuring when independent implementers have an authoritative target.

The [delivery plan](../docs/mobile-v1-delivery.md) selects SC1 and recovery,
while the historical release checklist lists all seven baseline transports.
The [interop matrix](../conformance/interoperability/matrix.yaml) permits
single-transport Core claims, but [core conformance](../specifications/core/conformance.md)
requires two transports for every claim. An explicit release-scope decision is
needed, not an accidental extra implementation dependency.

## 3. Proposal

The following clauses are the accepted replacement/addition text for the owners
listed in §4. They allocate no wire requirement IDs or conformance case IDs.
Initiator/host obligations, schema fields, errors, timers, and connection states
are unchanged by this RFC; RFCs 0001–0008 retain their own approval gates.

### D1. Disclose and ratify the bootstrap transition

Before adopting the new approval rule, the repository owner publishes a
ratification on the RFC/PR identifying their actual public account, evidence
of repository ownership, the exact reviewed commit, and the governance diff.
It explicitly acknowledges that the existing two-maintainer quorum was not
met and that this is a one-time owner-ratified bootstrap transition, not a
second approval or a precedent for bypassing future governance.

The ratification identifies the initial active maintainer and authorizes
publication of that identity in a maintainer roster alongside governance.
No account, reviewer, or approval is supplied by an assistant. Repository
ownership is established by the public repository administration/owner record,
not a claim in a document written by the contributor. If that authority cannot
be established, the transition remains blocked; the alternative is to appoint
a second real maintainer and satisfy the existing process.

The ratification is mirrored using the
[decision-record template](../docs/decision-record-template.md), then the
authorized governance/process diff and roster are applied together. Until
that happens, current governance remains in force. Ratifying this transition
does not accept RFCs 0001–0008, approve their compatibility changes, or
authorize a tag. New rule changes after bootstrap follow D2.

### D2. Match approval quorum to the published active roster

Proposed replacement intent for governance §3 and RFC process approval rules:

- With exactly one published active maintainer, an explicit approval by that
  maintainer can accept a normative RFC, governance amendment, or release
  decision. The record discloses when the approver is also the author.
- With two or more active maintainers, normative decisions require at least
  two distinct active-maintainer approvals. One person cannot count twice.
- With no active maintainer, normative acceptance and release authorization
  are blocked. Silence, a bot merge, and CI success are not approvals.
- No unresolved normative maintainer objection can be ignored. Retain
  governance §6's explicit resolution/overrule record and security review.
- Roster additions and status changes follow the rule in force before the
  change. Removing or deactivating a maintainer to change the quorum for an
  already open decision is not a valid substitute for resolving an objection.
- Non-normative changes retain the existing one-maintainer bar. Branch/tag
  protection, public PRs, DCO, compatibility review and private vulnerability
  handling are not waived.

Security-adjacent decisions still require a recorded human security review
with scope, findings and disposition. Where the sole maintainer performs that
review, identify it as self-review and record their relevant review basis; it
is not independent review. Automated analysis is advisory evidence, never a
maintainer vote or independent security approval. The independent production
gate in D5 cannot be satisfied by self-review.

### D3. Record three separate milestones

| Milestone | Proposed meaning | Evidence still separate |
|---|---|---|
| RFC accepted | Public decision approves one consolidated contract, its security review and explicit compatibility disposition | Owning specification/schema/case activation; downstream implementation |
| Specification freeze | Accepted owning specifications, authorized IDL, requirement indexes, profiles, cases and fixtures agree at a named revision | Independent runtime, mobile, operational and security release evidence |
| Stable release authorized | All applicable bundle evidence and reviews pass; maintainer explicitly authorizes the release revision and notes | Implementation artifact publication remains downstream-owned |

Acceptance is not permission to ship conflicting old owner text. Normative
activation follows the accepted RFC; a freeze record identifies the actual
activated revision. Existing RFC lifecycle terms remain: Implemented refers
to the specified spec/schema/test deliverables, not an implicit runtime PASS.
An unresolved contract or security-design ambiguity still blocks acceptance.

Consolidate each RFC before its decision. Release-execution tasks can be
identified as release gates rather than contract-acceptance prerequisites,
but that reclassification needs explicit review and cannot erase an unresolved
design finding. In particular, independent vector derivation that reveals a
contract mismatch returns the contract to review; it is not an implementation
exception. No Draft is automatically accepted by accepting this process RFC.

### D4. Select a WSS-first stable bundle without redefining Core optionality

The first stable bundle requires the following reviewed and activated contracts:

| Component | Required bundle scope |
|---|---|
| Core/session/RPC/security | All applicable requirements over the selected binding, including raw-wire rules, handshake failures, identity, races and bounds |
| SC1/WSS | Canonical RFC 0007 §11 bytes over verified TLS 1.3 WSS, independent server-key pinning, both bootstrap NK and returning NKpsk0 modes |
| Update recovery | Accepted RFC 0006 contract, explicit per-connection negotiation, required recovery behavior, persistence and snapshot crash evidence |
| Mobile/runtime | Accepted RFC 0008 lifecycle, replacement fencing, deadlines, reconnect, bounded execution/shutdown, supported iOS/Android integration evidence |
| Host deployment | Reviewed authorization/storage/rotation/revocation contract and at least one specified and tested permitted deployment topology. The accepted initial topology is direct verified TLS 1.3 WSS termination by the host; proxy termination is deferred and cannot be claimed until separately specified and tested (acceptance amendment, §11.2) |

The SC1/WSS identifier is allocated by the accepted carrier/profile work, not
by this RFC. SC1/WSS ciphertext records do not reuse the baseline WSS frame
mapping or its profile identity. Existing baseline profiles retain their own
identifiers and wire contracts; none is certified by an SC1/WSS pass.

Core-only interoperability remains a valid claim over a named supported
transport after its applicable requirements pass. Correct refusal of an
unclaimed optional capability is distinct from feature support. Recovery
refusal cannot satisfy this recovery-inclusive release bundle.

The initial bundle does not require all seven baseline transports to be
implemented or certified. Reconcile the two-transport proof with single-profile
claims: the proof is required only for a claim of transport independence across
two named transports, not for a single-transport Core or initial-bundle claim.
Every extra claimed transport still needs its own applicable evidence. This
changes a current conformance assertion and needs the owner edits in §4;
it is not an interpretation that is already active.

UDP/QUIC, logical-session resumption, reliable-session RPC reconciliation,
application E2EE and automatic mutation replay remain deferred. Raw SC1 TCP/WS
do not become public production profiles. WSS retains verified outer TLS;
there is no downgrade or new plaintext exception.

### D5. Retain independent evidence and production authorization

For this bundle, require pure Go initiator/Rust host and Rust initiator/pure
Go host, each SC1 mode, and all applicable accepted recovery/core/mobile cases.
FFI-backed Go using Rust is ABI evidence, not the independent Go implementation.
The general bootstrap packet-fixture alternative in governance §5 does not
replace this bundle's stronger selected independent-implementation gate.

Before stable authorization, obtain a named independent human review of the
SC1 construction and its complete deployment composition: TLS/pins/proxies,
fresh confirmation, principal agreement, provisioning/storage, rotation,
revocation, resource bounds and recovery integration. The reviewer is neither
the author nor implementer of the reviewed security-sensitive work and discloses
relevant affiliations/conflicts. A reviewer can be outside the maintainer team;
their findings are resolved before approval. AI review, self-review, primitive
library reputation and same-implementation tests do not meet this gate.

The release record pins specification/suite and implementation revisions,
roles, registered profiles/capabilities, per-case verdicts, evidence and declared
budgets. Applicable required cases have no FAIL, SKIP, UNSUPPORTED or
NOT_EXECUTED substitutions for a required success. Accepted refusal cases are
reported using the suite's verdict rules, without relabeling refusal as support.
Mobile/operational thresholds are declared before measurement. Open security
findings that undermine the contract or claimed deployment block promotion.

No stable configuration or tag is authorized by a specification freeze alone.
Release-please remains in prerelease mode until a reviewed stable-promotion
change verifies these gates and the explicit release authorization. Ordinary
development merges do not constitute that authorization.

## 4. Detailed design and activation map

This accepted decision is the first specification-first delivery increment. It
adds no runtime or generated bindings, profile registration, automatic approval
checker, or changed validator expectations.

| Proposed decision | Activation owner changes after ratification/acceptance |
|---|---|
| D1/D2 | GOVERNANCE.md §§2/3/6/8; publish actual active roster; CONTRIBUTING.md §4; rfcs/README.md approval text; preserve public decision evidence |
| D3 | RFC lifecycle explanation and each affected RFC's decision/acceptance sections; specification index and freeze record |
| D4 | RELEASE.md current checklist; delivery plan; conformance claims, profile selection and interop matrix; core conformance fixture rules and SNTR-WIRE-901 wording/trace where needed |
| D5 | Governance stable criteria; release checklist; conformance declaration/schema and evidence validation; mobile/security plans; reviewed stable-promotion workflow/configuration |

The [acceptance package](../docs/v1-acceptance-package.md) tracks the next
increments. Every wire/behavior/IDL activation remains paired with its owning
RFC, requirement-to-case trace and compatibility decision. No requirement or
case is retired merely to reduce the evidence needed for a claim.

## 5. Alternatives considered

1. Keep two approvals and appoint a second real maintainer. This is valid under
   current governance and remains the fallback if bootstrap ratification is
   unavailable; it is not the selected one-maintainer working model.
2. Silently count self-review twice or treat AI review as approval. Rejected:
   neither supplies another accountable maintainer or independent reviewer.
3. Require all transports at launch. Rejected for the selected scope: it adds
   implementation gates unrelated to the first secure mobile binding. No other
   profile may be advertised as passed without its own evidence.
4. Mark all documents Production now. Rejected: it conflates a selected design,
   accepted authority, actual implementation and verified deployment.
5. Do nothing. Rejected: it leaves quorum deadlock, ambiguous milestones and
   inconsistent transport prerequisites without an actionable acceptance path.

## 6. Compatibility

No Protobuf declaration, reserved value, encoding, state machine or peer
behavior changes in this patch. Governance and claim-scope changes are
observable process changes, not wire compatibility evidence. Historical
release claims/records remain history; new claims name their accepted scope.

RFCs 0003–0008 retain their separate behavioral/source/version decisions.
The proposed Go package migration is not authorized here. Its later decision
identifies exact option changes, downstream imports and FILE/source impact;
preserve immutable archives, keep STANDARD/FILE, and review any candidate
baseline transition explicitly. No baseline or compatibility failure is
hidden or rewritten by this RFC. `MIGRATION.md` and `CHANGELOG.md` are
updated with the actual authorized changes when they land.

## 7. Security considerations

A sole approver concentrates authority and cannot manufacture independence.
Public revision-pinned decisions, conflict disclosure, retained security
review, branch/tag protections and a separate independent production gate
make that limitation inspectable; they do not remove it. A change after review
that affects reviewed behavior needs renewed review of the affected scope.

Decision records contain public identities, scope and redacted evidence links,
never credentials, AKs, private keys or embargoed vulnerability details. Public
security disposition can reference the private handling process without
publishing exploitation information. The record template is not proof of
reviewer identity or artifact authenticity; those are verified during review.

## 8. Test plan and acceptance criteria

- [ ] Establish actual owner authority, maintainer identity and public review
  assignments; record D1 ratification or satisfy the existing quorum instead.
- [ ] Review proposed policy text, roster transition, security review basis,
  pre-stable compatibility treatment and exact WSS-first scope.
- [ ] Exercise decision-record review with missing approval, wrong revision,
  self-review presented as independent, unresolved objection and absent release
  evidence; each remains pending/blocked rather than approved by a template.
- [ ] Apply the accepted owner changes atomically with approval references;
  keep RFCs 0001–0008 unaccepted until their individual decisions are recorded.
- [ ] Run repository validation, schema regression checks and existing tests;
  record commands/results separately from runtime or release evidence.
- [ ] In the later evidence-tooling increment, add executable rejection tests
  for invalid records, incomplete role/mode matrices and missing required cases.

No runtime conformance test is added: this RFC activates no wire behavior.
The [record template](../docs/decision-record-template.md) describes human
review checks, not an implemented machine validator or a successful review.

## 9. Drawbacks and risks

Bootstrap ratification explicitly departs from the old quorum and therefore
depends on verifiable owner authority. One active maintainer remains a review
and continuity bottleneck. Independent security and downstream/mobile evidence
can still delay stable release; relaxing the maintainer count is not permission
to omit those gates. Scope reduction also needs careful claim wording so that
published transport specifications are not mistaken for certified implementations.

## 10. Unresolved questions and blockers

1. Public owner identity, ratification link and active roster: resolved by
   [Decision 0001](../docs/decisions/0001-bootstrap-ratification.md) and
   [MAINTAINERS.md](../MAINTAINERS.md).
2. Named protocol/process and human security review assignments and results:
   process review is recorded as self-review by the sole maintainer. Independent
   production security review remains a release gate and is not claimed.
3. RFCs 0001–0008 consolidated approvals, compatibility decisions and owning
   activation: pending their individual decisions; this RFC is not their
   acceptance record.
4. SC1/WSS profile registration and exact requirement/case selection: activated
   by the accepted RFC 0007 decision and the registered
   `SNTR-SC1-WSS-V1` profile; see §11.
5. Independent vectors, both-role/mode results, host/proxy lifecycle evidence,
   supported mobile runs and independent composition review: pending release
   gates, not fulfilled by repository checks. The initial permitted topology is
   direct verified TLS 1.3 WSS; proxy termination is deferred.
6. Decision/evidence machine validation and stable-promotion guards: pending
   tooling increment. Existing release automation is not changed by this RFC.

## 11. Acceptance decision (2026-10-29)

Decision state: accepted by the sole active maintainer under the bootstrap rule
in §3 D2. Author and approver are the same person; self-approval is disclosed.
This decision covers governance/process and the release-scope selection only.
It does not accept RFCs 0001–0008, activate wire behavior, register a profile,
or authorize a stable release.

Reviewed content: `tinkle-org/syntra` at
`94404d7378136d8b6c88ece28bf945c88d1653ba` plus the accepted governance/roster
diff. The public bootstrap act is
[Decision 0001](../docs/decisions/0001-bootstrap-ratification.md).

### 11.1 Accepted policy changes

- `GOVERNANCE.md` §§2/3 adopt the roster-based approval rule in D2.
- `CONTRIBUTING.md` §4 and `rfcs/README.md` reference the same rule.
- `MAINTAINERS.md` publishes the initial active roster.
- Acceptance, specification freeze and stable release remain separate
  milestones as proposed in D3.

### 11.2 Accepted release-scope amendments

The first stable bundle remains SC1/WSS, standardized recovery and applicable
mobile lifecycle evidence. Two scope details are fixed as follows:

- The host-deployment gate requires at least one specified and tested permitted
  topology. The initial permitted topology is **direct verified TLS 1.3 WSS
  termination by the host**. Proxy termination is deferred; it MUST NOT be
  claimed, and a forwarded header does not establish the external carrier.
- SC1/WSS ciphertext records remain distinct from the baseline WSS frame
  mapping. Baseline profiles retain their own identifiers and wire contracts.

Independent pure-Go/Rust execution, mobile and recovery evidence, the selected
topology tests and independent human composition review remain release gates
under D5. The Rust implementation at `tinkle-org/syntra-rs` main is implementation
evidence, not independent interoperability or an independent security review.

### 11.3 Claims excluded

No stable tag, production authorization, profile pass, or cross-language
interoperability claim follows from this acceptance. RFC 0006 recovery and the
core RFCs remain pending their own decisions.

## Appendix: References

- [Governance](../GOVERNANCE.md), [RFC process](README.md), and
  [contribution rules](../CONTRIBUTING.md).
- [Release process](../RELEASE.md), [current readiness](../audits/v1-release-readiness.md),
  and [delivery plan](../docs/mobile-v1-delivery.md).
- [Decision-record template](../docs/decision-record-template.md) and
  [acceptance package](../docs/v1-acceptance-package.md).
- [Mobile acceptance](../conformance/plans/mobile-v1.md),
  [SC1 plan](../conformance/plans/secure-channel.md), and
  [recovery plan](../conformance/plans/update-recovery.md).
