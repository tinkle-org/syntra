# Schema compatibility policy

Status: Draft review policy, alongside [RFC 0001](../../rfcs/0001-public-idl-layout.md).
The user-directed layout decision is implemented and recorded in RFC B9;
this policy allocates no requirement IDs and does not replace governance,
ADR-009, or [core versioning](../core/versioning.md). Formal maintainer/RFC
approval of the remaining behavior is not claimed.

## Three separate compatibility dimensions

| Dimension | Examples | Evidence |
|---|---|---|
| Binary wire | Field number/type, scalar presence, oneof membership, enum numbers, reserved tags | Buf WIRE audit plus explicit descriptor/codec fixtures |
| Generated source and descriptors | Type/package/field names, proto import paths, owning files, file-level descriptor symbols, generator versions/options | Buf **FILE**, generated-language compilation and consumer migration review |
| Behavior | State transitions, authentication/authorization, limits, deadlines, errors, optional feature gating, delivery/replay semantics | Normative RFC review and runtime conformance/interop tests; **not certified by Buf** |

Matching wire types alone is insufficient. A moved type retains binary
encoding but can break a descriptor consumer. A wire-additive field can
break behavior if older peers are required to act on it. Go/Rust convenience
APIs are non-normative and never define protocol semantics.

## Current migration and baseline

- Historical sources: the removed `schema/syntra/v1` files from commit
  `92e5f281aa7c3adac9ba78588c1140b12d55c1d9`. The immutable
  `compatibility/v1-initial/historical.json` FileDescriptorSet was generated
  from those actual unchanged sources before removal. The manifest retains
  `historical_sources` path/hash provenance and adds `historical_image_sha256`.
- Sole authoritative source: `proto/syntra/v1`, module root `proto` in `buf.yaml`.
  All eight messages and the enum are identical declarations, except for
  file ownership/import graph. `Frame`, `ServerReady`, `RpcResult`, and
  `Notification` keep their existing fully qualified names.
- The original historical comparison passed WIRE, but **failed FILE by design**:
  `syntra/v1/error.proto` disappears; seven message declarations leave
  `syntra/v1/session.proto`. This remains a known breaking source difference
  after the user-directed layout decision, not a clean source-compatibility
  result or a pending layout approval. Consumers migrate imports and regenerate
  bindings from `proto`; historical sources are available at the pinned commit,
  not as a second live source root.
- [`compatibility/v1-initial`](../../compatibility/v1-initial/README.md) is
  the first versioned seven-file descriptor snapshot. Its existing `image.json`
  is unchanged; FILE checks against it gate future edits. It is not a prior
  release or evidence of formal RFC approval. The repository has no prior
  release tag. The archived historical descriptor is a separate comparison input.

`buf.yaml` always uses FILE with no ignored files/rules. A separate WIRE
comparison in tests is migration evidence, not a weaker replacement gate.
Baseline replacement is a reviewed change, never an automatic CI repair.
Tests verify the archived descriptor hash and historical declarations without
a Git checkout or duplicate schema tree. The original validation run and
pending post-deletion results are distinguished in [validation](validation.md).

## Review checklist for later changes

1. Cite the defining requirements and an approved RFC for wire/behavior
   changes. Resolve conflicts first; no undocumented runtime choices.
2. Preserve published field numbers, types, names, package identity,
   presence and oneof membership. Reserve removed field **numbers and names**,
   and removed enum numbers/names; never recycle them in v1. A deletion may
   still break source APIs even when reserved properly.
3. Retain `Frame`'s permanent reservations: 16, 17, `event`, `resume`, `ack`.
4. Keep zero enum values non-successful where the registry defines them so.
   Unknown received error numbers map to UNKNOWN at the reporting layer;
   preserve raw numbers diagnostically where possible, never crash/succeed.
5. Do not depend on serialization order, generated debug strings, or whole
   serialized-byte equality. Do not require parsing opaque payload semantics.
6. New optional behavior needs an approved capability binding, bounded
   identifiers/parameter sizes/counts, explicit confirmation, unsupported-option
   behavior, and mandatory-only interop. Unknown fields are not negotiation.
7. Execute format/lint/build/generate, FILE against the last real accepted
   baseline, both language tests, and relevant behavioral conformance tests.
   Record actual results and expected migration failures separately.
8. Review generator/runtime/toolchain upgrades for generated-source breaks
   independently of unchanged IDL; update pins and lockfiles deliberately.

## Runtime gaps are not schema compatibility fixes

The raw-wire oneof, unknown-body classification, reserved-tag rejection,
typed handshake-error carrier, stale-ID reuse, pre-ACTIVE event handling,
and envelope/payload size conflicts are tracked in RFC 0001 B1–B8 and B10;
B9's layout authority decision is resolved. The protocol gaps are
not resolved by successful generation, a green FILE comparison, or a new
Protobuf field. No new error category is allocated without registry review.
