//! `syntra-core`: transport-independent Syntra v1 protocol mechanics.
//!
//! This crate owns envelope codec, validation (`SNTR-WIRE-*`,
//! `SNTR-SER-*`), version negotiation, the six-state connection machine
//! (`SNTR-HS-001`), request-id allocation, the bounded pending-RPC table,
//! method-shape validation, and typed errors. It never touches the
//! network and never interprets application payloads.
//!
//! Wire sources: committed prost output of `proto/syntra/v1/*.proto`
//! (see `buf.gen.yaml`; pins in `specifications/schema/generation.md`).
//! Generated types are data structures only; all behavior here is
//! implemented against `specifications/`.
//!
//! Open questions this crate does NOT invent bindings for (see
//! `SESSION-OPEN-QUESTIONS.md` and `rfcs/0002-auth-session-lifecycle.md`):
//! typed pre-`ACTIVE` error carrier (B1), pre-`ACTIVE` notification conflict
//! (B2), stale `request_id` reuse (B3), payload-vs-envelope size (B8).
//! Where a conflict exists the enforced rule is documented on the item.

/// Committed prost output (see `buf.gen.yaml`). Do not hand-edit; this
/// file is byte-pinned to a pinned `buf generate` run (drift-checked).
/// It is pulled in via `include!` (rather than `#[path] mod`) so stable
/// `rustfmt` leaves the pinned bytes untouched.
pub mod proto {
    include!("generated/syntra.v1.rs");
}

pub mod codec;
pub mod error;
pub mod frame;
pub mod handshake;
pub mod rpc;
pub mod state;

pub use codec::{decode_frame, encode_frame, MAX_FRAME_BYTES};
pub use error::{ErrorCode, RpcError, SyntraError};
pub use frame::{validate_frame, FrameKind, ValidationContext, MAX_DECODE_DEPTH};
pub use handshake::{
    build_hello, negotiate_version, validate_connection_id, validate_hello_range,
    HANDSHAKE_TIMEOUT_DEFAULT, MAX_CREDENTIAL_BYTES, MAX_VERSION, MIN_VERSION,
};
pub use proto::{Cancel, ClientHello, Frame, Notification, RpcRequest, RpcResult, ServerReady};
pub use rpc::{validate_method, PendingOutcome, PendingTable, RequestIdAllocator};
pub use state::{ConnectionState, StateEvent};
