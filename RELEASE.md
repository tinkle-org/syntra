# Syntra v1 Release Candidate — Release Process

This document defines how the repository is tagged as a Syntra v1 release
candidate, what is frozen at RC, how versions relate, and how release
artifacts are produced. It creates no new normative behavior; all rules
cite their owning specification or governance section.

> **Scope note (2026-10-27).** This repository returned to
> specification-first ownership: it publishes documents and schema
> provenance only, via release-please release PRs and `vX.Y.Z` tags (see
> `MIGRATION.md` §10). Language implementation gates and artifact
> publishing are out of scope for this repository. Sections below that
> describe retired implementation-era mechanics apply to the RC-1
> snapshot (`2a91da7`) and are retained as process history for that
> release.

Release authority: `GOVERNANCE.md` Sec. 5 (stability criteria),
`GOVERNANCE.md` Sec. 3 (approval quorum), `GOVERNANCE.md` Sec. 4 +
Deprecation (breaking/deprecation handling), `rfcs/README.md` (RFC
lifecycle — only **Accepted** RFCs may modify normative behavior),
`docs/schema-registry.md` (schema provenance and pinning contract),
`docs/schema-release-checklist.md` (per-schema-release gates).

Status terms: an RC is a **candidate**, not a stable release. Tagging an
RC asserts the checklist below holds; it does not assert two-implementation
conformance green (that is the stable-release bar per `GOVERNANCE.md`
Sec. 5). Known unresolved blockers MUST be listed in
`audits/v1-release-readiness.md` and MUST block promotion to stable.

### Accepted SC1 profile and release scope

[RFC 0007](rfcs/0007-secure-channel-device-authorization.md) and
[ADR-011](specifications/decisions/ADR-011-noise-device-authorization.md) are
accepted. `SNTR-SC1-WSS-V1` is an additional secure profile: canonical
`syntra.sc1.v1` context inside verified TLS 1.3 WSS at `/syntra/v1/sc1/ws`.
It does not change the baseline TLS requirements or the existing baseline
transport profiles. TCP and plaintext WS are restricted development carriers;
UDP is deferred and HTTP/HTTPS request-response is excluded from SC1. The
initial permitted topology is direct TLS termination by the host; proxy
termination is deferred.

The accepted first stable bundle is SC1/WSS, standardized recovery and
applicable mobile lifecycle evidence. Baseline transports remain independently
claimable but are not all required for the initial bundle. The Rust
implementation at `tinkle-org/syntra-rs` main (`50ca849`) implements the
reviewed proposal; its local evidence does not execute the registered
`CONF-SCW-*` cases or close independent interoperability, recovery, mobile,
topology or security-review gates. Host policy must independently verify root
identity, current enrollment and same-principal admission before `ready`.
Nil method authorization denies calls. There is no enrollment RPC or complete
issuance/storage/rotation workflow.

#### Recorded validation (2026-10-28)

The final implementation working-tree verification used Go 1.26.10 on
darwin/arm64, Apple M4, and records:

- Root pure-Go tests with CGO disabled, race tests and staticcheck passed;
  native-core race tests and staticcheck passed. Go 1.23.12 compatibility
  passed; it is a compatibility floor, not a production-security recommendation.
- Actual Docker adapter/core integration passed in **30.681s**, covering all
  six TCP/WS/WSS × bootstrap/returning groups with none skipped, including
  verified WSS and returning-mode Toxiproxy stalls/resets. High-level connection
  orchestration is covered by local unit tests, not those container cases.
- Reachable-vulnerability scans were zero for both root and integration
  modules on Go 1.26.10. This does not mean every dependency is advisory-free
  or that all build variants and the separately built fault proxy were scanned.
- Three 100ms in-memory benchmark samples at CPU settings 1 and 4 passed
  without failed samples. Timing is report-only, with no hard performance
  threshold; full Protobuf decode and RPCs are not zero-allocation.

See [verification evidence](docs/sc1-implementation.md#verification-evidence)
and [performance measurements](docs/perf-tradeoffs.md) for conditions and
limits. These results are implementation evidence, not a frozen release
attestation, independent SC1 wire interoperability or formal `CONF-*` verdicts.
Native-core linkage still uses the Go SC1 carriers.

Release promotion still needs the [remaining work](docs/sc1-implementation.md#remaining-work):
independent review, independent vectors/interoperability, accepted wire/policy
decisions and the applicable conformance declaration. Native ABI v1 lacks a
completion-timestamp input and explicit post-hello credential release; Go and
library cleanup do not guarantee erasure of all secret copies. Existing profile
passes, generation checks and document tags do not close these gaps. The
[SC1 conformance plan](conformance/plans/secure-channel.md) remains acceptance
planning; no new executable-profile release gate is implied by this record.

## 1. Release checklist (v1 RC)

The subsequent [mobile v1 delivery target](docs/mobile-v1-delivery.md) requires
SC1, standardized recovery and mobile lifecycle evidence for stable promotion.
Its selected proposals are RFCs 0006–0008 and the core decision set, not new
accepted profile gates. Before promotion, maintainers accept and activate the
owning contracts/cases, then review independent pure-Go/Rust results in both
roles, host lifecycle/security evidence, and iOS/Android lifecycle/operational
results from the [acceptance plan](conformance/plans/mobile-v1.md). Core-only
or same-implementation passes cannot satisfy this target. This supplement
does not retroactively change the historical RC-1 snapshot or claim completion.

[RFC 0009](rfcs/0009-v1-bootstrap-governance-and-release-scope.md) is accepted.
It establishes the WSS-first stable bundle, the bootstrap roster rule, and the
rule that a single-transport claim does not require a two-transport proof. The
two-transport proof is required only for a claim of transport independence
across two named transports. The [acceptance package](docs/v1-acceptance-package.md)
separates specification freeze from independent execution and stable
authorization. Acceptance does not waive any applicable bundle gate. Prerelease
configuration remains unchanged; structural validation alone does not authorize
stable promotion.

Check each box with evidence (command output, PR link, or reviewer sign-off).
An unchecked box blocks tagging **for the declared release scope**. The initial
stable bundle requires the SC1/WSS, recovery and mobile gates; it does not
require every baseline transport. Any additional transport named in a claim
must have its own applicable evidence. A baseline profile is never certified
by an SC1/WSS pass.

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
- [ ] Implementation gates pass (out of scope for this repository; owned by the separate language implementation projects) — not executed here
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
| Declared transport profiles | Every transport named in the release claim or bundle has an accepted spec and matching `conformance/profiles.yaml` ID. The initial bundle names SC1/WSS; baseline TCP/TLS/HTTP/HTTPS/WS/WSS are independently claimable and not all required. |
| Proto lint / breaking | `buf lint`, `buf build`, `buf breaking --against <stable baseline>` green (CI job `buf`) |
| Conformance requirements complete | `requirements.yaml` covers every defined ID; no `not_testable` without a stated reason (`validate-repo.py requirements manifests`) |
| Test vectors validated | `validate-repo.py vectors` green (hex parses, protobuf decodes against `proto/`, TCP lengths match, malformed vectors intentionally malformed) |
| Consistency audit no P0 | `audits/v1-consistency-review.md` P0 list empty or all P0s closed by Accepted RFCs; readiness report shows no BLOCKED area required for the RC scope |
| Implementation gates | Out of scope for this repository; owned by the separate language implementation projects (RC-1-era evidence rows below are process history) |
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

## 4. Tagging procedure (release-please release PR, then publish on merge)

`.github/workflows/release-please.yml` maintains a release PR that bundles
document changes into `CHANGELOG.md`. Review the complete release scope and
CI evidence before merging. Merging the release PR is what authorizes the
release; ordinary merges to `main` do not publish. The repository must
allow Actions to create PRs; approve the checks on bot-created PRs if
GitHub requires it before merging.

On merge, release-please tags `vX.Y.Z` (or increments the current
prerelease, e.g. `1.0.0-rc.1` → the next version per conventional commits)
and creates the GitHub Release with the CHANGELOG section as notes. Before
merging, reviewers must confirm every existing `[Unreleased]` entry has
been moved under the generated release entry (release-please proposes
this move in the release PR; do not merge while entries remain stranded
under `[Unreleased]`). This repository publishes no language artifacts;
language implementations pin schema revisions from here.

Recovery: rerun failed jobs. A maintainer may recreate a missing release
path using a new signed tag at an approved, merged commit:

```sh
git tag -s v1.0.0 -m "Syntra schema v1.0.0"
git push origin v1.0.0
```

Restrict `v*` tag creation to maintainers and the release
automation identity (historical `syntra-*-v*` crate-era tags keep their
existing protection). Deleting or moving a published tag is forbidden; fix
forward. The RC-1-era mechanics that follow in §§5–6 describe the retired
crate/Go release model and are retained as process history for that
release only.

## 5. Release artifacts

> Snapshot-scoped section (RC-1, `2a91da7`): the language artifacts below
> are process history for that release. Forward releases of this
> specification-first repository publish documents and schema provenance
> only.

The **syntra-core** RC-1 GitHub Release received this flat asset set:

- `image.json` — the `buf build` descriptor.
- `syntra-schema-<tag>.tar.gz` — `descriptor/` (descriptor and `buf export`
  sources), `manifests/`, and `test-vectors/`.
- `syntra-source-<tag>.tar.gz` — the full tracked source snapshot via
  `git archive`, including build scripts and schemas. Source archives do
  not vendor dependencies and do not promise offline builds.
- `CHANGELOG.md`, `RELEASE.md`, `GOVERNANCE.md`, `LICENSE` (as tagged).
- `SHA256SUMS` — checksums for exactly the uploaded assets other than itself.

Language artifact assets from that release (crate archives, Go-bindings
archive, native-ABI header distribution) are out of scope for this
repository going forward.

## 6. GitHub Release association (no BSR)

Snapshot-scoped section (RC-1, `2a91da7`): the crate-anchored tag pairing
below applied to that release. Forward releases of this specification-first
repository are tagged `vX.Y.Z` by release-please after a reviewed release
PR merge; they carry documents and schema provenance, not language
artifacts. There is no BSR module, `buf push`, or GHCR publication from
this repository. RC tags are marked prerelease; a tag alone never asserts
the protocol stability criteria in `GOVERNANCE.md` §5.
