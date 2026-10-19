# Syntra v1 Release Candidate — Release Process

This document defines how the repository is tagged as a Syntra v1 release
candidate, what is frozen at RC, how versions relate, and how release
artifacts are produced. It creates no new normative behavior; all rules
cite their owning specification or governance section.

Release authority: `GOVERNANCE.md` Sec. 5 (stability criteria),
`GOVERNANCE.md` Sec. 3 (approval quorum), `GOVERNANCE.md` Sec. 4 +
Deprecation (breaking/deprecation handling), `rfcs/README.md` (RFC
lifecycle — only **Accepted** RFCs may modify normative behavior),
`docs/schema-registry.md` (BSR publication contract),
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
- [ ] Conformance requirements complete
- [ ] Test vectors validated
- [ ] Consistency audit has no P0 blockers
- [ ] BSR publication ready
- [ ] License approved
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
| BSR publication ready | `docs/schema-registry.md` §1 module identity approved (no placeholder); `buf push --dry-run` semantics verified; publish workflow gates pass |
| License approved | `LICENSE` file added by maintainers per `GOVERNANCE.md` Sec. 7 |
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

## 4. Tagging procedure (maintainers only; no auto-tagging)

CI MUST NOT create tags. A maintainer creates the tag after the checklist
(§1) is fully evidenced and `audits/v1-release-readiness.md` is updated:

```sh
git tag -s v1.0.0-rc.1 -m "Syntra v1.0.0-rc.1 (release candidate, not stable)"
git push origin v1.0.0-rc.1
```

Rules: annotated (preferably signed) tags only; tag names `vX.Y.Z` for
candidates and finals, with `-rc.N` suffix for prerelease rounds
(`v1.0.0-rc.2`, …); branches never define releases (`GOVERNANCE.md`
Sec. 5). Tag protection rules SHOULD restrict tag creation to
maintainers. Deleting or moving a release tag is forbidden; fix forward
with a new tag.

## 5. Release artifacts

For each RC tag, `scripts/collect-release-artifacts.sh <tag>` assembles
(never publishes; no tagging inside):

- `descriptor/` — `buf build -o descriptor/image.json` (FileDescriptorSet
  of exactly the tagged revision) plus `buf export` tree for inspection.
- `manifests/` — copy of `conformance/manifest/*.yaml` at the tag.
- `test-vectors/` — copy of `conformance/test-vectors/` at the tag.
- `CHANGELOG.md`, `RELEASE.md`, `GOVERNANCE.md` (as tagged).
- `SHA256SUMS` — checksums for every file above, generated locally.

Artifacts live under `dist/release/<tag>/` (gitignored; reproducible on
any checkout of the tag). Checksums are the integrity contract for
downloadable artifacts; the tag + checksums together define the RC.

## 6. BSR release association (prepared, not executed)

`buf push` runs only via `.github/workflows/schema-publish.yml`, which
requires ALL of: a schema tag event, `BSR_MODULE` equal to exactly
`buf.build/tinklecorp/syntra`, and manual approval of the `bsr-publish`
environment holding the least-privilege `BUF_TOKEN`. See
`docs/schema-registry.md` §§1, 8–10 and `docs/schema-release-checklist.md`
§B–C.

Tag namespaces are distinct by design: repository releases use
`vX.Y.Z` (§4 above); schema publication follows `proto-vX.Y.Z` tags
(see `docs/schema-registry.md` §1; the `proto-v*` trigger and label
mapping live in the publish workflow). A schema publication tag is cut
only after the repository RC checklist (§1) holds for the schema scope
AND the publication policy RFC is accepted. Association rules: Git tag
`proto-vX.Y.Z` ↔ BSR commit in `buf.build/tinklecorp/syntra`; release
identity via BSR labels (`candidate` for `-rc` tags, `stable` for
finals); labels move forward only. Post-publish, the workflow verifies
public module access and generated-SDK availability read-only (no
credentials echoed; see workflow `verify` job). The preflight gate pins
the exact approved module and fails closed on anything else — by design.
