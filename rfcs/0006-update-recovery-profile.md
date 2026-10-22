# RFC 0006: Optional Update/Recovery Profile

- RFC: 0006
- Title: Optional Update/Recovery Profile for ordered delivery, replay, snapshot recovery, and committed progress
- Author(s): TBD — blocker
- Status: Draft
- Date: 2026-10-21
- Target version: v1 minor (additive optional profile; no envelope changes)
- Relates to: `specifications/core/events.md` (§§1, 1A–1J, 1L–1M), `specifications/core/reliability.md` (SNTR-REL-001–010), `specifications/core/capabilities.md` (SNTR-CAP-001–007), `specifications/architecture.md` (SYN-ARCH-001/002/010–013/020/021/030–035/040–045/050/051/060–062), `specifications/core/open-questions.md` (blockers 1–3, deferred items 5–7), `rfcs/0005-negotiation-bounds-identifiers.md` (D1 binding), `proto/syntra/v1/envelope.proto` (`Frame`, reserved values)
- Reviewers: TBD — blocker (assigned by maintainers)

> Draft per `rfcs/README.md` Lifecycle. Only an Accepted RFC may modify
> normative behavior. This Draft is a proposal: implementations MUST NOT
> ship behavior from it, and no test, claim, or release may cite it as
> authority. Fill-every-section rule applies; unknowns are marked
> "TBD — blocker". BCP 14 keywords carry normative force only where
> capitalized. Examples are neutral only: echo, generic key/value,
> generic subscription.

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
      implicit continuity, carrying forward only the last confirmed
      checkpoint bytes bound to the same stable stream identity where
      the stream specification permits.
    - `SYN-URP-007` — The initiator MUST enforce its bounds (pending
      calls, subscriptions, queued bytes, page sizes), MUST back off on
      `RESOURCE_EXHAUSTED`, MUST accept an explicit continuity-loss
      signal with a new generation as the only overflow path, and MUST
      NOT silently accept truncated history as complete.

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
      per confirmed subscription, MUST assign one continuity generation
      per stream, MUST increment the generation on every continuity loss
      (overflow, retention expiry, revocation-driven reset, or snapshot
      rebase), and MUST bind every checkpoint to exactly one stable
      stream identity and generation pair. The stable stream identity
      is the stream selected by the stream selector and persists across
      reconnects, separate from the connection-scoped subscription
      handle which is fresh per subscription. A checkpoint from a prior
      subscription for the same stable identity MAY resume when the
      generation is still valid; checkpoints from a prior generation
      MUST be rejected with `FAILED_PRECONDITION`, never reinterpreted
      under the new generation.
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
      saturation the host MUST apply the documented policy — reject new
      work with `RESOURCE_EXHAUSTED` and/or end the affected stream with
      an explicit continuity-loss signal carrying a new generation —
      never queue without bound and never deadlock silently.
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
      `subscription_handle`, `snapshot_handle`, checkpoints,
      boundaries, `capability`, versions) are required and
      missing/mismatched MUST fail with `FAILED_PRECONDITION`, never
      silently applied; unknown profile operations MUST be rejected
      with `UNIMPLEMENTED`.
    - `SYN-URP-022` — Replay continuation echo and idempotent retry:
      replay applies only to resumption from a non-empty
      `start_checkpoint`. When subscribe used an empty
      `start_checkpoint` (initial subscription) the initiator MUST NOT
      send `RecoveryReplayRequest` and MUST start live at the
      subscribed boundary B on completion (or follow the snapshot path
      if signaled). For resumption, the initiator MUST send an empty
      `continuation_marker` on the first `RecoveryReplayRequest` with
      `from_checkpoint` set to the last confirmed checkpoint
      (non-empty), and MUST echo the previous page's marker verbatim
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

- Methods and payload mapping (proposed, no normative force):
  Provisional draft only: this table carries no normative force and
  lands only after acceptance, consistent with the Draft notice above.
  All versioned profile payloads travel inside the existing
  `RpcRequest` / `RpcResult` / `Notification` envelopes with no
  `Frame` changes. Neutral examples only: echo, generic key/value,
  generic subscription. Stream selectors name generic subscriptions;
  batch payloads carry echo or generic key/value bytes; subscription
  handles route generic subscription batches.

  | Operation | Method string | Request payload | Result / stream payloads |
  |---|---|---|---|
  | Negotiate | `/syntra.update-recovery/1/Negotiate` | `RecoveryNegotiateRequest` (`profile_version`, `min_version`, `max_version`, `capability` `syntra.update-recovery/1`) | `RecoveryNegotiateResponse` (`selected_version` plus confirmed bounds) |
  | Subscribe | `/syntra.update-recovery/1/Subscribe` | `RecoverySubscribeRequest` (`profile_version`, `stream_selector` for a generic subscription, `start_checkpoint`) | `RecoverySubscribeResponse` (`profile_version`, `subscription_handle`, `generation`, `catchup_boundary`) |
  | Replay | `/syntra.update-recovery/1/Replay` | `RecoveryReplayRequest` (`profile_version`, `subscription_handle`, `from_checkpoint`, `max_batches` 1..64, `max_bytes` 1..262144, `continuation_marker` empty on first request, echo of previous page's marker thereafter) | exactly one `RecoveryReplayPage` per `RpcResult` plus continuation marker; completion as `RecoveryReplayComplete` or `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification` payload |
  | CatchUp | `/syntra.update-recovery/1/CatchUp` | `RecoveryCatchUpRequest` (`profile_version`, `subscription_handle`) | `RecoveryCatchUpAccepted` in the terminal `RpcResult`; `RecoveryBatch` plus `RecoveryBatchTrailer{catchup_complete=true}` streamed as `Notification` payloads over the existing connection |
  | Confirm | `/syntra.update-recovery/1/Confirm` | `RecoveryConfirmRequest` (`profile_version`, `subscription_handle`, `generation`, `checkpoint` result or boundary) | `RecoveryConfirmResponse` (`confirmed_checkpoint`); snapshot boundary confirm yields `RecoverySnapshotInstalled` |
  | SnapshotOffer | `/syntra.update-recovery/1/SnapshotOffer` | versioned bytes: `subscription_handle` accept (`profile_version=1`) | `RecoverySnapshotDescriptor` (`snapshot_handle`, provider-proven `boundary_checkpoint`, `total_pages` 1..256, `page_bytes_max` 1..262144) |
  | SnapshotFetch | `/syntra.update-recovery/1/SnapshotFetch` | `RecoverySnapshotFetchRequest` (`profile_version`, `snapshot_handle`, `page_index` 0..255) | exactly one `RecoverySnapshotChunk` per `RpcResult` with `page_index` correlation plus `boundary_checkpoint` equality; completion as `RecoverySnapshotComplete` (`total_pages`, `total_bytes` 1..67108864) |
  | Unsubscribe | `/syntra.update-recovery/1/Unsubscribe` | `RecoveryUnsubscribeRequest` (`profile_version`, `subscription_handle`) | versioned bytes acknowledgement; targeted `RecoveryBatchTrailer{terminated=true}` with `terminate_reason` where applicable |

  Response framing rule (proposed, no normative force): each Replay
  call returns exactly one `RecoveryReplayPage` in its `RpcResult` plus
  its continuation marker; the initiator paginates with the same
  `/syntra.update-recovery/1/Replay` method until the marker is empty.
  Replay is sent only for resumption; initial subscriptions (empty
  `start_checkpoint`) skip Replay and start live at B on completion.
  The first `RecoveryReplayRequest` carries an empty `continuation_marker`
  with `from_checkpoint` set to the last confirmed checkpoint (non-empty); each
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

  Version negotiation rule (proposed, no normative force,
  `SYN-URP-020`/`SYN-URP-021`): every profile payload carries
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
  missing/mismatch MUST fail with `FAILED_PRECONDITION`; unknown
  profile operations MUST be rejected with `UNIMPLEMENTED`, never
  silently applied.

- Schema diff (`.proto` snippet, field numbers, reserved handling):
  Provisional draft only: the IDL
  (`proto/syntra/v1/recovery_profile.proto`), generated code, and
  conformance fixtures in this PR are provisional drafts, carry no
  normative force, and land only after acceptance, consistent with the
  Draft notice above that implementations MUST NOT ship behavior from
  this proposal. The proposed change is additive and envelope-neutral:
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
    from its last confirmed checkpoint via
    `RecoveryReplayRequest.from_checkpoint` (non-empty; initial subscriptions with empty
    `start_checkpoint` skip replay and start live at B on completion)
    and validates each `RecoveryReplayPage.catchup_boundary` and each
    completion signal boundary against B before releasing held live batches;
    live `Notification`
    batches for the stream held until the catch-up completion signal
    under bounded holding per the documented overflow policy
    (while held during CATCHING_UP, saturation MUST end the stream
    with explicit continuity loss carrying a new generation and a
    CATCHING_UP -> CONTINUITY_LOST transition clearing the held queue,
    never a bare `RESOURCE_EXHAUSTED` that stalls waiting for an
    unreachable completion signal; outside holding, reject with
    `RESOURCE_EXHAUSTED` and/or continuity loss, never silent drop);
    `CATCHING_UP → LIVE` on catch-up
    completion signal with held then new live batches chaining from B;
    `CATCHING_UP → SNAPSHOT_REQUIRED` on
     snapshot-required signal; `SNAPSHOT_REQUIRED → INSTALLING` on
    accepted snapshot offer; `INSTALLING → LIVE` on boundary confirm;
    any streamed state → `TERMINATED(targeted)` on per-stream terminal
     signal or terminate operation; `cancel` applies to the invoking RPC
     only and does not by itself terminate the stream unless the confirmed
     stream binding states so; any streamed state → `CONTINUITY_LOST(new
    generation)` on overflow/expiry/revocation reset, then re-entry via
    fresh subscribe or replay-from-confirmed-checkpoint where offered.
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
  Every bound is deployment-documented; the following are the proposed
  profile defaults matching `proto/syntra/v1/recovery_profile.proto`
  header defaults (still Draft, see §10; carry no normative force until
  acceptance):
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
    |<-- result{opaque handle, gen 7,     |
    |         fixed B} -------------------|
    |         (live batches held until    |
    |          catch-up done; bounded      |
    |          holding per documented      |
    |          overflow policy)            |
    |--- request{replay from last confirmed}|
    |                                   -->|
    |<-- notification{page 1, cont C} -----|
    |<-- notification{page 2, cont end} ---|
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
    |--- request{snapshot offer accept} -->|
    |<-- result{snapshot page 1 / boundary||
    |         checkpoint proven by          |
    |         provider} -------------------|
    |--- request{confirm boundary} ------->|
    |<-- result{installed, gen 8} ---------|
```

## 4. Detailed design

Mechanics: framing, encoding, correlation, cancellation, error mapping,
capability negotiation, unknown-field/profile handling, resource bounds.

- Framing: unchanged. The profile adds no transport framing and no
  envelope variant. Existing length/type prefixes and envelope
  validation apply unmodified.
- Encoding: profile control operations use standardized generic RPC
  methods under the profile identifier
  (`/syntra.update-recovery/1/Negotiate`,
  `/syntra.update-recovery/1/Subscribe`,
  `/syntra.update-recovery/1/Replay`,
  `/syntra.update-recovery/1/CatchUp`,
  `/syntra.update-recovery/1/Confirm`,
  `/syntra.update-recovery/1/SnapshotOffer`,
  `/syntra.update-recovery/1/SnapshotFetch`,
  `/syntra.update-recovery/1/Unsubscribe`), each with versioned opaque
  payload bytes defined by this profile. Streamed content uses
  `Notification` payloads carrying versioned batch bytes
  (predecessor/result checkpoints, generation, continuation marker,
  completion or snapshot-required signal where applicable). A neutral
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
  checkpoints, boundaries, `capability`, versions) are required and
  missing/mismatch MUST fail with `FAILED_PRECONDITION`; unknown
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
    deadline fixtures at exactly-MAX and MAX+1; overflow yields explicit
    continuity loss with a new generation.
  - Authorization hooks: subscribe/replay/snapshot/continuation each
    re-evaluated; revoked/expired principal stops delivery with a typed
    signal; rejections leak no credentials.
  - Reserved/mandatory interop: reserved 16, 17, `event`, `resume`,
    `ack` untouched; mandatory-only peer interoperates with a
    profile-confirming peer at mandatory behavior.
- [ ] Requirement-to-test trace (ID → test):
  `SYN-URP-001`/`SYN-URP-020` → negotiation/version fixtures;
  `SYN-URP-002` → envelope preservation fixtures;
  `SYN-URP-003`/`SYN-URP-012`/`SYN-URP-013` →
  generation/checkpoint fixtures; `SYN-URP-004`/`SYN-URP-014` →
  paging/catch-up fixtures; `SYN-URP-015` → completion/snapshot-required
  fixtures; `SYN-URP-005`/`SYN-URP-016` → commit/snapshot fixtures;
  `SYN-URP-006`/`SYN-URP-017` → routing/termination and state-separation
  fixtures; `SYN-URP-007`/`SYN-URP-018` → bound fixtures;
  `SYN-URP-010`/`SYN-URP-011`/`SYN-URP-019` → negotiation/schema/hook
  fixtures; `SYN-URP-021` → unknown-field/schema fixtures;
  `SYN-URP-022` → continuation-echo and idempotent-retry fixtures
  (mismatched marker/from rejected; duplicate of the immediately
  preceding completed request returns the retained page);
  `SYN-URP-023` → subscribe-boundary fixtures (empty boundary rejected,
  pages validated against the subscribed boundary).
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
  exactly-MAX/MAX+1, and overflow always carries an explicit
  continuity-loss signal with a new generation.
- Generation-management defects could strand streams on stale
  checkpoints. Mitigation: stale checkpoints fail loudly with
  `FAILED_PRECONDITION`, recovery is always explicit re-subscribe or
  snapshot rebase, never silent reinterpretation.

## 10. Unresolved questions and blockers

Proposed values below are still Draft, not Accepted. Maintainers must
confirm or replace with rationale; implementations MUST NOT ship
behavior from this proposal and no test, claim, or release may cite it
as authority.

1. Proposed numeric bounds (from `proto/syntra/v1/recovery_profile.proto`
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
   0..255, `page_bytes` non-empty at most 262144,
   `RecoverySnapshotComplete{total_pages}` 1..256, `total_bytes`
   1..67108864); effective deadline default for profile RPCs 5 s where
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
2. Proposed method strings, canonical payloads, and version
   negotiation rule (`SYN-URP-020`/`SYN-URP-021`): exact
   standardized generic RPC methods are
   `/syntra.update-recovery/1/Negotiate`,
   `/syntra.update-recovery/1/Subscribe`,
   `/syntra.update-recovery/1/Replay`,
   `/syntra.update-recovery/1/CatchUp`,
   `/syntra.update-recovery/1/Confirm`,
   `/syntra.update-recovery/1/SnapshotOffer`,
   `/syntra.update-recovery/1/SnapshotFetch`, and
   `/syntra.update-recovery/1/Unsubscribe` under identifier
   `syntra.update-recovery/1`. Canonical payloads are
   `RecoveryNegotiateRequest`/`RecoveryNegotiateResponse`,
    `RecoverySubscribeRequest`/`RecoverySubscribeResponse`
    (response carries `catchup_boundary` fixed at subscribe accept),
    `RecoveryReplayRequest` (with `profile_version` and `continuation_marker` echo) with exactly one `RecoveryReplayPage` per
    `RpcResult`, `RecoveryCatchUpRequest` with `RecoveryCatchUpAccepted`
    in the terminal `RpcResult` (batches and completion trailer via
    `Notification`),
   `RecoveryConfirmRequest`/`RecoveryConfirmResponse`, and
   `RecoverySnapshotFetchRequest` with exactly one
   `RecoverySnapshotChunk` per `RpcResult`, all defined in
   `proto/syntra/v1/recovery_profile.proto`. The Negotiate invocation
   offers min and max profile versions (proposing 1/1); the host selects
   the maximum version it implements within the offered range. No
   overlap MUST fail with `FAILED_PRECONDITION` in `RpcResult`. Every
   other operation carries `profile_version=1`; mismatch MUST fail with
   `FAILED_PRECONDITION`. Wire policy defers to
   `specifications/core/serialization.md` (`SNTR-SER-003`) and
   `specifications/core/versioning.md` (`SNTR-VER-004`): unknown
   Protobuf fields MUST be ignored unless explicitly marked `Critical`;
   fields explicitly marked `Ignorable` MUST be ignored;
   `profile_version` and routing/identity fields are required and
   missing/mismatch MUST fail with `FAILED_PRECONDITION`; unknown
   profile operations MUST be rejected with `UNIMPLEMENTED`, never
   silently applied.
3. Proposed retention rule: retention stays deployment-documented with
   no implicit minimum assumed by initiators. Each deployment offering
   replay documents its retention minimum. A replay or catch-up request
   for a checkpoint outside retention MUST fail with
   `FAILED_PRECONDITION` in `RpcResult` while emitting
   `RecoveryBatchTrailer{snapshot_required=true}` in a `Notification`
   payload, per `SYN-URP-015`.
4. Proposed snapshot offer lifetime and supersede rule: an offer is
   valid from its `RecoverySnapshotDescriptor` until transfer completes
   with `RecoverySnapshotComplete` plus boundary confirm, or until
   targeted termination, continuity loss with a new generation, or
   supersede. Invalidation flows through the snapshot handle and RPC
   outcome without ordering checkpoint bytes: in-flight
   `SnapshotFetch` under a superseded `snapshot_handle` fails with
   `FAILED_PRECONDITION` (superseded), and/or the host emits an
   explicit continuity-loss/new-offer signal; the initiator MUST
   discard prior pages on supersede and MUST NOT install across
   boundaries. A `RecoverySnapshotChunk` is associated only when its
   `boundary_checkpoint` bytes equal the currently offered descriptor
   `boundary_checkpoint` bytes; equality validates association only,
   recency comes only from the explicit supersede signal or RPC
   outcome. Completion requires matching `total_pages` and
   `total_bytes`, and installation completes only when the initiator
   confirms that exact boundary checkpoint through
   `/syntra.update-recovery/1/Confirm`, yielding
   `RecoverySnapshotInstalled` with the new generation per
   `SYN-URP-016`.
5. Proposed fixture hosting note: conformance fixtures for this profile
   live in the conformance suite as additive fixtures using neutral
   payloads only (echo, generic key/value, generic subscription),
   tracing to §8 acceptance criteria and `SYN-URP` IDs. Interop evidence
   requires two independent profile implementations or recorded
   fixtures from two sources demonstrating mandatory-only interop plus
   confirmed-profile recovery interop; placeholders are tracked where
   implementations do not yet exist.

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
