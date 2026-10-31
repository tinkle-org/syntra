# Syntra Secure Channel v1 — Persistent device authorization

- Status: Accepted (2026-10-29) — RFC 0007; normative for `SNTR-SC1-WSS-V1`
- Date: 2026-10-29
- Owner: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Companion owner: [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md)
  — host enrollment and authorization lifecycle, requirements
  `SNTR-DAUTH-011`–`SNTR-DAUTH-024` (§5)
- Scope: Per-device shared authorization secrets and host-owned lifecycle
- Requirements: `SNTR-DAUTH-001`–`SNTR-DAUTH-010` (RFC 0007);
  `SNTR-DAUTH-011`–`SNTR-DAUTH-024` (RFC 0010 lifecycle contract)

BCP 14 keywords below are normative for the accepted profile. They do not
replace the generic [authentication interface](../core/authentication.md) or
weaken the [credential-security baseline](authentication-security.md).
The [shared channel](secure-channel.md) defines encryption and confirmation;
applications own enrollment authority, identity stores and permissions.
[noise-bindings.md](../transports/noise-bindings.md) owns the accepted v1
handle/epoch context bytes and first-envelope admission.
[RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md) makes the
lifecycle obligations of these accepted contracts operationally precise in §5
without changing any accepted wire behavior.

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

## 5. Host enrollment and authorization lifecycle (RFC 0010)

The requirements in this section are owned by
[RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md), the
operational companion contract to the accepted RFC 0007. They make the host
obligations of RFC 0007 §11.2 operationally precise without changing any
accepted wire behavior; `SNTR-DAUTH-001`–`SNTR-DAUTH-010`, §1–§4 and their
meaning are untouched. BCP 14 keywords below carry normative force for this
companion contract upon RFC 0010 acceptance. The conformance evidence for
this section lives in the planned lifecycle cases
(`PLAN-DAUTH-011`–`PLAN-DAUTH-024`) and the transaction fault matrices and
revocation time-budget checks of the
[acceptance plan](../../conformance/plans/secure-channel.md) §§7–8; none of
it is executed by this document.

### 5.1 Enrollment authority

Device obligations: use only the deployment-designated authority paths;
discard partial enrollment state on denial. Host obligations: validate
authority, principal and scope before anything is issued or recorded; denied
attempts leave no material.

**SNTR-DAUTH-011** — Enrollment authority. The host MUST validate enrollment
authority before issuing, staging or attempting to deliver any device
authorization material. Enrollment MUST occur only through (a) a completed,
server-authenticated SC1 bootstrap channel whose application enrollment
authority explicitly approves the operation, or (b) an equivalently
authenticated out-of-band provisioning authority; the deployment MUST
designate those authority paths, and a completed bootstrap exchange, anonymous
access, possession of an enrollment packet or possession of an AK candidate
MUST NOT imply enrollment permission by themselves (per RFC 0007 §3). Every
issuance MUST be validated against the authenticated enroller identity, the
target principal and the intended scope (endpoint/audience and service scope),
and the host SHOULD record the validated decision with a bounded audit trail.
An enrollment attempt whose enroller is unauthenticated, anonymous or
otherwise unauthorized for the requested principal and scope MUST be denied
before any material is issued or durably recorded. The device MUST use only
the deployment-designated authority paths and MUST discard partial enrollment
state when the authority denies the attempt; a denied attempt MUST NOT leave
the device in a state that later authenticates.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-011` exercises
unauthorized, anonymous and cross-principal enrollment attempts and observes
denial before any material issuance, zero durable records and zero protected
effects.

### 5.2 AK issuance

Host obligations: host-generated 256-bit AK; independent eight-byte handle
with collision checks; no duplicate issuance; immutable handle/epoch scope.
Device obligations: none beyond safe storage (existing `SNTR-DAUTH-004`).

**SNTR-DAUTH-012** — Host issuance of AK and handle. The host MUST generate
the AK itself as a 256-bit uniformly random value from a cryptographically
secure source; randomness failure MUST fail closed and MUST NOT fall back to
a weaker or deterministic source. An issuance candidate that is all-zero or
otherwise degenerate MUST be treated as generation failure and MUST NOT be
staged. The public handle MUST be an independent, uniformly random eight-byte
value — not derived from the AK, principal, epoch or scope values — with a
collision check against records in its store scope before staging; a collision
MUST be resolved through the documented bounded conflict procedure (reject the
attempt or redraw the handle) and MUST NOT overwrite or attach to another
principal's record. The host MUST refuse issuance that would duplicate or
overlap a live (handle, epoch) authorization tuple, whether from a retried
request or concurrent attempts. Issued AK, principal and scope MUST be
immutable within their (handle, epoch) scope as required by RFC 0007 §11.2;
any change requires a fresh issuance tuple with a new handle and epoch.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-012` injects entropy-
source failure (abort before any staged record), drives all-zero AK candidates,
forced handle collisions and duplicate or concurrent issuance attempts, and
observes refusal without overwriting records, adopting another principal's
identity, minting a second authorization for the same tuple or substituting
key material after issuance.

### 5.3 Durable provisioning

Device obligations: persist before acknowledging; never claim an
acknowledgment for unpersisted material. Host obligations: staged transaction
with a defined ordering; bounded activation timeout; idempotent retries;
loss-tolerant reconciliation; bounded cleanup.

**SNTR-DAUTH-013** — Staged provisioning transaction. The host MUST deliver
issued material through an explicitly staged transaction with the ordering
stage → encrypted delivery → device secure-storage persistence and
acknowledgment → durable host commit, where durable commit is the only step
after which the enrollment authorizes. Before commit, the staged record MUST
NOT satisfy returning-device validation, MUST NOT present a valid enrollment
to admission checks and MUST NOT authorize any protected effect. Delivery MUST
protect the AK end to end to the device and MUST NOT carry AK material through
any unverified channel, URL, diagnostic path or error/echo path. The device
MUST acknowledge only after its designated secure storage has durably
persisted the material (per `SNTR-DAUTH-004`), and a partially staged or
undelivered device state MUST NOT be treated by either peer as an authorized
enrollment. The host MUST bound every transaction with a documented
activation timeout that expires never-committed attempts through bounded
cleanup (`SNTR-DAUTH-014`).

Acceptance evidence (planned, not executed): `PLAN-DAUTH-013` drives each
transaction step and observes authorization materialize only after commit; an
uncommitted staged record cannot authenticate and never presents a valid
enrollment to admission.

**SNTR-DAUTH-014** — Idempotent retries and interrupted enrollment. The staged
transaction MUST be idempotent against retries: redelivery or re-issuance
keyed to the same attempt completes or recognizes the same record without
issuing a second AK or duplicating authorization. A lost device
acknowledgment, a lost delivery response or a lost commit outcome MUST
reconcile to at most one authorized enrollment without recreating, duplicating
or extending the transaction. A crash at any step MUST leave either a
completable staged transaction or a cleanly failed transaction with no
authorized state, no permanent inconsistency and no resurrection of an expired
or aborted attempt. Timeout cleanup MUST be bounded and MUST release staged
state so a later legitimate attempt re-provisions from scratch rather than
resuming the expired transaction's material.

Acceptance evidence (planned, not executed): the transaction fault matrix
(`PLAN-DAUTH-014`, §8.1 of the acceptance plan) crashes after each commit
boundary and withholds or duplicates each response and acknowledgment; the
observed outcome is never an unauthorized active enrollment, a double-issued
AK or a permanently inconsistent store.

### 5.4 Principal binding and the pre-`ready` sequence

Device obligations: no protected work before `ready`; connection
authorization state is fixed for the connection. Host obligations: the
accepted order below; binding of verified channel identity to the current
enrollment, trusted identity, endpoint scope and principal before `ready`.

**Decided operating sequence.** The accepted operational sequence, encoding
RFC 0007 §11.2, preserved verbatim as the operating sequence of this contract
(`SNTR-DAUTH-015` assigns the keyword force), is:

> Verified WSS + Noise handshake → fresh client confirmation + encrypted
> ClientHello → validate current enrollment, trusted identity, and
> same-principal policy → ServerReady → authorized RPC dispatch. A valid AK
> handshake authenticates possession of the enrolled secret. It does NOT
> automatically authorize every method, and it never lets an unverified
> ClientHello identity override the enrollment's principal. Any
> credential-less returning-device policy must be explicitly authenticated
> under accepted host policy rules.

**SNTR-DAUTH-015** — Protected pre-`ready` authorization sequence. For every
new SC1 connection the accepted operational sequence is: verified WSS + Noise
handshake → fresh client confirmation + encrypted ClientHello → validate
current enrollment, trusted identity and same-principal policy → `ServerReady`
→ authorized RPC dispatch; this order encodes RFC 0007 §11.2 and is normative
here. The host MUST validate the current enrollment, a trusted application
identity and the same-principal policy before sending `ServerReady` and MUST
NOT dispatch a protected operation that skipped, reordered or predicated on an
unconfirmed step. A valid AK handshake authenticates possession of the
enrolled secret only; it MUST NOT be interpreted as blanket method
authorization, and an unverified `ClientHello` identity candidate MUST NOT
override the enrollment's principal binding in policy evaluation. Any
credential-less returning-device policy MUST be explicitly authenticated
under the accepted host-policy rules before it can bind a principal. The
device MUST NOT send protected RPCs before `ready` and MUST treat the
connection's authorization state as fixed for that connection.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-015` drives each
out-of-order and omitted-step variant — replayed first flight offered as
confirmation, missing confirmation, stale or missing enrollment record,
unverified identity claim, pre-`ready` protected request — and observes no
`ServerReady` principal, no dispatch and no queued early effects.

**SNTR-DAUTH-016** — Enrollment-to-principal binding before `ready`. Before
answering `ready` for a returning device, the host MUST bind the verified
channel identity to (a) the current enrollment record — valid, unexpired and
non-revoked, matching the handle and epoch bound in the authenticated channel
context; (b) an independently verified trusted application identity; (c) the
intended endpoint/audience scope; and (d) the enrollment's principal binding.
The connection principal MUST equal the enrollment's principal under the
verified application identity: returning with application principal B against
an enrollment whose principal is A (or vice versa) MUST fail authorization
before `ready` with no privilege union, no remapping and no protected effect.
The binding MUST remain fixed for the connection under the core rules;
principal or scope changes require a new connection or a new enrollment,
never an in-place rebinding of a live channel.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-016` substitutes a
different verified application identity on a returning channel and observes
authorization fail before `ready` with zero protected effects, while the
correctly bound identity passes with exactly the enrollment's privileges.

### 5.5 Revocation and expiry policy

Device obligations: treat loss or rejection of authorization as requiring
explicit recovery or enrollment (existing `SNTR-DAUTH-006`); no
cached-permission continuation. Host obligations: the decided propagation
policy below, with keyword force assigned by
`SNTR-DAUTH-017`–`SNTR-DAUTH-019`.

**Decided revocation-propagation policy.** The accepted policy, recorded
verbatim here with keyword force assigned by
`SNTR-DAUTH-017`–`SNTR-DAUTH-019`, is:

- New connections: immediate enforcement — a revoked enrollment MUST NOT
  authenticate on a newly established connection.
- Existing connections: maximum 300 seconds from authoritative revocation
  commit to enforcement (hard profile maximum).
- Operational target: enforce within 60 seconds, preferably immediately
  through push invalidation.
- After the deadline: deny new protected operations and delivery; close
  affected channels.
- Revocation-store unavailable: fail closed when current validity cannot be
  established or the permitted freshness window expires.
- High-security deployments may enforce shorter bounds or zero grace; longer
  grace is NOT permitted under the default public production profile.
- Wording notes: the 300-second figure is a maximum tolerated
  stale-authorization window, not a mandatory waiting period; hosts should
  revoke immediately when possible; already-committed application effects
  cannot be retroactively undone; a nominal watchdog interval does not prove
  propagation.

**SNTR-DAUTH-017** — Immediate enforcement on new connections. A revoked or
expired enrollment MUST NOT authenticate on a newly established connection.
The host MUST consult the current enrollment record — validity, expiry and
revocation state — at admission and again before `ready` and any protected
effect; denial applies regardless of the record's earlier validity, the
handshake's cryptographic success or any cached decision. A revoked tuple,
including its epoch and handle, MUST NOT re-materialize as admissible through
replayed context flights, another carrier or stale store state.

**SNTR-DAUTH-018** — Bounded staleness on established connections. For an
already-established channel, the host MUST enforce current enrollment validity
within 300 seconds from the authoritative revocation commit to enforcement;
this is the hard profile maximum under the default public production profile,
not a mandatory waiting period. The operational target is enforcement within
60 seconds, and immediate enforcement through push invalidation is preferred.
At or after the deadline without confirmed enforcement, the host MUST deny
new protected operations on the affected channel, cut off further protected
delivery and close it; already-committed application effects are not
retroactively undone, and live executions remain accounted until stopped per
RFC 0007 §11.2. The deployment MUST document its cache-staleness,
propagation and check/close budgets so their sum fits the declared bound. A
configured watchdog or tick interval alone does not prove propagation:
acceptance evidence is observed enforcement latency. Hosts SHOULD enforce
revocation as early as their mechanisms permit, immediately where possible.
High-security deployments MAY enforce shorter bounds or zero grace; hosts
MUST NOT adopt enforcement slower than the 300-second profile maximum under
the default public production profile.

**SNTR-DAUTH-019** — Fail closed when validity cannot be established. When
current enrollment validity cannot be established — a failed or timed-out
authorization-store read, a cache beyond the deployment's declared freshness
bound, or an unresolved revocation state — the host MUST deny new admissions
and MUST NOT extend authorization on cached state past the last successful
validity check plus the deployment's declared bound. An established channel
whose binding cannot be re-validated MUST be closed no later than its last
successful check plus the declared bound, within the profile maximum of
`SNTR-DAUTH-018`. Availability MUST NOT be bought by admitting under stale or
unverifiable revocation state: store unavailability degrades availability,
never authorization integrity.

Acceptance evidence for this area (planned, not executed): `PLAN-DAUTH-017`
revokes before reconnects and observes admission denial on every carrier with
zero protected effects; `PLAN-DAUTH-018` injects clocks and store latency to
measure commit-to-enforcement latency against the hard maximum and the
operational target and observes post-deadline denial, delivery cutoff and
closure; `PLAN-DAUTH-019` forces store failure and stale-cache profiles and
observes fail-closed denial and bounded closure with no stale-allow.

### 5.6 Rotation

Device obligations: install durably before discarding the current
credential; no acknowledgment for unpersisted material. Host obligations:
fresh AK/handle, strictly increasing epoch, bounded overlap, durable
installation before normal retirement, reconciliation and hard cutoff.

**SNTR-DAUTH-020** — Rotation transaction. Rotation MUST issue a fresh,
independent AK and handle with a strictly increasing epoch, delivered through
the staged provisioning transaction (`SNTR-DAUTH-013`) and its idempotency
rules (`SNTR-DAUTH-014`). The replacement becomes the primary
authorized credential set at durable host commit. During the deployment's
declared overlap window the replacement and the old tuple both remain
admissible: the old tuple MUST stay admissible until its declared expiry (or
the overlap cutoff, whichever comes first), except when revocation, its own
credential expiry, or compromise response invalidates it earlier; it MUST NOT
remain usable at or after that boundary. Routine retirement MUST NOT discard
the only still-authorized usable credential until the replacement is durably
installed. Revocation, credential
expiry, compromise response and the hard overlap cutoff MUST NOT wait for
installation or acknowledgment: they can invalidate the last usable
credential, leaving the device fail-closed pending independently authorized
recovery (`SNTR-DAUTH-022`), and availability never extends old-key
authorization indefinitely. The overlap MUST be a finite, deployment-documented
window; a lost acknowledgment after durable installation MUST reconcile
within that window or default to the hard cutoff without resurrecting the old
credential, and the old credential MUST NOT remain usable at or after the
cutoff. The device MUST durably install the replacement before discarding the
current credential and MUST NOT claim an acknowledgment for material it has
not persisted.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-020` races rotation
against concurrent reconnects and injects crashes, overlap expiry and lost
acknowledgments, and observes installation before retirement on the success
path plus cutoff without resurrection on the failure paths.

**SNTR-DAUTH-021** — Epoch integrity and rollback prevention. The enrollment
epoch MUST increase strictly across successful rotations of a logical
enrollment. During a rotation the directly superseded epoch stays admissible
only within its declared overlap window under the rotation rules
(`SNTR-DAUTH-020`) and MUST be rejected once that window lapses, the epoch is
retired, or it is revoked; every other epoch lower than or equal to a
previously superseded epoch MUST be rejected. A rollback
of host authorization state to
a pre-revocation, pre-retirement or pre-rotation epoch MUST NOT revive that
epoch: once revoked or retired, an epoch stays invalid. Epoch exhaustion MUST
retire the enrollment through a fresh rotation or a new enrollment rather
than wrap or rewind the identifier, and use beyond exhaustion MUST NOT
continue through counting wrap or reuse. Concurrent reconnects during
rotation MUST settle each attempt against the durable epoch record at that
moment: mid-rotation attempts either succeed under the live overlap window or
fail after the cutoff, without hybrid or cross-epoch admission. Device loss
during rotation resolves only through re-enrollment under `SNTR-DAUTH-022`;
a returning device operating on a stale epoch is denied once its overlap has
lapsed or its enrollment fate has applied.

Acceptance evidence (planned, not executed): `PLAN-DAUTH-021` exercises
concurrent reconnect, rollback, overlap expiry, epoch overflow and device
loss; every stale, rolled-back or overflowed epoch is refused outside the
still-live overlap window, and no epoch
wraps or is revived.

### 5.7 Recovery and secrets

Device obligations: discard retired credentials at the earliest supported
platform mechanism; never present a revoked credential for recovery. Host
obligations: independent recovery authority; storage access control,
disposal and backup boundaries; authenticated bounded pin rotation.

**SNTR-DAUTH-022** — Compromise recovery uses an independent authority.
Re-enrollment after compromise MUST use an authority verified independently
of the compromised credential — such as a separately authenticated
out-of-band path or a bootstrap principal explicitly authorized under the
deployment's enrollment authority (`SNTR-DAUTH-011`). A compromised or
revoked credential MUST NOT restore or replace itself: it MUST NOT re-issue,
extend its own validity or epoch, authorize the recovery channel or supply
the trust evidence for its replacement, and recovery decisions MUST NOT rely
on possession of the compromised secret or of the compromised device state.
Recovery is not claimable by an implementation unless the deployment
designates and documents that independent authority path; the replacement
always carries a fresh tuple (new handle and epoch), never a resumption of
the compromised one.

**SNTR-DAUTH-023** — Storage access control and secret disposal. The host
MUST restrict access to usable AK material through access control scoped to
the lifecycle control plane, consistent with `SNTR-DAUTH-004`, and MUST
dispose of AK material on expiry, retirement, revocation or transaction
timeout without leaving recoverable copies outside the deployment's
documented boundary. AK material and enrollment transactions MUST NOT leak to
logs, traces, metrics, error text or durable telemetry, and authorization-
store backups stay a deployment secret boundary that the host documents and
restricts on restore. The device SHOULD dispose of a retired credential
through the earliest mechanism its platform supports, and a long-lived copy
SHOULD NOT persist in restorable backups. Disposal behavior is inspected
with synthetic markers, never with real AKs.

**SNTR-DAUTH-024** — Trusted server-key pin rotation. Rotation of the pinned
server static key — the trust anchor through which the initiator verifies the
host — MUST be distributed through a channel independently authenticated at
the deployment's trust boundary; the connecting peer MUST NOT be able to
teach the initiator a new trust anchor, and an unauthenticated peer or
channel MUST NOT supply pin changes. Pin updates MUST be bounded sets with
explicit activation, overlap and retirement semantics; adoption MUST NOT let
a retired pin's identity become usable again, a stale or replayed
configuration MUST NOT silently substitute the active pin, and peer-provided
pin material MUST NOT be accepted. Store format and distribution remain
host-owned per RFC 0007 §11.2.

Acceptance evidence for this area (planned, not executed): `PLAN-DAUTH-022`
replays compromised and revoked credentials against the recovery path and
observes universal denial except through the independently verified
authority; `PLAN-DAUTH-023` inspects logs, traces, metrics, errors and dumps
at every lifecycle step for synthetic key markers and exercises disposal at
revocation, retirement and cleanup without leakage; `PLAN-DAUTH-024` refuses
peer-taught, stale and replayed pin substitutions and demonstrates rollback
prevention.

## 6. Security and acceptance

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
review are not established by those results. The accepted
`SNTR-SC1-WSS-V1` profile and its `CONF-SCW-*` cases are registered;
registration is not execution, and no `CONF-*` verdict is claimed. The RFC
0010 lifecycle requirements add the planned `PLAN-DAUTH-011`–`PLAN-DAUTH-024`
cases, transaction fault matrices and revocation time-budget checks to that
plan; those too are planned, not executed.
