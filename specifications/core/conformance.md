# Syntra v1 Core — Conformance Requirement Mapping

- Identifier: `specifications/core/conformance.md`
- Title: Core Conformance Mapping (draft harness)
- Status: Draft (pending conformance-suite RFC)
- Version: 1.0.0-draft.1 (2026-10-19)
- Normative references: `requirements.md`; all `specifications/core/*.md`; future conformance suite (owns executable verification per SYN-ARCH-044)
- Scope: How each normative ID will be verified (fixture, negative test, interop proof). This file is informative until the suite RFC accepts it; it MUST NOT add new behavior.
- Terminology: Per `protocol.md`. **Conformant** = passes all Mandatory fixtures + correctly rejects/handles Optional absence.

## Minimal conformance profile (mandatory-only host + initiator)

A minimal implementation MUST pass:

1. **Handshake:** success; version-mismatch (low/high/disjoint); second `hello`; pre-ACTIVE `request`; timeout; graceful close; abrupt loss (SNTR-HS-900).
2. **Envelope:** one valid frame per variant; empty-body rejection; zero/nonzero `request_id` matrix; unknown-variant `UNIMPLEMENTED`; MAX+1 oversize `RESOURCE_EXHAUSTED`; empty-payload round-trip; reserved-number rejection (SNTR-WIRE-900).
3. **Serialization:** unknown-field tolerance; out-of-order fields; packed/unpacked equivalence; truncated varint; invalid UTF-8; depth/size exceedance; non-canonical equality (SNTR-SER-900/901).
4. **RPC:** echo (empty/small/large/arbitrary); `NOT_FOUND` mapping; malformed method; missing outcome; duplicate ID; cancel-before/after; deadline; interleaved notification; 16-concurrent; exactly-once-terminal proof (SNTR-RPC-900/901).
5. **Errors:** all 16 codes at least once; `UNSPECIFIED`-as-failure rejected; unknown-code→`UNKNOWN`; message hygiene; code-not-text branching (SNTR-ERR-900).
6. **Auth/sessions:** empty/invalid/expired credential handling; re-auth-same-connection rejected; `connection_id`-as-credential rejected; reconnect loses state (SNTR-AUTH-900, SNTR-SESS-900).
7. **Reliability:** loss→`UNAVAILABLE` + safe-retry discipline; no transport-ack-as-success (SNTR-REL-900/901).
8. **Versioning/caps:** range overlap selection; capability negotiation only through accepted profiles' own post-`ACTIVE` negotiation RPCs (no generic advertisement carrier): required-but-unsupported profile and profile operation before confirmation → `UNIMPLEMENTED` under that profile's contract (recovery: `SYN-URP-010`); unconfirmed-option use on an otherwise-confirmed connection → `FAILED_PRECONDITION` (SNTR-VER-900, SNTR-CAP-900).

Optional (only if claimed): event subscribe→events→cancel, replay/cursor, resumption (each with its capability ID cited).

## Fixture rules

- Neutral payloads only: `echo`, generic key/value, generic subscription. No domain types.
- Deterministic vectors: fixed bytes for every valid/invalid frame; no time-dependent flakiness (deadlines use injected clocks or generous margins + explicit `DEADLINE_EXCEEDED` assertion).
- Negative tests REQUIRED for every `MUST NOT` and every failure row in `handshake.md` §5.
- A single named transport profile is sufficient for a Core claim. Two-transport interop proof (SNTR-WIRE-901) and dimension-independence proof (SNTR-VER-901) are REQUIRED only for a claim of transport independence across two named transports. RFC 0009 D4 accepted this claim-scope rule; a baseline profile is never certified by another profile's pass.

## Reporting

Claims MUST list: implementation + transport profiles supported (secure/insecure labeling per SYN-ARCH-050), wire version(s), capabilities with IDs, bounds/defaults, and per-ID pass/fail with logs. Every result-bearing claim MUST additionally be machine-verifiable: it names the executed manifest case IDs (`CONF-*`), the runner/tool, the specification and suite revision pinned at execution, and the per-case results (suite verdict vocabulary; missing execution is NOT_EXECUTED, never PASS). Registered, planned rows with no run are not reportable as results. Core-only claims on one named profile remain permitted, but they cannot satisfy the recovery-inclusive stable bundle (RFC 0006 §11.1), which requires the recovery contract's own accepted requirements and evidence.

## Trace (requirement → fixture group)

| Requirement family | Fixture group | Suite location (forthcoming) |
|--------------------|---------------|------------------------------|
| SNTR-CORE-* | model/generic/negative-role | `conformance/core/` |
| SNTR-SER-* | encoding/unknown/malformed | `conformance/serialization/` |
| SNTR-WIRE-* | envelope/variant/size | `conformance/framing/` |
| SNTR-HS-* | handshake/state/timeout | `conformance/handshake/` |
| SNTR-AUTH-*, SNTR-SESS-* | auth/session/reconnect | `conformance/auth-session/` |
| SNTR-RPC-* | rpc/cancel/deadline | `conformance/rpc/` |
| SNTR-EVENT-* | events/streams (optional) | `conformance/events/` |
| SNTR-REL-* | reliability/backpressure | `conformance/reliability/` |
| SNTR-CAP-*, SNTR-VER-* | negotiation/versioning | `conformance/negotiation/` |
| SNTR-ERR-* | codes/hygiene/mapping | `conformance/errors/` |
