//! Quarantined native C ABI test fixture. **No production FFI is available.**
//!
//! Default builds export no Syntra C ABI symbols and contain no fixture host.
//! The explicit, non-default `test-fixture` Cargo feature enables the legacy
//! blocking loopback ABI for native tests only (including `--all-features`).
//! Do not ship or use that feature as a production client or server. It has
//! no transport attachment API: `syntra_open` always creates an in-process
//! echo/get-put fixture, even when given a token. ABI compatibility checks
//! concern this fixture's layout only, not production transport support.
//!
//! All WASM targets are rejected at compile time. A blocking browser ABI
//! cannot drive browser event-loop futures, and the former current-thread
//! runtime had no working Tokio timer driver. Enabling timers alone is not
//! a browser ABI fix. No replacement asynchronous ABI is defined here.
//!
//! Native fixture test command:
//! `cargo test -p syntra-ffi --features test-fixture`.
//! The matching opt-in C header is `include/syntra.h`. Build/target regression
//! checks: `python3 crates/syntra-ffi/tests/build_contract.py` from the workspace.
//!
//! A future production FFI must expose a usable transport boundary without
//! moving host policy into Syntra. Authentication, authorization, method
//! schemas, domain behavior, replay storage, presence, and durable data remain
//! host-owned. Externally reachable production traffic requires TLS; this
//! loopback fixture provides no peer-verification or confidentiality claim.
//!
//! # Caller obligations (fixture only)
//! All non-null pointers must be valid, aligned, and live for the call; input
//! strings must be NUL-terminated; byte buffers must cover their stated lengths.
//! Outputs must be writable and must not overlap one another or any input.
//! Return buffers must be freed exactly once with `syntra_free` and their
//! original length. Unwinding-panic containment does not make invalid pointers,
//! allocation failure, or panic=abort safe. Blocking functions must not be
//! called from a Tokio asynchronous execution context.

#[cfg(target_family = "wasm")]
compile_error!("syntra-ffi does not support WASM: the blocking fixture ABI is native-only; no production or browser ABI is available");

#[cfg(all(feature = "test-fixture", not(target_family = "wasm")))]
mod fixture;

#[cfg(all(feature = "test-fixture", not(target_family = "wasm")))]
pub use fixture::*;
