# Syntra v1 Security — Requirement Registry

- Identifier: `specifications/security/requirements.md`
- Title: Security Requirement Index
- Status: Draft (generated with security draft 1.0.0-draft.1, 2026-10-26)
- Version: 1.0.0-draft.1
- Normative references: All `specifications/security/*.md`; `specifications/core/requirements.md`; `proto/syntra/v1/*.proto`
- Scope: Single index of every normative security requirement ID. The defining document owns each ID; this file MUST NOT restate normative force. Conflicts resolve per `architecture.md` §8 (security specifications own security requirements, SYN-ARCH-043).
- Terminology: Per `core/protocol.md`.

## Index

| ID family | Defining document | Concern | Mandatory/Optional |
|-----------|-------------------|---------|--------------------|
| SNTR-TMOD-001/002/010/020/030/040/050–051/060–061/900–901 | `threat-model.md` | Assets, attackers, boundaries, assumptions, in/out scope, traceability | Mandatory model |
| SNTR-TSEC-001–011/020–021/030–031/900–901 | `transport-security.md` | TLS 1.3, validation, hostname, plaintext-dev, rotation, downgrade, proxies, ALPN, no custom crypto | Mandatory for public deployments |
| SNTR-ASEC-001–011/020–024/030–031/040–041/900–901 | `authentication-security.md` | Confidentiality, carriage (never in URLs), principals, expiry, revocation, tokens, rotation, fixation, disclosure + request-security hooks | Mandatory interface |
| SNTR-RPL-001/002/010–014/020–021/030–031/900–901 | `replay-protection.md` | 5 replay classes, TLS≠idempotency | Mandatory semantics |
| SNTR-OPQ-001–006/010/020/900–901 | `opaque-payloads.md` | Opaque carriage, no E2EE in core, transport still required, limits regardless of format | Mandatory scope |
| SNTR-STEST-001–011/900 | `test-plan.md` | Security test requirements (invalid cert … cross-session misuse) | Mandatory test coverage |

Total: 5 defining security documents + test plan, ~70 normative IDs + conformance/test IDs.

## Uniqueness and ownership rules

- IDs are unique suite-wide; new security IDs REQUIRE the prefix of their defining document (`TMOD`, `TSEC`, `ASEC`, `RPL`, `OPQ`, `STEST`).
- No ID is defined twice; companions cite, never duplicate (single-definition rule shared with core).
- `SNTR-SEC-*` is intentionally unused to keep per-document traceability; the family prefix `SNTR-*SEC*` collectively denotes security scope.
- Charter `SYN-ARCH-030–035` and core `SNTR-*` remain distinct namespaces; where this suite tightens a core rule (e.g., disclosure), the stricter security rule governs for security claims (SYN-ARCH-043) and MUST be cited in the implementation's conformance report.

## Verification

```sh
grep -rhoE "\*\*SNTR-(TMOD|TSEC|ASEC|RPL|OPQ|STEST)-[0-9]+\*\*" specifications/security/*.md | sort | uniq -c | awk '$1>1{print "DUP: "$0}'
# empty output = definitions unique
```
