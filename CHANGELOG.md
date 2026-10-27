# Changelog

All notable changes to Syntra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for protocol versions once stable (see `GOVERNANCE.md` Sec. 5). During
development, changes land under `Unreleased`.

## [v1.0.0-rc.1] - 2026-10-22 (release candidate, not stable)

First release candidate scope (protocol v1) for external Rust/Go imports.
Install: `cargo add syntra-core@1.0.0-rc.1`, Go `github.com/tinklehq/syntra/bindings/go@v1.0.0-rc.1`.
Known blockers for stable (do not block RC import): P0 findings F-01–F-06
(`audits/v1-consistency-review.md`), SESSION-OPEN-QUESTIONS items 1–11,
pending RFCs 0001–0005. Distribution is
per-crate tags `<crate>-vX.Y.Z` with crates.io publication plus GitHub
Release assets (no BSR, no GHCR); license is Apache-2.0
(`LICENSE`, `GOVERNANCE.md` §7). Where this plan differs from `Unreleased`,
the crates.io model governs.

### Added

- Public IDL: `proto/syntra/v1` (envelope, handshake, rpc, errors,
  events, session + capabilities documentation-only files), package
  `syntra.v1`, Buf v2 STANDARD/FILE governance with zero external
  dependencies.
- Core specifications: protocol model, serialization, framing,
  six-state handshake with version negotiation, opaque-credential
  authentication interface, connection-bound sessions, generic RPC
  (correlation, deadlines, cancellation, idempotency discipline),
  optional event streams, reliability/backpressure rules, 17-value `ErrorCode`
  registry (0–16, including 16 nonzero failure codes), capability negotiation,
  five-dimension versioning.
- Transport profiles: TCP, TLS 1.3/TCP, HTTP/1.1 (dev-only), HTTPS/H1,
  HTTPS/H2, WS/H1 (dev-only), WSS/H1 — each with framing, handshake
  binding, auth carriage, and failure mapping.
- Security specifications: threat model (T1–T10), transport security,
  authentication security, replay protection (5 classes), opaque
  payloads, security test plan (STEST-001…011).
- Executable conformance suite: 130 machine-readable cases across 11
  profiles, 498 requirement traceability rows (473 SNTR-* + 25 SYN-ARCH-*),
  golden protobuf vectors, TCP byte vectors, HTTP/WebSocket fixtures,
  result model, implementation declarations, claim wording.
- Repository validation: `scripts/validate-repo.py` (requirements,
  manifests, vectors, links, RFC metadata, markdown) plus
  `.github/workflows/repo-validation.yml` (11 CI items); RFC lifecycle
  with Review/Superseded statuses; release process (`RELEASE.md`).

### Changed

- Requirement registry extended with the SYN-ARCH-* charter namespace
  (25 rows; mostly `manual` charter attestation).
- `GOLD-PROT-UNKNOWN-FIELD-01` fixture corrected to unknown field 90
  (was field 86 on the wire).
- Manifest schema `requirement_id` pattern extended to accept
  `SYN-ARCH-*` alongside `SNTR-*`.

### Deprecated

- None.

### Removed

- None (no stable release exists to remove from).

### Security

- No wire or behavioral change in this entry. Security posture unchanged:
  secure transports required for public production; plaintext profiles
  restricted to trusted environments; credentials opaque and never logged;
  negative security cases enforced via STEST fixtures.

## [Unreleased]

### Added

- Documentation of the selected transport-independent Syntra Secure Channel
  v1 (SC1) proposal in new [Draft RFC 0007](rfcs/0007-secure-channel-device-authorization.md):
  initial `Noise_NK_25519_ChaChaPoly_SHA256` enrollment and returning
  `Noise_NKpsk0_25519_ChaChaPoly_SHA256` authentication with a unique random
  shared 32-byte AK and opaque 8-byte `auth_id` per device, fresh ephemeral
  material and directional traffic keys per channel, empty M1/M2 payloads,
  and client transport-record confirmation before protected actions.
  Guides describe host-owned enrollment/storage/authorization/revocation,
  proposed TCP/UDP/WS bindings, browser outer TLS, and the distinct
  Noise-in-WS wire boundary. [Migration record §9](MIGRATION.md#9-selected-sc1-design-record-2026-10-27)
  records the selected direction. RFC 0007 is not Accepted; baseline TLS
  requirements and existing executable conformance profiles are unchanged.
  No implementation, support, benchmark, conformance, session-resumption,
  or automatic RPC retry claim is introduced.
- Production native ABI in `crates/syntra-ffi` (`production` feature) with
  `crates/syntra-ffi/include/syntra_production.h`: transport-agnostic
  initiator/responder cores, stable handles, version checks, buffer
  ownership, lifecycle, frame ingest, and outbound actions.
- Host policy bridge in `crates/syntra-runtime::policy`: asynchronous
  authentication and authorization completion with tokens distinct from
  wire `request_id` values.
- Generic recovery boundary in `crates/syntra-runtime::recovery`:
  application-supplied stream checkpoints with local recovery actions; the
  core never invokes recovery RPCs.
- Go production adapter under `-tags syntranative` linked against the
  production library, with lifecycle and concurrency coverage.
- `docs/production-runtime.md` describing engine ownership, the native ABI,
  recovery rules, and distribution.
- Apache-2.0 `LICENSE`; all Rust packages are Apache-2.0 and publish
  to crates.io via release-plz Trusted Publishing (OIDC, with scoped
  `CARGO_REGISTRY_TOKEN` bootstrap fallback).
- `release-plz.toml` (Rust workspace versioning + Release PRs, crates.io
  publish enabled, per-crate tags on Release PR merge) and
  `.github/workflows/release.yml` (schema/source/crate/Go archives,
  descriptor/manifests/vectors, SHA256SUMS attached to the syntra-core
  GitHub Release; nested `bindings/go/vX.Y.Z` tag created-or-verified at
  the same revision by the release workflow; no browser-WASM assets —
  native production ABI ships as source plus header, built from the tagged
  source).
- `crates/syntra-ffi` is default-empty (no C ABI exports by default) with
  `test-fixture` for tests and `production` for the native ABI; all WASM
  targets are rejected at compile time. CI runs default workspace tests
  plus `--features test-fixture` and `--features production` tests and
  `build_contract.py`, and asserts the expected WASM failure alongside
  non-FFI WASM checks.
- Committed generated types under `crates/` (Rust) and `bindings/go/` (Go,
  incl. `*.pb.go`), drift-checked by `scripts/validate-schema.py
  --drift-only` and CI jobs (default + fixture + production `cargo test`,
  default-tag and `syntranative` `go test`, expected-failure WASM check).
- Seven-file public IDL in `proto/syntra/v1`, preserving the
  existing message names, field numbers, oneofs, enum registry and reservations.
  Session control/capability messages and requested extensions remain deferred
  pending normative definitions; see Draft RFC 0001.
- Buf v2 STANDARD/FILE configuration, pinned remote Rust/Go generation,
  initial seven-file descriptor baseline with historical provenance,
  schema reference/compatibility/generation documentation, and codec tests.
  The historical layout comparison is WIRE-compatible but FILE-breaking;
  the user-directed layout decision is implemented, with no stable release
  or formal maintainer/RFC approval claimed.
- Immutable `compatibility/v1-initial/historical.json` FileDescriptorSet
  generated before removal from the actual unchanged historical sources at
  commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9`. The manifest retains
  `historical_sources` path/hash provenance and adds `historical_image_sha256`;
  `image.json` remains unchanged. Historical comparisons read the archive
  without a Git checkout or duplicate source tree; a sole-source regression
  check is added to the descriptor/tooling suite (13 checks, executed —
  see the [validation record](specifications/schema/validation.md)).
- Auth/session lifecycle precision without wire change: three-concept
  separation, six-state lifecycle table with suggested-name mapping,
  seven handshake orderings with sequence diagrams, opaque-credential
  baseline with generic principal and authorization boundary, no v1
  session identifier, deferred optional resumption with cross-transport
  prohibition, HTTP principles, termination/timeout tables, and
  `conformance/auth-session/` cases (`CONF-SESS-001…010`,
  `CONF-AUTH-001…006`). Draft RFC 0002 records conflicts and blockers;
  `SESSION-OPEN-QUESTIONS.md` lists release blockers. No new normative
  IDs, no `.proto` change.
- RPC/error precision without wire change: six-stage RPC model with
  receipt-vs-execution distinction, outstanding-only `request_id` model,
  canonical method syntax, opaque-payload rules with explicit
  any-encoding decision, out-of-order concurrency, relative deadlines
  with stated start points, best-effort cancellation with race rules,
  `request_id`-vs-operation-key idempotency with worked example,
  retry table, seven-category error taxonomy mapped to the existing
  17-value registry, detail limits, protocol-vs-RPC table, transport-loss
  outcomes, and HTTP layering.   `conformance/rpc/` (`CONF-RPC-001…012`)
  and `conformance/errors/` (`CONF-ERR-001…004`) with sequence diagrams.
  No new normative IDs, no `.proto` change.
- Transport profiles `SNTR-TCP-V1` (restricted plaintext) and
  `SNTR-TLS-TCP-V1` (production-capable) in
  `specifications/transports/tcp.md` and `tls-tcp.md`: 4-byte
  big-endian length-prefixed framing with strict stream-loop semantics,
  1 MiB default bound with fail-closed pre-allocation checks, no magic
  bytes, plaintext restrictions with server-may-reject-auth, TLS 1.3
  with chain/hostname verification and deferred ALPN
  (no `syntra/1` registered), close/backpressure/keepalive/intermediary
  rules, exact byte vectors (`conformance/test-vectors/tcp/`), and
  `conformance/requirements/tcp.md` (`CONF-TCP-001…008`) plus
  `tls-tcp.md` (`CONF-TLS-001…004`). New requirement IDs `SNTR-TCP-*`
  and `SNTR-TLS-*` only; no `.proto` change.
- Event/replay precision without wire change: optional-only event
  delivery with proposed (unallocated) `syntra.events/1` and
  `syntra.events.replay/1` identifiers, wire-vs-payload field model,
  duplicate-tolerant identity rules, stream lifecycle, generic-RPC
  subscription pattern (no `SubscribeRequest` wire messages, no filter
  grammar), at-most-once default with per-stream at-least-once only,
  ordering scope, absent core ACKs, capability-gated replay with cursor
  rules, live+replay coordination strategies, HTTP push requirements
  (no delivery over plain request/response; no polling/long-polling or
  HTTP/2 push approved), backpressure, session-loss table, and
  `conformance/events/` (`CONF-EVT-001…015`, `UNSUPPORTED`/`SKIP` when
  unadvertised) with subscribe/reconnect/replay/coordination diagrams.
  `events.proto`/`capabilities.proto` reviewed: no changes proposed.
  No new normative IDs, no `.proto` change.

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
- Repository audit and migration plan: `MIGRATION.md` (historical inventory
  of `schema/syntra/v1/*.proto`, independence verification, and original
  preservation plan, now explicitly superseded by the layout decision).
- Requirement ownership matrix (Protobuf → representation; core specs →
  behavior; transport specs → mappings; security specs → requirements;
  conformance suite → verification; Rust → non-normative).

### Changed

- `proto/syntra/v1` is the sole authoritative schema root by explicit user
  direction, recorded in RFC 0001 B9. Imports, declaration-owning files and
  generated file-level APIs change; the historical FILE break remains
  documented and tested. Binary declarations and `reserved` values are
  preserved. Remaining behavioral/security blockers keep RFC 0001 Draft.

### Deprecated

- None.

### Removed

- Old `schema/syntra/v1/error.proto` and `session.proto` source tree;
  historical declarations survive in the immutable descriptor archive and
  original path/hash provenance. This supersedes the original additive-only
  preservation plan without adding wire types or changing protocol semantics.
- BSR publication path: deleted `.github/workflows/schema-publish.yml`, removed
  the `buf.build/tinklecorp/syntra` registry identity from `buf.yaml`, and
  retired `proto-v*` tags / BSR labels. Releases are per-crate tags
  `<crate>-vX.Y.Z` (+ nested `bindings/go/vX.Y.Z` at the syntra-core
  revision) with crates.io publication plus GitHub Release assets (source,
  crate, Go-bindings archives, descriptor, manifests, vectors, SHA256SUMS);
  no browser-WASM assets, no GHCR, no `buf push`. Go servers use the
  default pure-Go module or link the production library with
  `-tags syntranative` (native ABI via `syntra-ffi` `production` feature).
- `.tmp/`-only generation model: committed generated types now live under
  `crates/` (Rust) and `bindings/go/` (Go, incl. `*.pb.go`), drift-checked
  by `scripts/validate-schema.py --drift-only` (CI-enforced). No wire or
  behavioral change; `go_package` options are unchanged.

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
