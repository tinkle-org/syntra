//! Integration tests for recovery drivers, loss unification, and bounded
//! checkpoint reconciliation.
//!
//! Covers the task-2/3/4 acceptance set over neutral fixtures (no messenger
//! semantics):
//! - persistence failure leaves committed progress unchanged and retries
//!   from the last persisted position;
//! - a lost confirm is discovered by independently scheduled reconciliation
//!   without requiring another update (idle peers converge);
//! - snapshot failure (incomplete install) never advances generation;
//! - directed delivery isolates subscription handles (no broadcast);
//! - final-batch loss with idle peers surfaces as recovery via cumulative
//!   loss polling plus reconciliation.

use std::sync::Arc;
use std::time::{Duration, Instant};

use syntra_runtime::recovery::{
    CheckpointReconciler, ConnectionContext, HostDriver, InitiatorDriver, ProfileAction,
    ProfileCheckpoint, ProfileEngine, ProfileInput, ProviderError, RecoveryAuthorizer,
    ReconcilerConfig, StagedSnapshot, StoredBatch,
};
use syntra_runtime::session::Principal;

fn ctx(id: &str) -> ConnectionContext {
    ConnectionContext::new(id.to_string(), Principal::new("svc-test"), 1)
}

fn cp(sel: &[u8], gen: u64, base: &[u8], result: &[u8]) -> ProfileCheckpoint {
    ProfileCheckpoint {
        stream_selector: sel.to_vec(),
        generation: gen,
        base_cursor: base.to_vec(),
        result_cursor: result.to_vec(),
    }
}

struct AllowAll;
impl RecoveryAuthorizer for AllowAll {
    fn authorize_subscribe(&self, _s: &[u8]) -> Result<(), ProviderError> {
        Ok(())
    }
    fn authorize_replay(&self, _c: &ProfileCheckpoint) -> Result<(), ProviderError> {
        Ok(())
    }
    fn authorize_snapshot(
        &self,
        _c: &syntra_runtime::recovery::CommittedPosition,
    ) -> Result<(), ProviderError> {
        Ok(())
    }
    fn authorize_confirm(&self, _c: &ProfileCheckpoint) -> Result<(), ProviderError> {
        Ok(())
    }
}

#[test]
fn persistence_failure_retries_from_last_committed() {
    let mut d = InitiatorDriver::new(ctx("c1"), 16);
    d.track_stream(b"s".to_vec(), 7, b"c-40".to_vec()).unwrap();
    let batch = cp(b"s", 7, b"c-40", b"c-43");
    let offered = d.on_batch_validated(batch.clone());
    assert!(matches!(offered[0], ProfileAction::CommitCheckpoint { .. }));
    d.store_mut().fail_next_write();
    assert!(d.confirm(&batch, b"fx-1").is_err());
    assert_eq!(d.engine().committed(b"s"), Some(b"c-40".as_slice()));
    let retry = d.on_batch_validated(batch.clone());
    assert!(matches!(retry[0], ProfileAction::CommitCheckpoint { .. }));
    assert!(d.confirm(&batch, b"fx-1").unwrap().is_empty());
    assert_eq!(d.engine().committed(b"s"), Some(b"c-43".as_slice()));
}

#[test]
fn lost_confirm_discovered_by_reconciliation_without_new_update() {
    let mut d = InitiatorDriver::new(ctx("c1"), 16);
    d.track_stream(b"s".to_vec(), 7, b"c-40".to_vec()).unwrap();
    let batch = cp(b"s", 7, b"c-40", b"c-43");
    let offered = d.on_batch_validated(batch.clone());
    assert!(matches!(offered[0], ProfileAction::CommitCheckpoint { .. }));
    let mut rec = CheckpointReconciler::new(ReconcilerConfig {
        tick_interval: Duration::from_secs(0),
        max_streams_per_tick: 8,
    });
    rec.note_observed(batch.clone());
    let found = rec.tick(Instant::now(), d.engine(), d.store());
    assert_eq!(found.len(), 1);
    assert!(matches!(found[0], ProfileAction::RecoveryNeeded { .. }));
    assert!(d.confirm(&batch, b"fx-1").unwrap().is_empty());
    let quiet = rec.tick(Instant::now(), d.engine(), d.store());
    assert!(quiet.is_empty());
}

#[test]
fn snapshot_failure_never_advances_generation() {
    let mut d = InitiatorDriver::new(ctx("c1"), 16);
    d.track_stream(b"s".to_vec(), 7, b"c-40".to_vec()).unwrap();
    d.stage_snapshot(
        b"s".to_vec(),
        b"h1".to_vec(),
        b"b-100".to_vec(),
        2,
        1024,
    )
    .unwrap();
    d.stage_snapshot_page(b"s", b"h1", 0, b"half".to_vec(), b"b-100").unwrap();
    assert!(d.install_snapshot(b"s", 8).is_err());
    assert_eq!(d.engine().generation(b"s"), Some(7));
    assert_eq!(d.engine().committed(b"s"), Some(b"c-40".as_slice()));
    d.stage_snapshot_page(b"s", b"h1", 1, b"rest".to_vec(), b"b-100").unwrap();
    let (snap_cp, snap_bytes) = d.install_snapshot(b"s", 8).unwrap();
    assert_eq!(snap_cp.result_cursor, b"b-100");
    assert_eq!(snap_bytes, b"halfrest");
    assert!(d.install_snapshot(b"s", 9).is_err(), "staged entry removed after success");
    assert!(d.install_snapshot(b"s", 7).is_err(), "stale generation rejected");
    let mut engine = ProfileEngine::new();
    engine.insert_stream(b"s".to_vec(), 7, b"c-40".to_vec());
    let offered = engine.observe(ProfileInput::SnapshotInstalled {
        checkpoint: snap_cp.clone(),
    });
    assert!(matches!(offered[0], ProfileAction::CommitCheckpoint { .. }));
    let incomplete = StagedSnapshot::new(b"h".to_vec(), b"b".to_vec(), 2, 64).unwrap();
    assert!(!incomplete.is_complete());
    assert!(incomplete.install().is_err());
}

#[test]
fn directed_delivery_isolates_subscription_handles() {
    let mut h = HostDriver::new(ctx("c1")).with_authorizer(Arc::new(AllowAll));
    h.append_batch(b"stream-a".to_vec(), StoredBatch {
        predecessor: b"c-40".to_vec(),
        result: b"c-43".to_vec(),
        payload: b"batch-a".to_vec(),
        generation: 7,
    });
    h.append_batch(b"stream-b".to_vec(), StoredBatch {
        predecessor: b"d-40".to_vec(),
        result: b"d-43".to_vec(),
        payload: b"batch-b".to_vec(),
        generation: 7,
    });
    let (ha, _) = h.subscribe(b"stream-a".to_vec(), b"c-40".to_vec(), 7).unwrap();
    let (hb, _) = h.subscribe(b"stream-b".to_vec(), b"d-40".to_vec(), 7).unwrap();
    assert_ne!(ha, hb);
    let env_a = h.directed_delivery(&ha, b"batch-a".to_vec()).unwrap();
    assert_eq!(env_a.subscription_handle, ha);
    assert_ne!(env_a.subscription_handle, hb);
    let env_b = h.directed_delivery(&hb, b"batch-b".to_vec()).unwrap();
    assert_eq!(env_b.subscription_handle, hb);
    assert_ne!(env_a.payload, env_b.payload);
    assert!(h.directed_delivery(b"nope", b"x".to_vec()).is_err());
    h.unsubscribe(&ha).unwrap();
    assert!(h.directed_delivery(&ha, b"late".to_vec()).is_err());
    assert!(h.directed_delivery(&hb, b"still".to_vec()).is_ok());
}

#[test]
fn final_batch_loss_with_idle_peers_recovers_via_loss_and_reconcile() {
    let mut d = InitiatorDriver::new(ctx("c1"), 16);
    d.track_stream(b"s".to_vec(), 7, b"c-40".to_vec()).unwrap();
    assert!(d.poll_loss(b"s", 0).is_empty());
    let gap = d.poll_loss(b"s", 1);
    assert!(matches!(gap[0], ProfileAction::RecoveryNeeded { .. }));
    assert_eq!(d.engine().last_loss(b"s"), Some(1));
    assert!(d.poll_loss(b"s", 1).is_empty());
    let mut rec = CheckpointReconciler::new(ReconcilerConfig {
        tick_interval: Duration::from_secs(0),
        max_streams_per_tick: 8,
    });
    rec.note_observed(cp(b"s", 7, b"c-40", b"c-43"));
    let found = rec.tick(Instant::now(), d.engine(), d.store());
    assert_eq!(found.len(), 1);
    let batch = cp(b"s", 7, b"c-40", b"c-43");
    let offered = d.on_batch_validated(batch.clone());
    assert!(matches!(offered[0], ProfileAction::CommitCheckpoint { .. }));
    assert!(d.confirm(&batch, b"fx-1").unwrap().is_empty());
    assert!(
        d.on_batch_validated(batch.clone()).is_empty(),
        "confirmed duplicate must not re-offer"
    );
    let older = cp(b"s", 7, b"c-40", b"c-41");
    let older_actions = d.on_batch_validated(older);
    assert!(
        !older_actions
            .iter()
            .any(|a| matches!(a, ProfileAction::CommitCheckpoint { .. })),
        "older duplicate must not re-offer commit"
    );
}
