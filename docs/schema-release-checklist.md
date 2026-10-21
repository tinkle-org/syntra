# Syntra schema release checklist

Use this checklist for every schema change and schema/Go release. Normative
changes require the RFC + quorum path in `GOVERNANCE.md` §3; protocol stability
requires §5. Distribution uses crates.io, nested Go module tags, and GitHub
Releases (no BSR or GHCR).

## A. Change proposal (every schema PR)

- [ ] The change cites its defining requirement IDs and, for normative changes, its approved RFC.
- [ ] `CHANGELOG.md` (`Unreleased`) describes the change, its compatibility class (additive/minor vs breaking/major per SNTR-VER-003), and migration notes if consumer-visible.
- [ ] No `buf.yaml` lint/breaking exceptions added; if any are proposed, each carries its RFC citation and expiry in a comment. No registry `name:` re-added (see `docs/schema-registry.md` §1).
- [ ] No new external `.proto` dependency; if one is proposed, `buf.lock` is added/updated, pinned to an immutable commit, and the supply-chain review (§D of `schema-registry.md`) is attached.
- [ ] `reserved` numbers/names are preserved; nothing is reused (SNTR-VER-005).
- [ ] Committed generation updated: `crates/` + `bindings/go/` regenerated with the pinned template and committed in the same PR (no drift; `scripts/validate-schema.py --drift-only` green).
- [ ] Conformance impact assessed: new/changed behavior has test coverage or a tracked placeholder linked from the requirement's `requirements.yaml` row.
- [ ] CI is green: `buf format --diff --exit-code`, `buf lint`, `buf build`, `buf breaking` against the current Git baseline, generation drift check, `cargo test` (`--workspace` plus `-p syntra-ffi --features test-fixture`, `-p syntra-ffi --features production`, and `build_contract.py`), `go test` (default tags plus `-tags syntranative` against the production library), non-FFI WASM success plus expected `syntra-ffi does not support WASM` failure, plus the schema test suite (`scripts/validate-schema.py`, `tests/schema`).

## B. Pre-release (tag creation)

- [ ] `GOVERNANCE.md` §5 stability criteria hold for the release scope (accepted specs + schemas, green conformance on two independent implementations or one plus packet-fixture verification during bootstrap, `CHANGELOG.md` complete).
- [ ] Version mapping recorded: `syntra-core-vX.Y.Z`, paired `bindings/go/vX.Y.Z` at the same commit, each other crate's own version, Core wire version, schema package (`syntra.v1`), and profiles covered. No global `vX.Y.Z` tag is assumed.
- [ ] No BSR identity/publication configured (`buf.yaml` has no `name:`, no `BUF_TOKEN` or BSR environment). crates.io publication is expected and confined to release-plz's publishing job.
- [ ] Maintainer-reviewed Release PR authorizes publishing (`release_always = false`); syntra-core's version matches the intended schema/Go release. Go-only changes include an explicit syntra-core version bump when a new paired release is needed.
- [ ] Tag protection covers `syntra-*-v*` and `bindings/go/v*`, with the release automation identity allowed. release-plz owns crate tags; `release.yml` owns the Go ref and never moves an existing tag.
- [ ] Full Apache-2.0 license and package repository metadata present; publishing credentials configured (OIDC trusted publisher, or scoped bootstrap token).
- [ ] Release notes describe wire contracts, migration notes, and the actual source/schema asset set. Native Go mode links the production library per `docs/production-runtime.md`; browser WASM binaries are not promised.

## C. Release (direct reusable workflow call or tag recovery)

- [ ] release-plz output directly called `release.yml` for the syntra-core tag, or a maintainer used tag push/dispatch recovery. No dependency on GITHUB_TOKEN-created push/release events.
- [ ] Re-validation inside the release job passed (format, lint, build, breaking vs Git baseline, boundary/links, generation drift) before any asset was attached.
- [ ] Release tooling Python tests and actionlint passed; syntra-core's parsed package version and merged tag ancestry validated.
- [ ] Nested Go module tag created or verified at syntra-core's peeled commit; mismatches fail closed. Go v2+ is blocked until the required module-path migration.
- [ ] `cargo package --workspace --locked --no-verify` succeeded and crate archives exist; no packaging error was swallowed. Registry publication performed build verification separately.
- [ ] Full source/crate archives, Go bindings archive, descriptor, manifests, vectors, and exact flat-asset `SHA256SUMS` attached to the syntra-core GitHub Release.
- [ ] No browser-WASM support inferred from compile-only checks. Native support is proven by linked runtime tests against the production library, not by compile checks alone.
- [ ] Correct maturity flagged (`prerelease` for `-rc` tags); finals/latest alone do not assert protocol stability. Releases move forward only.

## D. Post-release

- [ ] Downstream pinning verified: a clean-room consumer can fetch the tag (and nested Go tag), verify `SHA256SUMS`, and reproduce the release's descriptor (`buf build` at the tag matches `image.json`).
- [ ] Breaking baseline update proposed: CI's `--against` reference now points at the new stable Git baseline (reviewed PR, never automatic).
- [ ] `CHANGELOG.md` finalized for the release; `Unreleased` reset.
- [ ] crates.io version resolves; Go proxy resolves `.../bindings/go@vX.Y.Z` (leading `v` preserved). Proxy retry exhaustion fails the job; pkg.go.dev indexing is best-effort.
- [ ] No credential appeared in logs; only the crates publishing job received registry credentials. Artifact recovery used the automatic GitHub token and did not republish crates.
- [ ] Announcement states the profile list covered (per `conformance/claims.md` wording rules), the asset list, and the Go nested-tag revision — never a bare "Syntra compliant."
