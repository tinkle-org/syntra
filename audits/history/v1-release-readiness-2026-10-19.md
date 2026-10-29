# Syntra v1 Release Readiness (RC gate)

Historical snapshot, superseded by [current readiness](../v1-release-readiness.md).
The findings and execution claims below are preserved as originally recorded;
they are not a statement of the current repository's state.

Date: 2026-10-19 (working-tree verification; no release tag exists).
Method: `scripts/validate-repo.py all`, `buf` gates, audit
`v1-consistency-review.md` findings, `SESSION-OPEN-QUESTIONS.md`,
RFC statuses, `GOVERNANCE.md` Sec. 5.

Verdict semantics: **COMPLETE** = RC-scope requirements for the area are
satisfied (documents frozen per `RELEASE.md` §2, validators green, no P0/P1
in the area, acceptance recorded). **BLOCKED** = otherwise, with reasons.
"Execution proven" (green conformance runs against implementations) is a
*stable*-release bar per `GOVERNANCE.md` Sec. 5, not an RC bar — but its
absence is recorded wherever it applies, since an RC with zero execution
evidence must say so.

| Area | Verdict | Reason |
|---|---|---|
| Core specification | BLOCKED | Specs Draft (RFCs 0001–0004); P0 F-02 (`request_id` reuse vs stale rejection), F-03 (no lawful pre-ACTIVE error carrier); P1 F-07, F-09, F-13, F-15 |
| Schemas | BLOCKED | P0 F-05 (private-org `go_package` in all 7 files); F-06 (1 MiB payload fixture vs envelope bound). BSR module identity approved (`buf.build/tinklecorp/syntra`; `buf.yaml`, `README.md` §BSR schema location, `docs/schema-registry.md` §1); publication policy remains unaccepted. Mechanical gates pass (`buf lint`/`build`/`breaking` clean) |
| Security | BLOCKED | P0 F-04 (HTTP per-exchange ID amnesia vs `SNTR-RPL-012`); P1 F-10 (carriage reconciliation); `SESSION-OPEN-QUESTIONS.md` items 2 and 11 (resumption standard; revocation bound, channel binding, offline-host revocation, proxy format per `specifications/security/open-questions.md` items 1–4); specs Draft |
| TCP | BLOCKED | Spec Draft, acceptance pending; no TCP-specific P0 (profile ID agrees); no executed interop |
| TLS/TCP | BLOCKED | Spec Draft; P1 F-19 (handshake-timer start unbound); no executed interop |
| HTTP | BLOCKED | P0 F-04; P1 F-10, F-14 (false `ServerReady` row); RFC 0004 Draft |
| HTTPS | BLOCKED | Inherits HTTP blockers; H1/H2 specs Draft |
| WS | BLOCKED | P0 F-01 (profile identifier mismatch); spec Draft |
| WSS | BLOCKED | P0 F-01; TLS/proxy rules Draft |
| Conformance | BLOCKED | P0 F-01 (suite/spec identifier mismatch), F-06 (unimplementable 1 MiB payload fixtures); 10 prose-only test IDs without manifest cases (P2); suite never executed (no IUT runs) |
| BSR | BLOCKED | Module identity approved (`buf.build/tinklecorp/syntra`); still blocked on P0 F-05 (`go_package` private-org path; needs RFC 0005 + migration note), RFC 0005 Draft, and unaccepted publication policy. Preflight now pins the exact module and fails closed on anything else; no push performed |

Supporting gates (RC checklist cross-check):

- Proto lint passes: YES (`buf lint` clean, Buf 1.59.0).
- Proto breaking checks pass: YES (`buf breaking` against
  `compatibility/v1-initial/image.json` clean; 498-row traceability
  matrix validates: 473 SNTR-* + 25 SYN-ARCH-*, 0 dangling references).
- Test vectors validated: YES, mechanically
  (`validate-repo.py vectors`: hex parses, protobuf decodes against
  `proto/`, TCP lengths match, malformed vectors intentionally malformed;
  one genuine fixture bug found and fixed — unknown-field vector used
  field 86 where field 90 is documented).
- Consistency audit P0s: 6 OPEN (F-01…F-06) — see below.
- License approved: NO (`GOVERNANCE.md` Sec. 7; no `LICENSE` file).
- Security process documented: YES (`SECURITY.md` private channel +
  `GOVERNANCE.md` embargo handling added by this task).
- CHANGELOG updated: YES (`[v1.0.0-rc.1] - TBD (pending)` section with
  Added/Changed/Deprecated/Removed/Security).

## Every blocker

P0 (must fix before v1; RFC proposals exist, none Accepted):

- F-01 — Transport profile identifier mismatch: specs
  (`SNTR-HTTP-V1`, `SNTR-WS-V1`, `SNTR-WSS-V1`) vs conformance suite
  (`SNTR-HTTP1-V1`, `SNTR-WS-H1-V1`, `SNTR-WSS-H1-V1`). Declarations are
  mutually unintelligible. → RFC 0005. Validator: 10 remaining errors,
  all this finding.
- F-02 — `request_id` reuse permitted (core) vs stale rejection
  (replay security). → RFC 0004.
- F-03 — No lawful pre-ACTIVE typed-handshake-error carrier; TCP/TLS
  hosts cannot surface the §5 code on the wire. → RFC 0003.
- F-04 — HTTP per-exchange ID amnesia vs `SNTR-RPL-012` stale rejection.
  → RFC 0004.
- F-05 — Private-organization `go_package` path in all seven proto
  files + org references in SECURITY/SUPPORT/CONTRIBUTING vs
  SYN-ARCH-001/062. → RFC 0005.
- F-06 — 1 MiB payload fixtures (SNTR-RPC-900, SNTR-OPQ-900) cannot fit
  the 1 MiB envelope. → RFC 0005.

Release blockers from `SESSION-OPEN-QUESTIONS.md` (11 items, all open):
mechanism negotiation; resumption standard; typed pre-ACTIVE carrier (B1);
pre-ACTIVE notification conflict (B2); stale `request_id` reuse (B3);
capability/session-extension binding and bounds (B7); payload vs envelope
size (B8); cancel/deadline/`UNAVAILABLE` races (B10); cross-transport
binding; HTTP profile bindings; revocation-propagation bound,
channel-binding construction, proxy propagation format.

RFC status (none Accepted; only Accepted RFCs may change normative
behavior): 0001 Draft (B9 layout decision implemented, behavior open),
0002 Draft, 0003 Draft, 0004 Draft, 0005 Draft.

Process blockers: no `LICENSE` file (license alternatives under
consideration, `GOVERNANCE.md` Sec. 7); publication policy RFC unaccepted
(module identity itself is approved); no independent implementation runs
against the conformance suite (bootstrap path — one implementation +
packet-fixture verification — also unexecuted).

## Path to green (tagging `v1.0.0-rc.1`)

1. Accept RFCs 0003–0005 decisions (or narrower Accepted RFCs covering
   F-01…F-06), land spec/schema/manifest diffs, update
   `SESSION-OPEN-QUESTIONS.md`.
2. Re-run `scripts/validate-repo.py all` → zero errors (F-01 errors
   clear when identifiers unify).
3. Resolve or explicitly defer-with-rationale the 11 open questions;
   record decisions (deferral of a blocker needs maintainer agreement
   with rationale, `GOVERNANCE.md` Sec. 6).
4. BSR module identity is approved (`tinklecorp/syntra`); approve
   `LICENSE` and the publication policy RFC; tag per `RELEASE.md`
   §4; collect artifacts per `RELEASE.md` §5.
5. Stable additionally requires: accepted specs, green suite on two
   independent implementations (or bootstrap equivalent),
   `CHANGELOG.md` migration notes, tagged release notes
   (`GOVERNANCE.md` Sec. 5).

Acceptance criterion "repository can be publicly tagged as RC":procedure
is ready (`RELEASE.md`, validators, workflows, artifacts script); the
tag MUST NOT be created until the BLOCKED items above clear, per the RC
checklist. No tag was created by this task. No `buf push` was performed.
No generated SDK or implementation source is treated as normative.
