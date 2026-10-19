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

- Protocol version: Syntra v1 (in development — charter + ADRs accepted,
  normative specifications forthcoming)
- IDL: Protocol Buffers (proto3), governed by Buf v2
- Reference implementation: Rust (forthcoming, non-normative)
- Methodology: Specification-Driven Development — specifications first,
  code second

> **New here?** Start with [`specifications/architecture.md`](specifications/architecture.md)
> (project charter). It explains what Syntra is and is not, design goals,
> roles, transports, and who owns what. Then read the
> [decision records](specifications/decisions/README.md).

---

## What Syntra is for

One protocol core that runs over many transports via thin adapters,
carrying **opaque** application bytes:

- `echo`, generic key/value requests (`get`/`put`), and generic event
  subscriptions are the neutral examples used in this repository.
- Hosts expose named methods (e.g., `/example.Echo/Echo`). Initiators
  invoke them with bounded budgets, correlate responses by `request_id`,
  and handle typed errors.
- Credentials, payloads, and event bytes are opaque to Syntra. Syntra
  routes, correlates, bounds, times out, and reports — it never parses
  application semantics or decrypts application ciphertext.

## What Syntra is not

- Not a messenger, social platform, payment system, database, cloud
  deployment, or proprietary infrastructure.
- No chat messages, conversations, contacts, user profiles, or receipts.
- No application-level encryption, ratchet, or custom cipher.
- Transport receipt does not prove application processing.
- The Rust implementation conforms to the spec; it is not the spec.

See `SYN-ARCH-001/002` in `specifications/architecture.md`.

## Repository layout

```text
README.md                      — this file
CONTRIBUTING.md                — how to contribute
CODE_OF_CONDUCT.md             — community standards
SECURITY.md                    — how to report vulnerabilities privately
SUPPORT.md                     — where to get help
GOVERNANCE.md                  — who decides what, releases, breaking changes
CHANGELOG.md                   — release history (Keep a Changelog)
MIGRATION.md                   — audit + migration plan for existing schema
rfcs/                          — public RFC process and template
schema/syntra/v1/              — authoritative Protobuf (error.proto, session.proto)
specifications/architecture.md — project charter + ownership matrix
specifications/decisions/      — ADRs 001–010 (each with an owner)
```

Normative behavior will live in `specifications/*.md` (core),
`specifications/transports/*.md`, and `specifications/security/*.md`
as they are accepted through the RFC process. The conformance suite and
Rust reference implementation are forthcoming and will be linked from
`CHANGELOG.md` when available.

## Specification authority

| Concern | Authoritative source |
|---------|----------------------|
| Data representation | `schema/syntra/v1/*.proto` |
| Behavior | `specifications/*.md` |
| Network mappings | `specifications/transports/*.md` (forthcoming) |
| Security requirements | `specifications/security/*.md` (forthcoming) |
| Executable verification | Conformance suite (forthcoming) |
| Implementation | Rust reference (forthcoming, **non-normative**) |

In case of conflict, the listed owner prevails. See
`specifications/architecture.md` Sec. 8 for the full matrix
(`SYN-ARCH-040`–`SYN-ARCH-045`).

## Supported v1 transports

**Production-capable (secure):** TLS 1.3 over TCP, HTTPS via HTTP/1.1,
HTTPS via HTTP/2, Secure WebSocket over HTTP/1.1.

**Restricted development only:** TCP, HTTP/1.1, WebSocket over HTTP/1.1.

**Deferred (future extensions only):** Raw UDP, DTLS, QUIC, HTTP/3,
QUIC DATAGRAM, WebSocket over HTTP/2 Extended CONNECT.

Insecure transports MUST NOT be used for public production traffic
(`SYN-ARCH-030`).

## Wire snapshot (v1, current)

```proto
message Frame {
  uint32 version = 1;
  uint64 request_id = 2;   // 0 reserved for notifications
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
See `schema/syntra/v1/session.proto` and ADR-004/009.

## Status and roadmap

- [x] Charter (`specifications/architecture.md`)
- [x] ADRs 001–010 (`specifications/decisions/`)
- [x] Open-source foundation (contributing, governance, RFC process)
- [ ] Core specifications (handshake, RPC, errors, streams)
- [ ] Transport specifications (7 v1 profiles)
- [ ] Security specifications
- [ ] Conformance + interop suite
- [ ] Rust reference implementation (non-normative)

Each item is accepted via the RFC process in `rfcs/README.md`.
No production code is deleted or silently rewritten; see `MIGRATION.md`.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md), the
[Code of Conduct](CODE_OF_CONDUCT.md), and [`GOVERNANCE.md`](GOVERNANCE.md).
Propose normative changes via RFC. Every MUST/MUST NOT needs a
requirement ID and a conformance test link. Be kind and precise.

## Security

Do **not** open public issues for vulnerabilities. Use GitHub's private
vulnerability reporting for this repository as described in
[`SECURITY.md`](SECURITY.md).

## License — pending maintainer decision

No license has been selected. There is **no `LICENSE` file** in this
repository yet. All rights are reserved pending maintainer approval.
See [`GOVERNANCE.md`](GOVERNANCE.md) Sec. 7 for the license alternatives
under consideration (e.g., Apache-2.0, MIT, BSD-3-Clause) and their
implications. Do not assume any license until a `LICENSE` file is added
by maintainers.
