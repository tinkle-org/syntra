# Changelog

Syntra 1.0 is pre-release. Current development is recorded under `Unreleased`;
no stable release is declared here. Release authorization follows
[GOVERNANCE.md](GOVERNANCE.md) and [RELEASE.md](RELEASE.md).

## [1.0.0-rc.2](https://github.com/tinkle-org/syntra/compare/v1.0.0-rc.1...v1.0.0-rc.2) (2026-11-06)


### Features

* add v1 release readiness with public IDL, RFCs, and conformance suite ([#1](https://github.com/tinkle-org/syntra/issues/1)) ([9d384cf](https://github.com/tinkle-org/syntra/commit/9d384cfa2b799e3763e3c4d91711b7d3ef842c98))
* native Rust workspace with Go FFI and registry releases ([#4](https://github.com/tinkle-org/syntra/issues/4)) ([aaa040d](https://github.com/tinkle-org/syntra/commit/aaa040d7d168e1a0846b1300e8559b6ace3ff35e))
* optional update/recovery profile with replay and snapshot recovery ([#7](https://github.com/tinkle-org/syntra/issues/7)) ([7cb8875](https://github.com/tinkle-org/syntra/commit/7cb8875100668f62d3a1ae226fe3d32cfb99a131))
* production runtime with native ABI and recovery boundary ([#6](https://github.com/tinkle-org/syntra/issues/6)) ([a07de4a](https://github.com/tinkle-org/syntra/commit/a07de4aa64831d58a0da002745bf3dbcc31c0680))
* reliable sessions with delivery reconciliation and recovery hardening ([#9](https://github.com/tinkle-org/syntra/issues/9)) ([8d13ebe](https://github.com/tinkle-org/syntra/commit/8d13ebe4b5882e125ce51a5b29082977d9d6bc0f))
* replay-then-live recovery contract with fixed boundary and loss observability ([#8](https://github.com/tinkle-org/syntra/issues/8)) ([9b8be21](https://github.com/tinkle-org/syntra/commit/9b8be21762bafb3f7eac2faa2445525f8609a37f))
* **spec:** adopt RFC 0014 terminal receipt canonically ([#26](https://github.com/tinkle-org/syntra/issues/26)) ([985d90e](https://github.com/tinkle-org/syntra/commit/985d90eb5ee6d7aec0d20ea088430f271eed7cd7))
* **spec:** define embeddable Syntra 1.0 protocol reference ([#23](https://github.com/tinkle-org/syntra/issues/23)) ([3f7e8ea](https://github.com/tinkle-org/syntra/commit/3f7e8ea037fefcc5c86101d23e7722c83e28a0d3))


### Bug Fixes

* **deps:** bump tokio 1.54.0 -&gt; 1.54.1 (1.54.0 yanked) ([b97f351](https://github.com/tinkle-org/syntra/commit/b97f3517343adc72cdd9f5c1358006c1a3806a03))
* **deps:** bump tokio 1.54.0 -&gt; 1.54.1 (1.54.0 yanked) ([160ed4c](https://github.com/tinkle-org/syntra/commit/160ed4c89c801af9f0754a07709c475e4c374000))
* enable BSR publish on main pushes with kept BUF_TOKEN ([#2](https://github.com/tinkle-org/syntra/issues/2)) ([02169d2](https://github.com/tinkle-org/syntra/commit/02169d2a42fce330670bac5d678450afd22990d5))
* **release:** reject edited maintainer decision comments ([#22](https://github.com/tinkle-org/syntra/issues/22)) ([5ac9b70](https://github.com/tinkle-org/syntra/commit/5ac9b70008280334966daf67c3f8a38dd06e374b))
* trigger BSR publish on workflow changes and manual dispatch ([#3](https://github.com/tinkle-org/syntra/issues/3)) ([8b7a14c](https://github.com/tinkle-org/syntra/commit/8b7a14c0e46d9622c0ff72e0e2a1dc322a03b925))

## [Unreleased]

### Changed

- Adopt accepted RFC 0014 in the connection, RPC, security and transport owners:
  thirteen `SNTR-TRC-*` requirements and fourteen reciprocal `CONF-TRC-*` case
  groups, all NOT_EXECUTED. The host-local exception remains disabled by default,
  uses the existing correlated result and preserves ordinary withdrawal. RFC 0014
  is Implemented for the adopted definitions and registered coverage; Rust is the
  SDK behavioral reference. SDK evidence, production durable application
  integration, independent release-security review and publication authorization
  remain separate.
  Source IDL and carrier allocations are unchanged. RFC 0013's guard retains
  every original base byte and permits only exact hash-pinned RFC 0014 appendices;
  HTTP adoption remains inactive.
- Clarify RFC 0014's pre-mutation partial-frame barrier and cross-language
  composition prerequisite. Check its accepted lifecycle status and Decision 0004
  disposition before adoption traces, and guard the complete bidirectional case
  composition. These are static checks; protocol execution remains NOT_EXECUTED.
- Accepted RFCs 0011–0014 under [Decision 0004](docs/decisions/0004-rfc-0011-0014-acceptance.md)
  with sole-maintainer approval and human self-review disclosed. RFC 0012
  ratifies the existing reference; RFC 0011 publisher activation and RFC 0013
  canonical carrier adoption remain separate work. RFC 0014's specification-local
  implementation status is recorded above. No freeze, conformance result or
  release is claimed.
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
