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
- IDL: Protocol Buffers (proto3), governed by Buf v2, distributed via
  crates.io, nested Go module tags, and GitHub Releases (see [Schema distribution](#schema-distribution))
- Reference implementation: Rust (non-normative, with production native ABI)
- Methodology: Specification-Driven Development — specifications first,
  code second

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
  [`docs/building-on-syntra.md`](docs/building-on-syntra.md)).
- Not a transport: Syntra runs *over* TCP, TLS, HTTP, and WebSocket via
  adapter profiles (see [Transport profiles](#supported-v1-transports)).
- Not an RPC framework: Syntra defines correlation, deadlines,
  cancellation, and typed errors, but method semantics, payload schemas,
  and handler behavior belong to the application.
- Not Protobuf itself: Protobuf is the serialization IDL; Syntra is the
  protocol (state machines, negotiation, errors, profiles) around it.
- Transport receipt does not prove application processing. Only an
  application-level `RpcResult` proves an application outcome.
- The Rust implementation conforms to the spec; it is not the spec.

See `SYN-ARCH-001/002` in `specifications/architecture.md`.

## Architecture

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
- [x] Rust runtime with production native ABI (`syntra-core`, `syntra-runtime`, `syntra-ws`, `syntra-ffi` production feature, Go `syntranative` adapter; see `docs/production-runtime.md`)

Each item is accepted via the RFC process in `rfcs/README.md`.
Release-blocking open questions are tracked in `SESSION-OPEN-QUESTIONS.md`
and the RFC set (`rfcs/0001`–`0005`); no `v1` release exists yet. Draft
status means: implementable for interop experiments, not yet stable —
check the referenced RFCs before freezing a production dependency.

## Supported v1 transports

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
specifications/decisions/      — ADRs 001–010 (each with an owner)
proto/syntra/v1/               — sole authoritative Protobuf source (seven files)
buf.yaml                         — Buf v2 validation (STANDARD lint, FILE breaking; no registry identity)
compatibility/v1-initial/      — initial baseline + archived historical descriptors
crates/                        — Rust workspace (protocol cores plus `syntra-ffi` with test-fixture and production ABIs; WASM unsupported; committed prost output, drift-checked)
bindings/go/                   — committed Go protobuf types + production native adapter + supported pure-Go core (drift-checked; default and `syntranative` tags)
tests/schema/                  — descriptor and codec validation (committed generation drift-checked; .tmp/ holds disposable repro only)
conformance/                   — executable conformance suite (manifests,
  profiles, test vectors, claims, declarations)
docs/                          — implementer guides, glossary, FAQ, registry docs
rfcs/                          — public RFC process, template, RFCs 0001–0005
audits/                        — independent consistency review (findings + RFC path)
```

Core/security drafts live in `specifications/core/*.md` and
`specifications/security/*.md`, pending acceptance through the RFC process.
Start with [`specifications/README.md`](specifications/README.md) for the
ordered reading path.

## Repository boundary

This repository is the authoring authority for the Syntra protocol: normative
sources plus the Rust/Go generated types and the tooling that validates them.
Rust crates are published to crates.io by release-plz after a reviewed Release
PR merges. Go modules are fetched through the Go proxy using nested module
tags. There is no Buf Schema Registry publication or GHCR image.

```text
Syntra Git repository
        │
        │ contains source schemas + committed generated types
        ▼
Per-crate tags (<crate>-vX.Y.Z) + crates.io + GitHub Releases
        │
        ├── Rust source / crate archives + SHA256SUMS (syntra-core release)
        ├── descriptor (image.json) + manifests + test vectors
        │       │
        │       ▼
        │   Rust consumers pin crates.io versions or exact Git revisions
        │
        └── Go consumers use bindings/go/vX.Y.Z at the syntra-core revision
            (default pure-Go mode; native mode via the production library)
```

Normative (the specification):

- `proto/` — sole authoritative Protobuf source schemas
- `specifications/` — protocol, transport, and security behavior;
  IDL reference, generation, and compatibility records; ADRs
- `conformance/` — requirements, manifests, test vectors, declarations

Supporting (validation, process, explanation):

- `docs/`, `rfcs/`, `audits/`
- `scripts/`, `tests/` — repository validation tooling only (requirement
  linter, manifest and vector validators, descriptor and codec checks;
  never a Syntra client/server implementation). Committed generation is
  drift-checked (`scripts/validate-schema.py --drift-only`, CI-enforced);
  `.tmp/` holds only disposable reproducibility output and must never be
  committed

Distribution:

- release-plz creates `<crate>-vX.Y.Z` tags and crates.io releases. The
  `syntra-core-vX.Y.Z` tag anchors schema assets and the nested Go module tag
  `bindings/go/vX.Y.Z` at the same commit. Global `vX.Y.Z` tags are not used.
- The syntra-core GitHub Release carries source/crate archives,
  descriptor/manifests/vectors, and SHA256SUMS (see `RELEASE.md` §5).
- `release-plz.yml` calls `release.yml` directly after publishing syntra-core;
  `release.yml` creates or verifies the nested Go tag and warms the Go proxy.
  Maintainers authorize releases through reviewed Release PRs.

External and non-normative (never in this repository):

- Syntra implementations (separate client/server projects)
- Generated SDK consumers
- Applications using Syntra

Generated Go/Rust types ARE committed here under `crates/` (Rust prost
output) and `bindings/go/` (Go protobuf output, incl. `*.pb.go`): there is
no `gen/` or `generated/` directory and no `bindings/` root outside
`bindings/go/`, and CI fails if legacy trees return, if `.tmp/` output is
tracked, or if committed types drift from a pinned regeneration. Generated
packages provide message types only — they do not implement the handshake,
session lifecycle, authentication, RPC correlation, idempotency, retries,
event streams, TCP framing, HTTP transport, or WebSocket transport (see
[`docs/schema-registry.md`](docs/schema-registry.md) §6).

## Schema distribution

Schemas and generated types ship via crates.io, Git-backed Go modules, and
GitHub Releases — there is no Buf Schema Registry module and no
`buf push` (see `buf.yaml`: no registry `name:` by design):

- Schema tag consumed: `syntra-core-vX.Y.Z` (and `-rc.N` prereleases) plus nested Go
  module tag `bindings/go/vX.Y.Z` at the same revision
- Package defined: `syntra.v1` (`proto/syntra/v1/*.proto`)
- Consumer contract, pinning, version mapping, and release policy:
  [`docs/schema-registry.md`](docs/schema-registry.md)

Committed generated packages contain **data structures only**. They do not
implement the handshake, session lifecycle, authentication behavior, RPC
correlation, idempotency, retries, event streams, TCP framing, HTTP
transport, or WebSocket transport — that is your implementation's job
(see [`docs/implementer-guide.md`](docs/implementer-guide.md) and the
[FAQ](docs/faq.md)). See [Repository boundary](#repository-boundary)
for what lives where. Pin Rust crate versions or exact Git revisions; Go consumers use the
default pure-Go module or link the production library with
`-tags syntranative` (see `docs/production-runtime.md` and
`bindings/go/README.md`). No browser WASM release asset is currently
promised. Native distribution requires the matching header and
cross-language link/runtime tests; a Rust compile check alone is
insufficient.

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
MIGRATION.md                   — historical audit + implemented layout migration
SESSION-OPEN-QUESTIONS.md      — release-blocking open questions
rfcs/                          — public RFC process, template, RFCs 0001–0005
proto/syntra/v1/               — sole authoritative Protobuf source (seven files)
buf.yaml                         — Buf v2 validation (STANDARD lint, FILE breaking; no registry identity)
crates/                        — Rust workspace (protocol cores; `syntra-ffi` with test-fixture and production ABIs; committed generation)
bindings/go/                   — committed Go protobuf types + supported pure-Go core + production native adapter
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
| Implementation | Rust reference in `crates/` (**non-normative**; see `docs/production-runtime.md`) |

In case of conflict, the listed owner prevails. See
`specifications/architecture.md` Sec. 8 for the full matrix
(`SYN-ARCH-040`–`SYN-ARCH-045`).

### Public IDL tooling

See the [schema documentation](specifications/schema/README.md) for pinned
toolchains and `python3 scripts/validate-schema.py` (committed generation
into `crates/` + `bindings/go/`, drift-checked; `.tmp/` holds only
disposable reproducibility output).
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

Apache-2.0 — see [`LICENSE`](LICENSE). Rust packages inherit
`license = "Apache-2.0"` and are eligible for crates.io publication through
release-plz. See [`GOVERNANCE.md`](GOVERNANCE.md) Sec. 7.
