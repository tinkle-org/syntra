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
- Experimental Go SC1 draft-1 contract and implementation evidence, recorded
  in the [implementation ledger](docs/sc1-implementation.md#implementation-status).
  Best-effort development support does not establish accepted production
  policy, a stable support window or independent security assurance.

## SC1 implementation and design discussion

The selected transport-independent secure-channel proposal is
[Draft RFC 0007](rfcs/0007-secure-channel-device-authorization.md), not an
Accepted RFC. Bounded experimental TCP/WS/WSS bootstrap and returning channels,
high-level connection helpers, channel-aware host policy, deny-by-default method
authorization and owned asynchronous output/shutdown are delivered. For design
questions, cite the proposed [secure channel](specifications/security/secure-channel.md),
[device authorization](specifications/security/device-authorization.md), or
[TCP/UDP/WS bindings](specifications/transports/noise-bindings.md), and
identify whether the report concerns draft-1 behavior, a proposal decision or
a baseline profile. UDP remains deferred; HTTP/HTTPS request-response is
excluded from this implementation. WSS retains verified outer TLS ≥1.3 and
does not automatically downgrade.
The TLS baseline and existing executable conformance profiles remain current.

Host policy must independently verify root identity, current enrollment and
admission before ready, enforcing the intended returning-mode same-principal
binding; the library does not compare principals automatically. Enrollment, per-device AK
storage, authorization and revocation remain host-owned. There is no enrollment
RPC or complete issuance/storage/rotation workflow. Independent review,
vectors/interoperability and native ABI completion-time/credential-release
gaps remain [open](docs/sc1-implementation.md#remaining-work).

For implementation reports include mode/carrier, toolchain, pure-Go or native
core, reproduction, configured limits and whether the failure occurred before
ready, during RPCs or during close. High-level connection helpers have local
unit coverage; the six-group Docker suite exercises adapters with core sessions.
Same-implementation tests are not independent wire interoperability or formal
`CONF-*` verdicts. Cite [verification evidence](docs/sc1-implementation.md#verification-evidence)
and [performance evidence](docs/perf-tradeoffs.md) with their conditions, rather
than treating the [acceptance plan](conformance/plans/secure-channel.md) as a pass.
Never include credentials or full hello/provisioning buffers. Continue to
report vulnerabilities privately through `SECURITY.md`.

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
