# Security Policy

> Do not open public issues for vulnerabilities. Use the private
> reporting channel described below.

## Supported versions

Syntra 1.0 is pre-release. This repository contains protocol specifications,
schemas, conformance definitions, and validation tooling. It contains no
protocol implementations and declares no stable security-support window.
Maintainers review reports against the current repository revision on a
best-effort basis. Release stability is governed by
[GOVERNANCE.md](GOVERNANCE.md) §5.

## How to report a vulnerability (private)

Use **GitHub's private vulnerability reporting** for the
`tinkle-org/syntra` repository (the "Security" tab → "Report a
vulnerability"). That flow notifies maintainers privately without
creating a public issue.

Include where possible:

- The affected specification section and requirement ID, schema file and
  field, conformance case, or validation-tooling file, with the exact commit
- Threat, impact, and affected roles or carriers
- A minimal neutral reproduction using throwaway data
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

## Scope

Reports about protocol design, schema representation, conformance definitions,
and repository validators belong here. Implementation-specific vulnerabilities
belong with the affected implementation's private reporting channel.
Application payload semantics, host authorization policy, credential storage,
and deployment configuration are application responsibilities within the
boundaries defined by the protocol.

The [security specification](specifications/security.md),
[connection specification](specifications/connection.md), and
[transport specification](specifications/transports.md) own security behavior.
The [conformance test guide](conformance/README.md) describes supporting
evidence. This policy defines reporting and triage; it grants no security
approval or conformance verdict.
