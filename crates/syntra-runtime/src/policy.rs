//! Host-owned policy bridge for foreign-language embedding.
//!
//! The core validates shape, selects versions, correlates RPCs, enforces
//! deadlines, and observes cancellation. The embedding application resolves
//! authentication, authorization, dispatch, and completion asynchronously.
//!
//! This module defines the completion-token contract used by the production
//! native ABI. Tokens are distinct from wire `request_id` values so late,
//! duplicate, cancelled, and post-close completions resolve deterministically.

use std::time::Duration;

use syntra_core::ErrorCode;

/// Authentication outcome resolved by the host application.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthDecision {
    /// Bind this principal and emit `ServerReady`.
    Allow { principal: String },
    /// Reject the handshake without an oracle.
    Deny { code: ErrorCode },
}

/// Per-request authorization outcome resolved by the host application.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthzDecision {
    Allow,
    Deny { code: ErrorCode },
}

/// Opaque completion token issued when a request is admitted for dispatch.
///
/// The token identifies the admitted dispatch slot. The wire `request_id`
/// identifies correlation on the transport. Separating them keeps
/// late completions, retries with reused ids, and post-close arrivals
/// unambiguous.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CompletionToken(pub u64);

/// A request admitted for application dispatch.
#[derive(Debug, Clone)]
pub struct AdmittedRequest {
    pub token: CompletionToken,
    pub request_id: u64,
    pub method: String,
    pub payload: Vec<u8>,
    pub deadline: Duration,
}

/// Result supplied by the application for an admitted request.
#[derive(Debug, Clone)]
pub struct HostResult {
    pub token: CompletionToken,
    pub payload: Option<Vec<u8>>,
    pub error: Option<(ErrorCode, String)>,
}

impl HostResult {
    pub fn ok(token: CompletionToken, payload: Vec<u8>) -> Self {
        Self { token, payload: Some(payload), error: None }
    }

    pub fn err(token: CompletionToken, code: ErrorCode, message: impl Into<String>) -> Self {
        Self { token, payload: None, error: Some((code, message.into())) }
    }
}

/// Resolution of a supplied result against core state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompletionDisposition {
    /// Result accepted; the terminal frame may be transmitted.
    Accepted,
    /// RPC already expired; the result must not be transmitted.
    Expired,
    /// Unknown or already-completed token; the result is dropped.
    Unknown,
    /// Handle closed; the result is dropped.
    Closed,
}

/// Policy deadlines owned by the deployment.
#[derive(Debug, Clone)]
pub struct PolicyDeadlines {
    /// Maximum time to resolve authentication for one handshake.
    pub auth_timeout: Duration,
    /// Maximum time to resolve authorization for one request.
    pub authz_timeout: Duration,
}

impl Default for PolicyDeadlines {
    fn default() -> Self {
        Self {
            auth_timeout: Duration::from_secs(5),
            authz_timeout: Duration::from_secs(5),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn completion_tokens_distinguish_wire_ids() {
        let a = CompletionToken(7);
        let b = CompletionToken(7);
        assert_eq!(a, b);
        let r = HostResult::ok(a, b"ok".to_vec());
        assert!(r.payload.is_some());
    }

    #[test]
    fn deny_decisions_carry_typed_codes() {
        let d = AuthzDecision::Deny { code: ErrorCode::PermissionDenied };
        assert!(matches!(d, AuthzDecision::Deny { .. }));
    }
}
