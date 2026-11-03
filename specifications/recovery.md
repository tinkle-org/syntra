# Syntra 1.0 — Notifications and update recovery

Notifications deliver updates independently of RPC results. The optional
`syntra.update-recovery/1` capability adds scoped checkpoints, fixed-boundary
replay, snapshot recovery, and confirmation of durable application progress.
This page defines those semantics. BCP 14 keywords are normative.

[Wire format](wire-format.md) owns envelopes and raw validation;
[RPC](rpc.md) owns correlation, deadlines, cancel, and output bounds;
[connection](connection.md) owns readiness/replacement;
[RPC capability negotiation](rpc.md#6-optional-capability-negotiation) owns the
shared negotiation mechanism; [security](security.md) owns identity and
credential policy; [transports](transports.md) owns carriage. Recovery payload
representation is defined by
[`recovery_profile.proto`](../proto/syntra/v1/recovery_profile.proto).

`profile_version` is the recovery payload version on the same Syntra
connection; it does not select security or transport.

```text
Initiator                                             Host
    |                 Connection ACTIVE                 |
    |--- Negotiate(syntra.update-recovery/1, version 1) -->|
    |<-- selected version and bounds --------------------|
    |--- Subscribe(selector, durable checkpoint C) ------>|
    |<-- fresh handle H, generation G, fixed boundary B --|
    |--- Replay(H, from=C, marker=empty) ---------------->|
    |<-- one page; repeat with its checkpoint/marker -----|
    |<-- RecoveryNotification{replay_complete(H,G,B)} -----|
    |    Validate and durably apply recovered data        |
    |    through B before releasing held live data        |
    |<-- RecoveryNotification{batch(H,G,predecessor,C2)} --|
    |    Validate; persist application effects and C2     |
    |--- Confirm(H,G,C2) -------------------------------->|
    |<-- confirmed checkpoint C2, unchanged G ------------|
```

The diagram shows resumption from non-empty C. An initial subscription uses
an empty checkpoint, skips Replay, and establishes its live baseline at B
through CatchUp or live validation. Requests and results are correlated RPCs;
notifications use `request_id=0`. CatchUp and snapshot transfer are detailed below.

## 1. Notifications and optional delivery

**SNTR-EVENT-001**, **SNTR-EVENT-011** — Event streams are OPTIONAL.
Initiators MUST NOT assume subscription success; unsupported subscriptions
MUST fail `UNIMPLEMENTED`, never silent ignore or unrelated delivery.
Only a confirmed capability supplies its stream contract.

**SNTR-EVENT-002**, **SNTR-EVENT-003**, **SNTR-EVENT-009** — The core
defines no event ID, stream ID, or cursor field. Identity/deduplication,
handles, and opaque expiring cursors live inside payloads under the
confirmed capability. The core MUST NOT synthesize IDs, parse cursors, or
infer authority or cross-carrier validity from them.

**SNTR-EVENT-004**, **SNTR-EVENT-010** — Subscriptions are established,
modified, and cancelled through generic RPC after ACTIVE. Termination
MUST be explicit through a typed capability signal or RPC error, except on
connection loss. `Cancel` of a subscribe call cancels that RPC only unless
the confirmed stream contract explicitly binds its lifetime. Hosts SHOULD
stop delivery promptly; initiators MUST tolerate pending post-cancel events.

**SNTR-EVENT-005** — Notifications use `request_id=0`, never complete
an RPC, and MUST NOT be emitted before ACTIVE or once CLOSING begins. A
pre-ACTIVE notification MUST fail the handshake: local
`FAILED_PRECONDITION`, discard without delivery or later queueing, then
CLOSING→CLOSED through the native close signal. It establishes no subscription.
The emission restriction does not reject a valid in-transit notification
received during CLOSING: bounded admission/loss accounting follows
[connection](connection.md#1-establishment-and-states), never new emission
or RPC completion.

**SNTR-EVENT-006**, **SNTR-EVENT-007**, **SNTR-EVENT-008** — The core
guarantees no cross-stream/cross-connection order or durable delivery.
Within an ordered carrier a subscription SHOULD retain send order.
Stronger ordering/replay guarantees REQUIRE a confirmed stream contract
that documents retention, duplicates, and coordination. Recovery below
defines those mechanics; application data formats and replay storage
remain provider-owned.

**SNTR-EVENT-020**, **SNTR-EVENT-021**, **SNTR-REL-005** — Clients MUST
negotiate before subscribing, handle interleaved notifications independently
of call correlation, tolerate duplicates without protocol errors/storms,
and explicitly re-subscribe after reconnect. Hosts SHOULD minimize
duplicates but MAY emit them in replay/reconnect overlap. No stream
survives its connection by default.

**SNTR-EVENT-030**, **SNTR-EVENT-031** — Hosts MUST authorize each
subscription, bound per-connection/per-subscription counts, rates and
bytes, apply a documented overflow policy, and MUST NOT emit for
revoked/expired principals. Affected subscriptions terminate with a typed
signal where possible. Unbounded queues, silent truncation, and silent
deadlock are forbidden. Recovery's more specific overflow rule is §7.

## 2. Scope and negotiation

Recovery is optional and explicitly negotiated on each active connection.
Without confirmation, the connection supplies only mandatory behavior and
previously confirmed options, with no recovery guarantee from this capability.

| Symbol | Meaning |
|---|---|
| P | Authenticated principal/authorization scope |
| S | Stable provider-resolved stream identity within P; not selector bytes |
| G | Provider continuity generation for `(P, S)` |
| C | Opaque checkpoint bound to `(P, S, G)` |
| H | Fresh connection-scoped subscription/delivery-instance handle |
| B | Non-empty immutable catch-up boundary captured at Subscribe accept |
| X | Snapshot offer handle |
| S0 | Provider-proven boundary of the offered snapshot |

A recovery round is identified by **connection + H**, never by equal B
bytes. Each subscription has independent delivery and recovery progress;
subscriptions observing the same `(P, S)` share its provider generation G.
A handle authorizes nothing by itself and is never reused within a
connection after retirement.

All methods have prefix `/syntra.v1.UpdateRecovery/`:

| Method suffix | Request / success payload |
|---|---|
| `Negotiate` | `RecoveryNegotiateRequest` / `RecoveryNegotiateResponse` |
| `Subscribe` | `RecoverySubscribeRequest` / `RecoverySubscribeResponse` |
| `Replay` | `RecoveryReplayRequest` / exactly one `RecoveryReplayPage` |
| `CatchUp` | `RecoveryCatchUpRequest` / `RecoveryCatchUpAccepted` |
| `Confirm` | `RecoveryConfirmRequest` / `RecoveryConfirmResponse` |
| `SnapshotOffer` | `RecoverySnapshotOfferRequest` / `RecoverySnapshotDescriptor` |
| `SnapshotFetch` | `RecoverySnapshotFetchRequest` / exactly one `RecoverySnapshotChunk` |
| `SnapshotConfirm` | `RecoverySnapshotConfirmRequest` / `RecoverySnapshotInstalled` |
| `Unsubscribe` | `RecoveryUnsubscribeRequest` / `RecoveryUnsubscribeResponse` |

Each success is a correlated `RpcResult.payload`. Each recovery
`Notification.payload` contains exactly one versioned `RecoveryNotification`
selecting `batch`, `replay_complete`, or `trailer`. Its outer `profile_version`
MUST equal the inner payload version, currently 1; an unset selection is
invalid. Replay pages travel only in correlated results.

**SYN-URP-001** — The initiator MUST negotiate after ACTIVE through the
standardized negotiation call, the only recovery operation permitted before
confirmation. It MUST NOT use other recovery operations before confirmation
on this connection and MUST handle partial acceptance by mandatory-only
fallback plus previously confirmed options.

**SYN-URP-002**, **SYN-URP-011** — Both roles MUST carry versioned recovery
bytes only in existing request/result/notification payloads, MUST NOT add
envelope fields/variants, and MUST preserve [core wire validation and
reservations](wire-format.md#2-bounded-raw-validation-and-first-error-precedence).
The host MUST implement the methods above; unknown operations fail
`UNIMPLEMENTED`, with no weakening of envelope validation.

**SYN-URP-010** — The host MUST confirm only implemented behavior for the
bound principal and this connection, document confirmed versions/bounds,
accept its Negotiate call after ACTIVE before confirmation, and reject
other unconfirmed-capability operations with `UNIMPLEMENTED`. An unconfirmed
option on a connection that has confirmed the capability fails
`FAILED_PRECONDITION`. Confirmation never transfers to another connection.

**SYN-URP-020** — The host MUST select the highest implemented recovery payload
version in the offered range, confirm only it, and fail no overlap with
`FAILED_PRECONDITION` in the result. The current recovery payload version and offered
version bounds are 1; the capability is exactly `syntra.update-recovery/1`.
Every other payload MUST carry that `profile_version`; missing/mismatched
versions fail `FAILED_PRECONDITION`.

**SYN-URP-021** — Unknown recovery Protobuf fields MUST be ignored unless
explicitly marked Critical in the IDL; Ignorable fields MUST be ignored.
Unknown operations fail `UNIMPLEMENTED`. Emptiness is per field:

| Field | Empty behavior |
|---|---|
| Capability, versions, required selector/H/X | Missing/invalid → `FAILED_PRECONDITION` |
| `start_checkpoint` | Empty = initial subscription; non-empty = durable known-safe C |
| `continuation_marker` | Empty = first replay request or no further page |
| `terminate_reason` | Empty = no termination; required non-empty for termination |
| Predecessor/result/boundary fields | Pairing/presence per §§3–5; subscribe B is always non-empty |

Field bounds are measured in bytes, regardless of encoding. Both roles MUST
enforce the IDL constraints, including these wire maxima:

| Field or payload | Wire constraint |
|---|---|
| Capability | Non-empty ASCII, at most 256 bytes |
| Stream selector | Non-empty opaque bytes, at most 1,024 bytes |
| Subscription/snapshot handle | Non-empty opaque bytes, at most 256 bytes |
| Checkpoint, boundary, continuation marker | At most 4,096 bytes; emptiness as above and per operation |
| Termination reason | At most 256 bytes; non-empty for termination |
| Replay request | `max_batches` 1–64; `max_bytes` 1–262,144 |
| Replay page | At most 64 serialized batches; each entry and their total at most 262,144 bytes |
| Serialized `RecoveryBatch` | At most 262,144 bytes, including metadata and encoding overhead |
| Snapshot descriptor | `total_pages` 1–256; `page_bytes_max` 1–262,144 |
| Snapshot chunk | `page_index` 0–255 and below offered page count; non-empty `page_bytes`, at most 262,144 bytes and within offered page-byte bound |

Confirmed or requested tighter limits still apply. The core total-frame bound
also includes the envelope and recovery encoding overhead.

## 3. Checkpoints, routing, and continuity

**SYN-URP-003** — The initiator MUST track one G per delivery instance,
treat C as opaque bytes bound to `(P, S, G)`, persist that context with C,
and present exact bytes with explicit predecessor/result pairing. It MUST
NOT perform checkpoint arithmetic, infer ordering, parse structure, or
infer scope/authority from selector equality.

**SYN-URP-012** — The host MUST resolve `(P, S)` and bind C to exactly
one `(P, S, G)`. G changes ONLY on true provider history loss or explicit
shared rebase in that scope, not local saturation, ordinary retention
pruning, or targeted revocation without policy-driven history reset.
A change invalidates all prior-generation checkpoints in the scope,
fences outstanding pages/offers/confirms/batches, and signals a trailer
with old `generation` and new `next_generation`. If the signal is lost,
the next old-generation operation MUST fail `FAILED_PRECONDITION`; old
bytes never silently acquire new meaning. Multi-scope provider loss
invalidates every affected scope explicitly. Identical selectors do not
establish identical scope or authority.

**SYN-URP-013** — Every batch MUST state predecessor and result
checkpoints; neither role computes successors by arithmetic. Before
exposing committable results or snapshot boundaries the host/provider MUST
establish recoverable issued bindings to `(P, S, G)`, durable or
reconstructible independently of Confirm receipt and per-handle reply
caching. Lost binding requires explicit failure/recovery, never an
assumption that lost acknowledgement means no local commit, or an invented
generation. Validating an issued resumable C differs from accepting an
unoffered Confirm: batch Confirm still requires a committable result issued
for that H/G, SnapshotConfirm the current offered boundary. Subject to
those conditions the host MAY accept valid C without a previous confirmation
record. Forged, malformed, cross-stream/generation/principal checkpoints
MUST fail `FAILED_PRECONDITION`, or `UNAUTHENTICATED` where token-like,
without leaking other principals' state.

**SYN-URP-006**, **SYN-URP-017** — Each batch MUST route to exactly its
current delivery instance. Per-stream termination tears down only that
instance, with a typed signal or invocation error where possible, not the
connection unless the connection itself ends. Unsubscribe ends the targeted
H; its response echoes H and carries the generation at termination.
Reconnect ALWAYS means fresh authenticated establishment, re-negotiation,
and Subscribe with fresh
H/B. It transfers no capability, pagination, or snapshot handle. Carry
forward only durable known-safe C under the same `(P, S)` where the host
validates it. Track locally durable C, Confirm sent, and peer-acknowledged
C as three distinct observations. Post-termination batches may race and
must be tolerated; retired-handle output has no current-round effect.
For a recognized operation on a confirmed connection, an invocation
presenting foreign, unrecognized, or retired H fails `FAILED_PRECONDITION`,
not `UNIMPLEMENTED`; handle validation uses the authenticated connection,
principal scope, generation, and operation's retained retry context.
An exact retry returns retained data only while that operation's scoped
eligibility still holds (§§4–5); a cache cannot revive a retired handle.
Ignoring stale recovery output never replaces an RPC terminal outcome
already selected under [RPC terminal rules](rpc.md#3-one-elapsed-deadline-and-one-terminal-outcome).

**SYN-URP-026** — Generation-change trailers select only old G plus
nonzero new `next_generation`, no second outcome. Every trailer MUST select
exactly one outcome: `next_generation`, `catchup_complete=true`,
`snapshot_required=true`, or `terminated=true`; an unset outcome is invalid.
Local saturation selects only `terminated=true` at current G with ASCII
`local-queue-exhausted`, never `next_generation`. Retention pruning,
connection end, per-stream termination,
offer/persist failure, confirm retry, or validation failure does not change
G. Revocation is targeted termination; history invalidation is only an
explicit scoped policy decision. No initiator manufactures provider G.

## 4. Fixed-boundary replay and catch-up

**SYN-URP-004** — Every round MUST begin with Subscribe and fresh H plus
the non-empty fixed B captured at that accept. Consume bounded correlated
replay pages, follow continuation, stop at B, and validate recovered/live
batches under the same rules. Duplicate result checkpoints are
tolerated only after version, handle/scope, G, authorization, and bounds
validation; equal bytes from another context are not duplicates. Held
live batches MUST NOT be released before matching validated completion.

**SYN-URP-014** — Each Replay MUST return exactly one page in its
correlated result, with continuation marker and fixed B. Oversized history
MUST be paged, never burst beyond queues. Invocation-triggered CatchUp
streams notification batches with the same validation and authorization as
live batches, starting from the checkpoint bound by Subscribe. A round
chooses Replay or CatchUp, never both concurrently. B MUST NOT advance
during a round. Retired-handle pages, completions, results, and batches have
no effect even if B equals the new round's B.
Bounded exact duplicate retries return retained pages/completion verbatim
without pagination/application advancement.

**SYN-URP-022** — Replay is only for non-empty `start_checkpoint`.
Initial subscriptions MUST skip Replay and obtain their live baseline at B
by CatchUp or live validation. On resumption the first Replay has empty
marker and `from_checkpoint=C` (durable, non-empty); each continuation
echoes the previous marker verbatim and uses the previous page's result
checkpoint. Mismatch/non-chaining fails `FAILED_PRECONDITION`, except an
exact duplicate of the immediately preceding completed request in the
current round returns the retained last page verbatim without advancing.
Retries use fresh RPC IDs. For lost completion, bounded exact retry of
that request or the same CatchUp returns retained page/acceptance and
re-emits completed-round completion without moving B, restarting pagination,
or rerunning effects. Retained-page eligibility ends on supersede,
termination, continuity change, or expiry. Retry/deadline exhaustion retires
H and starts a fresh Subscribe from durable C; no same-H second round/marker reset.

**SYN-URP-023** — Empty subscribe B MUST fail `FAILED_PRECONDITION`.
Each page B and completion boundary (`RecoveryReplayComplete`,
catch-up-complete trailer, or `RecoveryCatchUpAccepted`) MUST match
subscribed B. Release held live only after all recovered data through B
passes validation and local persistence and completion matches current
connection, H, G, recovery payload version, and exact B. Mismatch fails
`FAILED_PRECONDITION` or local recovery-needed without release. Equal B
alone never identifies a round. Duplicate current completions are
idempotent and never redeliver data. An already applied result checkpoint
bypasses predecessor chaining only after the other validations above.
Snapshot-held data has its separate gate in §5.

**SYN-URP-024** — Initial empty-start live baseline is not restoration of
historical application state. A resumption replays durable C while holding
live data. After progress C2 beyond B1, a new gap, newly detected loss,
or invalid completion retires H1 **locally first**: discard held data and
pagination state, invalidate pending snapshot offers; best-effort Unsubscribe;
Subscribe from C2 for fresh H2/B2 without waiting indefinitely for teardown.
Recover toward B2,
never obsolete B1. If C2 is no longer replayable use explicit snapshot
fallback, never empty-start silent reset. Idle is not caught-up; no
completion means no release. Exhausted lost-completion retries likewise
retire H and Subscribe anew. Remote resource bounds may require reconnect/backoff.

**SYN-URP-015** — The host MUST signal explicit catch-up completion.
Outside-retention or otherwise unrecoverable replay MUST fail its
invocation with `FAILED_PRECONDITION` and emit
`RecoveryBatchTrailer{snapshot_required=true}` as a notification. No G
change, silent unrelated restart, or silent truncation is permitted.

## 5. Snapshot transfer and local installation

**SYN-URP-016** — The host MUST offer and transfer snapshots through
bounded generic invocations. The descriptor binds `(P, S, H, G, S0)`
and carries H, X, provider-proven S0, page count N, and page-byte bound;
it has no G field, so G is the subscription's established generation.
At most one distinct X is offered under H. Exact duplicate offer returns
the retained descriptor. Superseding retires H and requires fresh Subscribe
before another X, even if S0/G are unchanged. Gap, continuity-loss, and
continuation-expiry reports invalidate pending offers.

Each SnapshotFetch returns one correlated chunk. Correlate RPC ID, X,
index, version, and exact S0. Indices 0..N−1 are fetched once logically;
exact retries never inflate counts. Complete index coverage and bounded
byte accounting establish local transfer completion. The IDL type
`RecoverySnapshotComplete` records this locally; it is not a wire variant.
Superseded X, retired H, or mixed pages fail `FAILED_PRECONDITION`;
discard uninstalled snapshot data without partial activation.
Oversized snapshots are rejected without partial install; exceeding page
count requires a fresh round and offer after Subscribe.

Installation is application-local durable replacement under S0, not a
shared rebase. G remains unchanged; subsequent batches chain from S0 in
that G and unrelated subscribers continue from their own C. The initiator
opens the snapshot live gate only after validated
`RecoverySnapshotInstalled` matching H/G/S0 (and recovery payload version), not
local durability alone or an old replay completion. Later catch-up needs
fresh H/B. A genuine provider rebase is signaled before a descriptor in
the new G, never as an install side effect. Before descriptor exposure the
host/provider coordinate a recoverable S0-to-`(P, S, G)`-and-content binding,
resumable after lost SnapshotConfirm/response independently of per-handle
cache. Lost binding requires explicit failure and snapshot fallback or
scoped invalidation, never interpreting old S0 in new G. Snapshot formats
remain provider-defined; Syntra owns transfer, boundary, and confirmation only.

**SYN-URP-025** — SnapshotConfirm uses exact offered S0 and current G.
Success carries unchanged G/S0, no replacement token. An exact duplicate
for the same authorized H, version, G, and boundary MUST return the
original retained installed response without reinstalling or G change,
only while retained and not superseded, terminated, continuity-changed,
or cache-expired. Boundary equality alone is insufficient. On expiry or
exhaustion use §6 reconnect, never repeated installation or fabricated
generation exceptions. Batch Confirm is stop-and-wait/idempotent: same
authorized current H, version, G, and issued checkpoint return the
confirmation without new effects/G change. `RecoveryConfirmResponse`
echoes the confirmed checkpoint and H with unchanged G.
Never-issued committable checkpoints fail `FAILED_PRECONDITION` without
advance. Supersede, termination, continuity change, and cache expiry end
retained-response eligibility; protection/counts/lifetimes are documented.

## 6. Persistence, confirmation, and crash recovery

**SYN-URP-005** — The initiator MUST validate received data and durably persist
its represented application effects and recovery context before sending
Confirm or SnapshotConfirm.
Persist covers represented application effects, not just checkpoint bytes:
atomically persist effects with `(P, S, G, C)`, or use a declared durable
idempotent recovery fence that identifies the operation and reconciles or
reapplies safely across every crash window. A checkpoint ahead of durable
application state is unsafe. Effects ahead of C require that fence or a
fresh local snapshot. The application MUST declare its durable success
point/fence; decode, transport receipt, or a write that is not yet durable
does not establish it. Syntra supplies neither a storage transaction nor
exactly-once application effects.

Durable known-safe C MAY be newer than peer-acknowledged C after lost
acknowledgement. Sending is not acknowledging; acknowledging never repairs
non-atomic local writes. Confirmation is stop-and-wait; exact method/payload
retry uses fresh RPC IDs, finite attempts, an absolute deadline, and
backoff. Late retired-H responses do not advance the current round.
Exhaustion preserves durable data and triggers reconnect/re-subscription,
never guessed rollback, infinite retry, or implicit acknowledgement.

| Durable evidence on restart | Recovery action / host check |
|---|---|
| No durable application progress | Reconcile via application fence and prior safe C; with none, explicitly choose initial live-only or snapshot. Live-only never claims restored history. |
| Effects + C durable; Confirm unsent | Subscribe with C; validate issued binding, authority, scope, G, retention despite no confirmation record. |
| Confirm sent; response lost | Same resume from C; no peer acknowledgement is inferred. |
| Response received; acknowledgement bookkeeping lost | Durable C suffices subject to host validation; missing application writes are not backfilled by peer confirmation. |
| Snapshot + S0 durable; confirm/response lost | Resume exact S0 and persisted scope/G; discard old X/H; no G inferred from an unreceived response. |
| Host restart/cache expiry; binding/history intact | Validate C/S0 independently of old retry cache, capture new B, resume. |
| Same scope/G; history outside retention | Explicit invocation failure plus snapshot-required; no empty-start reset. |
| Provider loss/shared rebase changed G | Reject old C, explicitly invalidate scoped checkpoints, establish current-generation subscription/snapshot. |
| Different P/S, revoked/expired authority, invalid binding | Deny before effects/progress; no checkpoint transplant or inferred continuity on reauthorization. |

## 7. Bounds, overflow, and authorization

**SYN-URP-007**, **SYN-URP-018** — Both roles MUST enforce documented
finite count, byte, and time limits for pending invocations, subscriptions,
queued delivery, pages, retention, and retained retry responses, per
connection, per principal, and in aggregate as applicable. They MUST back
off on `RESOURCE_EXHAUSTED`. Negotiate confirms
`max_subscriptions_per_connection`, `max_pending_rpcs_per_connection`,
`max_page_bytes`, and `max_snapshot_pages`. Page and snapshot limits MUST
respect §2's wire maxima. Every invocation has a bounded effective deadline
under [RPC](rpc.md#3-one-elapsed-deadline-and-one-terminal-outcome);
retention and retry-response lifetimes have no implicit minimum.

On accepted-subscription overflow the host MUST end only that instance
with mutually exclusive `terminated=true`, current G, non-empty ASCII
`terminate_reason=local-queue-exhausted`, no `next_generation`. Discard held
data rather than leave a silently live/stalled instance. An affected
pending call MAY also fail `RESOURCE_EXHAUSTED`; rejecting new work before
subscription acceptance remains valid. If terminal control cannot queue,
reserve bounded control capacity or explicitly close the exhausted
connection. Queue exhaustion never changes provider G.

On initiator-local overflow, end that subscription or surface explicit
recovery-needed, discard held data and pagination state, retire H, and begin
fresh Subscribe. Never fabricate G or invalidate another subscriber's C.
Unbounded queueing, silent deadlock, and silently complete truncated
history are forbidden. Shutdown stops new batches and follows [RPC's
bounded drain/settlement](rpc.md#fifo-output-and-shutdown);
loss maps invocations without a selected terminal to `UNAVAILABLE` with
unknown outcome. Already-selected terminal outcomes remain immutable;
connection loss or handle retirement can prevent delivery but never
discard or select a replacement terminal outcome.

**SYN-URP-019** — Every operation requires authorization: subscribe,
replay, snapshot offer/transfer, continuation, catch-up, and confirm.
The host MUST re-evaluate the bound principal, emit nothing for
revoked/expired authority, and deny with targeted termination where
possible. Revocation alone is not history reset. If policy invalidates
recovery history, change only that scoped G/binding explicitly; regrant
never revives invalidated bindings. Other principals retain their valid
subscriptions/checkpoints. Credentials remain opaque sensitive bytes,
never logged, core-persisted, or placed in errors. Handles/checkpoints/
selectors authorize nothing by themselves. Errors leak no checkpoint
secrets or private provider diagnostics.

## 8. Failure scope

| Condition | Observable result |
|---|---|
| Unknown operation or unconfirmed capability | `UNIMPLEMENTED` for that invocation |
| Unknown provider-resolved stream on Subscribe | `UNIMPLEMENTED` for that invocation |
| Invocation presenting foreign, unrecognized, or retired H | `FAILED_PRECONDITION`; retained retry context is valid only for its authorized current scope and operation, never handle revival |
| Confirmed-capability option not confirmed, missing/mismatched version/boundary/marker | `FAILED_PRECONDITION`; no release/advance |
| Invalid scoped checkpoint | `FAILED_PRECONDITION`, or `UNAUTHENTICATED` where token-like |
| Replay retention miss | `FAILED_PRECONDITION` plus snapshot-required trailer; same G |
| Local saturation | Targeted termination as §7; optional affected-call `RESOURCE_EXHAUSTED`; same G |
| Provider history loss/shared rebase | Old-G/new-G trailer only; later old-G calls fail |
| Authorization failure | `PERMISSION_DENIED`/`UNAUTHENTICATED` and targeted termination where possible |
| Deadline / connection loss | `DEADLINE_EXCEEDED` / `UNAVAILABLE` for affected calls |

Per-instance failure does not end the connection unless the connection
itself is exhausted, violated, revoked, or closed. No cross-stream or
cross-connection order is claimed.
