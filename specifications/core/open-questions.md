# Syntra v1 Core — Open Architectural Questions

- Identifier: `specifications/core/open-questions.md`
- Title: Open Questions and Deferred Decisions
- Status: Living list (updated via RFC; blockers MUST be resolved before stable release per `GOVERNANCE.md`)
- Version: 1.0.0-draft.1 (2026-10-19)
- Scope: Transport-independent questions intentionally left open in this draft. None blocks the draft; items marked **blocker** MUST be resolved before `v1` stable.

## Blockers for stable v1

Closed in the v1 acceptance wave (recorded here for traceability; the defining contracts now live in the accepted RFCs):

1. **Capability/extension negotiation binding — Resolved by accepted [RFC 0005](../../rfcs/0005-negotiation-bounds-identifiers.md) D1** with the accepted [RFC 0006](../../rfcs/0006-update-recovery-profile.md) supplying the first binding: negotiation is post-ACTIVE via an ordinary RPC defined by each profile's own accepted RFC (no generic capability enumeration, hello-extension list, or probe). Stable v1 chose the per-profile binding; the first stable bundle covers `syntra.update-recovery/1` (optional per connection).
2. **Resumption definition (blocker if claimed).** `sessions.md` defaults to connection-bound sessions. If any resumption is claimed for stable v1, its token format, lifetime, replay window, cross-transport binding, and revocation MUST be fully specified via RFC; otherwise stable v1 states “no resumption.” No resumption capability exists in the v1 acceptance bundle; RFCs 0002/0005 defer this explicitly (logical resumption stays open).
3. **Maximum defaults — Resolved by accepted RFC 0005** (D2/D3): `DEFAULT_MAX_FRAME_BYTES = 1 MiB` applies to the complete serialized `Frame` (exactly MAX in bound; MAX+1 rejected; no payload-only 1 MiB acceptance). The 5-second handshake timer default and admission-start deadline accounting are confirmed by accepted RFCs [0003](../../rfcs/0003-handshake-failure-signaling.md)/[0004](../../rfcs/0004-correlation-identity-carriage.md) (with RFC 0008 D2 wording); the suite MUST still test exactly MAX and MAX+1.
4. **Challenge/response location (blocker if multi-round auth claimed).** `authentication.md` layers multi-round auth above ACTIVE via generic RPC. If any mechanism needs pre-ACTIVE multi-round, it REQUIRES a capability RFC before stable (still open; RFC 0002 defers this).

## Non-blockers (future extensions, explicitly deferred)

5. Bidirectional streaming RPC (beyond at-most-once events + unary RPC).
6. Flow-control / stream multiplexing IDs (currently application-defined).
7. Durable replay retention and cross-transport cursors (per-stream RFCs).
8. New transports (QUIC/HTTP-3/etc. — charter-deferred; need transport-profile RFCs).
9. Formal model (TLA+/ProVerif) as supplement — valuable but not required for draft.
10. Buf v2 config pinning (`buf.yaml`, lint/breaking presets) — needed before schema edits, not before spec review.
11. Cross-transport resumption binding — deferred per the RFC 0002 §10 disposition (item 9); `sessions.md` §1D holds "not allowed in v1" until an accepted RFC defines it.
12. Reliable-session shipping authority — deferred per the RFC 0002 §10 disposition (item 12); `syntra.reliable-session/1` remains proposal-only (`capabilities.md` SNTR-CAP-008/902) until a future RFC grants shipping authority.

## Decisions deliberately NOT reopened

- Protobuf as IDL, transport-independent core, opaque payloads, no custom crypto, no domain types, at-most-once default, no exactly-once claim — all closed per ADRs/charter; reopening REQUIRES a new RFC with migration analysis.
