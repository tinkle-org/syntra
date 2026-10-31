# Client (Initiator) Implementation Guide

The initiator opens transport connections, proposes versions, presents
credentials, invokes RPCs, and handles results, errors, and optional
events. Normative requirements: `SNTR-CORE-010/011/012`, handshake
`SNTR-HS-001` table + §3, `SNTR-RPC-020/021`, errors `SNTR-ERR-010/011`,
reliability `SNTR-REL-020/021`, transport client sections.

The steps below describe the baseline TLS/profile behavior. SC1/WSS is an
accepted additional secure profile in
[RFC 0007](../rfcs/0007-secure-channel-device-authorization.md). Its exact
bytes are in [noise-bindings.md](../specifications/transports/noise-bindings.md).
The earlier Go draft-1 implementation is historical and is not the v1 format.

## Transport establishment

Open the transport per the chosen profile *before* any Syntra bytes:
TCP connect; TLS 1.3 handshake with full chain + hostname + expiry
validation (never send credentials to an unverified endpoint, never fall
back to plaintext); HTTP target `POST /syntra/v1/rpc`; WS Upgrade to
`/syntra/v1/ws` offering `syntra.v1` first and validating the `101`
selects exactly it (abort without Syntra bytes on any mismatch). Start the
handshake timer at connection establishment (default 5 s); expiry aborts
with `DEADLINE_EXCEEDED`, never implicit success.

## Syntra handshake

Send exactly one `ClientHello` as the first envelope
(`min_version ≤ max_version`, both nonzero, opaque credential bytes —
empty means anonymous attempt), then await `ServerReady` or a terminal
error before any `request`, `cancel`, or application payload. Never send a
second `hello`; never pipeline Syntra RPCs before `ACTIVE` (transport
negotiation bytes may pipeline only where the profile allows). Syntra timing
rule (accepted RFC 0003 D4, SNTR-HS-002): start the core handshake timer only
at the local `CONNECTED` boundary for frame-carrying profiles — established
TCP for TCP; successfully completed and verified TLS for TLS/TCP; a validated
Upgrade for WS; verified TLS plus a validated Upgrade for WSS — never during
socket/Upgrade establishment, which has its own separate bounded setup budget.
HTTP/HTTPS carries no frame carriage: every exchange synthesizes the sequence
under its own request deadline, and there is no connection-level Syntra
handshake timer at all. On
handshake error (accepted RFC 0003): the detecting side records a locally
typed cause; the peer observes only the transport-native close signal;
there is no typed wire error to surface. Close the transport and do not
retry with downgraded versions unless the application explicitly
re-negotiates.

In delivered SC1, host policy rejection closes the connection and the
client observes `UNAVAILABLE`; that does not establish receipt of a typed
authentication denial. Do not retry automatically with bootstrap or
another carrier.

## Authentication

Obtain credentials out of band. Send them only over permitted transports
(secure profiles in production; loopback-restricted plaintext for
development with throwaway fixtures). Never place them in URLs, logs,
error reports, or diagnostics; discard handshake state on rejection; retry
identical bytes only with bounded backoff, never in a tight loop. Treat
`UNAUTHENTICATED` as "present a different/fresh credential" and
`PERMISSION_DENIED` as "valid credential, access refused — do not retry
identically" (`SNTR-AUTH-021`).

## SC1 v1 clients

The accepted [carrier contract](../specifications/transports/noise-bindings.md)
selects WSS explicitly in bootstrap NK or returning NKpsk0 mode. Bootstrap
requires a trusted, provisioned server static-key pin; returning mode also
requires a nonzero 32-byte AK, an independently generated eight-byte handle and
nonzero epoch. The exact UTF-8 scope, carrier and server-key ID are
authenticated context. Neither AK nor handle is `connection_id`. M1/M2 payloads
are empty; no credentials or RPCs are early data. Every reconnect uses fresh
ephemeral material and directional traffic keys.

The Upgrade MUST use `/syntra/v1/sc1/ws` and the exact subprotocol
`syntra.sc1.v1`. The historical `syntra.sc1.draft1` identifier is not a v1
alias and MUST be rejected.

A conforming client completes TLS, Upgrade, SC1, hello and validated
`ServerReady` within one bounded attempt (default 15 seconds, shortened by the
caller). Channel establishment and first-record confirmation default to 5
seconds. Readiness is a snapshot, not a guarantee that
the next call cannot encounter disconnection.

A successfully connected client's lifetime is independent of its dial context.
Close it explicitly: high-level `Client.Close` cancels and joins for at most
5s; `Done` and `Wait(ctx)` observe termination, and canceling a wait does not
close the connection. Running core sessions own transport closure. Receive
cancellation after I/O begins can terminate an adapter; do not cancel its
shared receive pump merely to abandon one RPC. See
[ownership and limits](sc1-implementation.md#operational-limits).

WS and WSS use the exact `syntra.sc1.v1` subprotocol, one binary message per
M1/M2/record and disabled compression; they do not use the baseline
one-message/one-`Frame` mapping.
WSS retains verified outer TLS ≥1.3 as well as the Noise server pin. Standard
inspectable HTTP transports enforce verification; custom RoundTrippers own
their TLS policy. Redirects and automatic downgrade/fallback are refused.
UDP is deferred and HTTP/HTTPS request-response is excluded from this stack.

The host's [channel-aware policy](sc1-implementation.md#authentication-boundary)
must independently verify root credentials, current enrollment and admission
before ready, enforcing the intended returning-mode same-principal binding
itself. The library does not compare principals or implicitly authorize empty hello
credentials. Bootstrap authenticates the host, not an enrolled client;
only explicit authenticated out-of-band provisioning is supported. Secure
client storage, enrollment RPCs and complete issuance/rotation recovery are
not supplied. Reconnect/resubscribe and retry decisions remain explicit;
AK possession proves neither a lost RPC's outcome nor replay safety.

Local connection tests and same-implementation container carrier tests are
recorded in [verification evidence](sc1-implementation.md#verification-evidence).
They are not independent wire interoperability or formal conformance.
Independent review/vectors/interoperability and native-core ABI credential
release/completion-time gaps remain [open](sc1-implementation.md#remaining-work).

## Request IDs

IDs are nonzero `uint64`, strictly increasing within one connection, and
never reused — not even after the terminal `result` for that ID
([RFC 0004](../rfcs/0004-correlation-identity-carriage.md)). Reusing,
replaying or reissuing an already-seen ID is an ordered-admission violation:
the violating side records local `FAILED_PRECONDITION` and the connection
terminates; in-flight calls fail `UNAVAILABLE` per the connection rule.
Correlate every `result` by ID; accept out-of-order completion; never assume
FIFO. Handle interleaved `notification`s without completing any RPC. Every
new connection (and every HTTP exchange) starts a fresh ID space; logical
continuity across connections uses application operation keys inside
payloads, never the old `request_id`.

## RPC concurrency

Multiple RPCs may be outstanding (peers support at least 16; discover the
documented max and respect `RESOURCE_EXHAUSTED` with jittered backoff).
Drive each RPC with its own timer (≤ requested budget); on expiry surface
`DEADLINE_EXCEEDED` distinctly from application errors. Send `cancel` when
abandoning an RPC you no longer need, but still await (or explicitly
discard with a local timeout) the terminal `result` to avoid ID-reuse
races. Never treat transport/framing/TLS success as application success —
only `RpcResult{payload}` proves success.

The delivered Go client defaults to 16 outstanding calls and permits configured
limits of 1–16; the host defaults to 16 and permits 1–256. A configuration below
16 does not establish the baseline concurrency-floor claim without a negotiated
lower-limit binding. Default RPC timeout is 3s, maximum 30s. Hello credentials
are capped at 8 KiB and methods at 512 bytes; the 1 MiB serialized-envelope
ceiling includes overhead. These are implementation limits, not new RFC decisions.

## Error handling

Branch on `code`, never on `message` text. Map unknown future codes to
`UNKNOWN` for reporting (preserve the number diagnostically). Surface
`UNAVAILABLE` distinctly: it means *outcome unknown* (the handler may have
executed), unlike terminal application outcomes. Do not display or log
`message` verbatim where it could carry sensitive context.

## Reconnect

After any close or loss: assume no continuity (no in-flight RPC survives,
no subscription survives, no cursor is valid). Re-authenticate on a new
connection with a fresh handshake and fresh IDs; re-issue unacknowledged
RPCs only per the retry rules (idempotent or operation-keyed); re-subscribe
explicitly.

## Optional resumption

No resumption exists in default v1: any resumption attempt without a
negotiated RFC capability MUST fail, and clients MUST NOT send
`connection_id` as a credential or resumption token (nor cache it beyond
connection-lifetime diagnostics). Resumption is claimable only under a
future capability RFC defining token, lifetime, replay, and binding rules.

## Event handling

Only where negotiated: subscribe via the application-defined RPC after
`ACTIVE`; never correlate a `notification` to a `request_id`; tolerate
duplicate events and post-cancel arrivals; never expect events over plain
HTTP request/response (re-read application state via ordinary RPCs
instead). A mandatory-only host's `UNIMPLEMENTED` on subscribe is correct
behavior — record `UNSUPPORTED`, not failure.
