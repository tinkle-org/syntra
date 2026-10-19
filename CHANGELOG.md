# Changelog

All notable changes to Syntra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for protocol versions once stable (see `GOVERNANCE.md` Sec. 5). During
development, changes land under `Unreleased`.

## [Unreleased]

### Added

- Project charter: `specifications/architecture.md` (what Syntra is/is not,
  design goals, roles, boundaries, transports, threat assumptions, ownership
  matrix SYN-ARCH-001–062).
- Architecture decision records ADR-001–ADR-010 in
  `specifications/decisions/` (spec-first, Protobuf IDL, transport-independent
  core, layer boundaries, connection vs. session, generic RPC, optional event
  streams, transport security, versioning/compat, Rust reference status).
- Open-source foundation: `README.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `GOVERNANCE.md`,
  `rfcs/README.md`, `rfcs/template.md`.
- Repository audit and migration plan: `MIGRATION.md` (inventory of
  `schema/syntra/v1/*.proto`, independence verification, no-code-deletion
  guarantee).
- Requirement ownership matrix (Protobuf → representation; core specs →
  behavior; transport specs → mappings; security specs → requirements;
  conformance suite → verification; Rust → non-normative).

### Changed

- None (existing `schema/syntra/v1/error.proto` and `session.proto`
  preserved unchanged; `reserved` values intact).

### Deprecated

- None.

### Removed

- None (no production code deleted or rewritten).

### Fixed

- None.

### Security

- Documented transport security policy (secure profiles required for public
  production; insecure profiles restricted to development) and private
  vulnerability reporting via GitHub. No wire change.

## [0.1.0] — TBD (first stable candidate, not yet tagged)

A stable `0.1.0` or `1.0.0` will be declared only when `GOVERNANCE.md`
Sec. 5 criteria hold: accepted normative specs + schemas + green
conformance suite + tagged notes. This section will then list wire
contracts, supported transports, and migration notes.

[Unreleased]: https://github.com/tinklehq/syntra/compare/HEAD...main
[0.1.0]: https://github.com/tinklehq/syntra/releases/tag/v0.1.0
