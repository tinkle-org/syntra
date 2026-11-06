# Repository scope and boundary maintenance

Syntra 1.0 is pre-release. This file describes the current repository boundary;
it provides no migration procedure from an unreleased design.

## 10. Repository boundary

This repository maintains:

- The six current protocol reference pages under `specifications/`:
  [connection](specifications/connection.md),
  [wire format](specifications/wire-format.md), [RPC](specifications/rpc.md),
  [security](specifications/security.md),
  [transports](specifications/transports.md), and
  [recovery](specifications/recovery.md)
- Source IDL under `proto/syntra/v1/` and reviewed compatibility baselines
- [Conformance definitions, fixtures, and evidence formats](conformance/README.md)
- [Schema tooling](docs/schema-tooling.md), repository validators, and their tests
- Contribution, security, governance, and release-process documentation

There are no protocol implementations in this repository. Language runtimes,
adapters, native bindings, generated language packages, implementation test
harnesses, and language artifact publication belong to implementation projects.
Generated output is not committed here; local disposable generation follows
the schema tooling guide.

Boundary maintenance does not authorize protocol changes, replacement of
compatibility baselines, conformance claims, or releases. Changes affecting
behavior or compatibility follow [GOVERNANCE.md](GOVERNANCE.md) and the
[RFC process](rfcs/README.md). Record current user-visible changes under
`Unreleased` in [CHANGELOG.md](CHANGELOG.md), and use
[RELEASE.md](RELEASE.md) for publication procedure.

## RFC 0014 canonical adoption

[RFC 0014](rfcs/0014-scoped-terminal-receipt.md), accepted by Decision 0004,
is adopted in the existing connection, RPC, security and transport owners. Its
compatibility disposition is optional additive pre-release behavior: the
host-local terminal-result operation is disabled by default and ordinary
withdrawal remains the contract without explicit compatible support and method
policy. There is no new peer exchange, capability, field, carrier, schema pin or
generated artifact. Existing peers continue ordinary result validation and may
observe success or an unknown outcome.

Canonical requirements and positive/negative cases are registered; they supply
no SDK execution, application durability, formal conformance or publication
claim. SDK adoption and real application integration require separate evidence
against the adopted requirements. No release or dependency repinning follows
from this documentation change.
