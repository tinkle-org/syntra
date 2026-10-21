//! Generic synchronization and recovery boundary.
//!
//! The core transports opaque `Notification` bytes and reports observable
//! transport events. It does not interpret stream identity, checkpoint
//! syntax, replay methods, or snapshot formats.
//!
//! This module defines application-supplied checkpoint metadata and the
//! local actions a generic coordinator may emit. The application selects
//! recovery RPCs, constructs payloads, performs requests, persists
//! checkpoints, and installs snapshots.

/// Position within one independently ordered stream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StreamCheckpoint {
    /// Application-defined stream label, opaque to the core.
    pub stream: String,
    /// Continuity epoch. Changes when an old checkpoint cannot continue.
    pub generation: u64,
    /// State required before applying the next batch.
    pub base: u64,
    /// State reached after applying the complete batch.
    pub checkpoint: u64,
}

/// Input observed by the recovery coordinator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RecoveryInput {
    /// A complete batch validated by the application, ready to commit.
    BatchValidated { checkpoint: StreamCheckpoint },
    /// A batch arrived without continuity from the committed position.
    GapDetected { stream: String, expected_base: u64, observed_base: u64 },
    /// Transport loss or explicit continuity loss for the stream.
    ContinuityLost { stream: String, committed: u64 },
    /// The application reports that continuation is expired or unavailable.
    ContinuationExpired { stream: String, committed: u64 },
    /// The application installed a snapshot at the given checkpoint.
    SnapshotInstalled { checkpoint: StreamCheckpoint },
}

/// Local action emitted by the coordinator. Never an RPC invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RecoveryAction {
    /// Apply the batch, then commit its checkpoint after effects persist.
    CommitCheckpoint { checkpoint: StreamCheckpoint },
    /// Recover from the committed checkpoint using an application RPC.
    RecoveryNeeded { stream: String, committed: u64 },
    /// Obtain an authoritative snapshot before resuming the stream.
    SnapshotRequired { stream: String, committed: u64 },
    /// Reset the stream to a new generation after an explicit decision.
    ContinuityLost { stream: String, new_generation: u64 },
}

/// Minimal coordinator over one stream's committed progress.
///
/// The coordinator tracks the committed checkpoint only. The application
/// applies effects, persists checkpoints, and reports inputs.
#[derive(Debug, Clone)]
pub struct StreamRecovery {
    stream: String,
    generation: u64,
    committed: u64,
}

impl StreamRecovery {
    pub fn new(stream: impl Into<String>, generation: u64, committed: u64) -> Self {
        Self { stream: stream.into(), generation, committed }
    }

    pub fn committed(&self) -> u64 {
        self.committed
    }

    pub fn generation(&self) -> u64 {
        self.generation
    }

    /// Observes coordinator inputs. A validated batch returns a
    /// `CommitCheckpoint` action without advancing `committed`; the caller
    /// advances via [`Self::confirm_persisted`] only after the checkpoint
    /// and its effects are durably persisted.
    pub fn observe(&mut self, input: RecoveryInput) -> Vec<RecoveryAction> {
        match input {
            RecoveryInput::BatchValidated { checkpoint } => {
                if checkpoint.stream != self.stream
                    || checkpoint.generation != self.generation
                    || checkpoint.base != self.committed
                    || checkpoint.checkpoint < checkpoint.base
                {
                    return vec![RecoveryAction::RecoveryNeeded {
                        stream: self.stream.clone(),
                        committed: self.committed,
                    }];
                }
                vec![RecoveryAction::CommitCheckpoint { checkpoint }]
            },
            RecoveryInput::GapDetected { stream, expected_base: _, observed_base: _ } => {
                if stream != self.stream {
                    return vec![];
                }
                vec![RecoveryAction::RecoveryNeeded {
                    stream: self.stream.clone(),
                    committed: self.committed,
                }]
            },
            RecoveryInput::ContinuityLost { stream, committed: _ } => {
                if stream != self.stream {
                    return vec![];
                }
                vec![RecoveryAction::RecoveryNeeded {
                    stream: self.stream.clone(),
                    committed: self.committed,
                }]
            },
            RecoveryInput::ContinuationExpired { stream, committed } => {
                if stream != self.stream {
                    return vec![];
                }
                if committed < self.committed {
                    return vec![];
                }
                vec![RecoveryAction::SnapshotRequired {
                    stream: self.stream.clone(),
                    committed: self.committed,
                }]
            },
            RecoveryInput::SnapshotInstalled { checkpoint } => {
                if checkpoint.stream != self.stream
                    || checkpoint.checkpoint < checkpoint.base
                {
                    return vec![];
                }
                vec![RecoveryAction::CommitCheckpoint { checkpoint }]
            },
        }
    }

    /// Confirms the application durably persisted `checkpoint` and its
    /// effects. Advances persisted progress on success; on mismatch the
    /// checkpoint is not adopted and a `RecoveryNeeded` action retries from
    /// the last persisted position. Call only with the checkpoint previously
    /// returned as a `CommitCheckpoint` action; a persistence failure is
    /// reported by simply not calling this method.
    ///
    /// Snapshot actions (a generation change) follow their own continuity
    /// rules: only the stream and the checkpoint's internal consistency are
    /// validated, so a snapshot whose base differs from the pre-snapshot
    /// committed position is accepted. Same-generation checkpoints must
    /// continue exactly from `committed`. Generations move forward only: a
    /// confirmation from an older generation never rolls back newer
    /// progress and instead reports the current position for recovery.
    pub fn confirm_persisted(&mut self, checkpoint: &StreamCheckpoint) -> Vec<RecoveryAction> {
        if checkpoint.stream != self.stream || checkpoint.checkpoint < checkpoint.base {
            return vec![RecoveryAction::RecoveryNeeded {
                stream: self.stream.clone(),
                committed: self.committed,
            }];
        }
        if checkpoint.generation < self.generation {
            return vec![RecoveryAction::RecoveryNeeded {
                stream: self.stream.clone(),
                committed: self.committed,
            }];
        }
        if checkpoint.generation != self.generation {
            self.generation = checkpoint.generation;
            self.committed = checkpoint.checkpoint;
            return vec![];
        }
        if checkpoint.base != self.committed {
            return vec![RecoveryAction::RecoveryNeeded {
                stream: self.stream.clone(),
                committed: self.committed,
            }];
        }
        self.committed = checkpoint.checkpoint;
        vec![]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn checkpoint(base: u64, at: u64) -> StreamCheckpoint {
        StreamCheckpoint { stream: "s".to_string(), generation: 1, base, checkpoint: at }
    }

    #[test]
    fn contiguous_batch_commits_after_persistence() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let cp = checkpoint(40, 43);
        let actions = r.observe(RecoveryInput::BatchValidated { checkpoint: cp.clone() });
        assert_eq!(r.committed(), 40);
        assert!(matches!(actions[0], RecoveryAction::CommitCheckpoint { .. }));
        let confirmed = r.confirm_persisted(&cp);
        assert!(confirmed.is_empty());
        assert_eq!(r.committed(), 43);
    }

    #[test]
    fn persistence_failure_retries_from_last_committed() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let cp = checkpoint(40, 43);
        let actions = r.observe(RecoveryInput::BatchValidated { checkpoint: cp });
        assert!(matches!(actions[0], RecoveryAction::CommitCheckpoint { .. }));
        // Persistence failed: confirm_persisted is never called.
        assert_eq!(r.committed(), 40);
        let retry = r.observe(RecoveryInput::GapDetected {
            stream: "s".to_string(), expected_base: 40, observed_base: 45,
        });
        assert_eq!(r.committed(), 40);
        assert!(matches!(
            retry[0],
            RecoveryAction::RecoveryNeeded { committed: 40, .. }
        ));
    }

    #[test]
    fn gap_requires_recovery_without_advancing() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let actions = r.observe(RecoveryInput::GapDetected {
            stream: "s".to_string(), expected_base: 40, observed_base: 45,
        });
        assert_eq!(r.committed(), 40);
        assert!(matches!(actions[0], RecoveryAction::RecoveryNeeded { .. }));
    }

    #[test]
    fn expired_continuation_requires_snapshot() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let actions = r.observe(RecoveryInput::ContinuationExpired {
            stream: "s".to_string(), committed: 40,
        });
        assert!(matches!(actions[0], RecoveryAction::SnapshotRequired { .. }));
    }

    #[test]
    fn stale_expiry_reports_no_actions() {
        let mut r = StreamRecovery::new("s", 1, 43);
        let actions = r.observe(RecoveryInput::ContinuationExpired {
            stream: "s".to_string(), committed: 40,
        });
        assert!(actions.is_empty());
        assert_eq!(r.committed(), 43);
    }

    #[test]
    fn snapshot_advances_only_after_persistence() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let snap = StreamCheckpoint { stream: "s".to_string(), generation: 2, base: 0, checkpoint: 100 };
        let actions = r.observe(RecoveryInput::SnapshotInstalled { checkpoint: snap.clone() });
        assert!(matches!(actions[0], RecoveryAction::CommitCheckpoint { .. }));
        assert_eq!(r.committed(), 40);
        assert_eq!(r.generation(), 1);
        let confirmed = r.confirm_persisted(&snap);
        assert!(confirmed.is_empty());
        assert_eq!(r.generation(), 2);
        assert_eq!(r.committed(), 100);
    }

    #[test]
    fn stale_generation_confirm_cannot_roll_back() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let batch = checkpoint(40, 43);
        let snap = StreamCheckpoint { stream: "s".to_string(), generation: 2, base: 0, checkpoint: 100 };
        let _ = r.observe(RecoveryInput::BatchValidated { checkpoint: batch.clone() });
        let _ = r.observe(RecoveryInput::SnapshotInstalled { checkpoint: snap.clone() });
        // Newer snapshot persists first.
        assert!(r.confirm_persisted(&snap).is_empty());
        assert_eq!(r.generation(), 2);
        assert_eq!(r.committed(), 100);
        // Stale older-generation batch must not roll the coordinator back.
        let retry = r.confirm_persisted(&batch);
        assert!(matches!(
            retry[0],
            RecoveryAction::RecoveryNeeded { committed: 100, .. }
        ));
        assert_eq!(r.generation(), 2);
        assert_eq!(r.committed(), 100);
    }

    #[test]
    fn snapshot_failure_retains_previous_position() {
        let mut r = StreamRecovery::new("s", 1, 40);
        let snap = StreamCheckpoint { stream: "s".to_string(), generation: 2, base: 0, checkpoint: 100 };
        let actions = r.observe(RecoveryInput::SnapshotInstalled { checkpoint: snap });
        assert!(matches!(actions[0], RecoveryAction::CommitCheckpoint { .. }));
        // Persistence failed: confirm_persisted is never called.
        assert_eq!(r.committed(), 40);
        assert_eq!(r.generation(), 1);
    }
}
