# Security Policy

> Do not open public issues for vulnerabilities. Use the private
> reporting channel described below.

## Supported versions

Syntra v1 is in development (charter + ADRs accepted; normative core,
transport, and security specifications forthcoming).

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

## Threat assumptions (summary)

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

The forthcoming `specifications/security/*.md` owns normative security
requirements. This file states process, not protocol behavior.

## Scope

In scope: wire schemas, framing, handshake, RPC, errors, streams,
transport profiles, conformance suite, and the Rust reference
implementation (when present).

Out of scope: application payload semantics, credential formats, host
authorization policy, and third-party deployments — though Syntra
maintainers will advise on safe integration patterns using neutral
examples.
