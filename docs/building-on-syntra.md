# Building Applications on Syntra

Syntra carries your application's bytes and enforces the protocol; *meaning*
is yours. This guide explains how to define an application protocol above
Syntra. It is informative — application semantics are out of scope for
conformance — but following it keeps your application interoperable,
securable, and debuggable across independent Syntra implementations.

## Method namespaces

- Use canonical wire paths: `/package.Service/Method` (leading slash,
  exactly two slashes, non-empty segments, printable ASCII, no spaces —
  `SNTR-RPC-001`). Dotted names below are informal shorthand; the wire
  form is always canonical. Validate shape on both ends; malformed paths
  are rejected with `INVALID_ARGUMENT` before dispatch.
- Version your methods explicitly: a new method name or a versioned
  payload schema (the core parses neither). Document which you chose.
- No namespaces are reserved (`/syntra.auth/*` means nothing special);
  never rely on prefix-based dispatch at the core layer.

### Example application: calculator service

A neutral calculator exposing two methods (shorthand `example.math.add`,
`example.math.subtract`):

| Method (wire) | Request payload (yours) | Success result | Error mapping |
|---|---|---|---|
| `/example.Math/Add` | two numbers, e.g. `{"a":2,"b":3}` or your own binary encoding | sum, e.g. `{"sum":5}` | malformed operands → `INVALID_ARGUMENT`; overflow policy → documented `OUT_OF_RANGE` or `INVALID_ARGUMENT` |
| `/example.Math/Subtract` | two numbers | difference | same as above |

Syntra's job: envelope, correlation by `request_id`, `timeout_ms` budget,
cancellation, typed error delivery. Your job: operand encoding, arithmetic,
and the documented error mapping. Any payload encoding is acceptable
(Protobuf, JSON, CBOR, raw bytes) — the core never inspects it.

## Payload schemas

- Define request/response schemas per method in your own documentation or
  IDL; Syntra has no content-type field and negotiates no formats.
- Empty payloads are meaningful (empty input / empty success); unset
  `outcome` is never success — construct your bindings accordingly.
- Keep every serialized `Frame` (payload + envelope overhead) within the
  1 MiB default bound; document any tighter application caps.
- For safe retry of non-idempotent operations, embed an application
  operation key inside the payload and document dedup scope, retention,
  and duplicate behavior. Never reuse `request_id` for this purpose —
  correlation IDs are connection-scoped and die with the connection.

## Error mapping

Document, per method, which application conditions yield which `ErrorCode`
(e.g., unknown operation → `UNIMPLEMENTED` vs missing target → `NOT_FOUND`;
`INVALID_ARGUMENT` vs `FAILED_PRECONDITION`). Keep `message` generic and
public; keep backend detail server-side. Branch client logic on codes, not
text. Remember: only `RpcResult{payload}` proves success; every error —
including `DEADLINE_EXCEEDED`, `CANCELLED`, `INTERNAL`, `UNKNOWN`, and
`UNAVAILABLE` — leaves handler effects unknown unless your application
proves otherwise above Syntra.

## Optional events

If your application pushes state, define a subscription as ordinary RPCs
(e.g., `/example.Events/Subscribe` with an opaque filter; opaque handle in
the result; `/example.Events/Unsubscribe` to stop). Define: stream scope,
ordering metadata in payloads (the core guarantees none across streams),
duplicate tolerance (initiators MUST tolerate), queue/drop policy, replay
and cursor format/lifetime/recovery (only under a negotiated stream spec),
and termination signals. Every subscription is an authorization point for
the bound principal. Checkpoint discipline and the generic recovery
boundary are specified in `specifications/` and owned by your
implementation.

## Authentication policies

Define your credential format, issuance, lifetime, revocation, and
per-method authorization matrix outside Syntra; Syntra carries the opaque
bytes and binds the resulting principal per connection. Anonymous access,
if allowed, gets least privilege. Define expiry and revocation propagation as bounded, testable behavior (accepted RFC 0010: immediate enforcement on new connections; at most a 300-second hard profile maximum; fail-closed when validity cannot be established)
windows — clients treat post-expiry RPCs as `UNAUTHENTICATED` and
reconnect with fresh credentials.

### Accepted SC1 device policy

[RFC 0007](../rfcs/0007-secure-channel-device-authorization.md) is accepted and
adds `SNTR-SC1-WSS-V1` with initial
`Noise_NK_25519_ChaChaPoly_SHA256` enrollment and returning
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` channels. The accepted
[device model](../specifications/security/device-authorization.md) gives
each device a unique random shared 32-byte AK and opaque 8-byte `auth_id`
lookup handle. Hosts own enrollment permission, protected storage,
authorization, and revocation; no human account model or signing keypair
is required. A device's channel authentication does not decide which
methods or subscriptions it may use.

The AK stays off the reconnect wire; `auth_id` is not proof of authority,
and neither value is `connection_id`. Every channel uses fresh ephemeral
material and directional traffic keys. Empty M1/M2 payloads exclude 0-RTT
application data and credentials; the host verifies the first authenticated
client transport record before protected actions. Syntra hello/ready
remains necessary. Returning authentication does not resume a Syntra
session, restore subscriptions, or make an RPC safe to retry.

The accepted [secure channel](../specifications/security/secure-channel.md)
protects the peer-to-host path, not application E2EE. Its
[WSS mapping and restricted TCP/WS carriers](../specifications/transports/noise-bindings.md)
do not change existing TLS requirements or executable baseline profiles.
SC1/WSS requires verified outer TLS 1.3 plus the provisioned Noise pin; TCP/WS
are development-only; UDP is deferred and SC1 HTTP/HTTPS request-response is
excluded. Browser `wss://` retains outer TLS, and Noise-in-WS is distinct from
the baseline WS/WSS frame mappings.

The [implementation record](sc1-implementation.md#authentication-boundary)
defines the trusted channel-policy hook. It receives confirmed channel identity
and an explicit opaque hello credential; it does not independently establish
root identity, compare principals or recheck enrollment before ready on behalf
of the application. Those checks remain host-policy duties, and unset method
authorization denies access. Current delivery uses authenticated out-of-band
preprovisioning, not an enrollment RPC or complete storage/rotation transaction.

## Opaque encrypted payloads

Applications MAY transport encrypted bytes through Syntra. The contract is:

- The Syntra RPC core **does not decrypt application ciphertext** in
  payloads, event bytes, or follow-up auth bytes — it routes and bounds
  opaque bytes bit-preserved. Channel encryption/decryption is a separate
  layer; this remains true for the proposed SC1 record layer.
- Syntra **does not define application E2EE** ratchets, key exchange,
  algorithm identifiers, or handshakes; no E2EE key material may appear in
  envelope fields. Use established libraries above Syntra.
- Syntra **does not know** the encryption format: plaintext, serialized
  structures, and ciphertext behave identically for routing, correlation,
  bounds, and error mapping — and ciphertext gets no larger allowance.
- Current baseline transport security is **still required**: encrypted
  content MUST still traverse secure profiles in public deployments, because TLS protects
  endpoints, metadata, handshake, errors, and availability — none of which
  application encryption covers. Application encryption MUST NOT justify
  plaintext transport, skipped certificate validation, or missing
  authentication.

No private application's E2EE stack is referenced or required here.
