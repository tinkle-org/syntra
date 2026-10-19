# ADR-002: Protobuf as the Public IDL

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 5, 8; `proto/syntra/v1/*.proto`

## Context

Syntra needs a binary serialization format with multi-language support,
version tolerance, and established tooling. Candidates include Protocol
Buffers (proto3), FlatBuffers, Cap'n Proto, CBOR/CDDL, and a bespoke
binary envelope.

## Decision

Syntra uses Protocol Buffers (proto3) as the sole public Interface
Definition Language:

1. `proto/syntra/v1/*.proto` is the authoritative data representation (sole source; original `schema/syntra/v1/` tree removed after user-directed migration, declarations preserved).
2. Schema governance uses Buf v2 (lint + breaking-change detection).
3. Transport framing is kept separate from Protobuf encoding (see ADR-003).
4. No replacement binary IDL will be invented.

## Alternatives considered

- **FlatBuffers / Cap'n Proto (zero-copy).** Rejected for v1: smaller
  ecosystem for required languages, weaker unknown-field conventions,
  and higher implementation burden for equivalent interop.
- **CBOR / CDDL or JSON.** Rejected for the core envelope: larger
  encoding variance and weaker codegen/governance story for strict wire
  compatibility.
- **Custom IDL.** Rejected: violates the project constraint to avoid
  inventing a replacement IDL; fragments tooling and review.

## Consequences

- Implementers use `protoc` / Buf managed codegen in any language.
- Unknown-field tolerance comes from Protobuf semantics; specifications
  define strictness per field (ignore vs. reject).
- Build tooling MUST pin `protoc`/Buf versions for reproducible codegen.

## Compatibility implications

- Field numbers, types, and `reserved` values are wire contracts.
  Buf breaking-change checks gate every schema change.
- Proto3 semantics (zero values, `oneof` discipline) are part of v1.
  Changing IDL (e.g., to proto2 semantics or another format) REQUIRES a
  major version and RFC.

## Status

Accepted. The existing v1 declarations are preserved unchanged under this ADR, now distributed across `proto/syntra/v1/` as the sole source.
