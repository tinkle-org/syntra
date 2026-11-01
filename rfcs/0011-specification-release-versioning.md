# RFC 0011: Specification release versioning and publication

- RFC: 0011 (draft number; subject to assignment at acceptance)
- Title: Specification release versioning and publication
- Author(s): Pending public attribution
- Status: Discussion
- Date: 2026-10-31
- Target version: Pre-stable release-process decision; first stable release
  proposed as Syntra 1.0
- Relates to: [GOVERNANCE.md](../GOVERNANCE.md) §§3–5/8,
  [RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md) §§3 D3/D5,
  [ADR-009](../specifications/decisions/ADR-009-versioning-compatibility.md),
  [versioning.md](../specifications/core/versioning.md),
  [RELEASE.md](../RELEASE.md), and [schema-registry.md](../docs/schema-registry.md)
- Reviewers: Pending maintainer assignment and public review

This document is a proposal, not an accepted governance decision, a
specification freeze, or authorization to publish a release. The existing
governance, Release Please process, and RFC 0009 release gates remain in force
until this proposal is accepted and its changes are activated. Nothing here
claims that a release, interoperability result, or security review exists.

## 1. Summary

Propose maintainer-selected two-component specification releases, such as
Syntra 1.0 and 1.1, identified by Git tags `v1.0` and `v1.1`. Tags are the
release; no packages, archives, or GitHub Releases are produced. Release
candidates use a maturity suffix, such as `v1.0-rc1`; the suffix is not a
third protocol-version component. Propose replacing Release Please with a
manual, authorization-gated publishing workflow after this RFC is accepted.
The existing integer wire version, schema package, profiles, and downstream
implementation versions remain distinct. This proposal changes no peer or
wire behavior.

## 2. Motivation

Syntra releases a governed protocol specification and conformance contract,
not a language package. Conventional Commit categories are not a reliable
measure of the importance or compatibility of specification changes.
Maintainers need to select the version and scope explicitly, while retaining
automated validation, immutable release identities, and a curated changelog.

The current document release configuration uses three-component prerelease
versions. No standalone specification-only `v1.0.0-rc.1` tag exists. Historical
implementation-era tags, including `syntra-core-v1.0.0-rc.1` and
`bindings/go/v1.0.0-rc.1`, are separate records and do not establish a new
specification-release baseline.

## 3. Proposal

The proposed owner edits, if accepted, are in §4. All statements in this
section are proposed policy; they do not activate themselves.

### D1. Specification release identifiers

- Stable releases use `vMAJOR.MINOR`; candidate tags use
  `vMAJOR.MINOR-rcN`, where the numeric components are decimal, have no
  leading zeroes, and `N` is positive. For example, `v1.0-rc1` precedes
  `v1.0`. Versions are compared numerically, so 1.10 follows 1.9.
- The first stable specification release is intended to be `v1.0`, subject
  to the existing freeze, evidence, and release-authorization gates. A
  candidate is identified by the `-rcN` suffix and changelog section; there is
  no GitHub prerelease flag, and it is not a stability claim.
- These release identifiers are not Semantic Versioning 2.0. Downstream
  implementation projects choose their own versioning policies.
- Published tags name exact commits and are never moved or reused. A
  release and its notes identify the repository, tag, full commit SHA,
  release scope, maturity, profiles, and relevant decision/evidence links.

### D2. Compatibility and negotiation

Keep the existing negotiated integer `Frame.version`, `ClientHello` range,
`syntra.v1` schema namespace, profile identifiers, and profile-specific
capability negotiations. Neither the minor component nor an RC suffix is
transmitted or negotiated by this proposal. An implementation claiming a
specific release also identifies its applicable profiles and evidence;
wire version `1` alone does not prove conformance to every 1.x release.

Within an established major line, a minor release is intended for compatible
extensions and corrections, subject to the existing RFC, security,
conformance, and schema checks. Optional-feature deprecation and removal keep
the notice and compatibility rules in governance and the owning profile; a
minor release is not a promise that an explicitly retired optional feature
remains available. A breaking core protocol change requires the existing
major-version RFC and migration process. A change to actual wire negotiation
requires its own accepted design and is not authorized here.

### D3. Errata and corrections

Record an editorial or technical error against the affected published
release without altering its tag. The erratum records its identity, affected
revision and location, classification, status, reviewed disposition, and
links to the public decision or correction. A behavior-changing correction
follows the existing normative RFC and compatibility process; an erratum is
not a shortcut for changing peer obligations. Security reports continue to
follow [SECURITY.md](../SECURITY.md), including embargo handling. Accepted
corrections can be incorporated into a later appropriate release.

### D4. Release decisions and evidence

Keep RFC acceptance, specification freeze, and release authorization as
separate decisions. A maintainer-prepared release PR identifies its proposed
version, scope, accepted RFCs, compatibility disposition, profiles, and
changelog. After it merges, a freeze record identifies the exact merged
specification, schema, requirements, profiles, cases, and fixtures revision.

The public release decision names that exact full commit SHA and version,
the active roster and applicable quorum, actual approval and objection
dispositions, scope, reviewed release notes, and evidence. Keep the decision
outside the commit it identifies, avoiding a self-referential commit SHA.
Changes affecting the frozen scope require renewed review and any affected
verification. Acceptance, a green repository check, or an RC tag alone does
not establish stable release readiness.

This RFC would supersede only RFC 0009 D5's instruction to keep
Release Please in prerelease mode. It would not relax D5's independent
pure-Go/Rust role and mode matrix, required recovery/mobile and operational
evidence, or independent human security review for the selected initial
bundle. The general bootstrap fixture alternative does not replace those
bundle-specific gates.

### D5. Publication safeguards

After public acceptance, replace Release Please with a manually dispatched
workflow that validates an explicitly selected tag, full commit SHA, and
public decision. It must run trusted workflow code from the protected main
branch, verify that the target is a merged main-branch ancestor, and rerun
repository, schema, regression, and workflow checks against that exact
commit. Schema checks are unconditional at release time, even where a normal
CI workflow is path-filtered.

The publisher verifies the binding between version, target SHA, public
decision and active maintainer approvals, and rechecks the decision before
writes. The proposed format in `RELEASE.md` uses a maintainer-authored
`SYNTRA-APPROVE` comment bound to the SHA-256 of the decision body; a later
`SYNTRA-OBJECT` blocks publication until that maintainer approves the current
body. Changing the body invalidates approvals. With the current single
maintainer, one explicit approval suffices with self-review disclosed. Human
review remains responsible for evidence, independence, applicable verdicts,
and objections outside the structured format. The format and implementation
require review before acceptance.

Run validation without publication credentials. Restrict the publishing
identity and `v*` tag namespace, and require an administratively configured
protected environment. An environment's single approval is not a substitute
for roster quorum. With one active maintainer, do not require a distinct
environment reviewer in conflict with the existing disclosed self-approval
rule. Restrict the release workflow and environment to trusted main, and
ensure an automatically created, unprotected environment cannot authorize a
release.

Initially reject an existing tag. If tagging fails after partial progress,
permit a reviewed retry only when the existing tag resolves to the same
approved commit; never move a tag. Serialize concurrent publication attempts
and recheck tag identity at write time. Candidate maturity is carried by the
`-rcN` suffix and changelog section, not by GitHub prerelease or
latest-release metadata.

GitHub immutable releases (or tag protections/rulesets) may protect future
published tags if enabled by an administrator. The tagged changelog and
commit remain the canonical release snapshot; no release assets exist.

## 4. Detailed design and activation map

The proposed change affects release labels, documentation, workflow and
release authorization only. No message fields, framing, state transitions,
timeouts, resource budgets, profiles, requirement IDs, or peer behavior are
added or changed. Existing schema baselines and reserved fields remain intact.

The changes prepared in this branch are proposed for activation on acceptance:

1. Update `GOVERNANCE.md`, `RELEASE.md`, `docs/schema-registry.md`,
   `docs/schema-release-checklist.md`, `README.md`, and
   `docs/implementer-guide.md`. Correct active status and version references
   while preserving dated history. Amend ADR-009 or its owner text only to
   the extent actually approved by the decision.
2. Preserve the repository and schema validation workflows. Add a
   publication workflow with the controls in D5, and remove Release Please's
   workflow and configuration atomically with activation.
3. Configure and verify the environment, tag protections, required CI
   checks, publishing identity and permissions outside the repository.
   These settings are prerequisites, not consequences of adding YAML.
4. Consolidate changelog history and record the actual migration in
   `MIGRATION.md`. Retire the open Release Please PR after the new policy is
   active. Do not rename or delete historical implementation tags.
5. Make a reviewed post-release baseline change only when a new stable
   baseline exists. Never rewrite the initial compatibility archive merely
   to make validation pass.

The publication workflow is prepared in this branch but refuses to publish
while this RFC remains Draft. Its read-only validation job does not itself
verify release authority or produce a conformance result.

## 5. Alternatives considered

1. Keep Release Please and override generated versions. This retains useful
   automation but still needs explicit protocol-scope review and does not
   natively make the proposed two-component policy authoritative.
2. Use Semantic Versioning for specification tags. This supplies a patch
   component and broad package-tool support but does not match the proposed
   two-component public protocol naming.
3. Negotiate major and minor on the wire. This requires a separate protocol
   design, compatibility analysis and migration; a release-label decision
   alone is not enough.
4. Do nothing. Existing release automation and three-component labels remain
   in force, including the current need for manual scrutiny of release scope.

## 6. Compatibility

Binary wire, negotiation, Protobuf declarations, generated-source options,
reserved identifiers, and existing profiles are unchanged by this proposal.
No existing protocol requirement or conformance case is retired. The visible
release-label change is not SemVer: consumers using SemVer-only tag parsers
must instead pin the exact tag or commit, or update their tooling. Downstream
SDK versioning and package-manager requirements remain downstream-owned.

Historical crate and Go tags retain their original identity and meaning.
The proposed `v1.0-rc1` is a new specification candidate, not a rename or
representation of the old RC-1 implementation release. A separate accepted
major-version RFC remains necessary for an incompatible wire change.

## 7. Security considerations

Publication authority and tag integrity are security-sensitive. A malicious
workflow, forged decision, unprotected environment, stale approval, tag race,
or compromised publishing identity can misrepresent a release. Use public,
revision-bound decisions, least privilege, trusted workflow code, protected
tags, explicit environment configuration, and fail-closed handling. Validate
untrusted inputs without shell interpolation and do not execute target
scripts in a write-privileged publication job.

Security-adjacent review of the workflow and authorization format is required
before activation. This process change does not authorize security fallback,
weaken production transport policy, or waive independent security review.

## 8. Test plan and acceptance criteria

- [ ] Public maintainer decision covers this RFC and the exact governance diff;
      self-review and security review are disclosed as applicable.
- [ ] Candidate version syntax, numeric ordering, malformed identifiers,
      full-SHA validation, ancestry and duplicate-tag handling are tested.
- [ ] Automated approval checks reject missing, stale, duplicated, revoked,
      non-maintainer and wrong-version/wrong-revision approvals, and fail
      closed on an unresolved objection or absent environment protection.
- [ ] Candidate/stable flags, exact-target validation, concurrent attempts,
      partial publication and recovery are tested without a real release.
- [ ] Repository checks, schema checks, Python tests, and actionlint run;
      record actual commands and results separately from release evidence.
- [ ] No new protocol conformance requirement or wire test is claimed; this
      proposal changes no on-wire behavior. Applicable existing conformance
      and independent security evidence remain required for stable release.

## 9. Drawbacks and risks

Two-component identifiers may not be understood by tools that require
SemVer. Errata and a new minor release are less convenient than editing a
published tag. Manual authorization and a sole maintainer concentrate
responsibility; a protected environment does not prove independent review or
all evidence. Automated approval parsing adds a security-sensitive component
that needs its own review and regression tests before it can publish.

## 10. Unresolved questions and blockers

1. Public maintainer approval and security review of this RFC and its owner
   changes are pending; no authority is inferred from drafting it.
2. The proposed machine-readable approval/objection format and its trusted
   active-roster source require maintainer and security review. GitHub
   environment approval alone is not the complete quorum record.
3. The administrator must choose and verify a publishing identity compatible
   with tag rulesets and configure the environment and repository protections.
4. The first stable bundle still lacks its required freeze, independent
   interoperability and security review, recovery/mobile evidence, and final
   authorization. This proposal cannot satisfy those gates.

## Appendix: References

- [RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md),
  [decision record template](../docs/decision-record-template.md), and
  [current release readiness](../audits/v1-release-readiness.md).
- [RFC Editor errata](https://www.rfc-editor.org/series/rfc-errata/),
  [Semantic Versioning 2.0](https://semver.org/spec/v2.0.0.html), and
  [Matrix specification release process](https://github.com/matrix-org/matrix-spec/blob/main/meta/releasing.md).
