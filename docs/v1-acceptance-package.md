# v1 specification acceptance package

Status: active work plan. Governance, RFCs 0001–0010 and ADR-011 are accepted;
execution, freeze and release-scope work remains in progress. This is not a
specification freeze or release approval.
Baseline: `94404d7378136d8b6c88ece28bf945c88d1653ba` (2026-10-29 working tree),
with the acceptance wave reviewed against `0e8b0f8`. Approved revisions: RFC
0007 and RFC 0009 accepted 2026-10-29; RFCs 0001, 0002, 0003, 0004, 0005, 0006,
0008 and 0010 accepted 2026-10-30 via
[Decision 0002](decisions/0002-sdd-acceptance-wave.md), which applied the owner
files and normalized the recovery manifest; RFC 0005 D5 (`go_package`) is
explicitly deferred with a tracked FILE/source follow-up. Scope is
specification-first, canonical SC1 over verified WSS first, standardized update
recovery and applicable mobile lifecycle. One active maintainer is the public
roster; the bootstrap ratification is
[Decision 0001](decisions/0001-bootstrap-ratification.md).

## Current progress and approval boundary

[RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md) is
accepted. The public bootstrap record, active roster, roster-based quorum and
acceptance/freeze/release separation are in
[`GOVERNANCE.md`](../GOVERNANCE.md), [`MAINTAINERS.md`](../MAINTAINERS.md) and
[`CONTRIBUTING.md`](../CONTRIBUTING.md). [RFC 0007](../rfcs/0007-secure-channel-device-authorization.md),
[RFC 0010](../rfcs/0010-sc1-host-authorization-lifecycle.md) and
[ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md)
are accepted; the canonical v1 mapping, first-envelope rule, Upgrade admission
and direct-TLS topology are activated in the owning security/transport docs,
and RFC 0010's lifecycle contract `SNTR-DAUTH-011`–`024` is active in
`device-authorization.md` §5, normative now that RFC 0008 is accepted via
Decision 0002 along with RFC 0010's lifecycle contracts already noted above.
`SNTR-SC1-WSS-V1` is registered in
[`conformance/profiles.yaml`](../conformance/profiles.yaml) with executable
case specifications in [`sc1-wss.yaml`](../conformance/manifest/sc1-wss.yaml)
(`CONF-SCW-025`–`042` including the registered lifecycle rows). Registration
is not execution: no core, recovery or mobile execution result is claimed,
no release approval is implied, and the schema source migration, evidence
tooling, freeze and stable promotion remain outstanding gates.

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

Increments 1–5 have landed through the recorded decisions. Increment 1 landed
via [Decision 0001](decisions/0001-bootstrap-ratification.md). Decision 0002
completed increment 2 (one accepted contract per RFC, with individual
dispositions recorded for RFCs 0001, 0002, 0003, 0004, 0005, 0006, 0008 and
0010), landed increment 3 (core/parser/mobile owning files activated; the
RFC 0001, 0005 and 0008 contract set consolidated), increment 4 (RFC 0006
owner/IDL-comment map applied, `CONF-URP` cases corrected to the §11
shapes, `SYN-URP-*` requirement rows registered with 008/009 reserved) and
increment 5 (SC1 canonical contract with RFC 0010 lifecycle requirements and
the registered `CONF-SCW-025`–`042` planned rows). Increments 6–9 remain
open: schema source migration (RFC 0005 D5 deferred), evidence tooling,
specification freeze, stable promotion and release authorization. The Rust
implementation at `tinkle-org/syntra-rs` main
(`73f9775043ba2625a823f5cca3fbe92cdf345293`) targets the accepted RFC 0007 §11
canonical contract that Decision 0002 activated against the earlier draft-1
alignment targets, and the implementation's local implementation evidence
does not close the registered cases, independent interoperability or release
gates.

## Specific tooling and consistency work

- Resolved: recovery's IDL and registered cases were reconciled to RFC 0006
  §11 in the acceptance wave — owner/IDL-comment map applied, `CONF-URP`
  cases corrected to the §11 shapes, and the manifest schema plus Python
  requirement patterns extended to admit the recovery owner's `SYN-URP-*`
  family (008/009 intentionally reserved and unassigned) with the actual
  obligations registered. Preserved recovery requirement numbering; no new
  envelope was invented and the existing case identities were kept.
- Declarations already have PASS, FAIL, SKIP, UNSUPPORTED and NOT_EXECUTED.
  Add specification/implementation/suite provenance, evidence references and
  complete role/mode/case selection instead of creating a second verdict model.
- RFC 0009 D4 scoped the two-transport proof: a claim may be made on one named
  transport profile, including SC1 scoped to `SNTR-SC1-WSS-V1`; a proof across
  two named transports is required only when a claim asserts transport
  independence. This scoped rule is accepted and applied in the claim docs
  ([specifications/core/conformance.md](../specifications/core/conformance.md),
  [conformance/claims.md](../conformance/claims.md)); keep it as the rule for
  new owner documents.
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

## Verification record

First-increment verification record, executed locally on 2026-10-29 using
Python 3.14.7 and Buf 1.59.0:

| Command | Actual result | Evidence scope |
|---|---|---|
| `python3 scripts/validate-repo.py all` | Passed: 543 requirement rows/definitions, 141 registered cases, 204 Markdown files checked | Requirement/manifest/vector/link/RFC/Markdown/boundary consistency only |
| `python3 scripts/validate-schema.py` | Passed: format/lint/build/initial FILE gate and all 13 schema regression tests | Unchanged schema declarations and archived compatibility evidence; executed against the current reviewed revision, covering the seven pinned initial files plus the documented eighth file `recovery_profile.proto` (MIGRATION.md §8 post-baseline addition) |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | Passed: all four existing tests | License and proposed public SC1 context-fixture lint, not cryptographic execution |
| `git diff --check` | Passed | Tracked-diff whitespace checks; new documents also covered by repository Markdown validation |

2026-10-30 acceptance-wave recount (manifest integration pass, executed
locally): `python3 scripts/validate-repo.py requirements manifests` passed
with 593 requirement rows/definitions and 189 registered `CONF-*` cases across
the suite manifests (593 unique requirement IDs; `CONF-SCW-025`–`038`
registered against `SNTR-DAUTH-011`–`024` (one per requirement), and
`CONF-SCW-039`–`042` added separately as the registration splits of
`025`/`030` — the out-of-band and valid-but-unauthorized enrollment variants
after `025` and the mid-connection rebinding variant after `030`), and 209
Markdown files in the working
tree by recount. `validate-schema.py` (13 tests against the current revision, including `recovery_profile.proto` per MIGRATION.md §8) and the four unit tests
passed on this revision. The whole-run `validate-repo.py all` also passes on
this revision (requirements, manifests, vectors, links, RFCs, markdown,
boundary), re-verified locally on the reviewed branch on 2026-10-30;
anchor and whitespace hygiene is clean. Registration is not execution:
these numbers are structural, not executed verdicts.

No Go/Rust conformance execution, mobile-device run, independent security
approval, commit, push or release was performed as part of these verification
records; ratification and normative acceptance here refer only to the
recorded Decisions 0001/0002. Decision-record negative checks in RFC 0009
remain planned human/tooling acceptance work; no machine validator was added.
