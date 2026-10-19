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
8. Post-quantum TLS policy (follows the TLS implementation's defaults; no Syntra negotiation).
9. Formal analysis supplement (TLA+/ProVerif of handshake/auth state machines — valuable, not required for draft).

## Decisions deliberately NOT reopened

- No custom cryptography, no application E2EE in core, no URL credentials, TLS≠idempotency, opaque discipline, at-most-once default — closed per charter/ADRs; reopening REQUIRES a major RFC with migration and threat re-analysis.
