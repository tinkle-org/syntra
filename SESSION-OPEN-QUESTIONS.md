# Session Open Questions (release blockers)

Status: Updated 2026-10-30. RFC 0007 and RFC 0009 are accepted (2026-10-29);
the 2026-10-30 acceptance wave recorded in
[Decision 0002](docs/decisions/0002-sdd-acceptance-wave.md) accepted RFCs
0001, 0002, 0003, 0004, 0005, 0006, 0008 and 0010. The owning core/security
documents are accepted contracts; the historical inventory below is retained
as background and updated by the blocker map here. None of the remaining open
items is resolvable by implementation choice.

## Selected mobile release scope and decision package

The selected target requires SC1 and standardized update recovery. Their wire
optionality remains distinct from inclusion in this release bundle; a Core-only
pass does not satisfy it (RFC 0006 §11.1). See [delivery sequence](docs/mobile-v1-delivery.md),
[current readiness](audits/v1-release-readiness.md), and
[mobile acceptance plan](conformance/plans/mobile-v1.md). Acceptance of the
RFCs is recorded; executed conformance evidence, independent review, freeze
and release authorization remain outstanding.

| Workstream | Selected proposal | Remaining gate |
|---|---|---|
| Handshake failures | RFC 0003 (accepted): local typed cause/native generic peer signal, fail-close pre-ACTIVE notifications, timer phase binding | Execution of the owning cases |
| Correlation/races/HTTP | RFC 0004 (accepted): increasing emitted request IDs, ordered high-water admission, connection-fatal reuse, one terminal gate, profile credentials | Execution and runtime race evidence |
| Bounds/negotiation/imports | RFC 0005 (accepted, D1–D4): profile-specific recovery negotiation, concrete limits, current matching IDs; D5 Go path deferred | Execution; tracked FILE/source follow-up for D5 |
| Recovery | RFC 0006 (accepted) §11: fresh-round handles, local overflow isolation, scoped continuity, crash-safe persistence/confirmation and snapshot install; owner/IDL-comment map applied, recovery manifest normalized | Recovery-plan execution and independent crash evidence |
| SC1 | RFC 0007 (accepted) + RFC 0010 (accepted): canonical `syntra.sc1.v1` context/prologue/subprotocol and host lifecycle `SNTR-DAUTH-011`–`024` with planned `CONF-SCW-025`–`042` rows (registered, not executed) | Rust/Go alignment to the canonical contract, independent Noise vectors and both socket roles |
| Mobile/parser/resources | RFC 0008 (accepted): raw body classification, suspend-aware deadlines, half-open/replacement/reconnect rules, bounded executions/drain | iOS/Android and operational evidence |

The historical local-1/draft-1 byte differences are superseded alignment
targets: the canonical contract is activated in the owning specs. Public
context fixtures have a separate lint test; they contain no Noise ciphertext
and establish no peer acceptance or interoperability verdict.

Logical-session resumption, reliable-session RPC reconciliation, UDP/QUIC and
automatic mutation replay remain deferred. Reusing an enrollment or restoring
durable update progress does not resume a connection or replay its RPCs.

## SC1 acceptance and lifecycle status (2026-10-28 section, updated 2026-10-30)

[RFC 0007](rfcs/0007-secure-channel-device-authorization.md) is **Accepted**
(2026-10-29), together with accepted
[ADR-011](specifications/decisions/ADR-011-noise-device-authorization.md).
The accepted target is transport-independent SC1: initial
`Noise_NK_25519_ChaChaPoly_SHA256` enrollment, then returning
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` channels using a unique random shared
32-byte AK and opaque 8-byte `auth_id` per device. The AK is not sent on
reconnect and is not a signing keypair or `connection_id`. Every channel
has fresh ephemeral material and directional traffic keys; M1/M2 payloads
are empty, with no 0-RTT application data or credentials.

Acceptance activates this mechanism; the release blockers below are gated by
executed evidence, not by another decision. Baseline TLS requirements and all
existing executable conformance profiles remain unchanged. Returning-device
authentication is not session resumption, restored subscriptions, or
automatic RPC retry. ADR-011 is accepted and governs the SC1 device-authorization
policy; production TLS policy remains owned by the transport-security specs.

Delivered experimental Go SC1 draft-1 supports bounded TCP/WS/WSS in both
modes, ready-to-call connection helpers, server admission, channel-aware host
policy and owned asynchronous output/shutdown (historical record; the canonical
contract is the accepted one). Its self-contained
[implementation record](docs/sc1-implementation.md#implementation-status)
supplies concrete bytes and numerical defaults. UDP is deferred and
HTTP/HTTPS request-response is excluded from this implementation. WSS retains
verified outer TLS ≥1.3 with no automatic downgrade.

The accepted bounds, failure and verification details live in the accepted
[secure-channel](specifications/security/secure-channel.md),
[device-authorization](specifications/security/device-authorization.md)
(the RFC 0010 lifecycle contract is its accepted §5,
`SNTR-DAUTH-011`–`024`) and
[TCP/UDP/WS binding](specifications/transports/noise-bindings.md)
documents, with the [conformance plan](conformance/plans/secure-channel.md).
The host first verifies an authenticated client transport
record before protected actions, and Syntra hello/ready remains required.
Enrollment/storage/authorization/revocation are host-owned without
mandatory human accounts; RFC 0010 fixes the revocation-propagation policy
(immediate on new connections; 300 s hard maximum, 60 s operational target
on established channels; fail closed without current validity), superseding
the historical 1s-ticker wording. Before ready, host policy must
independently verify root identity, current
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

Remaining SC1 work includes independent review/vectors/interoperability,
executed lifecycle cases for the accepted provisioning/rotation workflow
(`CONF-SCW-025`–`042`, registered and not executed), secure storage and
deployment revocation/rate-limit policy. There is
no enrollment RPC. Native ABI v1 still lacks completion timestamps and explicit
post-hello credential release; cleanup does not guarantee erasure of every
secret copy. The core 1s callback grace, writer 1s join after transport close
and connection-server default/max 5s shutdown budget are distinct and cannot
forcibly terminate uncooperative operations. See
[operational limits](docs/sc1-implementation.md#operational-limits) and
[remaining work](docs/sc1-implementation.md#remaining-work).

## Blockers

Resolved blockage (recorded, 2026-10-29/2026-10-30; only executed evidence
remains as a release gate):

- **B1 typed pre-`ACTIVE` error carrier / B2 pre-`ACTIVE` notification conflict** → accepted RFC 0003 (Decision 0002).
- **B3 stale `request_id` reuse / B10 cancel/deadline/`UNAVAILABLE` races** → accepted RFC 0004 (ordered non-reuse IDs, terminal gate, race precedence).
- **B7 capability/session-extension binding, bounds, mechanism negotiation** → accepted RFC 0005 D1/D2 (mechanism negotiation is per-profile contracts post-ACTIVE; concrete limits accepted).
- **B8 payload vs envelope size** → accepted RFC 0005 D3 with the fixture correction applied.
- **Revocation-propagation bound** → accepted RFC 0010 (immediate on new connections; 300 s hard maximum and 60 s operational target on established channels; fail closed without current validity).

Remaining open:

1. **Reliable-session/reliable-delivery shipping authority** (item 12 of
   [RFC 0002](rfcs/0002-auth-session-lifecycle.md) §10): the reliable-session
   contracts remain proposals without an accepted authorizing RFC; case
   reservations `CONF-RS-*` stay non-executable.
2. **Logical resumption standard (conditional).** Default v1 has no
   logical-session resumption; a future resumption claim needs
   token/lifetime/rotation/replay/state/revocation rules (see `sessions.md`
   §1C, security open-questions item 5, `rfcs/0002` §10.8). Required update
   recovery is covered by accepted RFC 0006, not by resumption.
3. **Cross-transport binding (conditional).** Required only if
   cross-transport resumption is claimed (`sessions.md` §1D).
4. **Channel-binding construction.** Per
   `specifications/security/open-questions.md` item 1 and
   `SNTR-ASEC-002`: unchanged by the wave; if stable v1 claims channel
   binding, a dedicated RFC owns the exporter construction.
5. **Proxy propagation format.** Per security open-questions item 4;
   deployment-owned propagation mechanism still standardizes nothing.
6. **HTTP profile-binding principles.** Future transport RFCs must embody
   `sessions.md` §1E principles as constraints.

## Non-blockers for this task

- TLA+/ProVerif supplements, padding guidance, post-quantum policy, rate-limit baselines — valuable future work, not required to land the clarifications above.
- `session.proto`/`capabilities.proto` remain documentation-only by design; no schema change proposed (`buf lint`/`build`/breaking unaffected).
