# Audit B — Schema vs Specification Matrix (Syntra v1)

- Scope: every `.proto` message and field in `proto/syntra/v1/*.proto` against its normative definition; every normative wire concept against schema representation.
- Method: independent read of the seven IDL files and all defining documents. Proto comments are informative only (SYN-ARCH-040); behavior lives in `specifications/`.
- Verdict scale (fields): DEFINED · UNDERDEFINED · UNREFERENCED · CONFLICTING.
- Verdict scale (concepts): REPRESENTED · INTENTIONALLY ABSENT (documented, no wire form by decision) · MISSING (should exist, does not) · AMBIGUOUS.
- Related: B1–B11 in `rfcs/0001-public-idl-layout.md`; `specifications/schema/reference.md`.

## 1. Per-message, per-field classification

### 1.1 `Frame` — `envelope.proto` (fields 1, 2, 10–15; reserved 16, 17, `event`, `resume`, `ack`)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `version` | 1 | `uint32` | DEFINED | SNTR-HS-003/010/020, SNTR-VER-001/002. Pre-handshake = initiator max; post-handshake = selected. Zero is not a negotiated version. |
| `request_id` | 2 | `uint64` | DEFINED (semantics split — see finding F-02) | SNTR-RPC-002/010, SNTR-WIRE-003/010. Connection-scoped, initiator-chosen, nonzero for RPC. Reuse-after-completion permitted by core but rejected as stale by replay security (B3 conflict, not a schema defect). |
| `hello` | 10 | `ClientHello` | DEFINED | SNTR-HS-003/020, SNTR-CORE-010. Exactly once, initiator→host, first envelope. |
| `ready` | 11 | `ServerReady` | DEFINED | SNTR-HS-004, SNTR-CORE-020. Exactly one terminal success outcome per connection. |
| `request` | 12 | `RpcRequest` | DEFINED | SNTR-RPC-001/002/030. ACTIVE only, nonzero ID, authorized dispatch. |
| `result` | 13 | `RpcResult` | DEFINED (carrier gap — see finding F-03) | SNTR-RPC-002/006. Terminal RPC outcome. Has **no lawful pre-ACTIVE use** (SNTR-WIRE-003 forbids zero-ID `result`); the handshake-error carrier is the open blocker B1. |
| `cancel` | 14 | `Cancel` | DEFINED | SNTR-RPC-005. Advisory; target is the enclosing `request_id`. |
| `notification` | 15 | `Notification` | DEFINED | SNTR-EVENT-001/005. Host→initiator, zero ID, ACTIVE only. |
| reserved 16, 17 / `event`, `resume`, `ack` | — | — | DEFINED (rule) / UNENFORCEABLE-BY-CODEC (see B6) | SNTR-SER-008, SNTR-WIRE-008, SNTR-VER-005. Schema reservation does not make decoders reject these tags; runtime raw-field validation is still missing. |

### 1.2 `ClientHello` — `handshake.proto` (fields 1–3)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `min_version` | 1 | `uint32` | DEFINED | SNTR-HS-020: nonzero; `min ≤ max`. Shape validated before policy (SNTR-HS-030). |
| `max_version` | 2 | `uint32` | DEFINED | SNTR-HS-003/010/020: nonzero range ceiling; `Frame.version` pre-handshake equals this value. |
| `credential` | 3 | `bytes` | UNDERDEFINED | SNTR-AUTH-001…003, SNTR-ASEC-001…003. Opaque sensitive bytes; empty = anonymous attempt. **No field-specific maximum length exists** (B7; only HTTP profiles bound it at 64 KiB via SNTR-HTTP-113). No redaction annotation; generated debug/String/JSON output can leak it. |

### 1.3 `ServerReady` — `handshake.proto` (field 1)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `connection_id` | 1 | `string` | UNDERDEFINED | SNTR-SESS-002/020, SNTR-ASEC-010: opaque, unguessable (≥128-bit entropy), single-connection diagnostic; never auth/resume/session handle. **No length bound, no encoding of the entropy requirement** (a UTF-8 string cannot express "128-bit entropy"); emptiness is not explicitly rejected on the wire (only implied by the entropy rule). |

### 1.4 `RpcRequest` — `rpc.proto` (fields 1–3)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `method` | 1 | `string` | DEFINED (bound delegated) | SNTR-RPC-001 + §1C: canonical `/package.Service/Method`, ASCII printable, case-sensitive, no normalization. No separate v1 length bound; must fit the envelope; deployments document extra caps. |
| `payload` | 2 | `bytes` | DEFINED | SNTR-RPC-003, SNTR-OPQ-001/002: arbitrary bytes incl. empty/non-UTF-8; bit-preserved; never interpreted. |
| `timeout_ms` | 3 | `uint32` | DEFINED (default value delegated) | SNTR-RPC-004 + §1F: relative ms budget; 0 = bounded host default. No wire absolute timestamps. No suite-wide default or maximum; deployments document both. |

### 1.5 `RpcResult` — `rpc.proto` (`outcome` oneof: `payload` = 1, `error` = 2)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `payload` | 1 | `bytes` | DEFINED | SNTR-RPC-003/006, SNTR-WIRE-007: selected empty bytes = success with empty output; distinct from unset outcome. |
| `error` | 2 | `RpcError` | DEFINED | SNTR-RPC-006, SNTR-ERR-001: typed failure, nonzero code required. An embedded empty `RpcError` (code 0) is representable by codecs but MUST be rejected (SNTR-ERR-001). |

### 1.6 `Cancel` — `rpc.proto` (no fields)

No fields, no numbers: intentional. DEFINED via SNTR-RPC-005 (§1G): presence + enclosing `request_id` is the whole signal. No reason, deadline, or operation-ID field exists (B11 deferred).

### 1.7 `Notification` — `events.proto` (`payload` = 1, `bytes`)

DEFINED via SNTR-EVENT-001/002/005, SNTR-WIRE-007: opaque bytes, empty valid, zero `request_id`, never completes an RPC. No event/stream ID, type, sequence, cursor, ack, or stream-state field exists by decision (B11; events.md §9 IDL review).

### 1.8 `RpcError` — `errors.proto` (`code` = 1 enum, `message` = 2 string)

| Field | Tag | Type | Verdict | Normative definition |
|---|---|---|---|---|
| `code` | 1 | `ErrorCode` | DEFINED | SNTR-ERR-001/002/005/010: emit defined nonzero; reject zero-as-failure; map unknown numerics to `UNKNOWN` at the reporting layer (codecs do not do this automatically). |
| `message` | 2 | `string` | UNDERDEFINED (bound) | SNTR-ERR-003/021, SNTR-ASEC-011/024: human-readable public UTF-8, no secrets/diagnostics/raw bytes, not a machine channel. "SHOULD be concise" + envelope ceiling are the only size controls; **no explicit maximum length** (B7). |

`ErrorCode` 0–16: DEFINED, exact names/numbers preserved from history (reference.md §ErrorCode registry). No aliases. No new numbers allocated (B11).

### 1.9 `session.proto`, `capabilities.proto` (no messages, no fields, no enums)

DEFINED as documentation-only by decision (reference.md §A–G table rows C/F; RFC 0001 B11; sessions.md; capabilities.md). Not UNREFERENCED: the specs normatively state these files define nothing. BSR/language impact: some generators emit descriptor-only output or no source file — documented, no action (see audit K).

## 2. Normative wire-concept representation status

| Concept (task §A) | Status | Evidence |
|---|---|---|
| Protocol version (`Frame.version`, `min/max_version`) | REPRESENTED | `envelope.proto` f1, `handshake.proto` f1–2; negotiated per SNTR-HS-003/010, SNTR-VER-002. |
| `request_id` | REPRESENTED (semantics contested) | `envelope.proto` f2; scope rules in SNTR-RPC-002/010 + §1B vs SNTR-RPL-012 (finding F-02). |
| Session ID | INTENTIONALLY ABSENT | None exists in v1 by decision (SNTR-SESS-002, sessions.md §1B, RFC 0002). `connection_id` is explicitly not one. Consistent everywhere except one stale table row (finding F-14). |
| Operation ID | INTENTIONALLY ABSENT | No core field by decision (SNTR-RPC-007/010, SNTR-RPL-013); lives inside opaque payloads. Consistent. |
| Capability ID | INTENTIONALLY ABSENT (binding missing) | ASCII `name/version` shape defined (SNTR-CAP-001) but **no wire field, no advertisement/confirmation binding** exists in v1 (finding F-17; open-questions blocker 1). |
| Event ID / stream ID / cursor | INTENTIONALLY ABSENT | No wire fields by decision (SNTR-EVENT-002/003/009); live in payloads under future stream specs. Consistent. |
| Error code | REPRESENTED | `ErrorCode` 0–16; meanings SNTR-ERR-002. Task-example names (`PROTOCOL_VERSION_UNSUPPORTED`, `METHOD_NOT_FOUND`, …) correctly have no allocation; mapping table exists (errors.md §1A + RFC 0001 §4). |
| Transport profile (identifier) | REPRESENTED with CONTRADICTORY VALUES | Identifiers exist per profile but the specified strings disagree with the conformance suite's strings (finding F-01). |
| Authentication mechanism (identifier/negotiation) | INTENTIONALLY ABSENT | No mechanism field by decision (SNTR-AUTH-001/004, auth.md §1A; open-questions blocker 4). Consistent, except carriage reconciliation gap (finding F-10). |
| Resume token / re-auth / close-session message | INTENTIONALLY ABSENT | No messages by decision (SNTR-SESS-001/006, RFC 0002). Consistent. |
| Handshake failure carrier | MISSING | Required by SNTR-ERR-004/handshake §5 but **no legal `Frame` can carry a pre-ACTIVE typed error** (finding F-03 = B1). |
| Limit overrides / extension bounds | MISSING | Negotiation of lower frame bounds, credential/method/ID/text maxima have no binding (finding F-12 = B7). |
| Timestamps / absolute clocks | INTENTIONALLY ABSENT | Relative `timeout_ms` only; no clock sync assumed (rpc.md §1F). Consistent. |
| Compression negotiation | INTENTIONALLY ABSENT | No core field; per-profile policy only (HTTP-120/121, WS-090…092). Consistent. |

## 3. Schema-vs-spec verdicts

- No field lacks a defining requirement; no requirement names a field that does not exist — except stale **filename** references (`error.proto` for `errors.proto` in errors.md, framing.md, protocol.md, threat-model.md; `session.proto` cited as the home of `Frame` in framing.md and of `ClientHello`/`ServerReady` in authentication-security.md). Filenames are the sole authority's address (SYN-ARCH-040); wrong addresses misdirect implementers. P2 (finding F-20).
- `reserved 16, 17` + names: schema-declared, runtime-unenforced by codecs (B6, known).
- Oneof raw-wire multiplicity (B4, known) and unknown-body discriminator absence (B5, known) are codec-representation facts, confirmed by reference.md and generation.md (Prost drops unknown fields; Go preserves them — see audit K).
- `go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"` in all seven files embeds a private organization path in the normative schema (finding F-05).
