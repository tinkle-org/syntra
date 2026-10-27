# Session Open Questions (release blockers)

Status: Draft 2026-10-19. Produced because unresolved release-blocking questions remain for authentication, session lifecycle, and resumption. None of these is resolved by implementation choice. Normative clarifications landed in `specifications/core/handshake.md` (§1A–§1B/§2A), `authentication.md` (§1A–§1D), `sessions.md` (§1A–§1G), and `conformance/auth-session/`; the items below still need RFC decisions before stable v1.

## Selected SC1 direction (2026-10-27; proposal only)

New [RFC 0007](rfcs/0007-secure-channel-device-authorization.md) is
**Draft, not Accepted**. The selected target is transport-independent SC1:
initial `Noise_NK_25519_ChaChaPoly_SHA256` enrollment, then returning
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` channels using a unique random shared
32-byte AK and opaque 8-byte `auth_id` per device. The AK is not sent on
reconnect and is not a signing keypair or `connection_id`. Every channel
has fresh ephemeral material and directional traffic keys; M1/M2 payloads
are empty, with no 0-RTT application data or credentials.

This selects a mechanism; it does not resolve the baseline blockers below
by RFC acceptance. Baseline TLS requirements and all existing executable
conformance profiles remain unchanged. Returning-device authentication is
not session resumption, restored subscriptions, or automatic RPC retry.

Proposal review still needs to establish the complete bounds, failure and
verification details in the [secure-channel draft](specifications/security/secure-channel.md),
[device-authorization draft](specifications/security/device-authorization.md),
and [TCP/UDP/WS binding draft](specifications/transports/noise-bindings.md),
with the [conformance plan](conformance/plans/secure-channel.md). In
particular, the host first verifies an authenticated client transport
record before protected actions, and Syntra hello/ready remains required.
Enrollment/storage/authorization/revocation are host-owned without
mandatory human accounts; revocation enforcement still needs an explicit
deployment policy. Browser `wss://` retains outer TLS, and Noise-in-WS is
distinct from existing WS/WSS wire profiles. These are design constraints,
not new implementation, transport-support, or passing-test claims.

## Blockers

1. **Mechanism negotiation.** No identifier/advertisement/selection/challenge fields exist. If stable claims anything beyond opaque credential presentation with application-side agility, a capability RFC is required (see `rfcs/0002-auth-session-lifecycle.md` §10.7 and core `open-questions.md` blocker 4).
2. **Resumption standard.** No token format, lifetime, rotation, replay window, restored-state list, or revocation transport exists. Default v1 has no resumption; any resumption claim needs the full RFC (see `sessions.md` §1C, security open-questions item 5, `rfcs/0002` §10.8).
3. **Typed pre-`ACTIVE` error carrier (B1).** Which `Frame`, if any, carries handshake errors; zero-`request_id` `result` stays forbidden.
4. **Pre-`ACTIVE` notification conflict (B2).** Ignore-with-diagnostic vs fail/close.
5. **Stale `request_id` reuse (B3).** Core re-use permission vs replay rejection.
6. **Capability/session-extension binding and bounds (B7).** Identifiers, parameters, confirmation, limit overrides, token lifetimes/windows.
7. **Payload vs envelope size (B8).** 1 MiB payload fixtures cannot fit the 1 MiB serialized envelope.
8. **Cancel/deadline/`UNAVAILABLE` races (B10).** Precedence and safe-retry reporting.
9. **Cross-transport binding.** Required only if cross-transport resumption is claimed (`sessions.md` §1D).
10. **HTTP profile bindings.** Transport RFCs must embody `sessions.md` §1E principles.
11. **Revocation-propagation bound, channel-binding construction, proxy propagation format.** Per `specifications/security/open-questions.md` items 1–4; unchanged by this task.

## Non-blockers for this task

- TLA+/ProVerif supplements, padding guidance, post-quantum policy, rate-limit baselines — valuable future work, not required to land the clarifications above.
- `session.proto`/`capabilities.proto` remain documentation-only by design; no schema change proposed (`buf lint`/`build`/breaking unaffected).
