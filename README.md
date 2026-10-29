# Syntra

A general-purpose, transport-independent, binary client-server
communication protocol.

Syntra defines wire envelopes and Protobuf serialization, framing,
connection establishment, handshake and version negotiation, generic
authentication interfaces, logical sessions, request/response correlation
and generic RPC, capability negotiation, standardized errors, optional
generic event streams, transport profiles, and conformance requirements.

Syntra does **not** define any specific application's business logic,
data model, or internal architecture.

- Protocol version: Syntra v1 (in development — core/security drafts and
  public IDL tooling present; behavioral acceptance pending, see
  [Status](#current-protocol-status) and `SESSION-OPEN-QUESTIONS.md`)
- IDL: Protocol Buffers (proto3), governed by Buf v2; document releases are
  managed by release-please through this repository's Git tags and GitHub
  Releases (see [Schema distribution](#schema-distribution))
- Implementation evidence: delivered experimental Go SC1 draft-1 over
  TCP/WS/WSS, recorded in the [implementation ledger](docs/sc1-implementation.md#implementation-status);
  implementation behavior does not confer normative authority
- Methodology: Specification-Driven Development — specifications first,
  code second (this repository hosts specifications, schemas, and
  conformance definitions only)

> **New here?** Read this page for the architecture, then follow
> [`specifications/README.md`](specifications/README.md) (reading order),
> then the [`docs/implementer-guide.md`](docs/implementer-guide.md) to build
> an implementation. Normative detail lives in `specifications/`; this page
> is an overview and prevails nowhere over it.

---

## What Syntra is

One protocol core that runs over many transports via thin adapters,
carrying **opaque** application bytes:

- Hosts expose named methods (e.g., `/example.Echo/Echo`). Initiators
  invoke them with bounded budgets, correlate responses by `request_id`,
  and handle typed errors.
- Credentials, payloads, and event bytes are opaque to Syntra. Syntra
  routes, correlates, bounds, times out, and reports — it never parses
  application semantics or decrypts application ciphertext.
- `echo`, generic key/value requests (`get`/`put`), and generic event
  subscriptions are the neutral examples used in this repository.

## What Syntra is not

- Not a messenger, social platform, payment system, database, cloud
  deployment, or proprietary infrastructure.
- No chat messages, conversations, contacts, user profiles, or receipts.
- No application-level encryption, ratchet, or custom cipher. Applications
  needing end-to-end encryption implement it **above** Syntra with
  established libraries; Syntra carries the ciphertext opaquely (see
  [`docs/building-on-syntra.md`](docs/building-on-syntra.md)). The proposed
  SC1 peer-to-host secure channel below is separate from application E2EE.
- Not a transport: Syntra runs *over* TCP, TLS, HTTP, and WebSocket via
  adapter profiles (see [Transport profiles](#supported-v1-transports)).
- Not an RPC framework: Syntra defines correlation, deadlines,
  cancellation, and typed errors, but method semantics, payload schemas,
  and handler behavior belong to the application.
- Not Protobuf itself: Protobuf is the serialization IDL; Syntra is the
  protocol (state machines, negotiation, errors, profiles) around it.
- Transport receipt does not prove application processing. Only an
  application-level `RpcResult` proves an application outcome.
- Implementations conform to the spec; they are not the spec.

See `SYN-ARCH-001/002` in `specifications/architecture.md`.

## Architecture

Current baseline layering (the selected SC1 proposal is described below):

```text
Application Protocol          (methods, payload schemas, auth policy — yours)
       ↓
Syntra RPC / Events           (correlation, deadlines, cancel, notifications)
       ↓
Syntra Core                   (envelope, handshake, sessions, errors, versions)
       ↓
Transport Profile             (TCP / TLS / HTTP / HTTPS / WebSocket adapter)
       ↓
Network Transport             (sockets, TLS, HTTP — established implementations)
```

Each layer has exactly one owner (see
[Specification authority](#specification-authority)): the application owns
meaning; Syntra owns the protocol mechanics; the adapter owns byte framing;
established libraries own the network. Layers MUST NOT absorb each other's
responsibilities (`SYN-ARCH-010`–`013`).

## Current protocol status

- [x] Charter (`specifications/architecture.md`)
- [x] ADRs 001–010 (`specifications/decisions/`)
- [x] Open-source foundation (contributing, governance, RFC process)
- [x] Core specifications — handshake, RPC, errors, streams, sessions,
  reliability, capabilities, versioning (`specifications/core/*.md`,
  **drafts, acceptance pending**)
- [x] Transport specifications — all 7 v1 profiles
  (`specifications/transports/*.md`, **drafts, acceptance pending**)
- [x] Security specifications (`specifications/security/*.md`,
  **drafts, acceptance pending**)
- [x] Conformance + interop suite (`conformance/`, executable manifests
  and test vectors)
- [x] Bounded experimental SC1 draft-1 TCP/WS/WSS implementation, connection
  orchestration, local regressions, and same-implementation Docker integration
  recorded in the [evidence ledger](docs/sc1-implementation.md#verification-evidence)
- Independent SC1 wire interoperability and formal conformance verdicts
  remain pending; local test passes are not RFC acceptance

Each item is accepted via the RFC process in `rfcs/README.md`.
Release-blocking open questions are tracked in `SESSION-OPEN-QUESTIONS.md`
and the RFC set; no stable `v1` release exists yet. Draft
status means: implementable for interop experiments, not yet stable —
check the referenced RFCs before freezing a production dependency.

The selected [mobile v1 delivery target](docs/mobile-v1-delivery.md) requires
SC1 and standardized update recovery, plus mobile lifecycle and independent
Rust/Go verification. RFCs 0003–0008 contain selected proposals, not approvals.
The current Rust/Go SC1 experimental formats differ; the canonical wire proposal
and migration are in RFC 0007 §11. No interoperability fix or conformance pass
is claimed until downstream execution establishes it.

The SC1 design remains **Draft, not Accepted** in
[RFC 0007](rfcs/0007-secure-channel-device-authorization.md). An experimental
draft-1 implementation is delivered; its contract and evidence are recorded
here without promoting it to accepted production policy. Baseline TLS
requirements and all existing executable conformance profiles are unchanged.

## Supported v1 transports

These are the current baseline profiles, not the proposed SC1 bindings.

**Production-capable (secure):** TLS 1.3 over TCP (`SNTR-TLS-TCP-V1`),
HTTPS via HTTP/1.1 (`SNTR-HTTPS-H1-V1`), HTTPS via HTTP/2
(`SNTR-HTTPS-H2-V1`), Secure WebSocket over HTTP/1.1 (`SNTR-WSS-H1-V1`).

**Restricted development only (trusted environments — loopback or
isolated test networks, never public traffic):** TCP (`SNTR-TCP-V1`),
HTTP/1.1 (`SNTR-HTTP-V1`), WebSocket over HTTP/1.1 (`SNTR-WS-V1`).

**Deferred (future extensions only, MUST NOT be described as
implemented):** Raw UDP, DTLS, QUIC, HTTP/3, QUIC DATAGRAM, WebSocket
over HTTP/2 Extended CONNECT.

Insecure transports MUST NOT be used for public production traffic
(`SYN-ARCH-030`). See
[`docs/transport-selection.md`](docs/transport-selection.md) for neutral
selection guidance and the per-profile specifications for bindings.

## Experimental implementation: Syntra Secure Channel v1 (SC1)

SC1 is a transport-independent secure-channel state machine beneath Syntra
envelopes. The delivered Go draft-1 implementation uses:

- **Bootstrap:** `Noise_NK_25519_ChaChaPoly_SHA256`, with a provisioned host
  static-key pin. NK authenticates the host, not an enrolled client. Only
  authenticated out-of-band provisioning is supported; no enrollment RPC
  or complete issuance/storage/rotation workflow is implemented.
- **Returning device:** `Noise_NKpsk0_25519_ChaChaPoly_SHA256`, using a
  unique, random shared **32-byte authorization key (AK)** per device and
  an opaque **8-byte `auth_id`** for host-side key lookup. The AK is not
  sent on reconnect. `auth_id` is a lookup handle, not proof of authority;
  neither value is `ServerReady.connection_id`, which remains diagnostic.
- **Every channel:** fresh ephemeral key material and fresh directional
  traffic keys. Noise handshake messages M1 and M2 have empty payloads:
  no 0-RTT application data or credentials. Before any protected action,
  the host first verifies an authenticated client transport record. Syntra
  `ClientHello`/`ServerReady` and readiness checks are still required.

The channel-aware host hook receives confirmed channel evidence and explicit
`ClientHello.credential` bytes. Host policy must independently verify the root
credential, current enrollment and admission before `ServerReady`, enforcing
the intended returning-mode same-principal binding itself: the library does
not compare principals automatically. Missing method authorization denies calls. See the
[authentication boundary](docs/sc1-implementation.md#authentication-boundary).

Delivered carriers are **TCP, WS and WSS**, in bootstrap and returning modes.
UDP is deferred. HTTP/HTTPS request-response is excluded from this
implementation; HTTP is used for WebSocket upgrade. Existing baseline profile
definitions remain. SC1 uses the distinct `syntra.sc1.draft1` context domain
and WS subprotocol, not the baseline `syntra.v1` mapping. WSS retains verified
outer TLS 1.3 or newer; there is no automatic downgrade.

The canonical context is 42–296 bytes; M1 is context plus 48 Noise bytes,
and M2 is 48 bytes. Both modes therefore use **138–392 bytes before carrier
framing**, excluding confirmation and core hello/ready. TCP prefixes every
handshake/record message with u16BE; WS carries one message without that prefix.
Records protect an inner u32BE-length-prefixed frame stream, with empty AD,
65,535-byte ciphertext and 1 MiB serialized-frame ceilings.

Ready-to-call connection helpers bound socket/upgrade, SC1 and core readiness
to 10s total; successful client lifetime is independently owned. Server
admission defaults to 128 connections/16 handshakes, held through ready write.
Post-ready output uses one owned FIFO writer, bounded to 256 queued-plus-active
frames/8 MiB, with a 5s default per-write timeout. Sessions own transport close;
reconnect, subscription restoration and RPC replay remain explicit application
decisions. Exact limits and shutdown qualifications are in
[operational limits](docs/sc1-implementation.md#operational-limits).

Read the proposed [secure channel](specifications/security/secure-channel.md),
[device authorization](specifications/security/device-authorization.md),
[carrier bindings](specifications/transports/noise-bindings.md), and
[ADR-011 rationale](specifications/decisions/ADR-011-noise-device-authorization.md).
The [SC1 conformance plan](conformance/plans/secure-channel.md) distinguishes
local evidence from formal coverage. Docker exercised all six carrier/mode
groups, but same-implementation tests and native-core linkage are not independent
SC1 wire interoperability. [Performance evidence](docs/perf-tradeoffs.md) covers
in-memory measurements, not a deployment-speed guarantee. Independent review,
vectors/interoperability and native ABI completion-time/credential-release gaps
remain [open](docs/sc1-implementation.md#remaining-work). RFC 0007 and Proposed
ADR-011 still require acceptance; this evidence does not replace production TLS.
See [migration record §11](MIGRATION.md#11-sc1-draft-1-implementation-evidence-2026-10-28)
for the current implementation scope.

## Specification structure

```text
README.md                      — this file
specifications/README.md       — specification index + reading order
specifications/architecture.md — project charter + ownership matrix
specifications/core/           — transport-independent behavior
  (protocol, serialization, framing, handshake, authentication,
   sessions, rpc, events, reliability, capabilities, errors, versioning)
specifications/transports/     — per-profile byte bindings (tcp, tls-tcp,
  http, https, websocket, secure-websocket)
specifications/security/       — threat model, transport/auth/replay/opaque
  rules, test plan, review checklist
specifications/schema/         — IDL reference, generation, compatibility,
  validation records
specifications/decisions/      — baseline ADRs 001–010; proposed ADR-011 for SC1
proto/syntra/v1/               — sole authoritative Protobuf source (eight files)
buf.yaml                         — Buf v2 validation (STANDARD lint, FILE breaking; no registry identity)
compatibility/v1-initial/      — initial baseline + archived historical descriptors
tests/schema/                  — descriptor and codec validation (Buf gates; no committed generation)
conformance/                   — executable conformance suite (manifests,
  profiles, test vectors, claims, declarations)
docs/                          — implementer guides, glossary, FAQ, registry docs
rfcs/                          — public RFC process, template, proposals (including Draft RFC 0007)
audits/                        — independent consistency review (findings + RFC path)

Language implementations are separate projects, out of scope for this
repository.
```

Core/security drafts live in `specifications/core/*.md` and
`specifications/security/*.md`, pending acceptance through the RFC process.
Start with [`specifications/README.md`](specifications/README.md) for the
ordered reading path.

## Repository boundary

This repository is the authoring authority for the Syntra protocol: normative
sources, schemas, and the conformance/validation tooling. It contains no
implementation code; language implementations are separate projects, out of
scope for this repository and non-normative. There is no Buf Schema Registry
publication or GHCR image, and no language-artifact publishing from this
repository.

```text
Syntra Git repository (spec-first)
        │
        │ contains source schemas + validation tooling
        ▼
release-please document releases (vX.Y.Z tags + GitHub Releases)
        │
        └── protocol consumers and implementations pin schemas by
            exact Git revision or release tag
```

Normative (the specification):

- `proto/` — sole authoritative Protobuf source schemas
- `specifications/` — protocol, transport, and security behavior;
  IDL reference, generation, and compatibility records; ADRs
- `conformance/` — requirements, manifests, test vectors, declarations

Supporting (validation, process, explanation):

- `docs/`, `rfcs/`, `audits/`
- `docs/sc1-implementation.md` — self-contained experimental contract and
  implementation evidence; it does not amend draft requirements or grant conformance
- `scripts/`, `tests/` — repository validation tooling only (requirement
  linter, manifest and vector validators, descriptor and codec checks;
  never a Syntra client/server implementation). `.tmp/` holds only
  disposable reproducibility output and must never be committed

Distribution:

- release-please maintains a release PR bundling document changes into
  `CHANGELOG.md`; merging it tags `vX.Y.Z` and creates the GitHub Release
  for this repository (documents and schema provenance, no language
  artifacts).
- Language artifact distribution is out of scope for this repository;
  implementations pin schema revisions from here.

External and non-normative (never in this repository):

- Syntra implementations (separate projects)
- Generated SDK consumers
- Applications using Syntra

No generated language types are committed in this repository: there is no
`gen/` or `generated/` directory, no `bindings/` or `crates/` tree, no root
Cargo manifest, and CI fails if any of those return, if `.tmp/` output is
tracked, or if stray generated-code files appear. Consumers generate types
with the pinned toolchain (see [`specifications/schema/generation.md`](specifications/schema/generation.md))
or take them from the implementation repositories. Generated packages
provide message types only — they do not implement the handshake, session
lifecycle, authentication, RPC correlation, idempotency, retries, event
streams, TCP framing, HTTP transport, or WebSocket transport (see
[`docs/schema-registry.md`](docs/schema-registry.md) §6).

## Schema distribution

Schema assets are released from this repository via release-please Git tags
(`vX.Y.Z`) and GitHub Releases; there is no Buf Schema Registry module and no
`buf push` (see `buf.yaml`: no registry `name:` by design):

- Release tag: `vX.Y.Z` (release-please, document releases)
- Package defined: `syntra.v1` (`proto/syntra/v1/*.proto`)
- Consumer contract, pinning, version mapping, and release policy:
  [`docs/schema-registry.md`](docs/schema-registry.md)

No generated language packages are committed or published here. Consumers
generate types with the pinned toolchain documented in
[`specifications/schema/generation.md`](specifications/schema/generation.md)
or take them from your implementation's pinned tree. Generated
packages provide message types only — they do not implement the handshake,
session lifecycle, authentication, RPC correlation, idempotency, retries,
event streams, TCP framing, HTTP transport, or WebSocket transport (see
[`docs/schema-registry.md`](docs/schema-registry.md) §6).

## Conformance model

Conformance is proven per **profile** (`conformance/profiles.yaml`), never
by a vague "Syntra compatible" claim:

- Mandatory core: `SNTR-CORE-V1` (envelope, serialization, handshake, RPC,
  errors, auth interface, bounds), `SNTR-SESS-V1`, `SNTR-RPC-V1` — required
  for every claim, over at least one transport profile.
- Optional capability: `SNTR-EVENTS-V1` — only when event streams are claimed.
- Transport profiles: `SNTR-TCP-V1`, `SNTR-TLS-TCP-V1`, `SNTR-HTTP-V1`,
  `SNTR-HTTPS-H1-V1`, `SNTR-HTTPS-H2-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`.
  No implementation must support every transport to claim Core conformance.

Machine-readable test manifests live in `conformance/manifest/`, vectors in
`conformance/test-vectors/`, claim wording in `conformance/claims.md`.
Example claim: "Conforms to Syntra Core v1 and WSS/H1 v1". See
`conformance/README.md` for verdicts, declarations, and the full model.

## RFC process

Normative changes (any MUST/SHOULD, wire field, state machine, error code,
transport mapping, security requirement, conformance assertion) REQUIRE a
public RFC (`rfcs/README.md`) with maintainer quorum; breaking changes
REQUIRE a major-version RFC with migration notes (`GOVERNANCE.md` Sec. 3–4).
Non-normative fixes (typos, clarifications with no behavioral change, docs,
examples) may land as direct PRs. Significant wire-compat or security
disputes MUST become an RFC or a recorded blocker — never an undocumented
implementation choice.

## Security reporting

Do **not** open public issues for vulnerabilities. Use GitHub's private
vulnerability reporting for this repository as described in
[`SECURITY.md`](SECURITY.md).

## Versioning policy

Five independent dimensions that MUST NOT be conflated
(`specifications/core/versioning.md`, `SNTR-VER-001`): Protobuf schema
package (`syntra.v1`), core wire version (`Frame.version`, currently 1),
transport profile revision, extension/capability revision, implementation
release version. Additive changes (new optional field/variant/code,
relaxed validation) are minor and MUST stay backward compatible; breaking
changes (repurposed numbers, new required behavior, altered state machines,
weakened security) REQUIRE a new wire major version, a major RFC, migration
notes, and a `CHANGELOG.md` entry. Unknown Protobuf fields MUST be ignored;
unknown `Frame.body` variants MUST be rejected with `UNIMPLEMENTED`; `reserved
16, 17` and `reserved "event", "resume", "ack"` are permanent.

## Schema snapshot (v1, current representation)

```proto
message Frame {
  uint32 version = 1;
  uint64 request_id = 2;   // hello/ready/notification: 0; request/result/cancel: nonzero
  reserved 16, 17;
  reserved "event", "resume", "ack";
  oneof body {
    ClientHello hello = 10;
    ServerReady ready = 11;
    RpcRequest request = 12;
    RpcResult result = 13;
    Cancel cancel = 14;
    Notification notification = 15;
  }
}
```

`reserved 16, 17` and `reserved "event", "resume", "ack"` are permanent.
See [`proto/syntra/v1/envelope.proto`](proto/syntra/v1/envelope.proto)
and ADR-004/009. The schema reference documents runtime validation gaps;
the snapshot does not resolve the pending behavioral requirements.

## Repository layout (full)

```text
README.md                      — this file
CONTRIBUTING.md                — how to contribute
CODE_OF_CONDUCT.md             — community standards
SECURITY.md                    — how to report vulnerabilities privately
SUPPORT.md                     — where to get help
GOVERNANCE.md                  — who decides what, releases, breaking changes
CHANGELOG.md                   — release history (Keep a Changelog)
MIGRATION.md                   — historical audit, layout migration, selected SC1 design record
SESSION-OPEN-QUESTIONS.md      — release-blocking open questions
rfcs/                          — public RFC process, template, proposals (including Draft RFC 0007)
proto/syntra/v1/               — sole authoritative Protobuf source (eight files)
buf.yaml                         — Buf v2 validation (STANDARD lint, FILE breaking; no registry identity)
specifications/                — charter, core, transports, security, schema, ADRs
specifications/schema/         — IDL reference, generation and compatibility docs
compatibility/v1-initial/      — initial baseline + archived historical descriptors
tests/schema/                  — descriptor and codec validation
conformance/                   — executable suite: manifests, profiles, vectors
docs/                          — implementer guides, glossary, FAQ, registry docs
audits/                        — consistency review findings + RFC path
```

The user-directed layout decision is implemented and recorded in
[RFC 0001 B9](rfcs/0001-public-idl-layout.md#b9-recorded-layout-decision-and-known-source-break).
The old `schema/syntra/v1` tree is removed; historical provenance and
declarations are archived in [the compatibility baseline](compatibility/v1-initial/README.md).
This records a layout decision, not formal maintainer quorum or approval
of the remaining behavioral RFC questions.

## Specification authority

| Concern | Authoritative source |
|---------|----------------------|
| Data representation | `proto/syntra/v1/*.proto` (sole source of truth) |
| Behavior | `specifications/core/*.md` (drafts, acceptance pending) |
| Network mappings | `specifications/transports/*.md` (drafts, acceptance pending) |
| Security requirements | `specifications/security/*.md` (drafts, acceptance pending) |
| Executable verification | Conformance suite (`conformance/`) |
| Implementation evidence | `docs/sc1-implementation.md` (**informative**; implementation behavior does not override specifications) |

In case of conflict, the listed owner prevails. See
`specifications/architecture.md` Sec. 8 for the full matrix
(`SYN-ARCH-040`–`SYN-ARCH-045`).

### Public IDL tooling

See the [schema documentation](specifications/schema/README.md) for pinned
toolchains and `python3 scripts/validate-schema.py` (Buf format, lint,
build, and breaking checks against the initial baseline; this repository
commits no generated language types — generation is downstream-owned by the
implementation repositories).
[RFC 0001](rfcs/0001-public-idl-layout.md) records the implemented layout
decision, known FILE/source break, and missing capability/session/error
bindings. Tests use the immutable archived historical descriptor, without a
Git checkout or duplicate source tree. The [validation
record](specifications/schema/validation.md) distinguishes the original run
from pending post-deletion results. This is not a complete v1 runtime or a
claim that the core/security drafts have been approved.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md), the
[Code of Conduct](CODE_OF_CONDUCT.md), and [`GOVERNANCE.md`](GOVERNANCE.md).
Propose normative changes via RFC. Every MUST/MUST NOT needs a
requirement ID and a conformance test link. Be kind and precise.

## Security

Do **not** open public issues for vulnerabilities. Use GitHub's private
vulnerability reporting for this repository as described in
[`SECURITY.md`](SECURITY.md).

## License

Apache-2.0 — see [`LICENSE`](LICENSE). See [`GOVERNANCE.md`](GOVERNANCE.md) Sec. 7.
