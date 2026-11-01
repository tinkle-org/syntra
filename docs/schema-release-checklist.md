# Syntra schema release checklist

> **Proposed change:** this checklist follows Draft RFC 0011 and is not in
> force until its public acceptance. Implementation-era release mechanics are
> retained in `RELEASE.md` and `MIGRATION.md` as historical records.

Use this checklist for every schema change and schema release. Normative
changes require the RFC + quorum path in `GOVERNANCE.md` §3; protocol stability
requires §5. Schema provenance is released via authorized specification
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

- [ ] For stable releases, `GOVERNANCE.md` §5 and the applicable bundle-specific evidence gates hold; RFC 0009's first bundle requires independent pure-Go/Rust results and security review.
- [ ] Version recorded: `vX.Y` or `vX.Y-rcN` specification tag, Core wire version, schema package (`syntra.v1`), and profiles covered.
- [ ] No BSR identity/publication configured (`buf.yaml` has no `name:`, no `BUF_TOKEN` or BSR environment). No language-artifact publishing from this repository.
- [ ] Maintainer-reviewed release PR, frozen commit and public version/SHA-bound release authorization are recorded. Self-review is disclosed when applicable.
- [ ] Tag protection covers `v*` (historical crate-era `syntra-*-v*` tags keep their protection), with the release automation identity allowed; the immutable-releases setting is enabled for the repository where available.
- [ ] Full Apache-2.0 license present.
- [ ] Release notes describe wire contracts, migration notes, and the schema provenance. No browser-WASM assets are promised.

## C. Release (manual, authorization-gated workflow)

- [ ] Protected `spec-release` environment, active maintainer reviewers, main-only policy, scoped publishing token, tag rulesets and immutable releases are configured.
- [ ] The manually dispatched workflow validates the exact frozen commit, public approval, tag identity and changelog section before creating the tag and its corresponding GitHub Release record.
- [ ] The GitHub Release references the released tag, carries the release notes with the full commit SHA and decision link, contains no assets, and its prerelease flag mirrors the `-rcN` suffix.
- [ ] Repository and schema gates, release tooling Python tests and actionlint passed against the target; merged tag ancestry is validated.
- [ ] No language artifact expected: no crate archives, no bindings archive, no tag pairing beyond the document release tag.
- [ ] Correct maturity recorded (`-rcN` suffix, changelog section, and mirroring prerelease flag); finals/tags alone do not assert protocol stability. Published tags never move.

## D. Post-release

- [ ] Downstream pinning verified: a clean-room consumer can fetch the tag and verify the descriptor (`buf build` at the tag matches the expected image).
- [ ] Breaking baseline update proposed: CI's `--against` reference now points at the new stable Git baseline (reviewed PR, never automatic).
- [ ] `CHANGELOG.md` finalized for the release; `Unreleased` reset.
- [ ] No credential appeared in logs; the environment-scoped token was available only to the publisher.
- [ ] Announcement states the profiles and evidence covered per `conformance/claims.md`; never claim bare "Syntra compliant."
