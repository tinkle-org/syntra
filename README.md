# Syntra

Syntra is a binary client–server protocol for remote procedure calls and
notifications over a protected connection. A client invokes a named method
with an opaque byte payload; the server returns a result with the same
request identifier. Calls can run concurrently and complete out of order.

Applications define their methods, payload formats, authorization policy,
and durable storage. Syntra defines the message exchanges, channel protection,
and delivery semantics. **Syntra 1.0 is pre-release.**

## Protocol structure

Syntra 1.0 defines one protocol with mandatory channel protection. TCP, WS,
and WSS are carrier mappings of that protocol, not separately selectable
security profiles. Update recovery is an optional capability on the same
authenticated connection.

The protocol has three layers. The message layer encodes requests, results,
cancellation, and notifications as Protobuf `Frame` envelopes. The security
layer authenticates establishment and encrypts the framed message stream
using Noise. The transport layer carries handshake messages and protected
records over TCP, WebSocket, or WebSocket over TLS.

```text
Application methods and opaque payloads
                   ↓
       Syntra messages and RPC
                   ↓
       Authenticated Noise records
                   ↓
          TCP / WS / WSS
```

## Connection and exchange

The client first establishes the transport and verifies the server through
the protected handshake. It then sends an encrypted `ClientHello` with a
version range and opaque credential. The server validates the hello and
authenticates the client before returning `ServerReady`. Application traffic
begins only after readiness.

```text
Client                                            Server
   ───── transport and Noise establishment ──────────
   ───── hello { versions, credential } ────────────→
   ←──── ready { connection_id } ───────────────────
   ───── request { id: 1, method, payload } ────────→
   ←──── result  { id: 1, payload or error } ────────
   ←──── notification { id: 0, payload } ────────────
```

Requests, results, and cancellation use connection-scoped identifiers.
Notifications are independent of RPC completion. Cancellation is best-effort;
connection loss does not prove whether an operation took effect. The optional
update-recovery capability provides explicit replay and snapshots without
restoring a connection or replaying its unfinished calls.

## Detailed description

| Description | Contents |
|---|---|
| [Wire format](specifications/wire-format.md) | Message layout, encoding, validation, and versions |
| [Connection](specifications/connection.md) | Establishment, readiness, authentication, and lifetime |
| [RPC](specifications/rpc.md) | Requests, results, identifiers, deadlines, cancellation, and errors |
| [Security](specifications/security.md) | Channel construction, trust, and authorization |
| [Transports](specifications/transports.md) | TCP, WS, and WSS mappings |
| [Update recovery](specifications/recovery.md) | Notifications, checkpoints, replay, and snapshots |

All three transports use the same protected message protocol. Encrypted TCP
and verified WSS permit production use; WS is restricted to explicitly enabled
loopback development. WSS adds independent TLS ≥1.3 verification. The transport
description defines exact framing, context bytes, and WebSocket admission.

The [source schemas](proto/syntra/v1/) define fields and types. The wire version
is `Frame.version = 1` and the Protobuf package is `syntra.v1`.

[Reading guide](docs/implementer-guide.md) ·
[Schema tooling](docs/schema-tooling.md) ·
[Conformance tests](conformance/README.md)

[Apache-2.0 license](LICENSE) · [Private security reporting](SECURITY.md)

[Maintenance and contribution process](CONTRIBUTING.md)
