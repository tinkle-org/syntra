# Contributing to Syntra

Syntra is a pre-release protocol specification project. This repository owns
the protocol reference, source IDL, conformance definitions, and validation
tooling. It contains no protocol implementations.

Related: [governance](GOVERNANCE.md), [RFC process](rfcs/README.md),
[Code of Conduct](CODE_OF_CONDUCT.md), and [security reporting](SECURITY.md).

## 1. Ground rules

1. **Specifications first.** The current protocol reference is
   [connection](specifications/connection.md),
   [wire format](specifications/wire-format.md), [RPC](specifications/rpc.md),
   [security](specifications/security.md),
   [transports](specifications/transports.md), and
   [recovery](specifications/recovery.md). Source IDL defines representation;
   implementation behavior does not define the protocol.
2. **Independent and generic.** Keep private products, infrastructure,
   deployment details, and application-domain types out of protocol contracts.
   Use neutral echo, key/value, and subscription examples.
3. **Respect security boundaries.** Protocol channel security belongs to the
   security specification. Application encryption formats, payload meaning,
   and business policy belong to applications; do not introduce custom ciphers
   or application ratchets into the protocol.
4. **Small, auditable changes.** Prefer narrow PRs and one RFC per change.
   The Code of Conduct applies in all project spaces.

## 2. Ways to contribute

- Editorial corrections with no behavioral change may use a direct PR.
- Normative changes require an RFC, including wire fields, state machines,
  error semantics, carrier mappings, security requirements, and conformance
  assertions. Schema changes follow the same review bar and compatibility checks.
- Conformance definitions and fixtures should accompany changes to their
  owning requirements. Follow the [conformance test guide](conformance/README.md).
- Tooling and documentation improvements should respect the
  [repository boundary](MIGRATION.md#10-repository-boundary).
  Generated language output and protocol implementations are not committed here.

## 3. Proposing a change

1. Search existing [issues](https://github.com/tinkle-org/syntra/issues) and
   [RFC PRs](https://github.com/tinkle-org/syntra/pulls) to avoid duplicates.
2. For normative work, use [rfcs/template.md](rfcs/template.md) and the
   [RFC lifecycle](rfcs/README.md). Explain motivation, proposed owner changes,
   compatibility, security, and the verification plan.
3. Link the RFC and proposed specification/schema/conformance changes.
   Only an Accepted RFC may modify normative behavior; proposal text or CI
   success does not grant acceptance.
4. For each new normative requirement, provide a unique requirement ID,
   applicable role obligations, success/failure behavior, security and
   compatibility analysis, and testable acceptance criteria. Link conformance
   coverage or an explicitly tracked gap.
5. Update [CHANGELOG.md](CHANGELOG.md) under `Unreleased` for user-visible
   changes and supply compatibility notes where required by governance.

## 4. RFC review and acceptance

Discussion and approvals take place publicly on the RFC or PR under
[GOVERNANCE.md](GOVERNANCE.md) §3 and the published
[maintainer roster](MAINTAINERS.md):

- Non-normative changes may merge with one maintainer approval.
- Normative changes require an Accepted RFC and explicit active-maintainer
  approval. With exactly one active maintainer, that approval is sufficient
  with author/self-approval disclosed. With two or more, two distinct active
  maintainers must approve; with none, acceptance is blocked. No unresolved
  normative maintainer objection is permitted. Silence, bot merges, and CI
  success are not approvals.
- Security-adjacent changes require security review. Exploitable findings use
  the private process in [SECURITY.md](SECURITY.md).
- Breaking changes require the major-version RFC and compatibility/migration
  handling in governance §4. Governance and process changes use the normative
  review bar.

Acceptance, freeze, and stable release authorization remain separate decisions.
See governance §5 and [RELEASE.md](RELEASE.md); no document edit grants them.

## 5. Development checks

Run the checks appropriate to the changed material before requesting review:

```sh
python3 scripts/validate-repo.py all
python3 scripts/validate-schema.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The [schema tooling guide](docs/schema-tooling.md) documents prerequisites,
Buf checks, compatibility baselines, and reproducible generation. The
[conformance test guide](conformance/README.md) documents fixture authoring,
owner synchronization, and evidence requirements.

- Keep requirement IDs unique, indexed, and linked to appropriate cases.
- Keep schema comments and fixtures consistent with their current owners.
  Preserve field reservations; do not weaken compatibility checks or replace
  baselines to hide a break.
- Use BCP 14 keywords for normative requirements, with separate role
  obligations and bounded failure behavior where applicable.
- Include meaningful negative fixtures for affected failure paths.
- Review changes for private data, credentials, and application-specific
  dependencies. Keep generated output disposable and outside tracked sources.
- Report exact commands and results. Static checks and fixture registration
  are not executed protocol conformance or independent interoperability.

## 6. Sign-off (DCO)

All commits REQUIRE a `Signed-off-by` trailer to certify the Developer
Certificate of Origin (DCO 1.1):

```text
Signed-off-by: Your Name <you@example.com>
```

Use `git commit -s`. By signing off you certify you have the right to
contribute the change under the project's license (Apache-2.0, see
`LICENSE` and `GOVERNANCE.md` Sec. 7) and that the contribution
follows this guide.

## 7. Style

- Specifications: RFC-style Markdown, BCP 14 keywords, requirement IDs, and
  explicit role obligations. Use diagrams when they clarify behavior.
- Protobuf: explicit field numbers, preserved reservations, and comments
  consistent with the owning protocol text.
- Repository tooling: minimal dependencies, standard library preferred,
  no private registries.

## 8. What not to do

- Do not invent reporting contacts, deployment endpoints, or credentials.
- Do not change the project license on behalf of maintainers.
- Do not resolve protocol conflicts through implementation choices alone.
  Open an RFC or record a blocker against the current owner.
- Do not silently overwrite unrelated work or claim verification that was
  not executed.

Questions use [SUPPORT.md](SUPPORT.md). Vulnerabilities use
[SECURITY.md](SECURITY.md), never public issues.
