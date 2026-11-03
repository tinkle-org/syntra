# Support

## Where to get help

- **Documentation first:** the [protocol reading map](docs/implementer-guide.md),
  [schema tooling guide](docs/schema-tooling.md), and
  [conformance test guide](conformance/README.md).
- **Questions and ideas:** open a GitHub Discussion or Issue in
  `tinkle-org/syntra` with a clear title, what you tried, and a minimal
  neutral reproduction (echo / generic key-value / generic subscription).
- **Bugs in specs, schemas, conformance definitions, or validators:** open a GitHub Issue with the
  requirement ID or field number, expected vs. actual behavior, and
  environment (Buf/protoc version, OS, toolchain).
- **Vulnerabilities or conduct issues:** do **not** use public issues.
  See [`SECURITY.md`](SECURITY.md) and
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for private reporting via
  GitHub's private flows to the maintainer team.

No email, chat, or social handle is listed here to avoid publishing an
unapproved contact. GitHub Issues/Discussions and private GitHub
reporting for this repository are the authoritative channels.

## Report scope

This pre-release repository contains no protocol implementations. It handles
specification, schema, conformance-definition, and validation-tooling reports.
Cite the current owner from the reading map, its requirement ID or schema
field, and the exact repository revision. Protocol changes follow the
[RFC process](rfcs/README.md) and [governance](GOVERNANCE.md).

Implementation-specific reports belong with the affected implementation's
repository. Never include credentials or full hello/provisioning buffers.
Application business logic and private infrastructure are outside this
repository's support scope.

## Response expectations

Maintainers triage on a best-effort basis during pre-release development.
No stable support window is declared. Security and conduct reports are
prioritized per their reporting policies; release stability follows
[GOVERNANCE.md](GOVERNANCE.md) §5.
