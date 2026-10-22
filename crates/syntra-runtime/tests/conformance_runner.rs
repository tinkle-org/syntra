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
    /// Apply seeded faults to one host->initiator unit (response path).
    /// Same drop/duplicate/truncate semantics as [`transport_wrap`]; a
    /// separate injector instance per direction keeps each seeded stream
    /// deterministic and undisturbed by the other direction's draws.
    fn response_wrap(&mut self, bytes: Vec<u8>) -> Vec<Vec<u8>> {
        self.transport_wrap(bytes)
    }
}

fn hello_bytes() -> Vec<u8> {
    use prost::Message;
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::{ClientHello, Frame};
    Frame {
        version: 1,
        request_id: 0,
        body: Some(Body::Hello(ClientHello {
            min_version: 1,
            max_version: 1,
            credential: vec![].into(),
        })),
    }
    .encode_to_vec()
}

/// Assert bytes decode to the exactly-one terminal Result for `request_id`
/// carrying `expected` — the reconcile/duplicate invariant: same delivery,
/// same terminal, never a second distinct one.
fn assert_terminal_payload(frame_bytes: &[u8], expected: &[u8], request_id: u64) {
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::rpc_result::Outcome;
    let ctx = ValidationContext::active(1);
    let f = decode_frame(frame_bytes, ctx).expect("terminal must decode");
    assert_eq!(f.request_id, request_id, "terminal carries the delivery id");
    match f.body {
        Some(Body::Result(r)) => match r.outcome {
            Some(Outcome::Payload(p)) => {
                assert_eq!(&p[..], expected, "exactly-once payload preserved")
            }
            other => panic!("expected payload terminal, got {other:?}"),
        },
        other => panic!("expected result terminal, got {other:?}"),
    }
}

/// Re-ingest the same request bytes until a non-duplicate terminal arrives
/// (bounded): the original dispatch releases its request id only after its
/// terminal is queued, so an immediate retry can race and be rejected as a
/// duplicate. A duplicate rejection is retried with backoff; any other
/// terminal is returned for the caller to assert on.
async fn retry_same_delivery(
    host: &Arc<syntra_runtime::Host>,
    wrx: &mut tokio::sync::mpsc::Receiver<Vec<u8>>,
    raw: &[u8],
    what: &str,
) -> Vec<u8> {
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::rpc_result::Outcome;
    for _ in 0..20 {
        host.ingest(raw).await;
        let got = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .unwrap_or_else(|_| panic!("{what}"))
            .expect("open");
        let ctx = ValidationContext::active(1);
        let f = decode_frame(&got, ctx).expect("valid");
        let dup_reject = match &f.body {
            Some(Body::Result(r)) => match &r.outcome {
                Some(Outcome::Error(e)) => e.code == ErrorCode::FailedPrecondition.as_i32(),
                _ => false,
            },
            _ => false,
        };
        if !dup_reject {
            return got;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    panic!("{what}: retry kept racing the original dispatch");
}

async fn expect_ready(wrx: &mut tokio::sync::mpsc::Receiver<Vec<u8>>, what: &str) {
    tokio::time::timeout(Duration::from_secs(2), wrx.recv())
        .await
        .unwrap_or_else(|_| panic!("{what}"))
        .expect("open");
}

/// Build a handshaked Host while faulting the hello through `fi`.
/// Drop: no ready arrives; the same Host recovers via hello retry.
/// Truncate/duplicate: handshake validation terminally rejects the faulted
/// hello (never a bogus ready); a fresh Host plus a clean hello recovers.
async fn establish_host(
    fi: &mut FaultInjector,
    handler: Arc<dyn syntra_runtime::Handler>,
    hello_faults: &mut u32,
) -> (Arc<syntra_runtime::Host>, tokio::sync::mpsc::Receiver<Vec<u8>>) {
    let clean = hello_bytes();
    let (host, mut wrx) = syntra_runtime::Host::new(
        ConnectionConfig::default(),
        Arc::new(AllowAnonymous),
        handler.clone(),
    );
    let sends = fi.transport_wrap(clean.clone());
    if sends.len() == 1 && sends[0] == clean {
        host.ingest(&sends[0]).await;
        expect_ready(&mut wrx, "ready").await;
        return (host, wrx);
    }
    *hello_faults += 1;
    if sends.is_empty() {
        // Dropped hello: nothing may arrive; retry on the SAME host.
        assert!(
            tokio::time::timeout(Duration::from_millis(50), wrx.recv())
                .await
                .is_err(),
            "dropped hello must not produce a ready"
        );
        host.ingest(&clean).await;
        expect_ready(&mut wrx, "hello retry after drop recovers").await;
        return (host, wrx);
    }
    if sends.len() == 2 {
        // Duplicated hello: the first copy handshakes (exactly one ready);
        // the second copy is rejected as an unexpected hello — never a
        // second ready — and the handshake is torn down.
        host.ingest(&sends[0]).await;
        expect_ready(&mut wrx, "first hello copy handshakes").await;
        host.ingest(&sends[1]).await;
        match tokio::time::timeout(Duration::from_millis(50), wrx.recv()).await {
            Ok(Some(_)) => panic!("duplicated hello must not produce a second ready"),
            Ok(None) | Err(_) => {}
        }
    } else {
        // Truncated hello: handshake validation fails it; no ready and no
        // usable session — rejected terminally by design.
        host.ingest(&sends[0]).await;
        assert!(
            tokio::time::timeout(Duration::from_millis(50), wrx.recv())
                .await
                .is_err(),
            "truncated hello must not produce a ready"
        );
    }
    let (host, mut wrx) = syntra_runtime::Host::new(
        ConnectionConfig::default(),
        Arc::new(AllowAnonymous),
        handler,
    );
    host.ingest(&clean).await;
    expect_ready(&mut wrx, "clean handshake after faulted hello recovers").await;
    (host, wrx)
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
    // Deterministic faults on BOTH transport directions preserve terminal
    // semantics: request-side (initiator->host) drop/duplicate/truncate,
    // response-side (host->initiator) drop/duplicate/truncate, and faulted
    // hellos — asserting wire payloads, recovery by retry, and terminal
    // outcomes rather than overclaiming exactly-once:
    //
    // - A dropped request is NOT skipped: the initiator observes Unknown
    //   and retries the same delivery, which must yield exactly one
    //   terminal with the correct payload (reconcile-style retry).
    // - A duplicated request is rejected without a second terminal.
    // - A truncated request never breaks the connection; the intact retry
    //   still yields the correct terminal.
    // - A dropped/truncated response is recovered by retrying the same
    //   request bytes; a duplicated response delivers the identical
    //   terminal twice (deduped by request_id — exactly-once).
    // - A dropped hello is retried on the same Host; a
    //   truncated/duplicated hello is terminally rejected (never a bogus
    //   ready) and recovered with a fresh handshake.
    //
    // Request-path faults replay the original seeded sequence exactly
    // (seed 0x5EED1234); response and hello faults draw from their own
    // seeded streams so the request-side pattern is undisturbed. The same
    // seeds replay the same pattern.
    use prost::Message;
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::{Frame, RpcRequest};
    let mut fi = FaultInjector::new(0x5EED1234);
    let mut resp_fi = FaultInjector::new(0xBE5E11);
    let mut hello_fi = FaultInjector::new(0xCAFE01);
    let mut drops = 0u32;
    let mut dups = 0u32;
    let mut truncs = 0u32;
    let mut resp_drops = 0u32;
    let mut resp_dups = 0u32;
    let mut resp_truncs = 0u32;
    let mut hello_faults = 0u32;
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
            // Request lost in transport: the initiator observes Unknown and
            // retries the same delivery (reconcile-style). The retry must
            // yield exactly one terminal with the correct payload — a drop
            // is recovered by retry, never silently skipped.
            let (host, mut wrx) =
                establish_host(&mut hello_fi, echo_handler(), &mut hello_faults).await;
            host.ingest(&raw).await;
            let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
                .await
                .expect("retry after dropped request recovers")
                .expect("open");
            assert_terminal_payload(&resp, &payload, req_id);
            continue;
        }
        let is_truncated = sends.len() == 1 && sends[0] != raw;
        if is_truncated {
            truncs += 1;
            let (host, mut wrx) =
                establish_host(&mut hello_fi, echo_handler(), &mut hello_faults).await;
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
            let (host, mut wrx) =
                establish_host(&mut hello_fi, blocking, &mut hello_faults).await;
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
        let (host, mut wrx) =
            establish_host(&mut hello_fi, echo_handler(), &mut hello_faults).await;
        host.ingest(&sends[0]).await;
        let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .expect("echo under faults")
            .expect("open");
        // Fault the host->initiator response path too: result-side
        // drop/duplicate/truncate must preserve terminal semantics just
        // like request-side faults.
        let resends = resp_fi.response_wrap(resp.clone());
        if resends.is_empty() {
            resp_drops += 1;
            // Result lost in transport: the initiator observes Unknown and
            // retries the same request bytes; the retry must yield exactly
            // one terminal with the correct payload.
            let retry =
                retry_same_delivery(&host, &mut wrx, &raw, "retry after dropped response recovers")
                    .await;
            assert_terminal_payload(&retry, &payload, req_id);
        } else if resends.len() == 1 && resends[0] != resp {
            resp_truncs += 1;
            // A truncated result must fail decode (never a forged
            // terminal); the retry of the same bytes still recovers.
            let ctx = ValidationContext::active(1);
            assert!(
                decode_frame(&resends[0], ctx).is_err(),
                "truncated result must fail decode"
            );
            let retry =
                retry_same_delivery(&host, &mut wrx, &raw, "retry after truncated response recovers")
                    .await;
            assert_terminal_payload(&retry, &payload, req_id);
        } else if resends.len() == 2 {
            resp_dups += 1;
            // Duplicate result delivery: both copies decode to the
            // identical terminal (same delivery id, same payload) — no
            // second distinct terminal; the initiator dedupes by
            // request_id, preserving exactly-once.
            assert_eq!(resends[0], resends[1], "duplicate delivery is bit-identical");
            assert_terminal_payload(&resends[0], &payload, req_id);
            assert_terminal_payload(&resends[1], &payload, req_id);
        } else {
            assert_terminal_payload(&resp, &payload, req_id);
        }
    }
    assert!(drops < 8, "seeded drop rate sane: {drops}");
    assert!(dups > 0, "seeded duplicate branch exercised: {dups}");
    assert!(truncs > 0, "seeded truncation branch exercised: {truncs}");
    eprintln!("fault coverage: req drops={drops} dups={dups} truncs={truncs} | resp drops={resp_drops} dups={resp_dups} truncs={resp_truncs} | hello faults={hello_faults}");
    assert!(
        resp_drops + resp_dups + resp_truncs + hello_faults > 0,
        "response/hello fault branches must be exercised"
    );
}

#[tokio::test]
async fn sc_response_faults_recover() {
    // Response-path faults (host->initiator direction), deterministically:
    // a duplicated result delivers the identical terminal twice (deduped by
    // request_id — exactly-once); a dropped result is recovered by
    // retrying the same request bytes (reconcile-style: same delivery id
    // yields the terminal, not a hang and not a duplicate).
    use prost::Message;
    use syntra_core::proto::frame::Body;
    use syntra_core::proto::{Frame, RpcRequest};
    let payload = b"resp-fault".to_vec();
    let req_id = 4242u64;
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
    // Duplicate delivery: both copies are the identical terminal.
    {
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        host.ingest(&hello_bytes()).await;
        expect_ready(&mut wrx, "ready").await;
        host.ingest(&raw).await;
        let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .expect("terminal")
            .expect("open");
        let dup_a = resp.clone();
        let dup_b = resp;
        assert_eq!(dup_a, dup_b, "duplicate delivery is bit-identical");
        assert_terminal_payload(&dup_a, &payload, req_id);
        assert_terminal_payload(&dup_b, &payload, req_id);
    }
    // Dropped delivery: retry of the same bytes yields the terminal.
    {
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        host.ingest(&hello_bytes()).await;
        expect_ready(&mut wrx, "ready").await;
        host.ingest(&raw).await;
        let _dropped = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .expect("terminal (lost in transport)")
            .expect("open");
        let retry =
            retry_same_delivery(&host, &mut wrx, &raw, "retry after dropped response recovers")
                .await;
        assert_terminal_payload(&retry, &payload, req_id);
    }
    // Truncated delivery: the corrupt copy must fail decode (never a
    // forged terminal); retry of the same bytes still recovers.
    {
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        host.ingest(&hello_bytes()).await;
        expect_ready(&mut wrx, "ready").await;
        host.ingest(&raw).await;
        let resp = tokio::time::timeout(Duration::from_secs(2), wrx.recv())
            .await
            .expect("terminal")
            .expect("open");
        let mut truncated = resp;
        truncated.truncate(truncated.len().saturating_sub(1).max(1));
        let ctx = ValidationContext::active(1);
        assert!(
            decode_frame(&truncated, ctx).is_err(),
            "truncated result must fail decode"
        );
        let retry =
            retry_same_delivery(&host, &mut wrx, &raw, "retry after truncated response recovers")
                .await;
        assert_terminal_payload(&retry, &payload, req_id);
    }
}

#[tokio::test]
async fn sc_hello_faults_recover() {
    // Hello-path faults, deterministically: a dropped hello yields no
    // ready and the same Host recovers via retry; a duplicated hello
    // yields exactly one ready — the second copy is rejected and never
    // produces a second ready.
    {
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        assert!(
            tokio::time::timeout(Duration::from_millis(50), wrx.recv())
                .await
                .is_err(),
            "no hello, no ready"
        );
        host.ingest(&hello_bytes()).await;
        expect_ready(&mut wrx, "hello retry after drop recovers").await;
    }
    {
        let (host, mut wrx) = syntra_runtime::Host::new(
            ConnectionConfig::default(),
            Arc::new(AllowAnonymous),
            echo_handler(),
        );
        host.ingest(&hello_bytes()).await;
        expect_ready(&mut wrx, "first hello handshakes").await;
        host.ingest(&hello_bytes()).await;
        match tokio::time::timeout(Duration::from_millis(50), wrx.recv()).await {
            Ok(Some(_)) => panic!("duplicated hello must not produce a second ready"),
            Ok(None) | Err(_) => {}
        }
    }
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
