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
| [ADR-010](ADR-010-rust-reference-status.md) | Rust reference implementation status | Accepted | Syntra maintainers |

Each ADR contains: Context, Decision, Alternatives considered,
Consequences, Compatibility implications, Status.
