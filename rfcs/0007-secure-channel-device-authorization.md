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

This RFC is a proposal, not an acceptance record or implementation claim.
ADR-008 and the existing production TLS policy remain in effect. No existing
profile identifier, conformance case, Protobuf field, or generated type changes
meaning through this RFC. Raw UDP remains deferred until its binding is
specified and accepted. No SC1 implementation is added by this documentation
change.

## 2. Motivation

Persistent device authorization should survive a network reconnect without
requiring another interactive enrollment. It should not require reusing old
traffic keys, resuming cryptographic state, or weakening application replay
rules. Syntra also needs a security boundary independent of sockets and
carrier libraries: the same channel construction should have explicit TCP,
UDP, and WebSocket mappings.

SC1 uses an established Noise construction rather than introducing primitives
or a separate key schedule. Smaller dependency footprint, lower CPU use, and
better latency are evaluation goals, not measured results. The tradeoffs
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
| Verification | [acceptance plan](../conformance/plans/secure-channel.md) | planned cases, not executable conformance |

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
databases, or require an RPC framework or WebSocket library. A future optional
reference module can consume and produce bounded messages through caller-owned
I/O. Existing core/runtime and FFI complete-frame boundaries remain separate.
Host authentication integration needs trusted per-channel context rather than
an attacker-supplied assertion that a handle was verified.

### 4.2 Credential and context

AK is a uniformly random 256-bit secret scoped to one device enrollment and
intended Noise/hash context. `auth_id` is a proposed collision-checked,
independent eight-byte lookup handle, not proof of identity. An authorization
epoch belongs to credential lifecycle state. The exact wire representation
of the version, mode, carrier binding, endpoint scope, handle, and epoch is a
freeze blocker; both parties must bind identical authenticated context through
Noise's prologue. The secret itself is an input to `psk0`, never the prologue.

No negotiation menu or fallback is introduced. Bootstrap and returning modes
are explicitly selected. An unknown/revoked credential does not silently
trigger bootstrap or a weaker mode.

### 4.3 Records and limits

Use standard Noise transport message operations with empty associated data.
Noise ciphertext is at most 65,535 bytes, including a 16-byte authentication
tag; transport plaintext is at most 65,519 bytes. Carrier limits may be much
smaller. The default serialized Syntra envelope remains 1,048,576 bytes and
requires bounded segmentation/reconstruction where necessary.

The carrier proposal retains an encrypted inner `u32BE frame_length || Frame`
stream for ordered carriers. It avoids new fragment identifiers on reliable
streams. UDP requires a separately reviewed datagram mapping; the stream
mapping is not transplanted to datagrams. The exact mappings and their
tradeoffs are recorded in the carrier draft, not in core serialization.

### 4.4 Budgets, shutdown, and reconnect

The channel needs documented absolute handshake, record/frame assembly,
write-stall and close deadlines, plus aggregate connection, handshake-worker,
queue-byte/count and reassembly budgets. Trickle input does not extend an
absolute deadline. Numerical channel defaults are acceptance blockers; core
Syntra handshake and RPC bounds are not substitutes for these budgets.

The proposed operational ceiling is a new channel before 24 hours or
`2^32` records in either direction, whichever is first. These are proposed
Syntra policy, not Noise limits. A deployment may choose stricter ceilings.
No nonce reset, copied cipher state, custom ratchet, or PSK-only fast path is
defined. Connection renewal is a fresh channel and Syntra handshake, not an
in-place reauthentication or resumption shortcut.

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
proposed requirement to planned positive and negative cases. Traceability
rows are explicitly manual/planned with no executable test IDs or results.
Current conformance profiles and expected outcomes remain unchanged.

- [ ] Freeze wire context and carrier schemas; publish deterministic vectors
      derived through independent implementations, not invented ciphertext.
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
headers do not demonstrate smaller binaries or faster endpoints. Multiple
carrier implementations and an independent security review are required
before promoting this proposal to a production default.

## 10. Unresolved questions and blockers

1. Maintainer authorship/review assignment and approval of the policy amendment.
2. Exact canonical context, bootstrap/returning discriminant, epoch and
   server-key selection encoding; authenticated scope and negotiation rules.
3. Bounded enrollment RPC/out-of-band contract, host storage interface,
   idempotency, receipt/commit behavior and cross-language test fixtures.
4. Trusted channel-authentication context API for runtime/Go/FFI boundaries,
   preserving opaque credential carriage and existing principal semantics.
5. Numeric establishment/assembly/close and aggregate resource defaults;
   validation of proposed lifetime ceilings.
6. Frozen TCP/WS bindings and identifiers; complete UDP handshake demux,
   counters, replay window, path/DoS/reliability/fragmentation specification.
7. Revocation propagation bound, active-channel closure, rotation persistence
   and crash/concurrency semantics.
8. Version/deprecation designation if existing required behavior is replaced.
9. Independent vectors, implementations, threat analysis and security review.

Until these blockers are resolved, no production, interoperability, or full
conformance claim follows from this RFC or its companion documents.

## Appendix: References

- [Noise Protocol Framework, revision 34](https://noiseprotocol.org/noise.html):
  §§3, 5–7, 9, 11.2–11.4, 13–14.
- [Governance](../GOVERNANCE.md) §§3–5 and [RFC process](README.md).
- [Current transport security](../specifications/security/transport-security.md),
  [authentication](../specifications/core/authentication.md), and
  [sessions](../specifications/core/sessions.md).
