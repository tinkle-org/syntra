# Syntra schema release checklist

Use this checklist for every schema change (additive revision) and every release (tag + GitHub Release). All boxes must hold before a final release is marked latest. Normative changes additionally require the RFC + quorum path in `GOVERNANCE.md` §3 — this checklist does not replace it. Distribution is Git tags + GitHub Releases only (no BSR, no registries, no GHCR).

## A. Change proposal (every schema PR)

- [ ] The change cites its defining requirement IDs and, for normative changes, its approved RFC.
- [ ] `CHANGELOG.md` (`Unreleased`) describes the change, its compatibility class (additive/minor vs breaking/major per SNTR-VER-003), and migration notes if consumer-visible.
- [ ] No `buf.yaml` lint/breaking exceptions added; if any are proposed, each carries its RFC citation and expiry in a comment. No registry `name:` re-added (see `docs/schema-registry.md` §1).
- [ ] No new external `.proto` dependency; if one is proposed, `buf.lock` is added/updated, pinned to an immutable commit, and the supply-chain review (§D of `schema-registry.md`) is attached.
- [ ] `reserved` numbers/names are preserved; nothing is reused (SNTR-VER-005).
- [ ] Committed generation updated: `crates/` + `bindings/go/` regenerated with the pinned template and committed in the same PR (no drift; `scripts/validate-schema.py --drift-only` green).
- [ ] Conformance impact assessed: new/changed behavior has test coverage or a tracked placeholder linked from the requirement's `requirements.yaml` row.
- [ ] CI is green: `buf format --diff --exit-code`, `buf lint`, `buf build`, `buf breaking` against the current Git baseline, generation drift check, `cargo test`, `go test`, WASM check, plus the schema test suite (`scripts/validate-schema.py`, `tests/schema`).

## B. Pre-release (tag creation)

- [ ] `GOVERNANCE.md` §5 stability criteria hold for the release scope (accepted specs + schemas, green conformance on two independent implementations or one plus packet-fixture verification during bootstrap, `CHANGELOG.md` complete).
- [ ] Version mapping recorded: Git tag (`vX.Y.Z`), nested Go module tag (`bindings/go/vX.Y.Z`, same revision), Syntra Core version, package version (`syntra.v1`), and transport profiles covered.
- [ ] No registry identity configured (`buf.yaml` has no `name:`; no `BUF_TOKEN`, no `bsr-publish` environment, no `BSR_MODULE` variable). **If any registry push path exists, stop: publication is blocked.**
- [ ] Tags `vX.Y.Z` and `bindings/go/vX.Y.Z` created by a maintainer at the same revision; tag protection rules enforced (`v*`, `bindings/go/v*` restricted). CI never creates tags.
- [ ] `release-plz.toml` versions align with the tag (Apache-2.0, `publish = false`); Release PR merged before tagging.
- [ ] Release notes drafted from `CHANGELOG.md`: wire contracts, supported transports, native-lib/WASM asset list, migration notes, deprecation notices with removal versions.

## C. Release (tag workflow)

- [ ] Release workflow ran on the tag event only (never a branch push or manual local push; never creates tags).
- [ ] Re-validation inside the release job passed (format, lint, build, breaking vs Git baseline, boundary/links, generation drift) before any asset was attached.
- [ ] Nested Go module tag verified: `bindings/go/vX.Y.Z` resolves to the same revision as `vX.Y.Z` (workflow fails closed otherwise).
- [ ] Linux amd64/arm64 `syntra-ffi` native libs (cdylib/staticlib + header) built `--locked --release` and attached.
- [ ] Browser WASM archive built (`wasm32-unknown-unknown`) and attached.
- [ ] Rust source/crate archives, Go bindings archive, descriptor (`image.json`), manifests, test vectors, and `SHA256SUMS` attached to the GitHub Release.
- [ ] Correct maturity flagged (`prerelease` for `-rc` tags, `latest` for finals); releases move forward only.

## D. Post-release

- [ ] Downstream pinning verified: a clean-room consumer can fetch the tag (and nested Go tag), verify `SHA256SUMS`, and reproduce the release's descriptor (`buf build` at the tag matches `image.json`).
- [ ] Breaking baseline update proposed: CI's `--against` reference now points at the new stable Git baseline (reviewed PR, never automatic).
- [ ] `CHANGELOG.md` finalized for the release; `Unreleased` reset.
- [ ] No credential appeared in logs; release used only the automatic `github.token`.
- [ ] Announcement states the profile list covered (per `conformance/claims.md` wording rules), the asset list, and the Go nested-tag revision — never a bare "Syntra compliant."
