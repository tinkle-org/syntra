# Syntra schema release checklist

Use this checklist for every schema change (additive revision) and every schema release (tag + publication). All boxes must hold before a `stable` label moves. Normative changes additionally require the RFC + quorum path in `GOVERNANCE.md` §3 — this checklist does not replace it.

## A. Change proposal (every schema PR)

- [ ] The change cites its defining requirement IDs and, for normative changes, its approved RFC.
- [ ] `CHANGELOG.md` (`Unreleased`) describes the change, its compatibility class (additive/minor vs breaking/major per SNTR-VER-003), and migration notes if consumer-visible.
- [ ] No `buf.yaml` lint/breaking exceptions added; if any are proposed, each carries its RFC citation and expiry in a comment.
- [ ] No new external `.proto` dependency; if one is proposed, `buf.lock` is added/updated, pinned to an immutable commit, and the supply-chain review (§D of `schema-registry.md`) is attached.
- [ ] `reserved` numbers/names are preserved; nothing is reused (SNTR-VER-005).
- [ ] Conformance impact assessed: new/changed behavior has test coverage or a tracked placeholder linked from the requirement's `requirements.yaml` row.
- [ ] CI is green: `buf format --diff --exit-code`, `buf lint`, `buf build`, `buf breaking` against the current baseline, plus the schema test suite (`scripts/validate-schema.py`, `tests/schema`).

## B. Pre-release (tag creation)

- [ ] `GOVERNANCE.md` §5 stability criteria hold for the release scope (accepted specs + schemas, green conformance on two independent implementations or one plus packet-fixture verification during bootstrap, `CHANGELOG.md` complete).
- [ ] Version mapping recorded: Git tag (`proto-vX.Y.Z`), intended BSR label (`candidate` vs `stable`), Syntra Core version, package version (`syntra.v1`), and transport profiles covered.
- [ ] BSR module identity is approved and configured as `buf.build/tinklecorp/syntra` (repository variable `BSR_MODULE` must equal exactly this value — the publish workflow fails closed otherwise). **If the module is unset or mismatched, stop: publication is blocked.**
- [ ] Tag `proto-vX.Y.Z` created by a maintainer; tag protection rules enforced (`proto-v*` restricted).
- [ ] Release notes drafted from `CHANGELOG.md`: wire contracts, supported transports, migration notes, deprecation notices with removal versions.

## C. Publication (tag workflow)

- [ ] Publish workflow ran on the tag event only (never a branch push or manual local push).
- [ ] Re-validation inside the publish job passed (format, lint, build, breaking) before any network mutation.
- [ ] `buf push` succeeded for exactly the tagged revision; the BSR commit hash is recorded in the release notes.
- [ ] Correct label applied (`candidate` for `-rc` tags, `stable` for finals); labels move forward only.
- [ ] No `stable` label was moved to an older commit; if a rollback is ever needed, it is handled as a new forward release, not a re-point.

## D. Post-publication

- [ ] Downstream pinning verified: a clean-room consumer can `buf export` (or generate SDKs from) the published commit and reproduce the release's descriptor.
- [ ] Breaking baseline updated: CI's `--against` reference now points at the new stable commit (reviewed PR, never automatic).
- [ ] `CHANGELOG.md` finalized for the release; `Unreleased` reset.
- [ ] BSR token hygiene: no credential appeared in logs; rotation performed if any exposure is suspected.
- [ ] Announcement states the profile list covered (per `conformance/claims.md` wording rules), never a bare "Syntra compliant."
