# RFC 0010: SC1 host enrollment and authorization lifecycle

- RFC: 0010
- Title: SC1 host enrollment and authorization lifecycle
- Author(s): oscarlaw
- Status: Accepted
- Accepted: 2026-10-30 via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)
  (disclosed self-approval; sole active maintainer per `GOVERNANCE.md` Sec. 3)
- Date: 2026-10-30
- Target version: v1 minor — security and operational contract for the accepted
  `SNTR-SC1-WSS-V1` profile; no wire change initially or later in this RFC
- Relates to: [RFC 0007](0007-secure-channel-device-authorization.md) (accepted;
  §§3, 11.2, 11.4), [ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md),
  [RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md) (governs the
  bootstrap transition and release gates only); owning documents
  `specifications/security/device-authorization.md` (`SNTR-DAUTH-011`–`SNTR-DAUTH-024`),
  `specifications/security/open-questions.md`, `specifications/security/threat-model.md`,
  `conformance/plans/secure-channel.md`
- Reviewers: oscarlaw (self-review disclosed; sole active maintainer)

Dependency: this RFC depends on accepted RFC 0007 and accepted ADR-011 and
cannot be accepted or cited independently of them. It is a companion
operational-security contract scoped to host obligations under the existing
`SNTR-DAUTH-*` family. It defines no wire behavior and amends no accepted
Noise construction, context bytes, framing, handshake format or profile
identifier. RFC 0007 §11.2 already establishes the underlying security rules;
this RFC makes those obligations operationally precise, not a second competing
model. [RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md) is cited
only as governing the bootstrap transition and release scope.

## 1. Summary

SC1 acceptance made enrollment authority, durable provisioning, principal
binding before `ready`, revocation propagation, rotation and compromise
recovery explicit host implementation obligations (RFC 0007 §11.2 items 2–3)
but left their operational shape to deployment documentation. This RFC fixes
that shape as accepted requirement families `SNTR-DAUTH-011`–`SNTR-DAUTH-024`
in [device-authorization.md](../specifications/security/device-authorization.md):
who may enroll; how AKs and handles are issued; the staged provisioning
transaction and its idempotency/cleanup rules; the pre-`ready` authorization
sequence and principal binding; the decided revocation-propagation policy
(immediate on new connections; a hard 300-second profile maximum and a
60-second operational target on established channels; fail closed when
validity cannot be established); rotation with strictly increasing epochs,
bounded overlap and a hard cutoff; and compromise recovery through an
independently trusted authority, including secret hygiene and server-key pin
rotation. Who is affected: implementers and operators of SC1 hosts and
enrolling devices, plus conformance. No initiator, host or carrier byte
changes; no `.proto` field, reserved value, endpoint or subprotocol changes.

## 2. Motivation

RFC 0007 §11.2 requires each embedding host to supply a reviewed issuance
transaction, bounded revocation propagation and a rotation workflow whose
complete deployment contract and execution remain host/release gates, and its
open item 2 lists "authorized enrollment issuance/provisioning, durable
storage/commit/receipt, retry/idempotency, interrupted enrollment and
rotation/crash/concurrency flows" with none supplied by the profile. Three
problems follow.

1. **Untestable hosts.** Without fixed bounds and transaction semantics, two
   conformant-looking hosts can hold opposite policies: one revokes
   immediately, another treats a poll tick as a propagation guarantee; one
   survives a lost acknowledgment, another double-issues AKs after a crash.
   The existing contract records exactly these gaps: a "not an exact
   1-second revocation SLA" and the acceptance plan's "rotation overlap and
   deployment-wide guarantees remain open"
   ([secure-channel.md §1](../conformance/plans/secure-channel.md)).
2. **Unbounded staleness.** The security suite carried a standing blocker:
   the revocation-propagation maximum was deployment-documented with no
   suite-wide upper bound ([open-questions.md](../specifications/security/open-questions.md)
   `Blockers for stable v1` item 2), and no decision existed for hosts whose
   revocation store is unavailable (item 3). A valid AK handshake proves key
   possession only; the acceptance rule in RFC 0007 §11.2 still needs
   operational precision on what is validated and in what order.
3. **Recovery ambiguity.** Loss, theft and rotation failures are fail-closed
   by design, but the requirement that recovery proceed through an
   independently trusted authority — and that a compromised credential cannot
   restore itself — was stated without testable obligations, hygiene or
   pin-rotation duties.

Fixing these closes the revocation blockers with a decided policy, gives
every lifecycle duty a requirement ID and planned acceptance case, and stays
inside the accepted RFC 0007 contract instead of reopening it.

## 3. Proposal

Normative diff, in plain language: add requirement families
`SNTR-DAUTH-011`–`SNTR-DAUTH-024` to
[device-authorization.md](../specifications/security/device-authorization.md)
as a new §5, close the revocation blockers in
[open-questions.md](../specifications/security/open-questions.md), add
host-lifecycle threats to [threat-model.md](../specifications/security/threat-model.md),
and add planned lifecycle cases, transaction fault matrices and revocation
time-budget checks to [secure-channel.md](../conformance/plans/secure-channel.md).
No text of `SNTR-DAUTH-001`–`SNTR-DAUTH-010` changes; existing IDs, sections
§1–§4 and their meaning are preserved.

### 3.1 Area 1 — Enrollment authority (`SNTR-DAUTH-011`)

Client/device obligations: use only the deployment-designated authority paths;
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

### 3.2 Area 2 — AK issuance (`SNTR-DAUTH-012`)

Client/device obligations: none beyond safe storage (existing `SNTR-DAUTH-004`).
Host obligations: host-generated 256-bit AK; independent eight-byte handle
with collision checks; no duplicate issuance; immutable handle/epoch scope.

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

### 3.3 Area 3 — Durable provisioning (`SNTR-DAUTH-013`, `SNTR-DAUTH-014`)

Client/device obligations: persist before acknowledging; never claim an
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

### 3.4 Area 4 — Principal binding and the pre-`ready` sequence (`SNTR-DAUTH-015`, `SNTR-DAUTH-016`)

Client/device obligations: no protected work before `ready`; connection
authorization state is fixed for the connection. Host obligations: the
accepted order below; binding of verified channel identity to the current
enrollment, trusted identity, endpoint scope and principal before `ready`.

**Most-important acceptance rule (preserved decision).** The accepted
operational sequence, encoding RFC 0007 §11.2 and preserved verbatim as the
operating sequence of this RFC, is:

> Verified WSS + Noise handshake → fresh client confirmation + encrypted
> ClientHello → validate current enrollment, trusted identity, and
> same-principal policy → ServerReady → authorized RPC dispatch. A valid AK
> handshake authenticates possession of the enrolled secret. It does NOT
> automatically authorize every method, and it never lets an unverified
> ClientHello identity override the enrollment's principal. Any
> credential-less returning-device policy must be explicitly authenticated
> under accepted host policy rules.

`SNTR-DAUTH-015` assigns the keyword force of that rule.

```text
Returning device                               Host
    |--- verified WSS + Noise handshake ------->|  trusted server pin, fresh keys
    |--- encrypted ClientHello --------------->|  fresh client confirmation
    |                                           |  validate current enrollment,
    |                                           |  trusted identity, same-principal
    |                                           |  policy (SNTR-DAUTH-015/016)
    |<-- ServerReady ---------------------------|  principal bound, fixed
    |--- authorized RPC dispatch ------------->|  per-method authorization, still
    |                                           |  bound to enrollment validity
```

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

### 3.5 Area 5 — Revocation and expiry (`SNTR-DAUTH-017`–`SNTR-DAUTH-019`)

Client/device obligations: treat loss or rejection of authorization as
requiring explicit recovery or enrollment (existing `SNTR-DAUTH-006`); no
cached-permission continuation. Host obligations: the decided propagation
policy below, verbatim, with keyword force assigned by
`SNTR-DAUTH-017`–`SNTR-DAUTH-019`.

**Decided revocation-propagation policy (recorded normative decision).**

> - New connections: immediate enforcement — a revoked enrollment MUST NOT
>   authenticate on a newly established connection.
> - Existing connections: maximum 300 seconds from authoritative revocation
>   commit to enforcement (hard profile maximum).
> - Operational target: enforce within 60 seconds, preferably immediately
>   through push invalidation.
> - After the deadline: deny new protected operations and delivery; close
>   affected channels.
> - Revocation-store unavailable: fail closed when current validity cannot be
>   established or the permitted freshness window expires.
> - High-security deployments may enforce shorter bounds or zero grace;
>   longer grace is NOT permitted under the default public production profile.
> - Wording notes: the 300-second figure is a maximum tolerated
>   stale-authorization window, not a mandatory waiting period; hosts should
>   revoke immediately when possible; already-committed application effects
>   cannot be retroactively undone; a nominal watchdog interval does not prove
>   propagation.

```text
authoritative revocation commit (t = 0)
   |-- new connections: denied immediately            (SNTR-DAUTH-017)
   |-- established channels: enforcement target t+60 s,
   |   push invalidation preferred                    (SNTR-DAUTH-018)
   |-- hard profile maximum t+300 s: deny new protected
   |   operations and delivery; close affected channels (SNTR-DAUTH-018)
   `-- store unavailable: fail closed within the declared
       freshness bound                                (SNTR-DAUTH-019)
       (already-committed effects are not retroactively undone)
```

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

### 3.6 Area 6 — Rotation (`SNTR-DAUTH-020`, `SNTR-DAUTH-021`)

Client/device obligations: install durably before discarding the current
credential; no acknowledgment for unpersisted material. Host obligations:
fresh AK/handle, strictly increasing epoch, bounded overlap, durable
installation before normal retirement, reconciliation and hard cutoff.

**SNTR-DAUTH-020** — Rotation transaction. Rotation MUST issue a fresh,
independent AK and handle with a strictly increasing epoch, delivered through
the staged provisioning transaction (`SNTR-DAUTH-013`) and its idempotency
rules (`SNTR-DAUTH-014`). The replacement becomes the sole authorized
credential set after durable device installation and durable host commit.
Routine retirement MUST NOT discard the only still-authorized usable
credential until the replacement is durably installed. Revocation, credential
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
enrollment, and an epoch that is lower than or equal to a previously
superseded epoch MUST be rejected. A rollback of host authorization state to
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
loss; every stale, rolled-back or overflowed epoch is refused and no epoch
wraps or is revived.

### 3.7 Area 7 — Recovery and secrets (`SNTR-DAUTH-022`–`SNTR-DAUTH-024`)

Client/device obligations: discard retired credentials at the earliest
supported platform mechanism; never present a revoked credential for
recovery. Host obligations: independent recovery authority; storage access
control, disposal and backup boundaries; authenticated bounded pin rotation.

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

### 3.8 Configuration, bounds, and defaults

Fixed profile values introduced here: 300 seconds (hard enforcement maximum
on established channels), 60 seconds (operational target), 256-bit uniform
AK, eight-byte independent handle. Deployment-declared and required to be
documented (finite, no silent defaults): activation timeout, rotation overlap
window, validity freshness bound, audit-trail extent, and the high-security
shorter bounds. There is no wire field to configure: all of these are
host/store contracts. The null option for the state machines is "no
enrollment": absent, expired, aborted or timed-out attempts authorize
nothing.

## 4. Detailed design

### 4.1 Definitions

- **Authoritative revocation commit** — the earliest point at which a
  revocation is durably committed in the host's authoritative enrollment
  store, including whatever cache invalidation the deployment issues at that
  point. All propagation clocks in `SNTR-DAUTH-018`/`SNTR-DAUTH-019` start
  here, not at the operator's request or an internal intent record.
- **Enforcement** — the joint condition "new protected operations denied",
  "further protected delivery cutoff" and "channel closed" for an affected
  channel. Post-commit in-flight effects that already completed remain
  history; they are not un-done.
- **Operational target vs profile maximum** — 60 seconds is a target the
  acceptance plan observes as latency; 300 seconds is an enforcement bound.
  Neither is a grace period the enrollment is entitled to consume.
- **Freshness bound** — the deployment-declared maximum age of accepted
  enrollment-validity state (cache TTL or store-read allowance). Beyond it,
  validity is treated as not established (`SNTR-DAUTH-019`).
- **Activation timeout** — the deployment-declared finite lifetime of a
  staged, not-yet-committed enrollment or rotation delivery attempt.
- **Overlap window / hard cutoff** — the deployment-declared finite period
  during which a superseded credential remains usable, and the point at
  which it becomes unusable regardless of installation or acknowledgment
  state.
- **Logical enrollment** — one principal's authorization across rotation
  generations; the epoch sequences its generations. Epochs are per logical
  enrollment and MUST (per `SNTR-DAUTH-021`) increase strictly within it.
- **Independent authority** — an enrollment authority verified through
  evidence other than the compromised credential, per `SNTR-DAUTH-022`.

### 4.2 Enrollment and rotation transaction state machines

The transaction is an abstract store/device state machine; no wire message
defines it. Success path and failure transitions are normative via
`SNTR-DAUTH-013`/`SNTR-DAUTH-014`/`SNTR-DAUTH-020`; the table below is the
mechanical reading of those requirements, using the §4.1 terms.

| Step | State (enrollment) | Failure/cleanup transitions |
|---|---|---|
| S0 | absent | any denial or deletion → terminated (no material, no record) |
| S1 | staged (uncommitted, unauthorized) | crash → completable or expired via activation timeout → terminated, bounded cleanup |
| S2 | delivered (encrypted, unacknowledged) | delivery fails/corrupts → S1 retry idempotent; timeout → terminated |
| S3 | device-acknowledged (secure-storage persisted) | ack lost → host reconciles at most one authorized outcome; timeout → terminated per declaration |
| S4 | committed / active (authorized) | terminal success; later invalidation proceeds per revocation/expiry rules |
| S5 | superseded (rotation epoch raised) | survives only within the overlap window → hard cutoff → retired (new tuple or recovery; never revival) |
| S6 | revoked/expired (any state after S1) | terminal; denial per `SNTR-DAUTH-017`–`SNTR-DAUTH-019`; no un-revocation |

Rotation reuses S1–S3 for the replacement tuple and adds monotonic epoch
selection (`SNTR-DAUTH-021`) before S4 commits the replacement; retirement of
the previous tuple happens only at the overlap cutoff or documented earlier
condition. Epoch values update at commit, not at intent.

Device-side: `unknown` → `persisting` (secure storage) → `persisted`
(acknowledgable) → `obsolete` after a superseding replacement install. A
device whose persisted tuple is later invalidated (cutoff, revocation,
retirement) is fail-closed and re-enters authorization only through
`SNTR-DAUTH-022`'s independent re-enrollment path; no offline
credential-recovery mode exists at that point.

The lifecycle state machine precedes the ordinary protocol phases, but its
enforcement surface on the wire remains the existing `ready` sequencing and
per-method authorization — this RFC introduces no new state or `Frame`
variant.

### 4.3 Store and recovery mechanics

- Commit boundaries: enrollment and rotation commits are durable, ordered
  store writes; a torn or partially applied commit is either completable or
  cleanly failed (bounded cleanup), never half-authorized. Provider
  lock/checkpointing and compare-and-swap suitable stores are host-wide
  property, not a wire field.
- Epoch/monotonic sequencing: hosts keep the epoch on the durable store
  record; it is the epoch actually committed, not an increment emitted
  before persistence. A crash between intent and commit re-reads the durable
  record before a retry.
- Idempotency keys: retry identification and duplicate suppression inside
  the transaction are host/store decisions; the RFC fixes only the behavior:
  at most one authorized enrollment per attempt and a factory-reset-free
  path on lost responses/acks. Attempt identity (transaction ID) SHOULD be
  stable across redelivery within SNTR-DAUTH-014's single-attempt semantics.
- Loss of the device (destruction/reformatting) is a normal outcome: the
  enrollment record is recovered or invalidated per SNTR-DAUTH-019's
  fail-closed rule and re-enrollment proceeds under SNTR-DAUTH-022 through
  the independent authority.

### 4.4 Revocation mechanics and measurements

Revocation entry (operator/system request) writes the authoritative commit;
cache invalidation, push invalidation or a check tick may race the commit.
Enforcement evidence in acceptance runs is measured from the commit, not
from the entry point, to prevent "[the schedule exists, therefore I believe
propagation]" style false confidence. Push-based invalidation (the preferred
mechanism) is deployment-owned: no wire protocol is defined here, and its
failure mode still degrades to the SNTR-DAUTH-018/SNTR-DAUTH-019 rules,
never to a silent allowance.

### 4.5 Unknown-field/malformed handling

None. This RFC adds no wire field, no credential format change and no new
`Frame` variant, so the existing malformed-context and unknown-field rules
apply unchanged.

## 5. Alternatives considered

| Alternative | Disposition |
|---|---|
| Fold the operational contract into RFC 0007 by amending or reopening it | Rejected. RFC 0007 is accepted and its Noise NK/NKpsk0 construction, context bytes, framing and handshake format are protected design; reopening an accepted security RFC to add operational text would destabilize the accepted contract and re-litigate settled security decisions. A companion contract cleanly extends it. |
| Keep the lifecycle application-defined ("do nothing") | Rejected. That is today's contract-minus-bounds state: untestable evidence, undecidable revocation cases, duplicate-AK crash bugs and silent tolerance of 5-minute-plus revocation windows become deployment-documentation questions instead. Stable v1 needs the two open blockers resolved, not documented per-deployment. |
| Standardize a new `EnrollDevice` wire RPC | Rejected. It is an additive wire change requiring a schema RFC, a portability story and a device-identity model the current contract does not fix. A portable online enrollment RPC may become a separate explicitly negotiated profile later; that is out of scope here and is not authorized by this RFC. Preprovisioned issuance and other deployment-designated authority paths remain the delivered routes. |
| Break reset-lockout into a resumption capability | Rejected. Resumption is deliberately deferred in default v1; tie-breaking credential loss to a resumption capability would couple the loss path to an unnegotiated feature. Failure recovery here is re-enrollment through an independently trusted authority, fail closed. |

## 6. Compatibility

- Wire impact: none. No `.proto` field, type, reserved value, endpoint,
  subprotocol or profile identifier changes; RFC 0010 does not alter reserved
  or framing behavior. The device-authorization API surface remains the
  existing `ChannelIdentity`/`ChannelPolicy`-owned integration accepted by
  RFC 0007; this RFC adds no bridge-internal capability. Nothing is
  negotiated between host and device: the obligations live in host stores
  and device storage, not in any exchanged value.
- Negotiation: none introduced. `SNTR-SC1-WSS-V1` remains the only affected
  profile identity, unchanged.
- Reserved values: unaffected.
- Migration: none required beyond the publish step itself; hosts add host
  store semantically (activation timeout, overlap window, freshness bound)
  and device implementations add nothing on the wire. Existing hosts that
  implement only out-of-band preprovisioning remain RFC 0007-conformant for
  the accepted wire levels; the acceptance of this RFC makes
  `SNTR-DAUTH-011`–`SNTR-DAUTH-024` part of the required host operational
  bundle. The executable cases were registered in the same acceptance wave
  as `CONF-SCW-025`–`CONF-SCW-042` in `conformance/manifest/sc1-wss.yaml`
  (registration, not execution); registration never retroactively makes
  prior host implementations this bundle's conformant — executed cases do.
- Activation: acceptance flips this RFC's status; documentation, spec text
  and plan sections here are correct as of acceptance, but no executed
  result is claimed for any of them — conformance evidence for
  `SNTR-DAUTH-011`–`SNTR-DAUTH-024` remains "registered, not executed"
  until runs are recorded.

## 7. Security considerations

This RFC is the operational complement to the threat rows added in
[threat-model.md §5](../specifications/security/threat-model.md):
T11 host-store compromise, T12 enrollment abuse, T13 revocation lag, T14
lost-device recovery and rotation abuse, T15 secret leakage. Key residual
positions:

- **Fail-closed availability tradeoff.** Enforcing the 300-second bound and
  the fail-closed rule deliberately turns store/lifecycle failures into
  availability loss. That is the correct direction for an authorization
  system: an operator outage can lock out devices, but it cannot silently
  extend a stolen credential's life.
- **Committed-effect non-rollback.** Effects committed before enforcement
  are history, per RFC 0007 §11.2. Deployments accept this explicitly when
  they accept the bound; RPC idempotency and effect semantics remain
  application-owned.
- **Enumeration and timing.** Enrollment/revocation/rotation lookups stay
  bounded and generic per `SNTR-DAUTH-008`; the new status transitions
  (staged, superseded, revoked) introduce no new peer-visible signal. Handle
  collisions are resolved privately per `SNTR-DAUTH-012`; collision redraw
  attempts are bounded and rate-limited within the standing
  [authentication-security](../specifications/security/authentication-security.md)
  limits.
- **Diagnostics hygiene.** No new diagnostics surface is opened. Lifecycle
  events and enrollment decisions are deployment bookkeeping; the existing
  AK-material and handle-exposure rules (`SNTR-DAUTH-004`, `SNTR-DAUTH-008`,
  `SNTR-DAUTH-023`) and the credential/ASEC disclosure rules apply unchanged,
  including for lifecycle failures. Error text stays generic, without a
  new sub-reason taxonomy for issuance or rotation states.
- **No new protocol attack surface.** Zero new wire bytes means zero new
  wire-attack classes; the existing SC/DAUTH/SCW families' attack classes
  apply unchanged. DoS-relevant paths (enrollment retry storms, collision
  redrawing, revocation lookups, rotation storms) are rate-limited and
  bounded by the deployment's declared bounds and the activation timeout;
  cleanup releases staged state so crashed state cannot accumulate without
  bound.
- **Device-attack surface unchanged.** Compromise response here covers
  credential loss only; live-endpoint compromise, endpoint malware and
  physical attacks remain out of scope (per `threat-model.md` §6).

## 8. Test plan and acceptance criteria

- [ ] Conformance tests (positive + negative + fixtures): planned prose
      cases `PLAN-DAUTH-011`–`PLAN-DAUTH-024` plus the transaction fault
      matrices and revocation time-budget checks in
      [secure-channel.md](../conformance/plans/secure-channel.md) §§7–8. The
      prose cases are mapped and their executable rows are **registered** in
      `conformance/manifest/sc1-wss.yaml` as `CONF-SCW-025`–`CONF-SCW-042`
      (supplemental splits `039`–`042` included), but all are **not
      executed**: no verdict is claimed and only execution remains pending.
      Automated execution against the SC1/WSS fixture remains a later
      integration pass (see §11 Edit map).
- [ ] Requirement-to-test trace: `SNTR-DAUTH-011` → `PLAN-DAUTH-011`;
      `SNTR-DAUTH-012` → `PLAN-DAUTH-012`; `SNTR-DAUTH-013` →
      `PLAN-DAUTH-013` (+ §8.1 fault matrix); `SNTR-DAUTH-014` →
      `PLAN-DAUTH-014` (+ §8.1 fault matrix); `SNTR-DAUTH-015` →
      `PLAN-DAUTH-015`; `SNTR-DAUTH-016` → `PLAN-DAUTH-016`;
      `SNTR-DAUTH-017` → `PLAN-DAUTH-017` (+ §8.3 budgets); `SNTR-DAUTH-018`
      → `PLAN-DAUTH-018` (+ §8.2 fault matrix, §8.3 budgets);
      `SNTR-DAUTH-019` → `PLAN-DAUTH-019` (+ §8.3); `SNTR-DAUTH-020` →
      `PLAN-DAUTH-020` (+ §8.2); `SNTR-DAUTH-021` → `PLAN-DAUTH-021`
      (+ §8.2); `SNTR-DAUTH-022` → `PLAN-DAUTH-022`; `SNTR-DAUTH-023` →
      `PLAN-DAUTH-023`; `SNTR-DAUTH-024` → `PLAN-DAUTH-024`.
- [ ] Interop check: planned, conditional on the later integration pass.
      Independent cross-implementation lifecycle/revocation/rotation runs
      extend the `PLAN-INTEROP-001` scope; nothing is claimed executed here.
- [ ] Buf lint + breaking detection: no schema change is proposed in this
      RFC, so the existing `buf` lint/breaking workflow over
      `proto/syntra/v1/` is not exercised by this document; the registered
      `sc1-wss.yaml` rows for these cases assert host-store and device
      observation surfaces only, so schema assertions remain unchanged.

Truthful status note: the prose cases and the `CONF-SCW-025`–`CONF-SCW-042`
manifest rows are registered planning artifacts. No test has been executed
against this RFC's requirement texts; no fixture exists; no verdict is
claimed for any `CONF-*` case; registration establishes nothing about
execution, and executed evidence remains gated by the recorded runs.

## 9. Drawbacks and risks

- **Host complexity and deployment burden.** Implementers of SC1/WSS hosts
  now must support staged transactions with idempotent retries, bounded
  activation timeouts, overlap windows, push-or-bounded-poll revocation and
  epoch bookkeeping. This is deliberate: it is the accepted RFC 0007 §11.2
  obligation, made testable. Simpler deployments should not configure SC1.
- **Device-facing hard cut by design.** Loss or cutoff after rotation leaves
  a device without credentials pending independently authorized re-enrollment
  (`SNTR-DAUTH-022`). For fleet operators this mostly generates help-desk
  load; the blast radius stays intentional and bounded rather than
  accidental, which is the point of the hard cutoff. Deployments usually
  avoid overlapping rotation with known device-loss windows unless an
  independent authority is available.
- **Store-failure outage amplification.** Enforcing freshness bounds means
  a degraded or frozen authorization store can lock out devices, potentially
  fleet-wide, for as long as the declared freshness bound — always within
  the 300-second profile maximum. This residual risk is surfaced explicitly
  in the threat model rather than hidden; it is the fail-closed direction
  chosen here, and operators mitigate it with highly available stores,
  shorter declared bounds or shorter zero-grace configurations.
- **Clock and measurement dependency.** The propagation policy creates an
  implementer temptation to treat any store latency, wall-clock arithmetic
  or state-machine opinion as a substitute for measured enforcement
  evidence. The acceptance plan counters with injected clocks and observed
  enforcement latency; an implementation that cannot produce honest latency
  measurements does not claim compliant propagation. An implementation that
  builds no push mechanism reduces the 60-second operational target to the
  hard bound; that tradeoff is permitted, but it remains visible in evidence
  as estimated enforcement latency, not as the target's attainment.
- **Inspection-dependent verification.** Because no network-visible bytes
  change, conformance claims about this RFC rest entirely on host-store and
  device-state inspection; harnesses reach inside hosts to verify
  idempotency and epoch monotonicity. The plan compensates with instrumented
  peers, synthetic secret markers and store-state probes.
- **Store contracts over wire claims.** Immutability, idempotency and
  lost-ack behavior bind only where the deployment actually stages and
  commits records as specified; a host without such a store cannot claim
  conformance to those clauses.

## 10. Unresolved questions and blockers

1. **Channel-binding construction** (unchanged, kept open,
   [authentication-security.md](../specifications/security/authentication-security.md)
   `SNTR-ASEC-002`). The credential-security baseline explicitly does not
   claim channel binding; if stable v1 claims channel binding (for example,
   a TLS exporter bound to credentials), its exporter construction,
   negotiation and failure semantics require a dedicated RFC. This document
   does not change that: SC1's authenticated channel context is its own
   construction and is not asserted as credential channel binding.
2. **Portable online enrollment RPC** (deferred, not blocked). A portable
   online enrollment RPC may become a separate explicitly negotiated profile
   later. It is out of scope here, and no `EnrollDevice`-style wire method
   is standardized, reserved or implied by this RFC.
3. **Push-invalidation wire/transport** (deployment-owned, no blocker). The
   preferred immediate revocation mechanism is a push; its form (message
   bus, internal queue, store-triggered re-check) is a deployment secret.
   The bound governs outcomes, not mechanism.
4. **Collision-redraw audit extent** (future work). Hosts record bounded
   audit trails per `SNTR-DAUTH-011`; a future operational document may
   standardize their inspection format. Not needed for acceptance.
5. **High-security numeric sub-profiles** (future work). Shorter bounds and
   zero grace are permitted; naming a concrete high-security sub-profile
   (for example a documented zero-grace bundle) can be proposed in a
   follow-up, but no such profile identifier exists here.

## 11. Edit map

Files edited by RFC 0010's companion wave, with responsibility:

| File | Change |
|---|---|
| `specifications/security/device-authorization.md` | new §5 host enrollment/authorization lifecycle contract, requirements `SNTR-DAUTH-011`–`SNTR-DAUTH-024` (existing §§1–4 and IDs unchanged); §6 is the former §5, headers and the Requirements line updated |
| `specifications/security/open-questions.md` | `Blockers for stable v1` items 2 (revocation bound) and 3 (offline revocation fail-closed) marked resolved with the decided policy; item 1 (channel binding) and items 4–5 remain open; lifecycle status notes updated |
| `specifications/security/threat-model.md` | new §5 subsection with T11–T15 host-lifecycle threat rows (host-store compromise, enrollment abuse, revocation lag, lost-device recovery, secret leakage), marked planned, with `SNTR-DAUTH` owners |
| `conformance/plans/secure-channel.md` | new §§7–8: `PLAN-DAUTH-011`–`PLAN-DAUTH-024` planned cases, enrollment and rotation transaction fault matrices, revocation time-budget checks; owner/counts notes updated |
| `docs/server-implementation.md` | lifecycle sections are updated by their owning documentation pass in the same wave to reference these requirement IDs; this RFC's diff does not edit that file |
| `conformance/manifest/sc1-wss.yaml` | lifecycle case registration happened in the acceptance wave: `CONF-SCW-025`–`CONF-SCW-042` rows registered (registration is not execution; no verdict claimed) |

## Appendix: References

- [RFC 0007](0007-secure-channel-device-authorization.md) (accepted): the
  normative SC1 contract, in particular §11.2 (authorization, lifecycle,
  bounded renewal), §11.4 (accepted decisions), §3 (obligations and owners).
- [ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md)
  (accepted): Noise device-authorization policy amendment.
- [RFC 0009](0009-v1-bootstrap-governance-and-release-scope.md) (accepted):
  bootstrap governance and release-scope authority for v1; cited here only
  as governance, not as SC1 wire authority.
- [device-authorization.md](../specifications/security/device-authorization.md)
  (`SNTR-DAUTH-001`–`SNTR-DAUTH-024`), [secure-channel.md](../specifications/security/secure-channel.md)
  (`SNTR-SC-001`–`SNTR-SC-015`) and
  [noise-bindings.md](../specifications/transports/noise-bindings.md)
  (`SNTR-SCW-001`–`SNTR-SCW-012`): accepted owners of the profile.
- [open-questions.md](../specifications/security/open-questions.md),
  [threat-model.md](../specifications/security/threat-model.md),
  [authentication-security.md](../specifications/security/authentication-security.md)
  (the credential/session/token rules, `SNTR-ASEC-002` channel binding is the
  open item): security companions this RFC's sections cross-reference.
- [secure-channel.md acceptance plan](../conformance/plans/secure-channel.md):
  planned lifecycle cases and matrices; the executable registration lives in
  [sc1-wss.yaml](../conformance/manifest/sc1-wss.yaml) (`CONF-SCW-025`–`042`,
  registered in the acceptance wave, not executed).
- [GOVERNANCE.md](../GOVERNANCE.md) Sec. 3 and the
  [RFC process](README.md): acceptance quorum and disclosed self-approval.
