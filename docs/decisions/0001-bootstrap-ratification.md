# Decision 0001 — Bootstrap ratification

Status: approved by the repository owner; effective on publication of this
record. This is a process decision, not a protocol acceptance, conformance
result or release authorization.

## Identity and scope

| Field | Value |
|---|---|
| Record identifier | `BOOTSTRAP-2026-10-29` |
| Decision kind | bootstrap-ratification |
| Decision state | approved |
| Date | 2026-10-29 |
| Public decision link | The merge commit publishing this record; the owner also verified repository administration through the GitHub API on 2026-10-29 |
| Reviewed repository and commit | `tinkle-org/syntra` at `94404d7378136d8b6c88ece28bf945c88d1653ba`, plus the governance/roster diff in the publishing change |
| Scope | `GOVERNANCE.md` §§2/3/6/8; `CONTRIBUTING.md` §4; `rfcs/README.md` approval text; `MAINTAINERS.md` |
| Author and decision owner | `oscarlaw` (same person; disclosed) |
| Authority | `GOVERNANCE.md` as in force before this decision, with the owner's repository-administration authority verified |
| Supersedes | None |

## Approval and security review

| Field | Value |
|---|---|
| Required maintainer quorum | The existing two-maintainer quorum was **not** met. This is a one-time owner-ratified bootstrap transition, not a second approval and not a precedent for bypassing future governance. |
| Approvals | `oscarlaw`, repository owner, by the public act of publishing this record after verifying `permissions.admin = true` on `tinkle-org/syntra` |
| Self-review disclosure | The approver is the author and the initial sole active maintainer. No independent approval is claimed. |
| Security relevance | Process change only. No wire behavior, schema, credential handling or runtime behavior changes. |
| Human security review | Not applicable to this process decision. Security-adjacent protocol decisions still require the reviews described by `GOVERNANCE.md` §3 and RFC 0009 D2; an independent production review remains a separate release gate. |
| Independence | Self-review for governance. No second maintainer exists. |
| Normative objections | None recorded. |
| Advisory analysis | None counted as a vote. |

The owner authority is established by the public repository administration
record, not by a claim in this document. The GitHub API response used for this
record reported `admin: true`, `maintain: true`, `push: true` for `oscarlaw`
on `tinkle-org/syntra`. That verification establishes ownership; it is not a
second maintainer approval and does not establish independent security review.

## Compatibility and activation

| Dimension | Disposition |
|---|---|
| Binary wire | Unchanged |
| Behavior | No peer behavior changes. Approval quorum and roster publication change. |
| Generated source / FILE | No impact |
| Baselines | None touched |
| Migration | No downstream migration required |
| Activation | This record, `MAINTAINERS.md`, the quorum text in `GOVERNANCE.md` §3, `CONTRIBUTING.md` §4 and `rfcs/README.md` land together |
| Claims excluded | This record accepts no RFC, activates no protocol behavior, registers no profile or case and authorizes no release |

## Verification and release evidence

| Field | Value |
|---|---|
| Repository/schema checks | `python3 scripts/validate-repo.py all`; `python3 scripts/validate-schema.py`; `python3 -m unittest discover -s tests -p 'test_*.py' -v`. Results are recorded in the publishing change. |
| Specification and suite pins | Not applicable to this process decision |
| Implementations | Not applicable |
| Matrix | Not applicable |
| Case results | Not applicable; no conformance case is created or executed by this record |
| Declared bounds | Not applicable |
| Deployment/mobile review | Not applicable |
| Independent security approval | Not claimed; remains required where `GOVERNANCE.md` §3 or RFC 0009 D5 says so |
| Outstanding gates | Future normative decisions still need their own acceptance records; stable release still needs the RFC 0009 D5 evidence |

## Decision

Adopt the one-time bootstrap transition proposed by RFC 0009 D1/D2:

- `oscarlaw` is the initial active maintainer and repository owner.
- With exactly one published active maintainer, that maintainer's explicit
  approval may accept a normative RFC, governance amendment or release
  decision. The record MUST disclose when the approver is also the author.
- With two or more active maintainers, normative decisions require at least two
  distinct active-maintainer approvals. One person cannot count twice.
- With no active maintainer, normative acceptance and release authorization
  are blocked. Silence, a bot merge and CI success are not approvals.
- No unresolved normative maintainer objection may be ignored. Security review
  requirements and the independent production gate in RFC 0009 D5 remain.

This decision does not accept RFCs 0001–0008 by itself. Each requires its own
recorded decision. It does not authorize a tag or stable release.
