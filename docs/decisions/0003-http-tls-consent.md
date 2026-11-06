# Decision 0003: HTTP/TLS maintainer consent and pending adoption

Historical consent record. Its pending acceptance/review disposition is
superseded by [Decision 0004](0004-rfc-0011-0014-acceptance.md) and the
[public acceptance](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482).
The dated fields below retain the evidence available at preparation time; this
does not retroactively assert review of the earlier candidate. Canonical
adoption, independent release review and publication remain separate.

Status: pending public decision. This record preserves actual user consent; it
does not assert RFC acceptance, human security review, freeze or release approval.
It follows the [decision-record template](../decision-record-template.md).

## Identity and scope

| Field | Recorded value |
|---|---|
| Decision kind / state | RFC acceptance / pending |
| Consent report date | 2026-11-03 |
| Decision owner | oscarlaw, the sole active maintainer in [the roster](../../MAINTAINERS.md) |
| Source of consent | User report in this development conversation of the confirmation-tool answer “Approve as maintainer” to “Are you acting as an active maintainer and explicitly approving its normative adoption, including required self-approval disclosure if applicable?” |
| Self-approval disclosure | oscarlaw is the requesting author and approver of the AI-assisted proposal; this is self-approval, not a second reviewer |
| Scope | [RFC 0013](../../rfcs/0013-http-tls-carriers.md): HTTP carrier 4, HTTPS carrier 5, exact HTTP endpoint family and trusted in-process TLS-provider composition, including requested carrier-input ACK clarification |
| Baseline | `tinkle-org/syntra` at `3f7e8ea037fefcc5c86101d23e7722c83e28a0d3`, branch `feature/http-tls-carriers` |
| Initial draft fingerprint | SHA-256 `22fe572cd1f14dfc3d587fcfa3dd554975ecf30bad8c718ebfcc933da8fdcfbe` before this round's corrections; not a Git commit or approval of an unspecified later diff |
| Reviewed final candidate commit | Not supplied; the candidate is an uncommitted worktree |
| Public decision link | Pending; no public PR/comment/review evidence was supplied or created |
| Authority | [Governance §3](../../GOVERNANCE.md#3-who-approves-normative-changes) at the baseline; sole-maintainer quorum plus public approval and applicable security review |
| Supersedes | None |

## Approval and security review

The stated maintainer consent is explicit. The record does not infer that the
maintainer performed security review, read the final corrected bytes, or made a
public decision. Governance §3 does not require an independent reviewer for every
RFC acceptance; a properly documented human self-review can be considered under
that bar. None was supplied for this RFC. The
[AI advisory review](../../rfcs/0013-http-tls/review.md) cannot fill that field.
Independent composition review remains a separate production/release gate.

| Gate | Evidence/state |
|---|---|
| Maintainer consent with self-approval disclosed | Confirmed as reported above |
| Public approval of exact reviewed scope/revision | Pending |
| Human protocol/security review | Pending; reviewer assignment and findings disposition not supplied |
| Independent security review | NOT_EXECUTED; no independent reviewer asserted |
| Normative objections | No public review/objection inventory was supplied; absence of a report is not a verified absence of objections |
| Advisory analysis | AI-assisted document/fixture review only, not counted as a vote |

## Compatibility and activation

The candidate proposes additional context bytes 4/5, with the existing 1/2/3
encodings, common Noise construction, schema declarations/reservations and
recovery service unchanged. It changes the permitted local TLS-provider trust
boundary and carrier admission policy; the compatibility/version disposition
requires public human review against accepted decisions. No major-version
exemption is invented.

The candidate artifacts are under `rfcs/0013-http-tls/`. Active owner text,
`conformance/profiles.yaml`, context fixtures and
`compatibility/syntra-1.0.json` are not changed. Their base Git blobs are checked
by the candidate validator. This preserves accepted input hashes and prevents a
pending draft from appearing as an authoritative allocation.

## Verification and release evidence

Static checks validate the isolated candidate's constants, fixture bytes,
traceability, gate labels and separation from active inputs. They do not execute
an HTTP peer, TLS provider, proxy, encrypted driver or persistence integration.
Every candidate runtime case remains NOT_EXECUTED. No formal conformance,
independent interoperability, browser/device validation, freeze or release
authorization is asserted. Command reports identify the worktree fingerprint;
they do not manufacture a reviewed commit.

## Decision and next action

Maintainer consent is recorded, but formal acceptance and activation remain
blocked. An actual public decision needs the corrected RFC/candidate revision,
human security-review disposition, compatibility decision and any objection
resolutions. Publishing this preparation file later is not automatically a
maintainer approval comment. Do not mark the RFC Accepted or activate bytes 4/5
merely because this file exists or a validator passes. After the gates clear,
apply the [owner delta](../../rfcs/0013-http-tls/owner-delta.md), synchronize
canonical requirements/cases/fixtures and pin an actual reviewed commit.
