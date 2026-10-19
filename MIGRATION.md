# Migration Plan — From Existing Schema to Spec-First Public Repository

- Date: 2026-10-19
- Scope: Phase A audit + migration without deleting working code
- Authority: `specifications/architecture.md` Sec. 8; ADRs 001–010

This document satisfies the Phase A requirement to inventory, classify,
and plan. No production code is deleted or silently rewritten by this
plan.

## 1. Inventory (as found)

The local working directory contained, excluding IDE/tooling caches:

```text
schema/syntra/v1/error.proto    (51 lines — ErrorCode, RpcError)
schema/syntra/v1/session.proto  (79 lines — Frame, ClientHello, ServerReady,
                                 RpcRequest, RpcResult, Cancel, Notification)
```

No other Syntra source files, schemas, documentation, tests, Buf
configs, READMEs, or licenses were present.

Excluded from the public repository (local tooling only, not Syntra):

- `.agents/skills/*` — agent skill definitions for the local editor
- `.opencode/*` (including `node_modules/zod`) — local tooling cache
- `.DS_Store` files — OS metadata

These paths MUST NOT be published to `tinklehq/syntra`. They are listed
here so reviewers can verify nothing normative was missed.

## 2. Current transport and protocol behaviors (observed)

From the two `.proto` files and their comments:

- **Envelope:** `Frame{version, request_id, oneof body}` — versioned,
  correlated, exactly one operation per frame.
- **Handshake:** `ClientHello{min_version, max_version, credential}` →
  `ServerReady{connection_id}` or typed failure. Comments state
  credential is opaque, TLS-only, never interpreted/logged/persisted by
  the core; `connection_id` is opaque and MUST NOT be an auth session ID.
- **RPC:** `RpcRequest{method, payload, timeout_ms}` with canonical
  `/package.Service/Method` paths and opaque payloads; `RpcResult`
  with exactly one `payload` or `error{code, message}` outcome.
- **Cancellation:** `Cancel{}` targets its envelope `request_id`; comment
  states it requests cancellation, not rollback.
- **Notifications:** `Notification{payload}` — opaque, host-authorized,
  valid after `ready` only; no delivery/durable-state semantics.
- **Errors:** 17 generic codes (`CANCELLED`…`UNAUTHENTICATED`) plus
  `UNSPECIFIED` (invalid in failure outcomes); `RpcError.message` MUST
  NOT contain credentials or private diagnostics.
- **Evolution hygiene:** `reserved 16, 17` and
  `reserved "event", "resume", "ack"` — former application-replay
  operations permanently retired.
- **Correlation:** `request_id == 0` reserved for notifications;
  notifications MAY arrive before the corresponding `result`.

No transport adapter code, no handshake state machine, no timeout/
cancellation implementation, and no conformance tests were present.

## 3. Behavior defined only in implementation code

**None.** No implementation code (Rust or otherwise) was present in the
audited directory.

All behavior currently lives in `.proto` comments. Per ADR-001 those
comments are informative, not normative. Each behavior above MUST be
promoted to a normative specification via RFC before conformance can be
claimed. Tracked as future work in `CHANGELOG.md` (`Unreleased`).

## 4. Dependencies on private projects

**None found.**

- `import "syntra/v1/error.proto"` — intra-repository only.
- `option go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"`
  — public repository path, not a private dependency.
- No imports of messenger, chat SDK, server, Kafka, mail, or other
  sibling directories present in the surrounding workspace.
- No private registry, submodule, or vendored code.

Verification: full-text search of `schema/` for private product names,
company infrastructure, and unpublished paths returned no hits. Future
PRs MUST repeat this check per `CONTRIBUTING.md` Sec. 5.

## 5. Application-specific types or methods

**None found.**

Searched for: chat messages, conversations, contacts, user profiles,
read/delivery receipts, messaging groups, payment, social, and related
terms — zero hits.

Present types are generic and approved: `Frame`, `ClientHello`,
`ServerReady`, `RpcRequest`, `RpcResult`, `Cancel`, `Notification`,
`RpcError`, `ErrorCode`. Generic principals, endpoints, identities,
opaque payloads, requests, responses, streams, and events are the only
abstractions used — compliant with `SYN-ARCH-001/002`.

## 6. Classification

### Reusable as-is (preserve byte-for-byte unless an RFC says otherwise)

- `schema/syntra/v1/error.proto` — keep package, enum values, field
  numbers, comments. Buf breaking detection MUST gate any edit.
- `schema/syntra/v1/session.proto` — keep package, `Frame` numbers
  (1, 2, 10–15), `reserved` values, `oneof` discipline, message shapes.

Rationale: these are the only wire contracts in existence. Preserving
them satisfies "no deletion/silent rewrite" and gives the RFC process
a stable base.

### Requiring extraction (do not publish)

- Nothing to extract: no application logic, private helper, or
  domain-specific code was co-located with the schemas.

### Missing (to be created via RFC, not by copying private code)

- `buf.yaml` / `buf.gen.yaml` (Buf v2 governance)
- `specifications/core/*.md` (handshake, RPC, errors, streams)
- `specifications/transports/*.md` (7 v1 profiles)
- `specifications/security/*.md`
- Conformance + interop suite
- Rust reference implementation (non-normative)

These MUST be written fresh from the charter and ADRs. They MUST NOT be
extracted from any private repository.

## 7. Migration plan (no deletion, no silent rewrite)

1. **Preserve.** Keep both `.proto` files unchanged in this change.
   This plan makes zero wire edits.
2. **Surround.** Add charter (`specifications/architecture.md`), ADRs,
   foundation docs, and RFC process around the preserved schemas —
   exactly what this change does.
3. **Govern.** Add Buf v2 config in a follow-up RFC (lint + breaking
   check). Until then, `CONTRIBUTING.md` forbids schema edits without an
   RFC and manual `reserved` verification.
4. **Specify.** Promote each proto-comment behavior to a normative spec
   via focused RFCs (handshake → RPC → errors → streams → transports →
   security), each with requirement IDs and conformance tests.
5. **Verify.** Build the conformance suite against the specs, not against
   any private implementation. Use neutral fixtures (echo, generic
   key/value, generic subscription) and deterministic vectors.
6. **Implement.** Build the Rust reference to the specs. Any gap found
   during implementation triggers an RFC, not a silent proto edit.
7. **Exclude.** Ensure `.agents/`, `.opencode/`, `.DS_Store`, and any
   sibling private directories never enter the public history (see
   `.gitignore` guidance below and pre-push review).

Rollback: every step is additive. If a follow-up RFC is rejected, the
repository remains at this charter+ADRs+schemas state with no wire churn.

## 8. Pre-push checklist for `tinklehq/syntra`

- [ ] `git log` shows schemas added unchanged (diff empty vs. audit copy).
- [ ] No `.agents/`, `.opencode/`, `.DS_Store`, or sibling private files
      in history.
- [ ] `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
      `SUPPORT.md`, `GOVERNANCE.md`, `CHANGELOG.md` present.
- [ ] `rfcs/README.md`, `rfcs/template.md` present.
- [ ] `specifications/architecture.md`, `specifications/decisions/` (10
      ADRs + index) present.
- [ ] No `LICENSE` file (intentional — pending maintainer decision per
      `GOVERNANCE.md` Sec. 7).
- [ ] No invented contact addresses in any file.
- [ ] Remote `tinklehq/syntra` created as public; `main` protected;
      private vulnerability reporting enabled.

## Appendix: audit commands (reproducible)

```sh
find . -type f -not -path "./.opencode/*" -not -name ".DS_Store" | sort
grep -ri "chat\|contact\|receipt\|messenger\|tinkle-server\|kafka\|payment" schema/ || echo "no hits"
```
