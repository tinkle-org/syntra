# Syntra v1 Release Candidate — Release Process

> **Proposed change:** the release procedure in this branch is pending public
> approval of [RFC 0011](rfcs/0011-specification-release-versioning.md).
> The current process on `main` remains authoritative until acceptance.

This document defines how the repository is tagged as a Syntra v1 release
candidate, what is frozen at RC, how versions relate, and how release
artifacts are produced. It creates no new normative behavior; all rules
cite their owning specification or governance section.

> **Scope note (2026-10-27).** This repository returned to
> specification-first ownership: it publishes documents and schema
> provenance only, via maintainer-authorized `vX.Y` tags (see
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

## Accepted SC1 profile and release scope

[RFC 0007](rfcs/0007-secure-channel-device-authorization.md),
[RFC 0010](rfcs/0010-sc1-host-authorization-lifecycle.md) and
[ADR-011](specifications/decisions/ADR-011-noise-device-authorization.md) are
accepted. `SNTR-SC1-WSS-V1` is an additional secure profile: canonical
`syntra.sc1.v1` context inside verified TLS 1.3 WSS at `/syntra/v1/sc1/ws`.
It does not change the baseline TLS requirements or the existing baseline
transport profiles. TCP and plaintext WS are restricted development carriers;
UDP is deferred and HTTP/HTTPS request-response is excluded from SC1. The
initial permitted topology is direct TLS termination by the host; proxy
termination is deferred.

The accepted first stable bundle is SC1/WSS, standardized recovery and
applicable mobile lifecycle evidence (Option A per
[RFC 0006](rfcs/0006-update-recovery-profile.md) §11.1: recovery cannot be
omitted from that bundle and relabeled as optional; a Core-only pass is not
sufficient evidence for the recovery-inclusive bundle). SC1 includes the
export of the accepted host lifecycle obligations of
[RFC 0010](rfcs/0010-sc1-host-authorization-lifecycle.md)
(`SNTR-DAUTH-011`–`024`) with its registered, planned-not-executed
`CONF-SCW-025`–`042` rows. Baseline transports remain independently
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
independent review, independent vectors/interoperability and the applicable
conformance declaration; the wire/policy decisions are accepted (Decisions
0001/0002), so the remaining items are executed evidence, not contract
decisions. Native ABI v1 lacks a
completion-timestamp input and explicit post-hello credential release; Go and
library cleanup do not guarantee erasure of all secret copies. Existing profile
passes, generation checks and document tags do not close these gaps. The
[SC1 conformance plan](conformance/plans/secure-channel.md) remains acceptance
planning; no new executable-profile release gate is implied by this record.

## 1. Release checklist (v1 RC)

The subsequent [mobile v1 delivery target](docs/mobile-v1-delivery.md) requires
SC1, standardized recovery and mobile lifecycle evidence for stable promotion.
Its contract set is RFCs 0006–0008 and the core decision set, accepted via
Decision 0002. Before promotion, maintainers review the activated
owning contracts/cases, independent pure-Go/Rust results in both
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
authorization. Acceptance does not waive any applicable bundle gate. Candidate
releases remain distinct from stable promotion; structural validation does not authorize
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
- [ ] Release workflow ready to tag the authorized commit (tag-only: no packages, archives, or GitHub Releases)
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
| CHANGELOG updated | A section for the exact proposed tag; every wire-affecting change has migration notes |

### Specification freeze at pinned revision

A stable release MUST pin the exact accepted specification revision it
claims: the accepted RFC set and ADR-011, the owning specification documents,
`conformance/manifest/*` and `conformance/profiles.yaml` at one repository
revision, and the conformance suite at that same revision. Release notes and
claims MUST cite these revision SHAs. A release prepared against a revision
that cannot be reproduced to these pins is not freeze-complete, and any
post-pin behavior change requires renewed approval of the affected scope (see
`docs/decision-record-template.md` §Compatibility and activation).

### Production-release evidence gates (stable promotion)

The following rows are required for a **production/stable release**, distinct
from the structural RC boxes above — registration is not execution, and
registered, not-executed rows never substitute for these:

- [ ] Executed `CONF-SCW` rows, including the RFC 0010 lifecycle rows
      `CONF-SCW-025`–`042` (enrollment authority including the equivalent
      out-of-band path `039` and the valid-but-unauthorized cross-principal
      and out-of-scope rows `040`/`041`, AK/handle issuance, staged
      provisioning and idempotency, pre-`ready` sequence and principal
      binding including mid-connection rebinding `042`,
      revocation enforcement/bounded staleness/fail-closed, rotation
      and epoch integrity, compromise recovery, disposal hygiene, pin
      rotation), in both roles, with per-case verdicts and logs
- [ ] Executed recovery cases (`CONF-URP-*`): fresh-handle rounds, scoped
      generation fencing, local overflow isolation, snapshot install,
      same-G install and durable progress/crash cuts
- [ ] Both-role independent results (Rust + Go): Go initiator/Rust host and
      Rust initiator/Go host; FFI-backed Go is not the independent Go lane
- [ ] Independently derived Noise ciphertext vectors (not implementation
      self-generated fixtures), covering both bootstrap and returning modes
- [ ] Mobile gates: supported iOS/Android lifecycle/operational evidence from
      [conformance/plans/mobile-v1.md](conformance/plans/mobile-v1.md),
      including destination/resource budgets and declared operational bounds
- [ ] Independent human security review (crypto/composition review of SC1,
      the RFC 0010 lifecycle and recovery persistence) recorded per
      `GOVERNANCE.md` Sec. 3
- [ ] Specification freeze at the pinned revision recorded per the freeze
      subsection above

### Claims wiring rule

Release notes, claims and declaration summaries MUST be generated from
executed registered cases at the pinned revision — the cited case IDs MUST
exist in `conformance/manifest/*` at that revision and carry executed
verdicts. Asserted-in-advance results, planned-only rows, and structural or
implementation-local evidence MUST NOT be rendered as release claims.

## 2. Version freeze (RC)

> **Historical RC-1 snapshot — non-normative.** Everything in this section
> records the retired RC-1 implementation-era freeze at `2a91da7` as process
> history only. It carries no current normative force. Formerly open
> behaviors are superseded by the accepted contracts of
> [Decision 0002](docs/decisions/0002-sdd-acceptance-wave.md): request-ID
> ordering/non-reuse is governed by
> [RFC 0004](rfcs/0004-correlation-identity-carriage.md) (strictly increasing
> IDs in serialized emission order, no reuse for the lifetime of the
> persistent connection, host high-water rule, fail-close on non-increasing
> IDs), pre-`ACTIVE` failure carriage by
> [RFC 0003](rfcs/0003-handshake-failure-signaling.md), and the 1 MiB
> total-frame bound by [RFC 0005](rfcs/0005-negotiation-bounds-identifiers.md)
> D3. Do not implement from this section; cite the accepted owner
> specifications.

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

Frozen `request_id` semantics (RC-1 historical text; superseded by accepted
RFC 0004 — see the section header above): `uint64` connection-scoped
correlation; nonzero initiator-chosen, unique among outstanding RPCs on the
connection; `0` reserved for `hello`/`ready`/`notification`; reuse only
after the terminal `result` (stale-reuse conflict tracked as P0 finding
F-02, resolution via RFC 0004 — the freeze records current text, not a
resolution). The accepted contract (RFC 0004 D1/D2, Decision 0002) replaces
this RC-1 text: strictly increasing IDs in serialized emission order, no
reuse during the lifetime of the persistent connection, a lasting host
high-water mark, and fail-close on non-increasing request IDs.

Frozen capability identifiers (placeholders pending the events RFC;
MUST NOT be advertised until the RFC is accepted):
`events-v1`, `events-replay-v1`; resumption token `resume-v1` (no RFC
exists; only resume-rejection is mandatory).

Known RC exceptions (historical RC-1 status; disposition per accepted
[Decision 0002](docs/decisions/0002-sdd-acceptance-wave.md), 2026-10-30):
F-01 (profile identifier spellings), F-03 (pre-ACTIVE error carrier) and
F-04 (HTTP per-exchange ID amnesia) were resolved by accepted
[RFC 0003](rfcs/0003-handshake-failure-signaling.md) and
[RFC 0004](rfcs/0004-correlation-identity-carriage.md); F-02 (stale ID
reuse) was resolved by accepted RFC 0004 D1/D2; F-06 (1 MiB payload fixture
vs envelope bound) was resolved by accepted RFC 0005 D3. F-05 (private
`go_package` path) is explicitly deferred, not a blocker for this
documentation-provenance scope: it is a Protobuf FILE/source break
requiring downstream `syntra-go` confirmation and coordinated release
ordering, tracked as the RFC 0005 D5 follow-up.
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

## 4. Tagging procedure (manual, authorized publication)

This procedure is proposed by RFC 0011 (Discussion) and is not yet active.
Until acceptance, `.github/workflows/release-please.yml` and its configuration
remain the active publisher. On acceptance the workflow tags only
when RFC 0011 is marked Accepted on trusted `main`; that status must
follow an actual public maintainer decision, not a bot or this document. There
are no packages, archives, or GitHub Releases: the Git tag is the release.

### Administrative setup

1. Create the GitHub environment `spec-release`. Require a reviewer from the
   active maintainer roster (individual users, not teams) and select **only**
   the branch `main` under its
   custom deployment branch policies. With exactly one active maintainer,
   leave prevent-self-review disabled. The workflow checks these settings;
   GitHub's automatic creation of an unprotected environment is insufficient.
2. Store `SPEC_RELEASE_TOKEN` as an **environment secret**, not a repository
   or organization secret. Use a dedicated narrowly scoped repository token
   with contents write permission and permission to create `v*` tags. Validation
   jobs have only read access and do not receive
   this secret. Rotate it on suspected exposure.
3. Protect `main` and the `v*` tag namespace with appropriate rulesets:
   restrict creation to maintainers and the publishing identity, prohibit
   movement/deletion, and require the repository checks on PRs. Verify the
   publishing identity works with the rulesets. Enable immutable releases or
   tag protections for future tags where available.

### Prepare and authorize

Prepare a release PR containing the reviewed scope and a nonempty
`CHANGELOG.md` section whose heading is `## [<tag>]` exactly matching the tag
you will dispatch — for example `## [v1.0]` or `## [v1.0-rc1]` (the publisher
enforces exactly one matching section). Merge it, freeze
the exact resulting full commit SHA, and collect the evidence required for
its scope. The initial stable bundle retains RFC 0009's independent Go/Rust,
SC1, recovery, mobile and independent security-review gates. An RC does not
assert those stable gates passed.

Open a public issue or PR containing these unique, single-line fields. Use
the exact tag and full commit; describe any pending candidate evidence
honestly. Stable `Freeze`, `Evidence`, and `Security` fields must be HTTPS
links to the actual records. The maintainer reviews the linked contents,
including applicable profiles, case results and unresolved objections.

```text
Release-Tag: v1.0-rc1
Release-Commit: <full-commit-sha>
Release-Scope: <declared scope and profiles>
Release-Freeze: <freeze record or candidate status>
Release-Evidence: <evidence links or candidate limitations>
Release-Security: <security review link or candidate limitations>
Release-Objections: <none or resolution links>
Release-Self-Review: yes
```

After saving the final body, run the following with an authenticated `gh`
session and post its output as a **separate comment** on that issue or PR:

```sh
GITHUB_TOKEN="$(gh auth token)" python3 scripts/spec-release.py approval --issue 42 --tag v1.0-rc1 --target <full-commit-sha>
```

The comment binds the approving account, tag, commit and SHA-256 of the exact
decision body. Editing that body invalidates earlier approvals. With one
active maintainer one approval suffices; with two or more, two distinct
active maintainers must comment. To object, an active maintainer posts exactly
`SYNTRA-OBJECT <tag> <full-commit-sha>`; their later valid approval resolves
that structured objection. Reviewers must also check ordinary discussion:
automation cannot identify every unstructured objection or assess evidence.

### Tag and recover

Manually dispatch `.github/workflows/spec-release.yml` on `main` with the
tag, full target SHA, decision issue number, and `recovery=false`. After the
read-only validation succeeds, approve the protected environment. The
publisher rechecks the RFC status, current main revision, maintainer roster,
environment protections, public approvals, tag identity and changelog section
before creating the tag. The workflow does not execute target scripts with
release credentials. RC status lives in the tag suffix and changelog; there is
no separate prerelease flag or latest-release marker.

If publication stops after tag creation, investigate and rerun the same
authorized version and commit with `recovery=true`. Recovery only accepts an
existing tag pointing directly to the same approved commit. It never moves a
tag. Tag
protection and independent maintainer review of evidence are administrative
and human controls, not guarantees provided by the script.

The RC-1-era mechanics in §§5–6 are historical only.

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

## 6. Tag association (no BSR, no GitHub Releases)

Snapshot-scoped section (RC-1, `2a91da7`): the crate-anchored tag pairing
below applied to that release. Forward releases of this specification-first
repository use maintainer-authorized `vX.Y` tags; they carry documents and schema provenance, not language
artifacts. There is no BSR module, `buf push`, or GHCR publication from
this repository. RC status lives in the `-rcN` tag suffix; a tag alone never asserts
the protocol stability criteria in `GOVERNANCE.md` §5.
