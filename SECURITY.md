# Security Policy

> Do not open public issues for vulnerabilities. Use the private
> reporting channel described below.

## Supported versions

Syntra v1 is in development. Core, transport, and security specifications
are drafts pending the RFC process; package prereleases do not establish
protocol stability. SC1 in Draft RFC 0007 is selected design work, not a
supported cryptographic implementation or an Accepted RFC.

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

## Selected SC1 proposal: security boundary

[Draft RFC 0007](rfcs/0007-secure-channel-device-authorization.md) proposes
transport-independent Syntra Secure Channel v1 (SC1). It is not Accepted
and does not replace the TLS baseline above or alter existing executable
conformance profiles. The proposed [secure-channel state machine](specifications/security/secure-channel.md)
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

The proposed TCP/UDP/WS bindings are described in
[noise-bindings.md](specifications/transports/noise-bindings.md). Existing
HTTPS/WSS TLS compatibility remains, including outer TLS for browser
`wss://`; Noise-in-WS has a distinct wire binding from current WS profiles.
The [SC1 verification plan](conformance/plans/secure-channel.md) is planned
coverage, not evidence of implementation or security testing.

## Scope

In scope: wire schemas, framing, handshake, RPC, errors, streams,
transport profiles, conformance suite, and the Rust reference
implementation (when present).

Out of scope: application payload semantics, credential formats, host
authorization policy, and third-party deployments — though Syntra
maintainers will advise on safe integration patterns using neutral
examples.
