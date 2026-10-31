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

## Accepted secure channel — RFC 0007

The table above remains the baseline. [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
and [ADR-011](../decisions/ADR-011-noise-device-authorization.md) add
`SNTR-SC1-WSS-V1` as an additional secure profile; they do not remove or weaken
the TLS profiles. SC1/WSS requires verified outer TLS 1.3 plus the separately
provisioned Noise server pin.

| Accepted owner | Concern | Requirements |
|---|---|---|
| [secure-channel.md](secure-channel.md) | Shared channel independent of carrier I/O | `SNTR-SC-001`–`SNTR-SC-015` |
| [device-authorization.md](device-authorization.md) | Persistent per-enrollment shared authorization; host enrollment/authorization lifecycle | `SNTR-DAUTH-001`–`SNTR-DAUTH-010` (RFC 0007); `SNTR-DAUTH-011`–`SNTR-DAUTH-024` (accepted [RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md); execution pending) |
| [noise-bindings.md](../transports/noise-bindings.md) | Canonical v1 WSS mapping; restricted TCP/WS; deferred UDP | `SNTR-SCW-001`–`SNTR-SCW-012`; `SNTR-SC1-WSS-V1` |

After the baseline, read RFC 0007 → shared channel → device authorization →
carrier mapping → [registered cases](../../conformance/manifest/sc1-wss.yaml). SC1 uses
`Noise_NK_25519_ChaChaPoly_SHA256` for bootstrap and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for returning devices, with a
host-issued unique random 32-byte shared AK enrolled through authorized
bootstrap. Persistent authorization retains neither traffic keys nor session
state. The core keeps generic principals and opaque application payloads; no
signing-key-pair credential model or post-quantum security is claimed.

## Implementation evidence and remaining work

The [implementation evidence ledger](../../docs/sc1-implementation.md) owns the
historical and current implementation record. The Rust implementation records
local unit/race/native-core/transport tests and security checks. These facts do
not execute the registered `CONF-SCW-*` cases or establish independent
interoperability.

Only out-of-band preprovisioning is delivered; enrollment issuance, protected
storage/transactions and rotation flows are now specified as
`SNTR-DAUTH-011`–`SNTR-DAUTH-024` under accepted
[RFC 0010](../../rfcs/0010-sc1-host-authorization-lifecycle.md) — registration
is not execution, so their runtime implementation remains host work. Host
policy still owns
principal agreement, trusted root identity and synchronous enrollment checking
before `ready`; empty credentials never authorize automatically and nil method
authorization denies access. UDP is deferred; HTTP/HTTPS request-response is
excluded from SC1, with baseline profiles unchanged. Independent vectors,
cross-implementation interoperability, direct-topology tests, mobile/recovery
evidence and independent human security review remain release gates. In-memory
benchmarks are not TLS-relative performance evidence.
