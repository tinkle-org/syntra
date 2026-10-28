# Syntra v1 Security — Open Questions and Unresolved Decisions

- Identifier: `specifications/security/open-questions.md`
- Title: Unresolved Security Decisions
- Status: Living list (blockers MUST be resolved before stable release per `GOVERNANCE.md`; non-blockers are future RFCs)
- Version: 1.0.0-draft.1 (2026-10-26)
- Scope: Security-relevant ambiguities intentionally left open in this draft. Implementations MUST NOT resolve blockers by undocumented choice; they MUST record the blocker and fail closed.
- Terminology: Per `core/protocol.md`.

## Blockers for stable v1

1. **Channel-binding mechanism (blocker if claimed).** `authentication-security.md` SNTR-ASEC-002 explicitly does not claim channel binding. If stable v1 claims binding (e.g., TLS exporter to credential), the exporter construction, negotiation, and failure semantics REQUIRE a dedicated RFC. Until then, “channel bound” MUST NOT appear in conformance claims.
2. **Revocation-propagation bound (blocker).** Maximum staleness (time from revocation to enforcement) is deployment-documented but has no suite-wide upper bound. Stable v1 MUST set a default maximum (candidate: ≤5 minutes for public deployments, tighter for high-risk applications) or explicitly allow deployment-defined values with test verification of the documented value.
3. **Revocation/expiry transport for offline hosts (blocker if offline operation claimed).** How hosts without fresh revocation data fail closed (deny vs cached-allow with short TTL) MUST be specified before any “offline-capable” conformance claim.
4. **Proxy identity propagation format (blocker if proxied public deployments claimed).** SNI/Host/ALPN consistency is REQUIRED, but the exact backend-propagation field (header, mTLS identity, or private-network attestation) is transport-profile work. At least one proxied topology MUST be fully specified and tested before stable.
5. **Resume-token standard (blocker only if resumption claimed).** Default v1 has no resumption. Any resumption RFC MUST define token format, entropy, audience binding, lifetime, rotation, and replay windows before a resumption conformance claim.

## Non-blockers (deferred, fail-closed defaults apply)

6. Per-method rate-limit defaults (currently deployment-defined; a recommended baseline may follow operational experience).
7. Padding/quantization guidance for size/timing oracles (application-level; transport cannot fully remove them).
8. Post-quantum policy (future work). Current TLS profiles follow the established TLS implementation's secure defaults, with no Syntra cryptographic negotiation. RFC 0007's selected classical Noise suites make no post-quantum claim; any future construction needs its own RFC, binding and verification rather than an inferred v1 negotiation option.
9. Formal analysis supplement (TLA+/ProVerif of handshake/auth state machines — valuable, not required for draft).

## Decisions deliberately NOT reopened

- No custom cryptography, no application E2EE in core, no URL credentials, TLS≠idempotency, opaque discipline, at-most-once default — closed per charter/ADRs; reopening REQUIRES a major RFC with migration and threat re-analysis.

## RFC 0007 blockers (proposal-specific)

[Draft RFC 0007 §10](../../rfcs/0007-secure-channel-device-authorization.md#10-unresolved-questions-and-blockers)
owns these blockers. Its [shared channel](secure-channel.md),
[device authorization](device-authorization.md) and
[carrier candidates](../transports/noise-bindings.md) describe a selected
target, not an exception to current TLS policy or the blockers above.

1. **Authority and compatibility.** Assign protocol/cryptographic reviewers; accept the policy amendment proposed in [ADR-011](../decisions/ADR-011-noise-device-authorization.md). Replacing required profiles needs an explicit major-version/deprecation decision and migration window.
2. **Context and server-key trust.** Freeze canonical mode/version/carrier/endpoint/handle/epoch bytes, server-key selection and authenticated provisioning/rotation. No automatic suite or mode fallback is selected.
3. **Enrollment contract.** Specify host issuance of a unique random shared 32-byte AK after authorized NK bootstrap, protected transfer, durable commit/acknowledgment, bounded RPC or out-of-band contract, retries and interrupted-enrollment recovery. No signing-key-pair mechanism is selected.
4. **Trusted principal integration.** Define connection-scoped verified context for implementation authentication, distinct from client metadata or anonymous empty credentials; preserve generic principals, per-method policy and existing `ServerReady` semantics.
5. **Freshness and resource defaults.** Freeze numerical establishment/assembly/write/close and aggregate budgets, total-attempt limits, lifetime ceilings, and fresh client-record confirmation before protected effects. Empty handshake payloads exclude 0-RTT application effects.
6. **Credential lifecycle/privacy.** Specify usable-AK storage access, scoped eight-byte handle collision/lookup behavior, enumeration/correlation controls, expiry and active-channel revocation bounds, concurrent rotation overlap and crash recovery.
7. **Carrier freeze.** Assign separate TCP/WS identifiers and WS subprotocol/endpoint selection; preserve existing binary-message-to-`Frame` mapping and browser outer TLS. UDP stays deferred until a complete frozen, reviewed and accepted binding covers demux, counters/replay window, path validation, anti-amplification, reliability and bounded fragmentation.
8. **Verification.** Produce independent vectors, cross-implementation interoperability and full-composition security review against the [planned acceptance cases](../../conformance/plans/secure-channel.md). No production, conformance, performance-superiority or post-quantum claim follows from documenting the target.
