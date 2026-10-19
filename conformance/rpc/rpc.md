# Conformance — RPC correlation, deadlines, cancellation, idempotency (`CONF-RPC-001…012`)

Related normative requirements are cited per case; test IDs are not normative. All cases Mandatory. Neutral fixtures only (`/example.Echo/Echo`, `/example.KV/Get`).

## CONF-RPC-001 basic request/response

- Related normative requirement: SNTR-RPC-001, SNTR-RPC-002, SNTR-RPC-003, SNTR-RPC-006, SNTR-WIRE-001/002.
- Preconditions: session ACTIVE; method `/example.Echo/Echo` exists.
- Input: `Frame{id=7, request{method=/example.Echo/Echo, payload=opaque, timeout_ms=500}}` (repeat with empty, small, arbitrary non-UTF-8 payloads).
- Expected output: exactly one `Frame{id=7, result{payload}}` with bit-identical payload; correlation IDs match exactly.
- Expected connection state: ACTIVE, usable.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-002 two concurrent requests

- Related normative requirement: SNTR-RPC-002, SNTR-RPC-008, SNTR-REL-007.
- Preconditions: ACTIVE; host supports ≥2 concurrent RPCs (minimum is 16).
- Input: `Frame{id=7, request{Echo, A}}` and `Frame{id=8, request{KV/Get, B}}` outstanding simultaneously.
- Expected output: two terminal results, `id=7` and `id=8`, each correlated exactly once; no cross-delivery.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-003 reversed response order

- Related normative requirement: SNTR-RPC-002 (correlation, not FIFO).
- Preconditions: ACTIVE with two outstanding RPCs as in CONF-RPC-002.
- Input: host completes the second request first (e.g., slow handler A, fast handler B).
- Expected output: `Frame{id=8, result}` arrives before `Frame{id=7, result}`; initiator correlates by ID and MUST NOT treat order as significant.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-004 duplicate request ID

- Related normative requirement: SNTR-RPC-002, SNTR-RPC-§4, SNTR-ERR-002 (`FAILED_PRECONDITION`).
- Preconditions: ACTIVE; `id=7` outstanding (no terminal result yet).
- Input: second `Frame{id=7, request{...}}` while the first is outstanding.
- Expected output: new attempt rejected with `FAILED_PRECONDITION`; the original continues to exactly one terminal result; no double dispatch observable to the caller.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-005 unknown response ID

- Related normative requirement: SNTR-RPC-§4 (result for unknown ID).
- Preconditions: ACTIVE; no outstanding RPC with `id=99`.
- Input: peer sends `Frame{id=99, result{payload}}` (simulate via test harness acting as host).
- Expected output: locally ignored with a diagnostic; no error storm, no state change, no completion signaled to any caller.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-006 unknown method

- Related normative requirement: SNTR-RPC-001, SNTR-RPC-030, SNTR-ERR-002 (`UNIMPLEMENTED`), SNTR-ERR-020.
- Preconditions: ACTIVE.
- Input: `Frame{id=11, request{method=/example.Unknown/Call, payload, timeout}}`.
- Expected output: `Frame{id=11, result{error{UNIMPLEMENTED, generic message}}}`; no handler dispatch.
- Expected connection state: ACTIVE, usable.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-007 invalid method shape and oversize envelope

- Related normative requirement: SNTR-RPC-001, SNTR-WIRE-005/006, SNTR-SER-007, SNTR-ERR-002.
- Preconditions: ACTIVE.
- Input: (a) malformed paths (`example.Echo`, `/example`, `/a/b/c`, empty, with spaces/control chars); (b) a serialized `Frame` of exactly MAX+1 bytes (1,048,577).
- Expected output: (a) `INVALID_ARGUMENT` without dispatch; (b) `RESOURCE_EXHAUSTED` (or connection closure where unbounded pre-handshake); no panic, no unbounded allocation.
- Expected connection state: ACTIVE for (a); per policy for (b).
- Expected session state: unchanged for (a).
- Mandatory/optional: Mandatory.

## CONF-RPC-008 deadline expiry

- Related normative requirement: SNTR-RPC-004, SNTR-REL-006, SNTR-ERR-002 (`DEADLINE_EXCEEDED`).
- Preconditions: ACTIVE; handler deliberately slower than the budget (or injected clock).
- Input: `Frame{id=9, request{Echo, timeout_ms=100}}` with handler exceeding 100 ms.
- Expected output: `Frame{id=9, result{error{DEADLINE_EXCEEDED}}}`; handler effects unknown; initiator surfaces expiry distinctly from application errors.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-009 cancellation race

- Related normative requirement: SNTR-RPC-005, SNTR-RPC-021/031, SNTR-ERR-002 (`CANCELLED`).
- Preconditions: ACTIVE with an outstanding slow RPC `id=12`.
- Input: (a) `Frame{id=12, cancel}` before completion; (b — separate run) `cancel` arriving after the result was already determined; (c) `cancel` for unknown/completed `id=77`.
- Expected output: (a) `Frame{id=12, result{error{CANCELLED}}}`; (b) the success result wins (completion wins); (c) ignored with no error. Exactly one terminal result in every run; never a rollback claim.
- Expected connection state: ACTIVE throughout.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory. (The cancel-vs-deadline simultaneous race is the open tie-break B10 and is NOT asserted here.)

## CONF-RPC-010 malformed result without outcome

- Related normative requirement: SNTR-RPC-002, SNTR-ERR-004.
- Preconditions: ACTIVE with outstanding RPC `id=14`.
- Input: responder emits `Frame{id=14, result}` with neither payload nor error selected (client-side protocol violation).
- Expected output: client reports local `INVALID_ARGUMENT` for that RPC, never success; no error response on the wire is required.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Mandatory (client role only).

## CONF-RPC-011 resource exhaustion

- Related normative requirement: SNTR-RPC-008, SNTR-REL-007/008, SNTR-ASEC-020, SNTR-ERR-002 (`RESOURCE_EXHAUSTED`).
- Preconditions: ACTIVE with a documented concurrency/rate/queue bound.
- Input: exceed the bound (e.g., 17th concurrent RPC where max is 16, or flood within policy).
- Expected output: `RESOURCE_EXHAUSTED` for excess work; conformant traffic unaffected; host recovers without restart; backoff honored by the initiator.
- Expected connection state: ACTIVE (isolated offender handling).
- Expected session state: unchanged.
- Mandatory/optional: Mandatory.

## CONF-RPC-012 connection loss before response

- Related normative requirement: SNTR-HS-014, SNTR-REL-009, SNTR-CORE-005, SNTR-ERR-002 (`UNAVAILABLE`).
- Preconditions: ACTIVE with at least one in-flight RPC.
- Input: abrupt transport loss before any `result`.
- Expected output: `UNAVAILABLE` to every in-flight RPC; outcome reported as unknown; MUST NOT be reported as success or as proof of non-execution.
- Expected connection state: CLOSED (via loss).
- Expected session state: terminated abnormally; reconnect assumes no continuity.
- Mandatory/optional: Mandatory.

## Traceability

| Test | Requirement family |
|---|---|
| CONF-RPC-001 | RPC-001/002/003/006, WIRE-001/002 (model, correlation) |
| CONF-RPC-002 | RPC-002/008, REL-007 (concurrency) |
| CONF-RPC-003 | RPC-002 (ordering by ID) |
| CONF-RPC-004 | RPC-002/§4 (duplicate outstanding ID) |
| CONF-RPC-005 | RPC-§4 (unknown result ID) |
| CONF-RPC-006 | RPC-001/030, ERR-002 (unknown method) |
| CONF-RPC-007 | RPC-001/030, WIRE-005/006, SER-007 (validation, bounds) |
| CONF-RPC-008 | RPC-004, REL-006 (deadlines) |
| CONF-RPC-009 | RPC-005/021/031 (cancellation) |
| CONF-RPC-010 | RPC-002, ERR-004 (malformed result without outcome) |
| CONF-RPC-011 | RPC-008, REL-007/008 (exhaustion) |
| CONF-RPC-012 | HS-014, REL-009 (loss) |
