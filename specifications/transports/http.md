# Syntra v1 Transport — HTTP/1.1 RPC Mapping (Plaintext Profile)

- Identifier: `specifications/transports/http.md`
- Title: HTTP/1.1 Request/Response Mapping and Plaintext Profile
- Status: Draft (pending maintainer approval via RFC)
- Version: 1.0.0-draft.1 (2026-10-19)
- Normative references: BCP 14; RFC 9110, RFC 9112 (HTTP/1.1); RFC 4648 §4 (base64); `proto/syntra/v1/envelope.proto` (`Frame`), `rpc.proto`, `errors.proto`, `handshake.proto`
- Core dependencies: `specifications/core/protocol.md` (SNTR-CORE-*), `framing.md` (SNTR-WIRE-*), `serialization.md` (SNTR-SER-*), `rpc.md` (SNTR-RPC-*), `errors.md` (SNTR-ERR-*), `handshake.md` (SNTR-HS-*), `authentication.md` (SNTR-AUTH-*), `sessions.md` (SNTR-SESS-*), `events.md` (SNTR-EVENT-*), `reliability.md` (SNTR-REL-*), `versioning.md` (SNTR-VER-*)
- Security dependencies: `specifications/security/transport-security.md` (SNTR-TSEC-*), `authentication-security.md` (SNTR-ASEC-*), `replay-protection.md` (SNTR-RPL-*), `opaque-payloads.md` (SNTR-OPQ-*), `threat-model.md` (SNTR-TMOD-*)
- Charter/ADRs: SYN-ARCH-030/031/050/051; ADR-003 (transport-independent core), ADR-004 (layer boundaries), ADR-005 (connection vs session), ADR-006 (generic RPC), ADR-008 (transport security)
- Companion: `specifications/transports/https.md` (TLS, HTTPS/H1, HTTPS/H2)
- Scope: The normative mapping of one Syntra RPC onto one HTTP/1.1 request/response exchange, the canonical endpoint, media type, status layering, per-request authentication and session semantics, retries, caching, redirects, limits, compression, event exclusion, CORS posture, and the restricted-development plaintext profile. HTTPS/H1 and HTTPS/H2 bindings live in the companion document and inherit this mapping unchanged.

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 0. Design summary (informative)

HTTP is a strictly request/response transport with no server push and no
ordered bidirectional channel. The v1 mapping therefore treats each HTTP
exchange as one complete, independent logical Syntra connection: version
range and credential arrive as headers (the logical `ClientHello`), the
body carries exactly one `request` envelope, and the response carries
exactly one `result` envelope (the logical `ACTIVE` outcome and close in
one round trip). There is no persistent Syntra state between HTTP requests
in default v1 — no cookies, no session tokens, no `connection_id` reuse —
because v1 defines no resumption token (SNTR-SESS-006). Authentication is
per request, correlation is by echoing `request_id`, and every Syntra
failure the host produces travels as a 200-carried envelope while every
failure of the HTTP binding itself travels as a non-2xx status with no
Syntra body. HTTP semantics stay a transport mapping and never redefine
RPC semantics (SYN-ARCH-042, ADR-003).

[Draft RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
proposes a carrier-independent channel with [TCP/UDP/WebSocket candidates](noise-bindings.md),
not a Noise-over-HTTP request/response mapping. This profile's endpoint,
one-`Frame` body, `Authorization: Syntra` carriage, status layering and
per-request independence remain unchanged. Neither a proposed `auth_id` nor
an AK becomes an HTTP header, cookie, session authority or replacement
credential here. A future HTTP channel integration would need its own
explicit mapping and trusted authentication contract; connection reuse
cannot infer authorization. Existing HTTP tests and restricted-plaintext
policy continue to apply, with HTTPS required for public traffic under the
current TLS policy.

## 1. Protocol requirements

### 1A. Canonical RPC endpoint

**SNTR-HTTP-001** — The RPC endpoint is exactly:

```text
POST /syntra/v1/rpc
```

- The path is absolute, case-sensitive, and exact. `POST` is the only
  allowed method. The scheme/authority are deployment-defined (plaintext
  `http` for the restricted profile in §2, `https` for the secure
  profiles in `https.md`).
- **SNTR-HTTP-002** — Servers MUST accept `POST /syntra/v1/rpc` and MUST
  reject anything else as follows: a non-`POST` method on the exact path
  → `405` with an `Allow: POST` header; any other path (including with a
  different case or additional segments) → `404`; the exact path with a
  trailing slash (`/syntra/v1/rpc/`) → `404` (servers MUST NOT normalize
  it to the canonical path, so that path-confusion cannot merge distinct
  resources).
- **SNTR-HTTP-003** — Query policy: the canonical target MUST have no
  query component. A request whose target carries any query string
  (`/syntra/v1/rpc?...`, even empty `?`) MUST be rejected with `400`.
  Servers MUST NOT interpret query parameters, MUST NOT route on them,
  and MUST NOT read credentials, versions, or session hints from them
  (see §1H and SNTR-ASEC-003). Strict rejection (rather than the WS
  Upgrade binding's tolerance of unknown query parameters for routing)
  applies because the RPC endpoint has no routing use for query data:
  any query is either a client bug or smuggled material, and tolerance
  would widen cache-key and log-capture surface.
- **SNTR-HTTP-004** — Redirect behavior: servers SHOULD NOT redirect the
  RPC endpoint. A server that would otherwise redirect (canonical-host
  consolidation, path migration) SHOULD instead serve the endpoint
  directly or return the binding error (`404`/`400`); see §1L for the
  client rules that apply when a `3xx` is received anyway.
- **SNTR-HTTP-005** — No protocol credentials, session handles,
  `connection_id` values, principal references, or credential-derived
  material may appear in the target, query, fragment, `Host`, or any
  header except the single `Authorization` header defined in §1H. A
  request carrying credential-shaped material in any other position MUST
  be rejected with `400` without dispatch, and the material MUST be
  handled with credential confidentiality (§1H).
- **SNTR-HTTP-006** — Stable profile identifier: `SNTR-HTTP-V1` (this
  mapping over HTTP/1.1, plaintext or with TLS terminated before the
  host). The `-V1` suffix marks profile identifiers and distinguishes
  them from requirement IDs (`SNTR-HTTP-###`), consistent with
  `SNTR-WS-V1` / `SNTR-WSS-H1-V1`. Secure H1/H2 identifiers live in
  `https.md`. Implementations MUST document which identifiers they
  support per SYN-ARCH-050; insecure-only implementations MUST NOT
  claim production conformance.

### 1B. Media type

**SNTR-HTTP-010** — Bodies are project media type binary Protobuf:

```text
application/vnd.syntra.v1+protobuf
```

- The `vnd.` vendor tree plus `+protobuf` structured-syntax suffix
  documents that the bytes are one serialized `Frame`. This name is a
  project convention: it is NOT registered with IANA, v1 makes no claim
  of registration, implementations MUST NOT describe it as registered,
  and any future registration is a minor clarification, never a wire
  change. The type parameters, if any future revision defines them,
  REQUIRE an RFC; v1 senders MUST NOT emit parameters.
- **SNTR-HTTP-011** — Request `Content-Type` MUST be exactly this type
  (media-type token matched case-insensitively, no parameters). A
  missing, mismatched, or parameterized `Content-Type` MUST be rejected
  with `415` before body parsing. Charset or boundary parameters are
  meaningless for this binary type and MUST trigger `415`, not silent
  acceptance.
- **SNTR-HTTP-012** — A `200` response carrying a Syntra envelope MUST
  set `Content-Type: application/vnd.syntra.v1+protobuf`. Initiators MUST
  verify the response `Content-Type` on `200` and MUST treat a `200` with
  any other (or missing) type as a transport failure (§1G), never as an
  RPC outcome.
- **SNTR-HTTP-013** — Non-`200` responses carry no Syntra envelope and
  therefore carry no Syntra media type. Servers SHOULD send an empty body
  with binding errors; initiators MUST ignore the body of any non-`200`
  response (it may be injected by intermediaries and MUST NOT be parsed
  as a `Frame`).

### 1C. Message mapping (full envelope, exactly one)

**SNTR-HTTP-020** — The HTTP body contains the full Syntra `Frame`
envelope, never a bare `RpcRequest`/`RpcResult`:

- Request body: exactly one serialized `Frame` with `body = request`
  (field 12), a nonzero initiator-chosen `request_id`, and `version` set
  per §1D. `hello`, `ready`, `cancel`, and `notification` variants MUST
  NOT appear in HTTP request bodies; a request body decoding to any other
  variant (or to an empty `body`) MUST be rejected with `400`.
- Response body on `200`: exactly one serialized `Frame` with
  `body = result` (field 13), the same `request_id` as the request, and
  `version` equal to the selected version (§1D). The `outcome` oneof MUST
  be set (`payload` or `error`); a `200` body with an unset outcome is a
  host protocol violation and the initiator MUST treat it as a transport
  failure (§1G), never as success (SNTR-WIRE-007).
- **SNTR-HTTP-021** — Exactly one `Frame` per body in each direction.
  Senders MUST NOT batch multiple `Frame`s in one body and MUST NOT send
  length-prefixed streams of frames. Receivers MUST decode the entire
  body as one Protobuf message: Protobuf has no intrinsic end marker at
  which a "first complete Frame" can be separated from a suffix.
  Receivers MUST inspect raw-wire envelope fields before generated
  decoding can merge or overwrite them, and MUST reject duplicate known
  envelope fields (`version`, `request_id`, or any `body` member,
  including repeats of the same member) or multiple `body` members as
  batching/multiplicity violations. Concatenating complete serialized
  `Frame`s therefore cannot bypass the one-envelope rule via Protobuf
  merge/last-one-wins behavior. Malformed suffixes (e.g., a truncated
  varint or illegal field-zero tag) are also rejected. Rejection is `400`
  for requests and transport failure per §1G for responses. Valid unknown
  fields, including appended unknown fields, MUST be accepted per
  SNTR-SER-003, subject to size/depth limits, reserved-tag rejection, and
  envelope validation; their position is not a trailing-bytes violation.
- **SNTR-HTTP-022** — All core envelope rules apply unchanged inside the
  body: Protobuf binary encoding (SNTR-SER-001), unknown-field tolerance
  (SNTR-SER-003), ordered validation (SNTR-WIRE-005), the envelope size
  bound (§1N), empty-payload presence rules (SNTR-WIRE-007), and reserved
  rejection (SNTR-SER-008). The adapter MUST NOT interpret method,
  payload, or credential bytes beyond routing and bounding (ADR-004).

### 1D. Version negotiation synthesis (logical hello)

HTTP carries no `hello`/`ready` frames. The adapter synthesizes the
handshake from headers plus the request `Frame`. Header synthesis
(rather than envelope carriage as on the WS profile, where a persistent
connection carries real `hello`/`ready` frames) is REQUIRED here because
a request/response exchange has no channel for pre-RPC frames: the
version range and credential must arrive with the request itself. The
synthesized values have exactly the semantics of
`ClientHello{min_version, max_version, credential}` (SNTR-HS-003,
SNTR-AUTH-002), and the selected version has exactly the semantics of
the `Frame.version` agreed at `ServerReady` (SNTR-HS-004/010):

**SNTR-HTTP-030** — Every request MUST carry both headers, ASCII decimal,
no whitespace, nonzero, with `min ≤ max`:

```text
Syntra-Min-Version: 1
Syntra-Max-Version: 1
```

The request `Frame.version` MUST equal `Syntra-Max-Version`
(the initiator's proposed maximum, per SNTR-HS-003). The host selects the
highest version in the intersection of the advertised range and its
supported set (a v1 host supports exactly `{1}`), or, when the
intersection is empty, rejects with `400` without evaluating credentials
and without dispatch (version mismatch per SNTR-HS-003; `400` is the HTTP
binding of that handshake failure).

**SNTR-HTTP-031** — Every `200` response MUST carry:

```text
Syntra-Version: 1
```

whose value is the selected version. The response `Frame.version` MUST
equal this header value, and the initiator MUST verify the equality. A
`200` whose header and envelope versions disagree is a transport failure
(§1G). Non-`200` responses MAY omit `Syntra-Version` (binding failures
carry no negotiated version).

**SNTR-HTTP-032** — Header names are case-insensitive per HTTP semantics
(RFC 9110); values are exact decimal integers (no `v` prefix, no
whitespace, no leading `+`/`-`). Malformed, missing, or range-inverted
(`min > max`) version headers → `400`. Version state is per request:
there is no negotiated-version memory across requests (§1I).

### 1E. HTTP status layering (transport vs Syntra)

**SNTR-HTTP-040** — Layering rule (refines `errors.md` §1D for HTTP):

- A `200` carrying a valid `result` envelope is the ONLY carrier of a
  Syntra RPC outcome — success (`payload`) or application failure
  (`error`). The HTTP layer succeeded; the application verdict is inside.
- Any non-`200` status is a transport/binding outcome, never a Syntra
  RPC verdict. The host produced no `RpcResult` for that exchange. The
  adapter MUST NOT synthesize a `RpcResult` the host did not send, and
  the initiator MUST NOT treat any non-`200` as an application outcome.
- Adapters MUST NOT map `ErrorCode` values to HTTP statuses as a
  protocol signal. In particular, a normal Syntra error (`NOT_FOUND`,
  `PERMISSION_DENIED`, `INVALID_ARGUMENT`, `DEADLINE_EXCEEDED`,
  `RESOURCE_EXHAUSTED` from the handler, and so on) MUST travel as
  `200` + envelope, never as `4xx`/`5xx`. `500` MUST NOT be used for any
  RPC the handler evaluated.

**SNTR-HTTP-041** — Normative status table. "Body" constrains what the
server sends; "Local code" is the adapter's local report to its own
caller for that exchange — it is transport-adapter reporting, never a
host verdict, and it MUST be distinguishable from a 200-carried
`RpcResult{error}`. Retry-safety follows §1K; "definitely not executed"
claims rest on response authenticity, which holds on the secure profiles
(`https.md`) and is why the plaintext profile is development-only.

| Status | When the server sends it | Body | Local code (adapter report) | Handler executed? |
|---|---|---|---|---|
| `200 OK` | Binding valid; envelope dispatched (or handler rejected it as an RPC error) | REQUIRED: one `result` envelope (§1C); `Content-Type` + `Syntra-Version` + `Cache-Control: no-store` | The envelope's own outcome | Decided by the envelope |
| `400 Bad Request` | Malformed binding: bad target/query (§1A), bad version headers or no overlap (§1D), undecodable body, envelope validation failure (empty body, ID misuse, unknown variant, reserved), oversize headers beyond §1N, `Upgrade` on the endpoint (§1P), credential material outside `Authorization` (§1A) | SHOULD be empty; MUST be ignored | `INVALID_ARGUMENT` | No — rejected before dispatch |
| `401 Unauthorized` | Handshake auth failure: missing, malformed, invalid, expired, or revoked credential; unknown auth scheme (§1H) | SHOULD be empty; MUST be ignored; MUST include `WWW-Authenticate: Syntra realm="<deployment>"` | `UNAUTHENTICATED` | No — rejected before dispatch |
| `403 Forbidden` | Handshake authz failure: credential valid but the principal is denied all access at binding time (§1H) | SHOULD be empty; MUST be ignored | `PERMISSION_DENIED` | No — rejected before dispatch |
| `404 Not Found` | Unknown path (incl. trailing-slash variant) | SHOULD be empty; MUST be ignored | `UNIMPLEMENTED` (no such binding) | No |
| `405 Method Not Allowed` | Non-`POST` method on the endpoint | SHOULD be empty; MUST include `Allow: POST`; MUST be ignored | `UNIMPLEMENTED` | No |
| `408 Request Timeout` | Server gave up waiting for the complete request (slow headers/body past §1N windows) | SHOULD be empty; MUST be ignored; server SHOULD close the connection | `UNAVAILABLE` (outcome unknown) | No dispatch occurred, but the exchange is reported unknown so a racing dispatch can never be misread as proof |
| `413 Content Too Large` | Body exceeds §1N bounds (early `Content-Length` check or streaming cap) | SHOULD be empty; MUST be ignored | `RESOURCE_EXHAUSTED` | No — rejected before dispatch |
| `415 Unsupported Media Type` | Wrong/missing request `Content-Type` (§1B), or non-`identity` `Content-Encoding` where compression is not documented (§1O) | SHOULD be empty; MUST be ignored | `INVALID_ARGUMENT` | No |
| `429 Too Many Requests` | Pre-dispatch rate/concurrency/queue rejection | SHOULD be empty; MAY carry `Retry-After` as a transport hint (bounded jittered backoff REQUIRED regardless; the header is not a Syntra signal) | `RESOURCE_EXHAUSTED` | No — rejected before dispatch |
| `431 Request Header Fields Too Large` | Headers (incl. `Authorization`) exceed §1N bounds | SHOULD be empty; MUST be ignored | `RESOURCE_EXHAUSTED` | No |
| `500 Internal Server Error` | ONLY unexpected adapter/host failure with no Syntra verdict (crash before dispatch or during response encoding). MUST NOT carry handler failures. | SHOULD be empty; MUST be ignored | `UNAVAILABLE` (outcome unknown) | Unknown |
| `502 Bad Gateway` | Proxy/backend inconsistency (proxied deployments; see `https.md`) | Ignored | `UNAVAILABLE` (outcome unknown) | Unknown |
| `503 Service Unavailable` | Pre-dispatch overload or host shutdown | Ignored; MAY carry `Retry-After` as a hint | `UNAVAILABLE` (outcome unknown) | Unknown unless the deployment documents pre-dispatch rejection, in which case not executed |
| `3xx` | SHOULD NOT be sent for this endpoint (§1L) | Ignored; MUST NOT be followed automatically | `UNAVAILABLE` (transport outcome) | Unknown — MUST be treated as unknown |

**SNTR-HTTP-042** — Initiator handling of `200` bodies: a `200` whose
body is undecodable (including a malformed suffix), violates the raw-wire
multiplicity rules of SNTR-HTTP-021, echoes the wrong
`request_id`, carries a version mismatch against `Syntra-Version`, or
lacks `outcome` MUST be discarded as a transport failure reported locally
as `UNAVAILABLE` (outcome unknown — the handler may have executed). It
MUST NOT be reported as success and MUST NOT be branched on as an
application error.

**SNTR-HTTP-043** — Initiator handling of connection loss: a transport
that ends mid-exchange with no status and no complete `result` envelope
is reported locally as `UNAVAILABLE` (outcome unknown) per SNTR-REL-009;
retry follows §1K. A `200` is not a Syntra success signal — only
`RpcResult{payload}` is (SNTR-CORE-005).

### 1F. Timeouts and cancellation over HTTP

**SNTR-HTTP-050** — `RpcRequest.timeout_ms` is an end-to-end call budget
covering the whole HTTP exchange. `timeout_ms == 0` selects the host
default, which MUST be bounded and documented (SNTR-RPC-004). The host
MUST enforce the effective deadline on handler execution and return
`200` + `DEADLINE_EXCEEDED` on expiry; the initiator MUST enforce its own
timer (≤ requested budget) over the exchange.

**SNTR-HTTP-051** — Adapter validation (headers, version selection,
credential check) is handshake work and MUST complete within the
handshake deadline (default 5 s, SNTR-HS-002/011). Slow request headers
or a slow body past the documented inter-byte window MUST be closed with
`408` (SNTR-ASEC-021), never retained indefinitely.

**SNTR-HTTP-052** — No `Cancel` variant exists on HTTP profiles. An
initiator that no longer needs the RPC aborts the HTTP exchange
(closes the connection or cancels its request); locally it reports the
call per its own abandonment policy (commonly `CANCELLED`) but MUST NOT
represent the abort as a host verdict. A host observing a transport abort
SHOULD stop the associated work on a best-effort basis; cancellation is
advisory and MUST NOT be interpreted as rollback (SNTR-RPC-005). An
aborted exchange has unknown outcome; retry follows §1K.

### 1G. Initiator handling of transport outcomes

**SNTR-HTTP-055** — For any exchange that does not yield a valid `200`
envelope per §§1B–1D, the initiator MUST apply the §1E table: surface
the listed local code, synthesize no `RpcResult`, treat handler outcome
exactly as the table states (definitely-not-executed only where the
table says so, otherwise unknown), and choose retry per §1J. In
particular, a `200` with a wrong `Content-Type` (§1B), an unset
  `outcome` or version disagreement (§1C/§1D), or a malformed suffix or
  duplicate envelope fields (§1C) is a transport failure reported locally as
  `UNAVAILABLE` (unknown outcome) — never success and never an application error. This section
owns the initiator side of the §1E layering rule; servers own status
selection per SNTR-HTTP-040/041.

### 1H. Authentication carriage

**SNTR-HTTP-060** — The credential travels in exactly one header:

```text
Authorization: Syntra <base64>
```

where `<base64>` is the RFC 4648 §4 standard-alphabet base64 encoding
(padding included, no whitespace) of the opaque `ClientHello.credential`
bytes. The auth-scheme token `Syntra` is matched case-insensitively; the
parameter is case-sensitive base64. Semantics follow the approved opaque
framework (SNTR-AUTH-001/002, SNTR-ASEC-001/003): the adapter routes the
decoded bytes to credential evaluation bit-preserved, and MUST NOT log,
persist, echo, or interpret them.

**SNTR-HTTP-061** — Absent `Authorization` means an anonymous attempt
(empty credential, SNTR-AUTH-003); acceptance is host policy and binds a
least-privilege anonymous principal for that exchange only. A present
header with an undecodable, empty, or oversize parameter → `401`
(malformed credential material is evaluated as invalid, never as
anonymous, to avoid oracle/downgrade ambiguity). Any `Authorization`
scheme other than `Syntra` (e.g. `Bearer`, `Basic`) on this endpoint →
`401` with `WWW-Authenticate: Syntra ...`; the adapter MUST NOT attempt
to interpret foreign schemes as Syntra credentials.

**SNTR-HTTP-062** — Confidentiality: the header MUST traverse only secure
profiles in public deployments, or loopback-restricted plaintext for
development (SNTR-TSEC-009, §2). Initiators MUST verify endpoint
identity (hostname, chain) before sending the header on secure profiles
(SNTR-TSEC-004). Servers MUST treat the header as sensitive key material
in memory handling, logs, diagnostics, metrics labels, and error text
(SNTR-ASEC-001/011).

**SNTR-HTTP-063** — Missing vs expired: both are handshake auth failures
→ `401` with a generic message (SNTR-AUTH-006). The `401` MUST include
`WWW-Authenticate: Syntra realm="<deployment>"` where the realm is a
deployment identifier that leaks no principal, tenant, or backend
detail. Error text MUST NOT distinguish unknown-principal vs wrong-secret
vs expired vs revoked unless the deployment documents the oracle as
intentional (SNTR-ASEC-011).

**SNTR-HTTP-064** — Session binding: a validated credential binds the
principal for exactly one HTTP exchange (§1I). Per-RPC authorization
after binding uses the bound principal (SNTR-RPC-032): a method the
principal may not invoke → `200` + `PERMISSION_DENIED` (the handshake
succeeded; only this call is denied). Revocation or expiry observed
mid-exchange → the exchange fails `401` (or `200` +
`UNAUTHENTICATED` if a result envelope is still well-formed to send) and
no further exchanges are authorized without a fresh credential
(SNTR-AUTH-008). There is no same-exchange re-authentication: a second
credential for an in-flight exchange is impossible by construction, and
a changed credential goes on the next exchange (consistent with
SNTR-AUTH-010, which forbids same-connection principal change).

**SNTR-HTTP-065** — The binding MUST NOT depend on TCP connection
identity, source IP/port, TLS session identity, or connection reuse. Two
exchanges on one keep-alive connection with different credentials are two
independent bindings; one exchange's credential MUST NOT authorize
another exchange's work (SNTR-AUTH-031).

### 1I. Logical session over HTTP (per-request independence)

**SNTR-HTTP-070** — In default v1 (no resumption capability negotiated,
SNTR-SESS-006), each `POST /syntra/v1/rpc` exchange is one complete,
independent logical Syntra connection and session: synthesized
`hello` (headers + credential) → dispatch-or-reject → exactly one
terminal outcome (`200` envelope or binding status) → end. Sessions are
identified by nothing ambient: never by source IP/port, TLS session ID,
HTTP cookies, `connection_id`, `request_id`, or stream identity, unless a
future resumption RFC explicitly defines the binding (SNTR-SESS-006,
sessions §1E).

**SNTR-HTTP-071** — HTTP keep-alive, client connection pooling, and
pipelining MUST NOT merge Syntra state across exchanges. Hosts MUST NOT
cache principal bindings keyed by connection; initiators MUST present
the credential on every exchange (no "authenticated connection" concept
exists on HTTP profiles). A missing credential on exchange N is an
anonymous attempt even if exchange N−1 on the same connection was fully
authenticated.

**SNTR-HTTP-072** — Ordering: none. Concurrent exchanges (sequential
keep-alive requests outstanding via pipelining, parallel pooled
connections) are independent RPCs; responses MAY arrive in any order and
initiators MUST correlate solely by echoed `request_id`
(SNTR-RPC-002/§1E). Hosts MUST support at least 16 concurrent RPCs per
listener endpoint group unless a lower bound was negotiated, and MUST
reject excess pre-dispatch with `429` (or `200` +
`RESOURCE_EXHAUSTED` where the request was already accepted for
dispatch), per SNTR-RPC-008.

**SNTR-HTTP-073** — `request_id` discipline per exchange: nonzero,
initiator-chosen; the host MUST echo it identically in the `200`
envelope. IDs live for one exchange only. Hosts MUST NOT keep
cross-exchange `request_id` memory (no cross-request duplicate
rejection, no dedup on `request_id` — SNTR-RPC-007/010, SNTR-RPL-012);
clients SHOULD use unique IDs among in-flight exchanges to keep
correlation unambiguous. Reuse of an ID on a later exchange is a new,
unrelated correlation, never a replay (replay classes stay distinct per
SNTR-RPL-001).

**SNTR-HTTP-074** — Future resumption (reserved): a multi-exchange Syntra
session over HTTP is permitted ONLY under an RFC-defined resumption
capability with explicit token, lifetime, rotation, replay, and
cross-request binding rules. Until such an RFC exists, hosts MUST NOT
honor `Cookie`, `Session-ID`, `Syntra-Session`, or any non-specified
header as session state, and MUST NOT treat their absence as failure —
they are simply not part of v1.

### 1J. Retries and idempotency

**SNTR-HTTP-080** — HTTP-level retry does not make an operation safe.
`POST` is not idempotent by method, intermediaries MUST NOT retry `POST
/syntra/v1/rpc` automatically, and a mutating operation MUST NOT become
retryable merely because it travelled over HTTP (SNTR-REL-003,
SNTR-RPL-002). The core never retries (SNTR-REL-002); the initiator
decides per `rpc.md` §1I, with the HTTP binding adding only the
transport classification below.

**SNTR-HTTP-081** — Every retry attempt is a new exchange with a fresh
`request_id` (SNTR-RPL-020). An application operation key, where one
exists, is carried inside the opaque payload and MUST be repeated
bit-identical across attempts; the core/adapter preserves the bytes and
performs no deduplication (SNTR-RPC-007, SNTR-RPL-013).

**SNTR-HTTP-082** — Transport classification for the retry decision:

| Observation | Category | Rule |
|---|---|---|
| `200` + `result{payload}` | Definitive success | Do not re-issue as a retry; any repetition is a new application decision |
| `200` + `result{error}` other than `UNAVAILABLE`/`DEADLINE_EXCEEDED` | Definitive terminal outcome for this attempt | NOT_SAFE_TO_RETRY automatically; re-issue only as an explicit new application decision (SNTR-REL-003) |
| `200` + `result{error{UNAVAILABLE}}` or `DEADLINE_EXCEEDED` | UNKNOWN_OUTCOME | Retry only if idempotent or carrying the same operation key, with bounded jittered backoff |
| `408`, `500`, `502`, `503`, `504`, connection loss, `200`-with-corrupt-body (§1E) | UNKNOWN_OUTCOME | Same as above: retry only idempotent/with-key |
| `400`, `404`, `405`, `413`, `415`, `431` | Definitely not executed (binding rejected before dispatch; sound on response-authenticated profiles) | Fix the sender; do not retry identically (NOT_SAFE_TO_RETRY) |
| `401` | Handshake auth failure | Present a different/fresh credential on a new exchange with backoff; retrying identical bytes in a tight loop is FORBIDDEN (SNTR-AUTH-021, SNTR-ASEC-030) |
| `403` | Handshake authz failure | Do not retry identically; seek authorization change |
| `429` | Pre-dispatch exhaustion | Retry with bounded jittered backoff, same operation key, fresh `request_id` (SNTR-REL-008/020) |

**SNTR-HTTP-083** — `REFUSED_STREAM`/`GOAWAY` refinements for HTTP/2 are
defined in `https.md`; they narrow, but never contradict, this table.

### 1K. Caching

**SNTR-HTTP-090** — RPC responses MUST NOT be stored by any cache.
Servers MUST send `Cache-Control: no-store` on every response to the
endpoint (all statuses). Clients MUST send `Cache-Control: no-store` on
every request. Intermediaries MUST NOT store responses to authenticated
or anonymous RPC exchanges, and MUST NOT serve a stored response for
this endpoint under any circumstance.

**SNTR-HTTP-091** — Responses SHOULD also carry `Vary: Authorization` so
that any non-conformant store cannot collapse distinct principals'
responses. `ETag`, `Last-Modified`, and other validators MUST NOT be
emitted for the endpoint, and conditional-request headers
(`If-None-Match`, `If-Modified-Since`) MUST be ignored for RPC semantics
(a `304` MUST NOT be sent for this endpoint).

### 1L. Redirects (client rules)

**SNTR-HTTP-100** — Initiators MUST NOT follow redirects automatically
for `POST /syntra/v1/rpc`. A `3xx` received on the endpoint MUST
terminate the exchange as a transport outcome (`UNAVAILABLE`, unknown
per §1E) without re-sending the request or the credential.

**SNTR-HTTP-101** — Manual following (operator-directed only, never by
default) MUST satisfy ALL of: (a) strip `Authorization` and any
credential material before re-issuing, then re-authenticate explicitly
for the new target; (b) same-origin only (identical scheme, host, and
port) unless the operator has allow-listed the new origin; (c) never
downgrade (`https` → `http` following is FORBIDDEN; any downgrade
attempt MUST fail closed per SNTR-TSEC-007); (d) preserve method and
body semantics (only `307`/`308` preserve `POST`; a `301`/`302`/`303`
MUST NOT be followed by rewriting to `GET`); (e) a documented hop limit
(recommended: 0 by default, at most 3 when enabled); (f) re-validate
endpoint identity for the new origin before sending credentials
(SNTR-TSEC-004). Rationale: credential forwarding across origins, host
change, and plaintext downgrade are T2/T10 threats (SNTR-TMOD-030).

### 1M. Body and header limits

**SNTR-HTTP-110** — Maximum body: the serialized request `Frame` MUST
fit `DEFAULT_MAX_FRAME_BYTES` (1 MiB, SNTR-WIRE-006) unless the
deployment documents a different bound for this endpoint; the bound
covers the whole serialized envelope including method, payload,
credential-adjacent overhead, tags, and lengths — a 1 MiB application
payload alone therefore does NOT fit (open conflict B8; implementations
MUST enforce the envelope bound on serialized bytes and MUST NOT
silently raise it).

**SNTR-HTTP-111** — `Content-Length` behavior: servers MUST validate
`Content-Length` before allocating. A declared length exceeding the bound
→ `413` without reading the body. A declared length disagreeing with the
bytes actually received (truncation/overrun) → `400` (malformed
transport). Missing `Content-Length` with `Transfer-Encoding: chunked`
is accepted per §1M; a request with neither framing header has a
zero-length body (RFC 9112) and therefore fails as an empty body (`400`).

**SNTR-HTTP-112** — Chunked transfer: servers MUST support chunked
request bodies and MUST enforce the bound as a running count of
received bytes, aborting the read and answering `413` (then closing)
the moment the count exceeds the bound. Chunk extensions MUST be
ignored; trailers MUST be ignored for RPC semantics (they MUST NOT carry
credentials, versions, or session hints — §1A/§1H).

**SNTR-HTTP-113** — Header bounds: deployments MUST document maxima for
request headers (recommended defaults: 8 KiB per field, 16 KiB total).
Exceeding them → `431`. The decoded credential MUST additionally fit a
documented credential bound not exceeding the envelope bound (default
ceiling 64 KiB); larger → `431` (header-carried, oversize). All bounds
MUST be enforced before allocation and before any credential comparison
(SNTR-ASEC-020/040).

**SNTR-HTTP-114** — Early rejection and allocation: servers MUST reject
oversize exchanges as early as the first conclusive signal (declared
length, header size, streaming count, decompressed count) and MUST NOT
buffer unbounded bodies, decompress unboundedly, or retain stalled
partial bodies past §1F windows.

### 1N. Compression

**SNTR-HTTP-120** — Default posture: no content compression. Hosts MUST
reject a request with `Content-Encoding` other than `identity` (or
absent) with `415`, unless the deployment explicitly documents
compression support for this endpoint. Hosts MUST NOT send
`Content-Encoding` on responses unless the client sent `Accept-Encoding`
AND the deployment documents response compression.

**SNTR-HTTP-121** — Where a deployment documents compression, it MUST
also document: the allowed coding(s), the decompressed absolute cap
(≤ the §1M body bound), a decompression-ratio cap, and the
fail-closed behavior on violation (abort + `413`). Decompressed byte
counts feed the same running bound as §1M; a bomb that exceeds it is a
`413`, never an allocation failure. Because payloads are opaque and may
be attacker-influenced while headers/credentials are sensitive,
deployments SHOULD keep compression disabled for this endpoint; enabling
it without the documented caps is non-conformant. (TLS-level
compression does not exist in TLS 1.3; nothing is negotiated there.)

### 1O. Event delivery (no push over request/response)

**SNTR-HTTP-130** — Plain HTTP/1.1 request/response cannot deliver
unsolicited host-originated events: there is no channel for
`Notification` frames (events §1K). Hosts MUST NOT attempt push over
this binding; initiators MUST NOT expect `Notification`s on it.

**SNTR-HTTP-131** — Where an application needs fresher state than
per-call results, it polls with ordinary RPCs (e.g., an
application-defined read returning queued state) — polling is an
application pattern above Syntra, using the same endpoint and envelope,
with per-request authentication and the same retry/caching rules.
Server-Sent Events, long polling (indefinitely-held responses), and
`Upgrade: websocket` on `/syntra/v1/rpc` are NOT approved mechanisms and
MUST NOT be described as implemented: an `Upgrade` request on the
endpoint MUST be rejected with `400`. HTTP/2 server push MUST NOT be
used as Syntra event delivery (normative in `https.md`).

### 1P. CORS and browser posture (deployment policy, never authorization)

**SNTR-HTTP-140** — CORS is a deployment relaxation for browser-based
initiators, not a Syntra authorization model. CORS headers MUST NOT
grant, imply, or substitute for principal authentication or per-method
authorization (SNTR-RPC-032, SNTR-ASEC-022).

**SNTR-HTTP-141** — Deployments that enable browsers MUST: (a) serve an
explicit origin allow-list (never `*` together with credentialed
requests); (b) answer preflight (`OPTIONS`) at the deployment layer with
the allow-listed methods/headers only — `OPTIONS /syntra/v1/rpc` is
otherwise `405`; (c) expose only the headers browsers need
(`Syntra-Version`, `Content-Type`; never `Authorization` values in
exposed lists beyond the standard `Authorization` opt-in); (d) set
`Vary: Origin`; (e) keep every rule in §§1A–1O intact for browser
traffic (per-request credential, `no-store`, no query credentials).
Permissive CORS (`*` + credentials, reflected-origin without
allow-listing) MUST NOT be deployed and MUST fail closed in review
(STEST proxy/origin checks).

## 2. Plaintext profile (restricted development only)

**SNTR-HTTP-150** — Plaintext HTTP/1.1 (`http` scheme, no TLS) is a
restricted-development profile ONLY (SYN-ARCH-030, SNTR-TSEC-001/005):

- Permitted environments: loopback interfaces or isolated test networks
  with no public routing. Distributions MUST document that the profile
  provides no confidentiality, integrity, or endpoint authentication.
- Production builds MUST disable the profile by default; enabling it
  MUST emit an explicit insecure-mode warning at startup and on every
  use.
- Production credentials (any credential also used against a secure
  profile or carrying real authority) MUST NOT traverse it; test
  fixtures MUST use throwaway credentials.
- The mapping in §1 is identical on plaintext and secure profiles, so
  interop tests transfer — except §1H confidentiality and §1E
  "definitely not executed" soundness, which hold only where responses
  are authenticated (i.e., only on the secure profiles in `https.md`).

## 3. Client behavior

- **SNTR-HTTP-160** — The initiator MUST: target the exact endpoint with
  `POST`; send `Content-Type` (§1B), both version headers (§1D),
  `Cache-Control: no-store`, and `Authorization` (or deliberately omit it
  for anonymous attempts) on every exchange; verify `200`
  `Content-Type`, `Syntra-Version`-vs-envelope agreement, echoed
  `request_id`, and set `outcome` before acting; treat every other
  outcome per §1E/§1K; never place credentials outside `Authorization`;
  never follow redirects automatically (§1L); enforce per-exchange
  timers (§1F); use fresh `request_id`s per attempt with bit-identical
  operation keys across retries (§1J).

## 4. Server behavior

- **SNTR-HTTP-170** — The host MUST: validate target/method/headers
  before body parsing where possible; enforce version selection (§1D)
  before credential evaluation; evaluate credentials in constant-time
  comparison where applicable (SNTR-AUTH-030) within documented bounds
  (§1M); dispatch only valid `request` envelopes to the bound
  principal's authorized handler; answer exactly one HTTP response per
  exchange (one `200` envelope or one binding status); set
  `Cache-Control: no-store` always; rate-limit handshake attempts and
  isolate misbehaving sources before conformant traffic degrades
  (SNTR-ASEC-020/040); log negotiation/binding failures without
  credential or payload material (SNTR-ASEC-001).

## 5. Failure handling

Binding failures use §1E statuses; RPC failures use `200` + envelope
codes per `errors.md`. Oversize → `413`/`431`; slow → `408` + close;
overload pre-dispatch → `429`/`503`; overload post-dispatch →
`200` + `RESOURCE_EXHAUSTED`; deadline → `200` +
`DEADLINE_EXCEEDED`; loss mid-exchange → local `UNAVAILABLE`. Repeated
binding failures from one source MUST trigger rate-limiting or temporary
blocking (SNTR-ASEC-020).

## 6. Security considerations

Hostile-network assumption applies (charter §7): opaque bytes arrive
attacker-controlled; validation order is target → method → headers →
version → bounds → credential → dispatch (shape before policy,
SNTR-ASEC-040). Credential confidentiality (§1H), no-URL-carriage
(§1A), oracle-free errors (§1E/§1H), bounded allocation (§1M), downgrade
refusal (§1L), and proxy rules (`https.md`) are security boundaries.
Threat traceability: T1 (TLS-only production + no-log rules), T2
(version/downgrade refusal, §1D/§1L), T4 (per-class replay rules,
§§1H–1J), T5 (no ambient session identity, §1I), T6 (ordered
validation + bounds, §1M), T7 (rate/concurrency/timeout discipline,
§§1F/1M/1E), T8 (generic errors, §§1E/1H), T10 (proxy/origin rules,
`https.md` + §1L).

## 7. Compatibility considerations

This mapping adds no wire fields and changes no core state machine: the
`hello`→`ready`→RPC sequence is synthesized per exchange, never altered
(SYN-ARCH-042, ADR-003). Version dimension stays `Frame.version` plus
the two negotiation headers; transport revisions (this document,
`https.md`) MUST NOT change `Frame` semantics (SNTR-VER-001). New
headers, media-type parameters, or multi-exchange session tokens all
REQUIRE an RFC + capability and MUST be ignored-or-rejected (never
improvised) until then. Reserved `Frame` values stay retired.

## 8. Conformance requirements

- **SNTR-HTTP-900** — Executable cases in
  `conformance/requirements/http.md` (`CONF-HTTP-001…016`): canonical
  success, wrong method/path, trailing slash, query rejection, wrong
  content-type, malformed body/suffix, raw-wire duplicate envelope fields,
  valid appended unknown fields (SNTR-SER-003), oversize body,
  version mismatch, missing/invalid/expired credential, normal `RpcError`
  over `200`, binding-status layering, concurrent-exchange independence,
  retry/idempotency discipline, redirect non-following, cache headers,
  compression rejection, no-push behavior, CORS non-authorization.
- **SNTR-HTTP-901** — Interop proof: the same logical RPC fixtures
  (`/example.Echo/Echo`, `/example.KV/Get`) pass over this HTTP binding
  and at least one other transport profile with only adapter changes
  (SNTR-WIRE-901). Compare decoded RPC requests/results and opaque bytes,
  not serialized-byte identity or an identical whole `Frame` sequence:
  HTTP synthesizes the handshake per exchange and carries no
  `hello`/`ready`/`Notification` frames. Handshake and event assertions on
  other legs follow their own profiles and claimed capabilities. Byte
  vectors in `conformance/test-vectors/http/` exercise the HTTP mapping
  of those shared RPC outcomes. This two-transport proof is a separate
  goal, not a prerequisite for a single-transport Core claim.

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  C->>H: POST /syntra/v1/rpc (Min/Max-Version, Authorization, Content-Type)<br/>Frame{v=max, id=7, request{/example.Echo/Echo}}
  H->>H: target→headers→version→bounds→credential→dispatch
  alt success
    H-->>C: 200 (Syntra-Version, no-store)<br/>Frame{v=1, id=7, result{payload}}
  else app failure
    H-->>C: 200<br/>Frame{v=1, id=7, result{error{UNIMPLEMENTED}}}
  else bad credential
    H-->>C: 401 (+ WWW-Authenticate, empty body)
  else malformed/oversize
    H-->>C: 400/413 (empty body)
  end
  Note over C,H: No hello/ready/notification frames on the wire;<br/>each exchange is one independent logical connection
```
