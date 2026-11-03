# Pre-release questions and evidence gates

Syntra 1.0 is pre-release. The current protocol reference is
[connection](specifications/connection.md),
[wire format](specifications/wire-format.md), [RPC](specifications/rpc.md),
[security](specifications/security.md),
[transports](specifications/transports.md), and
[recovery](specifications/recovery.md). This page tracks release preparation;
it adds no protocol behavior or approval.

## Current gates

| Gate | Required disposition |
|---|---|
| Normative review | Record acceptance of the actual proposed scope through the RFC process and maintainer rules in [GOVERNANCE.md](GOVERNANCE.md) §3. Existing decisions do not approve subsequent design edits. |
| Specification freeze | Pin the exact reviewed specifications, IDL, requirements, selectors, cases, and fixtures at one reproducible repository revision. |
| Executed evidence | Collect scoped declarations and retained per-case results, independent interoperability, and applicable security, recovery, mobile, and operational evidence as described in the [conformance test guide](conformance/README.md). |
| Release authorization | Apply [GOVERNANCE.md](GOVERNANCE.md) §5 and any applicable bundle-specific gates; obtain explicit public authorization of the exact version, revision, scope, and notes. |
| Release-process proposal | [RFC 0011](rfcs/0011-specification-release-versioning.md) remains in Discussion. Its manual publication procedure is conditional on acceptance; see [RELEASE.md](RELEASE.md). |

## Recording an open question

For an ambiguity or conflict, cite the current owning section and requirement,
describe the interoperability or security impact, and open a public issue or
RFC through [CONTRIBUTING.md](CONTRIBUTING.md). Record its decision and affected
verification before including it in a freeze. Vulnerabilities use the private
channel in [SECURITY.md](SECURITY.md).

This repository contains no protocol implementations. Static validation,
registered cases, and generated-type checks do not establish executed protocol
conformance or satisfy release evidence gates.
