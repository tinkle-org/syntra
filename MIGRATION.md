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
