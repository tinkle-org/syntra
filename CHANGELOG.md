# Changelog

Syntra 1.0 is pre-release. Current development is recorded under `Unreleased`;
no stable release is declared here. Release authorization follows
[GOVERNANCE.md](GOVERNANCE.md) and [RELEASE.md](RELEASE.md).

## [Unreleased]

### Changed

- Remove obsolete development and readiness reports from the documentation;
  current tooling and verification requirements remain in their supporting guides.
- Use Syntra/channel terminology throughout the current reference, context
  fixtures, and test actions; carrier mappings and optional recovery are parts
  of the same protocol contract.
- Consolidated the current protocol reference into six pages: connection,
  wire format, RPC, security, transports, and recovery.
- Aligned public reading guides with the specification-only repository
  boundary: protocol implementations and generated language artifacts are
  owned outside this repository.
- Separated the [schema tooling guide](docs/schema-tooling.md) and
  [conformance test guide](conformance/README.md) from protocol requirements
  and from executed implementation evidence.
- Documented the active prerelease publisher and the proposed manual
  specification-release procedure. RFC 0011 remains in Discussion; its
  publication policy requires public acceptance before activation.
