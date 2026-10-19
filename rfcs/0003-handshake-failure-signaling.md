# RFC 0003: Handshake failure signaling (proposal)

- RFC: 0003
- Title: Typed handshake failure signaling, pre-ACTIVE event handling, timer binding
- Status: Draft (proposed by v1 consistency audit, findings F-03, F-07, F-08, F-09, F-16, F-19)
- Date: 2026-10-26
- Target version: v1 clarification; wire additions (if any) require capability-gated minor treatment per decision below
- Relates to: `specifications/core/handshake.md` (§1B, §2A rules 9–10, §5), `errors.md` (§§1C–1D), `events.md` (SNTR-EVENT-005/900, §4), `architecture.md` §12.1, `capabilities.md`, transports (TCP/TLS/TCP, HTTP/HTTPS, WS/WSS); RFC 0001 B1/B2; RFC 0002 §10 items 1–2
- Author(s): TBD — blocker (maintainer assignment)
- Reviewers: TBD — blocker (protocol + security maintainers)

> This RFC resolves no conflict by fiat. It records three TBD decisions and proposes a decision procedure with acceptance tests. No `.proto` change is proposed until a decision is taken.

## 1. Summary

Give handshake failures a lawful typed-error carrier (B1/F-03), select one pre-ACTIVE notification policy (B2/F-07), unify the version-mismatch code (F-09), bind the TLS/TCP handshake-timer start point (F-19), correct the charter illustration showing a forbidden `Frame{result}` failure (F-08), and refresh the stale errors.md §1D layering note (F-16).

## 2. Motivation

Today SNTR-ERR-004 and handshake §5 name codes for seven failure causes, but no pre-ACTIVE `Frame` may lawfully carry them (zero-ID `result` forbidden; `ready` has no error outcome). Consequences found by audit: (a) TCP/TLS hosts cannot transmit *which* handshake error occurred — SNTR-HS-020's "surface the typed code" is unimplementable there beyond local reporting; (b) receiver behavior for pre-ACTIVE `notification` is three-ways split (ignore / fail-close / per-stream-spec); (c) version-mismatch accepts two codes, doubling test matrices; (d) the TLS/TCP timer start is unbound, so slow-TLS behavior diverges; (e) the charter's own walkthrough depicts the forbidden pattern.

## 3. Proposal

Normative force remains with existing IDs; this RFC mints the decision records and any new IDs the chosen options require.

- **Decision D1 (carrier):** adopt exactly one of: (i) transport-native mapping only (close/status/WS-code tables become the carrier, with a per-profile code→`ErrorCode` table and a "typed code surfaced locally + profile signal on the wire" rule); (ii) a new capability-gated handshake-error record (minor-additive, B7 binding); (iii) status quo (local-only codes, transports close silently) with SNTR-HS-020/ERR-004 reworded to require only local surfacing. Proposing (i) as default: no wire change, matches what transports already do.
- **Decision D2 (pre-ACTIVE notification):** select ignore-with-diagnostic or fail-close suite-wide; align events.md, handshake.md, framing.md, and ADR-007 (which currently contradicts both). Proposing fail-close: a host sending pre-ACTIVE events is already in violation, and fail-close is the only policy observable without trusting the violator.
- **Decision D3 (mismatch code):** select `UNIMPLEMENTED` (version unknown) as the single version-mismatch code, keeping `FAILED_PRECONDITION` for state violations only.
- **Timer binding:** define CONNECTED per profile (TCP: TCP established; TLS/TCP: TLS completed; WSS: WSS established — already stated) and state the 5 s default runs from there.
- **Doc corrections (no decision needed):** fix architecture §12.1 failure arrow to "connection close (local typed code; no `result` on the wire)" pending D1; refresh errors.md §1D to cite the finalized HTTP/HTTPS status tables.

## 4. Detailed design

Mechanics unchanged except the selected options. Client/server obligations restated per option on acceptance; conformance fixtures: version-mismatch single-code matrix; pre-ACTIVE notification matrix (ignore vs close per D2); slow-TLS timer fixture (4 s TLS handshake + immediate hello → success; 6 s → `DEADLINE_EXCEEDED`); per-profile carrier table (TCP close / HTTP 400-401 / WS 1002/1008) mapping to the §5 codes.

## 5. Alternatives considered

1. New `HandshakeError` message now. Rejected as default: needs B7 binding design; acceptable only under option D1(ii) with full bounds/confirmation semantics.
2. Keep both mismatch codes. Rejected: doubles every version test matrix for zero interop benefit (both transitions are close).
3. Keep three pre-ACTIVE policies with "record your behavior." Rejected: receiver divergence is precisely the interop hazard; documentation does not converge it.

## 6. Compatibility

D1(i), D2, D3, timer binding: clarifications within v1 (no wire change). D1(ii): minor-additive capability + RFC binding. No major version.

## 7. Security considerations

Untyped closes leak less than verbose errors (oracle minimization, SNTR-ASEC-011); per-profile carrier tables MUST NOT introduce reason oracles. Fail-close on pre-ACTIVE events removes a trust-the-violator policy. Timer binding closes a slow-handshake asymmetry.

## 8. Test plan and acceptance criteria

- [ ] Version-mismatch matrix yields the single selected code on all profiles.
- [ ] Pre-ACTIVE `notification` yields the single selected behavior on all profiles.
- [ ] Slow-TLS (4 s/6 s) timer fixture passes on TLS/TCP.
- [ ] Architecture illustration and errors.md §1D corrected; ADR-007 aligned.
- [ ] SNTR-HS-900/901, SNTR-ERR-900/901, SNTR-EVENT-900 green on two implementations.

## 9. Drawbacks and risks

Selecting fail-close may drop debuggability for buggy hosts; mitigate with local diagnostics (allowed) without wire changes.

## 10. Unresolved questions and blockers

TBD — the three decisions above are blockers. Until taken, F-03/F-07/F-09/F-19 remain P0/P1 and v1 cannot release.
