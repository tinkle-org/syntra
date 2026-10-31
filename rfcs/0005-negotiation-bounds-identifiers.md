# RFC 0005: Negotiation binding, bounds, and identifiers

- RFC: 0005
- Title: RFC-defined post-ACTIVE profile negotiation, concrete bounds, stable profile IDs, and downstream Go package identity
- Status: Accepted for the protocol contract (closes findings F-01, F-06, F-11, F-12, F-17, F-18 at the specification level); D5 Go migration deferred
- Date: 2026-10-28
- Target version: pre-stable v1 contract proposal plus RFC-defined optional profiles; explicit freeze/version and FILE/source-break decisions required (§6)
- Relates to: `specifications/core/capabilities.md`, `rpc.md`, `framing.md`, `authentication.md`, `sessions.md`, `errors.md`, `events.md`, core/security open questions, transport profile identifiers, `proto/syntra/v1/*.proto` (`go_package`), schema generation/compatibility, `conformance/profiles.yaml`, `claims.md`; RFC 0001 B7/B8; RFC 0002 §10 items 4–11; RFC 0006
- Author(s): oscarlaw
- Reviewers: oscarlaw (self-review disclosed; sole active maintainer)

> Accepted via [Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)
> (2026-10-30) for the protocol contract recorded below, per the Status line;
> D5 (Go migration) remains deferred. This notice replaces the historical
> Draft-proposal caveat, which described only the pre-acceptance review state
> and no longer limits authority. Later changes remain subject to
> [governance](../GOVERNANCE.md) and the [RFC process](README.md).

## 1. Summary

Select RFC-defined post-ACTIVE profile negotiation through ordinary RPCs, with
RFC 0006 providing the Update/Recovery binding required for the release target.
Select concrete byte/resource bounds, keep the existing matching transport
profile identifiers, and propose a Go package option matching the downstream
Go repository layout. A release requiring recovery cannot be satisfied by
closing negotiation as mandatory-only with no binding. Mandatory-only peers
still interoperate at the core baseline; absence of recovery is not sufficient
for this release target.

## 2. Motivation

The core describes explicit capability confirmation but supplies no universal
wire advertisement channel. RFC 0006 defines one bounded, versioned
recovery negotiation RPC after ACTIVE; treating all negotiation as deferred
would leave the required recovery release contract impossible to complete.
Generic probing without an accepted binding would be equally ambiguous.

Several field limits have no concrete values, the concurrency floor has an
unbound negotiation escape, and fixtures ask for a 1 MiB payload inside a
1 MiB encoded envelope. These are different measurements. The old profile-ID
finding is stale: current transport documents and `conformance/profiles.yaml`
already match `SNTR-HTTP-V1`, `SNTR-WS-V1`, and `SNTR-WSS-H1-V1`.

The Go package option also needs to match the actual downstream module/output
layout rather than a removed in-tree binding path. Schema publication to BSR
is retired; importing from a published BSR module is not a release acceptance
condition. Remote generator use is a separate downstream tooling dependency.

## 3. Selections

All obligations below are accepted text (Decision 0002), with existing IDs tracing
the owning clauses; later changes go through the RFC process.

### D1 — Select RFC-defined post-ACTIVE profile negotiation

The selected binding model is a profile-specific ordinary RPC after ACTIVE,
not a new handshake field/variant and not a generic capabilities enumeration
method. A profile's accepted RFC defines its exact method, versioned payloads,
bounds, confirmation, unknown-input handling, and failure/fallback contract.
Only that defined negotiation call is exempt from prior confirmation of its
own profile; no other unconfirmed profile operation is permitted.

For the required Update/Recovery release target, select the binding defined
by [RFC 0006](0006-update-recovery-profile.md):

- Method `/syntra.v1.UpdateRecovery/Negotiate`, capability
  `syntra.update-recovery/1`, `RecoveryNegotiateRequest` and
  `RecoveryNegotiateResponse` inside existing request/result payloads.
- RFC 0006 offers `profile_version=1` and `min_version=max_version=1`;
  the host selects the greatest supported version in the offered range and
  explicitly confirms selected version and bounded parameters for this
  connection and bound principal. No overlap returns `FAILED_PRECONDITION` in
  a lawful RPC result; an unknown negotiation method returns `UNIMPLEMENTED`.
- Only validated confirmation enables recovery operations. Unknown or declined
  profile support leaves mandatory-only interoperability available, without
  falsely claiming recovery support. For this release target, the application
  reports recovery unavailable and does not treat fallback as successful
  recovery. A missing or unaccepted RFC 0006 blocks that release target.
- Confirmation does not resume a session, enable another connection, authorize
  a different principal, or negotiate a lower baseline security/resource floor.
  Profile bounds cannot override core/frame/profile hard limits implicitly.

RFC 0006 is accepted ([Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md)):
its method/identifier/messages may be confirmed and used only through the
profile's own negotiation RPC; there is no general advertisement channel, no
invented `Capabilities` method, no hello extension list,
and no optional-frame probe. A future generic negotiation binding requires
its own accepted contract. RFC 0006's optionality at the core layer and the
release target's requirement for recovery are distinct decisions; registration
of its cases is not execution, and conformance verdicts await executed evidence.

### D2 — Select concrete bounds and defaults

KiB/MiB below mean powers of 1024. These are accepted protocol ceilings/floors,
not schema-enforced annotations. Producers check before sending; receivers
bound before allocation/dispatch and enforce the same units.

| Item | Selected bound | Owning existing clause / scope |
|---|---|---|
| Encoded envelope | Default maximum 1,048,576 bytes of the complete serialized `Frame` | SNTR-WIRE-006, SNTR-SER-006; payload plus envelope overhead, not payload alone |
| Initial credential | Maximum 8 KiB (8,192) raw credential bytes | SNTR-AUTH-003/030, SNTR-SER-020, SNTR-ASEC-040; HTTP counts decoded bytes |
| `ServerReady.connection_id` | Maximum 128 UTF-8 encoded bytes | SNTR-HS-004, SNTR-SESS-002, SNTR-ASEC-010; diagnostic only, fresh ≥128-bit entropy remains required |
| `RpcError.message` | Maximum 4 KiB (4,096) UTF-8 encoded bytes | SNTR-ERR-003/020/021; public diagnostic text, never a bulk-data channel |
| RPC concurrency | Support at least 16 concurrent RPCs, with a documented bounded maximum ≥16 | SNTR-RPC-008; no negotiation below the floor; HTTP listener endpoint-group specialization retained |
| Graceful close | Default 5 seconds, configurable 0–30 seconds inclusive, hard maximum 30 seconds | SNTR-HS-006/013 and owning transport close rules; zero explicitly means immediate teardown, not unbounded grace |
| Method string | Keep the owning existing bound: canonical method fitting the serialized envelope, plus any documented deployment cap | SNTR-RPC-001, rpc §1C, SNTR-WIRE-006; no competing universal method-length number invented here |

Credential bounds apply to bytes, not base64 text length: 8,192 raw bytes expand
to 10,924 base64 characters, or 10,931 bytes for the `Syntra ` scheme plus value,
before the HTTP header name/framing. HTTP/HTTPS header budgets and intermediary
configuration need to accommodate this expansion plus other required headers
to support the selected raw ceiling. SNTR-HTTP-113 currently recommends 8 KiB
per header field and 16 KiB total, with a separate default decoded credential
ceiling of 64 KiB. This RFC replaces that decoded ceiling with 8 KiB and
requires adjusting the Authorization field allowance above its current 8 KiB
recommendation; otherwise a maximum-size raw credential cannot fit. Total
headers remain separately bounded and deployment-documented, not silently
unlimited. Shape and encoded-size checks precede bounded base64 decode, and
decoded length is checked before auth policy.
Anonymous empty credentials keep their existing meaning. Profile/carrier rules
and confidentiality are reconciled by [RFC 0004](0004-correlation-identity-carriage.md).

UTF-8 byte limits are not character counts. Producers emit valid bounded text;
public diagnostic truncation, if needed, stays on a UTF-8 boundary. Receivers
reject an oversized field; they do not silently truncate peer credentials or
connection IDs. An existing smaller native carrier limit still applies: a
4 KiB diagnostic ceiling does not permit a 4 KiB WebSocket Close reason.
No new diagnostic field or right to echo raw input is created.

The concurrency floor is supported capacity, not immunity from documented
rate/queue/principal admission control. Recovery may choose a stricter profile
pending-call maximum only while the aggregate core implementation still supports
the ≥16 baseline; it cannot negotiate a core maximum below 16. Grace begins
when new work is stopped and close is initiated, uses an absolute bounded
deadline, and is not restarted by pending writes or control frames. Fatal
protocol/security failures may tear down immediately; the grace does not delay
fail-close or extend existing RPC deadlines. RFC 0008 will coordinate complete
queue/write/suspend timing; acceptance must align its contract with this cap.

### D3 — Measure frame boundaries on encoded bytes

Select fixtures sized to the largest payload fitting an otherwise fixed legal
`Frame`, including tags, lengths, version, nonzero request ID, method, timeout,
and nested wrappers. Exactly-MAX (1,048,576) encoded bytes is within the default
size bound; MAX+1 is rejected before dispatch. A 1 MiB payload plus overhead is
oversized. Payload shape/content remains opaque, including empty and non-UTF-8.

The TCP four-byte length prefix, TLS record framing, WS framing, and HTTP
headers are not part of serialized `Frame` size. Their own independent
bounds still apply. WS counts assembled/decompressed message bytes; HTTP body
contains the full frame. Unknown well-formed fields count toward encoded size
even when ignored semantically. No fixture silently raises the default ceiling.

### D4 — Preserve the current matching profile IDs

Keep `SNTR-HTTP-V1`, `SNTR-WS-V1`, and `SNTR-WSS-H1-V1` exactly as currently
spelled in the owning specs and `conformance/profiles.yaml`. TCP, TLS/TCP, and
HTTPS/H1/H2 identifiers also stay as registered there. The acceptance task is
to verify byte-for-byte agreement in specs, declarations, and claim tooling,
not to rename already-matching identifiers or add aliases. An eventual new
HTTP/WS binding needs a separately reviewed identity, not reinterpretation of
an existing ID. Requirement IDs and profile IDs remain separate namespaces.

### D5 — Match Go package identity to downstream ownership

Select this proposed option for the existing public schema files when a schema
change is authorized after acceptance:

```proto
option go_package = "github.com/tinkle-org/syntra-go/gen/syntra/v1;syntrav1";
```

The intended downstream module is `github.com/tinkle-org/syntra-go`, with generated
files in that repository's `gen/syntra/v1/` directory, imported as
`github.com/tinkle-org/syntra-go/gen/syntra/v1` with package name `syntrav1`.
With the documented source-relative recipe, the downstream output root is `gen`
and the logical schema path is `syntra/v1/*.proto`; no extra `proto/` or
`bindings/go/` segment is introduced. Actual module ownership/layout and import
tests still require downstream-owner confirmation before acceptance. This is
an ecosystem import path, not a private service or runtime protocol dependency.

This repository continues to own only authoritative schemas, documentation,
and validation. It neither restores an in-tree `bindings/`/`gen/` directory
nor owns generated language artifacts. Downstream projects regenerate with the
recorded pins and review source/import changes. No `.proto` file, baseline,
generation template, or generated output is changed by this acceptance.

The option change is FILE/source-breaking even if Protobuf wire fields remain
identical. Review it against both the current initial FILE baseline and the
recorded historical break; the historical break does not excuse a new one.
Keep the gate and immutable baseline intact pending the explicit compatibility
decision. There is no BSR schema-publication, BSR import dry-run, registry
identity, or external publishing requirement. Any stale support/contribution
links need an actual maintainer-owned destination in a separately scoped
follow-up, not a fabricated neutral organization or publication workflow.

## 4. Detailed design

```text
Initiator                                      Host
    |--- hello --------------------------------->|
    |<-- ready ----------------------------------| ACTIVE
    |--- request{UpdateRecovery/Negotiate, v1} --->| accepted RFC binding only
    |<-- result{selected v1, confirmed bounds} ----|
    |--- confirmed recovery operations ---------->|
    |    no confirmation: core still available,   |
    |    required recovery target not satisfied   |
```

Negotiation is an ordinary valid nonzero-ID call subject to core correlation,
deadlines, authorization, concurrency, and envelope bounds. Its only exception
is the accepted profile's explicit pre-confirmation negotiation permission.
RFC 0006 owns parameter-specific ranges and version/unknown-field handling;
this RFC does not define a second negotiation schema or relax those ranges.
No malformed or unknown profile bytes are inferred to mean confirmation.
Ordinary unknown envelope fields retain existing serialization rules; unknown
body variants are not capability advertisements.

Bounds failures keep lawful scope: oversize hello or `ready` terminates the
handshake with a local typed cause/native failure as accepted in [RFC 0003](0003-handshake-failure-signaling.md);
there is no zero-ID error carrier. An oversized public diagnostic is rejected
as a protocol validation failure, with no reflected error storm. A valid
nonzero-ID request exceeding a call resource limit can receive
`RESOURCE_EXHAUSTED` once, while pre-dispatch HTTP header/body rejection uses
its native `431`/`413` table. Oversized decoded credential maps to local
`RESOURCE_EXHAUSTED`; the HTTP binding rejection uses `431` without a
Syntra envelope, whereas malformed base64 retains `401` handling. Acceptance
would align the oversize-parameter wording in SNTR-HTTP-061 with the `431`
decoded-size rule in SNTR-HTTP-113; a present empty parameter remains `401`,
not an anonymous attempt. That reconciliation needs explicit profile review.
Whole-frame overflow is checked before dispatch, even when a field-specific
ceiling would otherwise permit the value.

After acceptance, owning edits would cover core capability/field/grace clauses,
HTTP header/decoded-credential checks, size fixture wording, claim consistency,
and the separately approved Go option migration. There is no permission here
to modify specs, schemas, manifest requirement ownership, or release claims in
advance of that acceptance.

## 5. Alternatives considered

1. **Mandatory-only release with no negotiation binding.** Rejected for this
   release target: recovery is required. It remains a valid minimal core peer
   mode, not completion of the recovery release acceptance criteria.
2. **Generic capability probing or new hello fields now.** Rejected: no accepted
   method/payload or pre-ACTIVE carrier exists. RFC 0006's exact post-ACTIVE
   binding is narrower and supplies the needed version/confirmation semantics.
3. **Raise the frame ceiling to fit a 1 MiB payload.** Rejected: changes DoS
   budgets and every transport boundary. Correct the measurement instead.
4. **Rename HTTP/WS IDs to H1-explicit aliases.** Rejected: the current strings
   already match. Renaming adds claim/source churn without resolving a conflict.
5. **Keep removed in-tree Go paths or require BSR publication.** Rejected:
   inconsistent with downstream ownership and the retired publication model.
6. **Do nothing.** Rejected: leaves required recovery unbound and resource/source
   compatibility decisions to implementation accident.

## 6. Compatibility

Retaining current profile IDs and correcting payload-versus-frame measurement
do not change bytes. Numeric credential/text caps, a non-negotiable concurrency
floor, and bounded grace can reject or alter behavior previously allowed by
draft/deployment policy. Required recovery for a release is a stronger release
selection than core optionality; it does not silently make recovery mandatory
for every v1 peer. RFC 0006's envelope-neutral negotiation alone does not
prove all recorded baseline changes compatible.

Maintainers must explicitly record the pre-stable v1 contract freeze/version
decision and downstream impact inventory. If existing frozen behavior is
incompatible with the selected bounds/semantics, governance §4 requires a
major-version decision and migration, not a claim of inherent clarification
compatibility. Optional profile evolution follows its own accepted versioned
binding and core fallback contract; it cannot relax baseline hard limits.

D5 independently needs a reviewed FILE/source-break disposition, downstream
regeneration/import migration, and release ordering. If a pre-stable change is
authorized, record that decision explicitly; if a supported frozen source
contract is broken, follow the breaking-version process. Do not weaken Buf FILE
checks or replace baselines to hide the break. `MIGRATION.md`/`CHANGELOG.md` and
schema compatibility documentation are accepted-follow-up work, not changed
here. Reserved field numbers/names and wire types remain untouched.

## 7. Security considerations

Bound raw bytes before auth policy and allocation, including encoded and decoded
HTTP credential sizes. No caller gets a larger allowance by base64 encoding,
compression, ciphertext, unknown fields, or a profile's opaque payload. Credential
and diagnostic limits do not authorize logging or disclosure. UTF-8 byte limits
avoid multi-byte character expansion surprises; smaller transport control limits
remain effective.

Post-ACTIVE negotiation runs over the permitted secure transport and bound
principal, with per-connection confirmation and no assumed recovery support or
silent downgrade claim. It is not resumption, channel binding, or proof of
application commit. Queue, concurrency, and grace bounds remain independently
enforced; saturation never justifies unbounded profile state. Downstream package
identity needs real ownership and supply-chain review; no private infrastructure
or schema registry publication becomes a protocol trust requirement.

## 8. Test plan and acceptance criteria

Binding evidence only: this acceptance makes no behavioral PASS or new
conformance claim (registration is not execution). Existing traces locate
affected coverage; RFC 0006's accepted registered cases require executed
conformance evidence before any verdict.

| Existing requirement trace | Planned positive/negative evidence |
|---|---|
| SNTR-CAP-001/002/003/010/011/020/021/900/901 | Accepted RFC-defined negotiation after ACTIVE, explicit confirmation, no generic probe, per-connection isolation, unsupported method and version mismatch, mandatory-only interop; lack of recovery fails release-target readiness rather than core interop |
| SNTR-AUTH-003/030, SNTR-SER-020, SNTR-ASEC-040/900, SNTR-HTTP-060/061/062/113/900 | Raw credentials at 8,192 and 8,193 bytes; absent-header anonymous attempt versus present empty parameter; HTTP base64 expansion, field cap and total-header cap; reject overflow before auth policy, without credential echo |
| SNTR-HS-004/900, SNTR-SESS-002, SNTR-ASEC-010/900, SNTR-SER-007 | `connection_id` at 128/129 UTF-8 bytes, multi-byte boundaries, invalid UTF-8, fresh diagnostic-only identity, no zero-ID rejection result |
| SNTR-ERR-003/020/021/900, SNTR-SER-007 | Public diagnostic at 4,096/4,097 UTF-8 bytes; invalid UTF-8; no secret/raw-input reflection; smaller native Close reason cap still enforced |
| SNTR-RPC-001/008/900, SNTR-HTTP-072, SNTR-WS-100, SNTR-WSS-100 | Canonical methods under owning envelope/deployment bound; ≥16 supported concurrent calls with out-of-order completion; excess rejection at documented maximum; no negotiated below-floor mode |
| SNTR-HS-006/013/900, SNTR-TLS-010, SNTR-WS-080/082 | Grace default 5 s, explicit 0 and 30 s, reject out-of-range config; stop new work, bounded drain, no timer restart on writes, exactly one local terminal outcome with RFC 0004/0008 |
| SNTR-WIRE-006, SNTR-SER-006, SNTR-RPC-900, SNTR-OPQ-006/900, SNTR-HTTP-900, SNTR-WS-900, SNTR-WSS-900 | Exactly-MAX/MAX+1 total encoded frame across profiles, largest fitting payload and overhead variants, unknown-field bytes counted, no payload-only 1 MiB acceptance |
| SNTR-HTTP-006, SNTR-WS-004, SNTR-WSS-004, SYN-ARCH-050 | Specs/manifest/declarations/claim tooling use the existing exact IDs, no aliases or accidental rename |
| SYN-ARCH-001/062, existing schema FILE gate | Inspect actual downstream Go module and source-relative output layout; pinned downstream generation/import build; mechanical FILE/source diff and explicit compatibility disposition, no BSR publication test |

- [ ] RFC 0006 accepted, its complete bounded negotiation/recovery contract and
  independent evidence recorded, and recovery required for this release target.
- [ ] Protocol/security reviewers validate raw/encoded limits and native failure
  mappings, especially HTTP credential overflow and WS Close text size.
- [ ] RFC 0008 queue/suspend semantics aligned with grace and terminal failure flow.
- [ ] At acceptance, revise owning requirements/cases and migration records;
  verify independent implementations or governance's bootstrap alternative.
- [ ] For the later schema option change: separate Buf format/lint/build/FILE
  checks, reviewed break disposition, and downstream generation/import checks.
  No generated artifacts or registry-publication gate is added here.

## 9. Drawbacks and risks

Required recovery ties release readiness to RFC 0006's unresolved review and
interop work. That is a real dependency, not a reason to select an unbound
mandatory-only release. Tighter credentials may exclude existing large token
formats and need an explicit migration. Base64/header limits can differ at
intermediaries. Go package migration breaks imports once and needs coordinated
downstream ownership, even though wire fields are unchanged.

## 10. Decision status and acceptance blockers

| Proposal choice | Selection for review | Approval status |
|---|---|---|
| D1 | RFC-defined post-ACTIVE profile RPC; RFC 0006 recovery required for release target | Accepted 2026-10-30 (RFC 0006 accepted in the same wave) |
| D2 | 8 KiB raw credential, 128 UTF-8 byte connection ID, 4 KiB diagnostic, ≥16 concurrency, grace default 5 s/max 30 s; method bound stays with owner | Accepted 2026-10-30 |
| D3 | 1 MiB total encoded frame, not payload | Accepted 2026-10-30 (fixture/spec alignment applied) |
| D4 | Preserve current matching profile IDs | Accepted 2026-10-30 |
| D5 | Downstream `syntra-go/gen/syntra/v1;syntrav1` Go option | **Deferred — out of scope for the 2026-10-30 acceptance**; tracked follow-up pending downstream owner confirmation of module/output/import layout and release ordering |

Acceptance was recorded 2026-10-30 via
[Decision 0002](../docs/decisions/0002-sdd-acceptance-wave.md):
1. Owner/reviewers: oscarlaw (self-review disclosed per `GOVERNANCE.md` Sec. 3).
2. Approvals: recorded in Decision 0002 (D1–D4); security scope acknowledged;
   independent security review remains a release gate.
3. Satisfied: RFC 0006 is accepted in the same wave; the post-ACTIVE binding is
   the accepted negotiation form; no generic capability probing is authorized.
4. The specification-freeze decision that follows records the pre-stable
   version/migration disposition for the accepted bounds. **The Go
   FILE/source-break decision is explicitly excluded from this wave
   (D5 deferred)**; normative specification text stays implementation-neutral
   and free of SDK details.
5. The downstream `syntra-go` owner must confirm the module/output/import
   layout before the deferred go_package migration lands. No BSR publication
   blocker is reinstated (retired as drafted).
6. Owner updates (capabilities, framing, authentication, http credential
   caps, reference doc) and the RFC clocks alignment were applied in the
   acceptance PR; executed behavioral evidence remains a release gate.

## Appendix: References

- [Capabilities](../specifications/core/capabilities.md),
  [framing](../specifications/core/framing.md),
  [RPC](../specifications/core/rpc.md),
  [errors](../specifications/core/errors.md),
  [authentication security](../specifications/security/authentication-security.md).
- [Transport index](../specifications/README.md),
  [profile registry](../conformance/profiles.yaml),
  [claims](../conformance/claims.md),
  [schema generation](../specifications/schema/generation.md),
  [schema compatibility](../specifications/schema/compatibility.md).
- [RFC 0001](0001-public-idl-layout.md),
  [RFC 0002](0002-auth-session-lifecycle.md),
  [RFC 0004](0004-correlation-identity-carriage.md),
  [RFC 0006](0006-update-recovery-profile.md).
