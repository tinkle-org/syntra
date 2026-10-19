# RFC NNNN: Title

- RFC: NNNN
- Title: <concise, neutral, e.g., "Handshake timeouts and retry bounds">
- Author(s): <GitHub handle(s)>
- Status: Draft | Discussion | Review | Accepted | Rejected | Withdrawn | Superseded | Implementing | Implemented
  (Only Accepted RFCs may modify normative behavior; see rfcs/README.md Lifecycle.)
- Date: YYYY-MM-DD
- Target version: v1 minor | v1 patch/clarification | vNext major
- Relates to: <ADRs, spec sections, requirement IDs, schema files>
- Reviewers: <assigned by maintainers>

> Fill every section. Mark unknowns as "TBD — blocker" rather than
> leaving them blank. Use BCP 14 keywords only for normative force.
> Keep examples neutral (echo, generic key/value, generic subscription).

## 1. Summary

One paragraph: what changes, why, and who is affected (initiator, host,
transport, conformance).

## 2. Motivation

Problem statement, use cases, and why the current charter/specs/schemas
are insufficient. Link issues or prior discussion.

## 3. Proposal

Normative diff in plain language plus exact spec/schema edits.

- New/changed requirements with IDs (e.g., `SYN-HS-014`):
  - Client obligations:
  - Server obligations:
- Schema diff (`.proto` snippet, field numbers, reserved handling):
- State machine deltas (success + failure transitions):
- Configuration and defaults (timeouts, limits, sizes):

Include a sequence diagram for behavioral changes:

```text
Initiator                              Host
    |                                     |
    |--- ... ---------------------------->|
    |<-- ... ------------------------------|
```

## 4. Detailed design

Mechanics: framing, encoding, correlation, cancellation, error mapping,
capability negotiation, unknown-field/message handling, resource bounds.

## 5. Alternatives considered

At least two alternatives with rejection rationale. Include "do nothing".

## 6. Compatibility

- Wire impact: compatible minor/additive vs. breaking major (justify).
- Negotiation: how old/new peers interoperate; downgrade behavior.
- Reserved values: affected or preserved.
- Migration: dual-support window, rollout order, `MIGRATION.md` /
  `CHANGELOG.md` notes if breaking.

## 7. Security considerations

Threats, credential handling, diagnostics hygiene (`RpcError.message`
MUST NOT leak secrets), DoS bounds, transport policy impact, negative
tests for unauthenticated/oversized/malformed inputs.

## 8. Test plan and acceptance criteria

- [ ] Conformance tests (positive + negative + fixtures):
- [ ] Requirement-to-test trace (ID → test):
- [ ] Interop check (implementations or fixtures):
- [ ] Buf lint + breaking detection for schema changes:

Never report tests as passed unless executed; include command + summary.

## 9. Drawbacks and risks

What gets harder, what could go wrong, and mitigations.

## 10. Unresolved questions and blockers

Numbered list. Significant wire/security blockers MUST be resolved
before acceptance — not by undocumented implementation choice.

## Appendix: References

Specs, ADRs, Buf/protoc versions, related RFCs.
