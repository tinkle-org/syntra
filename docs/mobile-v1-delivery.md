# Mobile v1 specification-driven delivery

Status: selected delivery target, not a release verdict. SC1/WSS is accepted;
[RFC 0008](../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md) remains Draft,
so the mobile lifecycle and recovery portions are not yet normative.
[Release readiness](../audits/v1-release-readiness.md) records remaining
gates. Formal normative acceptance remains governed by `GOVERNANCE.md` §3.

## Scope and boundaries

The target includes core handshake/auth/RPC/error correctness, canonical SC1,
update recovery, bounded mobile lifecycle and independent Rust/Go evidence.
Recovery remains an explicitly negotiated optional wire profile: a Core-only
peer can interoperate at Core level but does not satisfy this release bundle.
An application requiring recovery receives a failure if negotiation cannot
provide it; silent reduced-functionality success is not the target contract.

Initial public testing uses SC1 over verified TLS 1.3 WSS. Test every additional
claimed carrier independently. Existing baseline profiles remain unchanged until
accepted owner edits. UDP, QUIC, logical-session resumption, reliable-session
RPC reconciliation, application E2EE and transparent mutation replay are deferred.
Update recovery resumes durable progress under a fresh subscription, not the
old connection, traffic keys or arbitrary RPC execution.

This repository owns specifications, schemas and conformance definitions.
`syntra-rs` and `syntra-go` own implementation, generated types, runners and
mobile/FFI integration. No implementation source or generated binding is added
here. No production secrets or private infrastructure are prerequisites.

The selected first increment is specification-only, with SC1 over verified WSS
as the initial production release target rather than certification of all
baseline transports. A sole active maintainer needs an explicit governance
transition, not an invented second approval. [Draft RFC 0009](../rfcs/0009-v1-bootstrap-governance-and-release-scope.md)
proposes that transition and the exact scope; the
[acceptance package](v1-acceptance-package.md) maps the follow-up changes.
Current quorum, baseline profile meanings and release gates remain unchanged
until the applicable decisions and owner edits are recorded.

## Dependency-ordered work and exit criteria

| Stage | Deliverable | Exit evidence |
|---|---|---|
| 0. Approval process | RFC 0009 governance/scope proposal and decision-record format; actual owner ratification/roster and authorized process edits next | Verifiable public transition or existing quorum; no retroactive protocol/security approval |
| 1. Decisions | RFCs 0001–0005 core/parser/identity/bounds; RFC 0006 recovery amendment; RFC 0007 canonical SC1; RFC 0008 mobile lifecycle | Explicit compatibility designation, protocol/security reviews, maintainer acceptance |
| 2. Normative activation | Synchronize owning specifications, authorized schema edits, permanent requirement IDs, profile/case definitions and positive/negative fixtures | No contradictory owner text; structural/Buf checks pass; reviewed requirement-to-case mapping |
| 3. Downstream alignment | Both independent implementations pin the same accepted revision; generated types refreshed where authorized; TDD fixes and host-policy/lifecycle examples | Package/runtime/adapter/security tests; ABI/mobile builds and bridge lifecycle tests where applicable |
| 4. Independent execution | Pure Go ↔ Rust in both roles; SC1 bootstrap/returning, required recovery, faults and deployment contracts | Exact commits, commands, bounds, vectors, logs and per-case verdicts; no mandatory omissions |
| 5. Mobile/operational assurance | Supported iOS/Android lifecycle tests, weak networks, idle/paused cost, soak and independent composition review | Declared performance/resource/revocation budgets met; failures retained as regressions |
| 6. Documentation/release | Guides, migrations, results and precise profile claims | Evidence-backed readiness assessment and maintainer-authorized release |

Specifications and expected results precede implementation. An interoperability
discovery that changes behavior goes back through RFC review, not an explanatory
doc edit that makes code authoritative. After execution, finalize implementation
guidance, supported-profile claims and measured limitations.

## SC1 interoperability status

The earlier Rust local-revision-1 and Go draft-1 formats were incompatible in
context, mode values, prologue and WS subprotocol. RFC 0007 §11.4 now fixes the
canonical `syntra.sc1.v1` format, and the Rust implementation at
`tinkle-org/syntra-rs` main (`50ca849`) implements that proposal. No legacy
identifier is an alias. Independent pure-Go/Rust execution in both roles and
both modes remains outstanding; same-implementation passes do not close it.

[Public context fixtures](../conformance/plans/sc1-context-v1.json) are checked
by `tests/test_sc1_proposal_vectors.py`. They contain no cryptographic vectors.
Independent Noise vectors and real sockets remain gates in the
[mobile acceptance plan](../conformance/plans/mobile-v1.md). Native Go backed
by Rust is useful ABI evidence but is not the second independent implementation.

## Inspiration and provenance

The architectural comparison used
[MTProto engine commit da4b217](https://github.com/TelegramMessenger/mtproto-engine/tree/da4b2170210aab0430c4ff18c032991f3030cf45),
specifically README architecture/testing, `session_runtime.rs` pause/network
handling, `clock.rs`, `tests/paused_cost.rs`, and `docs/protocol-coverage.md`.
Useful ideas are deterministic state-machine inputs, explicit lifecycle hooks,
fault simulation, paused/idle cost tests and reproducible state exploration.
This records source inspection, not independent reproduction of its benchmarks.
No source or prose is copied into Syntra. MTProto retransmission/deduplication,
cryptography and service-specific semantics do not become Syntra requirements.

## Current evidence limits

This change supplies selected proposals, planned acceptance scenarios and public
context fixture lint. It does not supply accepted normative owner edits,
registered SC1 cases, a cryptographic vector corpus, downstream wire alignment,
mobile execution, independent security approval or interoperability PASS.
Actual validation commands and results are recorded in the readiness audit.
