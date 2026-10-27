# Syntra schema release checklist

> **Scope note (2026-10-27).** This repository returned to specification-first
> ownership and is pre-release: schema changes are released as documents via
> release-please (see `MIGRATION.md` §10). Boxes below that reference
> language bindings, their release tags, or committed-generation drift
> apply to the RC-1 snapshot (`2a91da7`) and are retained as process
> history for that release; language gates are out of scope here.

Use this checklist for every schema change and schema release. Normative
changes require the RFC + quorum path in `GOVERNANCE.md` §3; protocol stability
requires §5. Schema provenance is released via release-please document
releases (no BSR or GHCR).

## A. Change proposal (every schema PR)

- [ ] The change cites its defining requirement IDs and, for normative changes, its approved RFC.
- [ ] `CHANGELOG.md` (`Unreleased`) describes the change, its compatibility class (additive/minor vs breaking/major per SNTR-VER-003), and migration notes if consumer-visible.
- [ ] No `buf.yaml` lint/breaking exceptions added; if any are proposed, each carries its RFC citation and expiry in a comment. No registry `name:` re-added (see `docs/schema-registry.md` §1).
- [ ] No new external `.proto` dependency; if one is proposed, `buf.lock` is added/updated, pinned to an immutable commit, and the supply-chain review (§D of `schema-registry.md`) is attached.
- [ ] `reserved` numbers/names are preserved; nothing is reused (SNTR-VER-005).
- [ ] Downstream regeneration recipe still works: the recorded generator pins in `specifications/schema/generation.md` regenerate these `.proto` files byte-identically (verified in the owning language projects, not here).
- [ ] Conformance impact assessed: new/changed behavior has test coverage or a tracked placeholder linked from the requirement's `requirements.yaml` row.
- [ ] CI is green: `buf format --diff --exit-code`, `buf lint`, `buf build`, `buf breaking` against the current Git baseline, plus the schema test suite (`scripts/validate-schema.py`, `tests/schema`).

## B. Pre-release (tag creation)

- [ ] `GOVERNANCE.md` §5 stability criteria hold for the release scope (accepted specs + schemas, green conformance on two independent implementations or one plus packet-fixture verification during bootstrap, `CHANGELOG.md` complete).
- [ ] Version recorded: `vX.Y.Z` document release tag, Core wire version, schema package (`syntra.v1`), and profiles covered.
- [ ] No BSR identity/publication configured (`buf.yaml` has no `name:`, no `BUF_TOKEN` or BSR environment). No language-artifact publishing from this repository.
- [ ] Maintainer-reviewed release PR (release-please) authorizes the release.
- [ ] Tag protection covers `syntra-*-v*`, with the release automation identity allowed.
- [ ] Full Apache-2.0 license present.
- [ ] Release notes describe wire contracts, migration notes, and the schema provenance. No browser-WASM assets are promised.

## C. Release (release-please merge)

- [ ] Release-please tagged `vX.Y.Z` (or the next prerelease) on release-PR merge and created the GitHub Release with the CHANGELOG notes. No dependency on GITHUB_TOKEN-created push/release events for validation.
- [ ] Re-validation inside the release job passed (format, lint, build, breaking vs Git baseline, boundary/links) before tagging.
- [ ] Release tooling Python tests and actionlint passed; merged tag ancestry validated.
- [ ] No language artifact expected: no crate archives, no bindings archive, no tag pairing beyond the document release tag.
- [ ] Correct maturity flagged (`prerelease` for `-rc` tags); finals/tags alone do not assert protocol stability. Releases move forward only.

## D. Post-release

- [ ] Downstream pinning verified: a clean-room consumer can fetch the tag and verify the descriptor (`buf build` at the tag matches the expected image).
- [ ] Breaking baseline update proposed: CI's `--against` reference now points at the new stable Git baseline (reviewed PR, never automatic).
- [ ] `CHANGELOG.md` finalized for the release; `Unreleased` reset.
- [ ] crates.io version resolves; Go proxy resolves `.../bindings/go@vX.Y.Z` (leading `v` preserved). Proxy retry exhaustion fails the job; pkg.go.dev indexing is best-effort.
- [ ] No credential appeared in logs; only the crates publishing job received registry credentials. Artifact recovery used the automatic GitHub token and did not republish crates.
- [ ] Announcement states the profile list covered (per `conformance/claims.md` wording rules), the asset list, and the Go nested-tag revision — never a bare "Syntra compliant."
