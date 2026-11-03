# RFC 0012: Protocol reference scope

- RFC: 0012
- Title: Protocol reference scope
- Author(s): Syntra contributors
- Status: Draft
- Date: 2026-11-03
- Target version: Syntra 1.0 pre-release
- Relates to: [protocol overview](../README.md), [wire format](../specifications/wire-format.md), [conformance guide](../conformance/README.md)
- Reviewers: Unassigned; maintainer review required

## 1. Summary

The reference describes the current protocol independently of a language,
runtime, code organization, or test harness. Six pages cover representation,
establishment, RPC, security, transports, and update recovery. Supporting guides
describe schema tooling and verification. This proposal does not claim acceptance
or release authorization.

## 2. Motivation

A peer author needs to understand message bytes, their ordering, and their
observable meaning without adopting a particular runtime architecture. The
overview should explain the protocol before introducing tooling or test selectors.

## 3. Proposal

Protocol requirements describe exchanged messages, role obligations, validation,
state transitions, security boundaries, and failure behavior. They do not prescribe
tasks, callbacks, synchronization primitives, buffer ownership, or local APIs.
Ordered output, bounded work, once-only outcomes, and cryptographic state safety
remain obligations regardless of the mechanisms used to achieve them.

Runtime configuration defaults are not interoperability requirements. Retain
wire bounds, security ceilings, timeout semantics, negotiated bounds, and explicit
overload behavior; allow implementations to choose finite local settings within
those constraints. Test selectors remain test metadata, not protocol modules.

The pre-release reading path describes one current contract, without superseded
feature descriptions or migration instructions. Protocol fields, reserved values,
cryptographic constructions, and security policies are unchanged by this proposal.

## 4. Detailed design

The root overview gives the layers and a complete establishment/RPC exchange.
The six reference pages link to one another for detailed rules. Source IDL defines
representation. Conformance inputs, declarations, and tool pins belong in
supporting guides. Current requirement definitions and actual test assertions
determine the registry; removed design inventory is not an active requirement.

## 5. Alternatives considered

Leaving the combined reference unchanged keeps implementation assumptions in the
protocol contract. Moving prose without reviewing its normative force would only
hide those assumptions. The proposed separation retains observable guarantees
while making implementation mechanisms non-prescriptive.

## 6. Compatibility

There are no wire declarations, enum values, reservations, or encoding changes.
No format aliases or dual-format negotiation are introduced. The proposal changes
the scope of local implementation obligations, not the messages accepted by peers.
Schema compatibility checks remain enabled against the committed baseline.

## 7. Security considerations

Keep all current carrier/trust policies, mandatory Noise protection, independent
WSS TLS verification, fresh confirmation and hello validation, authorization
lifecycle, revocation deadlines, secret hygiene, resource ceilings, and fail-closed
behavior. Review proposed security or deployment policy changes separately.

## 8. Test plan and acceptance criteria

Repository regression tests check the documentation boundary, current selection,
ownership, and requirement-to-case references. Link and Markdown checks cover all
repository records. Schema tests verify unchanged declarations and reservations.
Fixture checks cover the public context and recovery encodings. These are static
checks, not runtime conformance or independent security approval.

## 9. Drawbacks and risks

Removing an implementation prescription can accidentally remove an observable
guarantee. Review the retained ordering, expiry, authorization, output, and recovery
rules together with their fixtures. Do not turn missing coverage into a passing
claim or infer security from a document build.

## 10. Unresolved questions and blockers

Maintainer review of the requirement-scope changes is required before acceptance.
No approval is implied by preparing the reference or by passing repository checks.
