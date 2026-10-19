# Audit L — Conformance Coverage (Syntra v1)

- Method: machine-checked `conformance/manifest/requirements.yaml` (498 entries after the SYN-ARCH appendix added for the v1 RC) against `specifications/` definitions and `conformance/manifest/*.yaml` cases.
- Normative bar: ADR-001 — every MUST/MUST NOT carries an ID and links to a test. GOVERNANCE.md Sec. 3 — normative changes link IDs to tests or tracked placeholders.
- Update for v1 RC: the SYN-ARCH appendix (§3.1 recommendation) has been applied — 25 charter rows added, all `manual` except exercised rows noted below. Machine check: `scripts/validate-repo.py requirements` passes (498 rows, 498 defined IDs, zero dangling references).

## 1. Headline percentages (registered requirement IDs)

| Universe | Count | Automated | Partially automated | Manual | Uncovered |
|---|---|---|---|---|---|
| All registered requirement IDs | 498 | 418 (83.9%) | 44 (8.8%) | 36 (7.2%) | 0 (0.0%) |
| SNTR-* requirement IDs | 473 | 412 (87.1%) | 42 (8.9%) | 19 (4.0%) | 0 (0.0%) |
| SYN-ARCH-* charter IDs | 25 | 6 (24.0%) | 2 (8.0%) | 17 (68.0%) | 0 (0.0%) |
| Distinct CONF-* test IDs referenced | 128 | — | — | — | — |
| Machine-readable cases defined | 130 | — | — | — | — |
| Prose-only test IDs (no manifest case) | 10 | — | — | — | — |

Every SNTR-* ID resolves to at least one CONF-* case, and every referenced CONF-* ID resolves to a defined manifest case (verified: zero dangling references in either direction).

All 25 SYN-ARCH-* IDs have traceability rows; 15 of those 17 manual rows have empty `test_ids` and documented review dispositions. "Mapped" includes those dispositions; it does not mean automated or executed. Counts and statuses above are calculated from `requirements.yaml`; percentages are rounded to one decimal place.

## 2. Automation status key (both namespaces)

- Automated (418: 412 SNTR-* + 6 SYN-ARCH-*): rows designated for fully scripted wire assertions (timeouts use injected clocks or generous margins; expiry uses short-lived fixtures).
- Partially automated (44: 42 SNTR-* + 2 SYN-ARCH-*): harness-dependent rows — silent-peer timers, PKI rotation/proxy rigs, deployment posture review, rotation overlap windows, negotiation-trace confirmation, no-exactly-once attestation (half runner, half declaration review), plus charter secure-transport posture and credential-opacity review.
- Manual (36: 19 SNTR-* + 17 SYN-ARCH-*): human-review artifacts — threat-model inventories, out-of-scope lists, no-deprecation registries, mTLS-deferred confirmation, no-promise proofs, evidence-citation rules, and charter independence/layering/ownership/claim attestations.

These are manifest automation designations, not evidence of executed implementation conformance runs.

## 3. Uncovered mandatory requirements (must be reported)

### 3.1 SYN-ARCH-* charter IDs: all 25 mapped for v1 RC (previous gap closed)

`requirements.yaml` previously covered only the SNTR-* namespace. A charter-ID appendix has now been added (25 rows: 6 automated, 2 partially_automated, 17 manual). The original gap inventory is retained below as the mapping rationale:

- Independence: SYN-ARCH-001, 002, 060, 061, 062 (negative-grep enforceable; the suite already greps fixtures in CONF-EVT-015 but never asserts the charter IDs).
- Layering: SYN-ARCH-010, 011, 012, 013, 042 (adapter-purity rules; partially exercised by transport tests but never cited).
- Compatibility: SYN-ARCH-020, 021, 040, 041, 043, 044, 045 (ownership map; 044 cites suite results as the verification authority — self-referential, needs a manual attestation row).
- Security posture: SYN-ARCH-030, 031, 032, 033, 034, 035 (behavioral; exercised by STEST rows but never cited — e.g., no case cites SYN-ARCH-035 alongside SNTR-CORE-005/REL-001).
- Transports: SYN-ARCH-050, 051 (profile-claim labeling; CONF claims text exists in `claims.md` but no executable case cites 050/051).

Recommendation (documentation patch, no RFC): add a charter-ID appendix to `requirements.yaml` mapping each SYN-ARCH ID to its exercising cases (mostly existing STEST/CONF rows) or to `manual` with a review note for process/ownership IDs (040–045, 060–062). — DONE for v1 RC: rows added; `scripts/validate-repo.py requirements` confirms 498/498 with zero dangling references.

### 3.2 Prose test IDs without machine-readable cases (10)

These prose-defined cases have no `manifest/*.yaml` counterpart, so a YAML-only runner cannot execute them:

CONF-AUTH-001…006 (`conformance/auth-session/authentication.md`), CONF-ERR-001…004 (`conformance/errors/errors.md`).

Coverage is not lost (their requirements map to CONF-SESS/CONF-SEC/CONF-CORE rows), but ID-level traceability is: a declaration citing CONF-AUTH-003 has no manifest case to run. Recommendation: add `manifest/auth.yaml` and `manifest/errors.yaml` (or fold rows into existing manifests), P2.

### 3.3 Normative MUST statements without requirement IDs (systematic gap)

ADR-001 requires every MUST/MUST NOT to carry an ID. The clarifying subsections (§1A–§1M, §2A, appendices) contain normative-strength MUSTs with no ID and therefore no `requirements.yaml` row. Sample (non-exhaustive):

- rpc.md §1F: initiator timer ≤ requested budget; responder measures post-validation/pre-dispatch; maximum-budget policy documented.
- rpc.md §1G: completion-wins; unknown/completed cancel ignored; exactly one terminal code on cancel/deadline tie; tie-break documented.
- rpc.md §1H: operation-key optionality, server dedup documentation duties, no-indefinite-dedup, no cross-connection state.
- events.md §§1D–1M: stream defaults, handle non-reuse, filter bounds, drop policies, replay coordination strategy, cursor rules, reconnect re-subscription.
- sessions.md §§1A–1G: three-concept separation, resumption RFC content list, cross-transport prohibition conditions, HTTP principles, termination table rows, timeout table.
- handshake.md §1A/§1B/§2A: state-name mapping, full transition table rows, ordering rules 1–10.
- errors.md §§1A–1D: taxonomy mappings, detail limits, layering rules.
- Transport/table rows: WS close-code table mappings, HTTP status table rows, H2 stream rules.

Recommendation: mint IDs for the subset that constrains wire behavior (or explicitly mark subsections informative). Until then the "no silent zero coverage" claim holds only for the ID universe, not the MUST universe. P1 (process gap against ADR-001).

### 3.4 Core registry undercount

`specifications/core/requirements.md` claims "~130 normative IDs"; 179 bolded SNTR-* definitions exist in core documents alone. The index ranges are individually accurate but the total is stale. P3 (documentation patch).

### 3.5 Stale fixture counts in transport specs

- `http.md` SNTR-HTTP-900 cites `CONF-HTTP-001…016`; `conformance/requirements/http.md` defines 18 cases (001…018).
- `https.md` SNTR-HTTPS-900 cites `CONF-HTTPS-001…012`; the file defines 14 cases (001…014).

A runner implementing "001…016" would silently drop two mandatory cases. P2 (documentation patch aligning ranges, or capability-gate the delta explicitly).

## 4. Coverage by family (mapped / total defined, both namespaces)

All families map 100% of defined IDs. Status mix (automated / partial / manual):

CORE 16 (14/1/1) · SER 14 (14/0/0) · WIRE 14 (13/1/0) · HS 18 (15/3/0) · AUTH 16 (14/2/0) · SESS 14 (12/1/1) · RPC 16 (15/1/0) · EVENT 17 (17/0/0) · REL 16 (14/2/0) · CAP 13 (10/1/2) · ERR 12 (12/0/0) · VER 13 (10/2/1) · TMOD 12 (0/0/12) · TSEC 17 (12/5/0) · ASEC 22 (17/5/0) · RPL 13 (13/0/0) · OPQ 10 (10/0/0) · STEST 12 (10/2/0) · TCP 15 (11/3/1) · TLS 15 (12/2/1) · HTTP 59 (56/3/0) · HTTPS 29 (25/4/0) · WS 54 (53/1/0) · WSS 36 (33/3/0) · SYN-ARCH 25 (6/2/17, including 15 with empty test_ids).

Manual concentration is correct (threat-model review artifacts, deprecation registries, no-promise proofs). Partial concentration is correct (timers, PKI/proxy harnesses, deployment posture).

## 5. Acceptance-criterion verdict

"Mandatory normative requirements have conformance coverage": HOLDS for registered-ID traceability in both namespaces (498/498 mapped): SNTR-* is 473/473 mapped (87.1% designated automated); SYN-ARCH-* is 25/25 mapped (24.0% automated, 8.0% partial, mostly manual at 68.0%). Overall, 83.9% is designated automated. The criterion still FAILS for un-ID'd normative MUSTs (unmapped by construction, §3.3); charter mapping does not close that gap or establish executed conformance. The remaining ID gap can be addressed by the documentation work above without wire changes; no P0 is raised here beyond the underlying P0/P1 findings they would exercise (F-01…F-18 in the main review).
