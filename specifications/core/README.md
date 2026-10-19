# Syntra v1 Core Specifications — Index

- Version: 1.0.0-draft.1 (2026-10-19)
- Status: Draft (pending maintainer approval via RFC)
- Authority: Each document below owns its `SNTR-*` requirements; `requirements.md` is the index; `architecture.md` (§8) is the project ownership map.

| Document | Identifier | Title | Requirements |
|----------|------------|-------|--------------|
| `protocol.md` | `specifications/core/protocol.md` | General Protocol Model | SNTR-CORE-* |
| `serialization.md` | `specifications/core/serialization.md` | Protobuf Serialization and Validation | SNTR-SER-* |
| `framing.md` | `specifications/core/framing.md` | Wire Envelope and Framing | SNTR-WIRE-* |
| `handshake.md` | `specifications/core/handshake.md` | Handshake and Connection State Machine | SNTR-HS-* |
| `authentication.md` | `specifications/core/authentication.md` | Abstract Authentication Protocol | SNTR-AUTH-* |
| `sessions.md` | `specifications/core/sessions.md` | Logical Sessions | SNTR-SESS-* |
| `rpc.md` | `specifications/core/rpc.md` | Generic RPC | SNTR-RPC-* |
| `events.md` | `specifications/core/events.md` | Generic Events and Subscriptions | SNTR-EVENT-* |
| `reliability.md` | `specifications/core/reliability.md` | Reliability and Resource Bounds | SNTR-REL-* |
| `capabilities.md` | `specifications/core/capabilities.md` | Capabilities and Extensions | SNTR-CAP-* |
| `errors.md` | `specifications/core/errors.md` | Standardized Errors | SNTR-ERR-* |
| `versioning.md` | `specifications/core/versioning.md` | Versioning and Compatibility | SNTR-VER-* |
| `requirements.md` | `specifications/core/requirements.md` | Requirement Registry (index) | — |
| `conformance.md` | `specifications/core/conformance.md` | Conformance Mapping (informative until suite RFC) | — |
| `open-questions.md` | `specifications/core/open-questions.md` | Open Questions (living) | — |

## Reading order for a new implementer

1. `protocol.md` → `framing.md` → `serialization.md`
2. `handshake.md` → `authentication.md` → `sessions.md`
3. `rpc.md` → `errors.md` → `reliability.md`
4. `events.md` → `capabilities.md` → `versioning.md`
5. `requirements.md` + `conformance.md` + `open-questions.md`

All examples use neutral applications: `echo`, generic key/value, generic event subscription.
