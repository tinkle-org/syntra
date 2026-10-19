# RFC 0005: Negotiation binding, bounds, and identifiers (proposal)

- RFC: 0005
- Title: Capability negotiation binding, limit-override bounds, concurrency floor, payload fixtures, profile identifiers, schema independence
- Status: Draft (proposed by v1 consistency audit, findings F-01, F-05, F-06, F-11, F-12, F-17, F-18)
- Date: 2026-10-26
- Target version: v1 clarification + minor-additive bindings where wire fields are needed; identifier/path changes are breaking where noted
- Relates to: `specifications/core/capabilities.md`, `sessions.md` (§§1C–1E), `authentication.md` (§1A), `events.md` (§§1A/1I), `core/open-questions.md` blockers 1/3, security open-questions items 1–5, transports (profile-ID requirements), `proto/syntra/v1/*.proto` (`go_package`), SECURITY/SUPPORT/CONTRIBUTING, `conformance/profiles.yaml`, `claims.md`; RFC 0001 B7/B8; RFC 0002 §10 items 4–11
- Author(s): TBD — blocker (maintainer assignment)
- Reviewers: TBD — blocker (protocol + security maintainers)

> This RFC resolves no conflict by fiat. It records six TBD decisions. No `.proto` change is proposed until a decision is taken.

## 1. Summary

Provide the missing capability/limit negotiation binding (or formally defer it with a closed mandatory-only rule), set concrete bounds (credential/method/`connection_id`/message lengths, lower concurrency floors, close-grace default/max), fix the 1 MiB payload-vs-envelope fixture conflict, unify transport profile identifiers across specs and conformance, and remove private-organization paths from the public schema and support docs.

## 2. Motivation

Audit findings: (a) capabilities presume an advertisement/confirmation channel that has no v1 wire form, while also allowing an "application RPC" fallback that cannot interoperate without a defined method/payload; (b) several bounds are referenced but valueless (credential length, message text, `connection_id` length, close grace) and one clause ("lower bound negotiated," SNTR-RPC-008) references a nonexistent mechanism; (c) mandatory fixtures demand a 1 MiB payload inside a 1 MiB envelope — unimplementable as written; (d) the suite and the specs use different profile ID strings, so claims cannot match specifications; (e) every `.proto` file and three support docs hardcode a private org path, contradicting SYN-ARCH-001/062 and poisoning BSR consumption.

## 3. Proposal

- **Decision D1 (binding):** adopt exactly one of: (i) no v1 negotiation binding at all — mandatory-only operation is the complete v1 contract, CAP-002's "application-level negotiation RPC" sentence is struck, and any capability use before its RFC is a violation (no probing surface exists to misuse); (ii) a minimal capability-gated binding (minor-additive) with identifier/parameter/count/total-byte bounds, duplicate/unknown handling, confirmation timing, and per-connection scope. Proposing (i) for v1 stability, with (ii) as the named future RFC.
- **Decision D2 (bounds):** set explicit maxima: credential bytes (proposing: ≤ envelope bound, with 64 KiB default ceiling as HTTP already uses, extended suite-wide); `connection_id` (proposing: ≤128 bytes UTF-8); `RpcError.message` (proposing: ≤4 KiB); close grace (proposing: default 5 s, max 30 s, documented per deployment); lower concurrency floors (proposing: delete the "unless negotiated" clause until D1(ii) exists — the floor is 16, period).
- **Decision D3 (fixtures):** rewrite SNTR-RPC-900/OPQ-900 "1 MiB" rows as "largest payload fitting the 1 MiB envelope" plus explicit exactly-MAX/MAX+1 serialized-byte boundary fixtures (MAX and MAX+1 on total `Frame` bytes).
- **Decision D4 (identifiers):** unify on one string set across transport specs, `profiles.yaml`, `claims.md`, and declarations. Proposing the H1-explicit forms (`SNTR-HTTP1-V1`, `SNTR-WS-H1-V1`, `SNTR-WSS-H1-V1`; TCP/TLS/HTTPS unchanged) with the specs amended — rationale: the suite already uses them and HTTP-version disambiguation has forward value. The alternative (revert the suite to `SNTR-HTTP-V1` etc.) is equally acceptable; what is not acceptable is two live spellings.
- **Decision D5 (independence):** replace `go_package` with a neutral public path at publication (Buf-FILE-breaking: needs major-version handling or a pre-stable change window with migration notes), and replace `tinklehq/` references in SECURITY/SUPPORT/CONTRIBUTING with neutral contribution channels. Until then, BSR publication stays blocked.
- **Doc corrections:** none beyond the above; F-20 filename fixes and F-21 registry/count updates ride as direct doc patches.

## 4. Detailed design

Mechanics unchanged except selected options. Conformance: capability-absence fixtures assert mandatory-only interop with no advertisement channel (D1(i)); bound fixtures assert each D2 maximum and its mapped code; boundary fixtures assert MAX/MAX+1 on serialized bytes (D3); declaration linter accepts exactly the unified ID set (D4); BSR dry-run import from a neutral path (D5).

## 5. Alternatives considered

1. Define the full negotiation binding now (D1(ii) immediately). Rejected as default: B7 scope (parameters, confirmations, token lifetimes, replay windows) exceeds a stabilization RFC; it is the correct *next* RFC after v1, not part of it.
2. Raise the envelope to fit 1 MiB payloads. Rejected (RFC 0001 B8): silently moves every bound, test vector, and DoS analysis; the fixture text is what is wrong, not the bound.
3. Keep both identifier spellings with an alias table. Rejected: aliases in identifiers fracture claims, tooling, and the SYN-ARCH-050 documentation duty.

## 6. Compatibility

D1(i), D2 defaults, D3 fixture text, D4 (one direction), D5 pre-stable: clarifications/docs within v1. D1(ii) bindings, new bound fields, or post-stable `go_package` change: minor- or major-versioned per SNTR-VER-003 with migration notes.

## 7. Security considerations

Bounded everything (T6/T7); no silent limit-raising; negotiation binding (if ever added) must be integrity-protected and downgrade-proof (T2); identifier unification removes claim-spoofing surface; neutral paths remove private-infrastructure trust.

## 8. Test plan and acceptance criteria

- [ ] Mandatory-only interop fixture with no advertisement channel passes; unconfirmed-use rows unchanged.
- [ ] Each D2 bound has accept/reject fixtures with mapped codes.
- [ ] MAX/MAX+1 serialized-byte fixtures pass on all profiles.
- [ ] Declarations validate against the unified ID set; specs and suite agree byte-for-byte.
- [ ] BSR dry-run generation imports from the neutral path; no private-org string remains in schema or support docs.

## 9. Drawbacks and risks

D1(i) closes the door on v1 capability experimentation; mitigate by scoping the future binding RFC explicitly. D5 path change breaks generated imports once; mitigate with the pre-stable window and migration notes.

## 10. Unresolved questions and blockers

TBD — the six decisions above are blockers. Until taken, F-01/F-05/F-06 remain P0 and F-11/F-12/F-17/F-18 remain P1; v1 cannot release.
