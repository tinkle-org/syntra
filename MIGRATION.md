# Migration Record — From Historical Schema to Sole-Source Public IDL

- Date: 2026-10-19
- Scope: Historical Phase A audit + subsequent user-directed layout migration
- Authority: `specifications/architecture.md` Sec. 8; ADRs 001–010

> **Current layout decision (user-directed, implemented):**
> `proto/syntra/v1` is the sole Protobuf source of truth. The old
> `schema/syntra/v1` tree is removed. The original audit below records what
> existed at the time; its byte-for-byte, additive-only preservation plan
> is superseded by this explicit layout decision. It describes no live
> schema root. [RFC 0001 B9](rfcs/0001-public-idl-layout.md#b9-recorded-layout-decision-and-known-source-break)
> records the decision and known FILE/source break, without claiming
> formal maintainer quorum or behavioral RFC approval.

Sections 1–7 preserve the Phase A inventory, classification and plan as
historical context. Section 8 records the subsequent migration. No new
wire types or protocol semantics are introduced by the layout change;
remaining protocol blockers are pending.

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

## 2. Transport and protocol behaviors at the original audit (observed)

From the two historical `.proto` files and their comments (as found at the audit):

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

At the original audit, all observed behavior lived in `.proto` comments. Per ADR-001 those
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

Original verification: full-text search of the then-existing `schema/` for
private product names, company infrastructure, and unpublished paths
returned no hits. Future PRs MUST repeat this check against `proto/` per
`CONTRIBUTING.md` Sec. 5.

## 5. Application-specific types or methods

**None found.**

Searched for: chat messages, conversations, contacts, user profiles,
read/delivery receipts, messaging groups, payment, social, and related
terms — zero hits.

Types present at the audit were generic: `Frame`, `ClientHello`,
`ServerReady`, `RpcRequest`, `RpcResult`, `Cancel`, `Notification`,
`RpcError`, `ErrorCode`. Generic principals, endpoints, identities,
opaque payloads, requests, responses, streams, and events are the only
abstractions used — compliant with `SYN-ARCH-001/002`.

## 6. Classification

### Original reusable-as-is classification (preservation plan superseded; paths are historical, not live)

- Historical `schema/syntra/v1/error.proto` — keep package, enum values, field
  numbers, comments. Buf breaking detection MUST gate any edit.
- Historical `schema/syntra/v1/session.proto` — keep package, `Frame` numbers
  (1, 2, 10–15), `reserved` values, `oneof` discipline, message shapes.

Original rationale: these were the only wire contracts in existence.
Preserving them satisfied the original "no deletion/silent rewrite" plan
and gave the RFC process a stable base. These paths now identify historical
sources, not live files; see the pinned sources and descriptor archive in §8.

### Requiring extraction (do not publish)

- Nothing to extract: no application logic, private helper, or
  domain-specific code was co-located with the schemas.

### Missing at the foundation audit (subsequent status below)

- `buf.yaml` / `buf.gen.yaml` (Buf v2 governance)
- `specifications/core/*.md` (handshake, RPC, errors, streams)
- `specifications/transports/*.md` (7 v1 profiles)
- `specifications/security/*.md`
- Conformance + interop suite
- Rust reference implementation (non-normative)

Follow-up status: Buf configuration, generation tooling and
schema/codec tests now exist; core/security documents exist as unapproved
drafts. Transport profiles and the runtime conformance/reference
implementation remain forthcoming. See the follow-up migration section.

These MUST be written fresh from the charter and ADRs. They MUST NOT be
extracted from any private repository.

## 7. Original migration plan (historical; preservation plan superseded)

The following was the additive-only foundation plan. Its instruction to
retain both source files and its rollback assumption no longer govern the
layout; the later explicit user direction in §8 removes that tree.

1. **Preserve.** Keep both `.proto` files unchanged in this change.
   This plan makes zero wire edits.
2. **Surround.** Add charter (`specifications/architecture.md`), ADRs,
   foundation docs, and RFC process around the preserved schemas —
   exactly what this change does.
3. **Govern.** Add Buf v2 config in a follow-up RFC (lint + breaking
   check). Tooling subsequently arrived under Draft RFC 0001; its layout
   decision is now recorded as implemented in §8. Future field/behavior
   edits retain the RFC and `reserved` preservation requirements.
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

Original rollback assumption (superseded): every step is additive. If a follow-up RFC is rejected, the
repository remains at this charter+ADRs+schemas state with no wire churn.

## 8. Pre-push checklist for `tinklehq/syntra`

### Follow-up sole-source IDL migration (2026-10-19)

Explicit user direction establishes `proto/syntra/v1` as the sole source of
truth and removes `schema/syntra/v1`. Draft
[RFC 0001](rfcs/0001-public-idl-layout.md) records that implemented layout
decision in B9; it remains Draft for unresolved behavior and review, without
claiming formal maintainer quorum or RFC acceptance.

Existing messages are physically split without renaming or renumbering;
binary declarations are preserved but source imports, owning descriptors,
and generated file-level APIs change. In particular `error.proto` becomes
`errors.proto`, and `Frame` moves from `session.proto` to `envelope.proto`.

The historical FILE comparison intentionally reports those known breaking
differences; layout authority is resolved, not awaiting layout approval.
The seven-file layout has an initial descriptor snapshot, not a fictitious
prior release. See [compatibility policy](specifications/schema/compatibility.md)
and [generation instructions](specifications/schema/generation.md).

Before removal, `compatibility/v1-initial/historical.json` is generated as
an immutable FileDescriptorSet from the actual unchanged sources from
commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9`:
[error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto)
and [session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto).
The manifest retains `historical_sources` path/hash provenance and adds
`historical_image_sha256`; the existing `image.json` baseline is unchanged.
Tests verify the archived descriptor hash and historical declarations,
without depending on a Git checkout or duplicate source tree. The updated
suite includes the original 12 checks plus a sole-source regression check
(13 total); post-deletion execution results are pending in the
[validation record](specifications/schema/validation.md).

Protocol/security blockers remain pending. The layout decision supplies
no missing capability/session/error binding or runtime conformance result.

### Original foundation checklist

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

## Appendix: inventory and independence commands (current source root)

The original audit searched the now-removed schema tree. Use `proto/` for
current source checks; historical declarations and source provenance are
in [the compatibility archive](compatibility/v1-initial/README.md).

```sh
find . -type f -not -path "./.opencode/*" -not -name ".DS_Store" | sort
grep -ri "chat\|contact\|receipt\|messenger\|tinkle-server\|kafka\|payment" proto/ || echo "no hits"
```
