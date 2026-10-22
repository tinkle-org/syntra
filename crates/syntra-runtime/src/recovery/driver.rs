//! Recovery drivers: bind [`ProfileEngine`](super::engine::ProfileEngine) to live sessions.
//!
//! The coordinator is transport-agnostic and never performs calls, never
//! persists, and never delivers. Drivers close that gap without widening
//! it: they carry the connection/principal context for every hook, enforce
//! the [`RecoveryAuthorizer`](super::profile::RecoveryAuthorizer) at
//! subscribe/replay/snapshot/confirm, persist through a
//! [`DurableStore`](super::store::DurableStore) with durable
//! position/effects atomicity, suppress duplicate re-application through a
//! bounded [`DuplicateCache`](super::cache::DuplicateCache), stage snapshots
//! through [`StagedSnapshot`](super::snapshot::StagedSnapshot), and route
//! batches to exactly one subscription handle (directed delivery). There is
//! no broadcast path: a batch for handle A is never visible to handle B.
//!
//! - [`InitiatorDriver`] (initiator side): validates batches through the
//!   same pipeline as live batches, stages snapshots, polls cumulative
//!   loss, confirms only after atomic persistence.
//! - [`HostDriver`] (host side): authorizes every hook, serves bounded
//!   replay pages from stored batches, and emits
//!   [`TargetedEnvelope`]s addressed to one subscription handle.
//!
//! Persistence failure is reported by not confirming: the store error is
//! returned to the caller and the engine is untouched, so committed
//! progress never advances on a failed write.

use std::collections::HashMap;
use std::sync::Arc;

use super::cache::DuplicateCache;
use super::engine::ProfileEngine;
use super::profile::{
    CommittedPosition, ProfileAction, ProfileCheckpoint, ProfileInput, ProviderError,
    RecoveryAuthorizer, ReplayPage,
};
use super::snapshot::{SnapshotError, StagedSnapshot};
use super::store::{DurableStore, MemoryStore, StoreError};
use crate::session::Principal;

/// Initiator-side failure: persistence failure or authorization denial.
///
/// `Store` preserves the underlying [`StoreError`] without carrying
/// checkpoint bytes; `Unauthorized` carries the denying [`ProviderError`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InitiatorError {
    /// Durable store failure; retry from the last persisted position.
    Store(StoreError),
    /// Application authorizer denied the hook.
    Unauthorized(ProviderError),
}

impl From<StoreError> for InitiatorError {
    fn from(e: StoreError) -> Self {
        Self::Store(e)
    }
}

/// Connection/principal context bound at handshake and carried on every
/// recovery hook. Checkpoint and selector bytes are never authority by
/// themselves; the bound principal is checked at each hook.
#[derive(Debug, Clone)]
pub struct ConnectionContext {
    /// Per-connection diagnostic id (never authority).
    pub connection_id: String,
    /// Bound principal authorized at every hook.
    pub principal: Principal,
    /// Negotiated version.
    pub version: u32,
}

impl ConnectionContext {
    /// Context for the bound connection/principal.
    pub fn new(connection_id: String, principal: Principal, version: u32) -> Self {
        Self {
            connection_id,
            principal,
            version,
        }
    }
}

/// Envelope addressed to exactly one subscription handle.
///
/// Directed delivery: the host routes this envelope to the connection that
/// owns `subscription_handle` and to no other. Broadcast (`NotifyAll`-style
/// fan-out) must never be used for recovery batches: it leaks stream state
/// across principals and breaks per-stream termination scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TargetedEnvelope {
    /// Subscription handle that must receive this batch.
    pub subscription_handle: Vec<u8>,
    /// Opaque batch bytes.
    pub payload: Vec<u8>,
}

/// Encode a checkpoint as a duplicate-cache key (opaque, equality only).
fn cache_key(checkpoint: &ProfileCheckpoint) -> Vec<u8> {
    let mut k = Vec::with_capacity(
        checkpoint.stream_selector.len()
            + checkpoint.base_cursor.len()
            + checkpoint.result_cursor.len()
            + 8,
    );
    k.extend_from_slice(&checkpoint.generation.to_le_bytes());
    k.push(0);
    k.extend_from_slice(&checkpoint.stream_selector);
    k.push(0);
    k.extend_from_slice(&checkpoint.base_cursor);
    k.push(0);
    k.extend_from_slice(&checkpoint.result_cursor);
    k
}

/// Initiator-side recovery driver.
///
/// Owns one [`ProfileEngine`] (all tracked streams for this connection),
/// one [`MemoryStore`] adapter, one bounded [`DuplicateCache`], and one
/// staged snapshot per stream. All methods are synchronous and
/// transport-free; the caller transmits returned envelopes.
pub struct InitiatorDriver {
    ctx: ConnectionContext,
    engine: ProfileEngine,
    store: MemoryStore,
    cache: DuplicateCache,
    staged: HashMap<Vec<u8>, StagedSnapshot>,
    authorizer: Option<Arc<dyn RecoveryAuthorizer>>,
}

impl InitiatorDriver {
    /// Driver for the bound connection/principal with an empty store and a
    /// bounded duplicate cache of `cache_capacity` entries.
    pub fn new(ctx: ConnectionContext, cache_capacity: usize) -> Self {
        Self {
            ctx,
            engine: ProfileEngine::new(),
            store: MemoryStore::new(),
            cache: DuplicateCache::new(cache_capacity),
            staged: HashMap::new(),
            authorizer: None,
        }
    }

    /// Install an application authorizer checked at confirm time.
    pub fn with_authorizer(mut self, authorizer: Arc<dyn RecoveryAuthorizer>) -> Self {
        self.authorizer = Some(authorizer);
        self
    }

    /// Bound connection/principal context.
    pub fn context(&self) -> &ConnectionContext {
        &self.ctx
    }

    /// Underlying engine (read-only hooks for tests/embeds).
    pub fn engine(&self) -> &ProfileEngine {
        &self.engine
    }

    /// Underlying store (read-only hooks for tests/embeds).
    pub fn store(&self) -> &MemoryStore {
        &self.store
    }

    /// Mutable store (failure injection for tests).
    pub fn store_mut(&mut self) -> &mut MemoryStore {
        &mut self.store
    }

    /// Track a stream from its last confirmed position, restoring durable
    /// state when the store already holds it.
    pub fn track_stream(
        &mut self,
        stream_selector: Vec<u8>,
        generation: u64,
        committed: Vec<u8>,
    ) {
        if let Some(saved) = self.store.load(&stream_selector) {
            self.engine.insert_stream(
                saved.stream_selector.clone(),
                saved.generation,
                saved.committed.clone(),
            );
        } else {
            self.engine.insert_stream(stream_selector, generation, committed);
        }
    }

    /// Observe a validated batch. Duplicates answered from the bounded
    /// cache return no actions without re-applying effects or touching the
    /// coordinator; all other inputs delegate to the engine.
    pub fn on_batch_validated(&mut self, checkpoint: ProfileCheckpoint) -> Vec<ProfileAction> {
        let key = cache_key(&checkpoint);
        if self.cache.contains(&key) {
            return vec![];
        }
        self.engine.observe(ProfileInput::BatchValidated { checkpoint })
    }

    /// Confirm durable persistence of a previously offered checkpoint.
    ///
    /// Atomically stores the position plus `effects_digest` first; on store
    /// failure returns `Err` and never touches the engine, so committed
    /// progress cannot advance on a failed write. On success delegates to
    /// the engine and records the cache key so a re-delivery across the
    /// recovered/live boundary is tolerated without re-applying effects.
    pub fn confirm(
        &mut self,
        checkpoint: &ProfileCheckpoint,
        effects_digest: &[u8],
    ) -> Result<Vec<ProfileAction>, InitiatorError> {
        if let Some(auth) = &self.authorizer {
            if let Err(e) = auth.authorize_confirm(checkpoint) {
                return Err(InitiatorError::Unauthorized(e));
            }
        }
        let position = CommittedPosition {
            stream_selector: checkpoint.stream_selector.clone(),
            generation: checkpoint.generation,
            committed: checkpoint.result_cursor.clone(),
        };
        self.store.store_atomic(position, effects_digest)?;
        let actions = self.engine.confirm_persisted(checkpoint);
        if actions.is_empty() {
            self.cache.insert(cache_key(checkpoint));
        }
        Ok(actions)
    }

    /// Poll a caller-supplied cumulative loss count for the stream.
    pub fn poll_loss(
        &mut self,
        stream_selector: &[u8],
        loss_count: u64,
    ) -> Vec<ProfileAction> {
        self.engine.poll_loss(stream_selector, loss_count)
    }

    /// Record the subscribed catch-up boundary from the subscribe response.
    pub fn set_subscribed_boundary(
        &mut self,
        stream_selector: &[u8],
        boundary: Vec<u8>,
    ) -> Vec<ProfileAction> {
        self.engine.set_subscribed_boundary(stream_selector, boundary)
    }

    /// Track a replay page boundary.
    pub fn observe_replay_page(
        &mut self,
        stream_selector: &[u8],
        page: &ReplayPage,
    ) -> Vec<ProfileAction> {
        self.engine.observe_replay_page(stream_selector, page)
    }

    /// Validate a catch-up completion boundary before releasing live batches.
    pub fn observe_completion_boundary(
        &mut self,
        stream_selector: &[u8],
        completion_boundary: &[u8],
    ) -> Vec<ProfileAction> {
        self.engine.observe_completion_boundary(stream_selector, completion_boundary)
    }

    /// Begin staging a snapshot under a provider-proven boundary.
    pub fn stage_snapshot(
        &mut self,
        stream_selector: Vec<u8>,
        snapshot_handle: Vec<u8>,
        boundary_checkpoint: Vec<u8>,
        total_pages: u32,
        page_bytes_max: u32,
    ) -> Result<(), SnapshotError> {
        let staged = StagedSnapshot::new(
            snapshot_handle,
            boundary_checkpoint,
            total_pages,
            page_bytes_max,
        )?;
        self.staged.insert(stream_selector, staged);
        Ok(())
    }

    /// Stage one snapshot page for the stream.
    pub fn stage_snapshot_page(
        &mut self,
        stream_selector: &[u8],
        page_index: u32,
        bytes: Vec<u8>,
        boundary_checkpoint: &[u8],
    ) -> Result<(), SnapshotError> {
        match self.staged.get_mut(stream_selector) {
            Some(staged) => staged.stage_page(page_index, bytes, boundary_checkpoint),
            None => Err(SnapshotError::InvalidPage),
        }
    }

    /// Install the staged snapshot and offer it to the coordinator as a
    /// new-generation checkpoint. Returns the checkpoint plus the assembled
    /// bytes. The staged entry is removed only after a successful install.
    /// Generations not greater than the engine's current generation are
    /// rejected. The caller confirms the returned checkpoint via
    /// [`Self::confirm`] to advance the generation.
    pub fn install_snapshot(
        &mut self,
        stream_selector: &[u8],
        generation: u64,
    ) -> Result<(ProfileCheckpoint, Vec<u8>), SnapshotError> {
        if let Some(cur) = self.engine.generation(stream_selector) {
            if generation <= cur {
                return Err(SnapshotError::StaleGeneration);
            }
        }
        let staged = self.staged.get(stream_selector).ok_or(SnapshotError::Incomplete)?;
        let bytes = staged.install()?;
        let boundary = staged.boundary_checkpoint().to_vec();
        self.staged.remove(stream_selector);
        Ok((
            ProfileCheckpoint {
                stream_selector: stream_selector.to_vec(),
                generation,
                base_cursor: boundary.clone(),
                result_cursor: boundary,
            },
            bytes,
        ))
    }
}

/// Host-side recovery driver.
///
/// Authorizes every hook with the bound principal, serves bounded replay
/// pages from stored batches, and emits [`TargetedEnvelope`]s addressed to
/// exactly one subscription handle. No broadcast path exists.
pub struct HostDriver {
    ctx: ConnectionContext,
    authorizer: Option<Arc<dyn RecoveryAuthorizer>>,
    /// Batches per stream selector (opaque bytes keyed by result cursor).
    batches: HashMap<Vec<u8>, Vec<StoredBatch>>,
    /// Subscription handle -> stream selector routing table.
    routes: HashMap<Vec<u8>, Vec<u8>>,
    next_handle: u64,
    max_batches_per_page: u32,
    max_bytes_per_page: u32,
}

/// One stored batch: predecessor/result cursors plus opaque payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoredBatch {
    /// Checkpoint this batch continues from.
    pub predecessor: Vec<u8>,
    /// Checkpoint this batch advances to.
    pub result: Vec<u8>,
    /// Opaque batch bytes.
    pub payload: Vec<u8>,
}

impl HostDriver {
    /// Driver for the bound connection/principal.
    pub fn new(ctx: ConnectionContext) -> Self {
        Self {
            ctx,
            authorizer: None,
            batches: HashMap::new(),
            routes: HashMap::new(),
            next_handle: 1,
            max_batches_per_page: 64,
            max_bytes_per_page: 262_144,
        }
    }

    /// Install an application authorizer checked at every hook.
    pub fn with_authorizer(mut self, authorizer: Arc<dyn RecoveryAuthorizer>) -> Self {
        self.authorizer = Some(authorizer);
        self
    }

    /// Bound connection/principal context.
    pub fn context(&self) -> &ConnectionContext {
        &self.ctx
    }

    /// Append a stored batch for the stream (host application supply).
    pub fn append_batch(&mut self, stream_selector: Vec<u8>, batch: StoredBatch) {
        self.batches.entry(stream_selector).or_default().push(batch);
    }

    /// Subscribe a stream selector. Authorizes with the bound principal,
    /// assigns a fresh connection-scoped handle, and records the routing
    /// entry. Returns the handle plus the fixed catch-up boundary (latest
    /// result, or the start checkpoint when empty).
    pub fn subscribe(
        &mut self,
        stream_selector: Vec<u8>,
        start_checkpoint: Vec<u8>,
    ) -> Result<(Vec<u8>, Vec<u8>), ProviderError> {
        if let Some(auth) = &self.authorizer {
            auth.authorize_subscribe(&stream_selector)?;
        }
        let boundary = self
            .batches
            .get(&stream_selector)
            .and_then(|v| v.last().map(|b| b.result.clone()))
            .unwrap_or_else(|| start_checkpoint.clone());
        if boundary.is_empty() {
            return Err(ProviderError::StaleCheckpoint);
        }
        let handle = format!("sub-{}-{}", self.ctx.connection_id, self.next_handle).into_bytes();
        self.next_handle += 1;
        self.routes.insert(handle.clone(), stream_selector);
        Ok((handle, boundary))
    }

    /// Serve one bounded replay page continuing from `from_checkpoint`.
    /// The caller transmits the page inside the terminal `RpcResult`.
    pub fn replay_page(
        &self,
        subscription_handle: &[u8],
        from_checkpoint: &[u8],
        max_batches: u32,
        max_bytes: u32,
    ) -> Result<ReplayPage, ProviderError> {
        let selector = self.routes.get(subscription_handle).ok_or(ProviderError::UnknownStream)?;
        let probe = ProfileCheckpoint {
            stream_selector: selector.clone(),
            generation: 0,
            base_cursor: from_checkpoint.to_vec(),
            result_cursor: from_checkpoint.to_vec(),
        };
        if let Some(auth) = &self.authorizer {
            auth.authorize_replay(&probe)?;
        }
        let batches = self.batches.get(selector).ok_or(ProviderError::OutsideRetention)?;
        let start = batches
            .iter()
            .position(|b| b.predecessor == from_checkpoint)
            .ok_or(ProviderError::StaleCheckpoint)?;
        let max_batches = max_batches.clamp(1, self.max_batches_per_page).min(64);
        let max_bytes = max_bytes.clamp(1, self.max_bytes_per_page).min(262_144);
        let mut payloads = Vec::new();
        let mut bytes = 0u32;
        let mut end = start;
        let mut last_result = from_checkpoint.to_vec();
        for b in batches.iter().skip(start).take(max_batches as usize) {
            if payloads.len() as u32 >= max_batches {
                break;
            }
            let len = b.payload.len() as u32;
            if bytes.saturating_add(len) > max_bytes {
                if payloads.is_empty() {
                    return Err(ProviderError::Overloaded);
                }
                break;
            }
            bytes = bytes.saturating_add(len);
            last_result = b.result.clone();
            payloads.push(b.payload.clone());
            end += 1;
        }
        if payloads.is_empty() {
            return Err(ProviderError::OutsideRetention);
        }
        let boundary = batches.last().map(|b| b.result.clone()).unwrap_or_default();
        let more = end < batches.len();
        Ok(ReplayPage {
            predecessor_checkpoint: from_checkpoint.to_vec(),
            result_checkpoint: last_result,
            continuation_marker: if more {
                format!("marker-{end}").into_bytes()
            } else {
                Vec::new()
            },
            catchup_boundary: boundary,
            batch_payloads: payloads,
        })
    }

    /// Route a batch to exactly one subscription handle. Returns the
    /// addressed envelope; no other handle observes it.
    pub fn directed_delivery(
        &self,
        subscription_handle: &[u8],
        payload: Vec<u8>,
    ) -> Result<TargetedEnvelope, ProviderError> {
        if !self.routes.contains_key(subscription_handle) {
            return Err(ProviderError::UnknownStream);
        }
        Ok(TargetedEnvelope {
            subscription_handle: subscription_handle.to_vec(),
            payload,
        })
    }

    /// Terminate exactly one subscription. Connection state is untouched;
    /// other handles keep their routing entries.
    pub fn unsubscribe(&mut self, subscription_handle: &[u8]) -> Result<(), ProviderError> {
        self.routes.remove(subscription_handle).map(|_| ()).ok_or(ProviderError::UnknownStream)
    }

    /// Handles currently routed.
    pub fn routed_handles(&self) -> Vec<Vec<u8>> {
        self.routes.keys().cloned().collect()
    }
}
