# RFC Process

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
- Any exception to an ADR or to `specifications/architecture.md`.
- Any wire-incompatible (breaking) change — always major-version RFC.

Direct PRs (no RFC) are only for non-normative fixes: typos,
clarifications with no behavioral change, docs, neutral examples.

If unsure, open an RFC. Maintainers will fast-track it if no RFC was needed.

## Lifecycle

```text
Draft → Discussion → Accepted | Rejected | Withdrawn
Accepted → Implementing → Implemented (spec + schema + tests landed)
Breaking RFCs additionally → Major version + migration notes
```

1. **Draft.** Copy `template.md` to `rfcs/NNNN-short-title.md` (next
   number; short kebab-case title). Open a PR with the `rfc` label where
   supported. Fill every section; mark unknowns as "TBD — blocker".
2. **Discussion.** Maintainers assign reviewers (protocol + security
   where relevant). Discussion happens on the PR. Expect requests for
   requirement IDs, client/server obligations, diagrams, bounds, and
   negative tests.
3. **Accepted / Rejected / Withdrawn.** Maintainers record the decision
   on the PR per `GOVERNANCE.md` Sec. 3 (quorum for normative; security
   review where applicable). Accepted RFCs get a number and stay in
   `rfcs/` as history — they are not deleted after implementation.
4. **Implementing → Implemented.** Land the spec/schema/test diffs
   referencing the RFC. Update `CHANGELOG.md` (`Unreleased`). Mark the
   RFC implemented when conformance coverage exists or a tracked
   placeholder issue is filed.

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

Per `GOVERNANCE.md` Sec. 3:

- Non-normative: one maintainer may merge.
- Normative: at least two maintainer approvals, no unresolved normative
  objection, security review for security-adjacent work.
- Breaking: major-version RFC + migration plan + `CHANGELOG.md` entry.

## Numbering

RFC numbers are sequential (`0001`, `0002`, …). Numbers are assigned at
acceptance; drafts use the next free file name and are renamed if needed.
Accepted RFCs are never renumbered or deleted.

## Template

See [`template.md`](template.md).
