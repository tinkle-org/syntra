# Public decision record template

Status: informative preparation format, not an approval or an implemented
validation schema. [RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
(accepted) adopted this format for the bootstrap ratification, RFC
acceptance, specification freeze and release authorization records;
[governance](../GOVERNANCE.md) and the recorded decisions ([Decision 0001](decisions/0001-bootstrap-ratification.md),
[Decision 0002](decisions/0002-sdd-acceptance-wave.md)) determine authority
and quorum.

Copy the record below into the relevant public RFC/PR discussion and retain
a repository copy or an immutable link when the decision is recorded. Fill
actual identities and references only; retain pending fields where evidence
does not exist. A checked box or the word approved written by a contributor
does not establish the owner's or reviewer's approval.

Use a separate record for each decision kind. A bootstrap record does not
accept protocol RFCs; an RFC record does not authorize a release. A joint
decision on several RFCs lists each reviewed revision, scope and disposition
individually. Do not blanket-approve an unspecified future owner diff.

## Record to copy

### Identity and scope

| Field | Value to supply |
|---|---|
| Record identifier | Unique public RFC/PR decision reference; pending until assigned |
| Decision kind | bootstrap-ratification / rfc-acceptance / specification-freeze / release-authorization |
| Decision state | pending / approved / rejected / superseded; pending by default |
| Date | Actual decision date; pending until decided |
| Public decision link | Exact owner/maintainer decision comment or review, not just the PR URL |
| Reviewed repository and commit | Repository plus full commit SHA of reviewed content |
| Scope | Exact RFCs, documents, schema options, profiles and claims covered |
| Author and decision owner | Actual public accounts; disclose when they are the same person |
| Authority | Governing policy revision/section and active-roster revision |
| Supersedes | Prior decision link, or explicitly none |

### Approval and security review

| Field | Value to supply |
|---|---|
| Required maintainer quorum | Rule actually in force for this decision |
| Approvals | Distinct actual maintainer accounts, exact approval links and reviewed revisions |
| Self-review disclosure | Author/approver/reviewer overlap, or explicitly none |
| Security relevance | Applicable security scope, or reason security review is inapplicable |
| Human security review | Actual reviewer account, review basis, revision, scope, findings and disposition; pending if absent |
| Independence | Independent / self-review / advisory-only, with affiliations/conflicts and author/implementer relationships |
| Normative objections | Each objection and its resolution link; unresolved objections stay visible |
| Advisory analysis | Optional automated/AI findings, labeled advisory and not counted as votes |

For bootstrap ratification additionally record verified owner authority,
the initial active maintainer, the exact authorized governance/roster diff,
and the explicit acknowledgment that the old two-maintainer quorum was not
met. Without that special public owner act or the original quorum, leave the
transition pending. A private conversation or this template is not ratification.

### Compatibility and activation

| Dimension | Required disposition |
|---|---|
| Binary wire | Unchanged / compatible additive / breaking, with reason and exact changes |
| Behavior | Affected peer semantics, pre-stable freeze or major-version decision, and migration consequences |
| Generated source / FILE | Import/options/descriptor impact; no impact if unchanged, not inferred from WIRE |
| Baselines | Exact retained baseline paths/hashes and any separately authorized transition; no silent replacement |
| Migration | Relevant MIGRATION/CHANGELOG references, rollout order and legacy treatment |
| Activation | Exact owning spec/schema/registry/case changes; landed revision or pending follow-up |
| Claims excluded | Profiles/features not accepted or not verified by this decision |

The reviewed commit can precede the commit that adds this record; do not try
to embed a commit's own SHA in itself. Link the activation/recording revision
after it exists and verify that the reviewed content did not change. Changes
to the reviewed behavior require renewed approval of that affected scope.

### Verification and release evidence

| Field | Value to supply |
|---|---|
| Repository/schema checks | Actual command, tool version, result and retained log reference |
| Specification and suite pins | Full revisions used to define the executed requirements/cases |
| Implementations | Repository/full commit, language/runtime/crypto versions and independence basis |
| Matrix | Registered profile, capability, initiator/host roles and SC1 mode for each run |
| Case results | Case ID, verdict and immutable log/artifact reference; digest for retained artifacts |
| Declared bounds | Count/byte/time limits and operational/mobile thresholds declared before runs |
| Deployment/mobile review | Host lifecycle/persistence/proxy contract and actual device/OS/bridge evidence |
| Independent security approval | Actual composition-review decision, scope, reviewed revision and resolved findings |
| Outstanding gates | Every missing run, approval, registration or unresolved finding |

Use existing suite verdicts: PASS, FAIL, SKIP, UNSUPPORTED and NOT_EXECUTED.
Missing execution is NOT_EXECUTED, not PASS. Correct optional-feature refusal
retains the suite's verdict semantics but does not prove support for a required
feature. Structural checks, public context lint, codec/vector checks, live
interop, mobile runs and security review are different evidence layers.

Evidence fields in an RFC-acceptance record can be pending when they are
explicit release gates rather than unresolved contract questions. A release
authorization cannot omit required gates. Explain inapplicability per field;
an unexplained empty field is missing evidence, not an exemption. Retain failed
runs and their fixes/retests rather than replacing the history with a summary.

### Decision

State the exact decision, rationale, effective policy/specification revision
and permitted claims. List remaining work and responsible actual owners, or
mark assignment pending. For a freeze explicitly state that independent
execution/release authorization is separate. For a stable release identify
the exact authorized revision, version and reviewed notes, and establish
that all applicable bundle gates are complete.

## Review checks

These are proposed human checks, not capabilities of the current validator:

- Confirm the public approval belongs to the stated account and reviewed SHA.
- Confirm quorum under the policy that applied before the decision; do not
  use a proposed rule to approve itself without disclosed bootstrap ratification.
- Reject duplicated identities, a changed reviewed revision, concealed
  self-review, unresolved objections or AI analysis counted as approval.
- Verify scope, evidence provenance and references, not just that links exist.
- Keep acceptance, activation, verification and release outcomes separate.
- Do not approve a stable release with missing required role/mode/case results,
  unresolved applicable security findings or absent independent review.
- Redact production credentials and embargoed vulnerability details; retain
  public dispositions through the existing security process instead.
