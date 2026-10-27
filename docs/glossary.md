# Glossary

Precise definitions for protocol terms. Normative semantics live in
`specifications/`; this page fixes vocabulary only.

The terms below describe the current baseline. Proposed SC1 terms are
listed separately at the end; they do not replace baseline TLS
requirements or existing executable conformance profiles.

- **Endpoint** — Either peer of a Syntra connection: a client (initiator)
  or a server (host).
- **Client** — The initiator: opens the transport connection, proposes
  versions, presents credentials, invokes RPCs, correlates results,
  receives events.
- **Server** — The host: accepts transport connections, validates versions
  and credentials per application policy, dispatches RPCs to application
  handlers, enforces authorization, optionally emits events.
- **Transport** — The underlying network channel (TCP, TLS 1.3, HTTP/1.1,
  HTTP/2, WebSocket) managed by established implementations, never by
  Syntra itself.
- **Connection** — One disposable transport instance carrying a single
  Syntra handshake-to-teardown sequence and exactly one state-machine run.
- **Session** — The logical protocol context binding an authenticated
  principal to connection(s). By default its lifetime equals one
  connection; spanning connections requires a negotiated resumption
  capability (none exists in v1).
- **Principal** — The opaque authenticated identity bound at `ServerReady`
  for one connection. May be a human, device, service, key, or anonymous
  context; the wire never assumes which.
- **Credential** — Opaque sensitive bytes presented in
  `ClientHello.credential` (or the profile-defined binding, e.g. the HTTP
  `Authorization` header) and evaluated per application policy. Never
  logged, persisted, or placed in URLs.
- **Envelope** — One serialized `Frame{version, request_id, body}`: the
  Syntra message unit on every transport. Distinct from carrier framing
  or the proposed SC1 handshake and encrypted records.
- **Request** — An initiator-to-host invocation
  `RpcRequest{method, payload, timeout_ms}`, correlated by a nonzero
  `request_id`.
- **Response** — Exactly one terminal `RpcResult{payload | error}` per
  request, correlated by the same `request_id`. Only a success payload
  proves application success.
- **Operation** — The application-level unit of work, optionally carrying
  an idempotency key inside the opaque payload. Distinct from transport
  correlation: operation keys are durable and application-scoped;
  `request_id`s are connection-scoped and die with the connection.
- **Capability** — A named optional behavior (event streams, resumption,
  extensions) that MUST be explicitly negotiated. Mandatory interop never
  depends on one.
- **Event** — One host-originated `Notification{payload}`
  (`request_id == 0`) delivered after readiness; uncorrelated, never
  completing an RPC.
- **Stream** — An optional negotiated sequence of events from one
  subscription. No core stream ID exists; handles are opaque application
  bytes.
- **Cursor** — An optional opaque application token marking a stream
  position for replay. Opaque to Syntra; expires per application policy;
  no cross-transport validity is promised by the core.
- **Profile** — A named transport binding and claim boundary
  (`SNTR-TCP-V1`, `SNTR-TLS-TCP-V1`, `SNTR-HTTP-V1`, `SNTR-HTTPS-H1-V1`,
  `SNTR-HTTPS-H2-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`), each with its
  framing, handshake binding, auth carriage, and failure mapping.
- **Extension** — A versioned optional addition (new envelope variant,
  capability, or transport) accepted via RFC. Extensions MUST NOT alter
  mandatory behavior.
- **Conformance** — A per-profile claim proven by the executable suite
  (`conformance/`): passing all mandatory cases for the claimed profiles
  with logs, e.g., "Conforms to Syntra Core v1 and WSS/H1 v1". `PASS` is
  reported only when executed; `SKIP`, `UNSUPPORTED`, and `NOT_EXECUTED`
  are never passes.

## Selected SC1 proposal vocabulary

These definitions follow new [Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md),
which is not Accepted and establishes no implementation or support claim.
See the proposed [secure channel](../specifications/security/secure-channel.md)
and [device authorization](../specifications/security/device-authorization.md).

- **SC1 (Syntra Secure Channel v1)** — Transport-independent secure-channel
  state machine beneath Syntra envelopes, with proposed TCP/UDP/WS
  bindings. The core does not dial sockets or require WS or gRPC.
- **Enrollment** — Host-policy-authorized establishment of per-device
  authority over an initial `Noise_NK_25519_ChaChaPoly_SHA256` channel.
  NK host authentication alone does not authorize enrollment. Storage,
  authorization, and revocation remain host-owned; human accounts are
  optional.
- **AK (authorization key)** — Unique random shared 32-byte secret per
  device, used as the PSK for returning
  `Noise_NKpsk0_25519_ChaChaPoly_SHA256` channels. Not a signing keypair,
  not transmitted on reconnect, and not `connection_id`. It is distinct
  from the fresh ephemeral material and directional traffic keys derived
  for each channel.
- **`auth_id`** — Opaque 8-byte handle used to look up the device's AK at
  the host. Lookup alone is not authentication or authorization; the handle
  is not a Syntra session ID or `connection_id`.
- **M1/M2** — The two Noise handshake messages, whose payloads are empty
  in the selected SC1 design. They carry no 0-RTT application data or
  credentials. Their NK bodies total 96 bytes; returning bodies plus
  `auth_id` total 104 = 96 + 8 bytes, excluding framing and extra
  epoch/version fields, not a full establishment RTT.
- **Client transport-record confirmation** — Host verification of the
  first authenticated client record after the Noise handshake, required
  before protected actions in the proposal. Syntra hello/ready and host
  authorization remain separate gates.
- **Returning channel** — Fresh channel authenticated with an enrolled
  device AK and fresh directional traffic keys; it does not imply Syntra
  session resumption, restored subscriptions, or automatic RPC retries.
- **Noise-in-WS** — Proposed [SC1 WebSocket binding](../specifications/transports/noise-bindings.md),
  distinct from existing WS/WSS profile IDs and the `syntra.v1` mapping.
  Existing HTTPS/WSS TLS compatibility remains; browser `wss://` still
  requires outer TLS.
