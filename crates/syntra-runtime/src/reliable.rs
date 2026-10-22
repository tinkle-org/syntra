//! Reliable-session runtime managers: bounded, sync, transport-agnostic.

use std::collections::{HashMap, VecDeque};
use syntra_core::error::{ErrorCode, SyntraError};
use syntra_core::reliable::{
    check_duplicate_content, check_epoch_advance, next_epoch, validate_delivery_id,
    validate_epoch, validate_resume_credential, validate_session_id,
    ConfirmedLease, ControlBounds, DeliveryId, LeaseProposal, ReconcileOutcome, SessionId,
    SessionSignal, negotiate_lease,
};
use crate::connection::fill_random;

fn resource(msg: &str) -> SyntraError { SyntraError::ResourceExhausted(msg.to_string()) }
fn unauthenticated(msg: &str) -> SyntraError {
    SyntraError::Handshake { code: ErrorCode::Unauthenticated, message: msg.to_string() }
}
fn failed_precondition(msg: &str) -> SyntraError {
    SyntraError::Protocol { code: ErrorCode::FailedPrecondition, message: msg.to_string() }
}
fn internal(msg: &str) -> SyntraError {
    SyntraError::Protocol { code: ErrorCode::Internal, message: msg.to_string() }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StoredOutcome { Payload(Vec<u8>), Error { code: ErrorCode, message: String } }
impl StoredOutcome {
    fn byte_len(&self) -> usize {
        match self { Self::Payload(b) => b.len(), Self::Error { message, .. } => message.len() }
    }
}
#[derive(Debug, Clone)]
struct RetainedEntry { method: String, payload: Vec<u8>, outcome: StoredOutcome, retained_at_ms: u64 }
#[derive(Debug, Default)]
struct OutcomeStore { entries: HashMap<DeliveryId, RetainedEntry>, bytes: usize, forgotten: HashMap<DeliveryId, u64>, pending: HashMap<DeliveryId, u64> }
impl OutcomeStore {
    fn insert(&mut self, bounds: &ControlBounds, now_ms: u64, did: DeliveryId, method: String, payload: Vec<u8>, outcome: StoredOutcome) -> Result<ReconcileOutcome, SyntraError> {
        if let Some(existing) = self.entries.get(&did) {
            if now_ms.saturating_sub(existing.retained_at_ms) > bounds.result_retention_ms {
                let old = self.entries.remove(&did).expect("checked above");
                let f = old.method.len() + old.payload.len() + old.outcome.byte_len();
                self.bytes = self.bytes.saturating_sub(f);
            } else {
                check_duplicate_content(&existing.method, &existing.payload, &method, &payload)?;
                return Ok(ReconcileOutcome::Retained);
            }
        }
        if let Some(&forgot_at) = self.forgotten.get(&did) {
            if now_ms.saturating_sub(forgot_at) > bounds.result_retention_ms {
                self.forgotten.remove(&did);
            } else {
                self.forgotten.remove(&did);
            }
        }
        let n = method.len() + payload.len() + outcome.byte_len();
        if self.entries.len() >= bounds.max_retained_results { return Err(resource("retained result budget exhausted")); }
        if self.bytes.saturating_add(n) > bounds.max_retained_bytes { return Err(resource("retained result bytes exhausted")); }
        self.bytes = self.bytes.saturating_add(n);
        self.entries.insert(did, RetainedEntry { method, payload, outcome, retained_at_ms: now_ms });
        self.pending.remove(&did);
        Ok(ReconcileOutcome::Retained)
    }
    fn note_dispatch(&mut self, bounds: &ControlBounds, now_ms: u64, did: DeliveryId) -> Result<(), SyntraError> {
        if self.entries.contains_key(&did) || self.forgotten.contains_key(&did) {
            return Ok(());
        }
        if self.pending.contains_key(&did) {
            return Ok(());
        }
        if self.pending.len() >= bounds.max_retained_results {
            return Err(resource("pending dispatch budget exhausted"));
        }
        self.pending.insert(did, now_ms);
        Ok(())
    }
    fn get(&self, now_ms: u64, retention_ms: u64, did: &DeliveryId) -> ReconcileOutcome {
        match self.entries.get(did) {
            Some(e) if now_ms.saturating_sub(e.retained_at_ms) > retention_ms => ReconcileOutcome::Forgotten,
            Some(_) => ReconcileOutcome::Retained,
            None => match self.forgotten.get(did) {
                Some(&forgot_at) if now_ms.saturating_sub(forgot_at) > retention_ms => ReconcileOutcome::Unknown,
                Some(_) => ReconcileOutcome::Forgotten,
                None => match self.pending.get(did) {
                    Some(&dispatched_at) if now_ms.saturating_sub(dispatched_at) > retention_ms => ReconcileOutcome::Forgotten,
                    Some(_) => ReconcileOutcome::Pending,
                    None => ReconcileOutcome::Unknown,
                },
            },
        }
    }
    fn outcome_of(&self, did: &DeliveryId) -> Option<StoredOutcome> {
        self.entries.get(did).map(|e| e.outcome.clone())
    }
    fn forget(&mut self, bounds: &ControlBounds, now_ms: u64, did: &DeliveryId) -> bool {
        self.pending.remove(did);
        if let Some(e) = self.entries.remove(did) {
            let f = e.method.len() + e.payload.len() + e.outcome.byte_len();
            self.bytes = self.bytes.saturating_sub(f);
            if !self.forgotten.contains_key(did) && self.forgotten.len() >= bounds.max_retained_results {
                if let Some(oldest) = self.forgotten.iter().min_by_key(|(_, &t)| t).map(|(k, _)| *k) {
                    self.forgotten.remove(&oldest);
                }
            }
            self.forgotten.insert(*did, now_ms);
            true
        } else if !self.forgotten.contains_key(did) {
            if self.forgotten.len() >= bounds.max_retained_results {
                if let Some(oldest) = self.forgotten.iter().min_by_key(|(_, &t)| t).map(|(k, _)| *k) {
                    self.forgotten.remove(&oldest);
                }
            }
            self.forgotten.insert(*did, now_ms);
            true
        } else { false }
    }
    fn reap_expired(&mut self, bounds: &ControlBounds, now_ms: u64, retention_ms: u64) -> usize {
        let expired: Vec<DeliveryId> = self.entries.iter()
            .filter(|(_, e)| now_ms.saturating_sub(e.retained_at_ms) > retention_ms)
            .map(|(k, _)| *k).collect();
        let n = expired.len();
        for k in expired { self.forget(bounds, now_ms, &k); }
        let expired_pending: Vec<DeliveryId> = self.pending.iter()
            .filter(|(_, &t)| now_ms.saturating_sub(t) > retention_ms)
            .map(|(k, _)| *k).collect();
        for k in expired_pending {
            self.pending.remove(&k);
            if !self.forgotten.contains_key(&k) {
                if self.forgotten.len() >= bounds.max_retained_results {
                    if let Some(oldest) = self.forgotten.iter().min_by_key(|(_, &t)| t).map(|(kk, _)| *kk) {
                        self.forgotten.remove(&oldest);
                    }
                }
                self.forgotten.insert(k, now_ms);
            }
        }
        let expired_forgotten: Vec<DeliveryId> = self.forgotten.iter()
            .filter(|(_, &t)| now_ms.saturating_sub(t) > retention_ms)
            .map(|(k, _)| *k).collect();
        for k in expired_forgotten { self.forgotten.remove(&k); }
        n
    }
}
#[derive(Debug, Clone)]
struct TombstoneEntry { code: ErrorCode, retained_at_ms: u64 }
#[derive(Debug, Default)]
struct TombstoneStore { entries: HashMap<DeliveryId, TombstoneEntry> }
impl TombstoneStore {
    fn record(&mut self, bounds: &ControlBounds, now_ms: u64, did: DeliveryId, code: ErrorCode) -> Result<(), SyntraError> {
        // Spec (reliability): tombstones exist only for terminal
        // DEADLINE_EXCEEDED and CANCELLED. UNAVAILABLE means unknown
        // outcome and must stay reconcilable-as-Unknown, never tombstoned.
        if !matches!(code, ErrorCode::DeadlineExceeded | ErrorCode::Cancelled) {
            return Err(SyntraError::Protocol { code: ErrorCode::InvalidArgument, message: "tombstones only for deadline/cancel".to_string() });
        }
        // First-write-wins: racing deadline/cancel reports are deterministic.
        if let Some(existing) = self.entries.get(&did) {
            if existing.code != code {
                return Err(failed_precondition("tombstone already recorded with different terminal code"));
            }
            return Ok(());
        }
        if self.entries.len() >= bounds.max_tombstones {
            return Err(resource("tombstone budget exhausted"));
        }
        self.entries.insert(did, TombstoneEntry { code, retained_at_ms: now_ms });
        Ok(())
    }
    fn get(&self, now_ms: u64, retention_ms: u64, did: &DeliveryId) -> Option<ErrorCode> {
        self.entries.get(did).and_then(|e| {
            if now_ms.saturating_sub(e.retained_at_ms) > retention_ms { None } else { Some(e.code) }
        })
    }
    fn reap_expired(&mut self, now_ms: u64, retention_ms: u64) -> usize {
        let expired: Vec<DeliveryId> = self.entries.iter()
            .filter(|(_, e)| now_ms.saturating_sub(e.retained_at_ms) > retention_ms)
            .map(|(k, _)| *k).collect();
        let n = expired.len();
        for k in expired { self.entries.remove(&k); }
        n
    }
}
#[derive(Debug, Clone)]
struct ResumeEntry { session_id: SessionId, principal: String, version: u32, issued_at_ms: u64, expires_at_ms: u64 }
#[derive(Debug)]
struct SessionState {
    principal: String, version: u32, epoch: u64,
    last_activity_ms: u64, lease: ConfirmedLease,
    active_connection: Option<String>,
    outcomes: OutcomeStore, tombstones: TombstoneStore,
}
#[derive(Debug, Default)]
struct ControlQueue { queue: VecDeque<(SessionId, SessionSignal)>, bytes: usize }
impl ControlQueue {
    fn push(&mut self, bounds: &ControlBounds, id: SessionId, sig: SessionSignal) -> Result<(), SyntraError> {
        if self.queue.len() >= bounds.max_control_queue { return Err(resource("control queue full; back off")); }
        if self.bytes.saturating_add(32) > bounds.max_control_bytes { return Err(resource("control queue bytes exhausted")); }
        self.queue.push_back((id, sig));
        self.bytes = self.bytes.saturating_add(32);
        Ok(())
    }
    fn drain(&mut self, limit: usize) -> Vec<(SessionId, SessionSignal)> {
        let n = limit.min(self.queue.len());
        let mut out = Vec::with_capacity(n);
        for _ in 0..n {
            if let Some((id, sig)) = self.queue.pop_front() {
                self.bytes = self.bytes.saturating_sub(32);
                out.push((id, sig));
            }
        }
        out
    }
    fn len(&self) -> usize { self.queue.len() }
}
#[derive(Debug, Default)]
struct ManagerInner {
    sessions: HashMap<SessionId, SessionState>,
    resume_index: HashMap<Vec<u8>, ResumeEntry>,
    revoked: HashMap<Vec<u8>, u64>,
    signals: ControlQueue,
    draining: bool,
}
#[derive(Debug)]
pub struct ReliableSessionManager { inner: std::sync::Mutex<ManagerInner>, bounds: ControlBounds }
impl ReliableSessionManager {
    pub fn new(bounds: ControlBounds) -> Result<Self, SyntraError> {
        bounds.validate()?;
        Ok(Self { inner: std::sync::Mutex::new(ManagerInner::default()), bounds })
    }
    pub fn bounds(&self) -> ControlBounds { self.bounds }
    fn lock(&self) -> Result<std::sync::MutexGuard<'_, ManagerInner>, SyntraError> {
        self.inner.lock().map_err(|_| internal("manager lock poisoned"))
    }
    pub fn create_session(&self, now_ms: u64, principal: String, version: u32, proposal: LeaseProposal) -> Result<(SessionId, u64, Vec<u8>, ConfirmedLease), SyntraError> {
        if principal.is_empty() || principal.len() > syntra_core::reliable::MAX_RELIABLE_PRINCIPAL_LEN {
            return Err(SyntraError::Protocol { code: ErrorCode::InvalidArgument, message: "principal length out of bounds".to_string() });
        }
        if version == 0 { return Err(SyntraError::Protocol { code: ErrorCode::InvalidArgument, message: "version must be nonzero".to_string() }); }
        let lease = negotiate_lease(proposal)?;
        let mut inner = self.lock()?;
        if inner.draining { return Err(SyntraError::Unavailable("draining; no new sessions".to_string())); }
        if inner.sessions.len() >= self.bounds.max_sessions { return Err(resource("too many reliable sessions")); }
        if inner.resume_index.len() >= self.bounds.max_resume_credentials { return Err(resource("too many resume credentials")); }
        let sid = generate_session_id()?;
        if inner.sessions.contains_key(&sid) { return Err(internal("session id collision")); }
        let cred = generate_resume_credential()?;
        if inner.resume_index.contains_key(&cred) { return Err(internal("resume credential collision")); }
        let exp = now_ms.saturating_add(self.bounds.resume_lifetime_ms);
        inner.sessions.insert(sid, SessionState {
            principal: principal.clone(), version, epoch: 1,
            last_activity_ms: now_ms, lease, active_connection: None,
            outcomes: OutcomeStore::default(), tombstones: TombstoneStore::default(),
        });
        inner.resume_index.insert(cred.clone(), ResumeEntry { session_id: sid, principal, version, issued_at_ms: now_ms, expires_at_ms: exp });
        Ok((sid, 1, cred, lease))
    }
    pub fn attach(&self, now_ms: u64, session_id: &[u8], resume_credential: &[u8], connection_id: String, principal: &str, version: u32, proposal: LeaseProposal) -> Result<(u64, ConfirmedLease, Option<String>, Option<Vec<u8>>), SyntraError> {
        let sid = validate_session_id(session_id)?;
        if connection_id.is_empty() || connection_id.len() > 256 {
            return Err(SyntraError::Protocol { code: ErrorCode::InvalidArgument, message: "connection_id length out of bounds".to_string() });
        }
        let lease = negotiate_lease(proposal)?;
        let fresh_pre = if resume_credential.is_empty() {
            None
        } else {
            Some(generate_resume_credential()?)
        };
        let mut inner = self.lock()?;
        if inner.draining { return Err(SyntraError::Unavailable("draining; no new attachments".to_string())); }
        let (bp, bv, cur) = {
            let s = inner.sessions.get(&sid).ok_or_else(|| SyntraError::Handshake {
                code: ErrorCode::Unauthenticated, message: "unknown session".to_string() })?;
            (s.principal.clone(), s.version, s.epoch)
        };
        if bp != principal { return Err(unauthenticated("principal mismatch for session")); }
        if bv != version { return Err(failed_precondition("version mismatch for session")); }
        if let Some(fresh) = fresh_pre {
            let cred = validate_resume_credential(resume_credential)?;
            if inner.revoked.contains_key(&cred.0) { return Err(unauthenticated("resume credential revoked")); }
            let (rp, rv, rs, rexp) = {
                let e = inner.resume_index.get(&cred.0).ok_or_else(|| SyntraError::Handshake {
                    code: ErrorCode::Unauthenticated, message: "unknown resume credential".to_string() })?;
                (e.principal.clone(), e.version, e.session_id, e.expires_at_ms)
            };
            if rs != sid { return Err(unauthenticated("resume credential audience mismatch")); }
            if rp != principal || rv != version { return Err(unauthenticated("resume credential binding mismatch")); }
            if now_ms > rexp { return Err(unauthenticated("resume credential expired")); }
            let proposed = next_epoch(cur)?;
            check_epoch_advance(cur, proposed)?;
            if inner.resume_index.contains_key(&fresh) || inner.revoked.contains_key(&fresh) {
                return Err(internal("resume credential collision"));
            }
            let total = inner.resume_index.len().saturating_add(inner.revoked.len());
            if total.saturating_add(1) > self.bounds.max_resume_credentials.saturating_mul(2) {
                return Err(resource("too many resume credentials"));
            }
            let st = inner.sessions.get(&sid).ok_or_else(|| SyntraError::Handshake {
                code: ErrorCode::Unauthenticated, message: "unknown session".to_string() })?;
            if st.epoch != cur { return Err(failed_precondition("concurrent attach raced epoch")); }
            // Pre-reserve Fenced-signal capacity BEFORE committing the
            // epoch/connection rotation: ControlQueue::push is fallible
            // (bounded), and a post-mutation push failure must not leave a
            // committed rotation without its fence signal (or swallow the
            // error). Under the manager lock no concurrent mutation can
            // invalidate this check, so the push below must succeed.
            if st.active_connection.is_some()
                && (inner.signals.len() >= self.bounds.max_control_queue
                    || inner.signals.bytes.saturating_add(32) > self.bounds.max_control_bytes)
            {
                return Err(resource("control queue full; back off"));
            }
            let st = inner.sessions.get_mut(&sid).ok_or_else(|| SyntraError::Handshake {
                code: ErrorCode::Unauthenticated, message: "unknown session".to_string() })?;
            if st.epoch != cur { return Err(failed_precondition("concurrent attach raced epoch")); }
            let fenced = st.active_connection.clone();
            st.epoch = proposed;
            st.active_connection = Some(connection_id);
            st.last_activity_ms = now_ms;
            st.lease = lease;
            inner.resume_index.remove(&cred.0);
            let rev_exp = now_ms.saturating_add(self.bounds.resume_lifetime_ms);
            inner.revoked.insert(cred.0.clone(), rev_exp);
            let exp = now_ms.saturating_add(self.bounds.resume_lifetime_ms);
            inner.resume_index.insert(fresh.clone(), ResumeEntry {
                session_id: sid, principal: bp, version: bv, issued_at_ms: now_ms, expires_at_ms: exp });
            if fenced.is_some() {
                // Pre-reserved above: this push must succeed; propagate
                // instead of swallowing so a bound change is never silent.
                inner.signals.push(&self.bounds, sid, SessionSignal::Fenced)?;
            }
            Ok((proposed, lease, fenced, Some(fresh)))
        } else {
            validate_epoch(cur)?;
            let st = inner.sessions.get_mut(&sid).ok_or_else(|| SyntraError::Handshake {
                code: ErrorCode::Unauthenticated, message: "unknown session".to_string() })?;
            if st.active_connection.is_some() {
                return Err(failed_precondition("session already attached; present resume credential"));
            }
            st.active_connection = Some(connection_id);
            st.last_activity_ms = now_ms;
            st.lease = lease;
            let epoch = st.epoch;
            Ok((epoch, lease, None, None))
        }
    }
    pub fn detach(&self, session_id: &[u8], connection_id: &str) -> Result<(), SyntraError> {
        let sid = validate_session_id(session_id)?;
        let mut inner = self.lock()?;
        if let Some(st) = inner.sessions.get_mut(&sid) {
            if st.active_connection.as_deref() == Some(connection_id) { st.active_connection = None; }
        }
        Ok(())
    }
    pub fn record_result(&self, now_ms: u64, session_id: &[u8], expected_epoch: u64, delivery_id: &[u8], method: String, payload: Vec<u8>, outcome: StoredOutcome) -> Result<ReconcileOutcome, SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        if payload.len() > syntra_core::MAX_FRAME_BYTES { return Err(resource("payload exceeds envelope bound")); }
        let mut inner = self.lock()?;
        let st = inner.sessions.get_mut(&sid).ok_or_else(|| failed_precondition("unknown session for result"))?;
        // Fencing: a connection fenced by a newer attach (epoch advanced)
        // must not complete work. Callers pass the epoch they attached at;
        // anything stale is rejected before any outcome mutation.
        if st.epoch != expected_epoch {
            return Err(failed_precondition("stale attachment epoch; fenced connection cannot complete"));
        }
        st.last_activity_ms = now_ms;
        st.outcomes.insert(&self.bounds, now_ms, did, method, payload, outcome)
    }
    pub fn reconcile(&self, now_ms: u64, session_id: &[u8], delivery_id: &[u8]) -> Result<(ReconcileOutcome, Option<StoredOutcome>), SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        let inner = self.lock()?;
        let st = inner.sessions.get(&sid).ok_or_else(|| failed_precondition("unknown session for reconcile"))?;
        let o = st.outcomes.get(now_ms, self.bounds.result_retention_ms, &did);
        // Tombstones are terminal too: an outcome with no retained result
        // but a live tombstone reconciles to the tombstoned error instead
        // of Unknown, so a retry after deadline/cancel observes the
        // terminal code rather than re-dispatching forever.
        let (o, stored) = match o {
            ReconcileOutcome::Retained => (o, st.outcomes.outcome_of(&did)),
            ReconcileOutcome::Unknown => match st.tombstones.get(now_ms, self.bounds.tombstone_retention_ms, &did) {
                Some(code) => (ReconcileOutcome::Retained, Some(StoredOutcome::Error {
                    code, message: "terminal outcome retained as tombstone".to_string(),
                })),
                None => (ReconcileOutcome::Unknown, None),
            },
            ReconcileOutcome::Forgotten => (o, None),
            ReconcileOutcome::Pending => (o, None),
        };
        Ok((o, stored))
    }
    pub fn forget(&self, now_ms: u64, session_id: &[u8], expected_epoch: u64, delivery_id: &[u8]) -> Result<bool, SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        let mut inner = self.lock()?;
        let st = inner.sessions.get_mut(&sid).ok_or_else(|| failed_precondition("unknown session for forget"))?;
        if st.epoch != expected_epoch {
            return Err(failed_precondition("stale attachment epoch; fenced connection cannot forget"));
        }
        Ok(st.outcomes.forget(&self.bounds, now_ms, &did))
    }
    pub fn note_dispatch(&self, now_ms: u64, session_id: &[u8], delivery_id: &[u8]) -> Result<(), SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        let mut inner = self.lock()?;
        let st = inner.sessions.get_mut(&sid).ok_or_else(|| failed_precondition("unknown session for dispatch"))?;
        st.last_activity_ms = now_ms;
        st.outcomes.note_dispatch(&self.bounds, now_ms, did)
    }
    pub fn record_tombstone(&self, now_ms: u64, session_id: &[u8], expected_epoch: u64, delivery_id: &[u8], code: ErrorCode) -> Result<(), SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        let mut inner = self.lock()?;
        let st = inner.sessions.get_mut(&sid).ok_or_else(|| failed_precondition("unknown session for tombstone"))?;
        if st.epoch != expected_epoch {
            return Err(failed_precondition("stale attachment epoch; fenced connection cannot tombstone"));
        }
        st.outcomes.pending.remove(&did);
        st.tombstones.record(&self.bounds, now_ms, did, code)
    }
    pub fn tombstone_of(&self, now_ms: u64, session_id: &[u8], delivery_id: &[u8]) -> Result<Option<ErrorCode>, SyntraError> {
        let sid = validate_session_id(session_id)?;
        let did = validate_delivery_id(delivery_id)?;
        let inner = self.lock()?;
        let st = inner.sessions.get(&sid).ok_or_else(|| failed_precondition("unknown session for tombstone lookup"))?;
        Ok(st.tombstones.get(now_ms, self.bounds.tombstone_retention_ms, &did))
    }
    pub fn revoke(&self, now_ms: u64, credential: &[u8]) -> Result<bool, SyntraError> {
        let cred = validate_resume_credential(credential)?;
        let mut inner = self.lock()?;
        if !inner.revoked.contains_key(&cred.0) {
            let total = inner.resume_index.len().saturating_add(inner.revoked.len());
            if total >= self.bounds.max_resume_credentials.saturating_mul(2) {
                return Err(resource("revocation set exhausted; retire sessions"));
            }
        }
        let removed = inner.resume_index.remove(&cred.0).is_some();
        if !inner.revoked.contains_key(&cred.0) {
            let exp = now_ms.saturating_add(self.bounds.resume_lifetime_ms);
            inner.revoked.insert(cred.0, exp);
        }
        Ok(removed)
    }
    pub fn poll_idle(&self, now_ms: u64) -> Result<Vec<(SessionId, SessionSignal)>, SyntraError> {
        let mut inner = self.lock()?;
        let mut idle: Vec<(SessionId, SessionSignal)> = Vec::new();
        for (id, st) in inner.sessions.iter() {
            if idle.len() >= self.bounds.max_control_queue { break; }
            if st.active_connection.is_some()
                && now_ms.saturating_sub(st.last_activity_ms) > u64::from(st.lease.idle_timeout_ms) {
                idle.push((*id, SessionSignal::IdleTimeout));
            }
        }
        for (id, sig) in &idle {
            inner.signals.push(&self.bounds, *id, *sig)?;
        }
        for (id, _) in &idle {
            if let Some(st) = inner.sessions.get_mut(id) {
                st.active_connection.take();
            }
        }
        Ok(idle)
    }
    pub fn signal(&self, session_id: &[u8], signal: SessionSignal) -> Result<(), SyntraError> {
        let sid = validate_session_id(session_id)?;
        let mut inner = self.lock()?;
        if !inner.sessions.contains_key(&sid) { return Err(failed_precondition("unknown session for signal")); }
        inner.signals.push(&self.bounds, sid, signal)
    }
    pub fn drain_signals(&self, limit: usize) -> Vec<(SessionId, SessionSignal)> {
        let capped = limit.min(self.bounds.max_control_queue).max(1);
        match self.lock() { Ok(mut inner) => inner.signals.drain(capped), Err(_) => Vec::new() }
    }
    pub fn session_count(&self) -> usize { self.lock().map(|g| g.sessions.len()).unwrap_or(0) }
    pub fn signal_len(&self) -> usize { self.lock().map(|g| g.signals.len()).unwrap_or(0) }
    pub fn reap_expired(&self, now_ms: u64) -> (usize, usize, usize, usize) {
        let Ok(mut inner) = self.lock() else { return (0, 0, 0, 0); };
        let mut o = 0; let mut t = 0;
        for st in inner.sessions.values_mut() {
            o += st.outcomes.reap_expired(&self.bounds, now_ms, self.bounds.result_retention_ms);
            t += st.tombstones.reap_expired(now_ms, self.bounds.tombstone_retention_ms);
        }
        let before = inner.resume_index.len();
        inner.resume_index.retain(|_, e| now_ms <= e.expires_at_ms);
        let resume_reaped = before.saturating_sub(inner.resume_index.len());
        let before_rev = inner.revoked.len();
        inner.revoked.retain(|_, exp| now_ms <= *exp);
        let revoked_reaped = before_rev.saturating_sub(inner.revoked.len());
        (o, t, resume_reaped, revoked_reaped)
    }
    pub fn drain_for_shutdown(&self) -> Vec<(SessionId, SessionSignal)> {
        let Ok(mut inner) = self.lock() else { return Vec::new(); };
        inner.draining = true;
        let mut ids: Vec<SessionId> = Vec::new();
        for (id, st) in inner.sessions.iter_mut() {
            if st.active_connection.take().is_some() { ids.push(*id); }
        }
        let mut out = inner.signals.drain(self.bounds.max_control_queue);
        out.extend(ids.into_iter().map(|id| (id, SessionSignal::GoingAway)));
        out
    }
    pub fn epoch_of(&self, session_id: &[u8]) -> Result<u64, SyntraError> {
        let sid = validate_session_id(session_id)?;
        let inner = self.lock()?;
        inner.sessions.get(&sid).map(|s| s.epoch).ok_or_else(|| failed_precondition("unknown session"))
    }
}
fn generate_session_id() -> Result<SessionId, SyntraError> {
    let mut buf = [0u8; syntra_core::reliable::SESSION_ID_LEN];
    fill_random(&mut buf).map_err(|e| internal(&format!("session id RNG failed: {e}")))?;
    if buf == [0u8; syntra_core::reliable::SESSION_ID_LEN] { return Err(internal("session id RNG returned zero")); }
    Ok(SessionId(buf))
}
fn generate_resume_credential() -> Result<Vec<u8>, SyntraError> {
    let mut buf = vec![0u8; syntra_core::reliable::RESUME_CREDENTIAL_LEN];
    fill_random(&mut buf).map_err(|e| internal(&format!("resume RNG failed: {e}")))?;
    if buf.iter().all(|&b| b == 0) { return Err(internal("resume RNG returned zero")); }
    Ok(buf)
}
pub fn now_ms() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now().duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis().min(u128::from(u64::MAX)) as u64).unwrap_or(0)
}
#[cfg(test)]
mod tests {
    use super::*;
    use syntra_core::reliable::LeaseProposal;
    fn bounds() -> ControlBounds {
        ControlBounds {
            max_sessions: 4, max_retained_results: 4, max_retained_bytes: 4096,
            max_tombstones: 4, max_resume_credentials: 8,
            max_control_queue: 8, max_control_bytes: 1024,
            result_retention_ms: 60_000, tombstone_retention_ms: 60_000, resume_lifetime_ms: 60_000,
        }
    }
    fn proposal() -> LeaseProposal { LeaseProposal { idle_timeout_ms: 10_000, keepalive_interval_ms: 2_000 } }
    fn manager() -> ReliableSessionManager { ReliableSessionManager::new(bounds()).expect("bounds") }
    #[test]
    fn create_and_attach() {
        let m = manager();
        let (sid, epoch, cred, lease) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        assert_eq!(epoch, 1);
        assert_eq!(cred.len(), 32);
        assert!(lease.keepalive_interval_ms < lease.idle_timeout_ms);
        let (e, _, f, r) = m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("attach");
        assert_eq!(e, 1);
        assert!(f.is_none());
        assert!(r.is_none());
    }
    #[test]
    fn resume_fences() {
        let m = manager();
        let (sid, _, cred, _) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("first");
        let (e2, _, fenced, rotated) = m.attach(1_002, &sid.0, &cred, "conn-2".to_string(), "svc-a", 1, proposal()).expect("resume");
        assert_eq!(e2, 2);
        assert_eq!(fenced.as_deref(), Some("conn-1"));
        let rotated = rotated.expect("resume must rotate credential");
        assert_eq!(rotated.len(), 32);
        assert_ne!(rotated, cred);
        assert!(m.attach(1_003, &sid.0, &cred, "conn-3".to_string(), "svc-a", 1, proposal()).is_err());
    }
    #[test]
    fn reconcile_flow() {
        let m = manager();
        let (sid, _, _, _) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("attach");
        let did = [7u8; 16];
        let (o, _) = m.reconcile(1_002, &sid.0, &did).expect("r");
        assert_eq!(o, ReconcileOutcome::Unknown);
        m.record_result(1_003, &sid.0, 1, &did, "/example.Echo/Echo".to_string(), b"h".to_vec(), StoredOutcome::Payload(b"h".to_vec())).expect("rec");
        let (o2, _) = m.reconcile(1_004, &sid.0, &did).expect("r2");
        assert_eq!(o2, ReconcileOutcome::Retained);
        assert!(m.record_result(1_005, &sid.0, 1, &did, "/example.Echo/Echo".to_string(), b"x".to_vec(), StoredOutcome::Payload(b"x".to_vec())).is_err());
        let (o3, _) = m.reconcile(61_003 + 1_003, &sid.0, &did).expect("r3");
        assert_eq!(o3, ReconcileOutcome::Forgotten);
    }
    #[test]
    fn tombstone_flow() {
        let m = manager();
        let (sid, _, _, _) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("attach");
        m.record_tombstone(1_002, &sid.0, 1, &[11u8; 16], ErrorCode::DeadlineExceeded).expect("t");
        assert_eq!(m.tombstone_of(1_003, &sid.0, &[11u8; 16]).expect("l"), Some(ErrorCode::DeadlineExceeded));
        // UNAVAILABLE is unknown-outcome, never tombstoned.
        assert!(m.record_tombstone(1_004, &sid.0, 1, &[12u8; 16], ErrorCode::Unavailable).is_err());
        // A live tombstone reconciles to the terminal error, not Unknown.
        let (o, stored) = m.reconcile(1_005, &sid.0, &[11u8; 16]).expect("reconcile tombstone");
        assert_eq!(o, ReconcileOutcome::Retained);
        match stored {
            Some(StoredOutcome::Error { code, .. }) => assert_eq!(code, ErrorCode::DeadlineExceeded),
            other => panic!("expected tombstoned error, got {other:?}"),
        }
    }
    #[test]
    fn fenced_connection_cannot_complete() {
        let m = manager();
        let (sid, _, cred, _) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("first");
        // Advance the epoch: conn-1 is now fenced.
        let (e2, _, _, rotated) = m.attach(1_002, &sid.0, &cred, "conn-2".to_string(), "svc-a", 1, proposal()).expect("resume");
        assert_eq!(e2, 2);
        let _ = rotated;
        let did = [9u8; 16];
        // Stale epoch (conn-1) cannot record, forget, or tombstone.
        assert!(m.record_result(1_003, &sid.0, 1, &did, "/a/B/C".to_string(), b"p".to_vec(), StoredOutcome::Payload(b"p".to_vec())).is_err());
        assert!(m.forget(1_003, &sid.0, 1, &did).is_err());
        assert!(m.record_tombstone(1_003, &sid.0, 1, &did, ErrorCode::Cancelled).is_err());
        // Current epoch (conn-2) works.
        m.record_result(1_004, &sid.0, 2, &did, "/a/B/C".to_string(), b"p".to_vec(), StoredOutcome::Payload(b"p".to_vec())).expect("current epoch records");
        assert!(m.forget(1_005, &sid.0, 2, &did).expect("current epoch forgets"));
    }
    #[test]
    fn idle_and_drain_bounded() {
        let m = manager();
        let (sid, _, _, _) = m.create_session(1_000, "svc-a".to_string(), 1, proposal()).expect("create");
        m.attach(1_001, &sid.0, &[], "conn-1".to_string(), "svc-a", 1, proposal()).expect("attach");
        let s = m.poll_idle(12_001).expect("poll");
        assert_eq!(s.len(), 1);
        assert!(m.drain_signals(64).len() <= 8);
        let _ = m.drain_for_shutdown();
        assert!(m.create_session(99_999, "svc-b".to_string(), 1, proposal()).is_err());
    }
}
