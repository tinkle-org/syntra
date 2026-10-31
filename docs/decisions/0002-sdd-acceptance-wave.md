# Decision 0002 — SDD acceptance wave (RFCs 0001–0006, 0008, 0010)

Status: approved. Public decision record per
[`docs/decision-record-template.md`](../decision-record-template.md).
This record accepts the listed specification contracts in one MAJOR review
wave; each RFC has its own disposition block below. It does not authorize a
release, and it does not claim executed conformance evidence.

## Identity and scope

| Field | Value |
|---|---|
| Record identifier | Decision 0002 (this file; posted with the acceptance PR) |
| Decision kind | rfc-acceptance (joint record; per-RFC dispositions below) |
| Decision state | approved |
| Date | 2026-10-30 |
| Public decision link | This record plus the acceptance PR discussion: <https://github.com/tinkle-org/syntra/pull/20> (approval stated here and in that PR; the single-owner approval authority is explicitly disclosed per `GOVERNANCE.md` Sec. 3) |
| Reviewed repository and commit | `tinkle-org/syntra`, review of the working diff on top of baseline `main` at full SHA `0e8b0f8a4a789cb3d6d00b993e281867d2325e06` (git `#18`); the reviewed content is the acceptance PR head at decision time, full SHA `87b3e6edae6ee68a73bfd6b89b609154858d7212` (branch `docs/sdd-acceptance-wave`, PR #20); review-driven corrections to that content are applied on the same branch. Post-merge commit SHA to be recorded when the PR merges |
| Scope | RFC 0001, 0002, 0003, 0004, 0005, 0006, 0008 accepted; new RFC 0010 accepted; owner-file, owner-IDDL and conformance-manifest normalization applied in the same PR. RFC 0007 and RFC 0009 remain as previously accepted (2026-10-29). |
| Author and decision owner | oscarlaw (author of the acceptance edits; sole active maintainer / repository owner) |
| Authority | `GOVERNANCE.md` Sec. 3 as amended by accepted RFC 0009 and [Decision 0001](0001-bootstrap-ratification.md): exactly one active maintainer, explicit approval, disclosed self-approval |
| Supersedes | None as a whole. Within blocks, it records selected dispositions that supersede the corresponding Draft texts of RFC 0001–0006/0008 as noted below. |

## Approval and security review

| Field | Value |
|---|---|
| Required maintainer quorum | One active maintainer (owner-ratified bootstrap roster; `MAINTAINERS.md`) |
| Approvals | oscarlaw — approval stated in this record and in the acceptance PR |
| Self-review disclosure | Author and approver are the same person (oscarlaw), disclosed here per Sec. 3 |
| Security relevance | Handshake/auth/credentials/errors/streams are in scope (RFCs 0003, 0004, 0010 and the corresponding owner edits). |
| Human security review | Self-review by oscarlaw, disclosed; independent human security review is tracked as a release gate in `audits/v1-release-readiness.md` and `docs/v1-acceptance-package.md` and is NOT satisfied by this record |
| Independence | Self-review; no independent reviewer was available at acceptance time |
| Normative objections | None recorded |
| Advisory analysis | External review report (2026-10-29 session notes) used as advisory input only; advisory analysis is not a vote |

## Architectural decision — Option A (recovery stays in Syntra)

The maintainer ratified **Option A: the standardized Update/Recovery Profile
stays in Syntra's release bundle** (matching MTProto-style provider-recovery).
This is consistent with accepted RFC 0006 §11.1 and the accepted RFC 0009
release scope, so no amendment to RFC 0009 is required. On the wire,
`syntra.update-recovery/1` remains optional and explicitly negotiated per
connection; the negotiation binding is accepted RFC 0005 D1 (post-ACTIVE
profile RPC), and Core-only conformance cannot satisfy the
recovery-inclusive stable bundle.

## Per-RFC dispositions

### RFC 0001 — Public v1 IDL source layout

- Reviewed revision: post-`0e8b0f8` draft text; accepted after the §10
  blockers were resolved as recorded in this section.
- Disposition: **Accepted.** B9 stays resolved (layout: `proto/syntra/v1`
  sole source; FILE break recorded). Behavior blockers resolved by wave:
  B1/B2 → accepted RFC 0003; B3/B10 → accepted RFC 0004; B4/B5/B6 →
  accepted RFC 0008 D1 (raw-wire partition/validation order); B7 →
  accepted RFC 0005 D1 (post-ACTIVE profile contracts; no generic probing);
  B8 → accepted RFC 0005 D3 plus the fixture correction applied to
  `rpc.md`/`opaque-payloads.md`. B11 remains a deferred-additions table
  (no allocation claims).
- Compatibility: binary wire unchanged; source-layout FILE break already
  recorded; no new reserved reuse.

### RFC 0002 — Auth/session lifecycle precision

- Disposition: **Accepted as a dependency record.** Its restatement clauses
  carry history only. Formal supersession mapping (accepted in this wave):
  §10 item 1 (B1) and item 2 (B2) → RFC 0003; item 3 (B3) and item 6 (B10)
  → RFC 0004; items 4–5, 7 (B7/limits/mechanism negotiation) → RFC 0005 D1/D2
  with profile-specific negotiation; item 10 (HTTP bindings) → RFC 0004 D3/D5
  for carriage; item 11 (revocation propagation) → RFC 0010 (new in this
  wave). Still tracked open items: logical-session resumption standard
  (item 8), cross-transport binding (item 9), reliable-session/reliable-delivery
  shipping authority (item 12; SNTR-CAP-008/902 and related coverage stay
  proposals) — each tracked in `SESSION-OPEN-QUESTIONS.md` and the core
  open-questions list; none of them is authorized by this record.
- Compatibility: no wire change (as drafted).

### RFC 0003 — Handshake failure signaling

- Disposition: **Accepted.** D1 (local typed cause + transport-native peer
  signal; no error Frame), D2 (fail-close pre-ACTIVE notification), D3
  (`UNIMPLEMENTED` for version mismatch), D4 (core handshake timer starts at
  the profile's transport establishment waypoint; no partial-input resets).
- Pre-acceptance normalization: the RFC-to-owner wording pair is the
  controlling text (owner files `handshake.md`, `errors.md`, `events.md`
  applied in this PR). WS core-deadline close uses `1001` (replacing the
  earlier `1001/1008` menu); HTTP maps to `400` (no-overlap/malformed
  binding), `401`/`403` (auth); oversize is close `1009`.
- Security: touches handshake + errors; self-review disclosed as above.

### RFC 0004 — Correlation identity, races, authentication carriage

- Disposition: **Accepted.** D1/D2 (strictly increasing nonzero
  connection-scoped request IDs; no reuse; host high-water with
  ordered-admission violation semantics — the violating direction records
  local `FAILED_PRECONDITION` and the connection terminates via the native
  close signal; other in-flight calls fail `UNAVAILABLE` per the connection
  rule), D3 (HTTP/HTTPS per-exchange independence), D4 (single
  serialized, deadline-checked local terminal gate; cancel/deadline tie
  selects `DEADLINE_EXCEEDED`; a validated-selected result stays terminal,
  a merely buffered one does not win), D5 (profile-specific credential
  carriage: `ClientHello.credential` on connection transports;
  `Authorization: Syntra <base64>` on HTTP/HTTPS; forbidden
  principal-change requests fail `FAILED_PRECONDITION` under their valid
  ID with the binding intact).
- Timing reconciliation with RFC 0008 D2 (recorded here as the controlling
  resolution): the initiator's deadline starts at local call admission
  (before readiness waiting/writer queueing; sub-millisecond remainder
  expires locally and zero is never encoded as a default reset). The host
  timestamps complete bounded-frame receipt before worker-queue waiting;
  after validation establishes a legal request with an effective
  `timeout_ms`, its deadline is calculated from that receipt timestamp;
  validation and host queue time consume the budget; transit is not
  subtracted via peer wall clocks. Expired work is not dispatched; the
  writer's queued-to-emitting handoff is atomic with the
  terminal/deadline gate. Ownership split stands: RFC 0004 owns the
  single-terminal gate; RFC 0008 owns the complete queue/suspend contract.
- Security: touches RPC/errors/auth carriage; self-review disclosed.

### RFC 0005 — Negotiation binding, bounds, identifiers

- Disposition: **Accepted for its protocol contract** — D1 (post-ACTIVE
  profile negotiation bound to each profile's accepted RFC; no generic
  capability enumeration/probing), D2 (concrete bounds: 8 KiB raw
  credential, 128 UTF-8 byte connection identifier, 4 KiB diagnostic,
  ≥16 arithmetic concurrency floor, documented grace default 5 s/max 30 s),
  D3 (the 1 MiB bound measures the total serialized Frame; a
  MAX-sized frame is within the bound; MAX+1 is rejected before dispatch),
  D4 (current matching transport profile IDs retained).
- **D5 (Go `go_package` migration) is explicitly out of scope for this
  acceptance** and deferred: it is a Protobuf FILE/source break that
  requires downstream `syntra-go` owner confirmation of module/output
  layout and coordinated release ordering. It is tracked as a follow-up;
  this record makes no claim about generated SDK outputs, and the
  normative specification text remains implementation-neutral. BSR
  publication stays retired (as drafted).
- Compatibility: bounds are additive-tightening with the disposition
  recorded; go_package is a tracked FILE break, not merged here.

### RFC 0006 — Update/Recovery Profile (Option A)

- Disposition: **Accepted** with section 11 (decision amendment,
  2026-10-28) as the governing decisions and §§1–10 consolidated to agree
  with §11 at acceptance. §10 items 1–6 (numeric bounds; canonical method
  strings/version rule; retention rule; snapshot offer
  lifetime/supersede incl. supersede-retires-H; fixture hosting; review
  synchronization) are adopted as written there.
- Owner synchronization applied in this PR: `profiles/recovery.md`, the
  `recovery_profile.proto` comments (no field/tag/type/message changes:
  no new outcome, no round/boundary-update field, no transaction/fence
  field, no principal field), `conformance/manifest/recovery.yaml`
  (CONF-URP-001…017 reconciled; the pre-amendment
  shared-overflow/same-handle cases replaced), `schema.yaml` +
  `requirements.yaml` + `scripts/validate-repo.py` admission for
  `SYN-URP-*` (reserved `008/009` preserved), prose companion updated.
- Evidence: registration is not execution. Independent Rust/Go both-role
  recovery observations, crash/fault evidence, and application
  persistence-contract review remain release gates per §11.9.
- Security: principal scoping, checkpoint opacity, DoS bounds reviewed in
  this record; independent security review remains a release gate.

### RFC 0008 — Mobile lifecycle and v1 acceptance contract

- Disposition: **Accepted.** D1 (raw-wire interpretation: metadata 10–15
  tolerated within bounds; 16/17 forbidden everywhere in frame/body
  position; 18–31 future-body variants rejected with `UNIMPLEMENTED`;
  no body is `INVALID_ARGUMENT`; the exact validation order and
  `RpcResult.outcome` mirror rules as drafted), D2 (single elapsed
  operation budget; reconciled with RFC 0004 as recorded above), D3
  (connectivity/liveness/generation fencing; connection replacement is
  not resumption), D4 (reconnect bounded and explicit, never silent
  replay), D5 (resource ownership, one writer, graceful shutdown with
  drain cutoff).
- Remaining gates (not satisfied by acceptance): independently derived
  Noise ciphertext vectors, executable case registration for the owner
  files, host lifecycle/storage contracts, mobile/security operational
  evidence, and numeric deployment budgets declared before measurement.
- Security: touches lifecycle/resources; self-review disclosed.

### RFC 0010 — SC1 host enrollment and authorization lifecycle (new)

- Disposition: **Accepted** as a companion operational-security contract
  to accepted RFC 0007; NO wire change (no new RPC, no field, no framing
  change). Scope: enrollment authority; AK/handle issuance; staged durable
  provisioning with idempotent retries; principal binding before `ready`;
  revocation propagation (immediate on new connections; 300 s hard profile
  maximum from authoritative revocation commit; 60 s operational target
  with preferred push invalidation; fail-closed when current validity
  cannot be established; shorter bounds permitted, longer grace not);
  rotation with strictly increasing epochs and bounded overlap; compromise
  recovery via an independent authority; lifecycle storage control and
  secret disposal; trusted server-key pin rotation.
- New requirements `SNTR-DAUTH-011`–`SNTR-DAUTH-024` are registered with
  the owner documents updated in this PR; manifest rows follow in this
  PR's integration pass; execution evidence remains pending.
- Security: wholly security-adjacent; self-review disclosed; independent
  security review remains a release gate.

## Compatibility and activation

| Dimension | Disposition |
|---|---|
| Binary wire | Unchanged by 0002/0005 (bounds tighten validation); additive for the recovery profile (existing envelopes); no field/tag/type/message changes; reserved 16/17 and `event`/`resume`/`ack` preserved |
| FILE/source | `go_package` migration (RFC 0005 D5) explicitly deferred, not part of this wave |
| Errors/semantics | Handshake failure carrier split (0003), ID non-reuse (0004), post-ACTIVE-only negotiation (0005), fail-close pre-ACTIVE events — behavior changes previously recorded as Draft proposals are now accepted contracts; owner docs updated in this PR |
| Requirement registry | `SYN-URP-*` admitted (008/009 reserved); `SNTR-DAUTH-011…024` registered; `SNTR-SER-008A` indexed |
| Activation | Owner-file, IDL-comment, conformance-manifest and doc edits land in the acceptance PR referencing these accepted contracts; Rust/Go implementation and conformance execution follow the frozen revision and remain evidence, never authority |

## Remaining gates (explicitly NOT satisfied here)

1. Specification freeze record (next decision; pin accepted revisions).
2. Executed conformance runs (all `CONF-*` cases remain registered, not
   executed); independent Rust/Go both-role evidence; SC1 negative cases
   and Noise vectors.
3. Mobile iOS/Android lifecycle evidence; destination/resource budgets.
4. Independent human security review (crypto/composition review of SC1,
   RFC 0010 lifecycle, recovery persistence model).
5. RFC 0005 D5/go_package downstream follow-up; reliable-session shipping
   authority; logical resumption; cross-transport binding.
