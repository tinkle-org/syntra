//! Codec + validation vectors (SNTR-WIRE-900, SNTR-SER-900).
//!
//! Drives `conformance/test-vectors` byte expectations through the core
//! codec: one valid frame per variant, empty-body rejection, the
//! request_id misuse matrix, unknown-variant rejection, reserved-number
//! rejection, duplicate-oneof rejection, depth/allocation bounds, and
//! empty-payload round-trips.

use prost::Message;
use syntra_core::proto::frame::Body;
use syntra_core::proto::{
    Cancel, ClientHello, Frame, Notification, RpcError, RpcRequest, RpcResult, ServerReady,
};
use syntra_core::{
    decode_frame, encode_frame, validate_frame, ConnectionState, ErrorCode, ValidationContext,
    MAX_FRAME_BYTES,
};

fn active() -> ValidationContext {
    ValidationContext::active(1)
}

fn connected() -> ValidationContext {
    ValidationContext::pre_handshake(ConnectionState::Connected)
}

#[test]
fn one_valid_frame_per_variant() {
    let frames = vec![
        Frame {
            version: 1,
            request_id: 0,
            body: Some(Body::Hello(ClientHello {
                min_version: 1,
                max_version: 1,
                credential: vec![],
            })),
        },
        Frame {
            version: 1,
            request_id: 0,
            body: Some(Body::Ready(ServerReady {
                connection_id: "conn-1".into(),
            })),
        },
        Frame {
            version: 1,
            request_id: 7,
            body: Some(Body::Request(RpcRequest {
                method: "/example.Echo/Echo".into(),
                payload: b"hi".to_vec().into(),
                timeout_ms: 500,
            })),
        },
        Frame {
            version: 1,
            request_id: 7,
            body: Some(Body::Result(RpcResult {
                outcome: Some(syntra_core::proto::rpc_result::Outcome::Payload(
                    b"hi".to_vec().into(),
                )),
            })),
        },
        Frame {
            version: 1,
            request_id: 7,
            body: Some(Body::Cancel(Cancel {})),
        },
        Frame {
            version: 1,
            request_id: 0,
            body: Some(Body::Notification(Notification {
                payload: b"tick".to_vec().into(),
            })),
        },
    ];
    for f in &frames {
        let ctx = match f.body {
            // hello is the CONNECTED first unit; ready arrives in
            // NEGOTIATING/AUTHENTICATING; application units in ACTIVE.
            Some(Body::Hello(_)) => connected(),
            Some(Body::Ready(_)) => ValidationContext::pre_handshake(ConnectionState::Negotiating),
            _ => active(),
        };
        let bytes = encode_frame(f, ctx).expect("valid frame encodes");
        let back = decode_frame(&bytes, ctx).expect("valid frame decodes");
        assert_eq!(&back, f);
    }
}

#[test]
fn empty_body_rejected() {
    let f = Frame {
        version: 1,
        request_id: 0,
        body: None,
    };
    let bytes = f.encode_to_vec();
    let err = decode_frame(&bytes, connected()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::InvalidArgument);
}

#[test]
fn request_id_misuse_matrix() {
    // hello/ready/notification MUST use 0; request/result/cancel MUST NOT.
    let cases: Vec<(Frame, bool)> = vec![
        (
            Frame {
                version: 1,
                request_id: 3,
                body: Some(Body::Hello(ClientHello {
                    min_version: 1,
                    max_version: 1,
                    credential: vec![],
                })),
            },
            false,
        ),
        (
            Frame {
                version: 1,
                request_id: 0,
                body: Some(Body::Request(RpcRequest {
                    method: "/example.Echo/Echo".into(),
                    payload: vec![].into(),
                    timeout_ms: 0,
                })),
            },
            false,
        ),
        (
            Frame {
                version: 1,
                request_id: 0,
                body: Some(Body::Result(RpcResult { outcome: None })),
            },
            false,
        ),
        (
            Frame {
                version: 1,
                request_id: 5,
                body: Some(Body::Notification(Notification {
                    payload: vec![].into(),
                })),
            },
            false,
        ),
    ];
    for (f, ok) in cases {
        assert_eq!(validate_frame(&f, active()).is_ok(), ok);
    }
}

#[test]
fn reserved_numbers_rejected() {
    // Field 16, length-delimited, one zero byte of content.
    let bytes = vec![0x08, 0x01, 0x82, 0x01, 0x01, 0x00];
    let err = decode_frame(&bytes, connected()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::InvalidArgument);
}

#[test]
fn duplicate_oneof_rejected() {
    // A hello body (field 10) followed by a ready body (field 11):
    // prost would collapse these, so the raw scan must reject first.
    let mut bytes = Frame {
        version: 1,
        request_id: 0,
        body: Some(Body::Hello(ClientHello {
            min_version: 1,
            max_version: 1,
            credential: vec![],
        })),
    }
    .encode_to_vec();
    let ready = ServerReady {
        connection_id: "x".into(),
    }
    .encode_to_vec();
    bytes.push(0x5A); // field 11, wire type 2
    bytes.push(ready.len() as u8);
    bytes.extend_from_slice(&ready);
    let err = decode_frame(&bytes, connected()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::InvalidArgument);
}

#[test]
fn unknown_body_only_is_unimplemented() {
    // Version only + unknown field 90 (length-delimited "x"): no known
    // body, but unknown content -> UNIMPLEMENTED (not empty-body).
    let bytes = vec![0x08, 0x01, 0xD2, 0x05, 0x01, b'x'];
    let err = decode_frame(&bytes, connected()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::Unimplemented);
}

#[test]
fn unknown_fields_tolerated() {
    // Same hello as the no-length-prefix proof plus an unknown field:
    // accepted as the same logical Frame (SNTR-SER-003).
    let mut bytes = Frame {
        version: 1,
        request_id: 0,
        body: Some(Body::Hello(ClientHello {
            min_version: 1,
            max_version: 1,
            credential: vec![],
        })),
    }
    .encode_to_vec();
    bytes.extend_from_slice(&[0xD2, 0x05, 0x01, b'x']);
    let back = decode_frame(&bytes, connected()).expect("unknown fields tolerated");
    assert!(matches!(back.body, Some(Body::Hello(_))));
}

#[test]
fn oversize_rejected_at_max_plus_one() {
    let bytes = vec![0x55u8; MAX_FRAME_BYTES + 1];
    let err = decode_frame(&bytes, active()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::ResourceExhausted);
}

#[test]
fn huge_length_prefix_rejected_before_alloc() {
    // Tag for field 12 (request, LEN) with a 64 MiB length prefix but no
    // content: allocation bound fires before prost allocates.
    let bytes = vec![0x08, 0x01, 0x62, 0x80, 0x80, 0x80, 0x02];
    let err = decode_frame(&bytes, active()).unwrap_err();
    assert_eq!(err.code(), ErrorCode::ResourceExhausted);
}

#[test]
fn empty_payload_round_trips() {
    // Empty success payload is success (not missing outcome).
    let f = Frame {
        version: 1,
        request_id: 8,
        body: Some(Body::Result(RpcResult {
            outcome: Some(syntra_core::proto::rpc_result::Outcome::Payload(
                vec![].into(),
            )),
        })),
    };
    let bytes = encode_frame(&f, active()).unwrap();
    let back = decode_frame(&bytes, active()).unwrap();
    assert_eq!(back, f);
}

#[test]
fn missing_outcome_and_zero_code_rejected() {
    let f = Frame {
        version: 1,
        request_id: 9,
        body: Some(Body::Result(RpcResult { outcome: None })),
    };
    assert!(validate_frame(&f, active()).is_err());
    let f = Frame {
        version: 1,
        request_id: 9,
        body: Some(Body::Result(RpcResult {
            outcome: Some(syntra_core::proto::rpc_result::Outcome::Error(RpcError {
                code: 0,
                message: "bad".into(),
            })),
        })),
    };
    assert!(validate_frame(&f, active()).is_err());
}

#[test]
fn version_discipline() {
    // Pre-handshake zero version rejected.
    let f = Frame {
        version: 0,
        request_id: 0,
        body: Some(Body::Hello(ClientHello {
            min_version: 1,
            max_version: 1,
            credential: vec![],
        })),
    };
    assert!(decode_frame(&f.encode_to_vec(), connected()).is_err());
    // ACTIVE mismatch rejected.
    let f = Frame {
        version: 2,
        request_id: 3,
        body: Some(Body::Request(RpcRequest {
            method: "/example.Echo/Echo".into(),
            payload: vec![].into(),
            timeout_ms: 1,
        })),
    };
    assert!(validate_frame(&f, active()).is_err());
}

#[test]
fn malformed_bytes_rejected_deterministically() {
    // Truncated varint tag.
    assert!(decode_frame(&[0x80], active()).is_err());
    // Illegal wire type (6).
    assert!(decode_frame(&[0x08, 0x01, 0x36], active()).is_err());
    // Empty input.
    assert!(decode_frame(&[], active()).is_err());
}
