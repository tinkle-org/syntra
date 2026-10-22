//! `syntra-runtime`: connection runtime over transport-agnostic bytes.
//!
//! - [`Initiator`] — client engine: handshake, RPC calls, cancellation,
//!   notifications.
//! - [`Host`] — server engine: handshake acceptance, request dispatch,
//!   cancellation, connection-bound sessions.
//! - [`SessionManager`] / [`Principal`] / [`Authenticator`] — generic
//!   auth hooks. No user, account, or chat types exist here.
//!
//! Sessions are connection-bound only (SNTR-SESS-003): the session
//! lifetime equals the connection lifetime, and resumption across
//! connections is unavailable in v1 (SNTR-SESS-006; open blocker 2 —
//! recorded, not invented).
//!
//! Open questions this crate does NOT invent bindings for (see
//! `SESSION-OPEN-QUESTIONS.md`): typed pre-`ACTIVE` error carrier (B1),
//! pre-`ACTIVE` notification conflict (B2), stale `request_id` reuse
//! (B3), payload-vs-envelope size (B8), cancel/deadline/`UNAVAILABLE`
//! races (B10). Enforced choices are documented on the items.

pub mod connection;
pub mod host;
pub mod initiator;
pub mod policy;
pub mod recovery;
pub mod reliable;
pub mod session;

pub use connection::{CancelToken, Connection, ConnectionConfig};
pub use host::{AllowAll, FnHandler, Handler, HandlerFut, HandlerOutcome, Host};
pub use initiator::Initiator;
pub use policy::{
    AdmittedRequest, AuthDecision, AuthzDecision, CompletionDisposition, CompletionToken,
    HostResult, PolicyDeadlines,
};
pub use recovery::{RecoveryAction, RecoveryInput, StreamCheckpoint, StreamRecovery};
pub use reliable::{now_ms, ReliableSessionManager, StoredOutcome};
pub use session::{
    AllowAnonymous, AuthError, Authenticator, Principal, RejectAll, Session, SessionManager,
    StaticToken,
};

/// Sleep without depending on a timer driver: native tokio timers on
/// native targets, JS `setTimeout` on wasm32. Powers deadline paths that
/// must also run in browsers.
pub async fn sleep_for(d: std::time::Duration) {
    connection::sleep(d).await;
}

/// In-memory connected pair for tests, embeds, and FFI loopback.
///
/// Wires an [`Initiator`] to a [`Host`] with bounded channels and
/// background pumps (host<->initiator), exactly like a transport adapter
/// would, minus the sockets. Returns the initiator and the shared host.
/// Remote teardown propagates like a real transport: when either side
/// closes, both pumps end and the surviving peer observes transport loss
/// (`UNAVAILABLE` to in-flight waiters, handshake waiters fail) —
/// idempotent with local close, so graceful shutdown stays clean.
pub fn loopback_pair(
    auth: std::sync::Arc<dyn Authenticator>,
    handler: std::sync::Arc<dyn Handler>,
    config: ConnectionConfig,
) -> (Initiator, std::sync::Arc<Host>) {
    let (initiator, mut init_rx) = Initiator::new(config.clone());
    let (host, mut host_rx) = Host::new(config, auth, handler);

    // Teardown coordination: the two pumps must BOTH finish draining their
    // queued frames before either side observes transport loss. Previously
    // each pump called on_transport_lost() after its own drain, so the first
    // pump to finish could close the peer while the other pump still held
    // queued terminal results, losing them. Now both pumps rendezvous at a
    // barrier after draining, and exactly the barrier leader performs the
    // transport-lost notifications. Public API is unchanged.
    let teardown = std::sync::Arc::new(tokio::sync::Barrier::new(2));

    let pump_host = host.clone();
    let pump_init = initiator.clone();
    let mut init_closed_a = pump_init.subscribe_close();
    let mut host_closed_a = pump_host.subscribe_close();
    let teardown_a = teardown.clone();
    crate::connection::spawn_task(async move {
        loop {
            if pump_host.is_closed() || pump_init.is_closed() {
                break;
            }
            tokio::select! {
                biased;
                _ = init_closed_a.changed() => break,
                _ = host_closed_a.changed() => break,
                msg = init_rx.recv() => {
                    match msg {
                        Some(bytes) => pump_host.ingest(&bytes).await,
                        None => break,
                    }
                }
            }
        }
        while let Ok(bytes) = init_rx.try_recv() {
            pump_host.ingest(&bytes).await;
        }
        // Drain complete: wait for the sibling pump before tearing down, so
        // no queued terminal result is lost to an early close.
        if teardown_a.wait().await.is_leader() {
            pump_init.on_transport_lost().await;
            pump_host.on_transport_lost().await;
        }
    });
    let pump_host = host.clone();
    let pump_init = initiator.clone();
    let mut init_closed_b = pump_init.subscribe_close();
    let mut host_closed_b = pump_host.subscribe_close();
    let teardown_b = teardown.clone();
    crate::connection::spawn_task(async move {
        loop {
            if pump_host.is_closed() || pump_init.is_closed() {
                break;
            }
            tokio::select! {
                biased;
                _ = init_closed_b.changed() => break,
                _ = host_closed_b.changed() => break,
                msg = host_rx.recv() => {
                    match msg {
                        Some(bytes) => pump_init.ingest(&bytes).await,
                        None => break,
                    }
                }
            }
        }
        while let Ok(bytes) = host_rx.try_recv() {
            pump_init.ingest(&bytes).await;
        }
        // Drain complete: wait for the sibling pump before tearing down, so
        // no queued terminal result is lost to an early close.
        if teardown_b.wait().await.is_leader() {
            pump_init.on_transport_lost().await;
            pump_host.on_transport_lost().await;
        }
    });

    (initiator, host)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn loopback_echo_round_trip() {
        let auth = std::sync::Arc::new(AllowAnonymous);
        let handler =
            std::sync::Arc::new(FnHandler(
                |_m, p, _c| async move { HandlerOutcome::Payload(p) },
            ));
        let (initiator, _host) = loopback_pair(auth, handler, ConnectionConfig::default());
        let id = initiator.handshake(vec![]).await.expect("handshake");
        assert!(!id.is_empty());
        let out = initiator
            .call("/example.Echo/Echo", b"hello".to_vec(), 2000)
            .await
            .expect("echo");
        assert_eq!(out, b"hello");
    }
}
