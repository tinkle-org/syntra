# Glossary

Precise definitions for protocol terms. Normative semantics live in
`specifications/`; this page fixes vocabulary only.

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
  single Syntra unit on every transport.
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
