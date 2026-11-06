# Specification release process

Syntra 1.0 is pre-release. This repository publishes specification documents
and schema provenance; it contains no protocol implementations or language
artifact publisher.

## 1. Current publication status

[RFC 0011](rfcs/0011-specification-release-versioning.md) is **Accepted (design
only; activation deferred)** under [Decision 0004](docs/decisions/0004-rfc-0011-0014-acceptance.md)
and the [public acceptance](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482)
at reviewed revision `cfab7655c348f1d04f4e1d57e28cc1a634478854`.
Its two-component tags and manual publication procedure are accepted design,
not active publication policy. **Release Please remains the active publisher;
the prepared manual publisher remains disabled for publication.** Until separate
process activation, [release-please.yml](.github/workflows/release-please.yml)
and its configuration maintain document-release PRs and publish three-component
prerelease tags and GitHub Releases after validation and release-PR merge.

Current development notes stay under `Unreleased` in
[CHANGELOG.md](CHANGELOG.md). No stable release or completed evidence is
declared by this document. RFC 0011's qualified status deliberately does not
match the exact bare Accepted-status guard in [scripts/spec-release.py](scripts/spec-release.py).
Acceptance does not remove that lock, retire Release Please, or make
publisher-specific supersession effective. No workflow is changed by this record.
Administrative protections are not asserted configured or tested.

## 2. Authority and release scope

[GOVERNANCE.md](GOVERNANCE.md) §§3–5 and the
[RFC process](rfcs/README.md) govern acceptance, compatibility, and releases.
RFC acceptance, specification freeze, and stable release authorization are
separate decisions. A release identifies its exact specification and schema
revision, declared carriers and capabilities, applicable evidence, and notes.

Stable authorization requires accepted and indexed normative scope, the
independent verification required by governance, and all applicable
bundle-specific gates under [RFC 0009](rfcs/0009-v1-bootstrap-governance-and-release-scope.md).
The general bootstrap fixture alternative does not waive those bundle gates.
Use the [conformance test guide](conformance/README.md) for declarations,
per-case verdicts, independent role pairings, and applicable security,
recovery, mobile, and operational evidence. Repository validation and candidate
tags do not satisfy those execution or review gates.

The acceptance decision records oscarlaw's human protocol/security self-review
with self-approval disclosed. It does not satisfy the separate independent human
security-review gate for the initial stable bundle, establish a freeze, or
authorize publication.

## 3. Validation and preparation

Before publication, review the scope, compatibility disposition, current
notes, open objections, and required evidence. Pin specifications, source IDL,
requirement indexes, selectors, cases, and fixtures at the same exact revision.
Changes affecting that freeze need renewed review and affected verification.

The release workflows run these checks against the release target:

```sh
python3 scripts/validate-repo.py all
python3 scripts/validate-schema.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

They also run Actionlint. The [schema tooling guide](docs/schema-tooling.md)
documents tool versions and compatibility checks. These commands validate
repository material, not a protocol implementation.

## 4. Tagging procedure (manual, authorized publication)

**Conditional procedure:** this section describes the prepared
[spec-release.yml](.github/workflows/spec-release.yml) workflow and
[publisher](scripts/spec-release.py). RFC 0011 design acceptance is complete;
activation is deferred. This procedure requires separately reviewed process
activation, including synchronized owner text and verified administrative
controls, before use. It does not authorize a release or change the active
process in §1.

### Administrative setup

- Configure the `spec-release` GitHub environment with required reviewers
  drawn from the active [maintainer roster](MAINTAINERS.md), as individual
  users. Its custom deployment policy must allow only the branch `main`.
  With exactly one active maintainer, prevent-self-review must be disabled.
- Store `SPEC_RELEASE_TOKEN` only as an environment secret. Use a narrowly
  scoped publishing identity with permission to create the authorized tags
  and GitHub Release records. Validation jobs do not receive this secret.
- Protect `main` and the `v*` tag namespace: restrict tag creation, prohibit
  tag movement/deletion, and require repository checks. Enable immutable
  releases where available. Verify these administrative protections before
  publication; the script does not establish them.

### Prepare and authorize

Use `vMAJOR.MINOR` or `vMAJOR.MINOR-rcN`, without leading zeroes and with a
positive candidate number. A candidate suffix does not assert stability.
Prepare a reviewed release PR with exactly one nonempty changelog section
matching the proposed tag, for example `## [v1.0-rc1]`. This section is created
when preparing an authorized release, not in advance as a fictional release.
After merge, select the full lowercase 40-character target commit SHA; it must
be a commit on trusted `main`'s ancestry.

Open a public decision issue or PR with these unique single-line fields:

```text
Release-Tag: v1.0-rc1
Release-Commit: <full-commit-sha>
Release-Scope: <reviewed scope, carriers and capabilities>
Release-Freeze: <freeze record or candidate status>
Release-Evidence: <evidence links or candidate limitations>
Release-Security: <security review link or candidate limitations>
Release-Objections: <none or resolution links>
Release-Self-Review: <yes or no>
```

For a stable tag, `Freeze`, `Evidence`, and `Security` must be HTTPS links to
actual records. Review their contents and all discussion; the script checks
structure, not evidence quality or unstructured objections. Keep the decision
open during publication.

After finalizing the decision body, each approving maintainer runs:

```sh
GITHUB_TOKEN="$(gh auth token)" python3 scripts/spec-release.py approval --issue 42 --tag v1.0-rc1 --target <full-commit-sha>
```

Post the output as a separate, unedited comment on that decision. It binds
approval to the tag, commit, and SHA-256 of the exact decision body. Editing the
body invalidates prior approvals; post new comments rather than editing them.
One active maintainer may approve with self-review disclosed; with two or more,
two distinct active-maintainer approvals are required. With no active
maintainer, authorization is blocked. No unresolved maintainer objection is
permitted. A maintainer can post `SYNTRA-OBJECT <tag> <full-commit-sha>`;
their later valid approval of the current body resolves that structured
objection. Environment approval does not replace the public quorum.

### Tag and recover

Dispatch `spec-release.yml` on upstream `main` with `tag`, `target_sha`,
`decision_issue`, and `recovery=false`. The workflow validates the exact
target without publication credentials, then requires the protected
environment's approval. Trusted publisher code rechecks RFC acceptance,
current `main`, roster, environment, public approvals, changelog, and tag
identity before writing. A changed `main` requires a fresh dispatch.

The authorized action creates the Git tag and corresponding GitHub Release
record with no uploaded assets. The tag and exact commit identify the
specification release; notes include the reviewed changelog section, full SHA,
and public decision link. The prerelease flag mirrors the `-rcN` suffix;
latest-release metadata is informative. There is no package, archive, or
registry publication step.

If publication stops after tag creation, investigate before dispatching the
same approved tag and commit with `recovery=true`. Recovery requires an
existing tag directly naming that commit and never moves it. It completes a
missing Release record or verifies an existing one against the approved tag,
prerelease flag, empty assets, notes, SHA, and decision link. A mismatched
record fails with a correction procedure; recovery does not rewrite it.
