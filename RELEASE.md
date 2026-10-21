# Syntra v1 Release Candidate — Release Process

This document defines how the repository is tagged as a Syntra v1 release
candidate, what is frozen at RC, how versions relate, and how release
artifacts are produced. It creates no new normative behavior; all rules
cite their owning specification or governance section.

Release authority: `GOVERNANCE.md` Sec. 5 (stability criteria),
`GOVERNANCE.md` Sec. 3 (approval quorum), `GOVERNANCE.md` Sec. 4 +
Deprecation (breaking/deprecation handling), `rfcs/README.md` (RFC
lifecycle — only **Accepted** RFCs may modify normative behavior),
`docs/schema-registry.md` (Git-tags + GitHub-Releases distribution contract),
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
- [ ] Rust tests pass (`cargo test --locked --workspace`)
- [ ] Go tests pass (`go test ./...` in `bindings/go`)
- [ ] WASM compile check passes (`cargo check --locked -p syntra-ffi --target wasm32-unknown-unknown`)
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
| Committed generation fresh | `scripts/validate-schema.py --drift-only` green (committed `crates/` + `bindings/go/` match pinned regeneration); `cargo test`, `go test`, WASM check green |
| Release workflow ready | `release-plz.toml` (Apache-2.0, publish enabled) + `.github/workflows/release.yml` reviewed and validation/build prerequisites green; asset publication is verified after tagging (§6) |
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

Releases are cut via the release-plz PR flow (`.github/workflows/release-plz.yml`).
Conventional commits on main keep a Release PR up to date (version bumps +
CHANGELOG). Review and merge that PR — approval and merge is the release gate.
On the next main push, release-plz publishes unpublished crates to crates.io
(trusted publishing preferred), cuts per-package tags (`<name>-vX.Y.Z`), and
creates GitHub Releases. Native artifacts and Go proxy warmup attach in
`release.yml` on release published.

Manual recovery tags (maintainers only) remain supported after the checklist
(§1) is fully evidenced and `audits/v1-release-readiness.md` is updated:

```sh
git tag -s syntra-core-v1.0.0-rc.1 -m "syntra-core v1.0.0-rc.1 (release candidate, not stable)"
git tag -s bindings/go/v1.0.0-rc.1 'syntra-core-v1.0.0-rc.1^{commit}' -m "Go bindings v1.0.0-rc.1"
git push --atomic origin syntra-core-v1.0.0-rc.1 bindings/go/v1.0.0-rc.1
```

Rules: annotated (preferably signed) tags only. Rust crates use per-package
tags (`<name>-vX.Y.Z`, `-rc.N` for prereleases); branches never define releases
(`GOVERNANCE.md` Sec. 5). For every release commit, sync `bindings/go/vX.Y.Z`
(or `bindings/go/vX.Y.Z-rc.N` for prereleases) at the SAME revision (required
for Go MVS to resolve the `bindings/go` module; `release.yml` verifies both
tags resolve to the same commit and fails closed, and `go-proxy-warmup` warms
proxy.golang.org plus pkg.go.dev). Tag protection rules SHOULD restrict tag
creation to maintainers. Deleting or moving a release tag is forbidden; fix
forward with a new tag.

## 5. Release artifacts

For each tag, `.github/workflows/release.yml` assembles and attaches to the
GitHub Release (Rust publishing itself happens in release-plz.yml via
crates.io; no GHCR, no BSR push):

- `image.json` — `buf build` descriptor of exactly the tagged revision.
- `syntra-schema-<tag>.tar.gz` — `descriptor/` (the descriptor plus the
  `buf export` tree), `manifests/` (from `conformance/manifest/*.yaml`),
  and `test-vectors/` (from `conformance/test-vectors/`) at the tag.
- `rust/` — Rust source archive + per-crate `.crate` files (offline-friendly;
  Apache-2.0, published to crates.io by release-plz) when the workspace exists.
- `go/` — `bindings/go` source archive (CGO wrapper + committed `*.pb.go`).
- `syntra-native-linux-amd64-<tag>.tar.gz`, `syntra-native-linux-arm64-<tag>.tar.gz` — `syntra-ffi` cdylib
  (`libsyntra_ffi.so`), staticlib (`libsyntra_ffi.a`), and C header
  (`syntra_ffi.h`) built `--locked --release` on each arch.
- `wasm/` — browser WASM archive (`syntra_ffi.wasm` tarball, built for
  `wasm32-unknown-unknown`).
- `CHANGELOG.md`, `RELEASE.md`, `GOVERNANCE.md`, `LICENSE` (as tagged).
- `SHA256SUMS` — checksums for exactly the flattened uploaded assets
  (excluding the checksum file itself), including `image.json`.

`scripts/collect-release-artifacts.sh <tag>` reproduces the
descriptor/manifests/vectors + docs subset locally under
`dist/release/<tag>/` (gitignored). Checksums are the integrity contract
for downloadable artifacts; the tag + checksums together define the RC.

## 6. GitHub Release association (no BSR)

There is no BSR module and no `buf push`. Release identity lives in
crates.io + Go module proxy + GitHub Releases (see `docs/schema-registry.md`
§§1, 8–10 and `docs/schema-release-checklist.md` §B–C):

Tag namespaces are distinct by design: Rust crates use per-package tags
(`<name>-vX.Y.Z`, §4 above) created by release-plz on merge, and nested Go
module tags use `bindings/go/vX.Y.Z` at the same revision; prereleases pair
`-rc.N` suffixes identically (release.yml verifies and fails closed, then
`go-proxy-warmup` indexes via proxy.golang.org and pkg.go.dev). A release is
cut only after the repository RC checklist (§1) holds. Association rules: Git
tag `<name>-vX.Y.Z` ↔ crates.io version + GitHub Release carrying the §5
assets; nested tag `bindings/go/vX.Y.Z` ↔ the same commit (verified, fails
closed) ↔ `go get` + pkg.go.dev docs; release maturity via prerelease flags
(`-rc` tags marked prerelease, finals marked latest) — never by moving a tag.
After the release completes, verify the GitHub Release contains Linux
amd64/arm64 native archives with libraries + header, the WASM archive, Rust
source/crate archives, descriptor, manifests/vectors, and SHA256SUMS, that
`cargo add syntra-core@X.Y.Z` resolves, and that `GOPROXY=proxy.golang.org
go list -m github.com/tinklehq/syntra/bindings/go@vX.Y.Z` resolves. Download
the assets and verify their checksums read-only (no credentials echoed).
