# Syntra Update/Recovery Profile — Ordered Delivery, Replay, Snapshot, Committed Progress

- Identifier: `specifications/profiles/recovery.md`
- Title: Optional Update/Recovery Profile Mechanics
- Status: Draft — normative-adjacent, proposal only
- Version: 0.1.0-draft.1 (2026-10-22)
- Proposal reference: [RFC 0006](../../rfcs/0006-update-recovery-profile.md)
- Normative references: [events](../core/events.md), [reliability](../core/reliability.md), [capabilities](../core/capabilities.md), [architecture §8](../architecture.md#8-requirement-ownership-authoritative-sources), [core index](../core/README.md), [requirement registry](../core/requirements.md), [envelope schema](../../proto/syntra/v1/envelope.proto)
- Scope: Optional, capability-gated recovery contract on top of existing envelopes. Standardizes ordered delivery, bounded replay, catch-up boundary and completion, snapshot transfer and installation, committed-progress confirmation, routing scope, bounds, and authorization hooks for independent logical streams. No envelope changes. No new wire variants.
- Terminology: Per core protocol model. **Initiator** = invoking peer. **Host** = serving peer. **Connection** = one authenticated association. **Subscription** = one confirmed generic-RPC establishment. **Stream** = the delivery sequence of exactly one subscription. **Handle** = opaque subscription bytes returned inside `RpcResult` payload. **Generation** = host-assigned continuity epoch per stream. **Checkpoint** = opaque position bytes with explicit predecessor/result pairing. **Batch** = one or more ordered entries carried in a `Notification` payload. **Page** = one bounded replay or snapshot response unit. **Continuation marker** = opaque page cursor stating more remains. **Catch-up boundary** = the point where recovered history meets live delivery. **Snapshot** = provider-supplied state image installed under a proven boundary checkpoint. **Confirm** = initiator statement that the application persisted a checkpoint through its persistence point.

> Draft notice: This document describes [RFC 0006](../../rfcs/0006-update-recovery-profile.md) as a normative-adjacent draft. It carries no normative force until that RFC is accepted. Until acceptance, implementations MUST NOT ship behavior from it, and no test, claim, or release MAY cite it as authority. Where this document and a core specification diverge, the core specification prevails per [architecture §8](../architecture.md#8-requirement-ownership-authoritative-sources). Where this document and the RFC diverge, the RFC prevails as the proposal of record.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be interpreted as described in BCP 14 when, and only when, they appear in all capitals.

## 1. Profile status and optionality

The profile is OPTIONAL, capability-gated, and additive.

A minimal implementation supporting only handshake, generic invocation, cancellation, and typed errors interoperates with a profile-confirming peer at mandatory-only behavior with no recovery contract.

Capability identifier is `syntra.update-recovery/1`. Negotiation uses a standardized generic invocation after ACTIVE. Confirmation is per connection. Confirmation on one connection does not enable the profile on another. Partial acceptance falls back to mandatory-only operation plus any previously confirmed options.

Unnegotiated use fails. A host that does not confirm the profile rejects profile invocations while continuing mandatory service. An initiator that does not offer the profile never receives profile batches. Downgrade is explicit confirmation, never probing.

No `Frame` variant is added, deprecated, or renumbered. All versioned profile payloads travel inside existing `RpcRequest` payload, `RpcResult` payload, or `Notification` payload bytes. Reserved numbers 16, 17 and reserved names `event`, `resume`, `ack` in the [envelope schema](../../proto/syntra/v1/envelope.proto) are preserved unchanged and are not reused by this profile. Profile versioning lives inside the opaque payload bytes, not in `Frame.version`.

Standardized generic RPC methods are canonical `/package.Service/Method` paths with exactly two slashes per `SNTR-RPC-001`:

- `/syntra.v1.UpdateRecovery/Negotiate` — `RecoveryNegotiateRequest` / `RecoveryNegotiateResponse`
- `/syntra.v1.UpdateRecovery/Subscribe` — `RecoverySubscribeRequest` / `RecoverySubscribeResponse` (fixed `catchup_boundary` B)
- `/syntra.v1.UpdateRecovery/Replay` — `RecoveryReplayRequest` / exactly one `RecoveryReplayPage` per `RpcResult`
- `/syntra.v1.UpdateRecovery/CatchUp` — `RecoveryCatchUpRequest` / `RecoveryCatchUpAccepted` in terminal `RpcResult`
- `/syntra.v1.UpdateRecovery/Confirm` — batch `RecoveryConfirmRequest` / `RecoveryConfirmResponse`
- `/syntra.v1.UpdateRecovery/SnapshotConfirm` — snapshot-boundary `RecoverySnapshotConfirmRequest` / `RecoverySnapshotInstalled`
- `/syntra.v1.UpdateRecovery/SnapshotOffer` — `RecoverySnapshotOfferRequest` / `RecoverySnapshotDescriptor`
- `/syntra.v1.UpdateRecovery/SnapshotFetch` — `RecoverySnapshotFetchRequest` / exactly one `RecoverySnapshotChunk` per `RpcResult`, completion as `RecoverySnapshotComplete`
- `/syntra.v1.UpdateRecovery/Unsubscribe` — `RecoveryUnsubscribeRequest` / `RecoveryUnsubscribeResponse`

Every profile `Notification.payload` carries exactly one versioned `RecoveryNotification` discriminator (`batch` | `replay_complete` | `trailer` with matching `profile_version`) with no envelope changes. Malformed method paths MUST be rejected with `INVALID_ARGUMENT` before dispatch. All IDL types are defined in [recovery_profile.proto](../../proto/syntra/v1/recovery_profile.proto).

The separate `SnapshotConfirm` method and retained-install retry validation
below are synchronized draft proposal text under RFC 0006, not newly
accepted norms. Batch and snapshot confirmation have compatible Protobuf
field shapes, so distinct methods identify their intent. Generated codec
freshness establishes representation only; runtime validation and shipping
authority remain separate review blockers (RFC 0006 §10).

Ownership: Syntra owns framing, session and invocation machinery, envelope correlation, capability mechanics, and transport carriage. Authentication, authorization policy, method schemas, replay storage, snapshot content, presence, and durable data remain host-owned above Syntra. Connection liveness, authentication validity, committed progress, and durable acknowledgement stay distinct concerns.

All examples in this document are neutral only: echo round trip, generic key/value read, generic subscription establishment. They illustrate mechanics and impose no data model.

## 2. Requirement IDs

IDs in this section use prefix `SYN-URP`. They are proposed only and carry no normative force until acceptance. The defining proposal is [RFC 0006](../../rfcs/0006-update-recovery-profile.md). Core `SNTR-*` IDs remain owned by their defining core documents listed in [core index](../core/README.md) and indexed in [requirement registry](../core/requirements.md). `SYN-URP-008` and `SYN-URP-009` are reserved and not assigned.

### 2.1 Initiator obligations

**SYN-URP-001** — The initiator MUST NOT use any profile operation, except the standardized profile negotiation invocation after ACTIVE, before the profile capability is confirmed for the connection. The initiator MUST negotiate the profile after ACTIVE through the standardized generic invocation defined by the profile, MUST handle partial acceptance by falling back to mandatory-only operation plus any previously confirmed options, and MUST NOT send profile payloads for an unconfirmed capability. The negotiation invocation itself is the only permitted profile operation before confirmation.

**SYN-URP-002** — The initiator MUST treat every profile payload as versioned bytes carried inside existing `RpcRequest` payload, `RpcResult` payload, or `Notification` payload. The initiator MUST NOT require any new `Frame` body variant, field number, or field name, and MUST preserve and respect reserved numbers 16, 17 and reserved names `event`, `resume`, `ack`.

**SYN-URP-003** — The initiator MUST treat each subscription as one independent logical stream. The initiator MUST track one continuity generation per stream, MUST treat checkpoints as opaque bytes, MUST present exact checkpoint bytes with explicit predecessor/result pairing, and MUST NOT perform arithmetic on checkpoint bytes by increment, decrement, ordering inference, or structural parsing.

**SYN-URP-004** — The initiator MUST consume bounded replay pages, MUST follow the page continuation marker, MUST stop at the catch-up boundary, MUST apply the same validation pipeline to recovered batches and live batches, and MUST tolerate duplicates across the recovered/live boundary without treating a duplicate as a violation. The initiator detects a duplicate by result checkpoint equality with an already applied checkpoint and skips it before predecessor chaining validation.

**SYN-URP-005** — The initiator MUST follow the commit sequence receive → validate → offer → persist → confirm: receive the batch, validate it through the same pipeline as live batches, offer it to the application above Syntra, persist the resulting checkpoint through the application persistence point, and only then confirm the checkpoint through the defined generic invocation. Transport receipt or envelope decode MUST NOT be reported as committed progress or as application success.

**SYN-URP-006** — The initiator MUST route each received batch to exactly the subscription whose opaque handle it accompanies, MUST keep connection state separate from per-stream state, MUST tear down only the targeted subscription on a per-stream terminal signal, and MUST re-establish subscriptions explicitly after the connection ends with a fresh connection-scoped handle and no implicit continuity, carrying forward only the last confirmed checkpoint bytes bound to the same stable stream identity where the stream specification permits.

**SYN-URP-007** — The initiator MUST enforce its bounds for pending invocations, subscriptions, queued bytes, and page sizes, MUST back off on `RESOURCE_EXHAUSTED`, MUST accept an explicit continuity-loss signal with a new generation as the only overflow path, and MUST NOT silently accept truncated history as complete.

### 2.2 Host obligations

**SYN-URP-010** — The host MUST confirm the profile only where it implements it for the bound principal, MUST confirm per connection so that confirmation on one connection does not enable the profile on another, MUST document the confirmed profile version and bounds per deployment, MUST accept the standardized profile negotiation invocation after ACTIVE before confirmation where the host implements the profile, and MUST reject other unnegotiated profile use with `UNIMPLEMENTED` for an unknown operation or `FAILED_PRECONDITION` for use of an unconfirmed operation or for use of an unconfirmed option on a confirmed connection. The negotiation invocation itself is the only permitted profile operation before confirmation.

**SYN-URP-011** — The host MUST implement negotiation, subscribe, replay, catch-up, snapshot, continuation, confirm, and terminate operations as standardized generic invocations with versioned payloads inside existing envelopes. The host MUST NOT add envelope fields, MUST NOT reuse reserved numbers 16, 17 or reserved names `event`, `resume`, `ack`, and MUST keep unknown profile fields ignored on receipt where explicitly marked ignorable, rejecting unknown profile operations with `UNIMPLEMENTED`.

**SYN-URP-012** — The host MUST maintain independent logical streams per confirmed subscription, MUST assign one continuity generation per stream, MUST increment the generation on every continuity loss from overflow, retention expiry, revocation-driven reset, or snapshot rebase, and MUST bind every checkpoint to exactly one stable stream identity and generation pair. The stable stream identity is the stream selected by the stream selector and persists across reconnects, separate from the connection-scoped subscription handle which is fresh per subscription. A checkpoint from a prior subscription for the same stable identity MAY resume when the generation is still valid. Checkpoints from a prior generation MUST be rejected with `FAILED_PRECONDITION`, never reinterpreted under the new generation.

**SYN-URP-013** — The host MUST emit opaque checkpoints with explicit predecessor/result semantics on every batch: each batch states the predecessor checkpoint it continues from and the result checkpoint it advances to. The host MUST NOT require the initiator to compute a successor, and MUST reject forged, malformed, cross-stream, cross-generation, or cross-principal checkpoint bytes with `FAILED_PRECONDITION`, or `UNAUTHENTICATED` where token-like, without leaking other principals' stream state.

**SYN-URP-014** — The host MUST return bounded replay pages, each page stating its continuation marker and the catch-up boundary. Oversized history MUST be paged, never burst beyond the documented per-connection and per-subscription queue bounds. The host MUST stream invocation-triggered catch-up over the existing connection as `Notification` batches through the same validation and authorization path as live batches.

**SYN-URP-015** — The host MUST emit an explicit catch-up completion signal when the stream reaches live, and MUST fail the replay/catch-up invocation with `FAILED_PRECONDITION` in `RpcResult` while emitting an explicit snapshot-required signal as `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification` payload when the requested checkpoint is outside retention or otherwise unrecoverable by replay. Silent restart from an unrelated point is forbidden. Silent truncation without the documented signal is forbidden.

**SYN-URP-016** — The host MUST implement the snapshot transfer and installation contract through generic invocations in bounded pages: offer a snapshot under a provider-proven boundary checkpoint, transfer pages the initiator can store without interpreting, and mark installation complete only when the initiator confirms the boundary checkpoint through the defined confirm operation. The boundary MUST be proven by the provider, meaning the host application supplying the snapshot, so that subsequent batches MUST chain from exactly that boundary checkpoint and MUST be rejected otherwise. Snapshot formats remain provider-defined. Syntra defines only the transfer, boundary, and confirmation mechanics.

**SYN-URP-017** — The host MUST route every batch to exactly one targeted subscription, MUST terminate only the targeted subscription on per-stream termination with a typed terminal signal inside a profile payload or invocation error where possible, MUST NOT end the connection to terminate one stream except where the connection itself ends, and MUST keep connection state for ACTIVE and CLOSING, principal binding, and confirmed capabilities separate from per-stream state for handle, generation, checkpoint, catch-up phase, and routing entry.

**SYN-URP-018** — The host MUST bound all profile resources and document every bound: maximum subscriptions per connection and per principal, maximum pending profile invocations per connection, maximum queued `Notification` bytes per stream and per connection, maximum replay page batches and bytes, maximum snapshot page bytes and total pages, and effective deadlines for profile invocations. On saturation the host MUST apply the documented policy — reject new work with `RESOURCE_EXHAUSTED` and/or end the affected stream with an explicit continuity-loss signal carrying a new generation — never queue without bound and never deadlock silently.

**SYN-URP-019** — The host MUST authorize the bound principal at every profile authorization hook: subscribe, replay, snapshot offer and transfer, and continuation, catch-up, and confirm. The host MUST NOT emit batches for a revoked or expired principal and MUST terminate affected subscriptions with a typed signal where possible. Credential bytes MUST be treated as opaque sensitive bytes: never logged, never persisted by the core, never placed in error detail.

**SYN-URP-020** — Negotiation-version enforcement: the host MUST select the maximum version it implements within the initiator offered range in `RecoveryNegotiateRequest`, MUST confirm only that selected version in `RecoveryNegotiateResponse`, and MUST fail no overlap with `FAILED_PRECONDITION` in `RpcResult`. Both peers MUST carry the confirmed `profile_version` on every other profile payload; mismatch or missing version MUST fail with `FAILED_PRECONDITION`.

**SYN-URP-021** — Unknown-field/profile handling consistent with `specifications/core/serialization.md` (`SNTR-SER-003`) and `specifications/core/versioning.md` (`SNTR-VER-004`): unknown Protobuf fields inside profile payloads MUST be ignored on receipt unless explicitly marked `Critical` in `proto/syntra/v1/recovery_profile.proto`; fields explicitly marked `Ignorable` MUST be ignored; unknown profile operations MUST be rejected with `UNIMPLEMENTED`. Emptiness is per-field, not blanket (missing/mismatched where non-empty is required MUST fail with `FAILED_PRECONDITION`, never silently applied):

| Field | Rule | Empty sentinel meaning |
|---|---|---|
| `profile_version`, `min_version`/`max_version`, `capability` | MUST be non-empty/valid | No empty form; missing or invalid → `FAILED_PRECONDITION` |
| `stream_selector`, `subscription_handle`, `snapshot_handle` (where required) | MUST be non-empty | No empty form; missing → `FAILED_PRECONDITION` |
| `start_checkpoint` | MAY be empty | Empty means initial subscription; non-empty resumes (SYN-URP-022/024) |
| `continuation_marker` | MAY be empty | Empty means first replay request or no further page (SYN-URP-022) |
| `terminate_reason` | MAY be empty | Empty means no termination; non-empty required only when the terminated outcome is selected (SYN-URP-026) |
| `predecessor_checkpoint`, `result_checkpoint`, `boundary_checkpoint`, `catchup_boundary`, `live_boundary_checkpoint` | Per field comment | Presence/pairing governed by SYN-URP-013/023/024; `catchup_boundary` in subscribe response MUST be non-empty (SYN-URP-023) |

**SYN-URP-022** — Replay continuation echo and idempotent retry: replay applies only to resumption from a non-empty `start_checkpoint`. When subscribe used an empty `start_checkpoint` (initial subscription) the initiator MUST NOT send `RecoveryReplayRequest` and MUST start live at the subscribed boundary B on completion (or follow the snapshot path if signaled). For resumption, the initiator MUST send an empty `continuation_marker` on the first replay request with `from_checkpoint` set to the last confirmed checkpoint (non-empty), and MUST echo the previous page's marker verbatim with `from_checkpoint` equal to the previous page's `result_checkpoint` on each continuation. The host MUST reject a mismatched marker or non-chaining checkpoint with `FAILED_PRECONDITION`, except that the host MUST retain the last issued page per subscription and generation and MUST return it verbatim without advancing on a duplicate of the immediately preceding completed request (identical payload in the current generation), so unknown-outcome retries stay safe. The host MUST clear the retained page on generation increment, stream termination, or supersede.

**SYN-URP-023** — Subscribe boundary presence: the host MUST return a non-empty `catchup_boundary` in the subscribe response fixed at subscribe accept. Both peers MUST treat an empty boundary as omitted and MUST reject it with `FAILED_PRECONDITION`; the initiator MUST validate each `RecoveryReplayPage.catchup_boundary` and each catch-up completion signal boundary (`RecoveryReplayComplete.live_boundary_checkpoint`, `RecoveryBatchTrailer.boundary_checkpoint` when `catchup_complete`, `RecoveryCatchUpAccepted.catchup_boundary`) against the subscribed boundary and MUST NOT release held live batches on mismatch; mismatch MUST be rejected with `FAILED_PRECONDITION` (or treated locally as recovery-needed) without releasing held batches.

**SYN-URP-024** — Initial live-baseline bootstrap, repeated recovery rounds, and lost completion handling: initial subscriptions with an empty `start_checkpoint` MUST skip `Replay` and start live at the subscribed boundary B on validated completion (or follow the snapshot path if `snapshot_required` is signaled); resumption with a non-empty `start_checkpoint` MUST replay from the last confirmed checkpoint per `SYN-URP-022` while holding live batches until the validated completion signal at B. After a round completes, a new gap or loss triggers a new independent round from the current confirmed checkpoint with the same rules; B stays fixed per subscription and MUST NOT advance during paging. The initiator MUST NOT treat idle as caught-up; on loss-counter movement, timeout without completion, or boundary mismatch the initiator MUST start a new recovery round (`Replay` or `CatchUp` from the last confirmed checkpoint) and MUST NOT release held batches without a validated completion signal. Duplicate completion signals with equal boundary bytes are tolerated idempotently; mismatched completion MUST NOT release held batches.

**SYN-URP-025** — Snapshot generation transition and confirm-retry fencing: snapshot installation MUST move the stream to a new generation greater than the pre-install generation, bind subsequent checkpoints to the new generation and stable stream identity, and reject old-generation checkpoints with `FAILED_PRECONDITION`. The snapshot offer is bound to `subscription_handle` plus current generation plus exact `boundary_checkpoint` equality; in-flight `SnapshotFetch` under a superseded `snapshot_handle` MUST fail with `FAILED_PRECONDITION`, and the initiator MUST discard prior pages on supersede and MUST NOT install across boundaries. Batch Confirm is idempotent with stop-and-wait fencing: re-presenting the same batch checkpoint bytes in the same generation (`RecoveryConfirmRequest`) MUST return `RecoveryConfirmResponse` without new side effects or generation change. Snapshot confirmation uses `/syntra.v1.UpdateRecovery/SnapshotConfirm`; a first install requires the current pre-install generation and exact offered boundary. Retained-install rule: an exact duplicate `RecoverySnapshotConfirmRequest` for the same authorized subscription and profile version, carrying that pre-install generation and installed boundary bytes, MUST return the original retained `RecoverySnapshotInstalled` without reinstalling or further generation change, only while the response is retained and the current generation equals its installed generation. Supersede, termination, later continuity change, or retention expiry invalidates this narrow exception; other stale-generation requests MUST fail with `FAILED_PRECONDITION`. Boundary equality alone does not establish retry eligibility. Retention is bounded in count, bytes, and lifetime and documented by the deployment; this draft sets no implicit minimum. A checkpoint never returned as committable MUST be rejected with `FAILED_PRECONDITION` without advancing; gap, continuity-loss, and continuation-expiry reports invalidate any pending offer.

**SYN-URP-026** — Subscriber-local versus shared generation invalidation and revocation behavior: a generation increment signals a shared continuity change for the stable stream identity (overflow, retention expiry, revocation-driven reset, or snapshot rebase) and invalidates prior checkpoints across subscriptions for that identity; subscriber-local failures (batch validation failure, offer or persist failure, confirm retry, per-stream terminal signal, connection end with explicit re-subscription under a fresh handle) MUST NOT increment the generation. The host MUST re-evaluate the bound principal at every authorization hook, MUST NOT emit batches for a revoked or expired principal, MUST terminate affected subscriptions with a typed signal (`RecoveryBatchTrailer{terminated=true}` with `terminate_reason` or a typed invocation error) where possible, MUST increment the generation on revocation-driven reset so stale checkpoints fail loudly with `FAILED_PRECONDITION`, and MUST NOT leak other principals' stream state or place credentials in error detail.

## 3. Stream versus subscription handle

A subscription is established only by generic invocation after ACTIVE. The stream is the delivery sequence of exactly one subscription. One subscription maps to exactly one independent logical stream. Multiplexing of multiple subscriptions over one connection is multiplexing of independent streams, each with its own handle, generation, checkpoint, catch-up phase, and routing entry.

The opaque handle is returned inside `RpcResult` payload and is carried inside each profile batch payload so the initiator can route to exactly one subscription. The core does not interpret the handle. Handles are connection-scoped by default. A new subscription yields a new handle. Handles are not reused across connections. The stable stream identity selected by the stream selector persists across reconnects and is separate from the handle; a prior confirmed checkpoint bound to the same stable identity may resume under a new handle when the generation is still valid. The handle authorizes nothing by itself. Delivery begins only after host confirmation.

Per-stream termination affects only the targeted subscription. Connection end discards all per-stream state. Re-establishment after connection end is explicit re-subscription. No stream survives its connection by default, consistent with [events](../core/events.md) session-loss behavior. Pending batches may still arrive after termination by race. Initiators tolerate post-termination batches.

## 4. Opaque checkpoint predecessor and result rules

Checkpoints are opaque bytes to Syntra. Initiators present exact bytes. Hosts bind bytes to exactly one stable stream identity and generation pair.

Each batch carries both a predecessor checkpoint and a result checkpoint. The predecessor states what the batch continues from. The result states what the batch advances to. Gaps are detectable by predecessor chaining without arithmetic. No peer computes a successor by increment or ordering inference. No peer parses checkpoint structure.

Forged, malformed, cross-stream, cross-generation, or cross-principal checkpoint bytes are rejected without leaking other principals' stream state. Checkpoints from a prior generation are rejected after a generation increment, never reinterpreted under the new generation. Checkpoints expire per documented retention and provider policy. Expired or outside-retention checkpoints resolve to the snapshot-required path, never to silent restart.

Confirmation proves only that the initiator application persisted the checkpoint through its persistence point. It never proves business success beyond what the provider specification states.

## 5. Replay paging and catch-up boundary

Replay is capability-gated. No replay exists unless negotiated under this profile. Where offered, replay is bounded paging, never unbounded burst.

Each replay page states its continuation marker and the catch-up boundary. The continuation marker states whether more pages remain; the initiator echoes it verbatim in the next replay request. Replay is sent only to resume from a non-empty `start_checkpoint`; initial subscriptions (empty `start_checkpoint`) skip replay and start live at B on completion. The first replay request carries an empty marker with from_checkpoint set to the last confirmed checkpoint (non-empty); each continuation carries the previous page marker with from_checkpoint equal to the previous page result_checkpoint. The host rejects a mismatched marker or a non-chaining from_checkpoint with FAILED_PRECONDITION, except for an idempotent duplicate of the immediately preceding completed request (identical payload in the current generation), for which it returns the retained page verbatim without advancing (SYN-URP-022). The catch-up boundary states where recovered history meets live delivery. The initiator follows continuation markers page by page and stops at the boundary, and validates each page and each completion signal boundary against the subscribed boundary before releasing held live batches (SYN-URP-023).

Replay responses are subject to the same queue bounds as live batches per [reliability](../core/reliability.md). Oversized history is paged across multiple bounded pages. Invocation-triggered catch-up streams over the existing connection as `Notification` batches through the same validation and authorization path as live batches.

Recovered batches and live batches pass through the same validation pipeline: envelope validity, generation match, predecessor chaining, authorization context freshness, and size bounds. Duplicates across the recovered/live boundary are expected and tolerated. The initiator detects a duplicate by result checkpoint equality with an already applied checkpoint and skips it before predecessor chaining validation. A duplicate is never a violation.

Completion is explicit. When the stream reaches live, the host emits an explicit catch-up completion signal. When the requested checkpoint is outside retention or otherwise unrecoverable by replay, the host emits an explicit snapshot-required signal. Silent truncation without the documented signal is forbidden.

```text
Initiator                              Host
    |                                     |
    |--- invocation{negotiate profile} --->|
    |<-- result{confirmed + bounds} -------|
    |--- invocation{subscribe generic} --->|
    |<-- result{opaque handle, gen 7} -----|
    |<-- notification{batch P, pred A      |
    |         result B, gen 7} ------------|
    |--- invocation{replay from B} ------->|
    |<-- notification{page 1, cont C} -----|
    |<-- notification{page 2, cont end} ---|
    |<-- notification{catch-up done} ------|
    |--- invocation{confirm checkpoint D}->|
    |<-- result{confirmed D} --------------|
```

### 5.1 Draft proposal: replay-then-live fixed-boundary algorithm

This subsection is a Draft proposal under [RFC 0006](../../rfcs/0006-update-recovery-profile.md). It is proposed only and carries no normative force until that RFC is accepted. Until acceptance, implementations MUST NOT ship behavior from it, and no test, claim, or release MAY cite it as authority. Where this subsection and a core specification diverge, the core specification prevails per [architecture §8](../architecture.md#8-requirement-ownership-authoritative-sources). Where this subsection and the RFC diverge, the RFC prevails as the proposal of record.

Proposed steps, using only the terminology above and neutral mechanics only (generic subscription establishment, generic key/value read, echo round trip):

- Subscribe from committed Checkpoint: the Initiator establishes one Subscription with the last confirmed Checkpoint bytes, or with an empty `start_checkpoint` for an initial subscription, presenting exact Checkpoint bytes with explicit predecessor/result pairing. The Host binds the Subscription to exactly one Stream with one opaque Handle and one Generation. Initial subscriptions skip replay and start live at B on completion.
- Capture fixed non-empty catch-up boundary B at subscribe accept and hold live Batches: the Host captures one fixed catch-up boundary B when it accepts the subscribe invocation. The Host holds live Batches for the Stream until the catch-up completion signal, so Batches emitted after subscribe accept arrive only after B in ordered delivery. Holding is bounded subject to the documented overflow policy: while live Batches are held during CATCHING_UP, saturation MUST end the Stream with an explicit continuity-loss signal carrying a new Generation (transition CATCHING_UP -> CONTINUITY_LOST with the held queue cleared), never a bare `RESOURCE_EXHAUSTED` that leaves the Stream stalled waiting for a completion signal it cannot reach. Outside holding, reject new work with `RESOURCE_EXHAUSTED` with documented backoff and/or end the Stream with continuity-loss, never silent drop. B does not advance while catch-up Pages are emitted.
- Replay bounded Pages through B: the Host returns bounded Pages through B, each Page stating its Continuation marker and B. Replay is sent only for resumption; initial subscriptions skip replay. The first Replay carries an empty marker with from_checkpoint set to the last confirmed checkpoint (non-empty); each continuation echoes the previous marker verbatim with from_checkpoint equal to the previous result_checkpoint, and the Host rejects mismatch with FAILED_PRECONDITION except for an idempotent duplicate of the immediately preceding completed request, for which it returns the retained page verbatim without advancing (SYN-URP-022). The Initiator follows the Continuation marker Page by Page and stops at B, validating each page boundary against the subscribed boundary (SYN-URP-023). Oversized history is paged, never burst beyond the documented per-Connection and per-Subscription queue bounds. Invocation-triggered catch-up streams over the existing Connection as Notification Batches through the same validation and authorization path as live Batches. Held live Batches are not emitted before the catch-up completion signal.
- Persist in order receive-validate-offer-persist-confirm: for each Batch through B, the Initiator follows the commit sequence receive, validate, offer, persist, confirm. The Initiator receives the Batch, validates it through the same pipeline as live Batches, offers it to the application above Syntra, persists the resulting Checkpoint through the application persistence point, and only then confirms the Checkpoint through the defined generic invocation. Transport receipt or envelope decode is not reported as committed progress.
- Explicit catch-up completion at B: when the Stream reaches B, the Host emits an explicit catch-up completion signal carrying B. The Initiator treats B as the point where recovered history meets live delivery only on that signal, after validating the completion signal boundary against the subscribed boundary (SYN-URP-023). Completion releases held live Batches in order after B; mismatch MUST NOT release held batches.
- Continue after B: after completion, the Host emits held then new live Batches chaining from exactly B, and the Initiator validates them through the same pipeline as recovered Batches. Duplicates across the recovered/live boundary are expected and tolerated by result Checkpoint equality with an already applied Checkpoint, skipped before predecessor chaining validation, never treated as a violation.
- Snapshot fallback on outside-retention: when the requested Checkpoint is outside retention or otherwise unrecoverable by replay, the Host fails the replay/catch-up invocation with `FAILED_PRECONDITION` in `RpcResult` while emitting an explicit snapshot-required signal as `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification` payload. Recovery then follows the snapshot path with a provider-proven boundary Checkpoint. Silent restart from an unrelated point is forbidden.
- Generation scope separating shared continuity changes from subscriber-local failures: a Generation increment signals a shared continuity change for the Stream (overflow, retention expiry, revocation-driven reset, or snapshot rebase) and invalidates prior Checkpoints for that stable stream identity across Subscriptions. Subscriber-local failures affect only the targeted Subscription and do not increment the Generation: Batch validation failure, offer or persist failure, confirm retry, per-stream terminal signal, and Connection end with explicit re-subscription under a fresh Handle.
- Confirmation retry idempotency: re-presenting the same confirmed Checkpoint bytes through the confirm operation is idempotent. The Host returns confirmed without new side effects and without incrementing the Generation. The Initiator may retry confirm after `UNAVAILABLE`, `DEADLINE_EXCEEDED`, or a lost `RpcResult` by presenting the exact Checkpoint bytes again.

```text
Initiator                              Host
    |                                     |
    |--- invocation{subscribe generic,    |
    |         last confirmed Checkpoint} >|
    |<-- result{handle, gen 7, fixed B} --|
    |         (Host holds live Batches    |
    |          for Stream until catch-up   |
    |          done at B; bounded holding  |
    |          per documented overflow     |
    |          policy)                     |
    |<-- notification{bounded Page        |
    |         through B, cont marker} ----|
    |--- invocation{confirm Checkpoint} ->|
    |<-- result{confirmed, same bytes} ---|
    |<-- notification{catch-up done at B}-|
    |<-- notification{held then new live  |
    |         Batch from B} --------------|
```

### 5.2 Initial live-baseline bootstrap, repeated recovery rounds, lost completion handling

`SYN-URP-024` owns this subsection. An initial subscription carries an empty `start_checkpoint`, skips `Replay` entirely, and starts live at the subscribed boundary B on validated completion (or follows the snapshot path when `snapshot_required` is signaled). A resumption carries a non-empty `start_checkpoint` equal to the last confirmed checkpoint and replays per `SYN-URP-022` while live batches are held until the validated completion signal at B. B is fixed at subscribe accept and never advances during paging; every page and every completion boundary is validated against the subscribed B per `SYN-URP-023` before held batches are released.

Recovery rounds are independent: after a round completes, a later gap, loss-counter movement, timeout without completion, or boundary mismatch starts a new round from the current confirmed checkpoint with a fresh empty marker. The initiator never treats idle as caught-up and never releases held batches without a validated completion signal carrying equal boundary bytes. Duplicate completions with equal boundaries are tolerated idempotently; mismatched completions never release held batches. A lost completion is recovered by a new `Replay` or `CatchUp` from the last confirmed checkpoint; where the host still holds completion state it re-emits the completion signal with the same B.

## 6. Snapshot transfer and installation contract

Snapshot is the fallback when replay cannot recover the requested checkpoint. Formats are provider-defined. Syntra defines only transfer, boundary, and confirmation mechanics. Wire types are `RecoverySnapshotOfferRequest` / `RecoverySnapshotDescriptor`, `RecoverySnapshotFetchRequest` / `RecoverySnapshotChunk` / `RecoverySnapshotComplete`, boundary confirm `RecoverySnapshotConfirmRequest` / `RecoverySnapshotInstalled`, and the `RecoveryNotification{trailer}` snapshot-required signal inside `Notification.payload`.

Offer: the host offers a snapshot under a provider-proven boundary checkpoint in response to `RecoverySnapshotOfferRequest` carrying the current generation. The boundary is proven by the provider, meaning the host application supplying the snapshot attests that subsequent batches chain from exactly that boundary. The offer is bound to `subscription_handle` plus generation plus exact boundary equality.

Transfer: pages are bounded (`page_bytes_max`, `total_pages`). Each page carries snapshot bytes the initiator can store without interpreting. Oversized snapshots are rejected without partial install. Where a snapshot exceeds the maximum pages per offer, a fresh offer with a new boundary is required. A chunk is associated only when its `boundary_checkpoint` bytes equal the currently offered descriptor boundary; equality validates association only, recency comes only from the explicit supersede signal or RPC outcome. In-flight fetch under a superseded `snapshot_handle` fails with `FAILED_PRECONDITION`; the initiator discards prior pages on supersede and never installs across boundaries.

Installation: installation is complete only when the initiator confirms the exact offered boundary through `RecoverySnapshotConfirmRequest` and receives `RecoverySnapshotInstalled` with the new generation (`SYN-URP-025`). Subsequent batches must chain from exactly that boundary checkpoint under the new generation and are rejected otherwise. Partial install without boundary confirm is forbidden.

### 6.1 Snapshot generation transition and confirm-retry fencing

`SYN-URP-025` owns this subsection. Snapshot installation moves the stream to a new generation greater than the pre-install generation and binds subsequent checkpoints to the new generation and stable stream identity. Batch Confirm retries keep the same generation. SnapshotConfirm retries after `UNAVAILABLE`, `DEADLINE_EXCEEDED`, or a lost `RpcResult` use a fresh `request_id` and the original payload, including its pre-install generation, only under the exact retained-install exception in §2.2/RFC 0006. The host rechecks authorization and returns the original installed response and generation; it does not perform another installation or reinterpret old checkpoints. A later continuity change, supersede, termination, or retention expiry invalidates the exception even when boundary bytes match. All other old-generation requests fail with `FAILED_PRECONDITION`.

Deployment documentation bounds retained responses by count, bytes, and lifetime; this draft defines no implicit minimum retry window. A checkpoint never returned as committable is rejected without advancing; gap, continuity-loss, and continuation-expiry reports invalidate any pending offer. Positive and negative validation tests for this proposed exception remain required before a wire-conformance claim. This synchronization does not assert implementation coverage or RFC acceptance.

```text
Initiator                              Host
    |                                     |
    |<-- notification{snapshot-required} --|
    |--- invocation{snapshot offer} ----->|
    |<-- result{snapshot page, boundary   |
    |         checkpoint proven by          |
    |         provider} -------------------|
    |--- invocation{confirm boundary} ---->|
    |<-- result{installed, gen 8} ---------|
```

## 7. Commit sequence

The commit sequence is receive → validate → offer → persist → confirm:

1. Receive the batch over the existing connection.
2. Validate it through the same pipeline as live batches.
3. Offer it to the application above Syntra.
4. Persist the resulting checkpoint through the application persistence point.
5. Confirm the checkpoint through the defined generic invocation.

Transport receipt proves nothing about Syntra receipt. Syntra receipt proves delivery to the initiator core, not processing. Initiator confirmation proves only application persistence of the checkpoint, never business success beyond what the provider specification states, consistent with [reliability](../core/reliability.md) delivery distinction.

The initiator bounds pending confirmations and offered-but-unpersisted batches. The host does not treat transport receipt or envelope decode as committed progress.

## 8. Flow control bounds

Every queue, page, transfer, pending count, and subscription count is bounded and documented per deployment. Proposed defaults from the proposal remain to be confirmed and are recorded here without normative force: maximum 64 subscriptions per connection and 256 per principal; maximum 16 pending profile invocations per connection; maximum 256 KiB queued `Notification` bytes per stream and 1 MiB aggregate per connection; maximum replay page of 64 batches and 256 KiB, whichever binds first; maximum snapshot page of 256 KiB and 256 pages per offer; effective default deadline of 5 s for profile invocations where the invocation carries no explicit bounded deadline.

Initiators enforce pending-invocation, subscription, queued-byte, and page-size bounds and back off on `RESOURCE_EXHAUSTED`. Hosts enforce subscription, pending-invocation, queue-byte, page-byte, and deadline bounds and document every bound and default deadline.

On saturation the documented policy applies: reject new work with `RESOURCE_EXHAUSTED` and/or end the affected stream with an explicit continuity-loss signal carrying a new generation. While live batches are held during CATCHING_UP, saturation MUST end the stream with continuity-loss (CATCHING_UP -> CONTINUITY_LOST, held queue cleared) rather than a bare `RESOURCE_EXHAUSTED` that would stall the stream waiting for an unreachable completion signal. Unbounded queueing, silent deadlock, and silent truncation are forbidden. No unbounded per-batch work is permitted. Hosts do not spawn unbounded workers per batch and do not hold blocking locks across await points on the delivery path. Pending confirmations and offered-but-unpersisted batches are bounded on the initiator side.

Shutdown is orderly and explicit: stop new batches, observe the close grace, then tear down. In-flight profile invocations receive terminal errors. Connection interruption maps to `UNAVAILABLE` with unknown outcome for in-flight invocations, consistent with [reliability](../core/reliability.md).

## 9. Authorization hooks

Every profile operation is an authorization point for the bound principal: subscribe, replay, snapshot offer and transfer, continuation, catch-up, and confirm. Hosts re-evaluate the bound principal at each hook. Checkpoints and handles are never authority by themselves.

Hosts do not emit batches for revoked or expired principals and terminate affected subscriptions with a typed signal where possible (`RecoveryBatchTrailer{terminated=true}` with `terminate_reason` or a typed invocation error, plus `RecoveryUnsubscribeResponse` for explicit unsubscribe). Revocation-driven termination increments the generation so stale checkpoints fail loudly on re-presentation with `FAILED_PRECONDITION` (`SYN-URP-026`).

Subscriber-local failures never increment the generation: batch validation failure, offer or persist failure, confirm retry, per-stream terminal signal, and connection end with explicit re-subscription under a fresh handle affect only the targeted subscription. Only shared continuity changes increment the generation and invalidate prior checkpoints across subscriptions for the same stable stream identity: overflow, retention expiry, revocation-driven reset, or snapshot rebase. Checkpoints from a prior generation are never reinterpreted under the new generation.

Credential bytes stay opaque sensitive bytes, presented only as defined by the handshake and any follow-up authentication payloads, transmitted only over secure transports in externally reachable deployments. The core does not log, persist, or interpret them. Error detail does not contain credentials, checkpoint secrets, or private provider diagnostics.

## 10. Error mappings

Profile errors use the existing typed codes. No code semantics change. Mappings:

| Condition | Code | Scope |
|---|---|---|
| Unknown profile operation | `UNIMPLEMENTED` | Affected invocation only |
| Use of an unconfirmed profile operation | `FAILED_PRECONDITION` | Affected invocation only |
| Unknown stream handle | `UNIMPLEMENTED` | Affected invocation only |
| Use of an unconfirmed option on a confirmed connection | `FAILED_PRECONDITION` | Affected invocation only |
| Unauthorized or unknown principal at any hook | `PERMISSION_DENIED` or `UNAUTHENTICATED` | Affected invocation and targeted stream termination where possible |
| Stale, forged, malformed, cross-stream, cross-generation, or cross-principal checkpoint | `FAILED_PRECONDITION`, or `UNAUTHENTICATED` where token-like | Affected invocation only, without leaking other principals' state |
| Requested checkpoint outside retention or unrecoverable by replay | `FAILED_PRECONDITION` in the failed replay/catch-up `RpcResult` plus explicit snapshot-required signal as `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification` payload | Affected stream, recovery by snapshot path |
| Overload or bound saturation | `RESOURCE_EXHAUSTED` with documented backoff, and/or explicit continuity loss with a new generation | Affected invocation or stream, never silent drop |
| Transport loss with invocations outstanding | `UNAVAILABLE` with unknown outcome | All in-flight invocations on that connection |
| Deadline expiry | `DEADLINE_EXCEEDED` | Affected invocation only |
| Per-stream terminal condition | Typed terminal signal inside a profile payload or invocation error where possible | Targeted stream only, connection continues |

All bound violations are terminal for the affected invocation or stream, not the connection, unless the connection itself is exhausted, violated, or revoked. Error detail carries no credentials or private diagnostics.

## 11. Capability negotiation and state separation

Negotiation is explicit generic invocation after ACTIVE. The initiator offers the identifier and payload version. The host confirms only the subset it implements for the bound principal. No handshake binding is used. Capability state is per connection. Where the host does not confirm, peers operate mandatory-only or live-only generic subscription where separately agreed. The host does not silently weaken confirmation. The initiator does not proceed as if confirmed.

Connection state and per-stream state stay separate. Connection state holds ACTIVE and CLOSING phase, principal binding, and confirmed capabilities. Per-stream state holds handle, generation, checkpoint, catch-up phase, and routing entry. Per-stream termination and continuity loss never end the connection except where the connection itself ends.

Cancellation applies to the subscribing or profile invocation only and does not by itself terminate the stream unless the confirmed stream binding states so. Stream termination uses the targeted profile terminate operation or terminal signal. Every profile invocation has an effective deadline. Expiry surfaces as `DEADLINE_EXCEEDED`.

Ordering for one stream is generation-scoped send order on transports that preserve order, with predecessor and result chaining so gaps are detectable without arithmetic. No cross-stream ordering and no cross-connection ordering is claimed, consistent with [events](../core/events.md) ordering scope.

## 12. Compatibility and conformance notes

Wire impact is additive with zero envelope changes. Reserved values are preserved. Old and new peers interoperate mandatory-only. A confirming initiator against a non-confirming host falls back to mandatory-only plus any previously confirmed options and does not treat the absence as a connection failure where fallback exists.

This section is informative until acceptance. On acceptance, conformance is expected to cover, with neutral payloads only: negotiation confirm, decline, and partial accept; per-connection isolation; envelope preservation; predecessor and result chaining per generation; duplicate tolerance across the recovered and live boundary; same validation pipeline for recovered and live batches; bounded paging with continuation markers and catch-up boundary; oversized history paged, never burst; RPC-triggered catch-up over the existing connection; explicit completion and snapshot-required signals; bounded snapshot transfer with provider-proven boundary chaining and install only on boundary confirm; oversized snapshot rejected without partial install; commit order receive → validate → offer → persist → confirm; transport receipt never reported as committed; routing to exactly the targeted subscription; per-stream termination without ending the connection; explicit re-establishment after reconnect; bound fixtures at exactly maximum and maximum-plus-one; overflow to explicit continuity loss with a new generation; authorization hooks at subscribe, replay, snapshot, continuation, catch-up, and confirm; revoked or expired principal stops delivery with a typed signal; rejections leak no credentials; reserved values untouched; mandatory-only peer interoperates with a profile-confirming peer at mandatory behavior.
