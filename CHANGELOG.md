# Changelog

Syntra 1.0 is pre-release. Current development is recorded under `Unreleased`;
no stable release is declared here. Release authorization follows
[GOVERNANCE.md](GOVERNANCE.md) and [RELEASE.md](RELEASE.md).

## [Unreleased]

### Changed

- Adopt accepted RFC 0014 in the connection, RPC, security and transport owners:
  thirteen `SNTR-TRC-*` requirements and fourteen reciprocal `CONF-TRC-*` case
  groups, all NOT_EXECUTED. The host-local exception remains disabled by default,
  uses the existing correlated result and preserves ordinary withdrawal. SDK and
  application evidence remain pending. Source IDL and carrier allocations are
  unchanged. RFC 0013's guard retains every original base byte and permits only
  exact hash-pinned RFC 0014 appendices; HTTP adoption remains inactive.
- Clarify RFC 0014's pre-mutation partial-frame barrier and cross-language
  composition prerequisite. Check its accepted lifecycle status and Decision 0004
  disposition before adoption traces, and guard the complete bidirectional case
  composition. These are static checks; protocol execution remains NOT_EXECUTED.
- Accepted RFCs 0011–0014 under [Decision 0004](docs/decisions/0004-rfc-0011-0014-acceptance.md)
  with sole-maintainer approval and human self-review disclosed. RFC 0012
  ratifies the existing reference; RFC 0011 publisher activation, RFC 0013
  canonical carrier adoption and RFC 0014 terminal-receipt implementation
  remain separate work. No freeze, conformance result or release is claimed.
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
- Documented the active prerelease publisher and the accepted manual
  specification-release design. RFC 0011 publisher activation is deferred;
  the existing publisher and release-specific authorization gates remain intact.
