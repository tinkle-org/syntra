# Server (Host) Implementation Guide

The host accepts transport connections, validates versions and credentials
per application policy, dispatches RPCs to application handlers, enforces
authorization before any protected operation, and optionally emits events.
Normative requirements: `SNTR-CORE-020/021/022`, handshake `SNTR-HS-004`
table + §4, `SNTR-RPC-030/031/032`, errors `SNTR-ERR-020/021`, reliability
`SNTR-REL-030/031`, transport server sections, security `SNTR-ASEC-*`.

Current listener and handshake instructions below retain the baseline TLS
requirements and existing executable profiles. [RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
and ADR-011 are accepted; the SC1 section describes the accepted
`SNTR-SC1-WSS-V1` host obligations. Exact bytes and limits are in
[noise-bindings.md](../specifications/transports/noise-bindings.md).

## Listener profiles

Serve each claimed profile on its binding with its documented identifier
(`SNTR-TCP-V1`, `SNTR-TLS-TCP-V1`, `SNTR-HTTP-V1`, `SNTR-HTTPS-H1-V1`,
`SNTR-HTTPS-H2-V1`, `SNTR-WS-V1`, `SNTR-WSS-H1-V1`) per `SYN-ARCH-050`.
Present a valid certificate chain for the claimed endpoint on secure
profiles; enforce the TLS 1.3 minimum; refuse ALPN/SNI mismatches by
closing rather than falling back. Disable plaintext profiles by default in
any production-capable distribution and emit an explicit insecure-mode
warning when enabled. Document every bound and default deadline —
undocumented unbounded behavior is non-conformant (`SNTR-REL-031`).

## Handshake validation

Validate in order before any policy lookup: framing/size/depth bounds,
`hello` shape (`min_version ≤ max_version`, both nonzero, credential
within the documented length bound), then version overlap (highest overlap
wins, else `UNIMPLEMENTED`/`FAILED_PRECONDITION` + close), then credential
evaluation. Enforce concurrent-handshake caps and rate limits (excess →
`RESOURCE_EXHAUSTED` + close). Emit exactly one terminal outcome per
connection — `ServerReady` (→`ACTIVE`) or a handshake error (→`CLOSING`) —
never both, never a re-handshake on the same transport.

The pre-`ACTIVE` typed-error carrier remains unresolved (B1 in
`SESSION-OPEN-QUESTIONS.md`). In delivered SC1, policy rejection reports a
local error and closes the transport; the client can observe `UNAVAILABLE`
rather than a remotely delivered authentication code. Do not invent a
zero-ID result or claim the denial was delivered as a typed wire error.

## Authentication integration

The ordinary credential hook receives opaque credential bytes; the delivered
SC1 hook also receives trusted channel evidence, as described below. Issuance,
storage formats, and policy are the application's. Evaluate credentials with
constant-time comparison where applicable; treat empty as an anonymous attempt
governed by policy (least privilege); distinguish `UNAUTHENTICATED`
(invalid/expired/revoked) from `PERMISSION_DENIED` (valid but insufficient)
without leaking sub-reasons unless the oracle is intentional and
documented. Never log, persist, echo, or metric-label credential material.
Bind exactly one principal at `ServerReady` for the connection lifetime;
principal change requires a new connection.

## SC1 v1: host authorization boundary

SC1/WSS uses bootstrap `Noise_NK_25519_ChaChaPoly_SHA256` and returning
`Noise_NKpsk0_25519_ChaChaPoly_SHA256`. Both handshake payloads are empty.
Bootstrap authenticates the pinned host, not an enrolled client, and grants no
enrollment permission. Returning proves AK possession, but M1 is replayable:
the host requires an authenticated client record under fresh keys before
channel evidence is confirmed. The first authenticated envelope is exactly one
complete framed `ClientHello`, with no trailing envelope; it may span records.
Host policy runs before `ready`.

`HostConfig.ChannelPolicy` replaces ordinary `Policy` and requires confirmed
`ChannelIdentityProvider` evidence. It receives mode, carrier, exact scope,
handle, epoch, channel principal and the explicit hello credential. Before
returning a nonempty principal and allowing ready, host policy must:

1. Verify the root/application credential independently, including an explicit
   decision for an empty credential; it never implicitly means the channel principal.
2. Recheck the current enrollment and admission policy, not merely trust the
   successful Noise exchange or asynchronous lifecycle checker.
3. For returning channels, enforce the intended same-principal binding between
   independently verified root identity and channel identity. **The library
   does not compare these principals automatically; it binds the nonempty
   principal the callback returns.**

`connection.NewServer` requires this explicit channel policy. Nil ordinary
`Policy` denies ordinary admission; nil `Authorize` selects `DenyAllAuthorize`
for every method. An explicit allow-all policy is a deliberate application
choice, not the default. See the [authentication contract](sc1-implementation.md#authentication-boundary).

The host-owned read-only `Lookup` resolves the full provisioned tuple
(server-key ID, carrier, exact scope, handle and epoch). An enrollment needs
a nonzero 32-byte AK, nonempty principal, required future expiry and no
revocation. Keep key/principal immutable under that tuple: `ServerConfig.Check`
rechecks validity/principal but does not compare the current AK with the
handshake AK. A replacement key requires a new enrollment tuple. Unknown and
invalid records fail generically, without a constant-time lookup guarantee.

After confirmation the adapter triggers an asynchronous check and repeats on
a 1s ticker, each lookup bounded by a 1s context. Scheduling and store latency
affect revocation propagation; this is not an exact 1s promise or a substitute for pre-ready
policy. `DisconnectPrincipal` closes current matching active/idle connections;
admission must also reject future attempts. Only authenticated out-of-band
provisioning is supported. Generate the handle independently with collision
checks; secure storage, transactional issuance/delivery/ack recovery and a
complete rotation workflow are not implemented.

### Connection admission and carrier ownership

One `connection.Server` has one fixed carrier. Defaults are 128 concurrent
connections and 16 handshakes; maxima are 4,096 and 256. Handshake slots remain
held through SC1, core hello/policy and successful ready write. Excess TCP
sockets close before a connection goroutine starts; excess WS/WSS upgrades
receive HTTP 503. These are admission counts, not rate limits.

`ServeTCP` owns its listener and admitted raw/active sockets. After upgrade,
`WebSocketHandler` uses the server lifecycle, not `r.Context()`. The application
owns HTTP header limits/timeouts, origin policy and TLS, and must close the
connection server as well as the HTTP server because HTTP shutdown does not
close hijacked sockets. WSS requires verified outer TLS ≥1.3; forwarded headers
do not change the `r.TLS` carrier binding. No automatic downgrade is supplied.
UDP is deferred; HTTP/HTTPS request-response is excluded from this implementation.

Adapter handshake/write/frame/record timeouts default/max at 5s; lifetime is
at most 24h including handshake, with a 2^32-record ceiling per direction.
Pending operations default to 32 per direction, maximum 1,024. See
[operational limits](sc1-implementation.md#operational-limits) for absolute
assembly clocks, errors and exact framing. These experimental identifiers do
not redefine baseline transport profiles or relax production TLS policy.

### Post-ready output writer

Each connection has one asynchronous FIFO writer owning byte snapshots.
Queued plus active output is capped at **256 frames and 8 MiB**, including
terminal results and notifications. Admission never waits for socket I/O;
saturation terminates serving with `RESOURCE_EXHAUSTED`. The session loop
continues dispatch, cancellation and deadline work during a blocked write.
`HostConfig.WriteTimeout` defaults to 5s per send and accepts positive values;
the adapter's separate write timeout cannot exceed 5s. Failed/timed-out sends
terminate the connection.

The pure-Go core separately bounds notification admission by its shared
256-frame/8 MiB backlog. A successful notification enqueue is admission, not
delivery or acknowledgement. `NotifyDirected` selects all connections of a
principal, not a subscription. Method authorization returning `UNAUTHENTICATED`
revokes the binding, cancels other callbacks, queues the denial and attempts
actual-send drain for up to **200ms** before closing; delivery may fail.
Enrollment-watchdog failure and `DisconnectPrincipal` instead close directly.
Writer shutdown cancels I/O, closes the transport,
then joins for up to **1s after Close returns**.

Local regressions cover orchestration, stalled-writer progress and lifecycle
rechecks. Docker covers adapters with core sessions in six carrier/mode groups,
not high-level connection helpers or independent wire interoperability. See
[verification evidence](sc1-implementation.md#verification-evidence) and
[remaining work](sc1-implementation.md#remaining-work), including native ABI
completion-timestamp and post-hello credential-release gaps.

## Session tracking

Default: session lifetime equals connection lifetime. Generate a fresh,
unguessable `connection_id` (≥128-bit entropy) per connection for
diagnostics only — never accept it as auth, never let peers select it.
Track principal binding, expiry, and revocation per connection; on
revocation fail in-flight RPCs with `UNAUTHENTICATED` and close by default
within the documented propagation window. Reject any resumption attempt
without a negotiated capability (`FAILED_PRECONDITION`/`UNAUTHENTICATED` +
close). After close/loss, discard all per-connection state except
diagnostics.

## RPC method registry

Maintain the application's method table (canonical `/package.Service/Method`
paths, case-sensitive, no normalization). Validate method shape, size
bounds, and `ACTIVE` state **before** dispatch; reject malformed paths with
`INVALID_ARGUMENT` without invoking handlers; return `UNIMPLEMENTED` for
unknown methods with the connection left usable. Dispatch only to the bound
principal's authorized handler; return exactly one terminal `result` per
request; never send a second `result` for one ID. Map application failures
to the most specific `ErrorCode` with generic, non-leaking text.

## Authorization

Authorize **after** authentication and **before** handler effects on every
call: per-method and per-subscription checks against the bound principal
(`SNTR-RPC-032`, `SNTR-ASEC-022`). Post-ACTIVE single-call denials use
`RpcResult{error}` without tearing down the connection (unless policy
requires it); binding withdrawal closes by default. Never let one
connection's credential authorize another connection's work; never merge
namespaces across connections, streams, or profiles.

Authorization is fail-closed in a conforming server: deny every RPC with
generic `PERMISSION_DENIED` unless an explicit allow decision exists for
the bound principal and method. Implement a principal-aware authorization
hook invoked before handler effects; treat a missing or unset hook as deny
(no implicit allow-everything default). The delivered Go host follows this
deny-by-default rule; allow-all requires explicit opt-in. Denials expose
only generic `UNAUTHENTICATED`/`PERMISSION_DENIED` codes/messages.

## Backpressure

Bound everything: envelope size, concurrent RPCs (minimum supported 16,
documented max), handshake attempts, queues, event buffers, per-principal
rates. On saturation apply the documented policy — `RESOURCE_EXHAUSTED`
for excess RPCs (connection stays usable), connection-level close for
framing/exhaustion, documented drop-or-error for event streams — never
unbounded queueing, never silent deadlock, and isolate offenders before
conforming traffic degrades. Slow senders and stalled handshakes are closed
(`DEADLINE_EXCEEDED`/`UNAVAILABLE`), not retained. Recover without restart
where possible.

Delivered Go core limits include 8 KiB hello credentials, 512-byte methods,
1 MiB serialized envelopes and depth 32. RPC timeout defaults to 3s, maximum
30s. Host concurrency defaults to 16 and accepts 1–256; client concurrency
defaults to 16 and accepts 1–16. Configurations below 16 are not evidence of
meeting the baseline floor without a negotiated lower-limit binding. The
1 MiB payload ceiling does not waive envelope overhead. These are current
implementation choices, not resolution of pending RFC bounds decisions.

## Transport close

Graceful close: stop new RPCs, observe the profile's close grace period,
then teardown (`CLOSING → CLOSED`; TLS `close_notify`, WS Close handshake,
or TCP FIN per profile). In-flight RPCs receive `UNAVAILABLE` or
`CANCELLED`. Abrupt loss maps to `UNAVAILABLE` with unknown outcome for all
in-flight RPCs; never synthesize a `result` the host did not send; never
report loss as success. There is no `CloseSession` message in v1.

For the experimental implementation, running `Client.Run` and `Host.Serve`
own their transport and close it on terminal paths, including handshake
failure. SC1 adapter close is abortive and does not wait for a WebSocket
close handshake. Distinguish these shutdown budgets:

- The core callback drain has one shared **1s grace** across in-flight workers;
  a separate bounded receive join does not forcibly stop a violating reader.
- The post-ready writer has its own **1s join after transport Close returns**;
  the 200ms best-effort terminal drain is a separate phase.
- The high-level connection server joins listeners, raw handshakes and sessions
  within a **default/max 5s connection shutdown budget**; the client join is 5s.

These are not a universal bound on uncooperative operations. Synchronous
handshake policy, `Lookup`, custom transport I/O and `Close` must honor
cancellation/close contracts. Adapter close can wait indefinitely on a
violating operation; callback grace cannot kill application code. A high-level
shutdown timeout reports incomplete joining, not forced termination. Worker
capacity stays occupied until a callback actually returns, and late results
cannot answer a newer callback that reused its ID.

The pure-Go core preserves a callback completion published before its deadline
even if the loop processes it later. Native ABI v1 lacks that timestamp input
and still arbitrates at answer-processing time, so a delayed loop can lose an
on-time completion. Pure-Go regressions do not establish native parity or
settle the protocol's outstanding outcome-race questions.

## Error sanitization

Sanitize every `RpcError.message`: human-readable public UTF-8, no
credentials, tokens, principal enumerations, stack traces, paths, SQL text,
private diagnostics, or raw untrusted bytes. Keep operational detail in
privileged server-side diagnostics only. Never use errors as a data channel
(no paging or payload smuggling in `message`). Select the most specific
applicable code and document your application-to-code mapping.
