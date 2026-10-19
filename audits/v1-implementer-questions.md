# Audit I — 56 Implementer Questions (Syntra v1)

Each question an independent implementer (public repo only, no Rust access) would ask. Answers cite the specification; unanswerable items are marked SPECIFICATION GAP with a disposition (documentation patch or RFC issue, cross-referenced to findings F-01…F-22 in `v1-consistency-review.md`).

## Handshake and versioning

1. Can I reuse `request_id` 10 after receiving its response? — Both permitted (SNTR-RPC-002/010, SNTR-WIRE-010) and rejected-as-stale (SNTR-RPL-012). SPECIFICATION GAP (B3, F-02) → RFC 0004.
2. I support versions 1–3, the host supports 1. What is selected, and where is it recorded? — Highest overlap = 1, in every post-handshake `Frame.version` (SNTR-HS-010, SNTR-VER-002).
3. I support only version 2, the host only 1. What happens, and which code? — Handshake failure + close; code is `UNIMPLEMENTED` or `FAILED_PRECONDITION` at the host's choice (handshake.md §5). Either is conformant; initiators must accept both (F-09) → RFC 0003 (unify).
4. Can I send a second `hello` to renegotiate? — No: handshake failure `FAILED_PRECONDITION` + close; re-handshake on the same transport is forbidden (SNTR-HS-012/040).
5. The host sends `ServerHello`. What do I do? — No such message exists (§2A rule 2); an unknown variant MUST be rejected with `UNIMPLEMENTED` (SNTR-WIRE-004).
6. I receive a handshake rejection. Which `Frame` carries the typed code? — SPECIFICATION GAP (B1, F-03): no legal pre-ACTIVE carrier exists; surface locally and close. → RFC 0003.
7. How long do I wait for `ready` before giving up? — Bounded handshake deadline, default 5 s (SNTR-HS-002/011); abort with `DEADLINE_EXCEEDED`.
8. On TLS/TCP, does the 5 s timer start at TCP connect or TLS completion? — SPECIFICATION GAP (F-19): TCP starts at CONNECTED; TLS profile does not bind the start point; WSS starts at WSS establishment. → RFC 0003.
9. Can the host change `Frame.version` mid-connection? — No: must equal the selected version for the connection lifetime (SNTR-HS-005/010, SNTR-WIRE-021); attempt → `FAILED_PRECONDITION` + close.
10. A future peer sends an unknown `Frame.body` variant. Drop it? — Never silently drop: `UNIMPLEMENTED` where a context exists, else close during handshake (SNTR-WIRE-004, SYN-ARCH-021).

## Correlation, RPC, cancellation, deadlines

11. Are responses guaranteed in request order? — No: correlate solely by `request_id`; out-of-order completion is legal (rpc.md §1E, SNTR-RPC-002).
12. I get a `result` for an ID I never sent (or already completed). What do I do? — Ignore locally with a diagnostic; no error storm, no completion signaled (rpc.md §1B/§4). Note: "completed" collides with F-02 — an ID arriving after its terminal result is simultaneously "unknown" (ignore) and "stale replay" (reject). → RFC 0004.
13. My handler finishes at the same moment a `cancel` arrives. Which result wins? — Completion wins; the success (or application-error) result is delivered, not `CANCELLED` (rpc.md §1G).
14. Cancellation and deadline expiry are both pending with no result. Which code? — SPECIFICATION GAP (B10, F-15): exactly one terminal code, tie-break documented by the implementation. → RFC 0004.
15. `cancel` arrives for an unknown or completed ID. Error? — No: ignore it (SNTR-RPC-005) to tolerate races.
16. Does abandoning an RPC locally cancel it on the host? — No: local abandonment without an explicit `cancel` does not cancel the host (SNTR-RPC-004/021).
17. `timeout_ms = 0` — how long do I wait? — The host's bounded, documented default (SNTR-RPC-004, §1F); there is no suite-wide default value. Ask the deployment; always send nonzero for determinism.
18. What is the maximum call budget? — Deployment-documented; over-maximum is clamped or rejected (`OUT_OF_RANGE`/`INVALID_ARGUMENT`) per documented policy (rpc.md §1F). Initiators must accept either code.
19. The handler already committed effects, then the deadline fires. Roll back? — Never interpret cancellation/deadline as rollback (SNTR-RPC-005/031, §1F).
20. Can I send 32 concurrent RPCs? — You must support at least 16; beyond the documented max the host rejects excess with `RESOURCE_EXHAUSTED` (SNTR-RPC-008). Note: "unless a lower bound was negotiated" has no negotiation mechanism (F-11) → RFC 0005.
21. My method name is 900 bytes. Legal? — No separate v1 bound; it must fit the envelope, and deployments may cap it (rpc.md §1C). No universal answer exists.
22. Is `/example.Echo/Echo` the same method as `/example.echo/echo`? — No: byte-exact, case-sensitive, no normalization (rpc.md §1C).

## Sessions, authentication, principals

23. Where is the session ID on the wire? — Nowhere: v1 defines no session identifier (SNTR-SESS-002, sessions.md §1B).
24. Can I send `connection_id` back to resume? — No: reject as credential/resumption token; fresh handshake required (SNTR-SESS-002/006/020).
25. Same credential, new connection — same session? — No: new connection = new session, even for the same principal (sessions.md §1A).
26. Can I re-authenticate on the same connection with a new credential? — Forbidden by default; close and reconnect (SNTR-AUTH-010). Which code a post-ACTIVE re-auth RPC yields is unspecified (F-13) → RFC 0004.
27. The principal is revoked mid-connection. What do I observe? — Affected RPCs fail `UNAUTHENTICATED`; the connection closes by default (SNTR-AUTH-008, §1C). Propagation delay is deployment-documented (open-questions blocker 2).
28. Empty credential — valid or malformed? — Valid anonymous attempt on the wire; acceptance is host policy with least privilege (SNTR-AUTH-003). Exception: on HTTP, a present-but-empty `Authorization` parameter yields 401 while an absent header is the anonymous attempt (SNTR-HTTP-061) — per-profile difference, documented.
29. Can two connections share one principal's credential? — Each use is re-evaluated per connection; cross-connection authorization is forbidden (SNTR-AUTH-031, SNTR-RPL-020).
30. Where do I put the credential on HTTP? — Exactly one header, `Authorization: Syntra <base64>` (SNTR-HTTP-060). Strictly this refines ASEC-003's "only in `ClientHello.credential`" (F-10) → RFC 0004.

## Events, streams, replay

31. How do I subscribe? — One application-defined generic RPC after ACTIVE; the opaque `result` payload is the handle (events.md §1E).
32. What is my subscription's stream ID? — There is none on the wire; the opaque handle is connection-scoped and uninterpretable by the core (SNTR-EVENT-003).
33. A `notification` arrives before `ready`. What do I do? — SPECIFICATION GAP (B2, F-07): events default ignore-with-diagnostic; handshake/framing require failure. Record your behavior; never treat it as a subscription. → RFC 0003.
34. Can a `notification` complete my RPC? — Never (SNTR-EVENT-005, SNTR-CORE-012).
35. I get the same event twice. Protocol violation? — No: tolerate duplicates; no error storm (SNTR-REL-005, SNTR-RPL-014).
36. Are my two subscriptions' events ordered relative to each other? — No cross-stream ordering guaranteed (SNTR-EVENT-006).
37. How do I replay from last week? — Only under a negotiated replay capability with a documented cursor, retention, and strategy; otherwise re-subscribe live and accept the gap (events.md §1I). No replay capability exists in default v1.
38. My cursor expired. What code, and what now? — Documented `FAILED_PRECONDITION` or `NOT_FOUND`; re-subscribe from the documented point, never guess (events.md §1I).
39. Does the host have to store my events for replay? — No: a host without retention responds as if the cursor expired (or `UNIMPLEMENTED`) (events.md §1I).
40. Can the server push events over plain HTTP? — No: no delivery over request/response; no SSE/long-polling/Upgrade on the RPC endpoint; H2 push forbidden (events.md §1K, SNTR-HTTP-130/131).

## Transports and equivalence

41. Is `[length][protobuf]` valid inside a WebSocket message? — No: decode the message payload directly; reject prefixes/trailing bytes as `INVALID_ARGUMENT` (SNTR-WS-036, VEC-WS-009).
42. Text WebSocket message containing a valid `Frame`? — Invalid: binary only; close 1003 (SNTR-WS-031).
43. Which close code for a malformed envelope on WS? — 1002 (state/version/variant), 1007 (malformed protobuf), 1003 (text), 1008 (auth denial), 1009 (oversize), 1011 (internal) per SNTR-WS-081. Trailing-garbage-after-valid-Frame sits between 1002 and 1007 (F-22, P2): pick 1007 with `INVALID_ARGUMENT` and document it.
44. Does `ws://` ever become `wss://` automatically? — Never: scheme selection is explicit; auto-upgrade and downgrade are forbidden (SNTR-WS-011, SNTR-WSS-113).
45. I follow an HTTP 302 from the RPC endpoint. Conformant? — No: never auto-follow; manual following requires six conditions including no downgrade and re-validation (SNTR-HTTP-100/101).
46. On HTTP, is `request_id` 7 on exchange N related to 7 on exchange N+1? — No: each exchange is independent; IDs live for one exchange; reuse is a new unrelated correlation (SNTR-HTTP-073). Note this exempts HTTP from stale-ID rejection (F-04) → RFC 0004.
47. REFUSED_STREAM on one H2 stream — retry the RPC? — Yes, MAY treat as definitely-not-executed with fresh ID + same op key; any other reset is unknown-outcome (SNTR-HTTPS-051). Trusts the peer's RFC 9113 compliance.
48. Which profile identifiers do I claim? — SPECIFICATION GAP (F-01): specs say `SNTR-HTTP-V1`/`SNTR-WS-V1`/`SNTR-WSS-V1`; the conformance suite says `SNTR-HTTP1-V1`/`SNTR-WS-H1-V1`/`SNTR-WSS-H1-V1`. Blocked until unified. → RFC 0005. (`SNTR-TCP-V1`, `SNTR-TLS-TCP-V1`, `SNTR-HTTPS-H1/H2-V1` agree.)
49. Is `permessage-deflate` okay if both sides agree? — Only with explicit deployment opt-in, documented settings, and decompressed-size enforcement (1009 + `RESOURCE_EXHAUSTED`); default off (SNTR-WS-090…092).
50. A proxy terminates my TLS. What must hold? — Backend leg secured, front-door identity validated both ends, SNI/Host/ALPN unaltered-or-mapped, mismatch fails closed (SNTR-TSEC-008, SNTR-WSS-114). Exact propagation field is still open (security open-questions item 4).

## Errors, limits, BSR consumption

51. Which code for "your version is too old"? — `UNIMPLEMENTED` or `FAILED_PRECONDITION` (handshake.md §5); initiators accept both (F-09).
52. `RpcError.message` — can I put the SQL error in it for debugging? — No: generic public text only; diagnostics stay server-side (SNTR-ERR-003/021, SNTR-ASEC-024).
53. Unknown numeric error code 99 arrives. Crash? — No: map to `UNKNOWN` for reporting, preserve the number diagnostically, never treat as success (SNTR-ERR-005).
54. My payload is exactly 1 MiB. Accepted? — SPECIFICATION GAP (B8, F-06): it cannot fit the 1 MiB envelope with overhead. Send the largest payload that fits the serialized bound, or use an approved override. → RFC 0005.
55. I generate BSR bindings for Rust and Go. Any behavioral differences? — Yes: Prost drops unknown fields, Go preserves them (generation.md). Decoded comparison is unaffected; re-emitting proxies must not rely on retention. Also `session.proto`/`capabilities.proto` may yield empty packages, and `go_package` currently points at a private org path (F-05) → RFC 0005.
56. Do generated bindings implement the handshake/RPC runtime? — No: message types only; state machines, framing, auth, correlation, deadlines, and error mapping are yours to implement from `specifications/` (schema-registry §6, ADR-010).
