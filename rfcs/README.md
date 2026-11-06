# RFC Process

The numbered RFCs are dated design and decision records. They preserve the
names, wire identifiers, and scope reviewed at their recorded revision. The
[current protocol reference](../README.md#detailed-description) describes the
single Syntra protocol; historical profile registrations are not current
protocol options. This distinction changes no recorded approval status.

RFCs (Requests for Comments) are how Syntra makes normative decisions in
public. Any wire, behavioral, transport, or security change starts here.

Related: [`../CONTRIBUTING.md`](../CONTRIBUTING.md) (how to propose),
[`../GOVERNANCE.md`](../GOVERNANCE.md) (who approves, breaking changes,
stable releases).

## When you need an RFC

- Any new or changed MUST/SHOULD, state machine, handshake, RPC, error,
  stream, capability, version, or compatibility rule.
- Any `.proto` field change (addition, deprecation, option change).
- Any transport profile addition/change or security requirement.
- Any exception to an ADR or to the [protocol reference](../README.md#detailed-description).
- Any wire-incompatible (breaking) change — always major-version RFC.

Direct PRs (no RFC) are only for non-normative fixes: typos,
clarifications with no behavioral change, docs, neutral examples.

If unsure, open an RFC. Maintainers will fast-track it if no RFC was needed.

## Lifecycle

```text
Draft → Discussion → Review → Accepted | Rejected | Withdrawn
Accepted → Implementing → Implemented (spec + schema + tests landed)
Accepted → Superseded (by a newer accepted RFC)
Breaking RFCs additionally → Major version + migration notes
```

Only an **Accepted** RFC may modify normative behavior (MUST/SHOULD,
wire fields, state machines, error codes, transport mappings, security
requirements, conformance assertions). Draft, Discussion, and Review
RFCs are proposals: implementations MUST NOT ship behavior from them,
and no test, claim, or release may cite them as authority.

1. **Draft.** Copy `template.md` to `rfcs/NNNN-short-title.md` (next
   number; short kebab-case title). Open a PR with the `rfc` label where
   supported. Fill every section; mark unknowns as "TBD — blocker".
2. **Discussion.** Maintainers assign reviewers (protocol + security
   where relevant). Discussion happens on the PR. Expect requests for
   requirement IDs, client/server obligations, diagrams, bounds, and
   negative tests.
3. **Review.** When discussion converges, maintainers move the RFC to
   formal review: the proposal is frozen except for editorial fixes, and
   reviewers verify the review bar below plus `GOVERNANCE.md` Sec. 3
   quorum. Unresolved normative objections block acceptance.
4. **Accepted / Rejected / Withdrawn.** Maintainers record the decision
   on the PR per `GOVERNANCE.md` Sec. 3 (quorum for normative; security
   review where applicable). Accepted RFCs get a number and stay in
   `rfcs/` as history — they are not deleted after implementation.
   Withdrawn RFCs stay in `rfcs/` as history with the reason recorded.
5. **Implementing → Implemented.** Land the spec/schema/test diffs
   referencing the RFC. Update `CHANGELOG.md` (`Unreleased`). Mark the
   RFC implemented when conformance coverage exists or a tracked
   placeholder issue is filed.
6. **Superseded.** An Accepted RFC replaced in whole by a newer Accepted
   RFC is marked Superseded (with a pointer to the successor). The
   successor carries the normative force; the superseded RFC remains for
   history and MUST NOT be cited for new behavior.

## Review bar

- BCP 14 keywords used correctly; every MUST/MUST NOT has an ID.
- Client and server obligations stated separately.
- Success + failure transitions specified; no silent drops except where
  explicitly allowed with rationale.
- Bounded resources (frame size, concurrency, timeouts) stated.
- Unknown-field/message handling stated.
- Security considerations (threats, credential handling, diagnostics
  hygiene) and compatibility considerations (negotiation, reserved
  values, migration) included.
- Testable acceptance criteria + conformance test links (or placeholders).
- No private dependency or domain-specific concept.
- Neutral examples only (echo, generic key/value, generic subscription).

## Who approves

Per `GOVERNANCE.md` Sec. 3 and the published `MAINTAINERS.md` roster:

- Non-normative: one maintainer may merge.
- Normative: approval by the active roster — one active maintainer may accept
  with disclosed self-approval; two or more require two distinct approvals.
  No unresolved normative objection; security review for security-adjacent
  work.
- Breaking: major-version RFC + migration plan + `CHANGELOG.md` entry.

The 2026-10-29 bootstrap transition is recorded in
[`docs/decisions/0001-bootstrap-ratification.md`](../docs/decisions/0001-bootstrap-ratification.md).
It does not accept any protocol RFC by itself.

## Numbering

RFC numbers are sequential (`0001`, `0002`, …). Numbers are assigned at
acceptance; drafts use the next free file name and are renamed if needed.
Accepted RFCs are never renumbered or deleted.

## Template

See [`template.md`](template.md).

The [decision-record template](../docs/decision-record-template.md) retains
actual approvals, reviewed revisions, compatibility dispositions and evidence.
[RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md) is accepted; its
bootstrap transition is recorded in
[Decision 0001](../docs/decisions/0001-bootstrap-ratification.md). The
acceptance/freeze/release milestones remain separate. Publishing or merging an
RFC does not accept another RFC.

## Draft proposals

- [RFC 0014: Scoped terminal receipt and authorization retirement](0014-scoped-terminal-receipt.md)
  proposes one request-bound result after an authority-proven terminal
  transition, with pre-mutation output fencing and bounded closure. Public
  acceptance, compatibility disposition and human security review are pending.
  It changes no current owner, wire contract or implementation behavior.
- [RFC 0013: Noise-protected HTTP carriers and trusted TLS streams](0013-http-tls-carriers.md)
  proposes HTTP/HTTPS carriage and a trusted in-process TLS-provider boundary.
  Maintainer consent is recorded; public approval and human security review are
  pending. It is not accepted and does not change the current reference or registry.
