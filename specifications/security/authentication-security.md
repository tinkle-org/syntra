# Syntra v1 Security — Authentication Security

- Identifier: `specifications/security/authentication-security.md`
- Title: Credential, Session, and Token Security
- Status: Partially accepted (2026-10-30) — carriage rules (`SNTR-ASEC-003`, accepted [RFC 0004](../../rfcs/0004-correlation-identity-carriage.md) D5) and handshake-failure close semantics (accepted [RFC 0003](../../rfcs/0003-handshake-failure-signaling.md)) per [Decision 0002](../../docs/decisions/0002-sdd-acceptance-wave.md); remaining lifetime/disclosure sections remain Draft pending their own acceptance decision
- Version: 1.0.0-draft.1 (2026-10-26)
- Normative references:
  - BCP 14; `threat-model.md` (T1, T3, T5, T8, T9); `transport-security.md`; `replay-protection.md`; `opaque-payloads.md`
  - `specifications/core/authentication.md` (SNTR-AUTH-*, framework/principal/authorization in §1A–§1D), `sessions.md` (three concepts, resumption, cross-transport, HTTP, termination, timeouts in §1A–§1G), `handshake.md` (lifecycle table, ordering, diagrams in §1A–§1B/§2A), `errors.md`, `reliability.md`
  - `proto/syntra/v1/handshake.proto` (`ClientHello`, `ServerReady`)
- Scope: Security rules for credential carriage, principal handling, expiry/revocation, resume-token design, rotation, fixation defenses, and error disclosure. Credential formats and identity stores belong to the application; this document defines only channel, lifetime, and disclosure rules and is generic across user, service, device, or key-based principals.
- Terminology: Per `core/protocol.md`. **Principal** = opaque authenticated identity (never assumed to be a user account). **Resume token** = optional opaque token enabling resumption ONLY if a capability RFC defines it (default: no resumption in v1).

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 1. Protocol requirements

**SNTR-ASEC-001** — Credential confidentiality: credentials MUST be treated as sensitive key material. The core and adapters MUST NOT log, persist, cache beyond the handshake, echo in errors, or expose them in diagnostics, metrics labels, or traces. Memory handling SHOULD minimize retention (overwrite or release promptly where the language permits).

**SNTR-ASEC-002** — Channel binding: credentials MUST traverse only secure profiles in public deployments (see `transport-security.md` SNTR-TSEC-009) or loopback-restricted plaintext for development. If a negotiated channel-binding mechanism is defined by a future RFC (e.g., TLS exporter binding), its use MUST be explicit and versioned; absent such an RFC, implementations MUST NOT claim channel binding and MUST NOT improvise binding by mixing transport bytes into credential comparison.

**SNTR-ASEC-003** — Carriage (per accepted RFC 0004 §3 D5): initial credential bytes appear ONLY in `ClientHello.credential` on persistent frame-carrying profiles — where WS/WSS Upgrade `Authorization`/`Cookie` headers, when used for documented transport admission, do not establish or merge Syntra identity — and ONLY through `Authorization: Syntra <base64>` for that exchange on HTTP/HTTPS request-response profiles (or by deliberate omission for an anonymous attempt). Base64 is a byte-preserving binding for the header channel, not a second credential format or an added confidentiality mechanism; the header channel carries the same opaque sensitive bytes under the same obligations as `ClientHello.credential` (SNTR-ASEC-001). Explicitly documented follow-up authentication RPC payloads after `ACTIVE` remain subject to the owning authentication policy and do not implicitly authorize changing the connection principal or inventing mechanism negotiation (SNTR-AUTH-010). Credentials MUST NOT appear in URLs (no query-string, path, or fragment carriage), environment variables, logs, diagnostics, metrics labels, traces, `connection_id`, `request_id`, method strings, error messages, or event payloads as protocol metadata. Public deployments still require a permitted secure profile (charter SYN-ARCH-030; SNTR-ASEC-002). This rule holds even if the application encodes its own references inside opaque payloads — the Syntra layer MUST NOT require URL carriage.

**SNTR-ASEC-004** — Principal identity handling: principals MUST be opaque handles bound at `ServerReady` for exactly one connection (see `core/authentication.md` SNTR-AUTH-007). Implementations MUST NOT assume user accounts; authorization policy MUST treat service/device/key/anonymous principals uniformly through the same hooks. Principal identifiers in logs MUST be redacted or pseudonymized unless the deployment documents otherwise.

**SNTR-ASEC-005** — Credential expiration: every credential type MUST have a bounded lifetime documented by the application. Hosts MUST enforce expiry (handshake denial with `UNAUTHENTICATED` or per-RPC `UNAUTHENTICATED` after ACTIVE) and MUST NOT accept indefinitely valid credentials in public deployments except for explicitly documented long-lived service credentials with rotation procedures.

**SNTR-ASEC-006** — Session revocation: hosts MUST be able to revoke a principal binding and any issued resume/session tokens promptly. On revocation, in-flight RPCs for the binding MUST fail with `UNAUTHENTICATED` and the connection MUST close unless the deployment documents per-RPC survival (default: close). Maximum revocation-propagation delay MUST be documented (see residual risk in `threat-model.md`).

**SNTR-ASEC-007** — Resume token design requirements (only applicable if a resumption capability RFC exists; otherwise resumption MUST be refused per `core/sessions.md` SNTR-SESS-006): tokens MUST be unguessable (≥128-bit entropy), single-purpose (resumption only, never authentication-by-itself unless the RFC explicitly defines the derivation), audience- and principal-bound, time-boxed, revocable, and integrity-protected by the issuer. Tokens MUST NOT encode privileges beyond a reference; privilege state MUST be re-evaluated at resumption.

**SNTR-ASEC-008** — Token rotation policy: on every successful resumption (if defined), hosts SHOULD rotate the token (issue a fresh token, invalidate the presented one) to bound replay windows. Reuse of a rotated token MUST be treated as suspected replay per `replay-protection.md`.

**SNTR-ASEC-009** — Replay protection for authentication: credentials and resume tokens MUST be replay-resistant per `replay-protection.md` (per-class defenses; TLS alone is insufficient). In particular, capture-and-retransmit of a `hello` or token MUST NOT yield a new authenticated session without freshness/validity checks defined by the mechanism.

**SNTR-ASEC-010** — Session fixation defenses: `connection_id` MUST be freshly generated per connection (≥128-bit entropy), MUST NOT be accepted as input, MUST NOT be predictable from prior connections, and MUST NOT grant any privilege. Hosts MUST NOT allow a peer to select or fixate session state (no client-chosen session IDs in v1 core).

**SNTR-ASEC-011** — Authentication error disclosure: handshake denials MUST use `UNAUTHENTICATED` (credential invalid/expired/revoked) or `PERMISSION_DENIED` (valid credential, insufficient access) without distinguishing sub-reasons (unknown principal vs wrong secret vs expired vs revoked) unless the deployment documents the oracle as intentional. `RpcError.message` MUST be generic and MUST NOT contain credential material, token values, principal enumerations, or backend diagnostics. Timing behavior SHOULD minimize user-enumeration oracles (constant-time credential comparison where applicable).

### Proposed persistent authorization interaction (informative)

[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md) separates
[channel verification](secure-channel.md) from [enrollment and authorization](device-authorization.md).
The selected bootstrap is `Noise_NK_25519_ChaChaPoly_SHA256`, followed by
application-authorized enrollment: the host issues a unique random 32-byte
shared AK through the protected provisioning contract. Returning devices use
`Noise_NKpsk0_25519_ChaChaPoly_SHA256`; the AK enters standard `psk0` and is
not sent as a reconnect bearer credential. No device signing key pair is
selected. Principals remain generic devices, services or other identities,
without a human-account requirement.

The proposed independent eight-byte `auth_id` is a collision-checked scoped
lookup handle, not authority, a session ID, or proof of freshness. Clear stable
handles can correlate reconnects; bounded lookups, oracle-resistant failures,
restricted diagnostics and rotation privacy need review. Hosts would store
usable AKs under controlled wrapping, with expiry, revocation and rotation
policies; a one-way hash alone cannot supply a Noise PSK. This host-owned
store does not authorize credential persistence in the core or adapters.

Fresh client transport-record confirmation, current enrollment validity and
principal policy must precede `ready` under the proposal, with per-method
authorization still required. Persisting an AK does not resume a logical session
or preserve old traffic keys. The implemented experimental bridge provides
`ChannelIdentity` (mode, carrier, scope, handle, epoch and principal), a provider
returning a separate fresh-confirmation boolean, and `ChannelPolicy`, which
replaces ordinary `Policy` and receives the
explicit opaque hello credential, including empty bytes. It requires fresh
confirmed client transport and a nonempty returned principal. Replayed M1 is
not confirmation; the first valid client record, normally encrypted hello, is.

The bridge does not automatically compare channel and returned principals,
independently verify trusted root identity or synchronously `Check` enrollment
before `ready`; these are explicit host-policy duties. Empty credentials never
automatically authorize access; a nil method `Authorize` hook denies methods.
Host-owned lookup receives the full context and validates returned key,
principal, expiry and revoked state. Keys are immutable within a handle/epoch;
later `Check` evaluates validity and principal, not key equality.

The watchdog begins at first confirmation and runs on a 1-second tick with
1-second lookup contexts, including idle channels. This is not an exact
1-second revocation SLA. Principal disconnect closes current connections, not
future admission. Bounded close depends on cancellation-compliant I/O/store
callbacks and cannot forcibly terminate them. The
[implementation evidence ledger](../../docs/sc1-implementation.md) documents
the authentication boundary, actual-send drain, writer/operational budgets,
executed tests and remaining gaps.

Only out-of-band preprovisioning is delivered. Enrollment issuance, protected
storage/transactions and rotation flows remain absent; independent vectors,
interoperability and security review remain open. `ClientHello.credential`
stays opaque and `connection_id` diagnostic. The codec's 8 KiB pre-allocation
credential gate, depth-32/full validation and reserved-16/17 rejection in both
directions do not close the native-ABI completion-timestamp and post-hello
credential-release gaps. These proposed SC/DAUTH requirements do not amend the
current ASEC carriage, TLS or lifecycle rules before RFC acceptance.

## 2. Request-security hooks (per-connection/session limits)

**SNTR-ASEC-020** — Hosts MUST enforce, per connection AND per session/principal: maximum envelope size (default 1 MiB per `framing.md`), maximum concurrent RPCs, maximum handshake attempts per unit time, maximum subscriptions/events per principal, and call deadlines. Limits MUST be documented; exceeding them MUST yield `RESOURCE_EXHAUSTED` (RPC context) or handshake/connection closure, and MUST trigger rate-limiting or temporary blocking of the offending source before affecting conformant principals (see `reliability.md`).

**SNTR-ASEC-021** — Slow-client protection: hosts MUST bound time-to-first-`hello`, inter-frame gaps during handshake, and per-RPC payload delivery windows; stalled peers MUST be closed with `DEADLINE_EXCEEDED`/`UNAVAILABLE`, not retained indefinitely.

**SNTR-ASEC-022** — Rate-limiting and authorization hooks: the core MUST expose (or document as application-implemented) hooks for per-principal rate limiting and per-method/subscription authorization evaluated AFTER authentication and BEFORE handler dispatch. Bypassing either hook MUST be treated as a security failure, not a functional bug.

**SNTR-ASEC-023** — Malformed input handling: shape/size/depth failures MUST map to `INVALID_ARGUMENT`/`RESOURCE_EXHAUSTED`/`FAILED_PRECONDITION` per `errors.md` without handler invocation and without sensitive disclosure.

**SNTR-ASEC-024** — Safe error messages: all authentication/session/token failures MUST use the disclosure rules in SNTR-ASEC-011; operational detail (attempt counts, backend identifiers) MUST go to privileged server-side diagnostics only, never to the peer.

## 3. Client behavior

- **SNTR-ASEC-030** — Initiators MUST store credentials securely (per application guidance), MUST NOT place them in URLs, logs, or error reports, MUST discard handshake state on rejection, and MUST NOT retry identical credentials in a tight loop (bounded backoff REQUIRED).
- **SNTR-ASEC-031** — Initiators MUST treat `UNAUTHENTICATED` as “present different/fresh credential” and `PERMISSION_DENIED` as “do not retry identically; seek authorization change”.

## 4. Server behavior

- **SNTR-ASEC-040** — Hosts MUST validate shape/bounds before policy lookup, compare secrets in constant time where applicable, rate-limit authentication attempts per source AND per principal, and isolate principals (no cross-principal credential/state use).
- **SNTR-ASEC-041** — Hosts MUST re-check expiry/revocation on each RPC and subscription action where staleness would grant unauthorized access, within the documented propagation window.

## 5. Failure handling

Expired → `UNAUTHENTICATED`; revoked → `UNAUTHENTICATED` + close (default); unauthorized → `PERMISSION_DENIED`; fixation/resumption abuse → `FAILED_PRECONDITION` or `UNAUTHENTICATED` + close; overload → `RESOURCE_EXHAUSTED`. Repeated failures trigger backoff/blocks.

## 6. Security considerations

This document's rules are the application-independence guarantee: no user-account assumption, no private identity service, no URL credentials. Channel binding is explicitly unclaimed until an RFC defines it — claiming it without a specified mechanism is non-conformant.

## 7. Compatibility considerations

New credential types are application deployments (no protocol change). New token, rotation, or binding mechanisms REQUIRE capability RFCs. Tightening disclosure or lifetime rules is a minor clarification; relaxing them is major.

## 8. Conformance requirements

- **SNTR-ASEC-900** — Fixtures: expired/revoked/invalid credentials; unauthorized-but-authenticated; fixation (`connection_id` replay/client-chosen); URL-carriage absence (negative grep of implementation + wire traces); error-message hygiene; revocation mid-connection; rate-limit behavior; slow-client closure.
- **SNTR-ASEC-901** — Generic-principal proof: same rules demonstrated with non-user principals (e.g., service key + device token fixtures using neutral opaque bytes).

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  C->>H: hello{credential} (secure channel only)
  H->>H: shape/bounds → policy → expiry/revocation
  alt valid
    H-->>C: ready (principal bound, fresh connection_id)
  else expired/revoked/invalid
    H->>H: local typed cause UNAUTHENTICATED
    H-xC: native close signal only (WS/WSS Close 1008; TCP/TLS close)
  else valid but unauthorized
    H->>H: local typed cause PERMISSION_DENIED
    H-xC: native close signal only (per profile)
  end
```

Per accepted RFC 0003, handshake failures never travel as wire error
frames: the detecting side records the locally typed cause; the peer
observes only the transport-native close signal and may conclude at most
the generic per-profile failure report.
