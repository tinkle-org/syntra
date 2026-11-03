# Authenticated inner-frame stream fixtures

This directory tests the u32BE length plus serialized `Frame` stream inside
authenticated channel plaintext on every current carrier. The directory name
is a fixture path, not a carrier selector. These bytes are never sent directly
to a TCP socket or WebSocket message as an unprotected Syntra connection.
The outer TCP prefix is u16BE; WebSocket messages have no outer length prefix.
See [wire format](../../../specifications/wire-format.md) and
[transports](../../../specifications/transports.md) for the protocol rules.

- [`vectors.json`](vectors.json) contains V1–V9 with exact chosen fixture bytes.
- [`byte-vectors.yaml`](byte-vectors.yaml) adds request, result and notification
  units. Matching IDs in both files carry identical bytes.
- V1/V2 decode to the same logical hello despite different field order. This
  does not require byte-identical Protobuf re-encoding.
- V4 is a maximum-size construction recipe. All independent field limits and
  validation/state/authentication conditions still apply.
- V6 is rejected on its oversized inner prefix before allocating the body.
  V7/V8 close at EOF with incomplete prefix/body; no resynchronization occurs.

Static validation checks lengths and fixture consistency. It is not evidence
that a peer has executed the handling assertions.
