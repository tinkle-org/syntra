//! Non-normative generated-code smoke tests, not a protocol implementation.
pub mod syntra {
    pub mod v1 {
        // Smoke-test output generated into the ignored .tmp/ tree by
        // scripts/validate-schema.py. Never committed; never a repository binding.
        include!("../../../../.tmp/bufgen/rust/gen/syntra.v1.rs");
    }
}

#[cfg(test)]
mod tests {
    use super::syntra::v1::*;
    use prost::Message;
    use std::collections::BTreeMap;

    fn bytes(hex: &str) -> Vec<u8> {
        hex.as_bytes()
            .chunks_exact(2)
            .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
            .collect()
    }

    fn decode(hex: &str) -> Frame {
        Frame::decode(bytes(hex).as_slice()).unwrap()
    }

    fn fixtures() -> BTreeMap<String, String> {
        serde_json::from_str(include_str!("../../fixtures/frames.json")).unwrap()
    }

    #[test]
    fn shared_fixtures_and_payloads() {
        for (_, raw) in fixtures() {
            let frame = decode(&raw);
            assert_eq!(frame.version, 1);
            assert!(frame.body.is_some());
            assert_eq!(
                Frame::decode(frame.encode_to_vec().as_slice()).unwrap(),
                frame
            );
        }
        let values = fixtures();
        let frame = decode(&values["request"]);
        assert_eq!(frame.request_id, 7);
        match frame.body.unwrap() {
            frame::Body::Request(req) => {
                assert_eq!(req.method, "/example.Echo/Echo");
                assert_eq!(req.payload, [0, 255, 128]);
                assert_eq!(req.timeout_ms, 1);
            }
            _ => panic!("fixture is not a request"),
        }
        match decode(&values["notification"]).body.unwrap() {
            frame::Body::Notification(event) => assert_eq!(event.payload, [0, 255, 128]),
            _ => panic!("fixture is not a notification"),
        }
    }

    #[test]
    fn presence_defaults_and_invalid_states() {
        let frame::Body::Result(result) = decode(&fixtures()["empty_success"]).body.unwrap() else {
            panic!("fixture is not a result");
        };
        assert!(matches!(result.outcome, Some(rpc_result::Outcome::Payload(p)) if p.is_empty()));
        let frame::Body::Result(result) = decode("080110076a00").body.unwrap() else {
            panic!()
        };
        assert!(result.outcome.is_none());
        assert!(decode("0801").body.is_none());
        assert!(matches!(
            decode(&fixtures()["cancel"]).body,
            Some(frame::Body::Cancel(_))
        ));
        assert_eq!(RpcRequest::default().timeout_ms, 0);
        let frame::Body::Result(result) = decode("080110076a0412020800").body.unwrap() else {
            panic!()
        };
        assert!(matches!(result.outcome, Some(rpc_result::Outcome::Error(e)) if e.code == 0));
        // The last checks demonstrate representability, NOT protocol acceptance.
    }

    #[test]
    fn unknown_values_order_and_full_width_ids() {
        assert_eq!(decode("080110077200"), decode("720010070801"));
        // Prost discards unknown metadata; known fields still agree.
        assert_eq!(decode("080110077200"), decode("080110077200a00601"));
        let frame::Body::Result(result) = decode("080110076a05120308e707").body.unwrap() else {
            panic!()
        };
        let Some(rpc_result::Outcome::Error(error)) = result.outcome else {
            panic!()
        };
        assert_eq!(error.code, 999); // Reporting mapping is runtime work, not this codec.
        assert!(ErrorCode::try_from(error.code).is_err());
        for number in 0..=16 {
            let error = RpcError {
                code: number,
                message: String::new(),
            };
            assert_eq!(
                RpcError::decode(error.encode_to_vec().as_slice()).unwrap(),
                error
            );
        }
        let frame = Frame {
            version: 1,
            request_id: u64::MAX,
            body: Some(frame::Body::Cancel(Cancel {})),
        };
        assert_eq!(
            Frame::decode(frame.encode_to_vec().as_slice()).unwrap(),
            frame
        );
    }

    #[test]
    fn malformed_inputs_and_codec_limitations() {
        assert!(matches!(
            decode("080172007a00").body,
            Some(frame::Body::Notification(_))
        ));
        assert!(decode("0801820100").body.is_none()); // reserved tag is skipped, not rejected
        assert!(decode("0801a20100").body.is_none()); // future-only field is not a known body
        for raw in ["80", "08015202ff", "0f", "08015a030a01ff"] {
            assert!(
                Frame::decode(bytes(raw).as_slice()).is_err(),
                "malformed input: {raw}"
            );
        }
    }
}
