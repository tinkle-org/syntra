# RFC 0004: Correlation identity, races, and authentication carriage (proposal)

- RFC: 0004
- Title: `request_id` reuse vs stale rejection, cancel/deadline races, HTTP statelessness, credential carriage, re-auth code
- Status: Draft (proposed by v1 consistency audit, findings F-02, F-04, F-10, F-13, F-14, F-15 + errors.md "only" overclaim)
- Date: 2026-10-26
- Target version: v1 clarification; any new field/binding is capability-gated minor work
- Relates to: `specifications/core/rpc.md` (§§1B/1G–1I, §4), `security/replay-protection.md` (SNTR-RPL-012/020/030), `reliability.md` (SNTR-REL-001/003), `errors.md` (SNTR-ERR-002), `authentication.md` (SNTR-AUTH-010, §1C), `sessions.md` (§1B table, §1E), transports `http.md` (§§1H–1I) / `https.md`; RFC 0001 B3/B10; RFC 0002 §10 items 3, 6
- Author(s): TBD — blocker (maintainer assignment)
- Reviewers: TBD — blocker (protocol + security maintainers)

> This RFC resolves no conflict by fiat. It records five TBD decisions. No `.proto` change is proposed.

## 1. Summary

Settle what an initiator may assume about `request_id` lifetime across the core, replay security, and the stateless HTTP binding; set cancel/deadline/`UNAVAILABLE` race precedence and fix the "only code that implies unknown outcome" overclaim; reconcile credential carriage between ASEC-003 and the HTTP `Authorization` binding; assign a code to same-connection re-authentication attempts; correct the false sessions.md §1B HTTP/`ServerReady` row.

## 2. Motivation

Audit findings: (a) core permits ID reuse after terminal result while replay protection rejects stale reuse — the two rules share one observable (an ID arriving after its terminal result) with opposite verdicts; (b) HTTP hosts are forbidden cross-exchange memory, so they cannot enforce the stale rule the security suite demands; (c) cancel-vs-deadline ties and the `UNAVAILABLE`-"only" wording leave outcome-unknown reporting ambiguous; (d) ASEC-003's "credentials ONLY in `ClientHello.credential`" strictly outlaws the specified HTTP binding; (e) forbidden re-auth has no code; (f) the HTTP/`ServerReady` table row is false.

## 3. Proposal

- **Decision D1 (reuse):** adopt exactly one of: (i) non-reuse within a bounded tracking window (hosts remember terminal IDs for N seconds/entries, reject in-window reuse as stale, accept older reuse as new; window documented and bounded); (ii) always-permit with initiator-side discipline (replay security limited to cross-connection and outstanding cases only). Proposing (i): preserves the security intent with bounded state, keeps HTTP exempt explicitly (per-exchange independence is the documented HTTP semantic).
- **Decision D2 (HTTP reconciliation):** state that SNTR-HTTP-073 per-exchange independence is the profile's lawful specialization: stale-ID rejection and resumption rules apply to persistent-connection profiles; HTTP exchanges are separate logical connections by construction. Correct sessions.md §1B row (no `ServerReady`/`connection_id` on HTTP).
- **Decision D3 (races):** set precedence for cancel-vs-deadline with no result (proposing: deadline-expiry wins when the budget elapsed, else cancellation wins; exactly one terminal code; tie-break logged), and reword ERR-002 `UNAVAILABLE` from "the only code that implies unknown handler outcome" to "the code that reports unknown outcome for loss/shutdown; `DEADLINE_EXCEEDED`/`INTERNAL`/`UNKNOWN` equally leave execution unknown."
- **Decision D4 (carriage):** reword ASEC-003 to "credentials travel only in `ClientHello.credential` on frame-carrying profiles, and only in the profile-defined binding of the credential bytes (`Authorization: Syntra <base64>` on HTTP/HTTPS) elsewhere; never in URLs, IDs, methods, errors, or logs."
- **Decision D5 (re-auth code):** post-ACTIVE principal-change attempt → `FAILED_PRECONDITION` (state violation) without binding change; close only per documented policy.

## 4. Detailed design

Mechanics unchanged except selected options. Conformance: duplicate-outstanding rejection (existing); in-window stale reuse rejection + aged-reuse acceptance fixtures (D1); HTTP independence fixtures (existing HTTP-073 rows cited as the lawful exemption); cancel/deadline tie fixture asserting the single selected code; re-auth attempt fixture asserting D5; negative-grep carriage fixtures unchanged.

## 5. Alternatives considered

1. Add a core operation-ID/nonce field to disambiguate replays. Rejected: B11 defers it; bit-exact payload keys plus bounded tracking suffice for v1.
2. Require HTTP hosts to keep cross-exchange ID memory. Rejected: contradicts per-request independence and scales poorly; the exemption model (D2) is cleaner.
3. Leave all five to implementations. Rejected: that is the current hazard this RFC exists to remove.

## 6. Compatibility

Clarifications within v1 (no wire change). Any tracking-window or binding addition is minor-additive with capability gating where it touches the wire.

## 7. Security considerations

Bounded tracking windows bound attacker replay opportunity and host state (T4/T7). The HTTP exemption must not weaken persistent profiles. Precedence and wording fixes remove oracle/ambiguity surface. Re-auth code prevents privilege-confusion probing.

## 8. Test plan and acceptance criteria

- [ ] Stale-window fixtures (in-window reject, aged accept) green on TCP/TLS/WS/WSS.
- [ ] HTTP exchanges assert independence (no cross-exchange rejection).
- [ ] Cancel/deadline tie yields the single selected code; `UNAVAILABLE` wording corrected.
- [ ] ASEC-003 reworded; HTTP binding cited as the lawful specialization.
- [ ] Re-auth fixture yields `FAILED_PRECONDITION` with binding intact; sessions §1B row corrected.

## 9. Drawbacks and risks

Bounded windows add per-host state config; mitigate with documented defaults and caps (ties to RFC 0005 bounds work).

## 10. Unresolved questions and blockers

TBD — the five decisions above are blockers. Until taken, F-02/F-04 remain P0 and F-10/F-13/F-15 remain P1; v1 cannot release.
