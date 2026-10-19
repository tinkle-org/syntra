# Syntra v1 Core — Open Architectural Questions

- Identifier: `specifications/core/open-questions.md`
- Title: Open Questions and Deferred Decisions
- Status: Living list (updated via RFC; blockers MUST be resolved before stable release per `GOVERNANCE.md`)
- Version: 1.0.0-draft.1 (2026-10-19)
- Scope: Transport-independent questions intentionally left open in this draft. None blocks the draft; items marked **blocker** MUST be resolved before `v1` stable.

## Blockers for stable v1

1. **Capability advertisement binding (blocker).** `capabilities.md` permits handshake-extension or negotiation-RPC binding per capability RFC. Stable v1 MUST pick a single binding for the first capabilities (`events/1`, `resume/1` if defined) or explicitly allow both with precedence rules.
2. **Resumption definition (blocker if claimed).** `sessions.md` defaults to connection-bound sessions. If any resumption is claimed for stable v1, its token format, lifetime, replay window, cross-transport binding, and revocation MUST be fully specified via RFC; otherwise stable v1 MUST state “no resumption.”
3. **Maximum defaults (blocker).** `DEFAULT_MAX_FRAME_BYTES = 1 MiB` and handshake timeout default (5 s) are draft defaults. Transport specs MUST confirm or override with rationale; the suite MUST test exactly MAX and MAX+1.
4. **Challenge/response location (blocker if multi-round auth claimed).** `authentication.md` layers multi-round auth above ACTIVE via generic RPC. If any mechanism needs pre-ACTIVE multi-round, it REQUIRES a capability RFC before stable.

## Non-blockers (future extensions, explicitly deferred)

5. Bidirectional streaming RPC (beyond at-most-once events + unary RPC).
6. Flow-control / stream multiplexing IDs (currently application-defined).
7. Durable replay retention and cross-transport cursors (per-stream RFCs).
8. New transports (QUIC/HTTP-3/etc. — charter-deferred; need transport-profile RFCs).
9. Formal model (TLA+/ProVerif) as supplement — valuable but not required for draft.
10. Buf v2 config pinning (`buf.yaml`, lint/breaking presets) — needed before schema edits, not before spec review.

## Decisions deliberately NOT reopened

- Protobuf as IDL, transport-independent core, opaque payloads, no custom crypto, no domain types, at-most-once default, no exactly-once claim — all closed per ADRs/charter; reopening REQUIRES a new RFC with migration analysis.
