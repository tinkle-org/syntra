# Session Open Questions (release blockers)

Status: Draft 2026-10-19. Produced because unresolved release-blocking questions remain for authentication, session lifecycle, and resumption. None of these is resolved by implementation choice. Normative clarifications landed in `specifications/core/handshake.md` (§1A–§1B/§2A), `authentication.md` (§1A–§1D), `sessions.md` (§1A–§1G), and `conformance/auth-session/`; the items below still need RFC decisions before stable v1.

## SC1 draft-1 implementation and pending acceptance (2026-10-28)

[RFC 0007](rfcs/0007-secure-channel-device-authorization.md) is
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

Delivered experimental Go SC1 draft-1 supports bounded TCP/WS/WSS in both
modes, ready-to-call connection helpers, server admission, channel-aware host
policy and owned asynchronous output/shutdown. Its self-contained
[implementation record](docs/sc1-implementation.md#implementation-status)
supplies concrete bytes and numerical defaults; those choices do not settle
normative blockers. UDP is deferred and HTTP/HTTPS request-response is excluded
from this implementation. WSS retains verified outer TLS ≥1.3 with no automatic
downgrade. Proposed ADR-011 has not replaced production TLS policy.

Proposal review still needs to accept the complete bounds, failure and
verification details in the [secure-channel draft](specifications/security/secure-channel.md),
[device-authorization draft](specifications/security/device-authorization.md),
and [TCP/UDP/WS binding draft](specifications/transports/noise-bindings.md),
with the [conformance plan](conformance/plans/secure-channel.md). In
particular, the host first verifies an authenticated client transport
record before protected actions, and Syntra hello/ready remains required.
Enrollment/storage/authorization/revocation are host-owned without
mandatory human accounts. Confirmed-peer lifecycle checks run on a 1s ticker
with 1s lookup contexts, not a guarantee of exact 1s revocation propagation.
Before ready, host policy must independently verify root identity, current
enrollment and admission and enforce the intended returning-mode same-principal
binding; the library does not compare principals automatically. Nil method
authorization denies effects. See [authentication boundary](docs/sc1-implementation.md#authentication-boundary).

The [verification record](docs/sc1-implementation.md#verification-evidence)
includes final Go 1.26.10 root/native-core checks, Go 1.23.12 compatibility,
zero reachable root/integration scan findings and a 30.681s Docker pass across
all six carrier/mode groups with none skipped. High-level orchestration is
covered locally, not in containers. Same-implementation passes are not
independent SC1 wire interoperability or formal `CONF-*` evidence. In-memory
[benchmark evidence](docs/perf-tradeoffs.md) is report-only and full RPCs are
not zero-allocation.

Remaining SC1 work includes accepted wire/context identifiers and policy,
independent review/vectors/interoperability, complete provisioning and rotation
workflow, secure storage and deployment revocation/rate-limit policy. There is
no enrollment RPC. Native ABI v1 still lacks completion timestamps and explicit
post-hello credential release; cleanup does not guarantee erasure of every
secret copy. The core 1s callback grace, writer 1s join after transport close
and connection-server default/max 5s shutdown budget are distinct and cannot
forcibly terminate uncooperative operations. See
[operational limits](docs/sc1-implementation.md#operational-limits) and
[remaining work](docs/sc1-implementation.md#remaining-work).

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
