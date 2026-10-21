# Server (Host) Implementation Guide

The host accepts transport connections, validates versions and credentials
per application policy, dispatches RPCs to application handlers, enforces
authorization before any protected operation, and optionally emits events.
Normative requirements: `SNTR-CORE-020/021/022`, handshake `SNTR-HS-004`
table + §4, `SNTR-RPC-030/031/032`, errors `SNTR-ERR-020/021`, reliability
`SNTR-REL-030/031`, transport server sections, security `SNTR-ASEC-*`.

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

## Authentication integration

The core gives you opaque credential bytes; issuance, storage formats, and
policy are the application's. Evaluate credentials in constant-time
comparison where applicable; treat empty as an anonymous attempt governed
by policy (least privilege); distinguish `UNAUTHENTICATED`
(invalid/expired/revoked) from `PERMISSION_DENIED` (valid but insufficient)
without leaking sub-reasons unless the oracle is intentional and
documented. Never log, persist, echo, or metric-label credential material.
Bind exactly one principal at `ServerReady` for the connection lifetime;
principal change requires a new connection.

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

Rust `Host` (`crates/syntra-runtime/src/host.rs`) is fail-closed: the
`Handler::authorize` default denies every RPC with generic
`PERMISSION_DENIED`. Implement a principal-aware `authorize`, wrap a
legacy permissive handler in `AllowAll` to opt in explicitly, or use
`FnHandler` for closures (allow-all by construction, unchanged). Go
`Host` (`bindings/go/session.go`) exposes the same check as the optional
`HostConfig.Authorize`; nil preserves the legacy allow-everything
behavior for backward compatibility (divergent from Rust until set
explicitly — use `DenyAllAuthorize` for parity). Denials expose only
generic `UNAUTHENTICATED`/`PERMISSION_DENIED` codes/messages.

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

## Transport close

Graceful close: stop new RPCs, observe the profile's close grace period,
then teardown (`CLOSING → CLOSED`; TLS `close_notify`, WS Close handshake,
or TCP FIN per profile). In-flight RPCs receive `UNAVAILABLE` or
`CANCELLED`. Abrupt loss maps to `UNAVAILABLE` with unknown outcome for all
in-flight RPCs; never synthesize a `result` the host did not send; never
report loss as success. There is no `CloseSession` message in v1. Shutdown
joins are bounded: Rust `Host::close` waits at most `SHUTDOWN_GRACE` (1s)
when `TaskHandle::abort` is cooperative-only (wasm), mirroring Go
`handlerShutdownGrace` (1s) and WS `shutdown_grace`; Go `Serve` likewise
bounds a `Transport.Recv` that violates its context contract to the same
grace instead of hanging teardown.

## Error sanitization

Sanitize every `RpcError.message`: human-readable public UTF-8, no
credentials, tokens, principal enumerations, stack traces, paths, SQL text,
private diagnostics, or raw untrusted bytes. Keep operational detail in
privileged server-side diagnostics only. Never use errors as a data channel
(no paging or payload smuggling in `message`). Select the most specific
applicable code and document your application-to-code mapping.
