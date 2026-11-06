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
| Release-process activation | [RFC 0011](rfcs/0011-specification-release-versioning.md) is accepted as design only; activation is deferred. Release Please remains active, and the prepared manual publisher remains disabled for publication; see [RELEASE.md](RELEASE.md). |

[Decision 0004](docs/decisions/0004-rfc-0011-0014-acceptance.md) records the
[public acceptance](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482)
of RFCs 0011–0014 at `cfab7655c348f1d04f4e1d57e28cc1a634478854`.
The human protocol/security self-review and self-approval by `oscarlaw` are disclosed;
they do not satisfy independent human release security review. RFC 0012 ratifies
the already-landed reference. RFCs 0013/0014 are accepted optional additive
pre-release designs with adoption still pending, not executed conformance or
release authorization. RFC 0013's context values 4/5 remain isolated and
unclaimable until canonical owners, registry, and fixtures are synchronized.

## Recording an open question

For an ambiguity or conflict, cite the current owning section and requirement,
describe the interoperability or security impact, and open a public issue or
RFC through [CONTRIBUTING.md](CONTRIBUTING.md). Record its decision and affected
verification before including it in a freeze. Vulnerabilities use the private
channel in [SECURITY.md](SECURITY.md).

This repository contains no protocol implementations. Static validation,
registered cases, and generated-type checks do not establish executed protocol
conformance or satisfy release evidence gates.
