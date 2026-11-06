# Conformance test guide

This directory contains test definitions, selectors, fixtures, and evidence
formats for the current Syntra 1.0 pre-release. It does not implement a peer or
grant a runtime verdict. Protocol behavior is owned by
[connection](../specifications/connection.md), [wire format](../specifications/wire-format.md),
[RPC](../specifications/rpc.md), [security](../specifications/security.md),
[transports](../specifications/transports.md), and [recovery](../specifications/recovery.md).
The [IDL](../proto/syntra/v1/) owns representation. A test disagreement never
overrides its cited protocol requirement.

## Suite inputs and selectors

Consume [`profiles.yaml`](profiles.yaml), [`manifest/schema.yaml`](manifest/schema.yaml),
[`manifest/*.yaml`](manifest/), [`manifest/requirements.yaml`](manifest/requirements.yaml),
[`test-vectors/`](test-vectors/), and [`declaration.example.yaml`](declaration.example.yaml).
`CONF-*` IDs identify test definitions; requirement IDs identify their owners.

Syntra has one protocol contract. The `profiles` entries in the test registry
are suite selectors for protocol concerns, carriers, and capabilities. They
do not register distinct Syntra protocols or security profiles, negotiate wire
behavior, or prescribe code organization:

| Selector | Test scope |
|---|---|
| `SNTR-CORE-V1` | Envelopes, serialization, readiness, auth interface, bounds, mandatory refusal behavior |
| `SNTR-SESS-V1` | Connection-bound session, loss/close/expiry, no implicit resumption |
| `SNTR-RPC-V1` | Correlation, deadlines, cancellation, errors, retry discipline |
| `SNTR-EVENTS-V1` | Generic notification/refusal checks and separately negotiated update recovery |
| `SYNTRA-1.0-TCP` | Encrypted TCP, carrier 1 |
| `SYNTRA-1.0-WS` | Protected WS/H1, carrier 2; explicitly enabled loopback development only |
| `SYNTRA-1.0-WSS` | Protected WSS/H1, carrier 3; independently verified TLS ≥1.3 |

A claim names Core, session and RPC coverage over at least one current carrier.
Evaluate each additional carrier independently. Encrypted TCP and verified WSS
are production-permitted; WS evidence carries its restricted-development label.
There is no HTTP request/response or UDP suite binding. The transport owner
defines the carrier policy; selectors allocate no additional protocol behavior.

Capability support requires an exact allocated identifier and the defined
connection negotiation. `syntra.update-recovery/1` is the recovery gate.
Generic application subscription fixtures allocate no event or resume capability.
Mandatory-only peers remain conformant when they correctly refuse unconfirmed
options. Recovery is optional per connection, but its own evidence is required
for a recovery-inclusive claim; Core-only evidence cannot satisfy that claim.

Claims state the exact specification and suite revisions, roles, carriers,
capabilities, security labels, and exclusions, and link their evidence declaration.
A capability not evaluated is never implied to pass. Unqualified “compliant”,
“certified”, or “compatible” wording cannot substitute for that scope.

## Selection and execution

Each profile manifest reference loads all cases or applies its `select` map.
All filter fields must match. `select: {mandatory: true, capabilities: []}`
matches the exact empty capability list, not a wildcard. A profile filter matches
string equality or membership in a list-valued case profile. Shared cases execute
independently for each carrier and role; deduplicate overlapping selections by
case ID only within a carrier/role run. Then apply role and capability gates.
Loading a manifest does not negotiate an option. Core selects capability-free
notification/refusal cases without enabling recovery delivery.

Client-only implementations run applicable initiator halves; host-only run host
halves; full-stack implementations run both. Execute every mandatory applicable
case, including negatives and refusal probes. Optional capability cases run only
when claimed and their connection negotiation is established. Application-defined
stream checks require explicit harness setup; they cannot infer an allocated
protocol capability or a recovery guarantee.

`applicable_profiles` excludes other exact bindings during selection, without
creating a SKIP result. `applicable_transports` is a carrier-family applicability
filter (`tcp_tls` for encrypted TCP, `ws_wss` for WS/WSS); an empty intersection
permits an explicitly reasoned SKIP citing that key. The family label does not
require TLS on encrypted TCP. WSS-only certificate tests are not TCP tests.

Fixtures use neutral echo/key-value/subscription payloads, throwaway credentials
and documentation hostnames. Protobuf vectors compare decoded logical fields,
not encoder byte equality. Chosen framing/context fixtures may be byte-exact.
Public context vectors do not establish Noise ciphertext interoperability.
Certificate fixtures reference harness PKI identities, never production keys;
no frozen raw TLS exchange is required. Deadline tests use injected clocks or
explicit margins with expiry assertions.

## Manifest authoring and harness conventions

Manifests are portable YAML 1.2 maps. Preserve existing current case identities;
do not reuse a removed ID for a different test. The machine schema owns types
and vocabularies. A case cannot invent behavior beyond its cited requirements.

| Field | Contract |
|---|---|
| `id`, `requirement`, `profile` | Case ID, non-empty requirement list, one selector or non-empty independently applicable selector list |
| `roles`, `capabilities`, `mandatory` | Applicable client/server roles, prerequisite capabilities, mandatory execution flag |
| `applicable_transports` | Optional non-empty carrier-family filter; absence applies to all selected carriers |
| `applicable_profiles` | Optional exact current-binding filter; excluded bindings do not generate a verdict |
| `preconditions` | Non-empty explicit setup list |
| `input` | Frames, transport actions, structured faults/coordination, throwaway credentials |
| `expected` | Connection/session state, emitted frames, typed error, native observations, hygiene assertions |
| `control_connection` | Fresh paired control with structured setup and expectations |
| `notes` | Explanation, never extra protocol behavior |

### expected.frames entries

`expected.frames` lists only emitted response Frames, never injected stimuli or
native Close/status/alert signals. Entries contain Frame fields `request_id`,
`body`, `payload_b64` and assertion helpers `shape`, `note`, `has_connection_id`.
Credentials are input metadata, never expected Frame fields. Associate results
by echoed request ID and bit-identical payload. That alone cannot establish
principal-sensitive authorization without a corresponding assertion.

For failures, `expected.error.observer` distinguishes `detecting_host` from
`detecting_peer`; omission uses the initiator's exchange-context outcome.
`carriage: local_only` plus `frames: []` asserts no invented Syntra error envelope.
Native peer evidence is separate under `expected.transport.peer_observation`.
A generic close never proves the detector's exact private cause.
`message_pattern` is a case-insensitive substring or `NEGATIVE:` hygiene list,
never an application decision based on diagnostic wording.

Race-sensitive cases use structured barriers/injected clocks, never sleeps or
prose-only coordination. `duplicate_while_pending` holds the original handler's
completion candidate behind `first_terminal_result` until violation and closure.
Only an uncommitted candidate or undeliverable output is discarded; a selected
terminal outcome stays immutable even when closure prevents delivery. Invalid
stimuli are harness injections, not conformant client emissions.
`reverse_completion_order: {barrier: all_admitted}` tests correlation independently
of scheduling. Paired controls assert their own outcomes on fresh connections
with the same principal/scope/selector basis where required.

`*_b64` uses RFC 4648 standard-alphabet base64 of exact bytes. `*_hex` is lowercase
hex without prefixes/separators; strip whitespace in grouped displays.
`payload_b64: ""` is selected empty success, distinct from an absent outcome.
Resolve references against the schema, current requirement/profile registries
and retained vector paths.

Negative coverage is required for every `MUST NOT` and failure-mapping row.
Each requirement has an automated, partially automated, manual, or reasoned
not-testable disposition. A `test_ids` edge must name an existing case that
actually cites that requirement. Do not invent coverage to fill a registry:
use `test_ids: []`, a manual/not-testable disposition, and explanatory notes when
no adequate executable case exists. Neither registration nor an `automated`
authoring disposition asserts a run or PASS. Owner synchronization changes
locations only, not membership, coverage, automation status, or evidence.

## Verdicts and evidence

| Verdict | Meaning | Counts as PASS? |
|---|---|---|
| `PASS` | Executed; every assertion held; logs retained | Yes |
| `FAIL` | Assertion failed, crash, hang beyond bound, or unlisted error | No |
| `SKIP` | Not executed because cited precondition/applicability is absent | No |
| `UNSUPPORTED` | Executed refusal probe correctly declined an unconfirmed option | No; proves refusal only |
| `NOT_EXECUTED` | Planned, blocked or omitted; never run | No |

Never infer, copy or report PASS without execution and retained logs. Harness
inconvenience cannot justify skipping a mandatory case. An incomplete mandatory
run remains incomplete. Report SKIP/UNSUPPORTED separately; mandatory executed
pass-rate is `PASS / (PASS + FAIL)`, excluding them.

Implementation declarations name implementation/version/repository, roles,
exact selectors, allocated capabilities and their contracts, security labels,
documented bounds/defaults, executed IDs, runner/tool, exact specification and
suite revision pinned at execution, per-case verdicts, and rerunnable log
references. They live with the implementation and do not imply that its code
resides in this repository. Retain source IDL, schema, fixtures, compatibility
records and generator/tool provenance for reproduction.

**SNTR-CORE-901** — Evidence MUST cite requirement IDs and their ownership;
implementation behavior alone is not normative. A registered case,
generated-type round trip, benchmark, local unit test, or successful
build is not an executed manifest verdict, independent interoperability,
human review, freeze, or release authorization.

## Independent interoperability and acceptance evidence

Use the [matrix](interoperability/matrix.yaml) and
[scenarios](interoperability/scenarios.yaml) to record planned pairings.
Independent evidence requires genuinely different codebases, A initiator/B host
and then B initiator/A host, both versions/bounds, and per-leg logs. Two checkouts
or native linkage to the same implementation are not independent. Compare logical
requests/results and opaque bytes alongside each carrier's establishment/framing
assertions. A single-carrier claim needs one secure carrier; a transport/dimension
independence claim needs two named carrier legs. One carrier never certifies another.

Acceptance and release decisions follow [governance](../GOVERNANCE.md) and the
[release process](../RELEASE.md), not this guide or its static checks.

Fault runs record the governing requirements and cases, exact tested versions,
role, mode, carrier, bounds, random seed, faults, commands, outcomes, and cleanup.
Use an outer harness deadline. Exercise malformed and split inputs, request-ID
ordering, confirmation and principal checks, deadline/cancel/loss races, partial
output, slow consumers, and fresh establishment after loss. Recovery tests cover
checkpoint and snapshot persistence across crashes. Security tests cover
enrollment, revocation, rotation, store failures, and permitted endpoint topology.

When testing suspension and restart, record the environment and elapsed-time
behavior. A simulated clock is useful for protocol assertions but does not prove
behavior on a particular operating system. Neither a test harness nor a passing
build establishes application persistence correctness or independent security review.

## Security test groups

**SNTR-STEST-001** — Invalid/untrusted/malformed WSS certificates fail
before hello/credential release, with no fallback and generic failure to waiters.

**SNTR-STEST-002** — A valid chain for the wrong DNS/IP identity fails
before credentials; chain validity alone is insufficient. Tests cover
wrong SAN and inappropriate CN-only identity handling.

**SNTR-STEST-003** — Expired credentials fail `UNAUTHENTICATED` in the
appropriate phase without establishing an unauthorized binding.

**SNTR-STEST-004** — Revoked credentials fail at admission and active
bindings terminate within the documented, bounded propagation contract.

**SNTR-STEST-005** — Valid but insufficient principals receive
`PERMISSION_DENIED` for protected methods/subscriptions without handler
effects or undocumented existence oracles.

**SNTR-STEST-006** — A diagnostic connection ID presented as a credential
MUST NOT restore a session or authority. A new connection requires fresh
authentication under current host policy.

**SNTR-STEST-007** — Test otherwise-valid serialized Frames of MAX,
MAX+1, and 2×MAX, counting all envelope overhead. MAX is accepted only if
all other validation/state/auth/field bounds pass; oversize follows its
lawful resource-error/close path without panic/allocation failure.
Separately test method, credential, payload, and notification field caps;
never enlarge independent limits to construct a total-frame fixture.
Simulated application ciphertext uses the same bounds.

**SNTR-STEST-008** — Truncated varints/prefixes, incomplete handshakes,
and slow-drip inputs fail deterministically under decode/assembly/deadline
rules; slow clients are closed, not retained indefinitely.

**SNTR-STEST-009** — Flood handshakes, calls, subscriptions, and queues
from one principal while a conformant principal operates; verify bounded
rejection, offender isolation, documented priority, and recovery without restart.

**SNTR-STEST-010** — Reject weak WSS TLS, fallback after endpoint/channel
failure, downgraded wire/profile behavior, and endpoint-validation
confusion; verify highest secure overlap and no credential disclosure.

**SNTR-STEST-011** — Re-evaluate credential/handle/connection-ID misuse
across connections, principals, and carriers; deny cross-principal use
and fixation, never accept diagnostic IDs as authentication.

**SNTR-STEST-900** — Every group MUST include traces proving credential/
token absence from URLs/logs/errors/metrics labels, message-hygiene
checks, timing-robust criteria, and accurate secure/restricted-carrier
labels. Execute applicable certificate cases on WSS; encrypted TCP has
its independent pin/channel tests, never a fictitious TLS layer.

Channel/lifecycle tests also cover independently derived NK/NKpsk0 vectors,
wrong pins/AKs, unauthorized/interrupted enrollment, lookup collision/scope/epoch,
expiry/revocation/rotation races, replayed first flights with no effects before
fresh client confirmation, no 0-RTT, cross-carrier fresh keys, invalid tags/nonces,
lifetime/record/frame bounds, partial I/O and aggregate resources. No UDP result
is implied. Deterministic test RNG is never a production API.

Security-adjacent reviews cite affected threat/requirement IDs and applicable
negatives; analyze construction, trust provisioning, freshness, lifecycle/storage,
opacity, hygiene, downgrade, resources and compatibility; and record unresolved
objections/risks in the public approval process. Checks are not approval evidence;
the decision record identifies the actual approver and independence.

## Repository checks

From the root, run:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/sync-conformance-owners.py
python3 scripts/migrate-conformance-1.0.py
python3 scripts/validate-repo.py all
```

Owner discovery reads the six protocol pages, this guide, and the optional
schema-tooling guide. `--write` on the sync scripts updates only their described
metadata/fixture outputs; review registry membership and test edges separately.
Schema validation and repository-boundary gates remain independent checks in CI.

## Scoped terminal-receipt definitions

[RFC 0014](../rfcs/0014-scoped-terminal-receipt.md) is canonically adopted as
`SNTR-TRC-001` through `SNTR-TRC-013` in the four existing owners.
[`rpc.yaml`](manifest/rpc.yaml) registers `CONF-TRC-001` through `CONF-TRC-014`;
their numeric suffixes map one-to-one to accepted local cases `R14-T01` through
`R14-T14`. All fourteen groups are **NOT_EXECUTED**. The requirement rows' partial
automation disposition describes authored assertions plus required adapter,
platform and application review; no harness or execution is supplied here.

The existing RPC selector loads these cases without registering a new selector
or capability. `CONF-TRC-001` is mandatory refusal/default coverage; unsupported
hosts reject before mutation and retain ordinary withdrawal. The remaining
groups are optional operation-specific definitions requiring explicit host
support, method policy and coordinated runtime/driver/authority setup. A runner
records that setup and executes them for an operation-inclusive claim. Merely
loading the manifest, enabling a carrier or matching an application method name
cannot enable the host operation. These cases allocate no wire negotiation.

`input.faults.terminal_receipt` describes harness-local structured stimuli, never
wire fields: `rfc_case` is the accepted alias; `barrier` and `release_after` order
the named boundary; `variants` are independently executed setups with expected
dispositions. `fixed_result` describes only the healthy variant's response.
`expected.transport.positive_assertions` must hold; `negative_assertions` must
remain false in their applicable variants. Mixed positive/negative groups do not
assert a single common emitted Frame list. Record each variant's observations;
a group passes only when all its applicable variants pass. Expand combined
fault dimensions independently as the case notes require, using deterministic
barriers and injected clocks, not sleeps.

Run existing withdrawal, correlation, cancellation, deadline and loss suites as
well. `CONF-TRC-014` composes the thirteen groups in both independent TCP role
directions, including fragmentation and forced loss. Custom drivers and portable
builds require their own runs; TCP does not prove other permitted carriers.
Synthetic authority proves neither production persistence nor client storage.
Maintain distinct evidence for selection, queue admission, write, peer receipt,
durable storage and joined cleanup.

### Unrelated HTTP adoption guard

`scripts/check-http-candidate.py` retains RFC 0013's original base revision
`3f7e8ea037fefcc5c86101d23e7722c83e28a0d3`. Every pre-existing byte in its guarded
inputs is still compared to that immutable Git blob. Only six exact appendices
are permitted: four owner sections, thirteen requirement rows and the fourteen
RPC case groups. Their complete suffixes are SHA-256 pinned in the checker;
there is no generic marker bypass, baseline replacement or regeneration option.
An edit to old text/rows, extra appendix content, changed limits, ID drift or an
HTTP mapping addition fails. Separate semantic checks validate the RFC's accepted
case trace, canonical owner mapping and reciprocal edges. Pin changes require
explicit review; pins themselves do not prove approval or protocol execution.

The HTTP candidate's accepted-unadopted metadata, activation/claimability gates,
profiles, context vectors, schema and compatibility inputs remain intact.
`--require-adoption` still exits 2 for RFC 0013 after successful static checks.
