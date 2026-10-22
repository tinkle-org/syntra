# Syntra v1 Release Candidate — Release Process

This document defines how the repository is tagged as a Syntra v1 release
candidate, what is frozen at RC, how versions relate, and how release
artifacts are produced. It creates no new normative behavior; all rules
cite their owning specification or governance section.

Release authority: `GOVERNANCE.md` Sec. 5 (stability criteria),
`GOVERNANCE.md` Sec. 3 (approval quorum), `GOVERNANCE.md` Sec. 4 +
Deprecation (breaking/deprecation handling), `rfcs/README.md` (RFC
lifecycle — only **Accepted** RFCs may modify normative behavior),
`docs/schema-registry.md` (crates.io, Go modules, and GitHub Releases contract),
`docs/schema-release-checklist.md` (per-schema-release gates).

Status terms: an RC is a **candidate**, not a stable release. Tagging an
RC asserts the checklist below holds; it does not assert two-implementation
conformance green (that is the stable-release bar per `GOVERNANCE.md`
Sec. 5). Known unresolved blockers MUST be listed in
`audits/v1-release-readiness.md` and MUST block promotion to stable.

## 1. Release checklist (v1 RC)

Check each box with evidence (command output, PR link, or reviewer sign-off).
An unchecked box blocks tagging.

- [ ] Architecture approved
- [ ] Threat model approved
- [ ] Core specification complete
- [ ] Authentication/session complete
- [ ] RPC complete
- [ ] Events complete or marked optional
- [ ] TCP profile complete
- [ ] TLS/TCP profile complete
- [ ] HTTP profile complete
- [ ] HTTPS profiles complete
- [ ] WS profile complete
- [ ] WSS profile complete
- [ ] Proto lint passes
- [ ] Proto breaking checks pass
- [ ] Committed generated types fresh (`validate-schema.py --drift-only`)
- [ ] Rust tests pass (default `cargo test --locked --workspace` plus `cargo test -p syntra-ffi --features test-fixture`, `cargo test -p syntra-ffi --features production`, and `build_contract.py`)
- [ ] Go tests pass (`go test ./...` in `bindings/go` with default tags; `go test -tags syntranative ./...` against the production library)
- [ ] WASM checks pass (non-FFI `cargo check --locked -p syntra-core -p syntra-runtime -p syntra-ws -p syntra-web --target wasm32-unknown-unknown` succeeds; `syntra-ffi` WASM check fails with `syntra-ffi does not support WASM`)
- [ ] Conformance requirements complete
- [ ] Test vectors validated
- [ ] Consistency audit has no P0 blockers
- [ ] Release workflow ready to build and attach assets after tagging
- [ ] License present (Apache-2.0 `LICENSE`)
- [ ] Security process documented
- [ ] CHANGELOG updated

Evidence mapping (where each box is verified):

| Item | Evidence |
|---|---|
| Architecture / threat model approved | Accepted RFCs or maintainer quorum recorded on the RFC PRs; `SESSION-OPEN-QUESTIONS.md` shows no undecided blockers in scope |
| Core, auth/session, RPC, events specs | `specifications/core/*.md` accepted via RFC; every MUST/MUST NOT carries an ID (`scripts/validate-repo.py requirements`) |
| Events optional | `SNTR-EVENTS-V1` profile marked `OPTIONAL_CAPABILITY`; mandatory-only interop proven (`conformance/profiles.yaml`) |
| TCP … WSS profiles (7) | `specifications/transports/*.md` accepted; profile IDs match `conformance/profiles.yaml` exactly |
| Proto lint / breaking | `buf lint`, `buf build`, `buf breaking --against <stable baseline>` green (CI job `buf`) |
| Conformance requirements complete | `requirements.yaml` covers every defined ID; no `not_testable` without a stated reason (`validate-repo.py requirements manifests`) |
| Test vectors validated | `validate-repo.py vectors` green (hex parses, protobuf decodes against `proto/`, TCP lengths match, malformed vectors intentionally malformed) |
| Consistency audit no P0 | `audits/v1-consistency-review.md` P0 list empty or all P0s closed by Accepted RFCs; readiness report shows no BLOCKED area required for the RC scope |
| Committed generation fresh | `scripts/validate-schema.py --drift-only` green (committed `crates/` + `bindings/go/` match pinned regeneration); default + fixture `cargo test`, default-tag `go test`, and WASM checks green (non-FFI success + expected syntra-ffi failure) |
| Release workflow ready | `release-plz.toml` (publish enabled, `release_always = false`) + release workflows reviewed; tooling regression tests and actionlint green; asset publication is verified after tagging (§6) |
| License present | Apache-2.0 `LICENSE` file present per `GOVERNANCE.md` Sec. 7 |
| Security process documented | `SECURITY.md` private reporting channel live; embargo handling per `GOVERNANCE.md` Sec. 3 |
| CHANGELOG updated | `## [v1.0.0-rc.1]` section with Added/Changed/Deprecated/Removed/Security; every wire-affecting change has migration notes |

## 2. Version freeze (RC)

At RC tag time the following are frozen. After the tag, any change to a
frozen item REQUIRES explicit compatibility review: a normative RFC, a
`buf breaking` re-check against the RC baseline, updated conformance
fixtures, and `CHANGELOG.md`/`MIGRATION.md` notes. Additive clarifications
that change no wire bytes and no required behavior may land as
`v1.0.0-rc.2` prereleases under the same freeze.

Frozen protocol fields (`proto/syntra/v1`, package `syntra.v1`):

- `Frame`: `version = 1`, `request_id = 2`, `hello = 10`, `ready = 11`,
  `request = 12`, `result = 13`, `cancel = 14`, `notification = 15`;
  `reserved 16, 17`; `reserved "event", "resume", "ack"`.
- `ClientHello`: `min_version = 1`, `max_version = 2`, `credential = 3`
  (opaque bytes; empty means anonymous attempt per host policy).
- `ServerReady`: `connection_id = 1` (opaque diagnostic; never auth).
- `RpcRequest`: `method = 1`, `payload = 2`, `timeout_ms = 3`.
- `RpcResult`: `outcome` oneof with `payload = 1`, `error = 2`.
- `Cancel`: empty message (no fields).
- `Notification`: `payload = 1`.
- `RpcError`: `code = 1`, `message = 2`.
- `session.proto`, `capabilities.proto`: intentionally define no messages.

Frozen error codes (17 values, 0–16; only nonzero values are valid
failure outcomes; unknown received numbers map to `UNKNOWN` per
SNTR-ERR-005):

`ERROR_CODE_UNSPECIFIED = 0`, `ERROR_CODE_CANCELLED = 1`,
`ERROR_CODE_UNKNOWN = 2`, `ERROR_CODE_INVALID_ARGUMENT = 3`,
`ERROR_CODE_DEADLINE_EXCEEDED = 4`, `ERROR_CODE_NOT_FOUND = 5`,
`ERROR_CODE_ALREADY_EXISTS = 6`, `ERROR_CODE_PERMISSION_DENIED = 7`,
`ERROR_CODE_RESOURCE_EXHAUSTED = 8`,
`ERROR_CODE_FAILED_PRECONDITION = 9`, `ERROR_CODE_ABORTED = 10`,
`ERROR_CODE_OUT_OF_RANGE = 11`, `ERROR_CODE_UNIMPLEMENTED = 12`,
`ERROR_CODE_INTERNAL = 13`, `ERROR_CODE_UNAVAILABLE = 14`,
`ERROR_CODE_DATA_LOSS = 15`, `ERROR_CODE_UNAUTHENTICATED = 16`.

Frozen transport framing:

- TCP/TLS: 4-byte big-endian length prefix + serialized `Frame`; strict
  stream loop; no magic bytes; default 1 MiB bound with fail-closed
  pre-allocation (`SNTR-TCP-005`, `SNTR-TLS-009`).
- HTTP/HTTPS: `POST /syntra/v1/rpc`, one `Frame` per body, version
  headers, status layering (`200` + envelope = RPC outcome; anything else
  = transport outcome, never a synthesized `result`).
- WS/WSS: `/syntra/v1/ws` Upgrade, `syntra.v1` subprotocol, one binary
  message = one `Frame` (never `[length][protobuf]`), binary only,
  Ping/Pong liveness, normative close-code mapping.

Frozen handshake sequence: transport establishment →
`CONNECTED → NEGOTIATING → AUTHENTICATING → ACTIVE → CLOSING → CLOSED`;
exactly one `ClientHello` first; exactly one terminal outcome per
connection (`ServerReady` or handshake error + close); no re-handshake
on one transport (`SNTR-HS-001/040`).

Frozen `request_id` semantics: `uint64` connection-scoped correlation;
nonzero initiator-chosen, unique among outstanding RPCs on the
connection; `0` reserved for `hello`/`ready`/`notification`; reuse only
after the terminal `result` (stale-reuse conflict tracked as P0 finding
F-02, resolution via RFC 0004 — the freeze records current text, not a
resolution).

Frozen capability identifiers (placeholders pending the events RFC;
MUST NOT be advertised until the RFC is accepted):
`events-v1`, `events-replay-v1`; resumption token `resume-v1` (no RFC
exists; only resume-rejection is mandatory).

Known RC exceptions (frozen text contains these open conflicts; they MUST
be resolved by Accepted RFCs before stable): F-01 (profile identifier
spellings), F-02 (stale ID reuse), F-03 (pre-ACTIVE error carrier), F-04
(HTTP per-exchange ID amnesia vs stale rejection), F-05 (private
`go_package` path), F-06 (1 MiB payload fixture vs envelope bound).
See `audits/v1-consistency-review.md` and RFCs 0003–0005.

## 3. Version model

- **Syntra Core v1.0** versions protocol behavior (state machines,
  correlation, errors, negotiation). Governed by `SNTR-VER-*`.
- **Transport profile revisions are independent** of Core v1.0 and of
  each other (`SNTR-TCP-V1`, `SNTR-TLS-TCP-V1`, `SNTR-HTTP-V1`,
  `SNTR-HTTPS-H1-V1`, `SNTR-HTTPS-H2-V1`, `SNTR-WS-V1`,
  `SNTR-WSS-H1-V1`). A profile revision changes only byte binding,
  never `Frame` semantics (`SNTR-VER-001`; `SYN-ARCH-042`). There is
  deliberately no extra version-number layer: profiles are identified by
  stable IDs, and breaking profile changes are handled as major RFCs
  with migration notes, not as "Syntra TCP v2.0" product versions.
- **Schema package** `syntra.v1` versions representation; Buf governs
  field compatibility. A breaking schema change REQUIRES a new wire
  major version (`syntra.v2`), never an in-place break.
- **Implementation releases** version code only and NEVER version the
  protocol (ADR-010).

Consequence: "Syntra TCP v1.0" / "Syntra WSS v1.0" as independent
version lines are NOT defined. Claim conformance per profile ID
(`conformance/claims.md`, `declaration.example.yaml`); do not invent
per-transport version numbers.

## 4. Tagging procedure (release-plz PR, then publish on merge)

`.github/workflows/release-plz.yml` maintains a Release PR with package
versions and changelogs. Review its complete release scope and CI evidence
before merging. `release_always = false` prevents publication on ordinary
main commits: publication is authorized by merging a Release PR. The
repository must allow Actions to create PRs; approve the checks on bot-created
PRs if GitHub requires it before merging.

release-plz publishes Rust crates to crates.io (Trusted Publishing OIDC,
or a scoped bootstrap `CARGO_REGISTRY_TOKEN`), creates `<crate>-vX.Y.Z`
tags, and creates per-crate GitHub Releases. The explicit tag template is
stable even if the number of public crates changes. Package versions need
not all be equal; the artifact gate parses syntra-core's TOML version,
including workspace inheritance, instead of grepping dependency versions.

**The schema/Go release anchor is `syntra-core-vX.Y.Z`.** After publishing
syntra-core, release-plz passes its output tag directly to the reusable
`release.yml` workflow. A `GITHUB_TOKEN`-created tag or release does not
trigger another push/release workflow, so event chaining is not used.
Other crate releases carry their own notes and registry versions; they
do not each mint a Go tag or duplicate the schema assets. Global `vX.Y.Z`
tags are not part of this model.

After validation and packaging, `release.yml` creates the missing
`bindings/go/vX.Y.Z` ref at the syntra-core tag's **peeled commit**, or
verifies an existing ref at that commit. The workflow is the sole automated
owner of this namespace. It never moves an existing tag. This applies to
`-rc.N` suffixes too. Go v2+ is blocked until a reviewed module-path migration
adds the required major suffix. Changes to Go bindings alone require a
reviewed syntra-core version bump to cut a new paired release.

Recovery: rerun failed jobs, or dispatch `release.yml` with the existing
syntra-core tag. A maintainer may recreate a missing release path using a
new signed tag at an approved, merged commit whose package version matches:

```sh
git tag -s syntra-core-v1.0.0-rc.1 -m "syntra-core v1.0.0-rc.1 (release candidate, not stable)"
git push origin syntra-core-v1.0.0-rc.1
```

The tag push validates and attaches assets; it does **not** publish crates
to crates.io. Confirm registry publication separately during recovery.
Restrict `syntra-*-v*` and `bindings/go/v*` tag creation to maintainers and
the release automation identity. Automation may create lightweight refs;
manual recovery tags should be signed. Deleting or moving a published tag
is forbidden; fix forward. A mismatch in an existing Go tag blocks release
attachments and proxy warmup.

## 5. Release artifacts

The **syntra-core** GitHub Release receives this flat asset set from the
validated tagged commit (crates.io publishing is a separate preceding step):

- `image.json` — the `buf build` descriptor.
- `syntra-schema-<tag>.tar.gz` — `descriptor/` (descriptor and `buf export`
  sources), `manifests/`, and `test-vectors/`.
- `syntra-source-<tag>.tar.gz` — the full tracked source snapshot via
  `git archive`, including build scripts and schemas.
- `*.crate` — workspace package archives. `cargo package --workspace
  --locked --no-verify` must succeed; missing archives fail the job. The
  `syntra-ffi` default build exports no C ABI; `test-fixture` and
  `production` features export their respective ABIs. The registry
  publishing step performs build verification. Source archives do not
  vendor dependencies and do not promise offline builds.
- `syntra-go-bindings-<tag>.tar.gz` — the committed Go module source
  (`bindings/go` only; it documents the header location but does not carry
  the header). Native builds use the authoritative header from the source
  snapshot (`syntra-source-<tag>.tar.gz`:
  `crates/syntra-ffi/include/syntra_production.h`).
- `CHANGELOG.md`, `RELEASE.md`, `GOVERNANCE.md`, `LICENSE` (as tagged).
- `SHA256SUMS` — checksums for exactly the uploaded assets other than itself.

**Go native mode (`-tags syntranative`) builds against the production
library** (`cargo build -p syntra-ffi --features production`) and the
authoritative `crates/syntra-ffi/include/syntra_production.h`. Native
libraries are built from the tagged source; the Go module documents the
required header and linking setup. Browser WASM binaries remain withheld;
WASM checks are gates, not SDK claims. See `docs/production-runtime.md`.

`sh scripts/collect-release-artifacts.sh syntra-core-vX.Y.Z` (or
`sh scripts/collect-release-artifacts.sh vX.Y.Z syntra-core-vX.Y.Z` for a
version-named directory with an explicit `syntra-core-v…` ref) reproduces
only the descriptor/manifests/vectors + docs subset under
`dist/release/<name>/`. It does not publish a release. The default lookup
resolves `refs/tags/syntra-core-v…` (falling back from a bare `v…` name to
`refs/tags/syntra-core-v…`); otherwise supply the explicit `syntra-core-v…`
ref.

## 6. GitHub Release association (no BSR)

Rust package `<crate>` at version `X.Y.Z` maps to `<crate>-vX.Y.Z` and
its crates.io version. The schema/Go association is specifically
`syntra-core-vX.Y.Z` ↔ `bindings/go/vX.Y.Z` at the same commit ↔ the §5
assets. There is no BSR module, `buf push`, or GHCR publication.

RC tags are marked prerelease; final package tags do not by themselves
assert the protocol stability criteria in `GOVERNANCE.md` §5. After the
workflow completes, download and verify all assets against `SHA256SUMS`,
check that `cargo add syntra-core@X.Y.Z` resolves, and run
`GOPROXY=https://proxy.golang.org go list -m github.com/tinklehq/syntra/bindings/go@vX.Y.Z`.
Proxy warmup retries a version with the leading `v` and fails after five
unsuccessful attempts. pkg.go.dev indexing is asynchronous and best-effort.
If the registry release succeeded but later jobs failed, use §4 recovery;
publication and artifact attachment are not an atomic transaction.
