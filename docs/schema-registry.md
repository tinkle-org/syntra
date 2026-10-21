# Syntra Schema Registry — distribution and consumer contract

- Status: Active (Git tags + GitHub Releases; no BSR module, no registry publication)
- Scope: How Syntra's Protobuf schemas and generated types are distributed, what consumers are guaranteed, and what generated packages do **not** provide. Protocol behavior is owned by `specifications/`; this document owns only schema distribution.
- Normative references: `buf.yaml`, `proto/syntra/v1/*.proto`, `specifications/core/versioning.md` (SNTR-VER-*), `specifications/schema/compatibility.md`, `GOVERNANCE.md`, `CHANGELOG.md`, `conformance/profiles.yaml`, `RELEASE.md` §§4–6, `.github/workflows/release.yml`, `release-plz.toml`. (A root `buf.gen.yaml` MAY exist: it pins the committed `crates/` + `bindings/go/` generation. See §11.)
- Terminology: BCP 14 keywords per `specifications/core/protocol.md`.

## 1. Distribution identity (A)

There is **no BSR module**. Distribution identity is Git + GitHub Releases:

```text
Git tag vX.Y.Z (+ nested Go module tag bindings/go/vX.Y.Z, same revision)
```

- Release tags are cut by maintainers only (`RELEASE.md` §4; `GOVERNANCE.md` §5). Branches never define releases. CI never creates tags.
- `buf.yaml` carries **no registry `name:`** by design. A registry identity is only needed for `buf push` / `--against-registry` breaking checks, and this repository never pushes to a registry. Breaking baselines are committed Git artifacts (`compatibility/v1-initial/image.json`, §9). Do not re-add a registry name without a maintainer decision recorded on a governance RFC.
- The nested Go module tag (`bindings/go/vX.Y.Z`) is required for Go MVS to resolve the `bindings/go` module. `.github/workflows/release.yml` verifies it resolves to the same revision as `vX.Y.Z` and fails closed otherwise.

| Item | Policy |
|---|---|
| Module ownership | Held by the Syntra maintainers (interim: repository owners per `GOVERNANCE.md` §2). |
| Visibility | **Public** Git repository; GitHub Releases carry the downloadable assets. |
| Public status | Released only via tagged GitHub Releases. Until the first tag, the `main` head is the only distribution point. |
| Source repository relationship | Git is the authoring authority AND the distribution point for tagged revisions (§2). |
| Release/tag relationship | A Git tag of the form `vX.Y.Z` (or `vX.Y.Z-rc.N` prerelease) defines the release; `bindings/go/vX.Y.Z` at the same revision defines the Go module view. GitHub Releases attach the §5 asset set. |

## 2. Source of truth (B)

```text
Git repository (proto/syntra/v1/*.proto)   ← sole authoring authority
        │  pinned buf generate (reviewed change only)
        ▼
Committed generated types (crates/**, bindings/go/**)  ← reviewed, drift-checked
        │  maintainer tag vX.Y.Z (+ bindings/go/vX.Y.Z)
        ▼
GitHub Release (assets + SHA256SUMS)       ← published distribution
        │  git / tarball consumption
        ▼
Consumers (libtinkle via git; Go servers via CGO + prebuilt libs)
```

- **Git** is where schemas are written, reviewed (RFC + quorum per `GOVERNANCE.md` §3), linted, breaking-checked, and generated types are committed. Nothing is authoritative because it appeared in a release asset; it is in the asset because it was approved in Git.
- **Generated types are committed and reviewed.** History shows every regeneration; a bad generation is superseded by a new commit, never edited in place without review.
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

- Protobuf package: `package syntra.v1;` in all seven files. This is the wire-identity namespace and MUST NOT change within v1 (SNTR-VER-001/003).
- Language options audit:
  - `option go_package` is set in all seven files to `github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1`.
  - **Known wart:** this value embeds an organization path (`tinklehq`). Changing it alters generated import paths for every Go consumer and is therefore covered by Buf's `FILE` breaking rules (`FILE_SAME_GO_PACKAGE`): changing it requires the normative bar (RFC + maintainer quorum + `CHANGELOG.md` migration note), not an undocumented edit. The committed Go module lives at `bindings/go` with exactly this import path, so the wart is at least self-consistent until a migration RFC lands.
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
| Git tag (release) | `vX.Y.Z` | `v1.0.0` | Maintainer tag after `GOVERNANCE.md` §5 criteria hold |
| Nested Go module tag | `bindings/go/vX.Y.Z` | `bindings/go/v1.0.0` | Same revision as `vX.Y.Z` (verified by release.yml) |
| GitHub Release | tag assets + SHA256SUMS | `syntra-v1.0.0` assets | Attached by `.github/workflows/release.yml` |
| Syntra Core version | protocol behavior | Syntra Core v1 | `specifications/core/versioning.md` |
| Protobuf package version | representation namespace | `syntra.v1` | `proto/` + Buf FILE checks |

Rules:

- Backward-compatible schema revisions (new optional field, new optional `oneof` member + capability, new enum value with tolerance handling, new file with new types) **may occur within `syntra.v1`** and keep the package name. They REQUIRE the additive path: RFC, `FILE` breaking pass, conformance coverage, committed regeneration, `CHANGELOG.md` entry.
- Breaking changes (repurposed number/name, changed type, new required behavior, altered state machine, weakened security, changed failure semantics, `reserved` reuse) **require `syntra.v2`** (new package, new directory `proto/syntra/v2`) or an explicitly approved alternative recorded in a major-version RFC — never a silent in-place break (SNTR-VER-003, `GOVERNANCE.md` §4).
- The Core wire version (`Frame.version == 1`) and the package version (`syntra.v1`) advance independently: a `syntra.v1` additive revision does not change handshake negotiation; a Core v2 would require `syntra.v2` representation.
- Implementation release versions never version the protocol (ADR-010).

## 8. Release labels (H)

There are no registry labels. Channel semantics live in Git tag + GitHub Release metadata:

| Channel | GitHub mechanism | Git counterpart |
|---|---|---|
| `development` | `main` head (no release) | Commit on `main`, pre-tag |
| `candidate` | GitHub Release marked **prerelease** from a `-rc` tag | Tag `vX.Y.Z-rc.N` (+ nested Go tag) |
| `stable` | GitHub Release marked **latest** from a final tag | Tag `vX.Y.Z` (+ nested Go tag), after `GOVERNANCE.md` §5 criteria hold |

Releases move forward only: re-pointing a release at an older commit is forbidden and is treated as an incident (audit, announce, re-release). No other channel vocabulary is introduced; anything fancier stays in Git metadata (notes, release notes), not in a registry.

## 9. Breaking-change baseline (I)

Breaking checks compare against the **most recent stable Git baseline**, never an arbitrary branch:

```text
pull request
  ↓  buf format --diff --exit-code
  ↓  buf lint
  ↓  buf build
  ↓  buf breaking --against <Git baseline>
  ↓  committed-generation drift check (--drift-only)
  ↓  cargo test / go test / WASM check
  ↓  merge allowed (only on green + required reviews)
```

- Post-release baseline: the descriptor attached to the stable GitHub Release (or the tagged revision itself, e.g. `git show vX.Y.Z:descriptor/image.json`), adopted by a reviewed PR.
- **Bootstrap baseline (current):** no stable release exists yet, so CI compares against the committed snapshot `compatibility/v1-initial/image.json` — the first seven-file layout image, built with Buf 1.59.0. Verified: current sources pass against it (`exit 0`). This is a floor, not a release: passing proves "no worse than the initial snapshot," and the snapshot is replaced by the first real stable baseline at release (a reviewed change, never automatic).
- Baseline replacement is a reviewed PR that states the old baseline, the new baseline, and why the switch is legitimate. CI never rewrites baselines itself.

## 10. Release policy (J)

| Event | Action |
|---|---|
| Pull request | Validate only (format, lint, build, breaking vs Git baseline, generation drift, tests). No credentials present; nothing attached. |
| Merge to `main` | Re-validate. **No automatic release.** Release PRs are opened by release-plz (version bumps + CHANGELOG); maintainers merge them, then cut tags manually. |
| Version tag `vX.Y.Z` | Re-validate, then build native libs (amd64/arm64) + WASM + archives and attach to the GitHub Release. Tags are the only path to a release. Nested Go tag `bindings/go/vX.Y.Z` must exist at the same revision (verified, fails closed). |
| Local developer machine | MUST NOT be treated as an official release under any circumstances. Maintainer-run pushes outside the tag workflow do not exist. |

Unreviewed pushes can never become a `stable` release: the release workflow requires a tag event, validates versions/revision plus the nested Go tag identity, and only attaches assets — three independent gates (§14). CI never creates tags.

## 11. Committed generated-types consumer documentation (K)

Consumers obtain types from the committed tree or the release assets — never from a registry. Generated source IS committed here: `crates/**` (Rust) and `bindings/go/**` (Go, incl. `*.pb.go`), drift-checked by `scripts/validate-schema.py --drift-only` (CI-enforced). Repository-side codec tests run against the committed output; `.tmp/` holds only disposable reproducibility output and must never be committed (boundary check fails if it is).

Per-ecosystem guide (versions below are the versions pinned for this repository's validation in `specifications/schema/generation.md`, not floating `latest`):

- **Rust (primary):** depend on the crates directly via git (e.g. `libtinkle` consumes `syntra-schema` / `syntra-ffi` at the tagged revision). Message/enum types only — no networking, no gRPC, no transport. Runtime: `prost` at the pinned version. Branch on `ErrorCode`, never on message text; map unknown numeric codes to `UNKNOWN` per SNTR-ERR-005 — generated getters alone do not implement that policy. `release-plz.toml` versions the crates (Apache-2.0, `publish = false`); the GitHub Release carries source + `.crate` archives.
- **Go:** use the committed `bindings/go` module (`github.com/tinklehq/syntra/bindings/go`) at the tagged revision via the nested tag `bindings/go/vX.Y.Z`, plus the prebuilt Linux native libs (`libsyntra_ffi.so`/`.a` + `syntra_ffi.h`) attached to the GitHub Release for the CGO wrapper. `buf generate` with the remote plugin `buf.build/protocolbuffers/go:v1.36.6` (revision 1 in this repo's validation), `paths=source_relative`, against the pinned schema commit. Runtime: `google.golang.org/protobuf` at the pinned version.
- **Other languages:** generate from `buf export` output of the tagged revision with a pinned local compiler and record the toolchain version in the consumer's lockfile.

In every case: pin the Git tag (exact `vX.Y.Z`), pin the generator plugin version + revision, and vendor or lock the Protobuf runtime. Rebuild bindings deliberately; never float.

## 12. Reproducibility (L)

Production consumers pin **exact** revisions:

1. Pin the source: Git tag `vX.Y.Z` (preferred) or commit SHA; for the Go module, the nested tag `bindings/go/vX.Y.Z` at the same revision.
2. Pin the generator: remote plugin version **and** revision (as this repository's validation pins do — see `specifications/schema/generation.md` and `scripts/validate-schema.py`), plus the Protobuf runtime version in the consumer's own lockfile. Verify `SHA256SUMS` on release assets.
3. Record all three (Git tag, plugin version + revision, runtime version) where the consumer records dependencies, so a rebuild years later reproduces identical types.
4. Upgrades are deliberate PRs in the consumer: bump one pin at a time, regenerate, rerun the consumer's Syntra conformance subset, and review `CHANGELOG.md` entries since the previously pinned tag.

## 13. Deprecation (M)

Per SNTR-VER-006 and `GOVERNANCE.md` §4, deprecating any schema element follows all five steps, in order:

1. Mark the element `deprecated = true` with a comment stating the replacement and the RFC that orders the deprecation.
2. Document the replacement path (field, method, or capability) and the migration window in `CHANGELOG.md`.
3. Preserve the field number **and** name appropriately: keep both reserved on removal; never reuse a removed number or name in v1 (SNTR-VER-005, SNTR-VER-003).
4. Retain compatibility throughout v1 where promised: deprecated elements MUST remain functional until their documented removal version.
5. Remove only under major-version policy: removing a mandatory element is major (`syntra.v2`); removing an optional element is minor-with-notice per SNTR-CAP-007 — and removal still requires the RFC, notice period, and conformance updates. Skipping any step is a process violation, not a shortcut.

## 14. Release security (N)

- **Release credentials:** the release workflow uses only the automatic `github.token` with `contents: write` to attach assets to the GitHub Release — no long-lived push tokens, no registry credentials in code, logs, or artifacts. No `BUF_TOKEN`, no `bsr-publish` environment, no GHCR login.
- **CI secrets:** PR jobs receive **no** release credentials (validation is credential-less apart from the read-only checkout). `pull_request_target` is not used.
- **Least privilege:** the token cannot manage modules, owners, or other repositories. Rotation follows GitHub's automatic token rotation; exposure handling is per `SECURITY.md`.
- **Pull-request security:** validation runs on the PR's code but attaches nothing; the release path triggers only on tags, and tag protection rules restrict who can create `v*` and `bindings/go/v*` tags, so a malicious PR cannot self-release by adding a tag workflow.
- **Supply-chain implications:** remote generation submits schema text (including comments) to public generators — publishable content only, never production payloads or credentials (already policy in `specifications/schema/generation.md`). Consumers pin plugin revisions to blunt generator-side substitution.
- **Untrusted forks:** fork PRs run validation with no secrets (`pull_request`, not `push` semantics for forks); maintainer approval is required before any privileged context touches fork code.

## 15. Version mapping reference

Authoritative relationships at a glance (see §7 for rules):

| You want… | Use… | Example (illustrative) |
|---|---|---|
| Exact schema bytes | Git tag (or pre-release: Git SHA) | `v1.0.0` / `92e5f28…` |
| A release line | Git tag `vX.Y.Z` | `v1.0.0` |
| Nested Go module | Go module tag `bindings/go/vX.Y.Z` (same revision) | `bindings/go/v1.0.0` |
| Current development | `main` head | moves with each accepted merge |
| Release candidate | GitHub prerelease / `-rc` tag | `v1.1.0-rc.1` |
| Production dependency | GitHub Release marked latest / final tag | `v1.1.0` |
| Protocol behavior version | Syntra Core version (handshake-negotiated) | Core v1 (`Frame.version == 1`) |
| Representation namespace | Protobuf package | `syntra.v1` |
| Transport conformance | Transport profile ID | `SNTR-WSS-H1-V1` (see `conformance/profiles.yaml`) |
| Native libs / WASM | Release assets (+ SHA256SUMS) | `libsyntra_ffi.so`, `syntra_ffi.h`, `syntra-wasm-v1.0.0.tar.gz` |

Git tags look like `v1.0.0`, **not** `proto-v1.0.0`. The `proto-` prefix scheme is retired: schema and implementation releases share the single `vX.Y.Z` line, with the nested Go tag covering the module path (ADR-010: implementation versions never version the protocol, but they share the release vehicle).

## 16. What GitHub Releases provide — and do not

Provides: immutable Git tags, downloadable release assets (Rust source/crates, native libs + header, WASM archive, descriptor, manifests, vectors, SHA256SUMS), and a public browseable release page.

Does not provide: protocol behavior, state machines, transport implementations, authentication, RPC runtime semantics, conformance verdicts, security review, or any guarantee beyond "these bytes are the tagged revision." A green release workflow means the tag validated and assets attached — it says nothing about whether an implementation conforms (only `conformance/` says that).
