# Security Policy

> Do not open public issues for vulnerabilities. Use the private
> reporting channel described below.

## Supported versions

Syntra v1 is in development. Core, transport, and security specifications
are drafts pending the RFC process; package prereleases do not establish
protocol stability. A bounded experimental Go SC1 draft-1 implementation is
delivered over TCP/WS/WSS. RFC 0007 remains Draft and ADR-011 Proposed;
delivery and local verification do not establish an independently audited
construction, accepted production default or stable security-support window.

| Version | Status | Security support |
|---------|--------|------------------|
| v1 (main branch) | In development | Best-effort review of reports; fixes land on `main` via RFC/PR |
| Prior / tagged pre-releases (when published) | As noted in `CHANGELOG.md` | Only as stated in the corresponding release notes |

Once stable releases are tagged (see `GOVERNANCE.md` Sec. 5), this table
will list which release lines receive security fixes and for how long.

## How to report a vulnerability (private)

Use **GitHub's private vulnerability reporting** for the
`tinklehq/syntra` repository (the "Security" tab → "Report a
vulnerability"). That flow notifies maintainers privately without
creating a public issue.

Include where possible:

- Affected component (spec section + requirement ID, schema file +
  field, or implementation file + version/commit)
- Threat, impact, and who is affected (initiator, host, transport)
- Steps to reproduce (minimal config, neutral echo/key-value fixture —
  never include real credentials or private data)
- Suggested severity and any mitigations
- Whether the issue is already publicly known

Do not include credentials, private backend diagnostics, customer data,
or domain-specific private details. Do not probe public deployments
without authorization.

No email address is listed here. The GitHub private reporting flow is
the authoritative channel so reports stay private and triageable without
publishing an unapproved contact.

## What happens next

1. Maintainers acknowledge receipt privately and triage impact and
   scope.
2. Fixes are developed privately if exploitation is plausible, then
   disclosed via a GitHub Security Advisory and a `CHANGELOG.md` entry.
3. Normative security changes go through the RFC process
   (`rfcs/README.md`) and maintainer approval (`GOVERNANCE.md` Sec. 3)
   where wire or behavioral impact exists; purely editorial clarifications
   may land as direct PRs.
4. Reporters are credited only with consent.

## Current baseline threat assumptions (summary)

Syntra assumes a hostile network: observation, delay, reorder, replay,
truncation, and injection on insecure transports. See
`specifications/architecture.md` Sec. 7 and ADR-008:

- Public production MUST use TLS 1.3 over TCP, HTTPS (HTTP/1.1 or
  HTTP/2), or Secure WebSocket over HTTP/1.1 with established TLS
  implementations. Plain TCP / HTTP/1.1 / WebSocket are for restricted
  development only.
- `ClientHello.credential` is opaque and sensitive; the core MUST NOT
  log, persist, or interpret it.
- Hosts MUST NOT authorize protected operations before authentication.
  Error messages MUST NOT leak credentials or private diagnostics.
- Bounded buffers, explicit limits, deterministic timeout/cancellation;
  no panics on untrusted input; no unbounded allocation.
- Transport receipt proves nothing about application processing.

The baseline [transport-security specification](specifications/security/transport-security.md)
owns these requirements. This file states process, not protocol behavior.

## Experimental SC1 draft-1: security boundary

[Draft RFC 0007](rfcs/0007-secure-channel-device-authorization.md) proposes
transport-independent Syntra Secure Channel v1 (SC1). It is not Accepted
and does not replace the TLS baseline above or alter existing executable
conformance profiles. The delivered draft-1 [implementation contract](docs/sc1-implementation.md#implementation-status)
follows the selected [secure-channel construction](specifications/security/secure-channel.md), which
uses `Noise_NK_25519_ChaChaPoly_SHA256` for initial enrollment and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices.

The selected [device authorization model](specifications/security/device-authorization.md)
uses a unique, random shared 32-byte AK per device and an opaque 8-byte
`auth_id` lookup handle. Hosts own enrollment permission, protected AK
storage, authorization, and revocation; no human account model is required.
The shared AK is not a signing keypair, is not transmitted on reconnect,
and is never a `connection_id`. A supplied `auth_id` alone grants nothing.

M1/M2 payloads are empty: no credentials or application data in 0-RTT.
Fresh ephemeral material and directional traffic keys are derived for each
channel. The host verifies the first authenticated client transport record
before protected actions; successful Noise exchange alone does not grant
enrollment or method authority. Syntra hello/ready remains a separate gate.
Fresh channels do not imply session resumption or safe automatic RPC retry.

Delivered carriers are TCP/WS/WSS in both modes. UDP is deferred and HTTP/HTTPS
request-response is excluded from this implementation. Draft-1's exact context
domain/WS subprotocol is `syntra.sc1.draft1`, distinct from existing profile
identifiers and baseline WS bytes. WSS retains verified outer TLS ≥1.3 and an
independent Noise pin; no automatic downgrade is implemented. Standard
inspectable HTTP transports enforce certificate verification, while custom
RoundTrippers own their TLS policy. Accept uses `r.TLS`, not forwarded headers,
to bind the carrier. The application owns server TLS, origin and HTTP limits.

### Host policy and enrollment obligations

The delivered `ChannelPolicy` receives confirmed channel evidence and explicit
hello credentials. Host policy must independently verify root identity, current
enrollment and admission before ready, then enforce the intended returning-mode
same-principal binding itself. **The library does not compare principals
automatically** or implicitly authorize an empty credential. Nil method authorization selects deny;
every method still needs explicit authorization. See
[authentication boundary](docs/sc1-implementation.md#authentication-boundary).

Enrollment lookup is read-only, scoped to server-key ID/carrier/exact scope/
handle/epoch, and requires a nonzero AK, nonempty principal, future expiry and
no revocation. Key/principal bindings must be immutable under that tuple:
`Check` rechecks validity/principal, not original-key equality. Confirmed-peer
checks run after confirmation and on a 1s ticker with 1s lookup contexts;
scheduling and store latency prevent an exact 1s propagation promise. These
checks do not replace synchronous admission policy. Hosts can also disconnect
current connections by principal and must deny subsequent admissions.

Only authenticated out-of-band provisioning is supported. Independent random
handles need scoped collision checks. There is no enrollment RPC or complete
transactional issuance/delivery/ack recovery, protected client storage or
rotation workflow. Rate limits, cross-server budgets and lookup timing/privacy
remain host responsibilities.

### Resource and shutdown boundaries

Ciphertext is at most 65,535 bytes; serialized frames at most 1 MiB. Adapter
handshake/write/record/frame budgets default/max at 5s, lifetime at 24h including
establishment, and record count at 2^32 per direction. Pending operations default
to 32/direction, maximum 1,024. High-level establishment has a 10s total budget;
server admission defaults to 128 connections/16 handshakes, maxima 4,096/256,
with handshake admission held through ready write.

One post-ready asynchronous writer owns FIFO snapshots and caps queued plus
active output at 256 frames/8 MiB, including terminal results. Writes default
to 5s; saturation or write failure terminates the session. The pure-Go core's
separate notification admission cap is not a delivery acknowledgement. Method
authorization returning `UNAUTHENTICATED` cancels callbacks and attempts an
actual-send denial drain for up to 200ms, which may fail. Enrollment-watchdog
failure and explicit principal disconnect close directly. Sessions own terminal
transport close. Distinguish core callback grace
(1s), writer join (1s **after transport Close returns**) and high-level connection
server shutdown (default/max 5s). Uncooperative callbacks cannot be killed;
`Lookup`, I/O and `Close` must honor cancellation. Low-level close can otherwise
block. See [operational limits](docs/sc1-implementation.md#operational-limits).

### Assurance and verification limits

The final 2026-10-28 [verification record](docs/sc1-implementation.md#verification-evidence)
uses Go 1.26.10: root pure-Go CGO-disabled/race/staticcheck, native-core
race/staticcheck and Go 1.23.12 compatibility passed. Compatibility does not
recommend an old toolchain for production. Root and integration scans found
zero reachable vulnerabilities; that is not a dependency-wide advisory-free
claim or coverage of every build variant or the fault proxy's own module graph.
Production builds require a security-patched toolchain.

Actual Docker integration passed in 30.681s across six carrier/mode groups,
none skipped. It exercises adapters/core sessions, not high-level connection
helpers, whose coverage is local unit tests. Same-implementation Docker,
same-library Noise and native-core linkage are not independent SC1 wire
interoperability, a cryptographic audit or formal `CONF-*` conformance. The
[SC1 acceptance plan](conformance/plans/secure-channel.md) retains those distinctions.
In-memory benchmark passes likewise establish no performance superiority;
see [measurement conditions](docs/perf-tradeoffs.md).

Independent review, vectors/interoperability and complete credential lifecycle
work remain open. Native ABI v1 has no handler-completion timestamp input or
explicit post-hello credential-release operation; pure-Go timing fixes do not
establish native parity. Clearing accessible scratch and dropping references
does not guarantee erasure of every Go, native, Noise or compiler-created secret
copy. Key diagnostic formatting is redacted, but generated hello/debug output
and arbitrary application logs are not automatically safe. See
[remaining work](docs/sc1-implementation.md#remaining-work).

## Scope

In scope: wire schemas, framing, handshake, RPC, errors, streams,
transport profiles, the conformance suite and the implementation evidence
recorded here. Publication remains specifications/schema provenance rather
than language artifacts; experimental implementation results do not amend
normative security requirements.

Out of scope: application payload semantics, credential formats, host
authorization policy, and third-party deployments — though Syntra
maintainers will advise on safe integration patterns using neutral
examples.
