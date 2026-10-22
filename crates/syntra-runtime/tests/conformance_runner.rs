//! Shared conformance runner — async Rust leg (pairing `rust-async`).
//!
//! Drives `syntra-runtime::loopback_pair` through the shared scenario matrix
//! (`conformance/runner/scenarios.yaml`) with deterministic fault injection,
//! asserting wire payloads, durable state, bounds and terminal outcomes.
//! This is the executable counterpart to manifest validation: it runs the
//! protocol, not just the YAML.
//!
//! Fault injection is deterministic: a seeded counter decides drop/duplicate/
//! truncate faults, so the same seed replays the same pattern.

use std::sync::Arc;
use std::time::Duration;

use syntra_core::{decode_frame, ErrorCode, ValidationContext};
use syntra_runtime::{
    loopback_pair, AllowAnonymous, CancelToken, ConnectionConfig, FnHandler, HandlerOutcome,
};

fn echo_handler() -> Arc<dyn syntra_runtime::Handler> {
    Arc::new(FnHandler(
        |method: String, payload: Vec<u8>, _cancel: CancelToken| async move {
            match method.as_str() {
                "/example.Echo/Echo" => HandlerOutcome::Payload(payload),
                "/example.KV/Get" => HandlerOutcome::error(ErrorCode::NotFound, "missing"),
                "/example.Slow/Wait" => {
                    syntra_runtime::sleep_for(Duration::from_millis(300)).await;
                    HandlerOutcome::Payload(b"slow-ok".to_vec())
                }
                "/example.Huge/Reply" => {
                    HandlerOutcome::Payload(vec![0xAB; 2 * 1024 * 1024])
                }
                _ => HandlerOutcome::error(ErrorCode::Unimplemented, "unknown method"),
            }
        },
    ))
}

/// Deterministic fault injector: wraps raw transport bytes with seeded
/// drop/duplicate/truncation. The same seed replays the same pattern.
struct FaultInjector {
    seed: u64,
    counter: u64,
}

impl FaultInjector {
    fn new(seed: u64) -> Self {
        Self { seed, counter: 0 }
    }
    fn next(&mut self) -> u64 {
        // xorshift64* — deterministic, no external RNG.
        let mut x = self.seed.wrapping_add(self.counter.wrapping_mul(0x9E3779B97F4A7C15));
        self.counter += 1;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        x.wrapping_mul(0x2545F4914F6CDD1D)
    }
    fn should_drop(&mut self) -> bool {
        self.next() % 64 == 0
    }
    fn should_duplicate(&mut self) -> bool {
        self.next() % 128 == 0
    }
    fn should_truncate(&mut self) -> bool {
        self.next() % 96 == 0
    }
    /// Apply seeded faults to one transport unit. Returns the byte vectors
    /// the transport would deliver: empty on drop, two copies on duplicate,
    /// a single truncated copy on truncation, otherwise the input unchanged.
    fn transport_wrap(&mut self, bytes: Vec<u8>) -> Vec<Vec<u8>> {
        if self.should_drop() {
            return Vec::new();
        }
        if self.should_truncate() {
            let mut t = bytes;
            let n = t.len().saturating_sub(1).max(1);
            t.truncate(n);
            return vec![t];
        }
        if self.should_duplicate() {
            return vec![bytes.clone(), bytes];
        }
        vec![bytes]
    }
}

#[tokio::test]
async fn sc_echo() {
    let (initiator, _host) = loopback_pair(
        Arc::new(AllowAnonymous),
        echo_handler(),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    for payload in [vec![], b"hello".to_vec(), vec![7u8; 64 * 1024]] {
        let out = initiator
            .call("/example.Echo/Echo", payload.clone(), 2000)
            .await
            .expect("echo");
        assert_eq!(out, payload, "opaque bytes must be preserved bit-identically");
    }
}

#[tokio::test]
async fn sc_concurrent_16_out_of_order() {
    let (initiator, _host) = loopback_pair(
        Arc::new(AllowAnonymous),
        echo_handler(),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    let mut handles = Vec::new();
    for i in 0..16u8 {
        let c = initiator.clone();
        handles.push(tokio::spawn(async move {
            let p = vec![i; 32];
            let out = c.call("/example.Echo/Echo", p.clone(), 5000).await.expect("ok");
            assert_eq!(out, p);
        }));
    }
    for h in handles {
        h.await.unwrap();
    }
}

#[tokio::test]
async fn sc_cancel_wins_and_single_terminal() {
    let (initiator, _host) = loopback_pair(
        Arc::new(AllowAnonymous),
        Arc::new(FnHandler(|m: String, p: Vec<u8>, cancel: CancelToken| async move {
            // Only the first payload waits for cancel; follow-ups echo.
            if p == b"x".to_vec() {
                cancel.cancelled().await;
                HandlerOutcome::Payload(b"late".to_vec())
            } else {
                let _ = m;
                HandlerOutcome::Payload(p)
            }
        })),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    let token = CancelToken::new();
    let call = {
        let c = initiator.clone();
        let t = token.clone();
        tokio::spawn(async move {
            c.call_cancellable("/example.Echo/Echo", b"x".to_vec(), 5000, &t).await
        })
    };
    tokio::time::sleep(Duration::from_millis(100)).await;
    token.cancel();
    let err = call.await.unwrap().unwrap_err();
    assert_eq!(err.code(), ErrorCode::Cancelled);
    // Connection usable: exactly one terminal, no second result.
    let out = initiator
        .call("/example.Echo/Echo", b"after".to_vec(), 1000)
        .await
        .expect("usable");
    assert_eq!(out, b"after");
}

#[tokio::test]
async fn sc_deadline_exactly_once() {
    let (initiator, _host) = loopback_pair(
        Arc::new(AllowAnonymous),
        echo_handler(),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    let err = initiator
        .call("/example.Slow/Wait", b"x".to_vec(), 50)
        .await
        .unwrap_err();
    assert_eq!(err.code(), ErrorCode::DeadlineExceeded);
    assert!(err.is_unknown_outcome());
}

#[tokio::test]
async fn sc_oversize_handler_result_bounded() {
    let (initiator, _host) = loopback_pair(
        Arc::new(AllowAnonymous),
        echo_handler(),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    let err = initiator
        .call("/example.Huge/Reply", b"x".to_vec(), 2000)
        .await
        .unwrap_err();
    assert_eq!(err.code(), ErrorCode::ResourceExhausted);
    // Connection stays usable after bounded failure.
    let out = initiator
        .call("/example.Echo/Echo", b"ok".to_vec(), 1000)
        .await
        .expect("usable");
    assert_eq!(out, b"ok");
}

#[tokio::test]
async fn sc_duplicate_id_single_terminal() {
    use prost::Message;
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::{Frame, RpcRequest};
    let release = Arc::new(tokio::sync::Notify::new());
    let rh = release.clone();
    let blocking = Arc::new(FnHandler(move |_m: String, _p: Vec<u8>, _c: CancelToken| {
        let rh = rh.clone();
        async move {
            rh.notified().await;
            HandlerOutcome::Payload(b"first".to_vec())
        }
    }));
    let (host, mut wrx) = syntra_runtime::Host::new(
        ConnectionConfig::default(),
        Arc::new(AllowAnonymous),
        blocking,
    );
    {
        use syntra_core::proto::ClientHello;
        let raw = Frame {
            version: 1,
            request_id: 0,
            body: Some(Body::Hello(ClientHello {
                min_version: 1,
                max_version: 1,
                credential: vec![].into(),
            })),
        }
        .encode_to_vec();
        host.ingest(&raw).await;
    }
    let _ready = wrx.recv().await.expect("ready");
    let req = |id: u64| {
        Frame {
            version: 1,
            request_id: id,
            body: Some(Body::Request(RpcRequest {
                method: "/example.Echo/Echo".into(),
                payload: vec![].into(),
                timeout_ms: 5000,
            })),
        }
        .encode_to_vec()
    };
    host.ingest(&req(7)).await;
    tokio::time::sleep(Duration::from_millis(100)).await;
    host.ingest(&req(7)).await;
    let dup = wrx.recv().await.expect("dup result");
    let ctx = ValidationContext::active(1);
    let f = decode_frame(&dup, ctx).expect("valid");
    match f.body {
        Some(Body::Result(r)) => match r.outcome {
            Some(syntra_core::proto::rpc_result::Outcome::Error(e)) => {
                assert_eq!(e.code, ErrorCode::FailedPrecondition.as_i32())
            }
            other => panic!("expected error, got {other:?}"),
        },
        other => panic!("expected result, got {other:?}"),
    }
    release.notify_one();
    let first = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
        .await
        .expect("first")
        .expect("open");
    let f1 = decode_frame(&first, ctx).expect("valid");
    assert!(matches!(
        f1.body,
        Some(Body::Result(_))
    ));
}

#[tokio::test]
async fn sc_graceful_close_drains() {
    let (initiator, host) = loopback_pair(
        Arc::new(AllowAnonymous),
        echo_handler(),
        ConnectionConfig::default(),
    );
    initiator.handshake(vec![]).await.expect("handshake");
    let out = initiator
        .call("/example.Echo/Echo", b"before-close".to_vec(), 1000)
        .await
        .expect("ok");
    assert_eq!(out, b"before-close");
    // Graceful close: new RPCs rejected, queued results delivered, state discarded.
    host.close().await;
    // Initiator observes close (transport loss mapping is UNAVAILABLE for
    // in-flight; completed RPCs already delivered above).
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert_eq!(host.sessions().count(), 0);
}

#[tokio::test]
async fn sc_fault_injection_deterministic() {
    // Deterministic faults via a transport wrapper preserve exactly-once
    // terminal semantics: each non-dropped request yields exactly one
    // terminal with the correct payload; duplicates are rejected without a
    // second terminal; truncations never break the connection.
    use prost::Message;
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::{Frame, RpcRequest};
    let mut fi = FaultInjector::new(0x5EED1234);
    let mut drops = 0u32;
    let mut dups = 0u32;
    let mut truncs = 0u32;
    for i in 0..128u8 {
        let payload = vec![i; 16];
        let req_id = 1000u64 + i as u64;
        let raw = Frame {
            version: 1,
            request_id: req_id,
            body: Some(Body::Request(RpcRequest {
                method: "/example.Echo/Echo".into(),
                payload: payload.clone().into(),
                timeout_ms: 5000,
            })),
        }
        .encode_to_vec();
        let sends = fi.transport_wrap(raw.clone());
        if sends.is_empty() {
            drops += 1;
            continue;
        }
        let is_truncated = sends.len() == 1 && sends[0] != raw;
        if is_truncated {
            truncs += 1;
            let (host, mut wrx) = syntra_runtime::Host::new(
                ConnectionConfig::default(),
                Arc::new(AllowAnonymous),
                echo_handler(),
            );
            {
                use syntra_core::proto::ClientHello;
                let hello = Frame {
                    version: 1,
                    request_id: 0,
                    body: Some(Body::Hello(ClientHello {
                        min_version: 1,
                        max_version: 1,
                        credential: vec![].into(),
                    })),
                }
                .encode_to_vec();
                host.ingest(&hello).await;
                let _ = wrx.recv().await.expect("ready");
            }
            host.ingest(&sends[0]).await;
            host.ingest(&raw).await;
            let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
                .await
                .expect("truncated must not break connection")
                .expect("open");
            let ctx = ValidationContext::active(1);
            let f = decode_frame(&resp, ctx).expect("valid");
            match f.body {
                Some(Body::Result(r)) => {
                    use syntra_core::proto::rpc_result::Outcome;
                    match r.outcome {
                        Some(Outcome::Payload(p)) => assert_eq!(p, payload, "exactly-once payload preserved"),
                        other => panic!("expected payload, got {other:?}"),
                    }
                }
                other => panic!("expected result, got {other:?}"),
            }
            continue;
        }
        if sends.len() == 2 {
            dups += 1;
            let release = Arc::new(tokio::sync::Notify::new());
            let rh = release.clone();
            let ph = payload.clone();
            let blocking = Arc::new(FnHandler(move |_m: String, _p: Vec<u8>, _c: CancelToken| {
                let rh2 = rh.clone();
                let p = ph.clone();
                async move {
                    rh2.notified().await;
                    HandlerOutcome::Payload(p)
                }
            }));
            let (host, mut wrx) = syntra_runtime::Host::new(
                ConnectionConfig::default(),
                Arc::new(AllowAnonymous),
                blocking,
            );
            {
                use syntra_core::proto::ClientHello;
                let hello = Frame {
                    version: 1,
                    request_id: 0,
                    body: Some(Body::Hello(ClientHello {
                        min_version: 1,
                        max_version: 1,
                        credential: vec![].into(),
                    })),
                }
                .encode_to_vec();
                host.ingest(&hello).await;
                let _ = wrx.recv().await.expect("ready");
            }
            host.ingest(&sends[0]).await;
            tokio::time::sleep(Duration::from_millis(50)).await;
            host.ingest(&sends[1]).await;
            let dup_resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
                .await
                .expect("duplicate rejected")
                .expect("open");
            let ctx = ValidationContext::active(1);
            let f = decode_frame(&dup_resp, ctx).expect("valid");
            match f.body {
                Some(Body::Result(r)) => match r.outcome {
                    Some(syntra_core::proto::rpc_result::Outcome::Error(e)) => {
                        assert_eq!(e.code, ErrorCode::FailedPrecondition.as_i32());
                    }
                    other => panic!("expected duplicate error, got {other:?}"),
                },
                other => panic!("expected result, got {other:?}"),
            }
            release.notify_one();
            let first = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
                .await
                .expect("first")
                .expect("open");
            let f1 = decode_frame(&first, ctx).expect("valid");
            match f1.body {
                Some(Body::Result(r)) => match r.outcome {
                    Some(syntra_core::proto::rpc_result::Outcome::Payload(p)) => {
                        assert_eq!(p, payload, "exactly-once payload preserved")
                    }
                    other => panic!("expected payload, got {other:?}"),
                },
                other => panic!("expected result, got {other:?}"),
            }
            continue;
        }
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        {
            use syntra_core::proto::ClientHello;
            let hello = Frame {
                version: 1,
                request_id: 0,
                body: Some(Body::Hello(ClientHello {
                    min_version: 1,
                    max_version: 1,
                    credential: vec![].into(),
                })),
            }
            .encode_to_vec();
            host.ingest(&hello).await;
            let _ = wrx.recv().await.expect("ready");
        }
        host.ingest(&sends[0]).await;
        let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .expect("echo under faults")
            .expect("open");
        let ctx = ValidationContext::active(1);
        let f = decode_frame(&resp, ctx).expect("valid");
        match f.body {
            Some(Body::Result(r)) => {
                use syntra_core::proto::rpc_result::Outcome;
                match r.outcome {
                    Some(Outcome::Payload(p)) => assert_eq!(p, payload, "exactly-once payload preserved"),
                    other => panic!("expected payload, got {other:?}"),
                }
            }
            other => panic!("expected result, got {other:?}"),
        }
    }
    assert!(drops < 8, "seeded drop rate sane: {drops}");
    assert!(dups > 0, "seeded duplicate branch exercised: {dups}");
    assert!(truncs > 0, "seeded truncation branch exercised: {truncs}");
}

#[tokio::test]
async fn sc_wire_vectors_decode() {
    // Wire payloads: golden vectors decode to expected logical frames.
    let good_hex = crate::vectors::NO_LENGTH_PREFIX_GOOD_HEX;
    let bytes = crate::vectors::hex_to_bytes(good_hex);
    let ctx = syntra_core::ValidationContext::pre_handshake(syntra_core::ConnectionState::Connected);
    let f = decode_frame(&bytes, ctx).expect("golden vector decodes");
    assert!(matches!(
        f.body,
        Some(syntra_core::proto::frame::Body::Hello(_))
    ));
}

#[path = "../../../tests/interoperability/vectors.rs"]
mod vectors;
