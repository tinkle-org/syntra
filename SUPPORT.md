# Support

## Where to get help

- **Documentation first:** [`README.md`](README.md) →
  [`specifications/architecture.md`](specifications/architecture.md) →
  [`specifications/decisions/README.md`](specifications/decisions/README.md).
- **Questions and ideas:** open a GitHub Discussion or Issue in
  `tinklehq/syntra` with a clear title, what you tried, and a minimal
  neutral reproduction (echo / generic key-value / generic subscription).
- **Bugs in specs, schemas, or code:** open a GitHub Issue with the
  requirement ID or field number, expected vs. actual behavior, and
  environment (Buf/protoc version, OS, toolchain).
- **Vulnerabilities or conduct issues:** do **not** use public issues.
  See [`SECURITY.md`](SECURITY.md) and
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for private reporting via
  GitHub's private flows to the maintainer team.

No email, chat, or social handle is listed here to avoid publishing an
unapproved contact. GitHub Issues/Discussions and private GitHub
reporting for this repository are the authoritative channels.

## What is supported

- The charter, ADRs, RFC process, and governance documents on the
  `main` branch.
- `proto/syntra/v1/*.proto` as the sole Protobuf source of truth (field
  numbers, reserved values, comments). The removed schema tree is retained
  only as historical provenance and an archived descriptor in
  [`compatibility/v1-initial`](compatibility/v1-initial/README.md); the
  FILE/source migration is a known breaking difference.
- Draft specifications, transport profiles, and the conformance suite —
  support scope for each is stated in its README and `CHANGELOG.md`.
  Language implementations are separate projects with their own support
  channels.

## SC1 design discussion

The selected transport-independent secure-channel proposal is
[Draft RFC 0007](rfcs/0007-secure-channel-device-authorization.md), not an
Accepted RFC or supported runtime feature. For design questions, cite the
proposed [secure channel](specifications/security/secure-channel.md),
[device authorization](specifications/security/device-authorization.md), or
[TCP/UDP/WS bindings](specifications/transports/noise-bindings.md), and
identify whether the report concerns that proposal or the current profile.
The TLS baseline and existing executable conformance profiles remain current.

Enrollment, per-device AK storage, authorization, and revocation are
host-owned integration policy; no mandatory human account system is
provided. The [SC1 conformance plan](conformance/plans/secure-channel.md)
does not establish implementation support, test results, or benchmarks.
Continue to report vulnerabilities privately through `SECURITY.md`.

## What is not supported

- Private products, proprietary servers, databases, cloud deployments,
  or unpublished architectures.
- Application business logic, data models, or credential formats built
  above Syntra.
- Deferred transports (Raw UDP, DTLS, QUIC, HTTP/3, QUIC DATAGRAM,
  WebSocket over HTTP/2 Extended CONNECT) — tracked as future extensions
  only.
- Third-party forks or unpublished copies: file issues against the
  upstream repository with a reproduction on `main`.

## Response expectations

Maintainers triage on a best-effort basis during development. Stable
releases (per `GOVERNANCE.md` Sec. 5) will document support windows in
`CHANGELOG.md` and `SECURITY.md`. Security and conduct reports are
prioritized per those documents.
