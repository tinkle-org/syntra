# Syntra v1 Core — Capability Negotiation and Extensions

- Identifier: `specifications/core/capabilities.md`
- Title: Mandatory vs Optional Capabilities and Extension Rules
- Status: Partially accepted (2026-10-30) — negotiation-mechanics owner file for accepted [RFC 0005](../../rfcs/0005-negotiation-bounds-identifiers.md) D1/D2/D4 per [Decision 0002](../../docs/decisions/0002-sdd-acceptance-wave.md); reliable-session shipping authority (`SNTR-CAP-008`/`SNTR-CAP-902`, marked proposal-only inline) remains pending a future RFC
- Version: 1.0.0-draft.1 (2026-10-19, accepted-paragraph corrections 2026-10-30)
- Normative references: BCP 14; `protocol.md` (SNTR-CORE-004); `handshake.md`; `versioning.md`; `GOVERNANCE.md`; ADR-009
- Scope: How peers negotiate and use OPTIONAL behavior (e.g., event streams, resumption, extension payloads) without breaking mandatory interop. Capability identifiers and extension payloads themselves are defined by their respective RFCs; this document defines only the negotiation mechanics and rules.
- Terminology: Per `protocol.md`. **Mandatory** = required for interop (handshake, RPC, cancel, errors, versioning). **Optional** = negotiated (streams, resumption, extensions). **Extension** = RFC-defined optional addition.

The key words "MUST", "MUST NOT", etc. are per BCP 14.

## 1. Protocol requirements

**SNTR-CAP-001** — Every optional behavior MUST have a stable capability identifier (ASCII, e.g., `syntra.events/1`, `syntra.resume/1`) defined by its RFC. Identifiers MUST be versioned; unversioned or ambiguous identifiers MUST be rejected.

**SNTR-CAP-002** — Negotiation MUST be explicit. A peer MUST NOT assume support, MUST NOT probe by sending optional frames, and MUST NOT require an unnegotiated option. Per accepted [RFC 0005](../../rfcs/0005-negotiation-bounds-identifiers.md) D1, there is NO generic core capability enumeration, hello-extension list, or optional-frame probing mechanism in scope: capability/session extension for a profile is negotiated as part of that profile's own accepted contract — post-ACTIVE, via an ordinary RPC defined by the profile's accepted RFC, which owns the exact method, versioned payloads, bounds, confirmation, and unknown-input handling (e.g., the accepted [RFC 0006](../../rfcs/0006-update-recovery-profile.md) defines `syntra.update-recovery/1` negotiation via `/syntra.v1.UpdateRecovery/Negotiate`). Only the defined negotiation call is exempt from prior confirmation of its own profile; no other unconfirmed profile operation is permitted. Confirmation never resumes a session, enables another connection, or authorizes a different principal. No resumption, session-extension, multi-round-auth, event-stream, or replay capability exists in default v1: any such identifier — including the `syntra.events/1` and `syntra.events.replay/1` names proposed (not allocated) in `events.md` §1A — is unnegotiated until its RFC defines the binding, confirmation, bounds, and failure semantics (see `sessions.md` §1C–§1E, `authentication.md` §1A, `events.md` §1A/§1I, `rfcs/0002-auth-session-lifecycle.md`).

Negotiated limit overrides follow the same mechanism rule (accepted RFC 0005 D2): any bound-value override (concurrency, envelope size, grace, credential/diagnostic limits) MUST bind to explicit accepted negotiation under a profile's own contract — there is no negotiated escape below a core floor and no silent override of core limits. Core floors and defaults (e.g., the ≥16 supported-concurrent-RPC floor, the 1 MiB default envelope, the 4 KiB public diagnostic bound) hold via their owning documents; this section states the mechanism, not the numerics.

**SNTR-CAP-003** — Mandatory interop MUST NOT depend on any optional capability. A minimal implementation supporting only mandatory behavior MUST interoperate (with reduced functionality) against a full implementation.

**SNTR-CAP-004** — Unknown capabilities MUST be ignored if advertised as optional-by-peer, and MUST cause `UNIMPLEMENTED` only when the peer *requires* them. A host MUST NOT fail a handshake solely because the initiator advertised an unknown optional capability.

**SNTR-CAP-005** — Extensions MUST NOT alter mandatory state machines, envelope validation (SNTR-WIRE-*), or error semantics. They MAY add new `Frame.body` variants (minor, with capability gating), new methods, or new transports — each via RFC.

**SNTR-CAP-006** — Experimental capabilities MUST be clearly marked (identifier contains `exp`, documented as unstable) and MUST NOT affect mandatory interop or conformance claims.

**SNTR-CAP-007** — Deprecation: withdrawing an optional capability REQUIRES an RFC, a deprecation notice period, and a `versioning.md` entry. Peers MUST tolerate withdrawal gracefully (`UNIMPLEMENTED` + fallback, not connection failure where fallback exists).

**SNTR-CAP-008** — Reliable-session capability `syntra.reliable-session/1` (OPTIONAL, minor-additive, no envelope change): negotiation is explicit post-`ACTIVE` generic-RPC control (no handshake binding, no new `Frame` variant, reserved values preserved). Initiators advertise the identifier; hosts confirm only the subset implemented for the bound principal and per connection (confirmation on one connection never enables another). Unconfirmed use MUST fail with `FAILED_PRECONDITION` (RPC context) per §4; required-but-unsupported MUST fail with `UNIMPLEMENTED`. Confirmation MUST cite this identifier and the bounds in `sessions.md` §1H / `reliability.md` §1C. Mandatory-only peers MUST interoperate without it (SNTR-CAP-003). Draft-proposal notice: this SNTR-CAP-008 is proposal-only and carries no normative force until its authorizing RFC is accepted. Until acceptance, implementations MUST NOT ship behavior from it, and no test, claim, or release MAY cite it as authority.

No accepted reliable-session negotiation method or payload schema is
recorded. The identifier above is proposed, not an allocation or shipping
authorization. The `CONF-RS-*` plans in `sessions.md` §7.1 are not executable
wire fixtures. Local implementation APIs/unit tests and runner aggregates
do not establish negotiation conformance. Shipping authority for reliable
sessions remains deliberately deferred — the RFC 0002 disposition (§10,
reliable-session authority) keeps it open for a future RFC; the current
acceptance wave does not activate this offer.
`syntra.reliable-session/1` is proposal-only until a future RFC grants that
authority.

## 2. Client behavior

- **SNTR-CAP-010** — The client MUST advertise only capabilities it implements, MUST handle partial acceptance (subset confirmed), and MUST fall back to mandatory-only operation when an option is unavailable.
- **SNTR-CAP-011** — The client MUST NOT send extension frames for unconfirmed capabilities.

## 3. Server behavior

- **SNTR-CAP-020** — The server MUST confirm only capabilities it implements for the bound principal, MUST reject required-but-unsupported capabilities with `UNIMPLEMENTED`, and MUST document supported capabilities per deployment.
- **SNTR-CAP-021** — The server MUST isolate capability state per connection; negotiation on one connection MUST NOT enable options on another.

## 4. Failure handling

Required-but-unsupported → `UNIMPLEMENTED` (RPC context) or handshake failure (if handshake-gated). Use of an unconfirmed option → `FAILED_PRECONDITION` for a connection whose capability context is otherwise confirmed; a profile's own pre-confirmation operation handling is owned by that profile's accepted contract per §1 (SNTR-CAP-002) — the accepted recovery profile, for example, refuses profile operations on a connection that has not confirmed the profile with `UNIMPLEMENTED` and reserves `FAILED_PRECONDITION` for an unconfirmed option on a confirmed connection (`SYN-URP-010` in RFC 0006). Unknown optional advertisement → ignored with diagnostic.

## 5. Security considerations

Capability confusion (downgrade to weaker option) is a threat: negotiated sets MUST be integrity-protected by the secure transport; hosts MUST NOT silently downgrade security-relevant capabilities. Experimental options MUST NOT bypass authentication or bounds.

## 6. Compatibility considerations

Capabilities are the minor-evolution path (ADR-009). New mandatory behavior is never a capability — it is a major version. Capability identifiers are frozen once accepted; renaming REQUIRES a new identifier + deprecation of the old.

## 7. Conformance requirements

- **SNTR-CAP-900** — Fixtures: mandatory-only interop against full peer; unknown optional ignored; required-but-unsupported → `UNIMPLEMENTED`; unconfirmed-option use → `FAILED_PRECONDITION`; experimental marked and isolated.
- **SNTR-CAP-901** — Negotiation trace: each optional feature exercised MUST cite its capability identifier and RFC.
- **SNTR-CAP-902** — Proposed reliable-session negotiation coverage (OPTIONAL, gated after acceptance): advertise `syntra.reliable-session/1` post-`ACTIVE`; explicit confirmation; partial acceptance falls back to mandatory-only; unconfirmed session control → `FAILED_PRECONDITION`; confirmation remains connection-scoped. `CONF-RS-001` is a non-executable draft plan in `sessions.md` §7.1 pending an accepted canonical negotiation contract. Former attach/drain rows did not exercise negotiation and provide no evidence for this requirement. This requirement has the same proposal-only status as SNTR-CAP-008.

```mermaid
sequenceDiagram
  participant C as Initiator
  participant H as Host
  Note over C,H: handshake (hello/ready) → ACTIVE; core available mandatory-only
  Note over C,H: no generic advertisement/probe channel exists
  C->>H: request{profile negotiation method per its accepted RFC}
  H-->>C: result{confirmed version + bounds for THIS connection}
  C->>H: use an option without confirmation (FORBIDDEN → FAILED_PRECONDITION)
  C->>H: require an unsupported option (→ UNIMPLEMENTED)
```
