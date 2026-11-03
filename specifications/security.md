# Syntra 1.0 — Security

Syntra protects each connection with Noise, authenticates a fixed principal
before ready, and authorizes protected operations against current host policy.
Application payloads remain opaque. BCP 14 keywords are normative.

| Layer | Security contract |
|---|---|
| Channel | Bootstrap uses `Noise_NK_25519_ChaChaPoly_SHA256`; returning enrollment uses `Noise_NKpsk0_25519_ChaChaPoly_SHA256` with its authorization key (AK). Both require an independently provisioned server static key. |
| Carrier | Encrypted TCP and direct-host WSS are permitted for public traffic. WSS additionally verifies TLS 1.3 or higher. WS is explicit loopback development only. |
| Identity | Fresh client confirmation, valid hello, trusted application identity and any returning enrollment must agree before ready. AK possession alone grants no method permission. |
| Lifetime | Expiry, revocation, channel age and record-count limits apply independently. A new connection authenticates afresh. |

[Connection](connection.md) defines hello/ready, principal-binding outcomes and
shutdown. [Transports](transports.md) defines the exact context bytes, framing,
carrier admission and resource budgets. This page defines cryptography,
authorization lifecycle, replay boundaries and secret handling.

## 1. Threat model

**SNTR-TMOD-001** — Endpoints MUST protect credentials and AKs; principal,
expiry and revocation state; opaque payloads; endpoint identity and pins;
authorization decisions; subscriptions and filters; and resource availability.
Unsupported resumption MUST NOT restore authority.

**SNTR-TMOD-002** — The model MUST include unauthenticated clients, passive
observers, active delay/reorder/replay/truncation/injection attackers, malicious
authenticated peers, replay and exhaustion attackers, adversarial servers and
misconfigured intermediaries. A mitigation against one class is not coverage
of all classes. A trusted server pin authenticates the server, not its honesty.

**SNTR-TMOD-010** — Bytes and authority MUST be validated at every boundary:
network → carrier → authenticated record → bounded envelope → core → authorized
handler; unauthenticated → authenticated; principal → principal; host policy →
enrollment store; and any intermediary → endpoint. No partial or unauthenticated
plaintext reaches decode/dispatch. An untrusted network name/header cannot
establish endpoint, carrier or principal identity.

**SNTR-TMOD-020** — Endpoints MUST use established Noise/TLS implementations,
protect keys/issuers/stores, define application credential and payload policy,
and confine WS to explicit loopback development. Relative operation deadlines
MUST use local elapsed time including suspend, without synchronized peer clocks.
Credential validity clocks and their tolerance MUST be documented. Unknown
elapsed continuity fails closed.

**SNTR-TMOD-030** — Endpoints MUST apply the following threat mitigations:

| Threat | Required protection |
|---|---|
| T1: credential disclosure | Verified channels and protected secret carriage/storage (§§2–5) |
| T2: downgrade | Explicit selection, highest version overlap and no automatic fallback (§§2–3; [connection](connection.md)) |
| T3: impersonation/authentication bypass | Current enrollment, same-principal agreement and default-deny authorization (§§2, 4–5) |
| T4: replay | Fresh confirmation and separate replay-class defenses (§§2, 6) |
| T5: fixation/cross-connection misuse | Fresh diagnostic-only IDs, fixed principals and no implicit resumption (§§4–6) |
| T6: malformed/oversize/truncated input | Structural validation, bounds and no partial dispatch (§§2, 5; [wire format](wire-format.md)) |
| T7: exhaustion/slow peers | Absolute deadlines and bounded admission, execution, output and memory (§§2, 5; [transports](transports.md)) |
| T8: error oracle | Generic public errors and bounded lookup (§§4–5) |
| T9: unauthorized RPC/event delivery | Method/subscription authorization and withdrawal cutoff (§§4–5) |
| T10: intermediary identity break | Direct-host WSS TLS and exact authenticated carrier context (§§2–3) |
| T11: usable authorization-store compromise/rollback | Restricted AK access, immutable tuples and no stale or revived authority (§4) |
| T12: enrollment abuse | Explicit issuance authority and durable provisioning (§4) |
| T13: revocation lag | Bounded admission, delivery cutoff and channel closure (§4) |
| T14: lost device/rotation abuse | Finite overlap, hard cutoff and independent recovery (§4) |
| T15: lifecycle secret/pin leakage | Secret disposal and independently authenticated pin rotation (§4) |

**SNTR-TMOD-040** — Channel security MUST NOT be treated as application
correctness, application E2EE/key management, protection of compromised
endpoints/issuers/databases, physical/side-channel resistance or underlying
network availability. Application and operator responsibilities for these
boundaries MUST be documented.

**SNTR-TMOD-050** — Public traffic MUST apply every applicable threat mitigation
for its carrier. Loopback WS MUST NOT be used as a public-secure carrier.
Encrypted TCP still requires all authorization and lifecycle checks; it does
not permit bare frame carriage.

**SNTR-TMOD-051** — No custom primitives, TLS, ciphers, ratchets or application
E2EE protocol SHALL be introduced to satisfy this model.

**SNTR-TMOD-060** — Initiators MUST verify endpoint identity, release credentials
only on permitted established channels, enforce deadlines and treat loss as
outcome-unknown rather than proof of non-execution.

**SNTR-TMOD-061** — Hosts MUST validate then authorize at every crossing,
enforce bounds, sanitize errors, isolate principals and terminate withdrawn
bindings within the declared deadline.

Residual risks include traffic sizes/timing/endpoints and clear stable handle
correlation; bounded but nonzero revocation staleness; endpoint/store compromise;
and inability to forcibly stop arbitrary committed application effects. Padding
belongs above Syntra. Store unavailability deliberately reduces availability,
not authorization integrity.

## 2. Channel construction

**SNTR-SC-001** — Both endpoints MUST use an established implementation of
`Noise_NK_25519_ChaChaPoly_SHA256` for bootstrap and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning enrollment. The initiator's
trusted responder static key MUST come from authenticated provisioning/rotation,
never the unauthenticated peer. No custom cipher, schedule, pattern variation
or PSK-only reconnect is permitted.

**SNTR-SC-003** — Both roles MUST authenticate identical canonical context as
the entire standard Noise prologue: mode, carrier, server-key selector, scope,
handle and epoch, encoded exactly by [transports](transports.md#2-canonical-context).
The context prefixes M1 in clear. The AK enters only standard PSK input, never
the prologue. Mismatch fails rather than selecting another mode or format.

**SNTR-SC-004** — Both handshake payloads MUST be empty. Peers MUST reject
unexpected data; credentials, enrollment and application effects MUST NOT be
early handshake data. Replayed M1 may create bounded transient handshake state,
never a principal binding, authenticated-device update or handler effect.

**SNTR-SC-005** — Every attempt MUST use fresh ephemeral key pairs through
cryptographically secure randomness. Entropy failure fails closed. Obsolete
ephemeral/handshake secrets MUST be discarded promptly and never cached for
reconnect. Static server keys and persistent AKs have separate lifecycles.

**SNTR-SC-006** — The initiator MUST verify M2 before encrypted hello. The
responder MUST authenticate fresh client transport traffic and validate the
strict first hello before treating the client as confirmed for host policy.
It MUST validate current enrollment/root identity, scope and same-principal
binding before ready and protected effects. Clients MUST await ready before
protected RPCs; PSK possession never bypasses method authorization.

Trusted policy evidence includes mode, carrier, scope, handle, epoch and a
separately established fresh-confirmation signal. Lookup success, M2 emission
or an unconfirmed handshake cannot construct that authority. Policy receives
the opaque hello credential even when empty; it owns root-identity and
same-principal verification. A first authenticated record alone does not waive
the complete, valid, no-trailing-envelope hello admission rule.

**SNTR-SC-007** — After standard Noise `Split()`, each role MUST use independent
send/receive cipher states and standard transport operations with empty
associated data. Ciphertext is at most 65,535 bytes including its 16-byte tag;
plaintext is at most 65,519 bytes. Clear carrier headers are not authenticated
AD.

**SNTR-SC-008** — Adapters MUST enforce limits before allocation, authenticate
whole records before consuming plaintext and dispatch only complete validated
envelopes. The serialized `Frame` ceiling is 1,048,576 bytes including envelope
overhead, or a documented lower bound. Reassembly and aggregate incomplete
state MUST be bounded; small valid records do not waive resource caps.

**SNTR-SC-009** — Peers MUST NOT reuse traffic-key/nonce pairs, reset nonces
under a key, copy cipher state or migrate it across channels/carriers. Each
new channel requires a fresh handshake. A channel closes at 24 hours elapsed
age including establishment, idle and suspension, or on exhausting `2^32`
protected records in either direction, without counter wrap or further use.
Check before record protection/delivery. Stricter limits are permitted. Renewal
is a fresh channel and explicit recovery negotiation, never in-place rekey.

**SNTR-SC-010** — Handshake/context/authentication/record failure MUST fail
closed. No unauthenticated plaintext reaches the core. Ordered-carrier record
errors terminate without resynchronization. Errors/logs MUST NOT expose AKs,
private keys, credentials or private store diagnostics. Only the specified
carriers are supported.

**SNTR-SC-011** — Establishment, record/frame assembly, write stall and close
times MUST be absolute and bounded. Connections, unauthenticated handshakes,
cryptographic work, pending input/output counts and bytes, and reassembly
memory MUST be bounded in aggregate. Trickle traffic MUST NOT reset deadlines.
Carrier time and record ceilings are defined in
[transports](transports.md#6-limits-and-deadlines).

**SNTR-SC-012** — Once encryption consumes a nonce, the endpoint MUST emit that
exact ciphertext in order or abort the connection; partial output MUST NOT be
spliced, re-encrypted or reconsidered for admission. Shutdown stops admission,
drains only within the close budget and settles callers under
[connection](connection.md#5-shutdown-output-and-liveness). Truncated
records/frames are discarded. Complete-boundary EOF is not authenticated orderly
completion or application success.

**SNTR-SC-013** — Mode and carrier MUST be explicit. Authentication/lookup
failure MUST NOT trigger automatic retry as bootstrap, another suite, another
carrier, unprotected frames or another format.

**SNTR-SC-014** — Renewed enrollment establishes fresh channel authentication,
not logical-session resumption. RPC loss can leave unknown outcomes. Replay,
subscriptions and update recovery require explicit application/recovery
contracts. A live channel proves neither current credential validity,
idempotency, committed progress nor durable cursor acknowledgment.

**SNTR-SC-015** — Noise channel protection MUST NOT be treated as post-quantum
security, application E2EE, anonymity or live-endpoint compromise protection.
Forward secrecy depends on fresh, secret ephemeral keys and prompt disposal.
Any forward-secrecy statement MUST include those assumptions.

## 3. Carrier trust and TLS

**SNTR-TSEC-001**, **SNTR-TSEC-005** — Public traffic MUST use permitted protected
TCP or WSS, with explicit host registration and enrollment policy. Encrypted raw
TCP is production-permitted without outer TLS. WS MUST be explicitly enabled,
confined to loopback and disabled by default for production distributions;
production WS credential use is forbidden. WS still requires Noise and host
policy. Its absence of outer TLS MUST be documented, and its Noise-protected
records MUST NOT be described as plaintext application traffic. Bare TCP/WS
frame carriage is not Syntra 1.0.

**SNTR-TSEC-002** — WSS MUST use verified TLS 1.3 or higher through an established
implementation. WSS MUST NOT negotiate TLS 1.2 or lower. No custom TLS/cipher/
handshake is allowed. This TLS requirement does not apply to raw TCP, whose
endpoint trust is its independently provisioned Noise pin.

**SNTR-TSEC-003** — WSS initiators MUST validate the full certificate chain to
system or explicitly configured trust roots and expiry/revocation under
deployment policy. Invalid, expired, revoked or untrusted certificates are
terminal, with no Noise M1 or credential release and no validation bypass.

**SNTR-TSEC-004** — WSS initiators MUST verify the intended hostname (SAN
dNSName/iPAddress preferred; CN only under the referenced hostname rules)
before M1. A chain-valid wrong-host certificate is rejected. TLS trust and the
provisioned Noise pin are independent and both required.

**SNTR-TSEC-006** — Certificate rotation MUST require no protocol-version
change. Hosts SHOULD use overlapping validity; clients accept currently valid
chains under configured trust policy, not an undocumented hard-coded leaf.
Additional certificate/key pinning requires documented rotation. The mandatory
independent Noise pin follows `SNTR-DAUTH-024`.

**SNTR-TSEC-007** — Peers MUST NOT downgrade WSS below TLS 1.3 or retry another
carrier, format or unprotected mode automatically after failure.
Syntra version/capability negotiation MUST NOT weaken carrier security.

**SNTR-TSEC-008** — WSS MUST terminate verified TLS directly at the host.
Forwarded headers, private-network assertions and caller-terminated streams
cannot prove carrier 3. Byte-preserving routing does not replace endpoint
verification.

**SNTR-TSEC-009** — Credentials and follow-up authentication payloads MUST be
sent only after protected establishment on a permitted carrier. WSS additionally
requires TLS and Upgrade validation first. No reusable secret may travel through
an unverified channel.

**SNTR-TSEC-010** — WSS ALPN, if negotiated, MUST be `http/1.1`; absence is
permitted where the H1 stack does not use it. Mismatch fails, without unintended
protocol fallback. ALPN is neither a Syntra principal nor authorization signal.
No raw-TCP Syntra ALPN identifier is defined.

**SNTR-TSEC-011** — Established TLS secure defaults MUST be used without
weak suites or custom ciphers on WSS. Opaque application encryption
does not replace channel protection or permit omitted endpoint authentication.

**SNTR-TSEC-020** — Initiators MUST fail closed on endpoint/pin validation
failure, expose sanitized diagnostics and require operator/application recovery
before retrying that rejected trust configuration.

**SNTR-TSEC-021** — WSS SNI/hostname MUST be consistent. Every carrier verifies
its configured endpoint trust before credentials; credentials never enter URLs.

**SNTR-TSEC-030** — WSS hosts MUST present the valid intended chain, enforce
TLS ≥1.3 and close on downgrade attempts; operational logs omit secrets.

**SNTR-TSEC-031** — Hosts MUST reject inconsistent endpoint/carrier assertions;
unverified identity propagation cannot establish endpoint or carrier identity.

## 4. Device authorization and host lifecycle

An AK is a shared authorization key, not a signing key or a traffic key.
Bootstrap authenticates the pinned server, not an enrolled client. A returning
channel proves AK possession under fresh keys, not blanket method permission.
Both modes use the same [connection](connection.md) authentication interface.

**SNTR-DAUTH-003** — The public lookup handle MUST be an independent random
eight-byte value, collision-checked in store scope. Its secrecy is not authority,
freshness, principal identity or session identity. Both peers bind handle,
epoch and scope into context. Bootstrap has zero handle/epoch and no AK;
returning has nonzero handle/epoch and nonzero 32-byte AK. Clear stable handles
enable correlation and MUST NOT become public device identities or unrestricted
log/metric labels.

**SNTR-DAUTH-004** — Devices MUST use platform-appropriate secure AK storage.
Hosts MUST restrict usable AK access and protect persisted values with controlled
wrapping/encryption keys; a one-way hash alone cannot supply the Noise PSK.
Core/adapters MUST NOT persist or diagnostic-print AKs or expose raw traffic
keys. Storage/unwrapping is host-owned. Usable AK compromise is device-
impersonation risk, including against an encrypted-at-rest store.

**SNTR-DAUTH-005** — The host MUST bind enrollment to a generic principal,
device reference, endpoint/audience scope, epoch, validity and revocation state.
It MUST check current authorization before ready and per protected method/
subscription. Principal is fixed; handle and connection ID authorize nothing.
Enrollment state is host-owned; no enrollment protobuf message is defined.

**SNTR-DAUTH-006** — Applications MUST document bounded credential validity,
revocation propagation and renewal. Hosts reject expired/revoked reconnects
and withdraw active bindings within the bound, closing affected channels.
Clients require explicit recovery/enrollment, never cached-permission
continuation or automatic downgrade. Persistence does not mean perpetual access.

**SNTR-DAUTH-008** — Hosts MUST bound handle parsing, store lookups and negative
caching before expensive work, rate-limit attempts and avoid unknown/revoked/
expired/wrong-secret error and avoidable timing oracles. Replayed first flights
MUST NOT update authenticated-device state before fresh confirmation. Unknown
handles create no enrollment; failed attempts release PSK and transient state.

**SNTR-DAUTH-009** — Enrollment MAY permit multiple explicitly authorized
production bindings in one service scope: encrypted TCP, verified WSS, or both.
The host MUST require an explicit nonempty permitted-binding set; an empty or
default set permits nothing and is invalid for an enabled enrollment service.
Duplicate or unsupported binding entries MUST be rejected. WS MUST NOT be
admitted by a production enrollment store, including on loopback; development
use does not grant production enrollment portability. Changing a
URL, context carrier or listener registration MUST NOT expand this set.
Persisted policy MUST preserve the authorized set, and missing or mismatched
policy on reopen MUST fail closed rather than default or silently migrate.
Each new connection MUST authenticate its carrier in a fresh handshake and
re-evaluate scope/policy. No traffic keys, counters, replay state or connection
principal binding migrate; no session, subscription or RPC replay is implied.

**SNTR-DAUTH-010** — Integration MUST preserve opaque hello credentials and
ready semantics. AKs, handles and issuance results MUST NOT enter connection IDs
or invented ready fields. Host authentication receives trusted connection-
scoped verification evidence, never authority inferred from client metadata.
Empty credentials still require explicit authenticated policy; method policy
defaults deny.

### Issuance and durable provisioning

**SNTR-DAUTH-002**, **SNTR-DAUTH-011** — Enrollment MUST follow completed
server-authenticated bootstrap plus explicit application enrollment
authorization, or equivalently authenticated out-of-band provisioning. The host
MUST validate the designated enroller's authority, target principal and intended
endpoint/service scope before issuing, staging or delivering material. Anonymous
access, bootstrap completion, an enrollment packet or an AK candidate alone
grants nothing. Host issuance under `SNTR-DAUTH-012` is required; client-generated
issuance is not enabled. The provisioning contract MUST define generator,
transfer, durable commit, acknowledgment, idempotency and interruption before
use. The host SHOULD retain a bounded decision audit. Unauthorized attempts MUST
leave no issued/durable authorization; devices use only designated paths and
discard partial state on denial.

**SNTR-DAUTH-001**, **SNTR-DAUTH-012** — The host MUST generate a unique,
uniformly random 32-byte AK with 256 bits of entropy and an independent uniformly
random eight-byte handle using cryptographically secure randomness. The AK MUST
be scoped to the enrollment and Noise/hash context, never password-derived or
reused for unrelated encryption/authentication.
It enters standard `psk0`, not a returning bearer credential. Entropy failure or
an all-zero/degenerate AK fails before staging. Handle collisions MUST use a
documented bounded reject/redraw procedure, never overwrite another record.
Duplicate/overlapping live `(handle, epoch)` issuance, including retries and
concurrency, MUST be refused. AK, principal and scope are immutable within that
tuple; a change requires fresh handle and epoch. A zero returning handle is
not issuable authority.

**SNTR-DAUTH-013** — Provisioning MUST follow stage → encrypted delivery →
durable device secure-storage persistence and acknowledgment → durable host
commit. Only host commit activates authorization. Staged records MUST NOT pass
returning admission or authorize effects. Delivery protects the AK end to end
to the device, never through an unverified channel, URL, diagnostic/error/echo
path. Devices acknowledge only persisted material. Every transaction has a
documented finite activation timeout and bounded cleanup.

**SNTR-DAUTH-014** — Retried provisioning for one attempt MUST complete or
recognize the same record without a second AK or duplicate authorization.
Lost delivery, acknowledgment or commit outcome reconciles to at most one
active enrollment, without extending the attempt. Crash at every boundary
leaves completable staged state or clean failure, never unauthorized state,
permanent inconsistency or revival of an expired/aborted attempt. Cleanup
releases expired state; a later legitimate attempt provisions from scratch.

### Pre-ready identity and enforcement

**SNTR-DAUTH-015** — Every carrier MUST follow protected establishment (verified
TLS plus Upgrade first for WSS) → Noise handshake → fresh confirmation and
encrypted hello → current enrollment, trusted application identity and
same-principal policy → ready → authorized dispatch. No step may be skipped,
reordered or based on unconfirmed evidence. AK possession is not blanket
authorization. Unverified hello identity cannot override enrollment principal.
Credential-less returning policy MUST be explicitly authenticated. Devices
wait for ready; authorization state stays fixed for that connection.

**SNTR-DAUTH-016** — Before returning ready, the host MUST bind verified
channel evidence to (a) valid, unexpired, non-revoked current enrollment matching
context handle/epoch, (b) independently verified trusted application identity,
(c) intended endpoint/audience scope and (d) the enrollment principal. Principal
A versus verified application principal B MUST fail before ready, without
remapping, privilege union or effects. Principal/scope changes require fresh
connection/enrollment, not live-channel rebinding.

**SNTR-DAUTH-017** — Revoked/expired enrollment MUST NOT authenticate on a new
connection. The host MUST consult current validity at admission and again
before ready/effects regardless of prior cache or cryptographic success.
Replayed context, another carrier or stale restored state cannot revive a
revoked handle/epoch tuple.

**SNTR-DAUTH-018** — On established channels enforcement MUST occur no later
than 300 seconds after authoritative revocation commit: this is a hard maximum,
not a mandatory waiting period. The operational target is 60 seconds, preferably
immediate push invalidation. Enforcement means deny new protected operations,
cut off protected delivery and close affected channels, including idle ones.
Deployments MUST document cache staleness, propagation and check/close budgets
whose sum fits the bound. Shorter bounds or zero grace are permitted; longer
bounds are not. Committed effects cannot be undone and surviving executions
remain accounted until stopped.

**SNTR-DAUTH-019** — Failed/timed-out store reads, stale caches or unresolved
revocation MUST deny new admission. Cached authorization MUST NOT extend beyond
the last successful validity check plus the declared freshness bound. An
unverifiable active binding closes no later than that boundary, within
`SNTR-DAUTH-018`. Store unavailability MUST NOT buy availability through stale
allow. Authoritative commit is the earliest durable revoke point, not a later
watchdog observation.

### Rotation, rollback and recovery

**SNTR-DAUTH-007**, **SNTR-DAUTH-020** — Rotation MUST issue fresh independent
AK/handle and a strictly increasing epoch through the staged/idempotent
transaction, with durable transitions, concurrent reconnect handling,
commit/acknowledgment and crash recovery. Durable host commit activates the
replacement as primary. Old/new tuples remain
admissible only within a finite documented overlap, the old tuple expiring at
its credential expiry or overlap cutoff, whichever is earlier. Normal retirement
MUST NOT discard the only authorized usable credential before durable
replacement installation. Revocation, expiry, compromise and hard cutoff do
not wait for installation/ack: they may invalidate the last credential and
require independently authorized recovery. Lost acknowledgments reconcile
within overlap or hit hard cutoff without revival; availability never extends
old authority indefinitely. Devices durably install before discarding current
material and never acknowledge unpersisted replacement material.
Rollback and recovery follow the independent authority rules below; rotation
MUST NOT substitute a compromised secret for recovery or server-pin authority.

**SNTR-DAUTH-021** — Epochs MUST strictly increase across rotations. Only the
directly superseded epoch may remain valid during its declared live overlap;
other stale, retired, revoked or post-cutoff epochs MUST be rejected. Host
rollback MUST NOT revive pre-revoke/pre-retirement/pre-rotation authority.
Epoch exhaustion retires/re-enrolls rather than wraps/rewinds; there is no fresh
greater epoch beyond the integer maximum. Concurrent reconnects resolve against
the durable record at that moment, never hybrid epochs. Device loss during
rotation requires independently authorized re-enrollment.

**SNTR-DAUTH-022** — Compromise recovery MUST use authority independently
verified from the compromised credential/device state: a separately authenticated
out-of-band path or explicitly authorized bootstrap principal. A compromised
or revoked credential MUST NOT issue/extend/replace itself, authorize recovery
or supply its own replacement trust. Recovery claims require the documented
independent path and fresh handle/epoch, not resumption of compromised authority.

**SNTR-DAUTH-023** — Host usable-AK access MUST be scoped to the lifecycle
control plane. Expiry, retirement, revocation and transaction timeout MUST
dispose of material without recoverable copies outside the documented boundary.
AKs/transactions MUST NOT leak to logs, traces, metrics, errors or durable
telemetry. Backups/restores remain restricted secret and rollback boundaries.
Devices SHOULD dispose through the earliest supported platform mechanism and
exclude long-lived copies from restorable backups. No blanket memory-erasure
guarantee is implied.

**SNTR-DAUTH-024** — Noise server-pin rotation MUST be independently
authenticated at the deployment trust boundary. The connecting/unauthenticated
peer MUST NOT teach new trust anchors. Updates are bounded sets with activation,
overlap, retirement and rollback prevention; retired pins cannot return through
stale/replayed configuration. Store/distribution remain host-owned. TLS
certificate renewal is separate and does not replace Noise pin management.

## 5. Credentials, authorization and disclosure

**SNTR-ASEC-001** — Core/adapters MUST NOT log, persist, retain beyond need,
echo or expose credential bytes in diagnostics, metric labels or traces.
Memory retention SHOULD be minimized and accessible secret buffers cleared
where supported. Host-owned protected credential storage is the explicit
separate boundary in §4, not permission for adapter persistence.

**SNTR-ASEC-002** — Credentials MUST cross only permitted established channels.
Authenticated Noise context is defined here; no TLS-exporter-to-credential
binding is defined. Implementations MUST NOT claim such a binding or improvise
one by mixing transport bytes into credential comparison.

**SNTR-ASEC-003** — Initial credentials appear only in encrypted hello, plus
explicitly documented post-`ACTIVE` follow-up RPC payloads. They MUST NOT appear
in URLs, Upgrade headers, environment variables, logs, diagnostics, traces,
metrics, IDs, methods, errors or event metadata. Follow-ups do not negotiate a
mechanism or authorize live principal change. This contract defines no
HTTP/HTTPS request-response Authorization-header binding.

**SNTR-ASEC-004** — Principal handles MUST remain opaque and connection-bound,
with the same authentication and authorization policy interface for
device/service/key/human/anonymous contexts.
Logs redact/pseudonymize them unless the deployment documents otherwise.

**SNTR-ASEC-005** — Every credential type MUST have a documented bounded
lifetime and enforced expiry. Indefinite public credentials are forbidden
except explicitly documented long-lived service credentials with rotation.
Enrollment validity and the channel lifetime ceiling are independent limits.

**SNTR-ASEC-006** — Hosts MUST promptly revoke principal bindings and any
separately defined tokens. Binding withdrawal fails affected unfinished calls
with `UNAUTHENTICATED` and closes, preserving already-selected outcomes and
the RPC terminal gate. The enrollment propagation maximum remains §4.

**SNTR-ASEC-009** — Authentication freshness/validity MUST be re-evaluated by
the mechanism; replayed hello/token bytes cannot bypass those checks. Channel
replay protection alone is not application idempotency.

**SNTR-ASEC-010** — Connection diagnostics MUST be freshly generated and
unguessable, never client-selected, predictable from previous connections or
privileged. No session fixation through `connection_id` is permitted.

**SNTR-ASEC-011** — Authentication public failures MUST remain generic. No
unknown-identity/wrong-secret/expired/revoked distinctions or principal/store
enumeration may be disclosed by errors. Timing SHOULD minimize avoidable
oracles; compare secrets in constant time where applicable. Error text MUST NOT
include credentials, tokens, raw input, stack traces or private diagnostics.

**SNTR-ASEC-020** — Hosts MUST bound envelope size, concurrent calls/executions,
handshake rates, subscriptions/events, queue counts/bytes and deadlines per
connection and principal/aggregate host. Excess lawful work receives
`RESOURCE_EXHAUSTED`; connection/admission exhaustion closes/rejects without
invented results. Isolate/rate-limit offenders before degrading conformant
principals under documented priority. A departed connection does not release
the quota of a still-running handler.

**SNTR-ASEC-021** — Time-to-hello, handshake, record/frame assembly and stalled
payload/write windows MUST be bounded. Absolute timers are not refreshed by
trickles/control traffic. Stalled peers close rather than remain indefinitely.

**SNTR-ASEC-022** — Hosts MUST enforce per-principal rate policy and
per-method/subscription authorization after authentication and before effects.
Default method authorization denies; explicit opt-in is required for permissive
handling. Neither check may be bypassed.

**SNTR-ASEC-023** — Shape/size/depth failures MUST follow [wire format](wire-format.md) error
precedence without handlers or sensitive disclosure. Malformed unknown data
cannot hide behind unknown-field tolerance.

**SNTR-ASEC-024** — All credential/session/token failures MUST follow disclosure
rules; operational attempt/backend detail belongs only in privileged diagnostics.

**SNTR-ASEC-030** — Initiators MUST store credentials securely, omit them from
URLs/logs/reports, discard rejected handshake state and use bounded backoff.

**SNTR-ASEC-031** — `UNAUTHENTICATED` requires fresh credential/authority
recovery; `PERMISSION_DENIED` requires authorization change, not identical retry.

**SNTR-ASEC-040** — Hosts MUST bound/validate before lookup, rate-limit per
source/principal, compare secrets appropriately and isolate principal state.

**SNTR-ASEC-041** — Hosts MUST recheck expiry/revocation for RPC and subscription
actions where staleness could authorize effects, within the declared window.
Idle connections are included in active-binding enforcement.

## 6. Replay classes

**SNTR-RPL-001** — Credential replay, resume-token replay, repeated request IDs,
application idempotency keys and duplicate events MUST be treated as five
separate classes. No one defense establishes coverage of another class.

| Class | Current contract |
|---|---|
| Credential replay | Recheck freshness, expiry and revocation on each authentication. |
| Resume-token replay | Resumption is unsupported; tokens cannot restore authority. |
| Repeated request IDs | Enforce the connection-local ordered high-water rule. |
| Application operation keys | Preserve opaque bytes; the application defines idempotency. |
| Duplicate events | Tolerate duplicates without reply storms; recovery does not promise exactly-once delivery. |

**SNTR-RPL-002** — TLS and Noise record protection MUST NOT be claimed as
application idempotency, deduplication or exactly-once execution. Retries,
reconnections and stream recovery can duplicate application effects.

**SNTR-RPL-010** — Captured credentials MUST NOT extend their validity.
Every new hello is fresh authentication with expiry/revocation and the
mechanism's freshness rules re-evaluated. Replayed M1 cannot prove participation
in the responder's fresh keys; no 0-RTT effect is allowed.

**SNTR-RPL-011** — Unsupported resumption MUST be rejected with
`UNAUTHENTICATED` or `FAILED_PRECONDITION` under the connection's lawful
phase-specific signaling rules. Tokens cannot restore a Syntra 1.0 connection.

**SNTR-RPL-012** — `request_id` is connection-local correlation, never cross-
connection dedup. The [RPC](rpc.md) ordered high-water rule MUST reject a
duplicate/non-increasing request, including a retired ID, as local
`FAILED_PRECONDITION` and native close with no result under the offending ID or
zero ID. It MUST NOT redispatch, resurrect old calls or imply rollback. Noise
record replay and application idempotency remain independent.

**SNTR-RPL-013** — Application operation keys MUST be preserved bit-exact,
without core interpretation. Applications requiring safe retry define their
own dedup window, retained outcome and conflict policy; the core claims none.

**SNTR-RPL-014** — Initiators MUST tolerate duplicate events; hosts SHOULD
minimize them but recovery/reconnect may produce them. Duplicates are not
protocol violations and MUST NOT trigger reply storms.

**SNTR-RPL-020** — Every retry MUST be a fresh connection-local attempt, never
a migrated outstanding call or reused retired request identity. Safe-retry
applications retain the operation key and deduplicate event identities under
their own contract. Numeric IDs on distinct connections confer no continuity.

**SNTR-RPL-021** — Initiators MUST NOT interpret secure delivery as proof a
handler executed exactly once.

**SNTR-RPL-030** — Hosts MUST revalidate credentials/tokens, enforce ordered
request-ID admission, preserve operation keys and document any application
dedup windows. Fresh returning-channel authentication restores no RPC outcome.

**SNTR-RPL-031** — Suspected replay bursts MUST be bounded/rate-limited,
including request-ID collisions and unsupported token reuse.

## 7. Opaque application bytes

**SNTR-OPQ-001** — Arbitrary application bytes, including empty and non-UTF-8,
MUST be preserved bit-exact, without core semantic interpretation, transformation,
compression or application decryption.

**SNTR-OPQ-002** — Routing/correlation/bounds/error behavior MUST be identical
for plaintext, serialized objects and simulated ciphertext payloads.

**SNTR-OPQ-003** — Syntra MUST NOT define or negotiate application E2EE,
ratchets or application key exchange. Applications implement those above Syntra
using established libraries, not new envelope key/algorithm fields.

**SNTR-OPQ-004** — Core version/capability negotiation MUST NOT select or
advertise application cryptosystems. Application formats remain opaque.

**SNTR-OPQ-005** — Encrypted application payloads MUST still use permitted
protected channels with all endpoint and authorization checks. They do not
justify skipped TLS verification on WSS or skipped Noise on any carrier.

**SNTR-OPQ-006** — Byte, concurrency, deadline and queue limits MUST apply
before application processing regardless of content. The 1 MiB cap includes
the serialized envelope's overhead; ciphertext receives no larger allowance.

**SNTR-OPQ-010** — Initiators MUST size-check and MUST NOT smuggle credentials
or key material into protocol metadata even for encrypted payloads.

**SNTR-OPQ-020** — Hosts MUST route/authorize by method and principal, enforce
bounds before handlers and return typed failures without leaking payload bytes.
Application parsing belongs in the handler, not the Syntra core.

## 8. Scope and host policy

The host defines enrollment authority and provisioning interfaces, permitted
bindings, credential validity clocks and tolerance, cache/check/close budgets,
finite activation and overlap windows, backup rollback prevention, independent
recovery authority and authenticated pin distribution. These policies MUST be
documented and satisfy §4; they cannot expand the permitted carriers or extend
the protocol's security limits.

Syntra defines no universal enrollment RPC, application E2EE or logical-session
resumption. Only the carriers listed in [transports](transports.md) are supported.
