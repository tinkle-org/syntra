//! Browser-client API tests.
//!
//! On `wasm32-unknown-unknown` these exports drive the browser
//! `WebSocket`; on native targets `connect` wires the in-memory loopback
//! with neutral fixtures so the registry/call/notify/close contract is
//! testable without a browser.
//!
//! Note: `JsValue` error construction aborts natively by
//! `wasm-bindgen` design, so rejection-path tests are `wasm32`-only. The
//! same logic is covered natively through `syntra-runtime` and
//! `syntra-ffi` (FFI maps every error variant without `JsValue`).

#[tokio::test]
async fn connect_call_close_round_trip() {
    // The registry is process-global and tests run in parallel, so this
    // test asserts per-id behavior only (no global counts).
    let id = syntra_web::connect("loopback://test".to_string(), vec![])
        .await
        .expect("connect");
    let out = syntra_web::call(id, "/example.Echo/Echo".to_string(), b"web".to_vec(), 2000)
        .await
        .expect("call");
    assert_eq!(out, b"web");
    assert!(syntra_web::close(id).await);
    // Second close reports unknown (no JsValue involved).
    assert!(!syntra_web::close(id).await);
    assert!(!syntra_web::close(424242).await);
}

#[tokio::test]
async fn notify_poll_timeout_is_none() {
    let id = syntra_web::connect("loopback://test".to_string(), vec![])
        .await
        .expect("connect");
    // No notifications sent: bounded wait resolves None.
    let got = syntra_web::poll_notify(id, 100).await.expect("poll");
    assert!(got.is_none());
    assert!(syntra_web::close(id).await);
}

// Rejection paths construct `JsValue`, which aborts natively; they run
// on wasm32 only. Native equivalents live in syntra-ffi tests.
#[cfg(target_arch = "wasm32")]
#[tokio::test]
async fn unknown_method_rejects_without_closing() {
    let id = syntra_web::connect("loopback://test".to_string(), vec![])
        .await
        .expect("connect");
    syntra_web::call(id, "/example.Nope/Missing".to_string(), vec![], 2000)
        .await
        .expect_err("unknown method");
    let out = syntra_web::call(id, "/example.Echo/Echo".to_string(), b"ok".to_vec(), 2000)
        .await
        .expect("usable");
    assert_eq!(out, b"ok");
    assert!(syntra_web::close(id).await);
}

#[cfg(target_arch = "wasm32")]
#[tokio::test]
async fn unknown_client_rejects() {
    syntra_web::call(424242, "/example.Echo/Echo".to_string(), vec![], 500)
        .await
        .expect_err("unknown client");
    syntra_web::poll_notify(424242, 50)
        .await
        .expect_err("unknown client");
}
