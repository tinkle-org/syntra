# SC1 draft-1 implementation and verification record (historical)

Date: 2026-10-28. **Historical record.** It describes the earlier experimental
Go draft-1 channel and its executed verification. RFC 0007 and ADR-011 are now
accepted, and the normative v1 bytes are
[noise-bindings.md](../specifications/transports/noise-bindings.md). The current
Rust implementation evidence is recorded in `tinkle-org/syntra-rs` (`SC1.md`,
`AUDIT.md`, `docs/implementation-status.md`). This ledger is retained for
history; it does not define the accepted v1 contract, execute `CONF-SCW-*`
cases, or establish independent interoperability or security review.

## Implementation status

The Go implementation supplies a socket-independent Noise channel, ordered
TCP and WS/WSS adapters, channel-aware host authentication, and connection
orchestration through validated Syntra readiness. Bootstrap uses
`Noise_NK_25519_ChaChaPoly_SHA256`; returning devices use
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` with a provisioned 32-byte AK. Both modes
require a trusted server public-key pin and fresh ephemerals. Neither mode
supplies automatic reconnect, replay, downgrade, cryptographic-state resumption
or in-place reauthentication.

| Area | Implemented scope | Not established by delivery |
|---|---|---|
| Channel and wire | Exact `syntra.sc1.draft1` context; empty handshake payloads; fresh-record confirmation; bounded ordered records | Accepted profile, independent vectors or independent cryptographic review |
| Carriers | TCP, WS and verified WSS; segmentation/reassembly and absolute assembly clocks | UDP; SC1 over HTTP/HTTPS request-response |
| Credentials | Explicit authenticated out-of-band preprovisioning and host-owned lookup of current enrollment records | Enrollment RPC, transactional issuance/delivery/ack recovery, secure-storage backend or complete rotation workflow |
| Runtime | Confirmed channel evidence, explicit authentication policy, deny-by-default method authorization, bounded asynchronous writer | Automatic root-identity verification or agreement between channel and policy principals |
| Verification | Local unit/race tests, native-core integration, six same-implementation Docker groups, in-memory benchmarks | Full manifest-driven conformance, independent SC1 interoperability or production certification |

HTTP Upgrade is part of WebSocket establishment, not an SC1 HTTP RPC binding.
Existing TCP/TLS/HTTP/HTTPS/WS/WSS profile identifiers and Protobuf schemas retain
their meanings. The experimental WS subprotocol is exactly `syntra.sc1.draft1`,
not `syntra.v1`; WSS retains its outer verified TLS layer.

The implementation reviewed and measured here was a development working-tree
snapshot, not an immutable released artifact. The specification base was
`e27fa275f647ccc925b7cf79eb2dd332f20a3d02`. Results are dated observations of
that implementation, not release attestations or a claim about every SDK.

## Authentication boundary

The responder's completion of M2 does not freshly authenticate the client.
Confirmation requires a successfully decrypted client transport record under
the new keys; the encrypted Syntra hello normally supplies it. Replayed M1
can cause a new M2 but cannot confirm that new channel with an old record.
The client sends no hello credential before verifying M2 and waits for core
ready before protected RPCs.

`ChannelIdentity` contains mode, carrier, exact scope, handle, epoch and the
enrollment principal. The transport's `ChannelIdentity()` operation also returns
a boolean indicating fresh confirmation. `HostConfig.ChannelPolicy` replaces
ordinary `Policy`, requires confirmed transport evidence, and receives both
that identity and the explicit opaque hello credential, including an empty
value. It must return a nonempty principal. Empty credentials do not implicitly
select the channel principal or authorize an anonymous attempt.

Before returning success, the embedding policy must independently establish
the required root/application identity, check current enrollment and admission
policy, and enforce the intended principal agreement for returning channels.
The bridge does not compare the returned principal with the channel principal
or synchronously call `ServerConfig.Check` before ready. Periodic lifecycle
checking is not a substitute for those checks. Bootstrap authenticates the
server, not an enrolled client, and grants no enrollment authority by itself.

`Lookup` receives the complete context, not just a globally meaningful handle.
Returning records require a nonzero AK, nonempty principal, future expiry and
no revocation. Keys/principals must remain immutable under their scoped
handle/epoch tuple. Later `Check` validates current validity and principal,
not equality with the original handshake AK; key substitution in place is
not supported rotation. Unknown or invalid enrollments fail generically,
without a constant-time store-lookup guarantee.

After first confirmation, an asynchronous lifecycle check starts and repeats
on a one-second ticker with one-second lookup contexts, including idle
channels. Scheduling and store latency affect propagation; this is not an
exact one-second revocation SLA. `DisconnectPrincipal` cancels and closes
current matching connections, including idle ones, but authentication policy
must also reject future attempts. Nil method `Authorize` selects
`DenyAllAuthorize`. `PERMISSION_DENIED` keeps the connection usable;
authorization `UNAUTHENTICATED` cancels callbacks, attempts a bounded denial
drain, then closes.

## Operational limits

These are implemented experimental defaults, not newly accepted baseline
requirements. The complete byte grammar and byte-count definitions are owned
by the [carrier contract](../specifications/transports/noise-bindings.md).

| Resource or phase | Implemented limit/default |
|---|---|
| Context | Exact UTF-8 scope of 1–255 bytes; total canonical context 42–296 bytes |
| Handshake | M1 context plus 48 bytes; M2 exactly 48 bytes |
| Transport record | Plaintext 1–65,519 bytes; ciphertext 17–65,535 bytes including tag |
| Reconstructed frame | 1–1,048,576 serialized bytes; encrypted four-byte length is additional |
| Ordered adapter handshake, record assembly, frame assembly, write | 5s each; configuration may shorten, not extend, each limit |
| Channel lifetime | 24h by default, shorter allowed; adapter entry clock includes establishment and closes idle channels |
| Key use | At most `2^32` records per direction; original enrollment expiry also bounds use |
| Pending adapter operations | 32 per direction by default, maximum 1,024, including active work; excess rejected immediately |
| Total client establishment | 10s across socket/Upgrade, Noise and validated hello/ready; caller may shorten |
| Core hello/policy/ready | Separate 5s deadline, shortened by parent budget |
| Server admission | 128 connections / 16 concurrent handshakes by default; maxima 4,096 / 256 |
| Post-ready host writer | Queued plus active 256 frames / 8 MiB, including results and notifications |
| Host writer send deadline | 5s by default; host setting accepts any positive duration, unlike the adapter's at-most-5s setting |
| Terminal drain | Best effort, at most 200ms, waiting for actual send completion |
| Writer join | At most 1s after transport close returns |
| Core callback grace | One shared 1s drain for admitted callbacks; cannot forcibly terminate application code |
| High-level shutdown | Client join 5s; server default/max 5s, configurable shorter |

Idle reads do not start a record-assembly clock until the first carrier byte.
That clock includes partial headers and WebSocket fragments/control input.
Frame assembly starts with the first authenticated prefix byte; subsequent
records do not refresh it. Buffered bytes retain their original arrival time.
Frames and prefixes may span records; records may contain coalesced envelopes.
Lengths are bounded before allocating a frame, and no partial or unauthenticated
frame reaches the core. Malformed input terminates without resynchronization.

One post-ready writer owns FIFO snapshots. Queue admission does not wait on
socket I/O, so the session loop can process dispatch, cancellation and deadlines
during a stalled send. Saturation is terminal `RESOURCE_EXHAUSTED`; write failure
or timeout also terminates the connection. The pure-Go core separately bounds
notification admission by a shared 256-frame/8 MiB backlog. Enqueue success is
not transport completion or peer acknowledgement.

Handshake slots stay occupied through successful ready write. Excess TCP
connections close before spawning a serving goroutine; excess WS/WSS upgrades
receive HTTP 503. Counts are not rate limits. HTTP header limits/timeouts,
server TLS, proxy trust, cross-server budgets and lookup timing/privacy are
host responsibilities. WSS acceptance uses actual TLS state rather than
forwarded headers; the standard dial path verifies certificates and requires
TLS 1.3 or later. Custom RoundTrippers own their TLS policy.

Running clients and hosts own and close their transports on terminal paths.
Adapter close is abortive. Bounded joins depend on cancellation-compliant I/O,
lookup and close operations; no timer can kill a noncooperative callback.
HTTP shutdown does not close upgraded sockets, so the connection server must
also be closed. EOF is not authenticated orderly completion, and loss can
leave RPC effects unknown. No automatic retry is safe merely because a code
is considered retry-eligible.

## Verification evidence

The final verification recorded on 2026-10-28 used Go 1.26.10 on darwin/arm64.
Go 1.23.12 tests established build/API compatibility only; production builds
require a security-patched toolchain. The channel uses flynn/noise v1.1.0 and
the WebSocket adapter uses coder/websocket v1.8.15. Root Protobuf is v1.36.6;
root x/crypto is v0.38.0. The container-test graph selects x/crypto v0.56.0,
so it is not an identical dependency graph.

| Executed check | Result and scope |
|---|---|
| Full tests | Passed default and CGO-disabled pure-Go tests; Go 1.23.12 compatibility tests passed |
| Race and native core | Passed pure-Go and production native ABI v1 race suites; native core linkage is not an independent SC1 carrier |
| Static/tooling checks | Vet, staticcheck for both core builds, actionlint, schema formatting/lint/build, eight generated snapshots and whitespace checks passed |
| Vulnerability checks | Root reachable-code scan and integration test-inclusive scan reported zero reachable vulnerabilities on Go 1.26.10; required but unreachable module advisories remain |
| Fuzz smoke | Four five-second targets passed: `FuzzUnmarshalFrame`, `FuzzDuplicateContent`, `FuzzParseContext`, `FuzzContextRoundTrip`; not sustained or stateful record/carrier fuzz campaigns |
| Benchmarks | All in-memory cases passed, three 100ms samples at CPU settings 1 and 4; measured ranges and accounting in [performance results](perf-tradeoffs.md#6-sc1-draft-1-measured-results) |
| Docker integration | All six TCP/WS/WSS × bootstrap/returning groups passed, no container cases skipped; final whole-suite elapsed time 30.681s |

### Local regression coverage

Channel tests exercise exact context/length/payload constraints, mismatched
keys and bound context, generic enrollment denial, entropy failure in both
roles, replayed-M1 confirmation, invalid records and usage limits. Ordered and
carrier tests exercise split prefixes, coalesced frames, short writes,
serialization of whole envelopes, cancellation, absolute assembly deadlines,
admission, idle expiry/revocation, WS fragmentation/control traffic and verified
WSS. They also check clearing of reusable plaintext scratch. Clearing buffers
does not establish erasure of every compiler, native or dependency copy.

Local connection tests cover readiness and independent connection lifetime,
total dial budget, admission through core hello/ready, silent handshakes,
active/half-handshake shutdown, origin rejection and uncooperative-policy
timeout reporting. Writer/runtime tests cover stalled-send loop progress,
FIFO snapshots, active-inclusive caps, actual-send drain, deny-by-default
authorization, transport closure and callback-identity fencing. Codec tests
cover reserved tags 16/17 on emission and receipt, duplicate bodies/outcomes,
an 8 KiB credential gate before decode allocation, depth 32 and opaque bytes.

### Container integration matrix

Each of TCP, WS and WSS runs bootstrap and returning modes with real fixture
processes. Readiness requires listener readiness followed by successful
channel establishment, hello/ready and RPC, not just an open port. Tests exercise:

- Empty, 64 KiB and 1,048,448-byte echo payloads; 16 concurrent checked echoes.
- Cancellation and deadlines with observed handler entry/exit, then a successful
  RPC on the same connection; generic method denial followed by permitted work.
- Wrong server pin; returning wrong AK; bootstrap empty/wrong credential denial.
- WSS with a private fixture CA, hostname verification and TLS 1.3; wrong-host
  and untrusted-CA rejection without disabling verification.
- Sixteen pending calls during client close; fixture restart and explicit fresh
  sessions with replacement provisioning, rejection of stale material.
- Returning-mode Toxiproxy downstream stall and reset for all three carriers,
  bounded failure, toxic removal and a new explicitly opened successful session.

The stall case uses a 750ms RPC budget and a 3s caller context with a 5s outer
assertion. It proves bounded RPC failure, not autonomous idle-transport closure.
The harness then closes the affected session. Fixture builds use a pinned
Go 1.26.10 container builder and CGO-disabled binaries; Toxiproxy v2.12.0 is
source-built. Its separately built dependency graph is not covered by the
integration module vulnerability scan. Docker unavailability is failure, not
a skipped successful result.

This matrix exercises carrier adapters with core sessions, not the high-level
connection helpers. Returning fixtures deliberately use an explicit
channel-principal policy; they do not independently verify a root credential
or establish the pre-ready same-principal policy obligation. Revocation has
local regression coverage, not a container matrix case. Same-library Noise
checks, same-implementation Docker peers, native-core tests and independent
wire interoperability are different evidence.

No formal SC1 `CONF-*` cases or active profiles are registered. The
[acceptance plan](../conformance/plans/secure-channel.md) maps this executed
implementation evidence separately from portable acceptance cases and their
remaining verification work.

## Remaining work

Concrete context bytes, ordered carrier mappings, host-authentication hooks,
resource defaults, integration tests and microbenchmarks are implemented; they
are no longer unspecified design work. Acceptance of those choices still
requires protocol/security review and the normal RFC process.

Open work includes independent deterministic vectors and both-role independent
SC1 interoperability; full-composition security review; complete enrollment,
secure storage and rotation transactions; deployment revocation guarantees;
rate limits and cross-server resource accounting; and manifest-driven evidence
and release gates. UDP requires its own complete datagram design. HTTP/HTTPS
request-response is excluded, not a promised pending SC1 feature.

Native ABI v1 has no callback completion-timestamp input or post-hello
credential-release operation. Pure-Go completion publication preserves an
on-time callback observed later; native answer/deadline arbitration still
uses processing time. Native test passes do not close either ABI gap.

Malformed-result/bodyless-frame behavior still needs reconciliation with some
mandatory manifest expectations. Configurations permitting fewer than sixteen
concurrent RPCs do not establish the baseline floor without a negotiated lower
limit. Typed pre-ACTIVE errors, request-ID lifetime/reuse, capability/limit
negotiation and outcome races remain in the
[protocol blocker inventory](../SESSION-OPEN-QUESTIONS.md). No new wire field
or behavior is silently allocated to settle them.

Recovery and reliable-session helpers do not implement a complete negotiated
recovery service, per-subscription isolation or atomic durable effects/outcomes.
A timeout or cancellation request is not proof that effects have ceased; local
tombstone and retry helpers do not provide exactly-once execution.
