# Syntra v1 release readiness — current assessment

Assessment refreshed: 2026-10-30 from accepted specification and merged implementation source state; historical test commands were not rerun.
Scope: current specification-only repository and selected
mobile v1 target. Overall verdict: **BLOCKED**. This is not a tag, maintainer
approval, conformance declaration or independent security certification.
The [October 19 snapshot](history/v1-release-readiness-2026-10-19.md) is retained
as history; its source counts, distribution, license and profile-ID assertions
do not override current sources.

## Selected target and authority

The first stable bundle requires SC1/WSS, standardized update recovery and
applicable mobile lifecycle evidence. Recovery is a **Syntra-owned, optional,
post-ACTIVE negotiated profile** required for this specific release bundle;
a Core-only conformance claim remains valid on its own terms. [RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
accepted this release scope and the one-active-maintainer governance transition;
the public ratification and roster are [Decision 0001](../docs/decisions/0001-bootstrap-ratification.md)
and [MAINTAINERS.md](../MAINTAINERS.md).

[RFC 0007](../rfcs/0007-secure-channel-device-authorization.md) and
[ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md)
are **Accepted**; canonical `syntra.sc1.v1` on verified direct TLS 1.3 WSS
has an accepted owner contract and registered `SNTR-SC1-WSS-V1` profile
(`CONF-SCW-001`–`024`). Those registrations are not executable PASS results.
The Rust implementation merged [PR #15](https://github.com/tinkle-org/syntra-rs/pull/15)
to `main` at `73f9775043ba2625a823f5cca3fbe92cdf345293` and documents
partial case coverage; no independent Go/Rust interop verdict follows.

RFCs 0001–0006 and 0008 remain Draft and need separate decisions and
synchronized owner/schema/conformance edits. No draft behavior becomes
normative merely because it exists in Rust. The [acceptance package](../docs/v1-acceptance-package.md)
and [recovery placement rationale](../docs/recovery-profile-boundary.md)
identify the remaining review decisions. **Overall BLOCKED** refers to
the selected stable release, not to the already accepted SC1 specification.

## Current area assessment

| Area | Verdict | Current finding / next gate |
|---|---|---|
| Core/parser | BLOCKED | RFCs 0001/0008 select raw oneof, body-space, unknown/reserved and precedence proposals; owner edits and raw-wire cases await acceptance |
| Handshake | BLOCKED | RFC 0003 selects local typed causes/native peer failure, fail-close notifications and phase timers; existing contradictory owner text not activated yet |
| RPC/HTTP/auth carriage | BLOCKED | RFC 0004 selects ordered increasing IDs, native-close reuse rejection, terminal gate and per-profile credentials; compatibility and behavioral execution pending |
| Negotiation/bounds | BLOCKED | RFC 0005 selects RFC 0006 negotiation, concrete bounds and serialized-byte fixture correction; owning clauses/cases not synchronized before acceptance |
| Schema tooling | STRUCTURAL PASS ONLY | Buf format/lint/build/FILE and 13 schema tests pass; no schema edits. Legacy `go_package` remains; its proposed downstream path needs explicit FILE/source migration |
| Baseline profile identifiers | CONSISTENT | Current transport specs/suite agree: `SNTR-HTTP-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`; no alias/rename needed |
| SC1 | SPEC ACCEPTED / RELEASE BLOCKED | RFC 0007/ADR-011 accepted; `SNTR-SC1-WSS-V1` and 24 cases registered. Rust merged canonical v1. Full case execution, independently derived Noise vectors, Go/Rust interop and external security review remain pending |
| Authorization lifecycle | BLOCKED | Same-principal/current-enrollment gate, provisioning/rotation crash contracts, pins, fail-closed store behavior and verified deployment revocation bounds still need acceptance and execution |
| Update recovery | BLOCKED | Required target: RFC 0006 §11 selects fresh rounds, local overflow isolation, scoped generations, snapshot and durable state/checkpoint semantics; owner/IDL synchronization and independent crash tests pending |
| Mobile/runtime bounds | BLOCKED | RFC 0008 selects suspension/queue deadlines, connection generations, reconnect, active-execution accounting and bounded drain; downstream/mobile implementation tests pending |
| Transport/proxy security | SC1 DIRECT TOPOLOGY ACCEPTED / DEPLOYMENT BLOCKED | Accepted initial public topology is direct verified TLS 1.3 WSS termination at the host. Proxy termination is deferred, not an initial-release requirement; accepted topology deployment evidence remains pending |
| Conformance/interop | BLOCKED | Structural checks register 24 SC1/WSS cases but do not execute them. Independent SC1, recovery, mobile and Go/Rust results are not established |
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

## Historical verification record (2026-10-28; not rerun here)

The following was executed during the earlier audit change, not on this
2026-10-30 documentation refresh:

| Command | Result | What it establishes |
|---|---|---|
| `python3 scripts/validate-repo.py all` | Passed | 543 requirement definitions/rows; 141 registered cases; manifest/vector/link/RFC/Markdown/boundary consistency |
| `python3 scripts/validate-schema.py` | Passed | Pinned Buf format/lint/build/initial FILE baseline and all 13 schema tests, including hash-verified historical archive checks |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | Passed, 4 tests | Complete license plus three proposed-context fixture lint checks |

The new context test first failed with the fixture absent, then passed after
the public JSON was added. It checks exact context/prologue bytes, mode/carrier
coverage and negative-recipe traceability. It does not execute negative peer
rejections, Noise operations, or a transport. No schema baseline/generator
output was changed. These are historical structural results, not 141 executed peer cases.

Not executed: downstream Rust/Go alignment, deterministic Noise generation,
live bidirectional interoperability, deployment lifecycle/proxy/revocation tests,
mobile bridge/device tests, performance/soak or an independent external security
review. Specialist proposal review is advisory, not independent release approval.

## Latest known repository state (not an execution rerun)

At SDD `main` commit `0e8b0f8a4a789cb3d6d00b993e281867d2325e06`,
the merged PR #18 reports successful repository validation with **555 requirement
definitions/rows, 164 registered cases and 206 checked documents**. These
figures supersede the preceding snapshot for current *definitions*, but do
not establish that this documentation change reran those commands. The 164
cases include 24 SC1/WSS cases; no formal implementation verdict is implied.
The separately merged Rust `main` commit `73f9775` reports local test
evidence in its implementation ledger, not independent cross-language proof.

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

This assessment does not authorize a stable tag, assert a conformance verdict,
or replace the required public maintainer and security review records.
