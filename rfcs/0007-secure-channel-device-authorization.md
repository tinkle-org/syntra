# RFC 0007: Secure channel and persistent device authorization

- RFC: 0007
- Title: Transport-independent Noise secure channel with persistent device authorization
- Author(s): TBD — blocker (maintainer assignment)
- Status: Draft
- Date: 2026-10-27
- Target version: additive experimental profile; mandatory replacement/removal requires a major-version decision
- Relates to: ADR-003, ADR-004, ADR-008; proposed ADR-011; architecture §§5/7/9; core authentication, handshake, framing, sessions; security transport policy and replay protection
- Reviewers: TBD — blocker (protocol and cryptographic security maintainers)

## 1. Summary

The selected direction for Syntra Secure Channel v1 (SC1) is a shared,
transport-independent channel using `Noise_NK_25519_ChaChaPoly_SHA256` for
bootstrap enrollment and `Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning
devices. Each enrolled device and its host share a unique random 32-byte
authorization key (AK). The AK persists across reconnects; ephemeral keys,
directional traffic keys, and channel state do not.

This RFC remains a proposal; recording experimental delivery below is not an
acceptance record.
ADR-008 and the existing production TLS policy remain in effect. No existing
profile identifier, conformance case, Protobuf field, or generated type changes
meaning through this RFC. Raw UDP remains deferred until its binding is
specified and accepted. Experimental draft-1 channel, TCP/WS/WSS adapter,
host-authorization and asynchronous-writer implementations have been exercised.
Their scope and retained verification are recorded in the
[implementation evidence ledger](../docs/sc1-implementation.md). Implementation
and test execution do not accept this RFC or register a conformance profile.

## 2. Motivation

Persistent device authorization should survive a network reconnect without
requiring another interactive enrollment. It should not require reusing old
traffic keys, resuming cryptographic state, or weakening application replay
rules. Syntra also needs a security boundary independent of sockets and
carrier libraries: the same channel construction should have explicit TCP,
UDP, and WebSocket mappings.

SC1 uses an established Noise construction rather than introducing primitives
or a separate key schedule. In-memory benchmarks are recorded in the evidence
ledger; they are not TLS comparisons or evidence of a smaller dependency
footprint, lower CPU use, or better network latency. The tradeoffs
include server-side secret storage, authenticated server-key provisioning,
credential lifecycle management, and a new interoperable wire contract.

## 3. Proposal

Proposed requirements are owned by these companion drafts:

| Concern | Owning proposal | Requirement family |
|---|---|---|
| Shared secure channel | [secure-channel.md](../specifications/security/secure-channel.md) | `SNTR-SC-*` |
| Persistent authorization | [device-authorization.md](../specifications/security/device-authorization.md) | `SNTR-DAUTH-*` |
| Carrier mappings | [noise-bindings.md](../specifications/transports/noise-bindings.md) | references the two families above |
| Policy rationale | [ADR-011](../specifications/decisions/ADR-011-noise-device-authorization.md) | proposed amendment to ADR-008 |
| Verification | [acceptance plan](../conformance/plans/secure-channel.md) and [implementation evidence](../docs/sc1-implementation.md) | planned conformance work and separately scoped executed implementation tests |

### Client and host obligations

Both peers use exactly the selected Noise suite with empty handshake payloads,
fresh ephemeral key pairs, separate directional cipher states, bounded work,
and no automatic downgrade. The initiator authenticates the server static
public key through trusted provisioning. For returning devices, both peers
mix the same AK using the standard `psk0` operation; the AK is never carried
in a reconnect packet or used directly as a traffic key.

The host resolves an opaque authorization handle to a scoped, nonrevoked AK
record. A valid first handshake message is replayable and is not fresh client
confirmation. Only a valid client transport record under the new keys can
provide that confirmation. The host still evaluates current principal and
method authorization before dispatch. Clients still wait for Syntra `ready`
before protected RPCs.

### Schema and state machine

No `.proto` changes are proposed in this patch. `ClientHello.credential`
remains opaque and `ServerReady.connection_id` remains diagnostic only.
Neither field is repurposed as an AK, authorization handle, or resume token.
Enrollment responses require an explicitly specified application RPC or
out-of-band provisioning contract; `ServerReady` has no issuance field.

The channel state machine precedes the existing six-state Syntra handshake.
For SC1, `CONNECTED` would begin only after local channel establishment; an
absolute channel-establishment deadline covers the earlier phase. On the
host, the first encrypted `hello` can also provide fresh client key
confirmation, but no principal is accepted or application operation dispatched
until its authorization checks pass. Failure in either phase terminates the
attempt. No new core `Frame` variant or implicit capability is introduced.

```text
First enrollment:
Initiator                              Host
    |--- NK message 1 (empty) ---------->|
    |<-- NK message 2 (empty) -----------|
    |--- encrypted Syntra hello -------->|
    |<-- encrypted ready ---------------|
    |--- authorized enrollment RPC ----->|  application-defined contract
    |<-- protected enrollment result ----|  provisions AK + handle

Returning device:
    |--- handle/context + NKpsk0 M1 ---->|
    |<-- NKpsk0 M2 ---------------------|
    |--- encrypted hello -------------->|  fresh client key confirmation
    |                                   |  current enrollment/policy checks
    |<-- encrypted ready ---------------|
    |--- encrypted generic RPC --------->|
```

The enrollment RPC/result above illustrates the proposed lifecycle, not a
delivered issuance flow. Current execution uses out-of-band preprovisioning.

The first bootstrap `ready` binds only the principal established by bootstrap
policy. Enrollment does not change that binding in place: the device opens a
new channel to authenticate using its new AK. Empty/anonymous bootstrap
acceptance is host policy and grants no implicit enrollment permission.

## 4. Detailed design

### 4.1 Boundaries

```text
Application: enrollment authority, credential store, method permissions
Syntra core: Frame, hello/ready, sessions, RPC, errors, correlation
SC1: Noise handshake, key lifecycle, bounded encrypted records
Carrier binding: TCP stream | UDP datagrams | WebSocket binary messages
External I/O: socket / datagram / WebSocket implementation
```

The security state machine does not dial sockets, own application identity
databases, or require an RPC framework or WebSocket library. The implemented
experimental channel consumes and produces bounded messages through caller-owned
I/O; adapters own TCP/WS/WSS carriage. HTTP/HTTPS request-response is excluded
from SC1 draft-1; existing HTTP/HTTPS profiles are unchanged. Complete-frame
core and native-ABI boundaries remain separate.

The implemented `ChannelIdentity` carries mode, carrier, scope, handle, epoch
and principal. `ChannelIdentityProvider.ChannelIdentity()` returns that value
and a separate fresh-confirmation boolean. `ChannelPolicy` replaces ordinary
`Policy` for this integration, requires fresh confirmed client transport traffic,
and receives the explicit opaque hello credential, including an empty value.
It must return a nonempty principal. Empty credentials never automatically
authorize a channel. Comparing the channel principal with the callback's returned
principal, independently establishing trusted root identity, and checking current
enrollment synchronously before `ready` are explicit host-policy responsibilities;
the bridge does not perform those checks automatically. A nil `Authorize` hook
denies methods. See the evidence ledger for the complete authentication boundary.

### 4.2 Credential and context

AK is a uniformly random 256-bit secret scoped to one device enrollment and
intended Noise/hash context. `auth_id` is a collision-checked independent
eight-byte lookup handle, not proof of identity. An authorization epoch belongs
to credential lifecycle state. The implemented experimental draft-1 context has
the exact domain, mode, carrier, server-key selector, epoch, handle and scope
encoding specified in [the carrier contract](../specifications/transports/noise-bindings.md).
It is carried in clear before M1 and supplied unchanged as the Noise prologue.
The AK is an input to standard `psk0`, never the prologue. This encoding is
concrete experimental behavior; acceptance and independent verification remain open.

No negotiation menu or fallback is introduced. Bootstrap and returning modes
are explicitly selected. An unknown/revoked credential does not silently
trigger bootstrap or a weaker mode.

### 4.3 Records and limits

Use standard Noise transport message operations with empty associated data.
Noise ciphertext is at most 65,535 bytes, including a 16-byte authentication
tag; transport plaintext is at most 65,519 bytes. Carrier limits may be much
smaller. The default serialized Syntra envelope remains 1,048,576 bytes and
requires bounded segmentation/reconstruction where necessary.

The implemented experimental binding retains an encrypted inner `u32BE frame_length || Frame`
stream for ordered carriers. It avoids new fragment identifiers on reliable
streams. UDP requires a separately reviewed datagram mapping; the stream
mapping is not transplanted to datagrams. The exact mappings and their
tradeoffs are recorded in the carrier draft, not in core serialization.

### 4.4 Budgets, shutdown, and reconnect

The implemented ordered adapters default to absolute 5-second channel-handshake,
record-assembly, frame-assembly and write deadlines, configurable only to shorter
positive durations. Trickle input does not extend absolute deadlines. Dialing
has one 10-second total budget across socket establishment, Upgrade, Noise and
hello/ready, shortened by the caller's deadline; the core hello budget is
separately 5 seconds. Aggregate admission, queue, server and shutdown defaults
are specified in the [operational evidence ledger](../docs/sc1-implementation.md).
Server admission defaults to 128 connections (maximum 4,096) and 16 handshakes
(maximum 256), with handshake slots held through the `ready` write. Server
shutdown defaults to 5 seconds, configurable only to shorter positive durations.
These implementation defaults are not new accepted core requirements.

The experimental operational ceiling is a new channel before 24 hours or
`2^32` records in either direction, whichever is first, with stricter limits
permitted. The entry clock includes establishment, and lifetime expiry also
applies while idle. These implemented limits await policy acceptance and are
not Noise limits.
No nonce reset, copied cipher state, custom ratchet, or PSK-only fast path is
defined. Connection renewal is a fresh channel and Syntra handshake, not an
in-place reauthentication or resumption shortcut.

The host's post-ready asynchronous writer owns FIFO snapshots and bounds queued
plus active output to 256 frames / 8 MiB. Saturation is terminal
`RESOURCE_EXHAUSTED`; the host loop continues cancellation, deadlines and
dispatch while writes stall. Its write timeout defaults to 5 seconds but accepts
any positive host-configured value, independently of the adapter's at-most-5-second
write deadline. Method authorization returning `UNAUTHENTICATED` uses an
actual-send denial-drain budget of 200 ms; lifecycle-check failure and explicit
principal disconnect instead abort the connection. Writer
join is bounded to 1 second after `Close` returns. Abortive adapter close depends
on cancellation-compliant I/O and store callbacks, not forcible callback killing.
These bounds are distinct from the core callback grace and server shutdown budget.

Finish admitted complete output within a close budget or abort. Noise has no
authenticated orderly-close marker in this proposal. EOF even at a complete
record boundary cannot prove the peer sent all intended records. In-flight
RPC outcomes may remain unknown; neither transport receipt nor device
authorization supplies idempotency or automatic replay permission.

## 5. Alternatives considered

| Alternative | Disposition |
|---|---|
| Keep the current TLS-only policy | Remains the baseline until review; does not evaluate a narrower Syntra channel dependency set. |
| Plain NK followed by device signatures | Not the selected credential model; avoids shared server credentials but adds a separate proof mechanism and signing-key enrollment. |
| Reuse old traffic keys or remove fresh DH on reconnect | Rejected for SC1: increases cross-channel nonce/replay and compromise risks. |
| Multiple Noise suites and automatic fallback | Not part of v1: increases negotiation, downgrade and test scope. |

## 6. Compatibility

Adding a separately selected experimental profile does not reinterpret the
existing Protobuf schema or existing TLS/HTTP/WS identifiers. Existing
production-capable TLS/TCP, HTTPS and WSS mappings remain valid. Noise inside
WebSocket is a distinct binding: old WS messages contain a serialized `Frame`,
whereas the new mapping carries channel handshake messages or ciphertext.
Browser `wss://` still has its outer TLS layer.

Making SC1 mandatory or retiring an existing profile requires an explicit
major-version/deprecation decision, migration window, and accepted RFC. No
removal date is invented here. UDP support requires its own accepted complete
binding and evidence; raw UDP is not made supported by listing it as a target.

Historical RFCs, audits, compatibility archives, generated outputs, reserved
field numbers/names, and old test results retain their original meaning.

## 7. Security considerations

Assets include AKs, server static keys, ephemeral/traffic keys, credential
scope, principal bindings, protected operations and resource availability.
Attackers can observe, modify, replay, reorder, delay, truncate and flood
traffic; separate compromise scenarios include an authorization store, a
server static key, a device AK, and live channel state.

The host must retain usable PSKs, not merely password-style hashes. Wrapped
storage and restricted unwrapping permissions reduce storage exposure but do
not protect against theft of usable AKs from an authorized process. Such theft
allows affected-device impersonation until revocation. Forward-secrecy claims
assume fresh uncompromised ephemerals, effective disposal, and the underlying
cryptographic assumptions; no live-endpoint compromise protection, automatic
post-compromise recovery, or post-quantum security is claimed.

A stable clear handle can link reconnects. Lookup timing and error behavior,
bounded unknown-handle work, rotation privacy, and deployment scope are review
items. A UDP tag alone does not validate reachability of a new source address;
replay filtering, path validation and anti-amplification remain separate.
No raw secrets or attacker-controlled private diagnostics belong in errors.

## 8. Test plan and acceptance criteria

The [acceptance plan](../conformance/plans/secure-channel.md) traces every
proposed requirement to planned positive and negative cases. No formal SC1
`CONF-*` cases or profiles are registered. Separately, the
[implementation evidence ledger](../docs/sc1-implementation.md) records executed
local unit, race and native-core tests and six Docker integration groups:
TCP/WS/WSS × NK/NKpsk0. Those groups exercise echo, 64 KiB and near-1 MiB
payloads, 16 concurrent calls, cancellation/deadlines, authorization and bad-key
rejection, verified TLS, stalled/reset connections, restart and shutdown.
They use the same implementation and are not independent cryptographic or
runtime interoperability evidence. Current profile expectations remain unchanged.
The unchecked criteria below cover complete acceptance work; scoped execution
of overlapping tests is recorded in the ledger and is not erased by that status.

- [ ] Accept the concrete experimental wire context/carrier schemas and publish
      independently derived deterministic vectors, not invented ciphertext.
- [ ] Verify independent Rust–Go handshake/record interoperability and generic
      RPC exchange across accepted carrier bindings.
- [ ] Exercise wrong server keys, wrong/revoked AKs, stale epochs, replayed
      M1, fresh-key confirmation, cross-carrier confusion, invalid tags and
      nonce/lifetime limits before protected effects.
- [ ] Exercise size boundaries, partial I/O, bounded reconstruction, queue
      saturation, timeouts, cancellation, abrupt loss and bounded cleanup.
- [ ] Exercise concurrent reconnects, rotation overlap/crashes, active-binding
      revocation, enumeration hygiene and backend trust boundaries.
- [ ] Review the complete construction, dependencies and public deployment
      policy; record maintainer approvals and independent security evidence.
- [ ] Validate docs/manifests; run generation/compatibility checks only if a
      separately authorized schema change is necessary.

## 9. Drawbacks and risks

Server-held authorization secrets add a compromise surface. Authenticated
static-key provisioning and rotation replace neither application enrollment
nor permissions. New bindings add framing/replay/DoS state. Smaller wire
headers do not demonstrate smaller binaries or faster endpoints. Independent
verification of the implemented carriers and an independent security review are required
before promoting this proposal to a production default.

## 10. Unresolved questions and blockers

### Implemented experimental definitions; acceptance pending

- Exact draft-1 context and explicit mode/carrier selection, standard Noise
  suites, TCP length framing and WS/WSS binary mapping/subprotocol are defined
  in the carrier contract. They are no longer design TBDs.
- Trusted `ChannelIdentity`/`ChannelPolicy` integration, fail-closed method
  authorization, bounded adapters, operational defaults and host async writing
  exist with scoped execution evidence. They do not establish full conformance.

### Partial integration; explicit responsibilities and remaining gaps

- Preprovisioned credentials are supported through host-owned full-context
  lookup; key/principal/expiry/revoked fields are validated. Keys are immutable
  within a handle/epoch. Later `Check` validates validity and principal, not
  key equality. No enrollment issuance, transaction, protected-storage backend
  or rotation workflow is delivered.
- Confirmation comes only from the first valid client record, normally encrypted
  hello, never replayed M1. The watchdog starts at first confirmation and checks
  on a 1-second tick with 1-second lookup contexts, including idle channels;
  this is not an exact 1-second revocation SLA. Disconnecting a principal closes
  current connections, not future admission. Host policy still owns synchronous
  pre-ready validity checks, principal agreement and trusted root identity.
- The codec rejects reserved fields 16/17 in both directions, gates credentials
  at 8 KiB before allocation, bounds depth to 32 and performs full validation.
  Native-ABI completion-timestamp and post-hello credential-release gaps remain.

### Open acceptance and delivery work

1. Maintainer authorship/review assignment, policy amendment approval, and
   explicit version/deprecation designation if required behavior is replaced.
2. Authorized enrollment issuance/provisioning, durable storage/commit/receipt,
   retry/idempotency, interrupted enrollment and rotation/crash/concurrency flows.
3. Deployment revocation-propagation guarantees and independent validation of
   lifecycle, resource, lifetime and cancellation assumptions.
4. Complete UDP demux, counters/replay window, path validation, anti-amplification,
   reliability and bounded fragmentation contract; UDP remains deferred.
5. Independent deterministic vectors, cross-implementation interoperability,
   full-composition threat analysis and independent security review.
6. Accepted portable conformance cases and any separately approved profiles.

HTTP/HTTPS request-response is excluded from this SC1 implementation scope;
existing profiles remain unchanged. In-memory measurements do not establish
TLS-relative performance superiority. The evidence ledger owns detailed results
and the remaining-work record.

Until these blockers are resolved, no production, interoperability, or full
conformance claim follows from this RFC or its companion documents.

## 11. Selected interoperability proposal (2026-10-28; not accepted)

This section selects the target for review and takes precedence over conflicting
experimental descriptions **within this proposal only**. It does not rewrite
the evidence ledger, authorize shipping, or assert that either implementation
already supports the selected bytes. [Governance](../GOVERNANCE.md) still owns
acceptance. The mobile release target requires SC1 and the recovery profile;
neither requirement turns a Core-only implementation into an SC1 implementation.

### 11.1 Concrete mismatch and canonical context

Source inspection at Rust commit `c6553185026e29ba28ae98e1b4c15f6c5100b3bd`
and Go commit `7e2dc26aa5364839cf3177b2ce58299d9b98bc7c` found:

| Concern | Rust local revision 1 | Go draft-1 | Selected proposal |
|---|---|---|---|
| Public prefix | `SNTRSC1L`, explicit revision | `syntra.sc1.draft1` | `syntra.sc1.v1` |
| Mode | bootstrap 0, returning 1 | bootstrap 1, returning 2 | bootstrap 1, returning 2 |
| Carrier | TCP 1, WebSocket 2 | TCP 1, WS 2, WSS 3 | TCP 1, WS 2, WSS 3 |
| Field order | key, scope, handle, epoch | key, epoch, handle, scope | key, epoch, handle, scope |
| Prologue | separate domain + context | context | context only |
| WS subprotocol | `syntra.sc1.local1.ws` | `syntra.sc1.draft1` | `syntra.sc1.v1` |

These are observable incompatibilities, not a claim from a failed live test.
Pinned sources: [Rust context](https://github.com/tinkle-org/syntra-rs/blob/c6553185026e29ba28ae98e1b4c15f6c5100b3bd/SC1.md)
and [Go context](https://github.com/tinkle-org/syntra-go/blob/7e2dc26aa5364839cf3177b2ce58299d9b98bc7c/SC1.md).

Let `S` be scope byte length. The proposed exact concatenation, with half-open
offsets, is:

| Offset | Field | Encoding |
|---|---|---|
| `[0,13)` | domain | ASCII `syntra.sc1.v1`, no terminator |
| `[13,14)` | mode | u8, 1 or 2 |
| `[14,15)` | carrier | u8, 1, 2 or 3 |
| `[15,19)` | server key selector | u32BE; zero permitted |
| `[19,27)` | enrollment epoch | u64BE |
| `[27,35)` | enrollment handle | eight opaque bytes |
| `[35,37)` | S | u16BE |
| `[37,37+S)` | scope | valid UTF-8, 1..255 bytes, no normalization |

Bootstrap requires zero epoch/handle and no AK. Returning mode requires a
nonzero epoch/handle and a separately provisioned uniformly random 32-byte AK.
The responder checks the configured carrier, scope and trusted key selector;
an input selector cannot create trust. Context is public and exactly the Noise
prologue, without another prefix, hash or terminator. M1 is this context followed
by exactly 48 Noise bytes; M2 is exactly 48 Noise bytes. Payloads are empty.
Context is 38..292 bytes, M1 86..340 bytes, total handshake 134..388 bytes before
carrier framing. Reject malformed context before credential lookup/Noise work;
do not normalize or guess a legacy format.

TCP retains u16BE lengths for every handshake/record. WS/WSS retain one binary
message per handshake/record, without that prefix, with compression disabled.
The proposed endpoint is `/syntra/v1/sc1/ws`, subprotocol `syntra.sc1.v1`;
baseline `/syntra/v1/ws` and `syntra.v1` remain distinct. WSS uses carrier 3
even behind a proxy only when the accepted proxy trust contract proves the
external carrier. An untrusted forwarded header is insufficient. Initial public
production acceptance uses verified TLS 1.3 WSS with the separately provisioned
Noise pin. Raw TCP/WS remain restricted unless a separate accepted policy
explicitly authorizes public SC1 use; this amendment grants no such exception.

The encrypted stream remains u32BE serialized-frame length plus frame bytes;
record plaintext is 1..65,519 bytes, ciphertext 17..65,535, and record AD empty.
Frames are 1..1,048,576 serialized bytes. Authenticate before inner assembly;
one writer preserves order and partial offsets. No resynchronization, cipher
state persistence, early data or automatic fallback is introduced.

### 11.2 Authorization, lifecycle and bounded renewal

The selected ordering is verified M2 → encrypted hello → fresh client record
confirmation → current enrollment/root-credential policy and same-principal
check → ready → protected dispatch. A returning policy principal different
from the trusted enrollment principal fails before ready; no privilege union
or remapping occurs. Host-owned identity equivalence is explicit and tested.
Empty hello credentials need an explicit authenticated host policy; they never
implicitly select the channel principal. Replay of M1 supplies no fresh proof.

Revocation uses a deployment-declared finite maximum from authoritative revoke
commit to new-admission denial and active protected-delivery cutoff. The host
documents cache staleness, propagation and check/close budgets whose sum fits
that maximum. Failure to establish current validity denies admission; active
bindings close no later than their last successful check plus the declared
maximum. Idle channels are included. Work already committed cannot be rolled
back; live executions remain accounted until stopped. No offline cached-allow
claim or one-second SLA follows from a polling interval.

Provisioning/rotation is a host-owned **required lifecycle contract**, not an
invented core RPC. Before production acceptance each embedding host supplies a
reviewed issuance transaction: authorized generator, authenticated delivery,
immutable scoped handle/epoch, protected durable device/host storage,
idempotent acknowledgement, lost-response reconciliation and abort/expiry.
Successful routine rotation activates the replacement only after durable device
installation; normal recovery-preserving retirement does not discard the only
still-authorized usable credential merely because an acknowledgement was lost.
Revocation, credential expiry, compromise response and the hard overlap cutoff
do not wait for installation/acknowledgement. They can invalidate the last usable
credential and leave the device fail-closed, requiring independently authorized
recovery; availability never extends old-key authorization indefinitely.
Rotation allocates a fresh independent AK/handle and increasing epoch, with a
bounded documented overlap. Commit/ack crash cuts and concurrent reconnects
have explicit store outcomes; revoked epochs cannot be revived. Counter/epoch
overflow retires the enrollment rather than wrapping. Compromise recovery uses
an independent trusted authority, not only the compromised secret. An initial
implementation may use authenticated out-of-band provisioning, but it cannot
claim an online issuance or seamless rotation workflow it has not implemented.
The complete deployment contract and its execution remain acceptance gates.

Host pin updates are independently authenticated, bounded sets with explicit
activation, overlap, retirement and rollback prevention; the peer cannot teach
the initiator a new trust anchor. Store format and distribution remain host-owned.

Each direction permits at most `2^32` successfully protected records and each
channel at most 24 hours of elapsed lifetime, including suspension. Stricter
deployment limits are allowed. Check before record protection/delivery; when a
limit would be exceeded, close without wrapping/reusing counters and report
unknown outcomes for unfinished calls. A partially reconstructed frame is
discarded. Renew only with a fresh handshake and fresh traffic keys, followed
by explicit recovery negotiation/re-subscription; no in-place rekey or RPC
replay is implied. Test boundary counters using test-only state injection.

### 11.3 Migration, verification and owner edits

Neither legacy identifier is an alias for the new bytes. Explicit legacy
endpoints, if temporarily retained downstream, keep their exact experimental
meaning and separate configuration. A failed v1 attempt does not trigger legacy
or plaintext fallback. Both implementations migrate against the same accepted
spec revision; source/API and behavioral changes receive release notes.

The [context fixtures](../conformance/plans/sc1-context-v1.json) freeze public
encoding examples only. [Acceptance scenarios](../conformance/plans/mobile-v1.md)
require independently derived Noise vectors with test-only static/ephemeral
inputs, both role pairings and real sockets. No ciphertext is fabricated here.
Public context lint is neither cryptographic validation nor conformance.

On acceptance synchronize `security/secure-channel.md`,
`security/device-authorization.md`, `transports/noise-bindings.md`, ADR-011,
requirement indexes and registered SC1 cases/profiles. Existing requirement
traces are SNTR-SC-001 through SNTR-SC-015 and SNTR-DAUTH-001 through
SNTR-DAUTH-010; allocate additional IDs at normative activation if necessary.
Retain the implementation ledger as historical evidence, not the definition of
the new bytes. No core `.proto` field or baseline replacement is made here.

Acceptance remains blocked on maintainer/security approvals, full lifecycle
contracts, independent cryptographic vectors and composition review, and
downstream execution. Selection is not acceptance and this section closes no
interoperability verdict by inspection alone.

## Appendix: References

- [Noise Protocol Framework, revision 34](https://noiseprotocol.org/noise.html):
  §§3, 5–7, 9, 11.2–11.4, 13–14.
- [Governance](../GOVERNANCE.md) §§3–5 and [RFC process](README.md).
- [Current transport security](../specifications/security/transport-security.md),
  [authentication](../specifications/core/authentication.md), and
  [sessions](../specifications/core/sessions.md).
