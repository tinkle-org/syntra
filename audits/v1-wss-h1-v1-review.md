# Syntra v1 Core + SNTR-WSS-H1-V1 Review (interoperability reviewer view)

- Date: 2026-10-20. Branch: `main` at `8b7a14c`. Working tree clean at review time.
- Role: protocol specification architect and interoperability reviewer. No protocol implementation was written; no behavior was assumed from code.
- Read: `specifications/architecture.md`, `specifications/core/` (all 16 files), `specifications/transports/secure-websocket.md`, `specifications/transports/websocket.md`, `specifications/transports/tcp.md`, `specifications/transports/tls-tcp.md`, `specifications/transports/http.md` (endpoint, media, mapping, auth carriage sections), `specifications/transports/https.md` (profile/TLS/ALPN sections), `specifications/security/` (all 10 files), `specifications/decisions/` (ADR-001 through ADR-010), `specifications/schema/` (all 5 files), `proto/syntra/v1/` (all 7 files), `rfcs/` (README, template, 0001 through 0005), `SESSION-OPEN-QUESTIONS.md`, `audits/` (all 4 prior files), `conformance/` (profiles, claims, manifests, requirements prose, vectors, interoperability), `docs/` (implementer guides, registry, transport selection, glossary, FAQ), `GOVERNANCE.md`, `RELEASE.md`, `CHANGELOG.md`, `MIGRATION.md`, `scripts/validate-repo.py`, `scripts/validate-schema.py`, `tests/schema/test_schema.py`.
- Validation at review time: `python3 scripts/validate-repo.py all` passes (requirements 498 rows / 498 defined IDs, manifests 130 cases / 350 requirement refs, vectors protobuf/TCP/HTTP/WS checked, links 176 markdown files, RFC metadata, markdown hygiene, boundary). `python3 -m unittest discover -s tests/schema` passes (13 tests). `buf lint`, `buf build`, `buf breaking --against compatibility/v1-initial/image.json` pass.
- Governance posture: this file is a review and proposal record only. It makes no normative change, accepts no RFC, and authorizes no wire change. Every normative edit named below REQUIRES an Accepted RFC with maintainer quorum (and security review where applicable) per `GOVERNANCE.md` Sec. 3 before it lands. RFCs 0001 through 0005 remain Draft.

## 1. Requirement-to-schema-to-test traceability matrix

Source of counts: `conformance/manifest/requirements.yaml` (498 rows), manifest case files, `proto/syntra/v1/*.proto`, `conformance/test-vectors/`.

| Requirement family | Defining document | Schema representation | Conformance cases (manifest) | Vectors / prose |
|---|---|---|---|---|
| SNTR-CORE (16) | `core/protocol.md` | No new wire fields; model constraints | core.yaml CONF-CORE-001/008/009/010, rpc.yaml CONF-RPC-002/012, security.yaml CONF-SEC-009/010/011 | protobuf GOLD vectors (logical equality) |
| SNTR-SER (14) | `core/serialization.md` | proto3 binary; `reserved 16,17` + names; no `optional`/`repeated`/`map` | core.yaml CONF-CORE-003, security.yaml CONF-SEC-002/003, transport-tcp.yaml CONF-TCP-002/007, transport-http.yaml CONF-HTTP-006 | protobuf vectors.yaml (GOLD-PROT-*, UNKNOWN-FIELD-01 field 90, EMPTY-FRAME-01); `tests/schema/` codec checks |
| SNTR-WIRE (14) | `core/framing.md` | `Frame` fields 1, 2, 10-15; reserved 16,17 + `event`,`resume`,`ack` | core.yaml CONF-CORE-001/002/009, rpc.yaml CONF-RPC-005/006, security.yaml CONF-SEC-002, transport-tcp.yaml CONF-TCP-005/006/007, transport-ws.yaml CONF-WS-005/008/011 | protobuf + tcp byte-vectors (V1-V9) + ws fixtures VEC-WS-003/008/009 |
| SNTR-HS (18) | `core/handshake.md` | `ClientHello` fields 1-3; `ServerReady` field 1; `Frame.version` | core.yaml CONF-CORE-005/008/010, session.yaml CONF-SESS-001/003/007/010, security.yaml CONF-SEC-010/011, transport-tcp.yaml CONF-TCP-001, transport-ws.yaml CONF-WS-011/013 | protobuf GOLD-PROT-HELLO-01 / READY-01; tcp V1/V2; ws VEC-WS-001/002/007 |
| SNTR-AUTH (16) | `core/authentication.md` | `ClientHello.credential` opaque bytes; empty = anonymous attempt | session.yaml CONF-SESS-001/002/004, auth-session prose CONF-AUTH-001-006 (prose-only, no manifest rows; see Sec. 7 gap) | protobuf GOLD-PROT-AUTHN-01 (credential carriage) |
| SNTR-SESS (14) | `core/sessions.md` | No session ID field; `connection_id` diagnostic only | session.yaml CONF-SESS-001/004/005/006/007/008/009/010 + optional CONF-SESS-R01 (gated `resume-v1`, SKIP in default v1) | ws VEC-WS-007 reconnect rows |
| SNTR-RPC (16) | `core/rpc.md` | `RpcRequest` fields 1-3; `RpcResult` oneof payload=1 / error=2; `Cancel` empty | rpc.yaml CONF-RPC-001 through CONF-RPC-012 (all 12) | protobuf GOLD-PROT-REQ-01 / REQ-EMPTY-01 / RES-OK-01 / RES-EMPTY-01 / RES-ERR-01 / CANCEL-01 |
| SNTR-EVENT (17) | `core/events.md` | `Notification.payload` field 1 only; no IDs/cursors/acks | events.yaml CONF-EVT-001-015 (7 mandatory capability-free + 8 gated); core selects mandatory subset per `profiles.yaml` | neutral opaque payloads; hygiene negative grep |
| SNTR-REL (16) | `core/reliability.md` | No wire fields; timeout/cancel/loss mapping policy | rpc.yaml CONF-RPC-002/007/011/012, session.yaml CONF-SESS-007, events.yaml CONF-EVT-005/010 | rpc §1I retry table (guidance, not wire) |
| SNTR-CAP (13) | `core/capabilities.md` | `capabilities.proto` defines no types (documentation-only) | core.yaml CONF-CORE-006/007, events.yaml CONF-EVT-001/002 | capability placeholder names only; must not be advertised |
| SNTR-ERR (12) | `core/errors.md` | `ErrorCode` 0-16; `RpcError` fields 1-2 | rpc.yaml CONF-RPC-005/009/010, core.yaml CONF-CORE-004, errors prose CONF-ERR-001-004 (prose-only; see Sec. 7 gap) | protobuf GOLD-PROT-RES-ERR-01 (code 12) |
| SNTR-VER (13) | `core/versioning.md` | `Frame.version`, `min_version`/`max_version`; package `syntra.v1` | core.yaml CONF-CORE-005, session.yaml CONF-SESS-010 | version overlap fixtures |
| SNTR-TMOD (12) | `security/threat-model.md` | None (model) | security.yaml CONF-SEC-001-011 via `test-plan.md` STEST groups | review artifacts (manual) |
| SNTR-TSEC (17) | `security/transport-security.md` | None (TLS policy) | security.yaml CONF-SEC-001/008/009, transport-tls.yaml CONF-TLS-001-004, transport-wss.yaml CONF-WSS-001-009, transport-https.yaml CONF-HTTPS-001-008 | harness-named PKI references (no embedded key material) |
| SNTR-ASEC (22) | `security/authentication-security.md` | Carriage/disclosure rules; no new fields | security.yaml CONF-SEC-004/005/006/007/011, events.yaml CONF-EVT-013 | negative-grep hygiene rows |
| SNTR-RPL (13) | `security/replay-protection.md` | No new fields; 5-class separation | session.yaml CONF-SESS-008/009, security.yaml CONF-SEC-006 | replay/retransmit fixtures |
| SNTR-OPQ (10) | `security/opaque-payloads.md` | `bytes payload` fields (bit-preserved) | core.yaml CONF-CORE-001, security.yaml CONF-SEC-002 | arbitrary/non-UTF-8/simulated-ciphertext round-trips |
| SNTR-STEST (12) | `security/test-plan.md` | None (test groups G) | security.yaml CONF-SEC-001-011 (11 cases, one per group) | STEST-900 cross-cutting hygiene |
| SNTR-TCP (15) | `transports/tcp.md` | 4-byte big-endian length prefix + `Frame` | transport-tcp.yaml CONF-TCP-001-008 | tcp byte-vectors V1-V9 + vectors.json |
| SNTR-TLS (15) | `transports/tls-tcp.md` | Same units over TLS 1.3 session | transport-tls.yaml CONF-TLS-001-004 | shared TCP vectors; records-are-not-frames rows |
| SNTR-HTTP (59) | `transports/http.md` | `POST /syntra/v1/rpc`, one `Frame` per body, `Authorization: Syntra <base64>` | transport-http.yaml CONF-HTTP-001-018 | http fixtures.yaml |
| SNTR-HTTPS (29) | `transports/https.md` | Same mapping over TLS 1.3; H1/H2 bindings | transport-https.yaml CONF-HTTPS-001-014 | shared http fixtures |
| SNTR-WS (54) | `transports/websocket.md` | `/syntra/v1/ws`, `syntra.v1`, one binary message = one `Frame` | transport-ws.yaml CONF-WS-001-017 | websocket fixtures VEC-WS-001-009 |
| SNTR-WSS (36) | `transports/secure-websocket.md` | Same framing over TLS 1.3; TLS-first layering | transport-wss.yaml CONF-WSS-001-010 + full CONF-WS-001-017 over `wss://` | shared ws fixtures; TLS via harness names |
| SYN-ARCH (25) | `architecture.md` | Ownership/layering/independence charter | requirements.yaml appendix rows (6 automated, 2 partial, 17 manual) | review attestations |

Automation mix (from `requirements.yaml`): 418 automated (83.9%), 44 partially automated (8.8%), 36 manual (7.2%), 0 uncovered IDs. Uncovered-ID coverage holds for the registered-ID universe only; un-ID'd normative MUSTs in clarifying subsections remain unmapped (see Sec. 7).

Schema inventory (frozen per `RELEASE.md` Sec. 2): `Frame` (version=1, request_id=2, hello=10, ready=11, request=12, result=13, cancel=14, notification=15; reserved 16,17 + names), `ClientHello` (min_version=1, max_version=2, credential=3), `ServerReady` (connection_id=1), `RpcRequest` (method=1, payload=2, timeout_ms=3), `RpcResult` (oneof payload=1 / error=2), `Cancel` (no fields), `Notification` (payload=1), `RpcError` (code=1, message=2), `ErrorCode` 0-16, `session.proto` and `capabilities.proto` documentation-only. No `optional`, `repeated`, `map`, `Any`, services, or external imports.

## 2. Phase 1 conflicts: protobuf vs specification vs RFC vs conformance vs guides

Verdicts use the prior audit finding numbers F-01 through F-22 for continuity. Only F-01 is reclassified; all other P0/P1 findings are confirmed.

### F-01 transport profile identifiers: RESOLVED in tree, audits stale (no normative change needed, doc patch to audits only)

Prior audits claim specs use `SNTR-HTTP-V1`/`SNTR-WS-V1`/`SNTR-WSS-V1` while the suite uses `SNTR-HTTP1-V1`/`SNTR-WS-H1-V1`/`SNTR-WSS-H1-V1`. Reran the repository check: `SNTR-WSS-V1` is the obsolete spelling with zero hits in `specifications/`, `conformance/`, `proto/`, `docs/`; the live spelling is `SNTR-WSS-H1-V1`, which is present (`secure-websocket.md` SNTR-WSS-004, `transport-wss.yaml`, `profiles.yaml`, plus `docs/` references). The other second-spelling variants are likewise absent: `grep` for `SNTR-HTTP1-V1` and `SNTR-WS-H1-V1` returns zero hits in those trees. The live spellings are `SNTR-HTTP-V1` (`http.md` SNTR-HTTP-006, `transport-http.yaml`, `profiles.yaml`), `SNTR-WS-V1` (`websocket.md` SNTR-WS-004, `transport-ws.yaml`, `profiles.yaml`), `SNTR-WSS-H1-V1` (`secure-websocket.md` SNTR-WSS-004, `transport-wss.yaml`, `profiles.yaml`). `scripts/validate-repo.py` profile-pattern checks pass, which is consistent with a unified set. Disposition: close F-01 as fixed-in-tree; update `audits/v1-consistency-review.md`, `audits/v1-release-readiness.md`, `audits/v1-implementer-questions.md` Q48, and RFC 0005 Decision D4 to record the unified set actually present instead of proposing a unification that already holds. Requires maintainer sign-off as an audit correction (non-normative), not a wire change. The 10 validator errors cited in the readiness report against F-01 do not reproduce on the current tree.

### F-02 request_id reuse vs stale rejection: CONFIRMED P0 (B3)

Core permits reuse after terminal result (`rpc.md` SNTR-RPC-002/010, `framing.md` SNTR-WIRE-010, client guide "IDs may be reused only after the terminal result"). Replay security rejects a `request_id` arriving after its terminal result as stale (`replay-protection.md` SNTR-RPL-012) and forbids cross-connection reuse (`SNTR-RPL-020`), with `SNTR-RPL-030` requiring enforcement. `rpc.md` Sec. 1B and Sec. 4 acknowledge the conflict as open B3 and assert only duplicate-outstanding rejection in conformance. An old replay and a lawful new attempt are indistinguishable by ID alone. See Sec. 3 B3 proposal path (RFC 0004 Decision D1). No wire change is proposed until that decision is accepted.

### F-03 no lawful pre-ACTIVE typed error carrier: CONFIRMED P0 (B1)

Handshake Sec. 5 and `errors.md` SNTR-ERR-004 require typed terminal handshake failures, but `framing.md` SNTR-WIRE-003 forbids zero-`request_id` `result` and `handshake.md` SNTR-HS-012 forbids pre-ACTIVE results, while `ServerReady` has no error outcome. TCP/TLS hosts therefore cannot transmit which handshake error occurred beyond closing. `architecture.md` Sec. 12.1 depicts `Frame{result{...}}` on failure, which is exactly the forbidden pattern (F-08, same root cause). `websocket.md` SNTR-WS-041 contains a parenthetical "(except the handshake outcome carrier per core blocker B1)" that presupposes a carrier B1 declares absent; the parenthetical must be struck or rewritten when B1 is decided. See Sec. 3 B1 proposal path (RFC 0003 Decision D1). No new `Frame` variant is proposed until a decision is taken.

### F-04 HTTP per-exchange amnesia vs stale rejection: CONFIRMED P0

`http.md` SNTR-HTTP-073 makes each exchange an independent logical connection with fresh ID scope, while SNTR-RPL-012 demands stale-ID rejection that needs cross-exchange memory. The HTTP specialization must be recorded as the lawful exemption for that profile (persistent profiles keep the stale rule; HTTP exchanges do not share ID state). See Sec. 3 RFC 0004 Decision D2. No wire change.

### F-05 private-organization go_package path: CONFIRMED P0

All seven `proto/syntra/v1/*.proto` files carry `option go_package = "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1;syntrav1"`, and `tests/schema/test_schema.py` pins that value. This conflicts with SYN-ARCH-001/062 independence and poisons BSR Go consumption with a private import home. `docs/schema-registry.md` Sec. 5 already records the finding and withholds the change because `go_package` is covered by Buf `FILE` breaking rules (`FILE_SAME_GO_PACKAGE`). Disposition: changing it is a FILE-breaking schema edit requiring a normative RFC, maintainer quorum, and `CHANGELOG.md`/`MIGRATION.md` migration notes (RFC 0005 Decision D5). This review proposes no value and makes no edit; BSR publication stays blocked on this item per the readiness report until maintainers decide.

### F-06 1 MiB payload fixtures vs 1 MiB envelope: CONFIRMED P0 (B8)

`rpc.md` SNTR-RPC-900 and `opaque-payloads.md` SNTR-OPQ-900 ask for a 1 MiB payload round trip while `framing.md` SNTR-WIRE-006 caps the entire serialized `Frame` at 1 MiB. Tags, lengths, version, correlation, method, and budget overhead make a 1 MiB payload unshippable inside a 1 MiB envelope. The fixture text (not the bound) is wrong. See Sec. 3 B8 proposal path (RFC 0005 Decision D3): rewrite as largest-payload-fitting plus explicit exactly-MAX / MAX+1 serialized-byte boundary fixtures. No bound is raised by this review.

### F-07 pre-ACTIVE notification three-way split: CONFIRMED P1 (B2)

`events.md` SNTR-EVENT-005/900 defaults to ignore-with-diagnostic, `handshake.md` SNTR-HS-012/900 requires failure and close, `framing.md` SNTR-WIRE-003/011 requires rejection, and ADR-007 says ignore-or-reject per a forthcoming stream spec. `CONF-EVT-014` asserts ignore-tolerance while `CONF-SESS-003` and `CONF-WS-011` assert failure and close for pre-ACTIVE frames including notification variants. See Sec. 3 B2 proposal path (RFC 0003 Decision D2). No behavior is selected by this review.

### F-09 dual version-mismatch codes: CONFIRMED P1

Handshake Sec. 5 permits `UNIMPLEMENTED` or `FAILED_PRECONDITION` for version mismatch. Both transitions close, so interop is safe, but the test matrix doubles and `CONF-SESS-010`/`CONF-CORE-005` each assert one spelling. See RFC 0003 Decision D3 (proposing `UNIMPLEMENTED` for version-unknown, `FAILED_PRECONDITION` reserved for state violations). No code is unified by this review.

### F-10 credential carriage ASEC-003 vs HTTP Authorization: CONFIRMED P1

`authentication-security.md` SNTR-ASEC-003 says credentials appear only in `ClientHello.credential`, while `http.md` SNTR-HTTP-060/061 defines `Authorization: Syntra <base64>` as the HTTP binding. Strictly read, the security rule outlaws the HTTP profile. See RFC 0004 Decision D4 rewording (frame-carrying profiles vs profile-defined byte bindings; never URLs/IDs/methods/errors/logs). No carriage rule is changed by this review.

### F-11 dead lower-bound-negotiation clause: CONFIRMED P1

`rpc.md` SNTR-RPC-008 ("unless a lower bound was negotiated") references a negotiation mechanism that has no binding anywhere (`reference.md` confirms). See RFC 0005 Decision D2 (proposing deletion of the clause until a binding exists; floor is 16, period). No floor is changed by this review.

### F-12 missing field-specific bounds: CONFIRMED P1 (B7)

No maxima exist for `credential`, `connection_id`, or `RpcError.message`; close grace has no default or maximum; limit-override binding is absent. Only HTTP bounds credential bytes (64 KiB via SNTR-HTTP-113). This is DoS-relevant and blocks B7. See RFC 0005 Decision D2. No bound is set by this review.

### F-13 re-auth attempt has no code: CONFIRMED P1

`authentication.md` SNTR-AUTH-010 forbids same-connection re-authentication, but no section assigns the resulting code. See RFC 0004 Decision D5 (proposing `FAILED_PRECONDITION` without binding change). No code is assigned by this review.

### F-14 sessions.md Sec. 1B HTTP row is false: CONFIRMED P1 (doc patch, normative wording)

The table row "Exposed over HTTP profiles? `connection_id` travels only inside `ServerReady` like any envelope field" implies HTTP carries `ServerReady` frames. The HTTP mapping carries one `request` envelope in and one `result` envelope out per exchange (`http.md` Sec. 0/1C); there is no `hello`/`ready` frame exchange on HTTP. The row is fail-safe (it denies extra meaning and forbids URL placement) but factually wrong about carriage. Correction requires a normative doc patch via RFC 0004 (Decision D2 bundle). This review makes no edit.

### F-15 cancel/deadline/UNAVAILABLE race precedence: CONFIRMED P1 (B10)

`rpc.md` Sec. 1G documents completion-wins and single-terminal but leaves the cancel-vs-deadline tie with no result as an open tie-break; `errors.md` SNTR-ERR-002 calls `UNAVAILABLE` "the only code that implies unknown handler outcome" while `reliability.md` SNTR-REL-001 and `rpc.md` timeout/server-after-deadline text leave `DEADLINE_EXCEEDED`/`INTERNAL`/`UNKNOWN` equally unknown. See Sec. 3 B10 proposal path (RFC 0004 Decision D3). The word "only" must be struck when that RFC is accepted; it is not struck here.

### F-16 errors.md Sec. 1D staleness: CONFIRMED P1 (doc patch)

Sec. 1D says "Exact status bindings (if any) belong to the future transport specifications, not to this document; no mapping is finalized here." HTTP/HTTPS status tables are finalized in `http.md` Sec. 1E and `https.md`. The note is stale and creates authority confusion. Correction via RFC 0003 alignment bundle. No edit made here.

### F-17 capability advertisement presumed but unwired: CONFIRMED P1 (B7)

`capabilities.md` SNTR-CAP-002/004 presumes advertisement/confirmation while also deferring the binding to each capability RFC; no v1 binding exists. See RFC 0005 Decision D1. No binding is invented here.

### F-18 close grace has no default or maximum: CONFIRMED P1 (B7)

No default or maximum close-grace duration exists anywhere; unbounded CLOSING is lawful. See RFC 0005 Decision D2 (proposing default 5 s, maximum 30 s, deployment-documented). No value is set here.

### F-19 TLS/TCP handshake-timer start unbound: CONFIRMED P1

TCP starts at CONNECTED, WSS binds at WSS establishment, but TLS/TCP does not bind whether the 5 s timer starts at TCP connect or TLS completion. See RFC 0003 timer binding. No point is selected here.

### F-20 wrong schema filenames: CONFIRMED P2 (non-normative doc patches, approval per GOVERNANCE Sec. 3 non-normative bar)

`error.proto` for `errors.proto` appears in `core/errors.md`, `core/framing.md`, `core/protocol.md` (appendix ref), and `security/threat-model.md`; `session.proto` is cited as the home of `Frame` (`core/framing.md`) and of `ClientHello`/`ServerReady` (`security/authentication-security.md` Sec. 1). Additionally `security/threat-model.md` Sec. 1 references `proto/syntra/v1/session.proto` and `proto/syntra/v1/error.proto` as normative sources for `Frame` and error vocabulary, which misdirects implementers to documentation-only or historical paths. Corrections are filename-only and change no behavior. This review makes no edit; maintainers may land them as non-normative fixes with one approval each.

### F-21 registry counts and trace-table staleness: CONFIRMED P2

`core/requirements.md` claims "~130 normative IDs" while 179 bolded SNTR definitions exist in core documents alone (plus the 25 SYN-ARCH appendix rows now in `requirements.yaml` for 498 total). `core/conformance.md` Sec. trace table lists suite directories (`core/`, `handshake/`, `serialization/`, `framing/`, `reliability/`, `negotiation/`) that do not exist; the actual manifests are `core.yaml`, `session.yaml`, `rpc.yaml`, `events.yaml`, `transport-*.yaml`, `security.yaml`. `http.md` and `https.md` cite `CONF-HTTP-001...016` and `CONF-HTTPS-001...012` while the requirements files define 001...018 and 001...014. Doc patches only; no edit made here.

### F-22 assorted divergences: CONFIRMED P2 (profile-bundled doc patches)

WS credential-in-query tolerance (SNTR-WS-012 ignore) vs HTTP 400 strictness (SNTR-HTTP-003) is a deliberate per-profile difference, not a contradiction, but `secure-websocket.md` SNTR-WSS-011 server behavior on credential-in-query is unspecified beyond the MUST-NOT-appear rule. WS trailing-garbage close-code placement sits between 1002 and 1007 (implementer Q43 proposes 1007 + `INVALID_ARGUMENT` with documentation). HTTP empty-`Authorization` 401 vs core empty-credential anonymous is a documented per-profile difference (`http.md` SNTR-HTTP-061). `OUT_OF_RANGE` vs `INVALID_ARGUMENT` for over-max budgets needs the unstated robustness rule recorded (initiators accept both). H2 Content-Length/chunked language in `http.md` is H1-specific and must be scoped when read for H2. HTTP 504 appears in a retry table but is never sent. None is changed here.

### New observation N-01: WS-041 parenthetical presupposes B1 (normative wording)

`websocket.md` SNTR-WS-041 says no `request`/`result` (except the handshake outcome carrier per core blocker B1) is legal before handshake completion. B1 states no such carrier exists. The exception clause must be removed when B1 is decided; until then it reads as permission for a forbidden frame. Tracked as part of RFC 0003 Decision D1. No edit made here.

### New observation N-02: threat-model normative references point at historical filenames

`security/threat-model.md` header references `proto/syntra/v1/session.proto` and `proto/syntra/v1/error.proto`. The first is documentation-only in the current layout; the second does not exist (`errors.proto` is the live file). Same filename class as F-20. No edit made here.

## 3. Phase 2 blocker proposals (one interoperable behavior each; all PROPOSED, none accepted)

For each blocker: conflicting requirements, one proposed normative behavior, initiator/host obligations, wire representation, security consequences, compatibility impact, conformance cases (proposed IDs reference existing requirement IDs; the cases themselves are proposed in Sec. 7, not added to manifests), and maintainer-approval flag. "Proposed" means the text of Draft RFCs 0003/0004/0005 as they stand; this review endorses them as the decision procedure, not as accepted outcomes.

### B1 typed failures before ACTIVE (RFC 0003 Decision D1)

- Conflict: `handshake.md` Sec. 5 + `errors.md` SNTR-ERR-004 require typed terminal handshake failures; `framing.md` SNTR-WIRE-003 + `handshake.md` SNTR-HS-012 forbid the only error carrier (`result`, including zero-ID) pre-ACTIVE; `ServerReady` has no error outcome.
- Proposed behavior: transport-native mapping only (no wire change). Each profile's close/status/WS-code table becomes the carrier: the typed code is surfaced locally on both peers and the profile signal travels on the wire (TCP/TLS close, HTTP 4xx/401, WS/WSS close 1002/1007/1008/1009/1011 per existing tables). Reword SNTR-HS-020 and SNTR-ERR-004 to require local surfacing plus profile signal instead of a `Frame`-carried code.
- Initiator: surface the mapped code locally, close, never emit a zero-ID `result` to carry it, never retry with downgrade unless explicitly re-negotiated.
- Host: select the Sec. 5 code, emit the profile signal, close; never emit a pre-ACTIVE `result` or second `hello`.
- Wire: no new `Frame` variant. TCP/TLS: close. HTTP/HTTPS: status per `http.md` Sec. 1E. WS/WSS: close code per SNTR-WS-081/SNTR-WSS-081.
- Security: untyped closes leak less than verbose errors (oracle minimization, SNTR-ASEC-011). Carrier tables must not introduce reason oracles.
- Compatibility: clarification within v1, no wire change. The alternative (new capability-gated handshake-error record) would be minor-additive with a B7 binding and is deferred.
- Proposed cases: version-mismatch single-code matrix (existing CONF-SESS-010/CONF-CORE-005 narrowed to one code when D3 lands); per-profile carrier table test (TCP close / HTTP 400-401 / WS 1002-1008) asserting local code + wire signal pairs.
- Maintainer approval required: yes (normative rewording + architecture Sec. 12.1 illustration fix + WS-041 parenthetical removal + errors.md Sec. 1D refresh).

### B2 pre-ACTIVE notification handling (RFC 0003 Decision D2)

- Conflict: `events.md` SNTR-EVENT-005/900 (ignore with diagnostic) vs `handshake.md` SNTR-HS-012/900 and `framing.md` SNTR-WIRE-003/011 (failure and close).
- Proposed behavior: fail-close suite-wide. A host sending pre-ACTIVE events is already in violation; fail-close is the only policy observable without trusting the violator. Align `events.md`, `handshake.md`, `framing.md`, and ADR-007 (which currently contradicts both by saying ignore-or-reject per a forthcoming stream spec).
- Initiator: treat a pre-ACTIVE `notification` as handshake failure (`FAILED_PRECONDITION`) and close; record a diagnostic locally; never treat it as a subscription.
- Host: never send pre-ACTIVE `notification` (existing MUST); on detecting its own violation path, close.
- Wire: no change; existing close/status codes apply.
- Security: removes a trust-the-violator policy; no new surface.
- Compatibility: behavioral tightening within v1 (buggy hosts that relied on tolerance will now see closes). Documented as a clarification with migration note "hosts sending pre-ACTIVE events were already non-conformant."
- Proposed cases: pre-ACTIVE notification matrix asserting close on all profiles (replacing the ignore half of CONF-EVT-014); update CONF-WS-011/016 notes accordingly when accepted.
- Maintainer approval required: yes.

### B3 stale request_id reuse and duplicates (RFC 0004 Decision D1 + D2)

- Conflict: core permits reuse after terminal result (`rpc.md` SNTR-RPC-002/010, `framing.md` SNTR-WIRE-010) while replay security rejects stale IDs after completion (`replay-protection.md` SNTR-RPL-012) and forbids cross-connection reuse (`SNTR-RPL-020`).
- Proposed behavior: bounded non-reuse window. Hosts remember terminal IDs for a documented bounded window (entry count and/or seconds, deployment-documented with caps) and reject in-window reuse as stale (`FAILED_PRECONDITION`, not executed); reuse older than the window is accepted as a new attempt. HTTP exchanges are explicitly exempt (per-exchange independence per SNTR-HTTP-073 is the lawful specialization; no cross-exchange rejection).
- Initiator: use fresh IDs whenever in doubt (client guide already advises this); never reuse across connections; correlate solely by ID; treat in-window rejection as stale-retry with a fresh ID and the same operation key where safe.
- Host: enforce duplicate-outstanding rejection (existing); enforce in-window stale rejection with bounded state; document the window; exempt HTTP exchanges explicitly.
- Wire: no change. Operation keys stay inside opaque payloads (no new core field; B11 defers it).
- Security: bounds attacker replay opportunity and host state (T4/T7). The HTTP exemption must not weaken persistent profiles.
- Compatibility: clarification within v1; window sizing is deployment configuration, not wire. Implementations that currently always-permit will newly reject in-window reuse (documented behavior change for buggy or aggressive reusers).
- Proposed cases: in-window stale-reuse rejection + aged-reuse acceptance fixtures on TCP/TLS/WS/WSS (new PROPOSED-CONF-RPC-013); HTTP independence fixture asserting no cross-exchange rejection (ties to existing CONF-HTTP-013).
- Maintainer approval required: yes (normative reconciliation + `rpc.md` Sec. 1B/4 and `replay-protection.md` Sec. 2/5 rewording).

### B4 protobuf unknown-field and oneof validation (no new decision; enforcement clarification)

- Conflict (apparent, not normative): `framing.md` SNTR-WIRE-002 says Protobuf enforces single-member oneof, but generated oneofs expose one decoded case while raw bytes may carry multiple alternatives (last-wins/merge for both `Frame.body` and `RpcResult.outcome`).
- Proposed behavior: accept standard merge semantics at decode, require bounded raw-wire validation where the requirement demands rejection (reserved tags, duplicate-body evidence). Post-decode inspection alone cannot prove single occurrence. This is already the posture of `reference.md` runtime-validation table and RFC 0001 B4; no new RFC decision is proposed beyond what B4 states. Runtime validators that must reject multi-alternative encodings observe raw fields before they are discarded, with explicit precedence over general unknown tolerance.
- Initiator/host: implement raw-field validation per SNTR-SER-008/SNTR-WIRE-008 with documented precedence; never claim generated codecs already reject multi-field input.
- Wire: no change.
- Security: prevents smuggled-alternative confusion; bounds allocation during raw scan.
- Compatibility: no wire change; stricter validators may reject inputs that lenient decoders previously accepted (that rejection is the specified behavior).
- Proposed cases: raw oneof-duplicate fixture (two `body` alternatives on the wire) asserting rejection per SNTR-WIRE-002/008; reserved-16/17 raw-tag fixture asserting malformed (ties to existing CONF-TCP-007 rows, made explicit).
- Maintainer approval required: yes for any normative rewording of SNTR-WIRE-002 implication text; no for running the proposed fixtures as informationals.

### B7 capability negotiation and wire binding (RFC 0005 Decision D1 + D2)

- Conflict: `capabilities.md` permits handshake-extension or negotiation-RPC binding per capability RFC, but no v1 binding exists; SNTR-RPC-008 references a nonexistent lower-bound negotiation; `serialization.md` SNTR-SER-020 calls for a credential-length bound with no value; method, `connection_id`, and diagnostic-text bounds are unvalued; close grace is unbounded.
- Proposed behavior: two parts. (i) Binding: no v1 negotiation binding at all for stable v1 (mandatory-only operation is the complete contract; strike CAP-002's application-level negotiation RPC sentence; any capability use before its RFC is a violation). The minimal binding becomes the named next RFC after v1, not part of stabilization. (ii) Bounds: credential bytes at most the envelope bound with 64 KiB default ceiling suite-wide (HTTP already uses it); `connection_id` at most 128 bytes UTF-8; `RpcError.message` at most 4 KiB; close grace default 5 s and maximum 30 s deployment-documented; delete the "unless negotiated" clause in SNTR-RPC-008 (floor is 16, period).
- Initiator/host: mandatory-only interop; never advertise, confirm, require, or probe unallocated identifiers (including `events-v1`, `events-replay-v1`, `resume-v1`); enforce the bound set before dispatch/policy lookup; document every bound and default.
- Wire: no change under option (i). Option (ii) (future binding) would be minor-additive with identifier/parameter/count/total-byte bounds, duplicate/unknown handling, confirmation timing, and per-connection scope.
- Security: bounded everything (T6/T7); no silent limit-raising; any future negotiation binding must be integrity-protected and downgrade-proof (T2).
- Compatibility: option (i) plus bound defaults are clarifications and documentation within v1. A future binding, new bound fields, or post-stable `go_package` change version per SNTR-VER-003.
- Proposed cases: mandatory-only interop fixture with no advertisement channel (existing CONF-CORE-006/007 plus CONF-EVT-002); per-bound accept/reject fixtures for each D2 maximum with mapped codes; MAX/MAX+1 serialized-byte boundary fixtures (see B8).
- Maintainer approval required: yes (normative CAP-002 rewording, bound values, RPC-008 clause deletion).

### B8 serialized envelope versus payload-size limits (RFC 0005 Decision D3)

- Conflict: SNTR-RPC-900 and SNTR-OPQ-900 ask for 1 MiB payload round trips inside a 1 MiB serialized envelope.
- Proposed behavior: rewrite the two rows as largest-payload-fitting-the-envelope plus explicit exactly-MAX and MAX+1 serialized-`Frame`-byte boundary fixtures. `security/test-plan.md` SNTR-STEST-007 already states the correct construction (count all tags/lengths/wrappers, adjust opaque payload lengths to reach the intended total; a MAX-byte payload alone is not a MAX-byte envelope). Extend that construction to the RPC/OPQ rows.
- Initiator/host: enforce the envelope bound on serialized bytes; never silently raise it for large payloads; size-check before sending.
- Wire: no change; the bound stays 1 MiB default.
- Security: preserves the DoS boundary (T6); raising the bound silently would move every test vector and analysis.
- Compatibility: fixture-text correction, no wire change.
- Proposed cases: exactly-MAX accepted (valid decode/state/auth/field limits) and MAX+1 / 2xMAX rejected with `RESOURCE_EXHAUSTED` (or 413 / close 1009 / closure per profile) on every profile; method/payload/credential/notification field-limit boundaries tested separately at their own maxima.
- Maintainer approval required: yes (normative fixture-text change in `rpc.md`, `opaque-payloads.md`, and manifest notes).

### B10 cancel, deadline, disconnect, and result races (RFC 0004 Decision D3)

- Conflict: `errors.md` SNTR-ERR-002 says `UNAVAILABLE` is the only code implying unknown handler outcome, but `reliability.md` SNTR-REL-001/003/009 and `rpc.md` server-after-deadline text leave `DEADLINE_EXCEEDED`/`INTERNAL`/`UNKNOWN` equally unknown; cancel-vs-deadline with no result has no precedence; local abandonment vs terminal delivery is described in two places (`rpc.md` Sec. 1G vs Sec. 4 tone).
- Proposed behavior: precedence + wording fix. Deadline-expiry wins when the budget elapsed, else cancellation wins; exactly one terminal code; the tie-break is logged locally. Reword ERR-002 `UNAVAILABLE` from the only code implying unknown outcome to the code reporting unknown outcome for loss/shutdown, noting `DEADLINE_EXCEEDED`/`INTERNAL`/`UNKNOWN` equally leave execution unknown. Completion-wins over late cancel is retained; late/unknown results follow `framing.md` SNTR-WIRE-011 vs `rpc.md` Sec. 4 (ignore + diagnostic, no storm).
- Initiator: return exactly one terminal code per RPC; document the tie-break; never interpret any of these codes as non-execution or idempotency proof.
- Host: same; stop or disregard remaining work best-effort on expiry/cancel unless the result already won.
- Wire: no change.
- Security: removes oracle and ambiguity surface; no new channel.
- Compatibility: clarification within v1.
- Proposed cases: cancel/deadline tie fixture asserting the single selected code (new PROPOSED-CONF-RPC-014; existing CONF-RPC-008 notes the tie-break as not asserted until decided); `UNAVAILABLE`-wording correction in `errors.md`.
- Maintainer approval required: yes.

### RFC 0002 authentication and session lifecycle questions (all PROPOSED, none accepted)

Mechanism negotiation: no identifier, advertisement, selection, or challenge fields exist; stable v1 stays opaque-credential presentation with application-side agility (distinct methods/endpoints chosen above Syntra) unless a capability RFC is accepted. Resumption standard: default v1 has no resumption; any resumption claim needs token format, entropy, audience/principal/time/version/capability binding, lifetime, rotation, replay windows, restored-state list, failure mapping, and revocation transport fully specified. Cross-transport binding: forbidden unless a resumption RFC explicitly allows the named profile pair with revalidated endpoint identity and no downgrade. HTTP profile bindings: transport RFCs embody `sessions.md` Sec. 1E principles (per-request `hello`-to-`ready` logic, no ambient-identity sessions, resumption only via RFC token). Revocation-propagation bound, channel-binding construction, proxy propagation format: per `security/open-questions.md` items 1-4; unchanged by this review. Each item needs its RFC (or an explicit maintainer deferral with rationale per `GOVERNANCE.md` Sec. 6) before stable. No `.proto` change is proposed for any of them.

## 4. Phase 3 WSS profile (SNTR-WSS-H1-V1) completeness check

Checked against the 14 required behaviors; citations are to `secure-websocket.md` (which incorporates `websocket.md` Sec. 1B-1L by reference where not restated).

- TLS minimum and upgrade behavior: DEFINED. TLS 1.3 via established implementation, no lower negotiation, no custom TLS (SNTR-WSS-110, SNTR-TSEC-002). Upgrade is HTTP/1.1 `GET /syntra/v1/ws` to 101 before any Syntra byte (SNTR-WSS-010/040/041). Downgrade forbidden both layers (SNTR-WSS-113).
- Required subprotocol identifier: DEFINED. `syntra.v1`, client offers first, server selects exactly it in 101, missing/unsupported/multiple handling per SNTR-WS-020-023, ALPN `http/1.1` with fail-closed mismatch (SNTR-WSS-020/021).
- Frame to binary-message mapping: DEFINED. Exactly one complete binary message (opcode 0x2, reassembled) contains exactly one serialized `Frame`; binary only; empty binary invalid; decode after assembly; bound enforced during assembly (SNTR-WSS-030, SNTR-WS-030-035).
- Maximum serialized message size: DEFINED. Effective maximum envelope size, default 1 MiB, enforced during assembly with 1009 + `RESOURCE_EXHAUSTED` (SNTR-WSS-030/031, SNTR-WS-035). Field-specific maxima remain open per F-12/B7.
- Handshake timeout: DEFINED with one gap. Syntra timer default 5 s starts at WSS establishment, not TCP connect (SNTR-WSS-041). Deployments should additionally bound TLS establishment itself and must document the value; TLS/TCP start-point binding is open per F-19.
- Authentication ordering: DEFINED. No Syntra byte before TLS completion and 101; credential only in `ClientHello.credential` after WSS establishment; 101 proves nothing about auth (SNTR-WSS-040/041/050/051). HTTP-layer admission, if used, is transport admission only with no privilege union (SNTR-WSS-050, SNTR-WS-051).
- Text frames: DEFINED. Opcode 0x1 invalid, close 1003, `UNIMPLEMENTED` context, no synthesized result (SNTR-WS-031/081).
- Fragmentation: DEFINED. Senders may fragment; receivers must reassemble before decode; boundaries carry no semantics; control frames interleaved at WS layer (SNTR-WS-033/034/073).
- Ping/Pong: DEFINED. WS Ping/Pong is the liveness mechanism; no Syntra heartbeat; echo, timeout, and close mapping documented; control frames never reach the core; TLS keepalive independent (SNTR-WSS-070, SNTR-WS-070-073).
- Read/write timeouts: DEFINED. Handshake timer, per-RPC timers, liveness timeout policy bounded and documented, write-grace before closing on slow receivers (SNTR-WSS-041/100, SNTR-WS-072/101/102). Numeric liveness/write-grace values are deployment-documented, which is the specified posture.
- Connection close: DEFINED. Graceful sequence stop-RPCs, grace period, WS Close handshake over TLS, `close_notify`, TCP close; no `CloseSession` message; in-flight mapping to `UNAVAILABLE`/`CANCELLED`; state discarded (SNTR-WSS-080/081). Grace default/max open per F-18.
- Protocol error handling: DEFINED. Close-code table 1000/1001/1002/1003/1007/1008/1009/1011 with mapped Syntra contexts; reserved 1005/1006/1015 never sent; unknown application codes treated locally; trailing-garbage placement open per F-22 (proposed 1007 + `INVALID_ARGUMENT` with documentation).
- Backpressure and overload: DEFINED. Bounded queues, 16-concurrency minimum, documented limits, `RESOURCE_EXHAUSTED` for excess RPCs with usable connection, 1009/1011 for connection exhaustion, bounded write grace, stream-policy shedding, jittered backoff (SNTR-WSS-100, SNTR-WS-100-102).
- Reconnection responsibilities: DEFINED. New WSS connection requires new handshake; ID space, subscriptions, cursors, and in-flight RPCs do not survive; resumption only under negotiated RFC capability; cross-transport forbidden unless named; fresh `connection_id`; `connection_id`-as-credential rejected (SNTR-WSS-120).
- Application routing in transport spec: ABSENT (conformant). No methods, topics, filters, or payload semantics appear; subscription mechanics are referenced only as application RPCs after ACTIVE.

Net: the WSS profile is complete as a Draft except the bound values (F-12/F-18), timer start binding (F-19), carrier/table wording (B1/F-03, F-08, F-16, N-01), and trailing-garbage code placement (F-22), each tracked to its RFC decision above. No application routing is present.

## 5. Phase 4 RPC semantics verification

- Canonical naming: DEFINED (`rpc.md` SNTR-RPC-001 + Sec. 1C). `/package.Service/Method`, leading slash, exactly two slashes, non-empty segments, printable ASCII without spaces/control, byte-exact case-sensitive, no normalization. Neutral examples `/example.Echo/Echo`, `/example.KV/Get`. Dotted task forms are informal shorthand only.
- request_id scope: DEFINED with one open conflict. `uint64`, initiator-chosen, unique among outstanding RPCs on that connection only, nonzero for RPC, zero for hello/ready/notification, fresh space per connection and per HTTP exchange, operation keys separate inside payloads (`rpc.md` Sec. 1B, SNTR-RPC-002/007/010, SNTR-WIRE-003/010, SNTR-HTTP-073). Reuse-after-completion vs stale rejection is open B3 (see Sec. 3).
- Concurrent outstanding requests: DEFINED. Permitted and expected; out-of-order completion legal; correlation solely by ID; no FIFO assumption; minimum 16 per connection with documented maximum and `RESOURCE_EXHAUSTED` for excess (`rpc.md` Sec. 1E, SNTR-RPC-002/008). Lower-bound-negotiation clause open per F-11.
- Exactly one terminal RpcResult: DEFINED. Exactly one terminal `result` per accepted request; second `result` forbidden; missing `outcome` is `INVALID_ARGUMENT`, never success; interleaved notifications never complete an RPC (`rpc.md` Sec. 1A/1B, SNTR-RPC-002/006/020/030). Loss maps to local `UNAVAILABLE`, never a synthesized `result`.
- Success with explicitly selected empty payload: DEFINED. Selected empty `payload` outcome means success with empty output, distinct from unset outcome, at both codec and protocol layers (`framing.md` SNTR-WIRE-007, `rpc.md` SNTR-RPC-003/006/020, protobuf GOLD-PROT-RES-EMPTY-01).
- Unknown method handling: DEFINED. Valid envelope, unknown method: `result{error{UNIMPLEMENTED}}`, no dispatch, connection usable (`rpc.md` SNTR-RPC-030, CONF-RPC-005/006 pattern). Missing application targets are separately `NOT_FOUND` per documented mapping.
- Invalid method handling: DEFINED. Malformed path shape rejected with `INVALID_ARGUMENT` before dispatch, connection usable (`rpc.md` SNTR-RPC-001/030, Sec. 1C).
- Cancellation races: DEFINED except the open tie. Completion wins; unknown/completed cancel ignored; duplicate cancel ignored; best-effort interruption only, never rollback; terminal `result` always follows (`rpc.md` Sec. 1G, SNTR-RPC-005/021/031). Cancel-vs-deadline with no result is open B10.
- Deadline expiration: DEFINED. Every RPC has an effective deadline (`timeout_ms` or bounded documented host default); relative millisecond budget, no absolute timestamps, no clock sync; initiator timer at most the budget; responder measures post-validation pre-dispatch; expiry reports `DEADLINE_EXCEEDED`; effects unknown; local abandonment without `cancel` does not cancel the host (`rpc.md` Sec. 1F, SNTR-RPC-004/021). Maximum-budget overage policy (clamp vs `OUT_OF_RANGE`/`INVALID_ARGUMENT`) is deployment-documented; initiators accept either (F-22 robustness note to be recorded).
- Disconnect with unknown outcome: DEFINED. Abrupt loss maps to `UNAVAILABLE` for all in-flight RPCs with unknown outcome; never success, never proof of non-execution; retry only idempotent or operation-keyed with fresh IDs (`reliability.md` SNTR-REL-009, `rpc.md` Sec. 1I, `handshake.md` SNTR-HS-014).
- Non-idempotent retry: DEFINED. Core never retries automatically; retry table is non-binding guidance; automatic retry of non-idempotent operations without an operation key is non-conformant (`reliability.md` SNTR-REL-002/003, `rpc.md` Sec. 1H/1I). No exactly-once claim exists or is invented (`reliability.md` SNTR-REL-010).

## 6. Phase 5 optional notifications: negotiated capability vs deferred

Inconsistency: `events.md` SNTR-EVENT-001/011 and `capabilities.md` SNTR-CAP-002/004 require negotiated support with `UNIMPLEMENTED` for unnegotiated use, while no event capability binding exists anywhere (`capabilities.proto` documentation-only, `events.md` Sec. 1A proposed identifiers `syntra.events/1` and `syntra.events.replay/1` explicitly unallocated, `profiles.yaml` SNTR-EVENTS-V1 notes placeholders must not be advertised, `conformance/README.md` Sec. 1.5 same rule, `claims.md` forbids naming them without an RFC reference). `CONF-EVT-014` (ignore pre-ACTIVE) and the B2 fail-close proposal pull the same fault line.

Decision path (PROPOSED, requires RFC 0005 Decision D1 acceptance): mandatory-only v1 for stable. No event or replay capability is allocated in v1; mandatory-only operation is the complete contract; CAP-002's application-level negotiation RPC sentence is struck; any capability use before its RFC is a violation with `FAILED_PRECONDITION`/`UNIMPLEMENTED` handling unchanged. The minimal capability binding becomes the named next RFC after v1. This keeps behavior consistent across core (`events.md` Sec. 1A + `capabilities.md`), schema (`events.proto`/`capabilities.proto` unchanged, no fields added), conformance (mandatory-only hosts pass absence rows as `UNSUPPORTED`; gated cases `SKIP`; no advertisement fixtures), and guides (`client-implementation.md` event handling, `server-implementation.md` backpressure, `implementer-guide.md` step 9 optionality). Replay cursors, event content, and application ordering stay outside Syntra (payload-embedded, application-versioned) unless an approved generic extension defines them; no replay store, cursor field, ACK, or stream-state record is added here. Alternative (define the full binding now) is rejected as a stabilization RFC for B7 scope reasons; see RFC 0005 Sec. 5.

## 7. Phase 6 conformance: coverage gaps and proposed cases (PROPOSED, not added)

Registered-ID coverage is 498/498 mapped with zero dangling references, but the following gaps prevent an execution claim. Proposed case IDs use a `PROPOSED-` prefix so they cannot be mistaken for accepted `CONF-` cases. None has been added to `conformance/manifest/*.yaml`, `conformance/requirements/*.md`, `conformance/test-vectors/`, or `conformance/interoperability/*`; adding them requires Accepted RFCs per the approvals below.

- G-01 prose-only IDs without manifest rows: CONF-AUTH-001-006 (`conformance/auth-session/authentication.md`) and CONF-ERR-001-004 (`conformance/errors/errors.md`) have no `manifest/*.yaml` counterparts (10 IDs). A YAML-only runner cannot execute them. Proposed: add `manifest/auth.yaml` and `manifest/errors.yaml` (or fold rows into existing manifests) with identical IDs when the owning RFCs land. Requirement: RFC 0002/0004 (auth) + RFC 0003/0004 (errors mapping) acceptance for any wording the rows depend on.
- G-02 un-ID'd normative MUSTs: clarifying subsections (`rpc.md` Sec. 1F/1G/1H, `events.md` Sec. 1D-1M, `sessions.md` Sec. 1A-1G, `handshake.md` Sec. 1A/1B/2A, `errors.md` Sec. 1A-1D, transport close-code/status-table rows) carry normative-strength MUSTs with no IDs and therefore no `requirements.yaml` rows. Proposed: mint IDs for the wire-behavior subset or explicitly mark the subsections informative, per audit L Sec. 3.3. Requirement: maintainer process decision (P1 against ADR-001).
- G-03 successful handshake: covered (CONF-SESS-001, CONF-CORE-008/010, CONF-WS-001/002, CONF-WSS-001, CONF-TCP-001, CONF-TLS-001, CONF-HTTP-001, CONF-HTTPS-001/002). No gap.
- G-04 version incompatibility: covered (CONF-SESS-010, CONF-CORE-005) but dual-code. Proposed PROPOSED-CONF-VER-011: single-code matrix asserting the RFC 0003 D3 selection on every profile. Requirement: RFC 0003 D3 acceptance.
- G-05 invalid credential: covered (CONF-SESS-002, CONF-SEC-004/005, CONF-AUTH prose). Executable coverage complete once G-01 lands.
- G-06 malformed protobuf: covered (CONF-SEC-002/003, CONF-TCP-007, CONF-HTTP-006, CONF-WS-008/011, protobuf EMPTY-FRAME-01). Add raw oneof-duplicate + reserved-16/17 raw-tag negativity explicitly (PROPOSED-CONF-SER-012) when B4 validation text is accepted.
- G-07 invalid oneof (missing outcome): covered client-side (CONF-RPC-010). Add host-side missing-outcome rejection row explicitly (same proposed case).
- G-08 frame-size boundary: covered as MAX+1/oversize (CONF-SEC-002, CONF-TCP-006, CONF-WS-008, CONF-HTTP-007, STEST-007) but not as exactly-MAX-accepted with valid decode/state/auth/field limits. Proposed PROPOSED-CONF-BOUND-013: exactly-MAX accepted + MAX+1/2xMAX rejected on every profile with allocation proof (extends STEST-007 construction). Requirement: RFC 0005 D3 acceptance.
- G-09 multiple in-flight RPCs: covered (CONF-RPC-002/003, CONF-WS-015, CONF-TCP-004, CONF-HTTPS-003). No gap.
- G-10 out-of-order results: covered (CONF-RPC-003, CONF-WS-015, CONF-HTTPS-003). No gap.
- G-11 duplicate and stale IDs: duplicate-outstanding covered (CONF-RPC-004); unknown-ID ignore covered (CONF-RPC-006, CONF-RPC-010 notes). Stale-after-completion races are intentionally unasserted until B3 lands. Proposed PROPOSED-CONF-RPC-013: in-window stale rejection + aged acceptance + HTTP exemption. Requirement: RFC 0004 D1/D2 acceptance.
- G-12 timeout and cancellation races: deadline covered (CONF-RPC-007), cancel-before/after covered (CONF-RPC-008 with completion-wins and unknown-ignore sub-rows), loss covered (CONF-RPC-012). The simultaneous cancel-vs-deadline tie is intentionally unasserted (open B10). Proposed PROPOSED-CONF-RPC-014 asserting the RFC 0004 D3 precedence. Requirement: RFC 0004 D3 acceptance.
- G-13 unknown methods: covered (CONF-RPC-005/009 pattern, CONF-HTTP-011, CONF-ERR prose). No gap.
- G-14 unsupported capabilities: covered (CONF-CORE-006/007, CONF-EVT-002/012). No gap once Phase 5 D1(i) wording lands.
- G-15 notification ordering constraints: covered as scope (CONF-EVT-006 records deployment behavior, asserts no global ordering). No stronger assertion is proposed; global ordering must never be claimed.
- G-16 slow receivers: covered (CONF-WS-017, CONF-EVT-007, CONF-SEC-011, STEST-009). No gap.
- G-17 abrupt disconnect: covered (CONF-WS-012, CONF-SESS-007, CONF-RPC-012, CONF-EVT-010, CONF-TCP-008, STEST rows). No gap.
- G-18 graceful close: covered (CONF-CORE-010, CONF-SESS-006, CONF-WS-010, CONF-WSS close rows, CONF-TCP-008). Close-grace numeric default/max remain open per F-18; no timing value is asserted beyond documented-behavior conformance.
- G-19 interop scenarios: covered in prose and matrix (INTEROP-CORE-2T two-transport proof, INTEROP-CORE-2I two-implementation WSS roleswap, INTEROP-HTTP-H1-H2 logical equality, INTEROP-EVENT-ABSENT mandatory-only refusal, XIMPL-HELLO-ECHO-EVENT, XIMPL-NEGATIVE-PAIR). Execution evidence is absent (no IUT runs, including the bootstrap one-implementation-plus-fixture path). Proposed: execute the WSS two-role interop leg with packet-fixture verification as the bootstrap evidence set when at least B1/B2/B3 pre-ACTIVE and ID semantics are decided; until then runs would encode undecided behavior.
- G-20 WSS-specific slow-TLS timer: proposed PROPOSED-CONF-WSS-011 (4 s TLS handshake + immediate hello succeeds; 6 s fails `DEADLINE_EXCEEDED`) once the F-19 start point is bound. Requirement: RFC 0003 timer binding.

## 8. Accepted, proposed, blocked decisions

- Accepted (pre-existing, unchanged by this review): ADRs 001-010; BSR module identity `buf.build/tinklecorp/syntra` (publication policy itself remains unaccepted).
- Implemented but unapproved (present in tree, not accepted as outcomes): charter SYN-ARCH charter text as proposed (pending maintainer approval as a document, but its content is not altered here); user-directed sole-source layout decision RFC 0001 B9 (implemented; FILE break documented, not approved as behavioral acceptance).
- Proposed (Draft RFC text as it stands, endorsed as the decision procedure, not as outcomes): RFC 0003 Decisions D1 (transport-native carrier), D2 (fail-close pre-ACTIVE), D3 (`UNIMPLEMENTED` version-mismatch), timer binding, F-08/F-16 doc corrections; RFC 0004 Decisions D1 (bounded non-reuse window), D2 (HTTP exemption + sessions Sec. 1B correction), D3 (deadline-wins-else-cancel + ERR-002 rewording), D4 (ASEC-003 carriage rewording), D5 (`FAILED_PRECONDITION` re-auth code); RFC 0005 Decisions D1 (no v1 negotiation binding), D2 (credential 64 KiB default / `connection_id` 128 bytes / message 4 KiB / grace 5 s default 30 s max / floor 16), D3 (fixture-text rewrite), D4 (identifier set as actually unified; audit-correction variant), D5 (neutral `go_package` at publication with migration notes).
- Blocked (must be resolved before stable; RC must list them per `RELEASE.md`): B1, B2, B3, B4 (validation-text implication), B7 (binding + bounds), B8, B10; RFC 0002 items 7-11 (mechanism negotiation if claimed, resumption standard if claimed, cross-transport binding if claimed, HTTP bindings embodiment, revocation/channel-binding/proxy items); F-05 (`go_package` path); F-06 (fixture text); F-14/F-16/F-20/F-21/F-22 doc corrections (non-normative bar but release-checklist items); G-01/G-02 conformance ID gaps; `LICENSE` absence (`GOVERNANCE.md` Sec. 7); unaccepted publication policy; zero executed interop runs (stable bar; RC procedure ready but tag forbidden until BLOCKED clears).

## 9. Compatibility and release-readiness assessment

- Wire compatibility: preserved. This review makes no `.proto` edit, no field renumbering, no reservation reuse, no new variant, no code allocation, and no semantic reinterpretation. `buf lint`, `buf build`, `buf breaking --against compatibility/v1-initial/image.json`, and the 13 `tests/schema` checks pass on the reviewed tree.
- Source compatibility: unchanged from the reviewed baseline. The known FILE break from the implemented sole-source layout (RFC 0001 B9) stands as documented; no new source break is introduced here.
- Behavioral compatibility: unchanged. All B1-B10 resolutions are recorded as proposals with explicit old-vs-new wording and migration implications in their RFC sections; none is applied. The two tightenings to flag at acceptance time are B2 (fail-close may newly close buggy hosts that relied on tolerance) and B3 (bounded non-reuse may newly reject aggressive ID reusers in-window). Both are documented as clarifications of already-non-conformant behavior, not silent changes.
- BSR impact: none from this review (no schema edit, no push performed, no tag created, no label moved). F-05 remains the publication blocker alongside the unaccepted publication policy.
- mTLS/authz impact: none (no authentication, authorization, transport-security, or error-sanitization rule changed). All credential, principal-isolation, disclosure-hygiene, and bound-enforcement rules are restated, not altered.
- PII logging risk: none introduced. No new logging, metric-label, or diagnostic-content rule is added; hygiene negative-grep rows are restated.
- Resource bounds: none altered. Bound values are proposed (RFC 0005 D2) but not set; allocation-before-parse, depth-32, and 1 MiB envelope posture are unchanged.
- Release readiness: NOT READY for stable (six P0 findings F-01-fixed-aside then F-02-F-06 live, 13 P1 findings, 11 SESSION-OPEN-QUESTIONS items, 5 Draft RFCs, no `LICENSE`, no publication policy, zero executed interop runs). NOT READY for RC tag either: `RELEASE.md` Sec. 1 checklist items for core/auth-session/RPC/events/transports/conformance/BSR/license remain BLOCKED per `audits/v1-release-readiness.md`, whose verdicts this review confirms except for the F-01 reclassification. The RC procedure itself (checklist, validators, artifact script, workflows) is ready; the tag must not be created until the BLOCKED items clear.

## 10. Explicit approval requests (no edit made without them)

- A-01: audit-correction doc patch closing F-01 across `audits/v1-consistency-review.md`, `audits/v1-release-readiness.md`, `audits/v1-implementer-questions.md` Q48, and RFC 0005 D4 text to the unified set actually present. Non-normative; requests one-maintainer approval per `GOVERNANCE.md` Sec. 3.
- A-02: filename-correction doc patches for F-20/N-02 (`core/errors.md`, `core/framing.md`, `core/protocol.md` appendix, `security/threat-model.md`, `security/authentication-security.md` Sec. 1 header). Non-normative; requests one-maintainer approval.
- A-03: normative doc patches for F-14 (sessions Sec. 1B HTTP row), F-16 (errors Sec. 1D), N-01 (WS-041 parenthetical), architecture Sec. 12.1 illustration (F-08), `core/requirements.md` counts + `core/conformance.md` trace table + `http.md`/`https.md` CONF ranges (F-21). Each requests a normative RFC bundle (proposed: RFC 0003/0004 alignment bundles) with quorum + security review where applicable.
- A-04: RFC 0003 Decisions D1/D2/D3 + timer binding + B1/B2/F-09/F-19 conformance cases (Sec. 7 G-04/G-06/G-20 and carrier-table test). Requests RFC 0003 acceptance (quorum + security review).
- A-05: RFC 0004 Decisions D1-D5 + B3/B10/F-10/F-13/F-15 conformance cases (PROPOSED-CONF-RPC-013/014, G-11/G-12, carriage rewording). Requests RFC 0004 acceptance (quorum + security review).
- A-06: RFC 0005 Decisions D1-D5 + B7/B8/F-11/F-12/F-17/F-18 + G-08 boundary fixtures + neutral `go_package` migration. Requests RFC 0005 acceptance (quorum + security review); D5 additionally needs major-or-prestable handling with `CHANGELOG.md`/`MIGRATION.md` notes and BSR coordination.
- A-07: G-01 manifest additions (`manifest/auth.yaml`, `manifest/errors.yaml`) + G-02 ID minting or informative-marking + G-19 bootstrap execution. Requests conformance-suite RFC acceptance (or explicit maintainer deferral with rationale per `GOVERNANCE.md` Sec. 6 for any item left out of RC scope).
- A-08: `LICENSE` selection (`GOVERNANCE.md` Sec. 7) and publication-policy RFC acceptance. Requests maintainer decisions before any `buf push` or tag.

No Tinkle Messenger types or methods are introduced or referenced beyond this sentence. No RFC is declared accepted. No tag was created. No `buf push` was performed.
