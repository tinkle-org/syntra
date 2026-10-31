# Changelog

All notable changes to Syntra will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for protocol versions once stable (see `GOVERNANCE.md` Sec. 5). During
development, changes land under `Unreleased`.

## [Unreleased]

### Added

- Accepted the 2026-10-29 bootstrap governance transition: roster-based
  approval rule, `MAINTAINERS.md`, and
  `docs/decisions/0001-bootstrap-ratification.md`.
- Accepted RFC 0007 and ADR-011. Added the canonical `syntra.sc1.v1` carrier
  mapping, `SNTR-SCW-001`–`SNTR-SCW-012`, and the `SNTR-SC1-WSS-V1` profile
  with `CONF-SCW-001`–`CONF-SCW-024` case specifications.
- Added public SC1 context/prologue vectors under
  `conformance/test-vectors/sc1/`.
- Accepted the 2026-10-30 SDD acceptance wave per
  `docs/decisions/0002-sdd-acceptance-wave.md` (Option A: standardized
  recovery stays in Syntra): RFC 0001, 0002 (dependency record), 0003,
  0004, 0005 (protocol contract; Go `go_package` migration deferred),
  0006 (with §11 governing), 0008; new RFC 0010 (SC1 host enrollment and
  authorization lifecycle). Self-approval disclosed; executed conformance
  evidence remains a release gate.
- Added `SNTR-DAUTH-011`–`SNTR-DAUTH-024` (host enrollment/lifecycle
  obligations incl. the decided revocation propagation: new-connection
  immediate enforcement, 300 s hard maximum, 60 s operational target,
  fail-closed) and their planned `PLAN-DAUTH-*` case coverage.
- Registered `SYN-URP-001`–`007`/`010`–`026` requirement rows (reserved
  `008/009`) with the reconciled `CONF-URP-001`–`CONF-URP-017` recovery
  cases; the manifest schema and repository validation now admit
  `SYN-URP-*`.

### Changed

- Added machine-readable transport applicability: cases MAY declare
  `applicable_transports` (peer-observation family vocabulary) to encode
  transport-scoped requirements such as the RFC 0004 D3 persistent-carrier
  exemptions; `CONF-RPC-004` and `CONF-RPC-013` now declare
  `[tcp_tls, ws_wss]`, and an HTTP/HTTPS-only claim reports a valid `SKIP`
  citing the key (§6 exception to the no-SKIP-for-mandatory rule).
- Manifest validation now rejects present-but-null `expected.error` /
  `expected.transport` maps (case-level and `control_connection`) while
  absent keys stay allowed; clarified the `expected.frames: []` semantics
  (response-side Frames only — the stimulus Frame itself is never a
  member).
- Tightened two conformance fixtures (no RFC changes, no new protocol
  messages): `CONF-URP-015` now drives the recovery reconnect explicitly
  (fresh authenticated connection, `hello`, then `Negotiate` with
  `request_id` 1 and asserted confirmation before the `Subscribe` with
  `request_id` 3), matching RFC 0006 §11.6; `CONF-RPC-013` now gives each
  of the 16 concurrent `Echo` requests a distinct payload and asserts each
  result echoes its requester's payload, preserving the
  `reverse_completion_order` completion schedule.
- Handshake failures no longer promise a wire-typed code to the peer:
  detecting-side typed causes plus transport-native close signals
  (RFC 0003 D1/D3/D4; owner files updated).
- Request identifiers are strictly increasing, connection-scoped and never
  reused; duplicate/replayed IDs are ordered-admission violations
  (RFC 0004 D1/D2). Single serialized terminal gate: cancel/deadline ties
  select `DEADLINE_EXCEEDED`; clocks start at initiator admission and host
  bounded-frame receipt (reconciled with RFC 0008 D2).
- Pre-ACTIVE notifications are protocol violations — deterministic
  fail-close (RFC 0003 D2), replacing the ignore-with-diagnostic default.
- Capability/session extension binds post-ACTIVE per accepted profile
  contracts only; no generic capability enumeration (RFC 0005 D1). Bounds
  recorded: 8 KiB raw credential, 128-byte connection ID, 4 KiB diagnostic,
  ≥16 concurrency; 1 MiB applies to the total serialized Frame (RFC 0005
  D2/D3, fixtures corrected).
- Raw-wire validation is now the accepted contract: reserved 16/17
  rejected in frame/body position; future-body variants 18–31 rejected
  with `UNIMPLEMENTED`; duplicate `Frame.body` alternatives rejected
  regardless of codec merge behavior (RFC 0008 D1).
- Update/Recovery semantics compacted to RFC 0006 §11: local overflow
  ends only the affected subscription with `terminated=true` +
  `local-queue-exhausted` at the unchanged generation (no
  initiator-manufactured `next_generation`); generations bind to the
  authenticated principal scope (P, S, G) and change only on true
  provider loss or explicit shared rebase; every round uses a fresh
  handle and freshly captured boundary; snapshot installation is
  same-generation with no wire carrier for completion; resume anchors to
  the durable known-safe checkpoint.
- Recovery refusal mapping reconciled to the accepted `SYN-URP-010`
  wording by connection state: profile operations on a connection that
  has not confirmed the profile (like unknown operations) are refused
  `UNIMPLEMENTED`, and `FAILED_PRECONDITION` is reserved for an
  unconfirmed option on a connection that has confirmed the profile;
  owner files, `capabilities.md` §4, `events.md`, and `CONF-URP-001` now
  agree without an RFC change.
- Manifest cases can declare a machine-readable `control_connection`
  paired-control scenario (`schema.yaml`, validators, manifest format);
  `CONF-URP-001` registers its confirmed-connection control structurally,
  and validation requires it there instead of a prose-only note.
- Replaced the experimental `syntra.sc1.draft1` carrier documentation with the
  accepted v1 WSS mapping. Draft-1 and local-revision-1 remain historical and
  are not aliases.
- Made the release checklist and Core conformance claim rule scope-aware: a
  single named transport is sufficient for a Core claim; a two-transport proof
  is required only for a transport-independence claim.
- Marked the Go draft-1 implementation ledger historical; current Rust
  implementation evidence is recorded downstream and is not a conformance
  result.
- Clarified the two-observer handshake-failure representation in
  `CONF-CORE-005` and `CONF-HTTP-008` (RFC 0003 D1): `error.observer` /
  `error.carriage` bind the detecting host's local `UNIMPLEMENTED` cause
  to a no-invented-carrier assertion (`carriage: local_only`, zero
  Syntra Frames), and `transport.peer_observation` asserts the
  initiator's transport-native signal (TCP/TLS close → `UNAVAILABLE`
  absent better evidence; WS/WSS Close 1002 → generic protocol
  rejection; HTTP 400 → no envelope + adapter `INVALID_ARGUMENT`),
  documented and validated (`schema.yaml`, manifest README,
  `scripts/validate-repo.py`).
- Made `CONF-RPC-004` duplicate-ID detection deterministic with the
  validated structured barrier fault `duplicate_while_pending:
  {barrier: first_terminal_result, release_after: violation_and_closure}`
  (no sleeps; harness-injected duplicate; rejection at admission never
  dispatches, barrier released only after the violation and closure; no
  result under ID 7), synchronized its prose companion, and fixed a
  prose/manifest divergence where prose `CONF-RPC-011` still described
  the retired exhaustion case instead of the manifest's idempotent-retry
  case (exhaustion coverage remains under `CONF-RPC-013`).
- Clarified `SNTR-RPC-008`/§1E scope: the ≥16 floor binds to persistent
  Syntra connections (TCP/TLS, WS/WSS, SC1); HTTP/HTTPS exchanges are
  independent logical connections carrying one RPC (SNTR-HTTP-070, RFC
  0004 D3) with transport-owned minimums preserved (SNTR-HTTP-072
  listener endpoint groups; SNTR-HTTPS-041 HTTP/2 streams). Synced
  `CONF-RPC-002`/`CONF-RPC-013` notes and prose, and
  `specifications/schema/reference.md`.

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

### v1 acceptance preparation — 2026-10-29

- Added Draft RFC 0009 proposing an explicit public owner-ratified bootstrap
  to a published sole-maintainer approval model, with security self-review
  disclosure and independent SC1 composition review retained for production.
- Selected SC1 over verified WSS as the first stable bundle's transport,
  with standardized recovery and applicable mobile evidence. Proposed exact
  scope separates single-transport claims from the two-transport independence
  proof; no existing claim or profile rule is changed before acceptance.
- Added an informative decision-record template and dependency-ordered v1
  acceptance package separating RFC acceptance, normative activation/freeze,
  independent execution and stable release authorization. Current quorum,
  RFCs 0001–0008, schemas, compatibility archives, conformance registrations
  and prerelease automation are unchanged. No approval or PASS is invented.

### Mobile v1 decision package — 2026-10-28

- Selected SC1 and standardized update recovery as required release deliverables,
  retaining specification-first ownership and independent downstream Rust/Go.
- Replaced RFC 0003–0005 decision menus with concrete proposals for local/native
  handshake errors, increasing request identities, terminal race rules,
  profile-specific negotiation/carriage, encoded-frame limits and public Go
  package migration. All remain Draft; no schema/baseline or owner requirement
  is changed before acceptance.
- Added RFC 0006 recovery amendment for fresh rounds, local overflow isolation,
  scoped generations, durable state/checkpoint confirmation and local snapshot
  installation. Recovery is required for the target, while negotiated on wire.
- Identified incompatible Rust local-1/Go draft-1 SC1 bytes and selected a new
  canonical context/prologue/subprotocol proposal in RFC 0007 §11, with public
  context JSON and lint tests. No cryptographic vector or interop pass is claimed.
- Added Draft RFC 0008 mobile/parser/resource decisions, end-to-end acceptance
  plans and an SDD delivery record. Refreshed release readiness while retaining
  the October 19 audit as history. Formal acceptance, downstream alignment,
  independent security/interop and mobile execution remain release gates.

### Implementation evidence — 2026-10-28

- Recorded delivered bounded experimental Go SC1 draft-1 over TCP/WS/WSS,
  bootstrap NK and returning NKpsk0, with high-level ready-to-call connection
  helpers, server admission and owned transport shutdown. The
  [implementation ledger](docs/sc1-implementation.md#implementation-status)
  is self-contained; existing profile meanings, production TLS policy and
  historical release scope remain unchanged. RFC 0007 is Draft and ADR-011
  Proposed. UDP is deferred; HTTP/HTTPS request-response is excluded from
  this implementation; WSS keeps verified outer TLS ≥1.3 with no downgrade.
- Documented channel-aware host policy: independently verify root identity,
  current enrollment and admission before ready and enforce the intended
  returning-mode same-principal binding; the library does not compare principals
  automatically.
  Nil method authorization denies calls. The single asynchronous FIFO writer
  owns snapshots with 256-frame/8 MiB queued-plus-active caps, 5s default writes,
  200ms best-effort terminal drain and 1s join after transport Close. Core
  callback grace and connection shutdown budgets remain distinct.
- Recorded final Go 1.26.10 root race/pure-Go CGO-disabled/native-core
  race/staticcheck and Go 1.23.12 compatibility passes; Docker integration
  passed in 30.681s across all six carrier/mode groups with none skipped.
  High-level connection helpers have local unit coverage, not container
  coverage. Reachable-vulnerability scans were zero for root and integration,
  not dependency-wide advisory-free findings. See
  [verification evidence](docs/sc1-implementation.md#verification-evidence).
- Recorded three passing 100ms in-memory benchmark samples at CPU settings
  1 and 4 on darwin/arm64 Apple M4, without a hard performance threshold;
  full RPCs are not zero-allocation. See [measurements](docs/perf-tradeoffs.md).
  Same-implementation tests are not independent wire interoperability or formal
  `CONF-*` conformance. Enrollment RPCs, complete issuance/storage/rotation,
  independent review/vectors/interoperability and native ABI completion-time/
  credential-release gaps remain [open](docs/sc1-implementation.md#remaining-work).

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
  That 2026-10-27 design step introduced no implementation or verification
  result. The subsequent 2026-10-28 evidence entry above records delivered
  experimental behavior; neither step accepts the RFC, establishes formal
  conformance, or adds session resumption or automatic RPC retry.
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
- In-tree language implementations and their tooling (2026-10-27): the Rust workspace
  (all five crates, including committed generated types, native C ABI and
  WASM adapters), the Go module (committed protobuf types, pure-Go core,
  native adapter), root Cargo manifests, `release-plz.toml`, the root
  generation template, the four-leg conformance runner harness, the
  crate/Go release workflows, and implementation-only test fixtures.
  Source snapshot `2a91da7` (PR #12 merge) is the provenance record; see
  [MIGRATION.md §10](MIGRATION.md#10-implementation-extraction-record-2026-10-27).
- Distribution model changed: this repository publishes documents and
  schema provenance only via release-please document releases (`vX.Y.Z`
  tags, GitHub Releases); no crates.io, no Go module proxy, no nested
  tags, no language artifacts. Pre-release status unchanged; no wire or
  normative behavior change.
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
