# RFC 0001: Public v1 IDL source layout

- RFC: 0001
- Title: Public v1 IDL source layout
- Author(s): oscarlaw
- Status: Accepted
- Date: 2026-10-19
- Target version: v1 pre-stable source-layout migration
- Relates to: [ADR-002](../specifications/decisions/ADR-002-protobuf-idl.md), [ADR-009](../specifications/decisions/ADR-009-versioning-compatibility.md), [architecture §8](../specifications/architecture.md#8-requirement-ownership-authoritative-sources), `SNTR-SER-001`, `SNTR-VER-001…005`, `proto/syntra/v1/`, [historical descriptor archive](../compatibility/v1-initial/README.md)
- Reviewers: oscarlaw (self-review disclosed; sole active maintainer)

> **Recorded user-directed layout decision — implemented:**
> `proto/syntra/v1` is the sole Protobuf source of truth; the old
> `schema/syntra/v1` tree is removed. B9 layout authority is resolved. The
> FILE/source incompatibility remains a known breaking difference, not a
> pending layout approval. Historical declarations and source provenance
> are retained in the immutable compatibility archive. This records explicit
> user direction, not formal maintainer quorum or RFC acceptance. This RFC
> remains Draft for the remaining protocol/security blockers and review;
> current structural execution is recorded in the release-readiness audit;
> behavioral acceptance and interoperability remain pending.

Accepted 2026-10-30 via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)
(disclosed self-approval; sole active maintainer per `GOVERNANCE.md` Sec. 3).
B1–B8/B10 are resolved by accepted RFCs 0003–0005,
[RFC 0008](0008-mobile-lifecycle-and-v1-acceptance.md) D1 (raw-wire multiplicity,
body/metadata partition and reserved-tag validation), and accepted
RFCs 0006/0007/0010 for the required recovery/SC1/lifecycle target; the
disposition table in §10 below records the mapping. Owning-file edits land in
the acceptance PR. The [current audit](../audits/v1-release-readiness.md) records a
subsequent successful run of the 13-test archive-based schema suite; older
pending-run statements below describe the earlier record, not this new run.

## 1. Summary

This RFC records the user-directed physical split of the existing public `syntra.v1` Protobuf declarations across seven files under the sole authoritative source root `proto/syntra/v1/`, preserving every message name, field name, number, type, presence rule, oneof, reserved value, enum name/number, and existing Go package option. Initiators and hosts keep the same binary messages; source consumers, generators, and descriptor consumers need an explicit migration. `session.proto` and `capabilities.proto` are intentionally documentation-only entry points. This is a binary WIRE-compatible but source/descriptor FILE-breaking layout change. The original schema tree is removed after archiving its historical declarations and provenance. Layout authority is resolved by user direction; core/security specifications remain drafts pending approval, and their unresolved behavioral conflicts remain blockers here. No runtime conformance or formal maintainer/RFC approval is claimed.

## 2. Motivation

The historical [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto) grouped the envelope, handshake, RPC, cancellation, and notifications together; [error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto) owned the shared error registry. A public layout organized by concern makes declarations easier to locate and dependencies easier to audit. It also needs an honest account of what those declarations cannot express: typed handshake rejection, capability negotiation, and session extensions have no concrete binding today.

The original proposal kept the historical sources while awaiting a layout decision. That preservation plan is superseded by explicit user direction to remove the old tree and make `proto/syntra/v1` the sole source of truth. [ADR-002 §Decision](../specifications/decisions/ADR-002-protobuf-idl.md#decision), `SYN-ARCH-040`, and [serialization `SNTR-SER-001`](../specifications/core/serialization.md#1-protocol-requirements) identify that current representation root. This recorded layout decision does not resolve behavioral conflicts in the drafts or establish formal RFC acceptance.

## 3. Proposal

### Physical declaration ownership

All seven files use `syntax = "proto3"`, `package syntra.v1`, and the unchanged option `go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"`.

| Authoritative file | Physically declared symbols | Direct imports |
|---|---|---|
| [envelope.proto](../proto/syntra/v1/envelope.proto) | `Frame` | `events.proto`, `handshake.proto`, `rpc.proto` |
| [handshake.proto](../proto/syntra/v1/handshake.proto) | `ClientHello`, `ServerReady` | None |
| [session.proto](../proto/syntra/v1/session.proto) | None; documentation only | None |
| [rpc.proto](../proto/syntra/v1/rpc.proto) | `RpcRequest`, `RpcResult`, `Cancel` | `errors.proto` |
| [events.proto](../proto/syntra/v1/events.proto) | `Notification` | None |
| [capabilities.proto](../proto/syntra/v1/capabilities.proto) | None; documentation only | None |
| [errors.proto](../proto/syntra/v1/errors.proto) | `RpcError`, `ErrorCode` | None |

Import paths are relative to the `proto` module root, e.g. `syntra/v1/rpc.proto`. These are physical definitions, not forwarding stubs. The implemented layout retains Buf `STANDARD` lint with no exceptions and `FILE` breaking checks. Public imports are forbidden by `IMPORT_NO_PUBLIC`, which is included in `STANDARD`; an `import public` compatibility shim is therefore excluded. There are no external schema imports, `google.protobuf.Any`, application services, or replacement encoding.

### Representation diff and implemented authority-path change

The declaration diff is relocation only: historical `session.proto` splits into envelope/handshake/rpc/events; historical `error.proto` becomes `errors.proto`. The two documentation-only files add no messages, enums, fields, or runtime extension points. The [reference](../specifications/schema/reference.md#message-and-field-reference) inventories every field. In particular the unchanged envelope remains:

```proto
message Frame {
  uint32 version = 1;
  uint64 request_id = 2;
  reserved 16, 17;
  reserved "event", "resume", "ack";
  oneof body {
    ClientHello hello = 10;
    ServerReady ready = 11;
    RpcRequest request = 12;
    RpcResult result = 13;
    Cancel cancel = 14;
    Notification notification = 15;
  }
}
```

No new behavioral requirement IDs are allocated. Client and server obligations remain those cited from the defining drafts, subject to the blockers in §10. The user-directed layout migration updates representation-owner paths in architecture §8, ADR-002, serialization `SNTR-SER-001`, requirement indexes, and schema references throughout core/security documentation to `proto/syntra/v1`. Those path changes record the sole-source layout decision; they add no wire types or semantics and do not claim formal maintainer quorum or behavioral approval. The FILE/source break remains explicitly documented.

### Delivered versus blocked A–G coverage

“Delivered” below means represented by the current declarations and documented here, not runtime implementation or behavioral approval.

| Area | Delivered | Blocked/deferred requested scope and reason |
|---|---|---|
| A — Envelope | `Frame`, tags 1/2 and 10–15, original reservations | Additional variants and stronger raw-wire discrimination need B1/B4/B5/B6; no invented discriminator |
| B — Handshake/authentication | `ClientHello`, `ServerReady`, version range and opaque credential | `ServerHello` rename, auth rounds, typed rejection, advertised limits need B1/B7/B11 |
| C — Sessions | Documentation-only `session.proto`; implicit connection-bound establishment | Resume/close/session-control messages and dedicated session errors need B1/B7/B11 |
| D — RPC | `RpcRequest`, `RpcResult`, `Cancel`; correlation, opaque payload, relative budget | `RpcResponse` rename and logical operation-ID fields deferred; B3/B8/B10/B11 |
| E — Events | `Notification.payload`; application-owned subscription RPCs | `Event` rename, subscription/replay request/response types, cursor/ack/stream state need B2/B7/B11 |
| F — Capabilities | Documentation-only `capabilities.proto` | Capability records, parameters, lists, required/optional flags and confirmation/limit fields need B7 |
| G — Errors | `RpcError`, unchanged `ErrorCode` 0–16; proposed category mapping below | New errors/numbers, handshake/session error carriers, outcome guarantees need B1/B10/B11 |

### State-machine delta and defaults

There is no proposed state-machine change. The successful flow follows [handshake `SNTR-HS-001…005/010/020`](../specifications/core/handshake.md#1-state-machine). This diagram deliberately provides no invented failure packet:

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  Note over C,H: Secure transport verified before credential presentation
  C->>H: CONNECTED → NEGOTIATING: Frame(version=max, request_id=0, hello)
  H->>H: Validate range, select highest overlap → AUTHENTICATING
  H->>H: Validate opaque credential and bind principal
  H-->>C: Frame(version=selected, request_id=0, ready{connection_id})
  Note over C,H: ACTIVE; session lifetime equals connection lifetime
  C->>H: Frame(version=selected, request_id=7, request)
  H-->>C: Frame(version=selected, request_id=7, result{payload})
  Note over C,H: Rejection/timeout → CLOSING → CLOSED (resolved by accepted RFC 0003 D1: local typed cause, native peer signal, no error Frame)
```

Draft defaults are a 1,048,576-byte serialized envelope (`SNTR-WIRE-006`), embedded-message nesting depth 32 (`SNTR-SER-006`), a 5-second handshake timer (`SNTR-HS-002/011`), and at least 16 concurrent RPCs unless a lower bound was negotiated (`SNTR-RPC-008`). `timeout_ms=0` chooses a documented bounded host default; its numeric default is not specified (`SNTR-RPC-004`). Negotiated limit overrides have no current binding (B7), and the 1 MiB payload fixtures contradict the envelope bound (B8). No new default is chosen here.

## 4. Detailed design

### Encoding, presence, correlation, and cancellation

Protobuf binary remains the encoding; transport framing is separate ([serialization `SNTR-SER-001/002`](../specifications/core/serialization.md#1-protocol-requirements), [framing `SNTR-WIRE-001`](../specifications/core/framing.md#1-protocol-requirements-envelope)). Serialization is non-canonical: interoperability compares decoded logical values, not serialized byte equality. Payload bytes themselves remain bit-exact.

Unlabelled scalar/string/bytes/enum fields have implicit proto3 presence. Omitted and explicitly default-valued `timeout_ms`, credential, and ordinary payload fields cannot be distinguished after decoding. Message-valued oneof alternatives have explicit presence, and `RpcResult.outcome` distinguishes selected empty success bytes from an unset outcome. `Cancel{}` has no fields but selecting it in `Frame.body` is observable. A generated oneof enforces only the decoded case, not rejection of multiple alternatives in raw bytes (B4).

`Frame.request_id` is the sole connection-scoped correlation ID, not authentication, durable identity, or an idempotency key ([RPC `SNTR-RPC-002/007/010`](../specifications/core/rpc.md#1-protocol-requirements)). Hello/ready/notification use zero; request/result/cancel use nonzero. Core permits reuse after terminal result, but security rejects stale IDs after completion (B3). `Cancel` requests best-effort cancellation without rolling back committed effects; terminal-result and deadline race policies need reconciliation (B10).

### Proposed error-category mapping

These 14 user-facing categories are proposed mappings into the existing registry, not new enum declarations or additional numbers. Shorthand names below expand to `ERROR_CODE_*`. State and carrier availability still govern emission; a mapped code is not permission to send an illegal pre-ACTIVE `result`. [Errors `SNTR-ERR-001/002/020`](../specifications/core/errors.md#1-protocol-requirements) owns the registry and application-mapping policy.

| # | Category (including descriptive aliases) | Existing registry mapping | Binding/rationale |
|---|---|---|---|
| 1 | Invalid envelope | `INVALID_ARGUMENT (3)` | Shape errors; size exhaustion maps separately; `SNTR-SER-005/007`, `SNTR-WIRE-003` |
| 2 | Unsupported protocol version | `UNIMPLEMENTED (12)` or `FAILED_PRECONDITION (9)` | The handshake table permits both; selecting one interoperable policy and its carrier is blocked by B1 |
| 3 | Unsupported feature | `UNIMPLEMENTED (12)` | Unsupported required profile and unknown profile input fail under the profile's own accepted negotiation RPC (recovery: `UNIMPLEMENTED`, `SYN-URP-010`); no generic advertisement carrier exists (accepted RFC 0005 D1); `SNTR-CAP-004/020`, B7 |
| 4 | Handshake rejected | Cause-specific `UNAUTHENTICATED (16)`, `PERMISSION_DENIED (7)`, `FAILED_PRECONDITION (9)` or `UNIMPLEMENTED (12)` | No standalone category or legal typed rejection carrier; handshake §5 and B1 |
| 5 | Authentication required | `UNAUTHENTICATED (16)` | Missing credential/required authentication; `SNTR-AUTH-009`, `SNTR-ERR-002`; no human-account assumption |
| 6 | Authentication failed | `UNAUTHENTICATED (16)` | Invalid/expired/revoked credentials; generic disclosure; `SNTR-ASEC-011`, B1 |
| 7 | Permission denied | `PERMISSION_DENIED (7)` | Authenticated principal lacks access; `SNTR-RPC-032`, `SNTR-ASEC-022` |
| 8 | Invalid argument | `INVALID_ARGUMENT (3)` | Invalid argument/method syntax, not arbitrary payload interpretation; `SNTR-RPC-001/003` |
| 9 | Unknown method | `UNIMPLEMENTED (12)` | `SNTR-ERR-002`; a missing application target is separately `NOT_FOUND (5)` |
| 10 | Deadline exceeded | `DEADLINE_EXCEEDED (4)` | Call/handshake budget expiry, not rollback; `SNTR-RPC-004`, `SNTR-HS-011`, B1/B10 |
| 11 | Resource exhausted | `RESOURCE_EXHAUSTED (8)` | Size/concurrency/rate/queue budgets; `SNTR-WIRE-006`, `SNTR-ASEC-020` |
| 12 | Session expired | `UNAUTHENTICATED (16)`; `UNAVAILABLE (14)` for host shutdown | `SNTR-SESS-005`; no new session error carrier, B1/B7 |
| 13 | Protocol violation | `INVALID_ARGUMENT (3)` for shape, `FAILED_PRECONDITION (9)` for state, `UNIMPLEMENTED (12)` for unknown variant | Framing §4; no new numeric category; raw-field/state conflicts B2–B6 |
| 14 | Internal error | `INTERNAL (13)` | Generic sanitized text; `SNTR-ERR-002/003` |

> Correction (2026-10-31): row 3 aligned with accepted [RFC 0005](0005-negotiation-bounds-identifiers.md) D1 per [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md) — there is no generic capability advertisement carrier; optional-profile input fails under the profile's own negotiation contract, not through a handshake advertisement channel. The prior wording ("unknown optional advertisement is ignored") described the pre-D1 model.

The other existing codes, including `CANCELLED (1)`, `UNKNOWN (2)`, `NOT_FOUND (5)`, `ALREADY_EXISTS (6)`, `ABORTED (10)`, `OUT_OF_RANGE (11)`, `UNAVAILABLE (14)`, and `DATA_LOSS (15)` retain their meanings; the category table neither replaces the full registry nor limits its use. Zero remains invalid for failure. No category gets a new number. Unknown received enum values are mapped for application reporting by runtime policy, with the raw number retained diagnostically where possible; codecs do not perform that mapping automatically (`SNTR-ERR-005/010`).

### Capability, session, and event boundaries

[Sessions `SNTR-SESS-001/003/006…008`](../specifications/core/sessions.md#1-protocol-requirements) explicitly defines no separate v1 session handshake and no implicit resumption. [Capabilities `SNTR-CAP-001…005`](../specifications/core/capabilities.md#1-protocol-requirements) requires a capability-specific RFC to choose identifiers and an explicit binding; examples in prose allocate no fields or methods. Documentation-only files therefore accurately describe the available contract.

[Authentication `SNTR-AUTH-004/010`](../specifications/core/authentication.md#1-protocol-requirements) places optional follow-up authentication in application-defined RPCs after ACTIVE and prohibits same-connection reauthentication without an RFC. It does not authorize a new pre-ACTIVE auth-round message or a principal swap. [Events `SNTR-EVENT-002…004/008…010`](../specifications/core/events.md#1-protocol-requirements) leaves event/stream IDs, subscriptions, replay, cursors and cancellation bindings inside application payloads/RPCs. There is no core acknowledgment or durable stream-state record. B7/B11 lists the work needed before these can become concrete IDL.

## 5. Alternatives considered

1. **Do nothing: keep the two historical files as the only public layout.** This would have avoided a FILE break, but did not provide the requested concern-based public source layout or expose the binding gaps as clearly. Superseded by the recorded user-directed sole-source decision.
2. **Keep old paths as `import public` forwarding shims.** Rejected for this proposal: `STANDARD` includes `IMPORT_NO_PUBLIC`; shims would require lint exceptions, would not restore all generated API identities, and would obscure physical declaration ownership.
3. **Add aliases/renames and speculative session/capability/auth messages now.** Rejected: Protobuf has no source-compatible message alias mechanism here; extra types/fields would create an unsupported public contract and evade the pending behavior/security decisions.
4. **Change encoding or use `google.protobuf.Any` for extensions.** Rejected: [ADR-002](../specifications/decisions/ADR-002-protobuf-idl.md) freezes Protobuf, and unbounded type URLs/extension interpretation would introduce machinery absent from the specified opaque-byte contract.

## 6. Compatibility

| Dimension | Impact |
|---|---|
| Binary WIRE | Compatible for the preserved declarations: identical tags, wire types, package/type names, oneofs, enum values, and reservations; no changed negotiated version |
| Source/API | Breaking: downstream proto imports and file-derived generated modules/descriptors change; the same Go package option does not preserve every file-level API |
| Descriptor FILE | Breaking: definitions leave historical `syntra/v1/session.proto`/`error.proto`; file ownership, dependencies, descriptor paths, and source locations change |
| Behavior/security | Not certified by the split; contradictory draft requirements remain unresolved |

Buf `FILE` is deliberately stricter than `WIRE`. A historical-baseline FILE comparison is expected to flag moved/deleted declarations even when a WIRE comparison finds no binary change. A WIRE pass alone is not a source-compatibility result or formal migration approval; the layout decision is separately recorded as user direction. The configured category stays FILE without hiding the break. Full descriptor-set byte equality is neither expected nor an acceptance criterion.

No on-wire layout negotiation, downgrade, or capability is introduced. Old and new binaries can exchange the same messages subject to their behavior; current source builds use only `proto`. Loading the archived historical and current descriptor sets into the same pool is invalid: they duplicate `syntra.v1` symbols, and the historical and current `syntra/v1/session.proto` identities collide while containing different declarations. There is no dual-registration, alias bridge or second live source root.

The pre-stable source transition is implemented by user direction: `proto/syntra/v1` is authoritative and the old tree is removed. Downstream consumers must migrate direct imports and regenerate bindings; no retained live historical source window is promised. [MIGRATION.md](../MIGRATION.md) and [CHANGELOG.md](../CHANGELOG.md) record the decision and FILE-break inventory. The existing initial `image.json` baseline remains unchanged. Historical declarations are archived in immutable `compatibility/v1-initial/historical.json`, generated before removal from the actual unchanged sources at commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9`. The manifest retains `historical_sources` path/hash provenance and adds `historical_image_sha256`. Tests verify the archive hash and historical declarations without a Git checkout or duplicate tree; post-deletion results remain pending. Any later wire-breaking resolution needs its own versioning analysis under `SNTR-VER-003/005`, rather than being bundled into this layout change.

## 7. Security considerations

The schemas contain sensitive credentials but no redaction or runtime enforcement. Generated debug/String/JSON/reflection output can disclose `ClientHello.credential`; [authentication security `SNTR-ASEC-001/003/011/024`](../specifications/security/authentication-security.md#1-protocol-requirements) governs retention, carriage and generic error messages. `RpcError.message` must not leak credentials, tokens, raw bytes, stack traces or private diagnostics (`SNTR-ERR-003`). `connection_id` and `request_id` grant no authority; a diagnostic ID is never a resume token (`SNTR-SESS-002`, `SNTR-ASEC-010`).

Public traffic requires verified secure transport before credentials or application data, including TLS 1.3 and endpoint verification ([transport security `SNTR-TSEC-001…004/007/009`](../specifications/security/transport-security.md#1-protocol-requirements)). Opaque bytes remain uninterpreted and bit-preserved; application encryption neither replaces TLS nor adds core E2EE ([opaque payloads `SNTR-OPQ-001…006`](../specifications/security/opaque-payloads.md#1-protocol-requirements)).

Runtime validators/adapters need allocation/size/depth/time/rate/concurrency bounds before dispatch and authorization before handler effects (`SNTR-SER-006/007`, `SNTR-ASEC-020…023/040/041`). Reserved-tag detection and raw oneof duplicate policy cannot be inferred from generated decoded objects (B4/B6). Replays of credentials, tokens, correlation IDs, operation keys, and events require separate defenses ([replay protection `SNTR-RPL-001/002/010…014`](../specifications/security/replay-protection.md#1-protocol-requirements--class-separation)); TLS does not prove idempotency or exactly-once execution. No implementation of these obligations is claimed by this RFC.

## 8. Test plan and acceptance criteria

The checked schema/codec criteria below record the original execution before
the old tree's removal; results are preserved as historical evidence in the
[validation record](../specifications/schema/validation.md). Results for the
updated archive-based 13-test Python suite (original 12 plus a sole-source
regression check) remain pending. Unchecked runtime and review criteria
remain pending; B9 layout authority is resolved by user direction.

- [x] Original representation audit: exact declaration comparison, package options, seven files; session/capabilities contain no declarations.
- [x] Original tooling run: pinned versions, STANDARD lint/build/generation, real historical WIRE audit and expected FILE failures retained; initial snapshot and reproducible commands documented.
- [x] Descriptor checks in [tests/schema/test_schema.py](../tests/schema/test_schema.py): dependency closure, no external/Any/public imports, reservations, exact declaration registry, historical/current fixture interpretation, renumbering-negative.
- [x] Go/Rust codec fixtures: every body/outcome, selected empty success, empty cancel, arbitrary/non-UTF-8 payloads, unknown metadata/numeric enums, malformed inputs and raw-oneof limitations. Shared fixture decoding is not live socket interop or implemented error-reporting policy.
- [ ] Post-deletion validation: execute the archive-based hash/declaration/WIRE/FILE checks and 13-test descriptor/tooling suite, verify the sole-source regression, and record actual results. Original run results are not evidence of this execution.
- [ ] Runtime conformance fixtures, separate from codec smoke tests: state legality, no dispatch on malformed/unauthorized input, auth and revocation, request-ID reuse policy, timers/cancel races, reserved raw-tag rejection, size/depth/pre-allocation limits, capability confirmation, bounded queues and secure-transport failure behavior. Blocked expectations stay explicitly pending until §10 is resolved.
- [ ] Interop: mandatory-only initiator/host, historical/current message compatibility and at least two transport profiles, following [core conformance](../specifications/core/conformance.md); the historical archive is not a second live source root, and no optional-feature claim is made without a named approved capability RFC.
- [ ] Resolve remaining protocol/security blockers and obtain maintainer/security review before describing the behavioral RFC as accepted or v1 as stable. The implemented user-directed layout decision and published migration notes do not establish those approvals.

| Requirement trace | Planned evidence | Limitation |
|---|---|---|
| `SNTR-SER-001/002/900/901`, `SNTR-WIRE-007`, `SNTR-VER-005` | Python inventory + Go/Rust codec fixtures | Codec equality/presence and reserved declarations only; not runtime rejection |
| `SNTR-ERR-001/005/900` | All enum values, zero-error negative case, unknown numeric fixture plus explicit reporting helper | Raw decoding alone does not sanitize/map/report errors |
| `SNTR-WIRE-002…006/008/900`, `SNTR-SER-005…008` | Runtime validation negatives and raw-byte fixtures | B1/B4/B5/B6/B8 need approved expectations |
| `SNTR-HS-900`, `SNTR-RPC-900/901`, `SNTR-EVENT-900`, `SNTR-CAP-900` | State-machine, correlation, deadlines, events and negotiation harness | B1/B2/B3/B7/B10 prevent a complete pass claim |
| `SNTR-STEST-001…011/900`, `SNTR-RPL-900/901`, `SNTR-OPQ-900/901` | [Security test plan](../specifications/security/test-plan.md) and live secure-adapter tests | TLS, revocation, replay, resource isolation and diagnostic hygiene are not schema codec coverage |

Schema/codec and Buf results are limited to the linked validation record.
No transport/security runtime conformance result or maintainer approval is asserted.

## 9. Drawbacks and risks

The split breaks source consumers even while binary communication remains compatible. Descriptor identity can be mistaken for wire identity, and a documentation-only file can be mistaken for a supported extension. A sole authoritative source root, immutable historical descriptors, declaration comparison and a visible FILE-break inventory mitigate these risks. Runtime gaps are substantial: generated code can represent invalid protocol states and erase information needed for raw-wire validation. Until the draft conflicts are resolved, publishing the IDL cannot honestly imply a complete interoperable v1 runtime.

## 10. Unresolved questions and blockers

B9 stays resolved (user-directed layout, known FILE break). B1–B10 are
**resolved by accepted contracts** in the 2026-10-30 acceptance wave
([Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)); the mapping:

| Blocker | Resolved by | Disposition |
|---|---|---|
| B1 typed pre-`ACTIVE` carrier | RFC 0003 D1 | Resolved: no error `Frame`; local typed cause + native peer signal |
| B2 pre-ACTIVE notifications | RFC 0003 D2 | Resolved: deterministic fail-close |
| B3 stale `request_id` reuse | RFC 0004 D1/D2 | Resolved: permanent connection-local non-reuse; high-water ordered admission |
| B4 oneof raw-wire multiplicity | RFC 0008 D1 | Resolved: bounded raw-wire validation; duplicate bodies rejected |
| B5 unknown body vs metadata | RFC 0008 D1 | Resolved: 10..15 tolerated/bounded; 18..31 future-body rejected `UNIMPLEMENTED` |
| B6 reserved tags runtime validation | RFC 0008 D1 | Resolved: 16/17 rejected at top-level frame/body position irrespective of metadata |
| B7 capability/session binding and bounds | RFC 0005 D1 (+ accepted RFC 0006 negotiation) | Resolved: post-ACTIVE profile contracts; no generic enumeration |
| B8 payload vs envelope size | RFC 0005 D3 | Resolved: 1 MiB total serialized Frame; fixtures corrected |
| B10 races/tie/late results | RFC 0004 D4 (+ RFC 0008 D2) | Resolved: serialized gate; tie selects `DEADLINE_EXCEEDED`; late results per RFC 0004 |
| B9 layout | B9 itself | Resolved and implemented (sole `proto/syntra/v1` source) |

B11 remains the deferred-additions record: the deferrals are unchanged, and
none of them is authorized by this acceptance. The per-block prose below the
table is retained **as historical review context only**: it records why each
blocker was raised and its wording predates the table's approved
dispositions. It no longer states binding requirements; the accepted
dispositions in the table (Decision 0002 and the corresponding accepted RFC
decisions) are the operative record, and the prose must not be read as
leaving any listed disposition awaiting approval.

### B1. Typed handshake rejection

[Handshake `SNTR-HS-003/004/011/012/020/030/040`](../specifications/core/handshake.md), [authentication `SNTR-AUTH-006/009`](../specifications/core/authentication.md), and [errors `SNTR-ERR-004`](../specifications/core/errors.md) require a typed terminal handshake failure. The only error carrier is `Frame.result → RpcResult.error`; [framing `SNTR-WIRE-003`](../specifications/core/framing.md) requires its ID to be nonzero, while hello/ready use zero and `SNTR-HS-012` forbids pre-ACTIVE results. `ServerReady` has no error outcome. Neither a zero-ID result nor an invented nonzero-ID handshake RPC is legal. Closure/local reporting does not satisfy the promised remote typed error. An approved carrier/state/profile binding is needed, including unsolicited connection/session failure signaling after ACTIVE when no RPC is available. The architecture §12.1 failure illustration does not allocate that binding.

### B2. Pre-ACTIVE event conflict

[Events `SNTR-EVENT-005/900` and §4](../specifications/core/events.md) defaults to ignoring pre-ACTIVE notifications with a diagnostic without failing the handshake. [Handshake `SNTR-HS-012/900`](../specifications/core/handshake.md) requires failure/close, and [framing `SNTR-WIRE-003/011`](../specifications/core/framing.md) requires rejection. Select one behavior and align the fixtures; this RFC endorses neither conflicting expectation.

### B3. Completed request-ID reuse conflict

[Replay protection `SNTR-RPL-012/030/900`](../specifications/security/replay-protection.md) rejects stale IDs arriving after a terminal result. [RPC `SNTR-RPC-002/010`](../specifications/core/rpc.md) and [framing `SNTR-WIRE-010`](../specifications/core/framing.md) expressly permit reuse after terminal result. An old replay and permitted new attempt cannot be distinguished by ID alone. Approve reuse versus non-reuse semantics, exhaustion policy, bounded tracking lifetime and cross-connection rules before claiming replay conformance; adding an operation-ID field does not silently resolve this contradiction.

### B4. Oneof raw-wire multiplicity

[Framing `SNTR-WIRE-002/003`](../specifications/core/framing.md) says Protobuf enforces a single member. Generated oneofs expose one decoded case, but different alternatives can occur in the same encoded message; the last encountered alternative wins, and repeated message-valued occurrences can merge. That applies to both `Frame.body` and `RpcResult.outcome`. Post-decode inspection cannot prove only one alternative occurred on the wire. Decide whether the contract accepts standard merge semantics or requires bounded raw-wire validation, and define duplicate-same-field handling; do not claim generated codecs already reject multi-field input.

### B5. Unknown body versus metadata discriminator

[Serialization `SNTR-SER-003/004/021`](../specifications/core/serialization.md), [framing `SNTR-WIRE-004`](../specifications/core/framing.md), and [versioning `SNTR-VER-004`](../specifications/core/versioning.md) require ignoring unknown metadata but rejecting unknown bodies. An unknown field carries a number and wire type, not membership in an old decoder's oneof descriptor. No future-body tag range, criticality flag or discriminator is specified. An unset known body plus unknown fields cannot distinguish absent body from future body; even alongside a known body, unknown metadata and a future alternative are indistinguishable by the current contract. Define classification and precedence without rejecting all unknown fields or inventing a discriminator here.

### B6. Reserved tags are not runtime validation

[Serialization `SNTR-SER-008`](../specifications/core/serialization.md) and [framing `SNTR-WIRE-008`](../specifications/core/framing.md) require rejecting wire occurrences of Frame tags 16/17. Protobuf `reserved` prevents schema reuse; ordinary binary codecs can skip, retain or discard those tags as unknown data rather than reject them. Names `event`/`resume`/`ack` are schema reservations, not binary wire strings. A bounded validator that observes raw fields before they are discarded, with explicit precedence over general unknown tolerance, needs design and tests. Schema compilation alone does not meet this requirement.

### B7. Capability and session extension mechanics and bounds

[Capabilities `SNTR-CAP-001…005/010/020/021`](../specifications/core/capabilities.md) leaves handshake-extension versus application-RPC binding to an RFC. There are no concrete records, offers, selections, parameters, required-option markers or confirmation fields. Specify identifier and parameter byte lengths, list counts, total negotiation bytes, duplicate handling, unknown/required policy, confirmation/failure timing and per-connection scope. Negotiated frame/concurrency limit overrides also lack a binding. [Serialization `SNTR-SER-020`](../specifications/core/serialization.md) calls for a credential-length bound without assigning a field-specific maximum; method, connection-ID and diagnostic-text bounds need explicit treatment within the envelope budget too.

[Sessions `SNTR-SESS-001/005…008`](../specifications/core/sessions.md), [authentication security `SNTR-ASEC-007/008`](../specifications/security/authentication-security.md), and [replay protection `SNTR-RPL-011`](../specifications/security/replay-protection.md) require an RFC before resume tokens, token size/lifetime/rotation/replay tracking, extension counts, transport/principal binding, expiry/close signaling and failure carriers can be claimed. No separate session messages exist. Documentation-only files are deliberate, not incomplete placeholder wire records.

### B8. Payload and envelope size conflict

[RPC `SNTR-RPC-900`](../specifications/core/rpc.md) and [opaque payloads `SNTR-OPQ-900`](../specifications/security/opaque-payloads.md) ask for a 1 MiB payload round trip, while [framing `SNTR-WIRE-006`](../specifications/core/framing.md) caps the entire serialized Frame at 1 MiB. Tags, length varints, nesting, version, correlation and method/budget fields add bytes; even a result payload of exactly 1 MiB cannot fit the default envelope. Define payload-versus-frame fixtures and approved overrides, test exactly MAX and MAX+1 serialized bytes, and preserve allocation/depth bounds. This RFC neither raises the limit nor relabels payload size as frame size.

### B9. Recorded layout decision and known source break

**Layout authority resolved and implemented by explicit user direction:** remove `schema/syntra/v1` and use `proto/syntra/v1` as the sole source of truth. [ADR-002](../specifications/decisions/ADR-002-protobuf-idl.md), architecture `SYN-ARCH-040` and serialization `SNTR-SER-001` reflect the current path. This is a recorded user-directed decision, not evidence of formal maintainer quorum, accepted RFC status, or completed protocol review.

The FILE/source incompatibility is a known breaking difference, not an unresolved layout-approval blocker. Consumers migrate imports and regenerate bindings from `proto`; no duplicate tree, public-import shim or lint exception is retained. The initial `image.json` stays unchanged. Historical source paths/hashes and commit provenance remain in the manifest, with `historical_image_sha256` for the immutable `historical.json` FileDescriptorSet generated from the actual unchanged sources before removal. Tests use that archive without Git checkout dependencies. Post-deletion validation results remain pending in the validation record. B1–B8, B10 and B11 remain unresolved; the layout decision supplies no missing wire/behavior binding.

### B10. Handler outcome, cancellation and deadline conflicts

[Errors `SNTR-ERR-002/010`](../specifications/core/errors.md) says `UNAVAILABLE` is the only code implying unknown handler outcome, but [reliability `SNTR-REL-001/003/009`](../specifications/core/reliability.md) says error outcomes do not prove execution status, and [RPC `SNTR-RPC-004/005/031`](../specifications/core/rpc.md) permits expiry/cancellation without rollback. A committed effect can precede `CANCELLED` or `DEADLINE_EXCEEDED`. Cancellation says return `CANCELLED` unless already completed, while deadline enforcement says return `DEADLINE_EXCEEDED` on expiry. Define race precedence, terminal delivery versus local abandonment, late/unknown result treatment (`SNTR-WIRE-011` versus RPC §4), and safe-retry/unknown-outcome reporting. No error code proves non-execution or idempotency by itself.

### B11. Requested additions deliberately deferred

| Requested addition | Exact owning specification/requirements | Deferral rationale |
|---|---|---|
| `ServerHello`, `RpcResponse`, `Event` renames | Historical [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto); `SNTR-SER-001`, `SNTR-VER-001/003` | Existing public names are `ServerReady`, `RpcResult`, `Notification`; renames break symbol/generated API identity despite similar wire structure |
| Auth challenge/response rounds or mechanism records | [Authentication `SNTR-AUTH-001…004/007/010`](../specifications/core/authentication.md), [security `SNTR-ASEC-002/003/004`](../specifications/security/authentication-security.md) | Follow-ups are application RPC payloads after ACTIVE; no pre-ACTIVE round types or principal mutation without a capability RFC |
| Resume/close/session establishment and dedicated session errors | [Sessions `SNTR-SESS-001…008`](../specifications/core/sessions.md), `SNTR-HS-006/013`, `SNTR-ASEC-007…010`, `SNTR-RPL-011` | No separate session handshake/control contract; transport close and connection-bound lifetime only; carriers/security/bounds need B1/B7 |
| Subscription/replay request/response, cursor, ack, stream-state records | [Events `SNTR-EVENT-002…010`](../specifications/core/events.md), [reliability `SNTR-REL-004/005/010`](../specifications/core/reliability.md), `SNTR-WIRE-008` | Application-owned RPCs/opaque payloads; no core identity, durable replay or acknowledgment promise; retired Frame tags/names stay reserved |
| Capability/parameter/limit records | [Capabilities `SNTR-CAP-001…005/020/021`](../specifications/core/capabilities.md), [core open questions 1/3](../specifications/core/open-questions.md#blockers-for-stable-v1) | No approved binding, confirmation behavior or collection/length bounds; examples are not allocations (B7) |
| Logical operation ID/idempotency fields | [RPC `SNTR-RPC-007/010`](../specifications/core/rpc.md), `SNTR-REL-004/010`, [replay `SNTR-RPL-013`](../specifications/security/replay-protection.md) | Operation keys belong inside opaque application payloads; correlation is not deduplication |
| New error names/numbers or extra failure messages | [Errors `SNTR-ERR-001…005/020`](../specifications/core/errors.md), `SNTR-VER-003`, `SNTR-OPQ-020` | Existing registry is 0–16; category mapping adds no allocation; new carriers/semantics need approved behavior and registry review, not schema invention |

## Appendix: References

- [Schema reference](../specifications/schema/reference.md); historical [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto) and [error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto).
- [Architecture](../specifications/architecture.md), [RFC process](README.md), [governance](../GOVERNANCE.md), [ADR-002](../specifications/decisions/ADR-002-protobuf-idl.md), [ADR-009](../specifications/decisions/ADR-009-versioning-compatibility.md).
- [Core requirement index](../specifications/core/requirements.md), [core conformance draft](../specifications/core/conformance.md), [security test-plan draft](../specifications/security/test-plan.md). These drafts are pending approval; citations identify proposed normative owners, not acceptance.
- [Proto3 language guide](https://protobuf.dev/programming-guides/proto3/), [field presence](https://protobuf.dev/programming-guides/field_presence/), [wire encoding](https://protobuf.dev/programming-guides/encoding/), [Buf lint rules](https://buf.build/docs/lint/rules/), [Buf breaking categories](https://buf.build/docs/breaking/rules/).
- [Buf configuration](../buf.yaml): v2, module `proto`, lint `STANDARD`, breaking `FILE`; [generation configuration](../specifications/schema/generation.md#pinned-generators-and-toolchains): Go plugin v1.36.6 revision 1, community Prost plugin v0.4.0 revision 1 (local `buf.gen.yaml` removed; smoke tests generate into ignored `.tmp/` only). [Pinned tools](../specifications/schema/generation.md), [baseline provenance and historical archive](../compatibility/v1-initial/README.md), and [original results plus pending post-deletion validation](../specifications/schema/validation.md) are recorded separately from remaining behavioral approval.
