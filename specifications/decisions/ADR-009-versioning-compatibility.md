# ADR-009: Protocol Versioning and Compatibility

- Status: Accepted
- Date: 2026-10-19
- Owner: Syntra maintainers (see `GOVERNANCE.md`)
- Relates to: `specifications/architecture.md` Sec. 6, 8, 10; `GOVERNANCE.md`

## Context

Syntra v1 must evolve without silently breaking peers. Protobuf permits
additive changes, but semantic changes (new required behavior, altered
state machines, repurposed fields) need explicit governance.

## Decision

1. **Wire version:** `Frame.version` carries the negotiated version
   (currently 1). `ClientHello{min_version, max_version}` proposes a
   range; the host selects or fails with a typed error.
2. **Buf v2 governance:** lint + breaking-change detection gate every
   schema edit. `reserved` numbers/names are permanent.
3. **Unknown handling:** unknown fields are ignored; unknown
   `Frame.body` variants are rejected with `UNIMPLEMENTED` (never
   silently dropped).
4. **Mandatory vs. optional:** handshake, RPC, cancel, and typed errors
   are mandatory. Notifications/streams, resumption, and future
   capabilities are OPTIONAL and negotiated. Peers MUST NOT require an
   unnegotiated option.
5. **Change classes:** additive-compatible changes are minor (RFC,
   minor version or clarification); wire-incompatible changes are major
   (new major version, RFC, migration guide, dual-support window where
   feasible).
6. Every normative requirement carries an ID and a conformance test
   link.

## Alternatives considered

- **Semver on prose only, no wire version.** Rejected: peers cannot
  negotiate at runtime.
- **Strict rejection of all unknowns.** Rejected: prevents forward
  compatibility; every addition would break old peers.
- **Silent ignore of unknown messages.** Rejected: hides mismatch and
  makes debugging nondeterministic.

## Consequences

- Specifications version behavior explicitly; tests cover negotiation
  success, downgrade refusal, unknown-field tolerance, and
  unknown-message rejection.
- `CHANGELOG.md` records every wire-affecting change with migration
  notes.

## Compatibility implications

- This ADR freezes v1 rules. Any exception (e.g., reusing a reserved
  number) is itself a major-version RFC.
- Minor additions MUST be backward compatible; clients MUST tolerate
  newer minor fields they do not understand.

## Status

Accepted.
