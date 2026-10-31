# Syntra v1 Core — Standardized Errors

- Identifier: `specifications/core/errors.md`
- Title: Typed Errors and Failure Mapping
- Status: Accepted (2026-10-30) — error-vocabulary owner file for accepted [RFC 0003](../../rfcs/0003-handshake-failure-signaling.md) per [Decision 0002](../../docs/decisions/0002-sdd-acceptance-wave.md); correlated clauses from RFC 0004 carry inline citations
- Version: 1.0.0 (2026-10-30) — accepted lineage of 1.0.0-draft.1 (2026-10-19)
- Normative references: BCP 14; `proto/syntra/v1/errors.proto` (`ErrorCode`, `RpcError` — authoritative); `protocol.md`; `framing.md`; `rpc.md`; `handshake.md`; `reliability.md`
- Scope: The single shared error vocabulary, when each code is used, what `message` may contain, and how transport/handshake failures map to codes. Application domain errors belong inside opaque payloads or mapped to these codes without leaking internals.
- Terminology: Per `protocol.md`. **Typed error** = `RpcResult{error{code,message}}`, or a connection-failure local cause recorded by the detecting side (e.g., a pre-`ACTIVE` handshake failure code per `handshake.md` §5); a failed handshake does not carry a wire error `Frame`.

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 1. Protocol requirements

**SNTR-ERR-001** — The `ErrorCode` enum in `errors.proto` is the sole error vocabulary (17 values, 0–16). Implementations MUST emit only defined nonzero codes; `ERROR_CODE_UNSPECIFIED (0)` MUST NOT appear in a failure outcome and MUST be rejected if received as a failure code.

**SNTR-ERR-002** — Code meanings (binding):
- `CANCELLED (1)`: RPC cancelled (via `cancel` or local abandonment winning the race).
- `UNKNOWN (2)`: unclassified failure; SHOULD be avoided in favor of a specific code; MUST NOT carry private diagnostics.
- `INVALID_ARGUMENT (3)`: malformed envelope/method/payload shape (syntactic).
- `DEADLINE_EXCEEDED (4)`: call or handshake budget expired.
- `NOT_FOUND (5)`: method target or application resource not found (generic; no existence oracle beyond what the application intends).
- `ALREADY_EXISTS (6)`: creation conflict (generic).
- `PERMISSION_DENIED (7)`: valid credential, insufficient access.
- `RESOURCE_EXHAUSTED (8)`: size/concurrency/rate/queue bounds hit.
- `FAILED_PRECONDITION (9)`: state violation (e.g., pre-ACTIVE RPC, unconfirmed capability use, wrong-state frame).
- `ABORTED (10)`: concurrency conflict / aborted sequence (generic).
- `OUT_OF_RANGE (11)`: value outside supported range.
- `UNIMPLEMENTED (12)`: unknown method, unknown `Frame.body` variant, unsupported capability/transport feature.
- `INTERNAL (13)`: host-internal failure; message MUST be generic.
- `UNAVAILABLE (14)`: transport loss, host shutdown, or transient unavailability; reports unknown handler outcome for loss/shutdown. `DEADLINE_EXCEEDED`, `INTERNAL`, and `UNKNOWN` equally leave execution unknown (accepted [RFC 0004](../../rfcs/0004-correlation-identity-carriage.md) — its §4 records that `UNAVAILABLE` is not the only unknown-execution report; "unknown-outcome" reporting covers this code family). No single code proves non-execution or idempotency by itself.
- `DATA_LOSS (15)`: unrecoverable corruption/loss detected.
- `UNAUTHENTICATED (16)`: credential missing/invalid/expired/revoked or auth required.

**SNTR-ERR-003** — `RpcError.message` MUST be a human-readable public description, MUST NOT contain credentials, tokens, private backend diagnostics, stack traces, or raw untrusted bytes. Locales/verbosity are implementation-defined; codes are the interoperable signal.

**SNTR-ERR-004** — Every RPC offered under a lawful request context MUST end with exactly one terminal outcome. Handshake failures do not carry a wire code `Frame` (accepted [RFC 0003](../../rfcs/0003-handshake-failure-signaling.md) D1): the detecting side records a locally typed cause per the `handshake.md` §5 table, while the peer observes only the transport-native signal (close/status/HTTP status/WS close code). Transport loss maps to `UNAVAILABLE` to in-flight RPCs. No silent failures — the detecting side always yields a local typed cause or terminal outcome, and no error `Frame`, zero-ID result, or error-bearing `ready` is invented.

**SNTR-ERR-005** — Unknown codes on receipt (future enum values from a newer minor peer): implementations MUST map them to `UNKNOWN` for application reporting while preserving the numeric value in diagnostics where possible, and MUST NOT crash or treat them as success.

**SNTR-ERR-006** — Retriability guidance (non-binding hint; `reliability.md` governs): `UNAVAILABLE` and `DEADLINE_EXCEEDED` MAY be retried if idempotent; `RESOURCE_EXHAUSTED` MAY be retried with backoff; all others MUST NOT be blindly retried. The code itself MUST NOT be interpreted as an idempotency proof.

## 1A. Error taxonomy (informative grouping of the registry; not new codes)

The candidate category names below are documentation labels. They are NOT wire values, MUST NOT appear as an `ErrorCode`, and MUST NOT be treated as aliases that duplicate standard meanings — there is exactly one code per meaning per SNTR-ERR-002. Retryability here is non-binding; `rpc.md` §1I and `reliability.md` govern.

| Category (label) | Codes | Purpose | Retryability | Session impact | Connection impact |
|---|---|---|---|---|---|
| PROTOCOL_ERROR | `INVALID_ARGUMENT` (shape), `FAILED_PRECONDITION` (state), `UNIMPLEMENTED` (unknown variant), `OUT_OF_RANGE`, `ABORTED` (concurrency conflict), `DATA_LOSS` | Malformed, mis-sequenced, or unsupported protocol use | NOT_SAFE_TO_RETRY identically (fix the sender) | None beyond the affected RPC, except handshake-phase failures which end the connection | Handshake-phase: closes; `ACTIVE`-phase: usable unless exhausted/misbehaving |
| AUTHENTICATION_ERROR | `UNAUTHENTICATED` | Missing/invalid/expired/revoked credential, auth required | NOT_SAFE_TO_RETRY identically (fresh credential + new handshake first) | Binding withdrawn; default close | Closes by default |
| AUTHORIZATION_ERROR | `PERMISSION_DENIED` | Valid credential, insufficient access | NOT_SAFE_TO_RETRY (seek authorization change) | Binding intact | Usable |
| REQUEST_ERROR | `INVALID_ARGUMENT` (method/payload shape), `NOT_FOUND`, `ALREADY_EXISTS` | Definitive call outcomes owned by the application mapping | NOT_SAFE_TO_RETRY automatically (new application decision only) | None | Usable |
| RESOURCE_ERROR | `RESOURCE_EXHAUSTED` | Size/concurrency/rate/queue budgets | CONDITIONALLY_RETRYABLE with backoff | None | Usable (isolate offenders first) |
| TIMEOUT_ERROR | `DEADLINE_EXCEEDED` | Call or handshake budget expiry, not rollback | UNKNOWN_OUTCOME; retry only idempotent/with-key | None (handshake timeout closes the attempt) | Usable for calls; handshake timeout closes |
| SERVER_ERROR | `INTERNAL`, `UNKNOWN`, `CANCELLED`, `UNAVAILABLE` | Internal/unclassified faults, cancellation, transient unavailability | `UNAVAILABLE`: CONDITIONALLY_RETRYABLE (idempotent/with-key); `CANCELLED`: NOT_SAFE_TO_RETRY without re-evaluation; `INTERNAL`/`UNKNOWN`: UNKNOWN_OUTCOME | None, except shutdown-mapped `UNAVAILABLE` ends the session | Usable, except loss/shutdown |

Candidate wire names from the task (`PROTOCOL_VERSION_UNSUPPORTED`, `CAPABILITY_UNSUPPORTED`, `AUTHENTICATION_REQUIRED`, `AUTHENTICATION_FAILED`, `METHOD_NOT_FOUND`, `SESSION_EXPIRED`, `PROTOCOL_VIOLATION`) are NOT allocated as enum values. Their mappings are: version-unsupported → `UNIMPLEMENTED` (handshake §5; accepted RFC 0003 D3 — version mismatch has exactly this code); capability-unsupported → `UNIMPLEMENTED`; authentication-required/failed → `UNAUTHENTICATED`; method-not-found → `UNIMPLEMENTED` (unknown method) with application-missing targets as `NOT_FOUND`; session-expired → `UNAUTHENTICATED` (`UNAVAILABLE` for host shutdown); protocol-violation → shape/state/variant codes per row above. No duplicate aliases exist on the wire.

## 1B. Error detail limits (clarifies SNTR-ERR-003/020/021)

`RpcError` carries exactly `{code, message}` — there is no structured-details field, no detail count, and no `retry-after` field in v1.

- **Description:** `message` MUST be human-readable public UTF-8 text for the `code`. It MUST NOT contain stack traces, filesystem paths, SQL text, secret identifiers, tokens, credentials, principal enumerations, private backend diagnostics, or raw untrusted bytes (SNTR-ERR-003). It SHOULD be concise enough to fit comfortably inside the envelope bound; bulk data belongs in success payloads, never in `message` (SNTR-ERR-021).
- **Detail count:** zero — no supplementary detail records exist. Proposals for structured details REQUIRE an RFC and MUST define per-field bounds, redaction rules, and compatibility handling; they MUST NOT be smuggled into `message` as machine-readable metadata.
- **Retry-after:** no wire value exists. Backoff is governed by `reliability.md` (jittered bounded retries, documented policy). Servers MUST NOT encode a machine-readable retry-after contract inside `message` text.
- **Details in logs:** operational detail (attempt counts, backend identifiers) belongs to privileged server-side diagnostics only, never to the peer (SNTR-ASEC-024).

## 1C. Protocol error vs RPC error (clarifies SNTR-ERR-004, SNTR-WIRE-§4, SNTR-HS-§5)

A protocol error means the envelope or handshake itself is unusable; an RPC error means a valid envelope carried a call the application declined or failed. The connection consequences differ:

| Condition | Classification | Code | Connection |
|---|---|---|---|
| Empty `body`; `request_id` misuse; version mismatch (→`UNIMPLEMENTED` only per RFC 0003 D3); pre-`ACTIVE` `request`/`cancel`/`notification`; second `hello`; `hello` outside handshake states | Protocol error | `INVALID_ARGUMENT` (shape), `FAILED_PRECONDITION` (state — fail-close for pre-`ACTIVE` frames per RFC 0003 D2), `UNIMPLEMENTED` (unknown variant; version mismatch), `RESOURCE_EXHAUSTED` (oversize), `UNAUTHENTICATED` (pre-ready access) | Handshake-phase: fail-close — the detecting side records the cause and the connection terminates through the native signal (SNTR-HS-040, RFC 0003 D1). `ACTIVE`-phase framing violations: reject the affected unit; close only if exhausted/misbehaving per documented policy |
| Unknown `Frame.body` variant | Protocol error | `UNIMPLEMENTED` (or close during handshake) | Per row above; never silently dropped (SYN-ARCH-021) |
| Malformed method path | RPC error | `INVALID_ARGUMENT` | Usable; no dispatch occurred |
| Unknown method | RPC error | `UNIMPLEMENTED` | Usable |
| Application-missing target | RPC error | `NOT_FOUND` | Usable |
| Handler declined/failed (incl. authz) | RPC error | `PERMISSION_DENIED`, `UNAUTHENTICATED`, `FAILED_PRECONDITION`, `ABORTED`, `OUT_OF_RANGE`, `DATA_LOSS`, `INTERNAL`, `UNKNOWN` per mapping | Usable, except binding withdrawal closes |
| Overload (concurrency/rate/queue) | RPC error | `RESOURCE_EXHAUSTED` + backoff | Usable (isolate offenders) |
| Deadline expiry | RPC error | `DEADLINE_EXCEEDED` | Usable |
| Cancellation won | RPC error | `CANCELLED` | Usable |
| Transport loss / host shutdown | Connection-level mapping, not an RPC verdict | `UNAVAILABLE` to in-flight RPCs | Closed; outcome unknown |

Rule of thumb: malformed envelope → protocol error (possibly terminate the connection); valid `RpcRequest` the application cannot satisfy → `RpcResponse`-shaped `RpcResult{error}` (the published response name is `RpcResult`, not `RpcResponse`) with the connection remaining usable.

## 1D. HTTP layering (transport profiles own status bindings)

HTTP transport errors and Syntra RPC errors are different layers and MUST NOT be conflated:

- A Syntra RPC error travels inside the envelope as `RpcResult{error}`. `HTTP 200` carrying a valid envelope that contains `RpcResult{error{...}}` is correct layering where the transport profile defines it — the HTTP layer succeeded while the application declined the call.
- HTTP-level failures (non-2xx, truncated bodies, TLS failures) are transport outcomes, not RPC verdicts. Adapters MUST surface them locally as connection/transport failures (mapped to `UNAVAILABLE` for affected in-flight RPCs where no Syntra `result` exists), never synthesize a `RpcResult` the host did not send.
- Adapters MUST NOT map `ErrorCode` values to HTTP statuses as a protocol signal, and peers MUST NOT infer Syntra outcomes from HTTP statuses.
- Concrete binding per accepted [RFC 0003](../../rfcs/0003-handshake-failure-signaling.md) D1/D3, native-signal table (full table in `handshake.md` §5): a detecting host rejecting a malformed binding or with no version overlap closes with `400` and no Syntra envelope — locally these are `INVALID_ARGUMENT` (malformed binding) and `UNIMPLEMENTED` (no version overlap) at the detecting side; an authentication rejection closes with `401`/`403`. A receiving peer reports the generic binding failure locally: `400` maps to local `INVALID_ARGUMENT` per SNTR-HTTP-041, `401`/`403` to the corresponding generic authentication/authorization report without a sub-reason, and any other non-2xx or transport outcome to `UNAVAILABLE` (adapter default). Non-`200` statuses never synthesize `RpcResult` and never claim the host's precise rejection cause. HTTP profile size/status limits keep their owning profile rules and are not extended here.

## 1E. Detecting-side cause vs peer-visible signal (accepted RFC 0003 D1)

Handshake failure reporting has two axes and they MUST NOT be conflated:

- **Detecting side** (the endpoint that rejects): records the applicable locally typed cause from the `handshake.md` §5 table and terminates the attempt. Its local waiter receives that cause, subject to public diagnostic hygiene (no privileged rejection detail serialized — SNTR-ASEC-001/011/024).
- **Peer side** (the endpoint that observes the teardown): reports only the transport-native signal it actually observed (TCP close/TLS shutdown, HTTP status, WS close code), marked as a transport/binding failure rather than a received `RpcResult`. Where the signal cannot distinguish causes — a close status/code shared by several causes — the report stays generic and MUST NOT claim the detecting endpoint's precise code.
- No pre-`ACTIVE` error channel exists: no error `Frame`, zero-ID `result`, error-bearing `ready`, second `hello`, invented handshake record, or error inside a `notification` is ever sent (RFC 0003 D1), and a pre-`ACTIVE` `notification` fails the connection on receipt (RFC 0003 D2).
- SNTR-ERR-004's "no silent failures" therefore means: every handshake failure yields a typed local cause at one endpoint and an observable native signal at the other — never a mutually exchanged typed code over an invented carrier.

The full condition → local cause → native-signal → peer-conclusion table is normative in `handshake.md` §5 (mirroring RFC 0003 §4) and is not duplicated here.

## 2. Client behavior

- **SNTR-ERR-010** — The client MUST branch on `code`, not on `message` text; MUST handle SNTR-ERR-005 mapping; MUST surface `UNAVAILABLE` distinctly (outcome unknown) vs terminal application outcomes.
- **SNTR-ERR-011** — The client MUST NOT display or log `message` verbatim if it could contain sensitive context; it SHOULD present codes + generic text to end contexts.

## 3. Server behavior

- **SNTR-ERR-020** — The server MUST select the most specific applicable code, MUST sanitize `message`, MUST NOT emit `UNSPECIFIED` as a failure, and MUST document any application-to-code mapping (e.g., which app conditions yield `NOT_FOUND` vs `FAILED_PRECONDITION`).
- **SNTR-ERR-021** — The server MUST NOT use errors as a data channel (no paging, no payload smuggling in `message`); bulk data belongs in success payloads.

## 4. Failure handling

Malformed error frames (missing outcome, zero code with error set, invalid UTF-8 in `message`) are themselves protocol violations → `INVALID_ARGUMENT` (if a context exists) or connection closure. Error storms (repeated errors) are rate-limited per `reliability.md`.

## 5. Security considerations

Error oracles (distinguishing valid/invalid principals, existence, or state via codes/timing) MUST be minimized: use `UNAUTHENTICATED` vs `PERMISSION_DENIED` only where the distinction is intentional and documented; otherwise prefer the more generic applicable code with constant-time paths.

## 6. Compatibility considerations

New codes are minor-additive (with SNTR-ERR-005 tolerance) but SHOULD be rare; repurposing or removing a code is major. `message` text is never versioned — only codes are.

## 7. Conformance requirements

- **SNTR-ERR-900** — Fixtures: each of the 16 nonzero codes produced at least once via neutral operations; `UNSPECIFIED`-as-failure rejected; unknown future code mapped to `UNKNOWN`; `message` hygiene (negative grep for credential/diagnostic patterns); code-not-text branching proof.
- **SNTR-ERR-901** — Mapping proof: handshake table (`handshake.md` §5) + transport-loss→`UNAVAILABLE` + oversize→`RESOURCE_EXHAUSTED` all demonstrated, with the detecting-side cause and the peer-observed native signal asserted separately (many-to-one signals never claim the exact remote cause; accepted RFC 0003).
