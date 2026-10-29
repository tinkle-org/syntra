# Syntra v1 public IDL reference

- Status: Informative representation reference; user-directed layout decision implemented, behavioral questions remain Draft in [RFC 0001](../../rfcs/0001-public-idl-layout.md)
- Date: 2026-10-19
- Package: `syntra.v1`; encoding: Protobuf proto3 binary
- Scope: Existing declarations physically split across `proto/syntra/v1/`; no new wire types or behavioral approval

## Authority and compatibility status

`proto/syntra/v1` is the sole Protobuf source of truth by explicit user direction, recorded in RFC 0001 B9 and reflected in [ADR-002](../decisions/ADR-002-protobuf-idl.md), [architecture `SYN-ARCH-040` and §8](../architecture.md#8-requirement-ownership-authoritative-sources), and [serialization `SNTR-SER-001`](../core/serialization.md#1-protocol-requirements). The old source tree is removed. Historical [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto) and [error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto) remain pinned provenance; their declarations are preserved in [the archived historical descriptor](../../compatibility/v1-initial/README.md). This layout decision does not establish formal maintainer quorum or behavioral RFC acceptance. The core and most security specifications cited below are drafts pending approval; the accepted RFC 0007 owner documents ([secure-channel.md](../security/secure-channel.md), [device-authorization.md](../security/device-authorization.md), [noise-bindings.md](../transports/noise-bindings.md)) are not — their statements are normative. Requirement IDs identify the defining documents, and unresolved contradictions are recorded explicitly.

Moving the definitions preserves binary WIRE compatibility but breaks FILE/source/descriptor compatibility: proto imports, declaration-owning files, generated file-level APIs, descriptor filenames/dependencies and source locations change. An unchanged fully qualified message name or Go package does not preserve all generated APIs. Buf `FILE` failures against the historical layout remain known breaking differences after the implemented layout decision; WIRE compatibility alone does not clear them. Never combine the historical and current descriptor sets into one pool: duplicate symbols and conflicting `syntra/v1/session.proto` identities result. There is no second live source root. See [RFC §6](../../rfcs/0001-public-idl-layout.md#6-compatibility).

## File layout and dependency closure

Each file declares `syntax = "proto3"`, `package syntra.v1`, and the unchanged `go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"`. File paths below are relative to module root `proto`.

| File | Definitions | Direct imports |
|---|---|---|
| [syntra/v1/envelope.proto](../../proto/syntra/v1/envelope.proto) | `Frame` | `syntra/v1/events.proto`, `syntra/v1/handshake.proto`, `syntra/v1/rpc.proto` |
| [syntra/v1/handshake.proto](../../proto/syntra/v1/handshake.proto) | `ClientHello`, `ServerReady` | None |
| [syntra/v1/session.proto](../../proto/syntra/v1/session.proto) | None — documentation only | None |
| [syntra/v1/rpc.proto](../../proto/syntra/v1/rpc.proto) | `RpcRequest`, `RpcResult`, `Cancel` | `syntra/v1/errors.proto` |
| [syntra/v1/events.proto](../../proto/syntra/v1/events.proto) | `Notification` | None |
| [syntra/v1/capabilities.proto](../../proto/syntra/v1/capabilities.proto) | None — documentation only | None |
| [syntra/v1/errors.proto](../../proto/syntra/v1/errors.proto) | `ErrorCode`, `RpcError` | None |

The dependency graph is acyclic and entirely local. Consumers import the file directly owning the types they use; no public-import forwarding layer exists. The [buf.yaml](../../buf.yaml) configuration uses `STANDARD` without exceptions and `FILE` breaking checks. `STANDARD` includes `IMPORT_NO_PUBLIC`, so public imports are forbidden. There are no external schema dependencies, `google.protobuf.Any`, custom validation-option imports, or declared Protobuf services. Generic RPC method identifiers do not imply a generated gRPC service. `session.proto` and `capabilities.proto` allocate no wire extension space or behavior merely by existing.

## Delivered versus blocked A–G coverage

Delivered means described by the current schema, not runtime implementation or conformance.

| Area | Delivered representation | Blocked/deferred scope |
|---|---|---|
| A — Envelope | `Frame` with original body alternatives and reservations | Additional bodies, unknown-body discrimination, strict raw multiplicity and reserved-tag runtime rejection; RFC B1/B4/B5/B6 |
| B — Handshake/authentication | `ClientHello`, `ServerReady` | `ServerHello`, multi-round auth messages, typed rejection, capability/limit advertisement; RFC B1/B7/B11 |
| C — Sessions | Documentation-only `session.proto`; connection-bound implicit session | Resume/close/session-control types and dedicated session errors; RFC B1/B7/B11 |
| D — RPC | `RpcRequest`, `RpcResult`, empty `Cancel` | `RpcResponse`, operation-ID fields, resolved stale-ID/deadline/cancel policies; RFC B3/B8/B10/B11 |
| E — Events | `Notification` with opaque payload | `Event`, subscription/replay/cursor/ack/stream-state types; RFC B2/B7/B11 |
| F — Capabilities | Documentation-only `capabilities.proto` | Concrete capability, parameter, offer/confirmation and bounded-limit records; RFC B7 |
| G — Errors | `RpcError`, exact `ErrorCode` 0–16 registry | New numbers/names and new handshake/session error carriers; RFC B1/B10/B11 |

For precise owning requirements and rationale for every deferred addition, see [RFC B11](../../rfcs/0001-public-idl-layout.md#b11-requested-additions-deliberately-deferred). This table makes no broader completion claim.

## Message and field reference

### Presence conventions

All type names below resolve in `syntra.v1`. No field has an `optional`, `repeated`, or `map` declaration. “Implicit” means a proto3 scalar/string/bytes/enum default is returned when omitted; omission and an explicitly supplied default cannot be distinguished in the decoded API. Numeric/enum defaults are zero; string/bytes defaults are empty. “Explicit oneof” means the selected alternative is observable, including an empty message or zero-length bytes. Oneof groups themselves have no field number.

These are encoding/presence facts, not validation annotations. Protobuf accepts an unset oneof; [framing `SNTR-WIRE-002/003/007`](../core/framing.md#1-protocol-requirements-envelope) and [serialization `SNTR-SER-005`](../core/serialization.md#1-protocol-requirements) impose additional protocol checks at runtime. Ordinary scalars are not changed to optional fields by this layout migration.

### `Frame` — envelope.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `version` | 1 | `uint32` | Implicit; 0 | Proposed maximum in hello, selected version thereafter; zero is not a supported negotiated version. [Handshake `SNTR-HS-003/010/020`](../core/handshake.md#1-state-machine), [versioning `SNTR-VER-001/002`](../core/versioning.md#1-protocol-requirements) |
| `request_id` | 2 | `uint64` | Implicit; 0 | Connection-scoped correlation only. [Framing `SNTR-WIRE-003/010`](../core/framing.md), [RPC `SNTR-RPC-002/010`](../core/rpc.md#1-protocol-requirements); reuse conflict in RFC B3 |
| `hello` | 10 | `ClientHello` | Explicit oneof `body` | Initial initiator credential/version presentation; [handshake `SNTR-HS-003/020`](../core/handshake.md) |
| `ready` | 11 | `ServerReady` | Explicit oneof `body` | Host acceptance with selected version in enclosing Frame; [handshake `SNTR-HS-004`](../core/handshake.md#1-state-machine) |
| `request` | 12 | `RpcRequest` | Explicit oneof `body` | Generic application invocation after ACTIVE; [RPC `SNTR-RPC-001/030`](../core/rpc.md) |
| `result` | 13 | `RpcResult` | Explicit oneof `body` | Correlated terminal RPC outcome; [RPC `SNTR-RPC-002/006`](../core/rpc.md#1-protocol-requirements); not a legal current pre-ACTIVE error binding |
| `cancel` | 14 | `Cancel` | Explicit oneof `body` | Advisory cancellation of ID in enclosing Frame; [RPC `SNTR-RPC-005`](../core/rpc.md#1-protocol-requirements) |
| `notification` | 15 | `Notification` | Explicit oneof `body` | Host-originated uncorrelated event; [events `SNTR-EVENT-001/005`](../core/events.md#1-protocol-requirements) |

`Frame` reserves numbers **16, 17** and names **`event`, `resume`, `ack`** exactly as the historical definition does. Those are not additional body alternatives. Reservations prevent declaration reuse; they do not cause ordinary binary decoders to reject those tags. [Serialization `SNTR-SER-008`](../core/serialization.md#1-protocol-requirements), [framing `SNTR-WIRE-008`](../core/framing.md#1-protocol-requirements-envelope), and [versioning `SNTR-VER-005`](../core/versioning.md#1-protocol-requirements) demand additional preservation/rejection behavior; see RFC B6.

| Selected body | Expected direction | ID discipline | State constraints in drafts |
|---|---|---|---|
| `hello` | Initiator → host | Zero | Exactly once to begin negotiation; no second hello |
| `ready` | Host → initiator | Zero | Accepted authentication transitions to ACTIVE; never received by host |
| `request` | RPC initiator → responder | Nonzero | ACTIVE, authorized, bounded, no duplicate outstanding ID |
| `result` | Responder → RPC initiator | Same nonzero ID | Outstanding RPC in ACTIVE; close/in-flight handling needs profile/runtime rules, never a pre-ACTIVE result |
| `cancel` | RPC initiator → responder | Target nonzero ID | ACTIVE; core says unknown/completed cancel is ignored for races |
| `notification` | Host → initiator | Zero | Host emission after ACTIVE and before CLOSING; pre-ACTIVE receiver policy conflicts (RFC B2) |

Sources: [framing `SNTR-WIRE-002…005/010/011`](../core/framing.md), [handshake `SNTR-HS-005/006/012`](../core/handshake.md), [RPC `SNTR-RPC-002/005/020/030`](../core/rpc.md). These rows summarize the drafts without resolving their conflicts. At most one decoded body is available; raw bytes can contain several alternatives with last-one-wins/merge behavior (RFC B4). An empty decoded body is not protocol success.

### `ClientHello` — handshake.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `min_version` | 1 | `uint32` | Implicit; 0 | Nonzero minimum supported version; [handshake `SNTR-HS-020`](../core/handshake.md#3-client-behavior) |
| `max_version` | 2 | `uint32` | Implicit; 0 | Nonzero maximum, at least minimum; `Frame.version=max_version`; [handshake `SNTR-HS-003/010/020`](../core/handshake.md) |
| `credential` | 3 | `bytes` | Implicit; empty bytes | Sensitive opaque credential. Empty is a valid anonymous/unauthenticated attempt subject to host policy, not implicit acceptance; [authentication `SNTR-AUTH-001…003`](../core/authentication.md#1-protocol-requirements) |

Validate range, envelope size and resource bounds before credential policy (`SNTR-HS-030`, `SNTR-SER-020`, `SNTR-ASEC-040`). Credential format and principal type are application-owned. `credential` has no schema redaction or field-specific maximum; deployments still need documented bounds (RFC B7). No mechanism selector, auth-round field, capability list, resume token or requested-limit record is declared.

[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
establishes the accepted [shared Noise channel](../security/secure-channel.md)
before the Syntra handshake and supplies separately trusted channel context to
host authentication. [Device authorization](../security/device-authorization.md)
under the same RFC uses an enrolled shared AK and scoped eight-byte lookup
handle; neither is a
new `ClientHello` field or an implicit interpretation of `credential`.
Empty credentials remain anonymous attempts under current policy, not proof
of a returning-device handshake. Host authentication receives the trusted,
connection-scoped channel context through the accepted integration; Syntra
defines no enrollment RPC contract or enrollment protocol messages, and no
`.proto` or generated type change is introduced. This does not prohibit
host- or application-owned enrollment RPCs; enrollment authorization is
application-defined and owns its provisioning contract
([`SNTR-DAUTH-002`](../security/device-authorization.md)).

### `ServerReady` — handshake.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `connection_id` | 1 | `string` | Implicit; empty string | Opaque UTF-8 diagnostic ID for one connection, fresh and unguessable (at least 128-bit entropy); never a credential/session handle/resume token. [Sessions `SNTR-SESS-002/020`](../core/sessions.md), [authentication security `SNTR-ASEC-010`](../security/authentication-security.md#1-protocol-requirements) |

Selected wire version belongs to `Frame.version`, not a missing ready field. Acceptance establishes the principal binding, not synchronized or durable application state ([handshake `SNTR-HS-004`](../core/handshake.md#1-state-machine), [authentication `SNTR-AUTH-005/007`](../core/authentication.md#1-protocol-requirements)). The schema can decode an empty ID; entropy/freshness/length policy is runtime behavior. No `ServerHello`, rejection outcome, principal record, capability selection or resume handle is declared.

RFC 0007 does not add an AK/handle issuance field to `ServerReady` or repurpose
`connection_id`. Its first bootstrap `ready` would bind only the principal
authorized by bootstrap policy; using a newly enrolled AK would require a
fresh channel and Syntra handshake. Persistent authorization does not make
this message a session-resumption or traffic-key recovery mechanism.

### `RpcRequest` — rpc.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `method` | 1 | `string` | Implicit; empty string | UTF-8 string with canonical `/package.Service/Method` path: leading slash, exactly two slashes, nonempty segments, printable ASCII excluding spaces/control; [RPC `SNTR-RPC-001`](../core/rpc.md#1-protocol-requirements) |
| `payload` | 2 | `bytes` | Implicit; empty bytes | Opaque arbitrary application input, including empty/non-UTF-8; [RPC `SNTR-RPC-003`](../core/rpc.md#1-protocol-requirements), [opaque payloads `SNTR-OPQ-001/002`](../security/opaque-payloads.md#1-protocol-requirements) |
| `timeout_ms` | 3 | `uint32` | Implicit; 0 | Relative millisecond budget; zero chooses documented bounded host default, not infinite time. No absolute timestamp or clock synchronization; [RPC `SNTR-RPC-004`](../core/rpc.md#1-protocol-requirements), [reliability `SNTR-REL-006`](../core/reliability.md#1-protocol-requirements) |

Correlation lives in the enclosing Frame. Logical operation IDs/idempotency keys belong inside application payloads, not in a core field (`SNTR-RPC-007/010`, `SNTR-REL-004`, `SNTR-RPL-013`). Authorization and size/state checks precede dispatch (`SNTR-RPC-030/032`, `SNTR-ASEC-022`). There is no universal HTTP status or service-method registry in this message.

### `RpcResult` — rpc.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `payload` | 1 | `bytes` | Explicit oneof `outcome`; selected empty bytes valid | Successful opaque response; selected zero-length is success, unset outcome is not. [Framing `SNTR-WIRE-007`](../core/framing.md#1-protocol-requirements-envelope), [RPC `SNTR-RPC-003/006/020`](../core/rpc.md) |
| `error` | 2 | `RpcError` | Explicit oneof `outcome`; embedded message may be empty in codec | Typed failure; empty RpcError yields invalid code zero. [Errors `SNTR-ERR-001/005`](../core/errors.md#1-protocol-requirements) |

Exactly one decoded outcome is required by protocol. Generated APIs allow none and collapse conflicting raw-wire alternatives (RFC B4). There is no `RpcResponse` alias, progress/stream outcome, transport acknowledgment or extra error channel. An RPC has one terminal result; a notification cannot complete it (`SNTR-RPC-002/006/020/030`). Cancellation/deadline results do not prove rollback; error-outcome and race wording is blocked by RFC B10.

### `Cancel` — rpc.proto

`Cancel` has **no fields and no field numbers**. It has no reason, acknowledgment, deadline, or operation-ID field. Selecting the empty message as `Frame.cancel` provides explicit presence; `Frame.request_id` names the target. The draft requests best-effort cancellation, ignores unknown/completed targets, and forbids interpreting cancellation as rollback ([RPC `SNTR-RPC-005/021/031`](../core/rpc.md)). Cancellation of a subscription's originating RPC does not necessarily cancel the subscription ([events `SNTR-EVENT-010`](../core/events.md#1-protocol-requirements)).

### `Notification` — events.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `payload` | 1 | `bytes` | Implicit; empty bytes | Opaque application event, including empty/non-UTF-8 bytes; [framing `SNTR-WIRE-007`](../core/framing.md#1-protocol-requirements-envelope), [events `SNTR-EVENT-002/005`](../core/events.md#1-protocol-requirements) |

The enclosing ID is zero. There is no core event ID, stream ID, sequence, subscription handle, replay cursor, acknowledgment or stream-state field. Optional subscriptions/replay/cursors use application-defined RPCs and payloads under an approved capability binding ([events `SNTR-EVENT-001…004/006…010`](../core/events.md#1-protocol-requirements)); the concrete binding is absent today (RFC B7). Delivery is non-durable/at-most-once by default, with no cross-stream/cross-connection ordering guarantee; receipt does not prove application processing. Pre-ACTIVE handling is unresolved (RFC B2).

### `RpcError` — errors.proto

| Field | Tag | Protobuf type | Presence/default | Protocol meaning / defining requirement |
|---|---|---|---|---|
| `code` | 1 | `ErrorCode` | Implicit; `ERROR_CODE_UNSPECIFIED (0)` | Emit defined nonzero failure codes; reject zero failure; map unknown received numbers to UNKNOWN for reporting. [Errors `SNTR-ERR-001/005/010/020`](../core/errors.md) |
| `message` | 2 | `string` | Implicit; empty string | Public UTF-8 description; never credentials/private diagnostics/raw untrusted bytes, and never a machine-readable decision signal. [Errors `SNTR-ERR-003/010/011/021`](../core/errors.md), [security `SNTR-ASEC-011/024`](../security/authentication-security.md) |

There are no details, retry-after, category, session-error or logical-operation fields. Human-readable description and sanitization are runtime requirements; generated codecs do not enforce them. Field presence alone cannot make `RpcError` into a legal handshake or unsolicited session-failure carrier (RFC B1).

## `ErrorCode` registry — errors.proto

Exact names and numbers are preserved from historical `error.proto`. Meanings are owned by [errors `SNTR-ERR-001/002`](../core/errors.md#1-protocol-requirements); names below are the actual enum constants, not proposed categories.

| Number | Enum name | Meaning / reporting caveat |
|---|---|---|
| 0 | `ERROR_CODE_UNSPECIFIED` | Proto3 default; invalid failure outcome, never success-by-default |
| 1 | `ERROR_CODE_CANCELLED` | Cancellation; not rollback; deadline/completion race needs RFC B10 |
| 2 | `ERROR_CODE_UNKNOWN` | Unclassified failure; reporting target for unknown numeric values |
| 3 | `ERROR_CODE_INVALID_ARGUMENT` | Invalid argument or malformed shape |
| 4 | `ERROR_CODE_DEADLINE_EXCEEDED` | Call/handshake budget expired; not proof of no effects |
| 5 | `ERROR_CODE_NOT_FOUND` | Missing target/resource, subject to disclosure policy |
| 6 | `ERROR_CODE_ALREADY_EXISTS` | Creation conflict |
| 7 | `ERROR_CODE_PERMISSION_DENIED` | Authenticated principal lacks access |
| 8 | `ERROR_CODE_RESOURCE_EXHAUSTED` | Size, rate, concurrency, queue or other capacity bound |
| 9 | `ERROR_CODE_FAILED_PRECONDITION` | Operation/state precondition unsatisfied |
| 10 | `ERROR_CODE_ABORTED` | Aborted sequence/concurrency conflict |
| 11 | `ERROR_CODE_OUT_OF_RANGE` | Value outside supported range |
| 12 | `ERROR_CODE_UNIMPLEMENTED` | Unknown method/body or unsupported feature/capability |
| 13 | `ERROR_CODE_INTERNAL` | Internal failure with generic public text |
| 14 | `ERROR_CODE_UNAVAILABLE` | Loss/shutdown/transient unavailability; outcome may be unknown |
| 15 | `ERROR_CODE_DATA_LOSS` | Unrecoverable corruption/loss |
| 16 | `ERROR_CODE_UNAUTHENTICATED` | Missing, invalid, expired, revoked or unaccepted credential |

No new numbers or enum aliases are allocated. The proposed mapping for all 14 requested categories, including handshake rejection and session expiry, is in [RFC §4, proposed error-category mapping](../../rfcs/0001-public-idl-layout.md#proposed-error-category-mapping). That mapping is not an accepted expansion of the registry.

Unknown received numbers remain unknown numeric enum values at the codec layer where supported; generated enum getters do not implement `SNTR-ERR-005`. A runtime reporting layer maps them to `ERROR_CODE_UNKNOWN (2)` for the application, keeps the original number in sanitized diagnostics where possible, and never reports success. Do not rewrite fixtures to expect the raw decoder to change every unknown number to 2. Emission of known nonzero values and rejection of zero are separate validation rules. `SNTR-ERR-002/010`'s claim that only UNAVAILABLE implies unknown execution conflicts with reliability/cancellation semantics; see RFC B10 rather than inferring that other errors prove non-execution.

## Successful state flow and failure-binding gap

The six states are CONNECTED, NEGOTIATING, AUTHENTICATING, ACTIVE, CLOSING, CLOSED ([handshake `SNTR-HS-001…006`](../core/handshake.md#1-state-machine)). Version selection is the highest overlap; application traffic follows readiness. Sessions are implicit and connection-bound ([sessions `SNTR-SESS-001/003/004/007/008`](../core/sessions.md#1-protocol-requirements)).

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  Note over C,H: Verify secure transport, then CONNECTED
  C->>H: Frame{version=max_version, request_id=0, hello{min_version,max_version,credential}}
  Note over C,H: NEGOTIATING
  H->>H: Check range; choose highest mutual version
  Note over H: AUTHENTICATING: validate credential and bind principal
  H-->>C: Frame{version=selected, request_id=0, ready{connection_id}}
  Note over C,H: ACTIVE; implicit connection-bound session
  C->>H: Frame{version=selected, request_id=7, request{method,payload,timeout_ms}}
  H-->>C: Frame{version=selected, request_id=7, result{payload}}
  Note over C,H: Close/loss ends the session; reconnect requires a new handshake
  Note over C,H: Handshake rejection/timeout → CLOSING → CLOSED; typed failure binding TBD — blocker, no invented packet emitted
```

The existing schema has no legal typed handshake rejection: `RpcResult` needs a nonzero correlated request ID, while hello uses zero, and pre-ACTIVE results are forbidden (`SNTR-WIRE-003`, `SNTR-HS-012`). The diagram therefore never sends an invented `ServerHello`, `HandshakeError`, error-bearing `ServerReady`, or zero-ID `result`. A transport close/local error is not a complete remote typed-error binding. See [RFC B1](../../rfcs/0001-public-idl-layout.md#b1-typed-handshake-rejection).

## Runtime validation and security obligations

This section traces obligations in the defining drafts; it does not claim generated code implements them or choose between conflicting requirements.

Generated Rust/Go message types do not implement Noise handshakes, PSK lookup,
record encryption, fresh-key confirmation or device lifecycle policy. RFC
0007's [carrier candidates](../transports/noise-bindings.md) would authenticate
records and reconstruct bounded envelopes before decoding these same types;
record counters/context are not `Frame` fields. Proposed `SNTR-SC-*` and
`SNTR-DAUTH-*` acceptance work stays separate from the current TLS/core
requirements and schema tests below.

| Runtime responsibility | Defining requirements | Schema/codec boundary |
|---|---|---|
| Bound serialized envelope before full allocation/parse; bound recursion and allocation; reject malformed lengths/varints and invalid UTF-8 strings without panic | [Serialization `SNTR-SER-006/007`](../core/serialization.md#1-protocol-requirements), [framing `SNTR-WIRE-005/006`](../core/framing.md#1-protocol-requirements-envelope), [security `SNTR-ASEC-020/021/023`](../security/authentication-security.md#2-request-security-hooks-per-connectionsession-limits) | Draft default 1,048,576 serialized bytes and depth 32 are not `.proto` constraints; adapters/runtime enforce them |
| Validate version, zero/nonzero correlation IDs, legal state/direction, method syntax, outcome presence and nonzero failure code before dispatch | `SNTR-SER-005/011/020`, `SNTR-WIRE-002…005/020/021`, [RPC `SNTR-RPC-001/020/030`](../core/rpc.md) | A successful unmarshal does not prove protocol validity; stale-ID and late-result handling are blocked |
| Observe raw reserved tags and decide raw-oneof duplicate policy | `SNTR-SER-008`, `SNTR-WIRE-002/008` | Reserved declarations do not reject bytes; generated objects may have discarded evidence (RFC B4/B6) |
| Ignore unknown metadata, reject unknown body, never interpret unknown fields as auth/capability support | `SNTR-SER-003/004/021`, `SNTR-WIRE-004`, [versioning `SNTR-VER-004`](../core/versioning.md#1-protocol-requirements) | No specified discriminator separates unknown body from metadata (RFC B5); do not guess a tag range |
| Verify TLS 1.3, trust chain and endpoint hostname before credential/payload transmission; no plaintext fallback | [Transport security `SNTR-TSEC-001…004/007/009/020`](../security/transport-security.md) | IDL contains no TLS enforcement; permitted development plaintext remains restricted |
| Keep credentials opaque/sensitive; avoid logging/persistence/echo and URLs; authorize before effects and enforce expiry/revocation | [Authentication `SNTR-AUTH-001…010/030/031`](../core/authentication.md), [security `SNTR-ASEC-001…006/011/022/024/040/041`](../security/authentication-security.md) | Debug/String/JSON/reflection can leak credential bytes; no redaction annotation exists |
| Generate fresh opaque diagnostic connection IDs with at least 128-bit entropy; never accept them as auth/resume authority | [Sessions `SNTR-SESS-002/010/020`](../core/sessions.md), `SNTR-ASEC-010` | A UTF-8 string field does not supply randomness, freshness or privilege checks |
| Preserve opaque bytes, enforce the same byte budgets for plaintext/ciphertext, keep E2EE and logical operation keys above core | [Opaque payloads `SNTR-OPQ-001…006/010/020`](../security/opaque-payloads.md), `SNTR-RPC-007/010` | No decryption, format negotiation, transformation or automatic deduplication |
| Separate credential/token replay, correlation collisions, operation-key dedup and event duplicates | [Replay protection `SNTR-RPL-001/002/010…014/020/030`](../security/replay-protection.md) | TLS is not application idempotency; ID reuse is contradictory (RFC B3); operation keys stay in payloads |
| Enforce deadlines, concurrency/rate/queue/event bounds, backoff and principal isolation; sanitize typed errors and map unknown enum values for reporting | [Reliability `SNTR-REL-001…010/020/030/031`](../core/reliability.md), [errors `SNTR-ERR-003…006/010/020/021`](../core/errors.md), `SNTR-ASEC-020…024` | No codec-provided timer, authorization, error sanitizer or reporting mapping; terminal races need RFC B10 |

Handshake timer defaults to 5 s (`SNTR-HS-002/011`). `timeout_ms=0` is a bounded host default whose numeric value is deployment-documented (`SNTR-RPC-004`). The concurrency minimum is 16 unless a lower limit is negotiated (`SNTR-RPC-008`), but no limit-negotiation fields exist. Maximum credential/method/connection-ID/error-text lengths and future capability/session extension counts/byte lengths need an explicit bounded contract; the overall envelope ceiling is not a concrete extension-binding design (RFC B7).

A payload of exactly 1 MiB exceeds the default 1 MiB envelope once tags/lengths and enclosing fields are included. The 1 MiB payload fixtures in `SNTR-RPC-900` and `SNTR-OPQ-900` therefore need reconciliation with `SNTR-WIRE-006`; this reference does not silently raise a bound (RFC B8). Whole-message binary serialization is non-canonical (`SNTR-SER-002/901`), so logical equivalence checks differ from bit-exact preservation of the payload bytes.

## Blocking inconsistencies and deferred extensions

The complete blocker record is [RFC §10](../../rfcs/0001-public-idl-layout.md#10-unresolved-questions-and-blockers). In particular:

1. **B1:** No legal typed handshake rejection or general unsolicited typed session-close carrier; required failure semantics outstrip the declarations.
2. **B2:** `SNTR-EVENT-005/900` says ignore pre-ACTIVE events without failing handshake; `SNTR-HS-012/900` and `SNTR-WIRE-003/011` require rejection/failure.
3. **B3:** `SNTR-RPL-012` rejects completed stale IDs; `SNTR-RPC-002/010` and `SNTR-WIRE-010` permit reuse after terminal result.
4. **B4:** Standard oneof decoding uses last-one-wins/merge semantics; it does not reject every encoding containing multiple alternatives as framing prose implies.
5. **B5:** Unknown metadata and unknown future body alternatives have no specified discriminator; no inferred reserved future-body range is authorized.
6. **B6:** Reserved tags 16/17 are not automatically runtime-rejected by codecs; field names are not binary metadata.
7. **B7:** Capability confirmation/binding and session extension mechanics, byte/count bounds, token lifetimes and replay windows remain absent.
8. **B8:** 1 MiB payload fixtures cannot fit the default 1 MiB serialized envelope.
9. **B9 — layout authority resolved:** Explicit user direction makes `proto/syntra/v1` the sole source of truth and removes the old schema tree. The FILE/source break remains a known breaking difference; downstream imports/bindings must migrate. No formal maintainer quorum or behavioral RFC acceptance is claimed.
10. **B10:** Unknown handler outcome, cancellation-versus-deadline precedence, local abandonment, and late/unknown result treatment conflict across error/RPC/framing/reliability drafts.
11. **B11:** Renames to `ServerHello`/`RpcResponse`/`Event`, auth rounds, session/resume/close/error types, subscription/replay/cursor/ack/stream state, capability records, logical operation-ID fields and new errors are deferred with owning requirements and rationale. None is allocated here.

There is no separate session handshake (`SNTR-SESS-001`), no resumption absent an approved capability (`SNTR-SESS-006`, `SNTR-ASEC-007`), and no concrete capability binding (`SNTR-CAP-001…005`). Post-ACTIVE generic application RPCs do not authorize invented pre-ACTIVE messages or same-connection principal changes (`SNTR-AUTH-004/007/010`, `SNTR-SESS-007`). Capability examples in the drafts are not implemented capability records.

## Verification and conformance boundary

The following schema/codec checks are documented. The
[validation record](validation.md) preserves the original 12-test Python run
and language results; post-deletion results for the updated 13-test Python
suite are pending. They do not establish runtime conformance:

| Test location | Schema/codec checks | Runtime coverage not established by those checks |
|---|---|---|
| [tests/schema/test_schema.py](../../tests/schema/test_schema.py) | All eight files, symbols, field numbers/types/presence, reservations, exact enum names/numbers, local import graph, archived descriptor hash and historical declarations, sole-source regression | Formal RFC acceptance, state validation, raw reserved-tag rejection, security policy enforcement |
| Separate language implementation projects (out of scope for this repository; see [MIGRATION.md §10](../../MIGRATION.md)) | Language codec suites (Go/Rust round trips, body/outcome cases, unknown-field and enum behavior, historical-layout fixture interchange) moved with the implementations | TLS, auth, replay windows, deadline/cancel scheduling, resource isolation, sanitized application reporting |

Trace codec fixtures to `SNTR-SER-900/901`, `SNTR-WIRE-007/900`, `SNTR-ERR-900`, and `SNTR-OPQ-900`; keep runtime assertions distinct. Unknown-enum tests need separate raw-decoder and reporting-policy assertions. Reserved declarations can be checked statically; reserved-tag rejection needs raw-byte runtime tests. A no-body/missing-outcome decode test demonstrates representability, not semantic rejection by a codec.

The original executed schema checks included `buf lint` (`STANDARD`, no exceptions), `buf build`, generation, historical-baseline FILE break detection and a separate passing WIRE audit. Pinned tools and reproducible commands are in [generation](generation.md); the unchanged initial baseline and actual historical provenance are in [compatibility](compatibility.md). Updated comparisons read the immutable `historical.json` FileDescriptorSet and verify `historical_image_sha256`, without a Git checkout or duplicate schema tree; source paths/hashes remain provenance in `historical_sources`. B9 records the implemented layout decision. The [core conformance mapping](../core/conformance.md) and [security test plan `SNTR-STEST-001…011/900`](../security/test-plan.md) additionally require live state/timer/secure-adapter tests: invalid certificates/hostname, expired/revoked credentials, unauthorized requests, invalid resumption attempts, oversize/truncated inputs, resource exhaustion, downgrade attempts, cross-session misuse and diagnostic hygiene. Blocked cases need approved expectations before a runtime conformance claim. This reference reports no runtime conformance implementation or test pass.
