# Governance

This document defines who decides what in Syntra, how normative changes
are approved, how breaking changes are handled, and how a protocol
release becomes stable.

## 1. Principles

1. Specification authority is explicit
   (`specifications/architecture.md` Sec. 8). Code follows spec.
2. Independence: no private product, company, or infrastructure controls
   protocol behavior.
3. Open review: normative changes happen in public via RFCs, with
   rationale recorded.
4. Safety: security review is mandatory for security-adjacent changes;
   wire compatibility is checked mechanically (Buf) and behaviorally
   (conformance suite).

## 2. Roles

- **Contributors** — anyone who opens issues, RFCs, or PRs. Expected to
  follow `CONTRIBUTING.md` and the Code of Conduct.
- **Reviewers** — contributors with a track record whom maintainers
  invite to review. Reviews are advisory.
- **Maintainers** — the approval authority for normative changes,
  releases, and governance amendments. Maintainers are listed in the
  repository's maintainer file or GitHub team when designated by the
  project owners. Until that list is published, the repository owners
  act as interim maintainers. No individual contact address is listed
  here; use repository GitHub flows.

Maintainer decisions are recorded on the relevant RFC or PR. Absence of
a published maintainer list does not block non-normative contributions.

### Maintainer responsibilities

In addition to the approval authority above, maintainers are responsible
for:

- Triaging issues and RFCs (assigning protocol/security reviewers,
  moving RFCs through Draft → Discussion → Review → decision).
- Enforcing the review bar (`rfcs/README.md`): requirement IDs, client/
  server obligations, bounded resources, unknown-field handling, security
  and compatibility considerations, testable acceptance criteria.
- Tagging releases and publishing notes per Sec. 5; no other role may
  tag a release or push to the schema registry.
- Custody of publication and reporting secrets (BSR push token, private
  vulnerability reports): least privilege, no exposure in logs or PR
  jobs, rotation on suspected exposure.
- Keeping `CHANGELOG.md`, `MIGRATION.md`, and the conformance suite
  consistent with every normative merge.

## 3. Who approves normative changes

- **Non-normative** (typos, clarifications with no behavioral change,
  docs, examples): one maintainer approval may merge.
 - **Normative** (any MUST/SHOULD, wire field, state machine, error code,
   transport mapping, security requirement, conformance assertion):
   - REQUIRES an RFC (`rfcs/README.md`) with a test plan. Only an
     **Accepted** RFC may modify normative behavior; Draft, Discussion,
     Review, Withdrawn, and Superseded RFCs are proposals or history.
   - REQUIRES maintainer approval with quorum: at least two maintainer
     approvals and no unresolved normative objection from a maintainer.
   - REQUIRES security review if the change touches handshake, auth,
     credentials, transport policy, resource limits, errors, or streams.
     Security fixes with exploitation risk are developed privately per
     `SECURITY.md` and disclosed via advisory + `CHANGELOG.md` entry;
     embargo details MUST NOT appear in public issues or PRs.
   - Schema changes (field addition/deprecation/option change, `buf.yaml`
     rule changes) follow this same bar, plus a clean `buf lint`,
     `buf build`, and `buf breaking` gate. Wire-incompatible schema
     changes are breaking (Sec. 4). BSR publication happens only on
     reviewed version tags via the gated publish workflow.
   - MUST update `CHANGELOG.md` (`Unreleased`) and link requirement IDs
     to conformance tests (or tracked placeholders).
- **Governance / process changes** (this file, `CONTRIBUTING.md`,
  `rfcs/README.md`): same bar as normative.

All approvals happen in public on the RFC/PR. Private approvals do not count.

## 4. How breaking changes are handled

A **breaking change** is any wire-incompatible change: repurposed field
numbers/names, changed field types, new required behavior that old peers
cannot ignore, weakened security, or altered failure semantics that
breaks interop.

1. Breaking changes REQUIRE a major-version RFC describing motivation,
   incompatibility, migration path, dual-support window (if feasible),
   and rollout risks.
2. `reserved` values MUST NOT be reused without a major-version RFC.
3. The RFC MUST include updated conformance tests (positive + negative)
   and migration notes for `MIGRATION.md`/`CHANGELOG.md` as applicable.
4. Maintainers MUST NOT merge breaking changes without the quorum in
   Sec. 3 and an explicit major-version designation.

Minor additive changes (new optional fields, new optional capabilities,
clarifications) MUST remain backward compatible per ADR-009.

### Deprecation

Deprecation follows `SNTR-VER-006` (and `SNTR-CAP-007` for optional
capabilities); this subsection states who approves and records it:

1. Marking a field, capability, transport profile, or requirement
   deprecated REQUIRES a normative RFC with a notice period, a documented
   alternative path, and a removal version. The RFC states whether removal
   is major (mandatory feature) or minor-with-notice (optional feature).
2. Deprecated features MUST remain functional until their documented
   removal version. Removal without the documented notice is a breaking
   change handled under Sec. 4.
3. `reserved` field numbers/names are never reused, including after
   removal (see `SNTR-VER-005`).
4. The RFC MUST update the conformance suite (deprecation-notice
   presence fixtures) and `CHANGELOG.md` (Deprecated section).

## 5. How a protocol release becomes stable

A `vX.Y.Z` release is stable when **all** hold:

1. All normative specifications, schemas, and transport/security
   profiles in scope for the release are accepted and indexed with
   requirement IDs.
2. The conformance suite covering those requirements is green on at
   least two independent implementations (or one implementation plus
   independent packet-fixture verification, during bootstrap).
3. `CHANGELOG.md` lists every wire-affecting change with migration notes.
4. Maintainers tag the release and publish notes. The tag is the
   release; branches do not define stability.

Pre-stable development happens on `main` under `Unreleased`. No
stability is implied until a tag meeting the above criteria exists.

## 6. Decision making

- Prefer lazy consensus: silence after adequate review time is consent
  for non-normative work.
- Normative work needs explicit approvals (Sec. 3). Unresolved
  normative objections from maintainers block merge until resolved or
  formally overruled with recorded rationale (requires full maintainer
  agreement to overrule).
- Significant wire-compat or security disputes that cannot be resolved
  in a PR MUST become an RFC or a recorded blocker — never an
  undocumented implementation choice.

## 7. License — alternatives, no selection

> **No license has been selected.** There is no `LICENSE` file.
> All rights reserved pending maintainer decision.

Maintainers will select a license via a public proposal before the first
stable release. Suitable alternatives under consideration:

| Candidate | Implications for this project |
|-----------|-------------------------------|
| **Apache-2.0** | Permissive; explicit patent grant; compatible with broad commercial and open-source use; requires preservation of notices. Common for specifications + reference implementations. Often paired with CC-BY-4.0 for spec text if desired. |
| **MIT** | Highly permissive; simple; no explicit patent grant; minimal obligations (preserve notice). Maximizes reuse but offers less patent clarity than Apache-2.0. |
| **BSD-3-Clause** | Permissive like MIT with non-endorsement clause; no patent grant language. Similar reuse profile. |
| **Dual-license / spec + code split** (e.g., CC-BY-4.0 for spec text + Apache-2.0/MIT for code/schemas) | Respects that specifications and code have different reuse concerns; adds complexity and needs clear file-level labeling. |

Considerations maintainers will weigh publicly: patent clarity,
compatibility with downstream ecosystems (Rust crates, Go modules, etc.),
whether spec text needs a Creative Commons component, and contributor
comfort (DCO sign-off in `CONTRIBUTING.md` anticipates any of the above).

Until a `LICENSE` file is added by maintainers, do not assume any
license. Contributions are accepted under the DCO with the understanding
that the future license will be one of the permissive options above or
a reasoned equivalent proposed in public.

## 8. Amendments

Changes to this file follow Sec. 3 (normative bar). The maintainer list,
once published, lives alongside this file and is updated by the same process.
