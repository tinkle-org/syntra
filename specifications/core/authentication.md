# Syntra v1 Core — Authentication

- Identifier: `specifications/core/authentication.md`
- Title: Abstract Authentication Protocol
- Status: Draft (pending maintainer approval via RFC)
- Version: 1.0.0-draft.1 (2026-10-19)
- Normative references: BCP 14; `proto/syntra/v1/handshake.proto` (`ClientHello.credential`, `ServerReady`); `protocol.md`; `handshake.md`; `errors.md`; `sessions.md`; charter SYN-ARCH-031–033; ADR-004
- Scope: Transport-independent authentication interfaces: credential carriage, initiation, optional challenge/response, success/rejection, principal binding, expiration/revocation, re-authentication. Credential formats, identity stores, and policy belong to the application and are out of scope. No private identity service is specified or assumed.
- Terminology: Per `protocol.md`. **Credential** = opaque initial credential bytes carried per profile (SNTR-AUTH-002) plus optional explicitly documented follow-ups. **Principal** = opaque authenticated identity handle. No assumption of user accounts — principals MAY be services, devices, keys, or anonymous contexts where the application permits.

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## Accepted persistent device authorization (additive profile)

[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
and [device authorization](../security/device-authorization.md) establish a
shared per-device AK incorporated into Noise NKpsk0 on returning channels.
The AK is not sent as `ClientHello.credential`, and a client-supplied handle
alone is not evidence of authentication. The implemented experimental bridge
provides trusted per-channel verification context through `ChannelIdentity`
and `ChannelPolicy`; it does not silently reinterpret the existing
opaque-credential interface. The exact experimental contract and executed tests
are recorded in the [implementation evidence ledger](../../docs/sc1-implementation.md).

`ChannelIdentity` carries mode, carrier, scope, handle, epoch and principal.
`ChannelIdentityProvider.ChannelIdentity()` returns it with a separate
fresh-confirmation boolean. `ChannelPolicy` replaces ordinary `Policy` and receives
that identity plus the explicit opaque hello credential, including empty bytes.
It requires fresh confirmed client transport and returns a nonempty principal.
The bridge does not automatically compare channel and returned principals,
independently verify trusted root identity or synchronously `Check` enrollment
before `ready`; these are explicit host-policy responsibilities. Empty
credentials never automatically authorize a channel. A nil method `Authorize`
hook denies methods, including after successful channel authentication.

Bootstrap uses completed Noise NK before enrollment authorization. A valid
reconnect establishes a fresh principal binding; it does not change an old
binding or restore a session. `hello`/`ready` and method permissions still
apply. Enrollment responses require a separate application/provisioning
contract, not an invented `ServerReady` issuance field. Only out-of-band
preprovisioning is delivered; enrollment issuance/storage transactions and
rotation flows remain absent. The current requirements below remain unchanged
until RFC acceptance, and implementation tests do not establish formal SC1
conformance or independent interoperability.

## 1. Protocol requirements

**SNTR-AUTH-001** — Mechanisms MUST be pluggable. The core defines carriage and result semantics; it MUST NOT define credential syntax, cryptography, or any private identity service. Applications register mechanisms out of band.

**SNTR-AUTH-002** — Credential transport rules: (a) initial credential bytes are profile-specific per accepted RFC 0004 §3 D5: on persistent frame-carrying profiles only in `ClientHello.credential`; on HTTP/HTTPS request-response exchanges only through `Authorization: Syntra <base64>` for that exchange, or deliberate omission for an anonymous attempt; and, if the negotiated mechanism requires follow-ups, in subsequent explicitly documented application-defined RPC payloads after ACTIVE — never in URLs, `connection_id`, `request_id`, method strings, error messages, logs, or event metadata. Base64 is a byte-preserving binding for the header channel, not a second credential format or an added confidentiality mechanism (SNTR-ASEC-003); (b) in public production, credentials MUST traverse only secure transports (charter SYN-ARCH-030/032) — profile-specific carriage never weakens that rule; (c) the core MUST treat credentials as opaque sensitive bytes on every carrier — MUST NOT log, persist, interpret, or echo them.

**SNTR-AUTH-003** — Initiation: the client presents the initial credential per SNTR-AUTH-002's profile-specific carriage. Empty credential (`len == 0`) means "unauthenticated/anonymous attempt" and is valid on the wire; whether the host accepts it is application policy. The initial credential is bounded at 8 KiB (8,192) raw credential bytes per accepted RFC 0005 §3 D2: producers check the raw-byte bound before sending; receivers bound it before allocation/dispatch and before policy lookup, enforce the same units (raw bytes, not encoded text; HTTP counts decoded bytes), and reject an oversized credential instead of silently truncating it.

**SNTR-AUTH-004** — Challenge/response (OPTIONAL): mechanisms requiring more than one round trip MUST be layered above ACTIVE as generic RPCs (e.g., `/syntra.auth/Challenge`), NOT as new `Frame` variants, unless an RFC defines a new capability. The core MUST NOT interpret challenge payloads.

**SNTR-AUTH-005** — Success semantics: on acceptance the host emits `ServerReady`, binds the connection to the resulting principal for its lifetime, and authorizes subsequent RPCs per application policy. `ServerReady` proves authentication for this connection only.

**SNTR-AUTH-006** — Rejection semantics: on denial the host MUST fail the handshake with `UNAUTHENTICATED` (credential invalid/expired) or `PERMISSION_DENIED` (valid credential, insufficient access for any operation), MUST NOT distinguish oracle-revealing sub-reasons, and MUST NOT include private diagnostics or credential material in `RpcError.message`.

**SNTR-AUTH-007** — Principal binding: every ACTIVE connection has at most one principal. The binding MUST be fixed at `ServerReady` and MUST NOT change without re-authentication (see SNTR-AUTH-010). All authorization decisions on that connection MUST use the bound principal.

**SNTR-AUTH-008** — Expiration and revocation: credentials/principals MAY expire. The host MUST enforce expiry/revocation by failing affected RPCs with `UNAUTHENTICATED` and, if the binding is withdrawn mid-connection, by closing with `UNAUTHENTICATED`. Clients MUST handle mid-connection revocation as terminal for the binding (reconnect + re-authenticate), not as a retryable RPC error.

**SNTR-AUTH-009** — Authentication failure errors: handshake-phase denials never travel as wire error `Frame`s. On denial the detecting side records the applicable local typed cause (SNTR-AUTH-006: `UNAUTHENTICATED` for credential invalid/expired; `PERMISSION_DENIED` for a valid credential with insufficient access) and terminates through the transport-native signal (TCP/TLS close, HTTP `401`/`403`, WS/WSS Close `1008`). The peer observes only that native signal and may conclude at most the generic report its profile maps it to — `UNAVAILABLE` absent better evidence for an indistinguishable TCP/TLS close, the profile's generic status/close-code category otherwise — never the precise rejection code or an authentication sub-reason (accepted [RFC 0003](../../rfcs/0003-handshake-failure-signaling.md) §3 D1). Post-ACTIVE per-RPC authorization denials use `RpcResult{error}` with `UNAUTHENTICATED`/`PERMISSION_DENIED` without tearing down the connection unless policy requires it.

**SNTR-AUTH-010** — Reauthentication policy: re-authentication on the same connection without a new handshake is FORBIDDEN unless an RFC-defined capability explicitly permits it. Default flow is: close → new transport → new `hello` with fresh credential. A second `hello` after ACTIVE is a connection state violation: local `FAILED_PRECONDITION` plus native close, without any zero-ID result (per accepted RFC 0004 §3 D5; SNTR-AUTH-007). A valid post-ACTIVE request whose handler would change the credential's bound principal MUST be rejected with `FAILED_PRECONDITION` returned under its valid, nonzero request ID, leaving the existing principal binding intact and the connection usable by default: connection loss MAY still follow as a later consequence of host policy, but it is not the protocol-mandated default for this case. That rejection does not reserve a new authentication mechanism, and explicitly documented follow-up authentication RPC payloads after ACTIVE remain subject to the owning authentication policy — they MUST NOT implicitly change the connection principal or invent mechanism negotiation. Credential expiry/revocation and binding withdrawal keep their separate owning policy (SNTR-AUTH-008).

## 1A. Authentication framework decision (v1 baseline; see `rfcs/0002-auth-session-lifecycle.md`)

v1 defines an application-neutral framework, not a credential mechanism:

- **No mechanism identifier, advertisement, selection, or challenge fields exist in the v1 IDL.** `ClientHello` carries only `{min_version, max_version, credential}` and `ServerReady` carries only `{connection_id}` (`handshake.proto`). There is no mechanism registry, no negotiation field, and no pre-`ACTIVE` challenge/response message. Any such fields would REQUIRE a capability RFC per SNTR-AUTH-004 and SNTR-CAP-001/002.
- **The v1 mandatory baseline is opaque credential presentation.** Interoperability means: the initiator transmits arbitrary credential bytes bit-preserved (SNTR-AUTH-001/002, SNTR-RPL-013 carriage rule), the host evaluates them per application policy, and both sides implement identical success/rejection/binding semantics (SNTR-AUTH-005…010). Credential formats, issuers, and cryptographic constructions are application deployments and are never negotiated by the core.
- **Challenge/response beyond one round** uses application-defined RPCs after `ACTIVE` (SNTR-AUTH-004); the core MUST NOT interpret challenge payloads. A pre-`ACTIVE` multi-round mechanism is a capability-gated extension (see core `open-questions.md` blocker 4) and MUST NOT be improvised with new `Frame` variants.
- **No mandatory login, password, token-claim, or provider-name semantics.** The empty credential is a valid anonymous attempt (SNTR-AUTH-003); whether it succeeds is host policy. Two implementations interoperate on anonymous and opaque-credential flows without sharing any user database.

Because v1 cannot yet negotiate mechanisms, deployments needing mechanism agility (e.g., selecting between two credential types on one endpoint) MUST do so above Syntra (distinct methods/endpoints chosen by the application) or propose the capability RFC tracked in `rfcs/0002-auth-session-lifecycle.md`. That RFC is a release blocker for any conformance claim requiring mechanism negotiation.

## 1B. Principal model (generic; see SNTR-AUTH-005/007, SNTR-ASEC-004)

A principal is the opaque authenticated identity bound at `ServerReady` for exactly one connection:

- A principal MAY represent a human, device, service, process, API consumer, or anonymous context where the application permits. The wire protocol MUST NOT assume a human and MUST NOT encode human-specific fields.
- **Principal identifiers are opaque host-owned values, not wire fields.** No principal identifier appears in `Frame`, `ClientHello`, or `ServerReady`. `connection_id` is a per-connection diagnostic, never a principal identifier (SNTR-SESS-002). Application-defined RPC payloads MAY carry application principal references inside opaque bytes; the core MUST NOT interpret them.
- **Visibility**: peers learn only the authorization outcome (success with `ready`, per-RPC allow/deny), never another principal's handle. Logs and diagnostics MUST redact or pseudonymize principal identifiers unless the deployment documents otherwise (SNTR-ASEC-004).
- **Authorization context**: every `ACTIVE` connection has at most one bound principal (SNTR-AUTH-007). All per-method and per-subscription authorization decisions on that connection MUST use the bound principal (SNTR-RPC-032, SNTR-ASEC-022). Cross-connection use of one connection's credential or state is forbidden (SNTR-AUTH-031, SNTR-RPL-012/020).

## 1C. Authorization boundary (Syntra identifies; the application authorizes)

| Situation | Wire behavior | Codes |
|---|---|---|
| Protected method invoked without authentication (no usable binding) | Reject before handler dispatch (SNTR-AUTH-030, SNTR-ASEC-022) | `UNAUTHENTICATED` |
| Authenticated principal lacks access for the method/subscription | Reject before handler effects (SNTR-RPC-032) | `PERMISSION_DENIED` |
| Credential/permission valid at `ready` but revoked or expired mid-connection | Fail affected RPCs; close by default (SNTR-AUTH-008/009, SNTR-ASEC-006) | `UNAUTHENTICATED` (+ close) |
| Session requires reauthentication (new credential, step-up, rotation) | Default: close; reconnect with a new handshake (SNTR-AUTH-010). Same-connection principal change is forbidden without a capability RFC: a valid request that would change the bound principal returns `FAILED_PRECONDITION` under its own nonzero request ID with the binding intact and the connection usable; a second `hello` instead closes the connection (SNTR-AUTH-007/010, accepted RFC 0004 §3 D5) | `FAILED_PRECONDITION` for the forbidden principal-change request; `UNAUTHENTICATED` for the reauth/close path, then new `hello` on a new connection |

Role names, permission sets, and policy languages are application-defined and MUST NOT appear in the core IDL. Error text MUST stay generic per SNTR-AUTH-006 and SNTR-ASEC-011.

## 1D. Authentication timing (no separate auth timeout)

Authentication runs inside the handshake deadline (SNTR-HS-002/011): there is no independent v1 authentication timer. Slow or stalled peers are closed per SNTR-ASEC-021 with `DEADLINE_EXCEEDED`/`UNAVAILABLE`. Per-RPC authorization after `ACTIVE` is bounded by the RPC deadline (SNTR-RPC-004, SNTR-REL-006).

## 2. Client behavior

- **SNTR-AUTH-020** — The client MUST obtain credentials out of band, MUST send them only over permitted transports, MUST NOT cache them in logs/diagnostics, and MUST discard handshake state on rejection before retrying (with backoff, never with automatic downgrade).
- **SNTR-AUTH-021** — The client MUST NOT assume a principal type (user/service/device) and MUST treat `UNAUTHENTICATED` as "present different credential" and `PERMISSION_DENIED` as "credential valid, access refused — do not retry identically".

## 3. Server behavior

- **SNTR-AUTH-030** — The server MUST validate shape/bounds before policy lookup (including the initial 8 KiB raw-credential ceiling per SNTR-AUTH-003 and accepted RFC 0005 §3 D2), MUST evaluate credentials in constant-time comparison where applicable, MUST rate-limit authentication attempts, and MUST NOT grant protected operations before success (SYN-ARCH-033).
- **SNTR-AUTH-031** — The server MUST isolate principals: one connection's credential MUST NOT authorize another connection's RPCs, and MUST NOT leak via `connection_id` or errors.

## 4. Failure handling

Brute-force, replayed, expired, or malformed credentials → `UNAUTHENTICATED` (+ close in handshake, per-RPC error after). Valid-but-unauthorized → `PERMISSION_DENIED`. Repeated failures MUST trigger backoff/rate-limit (`RESOURCE_EXHAUSTED` or close) per `reliability.md`.

## 5. Security considerations

Credentials are the highest-sensitivity bytes in Syntra. Secure-transport enforcement, no-logging, bounded retries, and oracle-free errors are security boundaries. Custom cryptographic mechanisms are forbidden (SYN-ARCH-031); applications MUST use established libraries above Syntra. See `reliability.md` for DoS handling.

## 6. Compatibility considerations

New mechanisms are application deployments, not protocol versions. Core changes (e.g., new auth-related `Frame` variant or re-auth capability) REQUIRE an RFC and capability negotiation per `capabilities.md`.

## 7. Conformance requirements

- **SNTR-AUTH-900** — Fixtures: empty credential accepted/rejected per policy; invalid → `UNAUTHENTICATED`; unauthorized → `PERMISSION_DENIED`; expired mid-connection → per-RPC `UNAUTHENTICATED`; re-auth on same connection rejected; credential never appears in logs/errors/diagnostics (negative grep).
- **SNTR-AUTH-901** — Pluggability proof: two different opaque credential values (e.g., 32-byte random A vs B) MUST both traverse the core bit-preserved without core interpretation.

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  C->>H: Frame{hello{credential=opaque}}
  H->>H: shape check + policy eval
  alt accept
    H-->>C: Frame{ready} (principal bound)
  else reject
    H->>H: record local typed cause (UNAUTHENTICATED or PERMISSION_DENIED)
    H-->>C: transport-native signal only (TCP/TLS close, HTTP 401/403, WS/WSS Close 1008); no error Frame
    C->>C: generic local report per profile (UNAVAILABLE absent better evidence); precise cause not claimed
  end
```
