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

**SNTR-SER-003** — On receipt, implementations MUST ignore unknown Protobuf fields (tolerate and skip per wire-type) and MUST NOT fail, unless a future specification explicitly marks a field as critical. Unknown fields MUST NOT affect mandatory interop.

**SNTR-SER-004** — Forward compatibility: implementations MUST accept messages containing fields added as OPTIONAL in a minor version and MUST preserve no interpretation of them. They MUST NOT require an optional field without prior capability negotiation.

**SNTR-SER-005** — Required semantic validation (beyond Protobuf well-formedness): every decoded `Frame` MUST be validated per `framing.md` SNTR-WIRE rules (exactly one body, version check, `request_id` discipline, size bound). Every `RpcRequest`/`RpcResult`/`RpcError` MUST be validated per `rpc.md` / `errors.md` (method path shape, outcome presence, nonzero error code). Syntactically valid Protobuf that violates these rules MUST be rejected as `INVALID_ARGUMENT` or `FAILED_PRECONDITION`, never processed.

**SNTR-SER-006** — Size and recursion limits: implementations MUST enforce (a) maximum decoded message size ≤ maximum envelope size (see SNTR-WIRE-006, default 1 MiB unless transport profile states otherwise), (b) maximum nesting depth 32 for embedded messages, (c) maximum total allocation per message bounded before full parse (streaming/limited reader). Exceeding any limit MUST yield `RESOURCE_EXHAUSTED` (RPC context) or handshake/transport closure, never a panic or OOM.

**SNTR-SER-007** — Malformed input behavior: truncated varints, illegal wire types, overlong lengths, invalid UTF-8 in `string` fields (e.g., `method`, `connection_id`, `RpcError.message`), or depth/size violations MUST be rejected deterministically. In RPC context → `ERROR_CODE_INVALID_ARGUMENT` or `RESOURCE_EXHAUSTED`; in handshake → handshake failure + close; at framing layer → connection error per `framing.md`. Implementations MUST NOT panic, MUST NOT allocate unboundedly, and MUST NOT leak private state in the resulting error.

**SNTR-SER-008** — `reserved 16, 17` and `reserved "event", "resume", "ack"` MUST be preserved. Decoders MUST reject any wire occurrence of a reserved field number as malformed; encoders MUST never emit them.

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
