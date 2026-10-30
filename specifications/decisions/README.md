# Architecture Decision Records

This directory holds Syntra's architecture decision records (ADRs).
Each ADR has an explicit owner and status. Amendments REQUIRE an RFC
(see `../../rfcs/README.md`) and maintainer approval (see
`../../GOVERNANCE.md`).

| ADR | Title | Status | Owner |
|-----|-------|--------|-------|
| [ADR-001](ADR-001-specification-first.md) | Specification-first design | Accepted | Syntra maintainers |
| [ADR-002](ADR-002-protobuf-idl.md) | Protobuf as the public IDL | Accepted | Syntra maintainers |
| [ADR-003](ADR-003-transport-independent-core.md) | Transport-independent protocol core | Accepted | Syntra maintainers |
| [ADR-004](ADR-004-layer-boundaries.md) | Core vs transport vs application boundaries | Accepted | Syntra maintainers |
| [ADR-005](ADR-005-connection-vs-session.md) | Connection vs logical session | Accepted | Syntra maintainers |
| [ADR-006](ADR-006-generic-rpc.md) | Generic RPC design | Accepted | Syntra maintainers |
| [ADR-007](ADR-007-event-streams.md) | Optional generic event streams | Accepted | Syntra maintainers |
| [ADR-008](ADR-008-transport-security.md) | Transport security policy | Accepted | Syntra maintainers |
| [ADR-009](ADR-009-versioning-compatibility.md) | Protocol versioning and compatibility | Accepted | Syntra maintainers |
| [ADR-010](ADR-010-rust-reference-status.md) | Reference implementation status (non-normative; implementations external since 2026-10-27) | Accepted | Syntra maintainers |
| [ADR-011](ADR-011-noise-device-authorization.md) | Shared secure channel and persistent device authorization | Accepted (RFC 0007) | Syntra maintainers |

ADR-011 adds `SNTR-SC1-WSS-V1` as an additional secure profile. It does not
mark ADR-008 superseded: SC1/WSS still requires verified outer TLS 1.3, and
existing TLS-based profiles retain their identifiers and policy. Independent
production security review and release evidence remain separate gates.

Each ADR contains: Context, Decision, Alternatives considered,
Consequences, Compatibility implications, Status.
