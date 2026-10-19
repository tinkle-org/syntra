# Syntra Schema Registry — publication and consumer contract

- Status: Draft (BSR module identity approved as `tinklecorp/syntra`; publication policy pending RFC; publication is **disabled** until then)
- Scope: How Syntra's Protobuf schemas reach the Buf Schema Registry (BSR), what consumers are guaranteed, and what BSR does **not** provide. Protocol behavior is owned by `specifications/`; this document owns only schema distribution.
- Normative references: `buf.yaml`, `proto/syntra/v1/*.proto`, `specifications/core/versioning.md` (SNTR-VER-*), `specifications/schema/compatibility.md`, `GOVERNANCE.md`, `CHANGELOG.md`, `conformance/profiles.yaml`. (There is intentionally no `buf.gen.yaml`: the repository performs no local binding generation. See §11.)
- Terminology: BCP 14 keywords per `specifications/core/protocol.md`.

## 1. BSR module identity (A)

The approved BSR module path is:

```text
buf.build/tinklecorp/syntra
```

The module identity was approved by maintainer decision; the organization
is `tinklecorp` and the module name is `syntra`. Do not change the module
path without a new maintainer decision recorded on the publication RFC
(see `docs/schema-release-checklist.md`). Publication itself remains
disabled until the publication policy RFC is accepted and a maintainer
cuts a `proto-v*` tag — approving the identity does not authorize any push.

| Item | Policy |
|---|---|
| Module ownership | Held by the Syntra maintainers (interim: repository owners per `GOVERNANCE.md` §2). Ownership transfer or sharing requires the normative bar (`GOVERNANCE.md` §3). |
| Module visibility | **Public** on first publication. Private staging (if ever used) must never be cited as the consumer contract. |
| Public status | Not yet published. Until the first `buf push` to the approved module, the Git repository is the only distribution point. |
| Source repository relationship | Git is the authoring authority; BSR is a read-only distribution mirror of tagged schema revisions (§2). |
| Release/tag relationship | A Git tag of the form `proto-vX.Y.Z` (proposed; pending approval) triggers publication of exactly that revision. Branches never define releases (`GOVERNANCE.md` §5). BSR commits are content-addressed; human-meaningful release identity comes from BSR **labels** applied at push time (§8). |

## 2. Source of truth (B)

```text
Git repository (proto/syntra/v1/*.proto)   ← sole authoring authority
        │  buf push (reviewed tag only)
        ▼
BSR module (immutable commits + labels)     ← published distribution
        │  buf generate (remote plugins, pinned)
        ▼
Generated SDKs (message types only)         ← derived convenience artifacts
```

- **Git** is where schemas are written, reviewed (RFC + quorum per `GOVERNANCE.md` §3), linted, and breaking-checked. Nothing is authoritative because it appeared on BSR; it is on BSR because it was approved in Git.
- **BSR** stores immutable schema commits. History is never rewritten; a bad publication is superseded by a new commit, never edited in place.
- **Generated SDK code MUST NOT become normative.** Generated types are a convenience serialization of the schema; protocol state machines, transport framing, authentication, RPC correlation, deadlines, cancellation, and error semantics live in `specifications/` and the conformance suite. Any conflict between generated helper behavior and the specifications resolves in favor of the specifications (ADR-010; see §6).

## 3. Buf configuration review (C)

Current `buf.yaml` (verified 2026-10-19 with Buf **1.59.0**; `buf lint` and `buf build` pass clean):

```yaml
version: v2
modules:
  - path: proto        # single module root; sole source tree
    name: buf.build/tinklecorp/syntra   # approved BSR identity (§1)
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
| Module `name` | Correct: `buf.build/tinklecorp/syntra`, matching the approved BSR identity (§1). Required for `buf push` and `--against-registry` breaking checks. Do not change without a maintainer decision on the publication RFC. |
| Lint `STANDARD`, no exceptions | Correct. No `ignore` or per-rule exceptions exist, so none need justification. Any future exception MUST cite its RFC and expiry in a `buf.yaml` comment. |
| Breaking `FILE`, no exceptions | Correct and required: wire-only (`WIRE`) checks are insufficient for Syntra because moved types, import paths, and descriptor identity break consumers even when bytes do not (see `specifications/schema/compatibility.md`, three dimensions). Any future exception MUST cite its RFC and expiry. |
| Dependencies | **None.** All imports are intra-module (`syntra/v1/*.proto`). |
| Package layout | `package syntra.v1` in all seven files; import paths mirror the directory tree. No restructuring without a major-version RFC (SNTR-VER-003). |

`buf.yaml` carries no lint/breaking exceptions; the only post-review change is the approved module `name` above, which enables (but never auto-triggers) publication.

## 4. Dependencies and buf.lock (D)

No `buf.lock` exists, and none is required: the module declares zero remote dependencies, so there is nothing to lock. This was verified by inspecting every `import` in `proto/syntra/v1/*.proto` (all resolve inside the module) and by clean `buf build`/`buf lint` runs.

Rules going forward:

1. Avoid third-party schema dependencies. Prefer self-contained definitions; a new external import is a reviewed dependency decision, not a convenience.
2. If an external Protobuf module is ever imported: run `buf dep update`, commit the resulting `buf.lock`, and pin the dependency to an immutable commit (never a floating label).
3. Dependency update procedure: open a PR that updates `buf.lock`, shows `buf build` + full breaking + conformance impact, and passes security review (see §5). Merging the PR is the approval; direct pushes to dependency pins are forbidden.
4. Security review for dependency updates is mandatory: provenance of the dependency commit, change surface (new types/options that could alter generated code behavior), and supply-chain risk (maintainer identity, registry trust). Untrusted-fork dependencies are never accepted.

## 5. Public package namespace (E)

- Protobuf package: `package syntra.v1;` in all seven files. This is the wire-identity namespace and MUST NOT change within v1 (SNTR-VER-001/003).
- Language options audit:
  - `option go_package` is set in all seven files to `github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1`.
  - **Finding (publication blocker):** this value embeds a private organization path (`tinklehq`). For a public, BSR-published module it implies a private repository as the Go import home, which conflicts with the project's independence requirements. It is **not changed by this task** because `go_package` is covered by Buf's `FILE` breaking rules (`FILE_SAME_GO_PACKAGE`): changing it alters generated import paths for every Go consumer and therefore requires the normative bar (RFC + maintainer quorum + `CHANGELOG.md` migration note), not an undocumented edit.
  - **Recommendation (pending maintainer decision):** adopt a neutral, stable public value at publication time, e.g. a path derived from the approved BSR module identity or the public repository home, and record the migration in `CHANGELOG.md` and `MIGRATION.md`. Until then, Go consumers generate from the published schema (or, pre-publication, from this repository's `proto/` tree with their own generation template) and MUST NOT treat the interim import path as a stability promise. Nothing in this repository is generated from it: there are no local bindings to copy.
  - Java/C#/other languages: no explicit package options are set, and none are added by this task. Per policy, options are added only when the project decides they benefit consumers generally — never for a single private consumer.

## 6. Generated SDK policy (F)

BSR-generated SDKs are **convenience artifacts**. They provide generated Protobuf message types and nothing more. Stated prominently for every consumer:

- They **do** give you: typed `Frame`, `ClientHello`, `ServerReady`, `RpcRequest`, `RpcResult`, `Cancel`, `Notification`, `RpcError`, and `ErrorCode` values in your language, with serialization handled by the language's Protobuf runtime.
- They **do not** implement: Syntra handshake, session lifecycle, authentication behavior, RPC correlation, idempotency, retries, event streams, TCP framing, HTTP transport, or WebSocket transport — nor, more broadly: connection state machines, session binding, length prefixes, TLS handling, HTTP/WS mappings, credential handling, RPC deadlines/cancellation, capability negotiation, event subscription semantics, error-mapping policy, or resource bounds. All of that is specified in `specifications/` and proven by `conformance/` — there is no runtime in the SDK to "just call." Those behaviors are implemented by separate protocol implementation projects, never by generated packages.
- They are **not** the protocol. If generated convenience behavior ever appears to conflict with the specifications, the specifications win (ADR-010). SDK-only conveniences MUST remain non-normative and MUST NOT be cited in conformance claims.

## 7. Versioning strategy (G)

Five independent dimensions (SNTR-VER-001). The table below is the precise mapping; the dimensions MUST NOT be conflated:

| Dimension | Identifier | Examples | Governed by |
|---|---|---|---|
| Git commit | SHA | `92e5f28…` | Git history; every change lands here first |
| Git tag (schema) | `proto-vX.Y.Z` (proposed) | `proto-v1.0.0` | Maintainer tag after `GOVERNANCE.md` §5 criteria hold |
| BSR commit | content hash | assigned at `buf push` | BSR immutability; never rewritten |
| BSR label | release channel label | `stable`, plus version labels (see §8) | Applied at push; moves only forward to newer commits |
| Syntra Core version | protocol behavior | Syntra Core v1 | `specifications/core/versioning.md` |
| Protobuf package version | representation namespace | `syntra.v1` | `proto/` + Buf FILE checks |

Rules:

- Backward-compatible schema revisions (new optional field, new optional `oneof` member + capability, new enum value with tolerance handling, new file with new types) **may occur within `syntra.v1`** and keep the package name. They REQUIRE the additive path: RFC, `FILE` breaking pass, conformance coverage, `CHANGELOG.md` entry.
- Breaking changes (repurposed number/name, changed type, new required behavior, altered state machine, weakened security, changed failure semantics, `reserved` reuse) **require `syntra.v2`** (new package, new directory `proto/syntra/v2`) or an explicitly approved alternative recorded in a major-version RFC — never a silent in-place break (SNTR-VER-003, `GOVERNANCE.md` §4).
- The Core wire version (`Frame.version == 1`) and the package version (`syntra.v1`) advance independently: a `syntra.v1` additive revision does not change handshake negotiation; a Core v2 would require `syntra.v2` representation.
- Implementation release versions never version the protocol (ADR-010).

## 8. Release labels (H)

Only mechanisms BSR actually supports are used. BSR provides immutable commits and movable **labels** on commits; there is no built-in "channel" object. Channel semantics therefore live in label-application policy plus Git metadata:

| Channel | BSR mechanism | Git counterpart |
|---|---|---|
| `development` | Label applied to pushes from `main` (if the project enables main-branch pushes at all) | Commit on `main`, pre-tag |
| `candidate` | Label applied to a release-candidate tag push (e.g. `proto-v1.1.0-rc.1`) | The tag itself |
| `stable` | Label applied **only** to a final release tag push (e.g. `proto-v1.1.0`) | The tag itself, after `GOVERNANCE.md` §5 criteria hold |

Labels move forward only: re-pointing `stable` to an older commit is forbidden and is treated as an incident (audit, announce, re-advance). No other channel vocabulary is introduced; anything fancier stays in Git metadata (notes, releases page), not in BSR.

## 9. Breaking-change baseline (I)

Breaking checks compare against the **most recent stable schema release**, never an arbitrary branch:

```text
pull request
  ↓  buf format --diff --exit-code
  ↓  buf lint
  ↓  buf build
  ↓  buf breaking --against <stable baseline>
  ↓  merge allowed (only on green + required reviews)
```

- Post-publication baseline: the BSR commit carrying the `stable` label (`--against-registry` once module names are configured, or an explicit pinned commit).
- **Bootstrap baseline (current):** no stable release exists yet, so CI compares against the committed snapshot `compatibility/v1-initial/image.json` — the first seven-file layout image, built with Buf 1.59.0. Verified: current sources pass against it (`exit 0`). This is a floor, not a release: passing proves "no worse than the initial snapshot," and the snapshot is replaced by the first real stable baseline at publication (a reviewed change, never automatic).
- Baseline replacement is a reviewed PR that states the old baseline, the new baseline, and why the switch is legitimate. CI never rewrites baselines itself.

## 10. Push policy (J)

| Event | Action |
|---|---|
| Pull request | Validate only (format, lint, build, breaking). No credentials present; no push possible. |
| Merge to `main` | Re-validate. **No automatic BSR publication** until module identity and policy are approved; when enabled, main-branch pushes may publish under the `development` label only. |
| Version tag `proto-vX.Y.Z` | Re-validate, then authenticated `buf push` + apply the release label (`candidate` for `-rc` tags, `stable` for finals). Tags are the only path to `stable`. |
| Local developer machine | MUST NOT be treated as an official release under any circumstances. Maintainer-run pushes outside the tag workflow do not exist. |

Unreviewed pushes can never become `stable`: the publish workflow requires a tag event, a protected environment with manual approval, and the exact approved module identity (`buf.build/tinklecorp/syntra`, rejecting anything else) — three independent gates (§14).

## 11. Generated SDK consumer documentation (K)

Consumers obtain bindings by generating from the published schema — never by copying source from this repository. Generated source is never committed here: this repository contains no `bindings/`, `gen/`, or `generated/` directories, and CI fails if they (or generated `*.pb.go` / `*_grpc.pb.go` files) are committed. Repository-side codec smoke tests generate into the ignored `.tmp/` directory only, via `scripts/validate-schema.py` (see `specifications/schema/generation.md`).

Conceptual per-ecosystem guide (exact commands depend on the consumer's own pinned generation template; versions below are the versions pinned for this repository's validation in `specifications/schema/generation.md`, not floating `latest`):

- **Go:** `buf generate` with the remote plugin `buf.build/protocolbuffers/go:v1.36.6` (revision 1 in this repo's validation), `paths=source_relative`, against the pinned schema commit. Runtime: `google.golang.org/protobuf` at the pinned version. Branch on `ErrorCode`, never on message text; map unknown numeric codes to `UNKNOWN` per SNTR-ERR-005 — generated getters alone do not implement that policy.
- **Rust:** `buf generate` with `buf.build/community/neoeinstein-prost:v0.4.0` (revision 1 in this repo's validation). Message/enum types only — no networking, no gRPC, no transport. Runtime `prost` at the pinned version.
- **Other BSR-supported ecosystems:** generate with the corresponding BSR remote plugin at a pinned version + revision against the same pinned schema commit. BSR language support varies; do not assume every language has identical plugin coverage — check the registry's plugin list for the target language and pin whatever is used. If no supported plugin exists, generate locally from `buf export` output with a pinned local compiler and record the toolchain version in the consumer's lockfile.

In every case: pin the schema commit (§12), pin the plugin version + revision, and vendor or lock the Protobuf runtime. Rebuild bindings deliberately; never float.

## 12. Reproducibility (L)

Production consumers pin **exact** revisions — "always use latest" is not an acceptable dependency policy:

1. Pin the schema: BSR commit hash (preferred) or an immutable tag; for pre-publication use, the Git commit SHA of the consumed tree.
2. Pin the generator: remote plugin version **and** revision (as this repository's validation pins do — see `specifications/schema/generation.md` and `scripts/validate-schema.py`), plus the Protobuf runtime version in the consumer's own lockfile.
3. Record all three (schema commit, plugin version + revision, runtime version) where the consumer records dependencies, so a rebuild years later reproduces identical types.
4. Upgrades are deliberate PRs in the consumer: bump one pin at a time, regenerate, rerun the consumer's Syntra conformance subset, and review `CHANGELOG.md` entries since the previously pinned commit.

## 13. Deprecation (M)

Per SNTR-VER-006 and `GOVERNANCE.md` §4, deprecating any schema element follows all five steps, in order:

1. Mark the element `deprecated = true` with a comment stating the replacement and the RFC that orders the deprecation.
2. Document the replacement path (field, method, or capability) and the migration window in `CHANGELOG.md`.
3. Preserve the field number **and** name appropriately: keep both reserved on removal; never reuse a removed number or name in v1 (SNTR-VER-005, SNTR-VER-003).
4. Retain compatibility throughout v1 where promised: deprecated elements MUST remain functional until their documented removal version.
5. Remove only under major-version policy: removing a mandatory element is major (`syntra.v2`); removing an optional element is minor-with-notice per SNTR-CAP-007 — and removal still requires the RFC, notice period, and conformance updates. Skipping any step is a process violation, not a shortcut.

## 14. Publication security (N)

- **Publishing credentials:** a dedicated BSR API token with the minimum scope (push to exactly the Syntra module). Stored as a GitHub environment secret (`BUF_TOKEN`) on the `bsr-publish` environment — never as a repository-wide secret, never in code, logs, or artifacts.
- **CI secrets:** PR jobs receive **no** publishing credentials (workflows split: validation is credential-less; publishing requires the protected environment). `pull_request_target` is not used.
- **Least privilege:** the token cannot manage the module, owners, or other repositories. Token rotation is documented in the release checklist and performed on role changes or suspected exposure.
- **Pull-request security:** validation runs on the PR's code but publishes nothing; push paths trigger only on tags / `main` and additionally require environment approval, so a malicious PR cannot self-publish by adding a tag workflow — tag protection rules restrict who can create `proto-v*` tags.
- **Supply-chain implications:** remote generation submits schema text (including comments) to public generators — publishable content only, never production payloads or credentials (already policy in `specifications/schema/generation.md`). Consumers pin plugin revisions to blunt generator-side substitution.
- **Untrusted forks:** fork PRs run validation with no secrets (`pull_request`, not `push` semantics for forks); maintainer approval is required before any privileged context touches fork code.

## 15. Version mapping reference

Authoritative relationships at a glance (see §7 for rules):

| You want… | Use… | Example (illustrative) |
|---|---|---|
| Exact schema bytes | BSR commit (or pre-publication: Git SHA) | BSR commit hash / `92e5f28…` |
| A release line | Git tag `proto-vX.Y.Z` | `proto-v1.0.0` (proposed scheme) |
| Current development | BSR `development` label / `main` head | moves with each accepted merge |
| Release candidate | BSR `candidate` label / `-rc` tag | `proto-v1.1.0-rc.1` |
| Production dependency | BSR `stable` label / final tag | `proto-v1.1.0` |
| Protocol behavior version | Syntra Core version (handshake-negotiated) | Core v1 (`Frame.version == 1`) |
| Representation namespace | Protobuf package | `syntra.v1` |
| Transport conformance | Transport profile ID | `SNTR-WSS-H1-V1` (see `conformance/profiles.yaml`) |

Git tags look like `proto-v1.0.0`, **not** `v1.0.0`: the `proto-` prefix keeps schema releases distinct from future implementation releases, since implementation versions never version the protocol (ADR-010).

## 16. What BSR provides — and does not

Provides: immutable schema commits, labels, breaking-change detection on push, remote code generation plugins, `buf export`/`buf convert`/`buf dep` consumption primitives, and a public browseable contract.

Does not provide: protocol behavior, state machines, transport implementations, authentication, RPC runtime semantics, conformance verdicts, security review, or any guarantee beyond "these bytes are the published schema." A green BSR push means the schema is well-formed and non-breaking — it says nothing about whether an implementation conforms (only `conformance/` says that).
