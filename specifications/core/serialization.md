# Syntra v1 Core — Serialization

- Identifier: `specifications/core/serialization.md`
- Title: Protobuf Serialization and Validation
- Status: Draft (pending maintainer approval via RFC)
- Version: 1.0.0-draft.1 (2026-10-19)
- Normative references: BCP 14; `proto/syntra/v1/*.proto` (authoritative representation, SYN-ARCH-040); Protobuf proto3 + wire-format encoding docs; `protocol.md`; `framing.md`; `errors.md`
- Scope: How Syntra messages are encoded with Protobuf binary wire format, how unknown fields and malformed input are handled, and what semantic validation the core performs. Transport framing (length prefixes, HTTP/WS bindings) is out of scope — see `framing.md` and transport specs.
- Terminology: As in `protocol.md`. **Message** = a Protobuf message (`Frame`, `RpcRequest`, etc.). **Unknown field** = wire field number without a definition in the negotiated schema. **Unknown variant** = unrecognized `Frame.body oneof` member (handled in `framing.md`).

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 1. Protocol requirements

**SNTR-SER-001** — Syntra MUST use proto3 binary encoding for all core messages. The `.proto` files in `proto/syntra/v1/` are the sole authority for field numbers, types, and `reserved` values (SYN-ARCH-040). Prose in this suite MUST NOT redefine them.

**SNTR-SER-002** — Protobuf serialization is NOT canonical. Multiple byte sequences MAY represent the same logical message (field order, unknown-field retention, packed vs unpacked, default-value omission, length-prefix variations). Implementations MUST NOT hash, sign, or compare serialized bytes for equality of logical messages; they MUST compare decoded fields.

**SNTR-SER-003** — Bounded raw-wire validation applies to the two discriminated messages (`Frame` and the `RpcResult.outcome` group) before generated-merge semantics are used; peers agree on this validation before using decoded values, preserving non-canonical field ordering and non-minimal valid varint acceptance within bounded widths. Accepted [RFC 0008](../../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md) D1 (which closes RFC 0001 B4/B5/B6) fixes the definitive body-partition and validation order; first failure determines the error:

1. Structural validation of the complete bounded frame first: wire structure, lengths, varints and nesting depth for every field including unknown fields; malformed structure or a wrong wire type for any schema-known core field is `INVALID_ARGUMENT`. Known core message boundaries are validated recursively — including each occurrence in known nested messages such as `RpcRequest.timeout_ms`; a wrong-type occurrence followed by a valid one is never silently skipped — and opaque payload/credential bytes are never parsed as submessages; profile payload validation follows that profile's own schema.
2. `Frame` field numbers 16 or 17 MUST be rejected as a reserved-tag violation (`INVALID_ARGUMENT`), irrespective of other metadata (SNTR-SER-008).
3. More than one occurrence in body space — including two occurrences of the same alternative or a known body plus a future body — MUST be rejected as `INVALID_ARGUMENT` (SNTR-WIRE-002). Exactly one body is permitted.
4. A sole structurally valid body with a tag in the 18..31 space is a future-body variant: it MUST be rejected with `UNIMPLEMENTED` (an unknown required feature), and no body MUST be rejected with `INVALID_ARGUMENT`. Known bodies (tags 10..15) and future bodies allocated in that space are length-delimited; other wire types fail structurally.
5. Only after steps 1–4, decode the known body and apply field, version/state, correlation, and authorization rules from their owning documents before effects. Unknown `Frame` metadata (fields 3..9 and 32+; 1/2 retain their known header meanings) is ignored within the same byte/depth limits, regardless of order, and never affects mandatory interop.

The same raw policy governs `RpcResult.outcome`, which has one raw occurrence: known fields 1/2, future outcome space 3..15, unknown metadata 16+. Multiple outcomes (even the same field twice) are `INVALID_ARGUMENT`, a sole structurally valid outcome in 3..15 is `UNIMPLEMENTED`, and no outcome is `INVALID_ARGUMENT`; an empty selected success remains valid. Outside these two groups, ordinary singular fields retain standard Protobuf merge/last-value semantics. Rejections follow the owning carrier rules (`framing.md`; pre-`ACTIVE` failures are local handshake causes per `handshake.md`), never permission to emit pre-`ACTIVE` results.

**SNTR-SER-004** — Forward compatibility: implementations MUST accept messages containing fields added as OPTIONAL in a minor version and MUST preserve no interpretation of them. They MUST NOT require an optional field without prior capability negotiation.

**SNTR-SER-005** — Required semantic validation (beyond Protobuf well-formedness): every decoded `Frame` MUST be validated per `framing.md` SNTR-WIRE rules (exactly one body, version check, `request_id` discipline, size bound). Every `RpcRequest`/`RpcResult`/`RpcError` MUST be validated per `rpc.md` / `errors.md` (method path shape, outcome presence, nonzero error code). Syntactically valid Protobuf that violates these rules MUST be rejected as `INVALID_ARGUMENT` or `FAILED_PRECONDITION`, never processed.

**SNTR-SER-006** — Size and recursion limits: implementations MUST enforce (a) maximum decoded message size ≤ maximum envelope size (see SNTR-WIRE-006, default 1 MiB unless transport profile states otherwise), (b) maximum nesting depth 32 for embedded messages, (c) maximum total allocation per message bounded before full parse (streaming/limited reader). Exceeding any limit MUST yield `RESOURCE_EXHAUSTED` (RPC context) or handshake/transport closure, never a panic or OOM.

**SNTR-SER-007** — Malformed input behavior: truncated varints, illegal wire types, overlong lengths, invalid UTF-8 in `string` fields (e.g., `method`, `connection_id`, `RpcError.message`), or depth/size violations MUST be rejected deterministically. In RPC context → `ERROR_CODE_INVALID_ARGUMENT` or `RESOURCE_EXHAUSTED`; in handshake → handshake failure + close; at framing layer → connection error per `framing.md`. Implementations MUST NOT panic, MUST NOT allocate unboundedly, and MUST NOT leak private state in the resulting error.

**SNTR-SER-008** — `reserved 16, 17` and `reserved "event", "resume", "ack"` MUST be preserved. This reserved-tag runtime validation requirement is ACTIVE (per accepted [RFC 0008](../../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md) D1, step 2 of SNTR-SER-003): validators MUST reject any raw wire occurrence of reserved field numbers 16/17 in the top-level `Frame` as a reserved-tag violation (`INVALID_ARGUMENT`), irrespective of other metadata; encoders MUST never emit them. Scoping per RFC 0008 D1: the reject-on-occurrence rule applies at the top-level body position only. Numbers 16/17 inside nested messages (`RpcResult`, `RpcError`, `ClientHello`, etc.) are unassigned unknown fields, not reserved occurrences, and MUST be tolerated per SNTR-SER-003 (forward compatibility). `reserved` names are schema reservations, not binary wire strings.

**SNTR-SER-008A** — Duplicate scalar clarification (per accepted [RFC 0008](../../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md) D1, closing RFC 0001 B4): duplicate `version`/`request_id` occurrences on the wire follow protobuf merge semantics (last value wins) and MUST NOT be rejected as malformed; validators type-check each occurrence and validate the merged value. Duplicate bodies in the `Frame.body` oneof remain rejected per SNTR-WIRE-002: more than one occurrence in body space is a raw-wire validation failure, including a repeated same-body occurrence. Duplicate `Cancel` inner content is unknown-field tolerance, not a violation: `Cancel` carries no defined fields, so any well-formed inner bytes MUST be tolerated per SNTR-SER-003 (malformed inner wire still fails as `INVALID_ARGUMENT`).

## 2. Client behavior

- **SNTR-SER-010** — The client MUST encode with a conformant proto3 encoder, MUST NOT emit reserved numbers/names, and MUST set only defined fields. It MUST tolerate unknown fields in host responses per SNTR-SER-003.
- **SNTR-SER-011** — The client MUST validate every received message per SNTR-SER-005/006 before acting on it, including `ServerReady` and `RpcResult` payloads it does not semantically interpret (syntactic + bound checks only).

## 3. Server behavior

- **SNTR-SER-020** — The server MUST apply identical encode/validate rules, and MUST additionally validate `ClientHello` fields (version range shape, credential length bound) before authentication logic.
- **SNTR-SER-021** — The server MUST NOT interpret unknown fields as capabilities or authentication signals.

## 4. Failure handling

Truncated/oversized/invalid-UTF-8/depth-exceeded inputs map per SNTR-SER-007. Failures are terminal for the affected RPC; handshake failures are terminal for the connection (see `handshake.md`). Error messages for malformed input MUST be generic (`INVALID_ARGUMENT`/`RESOURCE_EXHAUSTED`) and MUST NOT echo raw bytes, credentials, or private diagnostics.

## 5. Security considerations

Attacker-controlled bytes reach the Protobuf decoder first. Bounded pre-allocation, depth caps, and UTF-8 strictness are security boundaries, not optimizations. Unknown-field skipping MUST respect wire-type lengths to avoid desync. See `reliability.md` for backpressure/exhaustion.

## 6. Compatibility considerations

Proto3 additive rules + SNTR-SER-003/004 give minor-version tolerance. Any change that makes a previously ignored field mandatory, or repurposes a number, is a major version per `versioning.md`. Serialization order MUST NOT be depended upon.

## 7. Conformance requirements

- **SNTR-SER-900** — Fixtures: empty/large/arbitrary payloads, unknown-field injection, out-of-order fields, packed/unpacked equivalence, truncated varint, invalid UTF-8, depth/size exceedance, reserved-number rejection. Decoder MUST pass all; encoder MUST emit only defined fields and MUST round-trip logically (not byte-identically).
- **SNTR-SER-901** — Non-canonical proof: two different byte encodings of the same `Frame` MUST decode to equal logical messages and MUST NOT be treated as distinct at the protocol layer.
