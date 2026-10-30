# RFC 0002: Auth/session lifecycle precision without new wire types

- RFC: 0002
- Title: Auth/session lifecycle precision without new wire types
- Author(s): TBD — blocker (maintainer assignment)
- Status: Draft
- Date: 2026-10-19
- Target version: v1 clarification (no wire change)
- Relates to: `specifications/core/handshake.md`, `authentication.md`, `sessions.md`, `capabilities.md`, `errors.md`, `versioning.md`, `reliability.md`; `specifications/security/authentication-security.md`, `replay-protection.md`, `threat-model.md`; `proto/syntra/v1/handshake.proto`, `session.proto`, `capabilities.proto`, `errors.proto`; ADR-005, ADR-009; RFC 0001 (B1–B11); core `open-questions.md` blockers 1–4; security `open-questions.md` items 1, 5
- Reviewers: TBD — blocker (protocol + security maintainers)

> This RFC resolves NO behavioral conflict by fiat. It records where the task glossary differs from approvals, proposes keeping the approved six-state machine and existing wire types, and lists the capability/binding RFCs still required. No `.proto` change is proposed.

Current decision package: RFCs 0003–0005 select core/HTTP/bounds proposals,
RFC 0006 §11 selects required update-recovery corrections, RFC 0007 §11
selects canonical SC1 migration, and [RFC 0008](0008-mobile-lifecycle-and-v1-acceptance.md)
selects mobile lifecycle/parser/resource behavior. RFC 0007 and
RFC 0009 are now Accepted; RFCs 0001–0006 and 0008 remain Draft.
Historical references to proposals in this document are not evidence of
acceptance of the remaining draft contracts. Logical-session resumption remains deferred and distinct from
required durable update recovery; no new core session identifier is introduced.

## 1. Summary

Make authentication and session lifecycle interoperable from specifications alone — three-concept separation, complete lifecycle table, exact handshake ordering, application-neutral auth baseline, generic principals, no v1 session identifier, deferred optional resumption, no cross-transport resumption, HTTP principles, termination/timeout/authorization rules — without adding messages, fields, codes, or states. Affected: initiators, hosts, transport adapters (read-only principles), and the `conformance/auth-session/` cases. Conformance stays executable against the current IDL.

## 2. Motivation

The task asks for eight states, `ServerHello`, session identifiers, mechanism advertisement, resume credentials, cross-transport rules, HTTP bindings, and typed failure messages. Approvals already fix incompatible answers: six states (SNTR-HS-001), `ServerReady`-only success, no session identifier (SNTR-SESS-002), opaque pluggable auth with no negotiation fields (SNTR-AUTH-001/004), default connection-bound sessions with no resumption (SNTR-SESS-003/006), and documentation-only `session.proto`/`capabilities.proto`. Choosing the task glossary inside the specs would silently contradict approvals and governance. This RFC documents each conflict, proposes the compatible reading implemented in the accompanying spec clarifications, and identifies the future RFCs that could change each answer with major-version analysis where required.

## 3. Proposal

Normative force remains with existing IDs; this RFC mints none. Client/server obligations below restate existing requirements in one place.

- **States (keep six; map suggested names):** No new state. `DISCONNECTED` = pre-transport (outside Syntra); `TRANSPORT_ESTABLISHED` = `CONNECTED`; `ERROR` is local reporting + `CLOSING`/`CLOSED`, never a wire state (SNTR-HS-001/006). Client obligations: implement exactly the six transitions; never shortcut or re-handshake on one transport (SNTR-HS-001/040). Server obligations: same; emit exactly one terminal outcome per handshake (SNTR-CORE-020).
- **Handshake ordering:** Initiator sends one `hello` first; host replies `ready` or handshake error, never `ServerHello` (SNTR-CORE-010/020, SNTR-HS-003/004). Version final at host selection in `Frame.version` (SNTR-HS-010). Capabilities final only where an RFC binding exists; default mandatory-only (SNTR-CAP-002). Auth starts with `hello` credential; follow-ups only via post-`ACTIVE` app RPCs (SNTR-AUTH-003/004). Empty credential is a policy-governed anonymous attempt. No session identifier is ever assigned (SNTR-SESS-002). App RPC/events legal only in `ACTIVE` (SNTR-HS-005). Failures terminate with the §5 code + closure (SNTR-HS-040); the pre-`ACTIVE` carrier gap stays open (B1).
- **Auth framework:** No mechanism identifier/advertisement/selection/challenge fields in v1; baseline is opaque credential presentation with host policy (SNTR-AUTH-001/003). Multi-round only above `ACTIVE` (SNTR-AUTH-004). Principal fixed per connection (SNTR-AUTH-007); re-auth same-connection forbidden by default (SNTR-AUTH-010).
- **Principal:** Generic opaque host-owned handle; MAY be human/device/service/process/API consumer/anonymous; never assumed human; no wire principal field; redacted logs (SNTR-AUTH-007, SNTR-ASEC-004).
- **Session identifier:** None in v1. `connection_id` stays diagnostic-only (SNTR-SESS-002, SNTR-ASEC-010).
- **Resumption:** Deferred/optional, off by default (SNTR-SESS-006, SNTR-CAP-003). Future RFC must define opaque token, entropy, audience/principal/time/version/capability binding, lifetime, rotation, replay windows, restored vs non-restored state, failure, and revocation (SNTR-ASEC-007/008, SNTR-RPL-011).
- **Cross-transport:** Not allowed in v1; allowed only where a resumption RFC explicitly binds the profile pair with revalidation and no downgrade (SNTR-TSEC-007/009).
- **HTTP:** No auth from TCP/HTTP-2 lifetime; per-connection `hello`→`ready`; sessions span HTTP requests only via RFC token; identity only via token, never ambient connection facts (SNTR-ASEC-003).
- **Termination/timeouts/authorization:** No `CloseSession` message; graceful close is stop-new-RPCs + profile grace + teardown; error mapping per tables (SNTR-HS-006/013, SNTR-ERR-002/004); timeouts per existing defaults (handshake 5 s, per-RPC `timeout_ms`/bounded host default, no separate auth timer, deployment session lifetimes, profile close grace); authorization `UNAUTHENTICATED` vs `PERMISSION_DENIED` per SNTR-AUTH-006/009.
- **Schema diff:** None. `handshake.proto` (6 fields), `session.proto` (no messages), `capabilities.proto` (no types), `errors.proto` (16 nonzero codes) are unchanged; `reserved 16, 17` and `event`/`resume`/`ack` preserved. Compatibility impact: zero wire/source impact.
- **State machine deltas:** None. Diagrams added are views of SNTR-HS-001, not new transitions.
- **Configuration and defaults:** None changed (1 MiB envelope, depth 32, 5 s handshake, ≥16 concurrent RPCs, bounded host RPC default). Session idle/absolute lifetimes and close grace stay deployment/profile-documented.

```text
Initiator                              Host
    |                                     |
    |--- transport connect -------------->|
    |--- Frame{hello{min,max,cred}} ------>|
    |                                     | select version → evaluate credential
    |<-- Frame{ready{connection_id}} ------|  (or handshake error + close)
    |--- Frame{id=7, request{Echo}} ----->|
    |<-- Frame{id=7, result{payload}} -----|
```

## 4. Detailed design

Mechanics unchanged; this section records review results. Framing/encoding/correlation/cancellation/error mapping/capability/unknown-field/bounds follow existing specs (`framing.md` SNTR-WIRE-*, `serialization.md` SNTR-SER-*, `rpc.md`, `errors.md`, `reliability.md`). Protobuf review (§N): every wire field has defined semantics — `ClientHello.{min_version,max_version,credential}` (range proposal + opaque attempt), `ServerReady.connection_id` (diagnostic only), `RpcError.{code,message}` (typed public failure), `ErrorCode 0–16` (registry; 0 invalid, unknown numerics map to `UNKNOWN` at reporting layer per SNTR-ERR-005); `session.proto`/`capabilities.proto` define no fields, so no undefined-lifetime/optional-absence questions arise; no enum state lacks behavior; no message lacks spec coverage; no specified concept lacks schema support except the intentionally deferred extensions (resumption/capability/auth-round records), which are capability-RFC work, not missing fields. Codecs demonstrate representability only (empty success vs unset outcome, unknown-enum retention, oneof last-wins); validators enforce rejection per SNTR-SER-005/008. `buf lint` (STANDARD), `buf build`, FILE baseline, WIRE audit, and descriptor/codec tests all pass with no schema edit.

## 5. Alternatives considered

1. **Adopt the eight-state machine with wire-visible ERROR.** Rejected for this task: contradicts SNTR-HS-001, needs major version + migration per SNTR-VER-003, and no acceptance exists. Do nothing instead: map suggested names informatively.
2. **Add `ServerHello`, session IDs, mechanism/record fields, resume/close messages now.** Rejected: Protobuf has no compatible alias path here; new semantics need capability RFCs with bounds/confirmation/failure design (B7/B11). Do nothing instead: document absence and blockers.
3. **Do nothing at all (no clarification).** Rejected: leaves ordering, HTTP, termination, and timeout answers scattered. Chosen path clarifies without changing behavior.

## 6. Compatibility

- Wire impact: none (no `.proto` change).
- Negotiation: unchanged; mandatory-only default preserved; no new downgrade surface.
- Reserved values: preserved; no reuse.
- Migration: none. Historical FILE break (RFC 0001) unchanged; no new source break.

## 7. Security considerations

No new crypto, mechanisms, or bindings. Threats/credential handling/diagnostic hygiene/DoS bounds/transport policy unchanged (T1–T10 mitigations, SNTR-ASEC-*/RPL-*/TSEC-*). Clarifications reduce fixation/confusion risk (`connection_id` never auth), oracle risk (generic errors), and replay risk (per-class defenses restated). Negative tests cover unauthenticated/oversized/malformed/resumed/replayed inputs in `conformance/auth-session/`.

## 8. Test plan and acceptance criteria

- [ ] Conformance tests: `conformance/auth-session/session.md` (CONF-SESS-001…010) + `authentication.md` (CONF-AUTH-001…006): positive, negative, and fixture cases as defined there.
- [ ] Requirement-to-test trace: session.md/authentication.md tables map each case to existing SNTR-HS/AUTH/SESS/RPC/ERR/VER/CAP/REL/RPL/ASEC IDs; no new IDs minted.
- [ ] Interop check: mandatory-only initiator vs full host over two transport profiles (SNTR-WIRE-901); resumption NOT exercised (no capability to cite per SNTR-CAP-901).
- [ ] Buf lint + breaking detection: `buf lint`, `buf build`, `buf breaking --against compatibility/v1-initial/image.json` — no schema change, expected pass (executed; see validation record).

Results are reported from execution, never asserted in advance.

## 9. Drawbacks and risks

Clarification-only RFCs can be mistaken for approval of the deferred features. Mitigation: SESSION-OPEN-QUESTIONS.md lists release blockers; conformance asserts rejection (not success) for resumption; reference docs state the baseline is opaque presentation, not a negotiated mechanism.

## 10. Unresolved questions and blockers

Carried forward; MUST be resolved before stable, never by implementation choice:

1. **B1 typed pre-`ACTIVE` error carrier** (which `Frame`, if any, carries handshake errors; zero-`request_id` `result` forbidden).
2. **B2 pre-`ACTIVE` notification conflict** (ignore vs fail).
3. **B3 stale `request_id` reuse** (core permits after terminal result; replay security rejects).
4. **B7 capability/session-extension binding and bounds** (identifiers, parameters, confirmation, limit overrides, token lifetimes/windows).
5. **B8 1 MiB payload vs 1 MiB envelope conflict.**
6. **B10 cancel/deadline/`UNAVAILABLE` outcome races.**
7. **Mechanism negotiation** (identifier/advertisement/selection/challenge) — release blocker if claimed; otherwise v1 stays opaque-presentation with application-side agility.
8. **Resumption standard** (token format, entropy, bindings, lifetime, rotation, replay, restored state, revocation) — blocker only if resumption claimed.
9. **Cross-transport binding** — blocker only if cross-transport resumption claimed.
10. **HTTP profile bindings** — transport-profile RFCs must embody §1E principles.
11. **Revocation-propagation bound, channel-binding, proxy propagation** — per security open questions.
12. **Reliable-session/reliable-delivery shipping authority and wire contract** —
    `sessions.md` §1H, `capabilities.md` SNTR-CAP-008/902, and
    `reliability.md` §1C and the reliable-delivery coverage in §7
    (e.g. SNTR-REL-902) remain proposals without an accepted authorizing
    RFC. SNTR-REL-900/901 remain shipping baseline. This RFC does not
    authorize them; RFC 0006 is a separate Draft
    update/recovery proposal. Canonical negotiation/control methods,
    versioned binary schemas, delivery-ID carriage, confirmation/fallback,
    and deterministic fixtures are still required. Former `CONF-RS-001..005`
    wire rows have been withdrawn from executable cases; the IDs and
    intended coverage remain draft plans in `sessions.md` §7.1. In particular,
    initial attachment uses epoch 1 and its first resume expects epoch 2;
    SNTR-SESS-034 needs both planned idle-expiry (`CONF-RS-003`) and drain
    (`CONF-RS-004`) coverage; attach/drain alone cannot establish CAP-902
    negotiation. The draft reliability proposal now explicitly keeps a
    bounded Pending/content fence while execution remains live, including
    past nominal result/tombstone retention; deadline/cancel/loss alone
    cannot prove execution stopped. Maintainer protocol/security review
    and acceptance are outstanding. Existing implementation unit tests
    remain useful local checks, not wire-conformance or shipping approval.

## Appendix: References

- `specifications/core/handshake.md` §1A–§1B/§2A, `authentication.md` §1A–§1D, `sessions.md` §1A–§1G; `capabilities.md`, `errors.md`, `versioning.md`, `reliability.md`.
- `specifications/security/*` (threat-model, authentication-security, replay-protection, transport-security, opaque-payloads, test-plan, open-questions).
- `proto/syntra/v1/handshake.proto`, `session.proto`, `capabilities.proto`, `errors.proto`; `specifications/schema/reference.md`, `generation.md`, `compatibility.md`, `validation.md`.
- RFC 0001 (B1–B11), core `open-questions.md`, `conformance/auth-session/`, `SESSION-OPEN-QUESTIONS.md`.
- Buf 1.59.0; pinned generators (Prost v0.4.0r1, Go v1.36.6r1); Go 1.26.4; Rust 1.85.1; Python 3.14.7.
