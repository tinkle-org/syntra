# Syntra v1 Security — Review Checklist

- Identifier: `specifications/security/review-checklist.md`
- Title: Security Review Checklist (for RFCs, specs, and implementations)
- Status: Draft (informative; REQUIRED for security-adjacent RFC approvals per `GOVERNANCE.md`)
- Version: 1.0.0-draft.1 (2026-10-26)
- Scope: What reviewers MUST verify before approving any security-adjacent change. This file adds no behavior; it operationalizes the normative documents.
- Terminology: Per `core/protocol.md`.

## A. General (every security-adjacent RFC)

- [ ] Threat mapping: which T1–T10 in `threat-model.md` are affected, and which `SNTR-TSEC/ASEC/RPL/OPQ` IDs cover them?
- [ ] No custom crypto: no new cipher, TLS implementation, ratchet, E2EE handshake, or algorithm negotiation in Syntra fields?
- [ ] Generic auth preserved: no user-account assumption, no private identity service, no URL credentials?
- [ ] Opaque discipline: core does not parse/decrypt payloads; limits enforced on byte length regardless of format?
- [ ] Error hygiene: `UNAUTHENTICATED` vs `PERMISSION_DENIED` justified; messages generic; no secret/diagnostic echo; constant-time compare where applicable?
- [ ] Bounds documented: frame size, concurrency, timers, queue/rate limits, propagation windows?
- [ ] Downgrade analysis: highest-secure-overlap preserved; no silent fallback to plaintext/weaker version?
- [ ] Proxy analysis (if in path): backend-leg security, SNI/Host/ALPN consistency, mismatch → failure?

## B. Per-document checks

- [ ] Transport (`transport-security.md`): TLS 1.3 minimum, chain + hostname + expiry/revocation, rotation without pinning trap, ALPN correct, plaintext dev-only with warning?
- [ ] Authentication (`authentication-security.md`): confidentiality (no log/persist/echo), carriage only in defined fields, expiry/revocation/rotation defined, fixation defenses (fresh `connection_id`), disclosure discipline, hooks (rate-limit + authorization) before dispatch?
- [ ] Replay (`replay-protection.md`): all five classes addressed independently; TLS≠idempotency stated; `request_id` not used cross-connection; operation-key bytes preserved?
- [ ] Opaque (`opaque-payloads.md`): no E2EE in core, no format negotiation, transport still required for encrypted payloads, same limits for ciphertext?

## C. Tests and traceability

- [ ] Which `SNTR-STEST-001–011` groups cover the change? New fixtures added for new behavior?
- [ ] Negative tests for every new `MUST NOT`? Downgrade/replay/exhaustion negatives included?
- [ ] Neutral fixtures only (echo / generic key/value / generic subscription)?
- [ ] Ambiguities recorded in `open-questions.md`, not resolved by code?

## D. Compatibility and disclosure

- [ ] Additive vs breaking classified per `versioning.md`; `reserved` untouched; deprecation notice if withdrawing?
- [ ] Residual risks updated in `threat-model.md` appendix if the change accepts new risk?
- [ ] No private product, infrastructure, or domain-type leakage (SYN-ARCH-001/002)?

Approval REQUIRES all applicable boxes checked with requirement-ID citations on the RFC.

## E. RFC 0007 acceptance review (retained reference)

These items review [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
and its accepted [SC](secure-channel.md), [DAUTH](device-authorization.md)
and [carrier](../transports/noise-bindings.md) contracts. The acceptance record
is RFC 0007 §11.4 and
[Decision 0001](../../docs/decisions/0001-bootstrap-ratification.md); unchecked
boxes are not an approval or evidence record. Sections A–D and current
TLS/certificate tests continue to apply to existing profiles.

- [x] Policy/status: RFC 0007 and ADR-011 are accepted; SC1/WSS is additive and does not replace ADR-008 or remove TLS 1.3.
- [ ] Construction: exact NK bootstrap and NKpsk0 returning suites, authenticated server-key provisioning, canonical context, fresh ephemerals/directional keys, no automatic fallback or reused channel state (SC-001–005/009/013)?
- [ ] Enrollment: host-issued unique random shared 32-byte AK only after authorized bootstrap; durable issuance/acknowledgment/retry contract; no selected signing-key-pair or required human-account model (DAUTH-001/002/005)?
- [ ] Handle: independent eight-byte `auth_id`, collision-checked scoped lookup with no authority; epoch binding, bounded unknown-handle work, enumeration/correlation and rotation privacy addressed (DAUTH-003/008)?
- [ ] Freshness: replayed first flights grant no binding/effects; empty handshake payloads, no 0-RTT effects, fresh client transport-record confirmation and current authorization before `ready`/dispatch (SC-004/006, DAUTH-005/008)?
- [ ] Lifecycle/integration: wrapped usable-AK storage, impersonation exposure, expiry, active-binding revocation and crash-safe rotation; trusted connection-scoped hook preserves opaque credentials, diagnostic IDs and generic principals (DAUTH-004–010)?
- [ ] Bounds/close: numeric channel and total-attempt budgets, authenticated complete records, bounded envelope reconstruction, partial writes/cancellation, nonce ceilings and truncation/unknown outcomes covered (SC-007–012/014)?
- [ ] Carriers: separate identifiers; existing WS binary-message-to-`Frame` and `syntra.v1` unchanged; candidate WS ciphertext distinct, browser outer WSS TLS retained, and UDP deferred until its complete binding is frozen/reviewed/accepted?
- [ ] Evidence: independent vectors/interop and negative cases in the [planned acceptance work](../../conformance/plans/secure-channel.md); no shipping, conformance, audit, measured-performance or post-quantum claims inferred from the proposal (SC-015)?
