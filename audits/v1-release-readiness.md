# Syntra v1 release readiness — current assessment

Date: 2026-10-28. Last updated: 2026-10-30 — the acceptance-wave planning
update, recount and verification record below are current as of that date,
not part of this 2026-10-28 snapshot. Scope: current specification-only
repository and selected mobile v1 target. Overall verdict: **BLOCKED**. This is not a tag, maintainer
approval, conformance declaration or independent security certification.
The [October 19 snapshot](history/v1-release-readiness-2026-10-19.md) is retained
as history; its source counts, distribution, license and profile-ID assertions
do not override current sources.

Planning update (2026-10-30, acceptance wave): RFCs 0001–0006, 0008 and 0010
are accepted via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md),
the owning files/recovery manifest are normalized, and RFC 0010's lifecycle
rows `CONF-SCW-025`–`042` plus requirement traces `SNTR-DAUTH-011`–`024` are
registered (planned, not executed). This audit's area rows in the table below
now reflect that recorded state. The BLOCKED verdict is retained only for the
genuine release gates: executed conformance runs, independent
vectors/evidence, independent security review and the specification freeze
record. Fresh structural recount: 593 requirement rows, 189 registered
`CONF-*` cases across the suite manifests, 209 Markdown files.

## Selected target and authority

The user selected SC1 and standardized update recovery as required release
deliverables. Core-only interoperability is still valid for its own claim but
does not complete this target. [RFC 0008](../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md)
and the [delivery record](../docs/mobile-v1-delivery.md) define the proposed
dependency order. RFC 0007 and RFC 0009 are accepted (2026-10-29); RFCs
0001–0006, 0008 and 0010 together with ADR-011 are accepted via
[Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md) (2026-10-30).
Execution, independent review, freeze and release authorization remain
required by [governance](../GOVERNANCE.md).

Planning update (2026-10-29, transition now recorded): RFC 0009 was accepted
and the public owner bootstrap ratified in
[Decision 0001](../docs/decisions/0001-bootstrap-ratification.md), which
established the public active roster, roster-based quorum and the
acceptance/freeze/release separation in
[`GOVERNANCE.md`](../GOVERNANCE.md), [`MAINTAINERS.md`](../MAINTAINERS.md) and
[`CONTRIBUTING.md`](../CONTRIBUTING.md). That transition is no longer a
proposal; the acceptance package and decision-record template are the active
working records, and the 2026-10-30 wave note above supersedes its remaining
pending items.

## Current area assessment

| Area | Verdict | Current finding / next gate |
|---|---|---|
| Core/parser | BLOCKED | RFCs 0001/0008 accepted (Decision 0002); owning clauses activated with raw-wire/reserved/precedence cases; behavioral execution and independent evidence pending |
| Handshake | BLOCKED | RFC 0003 accepted; conflicting owner text replaced with local typed causes/native peer failure, fail-close notifications and phase timers; execution pending |
| RPC/HTTP/auth carriage | BLOCKED | RFC 0004 accepted: ordered increasing IDs, native-close reuse rejection, terminal gate and per-profile credentials activated in owning docs; runtime and race evidence pending |
| Negotiation/bounds | BLOCKED | RFC 0005 accepted (D1–D4): owning clauses/cases synchronized in the acceptance wave; D5 (`go_package`) downstream follow-up explicitly deferred with a tracked FILE/source transition |
| Schema tooling | STRUCTURAL PASS ONLY | Buf format/lint/build/FILE and 13 schema tests pass on the current revision including `recovery_profile.proto`; no schema declarations changed. Legacy `go_package` remains; its proposed downstream path needs explicit FILE/source migration |
| Baseline profile identifiers | CONSISTENT | Current transport specs/suite agree: `SNTR-HTTP-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`; no alias/rename needed |
| SC1 | BLOCKED | `SNTR-SC1-WSS-V1` canonical profile registered (RFC 0007 + RFC 0010 accepted; historic draft-1/local-1 byte sets are superseded alignment targets); Rust/Go alignment, independent Noise vectors, independent execution and security review still pending |
| Authorization lifecycle | BLOCKED | RFC 0010 accepted: `SNTR-DAUTH-011`–`024` registered with planned `CONF-SCW-025`–`042` rows (registered, not executed); decided revocation policy (immediate on new connections, 300 s hard maximum/60 s target, fail-closed store) awaits executed lifecycle evidence |
| Update recovery | BLOCKED | RFC 0006 accepted (Decision 0002); owner/IDL-comment map applied and recovery manifest normalized (corrected/extended `CONF-URP` cases; `SYN-URP-*` rows admitted, 008/009 reserved); Rust/Go crash evidence remains pending |
| Mobile/runtime bounds | BLOCKED | RFC 0008 accepted: suspension/queue deadlines, connection generations, reconnect, active-execution accounting and bounded drain activated; iOS/Android implementation and operational tests pending |
| Transport/proxy security | BLOCKED | Initial public target SC1/WSS retains verified TLS; every claimed carrier requires applicable independent tests; a proxy topology requires accepted specification and independent tests only when a proxied deployment is claimed (the direct-TLS initial topology does not require one); no new raw public transport exception |
| Conformance/interop | BLOCKED | CI validates definitions/vectors, not complete IUT runs. Registered suite is now 189 cases (incl. `CONF-SCW-025`–`042` and recovery cases); registration is not execution and no independent results are added |
| Operational/mobile assurance | BLOCKED | Declared budgets and iOS/Android lifecycle, weak-network, idle-cost and soak evidence required; simulated/compile evidence alone insufficient |
| License | PRESENT | Apache-2.0 LICENSE present and full-text regression test passes |
| Distribution | PROPOSED UPDATE | Draft RFC 0011 proposes maintainer-authorized two-component tags; language artifacts remain downstream. BSR/GHCR gates remain retired. |

## Historical consistency findings disposition

These statuses distinguish source correction from normative acceptance; none
closes a behavioral defect merely because a proposal exists.

| Finding | Current disposition |
|---|---|
| F-01 profile identifiers | Resolved in current source; verify consistency mechanically, do not carry historical mismatch as P0 |
| F-02 completed-ID reuse | Closed: RFC 0004 accepted the increasing-ID/non-reuse rule and the owner pass activated the owning text; runtime test evidence remains open |
| F-03 pre-ACTIVE carrier | Closed: RFC 0003 accepted (local typed cause, native/generic peer failure, no illegal result); owner text activated |
| F-04 HTTP stale-ID conflict | Closed: RFC 0004 accepted per-exchange specialization; the owner pass synchronized the owning clauses |
| F-05 generated import identity | Open, deferred by Decision 0002 as a tracked FILE/source migration (RFC 0005 D5); package path references removed in-tree layout, not a required BSR publication workflow |
| F-06 payload/frame limit | Closed: RFC 0005 accepted the exact encoded MAX/MAX+1 bounds and the fixture correction |
| F-07/F-08/F-09 notifications/illustration/version code | Closed: RFC 0003 proposals accepted and owner cases/classification activated |
| F-10/F-13/F-14/F-15 carriage/re-auth/HTTP row/races | Partial: the RFC 0004 contract is accepted and the owner text corrected (the old “only UNAVAILABLE implies unknown outcome” wording is fixed); runtime race/test evidence remains open |
| F-11/F-12/F-17/F-18 negotiation/floor/bounds | Closed: RFC 0005 accepted with recovery negotiation required for the target; executed bound checks remain evidence |
| F-16 error-layering note | Closed: the owner-file normalization in the acceptance wave synchronized the error-layering text |
| F-19 TLS timer origin | Closed: corrected RFC 0003 tests separate setup from core budget |
| F-20 schema filenames | Resolved references in core; corrected remaining security owner references from `error.proto`/`session.proto` to `errors.proto`/`handshake.proto` in this editorial pass |
| F-21 coverage/counts | Partial, recounted in the 2026-10-30 wave: 593 requirement rows, 189 registered cases, 209 Markdown files. All 25 charter IDs have registry dispositions; the RFC 0010 lifecycle rows are now registered one-to-one with `CONF-SCW-025`–`042`. Structural registry validity is still not coverage/execution |
| F-22 transport/documentation edges | Partial: WS/HTTP query-policy rationale and WS malformed-suffix 1007 vectors now explicit. WSS credential-query rejection, HTTP missing-auth anonymous qualification, over-max budget robustness, inherited H1/H2 body framing, 504 status mapping and stale trace directories remain tracked owner work |

Deferred scope: UDP/QUIC, logical-session resumption, reliable-session RPC
reconciliation and automatic mutation replay. Required update recovery is not
among the deferrals. Classical SC1 makes no post-quantum or application-E2EE
claim. Every future supported feature needs its own accepted contract/evidence.

## Verification record for this branch

2026-10-30 acceptance-wave recount, executed locally in this repository
during the manifest integration pass:

| Command | Result | What it establishes |
|---|---|---|
| `python3 scripts/validate-repo.py requirements manifests` | Passed | 593 requirement rows/definitions with every registered requirement traced and unique; 189 registered `CONF-*` cases across the suite manifests (`sc1-wss.yaml` now carries `CONF-SCW-025`–`042` as registered, not-executed rows). Registration is not execution |
| `python3 scripts/validate-schema.py` | Passed | Pinned Buf format/lint/build/initial FILE baseline and all 13 schema regression tests, executed against the current reviewed revision: seven pinned initial files plus the documented eighth file `recovery_profile.proto` (MIGRATION.md §8 post-baseline addition), including hash-verified historical archive checks |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | Passed, 4 tests | Complete license plus three proposed-context fixture lint checks |

Structural recount (grep/parser based): 593 requirement rows in
`requirements.yaml`; 189 registered `CONF-*` case IDs across
`conformance/manifest/*`; 209 Markdown files. The full
`validate-repo.py all` links run (requirements, manifests, vectors, links,
RFCs, markdown, boundary) passes locally — re-verified on the branch's
reviewed revision on 2026-10-30; the earlier whole-run row of
2026-10-28 (543 requirement definitions/rows, 141 registered cases, 204
Markdown files) remains the count of that historical run.

These are structural results, not 185 executed peer cases. Registration only
formalizes planned cases for execution (both roles), which has not happened.

Not executed: downstream Rust/Go alignment, deterministic Noise generation,
live bidirectional interoperability, deployment lifecycle/proxy/revocation tests,
mobile bridge/device tests, performance/soak or an independent external security
review. Specialist proposal review is advisory, not independent release approval.

## Remaining release sequence

1. Record a specification freeze: pin the exact accepted specification, README
   and manifest revision (RFCs 0001–0010 plus ADR-011) and the conformance
   suite at the same revision, through a dedicated freeze decision.
2. Align separate Rust/Go implementations, generated types and host-policy
   contracts to that same frozen revision; the transitional draft-1/local-1
   byte sets are superseded alignment targets. Retain regression tests.
3. Execute the [mobile](../conformance/plans/mobile-v1.md),
   [recovery](../conformance/plans/update-recovery.md) and
   [SC1](../conformance/plans/secure-channel.md) plans in both independent
   roles for every claimed profile, including the `CONF-SCW-025`–`042`
   lifecycle rows and recovery cases; preserve exact evidence and
   independently derived Noise vectors.
4. Complete the declared operational/mobile budgets (lifecycle, weak-network,
   idle-cost, soak) and proxy/transport-security evidence for every claimed
   carrier and, when a proxied deployment is claimed, the accepted proxy
   topology.
5. Complete the independent human security review, then finalize guides,
   declaration/profile claims and maintainer-authorized release notes.

No tag, commit, push, production release or conformance verdict is created by
this assessment.
