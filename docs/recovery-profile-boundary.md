# Standardized update recovery — architecture and acceptance boundary

Status: informative decision rationale for the selected release scope.
Authority: [accepted RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
D4–D5 selects the recovery-inclusive first stable bundle; [RFC 0006](../rfcs/0006-update-recovery-profile.md)
is still Draft and owns the proposed wire/profile behavior. This document
neither accepts RFC 0006 nor creates a new MUST/MUST NOT, method, field,
capability ID or conformance result.

## Decision: keep recovery standardized within Syntra (Option A)

The first stable bundle intentionally includes **Syntra-managed generic
update/recovery semantics** as an **optional, explicitly negotiated extension**.
The stable bundle is more demanding than a Core-only conformance claim:

| Layer | Responsibility |
| --- | --- |
| Mandatory Syntra Core | Connection readiness, opaque request/result/notification transport, errors, correlation and loss reporting |
| Optional Syntra update/recovery profile | Post-ACTIVE capability negotiation, bounded ordered streams, opaque checkpoint/generation binding, replay/catch-up and snapshot/confirmation *contracts* |
| Host/provider adapter | Authenticated principal/scope checks, authorized history availability, issuance and validation of opaque checkpoints and snapshot boundaries, resource limits |
| Application | Domain events, state model, meaning of stream selector and payload, durable effects, storage transactions or idempotent fences, application-specific history and recovery policy |

No change to `Frame`, no compulsory update feed for Core-only hosts and no
automatic replay of failed/mutating RPCs follows from this selection.
A host may decline the optional capability and remain a conformant Core
implementation, but it cannot claim the **selected first stable bundle**
without meeting its accepted recovery obligations and independent evidence.

## External precedents and the layer distinction

Telegram documents gap detection and `updates.getDifference` /
`updates.getChannelDifference` for recovery after lost or offline updates.
**Those are Telegram API methods layered above MTProto**, not a requirement of
MTProto's transport/session core. The model informs the need for stable
checkpoints and client-coordinated catch-up, not a claim of identical layering.

Matrix defines incremental `/sync` with a `next_batch` token, which is
another application-protocol example of cursor-based recovery. Neither
precedent mandates that a general network transport owns stream history.

Syntra intentionally differs: an **optional generic protocol profile** gives
independent initiators and hosts an interoperable contract without assigning
application-specific entities, databases or server update-stream machinery
to mandatory core. That added interoperability also adds host-provider,
security, crash-consistency and conformance work.

Sources:
- [Telegram: Working with Updates](https://core.telegram.org/api/updates)
- [Telegram: updates.getDifference](https://core.telegram.org/method/updates.getDifference)
- [Matrix: Client–Server API / Syncing](https://spec.matrix.org/latest/client-server-api/#syncing)

## Behavior selected for RFC 0006 review, not yet accepted

RFC 0006 §11 is the current proposal for:

1. One fresh connection-scoped subscription handle and fixed catch-up
   boundary per round; stale handles cannot authorize later effects.
2. Provider-scoped `(principal, stream, generation)` checkpoint bindings:
   ordinary subscriber overflow is local; actual shared history loss is
   generation-scoped and explicitly signaled.
3. Deterministic Replay/CatchUp, bounded pages, explicit completion and
   snapshot fallback; page results are correlated RPC results.
4. Local durable application effects and checkpoints established atomically
   or through a demonstrable idempotent recovery fence. Sent confirmations,
   locally durable checkpoints and peer-acknowledged confirmations are
   three distinct observations.
5. Resubscription and renegotiation on a fresh authenticated connection
   after reconnect. No logical-session/key migration or arbitrary mutation
   replay.

The proposal retains pre-amendment contradictory text in earlier RFC 0006
sections and older owner/IDL comments. **Do not implement either as accepted
authority** until the maintained RFC, owning profile, schema comments,
registered cases and compatibility review agree.

## Gates before acceptance and before production

**Specification acceptance** requires named human maintainer decision under
the current roster, security review for identity/durability/resource semantics,
resolved existing RFC 0006 §11.9 blockers, coherent
`specifications/profiles/recovery.md` and
`proto/syntra/v1/recovery_profile.proto`, and mapped `SYN-URP-*` cases.
Acceptance does not require that Rust or Go already implements the result.

**Production promotion** requires independent Rust/Go both-role runs,
durability/crash-fault testing, scoped authorization and revocation validation,
snapshot/resubscription tests, supported mobile behavior, and human security
review. A schema build, registered case or same-library round trip is not
such evidence. See [acceptance plan](../conformance/plans/update-recovery.md),
[readiness audit](../audits/v1-release-readiness.md) and
[release process](../RELEASE.md).

Deferred independently: logical-session resumption, general RPC reconciliation
and exactly-once application execution. Avoid claiming any of these from
successful recovery negotiation or a checkpoint confirmation.
