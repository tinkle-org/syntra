# Syntra v1 Transport — HTTPS over HTTP/1.1 and HTTP/2

- Identifier: `specifications/transports/https.md`
- Title: Secure Profiles: TLS Policy, HTTPS/H1, HTTPS/H2
- Status: Draft (pending maintainer approval via RFC)
- Version: 1.0.0-draft.1 (2026-10-19)
- Normative references: BCP 14; RFC 8446 (TLS 1.3); RFC 5280 (PKIX); RFC 6125 and RFC 9110 §4.3.3 (hostname verification); RFC 7301 (ALPN); RFC 9113 (HTTP/2); RFC 9114 (QPACK, where applicable); `proto/syntra/v1/envelope.proto`
- Inherits (MUST NOT redefine): `specifications/transports/http.md` — endpoint (§1A), media type (§1B), envelope mapping (§1C), version headers (§1D), status layering (§1E), timeouts/cancel (§1F), auth carriage (§1H), per-request session independence (§1I), retries (§1J), caching (§1K), redirects (§1L), body limits (§1M), compression (§1N), no-push (§1O), CORS (§1P)
- Core/security dependencies: SNTR-TSEC-* (`transport-security.md`), SNTR-ASEC-* (`authentication-security.md`), SNTR-RPL-* (`replay-protection.md`), SNTR-SESS-006/§1E (`sessions.md`), SNTR-REL-* (`reliability.md`), SNTR-VER-007 (`versioning.md`); charter SYN-ARCH-030/031/050/051; ADR-008
- Scope: Everything the secure profiles add over the base HTTP mapping: TLS 1.3 requirements, certificate/hostname validation, ALPN negotiation, the HTTP/2 stream binding (concurrency, independence, failure mapping), proxy/termination rules, and deployment posture (HSTS). HTTP/3, QUIC, WebSocket-over-H2 Extended CONNECT, and server push as event delivery are explicitly excluded (§7). No custom Syntra TLS handshake exists before, during, or after the TLS handshake.

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 0. Design summary (informative)

The two production-capable profiles — HTTPS using HTTP/1.1 and HTTPS
using HTTP/2 — run the identical RPC mapping from `http.md` inside
TLS 1.3. HTTP/1.1 gives strictly sequential exchanges per connection
(pipelining aside); HTTP/2 multiplexes many independent RPC exchanges as
concurrent streams on one connection. In both cases every stream/exchange
is independently authenticated per request, carries its own version
headers, and ends with its own terminal outcome — connection and stream
identity never imply a principal, and keep-alive (including H2 PING)
never implies a session. Ordering, push, and cross-stream state from
HTTP/2 are transport artifacts the adapter hides; Syntra sees only
independent RPCs correlated by echoed `request_id`.

The [shared-channel proposal](../security/secure-channel.md) in
[Draft RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
does not redefine either HTTPS profile. Its [carrier candidates](noise-bindings.md)
are separate TCP/UDP/WebSocket work, not HTTPS/H1 or HTTPS/H2 negotiation
options. No Noise preface, new ALPN token, AK header or ambient device binding
is added here. Certificate/hostname validation, per-exchange credentials,
stream independence, current test IDs and the TLS production policy remain
in force until an accepted change defines otherwise. Proposed persistent
authorization on another permitted carrier would establish fresh channel
keys and principal checks, without resuming an HTTPS session or authorizing
other H2 streams.

## 1. Protocol requirements

### 1A. Profiles and negotiation

**SNTR-HTTPS-001** — The production-capable profiles are exactly:

1. **HTTPS/H1**: HTTP/1.1 semantics (`http.md` in full) over TLS 1.3.
2. **HTTPS/H2**: HTTP/2 (RFC 9113) over TLS 1.3 with ALPN `h2`, carrying
   the identical `http.md` mapping per stream.

Deployments MUST document which profile(s) they serve. Plaintext
HTTP/1.1 stays restricted-development (`http.md` §2); plaintext HTTP/2
with prior knowledge (`h2c`, RFC 9113 §3.4) MUST NOT be served except on
loopback-restricted development interfaces, MUST be disabled by default,
and MUST carry the same insecure-mode warning as plaintext H1.

**SNTR-HTTPS-002** — Stable profile identifiers: `SNTR-HTTPS-H1-V1`
(§1D binding) and `SNTR-HTTPS-H2-V1` (§1E binding). The `-V1` suffix
marks profile identifiers and distinguishes them from requirement IDs
  (`SNTR-HTTPS-###`), consistent with `SNTR-HTTP-V1`, `SNTR-WS-V1`, and
`SNTR-WSS-H1-V1`. Implementations MUST document which identifiers they
support per SYN-ARCH-050.

**SNTR-HTTPS-003** — No custom Syntra handshake exists at the TLS or
HTTP framing layer. The TLS handshake is the stock RFC 8446 handshake;
no Syntra bytes appear inside it, no Syntra credential influences cipher
or certificate selection, and the first post-TLS bytes are the ordinary
HTTP request (`POST /syntra/v1/rpc`). Peers MUST NOT invent
Syntra-specific TLS extensions, ALPN tokens, or preface bytes.

### 1B. TLS requirements (both profiles)

**SNTR-HTTPS-010** — Secure profiles MUST use TLS 1.3 (RFC 8446) via an
established implementation. TLS 1.2 or lower MUST NOT be negotiated for
Syntra traffic; if the peer offers only <1.3, negotiation MUST fail. No
custom TLS, cipher, ratchet, or handshake implementation SHALL be
introduced (SYN-ARCH-031, SNTR-TSEC-002/011). Cipher selection follows
the implementation's secure defaults; deployments MUST NOT enable
deprecated or weak suites.

**SNTR-HTTPS-011** — Initiators MUST validate the full chain to a trusted
root (system or explicitly configured), check expiry and revocation per
deployment policy, and fail closed on invalid/expired/revoked/
untrusted-self-signed certificates — before sending `ClientHello`
equivalents (version headers, credential) or any application payload.
Validation failure is a terminal handshake failure: no Syntra bytes are
sent, waiters get `UNAVAILABLE`, and there is MUST NOT be fallback to
plaintext or a weaker version (SNTR-TSEC-002/003/007).

**SNTR-HTTPS-012** — Hostname verification: initiators MUST verify the
presented identity matches the intended endpoint (SAN dNSName/iPAddress
preferred; CN only per RFC 6125 fallback) before presenting credentials
(SNTR-TSEC-004). Wrong-hostname certificates MUST be rejected even when
chain-valid. Credentials MUST never be sent to an unverified endpoint.

**SNTR-HTTPS-013** — Downgrade refusal: peers MUST NOT negotiate below
TLS 1.3, MUST NOT retry over plaintext after TLS failure (automatic
plaintext retry is FORBIDDEN), and MUST refuse Syntra-layer downgrades
that would weaken transport security (SNTR-TSEC-007, SNTR-VER-007).
Downgrade attempts → handshake failure + close, with no credential
disclosure.

**SNTR-HTTPS-014** — Rotation: hosts MUST support certificate rotation
without a protocol version change; initiators MUST NOT pin leaf
certificates/keys unless the deployment documents pinning with rotation
procedures, and MUST accept any currently valid chain during overlap
windows (SNTR-TSEC-006).

### 1C. ALPN (where the transport uses it)

**SNTR-HTTPS-020** — Initiators on TLS ports serving both profiles MUST
offer ALPN (RFC 7301) with at least `h2` and `http/1.1` (order expresses
preference; deployments MUST document theirs). Hosts select exactly one;
selection mismatch or absence where the endpoint requires ALPN MUST fail
the connection rather than fall back to an unintended protocol
(SNTR-TSEC-010). ALPN MUST NOT be used as an authentication or
authorization signal, and MUST NOT select anything other than the HTTP
version binding.

**SNTR-HTTPS-021** — Servers serving only HTTPS/H1 MAY omit ALPN
handling beyond the TLS stack default, but MUST still refuse to speak
plaintext HTTP on the TLS port (bytes that are not a TLS `ClientHello`
→ close, no HTTP response).

### 1D. HTTPS/H1 binding

**SNTR-HTTPS-030** — HTTPS/H1 is `http.md` in full, transported over the
§1B channel: same endpoint, method, headers, bodies, statuses, limits,
and per-request independence. Keep-alive (persistent connections) and
pipelining change connection efficiency only and MUST NOT merge Syntra
state across exchanges (`http.md` §1I applies verbatim).

**SNTR-HTTPS-031** — Sharing one keep-alive connection across exchanges
with different credentials (or anonymous alongside authenticated) is
safe BY CONSTRUCTION, because binding is per request (§1H/§1I): hosts
MUST re-evaluate every exchange independently and MUST NOT treat
connection reuse as continuity. Conversely, hosts MUST NOT infer a
principal from the fact that the TLS session resumed (session tickets /
PSK resumption authenticate the channel, never the Syntra principal —
SNTR-RPL-002 scope rule).

### 1E. HTTPS/H2 binding (streams are independent RPCs)

**SNTR-HTTPS-040** — Each Syntra RPC maps to exactly one normal HTTP/2
request/response stream: `:method = POST`, `:path = /syntra/v1/rpc`
(exact; `:scheme = https`, `:authority` = deployment host), the `http.md`
request headers and one-`Frame` body on the request stream, and one
status plus one-`Frame` body on the response stream. Pseudo-header
violations (wrong `:path`, `:method ≠ POST`, query on `:path`) fail per
the same rules as `http.md` §1A (mapped through H2 status delivery,
§1F). Connection-level frames (`SETTINGS`, `PING`, `GOAWAY`) MUST NOT
carry Syntra semantics.

**SNTR-HTTPS-041** — Concurrency and independence: streams are
independent RPCs. Hosts MUST support at least 16 concurrent streams per
connection unless a lower bound was negotiated (consistent with
SNTR-RPC-008 and `http.md` §1I), MUST enforce a documented maximum
(`SETTINGS_MAX_CONCURRENT_STREAMS` plus application caps), and MUST
reject excess pre-dispatch with `429`/`503` (H2 status delivery per §1F)
or post-acceptance with `200` + `RESOURCE_EXHAUSTED`, exactly as
`http.md` §1E prescribes.

**SNTR-HTTPS-042** — Ordering: none across streams. Responses MAY
complete out of request order; initiators MUST correlate solely by
echoed `request_id` and MUST NOT assume FIFO, stream-ID order, or
priority order. Stream priorities and weights are transport hints only
and MUST NOT affect Syntra outcome semantics.

**SNTR-HTTPS-043** — Syntra session independence from stream identity:
stream IDs, connection identity, and H2 coalescing MUST NOT imply
authentication or session continuity. Each stream carries its own
version headers and credential; each stream is one independent logical
connection/session per `http.md` §1I. Hosts MUST NOT expose H2 stream
identifiers as `request_id`, `connection_id`, or session handles, and
MUST NOT log stream IDs alongside principal material in ways that merge
the namespaces (SNTR-ASEC-001/004).

**SNTR-HTTPS-044** — Flow control and backpressure: H2 flow-control
exhaustion is a transport backpressure signal, not an RPC outcome.
Hosts MUST translate sustained pre-dispatch pressure to `429`/`503`
status delivery (never unbounded buffering), and post-dispatch pressure
to the documented queue policy (`200` + `RESOURCE_EXHAUSTED` or stream
reset with local `UNAVAILABLE`, outcome unknown). Deployments MUST
document window/queue bounds alongside §1M limits.

**SNTR-HTTPS-045** — Server push is FORBIDDEN as Syntra event delivery:
hosts MUST NOT send `PUSH_PROMISE` for Syntra resources, and initiators
MUST NOT accept pushed Syntra data (`http.md` §1O, events §1K).
Initiators SHOULD disable push (`SETTINGS_ENABLE_PUSH = 0`); a received
`PUSH_PROMISE` MUST be refused (`RST_STREAM`) and MUST NOT be parsed as
a `Frame` or an event.

### 1F. HTTP/2 failure mapping (stream vs connection)

**SNTR-HTTPS-050** — Delivery of §1E statuses over H2 uses normal
H2 response headers (`:status`) plus an empty/missing body per `http.md`
§1E; envelope rules for `200` are unchanged (verify `Content-Type`,
`Syntra-Version`, echoed `request_id`, set `outcome`).

**SNTR-HTTPS-051** — Stream errors and connection drain:

- `REFUSED_STREAM` means the host performed no application processing
  for that stream (RFC 9113): the initiator MAY treat the RPC as
  definitely-not-executed and retry per `http.md` §1J (fresh
  `request_id`, same operation key, bounded jittered backoff).
- Any other stream error (`RST_STREAM` with any other code,
  `STREAM_CLOSED` mid-body, compression failure) → transport failure
  for that RPC only, reported locally as `UNAVAILABLE` (outcome
  unknown); retry only idempotent/with-key.
- A received `GOAWAY` is a drain signal, not immediate failure of every
  in-flight RPC. Its last-stream-ID bounds which client-initiated streams
  the host might have processed (RFC 9113 §6.8/§8.7):
  - Streams with IDs greater than last-stream-ID were not processed;
    the initiator MAY classify them as definitely-not-executed and retry
    on a new connection per `http.md` §1J (fresh `request_id`, same
    operation key, bounded jittered backoff; the core never retries
    automatically).
  - Streams with IDs less than or equal to last-stream-ID may have been
    processed. They MAY finish during the grace window; a valid terminal
    `result` retains its outcome. If no definitive outcome is received
    before reset/loss/teardown, report local `UNAVAILABLE` (outcome
    unknown) per SNTR-REL-009; retry only idempotent/with-key. The cutoff
    does not itself prove execution or non-execution for these streams.
  - With multiple `GOAWAY`s, use the smallest received last-stream-ID;
    later cutoffs MUST NOT increase it. After `GOAWAY`, initiators MUST
    NOT open new streams on the draining connection. Servers SHOULD
    complete or reset eligible in-flight streams promptly and SHOULD
    allow a grace window per the documented close policy before teardown
    (analogous to SNTR-HS-006/013).
- Connection loss without a prior non-execution signal maps unfinished
  RPCs to local `UNAVAILABLE` (outcome unknown) per SNTR-REL-009; retry
  only idempotent/with-key. TLS/ALPN establishment failure before any RPC
  was sent cannot have dispatched an RPC and MUST NOT trigger fallback
  to plaintext or weaker TLS.

**SNTR-HTTPS-052** — A `200` stream whose body violates envelope rules
(malformed suffix, raw-wire duplicate envelope fields per SNTR-HTTP-021,
wrong `request_id`, version mismatch, unset outcome)
is handled exactly as `http.md` §1E: discard, local `UNAVAILABLE`. H2
framing success (END_STREAM received) proves nothing about application
processing (SNTR-CORE-005). Valid appended unknown fields remain accepted
per SNTR-SER-003; END_STREAM, not a Protobuf end marker, delimits the body.

### 1G. Proxies, termination, and deployment posture

**SNTR-HTTPS-060** — Where TLS terminates at a reverse proxy before the
host (SNTR-TSEC-008): (a) the proxy-to-host leg MUST be explicitly
secured (TLS 1.3 or a documented isolated private network — otherwise
treated as hostile); (b) the endpoint identity the initiator verified
MUST be the proxy's identity as the deployment's authenticated front
door, AND the proxy MUST validate the backend identity; (c)
`Host`/`:authority`/SNI/ALPN and principal context MUST propagate
without alteration or with explicitly documented mapping;
(d) misconfiguration (mismatched SNI, stripped identity, inconsistent
`:authority`) MUST cause handshake/binding failure, never silent
fallback. `X-Forwarded-*` / `Forwarded` headers MUST NOT be trusted for
authentication, principal selection, or session continuity; proxies MUST
NOT inject, copy, or forward `Authorization` across origins.

**SNTR-HTTPS-061** — Recommended deployment posture (policy, not wire):
serve HSTS (`Strict-Transport-Security`) on the HTTPS origins, disable
TLS-port plaintext fallback entirely, and document rotation and
revocation-check procedures alongside conformance claims
(SNTR-TSEC-003/006).

### 1H. No cross-profile session continuity

**SNTR-HTTPS-070** — A Syntra session established over one profile MUST
NOT resume over another (H1 ↔ H2, TLS/TCP ↔ HTTPS, WS ↔ HTTPS) in
default v1. Cross-transport resumption is permitted ONLY where a
resumption RFC explicitly binds the profile pair with revalidation and
no downgrade (`sessions.md` §1D). Until then, hosts MUST reject
cross-profile presentations exactly like any unnegotiated resumption
attempt.

## 2. Client behavior

- **SNTR-HTTPS-080** — The initiator MUST: negotiate TLS 1.3 with chain
  + hostname verification BEFORE any Syntra bytes (SNTR-TSEC-003/004);
  offer ALPN per §1C; send the exact `http.md` request shape on H1
  exchanges and H2 streams; verify `200` envelope agreement per stream;
  map stream/connection failures per §1F; never infer principal or
  session from connection/stream reuse; treat `GOAWAY` as drain (no new
  streams); refuse server push; never downgrade or auto-follow across
  origins (`http.md` §1L).

## 3. Server behavior

- **SNTR-HTTPS-081** — The host MUST: present a valid chain for the
  claimed endpoint; enforce TLS 1.3 minimum and ALPN selection; enforce
  per-stream version/header/credential validation identical to H1
  exchanges; enforce documented stream/queue/window bounds with
  pre-dispatch `429`/`503` before degrading conformant streams
  (SNTR-ASEC-020); never push; never expose stream IDs as Syntra IDs;
  log TLS/binding failures without credential or payload material.

## 4. Failure handling

TLS/ALPN failures → terminal handshake failure before any Syntra
exchange (no `hello` equivalent sent). Per-stream binding failures use
`http.md` §1E statuses delivered as H1 responses or H2 `:status`
headers. Unfinished streams on connection failure → local `UNAVAILABLE`
(outcome unknown), except where non-execution is proven by `REFUSED_STREAM`
or a received `GOAWAY` cutoff below the stream ID (§1F). Streams at or below
the cutoff may complete while draining; absent a definitive outcome they
remain unknown. No new streams open on the draining connection. Repeated
failures from one source MUST trigger rate-limiting or temporary blocking.

## 5. Security considerations

TLS protects the channel, not application semantics: it provides no
idempotency, authorization, or payload-validity (SNTR-RPL-002). Threat
traceability inherits `http.md` §6 with H2 additions: connection
coalescing and cross-origin reuse MUST NOT merge principal state
(T5/T9); `REFUSED_STREAM` retry-safety MUST NOT be extended to any other
reset (T4); push refusal closes an event-injection path (T9); proxy
termination rules close identity-binding breaks (T10); ALPN mismatch
fails closed against protocol-confusion downgrade (T2).

## 6. Compatibility considerations

HTTPS/H1 and HTTPS/H2 are transport revisions: they MUST NOT change
`Frame` semantics, the endpoint, headers, or status layering
(SNTR-VER-001). Adding a new ALPN binding or a new secure profile is a
minor RFC reusing the `Frame` unchanged; weakening TLS, permitting
plaintext public use, or giving stream IDs Syntra meaning is breaking
and FORBIDDEN for v1 public deployments. Capability-gated future work
(resumption tokens, compression codings) arrives via RFC, never by
improvising headers.

## 7. Explicit exclusions

**SNTR-HTTPS-090** — The following MUST NOT be claimed as supported by a
v1 HTTPS implementation: HTTP/3, QUIC (any version), WebSocket over
HTTP/2 Extended CONNECT (RFC 8441/9220), QUIC DATAGRAM, server push as
Syntra event delivery (any form), and long-lived event streams over H2
streams (each H2 stream is exactly one RPC/response pair, then ends).
Specifications MAY reserve extension points for them but MUST label them
future work (SYN-ARCH-051).

## 8. Conformance requirements

- **SNTR-HTTPS-900** — Executable cases in
  `conformance/requirements/https.md` (`CONF-HTTPS-001…012`): HTTPS/H1
  success, HTTPS/H2 success, concurrent H2 streams with out-of-order
  completion, invalid chain / wrong hostname / expired rejection before
  any credential, TLS <1.3 refusal, plaintext-fallback absence, ALPN
  mismatch closure, rotation acceptance, `REFUSED_STREAM` retry-safety
  vs other-reset unknown-outcome, `GOAWAY` drain mapping, proxy mismatch
  rejection, push refusal, cross-profile non-resumption.
- **SNTR-HTTPS-901** — Interop proof: the same logical RPC fixtures pass
  over HTTPS/H1 and HTTPS/H2 with equal decoded request/result fields and
  bit-preserved opaque payloads, not byte-identical Protobuf encodings
  (SNTR-SER-002/901). Both profiles synthesize negotiation/authentication
  per exchange; neither sends `hello`/`ready`/`Notification` frames. The
  two-profile proof is a separate goal, not a prerequisite for a
  single-transport Core claim. The H2 sequence in
  `conformance/test-vectors/http/http2-sequence.md` is reproducible from
  the specification alone.

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  Note over C,H: TLS 1.3 + ALPN(h2) verified before any Syntra bytes
  C->>H: TLS ClientHello (v1.3, ALPN h2/http/1.1, SNI)
  H-->>C: Certificate chain (validate + hostname)
  C->>H: HEADERS stream=1 POST /syntra/v1/rpc (Min/Max-Version, Authorization)<br/>DATA Frame{v=max, id=7, request{Echo}}
  C->>H: HEADERS stream=3 POST /syntra/v1/rpc<br/>DATA Frame{v=max, id=8, request{KV/Get}}
  H-->>C: HEADERS stream=3 :status=200<br/>DATA Frame{v=1, id=8, result{B}}
  H-->>C: HEADERS stream=1 :status=200<br/>DATA Frame{v=1, id=7, result{A}}
  Note over C: Out-of-order completion is legal; correlate by id only
  Note over C,H: No PUSH_PROMISE; no stream-ID-as-session; GOAWAY drains
```
