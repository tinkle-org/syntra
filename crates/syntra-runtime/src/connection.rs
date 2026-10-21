//! Shared transport-agnostic connection engine.
//!
//! A `Connection` owns one half of a Syntra conversation: the six-state
//! machine, the negotiated version, the bounded pending-RPC table, the
//! notification queue, and the outbound byte channel. `Initiator` and
//! `Host` wrap it with role-specific handshake/RPC behavior.
//!
//! Timing rules enforced here (SNTR-RPC-004, SNTR-HS-011):
//! - every effective deadline is computed as an absolute `Instant`
//!   BEFORE queue admission, so queueing can never silently consume the
//!   caller's budget;
//! - completion wins races: all `select!` sites are `biased` with the
//!   completion branch first (cancel-vs-deadline ties prefer `CANCELLED`;
//!   open tie-break B10 is recorded, not invented);
//! - handshake timeout explicitly closes the core
//!   (`fail_handshake_and_close`);
//! - pending entries are removed on validation failure, send failure,
//!   timeout, cancellation, transport loss, and dropped futures
//!   (`PendingGuard`).

use std::sync::{
    atomic::{AtomicBool, AtomicU32, Ordering},
    Arc,
};
use std::time::Duration;

use bytes::Bytes;
use tokio::sync::{mpsc, oneshot, watch, Mutex as AsyncMutex, Notify, RwLock};
use tracing::debug;

use syntra_core::{ConnectionState, PendingTable, RequestIdAllocator, StateEvent, SyntraError};

/// Tunables. All bounds are documented per deployment (SNTR-REL-031).
#[derive(Debug, Clone)]
pub struct ConnectionConfig {
    /// Max concurrent RPCs. Peers MUST support >=16 (SNTR-RPC-008).
    pub max_outstanding: usize,
    /// Default call budget when `timeout_ms == 0` (bounded, documented).
    pub default_timeout: Duration,
    /// Absolute clamp for any single RPC budget (documented policy:
    /// larger requested budgets are clamped, never silently unbounded).
    pub max_rpc_timeout: Duration,
    /// Handshake deadline (SNTR-HS-002/011).
    pub handshake_timeout: Duration,
    /// Outgoing notification channel capacity.
    pub notification_capacity: usize,
    /// Outgoing writer channel capacity (backpressure bound).
    pub writer_capacity: usize,
}

impl Default for ConnectionConfig {
    fn default() -> Self {
        Self {
            max_outstanding: 64,
            default_timeout: Duration::from_secs(30),
            max_rpc_timeout: Duration::from_secs(120),
            handshake_timeout: syntra_core::HANDSHAKE_TIMEOUT_DEFAULT,
            notification_capacity: 256,
            writer_capacity: 256,
        }
    }
}

/// Which half of the conversation this engine plays.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Role {
    Initiator,
    Host,
}

/// Cooperative cancellation token (no executor dependency).
#[derive(Debug, Clone)]
pub struct CancelToken {
    inner: Arc<CancelInner>,
}

#[derive(Debug)]
struct CancelInner {
    notify: Notify,
    flag: AtomicBool,
}

impl CancelToken {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(CancelInner {
                notify: Notify::new(),
                flag: AtomicBool::new(false),
            }),
        }
    }

    pub fn cancel(&self) {
        self.inner.flag.store(true, Ordering::SeqCst);
        self.inner.notify.notify_waiters();
    }

    pub fn is_cancelled(&self) -> bool {
        self.inner.flag.load(Ordering::SeqCst)
    }

    pub async fn cancelled(&self) {
        if self.is_cancelled() {
            return;
        }
        self.inner.notify.notified().await;
    }
}

impl Default for CancelToken {
    fn default() -> Self {
        Self::new()
    }
}

/// Sleep without depending on a timer driver (works on native and wasm).
pub(crate) async fn sleep(d: Duration) {
    #[cfg(not(target_arch = "wasm32"))]
    {
        tokio::time::sleep(d).await;
    }
    #[cfg(target_arch = "wasm32")]
    {
        wasm_sleep(d).await;
    }
}

#[cfg(target_arch = "wasm32")]
async fn wasm_sleep(d: Duration) {
    use wasm_bindgen::prelude::*;
    if d.is_zero() {
        return;
    }
    let ms = d.as_millis().min(u32::MAX as u128) as u32;
    let promise = js_sys::Promise::new(&mut |resolve, _reject| {
        let global = js_sys::global();
        let set_timeout =
            js_sys::Reflect::get(&global, &JsValue::from_str("setTimeout")).expect("setTimeout");
        let func: &js_sys::Function = set_timeout.unchecked_ref();
        let cb = Closure::once(move |_: JsValue| {
            let _ = resolve.call0(&JsValue::NULL);
        });
        let _ = func.call2(&global, cb.as_ref().unchecked_ref(), &JsValue::from(ms));
        // The closure must outlive the timer; the timer holds the only
        // other reference once scheduled.
        cb.forget();
    });
    let _ = wasm_bindgen_futures::JsFuture::from(promise).await;
}

/// Sleep until an absolute deadline (no-op when already past).
pub(crate) async fn sleep_until(deadline: std::time::Instant) {
    let now = std::time::Instant::now();
    if deadline > now {
        sleep(deadline - now).await;
    }
}

/// Spawn a background task. Native uses the tokio runtime; wasm uses the
/// browser microtask queue (`spawn_local`). The returned handle aborts
/// the task on native; on wasm cancellation is cooperative only
/// (documented: browser handlers MUST honor `CancelToken`).
pub(crate) struct TaskHandle {
    #[cfg(not(target_arch = "wasm32"))]
    inner: Option<tokio::task::JoinHandle<()>>,
}

impl TaskHandle {
    pub(crate) fn abort(&self) {
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(h) = &self.inner {
            h.abort();
        }
    }
}

#[cfg(not(target_arch = "wasm32"))]
pub(crate) fn spawn_task<F>(fut: F) -> TaskHandle
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    TaskHandle {
        inner: Some(tokio::spawn(fut)),
    }
}

/// Browser tasks run on the microtask queue (`spawn_local`), which does
/// not require `Send` (single-threaded). Cancellation there is
/// cooperative only — see `TaskHandle::abort`.
#[cfg(target_arch = "wasm32")]
pub(crate) fn spawn_task<F>(fut: F) -> TaskHandle
where
    F: std::future::Future<Output = ()> + 'static,
{
    wasm_bindgen_futures::spawn_local(fut);
    TaskHandle {}
}

/// Fill `buf` with cryptographic randomness (OS-backed on every target).
pub(crate) fn fill_random(buf: &mut [u8]) -> Result<(), String> {
    #[cfg(not(target_arch = "wasm32"))]
    {
        getrandom::fill(buf).map_err(|e| e.to_string())
    }
    #[cfg(target_arch = "wasm32")]
    {
        getrandom::getrandom(buf).map_err(|e| e.to_string())
    }
}

/// Remove a pending entry unless the RPC already completed. Guards every
/// path after queue admission: validation failure, send failure,
/// timeout, cancellation, and dropped futures (SNTR-REL-007).
pub(crate) struct PendingGuard<'a> {
    table: &'a PendingTable,
    id: u64,
}

impl<'a> PendingGuard<'a> {
    pub(crate) fn new(table: &'a PendingTable, id: u64) -> Self {
        Self { table, id }
    }
}

impl Drop for PendingGuard<'_> {
    fn drop(&mut self) {
        self.table.abandon(self.id);
    }
}

/// Successful handshake output observed by the waiter.
#[derive(Debug, Clone)]
pub(crate) struct HandshakeDone {
    pub connection_id: String,
}

pub(crate) struct Shared {
    pub role: Role,
    pub state: RwLock<ConnectionState>,
    pub version: RwLock<Option<u32>>,
    pub proposed_min: u32,
    pub proposed_max: u32,
    pub pending: PendingTable,
    pub ids: RequestIdAllocator,
    pub writer: mpsc::Sender<Vec<u8>>,
    pub notif_tx: mpsc::Sender<Bytes>,
    pub handshake_tx: AsyncMutex<Option<oneshot::Sender<Result<HandshakeDone, SyntraError>>>>,
    pub config: ConnectionConfig,
    pub closed: AtomicBool,
    /// ACTIVE-phase decode failures (misbehavior counter, SNTR-ASEC-020).
    pub misbehavior: AtomicU32,
    /// Close broadcast: fired on every path to CLOSED so transport pumps
    /// (which only hold byte channels) learn remote teardown promptly.
    /// Pumps `select!` on this alongside reads; firing is idempotent.
    pub closed_tx: watch::Sender<bool>,
}

impl Shared {
    pub fn new(
        role: Role,
        writer: mpsc::Sender<Vec<u8>>,
        config: ConnectionConfig,
        proposed_min: u32,
        proposed_max: u32,
    ) -> (Arc<Self>, mpsc::Receiver<Bytes>) {
        let (notif_tx, notif_rx) = mpsc::channel(config.notification_capacity);
        let (closed_tx, _) = watch::channel(false);
        let shared = Arc::new(Self {
            role,
            state: RwLock::new(ConnectionState::Connected),
            version: RwLock::new(None),
            proposed_min,
            proposed_max,
            pending: PendingTable::new(config.max_outstanding),
            ids: RequestIdAllocator::new(),
            writer,
            notif_tx,
            handshake_tx: AsyncMutex::new(None),
            config,
            closed: AtomicBool::new(false),
            misbehavior: AtomicU32::new(0),
            closed_tx,
        });
        (shared, notif_rx)
    }
}

/// Transport-agnostic half-connection: state machine, version, pending
/// correlation, notification queue, outbound byte channel.
#[derive(Clone)]
pub struct Connection {
    pub(crate) shared: Arc<Shared>,
    notif_rx: Arc<AsyncMutex<mpsc::Receiver<Bytes>>>,
}

impl Connection {
    pub(crate) fn wrap(shared: Arc<Shared>, notif_rx: mpsc::Receiver<Bytes>) -> Self {
        Self {
            shared,
            notif_rx: Arc::new(AsyncMutex::new(notif_rx)),
        }
    }

    /// Current state (for diagnostics; not a wire value).
    pub async fn state(&self) -> ConnectionState {
        *self.shared.state.read().await
    }

    pub async fn negotiated_version(&self) -> Option<u32> {
        *self.shared.version.read().await
    }

    pub fn is_closed(&self) -> bool {
        self.shared.closed.load(Ordering::Relaxed)
    }

    pub(crate) async fn ctx(&self) -> syntra_core::ValidationContext {
        let s = *self.shared.state.read().await;
        let v = *self.shared.version.read().await;
        syntra_core::ValidationContext {
            state: s,
            negotiated_version: v,
        }
    }

    pub(crate) async fn transition(&self, ev: StateEvent) -> Result<(), SyntraError> {
        let cur = *self.shared.state.read().await;
        let next = cur.transition(ev)?;
        *self.shared.state.write().await = next;
        debug!(from = ?cur, to = ?next, event = ?ev, role = ?self.shared.role, "syntra state");
        Ok(())
    }

    pub(crate) async fn send_bytes(&self, bytes: Vec<u8>) -> Result<(), SyntraError> {
        if self.is_closed() {
            return Err(SyntraError::Closed("connection closed".to_string()));
        }
        self.shared
            .writer
            .send(bytes)
            .await
            .map_err(|_| SyntraError::Closed("transport writer gone".to_string()))
    }

    /// Terminal handshake failure: surface the typed code locally to the
    /// waiter (B1: NO zero-`request_id` `result` and NO second `hello` is
    /// emitted to carry it), then explicitly close the core
    /// (CLOSING -> CLOSED, pending drained with `TransportLost`).
    pub(crate) async fn fail_handshake_and_close(
        &self,
        code: syntra_core::ErrorCode,
        message: String,
    ) {
        self.fail_handshake(SyntraError::Handshake { code, message })
            .await;
        self.mark_closed_via_closing().await;
    }

    pub(crate) async fn fail_handshake(&self, e: SyntraError) {
        if let Some(tx) = self.shared.handshake_tx.lock().await.take() {
            let _ = tx.send(Err(e));
        }
    }

    pub(crate) async fn complete_handshake(&self, done: HandshakeDone) {
        if let Some(tx) = self.shared.handshake_tx.lock().await.take() {
            let _ = tx.send(Ok(done));
        }
    }

    /// Graceful close from ACTIVE: stop new RPCs, then teardown.
    /// Transport adapters observe CLOSING for the close handshake before
    /// dropping; the core itself ends at CLOSED with in-flight RPCs
    /// mapped to `UNAVAILABLE` (SNTR-HS-006/013).
    pub async fn close(&self) {
        let st = self.state().await;
        if st == ConnectionState::Active {
            let _ = self.transition(StateEvent::GracefulClose).await;
        }
        self.mark_closed_via_closing().await;
    }

    /// Abrupt transport loss: `UNAVAILABLE` (unknown outcome) to all
    /// in-flight RPCs, handshake waiter fails, state moves to CLOSED.
    pub async fn on_transport_lost(&self) {
        self.fail_handshake(SyntraError::Unavailable(
            "transport lost (outcome unknown)".to_string(),
        ))
        .await;
        self.mark_closed_abrupt().await;
    }

    async fn mark_closed_via_closing(&self) {
        self.shared.closed.store(true, Ordering::Relaxed);
        let cur = *self.shared.state.read().await;
        let next = match cur {
            ConnectionState::Closed => ConnectionState::Closed,
            ConnectionState::Closing => ConnectionState::Closed,
            _ => {
                // Handshake failures and graceful close pass through
                // CLOSING first (SNTR-HS-006/040).
                match cur.transition(StateEvent::HandshakeFailed) {
                    Ok(s) => s,
                    Err(_) => match cur.transition(StateEvent::GracefulClose) {
                        Ok(s) => s,
                        Err(_) => ConnectionState::Closed,
                    },
                }
            }
        };
        *self.shared.state.write().await = next;
        if next == ConnectionState::Closing {
            *self.shared.state.write().await = ConnectionState::Closed;
        }
        self.shared.pending.drain_transport_lost();
        self.fire_closed();
    }

    async fn mark_closed_abrupt(&self) {
        self.shared.closed.store(true, Ordering::Relaxed);
        *self.shared.state.write().await = ConnectionState::Closed;
        self.shared.pending.drain_transport_lost();
        self.fire_closed();
    }

    /// Subscribe to the close broadcast. Fires (with `true`) on every
    /// path to CLOSED so transport pumps learn remote teardown without
    /// polling. Resolves immediately if already closed.
    pub fn subscribe_close(&self) -> watch::Receiver<bool> {
        self.shared.closed_tx.subscribe()
    }

    fn fire_closed(&self) {
        let _ = self.shared.closed_tx.send(true);
    }

    /// Take the next notification payload (opaque application bytes).
    /// Returns None when the connection is closed and drained.
    pub async fn next_notification(&self) -> Option<Vec<u8>> {
        self.notif_rx.lock().await.recv().await.map(|b| b.to_vec())
    }

    /// Number of outstanding RPCs (for backpressure observability).
    pub fn pending_len(&self) -> usize {
        self.shared.pending.len()
    }
}
