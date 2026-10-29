# v1 specification acceptance package

Status: selected work plan, not an accepted specification or release approval.
Baseline: `f092a4912c1259c0899b828e7570be0edd666ec4`. Scope was selected as
specification-first, canonical SC1 over verified WSS first, standardized update
recovery and applicable mobile lifecycle. One active maintainer is the reported
working situation; no public identity or approval is invented here.

## First increment and approval boundary

[Draft RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
provides the proposed sole-maintainer bootstrap rule, exact release scope,
separate acceptance/freeze/release milestones and independent production gates.
The [decision-record template](decision-record-template.md) makes the required
identities, revisions, compatibility choices and evidence explicit.

This increment prepares those documents only. It leaves current quorum,
RFCs 0001–0008, normative owners, IDL, profile/case registries, compatibility
archives and prerelease configuration unchanged. Publication or merge does
not ratify the amendment. Next, the actual owner records the explicit public
bootstrap decision (or appoints a second maintainer under the existing rule),
then the authorized governance/roster changes can land.

## Dependency-ordered follow-up changes

Each normative increment carries its owning specification changes,
requirement-to-case mapping, fixtures, compatibility disposition and migration
notes together. Requirement IDs stay with their owners; no test PASS is
inferred from a registered case.

| Increment | Concrete deliverable | Exit evidence |
|---|---|---|
| 1. Governance activation | Public owner ratification, actual active roster, synchronized governance/contributing/RFC process; approve precise bundle scope | Revision-pinned human decision and security review; no fabricated second vote |
| 2. Decision consolidation | One current contract in each RFC 0001–0008; reconcile amendments and distinguish contract review from release execution | Individual recorded acceptance, explicit behavioral and source/FILE treatment |
| 3. Core/parser/mobile activation | Serialization/framing precedence; handshake native failure; increasing IDs and terminal gate; HTTP carriage/header budgets; bounds and suspend/replacement/execution/shutdown rules | Owning clauses, permanent requirements, positive/negative raw/race/boundary cases and regression checks agree |
| 4. Recovery activation | Apply RFC 0006 §11.8 owner/IDL-comment map; correct old recovery cases; register actual recovery obligations | Fresh-handle, scoped-generation, overflow, snapshot and durable-progress cases trace the selected contract |
| 5. SC1 activation | Apply RFC 0007 §11 bytes/order/lifecycle; synchronize secure channel, device authorization, bindings and ADR-011; register distinct SC1/WSS profile | Exact public context plus reviewed vector-corpus contract, security obligations and both-mode cases; no draft-1 alias |
| 6. Schema source migration | Confirm downstream Go layout; apply only authorized package options and compatibility transition | Preserve historical hashes; demonstrate exact intended FILE/source differences; forward FILE checks and downstream import evidence |
| 7. Evidence tooling | Extend existing declarations, requirement/profile validation, role/mode selection and release checks | Negative tests reject missing provenance, invalid approvals and omitted required execution; structural checks remain separate |
| 8. Freeze and handoff | Pin accepted specification/suite revision; update guides, migrations and readiness assessment; give Go/Rust exact implementation and execution tasks | No in-scope owner contradictions or undecided contracts; explicit unexecuted downstream gates |
| 9. Stable promotion | Review independent pure-Go/Rust, mobile/operational, lifecycle and independent security evidence; authorize reviewed release notes/revision | All applicable selected gates pass; only then approve stable release configuration/tagging |

## Specific tooling and consistency work

- Recovery already has an IDL and registered placeholder cases. Update them;
  do not invent another envelope or replace their identities without trace.
  The manifest schema and Python requirement patterns currently exclude the
  recovery owner's `SYN-URP-*` family; extend them deliberately and register
  the actual obligations, preserving reserved recovery requirement numbers.
- Declarations already have PASS, FAIL, SKIP, UNSUPPORTED and NOT_EXECUTED.
  Add specification/implementation/suite provenance, evidence references and
  complete role/mode/case selection instead of creating a second verdict model.
- The current core conformance document requires two transports for every claim;
  the interop matrix permits single-transport claims. Apply the accepted scoped
  two-transport-proof decision across owners and selection rules together.
- The Go package change fails current FILE checks and exact-option schema
  tests. Its intentional source migration needs its own reviewed transition;
  keep STANDARD/FILE and immutable initial/historical evidence.
- Release automation is explicitly prerelease-only and runs structural checks,
  not independent peer tests. Keep it so until a separately approved stable
  promotion verifies the evidence; a green docs job is not release eligibility.

## Remaining implementation and production gates

Both independent implementations pin the same accepted revision and execute
Go initiator/Rust host and Rust initiator/Go host in NK and NKpsk0 modes.
FFI-backed Go is not the independent Go lane. The
[mobile acceptance plan](../conformance/plans/mobile-v1.md),
[recovery plan](../conformance/plans/update-recovery.md) and
[SC1 plan](../conformance/plans/secure-channel.md) supply planned coverage,
not results. Record actual host storage/rotation/revocation/proxy contracts,
durability/crash tests, supported iOS/Android runs, declared operational
budgets and an independent human composition review.

No new public SC1 TCP/WS, UDP/QUIC, logical-session resumption, reliable-session
RPC reconciliation, application E2EE or automatic mutation replay is included.
Published baseline profiles remain independently claimable only with their own
accepted requirements and evidence; SC1/WSS does not certify them implicitly.

Validation commands and actual outcomes belong in the change's review record.
The [readiness audit](../audits/v1-release-readiness.md) remains blocked until
its required gates are actually complete; this work plan is not their closure.

## First-increment verification record

Executed locally on 2026-10-29 using Python 3.14.7 and Buf 1.59.0:

| Command | Actual result | Evidence scope |
|---|---|---|
| `python3 scripts/validate-repo.py all` | Passed: 543 requirement rows/definitions, 141 registered cases, 204 Markdown files checked | Requirement/manifest/vector/link/RFC/Markdown/boundary consistency only |
| `python3 scripts/validate-schema.py` | Passed: format/lint/build/initial FILE gate and all 13 schema regression tests | Unchanged schema declarations and archived compatibility evidence |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | Passed: all four existing tests | License and proposed public SC1 context-fixture lint, not cryptographic execution |
| `git diff --check` | Passed | Tracked-diff whitespace checks; new documents also covered by repository Markdown validation |

No public ratification, normative acceptance, independent security approval,
Go/Rust execution, mobile-device run, commit, push or release was performed
as part of this verification. Decision-record negative checks in RFC 0009
remain planned human/tooling acceptance work; no machine validator was added.
