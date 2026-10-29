# Syntra Architecture and Project Charter

- Version: Syntra v1 (draft charter, 2026-10-19)
- Status: Proposed — pending maintainer approval via RFC process
- Authority: This document is the project charter. It is **non-normative
  overview** except where explicit `SYN-ARCH-*` requirements state
  otherwise. Normative behavior is owned by specifications listed in
  Section 8. The Rust implementation is non-normative (see ADR-010).
- Audience: A developer who has never heard of Syntra.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in BCP 14
[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html)
[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) when, and only
when, they appear in all capitals. Lowercase uses are ordinary English.

---

## 1. What Syntra is

Syntra is a general-purpose, transport-independent, binary client-server
communication protocol.

Syntra defines:

- Wire envelopes and Protobuf serialization (`proto/syntra/v1/*.proto`)
- Protocol framing separate from Protobuf encoding
- Connection establishment
- Handshake and version negotiation
- Generic authentication mechanisms and interfaces (opaque credentials)
- Logical sessions and optional resumption semantics (as specified;
  no durable-state guarantee beyond what a future session specification states)
- Request/response correlation and generic RPC
- Capability negotiation
- Standardized errors
- Optional generic event streams and recovery (as specified; at-most-once
  unless a future specification states otherwise)
- Supported network transport profiles
- Interoperability and conformance requirements

A Syntra **host** (server) exposes named methods with opaque byte
payloads. A Syntra **initiator** (client) invokes those methods,
correlates responses by identifier, and optionally receives opaque
event notifications after authentication. Syntra never interprets the
meaning of a method, payload, or event. Interpretation belongs to the
host application.

Neutral examples used throughout this project: `echo`, `get`/`put` on a
generic key/value service, and subscription to a generic event topic.
These examples illustrate mechanics only and impose no data model.

### Accepted secure-channel profile

[RFC 0007](../rfcs/0007-secure-channel-device-authorization.md) and
[ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md)
are accepted. Syntra Secure Channel v1 (SC1) uses Noise NK for authenticated
bootstrap and Noise NKpsk0 for returning devices sharing a unique random
32-byte authorization key (AK). AKs persist across reconnects; ephemeral keys,
directional traffic keys and channel state do not. A lookup handle is not an
authenticator. Enrollment, credential storage and permissions stay host-owned;
no particular account model is required. The public profile is
`SNTR-SC1-WSS-V1`; SC1/WSS still requires verified outer TLS 1.3.

The proposal adds a transport-independent channel layer below Syntra frames,
with separate TCP, UDP and WebSocket mappings. It does not make the core
open sockets, require a carrier library or implement application E2EE.
Existing adapters remain optional implementations, not the definition of
the protocol. No first-flight application effects or automatic security
fallback are proposed.

```text
Application: enrollment authority, stores, permissions, opaque payloads
Syntra core: Frame, hello/ready, sessions, RPC and correlation
SC1: established Noise implementation, channel state, protected records
Carrier binding: TCP stream | UDP datagrams | WebSocket binary messages
External carrier I/O supplied by the embedding application
```

See the proposed [shared channel](security/secure-channel.md),
[device authorization](security/device-authorization.md),
[carrier bindings](transports/noise-bindings.md), and [ADR-011](decisions/ADR-011-noise-device-authorization.md).
These do not yet amend the baseline requirements in §§3/7/9 or ADR-008.
Raw UDP is still deferred; existing HTTPS/WSS retain TLS, and a new
Noise-in-WebSocket binding would not change existing WS/WSS wire formats.
Persistent authorization is separate from logical-session recovery and RPC
replay. Acceptance and independent verification are outstanding.

## 2. What Syntra is not

Syntra is **not**:

- A messenger, social platform, payment system, proprietary server,
  database, cloud deployment, or unpublished application architecture.
- A definer of business logic, data models, or internal architecture
  for any specific application.
- A chat system. The protocol has no notion of messages in the human
  sense, conversations, contacts, user profiles, read receipts, delivery
  receipts, or messaging groups. Generic principals, endpoints,
  identities, opaque payloads, requests, responses, streams, and events
  are the only acceptable protocol abstractions.
- An application-level encryption protocol, cryptographic ratchet, or
  custom cipher. Syntra MUST NOT define or implement one (see Section 7).
- A transport receipt that proves application processing. Receipt of
  bytes by a transport or by Syntra framing proves nothing about
  application handling.
- A replacement binary IDL. Syntra uses Protocol Buffers (proto3) and
  MUST NOT invent a competing IDL.
- A socket library, TLS implementation, or application framework. The
  core is independent of sockets; transport adapters are independent of
  application logic.
- A normative Rust API. The Rust reference implementation conforms to
  the specification; it does not define it.

**SYN-ARCH-001** — Specifications and schemas MUST NOT reference any
specific messenger, social platform, payment system, proprietary server,
database, cloud deployment, or unpublished application architecture.

**SYN-ARCH-002** — Specifications and schemas MUST NOT embed
domain-specific concepts such as chat messages, conversations, contacts,
user profiles, read receipts, delivery receipts, or messaging groups.

## 3. Primary design goals

1. **Specification first.** Wire contracts and behavior are defined in
   Markdown specifications and `.proto` files before code. Code follows
   specification; specification never follows code.
2. **Transport independence.** One protocol core runs over multiple
   transports via thin adapters. Framing is transport-specific;
   Protobuf encoding is not.
3. **Genericity.** Methods, payloads, credentials, and events are opaque
   to the core. The core routes, correlates, bounds, times out, and
   reports errors without parsing application semantics.
4. **Explicit boundaries.** Core vs. transport vs. application are
   sharply separated (see Section 5 and ADR-004).
5. **Interoperability.** Any language can implement Syntra from the
   specifications and `.proto` files alone, without access to Rust
   source or any private repository.
6. **Safety and boundedness.** Bounded buffers, explicit resource
   limits, deterministic failure/timeout/cancellation behavior, no
   panics on untrusted input, no unbounded allocation.
7. **Secure by default for public use.** Public production deployments
   REQUIRE secure transports and established TLS implementations. No
   custom cryptography.
8. **Evolvability.** Versioned wire contracts, explicit unknown-field
   and unknown-message behavior, mandatory vs. optional capabilities,
   and a public RFC process for breaking changes.

## 4. Protocol roles

| Role | Obligation summary |
|------|--------------------|
| **Initiator (client)** | Opens a transport connection; proposes a version range and presents an opaque credential in `ClientHello`; invokes generic RPCs with bounded budgets; correlates `RpcResult` by `request_id`; handles `ServerReady`, typed errors, and optional notifications. |
| **Host (server)** | Validates versions and credentials per its own policy; accepts or rejects the connection with `ServerReady` or a typed error; dispatches opaque RPCs to application handlers; enforces authentication before protected operations; emits optional notifications only after readiness. |
| **Transport adapter** | Maps the transport-independent `Frame` to/from bytes on a specific transport (TCP, TLS, HTTP/1.1, HTTPS, HTTP/2, WebSocket). It MUST NOT interpret RPC semantics. |
| **Application** | Owns methods, payload schemas, credentials issuance/validation, authorization policy, and event meaning. It sits above Syntra and is out of scope for this repository except as neutral examples. |

Client and server obligations are specified separately in each
normative specification. Where this charter states a joint property,
the corresponding specification restates per-role requirements.

## 5. Layering and boundaries

```text
+--------------------------------------------------+
| Application (out of scope)                       |
|  methods, payload schemas, auth policy, events   |
+--------------------------------------------------+
| Syntra core (transport-independent)              |
|  Frame, hello/ready, RPC, cancel,               |
|  notification, errors, version/capability logic  |
+--------------------------------------------------+
| Transport adapter (per profile)                  |
|  TCP | TLS 1.3/TCP | HTTP/1.1 | HTTPS (H1/H2)     |
|  WS (H1) | WSS (H1)                               |
+--------------------------------------------------+
| Established TLS / socket / HTTP implementations  |
+--------------------------------------------------+
```

**SYN-ARCH-010** — The protocol core MUST be independent of any socket
library. Transport concerns MUST live in adapters.

**SYN-ARCH-011** — Transport adapters MUST be independent of
application logic. An adapter MUST NOT parse, decrypt, or validate
opaque application payloads or credentials beyond routing them.

**SYN-ARCH-012** — Protobuf encoding MUST be kept separate from
transport framing. A change of transport framing MUST NOT change the
Protobuf definition of `Frame`, and a change of `Frame` fields MUST NOT
require a new framing design except for length/type prefixes defined by
the transport specification.

**SYN-ARCH-013** — Syntra MUST carry opaque application bytes without
parsing or decrypting application ciphertext. If the application
encrypts, encryption and decryption occur above Syntra.

## 6. Compatibility guarantees

- **Wire versioning.** Every `Frame` carries `version`. Negotiation uses
  `min_version`/`max_version` in `ClientHello`. See ADR-009.
- **Unknown fields.** Protobuf unknown fields MUST be ignored on receipt
  and MUST NOT cause failure, unless a future specification explicitly
  marks a field as critical. Unknown message types (unrecognized `oneof`
  bodies) MUST be rejected with `UNIMPLEMENTED` and MUST NOT be silently
  dropped, so peers detect mismatch deterministically.
- **Reserved values.** `reserved 16, 17` and `reserved "event",
  "resume", "ack"` in `Frame` MUST be preserved. New fields MUST NOT
  reuse those numbers or names without a major-version RFC.
- **Mandatory vs. optional.** `hello`, `ready`, `request`, `result`,
  `cancel`, typed errors are mandatory to interoperate. `notification`
  (event streams), session resumption, and capability extensions are
  OPTIONAL and negotiated. A peer MUST NOT require an optional
  capability without prior negotiation.
- **Breaking changes.** Any wire-incompatible change REQUIRES a major
  version and an accepted RFC. Minor additions MUST be backward
  compatible. See `GOVERNANCE.md` and `rfcs/README.md`.

**SYN-ARCH-020** — Implementations MUST preserve and respect `reserved`
field numbers and names in `proto/syntra/v1/envelope.proto` (`Frame` reservations).

**SYN-ARCH-021** — Implementations MUST ignore unknown Protobuf fields
and MUST reject unknown `Frame.body` variants with
`ERROR_CODE_UNIMPLEMENTED`.

## 7. Threat assumptions and security policy

Syntra assumes a **hostile network**: attackers can observe, delay,
reorder, replay, truncate, and inject traffic on insecure transports,
and can present arbitrary bytes as credentials, methods, payloads, and
notifications.

Therefore:

- **SYN-ARCH-030** — Public production deployments MUST use secure
  transports (TLS 1.3 over TCP, HTTPS via HTTP/1.1 or HTTP/2, or Secure
  WebSocket over HTTP/1.1). Plain TCP, plain HTTP/1.1, and plain
  WebSocket over HTTP/1.1 are for restricted development environments
  only and MUST NOT be used for public production traffic.
- **SYN-ARCH-031** — Implementations MUST use established TLS
  implementations and MUST NOT invent cryptographic algorithms,
  ratchets, or custom ciphers.
- **SYN-ARCH-032** — `ClientHello.credential` MUST be treated as opaque
  sensitive bytes. The core MUST NOT log, persist, or interpret it. It
  MUST only be transmitted over secure transports in production.
- **SYN-ARCH-033** — Hosts MUST NOT grant access to protected
  operations before successful authentication. Failures MUST use
  `ERROR_CODE_UNAUTHENTICATED` or `ERROR_CODE_PERMISSION_DENIED`
  without leaking private diagnostics or credentials. `RpcError.message`
  MUST NOT contain credentials or private backend diagnostics.
- **SYN-ARCH-034** — Implementations MUST enforce bounded buffers,
  explicit resource limits (maximum frame size, maximum concurrent RPCs,
  call budgets via `timeout_ms`, handshake timeouts), and deterministic
  timeout/cancellation behavior. Untrusted input MUST NOT cause panics
  or unbounded allocation.
- **SYN-ARCH-035** — Transport receipt, framing acknowledgment, or TLS
  success MUST NOT be represented as application processing. Only an
  application-level `RpcResult` with a success payload proves
  application success.

Full requirements live in the (forthcoming) security specification,
which owns security requirements per Section 8. This charter does not
replace it.

## 8. Requirement ownership (authoritative sources)

This matrix is the **authoritative owner map**. In case of conflict,
the listed owner prevails for its row. All other artifacts are
informative for that concern.

| Concern | Authoritative source | Non-authoritative mirrors |
|---------|----------------------|---------------------------|
| Data representation (fields, numbers, types, reserved values) | `proto/syntra/v1/*.proto` (Protobuf schemas, Buf v2 governed) | Spec text summaries, code comments, wiki pages |
| Behavior (state machines, handshake, RPC, cancellation, errors, streams) | `specifications/*.md` — core specifications | Proto comments, READMEs, implementation docs |
| Network mappings (framing, TLS profile, HTTP/WS binding, limits on the wire) | `specifications/transports/*.md` — transport specifications (forthcoming) | Core specs, code |
| Security requirements (threat model, auth interfaces, transport policy, limits) | `specifications/security/*.md` — security specifications (forthcoming) | Architecture overview, code |
| Executable verification (what "conformant" means) | Conformance and interoperability suite (forthcoming) | Manual test notes |
| Implementation (one way to satisfy the above) | Separate language implementation projects, out of scope for this repository (non-normative) | Any conforming implementation |

For RFC 0007, the accepted security owners are `security/secure-channel.md`
and `security/device-authorization.md`; the network-mapping owner is
`transports/noise-bindings.md`. Acceptance does not create an exception to
this ownership matrix or to the TLS production policy.

**SYN-ARCH-040** — Protobuf schemas are the sole authority for data
representation. Specification prose MUST NOT redefine field numbers or
types.

**SYN-ARCH-041** — Core specifications are the sole authority for
behavior. Implementations MUST conform to them; implementations MUST
NOT become the normative source of behavior.

**SYN-ARCH-042** — Transport specifications are the sole authority for
network mappings. Core specifications MUST NOT embed socket or TLS
details.

**SYN-ARCH-043** — Security specifications are the sole authority for
security requirements. No other document MAY weaken them.

**SYN-ARCH-044** — The conformance suite is the sole executable
authority for verification. A claim of conformance MUST cite suite
results.

**SYN-ARCH-045** — The Rust reference implementation is
non-normative. It MUST conform to specifications; language-specific
convenience APIs MUST remain non-normative and MUST NOT impose
behavior on other languages.

## 9. Supported v1 transports and deferred profiles

### Supported in v1

- TCP — restricted development environments only.
- TLS 1.3 over TCP — production-capable.
- HTTP/1.1 — restricted development environments only.
- HTTPS using HTTP/1.1 — production-capable.
- HTTPS using HTTP/2 — production-capable.
- WebSocket over HTTP/1.1 — restricted development environments only.
- Secure WebSocket over HTTP/1.1 — production-capable.

Each profile will have a transport specification defining framing,
handshake binding, TLS requirements, limits, and failure mapping.

### Explicitly deferred (documented as future extensions only)

- Raw UDP
- DTLS
- QUIC
- HTTP/3
- QUIC DATAGRAM
- WebSocket over HTTP/2 Extended CONNECT

**SYN-ARCH-050** — Implementations claiming Syntra v1 conformance MUST
support at least one production-capable secure profile and MUST
clearly document which profiles they support. Insecure-only
implementations MUST NOT claim production conformance.

**SYN-ARCH-051** — Deferred profiles MUST NOT be described as
implemented. Specifications MAY reserve extension points for them but
MUST label them as future work.

## 10. Extension philosophy

- Prefer optional capabilities over version bumps.
- Prefer opaque payloads over core schema churn.
- Prefer explicit negotiation over probing.
- Prefer narrow, auditable public APIs.
- Every extension REQUIRES an RFC. Experimental extensions MUST be
  clearly marked and MUST NOT affect mandatory interop.

## 11. Implementation independence

**SYN-ARCH-060** — All specifications MUST be implementable without
access to Rust source code or any private repository.

**SYN-ARCH-061** — The Rust reference implementation MUST conform to
the specification. Language-specific convenience APIs MUST be
documented as non-normative.

**SYN-ARCH-062** — No specification, schema, or conformance test MUST
depend on a private product, company infrastructure, or unpublished
architecture.

## 12. Protocol walkthrough (informative)

### 12.1 Handshake

```text
Initiator                              Host
    |                                     |
    |--- transport connect --------------->|
    |--- Frame{hello{min,max,cred}} ------>|
    |                                     | validate version + credential
    |<-- Frame{ready{connection_id}} ------|
    |<-- Frame{result{...}} on failure ---X|
```

- `version` in each `Frame` is the negotiated wire version (currently 1).
- `request_id == 0` is reserved for notifications; RPCs use nonzero IDs.
- `connection_id` is opaque and MUST NOT be treated as an
  authentication session ID.

### 12.2 Generic RPC (echo example)

```text
Initiator                              Host
    |                                     |
    |--- Frame{id=7, request{            ->|
    |      method="/example.Echo/Echo",     |
    |      payload=<opaque>, timeout_ms=500}|
    |                                     | dispatch to handler
    |<-- Frame{id=7, result{payload}} -----|
    |   OR Frame{id=7, result{error}}       |
    |--- Frame{id=7, cancel} ------------->| (optional, best-effort)
```

Notifications MAY arrive before the corresponding `result`. `cancel`
requests cancellation; it does not roll back a committed mutation.

### 12.3 Key/value example (illustrative, non-normative)

- `method="/example.KV/Get"`, `payload=<opaque GetRequest bytes defined
  by the application>` → `result{payload=<opaque GetResponse>}` or
  `result{error{code=NOT_FOUND}}`.
- Syntra defines the envelope, correlation, timeout, and error code.
  The application defines what `Get` means.

## 13. Security and compatibility considerations (summary)

- See Section 7 for the binding policy. Rationale: development
  transports exist for offline/restricted testing; production MUST use
  vetted TLS.
- Compatibility: unknown-field tolerance plus strict unknown-message
  rejection gives safe evolution. Reserved values from earlier
  application-replay experiments are permanently retired to prevent
  cross-version confusion.
- Every normative requirement in future specifications MUST carry an ID
  and link to a conformance test. Every MUST/MUST NOT here links to
  acceptance criteria in Section 14.

## 14. Acceptance criteria (for this charter)

- [ ] A newcomer can state what Syntra is and is not without reading code.
- [ ] Roles, boundaries, transports, and deferred profiles are enumerated.
- [ ] Ownership matrix resolves every conflict of authority.
- [ ] No private dependency or domain-specific concept appears.
- [ ] Each `SYN-ARCH-*` requirement is testable by inspection or
      conformance suite.
- [ ] ADRs 001–010 each have an owner (the charter) and are linked from
      `specifications/decisions/`.

## Appendix A. Requirement index (this document)

SYN-ARCH-001, 002 (independence) · 010–013 (layering) · 020, 021
(compat) · 030–035 (security) · 040–045 (ownership) · 050, 051
(transports) · 060–062 (independence).

## Appendix B. References

- BCP 14 / RFC 2119 / RFC 8174 — requirement keywords.
- Protocol Buffers (proto3), Buf v2 — IDL and schema governance.
- TLS 1.3 (RFC 8446), HTTP/1.1, HTTP/2, WebSocket over HTTP/1.1 —
  transport profiles (details in forthcoming transport specs).
- Original schemas (historical commit `92e5f28`, now sole source in `proto/syntra/v1/`): `schema/syntra/v1/error.proto`, `schema/syntra/v1/session.proto` (removed; see `compatibility/v1-initial/` and pinned blob links in `specifications/schema/`).
