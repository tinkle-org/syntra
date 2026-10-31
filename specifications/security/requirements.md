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

## Accepted SC1 families — RFC 0007

These entries index the accepted
[RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md) profile.
The baseline above and ADR-008 TLS policy remain in effect; SC1/WSS is an
additional secure profile and does not replace them.

| ID family | Defining document | Concern | Status |
|---|---|---|---|
| `SNTR-SC-001`–`SNTR-SC-015` | [secure-channel.md](secure-channel.md) | Carrier-independent NK/NKpsk0 channel, authenticated context, fresh keys/confirmation, bounded records/lifecycle and claim limits | Accepted |
| `SNTR-DAUTH-001`–`SNTR-DAUTH-010` | [device-authorization.md](device-authorization.md) | Shared AK enrollment/storage, scoped handle, generic principal policy, revocation/rotation and trusted integration | Accepted; host lifecycle work is specified by `SNTR-DAUTH-011`–`SNTR-DAUTH-024` below (accepted RFC 0010); execution pending |
| `SNTR-DAUTH-011`–`SNTR-DAUTH-024` | [device-authorization.md](device-authorization.md) | Host enrollment/authorization lifecycle: enrollment authority; AK/handle issuance; staged provisioning transaction; idempotent interrupted enrollment; protected pre-`ready` sequence; enrollment-to-principal binding; immediate new-connection enforcement; bounded staleness (≤300 s hard maximum, 60 s operational target); fail-closed on unknown validity; rotation transaction; epoch integrity/rollback prevention; compromise recovery via independent authority; lifecycle storage control and secret disposal; trusted server-key pin rotation | Registered with accepted [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md) (this wave); execution pending |
| `SNTR-SCW-001`–`SNTR-SCW-012` | [noise-bindings.md](../transports/noise-bindings.md) | Canonical v1 WSS mapping, Upgrade admission, first-envelope rule, restricted TCP/WS and deferred UDP | Accepted |

[Carrier mapping](../transports/noise-bindings.md) registers
`SNTR-SC1-WSS-V1` and its `CONF-SCW-*` cases. Registration is not execution.
The [implementation evidence ledger](../../docs/sc1-implementation.md) retains
historical draft-1 evidence; current Rust local results are recorded
downstream. Those results do not imply coverage of every SC/DAUTH/SCW
obligation, independent interoperability or independent security review.
Enrollment issuance, protected storage/transactions and rotation flows are
specified as `SNTR-DAUTH-011`–`SNTR-DAUTH-024` obligations under accepted
[RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md); registration
is not execution, so implementing them remains host work. UDP remains
deferred and HTTP/HTTPS request-response is excluded from SC1.

## Uniqueness and ownership rules

- IDs are unique suite-wide; new security IDs REQUIRE the prefix of their defining document (`TMOD`, `TSEC`, `ASEC`, `RPL`, `OPQ`, `STEST`; `SC`, `DAUTH` and `SCW` under RFC 0007; `DAUTH-011`–`024` host lifecycle under RFC 0010).
- No ID is defined twice; companions cite, never duplicate (single-definition rule shared with core).
- `SNTR-SEC-*` is intentionally unused to keep per-document traceability; the family prefix `SNTR-*SEC*` collectively denotes security scope.
- Charter `SYN-ARCH-030–035` and core `SNTR-*` remain distinct namespaces; where this suite tightens a core rule (e.g., disclosure), the stricter security rule governs for security claims (SYN-ARCH-043) and MUST be cited in the implementation's conformance report.

## Verification

```sh
grep -rhoE "\*\*SNTR-(TMOD|TSEC|ASEC|RPL|OPQ|STEST|SC|DAUTH)-[0-9]+\*\*" specifications/security/*.md | sort | uniq -c | awk '$1>1{print "DUP: "$0}'
# empty output = definitions unique
```
