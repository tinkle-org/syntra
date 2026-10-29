# Syntra v1 release readiness — current assessment

Date: 2026-10-28. Scope: current specification-only repository and selected
mobile v1 target. Overall verdict: **BLOCKED**. This is not a tag, maintainer
approval, conformance declaration or independent security certification.
The [October 19 snapshot](history/v1-release-readiness-2026-10-19.md) is retained
as history; its source counts, distribution, license and profile-ID assertions
do not override current sources.

## Selected target and authority

The user selected SC1 and standardized update recovery as required release
deliverables. Core-only interoperability is still valid for its own claim but
does not complete this target. [RFC 0008](../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md)
and the [delivery record](../docs/mobile-v1-delivery.md) define the proposed
dependency order. RFCs 0001–0008 remain Draft and ADR-011 remains Proposed.
Selected alternatives are not accepted normative changes: real reviewers,
maintainer quorum, security review and explicit compatibility designation are
still required by [governance](../GOVERNANCE.md).

Planning update (2026-10-29): [Draft RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
proposes public owner-ratified bootstrap governance and the exact SC1/WSS-first
stable scope. The [acceptance package](../docs/v1-acceptance-package.md) and
[decision-record template](../docs/decision-record-template.md) prepare the
next approval/activation work. No transition, RFC acceptance, independent review,
wire/profile change or release authorization is recorded by those proposals.
The BLOCKED verdict and historical verification record below are unchanged.

## Current area assessment

| Area | Verdict | Current finding / next gate |
|---|---|---|
| Core/parser | BLOCKED | RFCs 0001/0008 select raw oneof, body-space, unknown/reserved and precedence proposals; owner edits and raw-wire cases await acceptance |
| Handshake | BLOCKED | RFC 0003 selects local typed causes/native peer failure, fail-close notifications and phase timers; existing contradictory owner text not activated yet |
| RPC/HTTP/auth carriage | BLOCKED | RFC 0004 selects ordered increasing IDs, native-close reuse rejection, terminal gate and per-profile credentials; compatibility and behavioral execution pending |
| Negotiation/bounds | BLOCKED | RFC 0005 selects RFC 0006 negotiation, concrete bounds and serialized-byte fixture correction; owning clauses/cases not synchronized before acceptance |
| Schema tooling | STRUCTURAL PASS ONLY | Buf format/lint/build/FILE and 13 schema tests pass; no schema edits. Legacy `go_package` remains; its proposed downstream path needs explicit FILE/source migration |
| Baseline profile identifiers | CONSISTENT | Current transport specs/suite agree: `SNTR-HTTP-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`; no alias/rename needed |
| SC1 | BLOCKED | Rust local-1 and Go draft-1 have different context/prologue/mode/carrier/subprotocol bytes. RFC 0007 §11 selects a new contract; downstream alignment, Noise vectors, independent sockets and security review pending |
| Authorization lifecycle | BLOCKED | Same-principal/current-enrollment gate, provisioning/rotation crash contracts, pins, fail-closed store behavior and verified deployment revocation bounds still need acceptance and execution |
| Update recovery | BLOCKED | Required target: RFC 0006 §11 selects fresh rounds, local overflow isolation, scoped generations, snapshot and durable state/checkpoint semantics; owner/IDL synchronization and independent crash tests pending |
| Mobile/runtime bounds | BLOCKED | RFC 0008 selects suspension/queue deadlines, connection generations, reconnect, active-execution accounting and bounded drain; downstream/mobile implementation tests pending |
| Transport/proxy security | BLOCKED | Initial public target SC1/WSS retains verified TLS; every claimed carrier and at least one accepted proxy topology require applicable independent tests; no new raw public transport exception |
| Conformance/interop | BLOCKED | CI validates definitions/vectors, not complete IUT runs. Registered suite unchanged; no SC1 profiles activated and no independent results added |
| Operational/mobile assurance | BLOCKED | Declared budgets and iOS/Android lifecycle, weak-network, idle-cost and soak evidence required; simulated/compile evidence alone insufficient |
| License | PRESENT | Apache-2.0 LICENSE present and full-text regression test passes |
| Distribution | CURRENT MODEL DOCUMENTED | Document/schema-provenance releases via release-please Git tags; language artifacts downstream. BSR schema publication/GHCR gates retired, not open blockers |

## Historical consistency findings disposition

These statuses distinguish source correction from normative acceptance; none
closes a behavioral defect merely because a proposal exists.

| Finding | Current disposition |
|---|---|
| F-01 profile identifiers | Resolved in current source; verify consistency mechanically, do not carry historical mismatch as P0 |
| F-02 completed-ID reuse | Open; RFC 0004 increasing-ID/non-reuse proposal replaces the bounded-window alternative |
| F-03 pre-ACTIVE carrier | Open; RFC 0003 proposes local precise cause and native/generic peer failure without an illegal result |
| F-04 HTTP stale-ID conflict | Open; RFC 0004 per-exchange specialization needs to be synchronized with the owning clauses |
| F-05 generated import identity | Open source/FILE migration; package path references removed in-tree layout, not a required BSR publication workflow |
| F-06 payload/frame limit | Open; RFC 0005 selects exact encoded MAX/MAX+1 and fitting payloads |
| F-07/F-08/F-09 notifications/illustration/version code | Open; selected RFC 0003 proposals await owner/case activation |
| F-10/F-13/F-14/F-15 carriage/re-auth/HTTP row/races | Open; RFC 0004 proposal and tests. The old “only UNAVAILABLE implies unknown outcome” wording is corrected in errors, but the broader F-15 race contract remains open |
| F-11/F-12/F-17/F-18 negotiation/floor/bounds | Open; RFC 0005 proposal, with recovery negotiation now required for the target |
| F-16 error-layering note | Pending editorial owner synchronization; exact remote codes cannot be inferred from many-to-one status/close signals |
| F-19 TLS timer origin | Open; corrected RFC 0003 tests separate setup from core budget |
| F-20 schema filenames | Resolved references in core; corrected remaining security owner references from `error.proto`/`session.proto` to `errors.proto`/`handshake.proto` in this editorial pass |
| F-21 coverage/counts | Partial: all 25 charter IDs have registry dispositions. Ten prose-only AUTH/ERR case IDs, incompletely designated obligations and stale local counts remain; structural registry validity is not complete coverage/execution |
| F-22 transport/documentation edges | Partial: WS/HTTP query-policy rationale and WS malformed-suffix 1007 vectors now explicit. WSS credential-query rejection, HTTP missing-auth anonymous qualification, over-max budget robustness, inherited H1/H2 body framing, 504 status mapping and stale trace directories remain tracked owner work |

Deferred scope: UDP/QUIC, logical-session resumption, reliable-session RPC
reconciliation and automatic mutation replay. Required update recovery is not
among the deferrals. Classical SC1 makes no post-quantum or application-E2EE
claim. Every future supported feature needs its own accepted contract/evidence.

## Verification record for this branch

Executed locally in this repository during this change:

| Command | Result | What it establishes |
|---|---|---|
| `python3 scripts/validate-repo.py all` | Passed | 543 requirement definitions/rows; 141 registered cases; manifest/vector/link/RFC/Markdown/boundary consistency |
| `python3 scripts/validate-schema.py` | Passed | Pinned Buf format/lint/build/initial FILE baseline and all 13 schema tests, including hash-verified historical archive checks |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | Passed, 4 tests | Complete license plus three proposed-context fixture lint checks |

The new context test first failed with the fixture absent, then passed after
the public JSON was added. It checks exact context/prologue bytes, mode/carrier
coverage and negative-recipe traceability. It does not execute negative peer
rejections, Noise operations, or a transport. No schema baseline/generator
output was changed. These are structural results, not 141 executed peer cases.

Not executed: downstream Rust/Go alignment, deterministic Noise generation,
live bidirectional interoperability, deployment lifecycle/proxy/revocation tests,
mobile bridge/device tests, performance/soak or an independent external security
review. Specialist proposal review is advisory, not independent release approval.

## Remaining release sequence

1. Assign real owners/reviewers and accept the decision set, with explicit
   compatibility/freeze decisions rather than automatic minor labels.
2. Land synchronized normative owner/schema/registry/case changes. Preserve
   initial/historical baselines and handle any intended FILE break openly.
3. Align separate Rust/Go implementations, generated types and host-policy
   contracts against that same revision; retain regression tests.
4. Execute the [mobile](../conformance/plans/mobile-v1.md),
   [recovery](../conformance/plans/update-recovery.md) and SC1 plans in both
   independent roles for every claimed profile; preserve exact evidence.
5. Complete security review and mobile/operational gates, then finalize guides,
   declaration/profile claims and maintainer-authorized release notes.

No tag, commit, push, production release or conformance verdict is created by
this assessment.
