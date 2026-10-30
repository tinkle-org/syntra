# Syntra v1 Security — Open Questions and Unresolved Decisions

- Identifier: `specifications/security/open-questions.md`
- Title: Unresolved Security Decisions
- Status: Living list (blockers MUST be resolved before stable release per `GOVERNANCE.md`; non-blockers are future RFCs)
- Version: 1.0.0-draft.1 (2026-10-26)
- Scope: Security-relevant ambiguities intentionally left open in this draft. Implementations MUST NOT resolve blockers by undocumented choice; they MUST record the blocker and fail closed.
- Terminology: Per `core/protocol.md`.

## Blockers for stable v1

1. **Channel-binding mechanism (blocker if claimed).** `authentication-security.md` SNTR-ASEC-002 explicitly does not claim channel binding. If stable v1 claims binding (e.g., TLS exporter to credential), the exporter construction, negotiation, and failure semantics REQUIRE a dedicated RFC. Until then, “channel bound” MUST NOT appear in conformance claims.
2. **Revocation-propagation bound (blocker) — RESOLVED (2026-10-30, RFC 0010).** The staleness maximum is now a decided policy: [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md) records it as requirements `SNTR-DAUTH-017`–`SNTR-DAUTH-019` in [device-authorization.md](device-authorization.md) (which assign the keyword force); the candidate “≤5 minutes” bound of this entry is adopted as the default public production profile 300-second hard maximum. Recording it verbatim:
   - New connections: immediate enforcement — a revoked enrollment MUST NOT authenticate on a newly established connection.
   - Existing connections: maximum 300 seconds from authoritative revocation commit to enforcement (hard profile maximum).
   - Operational target: enforce within 60 seconds, preferably immediately through push invalidation.
   - After the deadline: deny new protected operations and delivery; close affected channels.
   - Revocation-store unavailable: fail closed when current validity cannot be established or the permitted freshness window expires.
   - High-security deployments may enforce shorter bounds or zero grace; longer grace is NOT permitted under the default public production profile.
   - Wording notes: the 300-second figure is a maximum tolerated stale-authorization window, not a mandatory waiting period; hosts should revoke immediately when possible; already-committed application effects cannot be retroactively undone; a nominal watchdog interval does not prove propagation.
3. **Revocation/expiry transport for offline hosts (blocker if offline operation claimed) — RESOLVED (2026-10-30, RFC 0010).** Decided: fail closed, cached-allow is refused. When current validity cannot be established — a failed or timed-out authorization-store read, a cache beyond the deployment's declared freshness bound, or an unresolved revocation state — hosts deny new admissions and close established channels no later than the last successful validity check plus the deployment's declared bound, within RFC 0010's 300-second profile maximum (`SNTR-DAUTH-019`, bound owner `SNTR-DAUTH-018`). Availability is not bought by admitting under stale or unverifiable revocation state. Any conformance claim about “offline-capable” authorization still requires its own accepted profile and executed tests.
4. **Proxy identity propagation format (blocker if proxied public deployments claimed).** SNI/Host/ALPN consistency is REQUIRED, but the exact backend-propagation field (header, mTLS identity, or private-network attestation) is transport-profile work. At least one proxied topology MUST be fully specified and tested before stable.
5. **Resume-token standard (blocker only if resumption claimed).** Default v1 has no resumption. Any resumption RFC MUST define token format, entropy, audience binding, lifetime, rotation, and replay windows before a resumption conformance claim.

## Non-blockers (deferred, fail-closed defaults apply)

6. Per-method rate-limit defaults (currently deployment-defined; a recommended baseline may follow operational experience).
7. Padding/quantization guidance for size/timing oracles (application-level; transport cannot fully remove them).
8. Post-quantum policy (future work). Current TLS profiles follow the established TLS implementation's secure defaults, with no Syntra cryptographic negotiation. RFC 0007's selected classical Noise suites make no post-quantum claim; any future construction needs its own RFC, binding and verification rather than an inferred v1 negotiation option.
9. Formal analysis supplement (TLA+/ProVerif of handshake/auth state machines — valuable, not required for draft).

## Decisions deliberately NOT reopened

- No custom cryptography, no application E2EE in core, no URL credentials, TLS≠idempotency, opaque discipline, at-most-once default — closed per charter/ADRs; reopening REQUIRES a major RFC with migration and threat re-analysis.

## RFC 0007 accepted decisions and remaining gates

[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md) is accepted.
Its [shared channel](secure-channel.md), [device authorization](device-authorization.md)
and [carrier profile](../transports/noise-bindings.md) are normative for
`SNTR-SC1-WSS-V1`. The profile is additive: it does not weaken transport
security above or replace the baseline TLS profiles. The host lifecycle
companion contract is [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md):
it fixes revocation-propagation bounds, staged provisioning, rotation and
compromise-recovery obligations as `SNTR-DAUTH-011`–`SNTR-DAUTH-024`, closing
items 2–3 of `Blockers for stable v1`; it introduces no wire change and
standardizes no online enrollment RPC (a portable online enrollment RPC may
become a separate explicitly negotiated profile later).

### Accepted definitions

- **Context/carriers.** The [SC1/WSS mapping](../transports/noise-bindings.md)
  defines exact domain `syntra.sc1.v1`, mode/carrier/server-key selector, epoch,
  handle and exact UTF-8 scope bytes, carried before M1 and authenticated as the
  Noise prologue. TCP wraps every handshake/record in `u16BE`; WS/WSS use one
  binary message per handshake/record with the exact subprotocol
  `syntra.sc1.v1` at `/syntra/v1/sc1/ws`. The `draft-1` and local-revision-1
  formats are historical and are not aliases. Existing WS/WSS bytes remain
  unchanged; HTTP/HTTPS request-response is excluded from SC1.
- **First envelope.** The first authenticated plaintext is exactly one complete
  framed `ClientHello`; it may span records, and the completing record ends at
  the hello boundary. No second complete or partial envelope is permitted
  there. Host policy runs before `ready` and before protected effects.
- **Authentication/resources.** Fresh client confirmation, fail-closed method
  authorization, bounded ordered adapters and the post-ready host writer are
  required. The accepted defaults and maxima are in
  [noise-bindings.md](../transports/noise-bindings.md) §8. No automatic
  reconnect, replay or fallback is provided. Replayed M1 supplies no fresh
  client confirmation.
- **Executed verification.** The Rust implementation records local
  unit/race/native-core/transport tests and security checks as implementation
  evidence. They are not independent cryptographic/runtime interoperability,
  executed `CONF-SCW-*` verdicts or a security audit. Independent vectors,
  pure-Go/Rust both-role and both-mode runs, direct-topology tests,
  mobile/recovery evidence and independent human review remain release gates.

### Partial integration and responsibilities

- **Host-policy boundary.** The bridge requires confirmed client transport and
  a nonempty policy principal, but does not automatically compare that principal
  with the channel principal, independently verify trusted root identity or
  synchronously `Check` enrollment before `ready`. Host policy owns those checks;
  empty hello credentials never automatically authorize and nil `Authorize`
  denies methods. Ordinary credential carriage and `ServerReady` remain intact.
- **Preprovisioned lifecycle.** Full-context lookup validates returned key,
  principal, expiry and revocation. Keys are immutable within a handle/epoch;
  later `Check` checks validity/principal, not key equality. The watchdog starts
  at first confirmation and uses a 1-second tick and 1-second lookup contexts,
  including idle channels: not an exact 1-second revocation SLA. Principal
  disconnect closes current connections, not future admission. Close remains
  dependent on cancellation-compliant I/O/store callbacks.
- **Codec/native boundary.** Reserved fields 16/17 are rejected both ways,
  credentials have an 8 KiB pre-allocation gate, and depth-32/full validation is
  implemented. Native-ABI completion timestamps and post-hello credential
  release remain gaps; codec tests do not close them.

### Open blockers and deferred work

1. **Profile replacement.** Replacing required profiles requires an explicit
   version/deprecation decision and migration window. SC1/WSS is additive and
   does not replace the baseline TLS profiles.
2. **Enrollment and storage.** Only out-of-band preprovisioning is delivered.
   [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md) now
   specifies the required lifecycle transaction (`SNTR-DAUTH-011`–`SNTR-DAUTH-014`):
   enrollment authority, host-generated AK/handle issuance, the staged
   provision/deliver/ack/commit flow with idempotent retries, activation
   timeouts and interrupted-enrollment recovery. Delivering that transaction
   and its evidence remains host implementation work, and no online
   enrollment RPC is introduced by it. NK bootstrap support alone grants no
   enrollment authority.
3. **Credential lifecycle/privacy.** Rotation (`SNTR-DAUTH-020`/`SNTR-DAUTH-021`),
   compromise recovery (`SNTR-DAUTH-022`), secret hygiene and disposal
   (`SNTR-DAUTH-023`), server-key pin rotation (`SNTR-DAUTH-024`) and the
   revocation-propagation bound (`SNTR-DAUTH-017`–`SNTR-DAUTH-019`) now
   require complete contracts from [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md);
   delivering them, executing their planned `PLAN-DAUTH-*` cases and obtaining
   independent verification remain open. Nonzero AK validation does not
   establish entropy. Handle enumeration/correlation
   controls beyond `SNTR-DAUTH-008` are review items, not blockers.
4. **UDP.** A complete reviewed and accepted binding must cover demux,
   counters/replay window, path validation, anti-amplification, reliability and
   bounded fragmentation. UDP remains deferred, not inferred from stream tests.
5. **Independent verification and conformance.** Independent vectors,
   cross-implementation interoperability and full-composition security review
   remain open. `SNTR-SC1-WSS-V1` and its `CONF-SCW-*` cases are registered, but
   registration is not execution. Scoped implementation evidence does not
   establish conformance, production acceptance, performance superiority or
   post-quantum security.
