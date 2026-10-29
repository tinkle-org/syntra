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
Syntra Secure Channel v1 has a delivered bounded experimental Go draft-1
implementation over TCP/WS/WSS, in bootstrap and returning modes. The
[self-contained contract](sc1-implementation.md#implementation-status) records
its bytes, limits and APIs. [RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
remains Draft and ADR-011 Proposed: implementation delivery is not acceptance,
independent audit or a production-default decision. Current TLS requirements
and existing executable profile meanings remain unchanged. UDP is deferred;
HTTP/HTTPS request-response is excluded from this implementation.

**Does the selected design need human accounts or device signing keys?**
No. Bootstrap uses `Noise_NK_25519_ChaChaPoly_SHA256`. Host-owned
[device policy](../specifications/security/device-authorization.md)
controls enrollment, storage, authorization, and revocation. Each device
gets a unique random shared 32-byte AK and opaque 8-byte `auth_id` lookup
handle; returning channels use `Noise_NKpsk0_25519_ChaChaPoly_SHA256`.
The AK is not transmitted on reconnect, and the handle alone proves no
authority. Neither is `connection_id`. There is no device signing-keypair
requirement or mandatory human account model.

Bootstrap itself authenticates only the pinned host. Only explicit
authenticated out-of-band provisioning is supported; there is no enrollment
RPC, complete issuance/delivery/ack recovery, secure-storage implementation
or complete rotation workflow.

**Does SC1 permit early requests or replace hello/ready?**
No. M1/M2 payloads are empty, with no 0-RTT application data or
credentials. Every channel uses fresh ephemeral material and directional
traffic keys. The host verifies the first authenticated client transport
record before protected actions; Syntra hello/ready still gates RPCs.
Returning-device authentication does not resume a session, restore
subscriptions, or authorize automatic retries of lost RPCs.

**Does Noise-in-WebSocket remove TLS in browsers?**
No. WSS retains verified outer TLS ≥1.3 as well as the Noise server pin.
Standard inspectable HTTP transports enforce verification; custom RoundTrippers
own TLS policy. There is no automatic downgrade. Draft-1 uses the exact
`syntra.sc1.draft1` subprotocol and a distinct encrypted-record stream;
existing WS/WSS profile IDs and the `syntra.v1` mapping keep their meaning.

**Do 96 or 104 bytes describe complete connection establishment?**
No. Draft-1's canonical context is 42–296 bytes, M1 adds 48 Noise bytes and
M2 is 48 bytes. Both modes therefore use 138–392 bytes before carrier framing;
TCP adds four bytes for the two message-length prefixes. Confirmation, carrier
establishment and core hello/ready are additional work. These are calculated
byte counts, not latency measurements; see [performance evidence](perf-tradeoffs.md).

**Does the host hook automatically bind the channel principal?**
No. `ChannelPolicy` receives confirmed evidence and explicit hello bytes and
returns the session principal. Host policy must independently verify the
root identity, current enrollment and admission before ready, and enforce
the intended returning-mode same-principal binding. The library does not compare
principals automatically or treat empty credentials as channel authority. Nil method
authorization denies calls. See [authentication boundary](sc1-implementation.md#authentication-boundary).

**Does dialing success mean I can call immediately, and who closes the transport?**
High-level `DialTCP`/`DialWebSocket` return after validated ready within a 10s
total establishment budget. The returned lifetime is independent of the dial
context; close the client explicitly. Running core sessions own terminal
transport closure. Server connection/handshake defaults are 128/16; the
post-ready writer owns FIFO snapshots and caps queued plus active output at
256 frames/8 MiB. A 5s connection shutdown budget is distinct from the core
1s callback grace and writer 1s join after transport close; uncooperative
operations are not forcibly terminated. See [limits](sc1-implementation.md#operational-limits).

**Do the tests and benchmarks prove interoperability or performance superiority?**
No. The recorded Docker suite passed all six TCP/WS/WSS × bootstrap/returning
groups with faults and verified WSS, but uses the same implementation on both
ends. High-level connection helpers have local unit coverage, not container
coverage; native-core tests do not provide independent SC1 carriers. Formal
`CONF-*` verdicts, independent vectors/interoperability and security review
remain open. Three short in-memory benchmark samples at CPU settings 1 and 4
passed without a hard timing gate; full RPCs are not zero-allocation. See
[verification evidence](sc1-implementation.md#verification-evidence),
[performance evidence](perf-tradeoffs.md) and [remaining work](sc1-implementation.md#remaining-work).

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
