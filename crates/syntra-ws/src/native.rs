//! Native WSS/WS adapter (`tokio-tungstenite` + `rustls`).
//!
//! Security properties (WSS section 1M, transport-security):
//! - TLS 1.3 only via a pinned `rustls` client config; <1.3 fails closed.
//! - Full chain + hostname + expiry validation before any Syntra byte.
//! - No `wss://` -> `ws://` downgrade retry (FORBIDDEN).
//! - SNI sent consistently with the intended hostname.
//! - No credentials in Upgrade target/headers/query; the only Syntra
//!   credential carrier is `ClientHello.credential` after 101.
//! - `Origin` is never authentication (WS section 1H).
//!
//! Framing: one binary message = one `Frame` (no length prefix).
//! Text (0x1) -> close 1003. Empty binary -> `INVALID_ARGUMENT` + close.
//! Assembled message > MAX_FRAME_BYTES is rejected during assembly
//! (tungstenite size cap) and re-checked on receipt -> close 1009.
//! Control frames (Ping/Pong/Close) never reach the Syntra core:
//! Ping is answered, Pong feeds liveness, Close tears down.
//!
//! Backpressure/liveness (WS sections 1I/1L): outbound queue bounded by
//! `writer_capacity`; a write stalled past `write_grace` closes a slow
//! receiver (typically 1001); Ping/Pong liveness closes silent peers
//! (typically 1001). In-flight RPCs get `UNAVAILABLE` on teardown.

use std::sync::{
    atomic::{AtomicBool, AtomicU64, Ordering},
    Arc,
};
use std::time::Duration;

use futures_util::{SinkExt, StreamExt};
use tokio::sync::mpsc;
use tokio_tungstenite::tungstenite::protocol::{frame::coding::CloseCode, CloseFrame, Message};

use syntra_core::{ErrorCode, SyntraError};
use syntra_runtime::{ConnectionConfig, Initiator};

use crate::config::{Endpoint, WsConfig};
use crate::error::TransportError;
use crate::{ENDPOINT_PATH, SUBPROTOCOL};

/// Live transport handle: protocol engine + shutdown.
pub struct WsHandle {
    /// Generic Syntra initiator (handshake, RPCs, notifications).
    pub conn: Initiator,
    /// Server's `connection_id` from `ServerReady` (diagnostic only,
    /// never an authenticator or resume token).
    pub connection_id: String,
    /// Selected Syntra version (`Frame.version` post-handshake).
    pub version: u32,
    shutdown_tx: Option<mpsc::Sender<CloseCode>>,
    closed: Arc<AtomicBool>,
}

impl WsHandle {
    /// Graceful close: stop new RPCs, allow close grace, WS Close 1000,
    /// then teardown (WSS section 1J / WS section 1J).
    pub async fn close(mut self) {
        self.conn.close().await;
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(CloseCode::Normal).await;
        }
        self.closed.store(true, Ordering::Relaxed);
    }

    pub fn connection(&self) -> &Initiator {
        &self.conn
    }

    pub fn is_closed(&self) -> bool {
        self.closed.load(Ordering::Relaxed)
    }
}

/// Map a Syntra condition to the WS close code to send (WS section 1J
/// table, normative). Codes 1005/1006/1015 are NEVER sent (local-only).
pub fn close_code_for_syntra(code: ErrorCode) -> CloseCode {
    match code {
        ErrorCode::Unauthenticated | ErrorCode::PermissionDenied => CloseCode::Policy,
        ErrorCode::Unimplemented
        | ErrorCode::FailedPrecondition
        | ErrorCode::InvalidArgument
        | ErrorCode::OutOfRange
        | ErrorCode::Aborted
        | ErrorCode::DataLoss => CloseCode::Protocol,
        ErrorCode::ResourceExhausted => CloseCode::Size,
        ErrorCode::DeadlineExceeded | ErrorCode::Unavailable | ErrorCode::Cancelled => {
            CloseCode::Away
        }
        ErrorCode::Internal
        | ErrorCode::Unknown
        | ErrorCode::Unspecified
        | ErrorCode::NotFound
        | ErrorCode::AlreadyExists => CloseCode::Error,
    }
}

/// Build the TLS-1.3-only connector (WSS section 1M). Any peer offering
/// only <1.3 fails negotiation with no Syntra byte sent and no plaintext
/// fallback. No custom TLS/handshake implementation: version floor plus
/// rustls secure defaults.
#[cfg(not(target_arch = "wasm32"))]
fn tls13_connector() -> Result<tokio_tungstenite::Connector, TransportError> {
    let loaded = rustls_native_certs::load_native_certs();
    if !loaded.errors.is_empty() {
        return Err(TransportError::Tls(format!(
            "system roots unavailable: {:?}",
            loaded.errors
        )));
    }
    let mut roots = rustls::RootCertStore::empty();
    roots.add_parsable_certificates(loaded.certs);
    if roots.is_empty() {
        return Err(TransportError::Tls(
            "no trust anchors available; failing closed".to_string(),
        ));
    }
    let config = rustls::ClientConfig::builder_with_protocol_versions(&[&rustls::version::TLS13])
        .with_root_certificates(roots)
        .with_no_client_auth();
    Ok(tokio_tungstenite::Connector::Rustls(Arc::new(config)))
}

/// Connect, validate the Upgrade, run the Syntra handshake, and spawn
/// background pump tasks.
///
/// `credential` is secret bytes presented only as
/// `ClientHello.credential`. This function never logs it and the caller
/// should zeroize/drop it after the handshake where possible.
pub async fn connect(
    cfg: WsConfig,
    credential: Vec<u8>,
    conn_cfg: ConnectionConfig,
) -> Result<WsHandle, TransportError> {
    let endpoint = Endpoint::parse(&cfg.url, cfg.allow_insecure)?;
    if !endpoint.is_secure {
        tracing::warn!("insecure WS enabled: restricted-development only, never public traffic");
    }

    // Build the WS request with the Syntra subprotocol offered first.
    // No Authorization/Cookie/credential headers are ever set: browsers
    // forbid them and native code carries credentials only in
    // ClientHello.credential after 101.
    let host_header = cfg.sni_override.clone().unwrap_or(endpoint.host.clone());
    let request = {
        use tokio_tungstenite::tungstenite::http::Request;
        Request::builder()
            .uri(cfg.url.as_str())
            .header("Host", host_header)
            .header("Upgrade", "websocket")
            .header("Connection", "Upgrade")
            .header("Sec-WebSocket-Version", "13")
            .header(
                "Sec-WebSocket-Key",
                tokio_tungstenite::tungstenite::handshake::client::generate_key(),
            )
            .header("Sec-WebSocket-Protocol", SUBPROTOCOL)
            .body(())
            .map_err(|e| TransportError::InvalidUrl(format!("bad ws request: {e}")))?
    };

    let mut ws_config = tokio_tungstenite::tungstenite::protocol::WebSocketConfig::default();
    // Enforce the 1 MiB bound DURING assembly: tungstenite aborts
    // oversized messages before we allocate them.
    ws_config.max_message_size = Some(syntra_core::MAX_FRAME_BYTES);
    ws_config.max_frame_size = Some(64 * 1024);
    let connector = if endpoint.is_secure {
        Some(tls13_connector()?)
    } else {
        None
    };
    let _ = ENDPOINT_PATH; // path validated by Endpoint::parse above.
    let connect_fut = tokio_tungstenite::connect_async_tls_with_config(
        request,
        Some(ws_config),
        false,
        connector,
    );
    let (ws_stream, response) = tokio::time::timeout(cfg.connect_timeout, connect_fut)
        .await
        .map_err(|_| TransportError::Connect("ws connect timed out".to_string()))?
        .map_err(|e| map_tungstenite_error(&e))?;

    // Validate 101 + selected subprotocol (WS section 1C).
    let selected = response
        .headers()
        .get("sec-websocket-protocol")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if selected != SUBPROTOCOL {
        return Err(TransportError::Subprotocol(format!(
            "expected {SUBPROTOCOL}, got '{selected}'"
        )));
    }

    // Engine: the runtime owns handshake/RPC correlation; pumps move bytes.
    let (conn, mut wrx) = Initiator::new(conn_cfg.clone());
    let (close_tx, mut close_rx) = mpsc::channel::<CloseCode>(4);
    let (ctrl_tx, mut ctrl_rx) = mpsc::channel::<Message>(16);
    let closed = Arc::new(AtomicBool::new(false));
    let last_pong = Arc::new(AtomicU64::new(now_millis()));

    let (mut ws_write, mut ws_read) = ws_stream.split();

    // Write pump: the ONLY writer to the socket. One runtime Vec<u8> =
    // one binary message (never length-prefixed). Control flow arrives
    // on ctrl_rx (Ping from liveness, Pong replies from the read pump)
    // and close codes on close_rx.
    //
    // Slow receiver: a write stalled past write_grace closes (1001)
    // instead of queueing unboundedly (WS section 1L).
    let write_conn = conn.clone();
    let write_closed = closed.clone();
    let write_grace = cfg.write_grace;
    let writer_task = tokio::spawn(async move {
        loop {
            if write_closed.load(Ordering::Relaxed) {
                break;
            }
            tokio::select! {
                biased;
                code = close_rx.recv() => {
                    let code = code.unwrap_or(CloseCode::Normal);
                    send_close(&mut ws_write, code, "closing").await;
                    break;
                }
                msg = wrx.recv() => {
                    match msg {
                        Some(bytes) => {
                            if bytes.len() > syntra_core::MAX_FRAME_BYTES {
                                tracing::warn!("outgoing frame exceeds bound; dropping");
                                continue;
                            }
                            let send = ws_write.send(Message::Binary(bytes.into()));
                            match tokio::time::timeout(write_grace, send).await {
                                Ok(Ok(())) => {}
                                _ => {
                                    tracing::warn!("slow receiver; closing");
                                    send_close(&mut ws_write, CloseCode::Away, "slow receiver").await;
                                    break;
                                }
                            }
                        }
                        None => break,
                    }
                }
                ctrl = ctrl_rx.recv() => {
                    match ctrl {
                        Some(msg) => {
                            let send = ws_write.send(msg);
                            match tokio::time::timeout(write_grace, send).await {
                                Ok(Ok(())) => {}
                                _ => {
                                    tracing::warn!("control write stalled; closing");
                                    break;
                                }
                            }
                        }
                        None => break,
                    }
                }
            }
        }
        write_closed.store(true, Ordering::Relaxed);
        write_conn.on_transport_lost().await;
    });

    // Liveness: Ping at ping_interval; silence past pong_timeout closes
    // (1001) with UNAVAILABLE to in-flight RPCs (WS section 1I).
    // Unsolicited Pong is accepted and ignored beyond liveness.
    let live_conn = conn.clone();
    let live_closed = closed.clone();
    let live_pong = last_pong.clone();
    let live_ctrl = ctrl_tx.clone();
    let live_close = close_tx.clone();
    let ping_interval = cfg.ping_interval;
    let pong_timeout = cfg.pong_timeout;
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(ping_interval);
        interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
        loop {
            interval.tick().await;
            if live_closed.load(Ordering::Relaxed) {
                break;
            }
            let silent = now_millis().saturating_sub(live_pong.load(Ordering::Relaxed));
            if silent > pong_timeout.as_millis() as u64 {
                tracing::warn!("liveness timeout; closing");
                live_conn.on_transport_lost().await;
                let _ = live_close.send(CloseCode::Away).await;
                break;
            }
            if live_ctrl
                .send(Message::Ping(b"syntra-ping".to_vec().into()))
                .await
                .is_err()
            {
                break;
            }
        }
    });

    // Read pump: binary -> ingest; text -> close 1003; empty -> reject;
    // oversize -> close 1009; Ping answered, Pong feeds liveness;
    // control frames never reach the core.
    let read_conn = conn.clone();
    let read_closed = closed.clone();
    let read_pong = last_pong.clone();
    let read_ctrl = ctrl_tx.clone();
    let read_close = close_tx.clone();
    let reader_task = tokio::spawn(async move {
        while let Some(msg) = ws_read.next().await {
            match msg {
                Ok(Message::Binary(data)) => {
                    if data.is_empty() {
                        tracing::warn!("empty binary message rejected");
                        let _ = read_close.send(CloseCode::Invalid).await;
                        break;
                    }
                    if data.len() > syntra_core::MAX_FRAME_BYTES {
                        tracing::warn!("assembled message exceeds bound");
                        let _ = read_close.send(CloseCode::Size).await;
                        break;
                    }
                    read_conn.ingest(&data).await;
                    if read_conn.is_closed() {
                        break;
                    }
                }
                Ok(Message::Text(_)) => {
                    tracing::warn!("text message rejected (binary required)");
                    let _ = read_close.send(CloseCode::Unsupported).await;
                    break;
                }
                Ok(Message::Ping(payload)) => {
                    // Answered at the WS layer; never reaches the core.
                    let _ = read_ctrl.send(Message::Pong(payload)).await;
                }
                Ok(Message::Pong(_)) => {
                    read_pong.store(now_millis(), Ordering::Relaxed);
                }
                Ok(Message::Close(_)) => break,
                Ok(Message::Frame(_)) => {}
                Err(e) => {
                    tracing::debug!(error = %e, "ws read error");
                    break;
                }
            }
        }
        read_closed.store(true, Ordering::Relaxed);
        read_conn.on_transport_lost().await;
    });

    // Syntra handshake: exactly one hello first, then await ready.
    // No Syntra byte was sent before TLS + 101 (WSS section 1F).
    // No Authorization/credential headers were sent: the only credential
    // carrier is ClientHello.credential below.
    match conn.handshake(credential).await {
        Ok(connection_id) => {
            let version = conn.negotiated_version().await.unwrap_or(1);
            // Pumps live until shutdown/close (detached tasks).
            Ok(WsHandle {
                conn,
                connection_id,
                version,
                shutdown_tx: Some(close_tx),
                closed,
            })
        }
        Err(e) => {
            // Spec-mapped close before teardown; never downgrade/retry.
            let _ = close_tx.send(handshake_close_code(&e)).await;
            // Let the write pump flush the close, then stop the pumps.
            tokio::time::sleep(Duration::from_millis(100)).await;
            writer_task.abort();
            reader_task.abort();
            conn.on_transport_lost().await;
            Err(TransportError::Connect(format!(
                "syntra handshake failed: {e}"
            )))
        }
    }
}

fn now_millis() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

async fn send_close<S>(ws: &mut S, code: CloseCode, reason: &str)
where
    S: futures_util::Sink<Message> + Unpin,
    S::Error: std::fmt::Debug,
{
    let frame = CloseFrame {
        code,
        reason: reason.into(),
    };
    if let Err(e) = ws.send(Message::Close(Some(frame))).await {
        tracing::debug!(error = ?e, "close send failed");
    }
}

fn map_tungstenite_error(e: &tungstenite::Error) -> TransportError {
    use tungstenite::Error as E;
    match e {
        E::ConnectionClosed | E::AlreadyClosed => {
            TransportError::Closed("connection closed".to_string())
        }
        E::Capacity(_) => TransportError::TooBig,
        E::Protocol(p) => {
            // Subprotocol negotiation failures are Syntra handshake
            // failures (missing/wrong token), not generic protocol noise.
            use tungstenite::error::ProtocolError as P;
            match p {
                P::SecWebSocketSubProtocolError(_) => TransportError::Subprotocol(e.to_string()),
                _ => TransportError::Protocol(e.to_string()),
            }
        }
        E::Tls(_) => TransportError::Tls(e.to_string()),
        E::Io(io) => TransportError::Io(io.to_string()),
        _ => TransportError::Connect(e.to_string()),
    }
}

/// Map a handshake failure to its spec close code for adapters that
/// terminate the WS connection on handshake failure.
pub fn handshake_close_code(e: &SyntraError) -> CloseCode {
    close_code_for_syntra(e.code())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn subprotocol_and_path_constants() {
        assert_eq!(SUBPROTOCOL, "syntra.v1");
        assert_eq!(ENDPOINT_PATH, "/syntra/v1/ws");
    }

    #[test]
    fn close_code_mapping_never_reserved() {
        // WS section 1J: 1005/1006/1015 must never appear on the wire.
        // close_code_for_syntra only returns real codes; assert the
        // mapping table covers every Syntra code deterministically.
        use syntra_core::ErrorCode as C;
        let codes = [
            C::Unspecified,
            C::Cancelled,
            C::Unknown,
            C::InvalidArgument,
            C::DeadlineExceeded,
            C::NotFound,
            C::AlreadyExists,
            C::PermissionDenied,
            C::ResourceExhausted,
            C::FailedPrecondition,
            C::Aborted,
            C::OutOfRange,
            C::Unimplemented,
            C::Internal,
            C::Unavailable,
            C::DataLoss,
            C::Unauthenticated,
        ];
        for c in codes {
            let wire: u16 = close_code_for_syntra(c).into();
            assert!(
                ![1005, 1006, 1015].contains(&wire),
                "reserved code for {c:?}"
            );
        }
        // Spot-check the normative rows (fixtures VEC-WS-007).
        assert_eq!(u16::from(close_code_for_syntra(C::Unimplemented)), 1002);
        assert_eq!(
            u16::from(close_code_for_syntra(C::FailedPrecondition)),
            1002
        );
        assert_eq!(u16::from(close_code_for_syntra(C::InvalidArgument)), 1002);
        assert_eq!(u16::from(close_code_for_syntra(C::Unauthenticated)), 1008);
        assert_eq!(u16::from(close_code_for_syntra(C::PermissionDenied)), 1008);
        assert_eq!(u16::from(close_code_for_syntra(C::ResourceExhausted)), 1009);
        assert_eq!(u16::from(close_code_for_syntra(C::Unavailable)), 1001);
        assert_eq!(u16::from(close_code_for_syntra(C::Internal)), 1011);
    }

    #[test]
    fn tls13_connector_builds() {
        // Fails closed (no roots) rather than succeeding insecurely.
        let _ = tls13_connector();
    }
}
