# Syntra v1 Security Specifications — Index

- Version: 1.0.0-draft.1 (2026-10-26)
- Status: Draft (pending maintainer approval via RFC)
- Authority: `threat-model.md` owns scope; companion documents own mitigations; `requirements.md` is the ID index; `architecture.md` §8 governs conflicts (security specs own security requirements, SYN-ARCH-043).

| Document | Identifier | Title | Requirements |
|----------|------------|-------|--------------|
| `threat-model.md` | `specifications/security/threat-model.md` | Normative Threat Model | SNTR-TMOD-* |
| `transport-security.md` | `specifications/security/transport-security.md` | TLS and Transport Profile Security | SNTR-TSEC-* |
| `authentication-security.md` | `specifications/security/authentication-security.md` | Credential, Session, and Token Security | SNTR-ASEC-* |
| `replay-protection.md` | `specifications/security/replay-protection.md` | Replay Classes and Defenses | SNTR-RPL-* |
| `opaque-payloads.md` | `specifications/security/opaque-payloads.md` | Opaque Bytes and Encryption Scope | SNTR-OPQ-* |
| `requirements.md` | `specifications/security/requirements.md` | Requirement Registry (index) | — |
| `test-plan.md` | `specifications/security/test-plan.md` | Security Test Requirements (STEST-001–011) | SNTR-STEST-* |
| `review-checklist.md` | `specifications/security/review-checklist.md` | Review Checklist (informative) | — |
| `open-questions.md` | `specifications/security/open-questions.md` | Unresolved Decisions (living) | — |

## Reading order

1. `threat-model.md` → `transport-security.md` → `authentication-security.md`
2. `replay-protection.md` → `opaque-payloads.md`
3. `requirements.md` + `test-plan.md` + `review-checklist.md` + `open-questions.md`

All examples use neutral applications (echo, generic key/value, generic subscription). No application-level E2EE is defined; transport security remains REQUIRED even for opaque encrypted payloads.
