# RFC 0006: Update/Recovery Profile — Optional Wire, Required Release Target

- RFC: 0006
- Title: Negotiated Update/Recovery Profile for ordered delivery, replay, snapshot recovery, and committed progress
- Author(s): Pending — assigned via the acceptance PR (disclosed self-approval per GOVERNANCE.md Sec. 3)
- Status: Accepted
- Date: 2026-10-21
- Target version: v1 minor (required in the proposed release bundle; optional negotiated wire profile; no envelope changes)
- Decision amendment: 2026-10-28, §11 (adoptive); consolidated into §§1–10 at acceptance 2026-10-30
- Relates to: `specifications/core/events.md` (§§1, 1A–1J, 1L–1M), `specifications/core/reliability.md` (SNTR-REL-001–010), `specifications/core/capabilities.md` (SNTR-CAP-001–007), `specifications/architecture.md` (SYN-ARCH-001/002/010–013/020/021/030–035/040–045/050/051/060–062), `specifications/core/open-questions.md` (blockers 1–3, deferred items 5–7), `rfcs/0005-negotiation-bounds-identifiers.md` (D1 binding), `proto/syntra/v1/envelope.proto` (`Frame`, reserved values)
- Reviewers: Pending — assigned via the acceptance PR (disclosed self-approval per GOVERNANCE.md Sec. 3)

> Accepted 2026-10-30 via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)
> (disclosed self-approval; sole active maintainer per `GOVERNANCE.md` Sec. 3),
> with §11 as the governing decision amendment and §§1–10 consolidated to
> agree with it. Implementation MUST remain conformance evidence under the
> frozen revision; release authorization additionally requires the §11.9
> gates, which stay open. BCP 14 keywords carry normative force. Examples
> are neutral only: echo, generic key/value, generic subscription.

> Amendment reading rule: §11 records the decision amendment (2026-10-28).
> At acceptance, §§1–10 have been consolidated so their body text agrees with
> §11 wherever they overlapped; §11 remains the audited decision history for
> each change. The owning profile, IDL comments, and registered recovery
> manifest cases have been aligned to §11 in the acceptance PR (registration
> is not execution). The
> [acceptance plan](../conformance/plans/update-recovery.md) remains prose:
> not an executable or registered conformance-manifest run.

## 1. Summary

This RFC proposes an optional Syntra Update/Recovery Profile that
standardizes ordered delivery, bounded replay, snapshot recovery,
committed progress, flow control, and authorization lifecycle for
independent logical streams. The profile is opt-in and negotiated after
ACTIVE through a standardized generic RPC. All versioned profile
payloads travel inside the existing `RpcRequest` / `RpcResult` /
`Notification` envelopes with no `Frame` changes. It affects
initiators and hosts that confirm the profile, transport adapters only
as opaque carriers, and conformance only through additive fixtures;
mandatory-only peers are unaffected.

The proposed release target requires standardized recovery support and
acceptance evidence as part of its release bundle (§11.1). This release
inclusion requirement does not make recovery mandatory on every connection
or a condition of a Core-only conformance claim.

## 2. Motivation

The current suite defines generic host-to-initiator push with
at-most-once, unordered-by-default delivery, optional replay described
only as application-defined behavior, opaque continuation state with no
standard predecessor/result semantics, no standard catch-up boundary or
completion signal, no snapshot transfer/installation contract, no
standard committed-progress sequence, and no separation of connection
state from per-stream state beyond defaults (re-subscribe after
reconnect, no continuity by default).

Consequences: every deployment that needs ordered recovery re-invents
continuation handling, paging, catch-up coordination, snapshot
fallback, commit confirmation, routing/termination scope, bounds, and
authorization points. Those inventions diverge on duplicate handling,
gap signaling, overflow behavior, and revocation timing, so initiators
cannot interoperate across hosts and conformance cannot assert recovery
behavior.

This profile standardizes one optional recovery contract on top of the
existing envelopes so that confirming peers share generations,
checkpoints, bounded pages, catch-up and snapshot signals, commit
order, routing scope, bounds, and authorization hooks, while
non-confirming peers keep full mandatory-only interop.

## 3. Proposal

Normative rule: the profile is OPTIONAL, capability-gated, and
additive. A minimal implementation supporting only handshake, RPC,
cancel, and typed errors MUST interoperate with a profile-confirming
peer at mandatory-only behavior. Unnegotiated use MUST fail; no
mandatory state machine, envelope validation rule, or error semantic
changes.

- New/changed requirements with IDs (prefix `SYN-URP`):

  - Initiator obligations:
    - `SYN-URP-001` — The initiator MUST NOT use any profile operation,
      except the standardized profile negotiation invocation after ACTIVE,
      before the profile capability is confirmed for the connection. The
      initiator MUST negotiate the profile after ACTIVE through the
      standardized generic RPC defined by this profile, MUST handle
      partial acceptance by falling back to mandatory-only operation
      (plus any previously confirmed options), and MUST NOT send profile
      payloads for an unconfirmed capability. The negotiation invocation
      itself is the only permitted profile operation before confirmation.
    - `SYN-URP-002` — The initiator MUST treat every profile payload as
      versioned bytes carried inside existing `RpcRequest.payload`,
      `RpcResult.payload`, or `Notification.payload`. The initiator MUST
      NOT require any new `Frame` body variant, field number, or field
      name, and MUST preserve and respect reserved numbers 16, 17 and
      reserved names `event`, `resume`, `ack`.
    - `SYN-URP-003` — The initiator MUST treat each subscription as one
      independent logical stream. The initiator MUST track one
      continuity generation per stream, MUST treat checkpoints as opaque
      bytes, MUST present exact checkpoint bytes with explicit
      predecessor/result pairing, and MUST NOT perform arithmetic on
      checkpoint bytes (no increment, decrement, ordering inference, or
      structural parsing).
    - `SYN-URP-004` — The initiator MUST consume bounded replay pages,
      MUST follow the page continuation marker, MUST stop at the
      catch-up boundary, MUST apply the same validation pipeline to
      recovered batches and live batches, and MUST tolerate duplicates
      across the recovered/live boundary without treating a duplicate as
      a violation.
    - `SYN-URP-005` — The initiator MUST follow the commit sequence
      receive → validate → offer → persist → confirm: receive the batch,
      validate it through the same pipeline as live batches, offer it to
      the application above Syntra, persist the resulting checkpoint
      through the application persistence point, and only then confirm
      the checkpoint through the defined generic RPC. Transport receipt
      or envelope decode MUST NOT be reported as committed progress or
      as application success.
    - `SYN-URP-006` — The initiator MUST route each received batch to
      exactly the subscription whose opaque handle it accompanies, MUST
      keep connection state separate from per-stream state, MUST tear
      down only the targeted subscription on a per-stream terminal
      signal, and MUST re-establish subscriptions explicitly after the
      connection ends with a fresh connection-scoped handle and no
      implicit continuity, resuming only from its locally durable
      known-safe checkpoint bytes (which may be newer than the last
      peer-acknowledged checkpoint; §11.6) bound to the same stable
      stream identity where the stream specification permits. The host
      MAY accept a valid checkpoint without a previous confirmation
      record; validation of an issued checkpoint is distinct from
      accepting an unoffered confirm (§11.6).
    - `SYN-URP-007` — The initiator MUST enforce its bounds (pending
      calls, subscriptions, queued bytes, page sizes), MUST back off on
      `RESOURCE_EXHAUSTED`, MUST treat subscriber-local saturation as a
      subscriber-local failure per §11.4 — ending the affected
      subscription / reporting local recovery-needed via
      `RecoveryBatchTrailer{terminated=true}` with ASCII
      `terminate_reason=local-queue-exhausted` at the UNCHANGED current
      generation, without manufacturing a provider `next_generation` —
      and MUST NOT silently accept truncated history as complete. Local
      saturation MUST NOT increment the shared generation: it cannot
      rebase the provider or invalidate another subscriber's
      checkpoint.

  - Host obligations:
    - `SYN-URP-010` — The host MUST confirm the profile only where it
      implements it for the bound principal, MUST confirm per
      connection (confirmation on one connection MUST NOT enable the
      profile on another), MUST document the confirmed profile version
      and bounds per deployment, MUST accept the standardized profile
      negotiation invocation after ACTIVE before confirmation where the
      host implements the profile, and MUST reject other unnegotiated
      profile use with `UNIMPLEMENTED` (unknown or unconfirmed operation) or
      `FAILED_PRECONDITION` (use of an unconfirmed option on a confirmed
      connection). The negotiation invocation itself is the only permitted
      profile operation before confirmation.
    - `SYN-URP-011` — The host MUST implement negotiation, subscribe,
      replay, catch-up, snapshot, continuation, confirm, and terminate
      operations as standardized generic RPCs with versioned payloads
      inside existing envelopes. The host MUST NOT add envelope fields,
      MUST NOT reuse reserved numbers 16, 17 or reserved names `event`,
      `resume`, `ack`, and MUST keep unknown profile fields ignored on
      receipt where explicitly marked ignorable, rejecting unknown
      profile operations with `UNIMPLEMENTED`. Full wire policy is in
      `SYN-URP-021`.
    - `SYN-URP-012` — The host MUST maintain independent logical streams
      per confirmed subscription within the authenticated principal
      scope P, MUST assign one continuity generation G per stable stream
      identity S within that scope, MUST increment G only on a true
      provider history loss for (P, S) or an explicit shared rebase
      (§11.2) — NOT on subscriber-local saturation (§11.4), NOT on
      ordinary retention-window pruning, and NOT on revocation alone
      (§11.2) — and MUST bind every checkpoint C to exactly the
      principal-scope, stable stream identity, and generation tuple
      (P, S, G). The stable stream identity
      is the stream selected by the stream selector and persists across
      reconnects, separate from the connection-scoped subscription
      handle which is fresh per subscription. A checkpoint from a prior
      subscription for the same stable identity MAY resume while the
      generation is still valid — including through §11.6 reconnect
      with a fresh handle — and the host MAY accept it without a prior
      confirmation record; checkpoints whose generation no longer
      matches the current (P, S, G) binding MUST be rejected with
      `FAILED_PRECONDITION`, never reinterpreted under the new generation.
    - `SYN-URP-013` — The host MUST emit opaque checkpoints with explicit
      predecessor/result semantics on every batch: each batch states the
      predecessor checkpoint it continues from and the result checkpoint
      it advances to. The host MUST NOT require the initiator to compute
      a successor, and MUST reject forged, malformed, cross-stream,
      cross-generation, or cross-principal checkpoint bytes with
      `FAILED_PRECONDITION` (or `UNAUTHENTICATED` where token-like)
      without leaking other principals' stream state.
    - `SYN-URP-014` — The host MUST return bounded replay pages, each
      page stating its continuation marker and the catch-up boundary.
      Oversized history MUST be paged, never burst beyond the documented
      per-connection and per-subscription queue bounds. The host MUST
      stream RPC-triggered catch-up over the existing connection as
      `Notification` batches through the same validation and
      authorization path as live batches.
    - `SYN-URP-015` — The host MUST emit an explicit catch-up completion
      signal when the stream reaches live, and MUST fail the replay/catch-up
      invocation with `FAILED_PRECONDITION` in `RpcResult` while emitting an
      explicit snapshot-required signal as `RecoveryBatchTrailer{snapshot_required=true}`
      in a `Notification` payload when the requested checkpoint is outside
      retention or otherwise unrecoverable by replay. Silent restart from an
      unrelated point is forbidden; silent truncation without the documented
      signal is forbidden.
    - `SYN-URP-016` — The host MUST implement the snapshot
      transfer/installation contract through generic RPCs in bounded
      pages: offer a snapshot under a provider-proven boundary
      checkpoint, transfer pages the initiator can store without
      interpreting, and mark installation complete only when the
      initiator confirms the boundary checkpoint through the defined
      confirm operation. The boundary MUST be proven by the provider
      (the host application supplying the snapshot), meaning subsequent
      batches MUST chain from exactly that boundary checkpoint and MUST
      be rejected otherwise. Snapshot formats remain provider-defined;
      Syntra defines only the transfer, boundary, and confirmation
      mechanics.
    - `SYN-URP-017` — The host MUST route every batch to exactly one
      targeted subscription, MUST terminate only the targeted
      subscription on per-stream termination (with a typed terminal
      signal inside a profile payload or RPC error where possible),
      MUST NOT end the connection to terminate one stream except where
      the connection itself ends, and MUST keep connection state
      (ACTIVE/CLOSING, principal binding, confirmed capabilities)
      separate from per-stream state (handle, generation, checkpoint,
      catch-up phase, routing entry).
    - `SYN-URP-018` — The host MUST bound all profile resources and
      document every bound: maximum subscriptions per connection and per
      principal, maximum pending profile RPCs per connection, maximum
      queued `Notification` bytes per stream and per connection,
      maximum replay page batches and bytes, maximum snapshot page bytes
      and total pages, and effective deadlines for profile RPCs. On
      subscriber-local saturation the host MUST apply §11.4: reject new
      work with `RESOURCE_EXHAUSTED` before or after subscription
      acceptance, and for a saturated accepted subscription end ONLY the
      affected subscription with `RecoveryBatchTrailer{terminated=true}`
      and ASCII `terminate_reason=local-queue-exhausted` at the CURRENT
      generation, carrying NO `next_generation` — the initiator cannot
      manufacture a provider `next_generation` — while provider-side
      history loss invalidates the scoped (P, S, G) binding itself via a
      next_generation trailer per §11.2. The host MUST NOT queue without
      bound and never deadlock silently.
    - `SYN-URP-019` — The host MUST authorize the bound principal at
      every profile authorization hook: subscribe, replay, snapshot
      offer/transfer, and continuation/catch-up/confirm. The host MUST
      NOT emit batches for a revoked or expired principal and MUST
      terminate affected subscriptions with a typed signal where
      possible. Credential bytes MUST be treated as opaque sensitive
      bytes: never logged, never persisted by the core, never placed in
      error detail.
    - `SYN-URP-020` — Negotiation-version enforcement: the host MUST
      select the maximum version it implements within the initiator
      offered range in `RecoveryNegotiateRequest`, MUST confirm only
      that selected version in `RecoveryNegotiateResponse`, and MUST
      fail no overlap with `FAILED_PRECONDITION` in `RpcResult`. Both
      peers MUST carry the confirmed `profile_version` on every other
      profile payload; mismatch or missing version MUST fail with
      `FAILED_PRECONDITION`.
    - `SYN-URP-021` — Unknown-field/profile handling consistent with
      `specifications/core/serialization.md` (`SNTR-SER-003`) and
      `specifications/core/versioning.md` (`SNTR-VER-004`): unknown
      Protobuf fields inside profile payloads MUST be ignored on
      receipt unless explicitly marked `Critical` in
      `proto/syntra/v1/recovery_profile.proto`; fields explicitly
      marked `Ignorable` MUST be ignored; `profile_version` and
      routing/identity fields (`stream_selector`,
      `subscription_handle`, `snapshot_handle`, `capability`, versions)
      are required and missing/mismatched MUST fail with
      `FAILED_PRECONDITION`, never
      silently applied. Checkpoints, boundaries, and markers follow their
      per-field rules: empty `start_checkpoint` means initial subscription;
      empty `continuation_marker` means first request or no further page;
      `terminate_reason` is non-empty only for the terminated outcome.
      Other checkpoint/boundary presence and pairing follow the field comments
      and `SYN-URP-013`/`SYN-URP-023`/`SYN-URP-024`.
      Unknown profile operations MUST be rejected
      with `UNIMPLEMENTED`.
    - `SYN-URP-022` — Replay continuation echo and idempotent retry:
      replay applies only to resumption from a non-empty
      `start_checkpoint`. When subscribe used an empty
      `start_checkpoint` (initial subscription) the initiator MUST NOT
      send `RecoveryReplayRequest` and MUST start live at the
      subscribed boundary B on completion (or follow the snapshot path
      if signaled). For resumption, the initiator MUST send an empty
      `continuation_marker` on the first `RecoveryReplayRequest` with
      `from_checkpoint` set to its locally durable known-safe checkpoint
      per §11.6 (non-empty; it may be newer than the last peer-acknowledged
      checkpoint), and MUST echo the previous page's marker verbatim
      with `from_checkpoint` equal to the previous page's
      `result_checkpoint` on each continuation. The host MUST reject a
      request whose marker does not match the last issued marker for the
      stream and generation, or whose `from_checkpoint` does not chain
      from the previous result, with `FAILED_PRECONDITION`, except that
      the host MUST retain the last issued `RecoveryReplayPage` per
      subscription and generation and MUST return it verbatim without
      advancing when a request duplicates the immediately preceding
      completed request (identical payload in the current generation),
      so a retry after an unknown RPC outcome (`UNAVAILABLE`,
      `DEADLINE_EXCEEDED`, or loss with unknown outcome per
      `SNTR-REL-003`/`SNTR-REL-009`) is safe with a fresh `request_id`.
      The host MUST clear the retained page on generation increment,
      stream termination, or supersede, and MUST NOT advance pagination
      on a duplicate.
    - `SYN-URP-023` — Subscribe boundary presence: the host MUST return a
      non-empty `catchup_boundary` in `RecoverySubscribeResponse` fixed
      at subscribe accept. Both peers MUST treat an empty boundary as
      omitted and MUST reject it with `FAILED_PRECONDITION`; the
      initiator MUST validate each `RecoveryReplayPage.catchup_boundary`
      and each catch-up completion signal boundary
      (`RecoveryReplayComplete.live_boundary_checkpoint`,
      `RecoveryBatchTrailer.boundary_checkpoint` when `catchup_complete`,
      `RecoveryCatchUpAccepted.catchup_boundary`) against the subscribed
      boundary and MUST NOT release held live batches on mismatch;
      mismatch MUST be rejected with `FAILED_PRECONDITION` (or treated
      locally as recovery-needed) without releasing held batches.
    - `SYN-URP-024` — Initial live-baseline bootstrap, fresh-handle
      recovery rounds, and lost-completion handling: initial
      subscriptions with an empty `start_checkpoint` MUST skip `Replay`
      and start live at the newly captured boundary B on validated
      completion (or follow the snapshot path if `snapshot_required` is
      signaled); resumption with a non-empty `start_checkpoint` (the
      initiator's durable known-safe checkpoint, §11.6) MUST replay
      from that checkpoint per `SYN-URP-022` while holding live batches
      until the validated completion signal at B. Every round binds to
      exactly one connection-scoped handle H and the boundary B captured
      by its Subscribe; the host does not reuse a retired handle within
      a connection, and boundary equality does not identify a round.
      After a round completes, a new gap or loss means the initiator
      retires H locally, clears its held queue, and calls Subscribe for
      a fresh handle and newly captured boundary — never replaying
      toward the obsolete boundary; held batches release only after a
      validated completion matching connection, handle, generation,
      version, and the exact boundary B of the round. On a lost
      completion (unknown RPC outcome, `UNAVAILABLE`,
      `DEADLINE_EXCEEDED`, or loss per `SNTR-REL-003`/`SNTR-REL-009`)
      the initiator performs bounded exact retries with fresh
      `request_id` against the same round; the host re-emits the same
      completion with no new side effects. On exhaustion the initiator
      retires H and starts a fresh round from its durable known-safe
      checkpoint; no same-handle second round or marker reset is
      permitted. A round chooses `Replay` or `CatchUp`, never both
      concurrently; `CatchUp` streams from the start checkpoint already
      bound by Subscribe and its request carries no new checkpoint
      field. The initiator MUST NOT treat idle as caught-up; the
      initiator MUST NOT release held batches without a validated
      completion signal. Duplicate completion signals with equal
      boundary bytes are tolerated idempotently; mismatched completion
      MUST NOT release held batches.
    - `SYN-URP-025` — Snapshot transfer/installation and confirm-retry
      fencing: the snapshot descriptor binds the offered snapshot X to
      (P, S, H, G, S0) — the subscribed principal scope, stable stream
      identity, subscription handle, current generation, and the exact
      offered boundary checkpoint; at most one distinct snapshot is
      offered under H, and superseding an offer retires H and requires a
      fresh Subscribe before a new snapshot is issued, even if the new
      boundary equals S0 and G is unchanged. In-flight `SnapshotFetch`
      under a superseded `snapshot_handle` MUST fail with
      `FAILED_PRECONDITION`, and the initiator MUST discard prior pages on
      supersede and MUST NOT install across boundaries. The
      `RecoverySnapshotComplete` record has NO wire transmission — the
      amendment defines no method, result slot, or `RecoveryNotification`
      arm for it; completion is a peer-local transfer/installation
      record (§11.5). Installation is application-local: it occurs at
      the SAME generation G, does NOT rebase the shared provider stream,
      and does NOT change G; subsequent checkpoints chain from the
      installed S0 within the same generation, and
      `RecoverySnapshotInstalled` carries the current generation with
      no replacement token. Confirm is
      idempotent with stop-and-wait fencing: re-presenting the same batch
      checkpoint bytes in the same generation (`RecoveryConfirmRequest`)
      MUST return `RecoveryConfirmResponse` without new side effects or
      generation change. Snapshot-boundary confirmation uses the distinct
      `/syntra.v1.UpdateRecovery/SnapshotConfirm` method. First install
      requires the exact offered S0 and the CURRENT generation. An exact
      duplicate `RecoverySnapshotConfirmRequest` for the same
      authorized subscription and profile version, carrying the CURRENT
      generation and installed boundary bytes, MUST return the original
      retained `RecoverySnapshotInstalled` without reinstalling or further
      generation change, only while the response is retained. Supersede
      (which retires H), termination, a later continuity change that
      increments G, or retention expiry invalidates this narrow
      exception: on expiry or exhaustion the initiator reconnects per
      §11.6 (fresh authenticated connection, re-negotiation, fresh
      handle and boundary) — it MUST NOT fabricate a pre-install or
      otherwise obsolete-generation retry. Other stale-generation
      requests MUST fail with
      `FAILED_PRECONDITION`. Boundary equality alone does not establish
      retry eligibility. Retention is bounded in count, bytes, and lifetime
      and documented by the deployment; the accepted contract sets no implicit minimum.
      A checkpoint never returned as committable MUST be rejected with
      `FAILED_PRECONDITION`
      without advancing; gap, true provider continuity loss, and continuation-expiry
      reports invalidate any pending offer. Snapshot-held batches release
      only after the same validated round completion as replay-held
      batches: old replay completions cannot release snapshot-held
      batches; if catch-up is still needed after installation, it uses a
      fresh handle and freshly captured boundary via a new Subscribe
      (§11.3/§11.5).
    - `SYN-URP-026` — Subscriber-local versus shared generation
      invalidation and revocation behavior: a generation increment G→G′
      for a stable stream identity S in principal scope P signals ONLY
      a true provider history loss for (P, S) or an explicit shared
      rebase (§11.2), streamed to affected subscribers with a trailer
      carrying the old generation and the `next_generation`; ordinary
      retention-window pruning does not increment G, subscriber-local
      saturation does not increment G (§11.4), and revocation alone is
      targeted termination, not a reset. A provider loss spanning
      several principal scopes invalidates every affected scope
      explicitly. The host MUST re-evaluate the bound
      principal at every authorization hook, MUST NOT emit batches for a
      revoked or expired principal, and MUST terminate affected subscriptions
      with a typed signal (`RecoveryBatchTrailer{terminated=true}` with
      `terminate_reason` or a typed invocation error) where possible. A
      revocation is targeted termination: it MUST NOT manufacture a
      generation increment, and the host MUST NOT
      leak other principals' stream state or place credentials in error
      detail; if deployment policy also invalidates the revoked
      principal's recovery history, the host changes only that scoped
      (P, S, G) binding — a regrant never revives an invalidated
      binding.

- Methods and payload mapping (accepted mapping; §11 confirmation):
  At acceptance the operations, method strings, payload mapping, and
  per-field semantics below are the accepted contract for the
  negotiated profile. All versioned profile payloads travel inside the existing
  `RpcRequest` / `RpcResult` / `Notification` envelopes with no
  `Frame` changes. Neutral examples only: echo, generic key/value,
  generic subscription. Stream selectors name generic subscriptions;
  batch payloads carry echo or generic key/value bytes; subscription
  handles route generic subscription batches.

  | Operation | Method string | Request payload | Result / stream payloads |
  |---|---|---|---|
  | Negotiate | `/syntra.v1.UpdateRecovery/Negotiate` | `RecoveryNegotiateRequest` (`profile_version`, `min_version`, `max_version`, `capability` `syntra.update-recovery/1`) | `RecoveryNegotiateResponse` (`selected_version` plus confirmed bounds) |
  | Subscribe | `/syntra.v1.UpdateRecovery/Subscribe` | `RecoverySubscribeRequest` (`profile_version`, `stream_selector` for a generic subscription, `start_checkpoint`) | `RecoverySubscribeResponse` (`profile_version`, `subscription_handle`, `generation`, `catchup_boundary`) |
  | Replay | `/syntra.v1.UpdateRecovery/Replay` | `RecoveryReplayRequest` (`profile_version`, `subscription_handle`, `from_checkpoint`, `max_batches` 1..64, `max_bytes` 1..262144, `continuation_marker` empty on first request, echo of previous page's marker thereafter) | exactly one `RecoveryReplayPage` per `RpcResult` plus continuation marker; completion as `RecoveryReplayComplete` or `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification` payload |
  | CatchUp | `/syntra.v1.UpdateRecovery/CatchUp` | `RecoveryCatchUpRequest` (`profile_version`, `subscription_handle`) | `RecoveryCatchUpAccepted` in the terminal `RpcResult`; `RecoveryBatch` plus `RecoveryBatchTrailer{catchup_complete=true}` streamed as `Notification` payloads over the existing connection |
  | Confirm (batch) | `/syntra.v1.UpdateRecovery/Confirm` | `RecoveryConfirmRequest` (`profile_version`, `subscription_handle`, `generation`, `checkpoint` batch result) | `RecoveryConfirmResponse` (`confirmed_checkpoint`, `generation` unchanged; idempotent retry echoes same bytes) |
  | Confirm (snapshot boundary) | `/syntra.v1.UpdateRecovery/SnapshotConfirm` | `RecoverySnapshotConfirmRequest` (`profile_version`, `subscription_handle`, CURRENT `generation`, `boundary_checkpoint` must equal offered S0; exact retained-install retry per `SYN-URP-025`) | `RecoverySnapshotInstalled` (`boundary_checkpoint`, the unchanged CURRENT generation after install; original retained response on retry) |
  | SnapshotOffer | `/syntra.v1.UpdateRecovery/SnapshotOffer` | `RecoverySnapshotOfferRequest` (`profile_version`, `subscription_handle`, `generation` at offer time) | `RecoverySnapshotDescriptor` (`snapshot_handle`, provider-proven `boundary_checkpoint`, `total_pages` 1..256, `page_bytes_max` 1..262144) |
  | SnapshotFetch | `/syntra.v1.UpdateRecovery/SnapshotFetch` | `RecoverySnapshotFetchRequest` (`profile_version`, `snapshot_handle`, `page_index` 0..255) | exactly one `RecoverySnapshotChunk` per `RpcResult` with `page_index` correlation plus `boundary_checkpoint` equality. `RecoverySnapshotComplete` has NO wire transmission (§11.5): completion is a peer-local transfer/installation record with no method, result slot, or `RecoveryNotification` arm |
  | Unsubscribe | `/syntra.v1.UpdateRecovery/Unsubscribe` | `RecoveryUnsubscribeRequest` (`profile_version`, `subscription_handle`) | `RecoveryUnsubscribeResponse` (`profile_version`, `subscription_handle`, `generation` at termination); targeted `RecoveryBatchTrailer{terminated=true}` with `terminate_reason` where applicable |

  Response framing rule (accepted; §11.3): each Replay
  call returns exactly one `RecoveryReplayPage` in its `RpcResult` plus
  its continuation marker — NEVER a page `Notification` — and the
  initiator paginates with the same
  `/syntra.v1.UpdateRecovery/Replay` method until the marker is empty.
  Replay is sent only for resumption; initial subscriptions (empty
  `start_checkpoint`) skip Replay and start live at B on completion.
  The first `RecoveryReplayRequest` carries an empty `continuation_marker`
  with `from_checkpoint` set to the initiator's durable known-safe
  checkpoint per §11.6 (non-empty); each
  continuation carries `continuation_marker` equal verbatim to the previous
  page's marker with `from_checkpoint` equal to the previous page's
  `result_checkpoint` (`SYN-URP-022`). The host MUST reject a non-empty marker that does
  not match the last issued marker for the stream and generation, or a
  `from_checkpoint` that does not chain from the previous result, with
  `FAILED_PRECONDITION` (`SYN-URP-022`), except for an idempotent duplicate
  of the immediately preceding completed request (identical payload in the
  current generation), for which the host MUST return the retained page
  verbatim without advancing so unknown-outcome retries stay safe
  (`SYN-URP-022`).
  Completion arrives separately as `RecoveryReplayComplete` or as a
  trailer `Notification` carrying `RecoveryBatchTrailer`. Each
  SnapshotFetch call returns exactly one `RecoverySnapshotChunk` per
  `RpcResult` with `page_index` correlation; the same one-response-per-call
  rule applies to both Replay and SnapshotFetch.

  Notification discriminator rule (accepted): every
  profile `Notification.payload` carries exactly one versioned
  `RecoveryNotification` (`profile_version=1` outer must equal inner
  payload version) with exactly one of `batch` (`RecoveryBatch`),
  `replay_complete` (`RecoveryReplayComplete`), or `trailer`
  (`RecoveryBatchTrailer`) selected. An unset `notification` outcome is
  representable by codecs but is not valid and MUST be rejected with
  `FAILED_PRECONDITION`. `RpcResult` payloads stay bare typed messages
  per the table above — including replay pages (§11.3). No `Frame` field
  is added or renumbered; reserved
  16, 17 and `event`, `resume`, `ack` are preserved. All nine method
  strings are canonical `/package.Service/Method` paths with exactly two
  slashes per `SNTR-RPC-001`; any other shape MUST be rejected with
  `INVALID_ARGUMENT` before dispatch and MUST NOT be treated as a profile
  operation.

  Version negotiation rule (accepted; `SYN-URP-020`/`SYN-URP-021`): every profile payload carries
  `profile_version=1` in this draft. The Negotiate invocation carries
  `RecoveryNegotiateRequest` offering min and max versions (proposing
  1/1) with `capability` `syntra.update-recovery/1`; the host selects
  the maximum version it implements within the offered range and
  confirms it in `RecoveryNegotiateResponse`. No overlap MUST fail
  with `FAILED_PRECONDITION` in `RpcResult`. Any other operation
  carrying a `profile_version` outside the confirmed version MUST fail
  with `FAILED_PRECONDITION`. Wire policy defers to
  `specifications/core/serialization.md` (`SNTR-SER-003`) and
  `specifications/core/versioning.md` (`SNTR-VER-004`): unknown
  Protobuf fields inside profile payloads MUST be ignored unless
  explicitly marked `Critical`; fields explicitly marked `Ignorable`
  in `proto/syntra/v1/recovery_profile.proto` MUST be ignored;
  `profile_version` and routing/identity fields are required and
  missing/mismatch MUST fail with `FAILED_PRECONDITION`; checkpoint,
  boundary, and marker emptiness follows per-field rules in `SYN-URP-021`
  and the IDL, including initial-subscribe and pagination sentinels; unknown
  profile operations MUST be rejected with `UNIMPLEMENTED`, never
  silently applied.

- Schema diff (`.proto` snippet, field numbers, reserved handling):
  The IDL
  (`proto/syntra/v1/recovery_profile.proto`) is complete in the tree;
  acceptance covers its message set and semantic comments as aligned to
  §11.8 in the acceptance PR (registration is not execution; generated
  codecs alone do not enforce the contract). The change is additive and envelope-neutral:
  `proto/syntra/v1/recovery_profile.proto` adds profile payload messages
  carried inside the existing `request`
  (field 12), `result` (field 13), and `notification` (field 15) variants
  exactly as defined in `proto/syntra/v1/envelope.proto`. No `Frame`
  field is added, deprecated, or renumbered. Reserved numbers 16, 17 and
  reserved names `event`, `resume`, `ack` are preserved unchanged and
  MUST NOT be reused by this profile. Profile versioning lives inside
  the opaque payload bytes (a profile payload version field defined by
  this profile), not in `Frame.version`.

- State machine deltas (success + failure transitions):
  The connection handshake and ACTIVE/CLOSING/CLOSED transitions are
  unchanged. This profile adds one per-stream machine per confirmed
  subscription; connection end discards all per-stream state:
  - `SUBSCRIBED → CATCHING_UP` on subscribe confirm with fixed
    catch-up boundary B captured at subscribe accept and carried in
    `RecoverySubscribeResponse.catchup_boundary`; for resumption the initiator replays
    from its durable known-safe checkpoint via
    `RecoveryReplayRequest.from_checkpoint` (non-empty; initial subscriptions with empty
    `start_checkpoint` skip replay and start live at B on completion)
    and validates each `RecoveryReplayPage.catchup_boundary` and each
    completion signal boundary against B before releasing held live batches;
    live `Notification`
    batches for the stream held until the catch-up completion signal
    under bounded holding per the documented overflow policy
    (while held during CATCHING_UP, subscriber-local saturation MUST
    end ONLY the affected subscription with
    `RecoveryBatchTrailer{terminated=true}` and ASCII
    `terminate_reason=local-queue-exhausted` at the UNCHANGED current
    generation - no `next_generation`, no shared rebase, and no other
    subscriber's checkpoint is invalidated (11.4) - never a bare
    `RESOURCE_EXHAUSTED` that stalls waiting for an
    unreachable completion signal; outside holding, reject with
     `RESOURCE_EXHAUSTED` and/or a targeted `terminated=true`
     trailer with ASCII `terminate_reason` (§11.4), never silent drop);
    `CATCHING_UP → LIVE` on catch-up
    completion signal with held then new live batches chaining from B;
    `CATCHING_UP → SNAPSHOT_REQUIRED` on
     snapshot-required signal; `SNAPSHOT_REQUIRED → INSTALLING` on
    accepted snapshot offer; `INSTALLING → LIVE` on boundary confirm
    (installation is application-local at the same generation G;
    §11.5); any streamed state → `TERMINATED(targeted)` on per-stream terminal
     signal or terminate operation; `cancel` applies to the invoking RPC
    only and does not by itself terminate the stream unless the confirmed
    stream binding states so; any streamed state → `PROVIDER_LOST(old
    generation G, next_generation G′)` ONLY on a trailer streamed by the
    host for a true provider history loss of (P, S) or an explicit
    shared rebase (§11.2), then re-entry via a fresh Subscribe (fresh
    handle H′ and newly captured boundary) from the initiator's durable
    known-safe checkpoint where valid under G′. Subscriber-local
    saturation is NOT a provider-loss transition (§11.4): it uses the
    targeted `terminated` path with `local-queue-exhausted` at the
    unchanged generation. A lost completion does not itself transition
    the stream: the initiator either performs its bounded exact retries
    of the round's completion or exhausts them, retires the handle, and
    runs a fresh Subscribe/round from its durable known-safe checkpoint
    (§11.3).
  - Failure transitions are terminal for the affected RPC or stream,
    not the connection, unless the connection itself is exhausted,
    violated, or revoked: unknown operation → `UNIMPLEMENTED`;
    unconfirmed-option use → `FAILED_PRECONDITION`; unauthorized →
    `PERMISSION_DENIED` / `UNAUTHENTICATED` plus targeted termination;
    stale/cross-generation checkpoint → `FAILED_PRECONDITION`;
    overload → `RESOURCE_EXHAUSTED` plus documented backoff;
    transport loss → `UNAVAILABLE` to in-flight profile RPCs with
    unknown outcome; deadline expiry → `DEADLINE_EXCEEDED`.

- Configuration and defaults (timeouts, limits, sizes):
  Every bound is deployment-documented; the following are the accepted
  profile defaults matching `proto/syntra/v1/recovery_profile.proto`
  header defaults (adopted at acceptance; §10 items 1–2 record the
  adoption):
  - Maximum subscriptions per connection: 64; per principal: 256.
  - Maximum pending profile RPCs per connection: 16.
  - Maximum queued `Notification` bytes per stream: 256 KiB; per
    connection aggregate: 1 MiB.
  - Maximum replay page: 64 batches and 256 KiB, whichever binds first;
    continuation required beyond that.
  - Maximum snapshot page: 256 KiB; maximum pages per snapshot offer:
    256 (larger snapshots REQUIRE a fresh offer with a new boundary).
  - Effective deadline default for profile RPCs: 5 s where the
    `RpcRequest` carries no explicit bounded deadline; every profile RPC
    MUST have an effective deadline and MUST surface expiry as
    `DEADLINE_EXCEEDED`.
  - Retention minimum for replay where replay is offered: documented per
    deployment; no implicit minimum is assumed by initiators.

Include a sequence diagram for behavioral changes:

```text
Initiator                              Host
    |                                     |
    |--- request{negotiate profile v1} -->|
    |<-- result{confirmed v1 + bounds} ----|
    |--- request{subscribe generic} ----->|
    |<-- result{opaque handle H, gen 7,   |
    |         newly captured fixed B} ----|
    |         (live batches held until    |
    |          catch-up done; bounded      |
    |          holding; saturation ends    |
    |          only the subscription with  |
    |          terminated trailer at gen 7)|
    |--- request{replay from durable CDC} |
    |                                   -->|
    |<-- result{one replay page + marker} -|
    |<-- result{one replay page + marker} -|
    |<-- notification{catch-up done} ------|
    |<-- notification{held then new live  |
    |         batch from B} ---------------|
    |--- request{confirm checkpoint D} --->|
    |<-- result{confirmed D} --------------|
    |--- request{catch-up trigger} ------->|
    |<-- result{accepted with B} ----------|
    |<-- notification{recovered batch} -----|
    |<-- notification{catch-up done} ------|
    |<-- notification{live batch from B} --|
    |<-- notification{snapshot-required} --|
    |--- request{snapshot offer} --------->|
    |<-- result{snapshot descriptor binds  |
    |         (P,S,H,G,S0), proven by      |
    |         provider} -------------------|
    |--- request{snapshot fetch page} ---->|
    |<-- result{one chunk per call} -------|
    |--- request{confirm boundary at gen 7}|
    |<-- result{installed at gen 7; no G   |
    |         change (11.5)} --------------|
```

## 4. Detailed design

Mechanics: framing, encoding, correlation, cancellation, error mapping,
capability negotiation, unknown-field/profile handling, resource bounds.

- Framing: unchanged. The profile adds no transport framing and no
  envelope variant. Existing length/type prefixes and envelope
  validation apply unmodified.
- Encoding: profile control operations use standardized generic RPC
  methods under the profile identifier
  (`/syntra.v1.UpdateRecovery/Negotiate`,
  `/syntra.v1.UpdateRecovery/Subscribe`,
  `/syntra.v1.UpdateRecovery/Replay`,
  `/syntra.v1.UpdateRecovery/CatchUp`,
  `/syntra.v1.UpdateRecovery/Confirm`,
  `/syntra.v1.UpdateRecovery/SnapshotConfirm`,
  `/syntra.v1.UpdateRecovery/SnapshotOffer`,
  `/syntra.v1.UpdateRecovery/SnapshotFetch`,
  `/syntra.v1.UpdateRecovery/Unsubscribe`), each with versioned opaque
  payload bytes defined by this profile. All nine method strings are
  canonical `/package.Service/Method` paths with exactly two slashes per
  `SNTR-RPC-001`. Streamed content uses `Notification` payloads carrying
  exactly one versioned `RecoveryNotification` discriminator
  (`batch` | `replay_complete` | `trailer` with matching
  `profile_version`, predecessor/result checkpoints, generation,
  continuation marker, completion or snapshot-required signal where
  applicable) inside the existing `Notification.payload` with no envelope
  changes. A neutral
  echo round trip (`/example.Echo/Echo`), a neutral generic key/value
  read, and a neutral generic subscription establish the same envelope
  path; the profile only standardizes the payload contract above it.
- Correlation: `request_id` rules are unchanged and connection-scoped.
  `Notification` uses `request_id == 0` and MUST NOT complete any RPC.
  Profile batches carry the opaque subscription handle inside the
  payload so the initiator can route to exactly one stream; the core
  MUST NOT interpret the handle.
- Cancellation: existing `cancel` applies to the subscribing or
  profile RPC only and does not by itself terminate the stream unless
  the confirmed stream binding states so. Stream termination uses the
  targeted profile terminate operation or terminal signal. Pending
  batches MAY still arrive after termination (race); initiators MUST
  tolerate post-termination batches.
- Error mapping: unknown profile operation → `UNIMPLEMENTED`;
  unconfirmed-option use → `FAILED_PRECONDITION`; unknown stream →
  `UNIMPLEMENTED`; unauthorized at any hook → `PERMISSION_DENIED` or
   `UNAUTHENTICATED`; stale, forged, cross-stream, cross-generation, or
  cross-principal checkpoint → `FAILED_PRECONDITION` (or
  `UNAUTHENTICATED` where token-like); outside-retention replay →
   failed replay/catch-up `RpcResult` with `FAILED_PRECONDITION` plus
   `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification`
   payload; overload →
  `RESOURCE_EXHAUSTED`; loss → `UNAVAILABLE` (outcome unknown);
  deadline expiry → `DEADLINE_EXCEEDED`. Error detail MUST NOT contain
  credentials or private diagnostics.
- Capability negotiation: the profile Identifier is
  `syntra.update-recovery/1` (ASCII, versioned). Binding is generic RPC
  after ACTIVE: the initiator offers the identifier and payload
  version; the host confirms only the subset it implements for the
  bound principal. No handshake-extension binding is used. Capability
  state is per connection. Downgrade is explicit: where the host does
  not confirm, the peers operate mandatory-only (or live-only generic
  subscription where separately agreed); the host MUST NOT silently
  weaken confirmation and the initiator MUST NOT proceed as if
  confirmed.
- Unknown-field/profile handling (`SYN-URP-021`, consistent with
  `specifications/core/serialization.md` `SNTR-SER-003` and
  `specifications/core/versioning.md` `SNTR-VER-004`): envelope-level
  unknown fields are ignored per the compatibility rule and unknown
  `Frame.body` variants are rejected with `UNIMPLEMENTED`. Inside
  profile payload bytes, unknown Protobuf fields MUST be ignored
  unless explicitly marked `Critical` in
  `proto/syntra/v1/recovery_profile.proto`; fields explicitly marked
  `Ignorable` MUST be ignored; `profile_version` and routing/identity
  fields (`stream_selector`, `subscription_handle`, `snapshot_handle`,
  `capability`, versions) are required and missing/mismatch MUST fail
  with `FAILED_PRECONDITION`; checkpoints, boundaries, and markers use
  the per-field emptiness and pairing rules in `SYN-URP-021` and the IDL,
  not a blanket non-empty rule; unknown
  profile operations MUST be rejected with `UNIMPLEMENTED`, never
  silently applied.
- Resource bounds: §3 `SYN-URP-007` / `SYN-URP-018` own the bounds. No
  per-batch unbounded work is permitted: hosts MUST NOT spawn
  unbounded workers per batch, MUST NOT hold blocking locks across
  await points on the delivery path, and MUST drain explicitly during
  shutdown (stop new batches, observe the close grace, then tear down;
  in-flight profile RPCs receive terminal errors). Initiators MUST bound
  pending confirmations and offered-but-unpersisted batches.
- Ordering and validation pipeline: confirming hosts MUST emit batches
  for one stream in generation-scoped order on transports that preserve
  order, and MUST chain predecessor/result checkpoints so gaps are
  detectable without arithmetic. Confirming initiators MUST run
  recovered batches and live batches through the same validation
  pipeline (envelope validity, generation match, predecessor chaining,
  authorization context freshness, size bounds) before the offer step.
- Connection liveness, authentication validity, committed progress, and
  durable acknowledgement stay distinct: transport bytes prove nothing
  about Syntra receipt; Syntra receipt proves nothing about
  application processing; initiator confirmation proves only that the
  initiator application persisted the checkpoint through its
  persistence point, never business success beyond what the provider
  specification states. Replay storage, presence, durable data, method
  schemas, and domain handling remain above Syntra.

## 5. Alternatives considered

At least two alternatives with rejection rationale, including "do
nothing".

1. Handshake-bound negotiation for the profile. Rejected: the v1
   negotiation binding is itself unresolved (see `rfcs/0005` D1), and
   coupling recovery to handshake changes would widen every mandatory
   handshake fixture, complicate downgrade, and delay an otherwise
   additive profile. A generic RPC after ACTIVE keeps the mandatory
   handshake untouched and matches the allowed binding form where the
   capability RFC states its binding.
2. New `Frame` body variants for replay, catch-up, snapshot, and
   confirm. Rejected: it consumes envelope evolution budget, reuses
   pressure on reserved numbers/names, forces every transport adapter
   and every mandatory-only peer to change, and contradicts the
   profile-carries-bytes direction. The same contract fits inside
   existing envelopes with versioned payload bytes and preserves
   reserved 16, 17, `event`, `resume`, `ack` untouched.
3. Do nothing (leave replay/recovery as application-defined under the
   existing generic guidance). Rejected as the standing rule but not as
   the future: it preserves maximal optionality today at the cost of
   permanent divergence — no shared generations, no standard
   predecessor/result semantics, no catch-up boundary or completion
   signal, no snapshot contract, no commit order, and no testable
   conformance for recovery. This RFC keeps "do nothing" as the valid
   mandatory-only mode while giving confirming peers one shared
   contract.

## 6. Compatibility

- Wire impact: compatible minor/additive, justified by zero envelope
  changes. No field is added or reinterpreted; reserved numbers 16, 17
  and reserved names `event`, `resume`, `ack` are preserved; profile
  bytes are opaque to non-confirming peers. No major version is
  required.
- Negotiation: old/new peers interoperate mandatory-only. A host that
  does not confirm `syntra.update-recovery/1` rejects profile RPCs with
  `UNIMPLEMENTED` and continues mandatory RPC service. An initiator
  that does not offer the profile never receives profile batches. A
  confirming initiator against a non-confirming host falls back to
  mandatory-only (plus any previously confirmed options) and MUST NOT
  treat the absence as a connection failure where fallback exists.
  Downgrade behavior is explicit confirmation, never probing.
- Reserved values: preserved. This profile MUST NOT reuse reserved
  numbers or names without a major-version RFC.
- Migration: no migration. There is no dual-support window because
  there is no wire break. Deployments adopt the profile by confirming
  it; rollback is non-confirmation. No migration notes beyond recording
  the optional profile in deployment documentation.

## 7. Security considerations

Threats: forged or replayed checkpoint bytes presented as continuity;
cross-stream or cross-principal checkpoint transplant; snapshot bytes
that smuggle oversized or malicious content into the initiator
application; subscription flooding as a denial-of-service vector;
downgrade to an unconfirmed profile mode; revocation/expiry races where
batches continue after the principal lost authority; diagnostics that
leak credentials or provider internals.

Credential handling: credentials stay opaque sensitive bytes, presented
only as defined by the handshake and any follow-up authentication
payloads, transmitted only over secure transports in externally
reachable deployments. The core MUST NOT log, persist, or interpret
them. Profile operations re-evaluate the bound principal; they MUST NOT
accept checkpoint or handle bytes as authority.

Diagnostics hygiene: `RpcError.message` MUST NOT contain credentials,
checkpoint secrets, or private provider diagnostics. Rejections MUST use
typed codes without leaking other principals' stream state.

Denial-of-service bounds: every queue, page, snapshot transfer, pending
RPC count, and subscription count is bounded and documented; saturation
yields `RESOURCE_EXHAUSTED` and/or explicit continuity loss with a new
generation, never unbounded retention. Initiators back off with bounded
budgets and jitter, never tight loops. Retry storms after outages MUST
be damped.

Transport policy impact: none beyond the standing rule — externally
reachable deployments use secure transports; restricted development
transports MUST NOT carry public traffic. The profile adds no plaintext
exception and no custom cryptographic construction.

Negative tests: unauthenticated subscribe/replay/snapshot/continuation
MUST fail without emitting batches; oversized page/snapshot MUST fail
without partial install; malformed or cross-generation checkpoint MUST
fail without leaking state; revoked-principal delivery MUST stop with a
typed signal where possible.

## 8. Test plan and acceptance criteria

No tests executed in this RFC draft step. Acceptance requires the
following conformance coverage (all fixtures use neutral payloads:
echo, generic key/value, generic subscription):

- [ ] Conformance tests (positive + negative + fixtures):
  - Negotiation: confirm/decline/partial-accept; unconfirmed use fails;
    per-connection isolation (confirmation on one connection does not
    enable another).
  - Ordered delivery: predecessor/result chaining per generation;
    duplicate tolerance across recovered/live boundary; same validation
    pipeline for recovered and live batches.
  - Replay paging: bounded pages, continuation markers, catch-up
    boundary, oversized history paged (never burst).
  - Catch-up: RPC trigger streams over the existing connection;
    explicit completion; snapshot-required where outside retention.
  - Snapshot: bounded transfer, provider-proven boundary chaining,
    install only on boundary confirm; oversized snapshot rejected
    without partial install.
  - Commit order: receive → validate → offer → persist → confirm;
    transport receipt never reported as committed.
  - Routing/termination: batches reach exactly the targeted
    subscription; per-stream termination does not end the connection;
    reconnect requires explicit re-establishment.
  - Bounds: subscription, pending-RPC, queue-byte, page-byte, and
    deadline fixtures at exactly-MAX and MAX+1; subscriber-local
    saturation yields the targeted `terminated` trailer with ASCII
    `local-queue-exhausted` at the UNCHANGED generation (no
    `next_generation`), while a true provider loss yields the scoped
    next_generation trailer (§11.2/§11.4).
  - Authorization hooks: subscribe/replay/snapshot/continuation each
    re-evaluated; revoked/expired principal stops delivery with a typed
    signal; rejections leak no credentials.
  - Reserved/mandatory interop: reserved 16, 17, `event`, `resume`,
    `ack` untouched; mandatory-only peer interoperates with a
    profile-confirming peer at mandatory behavior.
- [ ] Requirement-to-test trace (ID → test):
  `SYN-URP-001`/`SYN-URP-020` → negotiation/version fixtures;
  `SYN-URP-002` → envelope preservation fixtures (no new `Frame` fields,
  reserved 16/17 and `event`/`resume`/`ack` untouched, all nine methods
  canonical `/package.Service/Method` with exactly two slashes,
  `RecoveryNotification` inside `Notification.payload`);
  `SYN-URP-003`/`SYN-URP-012`/`SYN-URP-013` →
  generation/checkpoint fixtures; `SYN-URP-004`/`SYN-URP-014` →
  paging/catch-up fixtures; `SYN-URP-015` → completion/snapshot-required
  fixtures; `SYN-URP-005`/`SYN-URP-016` → commit/snapshot fixtures
  (batch `RecoveryConfirmRequest`/`RecoveryConfirmResponse` vs snapshot
  `RecoverySnapshotConfirmRequest`/`RecoverySnapshotInstalled`,
  `RecoverySnapshotOfferRequest`/`RecoverySnapshotDescriptor`,
  `RecoveryUnsubscribeRequest`/`RecoveryUnsubscribeResponse`);
  `SYN-URP-006`/`SYN-URP-017` → routing/termination and state-separation
  fixtures; `SYN-URP-007`/`SYN-URP-018` → bound fixtures;
  `SYN-URP-010`/`SYN-URP-011`/`SYN-URP-019` → negotiation/schema/hook
  fixtures; `SYN-URP-021` → unknown-field/schema fixtures;
  `SYN-URP-022` → continuation-echo and idempotent-retry fixtures
  (mismatched marker/from rejected; duplicate of the immediately
  preceding completed request returns the retained page);
  `SYN-URP-023` → subscribe-boundary fixtures (empty boundary rejected,
  pages validated against the subscribed boundary);
  `SYN-URP-024` → fresh-handle round / lost-completion fixtures
  (initial skip-replay, fixed-B validation in correlated `RpcResult`
  pages, fresh Subscribe with H2/B2 after a second gap, bounded exact
  retries plus re-emitted completion on lost outcome, retire-H on
  exhaustion, no same-handle second round, no idle-as-caught-up);
  `SYN-URP-025` → snapshot transfer/install and
  confirm-fencing fixtures (same-generation install with no G change,
  current-generation retained-install retry returns the original
  retained installed response, different subscription/version/boundary
  rejected, supersede retires H even at equal boundary, later
  generation/termination/retention expiry rejects the stale request,
  un-offered confirm rejected, no wire carrier for the completion
  record); `SYN-URP-026` → invalidation-scope and revocation fixtures
  (scoped provider loss vs subscriber-local saturation, revoked
  principal stops with typed signal, no automatic generation increment
  on revocation unless policy resets the scope).
- [ ] Interop check (implementations or fixtures): at least two
  independent profile implementations (or recorded fixtures from two
  sources) demonstrating mandatory-only interop plus confirmed-profile
  recovery interop; placeholders tracked where implementations do not
  yet exist.
- [ ] Schema lint + breaking detection for schema changes: envelope
  schema unchanged — lint reports no new/renumbered fields and breaking
  detection reports no break; reserved values asserted present.

## 9. Drawbacks and risks

What gets harder, what could go wrong, and mitigations.

- Added surface: a full recovery contract (generations, checkpoints,
  paging, catch-up, snapshots, commits, hooks) is more to implement and
  review than live-only push. Mitigation: everything is optional and
  additive; mandatory-only stays conformant and simpler.
- Snapshot trust weight: a provider-proven boundary concentrates trust
  in the provider attestation and the initiator's offer/persist/confirm
  discipline. Mitigation: boundary chaining is mandatory, partial
  install is forbidden, and confirmation proves only persistence — never
  business success.
- Bound tuning risk: overly tight defaults throttle legitimate
  catch-up; overly loose bounds weaken denial-of-service posture.
  Mitigation: bounds are documented per deployment, fixtures assert
  exactly-MAX/MAX+1, and subscriber-local saturation always produces
  the observable targeted termination (§11.4) rather than silent loss.
- Generation-management defects could strand streams on stale
  checkpoints. Mitigation: stale checkpoints fail loudly with
  `FAILED_PRECONDITION`, recovery is always an explicit fresh-handle
  re-subscribe or a scoped provider loss transition, never silent
  reinterpretation or a manufactured generation.

## 10. Unresolved questions and blockers

All six items below were proposals (Draft). At acceptance (2026-10-30)
each adopted value/record is marked **Adopted**; the acceptance decision
record carries the approval. Implementation validation and Rust/Go
conformance evidence remain pending and are explicitly NOT satisfied by
this acceptance.

1. **Adopted at acceptance.** Numeric bounds (from
   `proto/syntra/v1/recovery_profile.proto`
   header defaults): maximum subscriptions per connection 64; maximum
   subscriptions per principal 256; maximum pending profile RPCs per
   connection 16; maximum queued `Notification` bytes per stream 262144
   (256 KiB); maximum queued `Notification` bytes per connection
   aggregate 1048576 (1 MiB); maximum replay page 64 batches and 262144
   total bytes, whichever binds first, with each serialized batch at
   most 262144 bytes; `RecoveryReplayRequest{max_batches}` valid range
   1..64 and `max_bytes` valid range 1..262144; maximum snapshot page
   262144 bytes; maximum pages per snapshot offer 256
   (`RecoverySnapshotDescriptor{total_pages}` 1..256,
   `page_bytes_max` 1..262144, `RecoverySnapshotChunk{page_index}`
   0..255,    `page_bytes` non-empty at most 262144,
   `RecoverySnapshotComplete{total_pages}` 1..256, `total_bytes`
   1..67108864 — field caps that apply to the peer-local
   installation record, which per §11.5 has NO wire transmission);
   effective deadline default for profile RPCs 5 s where
   the `RpcRequest` carries no explicit bounded deadline, with every
   profile RPC having an effective deadline and expiry surfaced as
   `DEADLINE_EXCEEDED`. Opaque field caps: `stream_selector` non-empty
  at most 1024 bytes; `start_checkpoint` empty means initial (skip replay, start live at B), otherwise
  at most 4096 bytes; `subscription_handle` and `snapshot_handle`
  non-empty at most 256 bytes; `from_checkpoint` non-empty (replay is sent only for resumption) at most 4096 bytes,
  `predecessor_checkpoint`, `result_checkpoint`, `boundary_checkpoint`,
  `live_boundary_checkpoint` at most 4096 bytes;
   `RecoverySubscribeResponse.catchup_boundary` non-empty at most 4096 bytes
   (empty means omitted and MUST be rejected with FAILED_PRECONDITION)
  (`SYN-URP-023`);
  other `catchup_boundary` and completion boundary fields at most 4096 bytes and MUST equal the subscribed boundary before releasing held live batches;
   request `continuation_marker` empty on the first request, otherwise echo
   of the previous page marker verbatim at most 4096 bytes (`SYN-URP-022`);
   response `continuation_marker` empty means no further page, otherwise
   at most 4096 bytes; `terminate_reason` non-empty when terminated, at most 256
   bytes;    `profile_version` valid value 1; `capability` non-empty at most 256
   bytes; `min_version`, `max_version`, and `selected_version` valid
   value 1; `checkpoint` and `confirmed_checkpoint` non-empty at most
   4096 bytes; `RecoveryNegotiateResponse` confirmed bounds are
   `uint32` deployment values.
2. **Adopted at acceptance.** Method strings, canonical payloads, and version
   negotiation rule (`SYN-URP-002`/`SYN-URP-020`/`SYN-URP-021`): exact
   standardized generic RPC methods are
   `/syntra.v1.UpdateRecovery/Negotiate`,
   `/syntra.v1.UpdateRecovery/Subscribe`,
   `/syntra.v1.UpdateRecovery/Replay`,
   `/syntra.v1.UpdateRecovery/CatchUp`,
   `/syntra.v1.UpdateRecovery/Confirm` (batch),
   `/syntra.v1.UpdateRecovery/SnapshotConfirm` (snapshot boundary),
   `/syntra.v1.UpdateRecovery/SnapshotOffer`,
   `/syntra.v1.UpdateRecovery/SnapshotFetch`, and
   `/syntra.v1.UpdateRecovery/Unsubscribe` under identifier
   `syntra.update-recovery/1`. Each method string MUST pass canonical
   `/package.Service/Method` validation per `SNTR-RPC-001` (leading slash,
   exactly two slashes, non-empty segments, printable ASCII excluding
   spaces/control); malformed paths MUST be rejected with
   `INVALID_ARGUMENT` before dispatch. Canonical payloads are
   `RecoveryNegotiateRequest`/`RecoveryNegotiateResponse`,
    `RecoverySubscribeRequest`/`RecoverySubscribeResponse`
    (response carries `catchup_boundary` fixed at subscribe accept),
    `RecoveryReplayRequest` (with `profile_version` and `continuation_marker` echo) with exactly one `RecoveryReplayPage` per
    `RpcResult`, `RecoveryCatchUpRequest` with `RecoveryCatchUpAccepted`
    in the terminal `RpcResult` (batches and completion trailer via
    `Notification` as `RecoveryNotification`),
   batch `RecoveryConfirmRequest`/`RecoveryConfirmResponse` and snapshot
   `RecoverySnapshotConfirmRequest`/`RecoverySnapshotInstalled` using
   distinct Confirm and SnapshotConfirm methods so identical Protobuf field
   shapes cannot confuse batch and snapshot intent,
   `RecoverySnapshotOfferRequest` with `RecoverySnapshotDescriptor`,
   `RecoverySnapshotFetchRequest` with exactly one
   `RecoverySnapshotChunk` per `RpcResult`, and
   `RecoveryUnsubscribeRequest` with `RecoveryUnsubscribeResponse`,
   plus the versioned `RecoveryNotification` discriminator/wrapper
   (`batch` | `replay_complete` | `trailer`) inside every profile
   `Notification.payload` with no envelope changes, all defined in
   `proto/syntra/v1/recovery_profile.proto`. The Negotiate invocation
   offers min and max profile versions (proposing 1/1); the host selects
   the maximum version it implements within the offered range. No
   overlap MUST fail with `FAILED_PRECONDITION` in `RpcResult`. Every
   other operation carries `profile_version=1` (outer `RecoveryNotification`
   version must equal inner payload version); mismatch or unset
   `notification` outcome MUST fail with `FAILED_PRECONDITION`. Wire
   policy defers to
   `specifications/core/serialization.md` (`SNTR-SER-003`) and
   `specifications/core/versioning.md` (`SNTR-VER-004`): unknown
   Protobuf fields MUST be ignored unless explicitly marked `Critical`;
   fields explicitly marked `Ignorable` MUST be ignored;
   `profile_version` and routing/identity fields are required and
   missing/mismatch MUST fail with `FAILED_PRECONDITION`; checkpoint,
   boundary, and marker emptiness is per-field (`SYN-URP-021`), not blanket;
   unknown profile operations MUST be rejected with `UNIMPLEMENTED`, never
   silently applied.
3. **Adopted at acceptance.** Retention rule: retention stays deployment-documented with
   no implicit minimum assumed by initiators. Each deployment offering
   replay documents its retention minimum. A replay or catch-up request
   for a checkpoint outside retention MUST fail with
   `FAILED_PRECONDITION` in `RpcResult` while emitting
   `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification`
   payload, per `SYN-URP-015`.
4. **Adopted at acceptance (per §11.5).** Snapshot offer lifetime and
   supersede rule: an offer is valid from its `RecoverySnapshotDescriptor`
   until transfer completes — which per §11.5 produces only the
   peer-local `RecoverySnapshotComplete` installation record with NO
   wire transmission — plus boundary confirm, or until
   targeted termination, a true provider continuity change incrementing
   G, or supersede. Superseding an offer RETIRES the subscription handle
   H, even when the new boundary equals S0 and G is unchanged, and
   requires a fresh Subscribe before a further snapshot may be issued.
   Invalidation flows through the snapshot handle and RPC
   outcome without ordering checkpoint bytes: in-flight
   `SnapshotFetch` under a superseded `snapshot_handle` fails with
   `FAILED_PRECONDITION` (superseded), and/or the host emits an
   explicit continuity signal for a genuine provider loss per §11.2;
   the initiator MUST
   discard prior pages on supersede and MUST NOT install across
   boundaries. A `RecoverySnapshotChunk` is associated only when its
   `boundary_checkpoint` bytes equal the currently offered descriptor
   `boundary_checkpoint` bytes; equality validates association only,
   recency comes only from the explicit supersede signal or RPC
   outcome. Completion requires matching `total_pages` and
   `total_bytes`, and installation completes only when the initiator
   confirms that exact boundary checkpoint — the offered S0 — through
   `/syntra.v1.UpdateRecovery/SnapshotConfirm`, yielding
   `RecoverySnapshotInstalled` carrying the UNCHANGED CURRENT
   generation per `SYN-URP-025`/§11.5.
   Exact retained-install retries carry the CURRENT generation and the
   installed boundary bytes under the `SYN-URP-025` exception, returning
   the original installed response; they do not reopen an offer,
   authorize old-generation work, or fabricate a pre-install generation.
   Retained responses are bounded by deployment-documented count, bytes,
   and lifetime and invalidated on supersede, termination, or later
   continuity change; no implicit retry-retention minimum is set.
5. **Adopted at acceptance.** Fixture hosting note: conformance fixtures for this profile
   live in the conformance suite as additive fixtures using neutral
   payloads only (echo, generic key/value, generic subscription),
   tracing to §8 acceptance criteria and `SYN-URP` IDs. Interop evidence
   requires two independent profile implementations or recorded
   fixtures from two sources demonstrating mandatory-only interop plus
   confirmed-profile recovery interop; placeholders are tracked where
    implementations do not yet exist. Registered case identities live in
   `conformance/manifest/recovery.yaml` (`CONF-URP-001…017`, §11-reconciled
   in the acceptance PR); registration is not execution.
6. **Adopted at acceptance; review synchronization applied.** The separate
   SnapshotConfirm method, per-field empty sentinels, and the
   current-generation retained-install retry (the pre-amendment
   pre-install-generation exception is removed by §11.5) align the
   contract with the profile/IDL intent, and the owning profile, IDL
   comments, and registered cases have been synchronized in the
   acceptance PR (registration is not execution). Generated codecs still
   do not enforce these validation rules; implementation validation and
   deterministic positive and negative retained-install tests must be
   verified before any conformance claim. Shipping authority remains
   gated on the required maintainer acceptance (recorded via the
   acceptance decision record) and protocol/security review, and on
   independent implementation/conformance evidence, which is pending.

## 11. Decision amendment — release inclusion and recovery safety

The decisions in this section were recorded by the 2026-10-28 amendment
and are adopted by this acceptance; the acceptance decision record
carries the approval. They resolve the design choices below for review;
owner-file synchronization, and the conformance and release evidence
trails were applied in the acceptance PR, while implementation evidence
remains outstanding. Existing `SYN-URP` IDs are retained; no IDs are
allocated here.

### 11.1 Release bundle versus wire optionality

Adopted decision (`SYN-URP-001`, `002`, `010`, `011`, `020`, `021`):
standardized recovery is required in the target release bundle. A release
presented as meeting that target includes the accepted recovery contract,
matching schema documentation, and independent Rust/Go acceptance evidence
for its initiator and host roles. Recovery cannot be omitted from that
release and relabeled as an optional future implementation item.

On the wire, `syntra.update-recovery/1` remains optional and explicitly
negotiated after ACTIVE, independently on every connection. No unsolicited
profile traffic, handshake extension, new `Frame` variant, or implicit
continuity is introduced. A Core-only implementation can still conform to
`SNTR-CORE-V1` with its required session/RPC/security coverage over a named
transport, without claiming recovery. Core-only success is insufficient
evidence for the recovery-inclusive release bundle. A release participant
still interoperates with Core-only peers using mandatory-only behavior;
fallback supplies no recovery guarantee and is recorded as such.

This is an adopted release acceptance obligation per RFC 0009's accepted
release scope (Option A: standardized recovery stays in Syntra), recorded
through the acceptance decision record. `SNTR-EVENTS-V1` registers
capability-gated recovery cases (registered, not executed). No new release-bundle profile ID is
invented. Release-scope governance already belongs to maintainers via
accepted RFC 0009; other release
work, including RFC 0008, Core, and SC1, retains its own decision process.

### 11.2 Identity and generation scope

Adopted replacement for `SYN-URP-003`, `006`, `012`, `013`, `019`, `026`:

- A subscription is a delivery instance, routed by a fresh connection-scoped
  handle H. A stable stream identity S is provider-resolved from the selector
  in an authenticated principal/authorization scope P. Several subscriptions
  can observe the same S. Their queues and phases remain independent.
- The host binds checkpoint C to `(P, S, G)`, where G is the provider's
  continuity generation for that scope. Identical selectors do not establish
  identical scope or authority. Initiators persist the binding context with
  C but never parse C or infer order from it. Host validation remains decisive.
- Generation changes represent true provider history loss or an explicit
  shared rebase within that scope. They invalidate all earlier-generation
  checkpoints in that scope, including those held by other subscriptions.
  The host fences their outstanding pages, offers, confirmations, and batches
  and signals the invalidation explicitly with a trailer whose `generation`
  is the old G and `next_generation` is the new G. If signaling is lost, the
  next old-generation operation fails `FAILED_PRECONDITION`; stale bytes
  never acquire the new meaning silently. A provider loss spanning several
  principal scopes invalidates every affected scope explicitly; principal
  isolation does not preserve history that was actually lost.
- A checkpoint outside a replay retention window requires explicit
  snapshot fallback. Ordinary pruning of that window need not invalidate
  otherwise valid checkpoints or increment G; actual shared continuity loss
  or provider reset does. This distinguishes replay unavailability from
  invalidation of the checkpoint binding itself.
- Revocation/expiry denies the affected principal at every authorization
  hook and stops affected delivery. Revocation alone is targeted termination,
  not a reset of unrelated principals' streams. If policy also invalidates
  that principal's recovery history, the host changes only that scoped G
  (or rejects that scoped binding), explicitly invalidating its checkpoints.
  Regrant never revives an invalidated binding. Other principals observing
  the same underlying source keep their own valid bindings and subscriptions.

### 11.3 One fresh handle and fixed boundary per recovery round

Adopted replacement for `SYN-URP-004`, `006`, `014`, `015`, `022`–`024`:

1. Each new round begins with Subscribe and receives a fresh H and a newly
   captured non-empty fixed B at host acceptance. B never moves during that
   round. A new capture can equal a previous boundary when no source progress
   occurred; equality does not identify a round. Connection + H identifies it.
   The host does not reuse a retired handle within a connection.
2. A resumption supplies the durable known-safe C defined in §11.6 as
   `start_checkpoint`; Replay starts from that same C with an empty marker.
   Continuations echo the previous marker and result exactly. Alternatively,
   CatchUp streams from the start checkpoint already bound by Subscribe;
   its request has no new checkpoint field. A round chooses Replay or
   CatchUp, never both concurrently. An empty initial start skips Replay;
   CatchUp can obtain explicit baseline completion at B. An initial live
   baseline does not assert installation of historical application state.
3. On a new gap, loss-counter movement, or invalid completion, retire H
   locally before new work. Clear its held queue, cursors and pending offers;
   request Unsubscribe when possible. Allocate the next H through Subscribe
   without waiting indefinitely for old teardown. Host resource bounds still
   apply; inability to retire remotely can require reconnect/backoff.
4. A second gap after durable progress C2 beyond the earlier B1 starts a
   new round `(H2, B2)` from C2. The host captures B2 at that new acceptance;
   it does not replay from C2 toward obsolete B1. If C2 is no longer replayable
   use explicit snapshot fallback, never an empty-start silent restart.
5. Release held live batches only after all recovered data through current B
   has passed validation and the local persistence gate, and a completion
   matches current connection, H, G, profile version and exact B. Process
   held then new batches with predecessor chaining from B. Retired-handle
   completions, pages, RPC results and batches have no effect even if their
   B bytes happen to equal current B. Duplicate current completions are
   idempotent and do not re-offer data. Batch duplicate suppression follows
   version, handle/scope, generation, authorization and bounds validation;
   only then can an already applied result checkpoint bypass predecessor
   chaining. Equal bytes from another context are not a duplicate.
6. Loss of completion is not evidence of catch-up. While still in the same
   round, bounded exact retries may recover it: repeat the immediately
   preceding Replay request under `SYN-URP-022`, or the same CatchUp request
   with a fresh RPC request ID. The host returns the retained page/acceptance
   and re-emits that round's completion if already complete, without rerunning
   application effects, moving B, or restarting pagination. For initial
   baseline recovery use CatchUp. Retention is bounded and documented;
   expiry fails explicitly. Exhaustion of the retry/deadline budget retires
   H and starts a fresh round from durable known-safe C. No same-handle
   second round or marker reset is permitted.

No round ID, moving-boundary field, or checkpoint arithmetic is needed.
Existing handles fence old rounds. Notifications retain `request_id == 0`;
Replay returns one page in its correlated `RpcResult`, not a page Notification.

### 11.4 Subscriber-local saturation does not rebase the provider

Adopted replacement for `SYN-URP-007`, `017`, `018`, `026`: a host or
initiator delivery/holding queue overflow is subscriber-local. End the
affected subscription or report an explicit local recovery-needed event,
clear its held queue, fence H, and begin a fresh round using §11.3. It does
not increment shared G or invalidate another subscriber's C. Host notification
uses the existing mutually exclusive `terminated=true` outcome with current
G and a non-empty machine-readable `terminate_reason` denoting local queue
exhaustion (proposed exact ASCII bytes `local-queue-exhausted`); an affected
pending RPC can also fail `RESOURCE_EXHAUSTED`.
Initiator-local overflow has an observable local recovery-needed event and
best-effort Unsubscribe; it cannot manufacture a provider `next_generation`.

While catching up, a bare reject-new-work response is insufficient if an
already accepted subscription can no longer reach completion: that subscription
must become explicitly recovery-needed/terminated. Rejecting new work before
acceptance remains valid. If even the terminal control signal cannot be queued,
reserve bounded control capacity or close the exhausted connection explicitly;
never leave a silently live/stalled subscription. A genuinely exhausted
connection has connection scope, but still does not change provider G merely
because its queues filled. True history loss is separately handled by §11.2.

### 11.5 Snapshot transfer, local installation, and coordinated binding

Adopted replacement for `SYN-URP-016`, `021`, `025`, `026`:

- SnapshotOffer returns `RecoverySnapshotDescriptor` with H, snapshot handle
  X, provider-proven boundary S0, page count N and page byte bound. G is the
  already established subscription generation; the descriptor has no G field.
  The host binds X to `(P, S, H, G, S0)`. Each SnapshotFetch returns exactly
  one `RecoverySnapshotChunk` in its `RpcResult`, correlated by request ID,
  X, index, version and S0. Fetch all indices `0..N-1` exactly once logically;
  retries do not increase counts. Local transfer completion is derived from
  complete index coverage and bounded byte accounting. The current
  `RecoverySnapshotComplete` message has no method/result slot or
  `RecoveryNotification` arm: this amendment proposes no wire transmission
  for it. Its counts can describe a local transfer record; no second result
  or unregistered Notification outcome is assumed.
- At most one distinct X is offered under H. Exact SnapshotOffer retries return
  the retained descriptor. Superseding an offer retires H and requires a fresh
  Subscribe before a new X is issued, even if the new boundary equals S0 and G
  is unchanged. Old confirmations then reference retired H and fail; no
  snapshot-handle field is assumed in SnapshotConfirm. This also fences a lost
  response from an earlier install with equal boundary bytes.
- Snapshot installation is application-local durable replacement under S0,
  followed by SnapshotConfirm. It does not rebase the shared provider stream
  or change G. Subsequent batches for that subscription chain from S0 in G;
  unrelated subscribers continue from their own checkpoints, without reset.
  Local durable installation and peer-acknowledged installation are distinct:
  the initiator opens the snapshot live gate only after a validated
  `RecoverySnapshotInstalled` matching H, G and S0. Until then it holds live
  batches boundedly or reconnects from durable S0 after retry exhaustion.
  Snapshot fallback exits the old catch-up path; snapshot installation is its
  own gate and does not masquerade as completion at the original subscribe B.
  Old replay completions cannot release snapshot-held batches. If another
  catch-up round is needed after installation it gets a fresh H and B.
- A provider that needs a real shared rebase performs and signals it before
  issuing a descriptor in the new G. Retire old handles and offers and
  re-subscribe in the new G before snapshot transfer. An install confirmation
  never creates that rebase as a side effect. Superseded X or mixed pages
  fail `FAILED_PRECONDITION`; discard staging, never partially activate it.
- Before descriptor exposure, the provider and host coordinate a recoverable
  binding of S0 to `(P, S, G)` and snapshot contents. S0 is resumable with host
  validation even if the initiator durably installs then loses SnapshotConfirm
  or its response. This binding is independent of per-H reply caching. The
  host either preserves/reconstructs it across restart, or explicitly reports
  loss of binding/history and takes snapshot fallback or scoped generation
  invalidation; it never interprets old S0 in a new G. No cross-system atomic
  transaction is supplied by Syntra.
- SnapshotConfirm uses the exact offered S0 and current G; success is
  `RecoverySnapshotInstalled{profile_version, subscription_handle,
  boundary_checkpoint=S0, generation=G}`. The response has no separate
  replacement checkpoint field. Do not infer an unseen post-install token or
  reinterpret S0 as belonging to a newly incremented G. An exact retry for
  the same authorized H, version, G and S0 returns the retained original
  response without installation effects or G change. Supersede, termination,
  later scoped continuity change or cache expiry ends this retry eligibility;
  equality alone is insufficient. On expiry/exhaustion use §11.6 reconnect,
  not repeated installation or a fabricated pre-install-generation exception.

### 11.6 Persistence, confirmation, and reconnect

Adopted replacement for `SYN-URP-005`, `006`, `013`, `016`, `022`, `025`:

`receive → validate → offer → persist → confirm` includes the application
effects represented by a checkpoint, not just saving opaque checkpoint bytes.
The application either atomically persists those effects and `(P, S, G, C)`,
or supplies an idempotent recovery fence that durably identifies the operation
and reconciles/reapplies it safely across every crash window. A checkpoint
ahead of durable application state is unsafe. Application effects ahead of C
can be replayed only with that fence (or recovered by a new local snapshot).
The application declares its durable success point and fence contract; offer
return, asynchronous write submission, decode, and transport receipt are not
that point. Unsupported persistence semantics cannot claim recovery safety.

Maintain three distinct observations: **locally durable C**, **Confirm sent
for C**, and **peer-acknowledged C** (a validated Confirm response). Sending
does not acknowledge; acknowledging does not retroactively make local writes
atomic. The durable known-safe C is the latest exact checkpoint whose
represented application state and binding are durable/reconcilable under the
contract above. It can be newer than the last peer-acknowledged C after an
acknowledgement is lost. Stop-and-wait confirmation bounds pending state;
retry the same method and exact payload with fresh request IDs under documented
finite attempts, absolute deadline and backoff. A late response for retired H
does not advance the current round. Retry exhaustion leaves durable data intact
and triggers reconnect and re-subscription, not rollback by guesswork.

Reconnect always establishes a new authenticated connection, negotiates again,
and subscribes with a fresh H and captured B. It transfers neither capability
state nor pagination/snapshot handles. Recovery cases are explicit:

| Durable evidence on restart | Required action and host check |
|---|---|
| No durable application progress | Use prior known-safe C with reconciliation/fence; if none exists, explicitly choose initial live-only baseline or snapshot according to application intent. Never label initial live-only as restored historical state. |
| Effects + C durable, Confirm never sent | Subscribe with C under the same P/S/G; host validates issued checkpoint and current authority, binding and retention even though it never received Confirm. |
| Confirm sent, response lost, effects + C durable | Same re-subscription with C; no claim that the peer acknowledged. Host may accept valid C without a previous confirmation record. |
| Response received, acknowledgement bookkeeping lost | Durable C is still sufficient subject to host validation; do not infer missing durable application writes from a host confirmation. |
| Snapshot + S0 durable, SnapshotConfirm or response lost | Resume with exact S0 and persisted P/S/G using §11.5's coordinated binding; no obsolete X or H, no new generation inferred from an unreceived result. |
| Host restart/cache expiry with provider history/binding intact | Validate C or S0 without old H's retry cache; capture new B and resume. |
| Same P/S/G but history outside replay retention | Explicit `FAILED_PRECONDITION` plus snapshot-required on the bound replay/catch-up path; no silent empty-start reset. |
| Provider loss/shared rebase changed G | Reject old C, explicitly invalidate scoped checkpoints, then establish a current-generation subscription and snapshot. |
| Different P, different resolved S, revoked/expired authority, or invalid binding | Deny before effects or progress. No checkpoint transplant; reauthorization does not itself prove continuity. |

Host validation of a resumable issued checkpoint is distinct from accepting an
unoffered Confirm on an active H: batch Confirm still requires a committable
batch result for that H/G, and SnapshotConfirm the current offered boundary.
Before exposing any committable batch result, the host/provider likewise
establishes its recoverable issued binding to P/S/G independently of Confirm
receipt. This can be reconstructible provider state rather than a new durable
record per batch. Loss of that binding requires explicit failure/recovery,
never assuming that a lost acknowledgement proves no local commit occurred.
Syntra supplies neither a storage transaction nor exactly-once application
effects. Retries can repeat delivery; crash safety comes from the application's
atomic persistence or explicit idempotent recovery fence.

### 11.7 Event sequence

```text
Initiator/application                         Host/provider
  durable (P,S,G,C0)                               |
  Subscribe(start=C0) --------------------------->|
  <--- RpcResult Subscribe(H1,G,B1) ---------------|
  Replay(H1,C0,empty marker) --------------------->|
  <--- RpcResult ReplayPage(...,B1,marker) --------|
  validate; atomically persist effects+C1          |
  Confirm(H1,G,C1) ------------------------------>|
  <--- RpcResult ConfirmResponse(C1,G) ------------|
  ... finish pages through B1; persist ...         |
  <--- Notification completion(H1,G,B1) -----------|
  <--- live batches chaining from B1 --------------|
  durable progress C2 beyond B1; detect new gap     |
  retire H1; Subscribe(start=C2) ----------------->|
  <--- RpcResult Subscribe(H2,G,B2) ---------------|
  <--- late completion(H1,G,B1): ignored            |
  Replay(H2,C2,empty marker) --------------------->|
  ... recover through B2; persist; complete H2 ...  |
  OR explicit snapshot fallback on replay failure  |
  <--- RpcResult SnapshotDescriptor(H2,X,S0,N) -----|
  Fetch(X,index) -> one RpcResult Chunk per index   |
  local complete coverage; durable snapshot+S0     |
  SnapshotConfirm(H2,G,S0) ----------------------->|
  <--- RpcResult SnapshotInstalled(S0,G), or lost --|
  bounded exact retry; then reconnect from S0       |
```

### 11.8 Acceptance edit map (applied in the acceptance PR)

In this table, **owner** means `specifications/profiles/recovery.md` and
**IDL** means `proto/syntra/v1/recovery_profile.proto`. These edits are
specified by the amendment and were applied in the acceptance PR
(registration is not execution; codecs alone still do not enforce the
contract).

| Decision / existing IDs | Exact required owner edits | Exact required IDL edits |
|---|---|---|
| §11.1; `001`, `002`, `010`, `011`, `020`, `021` | §1 and §12: separate required release-bundle inclusion from optional per-connection negotiation and Core-only claims; preserve existing capability/version and refusal rules. | Header: document release inclusion versus wire optionality; no field or envelope changes. |
| §11.2; `003`, `006`, `012`, `013`, `019`, `026` | Terminology; §2.1/2.2 IDs listed; §§3, 4, 5.1, 9: replace subscription-equals-stable-stream ambiguity with P/S/G binding, scoped revocation and explicit true shared invalidation; distinguish retention-window miss from provider reset. | Header and `RecoverySubscribeResponse.generation`, `RecoveryBatch.generation`, `RecoveryBatchTrailer.generation/next_generation`: document scoped provider epoch and shared invalidation, not queue overflow. No principal field: authenticated context plus opaque checkpoint binding suffices. |
| §11.3; `004`, `006`, `014`, `015`, `022`, `023`, `024` | §2 IDs listed, §§3, 5/5.1/5.2, 11: replace same-handle new rounds with fresh Subscribe/H/B, current-round completion fencing, retry-only CatchUp and terminal Replay completion re-emission; fix page-as-Notification diagrams. | `RecoverySubscribeRequest.start_checkpoint`, `RecoveryReplayRequest.from_checkpoint`, `RecoveryReplayComplete`, `RecoveryCatchUpRequest/Accepted`: document durable-safe start, immutable per-H round, mode exclusion, bounded exact retry and re-emission. No round or boundary-update field. |
| §11.4; `007`, `017`, `018`, `026` | §2 IDs listed, §§5.1, 8, 9, 10: replace local-overflow/new-G rule with targeted termination/recovery-needed; preserve reject-before-accept and explicit connection exhaustion escape. | `RecoveryBatchTrailer.terminated/terminate_reason/next_generation`: document local queue termination at unchanged G versus true provider loss at new G. Existing reason bytes carry the distinction; no new outcome. |
| §11.5; `016`, `021`, `025`, `026` | §1 method list; §2 IDs listed; §§6/6.1 and diagrams: remove automatic new-G on install and pre-install-generation retry exception; specify same-G local installation, coordinated resumable S0 binding, snapshot gate versus B gate, derived transfer completion; one distinct snapshot offer per H, supersession retires H even at equal boundary. | Header; `RecoverySnapshotDescriptor.boundary_checkpoint`, `RecoverySnapshotComplete`, `RecoverySnapshotInstalled.generation`, `RecoverySnapshotConfirmRequest` message and generation/retry comments: same-G local install, no replacement token, no wire carrier for Complete, current-G retained retries; old-H supersession fence. `SnapshotFetch` stays one chunk/result. No message/tag/type change. |
| §11.6; `005`, `006`, `013`, `016`, `022`, `025` | §2 IDs listed; §§4, 5/5.1/5.2, 6/6.1, 7: add atomic effects+checkpoint or explicit durable fence, three progress observations, finite retries and the reconnect table; replace blanket “last confirmed” with durable known-safe resume where applicable. | Header; `RecoverySubscribeRequest.start_checkpoint`, `RecoveryReplayRequest.from_checkpoint`, `RecoveryConfirmRequest/Response`, `RecoverySnapshotConfirmRequest/Installed`: clarify persistence precondition, issued-checkpoint resume versus offered Confirm, sent versus acknowledged, same-G snapshot resume. No transaction/fence field. |

Requirement numbers in the table use the `SYN-URP-` prefix. The acceptance
plan maps every decision to planned observations. The §11 synchronization
called for at acceptance has been applied: owner prose and IDL comments
were aligned to §11, the conformance prose companion and registered
recovery cases were reconciled (CONF-URP-009/010 replaced with the
§11.2/§11.4 dispositions; CONF-URP-004/011 response shapes corrected),
all recorded in the acceptance PR. Registration is not execution: none of
this is evidence of conformance runs.

The registry disposition was also recorded: `conformance/manifest/schema.yaml`
and the repository validation tooling now admit `SYN-URP-*` requirement
references explicitly. Reserved `008/009` are preserved as reserved;
existing case identities were reconciled or replaced where the amendment
changed their meaning; and case/status wording remains truthful
(registered, not executed).

### 11.9 Formal approval and evidence record

- Author and assigned protocol/security reviewers: assigned via the
  acceptance PR with disclosed self-approval (single active maintainer,
  owner-ratified bootstrap authority per `GOVERNANCE.md` Sec. 3).
  Design decisions in §§11.1–11.6 are specified decisions, not delegated
  runtime choices.
- Public maintainer acceptance was recorded via the acceptance decision
  record per `GOVERNANCE.md` Sec. 3 (self-approval disclosed); release-scope,
  compatibility, persistence, resource-limit and principal-isolation review
  rationale are carried in that record. Snapshot same-generation semantics
  change earlier draft meaning despite unchanged tags; codec compatibility
  alone cannot establish that semantic change — the §11 review is the
  authority.
- Numeric bounds/methods/version and bounded retry/retention policy
  (§10, as amended) are adopted at acceptance. Each deployment documents
  finite retry attempts, absolute time budget, backoff and
  reply-cache count/bytes/lifetime; no implicit guaranteed minimum
  retention is introduced.
- Done in the acceptance PR: owner/IDL-comment and registry
  synchronization. Release notes and migration documentation land under
  the accepted decision via `CHANGELOG.md`/`MIGRATION.md`.
- Explicitly still pending, and NOT satisfied by this acceptance:
  independent Rust and Go both-role acceptance observations, crash/fault
  evidence, application persistence-contract review and final release
  authorization. The linked plan is non-executable and entirely not
  executed; static repository validation establishes neither behavior nor
  release readiness.

## Appendix: References

- `specifications/core/events.md` — generic push, subscriptions,
  ordering scope, delivery defaults, replay/continuation guidance,
  backpressure, reconnection rule.
- `specifications/core/reliability.md` — at-most-once default, retry
  conditions, duplicate tolerance, timeouts, backpressure, exhaustion,
  interruption mapping, no exactly-once claim.
- `specifications/core/capabilities.md` — identifier, explicit
  negotiation, mandatory interop, unknown handling, extension limits,
  isolation per connection.
- `specifications/architecture.md` — roles, layering and boundaries,
  compatibility and reserved values, threat and transport policy,
  requirement ownership, independence rules.
- `specifications/core/open-questions.md` — negotiation binding,
  resumption, and bound blockers; deferred flow-control, multiplexing,
  and retention items.
- `rfcs/0005-negotiation-bounds-identifiers.md` — negotiation binding
  decision, bound-setting, fixture-boundary and identifier context.
- `proto/syntra/v1/envelope.proto` — `Frame` envelope, existing
  `request` / `result` / `notification` variants, reserved 16, 17 and
  reserved `event`, `resume`, `ack`.
- `rfcs/README.md`, `rfcs/template.md` — lifecycle and draft structure
  followed by this file.
