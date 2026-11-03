# Implementer reading map

Syntra 1.0 is pre-release. This repository contains the protocol reference,
source IDL, conformance definitions, and validation tooling, with no protocol
implementations. This informative map adds no requirements or approval.

## Protocol reference

| Read | Owns |
|---|---|
| [Connection](../specifications/connection.md) | Establishment, authentication interface, connection/session lifetime, shutdown |
| [Wire format](../specifications/wire-format.md) | Envelope representation, raw validation, bounds, version compatibility |
| [RPC](../specifications/rpc.md) | Requests, correlation, deadlines, cancellation, execution, errors |
| [Security](../specifications/security.md) | Threat model, protected channels, device authorization, credentials, replay boundaries |
| [Transports](../specifications/transports.md) | Carrier selection, establishment, framing, trust, resource and failure mappings |
| [Recovery](../specifications/recovery.md) | Notifications, negotiated update recovery, checkpoints, replay, snapshots, persistence |

The [source IDL](../proto/syntra/v1/) defines representation. For schema checks
and reproducible type generation, use the [schema tooling guide](schema-tooling.md).
For selectors, fixtures, declarations, and executed evidence, use the
[conformance test guide](../conformance/README.md). Neither tooling nor test
definitions override the protocol owners or establish an implementation verdict.

## Application boundary

Applications supply method schemas, payload meaning, business authorization,
credential storage, deployment configuration, and storage transactions within
the protocol's defined obligations. Protocol authentication and recovery
contracts do not define application business behavior.

Language APIs, native bindings, builds, operational measurements, and runtime
support belong with the implementation that provides them. Consumers pin the
exact specification and schema revision and declare the scope of their evidence.

Changes and questions follow [CONTRIBUTING.md](../CONTRIBUTING.md),
[SUPPORT.md](../SUPPORT.md), and [SECURITY.md](../SECURITY.md).
