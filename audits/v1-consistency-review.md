# Adversarial Consistency Review — Syntra v1 (independent-implementer view)

- Role: independent implementer with only the public repository. No protocol implementation was written; no behavior was assumed from code.
- Read: `proto/`, `specifications/` (all), `conformance/` (all), `rfcs/`, ADRs, README, SECURITY, GOVERNANCE (+ SUPPORT, CONTRIBUTING, CHANGELOG, MIGRATION).
- Companion detail docs: `v1-schema-spec-matrix.md` (audit B), `v1-implementer-questions.md` (audit I, 56 questions), `v1-conformance-coverage.md` (audit L).
- Already-known blockers B1–B11 (RFC 0001 §10) and SESSION-OPEN-QUESTIONS items were independently re-verified; this review confirms them and adds new findings F-01…F-22.
- Severity: P0 = security/interop blocker (must fix before v1) · P1 = major ambiguity · P2 = documentation problem · P3 = editorial. Per instructions, no architecture is rewritten to fix P0/P1; RFC proposals are the path.

## A. Cross-document concept audit

| Concept | Verdict | Notes |
|---|---|---|
| Protocol version | CONSISTENT | `Frame.version` + `min/max_version`, highest-overlap selection everywhere. Only divergence: two lawful mismatch codes (F-09, P1). |
| Session ID | CONSISTENT (absent by decision) | None exists in v1; `connection_id` explicitly excluded everywhere (SNTR-SESS-002, §1B table). One stale table row claims it "travels inside `ServerReady`" over HTTP, where no `ServerReady` frame exists (F-14, P1). |
| `request_id` | CONTRADICTORY | Core permits reuse after terminal result (SNTR-RPC-002/010, SNTR-WIRE-010); replay security rejects stale reuse (SNTR-RPL-012) and forbids cross-connection reuse (SNTR-RPL-020). F-02, P0 (confirms B3). |
| Operation ID | CONSISTENT (absent by decision) | No core field; payload-embedded; never conflated with `request_id` (SNTR-RPC-007/010). |
| Capability ID | SHAPE-DEFINED, BINDING-MISSING | ASCII versioned shape exists (SNTR-CAP-001) but no advertisement/confirmation wire binding exists, while CAP-002/004 presume advertisement (F-17, P1; confirms open-questions blocker 1). |
| Event / stream ID / cursor | CONSISTENT (absent by decision) | No wire fields (SNTR-EVENT-002/003/009, events.md §9). |
| Error codes | CONSISTENT | Registry 0–16 exact in schema and spec; task-example names correctly unallocated with mapping table. |
| Transport profile IDs | CONTRADICTORY | Specs: `SNTR-HTTP-V1`, `SNTR-WS-V1`, `SNTR-WSS-V1`. Conformance suite: `SNTR-HTTP1-V1`, `SNTR-WS-H1-V1`, `SNTR-WSS-H1-V1`. F-01, P0. |
| Authentication mechanism | CONSISTENT (absent by decision) | No mechanism identifier/negotiation (SNTR-AUTH-001/004, §1A). Carriage reconciliation gap on HTTP (F-10, P1). |

## New findings catalog (F-01…F-22)

P0 — fix before v1, RFC required:
- F-01 transport profile identifier mismatch (§A table). → RFC 0005.
- F-02 `request_id` reuse permission vs stale-ID rejection. → RFC 0004.
- F-03 no lawful pre-ACTIVE typed-handshake-error carrier (B1 confirmed; TCP/TLS hosts cannot surface the §5 code on the wire, so SNTR-HS-020 "surface the typed code" is unimplementable there). → RFC 0003.
- F-04 HTTP per-exchange `request_id` amnesia (SNTR-HTTP-073) vs SNTR-RPL-012 stale rejection: HTTP hosts are forbidden the memory the security rule needs. → RFC 0004.
- F-05 private-organization import path in all seven proto files (`go_package …tinklehq…`) + org references in SECURITY/SUPPORT/CONTRIBUTING vs SYN-ARCH-001/062 independence; BSR consumers would import a private path. → RFC 0005.
- F-06 1 MiB payload fixtures (SNTR-RPC-900, SNTR-OPQ-900) cannot fit the 1 MiB envelope (B8 confirmed at fixture level). → RFC 0005.

P1 — major ambiguity, RFC or normative doc patch required:
- F-07 pre-ACTIVE `notification`: three-way divergence — events.md ignore-default vs SNTR-HS-012 fail/close vs ADR-007 "ignore-or-reject per forthcoming stream spec" (B2 confirmed + ADR conflict). → RFC 0003.
- F-08 architecture §12.1 depicts handshake failure as `Frame{result…}`, the exact pattern B1 forbids. → RFC 0003 (charter illustration fix).
- F-09 version-mismatch code choice (`UNIMPLEMENTED` or `FAILED_PRECONDITION`). Interop-safe (both close) but untestable-as-one; unify. → RFC 0003.
- F-10 ASEC-003 "credentials ONLY in `ClientHello.credential`" vs HTTP `Authorization` binding (SNTR-HTTP-060/061). Strict reading outlaws the HTTP profile. → RFC 0004.
- F-11 SNTR-RPC-008 "unless a lower bound was negotiated" with no negotiation mechanism anywhere (reference.md confirms). Dead clause; sub-16 implementations have no lawful path. → RFC 0005.
- F-12 missing field-specific bounds: credential, method (delegated OK), `connection_id`, `RpcError.message` lengths; limit-override binding (B7 confirmed). DoS-relevant. → RFC 0005.
- F-13 re-auth-on-same-connection attempt has no specified code (AUTH-010 forbids; §4 silent). → RFC 0004.
- F-14 sessions.md §1B "connection_id travels inside `ServerReady`" over HTTP profiles is false — HTTP carries no `ServerReady` frames (SNTR-HTTP-020). → doc patch (RFC 0004 HTTP reconciliation).
- F-15 cancel/deadline/`UNAVAILABLE` race precedence (B10 confirmed). → RFC 0004.
- F-16 errors.md §1D "no [status] mapping is finalized here" is stale; HTTP/HTTPS mappings are finalized. Authority confusion. → doc patch (RFC 0003 alignment).
- F-17 capability advertisement presumed but unwired (see §A). → RFC 0005.
- F-18 close grace period has no default/max anywhere; unbounded CLOSING is lawful (T7 tension). → RFC 0005.
- F-19 TLS/TCP handshake-timer start point unbound (TCP-connect vs TLS-complete; WSS binds it, TLS/TCP does not). → RFC 0003.

P2 — documentation problems (doc patches, no RFC unless disputed):
- F-20 wrong schema filenames: `error.proto` for `errors.proto` (errors.md, framing.md, protocol.md, threat-model.md); `session.proto` cited as home of `Frame` (framing.md) and `ClientHello`/`ServerReady` (authentication-security.md).
- F-21 SYN-ARCH-* (25 IDs) with zero conformance mapping; 10 prose test IDs without manifest cases; un-ID'd normative MUSTs unmapped; stale counts (core registry "~130" vs 179; `CONF-HTTP-001…016` vs 18; `CONF-HTTPS-001…012` vs 14). See coverage doc.
- F-22 assorted divergences/ambiguities: WS credential-query tolerance (ignore) vs HTTP 400 (query-shape philosophy differs per profile); WSS-011 server behavior on credential-in-query unspecified; WS trailing-garbage close code (1002 vs 1007); HTTP empty-`Authorization` 401 vs core empty-credential anonymous; `OUT_OF_RANGE` vs `INVALID_ARGUMENT` for over-max budgets (initiators must accept both — unstated robustness rule); H2 Content-Length/chunked language is H1-specific; HTTP 504 in retry table never sent; core conformance.md trace table lists nonexistent suite directories (`core/`, `handshake/`, …).

P3 — editorial: SER-002 "length-prefix variations" (protobuf has none — framing's prefix, not serialization's); packed/unpacked fixture vacuous (no repeated fields); "1 MiB" unit consistency; version-mismatch dual codes (also F-09).

## C. State-machine audit (edge transitions)

| Attempt | Expected behavior (cited) | Gap? |
|---|---|---|
| `request` before `hello` | Handshake failure `FAILED_PRECONDITION` + close (SNTR-HS-012) | None |
| Second `hello` | Same as above | None |
| Auth after ACTIVE (re-auth RPC) | Forbidden (SNTR-AUTH-010); **no code specified** | F-13 |
| `ServerReady` sent by initiator / `ready` received by host | Handshake failure (SNTR-HS-012) | None |
| Close during AUTHENTICATING (client transport close) | Abort; timers/loss mapping per table | None (client-side abort path lawful) |
| Event before subscription (ACTIVE, unsubscribed) | Ignored unless a subscription exists; subscription required (SNTR-EVENT-001/004) | None |
| Event before ACTIVE (pre-`ready`) | Divergent | F-07 |
| `result` for unknown ID | Ignore + diagnostic | Collides with F-02 for completed IDs |
| Resume on an already-ACTIVE connection | No resume message exists; any `hello` in ACTIVE → violation + close | None (by absence) |
| `cancel` with `request_id == 0` | WIRE-003 violation → protocol error | None |
| `hello` with `min > max` / zero versions | "Oversize/malformed hello" → `INVALID_ARGUMENT`/`RESOURCE_EXHAUSTED` + close (table; SNTR-HS-030 shape check) | None |
| `Frame.version = 0` post-handshake | Version mismatch → failure + close (§5 table) | None |

## D. Version-negotiation audit (deterministic outcomes)

- 1–3 vs 1 → select 1, recorded in `Frame.version` (SNTR-HS-010). Deterministic.
- 2 vs 1 → failure + close, code host's choice (F-09). Terminating either way: interop-safe, test-ambiguous.
- Unknown future capability, optional-only → ignored, handshake proceeds (SNTR-CAP-004). Deterministic (channel presumed — see F-17).
- Required-but-unsupported → `UNIMPLEMENTED` (handshake-gated: failure + close). Deterministic.
- Unknown future protobuf field → ignored (SNTR-SER-003). Deterministic at decode; retention differs by language (audit K).
- Unknown enum value (e.g., future `ErrorCode`) → map to `UNKNOWN` for reporting, preserve numerically, never success (SNTR-ERR-005). Deterministic at policy layer; codecs do not auto-map (documented).

## E. Transport equivalence

Application RPC semantics are preserved across TLS/TCP, HTTPS/H1, HTTPS/H2, WSS/H1: same `Frame` validity, same `result` correlation, same error codes, same retry/unknown-outcome rules. Legitimate, documented differences: framing (length-prefix vs message vs per-exchange body); handshake-error carrier shape (close vs status vs WS code — all divergent pending F-03); correlation scope lifetime (persistent connection vs per-exchange IDs, with F-04 conflict); concurrency unit (connection vs H2 stream, both ≥16); cancellation (native `cancel` frame vs HTTP abort-is-abandonment); events (streams on persistent transports, none on plain HTTP); failure signals (`REFUSED_STREAM` definitely-not-executed exists only on H2); redirect handling (WS conditional vs HTTP never-auto vs WSS re-validate); query strictness (WS tolerate vs HTTP 400 — F-22). No transport redefines `Frame` semantics (SYN-ARCH-042 holds), except the F-14 false row.

## F. Error consistency

Single registry, single meanings (SNTR-ERR-002); protocol-vs-RPC table (errors.md §1C) agrees with handshake §5 and transport tables on every sampled row. Two live conflicts: pre-ACTIVE carrier absence (F-03 — every "handshake error CODE" row names a code with no lawful envelope) and errors.md §1D staleness (F-16). `UNAVAILABLE`-implies-unknown vs ERR-002's "only code that implies unknown outcome" vs reliability's "error outcomes prove nothing about execution" (B10, F-15): the word "only" overclaims — `DEADLINE_EXCEEDED`/`INTERNAL`/`UNKNOWN` equally leave execution unknown. Recommend striking "only" (RFC 0004).

## G. Limits consistency

Envelope bound 1 MiB serialized `Frame` is stated identically in core (WIRE-006), TCP (005), WS (035), WSS (by reference), HTTP (110). No contradictory constants found. Gaps, not contradictions: no per-field maxima (F-12); no lower-bound negotiation mechanism (F-11); no grace-period default/max (F-18); payload-vs-envelope fixture conflict (F-06); maximum call budget and idle/session lifetimes deployment-defined (consistent, documented).

## H. Security audit

- Plaintext credential exposure: forbidden on plaintext profiles (TSEC-009, TCP-008, WS-052, HTTP-150/062); enforced by channel rules + negative-grep STEST-900. Residual: WS credential-in-query ignored-not-rejected (F-22); `go_package` path and doc links to a private org (F-05).
- Unauthenticated protected RPC: denied pre-dispatch everywhere (AUTH-030, RPC-032, ASEC-022, HTTP-170). Consistent.
- Session fixation: fresh `connection_id`, never accepted as auth, no client-chosen state (SESS-002/010/020, ASEC-010). Consistent; HTTP has no `connection_id` at all (F-14 row is false but fail-safe).
- Token replay: five-class separation enforced; TLS≠idempotency explicit. F-02/F-04/F-15 bound the residual races.
- Downgrade: version/transport/capability refusal consistent (VER-007, TSEC-007, WSS-113, HTTPS-013/083); downgrade-proof fixtures exist. Residual: dual mismatch codes (F-09).
- Hostname validation: SAN-preferred, CN-fallback-per-6125, verify-before-credential, consistent across TLS/WSS/HTTPS (TSEC-004, TLS-004, WSS-112, HTTPS-012).
- WSS→WS downgrade: forbidden + no auto-retry (WSS-113, TSEC-007). Consistent.
- Redirect credential leakage: HTTP never-auto + six manual conditions; WS conditional + no-forward; WSS re-validate + no-forward (014/101/WSS-013). Consistent.
- Unbounded arrays/strings/bytes: no `repeated`/`map` in IDL; all bytes bounded by envelope + depth-32 + pre-allocation rules. Residual: field-specific maxima absent (F-12).
- Memory exhaustion: fail-closed oversize handling per transport (TCP close, HTTP 413/431, WS 1009, H2 reset/429/503). Consistent; grace-period unboundedness is the hole (F-18).
- Compression: default-off everywhere with bomb caps where enabled (HTTP-120/121, WS-090…092). Consistent; TLS 1.3 has none.
- Unknown message handling: unknown fields ignored, unknown variants rejected, never silent (SER-003, WIRE-004, ARCH-021). Codec limit B4/B6 documented. Consistent as policy; enforcement needs raw-wire validation (known).

## J. Two-implementation simulation (divergence table)

| Ambiguity | Team A (reasonable) | Team B (reasonable) | Interop result | Disposition |
|---|---|---|---|---|
| ID reuse after terminal result | Permits (core text) | Rejects as stale (RPL-012) | A-initiator reusing IDs against B-host gets `FAILED_PRECONDITION`; safe but surprising; reverse works | P0 (F-02) |
| Pre-ACTIVE `notification` | Ignores + diagnostic | Closes connection | Same behavior toward conformant hosts (never send); differs toward buggy hosts | P1 (F-07) |
| Version-mismatch code | `UNIMPLEMENTED` | `FAILED_PRECONDITION` | Both close; initiator handles both | P1→P3 after unification (F-09) |
| Over-max timeout budget | Clamp | Reject `OUT_OF_RANGE` | Initiator must accept either; unstated | P2 (F-22 robustness rule) |
| Close grace duration | 100 ms | 30 s | In-flight results may/may not arrive; both map the remainder to `UNAVAILABLE`/`CANCELLED` | P2 (F-18) |
| Cancel/deadline tie | `CANCELLED` | `DEADLINE_EXCEEDED` | Retry-safety classification differs for the same race | P1 (F-15) |
| Credential-in-query (WS) | Ignore + proceed | Reject 400 (HTTP-style) | Same-host cross-profile inconsistency | P2 (F-22) |
| Profile identifier claimed | `SNTR-WS-V1` | `SNTR-WS-H1-V1` | Declarations mutually unintelligible | P0 (F-01) |
| Unknown-field retention (proxy) | Drop (Prost) | Preserve (Go) | Re-emitted bytes differ; decoded meaning identical | P2 note (audit K) |

## K. BSR consumer audit

Consuming the module purely via BSR-generated bindings is sufficient for message types and insufficient for the protocol (by design; schema-registry §6). No spec depends on local `bindings/` layout, `go_package`-derived paths for semantics, private build systems, or helper APIs — with two exceptions: (1) `generation.md` ties the handwritten `bindings/go/go.mod` to the published `go_package`, which embeds the private org path (F-05) — BSR Go consumers would import `github.com/tinklehq/…`; fix by neutralizing the path at publication. (2) Conformance manifests and test vectors assume repo-relative paths; that is acceptable (they are consumed from the repo, not BSR) but BSR-only consumers need the equivalent fixture bytes — recommend publishing the golden vectors alongside the module description.

## M. Release blockers (final classification)

P0 (6): F-01, F-02, F-03, F-04, F-05, F-06 — each has an RFC proposal below. No v1 release while any stands.
P1 (13): F-07…F-19 except F-16/F-14-doc-parts (doc patches tracked in F-21) — RFC proposals below.
P2/P3: F-20…F-22 + editorial notes — documentation patches, no RFC unless disputed.

Acceptance criterion "no known unresolved P0 before v1 release": NOT MET today — six P0s are known and unresolved. The RFC proposals in `rfcs/0003…0005` are the resolution path, not the resolution.
