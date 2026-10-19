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

**Does BSR implement Syntra?**
No. BSR-generated packages contain message data structures only. They do
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
