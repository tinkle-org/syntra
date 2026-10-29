# Syntra Secure Channel v1 — Persistent device authorization

- Status: Accepted (2026-10-29) — RFC 0007; normative for `SNTR-SC1-WSS-V1`
- Date: 2026-10-29
- Owner: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Scope: Per-device shared authorization secrets and host-owned lifecycle
- Requirements: `SNTR-DAUTH-001`–`SNTR-DAUTH-010`

BCP 14 keywords below are normative for the accepted profile. They do not
replace the generic [authentication interface](../core/authentication.md) or
weaken the [credential-security baseline](authentication-security.md).
The [shared channel](secure-channel.md) defines encryption and confirmation;
applications own enrollment authority, identity stores and permissions.
[noise-bindings.md](../transports/noise-bindings.md) owns the accepted v1
handle/epoch context bytes and first-envelope admission.

Enrollment issuance, durable provisioning/storage transactions, rotation flows
and revocation propagation remain host implementation obligations; supporting
NK bootstrap does not implement authorized enrollment. The Rust implementation
records preprovisioned-AK and local lifecycle tests as implementation evidence,
not conformance or independent security review. An enrolled principal can be a
device, service or other generic identity; there is no required human-account
model.

## 1. Authorization material

**SNTR-DAUTH-001** — Each enrollment MUST have a unique, uniformly random
32-byte AK with 256 bits of entropy. Generation MUST use a cryptographically
secure source and fail closed on failure. AK is a shared authorization secret,
not an asymmetric signing key, password-derived value or traffic key. Both
roles MUST scope it to its intended device enrollment and Noise/hash context;
it MUST NOT be reused for unrelated application encryption or authentication.
The AK MUST be supplied through standard Noise `psk0`, never transmitted
as a returning-device bearer credential.

**SNTR-DAUTH-002** — Enrollment MUST occur only after a completed,
server-authenticated bootstrap channel and successful application-defined
enrollment authorization, or through equivalently authenticated out-of-band
provisioning. Merely presenting a new key MUST NOT grant protected access.
The provisioning contract MUST specify the authorized generator, secure
transfer, durable commit, acknowledgment, retry/idempotency and interrupted
enrollment behavior before implementation. The recommended bootstrap flow
uses a host-generated AK protected in transit to the device; client-generated
provisioning is not implicitly enabled by this profile.

**SNTR-DAUTH-003** — The `auth_id` MUST be an independent random eight-byte
lookup handle with collision checks in its store scope. It MUST NOT derive
authority from secrecy or substitute for PSK proof, principal authorization or
a session identifier. Both peers MUST bind handle, epoch and endpoint scope into
the authenticated context. The canonical v1 encoding is defined in
[noise-bindings.md](../transports/noise-bindings.md) §2: bootstrap has zero
epoch/handle and no AK; returning mode has nonzero epoch, nonzero handle and a
nonzero 32-byte AK. Rotation selection and lifecycle remain host obligations;
encoding those fields does not implement rotation. Deployments MUST account for
clear stable handles enabling correlation and MUST NOT expose them as public
device identities or unrestricted log/metric labels.

## 2. Storage and principal binding

**SNTR-DAUTH-004** — Devices MUST retain AKs in platform-appropriate secure
storage; hosts MUST restrict access to usable AKs and protect persisted values
with controlled wrapping/encryption keys. A one-way hash alone is insufficient
for a Noise PSK lookup. The core/adapters MUST NOT persist AKs, log/debug-print
them, include them in diagnostics, or expose raw channel keys. Storage and
unwrapping interfaces belong to the embedding host, not the protocol core.
Compromise of usable AKs MUST be treated as device-impersonation risk.

**SNTR-DAUTH-005** — The host MUST bind an enrollment record to a generic
principal, device reference, intended endpoint/audience, credential epoch,
validity and revocation state. A successful PSK handshake MUST NOT grant
unlimited RPC permission. The host MUST evaluate current authorization before
`ready` and per protected method/subscription; the channel's principal MUST
remain fixed under the existing core rules. Neither an `auth_id` nor a
diagnostic `connection_id` authorizes operations.

An illustrative host record is `{handle, wrapped_AK, principal_ref,
device_ref, scope, epoch, validity, revoked}`. This is storage guidance, not
a mandatory database schema or new Protobuf message. The host passes only
the minimum trusted context required for authentication/policy; application
payloads and identity-store structure remain outside core interpretation.

Implemented lookup is host-owned and receives the full channel context; returned
key, principal, expiry and revoked state are validated. Preprovisioned keys are
immutable within a handle/epoch. Subsequent `Check` evaluates validity and
principal, not key equality; changing key material in place is not a rotation
mechanism. This lookup surface is not a delivered protected-storage backend.

## 3. Expiration, revocation, and rotation

**SNTR-DAUTH-006** — Applications MUST define bounded credential validity,
revocation-propagation delay and any renewal policy. Hosts MUST reject expired
or revoked enrollment records during reconnect and withdraw active principal
bindings within the documented bound, closing affected channels by default.
Clients MUST treat loss/rejection of authorization as requiring explicit
recovery or enrollment, not automatic downgrade or continued use of cached
permissions. Persistent authorization means no repeated interactive login
while valid, not perpetual authorization.

The implemented watchdog begins after first client-record confirmation and uses
a 1-second tick with 1-second lookup contexts, including idle channels. These
intervals are not an exact 1-second revocation SLA, nor a synchronous pre-ready
validity check. A host requiring current enrollment before `ready` must enforce
it in policy. Principal disconnect closes current connections; it does not deny
future admission. Both watchdog failure and principal disconnect close directly.
Only method authorization returning `UNAUTHENTICATED` attempts a bounded
actual-send denial drain. That path and callback-cancellation limits are
documented in the evidence ledger.

**SNTR-DAUTH-007** — A rotation mechanism MUST define fresh AK/handle
issuance, epoch selection, bounded old/new overlap, durable state changes,
concurrent reconnects, acknowledgment/commit rules and crash recovery. Peers
MUST NOT retire the only usable credential before the recovery contract
permits it, accept old credentials beyond overlap, roll back a revoked epoch,
or derive a replacement only from a compromised secret while claiming
compromise recovery. Lost-device recovery and server static-key rotation
MUST be independently specified. The exact control RPC/storage transaction
contract is a blocker; opportunistic rotation is not an implemented feature.

**SNTR-DAUTH-008** — Hosts MUST bound handle parsing and credential-store
lookup work before expensive processing, rate-limit attempts and avoid
revealing unknown, revoked, expired or wrong-secret distinctions through
public errors or avoidable timing differences. A replayable valid first
flight MUST NOT update last-authenticated-device state or grant effects
before fresh client confirmation. Unknown handles MUST NOT create durable
enrollments. PSK/state and lookup metadata MUST be released on failure;
negative caching and transient attempt state MUST remain bounded.

## 4. Carrier and core integration

**SNTR-DAUTH-009** — A valid enrollment MAY authorize multiple explicitly
permitted carriers for the same service scope, but each new channel MUST
perform a fresh handshake with its carrier binding authenticated. Neither
peer may migrate traffic keys, counters, record replay state or principal
bindings from another channel. This MUST NOT imply logical-session
resumption, restored subscriptions or automatic replay of previous RPCs.
Applications MUST re-evaluate scope/policy for the chosen endpoint/carrier.

**SNTR-DAUTH-010** — Integration MUST preserve opaque
`ClientHello.credential` carriage and existing `ServerReady` semantics.
Implementations MUST NOT place AKs, handles or enrollment results in
`connection_id`, invent an issuance field, or infer authenticated device
context from client-provided metadata alone. Host authentication MUST receive
trusted, connection-scoped channel verification context. The accepted API
below specifies that integration; independent human security review remains a
release gate and is not supplied by the API or its tests. An enrollment
RPC contract remains absent; new wire fields require the schema RFC/generation
workflow. No credential-issuance or full binding conformance claim is established
by the API or its tests.

`ChannelIdentity` contains mode, carrier, scope, handle, epoch and principal.
`ChannelIdentityProvider.ChannelIdentity()` returns that value and a separate
fresh-confirmation boolean. `ChannelPolicy` replaces ordinary `Policy`, requires
fresh confirmed client transport and receives the explicit opaque hello
credential, including an empty value. It returns a nonempty principal. Only the
first valid client transport record provides confirmation; encrypted hello
normally does so, while replayed M1 does not. A completed NKpsk0 handshake or
empty credential never automatically authorizes an anonymous or enrolled binding.

The bridge does not automatically compare the identity principal with the policy
result, independently verify trusted root identity, or synchronously `Check`
enrollment before `ready`. Those are explicit host-policy responsibilities;
nil method `Authorize` denies methods. Ordinary opaque-credential mechanisms
retain their meaning. No handshake capability or new field is implicitly
negotiated by this profile.

## 5. Security and acceptance

The AK is not sent on reconnect, but both device and authorized host processes
need access to its value. Usable-store compromise allows affected-device
impersonation; encryption at rest does not protect against all process-level
compromises. High entropy is essential, including when a later compromise
permits offline checking of candidate secrets. Past-channel confidentiality
claims depend on fresh secret ephemerals and their disposal, not merely AK
storage or rotation.

The [acceptance plan](../../conformance/plans/secure-channel.md) covers
enrollment authorization, no secret leakage, handle collision/correlation,
lookup failures, expiry, active-binding revocation, rotation overlap/crashes,
cross-carrier separation and trusted authentication integration. The evidence
ledger separately records executed local and same-implementation integration
tests with their limited scope. Enrollment and rotation execution, independent
vectors/interoperability, deployment certification and independent security
review are not established by those results. No formal SC1 `CONF-*` cases or
profiles are registered.
