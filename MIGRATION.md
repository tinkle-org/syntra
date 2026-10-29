# Migration Records — Public IDL and Secure-Channel Design

- Date: 2026-10-19
- Scope: Historical Phase A audit + subsequent user-directed layout migration
- Authority: `specifications/architecture.md` Sec. 8; ADRs 001–010

> **Current layout decision (user-directed, implemented):**
> `proto/syntra/v1` is the sole Protobuf source of truth. The old
> `schema/syntra/v1` tree is removed. The original audit below records what
> existed at the time; its byte-for-byte, additive-only preservation plan
> is superseded by this explicit layout decision. It describes no live
> schema root. [RFC 0001 B9](rfcs/0001-public-idl-layout.md#b9-recorded-layout-decision-and-known-source-break)
> records the decision and known FILE/source break, without claiming
> formal maintainer quorum or behavioral RFC approval.

Sections 1–7 preserve the Phase A inventory, classification and plan as
historical context. Section 8 records the subsequent migration. No new
wire types or protocol semantics are introduced by the layout change;
remaining protocol blockers are pending.

Section 9 preserves the selected SC1 design record as of 2026-10-27; it
introduced no implementation at that date. Section 11 records delivered
experimental draft-1 behavior and verification on 2026-10-28, without
amending that historical scope or accepting the security proposal.

## 1. Inventory (as found)

The local working directory contained, excluding IDE/tooling caches:

```text
schema/syntra/v1/error.proto    (51 lines — ErrorCode, RpcError)
schema/syntra/v1/session.proto  (79 lines — Frame, ClientHello, ServerReady,
                                 RpcRequest, RpcResult, Cancel, Notification)
```

No other Syntra source files, schemas, documentation, tests, Buf
configs, READMEs, or licenses were present.

Excluded from the public repository (local tooling only, not Syntra):

- `.agents/skills/*` — agent skill definitions for the local editor
- `.opencode/*` (including `node_modules/zod`) — local tooling cache
- `.DS_Store` files — OS metadata

These paths MUST NOT be published to `tinklehq/syntra`. They are listed
here so reviewers can verify nothing normative was missed.

## 2. Transport and protocol behaviors at the original audit (observed)

From the two historical `.proto` files and their comments (as found at the audit):

- **Envelope:** `Frame{version, request_id, oneof body}` — versioned,
  correlated, exactly one operation per frame.
- **Handshake:** `ClientHello{min_version, max_version, credential}` →
  `ServerReady{connection_id}` or typed failure. Comments state
  credential is opaque, TLS-only, never interpreted/logged/persisted by
  the core; `connection_id` is opaque and MUST NOT be an auth session ID.
- **RPC:** `RpcRequest{method, payload, timeout_ms}` with canonical
  `/package.Service/Method` paths and opaque payloads; `RpcResult`
  with exactly one `payload` or `error{code, message}` outcome.
- **Cancellation:** `Cancel{}` targets its envelope `request_id`; comment
  states it requests cancellation, not rollback.
- **Notifications:** `Notification{payload}` — opaque, host-authorized,
  valid after `ready` only; no delivery/durable-state semantics.
- **Errors:** 17 generic codes (`CANCELLED`…`UNAUTHENTICATED`) plus
  `UNSPECIFIED` (invalid in failure outcomes); `RpcError.message` MUST
  NOT contain credentials or private diagnostics.
- **Evolution hygiene:** `reserved 16, 17` and
  `reserved "event", "resume", "ack"` — former application-replay
  operations permanently retired.
- **Correlation:** `request_id == 0` reserved for notifications;
  notifications MAY arrive before the corresponding `result`.

No transport adapter code, no handshake state machine, no timeout/
cancellation implementation, and no conformance tests were present.

## 3. Behavior defined only in implementation code

**None.** No implementation code (Rust or otherwise) was present in the
audited directory.

At the original audit, all observed behavior lived in `.proto` comments. Per ADR-001 those
comments are informative, not normative. Each behavior above MUST be
promoted to a normative specification via RFC before conformance can be
claimed. Tracked as future work in `CHANGELOG.md` (`Unreleased`).

## 4. Dependencies on private projects

**None found.**

- `import "syntra/v1/error.proto"` — intra-repository only.
- `option go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"`
  — public repository path, not a private dependency.
- No imports of messenger, chat SDK, server, Kafka, mail, or other
  sibling directories present in the surrounding workspace.
- No private registry, submodule, or vendored code.

Original verification: full-text search of the then-existing `schema/` for
private product names, company infrastructure, and unpublished paths
returned no hits. Future PRs MUST repeat this check against `proto/` per
`CONTRIBUTING.md` Sec. 5.

## 5. Application-specific types or methods

**None found.**

Searched for: chat messages, conversations, contacts, user profiles,
read/delivery receipts, messaging groups, payment, social, and related
terms — zero hits.

Types present at the audit were generic: `Frame`, `ClientHello`,
`ServerReady`, `RpcRequest`, `RpcResult`, `Cancel`, `Notification`,
`RpcError`, `ErrorCode`. Generic principals, endpoints, identities,
opaque payloads, requests, responses, streams, and events are the only
abstractions used — compliant with `SYN-ARCH-001/002`.

## 6. Classification

### Original reusable-as-is classification (preservation plan superseded; paths are historical, not live)

- Historical `schema/syntra/v1/error.proto` — keep package, enum values, field
  numbers, comments. Buf breaking detection MUST gate any edit.
- Historical `schema/syntra/v1/session.proto` — keep package, `Frame` numbers
  (1, 2, 10–15), `reserved` values, `oneof` discipline, message shapes.

Original rationale: these were the only wire contracts in existence.
Preserving them satisfied the original "no deletion/silent rewrite" plan
and gave the RFC process a stable base. These paths now identify historical
sources, not live files; see the pinned sources and descriptor archive in §8.

### Requiring extraction (do not publish)

- Nothing to extract: no application logic, private helper, or
  domain-specific code was co-located with the schemas.

### Missing at the foundation audit (subsequent status below)

- `buf.yaml` / `buf.gen.yaml` (Buf v2 governance)
- `specifications/core/*.md` (handshake, RPC, errors, streams)
- `specifications/transports/*.md` (7 v1 profiles)
- `specifications/security/*.md`
- Conformance + interop suite
- Rust reference implementation (non-normative)

Follow-up status at the layout migration: Buf configuration, generation tooling and
schema/codec tests now exist; core/security documents exist as unapproved
drafts. Transport profiles and the runtime conformance/reference
implementation remain forthcoming. See the follow-up migration section.

These MUST be written fresh from the charter and ADRs. They MUST NOT be
extracted from any private repository.

## 7. Original migration plan (historical; preservation plan superseded)

The following was the additive-only foundation plan. Its instruction to
retain both source files and its rollback assumption no longer govern the
layout; the later explicit user direction in §8 removes that tree.

1. **Preserve.** Keep both `.proto` files unchanged in this change.
   This plan makes zero wire edits.
2. **Surround.** Add charter (`specifications/architecture.md`), ADRs,
   foundation docs, and RFC process around the preserved schemas —
   exactly what this change does.
3. **Govern.** Add Buf v2 config in a follow-up RFC (lint + breaking
   check). Tooling subsequently arrived under Draft RFC 0001; its layout
   decision is now recorded as implemented in §8. Future field/behavior
   edits retain the RFC and `reserved` preservation requirements.
4. **Specify.** Promote each proto-comment behavior to a normative spec
   via focused RFCs (handshake → RPC → errors → streams → transports →
   security), each with requirement IDs and conformance tests.
5. **Verify.** Build the conformance suite against the specs, not against
   any private implementation. Use neutral fixtures (echo, generic
   key/value, generic subscription) and deterministic vectors.
6. **Implement.** Build the Rust reference to the specs. Any gap found
   during implementation triggers an RFC, not a silent proto edit.
7. **Exclude.** Ensure `.agents/`, `.opencode/`, `.DS_Store`, and any
   sibling private directories never enter the public history (see
   `.gitignore` guidance below and pre-push review).

Original rollback assumption (superseded): every step is additive. If a follow-up RFC is rejected, the
repository remains at this charter+ADRs+schemas state with no wire churn.

## 8. Pre-push checklist for `tinklehq/syntra`

### Follow-up sole-source IDL migration (2026-10-19)

Explicit user direction establishes `proto/syntra/v1` as the sole source of
truth and removes `schema/syntra/v1`. Draft
[RFC 0001](rfcs/0001-public-idl-layout.md) records that implemented layout
decision in B9; it remains Draft for unresolved behavior and review, without
claiming formal maintainer quorum or RFC acceptance.

Existing messages are physically split without renaming or renumbering;
binary declarations are preserved but source imports, owning descriptors,
and generated file-level APIs change. In particular `error.proto` becomes
`errors.proto`, and `Frame` moves from `session.proto` to `envelope.proto`.

The historical FILE comparison intentionally reports those known breaking
differences; layout authority is resolved, not awaiting layout approval.
The seven-file layout has an initial descriptor snapshot, not a fictitious
prior release. See [compatibility policy](specifications/schema/compatibility.md)
and [generation instructions](specifications/schema/generation.md).

Before removal, `compatibility/v1-initial/historical.json` is generated as
an immutable FileDescriptorSet from the actual unchanged sources from
commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9`:
[error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto)
and [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto).
The manifest retains `historical_sources` path/hash provenance and adds
`historical_image_sha256`; the existing `image.json` baseline is unchanged.
Tests verify the archived descriptor hash and historical declarations,
without depending on a Git checkout or duplicate source tree. The updated
suite includes the original 12 checks plus a sole-source regression check
(13 total); post-deletion execution results are pending in the
[validation record](specifications/schema/validation.md).

Protocol/security blockers remain pending. The layout decision supplies
no missing capability/session/error binding or runtime conformance result.

### Original foundation checklist

- [ ] `git log` shows schemas added unchanged (diff empty vs. audit copy).
- [ ] No `.agents/`, `.opencode/`, `.DS_Store`, or sibling private files
      in history.
- [ ] `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
      `SUPPORT.md`, `GOVERNANCE.md`, `CHANGELOG.md` present.
- [ ] `rfcs/README.md`, `rfcs/template.md` present.
- [ ] `specifications/architecture.md`, `specifications/decisions/` (10
      ADRs + index) present.
- [ ] No `LICENSE` file (intentional — pending maintainer decision per
      `GOVERNANCE.md` Sec. 7).
- [ ] No invented contact addresses in any file.
- [ ] Remote `tinklehq/syntra` created as public; `main` protected;
      private vulnerability reporting enabled.

## 9. Selected SC1 design record (2026-10-27)

### Inventory and status at the design record

This section is dated 2026-10-27. Its future-work statements describe that
design step; current experimental implementation evidence is recorded in §11.

The current baseline retains TLS 1.3/TCP, HTTPS/H1, HTTPS/H2, and WSS/H1
for public deployments, with restricted-development plaintext profiles.
Existing schemas, executable conformance profiles, and implementations
are unchanged by this record. The historical layout migration above is
independent of this proposed secure-channel work.

New [RFC 0007](rfcs/0007-secure-channel-device-authorization.md) is
**Draft, not Accepted**. The selected direction is transport-independent
Syntra Secure Channel v1 (SC1), with proposed
[secure-channel behavior](specifications/security/secure-channel.md),
[device authorization](specifications/security/device-authorization.md),
[TCP/UDP/WS bindings](specifications/transports/noise-bindings.md), and
[ADR-011 rationale](specifications/decisions/ADR-011-noise-device-authorization.md).
Selection does not amend the normative baseline or establish support.

### Selected target

- Initial enrollment uses `Noise_NK_25519_ChaChaPoly_SHA256`; host policy
  authorizes enrollment over the resulting protected channel.
- Each device has its own unique random shared 32-byte AK and opaque
  8-byte `auth_id` lookup handle. Returning channels use
  `Noise_NKpsk0_25519_ChaChaPoly_SHA256`. The AK is not a signing keypair,
  is not sent on reconnect, and is not `connection_id`; the handle is not
  authentication proof.
- Every channel uses fresh ephemeral material and directional traffic
  keys. M1/M2 payloads are empty, with no 0-RTT application data or
  credentials. The host verifies the first authenticated client transport
  record before protected actions; Syntra hello/ready remains required.
- Enrollment, storage, authorization, and revocation are host-owned. A
  deployment need not have human accounts.

### Compatibility and migration boundary

The proposed channel state machine is carrier-independent; the core does
not dial sockets or require WebSocket or gRPC. Existing HTTPS/WSS TLS
compatibility remains, and browser `wss://` still requires outer TLS.
Noise-in-WS is a distinct wire binding: existing WS/WSS profile IDs and
their one-binary-message/one-`Frame` mapping are not reinterpreted. The
UDP binding remains proposed, not newly supported by the runtime.

Returning-device authentication is a fresh channel, not Syntra session
resumption. It restores neither in-flight RPC outcomes nor subscriptions
and provides no basis for automatic retries. `connection_id` remains a
diagnostic value. AK provisioning/storage is separate from baseline
opaque `ClientHello.credential` carriage; no existing field is silently
reassigned to carry AK or `auth_id`.

Empty NK handshake bodies total 96 bytes; returning-device handshake
bodies plus the lookup handle total 104 = 96 + 8 bytes. Framing and extra
epoch/version fields are excluded, as are client transport-record
confirmation, Syntra hello/ready, and carrier establishment. These are
byte counts, not a complete establishment RTT or benchmark.

Acceptance, any eventual implementation migration, and executable
verification remain future work. The [SC1 conformance plan](conformance/plans/secure-channel.md)
is a plan only; no new conformance result or implementation claim is
recorded here. Existing baseline TLS requirements and executable profiles
continue to govern their current scope.

## Appendix: inventory and independence commands (current source root)

The original audit searched the now-removed schema tree. Use `proto/` for
current source checks; historical declarations and source provenance are
in [the compatibility archive](compatibility/v1-initial/README.md).

```sh
find . -type f -not -path "./.opencode/*" -not -name ".DS_Store" | sort
grep -ri "chat\|contact\|receipt\|messenger\|tinkle-server\|kafka\|payment" proto/ || echo "no hits"
```

## 10. Implementation extraction record (2026-10-27)

This repository returned to specification-first ownership and is
pre-release. On 2026-10-27, the in-tree language implementations were
extracted from source snapshot
`2a91da7fdb96f3e75badf07614c14e4f85c9ba1c` (the PR #12 merge) into separate
language implementation projects, out of scope for this repository:

| Source path in this repository | Disposition |
|---|---|
| `crates/` (five Rust crates, committed prost output, C headers, FFI contract) | Extracted; removed here |
| `bindings/go/` (Go module: protobuf types, pure-Go core, native adapter) | Extracted; removed here |
| `tests/integration/`, `tests/interoperability/` (Rust test fixtures) | Extracted; removed here |
| `tests/schema/rust/`, `tests/schema/go/` (language smoke suites) | Extracted; removed here |
| `conformance/runner/` (four-leg harness driving in-repo code) | Extracted; removed here (conformance definitions, manifests, and vectors stay) |
| `Cargo.toml`, `Cargo.lock`, `release-plz.toml`, `buf.gen.yaml` | Removed (downstream-owned) |
| `.github/workflows/release-plz.yml`, `release.yml`, and the rust/go/wasm/generated-freshness jobs in `repo-validation.yml` | Removed/replaced |
| `docs/production-runtime.md` (implementation-era build/native doc) | Extracted; removed here |
| `tests/test_release_workflow.py`, `tests/test_schema_drift.py`, `tests/test_conformance_runner.py` | Removed (coupled to removed artifacts) |

Kept here: `proto/` (sole IDL), `buf.yaml`, the
`compatibility/v1-initial/` baseline and historical archive,
`specifications/`, `rfcs/`, conformance definitions/manifests/test
vectors (minus the implementation harness), the repository validators
(`scripts/validate-repo.py` and `scripts/validate-schema.py`, which runs
the Buf checks and `tests/schema/test_schema.py`),
`tests/schema/test_schema.py` with its fixture, and `tests/test_license.py`.

Forward policy: release-please maintains document releases (`vX.Y.Z`
tags, GitHub Releases) bundling `CHANGELOG.md`; schema provenance rides
those tags. Language implementations pin schema revisions from here; no
language artifacts are published from this repository. The frozen
`go_package` option bytes in `proto/syntra/v1/*.proto` remain historical
module metadata (FILE-breaking to change against the initial baseline).

This record changes no wire format, requirement, capability, or normative
behavior. Executable conformance runs against any implementation remain
pending verification goals, not this repository's claims.

## 11. SC1 draft-1 implementation evidence (2026-10-28)

This is a subsequent implementation-evidence record, not retroactive RFC
acceptance or a change to historical release meaning. The
[self-contained implementation ledger](docs/sc1-implementation.md#implementation-status)
records delivered experimental Go TCP/WS/WSS bootstrap NK and returning
NKpsk0 channels, high-level ready-to-call connection helpers, bounded server
admission, channel-aware host policy and owned shutdown. UDP remains deferred;
HTTP/HTTPS request-response is excluded from this implementation. Baseline
profile definitions and production TLS policy remain unchanged. WSS retains
verified outer TLS ≥1.3 and a separate Noise pin, without automatic downgrade.

Draft-1 uses exact context domain/WS subprotocol `syntra.sc1.draft1`.
Canonical context binds mode, carrier, server-key ID, epoch, independent
eight-byte handle and exact UTF-8 scope. M1 is context plus 48 Noise bytes;
M2 is 48 bytes. TCP length-prefixes each handshake/record message with u16BE;
WS/WSS carry one binary message without that prefix. Both encrypt the inner
u32BE-length-prefixed frame stream with empty record AD. These experimental
bytes do not reinterpret existing WS/WSS profiles or change `Frame` fields.

### Authentication and lifecycle integration

The [host hook](docs/sc1-implementation.md#authentication-boundary) receives
freshly confirmed channel evidence and explicit hello credentials. Host policy
must independently verify root identity, current enrollment and admission
before ready, enforcing the intended returning-mode same-principal binding;
the library does not compare principals automatically. Nil method authorization now denies
calls. This is a behavior change from permissive implementation defaults,
not a new normative rule introduced by this record.

Running sessions own terminal transport closure. Successful high-level clients
outlive their dial context and must be closed explicitly. Dial establishment
has a 10s total budget; server admission defaults to 128 connections and 16
handshakes, retained through successful ready write. The post-ready writer
owns FIFO snapshots with 256-frame/8 MiB queued-plus-active caps, a 5s default
write timeout, a best-effort 200ms terminal drain and a 1s join after transport
close. The core 1s callback grace and high-level default/max 5s server shutdown
budget are separate; uncooperative I/O, lookup or callbacks cannot be forcibly
terminated. See [operational limits](docs/sc1-implementation.md#operational-limits).

### Evidence and remaining migration work

Final working-tree verification records Go 1.26.10 pure-Go/CGO-disabled tests,
root race/staticcheck, native-core race/staticcheck and Go 1.23.12 compatibility
passes. Docker integration completed in 30.681s, all six carrier/mode groups
executed with none skipped. Container cases use adapters with core sessions;
high-level connection orchestration has local unit coverage. Root/integration
reachable-vulnerability scans were zero, not dependency-wide advisory-free
findings. Three 100ms in-memory benchmark samples at CPU settings 1 and 4 on
darwin/arm64 Apple M4 passed without failed samples or a hard timing gate;
full RPCs are not zero-allocation. Conditions and measured results belong to
[verification evidence](docs/sc1-implementation.md#verification-evidence) and
[performance evidence](docs/perf-tradeoffs.md).

Same-implementation Docker and native-core passes are not independent SC1
wire interoperability or formal `CONF-*` conformance. Only authenticated
out-of-band provisioning is supported: no enrollment RPC or complete
issuance/delivery/ack, protected-storage or rotation workflow is supplied.
Independent security review, vectors/interoperability and RFC/ADR acceptance
remain open, as do native ABI completion-timestamp and post-hello
credential-release gaps. See [remaining work](docs/sc1-implementation.md#remaining-work).
No automatic session resume, subscription restoration or RPC replay is added.

## 12. Mobile v1 decision package and pending downstream migration (2026-10-28)

The selected [delivery target](docs/mobile-v1-delivery.md) requires SC1 and
standardized recovery. RFCs 0003–0008 now provide concrete review proposals;
they do not record maintainer/security approval or modify normative owners.
Core/schema/conformance activation precedes downstream standardization, then
independent execution precedes final implementation guidance and release claims.

Inspection found Rust local revision 1 and Go draft-1 incompatible at the SC1
context/prologue, mode/carrier encoding and WS subprotocol. RFC 0007 §11 pins
the inspected commits and proposes `syntra.sc1.v1`, context-only prologue,
explicit mode/carrier values and separate endpoint `/syntra/v1/sc1/ws`. Both
implementations need explicit migration from experimental identifiers; none is
silently aliased or retried after secure failure. The existing §11 ledger and
baseline `syntra.v1` WS mapping keep their historical meanings.

The proposed increasing request-ID rule, raw-body field partition, deadline
origins and recovery snapshot/generation changes are behavioral compatibility
changes, as are RFC 0003's fail-close behavior, version-mismatch code, peer
reporting, WebSocket timeout mapping and timer boundaries, and RFC 0004's
credential carriage and reauthentication changes. An explicit pre-stable
freeze/version designation and downstream inventory remain prerequisites.
RFC 0005 proposes the actual public Go generated
package path; the option bytes are unchanged here because that future edit is
FILE/source-breaking. Do not regenerate an immutable baseline or weaken Buf
checks to hide it. This change adds no generated types, runtime or artifacts.

The [mobile plan](conformance/plans/mobile-v1.md) and
[recovery plan](conformance/plans/update-recovery.md) state expected acceptance
coverage. Context JSON lint verifies public encoding consistency only, not
Noise cryptography, parser rejection, socket interop or production readiness.
