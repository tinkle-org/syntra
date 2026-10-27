# Client (Initiator) Implementation Guide

The initiator opens transport connections, proposes versions, presents
credentials, invokes RPCs, and handles results, errors, and optional
events. Normative requirements: `SNTR-CORE-010/011/012`, handshake
`SNTR-HS-001` table + §3, `SNTR-RPC-020/021`, errors `SNTR-ERR-010/011`,
reliability `SNTR-REL-020/021`, transport client sections.

The steps below describe the current TLS/profile baseline. The selected
SC1 path in [Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
is not Accepted or implemented by these instructions; its client-side
implications are recorded separately below.

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
negotiation bytes may pipeline only where the profile allows). On
handshake error: surface the typed code, close the transport, and do not
retry with downgraded versions unless the application explicitly
re-negotiates.

## Authentication

Obtain credentials out of band. Send them only over permitted transports
(secure profiles in production; loopback-restricted plaintext for
development with throwaway fixtures). Never place them in URLs, logs,
error reports, or diagnostics; discard handshake state on rejection; retry
identical bytes only with bounded backoff, never in a tight loop. Treat
`UNAUTHENTICATED` as "present a different/fresh credential" and
`PERMISSION_DENIED` as "valid credential, access refused — do not retry
identically" (`SNTR-AUTH-021`).

## Selected SC1 proposal: client enrollment and returning channels

For the proposed [SC1 state machine](../specifications/security/secure-channel.md),
the initiator trusts the host static key before initial
`Noise_NK_25519_ChaChaPoly_SHA256` enrollment. Enrollment permission and
issuance/storage of a unique random shared 32-byte AK plus opaque 8-byte
`auth_id` are defined by [host device policy](../specifications/security/device-authorization.md).
The client protects its stored AK; no signing keypair or human account is
required by this model.

A returning initiator supplies the lookup handle and uses
`Noise_NKpsk0_25519_ChaChaPoly_SHA256`, without transmitting the AK.
Use fresh ephemeral material and derive fresh directional traffic keys on
every channel. M1/M2 payloads stay empty: no 0-RTT credentials or
application data. The host verifies the first authenticated client
transport record before protected actions. Syntra `ClientHello` and
`ServerReady` still gate RPCs; Noise completion alone is not readiness.
Neither AK nor `auth_id` is `connection_id`.

The proposed [TCP/UDP/WS bindings](../specifications/transports/noise-bindings.md)
do not change baseline TLS validation or existing HTTPS/WSS compatibility.
Browser `wss://` retains outer TLS; Noise-in-WS uses a distinct wire from
current WS/WSS profiles. Reconnect still needs explicit application
recovery and retry decisions; returning-device authentication supplies no
session resumption, subscription restoration, or proof that a lost RPC did
not execute.

## Request IDs

Generate nonzero `uint64` IDs, unique among *outstanding* RPCs on the
connection. IDs may be reused only after the terminal `result` for that
ID (note the replay-security interaction in `SESSION-OPEN-QUESTIONS.md`
B3: when in doubt, use fresh IDs). Correlate every `result` by ID; accept
out-of-order completion; never assume FIFO. Handle interleaved
`notification`s without completing any RPC. Every new connection (and
every HTTP exchange) starts a fresh ID space; logical continuity across
connections uses application operation keys inside payloads, never the old
`request_id`.

## RPC concurrency

Multiple RPCs may be outstanding (peers support at least 16; discover the
documented max and respect `RESOURCE_EXHAUSTED` with jittered backoff).
Drive each RPC with its own timer (≤ requested budget); on expiry surface
`DEADLINE_EXCEEDED` distinctly from application errors. Send `cancel` when
abandoning an RPC you no longer need, but still await (or explicitly
discard with a local timeout) the terminal `result` to avoid ID-reuse
races. Never treat transport/framing/TLS success as application success —
only `RpcResult{payload}` proves success.

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
