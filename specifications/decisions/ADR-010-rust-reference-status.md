# ADR-010: Rust Reference Implementation Status

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 8, 11; `GOVERNANCE.md`

## Context

A reference implementation helps validate specifications and gives
implementers a runnable example. But if the implementation becomes the
de facto standard, other languages inherit Rust-specific choices and
independent implementation becomes impossible.

## Decision

1. The Rust implementation is **non-normative**. Specifications and
   `.proto` files define conformance; Rust MUST conform to them, not
   vice versa.
2. Language-specific convenience APIs (builders, async runtimes,
   ergonomic error types) MUST remain non-normative and MUST NOT impose
   wire or behavioral requirements on other languages.
3. Implementation-only behavior is not conformance. Any behavior that
   matters MUST be promoted to a specification via RFC before other
   implementations rely on it.
4. Engineering bars for the reference: small auditable APIs, no
   `unsafe` without documented reviewed justification, no panics on
   untrusted input, bounded allocation, unit + integration + negative
   tests, deterministic fixtures, no private dependencies, no
   unnecessary frameworks.

## Alternatives considered

- **Normative reference implementation.** Rejected: violates
  implementation independence (SYN-ARCH-060/061) and blocks other
  languages.
- **No reference implementation.** Rejected: leaves specifications
  unvalidated and slows adoption. A non-normative reference is the
  middle path.
- **Multi-language normative SDKs.** Rejected for v1: multiplies the
  normative surface. Non-normative SDKs in other languages MAY follow
  once v1 stabilizes.

## Consequences

- Spec reviews do not defer to "what Rust does"; code reviews defer to
  "what the spec says."
- Conformance suite tests behavior, not Rust APIs.
- Rust changes that imply spec gaps trigger RFCs, not silent fixes.

## Compatibility implications

- Rust releases do not version the protocol. Protocol versions advance
  only via accepted RFCs and `CHANGELOG.md`.
- Breaking Rust API changes are not protocol breaking changes (and vice
  versa), but both MUST be documented clearly to avoid confusion.

## Status

Accepted (with 2026-10-27 addendum). The in-tree implementation snapshot
was removed from this repository on 2026-10-27; language implementations
are separate projects, out of scope for this repository, and remain
non-normative with unchanged engineering bars. The decision itself and its
normative/non-normative boundary are unchanged (see `MIGRATION.md` §10).

Historical status text at acceptance time: the reference implementation
was present in `crates/` (including the production native ABI) outside the
normative paths defined in `specifications/architecture.md` Sec. 8; the
architecture ownership row has since been aligned to the same external,
non-normative status. Amending this decision still REQUIRES an RFC per
`specifications/decisions/README.md`.
