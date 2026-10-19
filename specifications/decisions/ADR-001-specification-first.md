# ADR-001: Specification-First Design

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 3, 8, 11; `GOVERNANCE.md`; `rfcs/README.md`

## Context

Syntra must be implementable by independent parties without access to
Rust source code or any private repository. Early protocol work produced
two Protobuf files (`schema/syntra/v1/error.proto`,
`schema/syntra/v1/session.proto`) with behavior described only in code
comments. Without an explicit authority, implementers cannot tell whether
a comment, a Rust behavior, or a test is normative, and wire compatibility
cannot be audited.

## Decision

Syntra adopts specification-driven development (SDD):

1. Markdown specifications plus `.proto` files are the sole normative
   sources. Code follows specification.
2. Every MUST/MUST NOT carries a requirement ID and links to a
   conformance test.
3. Behavior defined only in implementation code is not normative. If it
   matters, it MUST be promoted to a specification via RFC before
   implementations may rely on it.
4. Significant wire-compatibility or security questions MUST NOT be
   resolved by undocumented implementation choices; they REQUIRE an RFC
   or a recorded blocker.

## Alternatives considered

- **Code-first (reference implementation as norm).** Rejected: ties the
  standard to one language, hides obligations, and prevents independent
  verification.
- **Wiki-driven prose without IDs.** Rejected: untestable, conflicts
  unresolvable, no conformance linkage.
- **Formal-only specification (e.g., TLA+ / machine-readable only).**
  Rejected as the sole source: valuable for verification but inaccessible
  to most implementers. Formal models MAY supplement but MUST NOT replace
  Markdown + Protobuf.

## Consequences

- New behavior needs a specification change and review before code.
- Slower initial velocity, faster interop and fewer breaking surprises.
- Requires RFC discipline, requirement IDs (BCP 14), and a conformance
  suite that tracks each requirement.

## Compatibility implications

- This ADR introduces no wire change. It freezes the rule for future
  changes: wire-incompatible changes REQUIRE a major version and an
  accepted RFC (see ADR-009, `GOVERNANCE.md`).
- Existing `.proto` field numbers and `reserved` values are preserved
  under this policy.

## Status

Accepted. Amendments REQUIRE an RFC and maintainer approval.
