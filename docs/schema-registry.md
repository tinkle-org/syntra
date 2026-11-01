# Syntra Schema Registry — distribution and consumer contract

> **Proposed release-process update:** the `vX.Y` publication procedure in
> this branch is subject to public approval of Draft RFC 0011. The repository
> is specification-first and publishes no language bindings. Sections
> describing crates.io publication, nested Go module tags, or the
> committed-generation contract apply to the RC-1 snapshot (`2a91da7`) and
> are retained as process history for that release. Schema provenance,
> pinning discipline, and the tag-preservation rules remain in force.

- Status: Active schema-provenance and pinning contract (see scope note)
- Scope: How Syntra's Protobuf schemas are released and pinned, what consumers are guaranteed, and what generated packages do **not** provide. Protocol behavior is owned by `specifications/`; this document owns only schema provenance and consumer pinning.
- Normative references: `buf.yaml`, `proto/syntra/v1/*.proto`, `specifications/core/versioning.md` (SNTR-VER-*), `specifications/schema/compatibility.md`, `GOVERNANCE.md`, `CHANGELOG.md`, `conformance/profiles.yaml`, `RELEASE.md` §§4–6, `.github/workflows/spec-release.yml`.
- Terminology: BCP 14 keywords per `specifications/core/protocol.md`.

## 1. Distribution identity (A)

There is **no BSR module** and no release packaging. Proposed specification release tags:

```text
vX.Y      — specification release (Git tag only)
vX.Y-rcN  — release candidate (tag suffix only)
```

- Maintainers review the release PR and explicitly authorize the frozen
  version and commit in public (see `RELEASE.md` §4). Branches never define releases.
- `buf.yaml` carries **no registry `name:`** by design. A BSR identity is
  only needed for `buf push` / `--against-registry` breaking checks; this
  repository never pushes schemas to the BSR. Breaking baselines are
  committed Git artifacts (`compatibility/v1-initial/image.json`, §9). Do
  not re-add a BSR name without a maintainer decision recorded on a
  governance RFC.
- Language implementations pin schema revisions from here; no language
  artifacts are published from this repository.

| Item | Policy |
|---|---|
| Module ownership | Held by the Syntra maintainers (interim: repository owners per `GOVERNANCE.md` §2). |
| Visibility | **Public** Git repository; the tag and `CHANGELOG.md` at that commit carry the release. |
| Public status | A configured publishing path is not evidence of a completed release. Verify the tag and notes before pinning a dependency. |
| Source repository relationship | Git is the authoring authority AND the release point for tagged revisions (§2). |
| Release/tag relationship | Specification releases are tagged `vX.Y`; language implementations pin those revisions from here (see `RELEASE.md` §4). |

## 2. Source of truth (B)

```text
Git repository (proto/syntra/v1/*.proto)   ← sole authoring authority
        │  reviewed release PR + explicit authorization
        ▼
Release tag vX.Y (+ `CHANGELOG.md` section at that commit)
        │  git / tag pinning
        ▼
Consumers (implementations pin exact revisions; downstream generators
regenerate language types with the recorded pins)
```

- **Git** is where schemas are written, reviewed (RFC + quorum per `GOVERNANCE.md` §3), linted, and breaking-checked. Nothing is authoritative because it appeared in a release note; it is released because it was approved in Git.
- **Generated language types are downstream-owned.** Language
  implementation projects commit and drift-check their own generated
  output; this repository commits none.
- **Generated code MUST NOT become normative.** Generated types are a convenience serialization of the schema; protocol state machines, transport framing, authentication, RPC correlation, deadlines, cancellation, and error semantics live in `specifications/` and the conformance suite. Any conflict between generated helper behavior and the specifications resolves in favor of the specifications (ADR-010; see §6).

## 3. Buf configuration review (C)

Current `buf.yaml` (verified with Buf **1.59.0**; `buf lint` and `buf build` pass clean):

```yaml
version: v2
modules:
  - path: proto        # single module root; sole source tree (no registry name)
lint:
  use:
    - STANDARD          # no exceptions
breaking:
  use:
    - FILE              # no exceptions
```

Review findings:

| Check | Result |
|---|---|
| `version: v2` | Correct. |
| Single module, root `proto` | Correct. `proto/syntra/v1` is the sole source of truth; no second root, no historical tree. |
| Module `name` | Correct: **absent by design**. No `buf push` or `--against-registry` checks exist, so no registry identity is configured. Do not re-add one without a governance RFC. |
| Lint `STANDARD`, no exceptions | Correct. No `ignore` or per-rule exceptions exist, so none need justification. Any future exception MUST cite its RFC and expiry in a `buf.yaml` comment. |
| Breaking `FILE`, no exceptions | Correct and required: wire-only (`WIRE`) checks are insufficient for Syntra because moved types, import paths, and descriptor identity break consumers even when bytes do not (see `specifications/schema/compatibility.md`, three dimensions). Any future exception MUST cite its RFC and expiry. |
| Dependencies | **None.** All imports are intra-module (`syntra/v1/*.proto`). |
| Package layout | `package syntra.v1` in all seven files; import paths mirror the directory tree. No restructuring without a major-version RFC (SNTR-VER-003). |

`buf.yaml` carries no lint/breaking exceptions and no registry identity.

## 4. Dependencies and buf.lock (D)

No `buf.lock` exists, and none is required: the module declares zero remote dependencies, so there is nothing to lock. This was verified by inspecting every `import` in `proto/syntra/v1/*.proto` (all resolve inside the module) and by clean `buf build`/`buf lint` runs.

Rules going forward:

1. Avoid third-party schema dependencies. Prefer self-contained definitions; a new external import is a reviewed dependency decision, not a convenience.
2. If an external Protobuf module is ever imported: run `buf dep update`, commit the resulting `buf.lock`, and pin the dependency to an immutable commit (never a floating label).
3. Dependency update procedure: open a PR that updates `buf.lock`, shows `buf build` + full breaking + conformance impact, and passes security review (see §5). Merging the PR is the approval; direct pushes of dependency pins are forbidden.
4. Security review for dependency updates is mandatory: provenance of the dependency commit, change surface (new types/options that could alter generated code behavior), and supply-chain risk. Untrusted-fork dependencies are never accepted.

## 5. Public package namespace (E)

- Protobuf package: `package syntra.v1;` in all eight files. This is the wire-identity namespace and MUST NOT change within v1 (SNTR-VER-001/003).
- Language options audit:
  - `option go_package` is set in all eight files to `github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1` — historical module metadata (see MIGRATION.md §10); frozen bytes, FILE-breaking to change.
  - **Known wart:** this value embeds an organization path (`tinklehq`). Changing it alters generated import paths for every Go consumer and is therefore covered by Buf's `FILE` breaking rules (`FILE_SAME_GO_PACKAGE`): changing it requires the normative bar (RFC + maintainer quorum + `CHANGELOG.md` migration note), not an undocumented edit.
  - Java/C#/other languages: no explicit package options are set, and none are added for a single private consumer. Options are added only when the project decides they benefit consumers generally.

## 6. Generated-code policy (F)

Committed generated types are **convenience artifacts**. They provide generated Protobuf message types and nothing more. Stated prominently for every consumer:

- They **do** give you: typed `Frame`, `ClientHello`, `ServerReady`, `RpcRequest`, `RpcResult`, `Cancel`, `Notification`, `RpcError`, and `ErrorCode` values in your language, with serialization handled by the language's Protobuf runtime.
- They **do not** implement: Syntra handshake, session lifecycle, authentication behavior, RPC correlation, idempotency, retries, event streams, TCP framing, HTTP transport, or WebSocket transport — nor, more broadly: connection state machines, session binding, length prefixes, TLS handling, HTTP/WS mappings, credential handling, RPC deadlines/cancellation, capability negotiation, event subscription semantics, error-mapping policy, or resource bounds. All of that is specified in `specifications/` and proven by `conformance/` — there is no runtime in the generated package to "just call." Those behaviors are implemented by protocol implementation projects, never by generated packages.
- They are **not** the protocol. If generated convenience behavior ever appears to conflict with the specifications, the specifications win (ADR-010). Generated-only conveniences MUST remain non-normative and MUST NOT be cited in conformance claims.

## 7. Versioning strategy (G)

Five independent dimensions (SNTR-VER-001). The table below is the precise mapping; the dimensions MUST NOT be conflated:

| Dimension | Identifier | Examples | Governed by |
|---|---|---|---|
| Git commit | SHA | `92e5f28…` | Git history; every change lands here first |
| Git tag (specification release) | `vX.Y` or `-rcN` | `v1.0-rc1` | Maintainer authorization; protocol stability separately governed by `GOVERNANCE.md` §5 |
| Git tag | release identity | `v1.0` tag | Published by `.github/workflows/spec-release.yml` |
| Syntra Core version | protocol behavior | Syntra Core v1 | `specifications/core/versioning.md` |
| Protobuf package version | representation namespace | `syntra.v1` | `proto/` + Buf FILE checks |

Rules:

- Backward-compatible schema revisions (new optional field, new optional `oneof` member + capability, new enum value with tolerance handling, new file with new types) **may occur within `syntra.v1`** and keep the package name. They REQUIRE the additive path: RFC, `FILE` breaking pass, conformance coverage, `CHANGELOG.md` entry.
- Breaking changes (repurposed number/name, changed type, new required behavior, altered state machine, weakened security, changed failure semantics, `reserved` reuse) **require `syntra.v2`** (new package, new directory `proto/syntra/v2`) or an explicitly approved alternative recorded in a major-version RFC — never a silent in-place break (SNTR-VER-003, `GOVERNANCE.md` §4).
- The Core wire version (`Frame.version == 1`) and the package version (`syntra.v1`) advance independently: a `syntra.v1` additive revision does not change handshake negotiation; a Core v2 would require `syntra.v2` representation.
- Implementation release versions never version the protocol (ADR-010).

## 8. Release labels (H)

Channel semantics live in exact package versions and Git tags:

| Channel | GitHub mechanism | Git counterpart |
|---|---|---|
| `development` | `main` head (no release) | Commit on `main`, pre-tag |
| `candidate` | Tag suffix `-rcN` | `vX.Y-rcN` at the authorized commit |
| `stable` | Final release meeting the protocol stability criteria | `vX.Y` at the authorized commit, after `GOVERNANCE.md` §5 and applicable bundle gates hold |

Releases move forward only: re-pointing a release at an older commit is forbidden and is treated as an incident (audit, announce, re-release). No other channel vocabulary is introduced; anything fancier stays in Git metadata (notes, release notes), not in a registry.

## 9. Breaking-change baseline (I)

Breaking checks compare against the **most recent stable Git baseline**, never an arbitrary branch:

```text
pull request
  ↓  buf format --diff --exit-code
  ↓  buf lint
  ↓  buf build
  ↓  buf breaking --against <Git baseline>
  ↓  merge allowed (only on green + required reviews)
```

Downstream language projects run their own generation-drift, codec, and
(WASM where applicable) gates in their own repositories before relying on
a revision.

- Post-release baseline: build `image.json` from the stable release tag locally, verify its checksum, and commit it at a baseline path through a reviewed PR. Operators reproduce descriptors from the tagged revision:
  ```sh
  git fetch origin tag vX.Y
  git worktree add --detach /tmp/syntra-stable vX.Y
  (cd /tmp/syntra-stable && buf build -o /tmp/stable-image.json)
  shasum -a 256 /tmp/stable-image.json
  ```
  Do not retrieve a descriptor with `git show` from an arbitrary commit; only the reviewed release tag is an acceptable source. The `descriptor/` path is never committed at a tag in this repository.
- **Bootstrap baseline (current):** no stable release exists yet, so CI compares against the committed snapshot `compatibility/v1-initial/image.json` — the first seven-file layout image, built with Buf 1.59.0. Verified: current sources pass against it (`exit 0`). This is a floor, not a release: passing proves "no worse than the initial snapshot," and the snapshot is replaced by the first real stable baseline at release (a reviewed change, never automatic).
- Baseline replacement is a reviewed PR that states the old baseline, the new baseline, and why the switch is legitimate. CI never rewrites baselines itself.

## 10. Release policy (J)

| Event | Action |
|---|---|
| Pull request | Validate only (format, lint, build, breaking vs Git baseline). No credentials present; nothing attached. |
| Ordinary merge to `main` | Re-validate; no release is created. |
| Release PR merge | Freeze the merged revision and gather the required evidence; merging alone does not publish. |
| Authorized manual dispatch | Validate the exact commit and publish `vX.Y` or `vX.Y-rcN`; operators build `image.json` from the tag per §9. |
| Maintainer recovery release | Re-validate the existing merged tag and re-attach notes. Does not publish language artifacts. |
| Local developer machine | Can validate and prepare source, but does not bypass maintainer release authorization. Manual recovery is defined in `RELEASE.md` §4. |

Release automation checks tag identity, merged ancestry, and schema gates.
It cannot prove RFC approval or protocol conformance. Maintainer review,
branch/tag protection, and `GOVERNANCE.md` §5 remain required.

## 11. Consumer documentation (K)

This repository publishes no language bindings. Consumers pin a revision
of this repository (release tag or commit SHA) and generate types with the
recorded pins in `specifications/schema/generation.md`, or take types from
their language implementation project. Generated packages provide message
types only — no handshake, session lifecycle, authentication, RPC
correlation, idempotency, retries, event streams, TCP framing, HTTP
transport, or WebSocket transport.

Per-ecosystem guidance:

- Pin the schema source: a specification tag (`vX.Y`) or exact commit
  SHA of this repository.
- Pin the generator: remote plugin version **and** revision (as recorded
  in `specifications/schema/generation.md`), plus the language runtime
  version in the consumer's own lockfile.
- Branch on `ErrorCode`, never message text; map unknown numeric codes to
  `UNKNOWN` per SNTR-ERR-005. Generated getters alone do not implement
  that policy.

Pin exact Git revisions, generator plugin versions and revisions, and the
Protobuf runtime. Rebuild bindings deliberately; never float.

## 12. Reproducibility (L)

Production consumers pin **exact** revisions:

1. Pin the source: a specification tag (`vX.Y`) or commit SHA of this repository.
2. Pin the generator: remote plugin version **and** revision (see `specifications/schema/generation.md`), plus the Protobuf runtime version in the consumer's own lockfile. Verify `SHA256SUMS` on release assets when release assets are used.
3. Record all pins where the consumer records dependencies, so a rebuild years later reproduces identical types.
4. Upgrades are deliberate PRs in the consumer: bump one pin at a time, regenerate, rerun the consumer's Syntra conformance subset, and review `CHANGELOG.md` entries since the previously pinned tag.

## 13. Deprecation (M)

Per SNTR-VER-006 and `GOVERNANCE.md` §4, deprecating any schema element follows all five steps, in order:

1. Mark the element `deprecated = true` with a comment stating the replacement and the RFC that orders the deprecation.
2. Document the replacement path (field, method, or capability) and the migration window in `CHANGELOG.md`.
3. Preserve the field number **and** name appropriately: keep both reserved on removal; never reuse a removed number or name in v1 (SNTR-VER-005, SNTR-VER-003).
4. Retain compatibility throughout v1 where promised: deprecated elements MUST remain functional until their documented removal version.
5. Remove only under major-version policy: removing a mandatory element is major (`syntra.v2`); removing an optional element is minor-with-notice per SNTR-CAP-007 — and removal still requires the RFC, notice period, and conformance updates. Skipping any step is a process violation, not a shortcut.

## 14. Release security (N)

- **Release credentials:** validation uses a read-only `github.token`;
  publication uses the scoped `SPEC_RELEASE_TOKEN` environment secret after
  authorization. No `BUF_TOKEN`, BSR publishing environment, or GHCR login.
- **CI secrets:** PR jobs receive **no** release credentials (validation is credential-less apart from the read-only checkout). `pull_request_target` is not used.
- **Least privilege:** tag creation/attachment is confined to the release automation. Validation uses read-only permissions. Exposure handling is per `SECURITY.md`.
- **Pull-request security:** PR validation attaches nothing. Protect `main` (pull requests required) and protect creation/changes of the `v*` release-tag namespace for the maintainer-authorized workflow; historical implementation-era `syntra-*-v*` tags keep their existing protection. Release workflows run only in the upstream repository; privileged workflow changes require maintainer review.
- **Supply-chain implications:** remote generation submits schema text (including comments) to public generators — publishable content only, never production payloads or credentials (already policy in `specifications/schema/generation.md`). Consumers pin plugin revisions to blunt generator-side substitution.
- **Untrusted forks:** fork PRs run validation with no secrets (`pull_request`, not `push` semantics for forks); maintainer approval is required before any privileged context touches fork code.

## 15. Version mapping reference

Authoritative relationships at a glance (see §7 for rules):

| You want… | Use… | Example (illustrative) |
|---|---|---|
| Exact schema bytes | Release tag or Git SHA | `v1.0` / `92e5f28…` |
| A specification release | Authorized Git tag (no GitHub Release) | `v1.0` |
| Current development | `main` head | moves with each accepted merge |
| Release candidate | Tag suffix `-rcN` | `v1.1-rc1` |
| Production dependency | Reviewed exact version meeting the needed stability criteria | `v1.1`; see `GOVERNANCE.md` §5 |
| Protocol behavior version | Syntra Core version (handshake-negotiated) | Core v1 (`Frame.version == 1`) |
| Representation namespace | Protobuf package | `syntra.v1` |
| Transport conformance | Transport profile ID | `SNTR-WSS-H1-V1` (see `conformance/profiles.yaml`) |

Specification release tags such as `v1.0` are explicit. Language artifact
distribution does not drive this workflow. Implementation versions do not
version the protocol (ADR-010).

## 16. What tags provide — and do not

Provides: release notes at the tagged revision. Tags must never be moved;
tag identity is the release identity — there is no mutable asset to
re-verify.

Does not provide: protocol behavior, state machines, transport implementations, authentication, RPC runtime semantics, conformance verdicts, security review, or any guarantee beyond "these bytes are the tagged revision." A green validation run says nothing about whether an implementation conforms (only `conformance/` says that).
