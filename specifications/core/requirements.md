# Syntra v1 Core — Requirement Registry

- Identifier: `specifications/core/requirements.md`
- Title: Normative Requirement Index
- Status: Draft (generated with core draft 1.0.0-draft.1, 2026-10-19)
- Version: 1.0.0-draft.1
- Normative references: All `specifications/core/*.md`; `proto/syntra/v1/*.proto`
- Scope: Single index of every normative requirement ID in the v1 core suite. The defining document owns each ID; this file is an index and MUST NOT restate normative force. In case of divergence, the defining document prevails.
- Terminology: Per `protocol.md`.

## Index

| ID | Defining document | Concern | Mandatory/Optional |
|----|-------------------|---------|--------------------|
| SNTR-CORE-001…006, 010–012, 020–022, 030–031, 900–901 | `protocol.md` | General model, layering, roles | Mandatory |
| SNTR-SER-001…008A, 010–011, 020–021, 900–901 | `serialization.md` | Protobuf encoding, unknown fields, bounded raw-wire validation, bounds, malformed input, non-canonical | Mandatory |
| SNTR-WIRE-001…008, 010–011, 020–021, 900–901 | `framing.md` | Envelope variants, validation, size, empty payloads, reserved, transport-independence | Mandatory |
| SNTR-HS-001…006, 010–015, 020–021, 030–031, 040, 900–902 | `handshake.md` | Six-state machine, negotiation, timeouts, close/loss; reliable attachment (optional, no state change) | Mandatory (+ optional reliable) |
| SNTR-AUTH-001…010, 020–021, 030–031, 900–901 | `authentication.md` | Pluggable auth, credential rules, principal binding, expiry, re-auth | Mandatory interface; mechanisms application-defined |
| SNTR-SESS-001…008, 010–011, 020–021, 030–034, 900–902 | `sessions.md` | Connection-bound sessions, no implicit resumption; reliable sessions (optional) | Mandatory (+ optional reliable) |
| SNTR-RPC-001…008, 010–013, 020–021, 030–032, 900–902 | `rpc.md` | Method shape, correlation, deadlines, cancel, errors, idempotency distinction; delivery IDs + reconciliation (optional) | Mandatory (+ optional reliable) |
| SNTR-EVENT-001…011, 020–021, 030–031, 900–901 | `events.md` | Optional events/streams, ordering, at-most-once default, replay/cursor | Optional (negotiated) |
| SNTR-REL-001…015, 020–021, 030–031, 900–902 | `reliability.md` | At-most-once default, retries, dedup, backpressure, exhaustion, loss; reliable delivery (optional) | Mandatory semantics (+ optional reliable) |
| SNTR-CAP-001…008, 010–011, 020–021, 900–902 | `capabilities.md` | Explicit negotiation, mandatory interop, extensions, experiments; reliable-session capability | Mandatory mechanism; features optional |
| SNTR-ERR-001…006, 010–011, 020–021, 900–901 | `errors.md` | 16 nonzero codes, message hygiene, unknown-code mapping | Mandatory |
| SNTR-VER-001…007, 010–011, 020–021, 900–901 | `versioning.md` | Five dimensions, additive vs breaking, reserved, deprecation | Mandatory process |

Total: 12 defining documents, ~130 normative IDs + conformance IDs (`*-900`, `*-901`).

## Uniqueness and ownership rules

- IDs are unique across the suite; new IDs REQUIRE the prefix of their defining document.
- No ID appears in two defining documents; cross-references use citations, not duplication (single-definition rule).
- Conformance IDs (`*-900`/`*-901`) are testable acceptance criteria for their document.
- Charter IDs (`SYN-ARCH-*`) and core IDs (`SNTR-*`) are distinct namespaces; conflicts resolve per the ownership map (`architecture.md` §8).

## Verification

```sh
grep -rhoE "SNTR-[A-Z]+-[0-9]+" specifications/core/*.md | sort | uniq -c | sort -rn | head
# every ID MUST appear exactly once as a definition (bolded `**SNTR-...**`)
```
