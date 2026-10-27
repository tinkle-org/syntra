# Frequently Asked Questions

**Is Syntra a transport?**
No. Syntra runs *over* transports via adapter profiles (TCP, TLS,
HTTP/HTTPS, WebSocket). The core never touches sockets; the adapter never
interprets RPC semantics (`SYN-ARCH-010/011`).

**Is Syntra RPC?**
Partly: Syntra defines generic RPC mechanics — correlation by
`request_id`, deadlines, cancellation, typed errors, concurrency — but
method semantics, payload schemas, and handler behavior are the
application's. There is no service registry or stub compiler in Syntra.

**Is Protobuf Syntra?**
No. Protobuf (proto3) is the serialization IDL for Syntra envelopes;
Syntra is the protocol around it: handshake, sessions, errors, versions,
profiles, and conformance. Changing framing never changes the Protobuf
definition and vice versa (`SYN-ARCH-012`).

**Do generated packages implement Syntra?**
No. Generated packages contain message data structures only. They do
not implement the handshake, sessions, RPC runtime, transport, or
authentication — that is your implementation (see
`docs/implementer-guide.md` and `docs/schema-registry.md` §6).

**Can I use JSON payloads?**
Yes — inside opaque `payload` bytes. Syntra never inspects payload format;
JSON, CBOR, raw bytes, and ciphertext are equally acceptable. Only the
envelope itself is always Protobuf.

**Can I implement Syntra in Java (or any language)?**
Yes. The suite is language-independent: specs plus `.proto` files plus
YAML test manifests are sufficient; no Rust, Go, or any framework is
required. At least two independent implementations are the stability bar
(`GOVERNANCE.md` Sec. 5).

**Must I support every transport?**
No. Claim Core over at least one transport profile; add profiles
independently. Production claims MUST name only secure profiles; insecure
profiles are development-only and must be labeled as such.

**Does Syntra provide E2EE?**
No, and it MUST NOT. Applications needing end-to-end encryption implement
it above Syntra with established libraries; Syntra carries ciphertext
opaquely and still requires transport security (see
`docs/building-on-syntra.md`).

**What is SC1, and can I use it now?**
Syntra Secure Channel v1 is the selected transport-independent channel
proposal in new [Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md).
It is not Accepted or shipped crypto. The current TLS requirements and
all existing executable conformance profiles remain unchanged. Proposed
[TCP/UDP/WS bindings](../specifications/transports/noise-bindings.md)
share a [channel state machine](../specifications/security/secure-channel.md);
the core does not dial sockets or require WebSocket or gRPC.

**Does the selected design need human accounts or device signing keys?**
No. Initial enrollment uses `Noise_NK_25519_ChaChaPoly_SHA256`. Host-owned
[device policy](../specifications/security/device-authorization.md)
controls enrollment, storage, authorization, and revocation. Each device
gets a unique random shared 32-byte AK and opaque 8-byte `auth_id` lookup
handle; returning channels use `Noise_NKpsk0_25519_ChaChaPoly_SHA256`.
The AK is not transmitted on reconnect, and the handle alone proves no
authority. Neither is `connection_id`. There is no device signing-keypair
requirement or mandatory human account model.

**Does SC1 permit early requests or replace hello/ready?**
No. M1/M2 payloads are empty, with no 0-RTT application data or
credentials. Every channel uses fresh ephemeral material and directional
traffic keys. The host verifies the first authenticated client transport
record before protected actions; Syntra hello/ready still gates RPCs.
Returning-device authentication does not resume a session, restore
subscriptions, or authorize automatic retries of lost RPCs.

**Does Noise-in-WebSocket remove TLS in browsers?**
No. Browser `wss://` still requires outer TLS, and existing HTTPS/WSS TLS
compatibility stays. Proposed Noise-in-WS is a distinct wire binding;
existing WS/WSS profile IDs and the `syntra.v1` mapping keep their meaning.

**Do 96 or 104 bytes describe complete connection establishment?**
No. With empty M1/M2 payloads, NK handshake bodies total 96 bytes; the
returning total is 104 = 96 + 8 bytes including `auth_id`. These counts
exclude framing and additional epoch/version fields, client
transport-record confirmation, carrier establishment, and Syntra
hello/ready. They are not complete establishment RTTs or measured
benchmarks; see [size accounting](perf-tradeoffs.md#5-sc1-handshake-size-accounting-proposal-only).

**Does Syntra provide exactly-once RPC?**
No. The default is at-most-once per connection; the core never retries
automatically. Effectively-once behavior is achievable only through
documented application idempotency (operation keys, dedup windows) above
Syntra. Only `RpcResult{payload}` proves success; every other outcome
leaves handler effects unknown.

**Can sessions survive reconnect?**
By default, no: session lifetime equals connection lifetime, and
reconnect starts a new session (fresh handshake, fresh IDs, explicit
re-subscription). Resumption exists only under a future negotiated
capability RFC; without one, any resumption attempt MUST be rejected.

**Can I add custom RPC methods?**
Yes — methods are entirely yours (`/package.Service/Method` shape,
your payload schemas, your error mapping). No registry approval is
needed. New *protocol* behavior (envelope variants, core fields,
transports, capabilities), by contrast, REQUIRES an RFC and, if breaking,
a major version.
