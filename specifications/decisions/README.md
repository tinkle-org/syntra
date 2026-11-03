# Architecture Decision Records

This directory holds dated architecture decision records (ADRs), not a second
protocol reference. Records preserve the terminology, identifiers, and scope
reviewed at their recorded revision. Read the [current protocol reference](../../README.md#detailed-description)
for Syntra's single protocol contract. Each ADR has an explicit owner and status. Amendments REQUIRE an RFC
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

ADR-008 and ADR-011 record an earlier additive-channel design and its original
carrier policies. Their historical names and byte descriptions do not register
additional current profiles. This editorial distinction changes no recorded
acceptance status and grants no new protocol or release approval.

Each ADR contains: Context, Decision, Alternatives considered,
Consequences, Compatibility implications, Status.
